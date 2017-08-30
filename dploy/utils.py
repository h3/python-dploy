import os

from fabric.api import cd, sudo

from dploy.context import ctx


def parent_dir(p):
    return os.path.abspath(os.path.join(p, os.pardir))


def venv(i):
    with cd(ctx('git.dirs.root')):
        sudo('{}/bin/{}'.format(
            ctx('virtualenv.dirs.root'), i))


def pip(i):
    if ctx('python.version') == 3:
        venv('pip3 {}'.format(i))
    else:
        venv('pip {}'.format(i))


def python(i):
    if ctx('python.version') == 3:
        venv('python3 {}'.format(i))
    else:
        venv('python2 {}'.format(i))


def manage(i):
    python('manage.py {}'.format(i))
