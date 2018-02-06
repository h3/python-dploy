import os
import yaml
import dploy

from fabric.colors import red
from fabric.contrib import files
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
    package_path = os.path.realpath(os.path.join(
        os.path.dirname(dploy.__file__), '../templates'))
    if os.path.exists(os.path.join(package_path, name)):
        return package_path
    return None


def get_template_path(name):
    return os.path.join(get_template_dir(name), name)


def select_template(templates):
    """
    Returns the first file that exists from a list of file paths
    """
    for tpl in templates:
        if os.path.exists(tpl):
            return tpl
    return None


def upload_template(name, path, **kwargs):
    """
    This function takes a template name and a destination path.

    It is a proxy function for files.upload_template with sensible defaults and
    context preseeding.

    It will also lookup for the template at two specific places:
        1. <project_dir>/deploy/
        2. <dploy_package_dir>/templates/
    """
    _context = env.context
    _context.update({
        'ctx': dploy.context.ctx,
        'project_dir': dploy.context.get_project_dir(),
    })
    if kwargs.get('context'):
        _context.update(kwargs.get('context'))
        del kwargs['context']
    defaults = {
        'context': _context,
        'use_jinja': True,
        'use_sudo': True,
        'backup': False,
        'mode': None,
    }
    defaults.update(kwargs)
    if not kwargs.get('template_dir'):
        defaults['template_dir'] = get_template_dir(name)

    if defaults.get('template_dir'):
        return files.upload_template(name, path, **defaults)
    else:
        # log ?
        return None
