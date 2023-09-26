import numpy as np
import random
import os
import shutil
import time
import os.path as osp


def exists_results(opt, test_month, indus_type):

    results_folder=osp.join(opt['path']['results_root'], str(test_month))
    results_name = 'results_month{}_indus{}.csv'.format(test_month, indus_type)
    results_path = osp.join(results_folder, results_name)
    if osp.exists(results_path):
        return True
    else:
        return False

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

class Timer():
    def __init__(self):
        self.v = time.time()

    def start(self):
        self.v = time.time()

    def item(self):
        return time.time() - self.v


def time_str(t):
    if t > 3600:
        return '{:.1f}h'.format(t/3600)
    if t > 60:
        return '{:.1f}min'.format(t/60)
    return '{:.1f}s'.format(t)


def get_time_str():
    return time.strftime('%Y%m%d_%H%M%S', time.localtime())

