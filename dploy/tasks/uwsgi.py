import os

from fabric.api import task, sudo, env
from fabric.colors import cyan
from dploy.context import ctx, get_project_dir
from dploy.utils import upload_template


@task
def setup():
    """
    Configure uWSGI
    """
    print(cyan('Configuring uwsgi {}'.format(env.stage)))
    project_dir = get_project_dir()
    wsgi_file = os.path.join(project_dir, ctx('django.project_name'), 'wsgi.py')
    uwsgi_ini = os.path.join(project_dir, 'uwsgi.ini')
    context = {'ctx': ctx, 'project_dir': project_dir, 'wsgi_file': wsgi_file}
    log_file = '{}/uwsgi.log'.format(ctx('logs.dirs.root'))
    sudo('touch {logfile}'.format(logfile=log_file))
    sudo('chown {user}:{group} {logfile}'.format(
        logfile=log_file, user=ctx('system.user'), group=ctx('system.group')))
    upload_template('uwsgi.template', uwsgi_ini, context=context)
