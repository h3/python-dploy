import os
import pprint
import fabtools
# import tempfile

from jinja2 import Template
from jinja2.exceptions import TemplateNotFound

from fabric.colors import *  # noqa
from fabric.api import *  # noqa
from fabric.contrib import files
from fabtools import require
from fabtools.python import virtualenv

from dploy.context import get_context, ctx, get_project_dir
from dploy.commands import pip, manage  # noqa
from dploy.utils import git_dirname, upload_template
from dploy.tasks.django import (  # noqa
    django_setup_settings, django_setup, django_collectstatic, django_migrate,
    django
)


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
def print_context():
    """
    Prints deployment context
    """
    print('-' * 80)
    print(green('Global context', bold=True))
    print('-' * 80)
    print('\x1b[33m')
    pprint.pprint(env.context)
    print('\x1b[0m')
    print('-' * 80)


@task
def install_system_dependencies():
    """
    Install system dependencies (dploy.yml:system.packages)
    """
    deps = ctx('system.packages')
    if deps:
        _cmd = 'apt-get install -qy {}'.format(deps.replace('\\\n', ''))
        print(cyan('Installing system dependencies on {}'.format(env.stage)))
        if len(env.hosts) == 0 and env.stage == 'dev':
            local(_cmd)
        else:
            sudo(_cmd)


# @task
# def context_setup():
#     if env.stage == 'dev':
#         abort(red('This task is only for remote stages.'))
#     context_path = '/root/.context/{project}/{stage}.yml'.format(**{
#         'project': ctx('django.project_name'),
#         'stage': env.stage,
#     })
#     if files.exists(context_path, use_sudo=True):
#         # TODO: interactive edit
#         # http://klenwell.com/is/FabricEditRemoteFile
#         print('Context already exists')
#     else:
#         with tempfile.TemporaryFile() as tmp:
#             tmp.write(CONTEXT_TEMPLATE)
#             import IPython
#             IPython.embed()


@task
def create_dirs():
    """
    Creates necessary directories and apply user/group permissions
    """
    paths = []
    print(cyan('Creating directories on {}'.format(env.stage)))
    for k in env.context.keys():
        if type(env.context.get(k)) is dict:
            dirs = env.context.get(k).get('dirs')
            if dirs:
                for name, path in dirs.items():
                    p = Template(path).render(**env.context)
                    paths.append(p)
    out = ' '.join(paths)
    sudo('mkdir -p {paths}'.format(paths=out))
    sudo('chown -R {user}:{group} {paths}'.format(
            user=ctx('system.user'), group=ctx('system.group'), paths=out))


@task
def checkout():
    """
    Checkouts the code on the remote location using git
    """
    branch = ctx('git.branch')
    git_root = ctx('git.dirs.root')
    git_dir = git_dirname(ctx('git.repository'))
    git_path = os.path.join(git_root, git_dir)
    if not fabtools.deb.is_installed('git'):
        fabtools.deb.install('git')

    # Experimental
    require.git.working_copy(ctx('git.repository'),
                             path=git_path, branch=branch, update=True,
                             use_sudo=True)
    with cd(git_path):
        sudo('git submodule update --init --recursive')
        sudo("find . -iname '*.pyc' | xargs rm -f")
    # /Experimental

    # if files.exists(os.path.join(git_path, '.git'), use_sudo=True):
    #     print(cyan('Updating {} on {}'.format(branch, env.stage)))
    #     with cd(git_path):
    #         sudo('git reset --hard')
    #         sudo('git pull')
    #         sudo('git submodule update --init --recursive')
    #         sudo('git checkout {}'.format(branch))
    #         sudo("find . -iname '*.pyc' | xargs rm -f")
    # else:
    #     print(cyan('Cloning {} on {}'.format(branch, env.stage)))
    #     with cd(git_root):
    #         sudo('git clone --recursive -b {} {} {}'.format(
    #             ctx('git.branch'), ctx('git.repository'), git_dir))


