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


def parse_options(root_path, ensure=True, yaml_path=None):
    if yaml_path:
        parser = argparse.ArgumentParser()
        parser.add_argument('-option', type=str, default=os.path.join(root_path, yaml_path), help='Path to option YAML file.')
        parser.add_argument('-is_realtime', action='store_true', help='Whether the phase is backtesting or realtime')
        parser.add_argument('-debug', action='store_true',
                            help='Whether to use debug mode')  # it'll contain ticker num <= 10
        args = parser.parse_args()
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('-option', type=str, default='option/ddb_null_factor_reg/ddb_null_factor_reg_hs300_highprice_lgbm_15s.yaml', help='Path to option YAML file.')
        parser.add_argument('-is_realtime', action='store_true', help='Whether the phase is backtesting or realtime')
        parser.add_argument('-debug', action='store_true', help='Whether to use debug mode') # it'll contain ticker num <= 10
        args = parser.parse_args()

    # parse yml to dict
    if not osp.exists(args.option):
        raise FileExistsError(f"No such option file named", args.option)
    opt = yaml_load(args.option)

    # parse cmd flag
    if not opt.get('is_realtime'):
        opt['is_realtime'] = args.is_realtime
    opt['debug'] = args.debug

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
        # eval experiments path
        if  opt['eval_rt']:
            experiments_root = osp.join(root_path, 'eval_experiments')
    experiments_root = osp.join(experiments_root, opt['name'])
    opt['path']['experiments_root'] = experiments_root
    if ensure:
        ensure_path(experiments_root)


    # saving path
    opt['path']['model_path'] = dict()
    opt['path']['results_path'] = dict()
    opt['path']['preprocess_path'] = dict()
    opt['path']['inference_path'] = dict()
    opt['path']['signal_path'] = dict()
    if opt['train'].get('save_proba'):
        opt['path']['train_signal_path'] = dict()
    opt['path']['selection_path'] = dict()
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

        if opt['train'].get('save_proba'):
            train_signal_path = osp.join(experiments_root, str(test_month), 'train_signal')
            opt['path']['train_signal_path'][test_month] = train_signal_path
            mkdir(train_signal_path)

        if opt.get('feature_selector'):
            selection_path = osp.join(opt['path']['experiments_root'], str(test_month), 'factor_selection')
            opt['path']['selection_path'][test_month] = selection_path
            if not os.path.exists(selection_path):
                os.makedirs(selection_path)


    # log path
    log_root = opt['path'].get('log_root')
    if log_root is None:
        log_root = osp.join(experiments_root, 'log')
    opt['path']['log'] = log_root
    mkdir(log_root)

    # copy option
    shutil.copy2(args.option, opt['path']['experiments_root'])

    return opt, args

