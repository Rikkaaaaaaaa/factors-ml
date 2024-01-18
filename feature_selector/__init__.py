import importlib
from os import path as osp
from copy import deepcopy
from utils import scandir
from utils.logger import get_root_logger
from utils.registry import SELECTOR_REGISTRY

__all__ = ['build_selector']

# automatically scan and import models modules for registry
# scan all the files under the 'models' folder and collect files ending with '_model.py'
selector_folder = osp.dirname(osp.abspath(__file__))
selector_filenames = [osp.splitext(osp.basename(v))[0] for v in scandir(selector_folder) if v.endswith('_selector.py')]
# import all the models modules
_selector_modules = [importlib.import_module(f'feature_selector.{file_name}') for file_name in selector_filenames]


def build_selector(opt, test_month, indus_type):
    """Build models from options.

    Args:
        opt (dict): Configuration. It must contain:
            model_type (str): Model type.
    """
    opt = deepcopy(opt)
    selector = SELECTOR_REGISTRY.get(opt['feature_selector']['type'])(opt, test_month, indus_type)
    logger_name = f"month{test_month}_indus{indus_type}"
    logger = get_root_logger(logger_name)
    logger.info(f'{test_month}_indus_{indus_type}: Selector [{selector.__class__.__name__}] is created.')
    return selector
