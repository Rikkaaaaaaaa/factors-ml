import multiprocessing as mp

import utils
from dataset.factor_dataset import FactorDataset
from dataset import check_indus
from model.lgbm_model import LgbmModel
from backtester import  BackTester
from utils.option import parse_options
from utils.report import push_report



def init(args):
    global lock
    lock = args[0]

def train_pipeline(train_args):
    opt, test_month, indus_type = train_args
    dataset = FactorDataset(opt, test_month, indus_type, lock=lock)
    dataset.load_data()

    model = LgbmModel(opt, test_month, indus_type)
    model.train(dataset.x_train, dataset.y_train)
    model.save_ckpt()

    backtester = BackTester(opt, test_month, indus_type)
    if opt['is_backtest']:
        backtester.backtest(dataset, model)
    else:
        backtester.runtime(dataset, model)



def gen_mp_args(opt):
    args = []
    for month in opt['dataset']['backtest_month']:
        industry = check_indus(opt, month)
        for indus_type in industry:
            args.append((opt, month, indus_type))
    return args

def main(root_path):
    lock = mp.Lock()
    init_args = [lock, ]

    opt = parse_options(root_path)
    args = gen_mp_args(opt)

    pool = mp.Pool(opt['n_jobs'], initializer=init, initargs=(init_args,))#
    global_timer = utils.Timer()
    results = [pool.apply_async(train_pipeline, (arg,)) for arg in args]
    [result.get() for result in results]
    print("Task time is {}".format(utils.time_str(global_timer.item())))

    # report
    push_report(opt)

if __name__ == '__main__':

    root_path = './'
    main(root_path)