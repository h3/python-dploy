# python-dploy

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
