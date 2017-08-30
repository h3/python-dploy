from fabric.api import run, task, env, execute, cd, sudo, get, hide


class FabricException(Exception):
    pass

env.abort_exception = FabricException
env.use_ssh_config = True
