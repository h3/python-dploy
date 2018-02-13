from fabric.colors import *  # noqa
from fabric.api import *  # noqa

from dploy.context import get_context
from dploy.commands import pip, manage  # noqa
from dploy.tasks import django  # noqa
from dploy.tasks import virtualenv # noqa
from dploy.tasks import letsencrypt # noqa
from dploy.tasks import cron  # noqa
from dploy.tasks import supervisor  # noqa
from dploy.tasks import uwsgi  # noqa
from dploy.tasks import nginx  # noqa
from dploy.tasks import system # noqa
from dploy.tasks import git  # noqa
from dploy.tasks import context  # noqa


@task
def on(stage):
    """
    Sets the stage to perform action on
    """
    localhosts = ['localhost', '127.0.0.1']
    env.stage = stage
    env.context = get_context()
    hosts = env.context['hosts']
    if stage == 'dev' and len(hosts) == 1 and hosts[0] in localhosts:
        env.hosts = []
    else:
        env.hosts = env.context['hosts']


@task
def deploy(upgrade=False):
    """
    Perform all deployment tasks sequentially
    """
    print("Deploying project on {} !".format(env.stage))
    execute('system.create_dirs')
    execute('git.checkout')
    execute('virtualenv.setup')
    execute('django.setup')
    execute('cron.setup')
    execute('uwsgi.setup')
    execute('supervisor.setup')
    execute('nginx.setup')
