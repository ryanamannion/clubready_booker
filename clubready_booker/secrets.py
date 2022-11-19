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


def get_secrets(yaml_path: Union[str, Path]):
    unsuccessful = []
    for directory in CHECK_PATHS:
        yaml_path = directory.joinpath(FILE_NAME)
        if not yaml_path.exists():
            unsuccessful.append(yaml_path)
            continue
        else:
            with yaml_path.open('r') as f:
                return yaml.safe_load(f)
    msg = SECRETS_NOT_FOUND.format(FILE_NAME, PATH)
    logger.error(msg)
    raise FileNotFoundError(msg)


SECRETS_NOT_FOUND = "Could not find {} in secrets path {}"
