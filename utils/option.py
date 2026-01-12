import yaml
import os
from collections import OrderedDict
import random
import argparse
import os.path as osp
import shutil

from utils.misc import set_random_seed, ensure_path, mkdir, deep_merge_with_log

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


def parse_options(args, ensure=True, yaml_path=None, opt_manager=None):
    # parse yml to dict
    if not yaml_path:
        yaml_path = args.option
    if not osp.exists(yaml_path):
        raise FileExistsError(f"No such option file named", yaml_path)
    opt = yaml_load(yaml_path)

    # parse argparser
    if not opt.get('is_realtime'):
        opt['is_realtime'] = args.is_realtime
    opt['debug'] = args.debug
    root_path = args.root_path

    # get mode param
    opt['mode'] = opt.get('mode', 'train')
    if opt['is_realtime']:
        opt['mode'] = 'rt'

    # overwrite option with option manager
    if not opt_manager is None:
        # opt['dataset']['test_month'] = opt_manager['test_month']
        # opt['dataset']['pool_name'] = opt_manager['pool_name']
        # opt['base_name'] = opt_manager['base_name']
        # opt['mode'] = opt_manager['mode']
        merged_opt, changes = deep_merge_with_log(opt, opt_manager)
        print(f"[option_{opt['dataset']['ret_name']}] Suscessfully update option with option manager:")
        for key, old_val, new_val in changes:
            print(f"  {key}: {old_val} -> {new_val}")
        opt = merged_opt

    # random seed
    seed = opt.get('manual_seed')
    if seed is None:
        seed = random.randint(1, 10000)
        opt['manual_seed'] = seed
    set_random_seed(seed)

    # save path init
    if not opt.get('path'):
        opt['path'] = dict()
    # root_path
        opt['path']['root_path'] = root_path

    # base name
    if opt.get('base_name'):
        exp_folder_name = f"{opt['base_name']}_{opt['dataset']['ret_name']}"
        opt['name'] = exp_folder_name
    else:
        # adjust for old option file with param "name"
        if opt.get("name"):
            exp_folder_name = opt['name']
        else:
            raise ValueError('option file need param named [base_name]!')
    print(f"Running {opt['mode']} mode in {opt['name']}")

    # experiment path
    experiments_root = opt['path'].get('experiments_root')
    if experiments_root is None:
        # eval experiments path
        if opt['mode'] == 'eval':
            experimens_root_path = 'eval_experiments'
        else:
            experimens_root_path = 'experiments'
        # base name folder
        if opt.get('base_name'):
            experiments_root = osp.join(root_path, experimens_root_path, opt['base_name'], exp_folder_name)
        else:
            experiments_root = osp.join(root_path, experimens_root_path, exp_folder_name)
        opt['path']['experiments_root'] = experiments_root
    print(f"Files will be save at experiment folder path [{experiments_root}]")

    # ensure path
    if opt['mode'] != 'eval':
        opt['new_session_flag'] = ensure_path(experiments_root, ensure)     # opt['new_session_flag']=True if input "y"

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

    if opt['mode'] == 'eval':
        # define pretrain param path
        # base name folder
        if opt.get('base_name'):
            pretrain_root = osp.join(root_path, 'experiments', opt['base_name'], exp_folder_name)
        else:
            pretrain_root = osp.join(root_path, 'experiments', exp_folder_name)
        print(f"Loading pretrained model from {pretrain_root}")

        opt['path']['pretrain_root'] = pretrain_root
        opt['path']['pretrain_model_path'] = dict()
        opt['path']['pretrain_preprocess_path'] = dict()
        opt['path']['pretrain_inference_path'] = dict()
        for test_month in opt['dataset']['test_month']:
            model_path = osp.join(pretrain_root, str(test_month), 'ckpt')
            opt['path']['pretrain_model_path'][test_month] = model_path

            preprocess_path = osp.join(pretrain_root, str(test_month), 'preprocess_params')
            opt['path']['pretrain_preprocess_path'][test_month] = preprocess_path

            inference_path = osp.join(pretrain_root, str(test_month), 'inference_params')
            opt['path']['pretrain_inference_path'][test_month] = inference_path


    # log path
    log_root = opt['path'].get('log_root')
    if log_root is None:
        log_root = osp.join(experiments_root, 'log')
    opt['path']['log'] = log_root
    mkdir(log_root)

    # copy option
    shutil.copy2(yaml_path, opt['path']['experiments_root'])

    return opt
def parse_opt_manager(args, ensure=True, yaml_path=None):
    # parse yml to dict
    if not yaml_path:
        yaml_path = args.option
    if not osp.exists(yaml_path):
        raise FileExistsError(f"No such option file named", args.option)
    opt_manager = yaml_load(yaml_path)

    # parse argparser
    if not opt_manager.get('is_realtime'):
        opt_manager['is_realtime'] = args.is_realtime
    opt_manager['debug'] = args.debug
    root_path = args.root_path

    # get mode param
    opt_manager['mode'] = opt_manager.get('mode', 'train')
    if opt_manager['is_realtime']:
        opt_manager['mode'] = 'rt'
    print(f"[option manager] option manager [{opt_manager['base_name']} has been created]")
    print(f"[option manager] Running {opt_manager['mode']} mode with option manager")
    print(f"[option manager] Return windows include [{opt_manager['ret_names']}]")

    # random seed
    seed = opt_manager.get('manual_seed')
    if seed is None:
        seed = random.randint(1, 10000)
        opt_manager['manual_seed'] = seed
    set_random_seed(seed)

    # experiment path
    experiments_root = osp.join(root_path, 'experiments')
    # eval experiments path
    if opt_manager['mode'] == 'eval':
        experiments_root = osp.join(root_path, 'eval_experiments')
    experiments_root = osp.join(experiments_root, opt_manager['base_name'])
    opt_manager['experiments_root'] = experiments_root

    # ensure experiments_root
    if opt_manager['mode'] != 'eval':
        ensure_path(experiments_root)
    print(f"[option manager] Suscessfully copy all yaml files to {experiments_root}")

    # sub options init
    opt_manager['opt_folder_path'] = os.path.dirname(args.option)
    sub_options = {}
    # update multi-return option, such as xxx_hs300_highprice_lgbm_15s.yaml
    for ret_name in opt_manager['ret_names']:
        sub_opt_path = os.path.join(opt_manager['opt_folder_path'], f"{opt_manager['base_name']}_{ret_name}.yaml")
        sub_options[ret_name] = parse_options(args, ensure=False, yaml_path=sub_opt_path, opt_manager=opt_manager)
    opt_manager['sub_options'] = sub_options

    # copy opt_manager
    shutil.copy2(yaml_path, opt_manager['experiments_root'])

    return opt_manager