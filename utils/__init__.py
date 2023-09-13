import numpy as np
import time
import os
import shutil

from .read_files import cx_read_sql, create_pd_engine, create_index




def get_pct_up(x):
    return np.percentile(x, 95)

def get_pct_down(x):
    return np.percentile(x, 5)

class Timer():
    def __init__(self):
        self.v = time.time()

    def s(self):
        self.v = time.time()

    def t(self):
        return time.time() - self.v


def time_str(t):
    if t > 3600:
        return '{:.1f}h'.format(t/3600)
    if t > 60:
        return '{:.1f}min'.format(t/60)
    return '{:.1f}s'.format(t)


def ensure_path(path, remove=True):
    basename = os.path.basename(path).rstrip('/')
    if os.path.exists(path):
        if remove or input('{} exists, remove? (y/n)'.format(path)) != 'n':
            shutil.rmtree(path)
            os.makedirs(path)
    else:
        os.makedirs(path)
