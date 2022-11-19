"""Functions for managing secrets"""
from typing import Union
from pathlib import Path
import yaml


def get_secrets(yaml_path: Union[str, Path]):
    yaml_path = Path(yaml_path).resolve()
    assert yaml_path.exists(), f"Cannot find secrets at {str(yaml_path)}"
    with yaml_path.open('r') as f:
        return yaml.safe_load(f)
