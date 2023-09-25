import numpy as np
import random
import os
import shutil


def set_random_seed(seed):
    """Set random seeds."""
    random.seed(seed)
    np.random.seed(seed)
    # torch.manual_seed(seed)
    # torch.cuda.manual_seed(seed)
    # torch.cuda.manual_seed_all(seed)


def ensure_path(path, remove=False):
    """
    mkdir and check when there exists path

    Args:
        path(str): file or folder path
        remove(bool): if exists, whether force to remove path
    """
    basename = os.path.basename(path).rstrip('/')
    if os.path.exists(path):
        if remove or input('{} exists, remove? (y/n)'.format(path)) == 'y':
            shutil.rmtree(path)
            os.makedirs(path)
    else:
        os.makedirs(path)


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def copy_option(opt):
    opt['path']['experimen']