from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class EideModel:
    project_name: str
    target_names: list[str]
    payload: dict[str, Any]


def load_eide_model(eide_yml_path: Path) -> EideModel:
    with eide_yml_path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    targets = list((payload.get("targets") or {}).keys())
    return EideModel(project_name=str(payload.get("name", "")), target_names=targets, payload=payload)
