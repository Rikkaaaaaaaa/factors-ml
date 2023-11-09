import utils


def get_db_list():
    '''
    获取所有的数据库名称
    '''
    db_list = utils.cx_read_sql('select table_schema  from information_schema.tables group by table_schema')
    db_list = list(db_list['TABLE_SCHEMA'])
    db_list.remove('information_schema')
    return db_list


def get_table_name(data_base):
    '''
    获取db中以factor结尾的表格名称
    '''
    table_names = utils.cx_read_sql(
        'select table_name from information_schema.tables  where table_schema="{}"'.format(data_base),
        database=data_base)
    table_names = table_names['TABLE_NAME']
    table_names = [tn for tn in table_names if tn.startswith('factor')]
    return table_names


def get_factor_list(data_base, table_name):
    '''
    获取表中所有因子名称
    '''
    idx_cols = ['ticker', 'date', 'time', 'close']
    query = 'select COLUMN_NAME from information_schema.columns where table_schema="{}" and table_name="{}"  order by ORDINAL_POSITION'.format(
        data_base, table_name)
    factor_names = list(utils.cx_read_sql(query, data_base)['COLUMN_NAME'])
    #print(factor_names)
    [factor_names.remove(col) for col in idx_cols if col in factor_names]
    return factor_names


if __name__ == '__main__':
    factor1 = get_factor_list('strategy', 'factor_202301')
    print(factor1)
    factor2 = get_factor_list('factor_test', 'factor_202301')
    print(factor2)
    factor3 = get_factor_list('factor_test', 'batch3_factor_202301')
    print(factor3)
    factor3 = get_factor_list('factor_test', 'fok_factor_202301')
    print(factor3)
    factor4 = get_factor_list('factor_test', 'all_factor_202301')
    print(factor4)


