"""Functions for managing secrets"""
import os
from pathlib import Path
import yaml
import logging
from typing import Union, Dict

logger = logging.getLogger(__name__)


CHECK_PATHS = [
    Path("~/.config/clubready_booker").expanduser(),
    Path(__file__).parent
]
PATH = ":".join(map(str, CHECK_PATHS))
FILE_NAME = "config.yaml"


class NotSpecified:

    def __init__(self):
        return


# Get some environment variables
ENV_VAR_PREFIX = "CLUBREADYBOOKER_"

default_config_vals = {
    'username': None,
    'password': None,
    'url': None,
    'bookable_range': 2,
    'max_results': 100,
    'timezone': 'America/New_York',
    'config_dir': None
}

env_vars = {
    name: os.environ.get(ENV_VAR_PREFIX + name.upper(), NotSpecified())
    for name in default_config_vals
}


def get_config_location():
    if not isinstance(env_vars['config_dir'], NotSpecified):
        directory = Path(env_vars['config_dir'])
        if not directory.exists():
            msg = (
                f"Got config dir from env var, but path does not exist: "
                f"{env_vars['config_dir']}"
            )
            logger.error(msg)
            raise NotADirectoryError(msg)
    for directory in CHECK_PATHS:
        if directory.exists():
            logger.debug(f"Using config dir {directory}")
            return directory
    else:
        msg = SECRETS_NOT_FOUND.format(
            "clubready_booker config dir", PATH
        )
        logger.error(msg)
        raise FileNotFoundError(msg)


def get_var_from_hierarchy(config, var_name):
    env_val = env_vars.get(var_name, NotSpecified())
    if not isinstance(env_val, NotSpecified):
        return env_val
    config_val = config.get(var_name, NotSpecified())
    if not isinstance(config_val, NotSpecified):
        return config_val
    return default_config_vals[var_name]


def get_config():
    config_dir = get_config_location()
    config_path = config_dir.joinpath(FILE_NAME)
    if not config_path.exists():
        msg = (
            f"Cannot find {FILE_NAME} in {str(config_dir)}, webpage functions "
            f"will not work without secrets."
        )
        logger.warning(msg)
        parsed_config = {}
    else:
        with config_path.open('r') as f:
            parsed_config: Dict[str, Union[int, str]] = yaml.safe_load(f)

    config = {}
    for key in default_config_vals:
        config[key] = get_var_from_hierarchy(parsed_config, key)
    return config


SECRETS_NOT_FOUND = "Could not find {} in path {}"
