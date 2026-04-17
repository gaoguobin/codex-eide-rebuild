from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path


def normalize_path(path_value: str | Path) -> str:
    return str(Path(path_value)).replace("\\", "/")


def current_platform() -> str:
    return "windows" if os.name == "nt" else "linux"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def elapsed_ms(start_mark: float) -> int:
    return int((time.perf_counter() - start_mark) * 1000)
