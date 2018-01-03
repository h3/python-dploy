import os
import sys
import pprint
import time

from jinja2 import Template
from jinja2.exceptions import TemplateNotFound

from fabric.colors import cyan, green, red, yellow
from fabric.api import task, env, cd, sudo, local, get, hide, run, execute  # noqa
from fabric.contrib import files

from dploy.context import get_context, ctx, get_project_dir
from dploy.commands import pip, manage
from dploy.utils import (
    FabricException, git_dirname, version_supports_migrations, select_template,
)

TEMPLATES_DIR = './dploy/'


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
                for name, path in dirs.iteritems():
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

    extra_requirements = ctx('virtualenv.extra_requirements')
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
    files.upload_template(filename, _settings_dest,
                          context={'ctx': ctx, 'project_dir': project_dir},
                          use_jinja=True, template_dir=templates_dir,
                          use_sudo=True, backup=False, mode=None)


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
def setup_cron():
    # Cron doesn't like dots in filename
    filename = ctx('nginx.server_name').replace('.', '_')
    dest = os.path.join(ctx('cron.config_path'), filename)
    try:
        files.upload_template('cron.template', dest,
                              context={'ctx': ctx}, use_jinja=True,
                              template_dir=TEMPLATES_DIR, use_sudo=True,
                              backup=False, mode=None)

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
    files.upload_template('uwsgi.template', uwsgi_ini,
                          context=context, use_jinja=True,
                          template_dir=TEMPLATES_DIR, use_sudo=True,
                          backup=False, mode=None)


# ---


@task
def django(cmd):
    print(cyan("Django manage {} on {}".format(cmd, env.stage)))
    manage(cmd)


@task
def setup_nginx():
    print(cyan('Configuring nginx on {}'.format(env.stage)))

    ssl = False
    context = {
        'ctx': ctx,
        'ssl_with_dhparam': False,
        'ssl_cert': None,
        'ssl_key': None,
        'project_dir': get_project_dir(),
    }

    if ctx('ssl.key') and ctx('ssl.cert'):
        ssl = True
        if files.exists(ctx('ssl.key'), use_sudo=True):
            context['ssl_key'] = ctx('ssl.key')
        if files.exists(ctx('ssl.cert'), use_sudo=True):
            context['ssl_cert'] = ctx('ssl.cert')
        if files.exists(ctx('ssl.dhparam'), use_sudo=True):
            context['ssl_with_dhparam'] = True
    if ssl:
        files.upload_template(
            'nginx_ssl.template', ctx('nginx.config_path'),
            context=context, use_jinja=True, template_dir='dploy/',
            use_sudo=True, backup=False, mode=None)
    else:
        files.upload_template(
            'nginx.template', ctx('nginx.config_path'),
            context=context, use_jinja=True, template_dir='dploy/',
            use_sudo=True, backup=False, mode=None)

    if files.exists(ctx('nginx.document_root'), use_sudo=True):
        sudo('chown -R {user}:{group} {path}'.format(
            path=ctx('nginx.document_root'), user=ctx('system.user'),
            group=ctx('system.group')))

    sudo('service nginx reload')


@task
def setup_supervisor():
    print(cyan('Configuring supervisor {}'.format(env.stage)))
    project_dir = get_project_dir()
    uwsgi_ini = os.path.join(project_dir, 'uwsgi.ini')
    context = {'project_dir': project_dir, 'uwsgi_ini': uwsgi_ini, 'ctx': ctx}
    dest = os.path.join(
        ctx('supervisor.dirs.root'),
        '{}.conf'.format(ctx('nginx.server_name').replace('.', '_')))
    files.upload_template(
        'supervisor.template', dest,
        context=context, use_jinja=True, template_dir='dploy/', use_sudo=True,
        backup=False, mode=None)
    sudo('supervisorctl reload')


@task
def check_services():
    print(cyan('Checking services on {}'.format(env.stage)))
    time.sleep(3)  # give uwsgi time to come back
    checks = {
        'uwsgi': "ps aux | grep uwsgi | grep '{}' | grep '^www-data' | grep -v grep".format(ctx('nginx.server_name')),  # noqa
        'nginx': "ps aux | grep nginx | grep '^www-data' | grep -v grep",
        'supervisor': "ps aux | grep supervisord.conf | grep '^root' | grep -v grep",  # noqa
    }
    for check, cmd in checks.iteritems():
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
