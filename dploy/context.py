import os
import sys
import yaml
import collections

from io import BytesIO
from jinja2 import Template

from fabric.api import env, get
from fabric.utils import abort
from fabric.colors import red
from fabric.contrib import files

from dploy.utils import load_yaml, git_dirname

CONTEXT_CACHE = {}


def update(orig_dict, new_dict):
    for key, val in new_dict.items():
        if isinstance(val, collections.Mapping):
            tmp = update(orig_dict.get(key, {}), val)
            orig_dict[key] = tmp
        elif isinstance(val, list):
            orig_dict[key] = (orig_dict.get(key, []) + val)
        else:
            orig_dict[key] = new_dict[key]
    return orig_dict


def get_project_context():
    context = load_yaml(os.path.join(env.base_path, 'dploy.yml'))
    if not context:
        print('The file "dploy.yml" was not found in the current directory.')
        # print('Would you like to bootstrap this project ? [Y|n]')
        # TODO
        sys.exit(1)
    else:
        return context


def get_stage_context(project_name, stage):
    _path = '/root/.context/{project}/{stage}.yml'.format(**{
        'project': project_name,
        'stage': stage,
    })
    if not CONTEXT_CACHE.get(_path):
        if files.exists(_path, use_sudo=True):
            fd = BytesIO()
            get(_path, fd, use_sudo=True)
            CONTEXT_CACHE[_path] = yaml.load(fd.getvalue())
        else:
            print(red(
                'ERROR: context file not found: {}, aborting'.format(_path)))
            sys.exit(1)
            CONTEXT_CACHE[_path] = {}
    return CONTEXT_CACHE.get(_path)


def get_context():
    defaults = os.path.join(os.path.dirname(__file__), 'base-context.yml')
    base_context = load_yaml(defaults)
    project_context = get_project_context()
    base_context = update(base_context, project_context.get('global'))
    # TODO: use get_stage_context
    base_context = update(base_context,
                          project_context.get('stages').get(env.stage))
    return base_context


def ctx(path, default=None, context=None):
    if path == 'stage':
        return env.stage
    elif path == 'base_path':
        return env.base_path
    context = env.context
    if env.host_string:
        context = update(
            context, get_stage_context(
                context['django']['project_name'], env.stage))
    tokens = path.split('.')
    tokens.reverse()
    val = env.context
    while len(tokens):
        try:
            val = val.get(tokens.pop())
            if len(tokens) == 0:
                break
        except AttributeError:
            val = None
            break

    if not val and default is not None:
        val = default
    elif not val:
        abort(red('Configuration error: {}'.format(path)))

    if isinstance(val, str):
        if context is None:
            context = env.context
        context['stage'] = env.stage
        return Template(val).render(**context)
    else:
        return val


def get_project_dir():
    return os.path.join(ctx('nginx.document_root'),
                        git_dirname(ctx('git.repository')))
