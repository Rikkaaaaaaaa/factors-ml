import seaborn as sns
import matplotlib.pyplot as plt
from utils.sql_query import get_return, get_ticker_list, get_indus_list


def plot_dist():
    pool_name = 'hs300'
    price_name = 'highprice'
    test_month = 202301
    ret_name = '15s'
    indus_class = 'wind1'
    # tickers = get_ticker_list(pool_name, price_name, test_month)
    # ret = get_return(ret_name, test_month, tickers)
    # print(len(tickers), len(ret))
    plt.figure(figsize=(25,20))
    indus_list = get_indus_list(pool_name, test_month, indus_class)
    for indus_type in indus_list:
        plt.subplot(4, 3, indus_type)
        tickers = get_ticker_list(pool_name, price_name, test_month, indus_class, indus_type)
        ret = get_return(ret_name, test_month, tickers)[f'ret_{ret_name}']
        sns.histplot(ret, bins=100, kde=True)
        median = ret.median()
        plt.axvline(median, color='k', linestyle='--', linewidth=2)
        plt.xlim([-0.01, 0.01])
        plt.title(f'indus_{indus_type} {ret_name} dist, {median:.5f}')
        plt.xlabel('return/bps')
        plt.ylabel('frequency')

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    plot_dist()