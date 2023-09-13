import glob
import argparse
import pandas as pd
import os
import pandas as pd
import sqlalchemy.types
import pymysql
from utils import create_pd_engine, create_index




def get_summary(config):
    csv_folder = os.path.join(config.res_path, 'signal')
    res_csv = glob.glob(csv_folder.rstrip('/') + '/*csv')
    res = []
    for r in res_csv:
        res.append(pd.read_csv(r))
    res = pd.concat(res).reset_index(drop=True)
    res = res[['ticker', 'date', 'time', 'signal', 'proba', 'up_bound', 'down_bound']]
    res.rename(columns={'signal': 'signal_{}'.format(config.label_name)}, inplace=True)
    basename = os.path.basename(config.res_path)
    res.to_csv(os.path.join(config.res_path, basename + '_sig.csv'))
    return res
def main(signal):
    engine = create_pd_engine('strategy')
    data_name = 'signal_zz800_{}_ml'.format((config.label_name))
    signal.to_sql( data_name, con=engine, index=False, if_exists='replace', chunksize=10000,
                   dtype={'ticker':sqlalchemy.types.VARCHAR(length=10),
                       'date':sqlalchemy.types.BIGINT,
                        'time': sqlalchemy.types.BIGINT,
                   })
    create_index('strategy', data_name, ['ticker', 'date', 'time'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='concat hs300 signal')
    parser.add_argument('--res_path', type=str, default='experiments/wind1_lgbm_alpha10.0_zscore2_pct5_5_class2_epoch200_balance2_300s', help="the path of csv results")
    parser.add_argument('--csv_name', type=str, default='summary', help="the path of final csv results")
    parser.add_argument('--label_name', type=str, default='300s', help="future return")
    config = parser.parse_args()

    signal = get_summary(config)
    main(signal)
