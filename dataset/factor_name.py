

# all factor names
__all__ = [ # factor names
           'base_factor',
           'ofl_factor',
           'ofl_factor_std',
           'fok_factor',
           'slope_factor',
           'slope_factor_std',
            'genetic_programming_factor_1',
            'genetic_programming_factor_2',
            'genetic_programming_factor_3',
            'genetic_programming_factor_2_div_open',
           # factor collections
           'batch2_factor',
           # factors need to be preprocessed
           'log_factor',
            # DDB factor
            "ddb_slope_std_factor",
            "ddb_slope_factor",
            "ddb_ofl_factor",
            "ddb_gp_factor",
            "ddb_fok_factor",
            "ddb_base_factor",
            "ddb_gp_factors_batch2",
            ]

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

# base factor name (no time)
base_factor = factor_list[1:] + indus_factor_name + mkt_factor_name

# orderflow factor name
ofl_factor = ['ask1_ofl_std_3s', 'ask1_ofl_std_15s', 'ask1_ofl_std_min', 'ask1_ofl_std_2min', 'ask1_ofl_std_5min',
                 'bid1_ofl_std_3s', 'bid1_ofl_std_15s', 'bid1_ofl_std_min', 'bid1_ofl_std_2min', 'bid1_ofl_std_5min',
                 'ofl1_std_3s', 'ofl1_std_15s', 'ofl1_std_min', 'ofl1_std_2min', 'ofl1_std_5min', 'ask2_ofl_std_3s',
                 'ask2_ofl_std_15s', 'ask2_ofl_std_min', 'ask2_ofl_std_2min', 'ask2_ofl_std_5min', 'bid2_ofl_std_3s',
                 'bid2_ofl_std_15s', 'bid2_ofl_std_min', 'bid2_ofl_std_2min', 'bid2_ofl_std_5min', 'ofl2_std_3s',
                 'ofl2_std_15s', 'ofl2_std_min', 'ofl2_std_2min', 'ofl2_std_5min', 'ask1_order_dst_3s', 'ask1_order_dst_15s',
                 'ask1_order_dst_min', 'ask1_order_dst_2min', 'ask1_order_dst_5min', 'bid1_order_dst_3s', 'bid1_order_dst_15s',
                 'bid1_order_dst_min', 'bid1_order_dst_2min', 'bid1_order_dst_5min', 'depth_im1_3s', 'depth_im2_3s',
                 'depth_im1_15s', 'depth_im2_15s', 'depth_im1_min', 'depth_im2_min', 'depth_im1_2min', 'depth_im2_2min',
                 'depth_im1_5min', 'depth_im2_5min', 'ask_press_3s', 'ask_press_15s', 'ask_press_min', 'ask_press_2min',
                 'ask_press_5min', 'bid_press_3s', 'bid_press_15s', 'bid_press_min', 'bid_press_2min', 'bid_press_5min',
                 'press_3s', 'press_15s', 'press_min', 'press_2min', 'press_5min', 'close_versus_mid_3s', 'close_versus_mid_15s',
                 'close_versus_mid_min', 'close_versus_mid_2min', 'close_versus_mid_5min', 'spread_tick_3s', 'spread_tick_15s',
                 'spread_tick_min', 'spread_tick_2min', 'spread_tick_5min', 'ask_wap_versus_mid_3s', 'ask_wap_versus_mid_15s',
                 'ask_wap_versus_mid_min', 'ask_wap_versus_mid_2min', 'ask_wap_versus_mid_5min', 'bid_wap_versus_mid_3s',
                 'bid_wap_versus_mid_15s', 'bid_wap_versus_mid_min', 'bid_wap_versus_mid_2min', 'bid_wap_versus_mid_5min'
                ]


ofl_factor_std = ['ask_wap_versus_mid_3s', 'ask_wap_versus_mid_15s', 'ask_wap_versus_mid_min', 'ask_wap_versus_mid_2min',
                 'ask_wap_versus_mid_5min', 'bid_wap_versus_mid_3s', 'bid_wap_versus_mid_15s', 'bid_wap_versus_mid_min',
                 'bid_wap_versus_mid_2min', 'bid_wap_versus_mid_5min']

