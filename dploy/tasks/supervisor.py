import os
import fabtools

from fabric.api import task, env
from fabric.colors import cyan
from dploy.context import ctx, get_project_dir
from dploy.utils import upload_template


@task
def setup():
    """
    Configure supervisor to monitor the uwsgi process
    """
    print(cyan('Configuring supervisor {}'.format(env.stage)))
    if not fabtools.deb.is_installed('supervisor'):
        fabtools.deb.install('supervisor')
    project_dir = get_project_dir()
    uwsgi_ini = os.path.join(project_dir, 'uwsgi.ini')
    name = ctx('supervisor.program_name')
    context = {'uwsgi_ini': uwsgi_ini}
    dest = os.path.join(
        ctx('supervisor.dirs.root'),
        '{}.conf'.format(ctx('nginx.server_name').replace('.', '_')))
    upload_template('supervisor.template', dest, context=context)
    fabtools.supervisor.update_config()
    if fabtools.supervisor.process_status(name) == 'RUNNING':
        fabtools.supervisor.restart_process(name)
    elif fabtools.supervisor.process_status(name) == 'STOPPED':
        fabtools.supervisor.start_process(name)
