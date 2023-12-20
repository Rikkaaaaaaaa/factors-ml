
import logging
import time
import sys
sys.path.append('../')
initialized_logger = {}


class AvgTimer():

    def __init__(self, window=200):
        self.window = window  # average window
        self.current_time = 0
        self.total_time = 0
        self.count = 0
        self.avg_time = 0
        self.start()

    def start(self):
        self.start_time = self.tic = time.time()

    def record(self):
        self.count += 1
        self.toc = time.time()
        self.current_time = self.toc - self.tic
        self.total_time += self.current_time
        # calculate average time
        self.avg_time = self.total_time / self.count

        # reset
        if self.count > self.window:
            self.count = 0
            self.total_time = 0

        self.tic = time.time()

    def get_current_time(self):
        return self.current_time

    def get_avg_time(self):
        return self.avg_time


def get_root_logger(logger_name='', log_level=logging.INFO, log_file=None):
    """Get the root logger.

    The logger will be initialized if it has not been initialized. By default a
    StreamHandler will be added. If `log_file` is specified, a FileHandler will
    also be added.

    Args:
        logger_name (str): root logger name. Default: 'factor-ml'.
        log_file (str | None): The log filename. If specified, a FileHandler
            will be added to the root logger.
        log_level (int): The root logger level. Note that only the process of
            rank 0 is affected, while other processes will set the level to
            "Error" and be silent most of the time.

    Returns:
        logging.Logger: The root logger.
    """
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()
    # if the logger has been initialized, just return it
    if logger_name in initialized_logger:
        return logger

    format_str = '%(asctime)s %(levelname)s: %(message)s'
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(format_str))
    logger.addHandler(stream_handler)
    logger.propagate = False

    if log_file is not None:
        logger.setLevel(log_level)
        # add file handler
        file_handler = logging.FileHandler(log_file, 'w')
        file_handler.setFormatter(logging.Formatter(format_str))
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)
    initialized_logger[logger_name] = True
    return logger


def get_env_info():
    """Get environment information.

    Currently, only log the software version.
    """

    __version__ = '2.0.1'

    msg = r"""
          ______ ____             _      _____  ____  
         |  ____/ __ \      /\   | |    / ____|/ __ \ 
         | |__ | |  | |    /  \  | |   | |  __| |  | |
         |  __|| |  | |   / /\ \ | |   | | |_ | |  | |
         | |___| |__| |  / ____ \| |___| |__| | |__| |
         |______\___\_\ /_/    \_\______\_____|\____/ 
                                              
    """
    # msg += ('\nVersion Information: '
    #         f'\n\tBasicAlgo: {__version__}'
    #         #f'\n\tPyTorch: {torch.__version__}'
    #         #f'\n\tTorchVision: {torchvision.__version__}'
    #          )

    msg += ('\nVersion Information: '
            f'\n\tBasic-ALgo: {__version__}')
    return msg

