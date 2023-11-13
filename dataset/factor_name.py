

# all factor names
__all__ = [ # factor names
            'base_factor',
           'ofl_factor',
           'fok_factor',
            'slope_factor',
           # factor collections
           'batch2_factor',
           # factors need to be preprocessed
           'log_factor' ]

factor_list = ['time', 'close_ret_15s', 'close_ret_30s', 'close_ret_60s', 'ma_close_ret_1', 'ma_close_ret_2', 'ma_close_ret_5',
                'ma_close_ret_10', 'ma_close_ret_2_5', 'ma_close_ret_2_10', 'mid_ret_15s', 'mid_ret_30s', 'mid_ret_60s',
                'ma_mid_ret_1', 'ma_mid_ret_2', 'ma_mid_ret_5', 'ma_mid_ret_10', 'ma_mid_ret_2_5', 'ma_mid_ret_2_10',
                'mid_mmt_route_5_5', 'mid_mmt_route_10_10', 'mid_ret_skew_10', 'book_pressure_15s', 'book_pressure_30s',
                'book_pressure_delta_15s', 'active_buy_sell_diff_15s', 'active_buy_sell_diff_30s', 'bulk_buy_sell_diff_15s',
                'bulk_buy_sell_diff_30s', 'bulk_buy_sell_diff_60s', 'bulk_active_buy_sell_diff_15s', 'bulk_active_buy_sell_diff_30s',
                'bulk_active_buy_sell_diff_60s', 'higher_bid_amt_15s', 'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s',
                'lower_ask_amt_30s', 'lower_ask_amt_60s', 'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s', 'net_bid_amt_delta_60s',
                'order_diff1_15s', 'order_diff10_15s', 'cancel_diff10_15s']

indus_factor_list = ['close_ret_15s', 'close_ret_30s', 'close_ret_60s', 'mid_ret_15s', 'mid_ret_30s', 'mid_ret_60s',
                     'book_pressure_15s', 'book_pressure_delta_15s', 'active_buy_sell_diff_15s', 'active_buy_sell_diff_30s',
                     'bulk_active_buy_sell_diff_15s', 'bulk_active_buy_sell_diff_30s', 'bulk_active_buy_sell_diff_60s',
                     'higher_bid_amt_15s', 'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s',
                     'lower_ask_amt_30s', 'lower_ask_amt_60s', 'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s',
                     'net_bid_amt_delta_60s', 'order_diff1_15s', 'order_diff10_15s', 'cancel_diff10_15s']

indus_factor_name = ['indus_'+factor for factor in indus_factor_list]

mkt_factor_list = ['close_ret_15s', 'book_pressure_15s', 'active_buy_sell_diff_15s', 'bulk_active_buy_sell_diff_15s',
                   'higher_bid_amt_15s', 'lower_ask_amt_15s', 'net_bid_amt_delta_15s', 'order_diff10_15s']

mkt_factor_name = ['mkt_'+factor for factor in mkt_factor_list]

# base factor
base_factor = factor_list[1:] + indus_factor_name + mkt_factor_name


# orderflow factor
ofl_factor =    ['ask1_ofl_std_3s', 'ask1_ofl_std_6s', 'ask1_ofl_std_9s', 'ask1_ofl_std_15s', 'ask1_ofl_std_30s',
                 'bid1_ofl_std_3s', 'bid1_ofl_std_6s', 'bid1_ofl_std_9s', 'bid1_ofl_std_15s', 'bid1_ofl_std_30s',
                 'ofl1_std_3s', 'ofl1_std_6s', 'ofl1_std_9s', 'ofl1_std_15s', 'ofl1_std_30s', 'ofl1_std_45s', 'ofl1_std_min',
                 'ask1_order_dst_3s', 'ask2_order_dst_3s', 'ask3_order_dst_3s',
                 'ask1_order_dst_6s', 'ask2_order_dst_6s', 'ask3_order_dst_6s',
                 'ask1_order_dst_15s', 'ask2_order_dst_15s', 'ask3_order_dst_15s',
                 'ask1_order_dst_min', 'ask2_order_dst_min', 'ask3_order_dst_min',
                 'bid1_order_dst_3s', 'bid2_order_dst_3s', 'bid3_order_dst_3s',
                 'bid1_order_dst_6s', 'bid2_order_dst_6s', 'bid3_order_dst_6s',
                 'bid1_order_dst_15s', 'bid2_order_dst_15s', 'bid3_order_dst_15s',
                 'bid1_order_dst_min', 'bid2_order_dst_min', 'bid3_order_dst_min',
                 'depth_im1_3s', 'depth_im2_3s', 'depth_im3_3s', 'depth_im1_6s', 'depth_im2_6s', 'depth_im3_6s',
                 'depth_im1_15s', 'depth_im2_15s', 'depth_im3_15s', 'depth_im1_30s', 'depth_im2_30s', 'depth_im3_30s',
                 'depth_im1_min', 'depth_im2_min', 'depth_im3_min',
                 'height_im3_3s', 'height_im2_3s', 'height_im1_3s',
                 'press_3s', 'press_6s', 'press_9s', 'press_15s', 'press_30s', 'press_min']
# fok factor
fok_factor = ['fok_0.5s_9s', 'fok_0.5s_15s', 'fok_0.5s_30s', 'fok_0.5s_60s', 'fok_0.5s_120s', 'fok_0.5s_300s',
              'fok_2s_9s', 'fok_2s_15s', 'fok_2s_30s', 'fok_2s_60s', 'fok_2s_120s', 'fok_2s_300s', 'meta_15s',
              'meta_30s', 'meta_60s', 'meta_120s', 'meta_300s', 'limit_1']
             # ['fok_1', 'fok_2', 'fok_3', 'fok_4', 'fok_5', 'fok_6', 'fok_7', 'fok_8', 'fok_9', 'meta_1']

# slope_factor
slope_factor = ['QR1-2', 'press', 'skew15', 'skew60', 'skew120', 'slope_ask3', 'slope_bid3', 'Slope_diff3', 'slope_ask10', 'slope_bid10', 'Slope_diff10', 'slope_askh2', 'slope_bidh2', 'EMA', 'RSI', 'WILLR', ]

# log format factor list
log_factor = ['book_pressure_15s', 'book_pressure_30s', 'book_pressure_delta_15s', 'higher_bid_amt_15s',
                   'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s', 'lower_ask_amt_30s', 'lower_ask_amt_60s',
                   'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s', 'net_bid_amt_delta_60s', 'indus_book_pressure_15s',
                   'indus_book_pressure_delta_15s', 'indus_higher_bid_amt_15s', 'indus_higher_bid_amt_30s', 'indus_higher_bid_amt_60s',
                   'indus_lower_ask_amt_15s', 'indus_lower_ask_amt_30s', 'indus_lower_ask_amt_60s', 'indus_net_bid_amt_delta_15s',
                   'indus_net_bid_amt_delta_30s', 'indus_net_bid_amt_delta_60s', 'mkt_book_pressure_15s', 'mkt_higher_bid_amt_15s',
                   'mkt_lower_ask_amt_15s', 'mkt_net_bid_amt_delta_15s']

# factor group
batch2_factor = base_factor + ofl_factor + fok_factor + slope_factor

# build factor name dict
FACTOR_NAME = {k: eval(k) for k in __all__ }

# build factor name func
def build_factor_name(name):
    factor_name = []
    if isinstance(name, list):
        for n in name:
            factor_name.extend(FACTOR_NAME[n])
    if isinstance(name, str):
        factor_name = name
    return factor_name