from jinja2 import Template

from fabric.api import task, env, local, sudo
from fabric.colors import cyan
from dploy.context import ctx


@task
def install_dependencies():
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
