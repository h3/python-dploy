import os
import fabtools

from fabtools import require
from fabric.api import task, sudo, cd
from fabric.colors import cyan
from dploy.context import ctx
from dploy.utils import git_dirname


@task
def checkout():
    """
    Checkouts the code on the remote location using git
    """
    branch = ctx('git.branch')
    git_root = ctx('git.dirs.root')
    git_dir = git_dirname(ctx('git.repository'))
    git_path = os.path.join(git_root, git_dir)
    if not fabtools.deb.is_installed('git'):
        fabtools.deb.install('git')

    print(cyan('Checking out {} @ {} -> {}'.format(
        branch, ctx('git.repository'), git_path)))
    # Experimental
    require.git.working_copy(ctx('git.repository'),
                             path=git_path, branch=branch, update=True,
                             use_sudo=True)
    with cd(git_path):
        sudo('git submodule update --init --recursive')
        sudo("find . -iname '*.pyc' | xargs rm -f")
    # /Experimental

    # if files.exists(os.path.join(git_path, '.git'), use_sudo=True):
    #     print(cyan('Updating {} on {}'.format(branch, env.stage)))
    #     with cd(git_path):
    #         sudo('git reset --hard')
    #         sudo('git pull')
    #         sudo('git submodule update --init --recursive')
    #         sudo('git checkout {}'.format(branch))
    #         sudo("find . -iname '*.pyc' | xargs rm -f")
    # else:
    #     print(cyan('Cloning {} on {}'.format(branch, env.stage)))
    #     with cd(git_root):
    #         sudo('git clone --recursive -b {} {} {}'.format(
    #             ctx('git.branch'), ctx('git.repository'), git_dir))
