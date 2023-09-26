import multiprocessing as mp
import os.path as osp
import logging

from dataset.factor_dataset import FactorDataset
from dataset import check_indus
from model.lgbm_model import LgbmModel
from backtester import  BackTester
from utils.logger import get_root_logger, get_env_info
from utils.option import parse_options, dict2str
from utils.report import push_report
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
    #logger.info(get_env_info())
    #logger.info(dict2str(opt))

    dataset = FactorDataset(opt, test_month, indus_type, lock=lock)
    dataset.load_data()
    #
    # model = LgbmModel(opt, test_month, indus_type)
    # model.train(dataset.x_train, dataset.y_train)
    # model.save_ckpt()
    #
    # backtester = BackTester(opt, test_month, indus_type)
    # if opt['is_backtest']:
    #     backtester.backtest(dataset, model)
    # else:
    #     backtester.runtime(dataset, model)


def gen_mp_args(opt):
    args = []
    for month in opt['dataset']['backtest_month']:
        industry = check_indus(opt, month)
        for indus_type in industry:
            if not exists_results(opt, month, indus_type):
                args.append((opt, month, indus_type))
    return args

def main(root_path):
    lock = mp.Lock()
    init_args = [lock, ]

    opt = parse_options(root_path)
    args = gen_mp_args(opt)

    pool = mp.Pool(opt['n_jobs'], initializer=init, initargs=(init_args,))#
    global_timer =Timer()
    results = [pool.apply_async(train_pipeline, (arg,)) for arg in args]
    [result.get() for result in results]
    print("Task time is {}".format(time_str(global_timer.item())))

    # report
    push_report(opt)

if __name__ == '__main__':

    root_path = './'
    main(root_path)