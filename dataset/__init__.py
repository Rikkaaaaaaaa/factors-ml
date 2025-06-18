import os.path as osp
import importlib

from dataset.sql_ops import check_indus, get_ticker_list
from dataset.factor_name import build_factor_name
from utils import scandir
from utils.logger import get_root_logger
from utils.registry import DATASET_REGISTRY

__all__ = ['build_factor_name', 'build_dataset']
# automatically scan and import dataset modules for registry
# scan all the files under the data folder with '_dataset' in file names
data_folder = osp.dirname(osp.abspath(__file__))
dataset_filenames = [osp.splitext(osp.basename(v))[0] for v in scandir(data_folder) if v.endswith('_dataset.py')]
# import all the dataset modules
_dataset_modules = [importlib.import_module(f'dataset.{file_name}') for file_name in dataset_filenames]


def build_dataset(opt, test_month, indus_type):
    """Build dataset from options.

    Args:
        dataset_opt (dict): Configuration for dataset. It must contain:
            name (str): Dataset name.
            type (str): Dataset type.
    """
    #dataset_opt = deepcopy(dataset_opt)
    dataset = DATASET_REGISTRY.get(opt['dataset']['type'])(opt, test_month, indus_type)
    logger_name = f"month{test_month}_indus{indus_type}"
    logger = get_root_logger(logger_name)
    logger.info(f'{test_month}_indus_{indus_type}: Dataset [{dataset.__class__.__name__}] is built.')
    return dataset

