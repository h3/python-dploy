import os
import yaml


class FabricException(Exception):
    pass


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


def version_supports_migrations(v):
    major, minor, revision = map(int, v.split('.'))
    if major > 1:
        return True
    elif major == 1 and minor >= 7:
        return True
    else:
        return False
