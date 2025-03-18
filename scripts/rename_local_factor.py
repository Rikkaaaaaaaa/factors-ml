import pandas as pd
import glob
import os.path as osp
import os
import multiprocessing as mp

save_root = '../'
local_dataset_path = '../experiments/gen_factor_hs300_highprice'
test_month = [202304, 202305, 202306, 202307, 202308, 202309, 202310, 202311]

def init_args():
    args = []
    for month in test_month:
        for data_path in glob.glob(f"{local_dataset_path}/{month}/*data*indus*"):
            args.append((data_path, month))

    return args

def rename_df(args):
    data_path, month = args
    if not osp.exists(f"{save_root}/local_factor/{month}"):
        os.makedirs(f"{save_root}/local_factor/{month}")
    local_factor_path = osp.join(f"{save_root}/local_factor/{month}/{data_path.split('/')[-1]}")
    if osp.exists(local_factor_path):
        return
    data = pd.read_csv(data_path, index_col=0)
    factor_name = data.drop(['ticker', 'date', 'time'], axis=1).columns
    factor_num = len(factor_name)
    factor_map = {}
    for i in range(factor_num):
        factor_map.update({factor_name[i]: f'alpha_{i}'})

    data.rename(columns=factor_map, inplace=True)
    print(f'file has been saved at {local_factor_path}')
    data.to_csv(local_factor_path)


def gen_factor_map():
    for month in test_month:
        for data_path in glob.glob(f"{local_dataset_path}/{month}/*data*indus_5*"):
            data = pd.read_csv(data_path, index_col=0)
            factor_name = data.drop(['ticker', 'date', 'time'], axis=1).columns

            factor_df = pd.DataFrame()
            factor_df['factor_name'] = factor_name
            factor_df['transform_name'] = [ f'alpha_{i}' for i in range(len(factor_name))]
            save_path = f"{save_root}/local_factor/real_factor_map.csv"
            print(save_path)
            factor_df.to_csv(save_path, index=False)

            return

if __name__ == '__main__':
    pool = mp.Pool(processes=1, )

    # args = init_args()
    # results = [pool.apply_async(rename_df, (arg,)) for arg in args]
    # [result.get() for result in results]
    # pool.close()
    # pool.join()

    gen_factor_map()