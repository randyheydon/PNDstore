import options, urllib2, ctypes


def open_repos():
    return [urllib2.urlopen(i) for i in options.get_repos()]


def update_remote():
    pass


def update_local():
    pass
