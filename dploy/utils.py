import os
import yaml
import dploy

from fabric.colors import red
from fabric.api import env


class FabricException(Exception):
    pass


def load_yaml(path):
    try:
        with open(path, 'r') as fd:
            try:
                rs = yaml.load(fd)
            except yaml.YAMLError as e:
                rs = None
                print(red(e))
    except IOError:
        rs = None
    return rs


def parent_dir(p):
    return os.path.abspath(os.path.join(p, os.pardir))


def git_dirname(uri):
    return uri.split('/')[-1].replace('.git', '')


def version_supports_migrations(v):
    major, minor, revision = map(int, v.split('.'))
    if major > 1:
        return True
    elif major == 1 and minor >= 7:
        return True
    else:
        return False


def get_template_dir(name):
    """
    Returns "deploy/" if the template exists at project level, otherwise
    returns "package_dir/templates/" of ot exists.
    Returns None if the template does not exists.
    """
    local_path = os.path.join(env.base_path, 'dploy/', name)
    if os.path.exists(local_path):
        return 'dploy/'
    package_path = os.path.join(dploy.__file__, 'templates/')
    if os.path.exists(os.path.join(package_path, name)):
        return package_path
    return None


def select_template(templates):
    """
    Returns the first file that exists from a list of file paths
    """
    for tpl in templates:
        if os.path.exists(tpl):
            return tpl
    return None
