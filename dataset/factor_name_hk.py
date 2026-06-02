

# all factor names
__all__ = [ # factor names
           'ddb_test_factor',
           'log_factor',
            ]

factor_list_orig = """
willr_5min
willr_2min
willr_1min
willr_15s
slope_diffh2_5min
slope_diffh2_3s
slope_diffh2_2min
slope_diffh2_1min
slope_diffh2_15s
slope_diff3_5min
slope_diff3_3s
slope_diff3_2min
slope_diff3_1min
slope_diff3_15s
slope_bidh2_5min
slope_bidh2_3s
slope_bidh2_2min
slope_bidh2_1min
slope_bidh2_15s
slope_bid3_5min
slope_bid3_3s
slope_bid3_2min
slope_bid3_1min
slope_bid3_15s
slope_askh2_5min
slope_askh2_3s
slope_askh2_2min
slope_askh2_1min
slope_askh2_15s
slope_ask3_5min
slope_ask3_3s
slope_ask3_2min
slope_ask3_1min
slope_ask3_15s
skew_60s
skew_15s
skew_120s
sell_sum_delta
sell_mega_sum_delta
rsi_5min
rsi_2min
rsi_1min
rsi_15s
ret_3s
price_diff_pos
price_diff_neg
price_diff
price_3s_before
period_low_5min
period_low_2min
period_low_1min
period_low_15s
period_high_5min
period_high_2min
period_high_1min
period_high_15s
order_diff1_3s
order_diff1_15s
order_diff10_3s
order_diff10_15s
net_mega_bid_amt_delta_60s
net_mega_bid_amt_delta_3s
net_mega_bid_amt_delta_30s
net_mega_bid_amt_delta_15s
net_mega_bid_amt_delta_120s
net_bid_amt_delta_60s
net_bid_amt_delta_3s
net_bid_amt_delta_30s
net_bid_amt_delta_15s
net_bid_amt_delta_120s
midPrice_mavg_8_15s
midPrice_mavg_4_15s
midPrice_mavg_40_15s
midPrice_mavg_20_15s
midPrice_60s_before
midPrice_30s_before
midPrice_15s_before
ma_close_ret_5
ma_close_ret_2_5
ma_close_ret_2_10
ma_close_ret_2
ma_close_ret_10
ma_close_ret_1
lower_ask_fill_amt_60s
lower_ask_fill_amt_3s
lower_ask_fill_amt_30s
lower_ask_fill_amt_120s
lower_ask_amt_60s
lower_ask_amt_3s
lower_ask_amt_30s
lower_ask_amt_15s
lower_ask_amt_120s
lastPrice_mavg_8_15s
lastPrice_mavg_4_15s
lastPrice_mavg_40_15s
lastPrice_mavg_20_15s
lastPrice_60s_before
lastPrice_30s_before
lastPrice_15s_before
higher_bid_fill_amt_60s
higher_bid_fill_amt_3s
higher_bid_fill_amt_30s
higher_bid_fill_amt_120s
higher_bid_amt_60s
higher_bid_amt_3s
higher_bid_amt_30s
higher_bid_amt_15s
higher_bid_amt_120s
flickering_b_60s
flickering_b_3s
flickering_b_300s
flickering_b_15s
flickering_b_120s
flickering_a_60s
flickering_a_3s
flickering_a_300s
flickering_a_15s
flickering_a_120s
ema_5min
ema_3s
ema_30s
ema_2min
ema_1min
ema_15s
close_ret_60s
close_ret_30s
close_ret_15s
cancel_diff10_3s
cancel_diff10_15s
buy_sum_delta
buy_mega_sum_delta
bulk_buy_sell_diff_60s
bulk_buy_sell_diff_3s
bulk_buy_sell_diff_30s
bulk_buy_sell_diff_15s
bulk_buy_sell_diff_120s
active_buy_sell_diff_60s
active_buy_sell_diff_3s
active_buy_sell_diff_30s
active_buy_sell_diff_15s
active_buy_sell_diff_120s
QR1_3_5min
QR1_3_2min
QR1_3_1min
QR1_3_15s
QR1_3
QR1_2_5min
QR1_2_2min
QR1_2_1min
QR1_2_15s
QR1_2
"""

ddb_test_factor = factor_list_orig.strip().splitlines()

# log format factor list
log_factor = factor_list_orig.strip().splitlines()

# build factor name dict
FACTOR_NAME = {k: eval(k) for k in __all__ }

# build factor name func
def build_factor_name_hk(name):
    factor_name = []
    if isinstance(name, list):
        for n in name:
            factor_name.extend(FACTOR_NAME[n])
    if isinstance(name, str):
        factor_name = name

    return factor_name
