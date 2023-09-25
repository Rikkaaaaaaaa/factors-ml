import yaml
import os
from collections import OrderedDict
import random
import argparse
import os.path as osp
import shutil

from utils.misc import set_random_seed, ensure_path, mkdir



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
    parser.add_argument('-option', type=str, default='', help='Path to option YAML file.')
    parser.add_argument('-is_backtest', type=bool, default=True, help='Whether the phase is backtesting or runtime')
    args = parser.parse_args()

    #args.option = 'config\wind1_lgbm_alpha5_15s.yaml'

    # parse yml to dict
    opt = yaml_load(args.option)

    # parse backtest flag
    opt['is_backtest'] = args.is_backtest

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

    # model root: ckpt and training_states
    model_root = opt['path'].get('model_root')
    if model_root is None:
        model_root = osp.join(experiments_root, 'ckpt')
    opt['path']['model_root'] = model_root
    mkdir(model_root)

    # results path
    results_root = opt['path'].get('results_root')
    if results_root is None:
        results_root = osp.join(experiments_root, 'results')
    opt['path']['results_root'] = results_root
    mkdir(results_root)

    # preprocess param root
    preprocess_root = opt['path'].get('preprocess_root')
    if preprocess_root is None:
        preprocess_root = osp.join(experiments_root, 'preprocess')
    opt['path']['preprocess_root'] = preprocess_root
    mkdir(preprocess_root)

    # inference param root
    inference_root = opt['path'].get('inference_root')
    if inference_root is None:
        inference_root = osp.join(experiments_root, 'inference_params')
    opt['path']['inference_root'] = inference_root
    mkdir(inference_root)

    # signal param root
    signal_root = opt['path'].get('signal_root')
    if signal_root is None:
        signal_root = osp.join(experiments_root, 'signal')
    opt['path']['signal_root'] = signal_root
    mkdir(signal_root)

    # log path
    opt['path']['log'] = experiments_root

    # copy option
    shutil.copy2(args.option, opt['path']['experiments_root'])

    return opt

