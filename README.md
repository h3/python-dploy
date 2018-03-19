# python-dploy

## Installation

There are no official release yet, so to install it you must add these to your requirements file.

### Python2

```
git+https://github.com/h3/python-dploy.git#egg=dploy
```

### Python3

If you need Python3 support, you will also need this temporary fork of fabtools:

```
git+https://github.com/h3/fabtools.git@python3#egg=fabtools-0.20.0
git+https://github.com/h3/python-dploy.git#egg=dploy
```
This is needed until official Python3 support is added to fabtools ([seems to be planned for 0.21.0](https://github.com/fabtools/fabtools/commit/f1960b0323323c825d72180ce8d7b3a17dda59ea#diff-354f30a63fb0907d4ad57269548329e3R5))


## Global commands

### init

It is up to you to define your deploy tasks in your project's `fabfile.py`.

Use `python-dploy init <projectname>` to generate a generic fabfile that you can
later modify to your needs:

```bash
$ cd project-dir/
$ source venv/bin/activate
(venv)$ pip install -r requirements.pip
(venv)$ python-dploy init projectname
Git repository: git@gitlab.com:namespace/project-name.git
Git directory: [project-name]
Created dploy.yml
Created fabfile.py
```

### Usage and commands

```bash
(venv)$ fab -l

This fabfile is used to deploy mp project

The project can be deployed as follow:

$ fab on:prod deploy

Tasks can be chained:

$ fab on:prod virtualenv.setup nginx.setup

Multi stage deployment can also be chained:

$ fab on:beta deploy on:prod deploy


Documentation: https://github.com/h3/python-dploy


Available commands:

    deploy                           Perform all deployment tasks sequentially
    on                               Sets the stage to perform action on
    context.pprint                   Prints deployment context
    context.setup                    Create context on remote stage (not functional yet)
    cron.setup                       Configure Cron if a dploy/cron.template exists
    django.collectstatic             Collect static medias
    django.dumpdata                  Runs dumpdata on a given app and fetch the file locally
    django.manage                    Runs django manage.py with a given command
    django.migrate                   Perform django migration (only if the django version is >= 1.7)
    django.setup                     Performs django_setup_settings, django_migrate and django_collectstatic
    django.setup_settings            Takes the dploy/<STAGE>_settings.py template and upload it to remote
    git.checkout                     Checkouts the code on the remote location using git
    letsencrypt.install              Install letsencrypt's certbot
    letsencrypt.setup                Configure SSL with letsencrypt's certbot for the domain
    nginx.setup                      Configure nginx, will trigger letsencrypt setup if required
    supervisor.setup                 Configure supervisor to monitor the uwsgi process
    system.create_dirs               Creates necessary directories and apply user/group permissions
    system.install_dependencies      Install system dependencies (dploy.yml:system.packages)
    uwsgi.setup                      Configure uWSGI
    virtualenv.install_requirements  Installs pip requirements
    virtualenv.setup                 Setup virtualenv on the remote location
```


### Project level fabfile.py

The `python-dploy init projectname` command will generate a `fabfile.py`
template that works of out the box using the default deploy task.

This is all that is needed:

```python
import os
from dploy.tasks import *  # noqa
env.base_path = os.path.dirname(__file__)
```


### Tweaking default workflow

Here's an example of deploy workflow tweak to add a rollback
step that runs only on the production stage:


```python
import os
from dploy.tasks import *  # noqa
env.base_path = os.path.dirname(__file__)


@task
def rollback_list():
    if env.stage == 'prod':
        manage('rollback --list')


@task
def rollback_create():
    if env.stage == 'prod':
        print(cyan('Creating rollback on %s' % env.stage))
        manage('rollback --create --no-media')


@task
def rollback_restore(uid=None):
    if env.stage == 'prod':
        print(cyan('Restoring rollback on %s' % env.stage))
        manage('rollback --restore {}'.format(uid))


@task
def deploy(upgrade=False):
    print(cyan("Deploying project on {} !".format(env.stage)))
    if env.stage == 'prod':
        execute(rollback_create)
    execute('system.setup')
    execute('git.checkout')
    execute('virtualenv.setup', upgrade=upgrade)
    execute('django.setup')
    execute('cron.setup')
    execute('uwsgi.setup')
    execute('supervisor.setup')
    execute('nginx.setup')
```

**Note**: This is an example that assumes that there is a `rollback` management command present in the django project.


## Project commands


### on

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

### install\_system\_dependencies

Some packages might need to be installed prior to deployment, the command
`install_system_dependencies` handles system level requirements.


```bash
$ fab on:beta install_system_dependencies
```

 **Note**: Only works for debian based Linux distributions for now.

### deploy

The `deploy` command is the main command used to deploy or update a site.


```bash
$ fab on:beta deploy
```

It is also possible to run any of the steps individually:


```bash
$ fab on:beta setup_uwsgi setup_nginx
```