# fok factor name
fok_factor = ['fok_0.5s_9s', 'fok_0.5s_15s', 'fok_0.5s_30s', 'fok_0.5s_60s', 'fok_0.5s_120s',
                'fok_0.5s_300s', 'fok_2s_9s', 'fok_2s_15s', 'fok_2s_30s', 'fok_2s_60s',
                'fok_2s_120s', 'fok_2s_300s', 'meta_15s', 'meta_30s', 'meta_60s',
                'meta_120s', 'meta_300s', 'limit1_15s', 'limit1_30s', 'limit1_60s',
                'limit1_120s', 'limit1_300s', 'limit2_15s', 'limit2_30s', 'limit2_60s',
                'limit2_120s', 'limit2_300s', 'trade1_15s', 'trade1_30s', 'trade1_60s',
                'trade1_120s', 'trade1_300s', 'regret_15s', 'regret_30s', 'regret_60s',
                'regret_120s', 'regret_300s']


# slope factor name
slope_factor = ['skew_15', 'skew_60', 'skew_120', 'slope_ask3_3s', 'slope_ask3_15s', 'slope_ask3_min',
                'slope_ask3_2min', 'slope_ask3_5min', 'slope_bid3_3s', 'slope_bid3_15s', 'slope_bid3_min',
                'slope_bid3_2min', 'slope_bid3_5min', 'slope_diff3_3s', 'slope_diff3_15s', 'slope_diff3_min',
                'slope_diff3_2min', 'slope_diff3_5min', 'slope_ask10_3s', 'slope_ask10_15s', 'slope_ask10_min',
                'slope_ask10_2min', 'slope_ask10_5min', 'slope_bid10_15s', 'slope_bid10_3s', 'slope_bid10_min',
                'slope_bid10_2min', 'slope_bid10_5min', 'slope_diff10_15s', 'slope_diff10_3s', 'slope_diff10_min',
                'slope_diff10_2min', 'slope_diff10_5min', 'slope_askh2_15s', 'slope_askh2_3s', 'slope_askh2_min',
                'slope_askh2_2min', 'slope_askh2_5min', 'slope_bidh2_15s', 'slope_bidh2_3s', 'slope_bidh2_min',
                'slope_bidh2_2min', 'slope_bidh2_5min', 'EMA_std_3s', 'EMA_std_15s', 'EMA_std_min', 'EMA_std_2min',
                'EMA_std_5min', 'RSI_15s','RSI_3s', 'RSI_min', 'RSI_2min', 'RSI_5min', 'WILLR_15s', 'WILLR_3s',
                'WILLR_min', 'WILLR_2min', 'WILLR_5min', 'QR1_2_15s', 'QR1_2_3s', 'QR1_2_min', 'QR1_2_2min',
                'QR1_2_5min', 'QR1_3_15s', 'QR1_3_3s', 'QR1_3_min', 'QR1_3_2min', 'QR1_3_5min'
]

slope_factor_std = ['skew_15', 'skew_60', 'skew_120', 'slope_ask3_3s', 'slope_ask3_15s', 'slope_ask3_min',
                    'slope_ask3_2min', 'slope_ask3_5min', 'slope_bid3_3s', 'slope_bid3_15s', 'slope_bid3_min',
                    'slope_bid3_2min', 'slope_bid3_5min', 'slope_diff3_3s', 'slope_diff3_15s', 'slope_diff3_min',
                    'slope_diff3_2min', 'slope_diff3_5min', 'slope_ask10_3s', 'slope_ask10_15s', 'slope_ask10_min',
                    'slope_ask10_2min', 'slope_ask10_5min', 'slope_bid10_15s', 'slope_bid10_3s', 'slope_bid10_min',
                    'slope_bid10_2min', 'slope_bid10_5min', 'slope_diff10_15s', 'slope_diff10_3s', 'slope_diff10_min',
                    'slope_diff10_2min', 'slope_diff10_5min', 'slope_askh2_15s', 'slope_askh2_3s', 'slope_askh2_min',
                    'slope_askh2_2min', 'slope_askh2_5min', 'slope_bidh2_15s', 'slope_bidh2_3s', 'slope_bidh2_min',
                    'slope_bidh2_2min', 'slope_bidh2_5min',
                    'EMA_std_3s', 'EMA_std_15s', 'EMA_std_min', 'EMA_std_2min', 'EMA_std_5min'
]

