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


def exists_results_low_price(opt, test_month, indus_type, bs_flag):
    if opt.get('path') and opt.get('path').get('results_path'):
        results_folder = opt.get('path').get('results_path')[test_month]
        results_name = 'result_summary_{}_price_group_{}_{}.csv'.format(test_month, indus_type, bs_flag)
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


def ensure_path(path, ensure=True):
    """
    mkdir and check when there exists path

    Args:
        path(str): file or folder path
        remove(bool): if exists, whether force to remove path
    """
    basename = os.path.basename(path).rstrip('/')
    new_session_flag = False
    if os.path.exists(path):
        if ensure:
            input_content = input('{} exists, remove? (y/n)'.format(path))
            if input_content == 'y':
                new_session_flag = True
                shutil.rmtree(path)
                os.makedirs(path)
        else:
            pass
    else:
        os.makedirs(path)
    return new_session_flag

def ensure_table_name(database, table_name, skip=False):
    if skip:
        print('Signals will be saved to {}.{}'.format(database, table_name))
    else:
        if input('Signals will be saved to {}.{} (y/n)'.format(database, table_name)) == 'y':
            pass
        else:
            return -1

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


def deep_merge_with_log(opt, opt_manager, modified_keys=None, parent_key=''):
    if modified_keys is None:
        modified_keys = []

    for key, value in opt_manager.items():
        full_key = f"{parent_key}.{key}" if parent_key else key

        if key in opt:
            if isinstance(opt[key], dict) and isinstance(value, dict):
                # 递归处理嵌套字典
                deep_merge_with_log(opt[key], value, modified_keys, full_key)
            elif opt[key] != value:
                # 记录非字典类型的修改
                modified_keys.append((full_key, opt[key], value))
                opt[key] = value
        # else:
        #     # 记录新增的键
        #     modified_keys.append((full_key, None, value))
        #     opt[key] = value

    return opt, modified_keys


