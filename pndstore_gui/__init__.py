"""This package provides the graphical user interface to PNDstore."""

import gtk, os.path
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


    def get_selected(self):
        treemodel, treeiter = self.view.get_selection().get_selected()
        return packages.Package(treemodel.get_value(treeiter, 0))


    # Event callbacks.
    def on_window_destroy(self, window, *data):
        gtk.main_quit()


    def on_button_install(self, button, *data):
        pass


    def on_button_remove(self, button, *data):
        self.get_selected().remove()
        self.update_treeview()


    def on_button_upgrade(self, button, *data):
        for p in packages.get_updates():
            p.upgrade()
        self.update_treeview()


    def on_button_update(self, button, *data):
        database_update.update_local()
        database_update.update_remote()
        self.update_treeview()