genetic_programming_factor_1 = ['genetic_programming_1', 'genetic_programming_2', 'genetic_programming_3', 'genetic_programming_4',
                     'genetic_programming_5', 'genetic_programming_6', 'genetic_programming_7', 'genetic_programming_8',
]


genetic_programming_factor_2 = ['genetic_programming_{}'.format(x) for x in range(1, 37)]
genetic_programming_factor_2_div_open = ['genetic_programming_{}'.format(x) for x in range(1, 37)]
genetic_programming_factor_3 = ['genetic_programming_{}'.format(x) for x in range(37, 60)]



# log format factor list
log_factor = ['book_pressure_15s', 'book_pressure_30s', 'book_pressure_delta_15s', 'higher_bid_amt_15s',
                   'higher_bid_amt_30s', 'higher_bid_amt_60s', 'lower_ask_amt_15s', 'lower_ask_amt_30s', 'lower_ask_amt_60s',
                   'net_bid_amt_delta_15s', 'net_bid_amt_delta_30s', 'net_bid_amt_delta_60s', 'indus_book_pressure_15s',
                   'indus_book_pressure_delta_15s', 'indus_higher_bid_amt_15s', 'indus_higher_bid_amt_30s', 'indus_higher_bid_amt_60s',
                   'indus_lower_ask_amt_15s', 'indus_lower_ask_amt_30s', 'indus_lower_ask_amt_60s', 'indus_net_bid_amt_delta_15s',
                   'indus_net_bid_amt_delta_30s', 'indus_net_bid_amt_delta_60s', 'mkt_book_pressure_15s', 'mkt_higher_bid_amt_15s',
                   'mkt_lower_ask_amt_15s', 'mkt_net_bid_amt_delta_15s']

# factor group
batch1_factor = base_factor + ofl_factor
batch2_factor = base_factor + ofl_factor + fok_factor
batch3_factor = base_factor + ofl_factor + fok_factor + slope_factor
batch4_factor = base_factor + ofl_factor + fok_factor + slope_factor + genetic_programming_factor_2

# DDB factor name
ddb_slope_factor = ["skew_15", "skew_60", "skew_120",
                    "slope_ask3_3s","slope_ask3_15s","slope_ask3_min","slope_ask3_2min","slope_ask3_5min",
                    "slope_bid3_3s", "slope_bid3_15s","slope_bid3_min","slope_bid3_2min","slope_bid3_5min",
                    "slope_diff3_3s", "slope_diff3_15s","slope_diff3_min","slope_diff3_2min","slope_diff3_5min",

                    "slope_ask10_3s","slope_ask10_15s","slope_ask10_min","slope_ask10_2min","slope_ask10_5min",
                    "slope_bid10_3s", "slope_bid10_15s","slope_bid10_min","slope_bid10_2min","slope_bid10_5min",
                    "slope_diff10_3s", "slope_diff10_15s","slope_diff10_min","slope_diff10_2min","slope_diff10_5min",

                    "slope_askh2_3s","slope_askh2_15s","slope_askh2_min","slope_askh2_2min","slope_askh2_5min",
                    "slope_bidh2_3s", "slope_bidh2_15s","slope_bidh2_min","slope_bidh2_2min","slope_bidh2_5min",

                    "EMA_std_3s","EMA_std_15s","EMA_std_min","EMA_std_2min","EMA_std_5min",
                    "RSI_3s", "RSI_15s","RSI_min","RSI_2min","RSI_5min",

                    "WILLR_3s","WILLR_15s","WILLR_min","WILLR_2min","WILLR_5min",
                    "QR1_2_3s", "QR1_2_15s","QR1_2_min","QR1_2_2min","QR1_2_5min",
                    "QR1_3_3s", "QR1_3_15s","QR1_3_min","QR1_3_2min","QR1_3_5min",
                    ]

