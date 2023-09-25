import numpy as np
import pandas as pd
import os.path as osp

from utils.mysql import cx_read_sql


def check_indus(opt, test_month):
    pools = opt['dataset']['pool_name']
    indus_class = opt['dataset']['indus_class']
    indus_list = []
    for pool in pools:
        indus_table = cx_read_sql('select distinct {} from static_data_industry_{}_history where  test_month={}'.format(
                                    indus_class, pool, test_month))

        indus_list.extend(list(indus_table[indus_class]))

    return set(indus_list)

