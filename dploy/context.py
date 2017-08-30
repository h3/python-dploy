import os
import sys
import yaml
import collections

from StringIO import StringIO
from jinja2 import Template

from fabric.api import env, get
from fabric.colors import red
from fabric.contrib import files

CONTEXT_CACHE = {}

BASE_GLOBAL_CONTEXT = """
dploy:
    project_name: 'example_project'
"""


def update(orig_dict, new_dict):
    for key, val in new_dict.iteritems():
        if isinstance(val, collections.Mapping):
            tmp = update(orig_dict.get(key, {}), val)
            orig_dict[key] = tmp
        elif isinstance(val, list):
            orig_dict[key] = (orig_dict.get(key, []) + val)
        else:
            orig_dict[key] = new_dict[key]
    return orig_dict


def get_project_context():
    _f = os.path.join(env.base_path, 'dploy.yml')
    try:
        with open(_f, 'r') as fd:
            try:
                rs = yaml.load(fd)
            except yaml.YAMLError as e:
                print(e)
    except IOError:
        print('The file dploy.yml was not found in the current directory.')
        print('Would you like to bootstrap this project ? [Y|n]')
        # TODO
        sys.exit(1)
    return rs


def get_stage_context(project_name, stage):
    _path = '/root/.context/{project}/{stage}.yml'.format(**{
        'project': project_name,
        'stage': stage,
    })
    if not CONTEXT_CACHE.get(_path):
        if files.exists(_path, use_sudo=True):
            fd = StringIO()
            get(_path, fd, use_sudo=True)
            CONTEXT_CACHE[_path] = yaml.load(fd.getvalue())
        else:
            print(red('Warning context file not found: {}'.format(_path)))
            CONTEXT_CACHE[_path] = {}
    return CONTEXT_CACHE.get(_path)


def get_context():
    base_context = yaml.load(BASE_GLOBAL_CONTEXT)
    project_context = get_project_context()
    base_context = update(base_context, project_context.get('global'))
    # TODO: use get_stage_context
    base_context = update(base_context,
                          project_context.get('stages').get(env.stage))
    return base_context


def ctx(path, context=None):
    if path == 'stage':
        return env.stage
    elif path == 'base_path':
        return env.base_path
    context = env.context
    if env.host_string:
        context = update(
            context, get_stage_context(
                context['dploy']['project_name'], env.stage))
    tokens = path.split('.')
    tokens.reverse()
    val = env.context
    while len(tokens):
        try:
            val = val.get(tokens.pop())
        except AttributeError:
            print(red('Configuration error: {}'.format(path)))
            sys.exit(1)
    if isinstance(val, str):
        if context is None:
            context = env.context
        return Template(val).render(**context)
    else:
        return val
