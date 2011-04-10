"""
This module populates the app database with installed and available
applications.  Consumers of this module will likely only need the functions
update_remote and update_local (and maybe update_local_file, if you're feeling
fancy).

Concurrency note: Most functions here make changes to the database.  However,
they all create their own connections and cursors; since sqlite can handle
concurrent database writes automatically, these functions should be thread safe.
"""

import options, libpnd, urllib2, sqlite3, json, ctypes, warnings
import xml.etree.cElementTree as etree
from hashlib import md5

#This module currently supports these versions of the PND repository
#specification as seen at http://pandorawiki.org/PND_repository_specification
REPO_VERSION = (2.0,)

LOCAL_TABLE = 'local'
REPO_INDEX_TABLE = 'repo_index'
SEPCHAR = ';' # Character that defines list separations in the database.

PXML_NAMESPACE = 'http://openpandora.org/namespaces/PXML'
xml_child = lambda s: '{%s}%s' % (PXML_NAMESPACE, s)

class RepoError(Exception): pass
class PNDError(Exception): pass


def sanitize_sql(name):
    """The execute method's parametrization does not work for table names.
    Therefore string formatting must be used, which bypasses the sqlite3
    package's sanitization.  This function takes a stab at sanitizing.  Since
    table names are put in double quotes (thereby representing an SQL
    identifier), any characters should be fine except double quotes.  But since
    all table names are URLs read from a JSON file, they likely won't include
    quotes, so this function is mostly useless."""
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
        title Text,
        description Text,
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
                # This repo is not yet in the index (it's the first time it's
                # been checked), so make an empty entry and table for it.
                c.execute('Insert Into "%s" (url) Values (?)'
                    %REPO_INDEX_TABLE, (table_id,) )
                create_table(c, table_id)
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
            try:
                url_handle = opener.open(req)
                # If no error, add to list to be read by update_remote.
                if url_handle != 304:
                    repos.append(url_handle)
            except Exception as e:
                warnings.warn("Could not reach repo %s: %s" % (url, repr(e)))

        db.commit()

        #TODO: If a repo gets removed from the cfg, perhaps this function
        #should remove its index entry and drop its table.

    return repos


