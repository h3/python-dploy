import os

from fabric.api import cd, sudo

from dploy.context import ctx, get_project_dir


def venv(i):
    venv_path = os.path.join(
        ctx('virtualenv.dirs.root'), ctx('virtualenv.name'))
    with cd(get_project_dir()):
        return sudo('{}/bin/{}'.format(venv_path, i))


def pip(i):
    venv('pip {}'.format(i))


def python(i):
    if ctx('python.version') == 3:
        return venv('python3 {}'.format(i))
    else:
        return venv('python2 {}'.format(i))


def manage(i):
    return python('manage.py {}'.format(i))
