"""This module implements various functions to give information on the database of applications.  And by "various", I mean "get_updates" and the functions it uses, but more could come later."""

import options, sqlite3
from distutils.version import LooseVersion
from database_update import LOCAL_TABLE, REPO_INDEX_TABLE



class PNDVersion(LooseVersion):
    """Gives the flexibility of distutils.version.LooseVersion, but ensures that any text is always considered less than anything else (including nothing)."""
    def __cmp__(self, other):
        if isinstance(other, str):
            other = self.__class__(other)

        for i,j in map(None, self.version, other.version):
            iStr = isinstance(i, str)
            jStr = isinstance(j, str)
            if iStr and not jStr: return -1
            elif jStr and not iStr: return 1
            else:
                c = cmp(i,j)
                if c != 0: return c
        return 0 # If it hasn't returned yet, they're the same.



def get_remote_tables():
    """Checks the remote index table to find the names of all tables containing data from remote databases.  Returns a list of strings."""
    with sqlite3.connect(options.get_database()) as db:
        db.row_factory = sqlite3.Row
        c = db.execute('Select url From "%s"' % REPO_INDEX_TABLE)
        names = [i['url'] for i in c]
    return names



def get_all_available(pkgid):
    """Returns a list of all available instances of the package "pkgid", including local and remote ones."""
    tables = [LOCAL_TABLE]
    tables.extend(get_remote_tables())
    pkgs = []
    with sqlite3.connect(options.get_database()) as db:
        db.row_factory = sqlite3.Row
        pkgs = [db.execute('Select * From "%s" Where id=?'
            % i, (pkgid,)).fetchone() for i in tables]
    return pkgs



def get_all_available_sorted(pkgid):
    pkgs = get_all_available(pkgid)
    pkgs = [i for i in pkgs if i is not None]
    pkgs.sort( key = lambda i: PNDVersion(i['version']), reverse = True)
    return pkgs



def get_updates():
    """Checks for updates for all installed packages.  Returns a list containing row objects for each remote package that is an update."""
    pass