@task
def virtualenv_setup():
    """
    Setup virtualenv on the remote location
    """
    venv_root = ctx('virtualenv.dirs.root')
    venv_name = ctx('virtualenv.name')
    venv_path = os.path.join(venv_root, venv_name)
    py = 'python{}'.format(ctx('python.version'))
    env.venv_path = venv_path

    if not fabtools.deb.is_installed('python-virtualenv'):
        fabtools.deb.install('python-virtualenv')
    # Experimental
    require.python.virtualenv(venv_path, python_cmd=py, use_sudo=True)
    with virtualenv(venv_path):
        require.python.pip()
        require.python.setuptools()
    # /Experimental

    # lib_root = os.path.join(venv_root, venv_name, 'lib')
    # if not files.exists(lib_root, use_sudo=True):
    #     print(cyan("Setuping virtualenv on {}".format(env.stage)))
    #     with cd(venv_root):
    #         sudo('virtualenv --python=python{version} {name}'.format(
    #             version=ctx('python.version'),
    #             name=ctx('virtualenv.name')))
    # pip('install -U setuptools pip')  # Just avoiding some headaches..


@task
def install_requirements(upgrade=False):
    """
    Installs pip requirements
    """
    project_dir = get_project_dir()
    requirements_pip = os.path.join(project_dir, 'requirements.pip')
    # it is necessary to cd into project dir to support relative
    # paths inside requirements correctly
    with cd(project_dir):
        if files.exists(requirements_pip, use_sudo=True):
            print(cyan("Installing requirements.pip on {}".format(env.stage)))
            with virtualenv(env.venv_path):
                fabtools.python.install_requirements(
                    requirements_pip, upgrade=upgrade, use_sudo=True)

        requirements_txt = os.path.join(project_dir, 'requirements.txt')
        if files.exists(requirements_txt, use_sudo=True):
            print(cyan("Installing requirements.txt on {}".format(env.stage)))
            with virtualenv(env.venv_path):
                fabtools.python.install_requirements(
                    requirements_txt, upgrade=upgrade, use_sudo=True)

        extra_requirements = ctx('virtualenv.extra_requirements',
                                 default=False)
        if extra_requirements and isinstance(extra_requirements, list):
            for req in extra_requirements:
                print(cyan("Installing {} on {}".format(req, env.stage)))
                with virtualenv(env.venv_path):
                    if req.startswith('./'):
                        req = os.path.join(project_dir, req[:2])
                    fabtools.python.install(req, use_sudo=True)


@task
def cron_setup():
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


@task
def uwsgi_setup():
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


@task
def letsencrypt_install():
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
def letsencrypt_setup():
    """
    Configure SSL with letsencrypt's certbot for the domain
    """
    server_name = ctx("nginx.server_name")
    path_letsencrypt = '/etc/letsencrypt/live'
    path_dhparams = '/etc/letsencrypt/ssl-dhparams.pem'
    path_key = '{}/{}/privkey.pem'.format(path_letsencrypt, server_name)
    path_cert = '{}/{}/fullchain.pem'.format(path_letsencrypt, server_name)

    if not fabtools.deb.is_installed('certbot'):
        execute(letsencrypt_install)

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


@task
def nginx_setup():
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
        execute(letsencrypt_setup)
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


@task
def supervisor_setup():
    """
    Configure supervisor to monitor the uwsgi process
    """
    print(cyan('Configuring supervisor {}'.format(env.stage)))
    if not fabtools.deb.is_installed('supervisor'):
        fabtools.deb.install('supervisor')
    project_dir = get_project_dir()
    uwsgi_ini = os.path.join(project_dir, 'uwsgi.ini')
    process_name = '{}-{}'.format(env.stage, ctx('django.project_name'))
    context = {'uwsgi_ini': uwsgi_ini}
    dest = os.path.join(
        ctx('supervisor.dirs.root'),
        '{}.conf'.format(ctx('nginx.server_name').replace('.', '_')))
    upload_template('supervisor.template', dest, context=context)
    fabtools.supervisor.update_config()
    if fabtools.supervisor.process_status(process_name) == 'RUNNING':
        fabtools.supervisor.restart_process(process_name)
    elif fabtools.supervisor.process_status(process_name) == 'STOPPED':
        fabtools.supervisor.start_process(process_name)


@task
def deploy(upgrade=False):
    """
    Perform all deployment tasks sequentially
    """
    print("Deploying project on {} !".format(env.stage))
    execute(create_dirs)
    execute(checkout)
    execute(virtualenv_setup)
    execute(install_requirements, upgrade=upgrade)
    execute(django_setup)
    execute(cron_setup)
    execute(uwsgi_setup)
    execute(supervisor_setup)
    execute(nginx_setup)
