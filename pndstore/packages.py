"""
This module implements a means of interacting with and acting on package
data.  Notable is the Package class that encapsulates all available versions of
a package, also allowing for installation and removal.  Also, the get_updates
function is useful.
"""

import options, database_update, sqlite3, os, shutil, urllib2, md5
from distutils.version import LooseVersion
from database_update import LOCAL_TABLE, REPO_INDEX_TABLE, SEPCHAR


class PackageError(Exception): pass



class PNDVersion(LooseVersion):
    """Gives the flexibility of distutils.version.LooseVersion, but ensures that
    any text is always considered less than anything else (including nothing)."""
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
    """Checks the remote index table to find the names of all tables containing
    data from remote databases.  Returns a list of strings."""
    with sqlite3.connect(options.get_database()) as db:
        db.row_factory = sqlite3.Row
        c = db.execute('Select url From "%s"' % REPO_INDEX_TABLE)
        names = [i['url'] for i in c]
    return names



class PackageInstance(object):
    """Gives information on a package as available from a specific source.
    This should not generally used by external applications.  The Package class
    should cover all needs."""

    def __init__(self, sourceid, pkgid):
        "sourceid should be the name of the table in which to look for this package."
        self.sourceid = sourceid
        self.pkgid = pkgid

        with sqlite3.connect(options.get_database()) as db:
            db.row_factory = sqlite3.Row
            self.db_entry = db.execute('Select * From "%s" Where id=?'
                % database_update.sanitize_sql(sourceid), (pkgid,)).fetchone()
        self.exists = self.db_entry is not None
        self.version = ( self.exists and PNDVersion(self.db_entry['version'])
            or PNDVersion('a') ) # This should be the lowest possible version.


    def install(self, installdir):
        # Check if this is actually a locally installed file already.
        if os.path.exists(self.db_entry['uri']):
            raise PackageError('Package is already installed.')
            # Or maybe skip the rest of the function without erroring.

        # Make connection and determine filename.
        p = urllib2.urlopen(self.db_entry['uri'])
        header = p.info().getheader('content-disposition')
        fkey = 'filename="'
        if header and (fkey in header):
            n = header.find(fkey) + len(fkey)
            filename = header[n:].split('"')[0]
        else:
            filename = os.path.basename(p.geturl())
        path = os.path.join(installdir, filename)

        data = p.read()
        if not md5.new(data).hexdigest() == self.db_entry['md5']:
            raise PackageError("File corrupted.  MD5 sums do not match.")

        # Put file in place.  No need to check if it already exists; if it
        # does, we probably want to replace it anyways.
        with open(path, 'wb') as dest:
            dest.write(data)

        # Update local database with new info.
        database_update.update_local_file(path)

        # TODO, maybe: Make parent Package recreate its self.local.



class Package(object):
    """Informs on and modifies any package defined by a package id.  Includes
    all locally-installed and remotely-available versions of that package."""

    def __init__(self, pkgid):
        self.id = pkgid

        self.local = PackageInstance(LOCAL_TABLE, pkgid)
        self.remote = [PackageInstance(i, pkgid) for i in get_remote_tables()]


    def get_latest_remote(self):
        return max(self.remote, key=lambda x: x.version)


    def get_latest(self):
        """Returns PackageInstance of the most recent available version.
        Gives preference to locally installed version."""
        m = self.get_latest_remote()
        return self.local.version >= m.version and self.local or m


    def install(self, repo=None):
        pass


    def upgrade(self):
        installdir = os.path.dirname(self.local.db_entry['uri'])
        # Remove and hope we don't get a failure that would result in a bad DB.
        os.remove(self.local.db_entry['uri'])
        # Install the latest remote.
        m = self.get_latest_remote()
        if not m.exists:
            raise PackageError('No remote from which to upgrade %s.' % self.id)
        m.install(installdir)
        # Local table has changed, so update the local PackageInstance.
        self.local = PackageInstance(LOCAL_TABLE, self.id)


    def remove(self):
        "Remove any locally-installed copy of this package."
        # Check if it's even locally installed.
        if not self.local.exists:
            raise PackageError("%s can't be removed since it's not installed." % self.id)
        # If so, remove it.
        os.remove(self.local.db_entry['uri'])
        # Remove it from the local database.
        with sqlite3.connect(options.get_database()) as db:
            db.execute('Delete From "%s" Where id=?' % LOCAL_TABLE, (self.id,))
            db.commit()
        # Local table has changed, so update the local PackageInstance.
        self.local = PackageInstance(LOCAL_TABLE, self.id)


    def remove_appdatas(self):
        # Use libpnd to find location of all appdatas.
        # shutil.rmtree all of them
        # Maybe create a way to remove appdatas of individual apps?
        pass



def get_all():
    """Returns Package object for every installed package."""
    with sqlite3.connect(options.get_database()) as db:
        c = db.execute('Select id From "%s"' % LOCAL_TABLE)
        return [ Package(i[0]) for i in c ]


def get_updates():
    """Checks for updates for all installed packages.
    Returns a list of Package objects for which a remote version is newer than
    the installed version.  Does not include packages that are not locally installed."""
    return [ i for i in get_all() if i.local is not i.get_latest() ]
