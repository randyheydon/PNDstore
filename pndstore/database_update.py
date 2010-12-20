import options, urllib2, ctypes, sqlite3


def open_repos():
    return [urllib2.urlopen(i) for i in options.get_repos()]


def update_remote():
    #open database connection.
    for i in open_repos():
        #parse JSON
        #create/write table for this repo
        pass


def update_local():
    pass
