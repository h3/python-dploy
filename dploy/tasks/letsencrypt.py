import fabtools

from fabric.contrib import files
from fabric.api import task, sudo, execute
from dploy.context import ctx
from dploy.utils import upload_template


@task
def install():
    """
    Install letsencrypt's certbot
    """
    # TODO: detect unsupported platforms
    if not fabtools.deb.is_installed('software-properties-common'):
        fabtools.deb.install('software-properties-common')
    fabtools.deb.add_apt_key(keyid='75BCA694', keyserver='keyserver.ubuntu.com')
    sudo('add-apt-repository ppa:certbot/certbot')
    fabtools.deb.update_index()
    fabtools.deb.upgrade(safe=True)
    fabtools.deb.install([
        'software-properties-common',
        'python-certbot-nginx'
    ])


@task
def setup():
    """
    Configure SSL with letsencrypt's certbot for the domain
    """
    server_name = ctx("nginx.server_name")
    path_letsencrypt = '/etc/letsencrypt/live'
    path_dhparams = '/etc/letsencrypt/ssl-dhparams.pem'
    path_key = '{}/{}/privkey.pem'.format(path_letsencrypt, server_name)
    path_cert = '{}/{}/fullchain.pem'.format(path_letsencrypt, server_name)

    if not fabtools.deb.is_installed('certbot'):
        execute(install)

    if not files.exists(path_cert, use_sudo=True):
        upload_template('nginx_letsencrypt_init.template',
                        ctx('nginx.config_path'))
        sudo('certbot --authenticator webroot --installer nginx -d {}'.format(
            server_name))

    upload_template('nginx_letsencrypt.template', ctx('nginx.config_path'),
                    context={
                        'ssl': {
                            'letsencrypt': True,
                            'dhparams': path_dhparams,
                            'key': path_key,
                            'cert': path_cert,
                        }
                    })
