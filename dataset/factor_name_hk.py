from pathlib import Path
import os
import pandas as pd

# all factor names
__all__ = [ # factor names
            'ddb_test_factor',
            'log_factor',
            'clip_factor'
            ]

factor_name_path = str(Path(__file__).resolve().parents[0])
factor_data_table = pd.read_csv(os.path.join(factor_name_path, "hk_factor_name.csv"))

# all factor list
ddb_test_factor = factor_data_table['all_factors'].dropna().to_list()

# log factor list
log_factor = factor_data_table['log_factors'].dropna().to_list()

# clip factor list
clip_factor = factor_data_table['clip_factors'].dropna().to_list()

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
