import options, urllib2, sqlite3, json, ctypes

#This module currently only supports version 1.0 of the PND repository
#specification as seen at http://pandorawiki.org/PND_repository_specification
REPO_VERSION = 1.0

LOCAL_TABLE = 'local'

class RepoError(Exception): pass


def open_repos():
    return [urllib2.urlopen(i) for i in options.get_repos()]


def update_remote():
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

                #Create table for this repo.
                #The execute method's parametrization does not work for table
                #names.  Therefore sanitize it and string format.  Any other
                #dangerous characters that should be removed?
                table = str(repo["repository"]["name"]).translate(None, """.,;:'"(){}""")
                if table == LOCAL_TABLE:
                    raise RepoError('Cannot handle a repo named "%s"; name is reserved for internal use.'%LOCAL_TABLE)
                c.execute("""Create Table "%s" (
                    id Primary Key,
                    version_major Int Not Null,
                    version_minor Int Not Null,
                    version_release Int Not Null,
                    version_build Int Not Null,
                    uri Not Null,
                    title Not Null,
                    description Not Null,
                    author, vendor, icon, icon_cache Buffer)""" % table)

                #Insert Or Replace for each app in repo.
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
                    #TODO: make sure no required fields are missing.
                    #covered by try and Not Null?

            except KeyError:
                raise RepoError('A required field is missing from this repository')
                #TODO: Make it indicate which field that is?

    finally:
        for i in repos: i.close()
        db.commit()
        c.close()


def update_local():
    pass
