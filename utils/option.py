import yaml
import os
from collections import OrderedDict
import random
import argparse
import os.path as osp
import shutil

from utils.misc import set_random_seed, ensure_path, mkdir

def dict2str(opt, indent_level=1):
    """dict to string for printing options.

    Args:
        opt (dict): Option dict.
        indent_level (int): Indent level. Default: 1.

    Return:
        (str): Option string for printing.
    """
    msg = '\n'
    for k, v in opt.items():
        if isinstance(v, dict):
            msg += ' ' * (indent_level * 2) + k + ':['
            msg += dict2str(v, indent_level + 1)
            msg += ' ' * (indent_level * 2) + ']\n'
        else:
            msg += ' ' * (indent_level * 2) + k + ': ' + str(v) + '\n'
    return msg

def ordered_yaml():
    """Support OrderedDict for yaml.

    Returns:
        tuple: yaml Loader and Dumper.
    """
    try:
        from yaml import CDumper as Dumper
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Dumper, Loader

    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

    def dict_representer(dumper, data):
        return dumper.represent_dict(data.items())

    def dict_constructor(loader, node):
        return OrderedDict(loader.construct_pairs(node))

    Dumper.add_representer(OrderedDict, dict_representer)
    Loader.add_constructor(_mapping_tag, dict_constructor)
    return Loader, Dumper

def yaml_load(f):
    """Load yaml file or string.

    Args:
        f (str): File path or a python string.

    Returns:
        dict: Loaded dict.
    """
    #use ordered_yaml loader
    if os.path.isfile(f):
        with open(f, 'r') as f:
            return yaml.load(f, Loader=ordered_yaml()[0])
    else:
        return yaml.load(f, Loader=ordered_yaml()[0])

    # # use FullLoader
    # if os.path.isfile(f):
    #     with open(f, 'r', encoding='utf-8') as f:
    #         result = yaml.load(f.read(), Loader=yaml.FullLoader)
    # else:
    #     return yaml.load(f, Loader=yaml.FullLoader)


def parse_options(root_path):
    parser = argparse.ArgumentParser()
    parser.add_argument('-option', type=str, default='option/test_lgbm_300s_highprice_hs300.yaml', help='Path to option YAML file.')
    parser.add_argument('-is_runtime', action='store_true', help='Whether the phase is backtesting or runtime')
    args = parser.parse_args()

    # parse yml to dict
    opt = yaml_load(args.option)

    # parse backtest flag
    opt['is_runtime'] = args.is_runtime

    # random seed
    seed = opt.get('manual_seed')
    if seed is None:
        seed = random.randint(1, 10000)
        opt['manual_seed'] = seed
    set_random_seed(seed)

    # save path init
    if not opt.get('path'):
        opt['path'] = dict()
    # experiment path
    experiments_root = opt['path'].get('experiments_root')
    if experiments_root is None:
        experiments_root = osp.join(root_path, 'experiments')
    experiments_root = osp.join(experiments_root, opt['name'])
    opt['path']['experiments_root'] = experiments_root
    ensure_path(experiments_root)

    # saving path
    opt['path']['model_path'] = dict()
    opt['path']['results_path'] = dict()
    opt['path']['preprocess_path'] = dict()
    opt['path']['inference_path'] = dict()
    opt['path']['signal_path'] = dict()
    for test_month in opt['dataset']['test_month']:
        model_path = osp.join(experiments_root, str(test_month), 'ckpt')
        opt['path']['model_path'][test_month] = model_path
        mkdir(model_path)

        results_path = osp.join(experiments_root, str(test_month),'results')
        opt['path']['results_path'][test_month]  = results_path
        mkdir(results_path)

        preprocess_path = osp.join(experiments_root, str(test_month), 'preprocess_params')
        opt['path']['preprocess_path'][test_month] = preprocess_path
        mkdir(preprocess_path)

        inference_path = osp.join(experiments_root, str(test_month), 'inference_params')
        opt['path']['inference_path'][test_month] = inference_path
        mkdir(inference_path)

        signal_path = osp.join(experiments_root, str(test_month), 'signal')
        opt['path']['signal_path'][test_month] = signal_path
        mkdir(signal_path)



    # log path
    log_root = opt['path'].get('log_root')
    if log_root is None:
        log_root = osp.join(experiments_root, 'log')
    opt['path']['log'] = log_root
    mkdir(log_root)

    # copy option
    shutil.copy2(args.option, opt['path']['experiments_root'])

    return opt

