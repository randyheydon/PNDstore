"""This module populates the app database with installed and available applications.  Consumers of this module will likely only need the functions update_remote and update_local (and maybe update_local_file, if you're feeling fancy).

Concurrency note: Most functions here make changes to the database.  However, they all create their own connections and cursors; since sqlite can handle concurrent database writes automatically, these functions should be thread safe."""

import options, libpnd, urllib2, sqlite3, json, md5

#This module currently supports these versions of the PND repository
#specification as seen at http://pandorawiki.org/PND_repository_specification
REPO_VERSION = (2.0,)

LOCAL_TABLE = 'local'
REPO_INDEX_TABLE = 'repo_index'
SEPCHAR = ';' # Character that defines list separations in the database.

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
        author_name Text,
        author_website Text,
        author_email Text,
        title Text Not Null,
        description Text Not Null,
        icon Text,
        uri Text Not Null,
        md5 Text Not Null,
        vendor Text,
        rating Int,
        applications Text,
        previewpics Text,
        licenses Text,
        source Text,
        categories Text,
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
            # TODO: A way to force an update.
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

                #Insert Or Replace for each package in repo.
                #TODO: Break into subfunctions?
                for pkg in repo["packages"]:

                    #Get info in preferred language (fail if none available).
                    title=None; description=None
                    for lang in options.get_locale():
                        try:
                            title = pkg['localizations'][lang]['title']
                            description = pkg['localizations'][lang]['description']
                            break
                        except KeyError: pass
                    if title is None or description is None:
                        raise RepoError('An application does not have any usable language')

                    # These fields will not be present for every app.
                    opt_field = {'vendor':None, 'icon':None, 'rating':None}
                    for i in opt_field.iterkeys():
                        try: opt_field[i] = pkg[i]
                        except KeyError: pass

                    author = {'name':None, 'website':None, 'email':None}
                    for i in author.iterkeys():
                        try: author[i] = pkg['author'][i]
                        except KeyError: pass

                    # These fields should only be used if not present in the
                    # applications array.  Set them here, then override with
                    # contents of applications array if present.
                    opt_list = {'previewpics':None, 'licenses':None,
                        'source':None, 'categories':None}
                    for i in opt_list.iterkeys():
                        try: opt_list[i] = SEPCHAR.join(pkg[i])
                        except KeyError: pass

                    applications = None
                    try:
                        applist = pkg['applications']
                        applications = SEPCHAR.join(
                            [app['id'] for app in applist] )

                        # Join all lists of all apps into one megalist.
                        for i in opt_list.iterkeys():
                            opt_list[i] = SEPCHAR.join([ SEPCHAR.join(app[i])
                                for app in applist ] )

                    except KeyError: pass

                    c.execute("""Insert Or Replace Into "%s" Values
                        (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""" % table,
                        ( pkg['id'],
                        '.'.join( (
                            pkg['version']['major'],
                            pkg['version']['minor'],
                            pkg['version']['release'],
                            pkg['version']['build'], ) ),
                        author['name'],
                        author['website'],
                        author['email'],
                        title,
                        description,
                        opt_field['icon'],
                        pkg['uri'],
                        pkg['md5'],
                        opt_field['vendor'],
                        opt_field['rating'],
                        applications,
                        opt_list['previewpics'],
                        opt_list['licenses'],
                        opt_list['source'],
                        opt_list['categories'],
                        None) )
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
    # NOTE, TODO: libpnd doesn't yet have functions to look at the package
    # element of a PND.  For now, check the first application element, and
    # assume that it's representative of the package as a whole.
    pkg = pxml[0]
    libpnd.pxml_get_unique_id(pkg)

    # Find out how many apps are in the PXML, so we can iterate over them.
    n_apps = 0
    for i in pxml:
        if i is None: break
        n_apps += 1

    applications = SEPCHAR.join([ libpnd.pxml_get_unique_id( pxml[i] )
        for i in xrange(n_apps) ])

    previewpics = []
    for i in xrange(n_apps):
        p = libpnd.pxml_get_previewpic1( pxml[i] )
        if p is not None: previewpics.append(p)
        p = libpnd.pxml_get_previewpic2( pxml[i] )
        if p is not None: previewpics.append(p)
    if previewpics:
        previewpics = SEPCHAR.join(previewpics)
    else: previewpics = None

    # TODO: Get licenses and source urls once libpnd has that functionality.

    categories = []
    for i in xrange(n_apps):
        c = libpnd.pxml_get_main_category( pxml[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_subcategory1( pxml[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_subcategory2( pxml[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_altcategory( pxml[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_altsubcategory1( pxml[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_altsubcategory2( pxml[i] )
        if c is not None: categories.append(c)
    if categories:
        categories = SEPCHAR.join(categories)
    else: categories = None

    # TODO: Opening a new connection for each file getting added is probably
    # inefficient.  Might be better if a connection or cursor object could be
    # passed in, but a new one could be generated if needed?
    with sqlite3.connect(options.get_database()) as db:
        c = db.cursor()
        c.execute("""Insert Or Replace Into "%s" Values
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""" % LOCAL_TABLE,
            ( libpnd.pxml_get_unique_id(pkg),
            '.'.join( (
                libpnd.pxml_get_version_major(pkg),
                libpnd.pxml_get_version_minor(pkg),
                libpnd.pxml_get_version_release(pkg),
                libpnd.pxml_get_version_build(pkg), ) ),
            libpnd.pxml_get_author_name(pkg),
            libpnd.pxml_get_author_website(pkg),
            None, # NOTE: libpnd has no pxml_get_author_email?
            # TODO: I'm not sure how libpnd handles locales exactly...
            libpnd.pxml_get_app_name(pkg, options.get_locale()[0]),
            libpnd.pxml_get_description(pkg, options.get_locale()[0]),
            libpnd.pxml_get_icon(pkg),
            path,
            m.hexdigest(),
            None, # I see no use for "vendor" on installed apps.
            None, # Nor "rating".
            applications,
            previewpics,
            None, # TODO: Licenses once libpnd can pull them.
            None, # TODO: Sources once libpnd can pull them.
            categories,
            None) ) # TODO: Get icon buffer with pnd_desktop's pnd_emit_icon_to_buffer
    libpnd.pxml_delete(pkg)


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
