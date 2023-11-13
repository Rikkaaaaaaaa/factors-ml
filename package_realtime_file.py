import glob
from os import makedirs
import os.path as osp
import shutil

import pandas as pd


def push_realtime_files(root_path='experiments', res_path='./', test_month=202307):
    pool_name = 'zz800'
    highprice_folder = glob.glob(f'{root_path}/*highprice*')
    lowprice_folder = glob.glob(f'{root_path}/*lowprice*')
    folders = ['15s', '60s', '120s', '300s']
    saved_folders = ['ckpt', 'inference_params', 'preprocess_params']

    for window in folders:
        window_path = osp.join(res_path, 'lgbm_data', window)
        makedirs(window_path)
        for high_folder in highprice_folder:
            if window in high_folder and pool_name in high_folder:
                for folder in saved_folders:
                    src = osp.join(high_folder, str(test_month), folder)
                    dst = osp.join(window_path, folder)

                    if not osp.exists(dst):
                        makedirs(dst)
                    # 处理preprocess_params文件夹中的文件，增加high/lowprice后缀
                    if folder == 'preprocess_params':
                        preprocess_params = []
                        for preprocess_csv in glob.glob(f'{src}/preprocess_params*'):
                            preprocess_params.append(pd.read_csv(preprocess_csv))
                        preprocess_params = pd.concat(preprocess_params, ignore_index=True)
                        dst = osp.join(dst, 'preprocess_params_highprice.csv')
                        preprocess_params.to_csv(dst)

                    # others: copy all files to new folder
                    else:
                        [shutil.copy2(s, dst) for s in glob.glob(src.rstrip('/')+'/*')]

        for low_folder in lowprice_folder:
            if window in low_folder and pool_name in low_folder:
                for f in saved_folders:
                    src = osp.join(low_folder, str(test_month), f)
                    dst = osp.join(window_path, f)
                    if not osp.exists(dst):
                        makedirs(dst)

                    # 处理preprocess_params文件夹中的文件，增加high/lowprice后缀
                    if f == 'preprocess_params':
                        preprocess_params = []
                        for preprocess_csv in glob.glob(f'{src}/preprocess_params*'):
                            preprocess_params.append(pd.read_csv(preprocess_csv))
                        preprocess_params = pd.concat(preprocess_params, ignore_index=True)
                        dst = osp.join(dst, 'preprocess_params_lowprice.csv')
                        preprocess_params.to_csv(dst)
                    else:
                        [shutil.copy2(s, dst) for s in glob.glob(src.rstrip('/') + '/*')]



if __name__ == '__main__':
    push_realtime_files()