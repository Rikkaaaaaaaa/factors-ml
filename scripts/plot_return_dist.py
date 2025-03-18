import sys

import numpy as np
import pandas as pd

sys.path.append('../')
sys.path.append('./')
import seaborn as sns
import matplotlib.pyplot as plt
from utils.sql_query import get_return, get_ticker_list, get_indus_list


def plot_dist():
    pool_name = 'hs300'
    price_name = 'highprice'
    test_month = [202308,202309, 202310, 202311]
    ticker_month  = 202307
    ret_name = '60s'
    indus_class = 'wind1'
    base_alpha = 5e-4
    # tickers = get_ticker_list(pool_name, price_name, test_month)
    # ret = get_return(ret_name, test_month, tickers)
    # print(len(tickers), len(ret))

    indus_list = get_indus_list(pool_name, ticker_month, indus_class)
    quantile_num = [20, 30, 40, 50, 60, 70, 80]
    quantile_ret = pd.DataFrame(columns=quantile_num, index=sorted(indus_list))
    plt.figure(figsize=(25, 20))
    for indus_type in sorted(indus_list):
        # plot dist
        plt.subplot(4, 3, indus_type)
        tickers = get_ticker_list(pool_name, price_name, ticker_month, indus_class, indus_type)
        ret = []
        for month in test_month:
            _ret = get_return(ret_name, month, tickers)[f'ret_{ret_name}']
            ret.append(_ret.dropna().values)
        ret = np.concatenate(ret, axis=0)

        up_ret = ret[ret>=0]
        down_ret = ret[ret<=0]
        up_alpha_quantile = 1 - len(ret[ret >= base_alpha]) / len(ret)
        down_alpha_quantile =  len(ret[ret <= -1*base_alpha]) / len(ret)

        # compute realized vol
        rv = np.sqrt(np.sum(ret**2))

        #print(max(ret), min(ret))
        sns.histplot(ret, bins=200, kde=True)
        quantiles = np.percentile(ret, quantile_num)
        for quantile in [quantiles[0], quantiles[-1]]:
            plt.axvline(quantile, color='k', linestyle='--')
            plt.text(quantile, plt.ylim()[1]*0.9, f'{quantile*10000:.2f}',color='red', horizontalalignment='left')

        if ret_name == '15s':
            plt.xlim([-0.002, 0.002])
        else:
            plt.xlim([-0.005, 0.005])
        plt.title(f'indus_{indus_type} {ret_name} dist, rv is {rv:.2f} and quantile of {base_alpha} is [{down_alpha_quantile:.2f}, {up_alpha_quantile:.2f}] ')
        plt.xlabel('return/bps')
        plt.ylabel('frequency')

        # record quantile ret
        quantile_ret.loc[indus_type, :] = np.round(quantiles*1e5, 2)
        # quantile_ret.loc[indus_type, 'up_alpha_quantile'] = np.round(up_alpha_quantile)
        # quantile_ret.loc[indus_type, 'down_alpha_quantile'] = np.round(down_alpha_quantile)

    plt.tight_layout()
    #plt.show()
    plt.savefig(f"{pool_name}_{price_name}__{ret_name}_dist.png")
    quantile_ret.to_csv(f"{pool_name}_{price_name}_{ret_name}_dist.csv")

if __name__ == '__main__':
    plot_dist()