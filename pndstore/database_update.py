"""This module populates the app database with installed and available applications.  Consumers of this module will likely only need the functions update_remote and update_local (and maybe update_local_file, if you're feeling fancy).

Concurrency note: Most functions here make changes to the database.  However, they all create their own connections and cursors; since sqlite can handle concurrent database writes automatically, these functions should be thread safe."""

import options, libpnd, urllib2, sqlite3, json, md5

#This module currently supports these versions of the PND repository
#specification as seen at http://pandorawiki.org/PND_repository_specification
REPO_VERSION = (1.0, 1.1, 1.2, 1.3)

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
        id Text Primary Key,
        version Text Not Null,
        uri Text Not Null,
        title Text Not Null,
        description Text Not Null,
        categories Text,
        author Text,
        vendor Text,
        md5 Text,
        icon Text,
        icon_cache Buffer
        )""" % name)


def open_repos():
    repos = []
    with sqlite3.connect(options.get_database()) as db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        #Create index for all repositories to track important info.
        c.execute("""Create Table If Not Exists "%s" (
            url Text Primary Key, name Text, etag Text, last_modified Text
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
            req = urllib2.Request(url, headers={
                'If-None-Match':etag, 'If-Modified-Since':last_modified})
            class NotModifiedHandler(urllib2.BaseHandler):
                def http_error_304(self, req, fp, code, message, headers):
                    return 304
            opener = urllib2.build_opener(NotModifiedHandler())
            url_handle = opener.open(req)

            #If no error, add to list to be read by update_remote
            if url_handle != 304:
                repos.append(url_handle)

        #TODO: If a repo gets removed from the cfg, perhaps this function
        #should remove its index entry and drop its table.

    return repos


def update_remote():
    """Adds a table for each repository to the database, adding an entry for each application listed in the repository."""
    #Open database connection.
    db = sqlite3.connect(options.get_database())
    db.row_factory = sqlite3.Row
    c = db.cursor()
    repos = open_repos()
    try:
        for r in repos:

            #Parse JSON.
            #TODO: Is there any way to gracefully handle a malformed feed?
            try: repo = json.load(r)
            except ValueError:
                raise RepoError('Malformed JSON file from %s'%r.url)

            try: 
                #Check it's the right version.
                v = repo["repository"]["version"]
                if v not in REPO_VERSION:
                    raise RepoError('Incorrect repository version (required one of %s, got %f)'
                        % (REPO_VERSION, v))

                #Create table from scratch for this repo.
                #Drops it first so no old entries get left behind.
                #TODO: Yes, there are probably more efficient ways than
                #dropping the whole thing, whatever, I'll get to it.
                #FIXME: Will r.url give the same url listed in the cfg?
                table = sanitize_sql(r.url)
                if table == LOCAL_TABLE or table == REPO_INDEX_TABLE:
                    raise RepoError('Cannot handle a repo named "%s"; name is reserved for internal use.'%table)
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

                    # These fields will not be present for every app.
                    # Note that 'md5' is mandatory in repo version 1.1, and
                    # 'author' in 1.3.  However, I get full compatibility with
                    # all versions by just leaving them optional.  Just don't
                    # rely on this code to fully validate your repository!
                    opt_field = {'author':None, 'vendor':None, 'md5':None, 'icon':None}
                    for i in opt_field.iterkeys():
                        try: opt_field[i] = app[i]
                        except KeyError: pass

                    #As of repo version 1.2, version numbers are strings, not
                    #just ints.  But the columns' text affinity autoconverts
                    #them as necessary.
                    c.execute("""Insert Or Replace Into "%s" Values
                        (?,?,?,?,?,?,?,?,?,?,?)""" % table,
                        ( app['id'],
                        '.'.join( (
                            app['version']['major'],
                            app['version']['minor'],
                            app['version']['release'],
                            app['version']['build'], ) ),
                        app['uri'],
                        title,
                        description,
                        ':'.join(app['categories']),
                        opt_field['author'],
                        opt_field['vendor'],
                        opt_field['md5'],
                        opt_field['icon'], None) )
                    #TODO: make sure no required fields are missing. covered by try and Not Null?
                    #TODO: Don't erase icon_cache if icon hasn't changed.

                #Now repo is all updated, let the index know its etag/last-modified.
                headers = r.info()
                c.execute('Update "%s" Set name=?, etag=?,last_modified=? Where url=?'
                    %REPO_INDEX_TABLE, (
                        repo['repository']['name'],
                        headers.getheader('ETag'),
                        headers.getheader('Last-Modified'),
                        table) )

            except KeyError:
                raise RepoError('A required field is missing from this repository')
                #TODO: Make it indicate which field that is?

    finally:
        for i in repos: i.close()
        db.commit()
        c.close()



def update_local_file(path):
    """Adds an entry to the local database based on the PND found at "path"."""
    pxml = libpnd.pxml_get_by_path(path)
    if not pxml:
        raise ValueError("%s doesn't seem to be a real PND file." % path)
    with open(path, 'rb') as p: m = md5.new(p.read())

    # Extract all the useful information from the PND and add it to the table.
    # NOTE: For now, only considers the first app in the PND, since that's what
    # milkshake's repo does.  Will likely need to expand it in the future.
    app = pxml[0]

    categories = ( libpnd.pxml_get_main_category(app), libpnd.pxml_get_subcategory1(app),
        libpnd.pxml_get_subcategory2(app), libpnd.pxml_get_altcategory(app),
        libpnd.pxml_get_altsubcategory1(app), libpnd.pxml_get_altsubcategory2(app) )

    # TODO: Opening a new connection for each file getting added is probably
    # inefficient.  Might be better if a connection or cursor object could be
    # passed in, but a new one could be generated if needed?
    with sqlite3.connect(options.get_database()) as db:
        c = db.cursor()
        c.execute("""Insert Or Replace Into "%s" Values
            (?,?,?,?,?,?,?,?,?,?,?)""" % LOCAL_TABLE,
            ( libpnd.pxml_get_unique_id(app),
            '.'.join( (
                libpnd.pxml_get_version_major(app),
                libpnd.pxml_get_version_minor(app),
                libpnd.pxml_get_version_release(app),
                libpnd.pxml_get_version_build(app), ) ),
            path,
            # TODO: I'm not sure how libpnd handles locales exactly...
            libpnd.pxml_get_app_name(app, options.get_locale()[0]),
            libpnd.pxml_get_app_description(app, options.get_locale()[0]),
            ':'.join([i for i in categories if i is not None]),
            libpnd.pxml_get_author_name(app),
            None, # I see no use for "vendor" on installed apps.
            m.hexdigest(),
            libpnd.pxml_get_icon(app),
            None) ) # TODO: Get icon buffer with pnd_desktop's pnd_emit_icon_to_buffer
    libpnd.pxml_delete(app)


def update_local():
    """Adds a table to the database, adding an entry for each application found in the searchpath."""
    # Open database connection.
    with sqlite3.connect(options.get_database()) as db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        # Create table from scratch to hold list of all installed PNDs.
        # Drops it first so no old entries get left behind.
        # TODO: Yes, there are probably more efficient ways than dropping
        # the whole thing, whatever, I'll get to it.
        c.execute('Drop Table If Exists "%s"' % LOCAL_TABLE)
        create_table(c, LOCAL_TABLE)

    # Find PND files on searchpath.
    searchpath = ':'.join(options.get_searchpath())
    search = libpnd.disco_search(searchpath, None)
    if not search:
        raise ValueError("Your install of libpnd isn't behaving right!  pnd_disco_search has returned null.")

    # If at least one PND is found, add each to the database.
    n = libpnd.box_get_size(search)
    if n > 0:
        node = libpnd.box_get_head(search)
        update_local_file(libpnd.box_get_key(node))
        for i in xrange(n-1):
            node = libpnd.box_get_next(node)
            update_local_file(libpnd.box_get_key(node))
