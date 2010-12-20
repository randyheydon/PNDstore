import options, urllib2, sqlite3, json, ctypes

#This module currently only supports version 1.0 of the PND repository
#specification as seen at http://pandorawiki.org/PND_repository_specification
REPO_VERSION = 1.0

class RepoError(Exception): pass


def open_repos():
    return [urllib2.urlopen(i) for i in options.get_repos()]


def update_remote():
    #Open database connection.
    db = sqlite3.connect(options.get_database())
    db.row_factory = sqlite3.Row
    repos = open_repos()
    try:
        for i in repos:
            #Parse JSON.
            #TODO: Is there any way to gracefully handle a malformed feed?
            #Apparently a trailing comma will cause it to break.
            try: repo = json.load(i)
            except ValueError:
                raise RepoError('Malformed JSON file from %s'%i.geturl())
            try: 
                #Check it's the right version.
                v = repo["repository"]["version"]
                if v != REPO_VERSION:
                    raise RepoError('Incorrect repository version (required %f, got %f)'
                        % (REPO_VERSION, v))
                #TODO: create/write table for this repo
                #TODO: make sure no required fields are missing
            finally: pass
    finally:
        for i in repos: i.close()


def update_local():
    pass
