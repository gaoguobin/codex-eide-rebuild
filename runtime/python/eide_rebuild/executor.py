from __future__ import annotations

import locale
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .builder_params import generate_builder_params, write_builder_params
from .platform import elapsed_ms, normalize_path, utc_now
from .result_model import StepResult, TargetResult
from .tools import build_process_env, resolve_unify_builder_dll


BUILD_STEP_TIMEOUT_SECONDS = 60
TIMEOUT_EXIT_CODE = 124


def _timeout_payload(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(locale.getpreferredencoding(False), errors="replace")
    return str(value)


def run_step(
    kind: str,
    name: str,
    command: list[str] | str,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout_seconds: int = BUILD_STEP_TIMEOUT_SECONDS,
) -> StepResult:
    start_mark = time.perf_counter()
    started_at = utc_now()
    run_kwargs: dict[str, Any] = {
        "cwd": cwd,
        "capture_output": True,
        "text": True,
        "timeout": timeout_seconds,
    }
    if env:
        merged_env = os.environ.copy()
        merged_env.update(env)
        run_kwargs["env"] = merged_env
    if isinstance(command, str):
        run_kwargs["shell"] = True
    command_parts = [command] if isinstance(command, str) else [str(part) for part in command]
    try:
        completed = subprocess.run(command, **run_kwargs)
    except subprocess.TimeoutExpired as error:
        finished_at = utc_now()
        return StepResult(
            kind=kind,
            name=name,
            ok=False,
            exit_code=TIMEOUT_EXIT_CODE,
            error_code="STEP_TIMEOUT",
            message=f"{name} timed out after {timeout_seconds} seconds.",
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=elapsed_ms(start_mark),
            stdout=_timeout_payload(error.output),
            stderr=_timeout_payload(error.stderr),
            command=command_parts,
            cwd=normalize_path(cwd.resolve()),
        )
    finished_at = utc_now()
    exit_code = int(completed.returncode)
    return StepResult(
        kind=kind,
        name=name,
        ok=exit_code == 0,
        exit_code=exit_code,
        error_code="OK" if exit_code == 0 else "STEP_FAILED",
        message="" if exit_code == 0 else f"{name} failed with exit code {exit_code}.",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=elapsed_ms(start_mark),
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        command=command_parts,
        cwd=normalize_path(cwd.resolve()),
    )


def build_unify_builder_command(dotnet_path: str, unify_builder_path: str, builder_params_path: str) -> list[str]:
    unify_builder_dll = resolve_unify_builder_dll(unify_builder_path)
    return [
        dotnet_path,
        "exec",
        "--roll-forward",
        "Major",
        unify_builder_dll,
        "-p",
        builder_params_path,
        "--rebuild",
    ]


def _make_step_result(
    *,
    kind: str,
    name: str,
    started_at: str,
    finished_at: str,
    duration_ms: int,
    ok: bool,
    error_code: str,
    message: str = "",
    stdout: str = "",
    stderr: str = "",
    command: list[str] | None = None,
    cwd: Path | None = None,
    exit_code: int = 0,
) -> StepResult:
    return StepResult(
        kind=kind,
        name=name,
        ok=ok,
        exit_code=exit_code,
        error_code=error_code,
        message=message,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        stdout=stdout,
        stderr=stderr,
        command=list(command or []),
        cwd=normalize_path(cwd.resolve()) if cwd is not None else "",
    )


def _read_text_file(path_value: Path) -> str:
    payload = path_value.read_bytes()
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        text = payload.decode(locale.getpreferredencoding(False), errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _resolve_build_dir(project_root: Path, dump_path: str) -> Path:
    path_obj = Path(dump_path)
    if path_obj.is_absolute():
        return path_obj.resolve()
    return (project_root / path_obj).resolve()


def collect_output_files(project_root: Path, target_name: str, dump_path: str | None = None) -> list[dict[str, object]]:
    build_dir = _resolve_build_dir(project_root, dump_path or f"build/{target_name}")
    if not build_dir.exists():
        return []

    suffix_map = {
        ".bin": "bin",
        ".hex": "hex",
        ".a": "archive",
        ".map": "map",
    }
    artifacts: list[dict[str, object]] = []
    for candidate in sorted(build_dir.iterdir()):
        artifact_kind = suffix_map.get(candidate.suffix.lower())
        if artifact_kind is None or not candidate.is_file():
            continue
        artifacts.append(
            {
                "path": normalize_path(candidate.resolve()),
                "kind": artifact_kind,
                "size": candidate.stat().st_size,
            }
        )
    return artifacts


def _build_transcript(steps: list[StepResult]) -> str:
    parts: list[str] = []
    for step in steps:
        if step.stdout:
            parts.append(step.stdout.rstrip("\n"))
        if step.stderr:
            parts.append(step.stderr.rstrip("\n"))
    return "\n".join(part for part in parts if part)


def _size_to_bytes(size_value: str, unit: str) -> int:
    multipliers = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 * 1024,
    }
    return int(float(size_value) * multipliers[unit.upper()])


def _parse_memory_regions(stdout: str) -> list[dict[str, object]]:
    pattern = re.compile(
        r"^\s*(?P<name>[A-Za-z0-9_]+):\s+"
        r"(?P<used>\d+(?:\.\d+)?)\s+(?P<used_unit>B|KB|MB)\s+"
        r"(?P<total>\d+(?:\.\d+)?)\s+(?P<total_unit>B|KB|MB)\s+"
        r"(?P<percent>\d+(?:\.\d+)?)%$"
    )
    regions: list[dict[str, object]] = []
    for raw_line in stdout.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = pattern.match(raw_line.strip())
        if not match:
            continue
        regions.append(
            {
                "name": match.group("name"),
                "used": _size_to_bytes(match.group("used"), match.group("used_unit")),
                "total": _size_to_bytes(match.group("total"), match.group("total_unit")),
                "percent": float(match.group("percent")),
                "unit": "B",
            }
        )
    return regions


def _parse_source_stats(stdout: str) -> dict[str, int]:
    stats_pattern = re.compile(
        r"\|\s*(?P<c>\d+)\s*\|\s*(?P<cpp>\d+)\s*\|\s*(?P<asm>\d+)\s*\|\s*(?P<libobj>\d+)\s*\|\s*(?P<total>\d+)\s*\|"
    )
    jobs_pattern = re.compile(r"start compiling \(jobs:\s*(?P<jobs>\d+)\)")
    result: dict[str, int] = {}

    for raw_line in stdout.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        match = stats_pattern.search(line)
        if match:
            result.update(
                {
                    "cFiles": int(match.group("c")),
                    "cppFiles": int(match.group("cpp")),
                    "asmFiles": int(match.group("asm")),
                    "libObjFiles": int(match.group("libobj")),
                    "totalFiles": int(match.group("total")),
                }
            )
            continue
        match = jobs_pattern.search(line)
        if match:
            result["jobs"] = int(match.group("jobs"))

    return result


def _parse_embedded_task_failures(stdout: str) -> list[dict[str, str]]:
    task_pattern = re.compile(r"^>>\s*(?P<name>.+?)\s+\[(?P<status>done|failed)\]\s*$", re.IGNORECASE)
    current_section = "build-task"
    failures: list[dict[str, str]] = []

    for raw_line in stdout.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        lowered = line.lower()
        if lowered == "[ info ] pre-build tasks ...":
            current_section = "pre-build-task"
            continue
        if lowered == "[ info ] post-build tasks ...":
            current_section = "post-build-task"
            continue
        if lowered == "[ info ] start outputting files ...":
            current_section = "output-task"
            continue

        match = task_pattern.match(line)
        if match and match.group("status").lower() == "failed":
            failures.append(
                {
                    "kind": current_section,
                    "name": match.group("name").strip(),
                }
            )

    return failures


def rebuild_target(
    *,
    project_root: Path,
    project_name: str,
    target_name: str,
    target_index: int,
    target_total: int,
    dotnet_path: str,
    unify_builder_path: str,
    eide_tools_dir: str,
    toolchain_root: str,
) -> TargetResult:
    start_mark = time.perf_counter()
    started_at = utc_now()
    steps: list[StepResult] = []
    compiler_log = ""
    build_dir = _resolve_build_dir(project_root, f"build/{target_name}")
    compiler_log_path = build_dir / "compiler.log"
    builder_params_path = build_dir / "builder.params"
    stack_report_json_path = build_dir / "stack_report.json"
    stack_report_html_path = build_dir / "stack_report.html"
    builder_params_summary: dict[str, object] = {}
    memory: list[dict[str, object]] = []
    source_stats: dict[str, int] = {}
    error_code = "OK"
    message = ""
    exit_code = 0

    try:
        step_started_mark = time.perf_counter()
        step_started_at = utc_now()
        params = generate_builder_params(project_root, target_name, eide_tools_dir, toolchain_root)
        build_dir = _resolve_build_dir(project_root, str(params.get("dumpPath") or f"build/{target_name}"))
        compiler_log_path = build_dir / "compiler.log"
        stack_report_json_path = build_dir / "stack_report.json"
        stack_report_html_path = build_dir / "stack_report.html"
        builder_params_path = write_builder_params(project_root, target_name, params)
        step_finished_at = utc_now()
        builder_params_summary = {
            "toolchain": params.get("toolchain", ""),
            "threadNum": params.get("threadNum", 0),
            "sourceCount": len(list(params.get("sourceList") or [])),
            "dumpPath": params.get("dumpPath", ""),
        }
        hook_env = {str(key): str(value) for key, value in dict(params.get("env") or {}).items()}
        process_env = build_process_env(hook_env, toolchain_root)
        steps.append(
            _make_step_result(
                kind="generate-builder-params",
                name=f"generate {target_name} builder.params",
                started_at=step_started_at,
                finished_at=step_finished_at,
                duration_ms=elapsed_ms(step_started_mark),
                ok=True,
                error_code="OK",
                stdout=f"Generated: {normalize_path(builder_params_path.resolve())}\n",
            )
        )

        build_step = run_step(
            kind="unify-builder",
            name=f"build {target_name}",
            command=build_unify_builder_command(
                dotnet_path=dotnet_path,
                unify_builder_path=unify_builder_path,
                builder_params_path=normalize_path(builder_params_path.resolve()),
            ),
            cwd=project_root,
            env=process_env,
        )
        steps.append(build_step)

        if not build_step.ok:
            error_code = build_step.error_code if build_step.error_code == "STEP_TIMEOUT" else "UNIFY_BUILDER_FAILED"
            message = build_step.message or f"{target_name} build failed."
            exit_code = build_step.exit_code if build_step.error_code == "STEP_TIMEOUT" else 6
        elif compiler_log_path.exists():
            compiler_log = _read_text_file(compiler_log_path)
            memory = _parse_memory_regions(build_step.stdout)
            source_stats = _parse_source_stats(build_step.stdout)
            embedded_failures = _parse_embedded_task_failures(build_step.stdout)
            if embedded_failures:
                first_failure = embedded_failures[0]
                error_code_map = {
                    "pre-build-task": "PRE_BUILD_TASK_FAILED",
                    "post-build-task": "POST_BUILD_TASK_FAILED",
                    "output-task": "OUTPUT_TASK_FAILED",
                }
                error_code = error_code_map.get(first_failure["kind"], "BUILD_TASK_FAILED")
                message = f"{first_failure['name']} failed inside unify_builder."
                exit_code = 4
        else:
            error_code = "COMPILER_LOG_MISSING"
            message = f"compiler.log not found: {normalize_path(compiler_log_path)}"
            exit_code = 8
    except Exception as error:
        if exit_code == 0:
            error_code = "BUILDER_PARAMS_GENERATION_FAILED"
            message = str(error)
            exit_code = 4

    finished_at = utc_now()
    artifacts = collect_output_files(project_root, target_name, builder_params_summary.get("dumpPath") or None)
    transcript = _build_transcript(steps)
    return TargetResult(
        name=target_name,
        index=target_index,
        total=target_total,
        ok=exit_code == 0,
        exit_code=exit_code,
        error_code=error_code,
        message=message,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=elapsed_ms(start_mark),
        builder_params_path=normalize_path(builder_params_path.resolve()),
        builder_params_summary=builder_params_summary,
        compiler_log_path=normalize_path(compiler_log_path.resolve()),
        compiler_log=compiler_log,
        stack_report_json_path=normalize_path(stack_report_json_path.resolve()) if stack_report_json_path.exists() else "",
        stack_report_html_path=normalize_path(stack_report_html_path.resolve()) if stack_report_html_path.exists() else "",
        source_stats=source_stats,
        memory=memory,
        artifacts=artifacts,
        transcript=transcript,
        steps=steps,
    )
