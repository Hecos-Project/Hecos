import os
from hecos.config.yaml_utils import load_yaml, save_yaml
from hecos.core.constants import CONFIG_DATA_DIR
from .schema import PresenterConfig

def _get_config_path() -> str:
    return os.path.join(CONFIG_DATA_DIR, "presenter.yaml")

def load_presenter_config() -> PresenterConfig:
    return load_yaml(_get_config_path(), PresenterConfig)

def save_presenter_config(config: PresenterConfig) -> bool:
    return save_yaml(_get_config_path(), config)
