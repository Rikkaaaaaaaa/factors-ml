import numpy as np
import pandas as pd
import os.path as osp

from utils import cx_read_sql


def check_indus(opt, first_month):
    pools = opt['dataset']['pool_name']
    indus_class = opt['dataset']['indus_class']
    indus_list = []
    if opt['dataset']['is_highprice']:
        for pool in pools:
            indus_table = cx_read_sql('select distinct {} from static_data_industry_{}_history where test_month={}'.format(
                                        indus_class, pool, first_month))

            indus_list.extend(list(indus_table[indus_class]))
    # default class num of low price is zero
    else: indus_list = [0]

    return set(indus_list)

def write_factor_sql(test_month, x_test, ):

    table_name = f'train_factor_ml_{test_month}'





