"""Finds and parses common option values used by other modules.

Concurrency note: as long as working_dir and the config file already exist, all functions here should have no side effects, and should therefore be thread safe.  To ensure that both exist, call get_cfg() at least once before starting other threads."""

from json import load as jload
import shutil, os, locale
import libpnd

#If a different working directory is to be used, the script importing this
#module should modify this value before calling any functions here (or using
#other modules that rely on them).
working_dir = os.path.expanduser('~/.pndstore')


DEFAULT_KEY = 'default'


def get_working_dir():
    """Gives full path to working directory, creating it if needed."""
    #Create working directory if needed.
    if not os.path.isdir(working_dir):
        os.makedirs(working_dir)
    return os.path.abspath(working_dir)

def get_cfg():
    """Gives path to main config file and copies the default one into place if needed."""
    cfg_path = os.path.join(get_working_dir(), 'pndstore.cfg')
    if not os.path.isfile(cfg_path):
        cfg_template = os.path.join(os.path.dirname(__file__), 'cfg', 'default.cfg')
        shutil.copy(cfg_template, cfg_path)
    return cfg_path


def get_database():
    """Gives full path to main sqlite database file."""
    #Unlike in get_cfg, the database file does not need to be created here, as
    #sqlite will create it automatically if needed.
    return os.path.abspath(os.path.join(working_dir, 'app_database.sqlite'))


def get_repos():
    """Returns list of repository urls in the given order."""
    #TODO: Perhaps validate URLs first?
    #TODO: Perhaps validate that a list is being returned?
    #   or not: a dictionary with urls as keys would still work in database_update.
    with open(get_cfg()) as cfg:
        return jload(cfg)['repositories']



def get_locale_default():
    return locale.getdefaultlocale()[0]


def get_locale():
    """Returns a list of locales in the given order.  If none are specified, first preference is the system locale.  The PND spec requires that en_US always be available for titles and descriptions, so that will always be the last entry in the list (it shouldn't matter if it appears multiple times in the list)."""
    #TODO: Perhaps validate language codes?
    #TODO: What should be done for language codes without country codes?
    with open(get_cfg()) as cfg:
        locales = jload(cfg)['locales']

    if DEFAULT_KEY in locales:
        i = locales.index(DEFAULT_KEY)
        locales[i] = get_locale_default()

    #The en_US locale should be available in all PNDs, so it should be a last resort.
    locales.append('en_US')
    return locales



def get_searchpath_default():
    conf_path = libpnd.conf_query_searchpath()
    if not conf_path:
        raise ValueError("Your install of libpnd isn't behaving right! pnd_conf_query_searchpath has returned null.")

    conf = libpnd.conf_fetch_by_name('apps', conf_path)
    if not conf:
        raise ValueError("Your install of libpnd isn't behaving right!  pnd_conf_fetch_by_name has returned null.")

    return libpnd.conf_get_as_char(conf, 'autodiscovery.searchpath').split(':')


def get_searchpath():
    #TODO: Perhaps validate paths?
    with open(get_cfg()) as cfg:
        searchpath = jload(cfg)['searchpath']

    if DEFAULT_KEY in searchpath:
        i = searchpath.index(DEFAULT_KEY)
        searchpath[i:i+1] = get_searchpath_default()

    return searchpath
