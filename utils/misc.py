import numpy as np
import random
import os
import shutil
import time
import os.path as osp


def list2str(input_list):
    msg = ''
    for i in input_list:
        msg += str(i) + ' '
    return msg


def exists_results(opt, test_month, indus_type):
    if opt.get('path') and opt.get('path').get('results_path'):
        results_folder = opt.get('path').get('results_path')[test_month]
        results_name = 'results_{}_indus{}.csv'.format(test_month, indus_type)
        results_path = osp.join(results_folder, results_name)
        if osp.exists(results_path):
            return True
        else:
            return False
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

def ensure_table_name(database, table_name):

    if input('Signals will be saved to {}.{} (y/n)'.format(database, table_name)) == 'y':
        pass
    else:
        pass

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


def scandir(dir_path, suffix=None, recursive=False, full_path=False):
    """Scan a directory to find the interested files.

    Args:
        dir_path (str): Path of the directory.
        suffix (str | tuple(str), optional): File suffix that we are
            interested in. Default: None.
        recursive (bool, optional): If set to True, recursively scan the
            directory. Default: False.
        full_path (bool, optional): If set to True, include the dir_path.
            Default: False.

    Returns:
        A generator for all the interested files with relative paths.
    """

    if (suffix is not None) and not isinstance(suffix, (str, tuple)):
        raise TypeError('"suffix" must be a string or tuple of strings')

    root = dir_path

    def _scandir(dir_path, suffix, recursive):
        for entry in os.scandir(dir_path):
            if not entry.name.startswith('.') and entry.is_file():
                if full_path:
                    return_path = entry.path
                else:
                    return_path = osp.relpath(entry.path, root)

                if suffix is None:
                    yield return_path
                elif return_path.endswith(suffix):
                    yield return_path
            else:
                if recursive:
                    yield from _scandir(entry.path, suffix=suffix, recursive=recursive)
                else:
                    continue

    return _scandir(dir_path, suffix=suffix, recursive=recursive)