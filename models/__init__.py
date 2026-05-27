import importlib
from os import path as osp
from copy import deepcopy
from utils import scandir
from utils.logger import get_root_logger
from utils.registry import MODEL_REGISTRY

__all__ = ['build_model']

# automatically scan and import models modules for registry
# scan all the files under the 'models' folder and collect files ending with '_model.py'
model_folder = osp.dirname(osp.abspath(__file__))
model_filenames = [osp.splitext(osp.basename(v))[0] for v in scandir(model_folder) if v.endswith('_model.py')]
# import all the models modules
_model_modules = [importlib.import_module(f'models.{file_name}') for file_name in model_filenames]


def build_model(opt, test_month, indus_type, logger_name=None):
    """Build models from options.

    Args:
        opt (dict): Configuration. It must contain:
            model_type (str): Model type.
    """
    opt = deepcopy(opt)
    model = MODEL_REGISTRY.get(opt['model']['type'])(opt, test_month, indus_type, logger_name)
    if logger_name is None:
        logger_name = f"month{test_month}_indus{indus_type}"
    logger = get_root_logger(logger_name)
    logger.info(f'[{logger_name}] Model [{model.__class__.__name__}] is created.')
    return model
