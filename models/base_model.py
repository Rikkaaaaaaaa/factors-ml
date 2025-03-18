import os
import time
from collections import OrderedDict
from copy import deepcopy

from utils.logger import get_root_logger


class BaseModel():
    """Base models."""

    def __init__(self, opt):
        self.opt = opt


    def feed_data(self, data):
        pass

    def optimize_parameters(self):
        pass


