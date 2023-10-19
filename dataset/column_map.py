def get_col_dict_from_list(col_name_list):
    return {col_name_list[i]: i for i in range(len(col_name_list))}


kline_from_tick_col = {
    'mid': 0, 'ask_size': 1, 'bid_size': 2
}

kline_from_trade_col = {
    'close': 0, 'volume': 1, 'amount': 2, 'active_buy_amount': 3, 'active_sell_amount': 4,
}

kline_from_order_col_list = ['higher_bid_amt', 'lower_ask_amt', 'bid_amt_delta', 'ask_amt_delta', 'bid1_add_volume',
                             'ask1_add_volume', 'bid1_trade_volume', 'ask1_trade_volume', 'bid1_cancel_volume',
                             'ask1_cancel_volume', 'bid10_add_volume', 'ask10_add_volume', 'bid10_trade_volume',
                             'ask10_trade_volume', 'bid10_cancel_volume', 'ask10_cancel_volume']
kline_from_order_col = get_col_dict_from_list(kline_from_order_col_list)

last_tick_col = {
    'bid1': 0, 'ask1': 1, 'bid1_add_amt': 2, 'ask1_add_amt': 3
}

data_col = {
    'time': 0, 'mid': 1, 'ask_size': 2, 'bid_size': 3, 'close': 4, 'volume': 5, 'amount': 6, 'active_buy_amount': 7,
    'active_sell_amount': 8, 'bulk_buy_amt': 9, 'bulk_active_buy_amt': 10, 'bulk_sell_amt': 11, 'bulk_active_sell_amt': 12,
    'higher_bid_amt': 13, 'lower_ask_amt': 14, 'bid_amt_delta': 15, 'ask_amt_delta': 16, 'bid1_add_volume': 17,
    'ask1_add_volume': 18, 'bid1_trade_volume': 19, 'ask1_trade_volume': 20, 'bid1_cancel_volume': 21,
    'ask1_cancel_volume': 22, 'bid10_add_volume': 23, 'ask10_add_volume': 24, 'bid10_trade_volume': 25,
    'ask10_trade_volume': 26, 'bid10_cancel_volume': 27, 'ask10_cancel_volume': 28
}

factor_list = [
    'time', 'close_ret_15s', 'close_ret_30s', 'close_ret_60s', 'ma_close_ret_1', 'ma_close_ret_2', 'ma_close_ret_5',
    'ma_close_ret_10', 'ma_close_ret_2_5', 'ma_close_ret_2_10', 'mid_ret_15s', 'mid_ret_30s', 'mid_ret_60s',
    'ma_mid_ret_1', 'ma_mid_ret_2', 'ma_mid_ret_5', 'ma_mid_ret_10', 'ma_mid_ret_2_5', 'ma_mid_ret_2_10',
    'mid_mmt_route_5_5', 'mid_mmt_route_10_10', 'mid_ret_skew_10', 'book_pressure_15s', 'book_pressure_30s',
    'book_pressure_delta_15s', 'active_buy_sell_diff_15s', 'active_buy_sell_diff_30s', 'bulk_buy_sell_diff_15s',
    'bulk_buy_sell_diff_30s', 'bulk_buy_sell_diff_60s', 'bulk_active_buy_sell_diff_15s', 'bulk_active_buy_sell_diff_30s',
    'bulk_active_buy_sell_diff_60s', 'higher_bid_amt_15s', 'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s',
    'lower_ask_amt_30s', 'lower_ask_amt_60s', 'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s', 'net_bid_amt_delta_60s',
    'order_diff1_15s', 'order_diff10_15s', 'cancel_diff10_15s'
]
factor_col = {factor_list[i]: i for i in range(len(factor_list))}

indus_factor_list = ['close_ret_15s', 'close_ret_30s', 'close_ret_60s', 'mid_ret_15s', 'mid_ret_30s', 'mid_ret_60s',
                     'book_pressure_15s', 'book_pressure_delta_15s', 'active_buy_sell_diff_15s', 'active_buy_sell_diff_30s',
                     'bulk_active_buy_sell_diff_15s', 'bulk_active_buy_sell_diff_30s', 'bulk_active_buy_sell_diff_60s',
                     'higher_bid_amt_15s', 'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s',
                     'lower_ask_amt_30s', 'lower_ask_amt_60s', 'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s',
                     'net_bid_amt_delta_60s', 'order_diff1_15s', 'order_diff10_15s', 'cancel_diff10_15s']
indus_factor_col = {indus_factor_list[i]: i for i in range(len(indus_factor_list))}
indus_factor_name = ['indus_'+factor for factor in indus_factor_list]

mkt_factor_list = ['close_ret_15s', 'book_pressure_15s', 'active_buy_sell_diff_15s', 'bulk_active_buy_sell_diff_15s',
                   'higher_bid_amt_15s', 'lower_ask_amt_15s', 'net_bid_amt_delta_15s', 'order_diff10_15s']
mkt_factor_col = {mkt_factor_list[i]: i for i in range(len(mkt_factor_list))}
mkt_factor_name = ['mkt_'+factor for factor in mkt_factor_list]


log_factor_list = ['book_pressure_15s', 'book_pressure_30s', 'book_pressure_delta_15s', 'higher_bid_amt_15s',
                   'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s', 'lower_ask_amt_30s', 'lower_ask_amt_60s',
                   'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s', 'net_bid_amt_delta_60s', 'indus_book_pressure_15s',
                   'indus_book_pressure_delta_15s', 'indus_higher_bid_amt_15s', 'indus_higher_bid_amt_30s', 'indus_higher_bid_amt_60s',
                   'indus_lower_ask_amt_15s', 'indus_lower_ask_amt_30s', 'indus_lower_ask_amt_60s', 'indus_net_bid_amt_delta_15s',
                   'indus_net_bid_amt_delta_30s', 'indus_net_bid_amt_delta_60s', 'mkt_book_pressure_15s', 'mkt_higher_bid_amt_15s',
                   'mkt_lower_ask_amt_15s', 'mkt_net_bid_amt_delta_15s']
factor_all = factor_list[1:] + indus_factor_name + mkt_factor_name
log_factor_index = [factor_all.index(factor) for factor in log_factor_list]
