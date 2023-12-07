

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


ofl_factor =  ['ask1_ofl_std_3s', 'ask1_ofl_std_15s', 'ask1_ofl_std_min', 'ask1_ofl_std_2min', 'ask1_ofl_std_5min', 'bid1_ofl_std_3s',
                 'bid1_ofl_std_15s', 'bid1_ofl_std_min', 'bid1_ofl_std_2min', 'bid1_ofl_std_5min', 'ofl1_std_3s', 'ofl1_std_15s',
                 'ofl1_std_min', 'ofl1_std_2min', 'ofl1_std_5min', 'ask2_ofl_std_3s', 'ask2_ofl_std_15s', 'ask2_ofl_std_min',
                 'ask2_ofl_std_2min', 'ask2_ofl_std_5min', 'bid2_ofl_std_3s', 'bid2_ofl_std_15s', 'bid2_ofl_std_min',
                 'bid2_ofl_std_2min', 'bid2_ofl_std_5min', 'ofl2_std_3s', 'ofl2_std_15s', 'ofl2_std_min', 'ofl2_std_2min',
                 'ofl2_std_5min', 'ask1_order_dst_3s', 'ask1_order_dst_15s', 'ask1_order_dst_min', 'ask1_order_dst_2min',
                 'ask1_order_dst_5min', 'bid1_order_dst_3s', 'bid1_order_dst_15s', 'bid1_order_dst_min', 'bid1_order_dst_2min',
                 'bid1_order_dst_5min', 'depth_im1_3s', 'depth_im2_3s', 'depth_im1_15s', 'depth_im2_15s', 'depth_im1_min',
                 'depth_im2_min', 'depth_im1_2min', 'depth_im2_2min', 'depth_im1_5min', 'depth_im2_5min', 'ask_press_3s',
                 'ask_press_15s', 'ask_press_min', 'ask_press_2min', 'ask_press_5min', 'bid_press_3s', 'bid_press_15s',
                 'bid_press_min', 'bid_press_2min', 'bid_press_5min', 'press_3s', 'press_15s', 'press_min', 'press_2min',
                 'press_5min', 'close_versus_mid_3s', 'close_versus_mid_15s', 'close_versus_mid_min', 'close_versus_mid_2min',
                 'close_versus_mid_5min', 'spread_tick_3s', 'spread_tick_15s', 'spread_tick_min', 'spread_tick_2min', 'spread_tick_5min',
                 'ask_wap_versus_mid_3s', 'ask_wap_versus_mid_15s', 'ask_wap_versus_mid_min', 'ask_wap_versus_mid_2min',
                 'ask_wap_versus_mid_5min', 'bid_wap_versus_mid_3s', 'bid_wap_versus_mid_15s', 'bid_wap_versus_mid_min',
                 'bid_wap_versus_mid_2min', 'bid_wap_versus_mid_5min']

slope_factor = ['skew_15', 'skew_60', 'skew_120', 'slope_ask3_3s', 'slope_ask3_15s', 'slope_ask3_min', 'slope_ask3_2min', 'slope_ask3_5min', 'slope_bid3_3s', 'slope_bid3_15s', 'slope_bid3_min', 'slope_bid3_2min', 'slope_bid3_5min', 'slope_diff3_3s', 'slope_diff3_15s', 'slope_diff3_min', 'slope_diff3_2min', 'slope_diff3_5min', 'slope_ask10_3s', 'slope_ask10_15s', 'slope_ask10_min', 'slope_ask10_2min', 'slope_ask10_5min', 'slope_bid10_15s', 'slope_bid10_3s', 'slope_bid10_min', 'slope_bid10_2min', 'slope_bid10_5min', 'slope_diff10_15s', 'slope_diff10_3s', 'slope_diff10_min', 'slope_diff10_2min', 'slope_diff10_5min', 'slope_askh2_15s', 'slope_askh2_3s', 'slope_askh2_min', 'slope_askh2_2min', 'slope_askh2_5min', 'slope_bidh2_15s', 'slope_bidh2_3s', 'slope_bidh2_min', 'slope_bidh2_2min', 'slope_bidh2_5min', 'EMA_15s', 'EMA_3s', 'EMA_30s', 'EMA_min', 'EMA_2min', 'EMA_5min', 'EMA_std_3s', 'EMA_std_15s', 'EMA_std_min', 'EMA_std_2min', 'EMA_std_5min', 'RSI_15s', 'RSI_3s', 'RSI_min', 'RSI_2min', 'RSI_5min', 'WILLR_15s', 'WILLR_3s', 'WILLR_min', 'WILLR_2min', 'WILLR_5min', 'QR1_2_15s', 'QR1_2_3s', 'QR1_2_min', 'QR1_2_2min', 'QR1_2_5min', 'QR1_3_15s', 'QR1_3_3s', 'QR1_3_min', 'QR1_3_2min', 'QR1_3_5min']

genetic_factor = ['genetic_programming_1', 'genetic_programming_2', 'genetic_programming_3', 'genetic_programming_4',
                     'genetic_programming_5', 'genetic_programming_6', 'genetic_programming_7', 'genetic_programming_8',
                     'genetic_programming_9', 'genetic_programming_10']



# fok factor
fok_factor = ['fok_0.5s_9s', 'fok_0.5s_15s', 'fok_0.5s_30s', 'fok_0.5s_60s', 'fok_0.5s_120s', 'fok_0.5s_300s',
              'fok_2s_9s', 'fok_2s_15s', 'fok_2s_30s', 'fok_2s_60s', 'fok_2s_120s', 'fok_2s_300s', 'meta_15s',
              'meta_30s', 'meta_60s', 'meta_120s', 'meta_300s', 'limit_1']
             # ['fok_1', 'fok_2', 'fok_3', 'fok_4', 'fok_5', 'fok_6', 'fok_7', 'fok_8', 'fok_9', 'meta_1']

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
batch3_factor = base_factor + ofl_factor + genetic_factor + slope_factor

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