ddb_ofl_factor = ["ask1_ofl_std_3s", "ask1_ofl_std_15s", "ask1_ofl_std_min", "ask1_ofl_std_2min", "ask1_ofl_std_5min",
                    "bid1_ofl_std_3s", "bid1_ofl_std_15s", "bid1_ofl_std_min", "bid1_ofl_std_2min", "bid1_ofl_std_5min",
                    "ofl1_std_3s", "ofl1_std_15s", "ofl1_std_min", "ofl1_std_2min", "ofl1_std_5min",

                    "ask1_order_dst_3s", "ask1_order_dst_15s", "ask1_order_dst_min", "ask1_order_dst_2min", "ask1_order_dst_5min",
                    "bid1_order_dst_3s", "bid1_order_dst_15s", "bid1_order_dst_min", "bid1_order_dst_2min", "bid1_order_dst_5min",

                    "depth_im1_3s", "depth_im1_15s", "depth_im1_min", "depth_im1_2min", "depth_im1_5min",
                    "depth_im2_3s", "depth_im2_15s", "depth_im2_min", "depth_im2_2min", "depth_im2_5min",

                    "ask_press_3s", "ask_press_15s", "ask_press_min", "ask_press_2min", "ask_press_5min",
                    "bid_press_3s", "bid_press_15s", "bid_press_min", "bid_press_2min", "bid_press_5min",
                    "press_3s", "press_15s", "press_min", "press_2min", "press_5min",

                    "close_versus_mid_3s", "close_versus_mid_15s", "close_versus_mid_min", "close_versus_mid_2min", "close_versus_mid_5min",
                    "spread_tick_3s", "spread_tick_15s", "spread_tick_min", "spread_tick_2min", "spread_tick_5min",
                    "ask_wap_versus_mid_3s", "ask_wap_versus_mid_15s", "ask_wap_versus_mid_min", "ask_wap_versus_mid_2min", "ask_wap_versus_mid_5min",
                    "bid_wap_versus_mid_3s", "bid_wap_versus_mid_15s", "bid_wap_versus_mid_min", "bid_wap_versus_mid_2min", "bid_wap_versus_mid_5min"
                    ]

ddb_base_factor = ['ma_close_ret_10', 'bulk_buy_sell_diff_15s', 'indus_active_buy_sell_diff_30s', 'order_diff_10_15s',
               'net_bid_amt_delta_60s', 'ma_close_ret_5', 'bulk_active_buy_sell_diff_60s', 'ma_mid_ret_2_10',
               'net_bid_amt_delta_30s', 'indus_lower_ask_amt_60s', 'active_buy_sell_diff_15s', 'mid_ret_15s',
               'mkt_bulk_active_buy_sell_diff_15s', 'net_bid_amt_delta_15s', 'indus_mid_ret_30s', 'indus_higher_bid_amt_30s',
               'indus_order_diff_1_15s', 'mid_ret_30s', 'close_ret_30s', 'book_pressure_15s', 'indus_close_ret_30s',
               'ma_close_ret_1', 'indus_net_bid_amt_delta_30s', 'lower_ask_amt_60s', 'mkt_book_pressure_15s',
               'ma_close_ret_2_10', 'indus_close_ret_60s', 'bulk_active_buy_sell_diff_30s', 'mkt_net_bid_amt_delta_15s',
               'indus_bulk_active_buy_sell_diff_15s', 'higher_bid_amt_60s', 'close_ret_15s', 'book_pressure_delta_15s',
               'indus_mid_ret_60s', 'indus_close_ret_15s', 'indus_lower_ask_amt_30s', 'ma_mid_ret_2_5',
               'indus_bulk_active_buy_sell_diff_60s', 'indus_mid_ret_15s', 'indus_order_diff_10_15s',
               'active_buy_sell_diff_30s', 'book_pressure_30s', 'mid_ret_60s', 'mkt_lower_ask_amt_15s',
               'indus_active_buy_sell_diff_15s', 'indus_bulk_active_buy_sell_diff_30s', 'indus_net_bid_amt_delta_60s',
               'lower_ask_amt_15s', 'bulk_buy_sell_diff_60s', 'bulk_active_buy_sell_diff_15s', 'ma_close_ret_2',
               'indus_cancel_diff_10_15s', 'mkt_close_ret_15s', 'indus_book_pressure_15s', 'mkt_active_buy_sell_diff_15s',
               'ma_mid_ret_2', 'mid_mmt_route_5_5', 'ma_mid_ret_5', 'bulk_buy_sell_diff_30s', 'mkt_higher_bid_amt_15s',
               'close_ret_60s', 'indus_net_bid_amt_delta_15s', 'order_diff_1_15s', 'mid_mmt_route_10_10',
               'indus_higher_bid_amt_60s', 'indus_book_pressure_delta_15s', 'ma_close_ret_2_5', 'higher_bid_amt_30s',
               'ma_mid_ret_10',  'mid_ret_skew_10', 'mkt_order_diff_10_15s', 'indus_lower_ask_amt_15s',
               'lower_ask_amt_30s',  'higher_bid_amt_15s', 'indus_higher_bid_amt_15s', 'ma_mid_ret_1',
               'cancel_diff_10_15s'
               ]




