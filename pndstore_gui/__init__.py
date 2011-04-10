"""This package provides the graphical user interface to PNDstore."""

import gtk, os.path, warnings
from pndstore import database_update, packages

class PNDstore(object):
    "The main GUI object that does all the work."

    def __init__(self):
        builder = gtk.Builder()
        builder.add_from_file(
            os.path.join( os.path.dirname(__file__), 'PNDstore.glade') )
        builder.connect_signals(self)

        self.window = builder.get_object('window')
        self.window.show()

        # Load up the treemodel with package info.
        self.view = builder.get_object('treeview')
        self.update_treeview()


    def update_treeview(self):
        model = self.view.get_model()
        model.clear()

        for p in packages.get_all():
            latest = p.get_latest()
            info = latest.db_entry
            if p.local.exists:
                v_local = p.local.db_entry['version']
                if p.local is not latest:
                    icon = 'system-software-update'
                else:
                    icon = 'emblem-default'
            else:
                v_local = None
                icon = None

            model.append( ( p.id,
                info['title'],
                info['description'],
                v_local,
                info['version'],
                icon, ) )


    def display_warnings(self, func, *args, **kwargs):
        """Calls func with *args and **kwargs, then displays a dialog with any
        warnings detected."""
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always')
            func(*args, **kwargs)
            if len(w) > 0:
                m = "The following errors were detected in %s:\n%s" % (
                    func.__name__, '\n'.join( [str(i.message) for i in w]) )
                dialog = gtk.MessageDialog(type=gtk.MESSAGE_WARNING,
                    parent=self.window, buttons=gtk.BUTTONS_OK, message_format=m)
                dialog.run()
                dialog.destroy()


    def get_selected(self):
        treemodel, treeiter = self.view.get_selection().get_selected()
        return packages.Package(treemodel.get_value(treeiter, 0))


    def install_etc(self, pkg):
        "Wrapper around Package.install and Package.upgrade."
        if pkg.local.exists:
            if pkg.local is pkg.get_latest():
                dialog = gtk.MessageDialog(buttons=gtk.BUTTONS_OK,
                    parent=self.window, message_format='Already up-to-date.')
                dialog.run()
                dialog.destroy()
            else:
                d = gtk.MessageDialog(parent=self.window, flags=gtk.DIALOG_MODAL,
                    type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO,
                    message_format="Do you want to upgrade %s?\nVersion %s -> %s"
                        % ( pkg.local.db_entry['title'], pkg.local.version,
                        pkg.get_latest().version ) )
                if d.run() == gtk.RESPONSE_YES:
                    pkg.upgrade()
                    self.update_treeview()
                d.destroy()
        else:
            # Pop up install location chooser.
            d = gtk.Dialog(title="Select install location.",
                parent=self.window, flags=gtk.DIALOG_MODAL,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                    gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
            box = gtk.combo_box_new_text()
            for t in packages.get_searchpath_full():
                box.append_text(t)
            box.set_active(0)
            d.vbox.pack_start(box)
            box.show()
            if d.run() == gtk.RESPONSE_ACCEPT:
                pkg.install(box.get_active_text())
                self.update_treeview()
            d.destroy()



    # Event callbacks.
    def on_window_destroy(self, window, *data):
        gtk.main_quit()


    def on_button_install(self, button, *data):
        p = self.get_selected()
        self.install_etc(p)


    def on_button_remove(self, button, *data):
        self.get_selected().remove()
        self.update_treeview()


    def on_button_upgrade(self, button, *data):
        # TODO: Give summary, request confirmation.
        for p in packages.get_updates():
            p.upgrade()
        self.update_treeview()


    def on_button_update(self, button, *data):
        self.display_warnings(database_update.update_local)
        self.display_warnings(database_update.update_remote)
        self.update_treeview()
