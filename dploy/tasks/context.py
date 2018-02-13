import tempfile

import pprint as _pprint

from fabric.contrib import files
from fabric.api import task, env
from fabric.utils import abort
from fabric.colors import cyan, green, red
from dploy.context import ctx


@task
def setup():
    print(cyan('Configuring context on {}'.format(env.stage)))
    if env.stage == 'dev':
        abort(red('This task is only for remote stages.'))
    context_path = '/root/.context/{project}/{stage}.yml'.format(**{
        'project': ctx('django.project_name'),
        'stage': env.stage,
    })
    if files.exists(context_path, use_sudo=True):
        # TODO: interactive edit
        # http://klenwell.com/is/FabricEditRemoteFile
        print('Context already exists')
    else:
        with tempfile.TemporaryFile() as tmp:
            tmp.write('CONTEXT_TEMPLATE')
            import IPython
            IPython.embed()


@task
def pprint():
    """
    Prints deployment context
    """
    print('-' * 80)
    print(green('Global context', bold=True))
    print('-' * 80)
    print('\x1b[33m')
    _pprint.pprint(env.context)
    print('\x1b[0m')
    print('-' * 80)
