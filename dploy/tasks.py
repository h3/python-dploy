import os
import sys
import pprint
import time
import fabtools
import tempfile

from jinja2 import Template
from jinja2.exceptions import TemplateNotFound

from fabric.colors import cyan, green, red, yellow
from fabric.api import task, env, cd, sudo, local, get, hide, run, execute  # noqa
from fabric.contrib import files
from fabric.utils import abort

from dploy.context import get_context, ctx, get_project_dir
from dploy.commands import pip, manage
from dploy.utils import (
    FabricException, git_dirname, version_supports_migrations, select_template,
    upload_template,
)

TEMPLATES_DIR = './dploy/'
CONTEXT_TEMPLATE = """
django:
    scret_key: '{{ ctx('django.secret_key ') }}'

databases:
    default:
        user: ''
        name: ''
        password: ''
        host: ''

email:
    host: ''
    tls: true
    port: 587
    user: ''
    pass: ''
"""


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
    deps = ctx('system.packages')
    if deps:
        _cmd = 'apt-get install -qy {}'.format(deps.replace('\\\n', ''))
        print(cyan('Installing system dependencies on {}'.format(env.stage)))
        if len(env.hosts) == 0 and env.stage == 'dev':
            local(_cmd)
        else:
            sudo(_cmd)


# @task
# def configure_context():
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
    print(cyan('Creating directories on {}'.format(env.stage)))
    for k in env.context.keys():
        if type(env.context.get(k)) is dict:
            dirs = env.context.get(k).get('dirs')
            if dirs:
                for name, path in dirs.items():
                    p = Template(path).render(**env.context)
                    sudo('mkdir -p {}'.format(p))
                    sudo('chown -R {user}:{group} {path}'.format(
                         user=ctx('system.user'), group=ctx('system.group'),
                         path=p))


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
    if files.exists(os.path.join(git_path, '.git'), use_sudo=True):
        print(cyan('Updating {} on {}'.format(branch, env.stage)))
        with cd(git_path):
            sudo('git reset --hard')
            sudo('git pull')
            sudo('git submodule update --init --recursive')
            sudo('git checkout {}'.format(branch))
            sudo("find . -iname '*.pyc' | xargs rm -f")
    else:
        print(cyan('Cloning {} on {}'.format(branch, env.stage)))
        with cd(git_root):
            sudo('git clone --recursive -b {} {} {}'.format(
                ctx('git.branch'), ctx('git.repository'), git_dir))


@task
def setup_virtualenv():
    """
    Setup virtualenv on the remote location
    """
    venv_root = ctx('virtualenv.dirs.root')
    venv_name = ctx('virtualenv.name')
    lib_root = os.path.join(venv_root, venv_name, 'lib')
    if not fabtools.deb.is_installed('python-virtualenv'):
        fabtools.deb.install('python-virtualenv')
    if not files.exists(lib_root, use_sudo=True):
        print(cyan("Setuping virtualenv on {}".format(env.stage)))
        with cd(venv_root):
            sudo('virtualenv --python=python{version} {name}'.format(
                version=ctx('python.version'),
                name=ctx('virtualenv.name')))
    pip('install -U setuptools pip')  # Just avoiding some headaches..


@task
def install_requirements():
    project_dir = get_project_dir()
    requirements_pip = os.path.join(project_dir, 'requirements.pip')
    if files.exists(requirements_pip, use_sudo=True):
        print(cyan("Installing requirements.pip on {}".format(env.stage)))
        pip('install -qr {}'.format(requirements_pip))

    requirements_txt = os.path.join(project_dir, 'requirements.txt')
    if files.exists(requirements_txt, use_sudo=True):
        print(cyan("Installing requirements.txt on {}".format(env.stage)))
        pip('install -qr {}'.format(requirements_txt))

    extra_requirements = ctx('virtualenv.extra_requirements', default=False)
    if extra_requirements and isinstance(extra_requirements, list):
        for req in extra_requirements:
            if files.exists(requirements_txt, use_sudo=True):
                print(cyan("Installing {} on {}".format(req, env.stage)))
                pip('install -qr {}'.format(req))


@task
def update_requirements():
    print(cyan("Updating requirements on {}".format(env.stage)))
    pip('install -qUr requirements.pip')