ddb_gp_factor = [ "gp_1", "gp_2", "gp_3", "gp_4", "gp_5", "gp_6", "gp_7", "gp_8", "gp_9", "gp_10", "gp_11", "gp_12",
               "gp_13", "gp_14", "gp_15", "gp_16","gp_17", "gp_19", "gp_20", "gp_25", "gp_26", "gp_27", "gp_28", "gp_29", "gp_30",
               "gp_21", "gp_22", "gp_23", "gp_24",  "gp_31", "gp_32", "gp_33", "gp_34", "gp_35", "gp_36"
                ]

ddb_fok_factor = [ 'fok_2000_120s', 'fok_2000_15s', 'fok_2000_300s', 'fok_2000_30s',
                   'fok_2000_60s', 'fok_500_120s', 'fok_500_15s', 'fok_500_300s',
                   'fok_500_30s', 'fok_500_60s', 'limit1_120s', 'limit1_15s', 'limit1_300s',
                   'limit1_30s', 'limit1_60s', 'limit2_120s', 'limit2_15s', 'limit2_300s',
                   'limit2_30s', 'limit2_60s', 'meta_120s', 'meta_15s', 'meta_300s',
                    'meta_30s', 'meta_60s', 'regret_120s', 'regret_15s', 'regret_300s',
                   'regret_30s', 'regret_60s','trade1_120s', 'trade1_15s', 'trade1_300s',
                   'trade1_30s', 'trade1_60s']

ddb_slope_std_factor = ['skew_15', 'skew_60', 'skew_120', 'slope_ask3_3s', 'slope_ask3_15s', 'slope_ask3_min',
                    'slope_ask3_2min', 'slope_ask3_5min', 'slope_bid3_3s', 'slope_bid3_15s', 'slope_bid3_min',
                    'slope_bid3_2min', 'slope_bid3_5min', 'slope_diff3_3s', 'slope_diff3_15s', 'slope_diff3_min',
                    'slope_diff3_2min', 'slope_diff3_5min', 'slope_ask10_3s', 'slope_ask10_15s', 'slope_ask10_min',
                    'slope_ask10_2min', 'slope_ask10_5min', 'slope_bid10_15s', 'slope_bid10_3s', 'slope_bid10_min',
                    'slope_bid10_2min', 'slope_bid10_5min', 'slope_diff10_15s', 'slope_diff10_3s', 'slope_diff10_min',
                    'slope_diff10_2min', 'slope_diff10_5min', 'slope_askh2_15s', 'slope_askh2_3s', 'slope_askh2_min',
                    'slope_askh2_2min', 'slope_askh2_5min', 'slope_bidh2_15s', 'slope_bidh2_3s', 'slope_bidh2_min',
                    'slope_bidh2_2min', 'slope_bidh2_5min',
                    'EMA_std_3s', 'EMA_std_15s', 'EMA_std_min', 'EMA_std_2min', 'EMA_std_5min'
]

ddb_gp_factors_batch2 = ['gp_{}'.format(x) for x in range(37, 73)]  # 20250314 new GP factors (37~72)

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