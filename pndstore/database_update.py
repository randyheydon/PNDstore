import options, urllib2, sqlite3, json, ctypes

#This module currently only supports version 1.0 of the PND repository
#specification as seen at http://pandorawiki.org/PND_repository_specification
REPO_VERSION = 1.0

LOCAL_TABLE = 'local'
REPO_INDEX_TABLE = 'repo_index'

class RepoError(Exception): pass


def sanitize_sql(name):
    """The execute method's parametrization does not work for table names.  Therefore string formatting must be used, which bypasses the sqlite3 package's sanitization.  This function takes a stab at sanitizing.  Since table names are put in double quotes (thereby representing an SQL identifier), any characters should be fine except double quotes.  But since all table names are URLs read from a JSON file, they likely won't include quotes, so this function is mostly useless."""
    return str(name).translate(None, '"')
    #TODO: Remove str call once/if it's not needed.


def create_table(cursor, name):
    name = sanitize_sql(name)
    cursor.execute("""Create Table If Not Exists "%s" (
        id Primary Key,
        version_major Int Not Null,
        version_minor Int Not Null,
        version_release Int Not Null,
        version_build Int Not Null,
        uri Not Null,
        title Not Null,
        description Not Null,
        author,
        vendor,
        icon,
        icon_cache Buffer
        )""" % name)
    #TODO: Holy crap!  Forgot categories!


def open_repos():
    repos = []
    with sqlite3.connect(options.get_database()) as db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        #Create index for all repositories to track important info.
        c.execute("""Create Table If Not Exists "%s" (
            url Primary Key, name, etag, last_modified
            )""" % REPO_INDEX_TABLE)

        for url in options.get_repos():
            #Check if repo exists in index and has an etag/last-modified.
            table_id = sanitize_sql(url)
            c.execute('Select etag,last_modified From "%s" Where url=?'
                %REPO_INDEX_TABLE, (table_id,) )
            result = c.fetchone()
            if result is None:
                #This repo is not yet in the index (it's the first time it's
                #been checked), so make an empty entry for it.
                c.execute('Insert Into "%s" (url) Values (?)'
                    %REPO_INDEX_TABLE, (table_id,) )
                result = (None, None)
            etag, last_modified = result
            #Do a conditional get.
            req = urllib2.Request(url)
            req.add_header('If-None-Match', etag)
            req.add_header('If-Modified-Since', last_modified)
            class NotModifiedHandler(urllib2.BaseHandler):
                def http_error_304(self, req, fp, code, message, headers):
                    return 304
            opener = urllib2.build_opener(NotModifiedHandler())
            url_handle = opener.open(req)
            #If no error, add to list to be read by update_remote
            if url_handle != 304:
                repos.append(url_handle)
                #Update latest etag/last-modified.
                #Should this be left until update_remote completes?
                headers = url_handle.info()
                etag_new = headers.getheader('ETag')
                last_modified_new = headers.getheader('Last-Modified')
                c.execute('Update "%s" Set etag=?,last_modified=? Where url=?'
                    %REPO_INDEX_TABLE, (etag_new, last_modified_new, table_id) )

    return repos


def update_remote():
    """Adds a table for each repository to the database, adding an entry for each application listed in the repository."""
    #Open database connection.
    db = sqlite3.connect(options.get_database())
    db.row_factory = sqlite3.Row
    c = db.cursor()
    repos = open_repos()
    try:
        for i in repos:

            #Parse JSON.
            #TODO: Is there any way to gracefully handle a malformed feed?
            try: repo = json.load(i)
            except ValueError:
                raise RepoError('Malformed JSON file from %s'%i.geturl())

            try: 
                #Check it's the right version.
                v = repo["repository"]["version"]
                if v != REPO_VERSION:
                    raise RepoError('Incorrect repository version (required %f, got %f)'
                        % (REPO_VERSION, v))

                #Create table from scratch for this repo.
                #Drops it first so no old entries get left behind.
                #TODO: Yes, there are probably more efficient ways than
                #dropping the whole thing, whatever, I'll get to it.
                table = sanitize_sql(repo["repository"]["name"])
                if table == LOCAL_TABLE or table == REPO_INDEX_TABLE:
                    raise RepoError('Cannot handle a repo named "%s"; name is reserved for internal use.'%LOCAL_TABLE)
                c.execute('Drop Table If Exists "%s"' % table)
                create_table(c, table)

                #Insert Or Replace for each app in repo.
                #TODO: Break into subfunctions?
                for app in repo["applications"]:

                    #Get info in preferred language (fail if none available).
                    title=None; description=None
                    for lang in options.get_locale():
                        try:
                            title = app['localizations'][lang]['title']
                            description = app['localizations'][lang]['description']
                            break
                        except KeyError: pass
                    if title is None or description is None:
                        raise RepoError('An application does not have any usable language')

                    #These fields will not be present for every app.
                    opt_field = {'author':None, 'vendor':None, 'icon':None}
                    for i in opt_field.iterkeys():
                        try: opt_field[i] = app[i]
                        except KeyError: pass

                    c.execute("""Insert Or Replace Into "%s" Values
                        (?,?,?,?,?,?,?,?,?,?,?,?)""" % table,
                        ( app['id'],
                        app['version']['major'],
                        app['version']['minor'],
                        app['version']['release'],
                        app['version']['build'],
                        app['uri'],
                        title,
                        description,
                        opt_field['author'],
                        opt_field['vendor'],
                        opt_field['icon'], None) )
                    #TODO: Holy crap!  Forgot categories!
                    #TODO: make sure no required fields are missing. covered by try and Not Null?
                    #TODO: Don't erase icon_cache if icon hasn't changed.

            except KeyError:
                raise RepoError('A required field is missing from this repository')
                #TODO: Make it indicate which field that is?

    finally:
        for i in repos: i.close()
        db.commit()
        c.close()


def update_local():
    #Useful libpnd functions:
    #pnd_apps.h: get_appdata_path for when we want a complete removal
    #   (this will be needed elsewhere later)
    #pnd_conf.h: pnd_conf_query_searchpath if we happen to need libpnd configs
    #pnd_desktop.h: pnd_emit_icon_to_buffer to get an icon for caching.
    #   pnd_map_dotdesktop_categories ?
    #pnd_discovery.h: pnd_disco_search gives list of valid apps.  PERFECT.
    #pnd_locate.h: pnd_locate_filename for finding path of specific PND.
    #pnd_notify.h: everything in here for watching for file changes.
    #   or perhaps use dbus as per pnd_dbusnotify.h
    #pnd_pndfiles.h: pnd_pnd_mount for getting screenshots from within.
    #all of pnd_pxml.h for information from a PXML.
    #pnd_tinyxml.h: pnd_pxml_parse for exactly what it says.
    pass