@task
def setup_django_settings():
    """
    Takes the dploy/<STAGE>_settings.py template and upload it to remote
    django project location (as local_settings.py)
    """
    print(cyan("Setuping django settings project on {}".format(env.stage)))
    project_dir = get_project_dir()
    project_name = ctx('django.project_name')
    stage_settings = '{stage}_settings.py'.format(stage=env.stage)
    templates = [
        os.path.join(TEMPLATES_DIR, stage_settings),
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
def setup_django():
    execute(setup_django_settings)
    execute(django_migrate)
    execute(django_collectstatic)


@task
def setup_cron():
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
def setup_uwsgi():
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
def django(cmd):
    print(cyan("Django manage {} on {}".format(cmd, env.stage)))
    manage(cmd)


@task
def install_letsencrypt():
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
def setup_letsencrypt():
    server_name = ctx("nginx.server_name")
    path_letsencrypt = '/etc/letsencrypt/live'
    path_dhparams = '/etc/letsencrypt/ssl-dhparams.pem'
    path_key = '{}/{}/privkey.pem'.format(path_letsencrypt, server_name)
    path_cert = '{}/{}/fullchain.pem'.format(path_letsencrypt, server_name)

    if not fabtools.deb.is_installed('certbot'):
        execute(install_letsencrypt)

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
def setup_nginx():
    print(cyan('Configuring nginx on {}'.format(env.stage)))
    context = {
        'ssl_letsencrypt': False,
        'ssl_with_dhparam': False,
        'ssl_cert': None,
        'ssl_key': None,
    }

    if ctx('ssl.letsencrypt'):
        execute(setup_letsencrypt)
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
def setup_supervisor():
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
def check_services():
    print(cyan('Checking services on {}'.format(env.stage)))
    time.sleep(3)  # give uwsgi time to come back
    checks = {
        'uwsgi': "ps aux | grep uwsgi | grep '{}' | grep '^www-data' | grep -v grep".format(ctx('nginx.server_name')),  # noqa
        'nginx': "ps aux | grep nginx | grep '^www-data' | grep -v grep",
        'supervisor': "ps aux | grep supervisord.conf | grep '^root' | grep -v grep",  # noqa
    }
    for check, cmd in checks.items():
        try:
            label = ('%s...' % check).ljust(20)
            with hide('output', 'running'):
                run(cmd)
            print(' - %s [%s]' % (label, green('OK', bold=True)))
        except Exception:
            print(' - %s [%s]' % (label, red('FAIL', bold=True)))


@task
def install_packages():
    if ctx('system.packages'):
        sudo('apt-get update && apt-get upgrade')
        sudo('apt-get install -qy {}'.format(ctx('system.packages')))


@task
def rollback_list():
    manage('rollback --list')


@task
def rollback_create():
    print(cyan('Creating rollback on {}'.format(env.stage)))
    manage('rollback --create')


@task
def rollback_restore(uid=None):
    print(cyan('Restoring rollback on {}'.format(env.stage)))
    manage('rollback --restore {}'.format(uid))


@task
def dumpdata(app, dest=None):
    if dest is None:
        manage('dumpdata --indent=2 {}'.format(app))
    else:
        tmp_file = '/tmp/{}.tmp'.format(app)
        manage('dumpdata --indent=2 {} > {}'.format(app, tmp_file))
        with open(dest, 'w+') as fd:
            get(tmp_file, fd, use_sudo=True)
        sudo('rm -f {}'.format(tmp_file))


"""
@task
def deploy(update=False):
    print("Deploying project on {} !".format(env.stage))
    execute(rollback_create)
    execute(create_dirs)
    execute(checkout)
    execute(setup_virtualenv)
    if update:
        execute(update_requirements)
    else:
        execute(install_requirements)
    execute(setup_django_settings)
    execute(django_migrate)
    execute(django_collectstatic)
    execute(setup_cron)
    execute(setup_uwsgi)
    execute(setup_supervisor)
    if ctx('nginx.hosts'):
        execute(setup_nginx, hosts=ctx('nginx.hosts'))
    else:
        execute(setup_nginx)
    execute(check_services)
    manage('deploy_notification')
"""
