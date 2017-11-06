import os
import yaml


def load_yaml(path):
    try:
        with open(path, 'r') as fd:
            try:
                rs = yaml.load(fd)
            except yaml.YAMLError as e:
                rs = None
                print(e)  # TODO: use logging
    except IOError:
        rs = None
    return rs


def parent_dir(p):
    return os.path.abspath(os.path.join(p, os.pardir))


def git_dirname(uri):
    return uri.split('/')[-1].replace('.git', '')
