

# all factor names
__all__ = [ # factor names
           'ddb_test_factor',
           'log_factor',
            ]

ddb_test_factor = ["lower_ask_amt_120s", "higher_bid_amt_120s", "higher_bid_amt_30s", "cancel_diff10_15s", "cancel_diff10_3s"
               ]

# log format factor list
log_factor = ["lower_ask_amt_120s", "higher_bid_amt_120s", "higher_bid_amt_30s", "cancel_diff10_15s", "cancel_diff10_3s"
              ]

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