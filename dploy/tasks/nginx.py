from fabric.contrib import files
from fabric.api import task, sudo, env, execute
from fabric.colors import cyan
from dploy.context import ctx
from dploy.utils import upload_template


@task
def setup():
    """
    Configure nginx, will trigger letsencrypt setup if required
    """
    print(cyan('Configuring nginx on {}'.format(env.stage)))
    context = {
        'ssl_letsencrypt': False,
        'ssl_with_dhparam': False,
        'ssl_cert': None,
        'ssl_key': None,
    }

    if ctx('ssl.letsencrypt'):
        execute('letsencrypt.setup')
    elif ctx('ssl.key') and ctx('ssl.cert'):
        ssl = True
        dhparams = ctx('ssl.dhparam', default=False)
        key = ctx('ssl.key', default=False)
        cert = ctx('ssl.cert', default=False)

        if key and files.exists(key, use_sudo=True):
            context['ssl_key'] = ctx('ssl.key')
        if cert and files.exists(cert, use_sudo=True):
            context['ssl_cert'] = ctx('ssl.cert')
        if dhparams and files.exists(dhparams, use_sudo=True):
            context['ssl_with_dhparam'] = True
        if ssl:
            upload_template(
                'nginx_ssl.template', ctx('nginx.config_path'), context=context)
    else:
        upload_template(
            'nginx.template', ctx('nginx.config_path'), context=context)

    if files.exists(ctx('nginx.document_root'), use_sudo=True):
        sudo('chown -R {user}:{group} {path}'.format(
            path=ctx('nginx.document_root'), user=ctx('system.user'),
            group=ctx('system.group')))

    sudo('service nginx reload')
