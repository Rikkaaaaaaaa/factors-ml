import multiprocessing as mp
import logging
import random
import os.path as osp
import shutil

from utils.misc import set_random_seed, ensure_path, mkdir
from dataset.sql_data import check_indus
from dataset import build_dataset
from utils.option import yaml_load
from utils.logger import get_root_logger, get_env_info
from utils.misc import Timer, time_str, get_time_str, exists_results


def init(args):
    global lock
    lock = args[0]

def train_pipeline(train_args):
    opt, test_month, indus_type = train_args
    # logger init
    logger_name = f"month{test_month}_indus{indus_type}"
    log_file = osp.join(opt['path']['log'], f"{logger_name}_{get_time_str()}.log")
    logger = get_root_logger(logger_name=logger_name, log_level=logging.INFO, log_file=log_file)

    # get data set from test month
    dataset = build_dataset(opt, test_month=test_month, indus_type=indus_type)
    dataset.load_data()
    if dataset.is_empty:
        return

    dataset.train_data.to_csv(f"{opt['path']['experiments_root']}/{test_month}/train_data_{test_month}_indus_{indus_type}.csv", index=False)
    dataset.test_data.to_csv(f"{opt['path']['experiments_root']}/{test_month}/test_data_{test_month}_indus_{indus_type}.csv",index=False)
    dataset.labels.to_csv(f"{opt['path']['experiments_root']}/{test_month}/ret_{test_month}_indus_{indus_type}.csv", index=False)


def gen_mp_args(opt):
    args = []
    for test_month in opt['dataset']['test_month']:
        industry = check_indus(opt, test_month)
        # industry = [2]
        for indus_type in industry:
            if not exists_results(opt, test_month, indus_type):
                args.append((opt, test_month, indus_type))
    return args


def parse_option(root_path = '../', option_path='../option/gen_factor/gen_factor_hs300_highprice.yaml'):
    if not osp.exists(option_path):
        raise FileExistsError(f"No such option file named", option_path)
    opt = yaml_load(option_path)
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

    # month path
    for test_month in opt['dataset']['test_month']:
        test_month_path = osp.join(experiments_root, str(test_month))
        mkdir(test_month_path)

    # log path
    log_root = opt['path'].get('log_root')
    if log_root is None:
        log_root = osp.join(experiments_root, 'log')
    opt['path']['log'] = log_root
    mkdir(log_root)
    # copy option
    shutil.copy2(option_path, opt['path']['experiments_root'])

    return opt


if __name__ == '__main__':
    option_path = '../option/gen_factor/gen_factor_no_std_for_rl_20240724.yaml'
    run_function = train_pipeline

    opt = parse_option(option_path=option_path)
    print(get_env_info())
    pool = mp.Pool(processes=opt['n_jobs'], )
    global_timer = Timer()
    args = gen_mp_args(opt)
    results = [pool.apply_async(run_function, (arg,)) for arg in args] # main function
    [result.get() for result in results]
    pool.close()
    pool.join()
    print("Task time is {}".format(time_str(global_timer.item())))
    # data = pd.read_csv('/share/batch4_factor/202401/test_data_202401_indus_6.csv')
    # print(len(data))

