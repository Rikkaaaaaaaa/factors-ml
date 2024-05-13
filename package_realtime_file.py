import glob
from os import makedirs
import os.path as osp
import shutil

import pandas as pd


def push_realtime_files(root_path='experiments', res_name='lgbm_data', res_folder_path='./', test_month=202307):
    pool_name = 'hs300'
    highprice_folder = glob.glob(f'{root_path}/batch4_factor_no_fok_hs300_highprice_lgbm*')
    lowprice_folder = glob.glob(f'{root_path}/batch4_factor_no_fok_hs300_lowprice_lgbm*')
    folders = ['15s', '60s', '120s', '300s']
    saved_folders = ['ckpt', 'inference_params', 'preprocess_params']

    for window in folders:
        window_path = osp.join(res_folder_path, res_name, window)
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
                        clip_params = []
                        std_params = []

                        for clip_csv in glob.glob(f'{src}/clip_*.csv'):
                            clip_params.append(pd.read_csv(clip_csv))
                        clip_params = pd.concat(clip_params, ignore_index=True)
                        clip_path = osp.join(dst, 'clip_params_highprice.csv')
                        clip_params.to_csv(clip_path, index=False)

                        for std_csv in glob.glob(f'{src}/std_*.csv'):
                            std_params.append(pd.read_csv(std_csv))
                        std_params = pd.concat(std_params, ignore_index=True)
                        std_path = osp.join(dst, 'std_params_highprice.csv')
                        std_params.to_csv(std_path, index=False)

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
                        clip_params = []
                        std_params = []
                        for clip_csv in glob.glob(f'{src}/clip*'):
                            clip_params.append(pd.read_csv(clip_csv))
                        clip_params = pd.concat(clip_params, ignore_index=True)
                        clip_path = osp.join(dst, 'clip_params_lowprice.csv')
                        clip_params.to_csv(clip_path, index=False)

                        for std_csv in glob.glob(f'{src}/std*'):
                            std_params.append(pd.read_csv(std_csv))
                        std_params = pd.concat(std_params, ignore_index=True)
                        std_path = osp.join(dst, 'std_params_lowprice.csv')
                        std_params.to_csv(std_path, index=False)

                    else:
                        [shutil.copy2(s, dst) for s in glob.glob(src.rstrip('/') + '/*')]



if __name__ == '__main__':
    push_realtime_files(test_month=202401)