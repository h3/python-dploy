import os
import sys

from fabric.colors import cyan, red, yellow
from fabric.api import task, env, cd, sudo, local, get, hide, run, execute  # noqa

from dploy.context import ctx, get_project_dir
from dploy.commands import manage as django_manage
from dploy.utils import (
    FabricException, version_supports_migrations, select_template,
    upload_template,
)


@task
def manage(cmd):
    """
    Runs django manage.py with a given command
    """
    print(cyan("Django manage {} on {}".format(cmd, env.stage)))
    django_manage(cmd)


@task
def setup_settings():
    """
    Takes the dploy/<STAGE>_settings.py template and upload it to remote
    django project location (as local_settings.py)
    """
    print(cyan("Setuping django settings project on {}".format(env.stage)))
    project_dir = get_project_dir()
    project_name = ctx('django.project_name')
    stage_settings = '{stage}_settings.py'.format(stage=env.stage)
    templates = [
        os.path.join('./dploy/', stage_settings),
        os.path.join('./', project_name, 'local_settings.py-dist'),
        os.path.join('./', project_name, 'local_settings.py-default'),
        os.path.join('./', project_name, 'local_settings.py-example'),
        os.path.join('./', project_name, 'local_settings.py.dist'),
        os.path.join('./', project_name, 'local_settings.py.default'),
        os.path.join('./', project_name, 'local_settings.py.example'),
    ]

    template = select_template(templates)
    if not template:
        print(red('ERROR: the project does not have a settings template'))
        print("The project must provide at least one of these file:")
        print("\n - {}\n".format("\n - ".join(templates)))
        sys.exit(1)

    filename = os.path.basename(template)
    templates_dir = os.path.dirname(template)
    _settings_dest = os.path.join(project_dir, project_name,
                                  'local_settings.py')
    upload_template(filename, _settings_dest, template_dir=templates_dir)


@task
def migrate():
    """
    Perform django migration (only if the django version is >= 1.7)
    """
    with hide('running', 'stdout'):
        version = django_manage('--version')
    if version_supports_migrations(version):
        print(cyan("Django migrate on {}".format(env.stage)))
        try:
            django_manage('migrate --noinput')
        except FabricException as e:
            print(yellow(
                'WARNING: faked migrations because of exception {}'.format(e)))
            django_manage('migrate --noinput --fake')
    else:
        print(yellow(
            "Django {} does not support migration, skipping.".format(version)))


@task
def collectstatic():
    """
    Collect static medias
    """
    print(cyan("Django collectstatic on {}".format(env.stage)))
    django_manage(ctx('django.commands.collectstatic'))


@task
def dumpdata(app, dest=None):
    """
    Runs dumpdata on a given app and fetch the file locally
    """
    if dest is None:
        django_manage('dumpdata --indent=2 {}'.format(app))
    else:
        tmp_file = '/tmp/{}.tmp'.format(app)
        django_manage('dumpdata --indent=2 {} > {}'.format(app, tmp_file))
        with open(dest, 'w+') as fd:
            get(tmp_file, fd, use_sudo=True)
        sudo('rm -f {}'.format(tmp_file))


@task
def setup():
    """
    Performs django_setup_settings, django_migrate and django_collectstatic
    """
    execute(setup_settings)
    execute(migrate)
    execute(collectstatic)
