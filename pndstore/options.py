"""Finds and parses common option values used by other modules."""
from ConfigParser import SafeConfigParser as cp
import shutil, os.path

#If a different working directory is to be used, the script importing this
#module should modify this value before using other modules that rely on it.
working_dir = os.path.expanduser('~/.pndstore')


def get_cfg():
    """Gives full path to main config file."""
    cfg_path = os.path.abspath(os.path.join(working_dir, 'pndstore.cfg'))
    if not os.path.exists(cfg_path):
        cfg_template = os.path.join(os.path.dirname(__file__), 'cfg', 'default.cfg')
        shutil.copy(cfg_template, cfg_path)
    return cfg_path


def get_database():
    """Gives full path to main sqlite database file."""
    return os.path.abspath(os.path.join(working_dir, 'app_database.sqlite'))


def get_repos():
    """Returns list of repository urls in order sorted by key.
    Keys in the repository section otherwise have no effect."""
    cfg = cp()
    cfg.read(get_cfg())
    return [cfg.get('repositories',i) for i in sorted(cfg.options('repositories'))]
