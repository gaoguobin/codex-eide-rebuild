from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EideModel:
    project_name: str
    target_names: list[str]
    payload: dict[str, Any]


def require_yaml_module() -> Any:
    try:
        import yaml as yaml_module
    except ModuleNotFoundError as error:
        raise RuntimeError("PyYAML is required. Run `python -m pip install --user PyYAML`.") from error
    return yaml_module


def load_eide_model(eide_yml_path: Path) -> EideModel:
    yaml_module = require_yaml_module()
    with eide_yml_path.open("r", encoding="utf-8") as stream:
        payload = yaml_module.safe_load(stream) or {}
    targets = list((payload.get("targets") or {}).keys())
    return EideModel(project_name=str(payload.get("name", "")), target_names=targets, payload=payload)
