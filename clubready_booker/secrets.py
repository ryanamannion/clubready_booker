"""Functions for managing secrets"""
from typing import Union
from pathlib import Path
import yaml
import logging

logger = logging.getLogger(__name__)


CHECK_PATHS = [
    Path("~/.config/clubready_booker").expanduser(),
    Path(__file__).parent
]
PATH = ":".join(map(str, CHECK_PATHS))
FILE_NAME = "secrets.yaml"


def get_config_location():
    for directory in CHECK_PATHS:
        if directory.exists():
            return directory
    else:
        msg = SECRETS_NOT_FOUND.format(
            "clubready_booker config dir", PATH
        )
        logger.error(msg)
        raise FileNotFoundError(msg)


def get_secrets(yaml_path: Union[str, Path]):
    config_dir = get_config_location()
    yaml_path = config_dir.joinpath(FILE_NAME)
    assert yaml_path.exists(), f"Cannot find {FILE_NAME} in {str(config_dir)}"
    with yaml_path.open('r') as f:
        return yaml.safe_load(f)


SECRETS_NOT_FOUND = "Could not find {} in secrets path {}"