def update_remote_url(url, cursor):
    """Adds database table for the repository held by the url object."""
    #Parse JSON.
    #TODO: Is there any way to gracefully handle a malformed feed?
    repo = json.load(url)

    #Check it's the right version.
    v = repo["repository"]["version"]
    if v not in REPO_VERSION:
        raise RepoError(
            'Incorrect repository version (required one of %s, got %f)'
            % (REPO_VERSION, v))

    #Create table from scratch for this repo.
    #Drops it first so no old entries get left behind.
    #TODO: Yes, there are probably more efficient ways than
    #dropping the whole thing, whatever, I'll get to it.
    #FIXME: Will r.url give the same url listed in the cfg?
    table = sanitize_sql(url.url)
    if table in (LOCAL_TABLE, REPO_INDEX_TABLE):
        raise RepoError(
            'Cannot handle a repo named "%s"; name is reserved for internal use.'
            % table)
    cursor.execute('Drop Table If Exists "%s"' % table)
    create_table(cursor, table)

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
            raise RepoError('A package does not have any usable language.')

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

        cursor.execute("""Insert Or Replace Into "%s" Values
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
    headers = url.info()
    cursor.execute('Update "%s" Set name=?, etag=?,last_modified=? Where url=?'
        %REPO_INDEX_TABLE, (
            repo['repository']['name'],
            headers.getheader('ETag'),
            headers.getheader('Last-Modified'),
            table) )


def update_remote():
    """Adds a table for each repository to the database, adding an entry for each
    application listed in the repository."""
    #Open database connection.
    with sqlite3.connect(options.get_database()) as db:
        db.row_factory = sqlite3.Row
        c = db.cursor()
        repos = open_repos()
        for r in repos:
            try:
                update_remote_url(r, c)
            except Exception as e:
                warnings.warn("Could not process %s: %s" % (r.url, repr(e)))
            r.close() # Shouldn't need to, but might as well.



def update_local_file(path):
    """Adds an entry to the local database based on the PND found at "path"."""
    apps = libpnd.pxml_get_by_path(path)
    if not apps:
        raise ValueError("%s doesn't seem to be a real PND file." % path)

    m = md5()
    with open(path, 'rb') as p:
        for chunk in iter(lambda: p.read(128*m.block_size), ''):
            m.update(chunk)

    # Extract all the useful information from the PND and add it to the table.
    # NOTE: libpnd doesn't yet have functions to look at the package element of
    # a PND.  Instead, extract the PXML and parse that element manually.
    pxml_buffer = ctypes.create_string_buffer(libpnd.PXML_MAXLEN)
    f = libpnd.libc.fopen(path, 'r')
    if not libpnd.pnd_seek_pxml(f):
        raise PNDError('PND file has no starting PXML tag.')
    if not libpnd.pnd_accrue_pxml(f, pxml_buffer, libpnd.PXML_MAXLEN):
        raise PNDError('PND file has no ending PXML tag.')
    try:
        # Strip extra trailing characters from the icon.  Remove them!
        end_tag = pxml_buffer.value.rindex('>')
        pxml = etree.XML(pxml_buffer.value[:end_tag+1])
        # Search for package element.
        pkg = pxml.find(xml_child('package'))
    except: # etree.ParseError isn't in Python 2.6 :(
        warnings.warn("Invalid PXML in %s; will attempt processing" % path)
        pxml = pkg = None

    if pkg is not None:
        # Parse package element if it exists.
        pkgid = pkg.attrib['id']

        v = pkg.find(xml_child('version'))
        # TODO: Add support for 'type' attribute.
        # NOTE: Using attrib instead of get will be fragile on non standards-
        # compliant PNDs.
        version = '.'.join( (
            v.attrib['major'],
            v.attrib['minor'],
            v.attrib['release'],
            v.attrib['build'], ) )

        author = pkg.find(xml_child('author'))
        author_name = author.get('name')
        author_website = author.get('website')
        author_email = author.get('email')

        # Get title and description in the most preferred language available.
        # All PNDs *should* have an en_US title and description, but this could
        # result in an error if they don't.
        titles = {}; descs = {}
        for t in pkg.find(xml_child('titles')):
            titles[t.attrib['lang']] = t.text
        for d in pkg.find(xml_child('descriptions')):
            descs[d.attrib['lang']] = d.text
        for l in options.get_locale():
            try:
                title = titles[l]
                description = descs[l]
                break
            except KeyError: pass

        i = pkg.find(xml_child('icon'))
        if i is not None:
            icon = i.get('src')
        else: icon = None

    else:
        # package element not found.
        # Assume first app element is representative of the package as a whole.
        pkg = apps[0]
        pkgid = libpnd.pxml_get_unique_id(pkg)
        version = '.'.join( (
            libpnd.pxml_get_version_major(pkg),
            libpnd.pxml_get_version_minor(pkg),
            libpnd.pxml_get_version_release(pkg),
            libpnd.pxml_get_version_build(pkg), ) )
        author_name = libpnd.pxml_get_author_name(pkg)
        author_website = libpnd.pxml_get_author_website(pkg)
        author_email = None # NOTE: libpnd has no pxml_get_author_email?
        # TODO: I'm not sure how libpnd handles locales exactly...
        title = libpnd.pxml_get_app_name(pkg, options.get_locale()[0])
        description = libpnd.pxml_get_description(pkg, options.get_locale()[0])
        icon = libpnd.pxml_get_icon(pkg)

    # Find out how many apps are in the PXML, so we can iterate over them.
    n_apps = 0
    for i in apps:
        if i is None: break
        n_apps += 1

    # Create the full list of contained applications.
    applications = SEPCHAR.join([ libpnd.pxml_get_unique_id( apps[i] )
        for i in xrange(n_apps) ])

    # Get all previewpics.  libpnd only supports two per application.
    previewpics = []
    for i in xrange(n_apps):
        p = libpnd.pxml_get_previewpic1( apps[i] )
        if p is not None: previewpics.append(p)
        p = libpnd.pxml_get_previewpic2( apps[i] )
        if p is not None: previewpics.append(p)
    if previewpics:
        previewpics = SEPCHAR.join(previewpics)
    else: previewpics = None

    # TODO: Get licenses and source urls once libpnd has that functionality.

    # Combine all categories in all apps.  libpnd supports two categories, each
    # with two subcategories in each app.  No effort is made to uniquify the
    # completed list.
    categories = []
    for i in xrange(n_apps):
        c = libpnd.pxml_get_main_category( apps[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_subcategory1( apps[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_subcategory2( apps[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_altcategory( apps[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_altsubcategory1( apps[i] )
        if c is not None: categories.append(c)
        c = libpnd.pxml_get_altsubcategory2( apps[i] )
        if c is not None: categories.append(c)
    if categories:
        categories = SEPCHAR.join(categories)
    else: categories = None

    # TODO: Opening a new connection for each file getting added is probably
    # inefficient.  Might be better if a connection or cursor object could be
    # passed in, but a new one could be generated if needed?
    with sqlite3.connect(options.get_database()) as db:

        # Output from libpnd gives encoded bytestrings, not Unicode strings.
        db.text_factory = str

        c = db.cursor()
        c.execute("""Insert Or Replace Into "%s" Values
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""" % LOCAL_TABLE,
            ( pkgid,
            version,
            author_name,
            author_website,
            author_email,
            title,
            description,
            icon,
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
        db.commit()

    # Clean up the pxml handle.
    for i in xrange(n_apps):
        libpnd.pxml_delete(apps[i])



def update_local():
    """Adds a table to the database, adding an entry for each application found
    in the searchpath."""
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
        db.commit()

    # Find PND files on searchpath.
    searchpath = ':'.join(options.get_searchpath())
    search = libpnd.disco_search(searchpath, None)
    if not search:
        raise ValueError("Your install of libpnd isn't behaving right!  pnd_disco_search has returned null.")

    # If at least one PND is found, add each to the database.
    # Note that disco_search returns the path to each *application*.  PNDs with
    # multiple apps will therefore be returned multiple times.  Process any
    # such PNDs only once.
    n = libpnd.box_get_size(search)
    done = set()
    if n > 0:
        node = libpnd.box_get_head(search)
        path = libpnd.box_get_key(node)
        try: update_local_file(path)
        except Exception as e:
            warnings.warn("Could not process %s: %s" % (path, repr(e)))
        done.add(path)
        for i in xrange(n-1):
            node = libpnd.box_get_next(node)
            path = libpnd.box_get_key(node)
            if path not in done:
                try: update_local_file(path)
                except Exception as e:
                    warnings.warn("Could not process %s: %s" % (path, repr(e)))
                done.add(path)
