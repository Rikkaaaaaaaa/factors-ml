LONG_TERM_BASE_FACTOR_15S = [
    'ma_close_ret_10', 'bulk_buy_sell_diff_15s', 'order_diff_10_15s',
    'ma_close_ret_5', 'ma_mid_ret_2_10', 'active_buy_sell_diff_15s',
    'mid_ret_15s', 'mkt_bulk_active_buy_sell_diff_15s', 'net_bid_amt_delta_15s',
    'indus_order_diff_1_15s', 'book_pressure_15s', 'ma_close_ret_1',
    'mkt_book_pressure_15s', 'ma_close_ret_2_10', 'mkt_net_bid_amt_delta_15s',
    'indus_bulk_active_buy_sell_diff_15s', 'close_ret_15s', 'book_pressure_delta_15s',
    'indus_close_ret_15s', 'ma_mid_ret_2_5', 'indus_mid_ret_15s',
    'indus_order_diff_10_15s', 'mkt_lower_ask_amt_15s', 'indus_active_buy_sell_diff_15s',
    'lower_ask_amt_15s', 'bulk_active_buy_sell_diff_15s', 'ma_close_ret_2',
    'indus_cancel_diff_10_15s', 'mkt_close_ret_15s', 'indus_book_pressure_15s',
    'mkt_active_buy_sell_diff_15s', 'ma_mid_ret_2', 'mid_mmt_route_5_5',
    'ma_mid_ret_5', 'mkt_higher_bid_amt_15s', 'indus_net_bid_amt_delta_15s',
    'order_diff_1_15s', 'mid_mmt_route_10_10', 'indus_book_pressure_delta_15s',
    'ma_close_ret_2_5', 'ma_mid_ret_10', 'mid_ret_skew_10',
    'mkt_order_diff_10_15s', 'indus_lower_ask_amt_15s', 'higher_bid_amt_15s',
    'indus_higher_bid_amt_15s', 'ma_mid_ret_1', 'cancel_diff_10_15s'
]

LONG_TERM_FACTOR_TABLE_15S = {
    'dfs://DDB_Factor_15s': ['BaseFokFactor']
}

LONG_TERM_FACTOR_GROUPS = {
    'long_term_base_factor_15s': LONG_TERM_BASE_FACTOR_15S,
}

LONG_TERM_FACTOR_TABLE_GROUPS = {
    'long_term_factor_table_15s': LONG_TERM_FACTOR_TABLE_15S,
}


def build_factor_name_long_term(name):
    factor_name = []
    if isinstance(name, list):
        for item in name:
            if item in LONG_TERM_FACTOR_GROUPS:
                factor_name.extend(LONG_TERM_FACTOR_GROUPS[item])
            else:
                factor_name.append(item)
        return factor_name
    if isinstance(name, str):
        if name in LONG_TERM_FACTOR_GROUPS:
            return LONG_TERM_FACTOR_GROUPS[name]
        return [name]
    return factor_name


def build_factor_table_long_term(name):
    if isinstance(name, str):
        name = [name]

    factor_table = {}
    if isinstance(name, list):
        for item in name:
            if item not in LONG_TERM_FACTOR_TABLE_GROUPS:
                raise KeyError(f'Unknown long-term factor table group: [{item}]')
            group_table = LONG_TERM_FACTOR_TABLE_GROUPS[item]
            for database, tables in group_table.items():
                factor_table.setdefault(database, [])
                factor_table[database].extend(tables)

    for database, tables in factor_table.items():
        factor_table[database] = list(dict.fromkeys(tables))

    return factor_table
