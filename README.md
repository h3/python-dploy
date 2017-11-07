# python-dploy

# Commands


# on

The `on` command is used to specify on which stage to run the following commands.

```bash
$ fab on:<stagename> <command>
```

You can chain many commands:

```bash
$ fab on:<stagename> <command1> <command2> <command3>
```

Or run multiple commands on multiple stages:

```bash
$ fab on:<stage1> <command1> <command2> on:<stage3> <command3>
```

## install\_system\_dependencies

Some packages might need to be installed prior to deployment, the command
`install_system_dependencies` handles system level requirements.


```bash
$ fab on:beta install_system_dependencies
```

 **Note**: Only works for debian based Linux distributions for now.

## deploy

The `deploy` command is the main command used to deploy or update a site.


```bash
$ fab on:beta deploy
```

It is up to you to define your deploy command in your project's `fabfile.py`
according to your specific needs.

Here's a generic fabfile template for fairly common django setup:


 ```python
import os

from dploy.tasks import (  # noqa
    env, task, execute, on, print_context, create_dirs, checkout,
    setup_virtualenv, update_requirements, install_requirements,
    setup_django_settings, django_migrate, django_collectstatic,
    setup_cron, setup_cron, setup_uwsgi, setup_supervisor,
    setup_nginx, install_system_dependencies
)

env.base_path = os.path.dirname(__file__)


@task
def deploy(update=False):
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
    execute(setup_nginx)
```

It is also possible to run any of the steps individually:


```bash
$ fab on:beta setup_uwsgi setup_nginx
```
