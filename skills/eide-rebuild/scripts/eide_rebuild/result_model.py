from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


_KEY_MAP = {
    "schema_version": "schemaVersion",
    "exit_code": "exitCode",
    "error_code": "errorCode",
    "workspace_path": "workspacePath",
    "project_root": "projectRoot",
    "project_name": "projectName",
    "started_at": "startedAt",
    "finished_at": "finishedAt",
    "duration_ms": "durationMs",
    "target_names": "targetNames",
    "source_stats": "sourceStats",
    "builder_params_path": "builderParamsPath",
    "builder_params_summary": "builderParamsSummary",
    "compiler_log_path": "compilerLogPath",
    "compiler_log": "compilerLog",
    "stack_report_json_path": "stackReportJsonPath",
    "stack_report_html_path": "stackReportHtmlPath",
}


@dataclass
class StepResult:
    kind: str = ""
    name: str = ""
    ok: bool = False
    exit_code: int = 0
    error_code: str = ""
    message: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    stdout: str = ""
    stderr: str = ""
    command: list[str] = field(default_factory=list)
    cwd: str = ""


@dataclass
class TargetResult:
    name: str = ""
    index: int = 0
    total: int = 0
    ok: bool = False
    exit_code: int = 0
    error_code: str = ""
    message: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    source_stats: dict[str, Any] = field(default_factory=dict)
    builder_params_path: str = ""
    builder_params_summary: dict[str, Any] = field(default_factory=dict)
    compiler_log_path: str = ""
    compiler_log: str = ""
    stack_report_json_path: str = ""
    stack_report_html_path: str = ""
    transcript: str = ""
    memory: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    steps: list[StepResult] = field(default_factory=list)


@dataclass
class RunResult:
    schema_version: str = "1"
    ok: bool = False
    exit_code: int = 7
    error_code: str = "INTERNAL_ERROR"
    message: str = ""
    mode: str = "rebuild-all"
    platform: str = ""
    workspace_path: str = ""
    project_root: str = ""
    project_name: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    summary: dict[str, Any] = field(default_factory=dict)
    target_names: list[str] = field(default_factory=list)
    transcript: str = ""
    targets: list[TargetResult] = field(default_factory=list)


def _to_json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _to_json_value(asdict(value))
    if isinstance(value, dict):
        return {_KEY_MAP.get(key, key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    return value


def render_json_result(result: RunResult) -> str:
    return json.dumps(_to_json_value(result), ensure_ascii=False, indent=2) + "\n"


def _normalize_path(path_value: Path | str) -> str:
    return str(Path(path_value).resolve()).replace("\\", "/")


def _current_platform() -> str:
    import os

    return "windows" if os.name == "nt" else "linux"


def build_run_result(
    workspace_path: str,
    project_root: Path | str,
    project_name: str,
    platform_name: str,
    target_names: list[str],
    started_at: str,
    finished_at: str,
    duration_ms: int,
    targets: list[TargetResult],
    transcript: str,
) -> RunResult:
    passed = sum(1 for target in targets if target.ok)
    failed = len(targets) - passed
    return RunResult(
        ok=failed == 0,
        exit_code=0 if failed == 0 else 6,
        error_code="OK" if failed == 0 else "BUILD_FAILED",
        message="" if failed == 0 else f"{failed} target(s) failed.",
        mode="rebuild-all",
        platform=platform_name,
        workspace_path=workspace_path,
        project_root=_normalize_path(project_root),
        project_name=project_name,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        summary={"discovered": len(target_names), "passed": passed, "failed": failed},
        target_names=target_names,
        transcript=transcript,
        targets=targets,
    )


def build_error_result(error: Exception, started_at: str, finished_at: str, duration_ms: int) -> RunResult:
    error_code = getattr(error, "error_code", "INTERNAL_ERROR")
    exit_code = getattr(error, "exit_code", 7)
    return RunResult(
        ok=False,
        exit_code=exit_code,
        error_code=error_code,
        message=str(error),
        mode="rebuild-all",
        platform=_current_platform(),
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        summary={"discovered": 0, "passed": 0, "failed": 0},
    )


def write_run_result(output_path: Path | str, result: RunResult) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json_result(result), encoding="utf-8", newline="\n")
