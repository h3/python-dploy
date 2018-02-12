import os
import sys

from fabric.colors import cyan, red, yellow
from fabric.api import task, env, cd, sudo, local, get, hide, run, execute  # noqa

from dploy.context import ctx, get_project_dir
from dploy.commands import manage
from dploy.utils import (
    FabricException, version_supports_migrations, select_template,
    upload_template,
)


@task
def django(cmd):
    """
    Runs django manage.py with a given command
    """
    print(cyan("Django manage {} on {}".format(cmd, env.stage)))
    manage(cmd)


@task
def django_setup_settings():
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
def django_migrate():
    """
    Perform django migration (only if the django version is >= 1.7)
    """
    with hide('running', 'stdout'):
        version = manage('--version')
    if version_supports_migrations(version):
        print(cyan("Django migrate on {}".format(env.stage)))
        try:
            manage('migrate --noinput')
        except FabricException as e:
            print(yellow(
                'WARNING: faked migrations because of exception {}'.format(e)))
            manage('migrate --noinput --fake')
    else:
        print(yellow(
            "Django {} does not support migration, skipping.".format(version)))


@task
def django_collectstatic():
    """
    Collect static medias
    """
    print(cyan("Django collectstatic on {}".format(env.stage)))
    manage(ctx('django.commands.collectstatic'))


@task
def django_dumpdata(app, dest=None):
    """
    Runs dumpdata on a given app and fetch the file locally
    """
    if dest is None:
        manage('dumpdata --indent=2 {}'.format(app))
    else:
        tmp_file = '/tmp/{}.tmp'.format(app)
        manage('dumpdata --indent=2 {} > {}'.format(app, tmp_file))
        with open(dest, 'w+') as fd:
            get(tmp_file, fd, use_sudo=True)
        sudo('rm -f {}'.format(tmp_file))


@task
def django_setup():
    """
    Performs django_setup_settings, django_migrate and django_collectstatic
    """
    execute(django_setup_settings)
    execute(django_migrate)
    execute(django_collectstatic)
