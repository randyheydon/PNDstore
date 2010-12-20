"""Finds and parses common option values used by other modules.

Concurrency note: as long as working_dir and the config file already exist, all functions here should have no side effects, and should therefore be thread safe.  To ensure that both exist, call get_cfg() at least once before starting other threads."""

from ConfigParser import SafeConfigParser
import shutil, os.path

#If a different working directory is to be used, the script importing this
#module should modify this value before calling any functions here (or using
#other modules that rely on them).
working_dir = os.path.expanduser('~/.pndstore')


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
    """Returns list of repository urls in order sorted by key.
    Keys in the repository section otherwise have no effect."""
    cfg = SafeConfigParser()
    cfg.read(get_cfg())
    #TODO: Perhaps validate URLs first?
    return [cfg.get('repositories',i) for i in sorted(cfg.options('repositories'))]
