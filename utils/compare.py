import pandas as pd
import utils
import multiprocessing as mp

def single_process(indus_type=2):
    timer = utils.Timer()
    factor_path = '../data/wind11/' + 'factor_202306_indus_{}.csv'.format(indus_type)
    data = pd.read_csv(factor_path)
    print('indus_type ', indus_type, utils.time_str(timer.t()))

def multi_process(n_jobs=10):
    timer = utils.Timer()
    pool = mp.Pool(processes=n_jobs)
    args = [i for i in range(10)]
    pool.map(single_process, args)
    print('multi process ', utils.time_str(timer.t()))

if __name__ == '__main__':
    #single_process()
    multi_process()