"""This package provides the graphical user interface to PNDstore."""

import gtk, os.path, warnings, threading, time
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
        self.window.maximize()

        self.statusbar = builder.get_object('statusbar')

        # Load up the treemodel with package info.
        self.view = builder.get_object('treeview')
        self.update_treeview()

        # Only one thread can perform operations on the database.
        self.op_thread = threading.Thread()
        self.op_thread.start()

        self.cid = self.statusbar.get_context_id('status')


    def update_treeview(self):
        model = self.view.get_model()
        model.clear()

        for p in packages.get_all():
            latest = p.get_latest()
            remote = p.get_latest_remote()
            info = latest.db_entry

            if remote.exists:
                v_remote = remote.db_entry['version']
            else:
                v_remote = None

            if p.local.exists:
                v_local = p.local.db_entry['version']
                if p.local is not latest:
                    icon = 'system-software-update'
                else:
                    icon = 'emblem-default'
            else:
                v_local = None
                icon = None

            model.append( (
                info['title'],
                p.id,
                info['description'],
                v_local,
                v_remote,
                icon, ) )


    def get_selected(self):
        treemodel, treeiter = self.view.get_selection().get_selected()
        return packages.Package(treemodel.get_value(treeiter, 1))


    def install(self, pkg):
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
                    message_format=u"Do you want to upgrade %s?\nVersion %s \u2192 %s"
                        % ( pkg.local.db_entry['title'], pkg.local.version,
                        pkg.get_latest().version ) )

                if d.run() == gtk.RESPONSE_YES:
                    self.op_thread.join()

                    class ThreadUpgrade(threading.Thread):
                        def run(thread):

                            self.statusbar.push(self.cid, 'Upgrading %s...' %
                                pkg.local.db_entry['title'])
                            pkg.upgrade()
                            self.statusbar.pop(self.cid)

                            self.update_treeview()

                    self.op_thread = ThreadUpgrade()
                    self.op_thread.start()

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

            words = gtk.Label(
                '\nThis will take a while after clicking OK.  Please be patient.')
            d.vbox.pack_start(words)
            words.show()

            if d.run() == gtk.RESPONSE_ACCEPT:
                self.op_thread.join()

                class ThreadInstall(threading.Thread):
                    def run(thread):

                        self.statusbar.push(self.cid, 'Installing %s...' %
                            pkg.get_latest().db_entry['title'])
                        pkg.install(box.get_active_text())
                        self.statusbar.pop(self.cid)

                        self.update_treeview()

                self.op_thread = ThreadInstall()
                self.op_thread.start()

            d.destroy()


    def remove(self, pkg):
        "Wrapper around Package.remove."

        if pkg.local.exists:
            d = gtk.MessageDialog( parent=self.window, flags=gtk.DIALOG_MODAL,
                type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO,
                message_format="Are you sure you want to remove %s?\nAppdata will not be removed."
                    % pkg.local.db_entry['title'] )
            if d.run() == gtk.RESPONSE_YES:
                # Make sure op_thread is finished before acting.
                self.op_thread.join()
                pkg.remove()
                self.update_treeview()
            d.destroy()
        else:
            d = gtk.MessageDialog( parent=self.window, flags=gtk.DIALOG_MODAL,
                buttons=gtk.BUTTONS_OK, message_format="Not locally installed.")
            d.run()
            d.destroy()


    def upgrade_all(self, pkgs):
        d = gtk.Dialog(title="Select packages to upgrade.",
            parent=self.window, flags=gtk.DIALOG_MODAL,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

        checks = {}
        for p in pkgs:
            b = gtk.CheckButton(u'%s %s \u2192 %s' % (p.local.db_entry['title'],
                p.local.version, p.get_latest().version))
            b.set_active(True)
            checks[p] = b
            d.vbox.pack_start(b)
            b.show()

        if d.run() == gtk.RESPONSE_ACCEPT:
            self.op_thread.join()

            class ThreadUpgrades(threading.Thread):
                def run(thread):

                    for p in pkgs:
                        if checks[p].get_active():
                            self.statusbar.push(self.cid, 'Upgrading %s...' %
                                p.local.db_entry['title'])
                            p.upgrade()
                            self.statusbar.pop(self.cid)

                    self.update_treeview()

            self.op_thread = ThreadUpgrades()
            self.op_thread.start()

        d.destroy()


    def update_all(self):
        # Make sure this isn't running already.
        if self.op_thread.is_alive(): return

        class ThreadUpdates(threading.Thread):
            def run(thread):

                with warnings.catch_warnings(record=True) as w:
                    warnings.filterwarnings('always')

                    self.statusbar.push(self.cid,
                        'Updating remote package list...')
                    database_update.update_remote()
                    self.statusbar.pop(self.cid)

                    self.statusbar.push(self.cid,
                        'Updating local package list...')
                    database_update.update_local()
                    self.statusbar.pop(self.cid)

                self.update_treeview()

                for msg in w:
                    self.statusbar.push(self.cid, str(msg.message))
                    time.sleep(5)
                    self.statusbar.pop(self.cid)

        self.op_thread = ThreadUpdates()
        self.op_thread.start()



    # Event callbacks.
    def on_window_destroy(self, window, *data):
        gtk.main_quit()


    def on_row_activated(self, treeview, path, view_column, *data):
        self.install(self.get_selected())


    def on_button_install(self, button, *data):
        self.install(self.get_selected())


    def on_button_remove(self, button, *data):
        self.remove(self.get_selected())


    def on_button_upgrade(self, button, *data):
        p = packages.get_updates()
        if len(p) > 0:
            self.upgrade_all(p)
        else:
            d = gtk.MessageDialog( parent=self.window, flags=gtk.DIALOG_MODAL,
                buttons=gtk.BUTTONS_OK, message_format="No upgrades available.")
            d.run()
            d.destroy()


    def on_button_update(self, button, *data):
        self.update_all()
