import os

from fabric.api import task, sudo, env
from fabric.colors import cyan, yellow
from dploy.context import ctx
from dploy.utils import upload_template
from jinja2.exceptions import TemplateNotFound


@task
def setup():
    """
    Configure Cron if a dploy/cron.template exists
    """
    # Cron doesn't like dots in filename
    filename = ctx('nginx.server_name').replace('.', '_')
    dest = os.path.join(ctx('cron.config_path'), filename)
    try:
        upload_template('cron.template', dest)
        print(cyan('Configuring cron {}'.format(env.stage)))
        # We make sure the cron file always ends with a blank line, otherwise
        # it will be ignored by cron. Yeah, that's retarded.
        sudo("echo -en '\n' >> {}".format(dest))
        sudo('chown -R root:root {}'.format(dest))
        sudo('chmod 644 {}'.format(dest))
    except TemplateNotFound:
        print(yellow('Skipping cron configuration on {}'.format(env.stage)))
