import os

from fabric.api import cd, sudo

from dploy.context import ctx


def venv(i):
    venv_path = os.path.join(
        ctx('virtualenv.dirs.root'), ctx('virtualenv.name'))
    with cd(ctx('git.dirs.root')):
        sudo('{}/bin/{}'.format(venv_path, i))


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
