from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from .builder_params import generate_builder_params, write_builder_params
from .eide_model import EideModel, load_eide_model
from .executor import build_unify_builder_command, collect_output_files, rebuild_target, run_step
from .platform import current_platform, elapsed_ms, normalize_path, utc_now
from .project import ProjectInput, resolve_project_input
from .result_model import (
    RunResult,
    StepResult,
    TargetResult,
    build_agent_summary,
    build_error_result,
    build_minimal_summary,
    build_run_result,
    render_agent_summary_result,
    render_json_result,
    render_minimal_summary_result,
    write_run_result,
)
from .tools import (
    build_process_env,
    check_eide_mcp_health,
    check_unify_builder_runtime,
    find_dotnet,
    find_eide_extension_dir,
    find_eide_tools_dir,
    find_eide_utils_dir,
    find_toolchain_root,
    find_unify_builder,
    run_doctor,
)


class ExitError(RuntimeError):
    def __init__(self, exit_code: int, message: str, error_code: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.error_code = error_code


__all__ = [
    "EideModel",
    "ExitError",
    "ProjectInput",
    "RunResult",
    "StepResult",
    "TargetResult",
    "build_agent_summary",
    "build_error_result",
    "build_minimal_summary",
    "build_run_result",
    "build_unify_builder_command",
    "build_process_env",
    "check_eide_mcp_health",
    "check_unify_builder_runtime",
    "collect_output_files",
    "current_platform",
    "elapsed_ms",
    "find_dotnet",
    "find_eide_extension_dir",
    "find_eide_tools_dir",
    "find_eide_utils_dir",
    "find_toolchain_root",
    "find_unify_builder",
    "generate_builder_params",
    "load_eide_model",
    "main",
    "normalize_path",
    "rebuild_target",
    "render_agent_summary_result",
    "render_json_result",
    "render_minimal_summary_result",
    "resolve_project_input",
    "run_doctor",
    "run_step",
    "utc_now",
    "write_builder_params",
    "write_run_result",
]


STDOUT_MODES = {"full", "summary", "minimal"}


def _resolve_project_input_or_raise(input_path: str) -> ProjectInput:
    try:
        return resolve_project_input(input_path)
    except RuntimeError as error:
        raise ExitError(2, str(error), "MULTIPLE_WORKSPACES") from error
    except FileNotFoundError as error:
        missing_path = str(error)
        error_code = "EIDE_YML_NOT_FOUND" if missing_path.replace("\\", "/").endswith("/.eide/eide.yml") else "PROJECT_PATH_NOT_FOUND"
        raise ExitError(2, missing_path, error_code) from error


def _resolve_required_tools(workspace_path: str = "") -> tuple[str, str, str, str]:
    try:
        tool_paths = (
            find_dotnet(),
            find_unify_builder(),
            find_eide_tools_dir(),
            find_toolchain_root(workspace_path),
        )
        runtime_check = check_unify_builder_runtime(tool_paths[0], tool_paths[1])
        if not runtime_check.get("ok", False):
            raise ExitError(7, str(runtime_check.get("message") or "Unify builder runtime check failed."), "DOTNET_RUNTIME_MISSING")
        return tool_paths
    except FileNotFoundError as error:
        raise ExitError(3, str(error), getattr(error, "error_code", "TOOL_NOT_FOUND")) from error


def _parse_rebuild_arguments(arguments: list[str]) -> tuple[str, str]:
    if not arguments or arguments[0] != "rebuild":
        raise ExitError(2, "Missing command or path.", "WORKSPACE_NOT_FOUND")

    stdout_mode = "full"
    paths: list[str] = []
    index = 1
    while index < len(arguments):
        token = arguments[index]
        if token == "--stdout":
            index += 1
            if index >= len(arguments):
                raise ExitError(2, "Missing value for --stdout.", "INVALID_ARGUMENT")
            stdout_mode = arguments[index]
        elif token.startswith("--stdout="):
            stdout_mode = token.split("=", 1)[1]
        elif token.startswith("-"):
            raise ExitError(2, f"Unknown option: {token}", "INVALID_ARGUMENT")
        else:
            paths.append(token)
        index += 1

    if stdout_mode not in STDOUT_MODES:
        raise ExitError(2, f"Invalid --stdout value: {stdout_mode}. Expected full, summary, or minimal.", "INVALID_ARGUMENT")
    if len(paths) != 1:
        raise ExitError(2, "Missing command or path.", "WORKSPACE_NOT_FOUND")
    return paths[0], stdout_mode


def _render_stdout_result(result: RunResult, stdout_mode: str) -> str:
    if stdout_mode == "minimal":
        return render_minimal_summary_result(result)
    if stdout_mode == "summary":
        return render_agent_summary_result(result)
    return render_json_result(result)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    started_mark = time.perf_counter()
    started_at = utc_now()
    stdout_mode = "full"

    try:
        if arguments and arguments[0] == "doctor":
            doctor_result = run_doctor()
            sys.stdout.write(json.dumps(doctor_result, ensure_ascii=False, indent=2) + "\n")
            return int(doctor_result["exitCode"])

        input_path, stdout_mode = _parse_rebuild_arguments(arguments)
        project_input = _resolve_project_input_or_raise(input_path)
        model = load_eide_model(project_input.eide_yml_path)
        if not model.target_names:
            raise ExitError(6, "No targets found in .eide/eide.yml.", "TARGETS_NOT_FOUND")

        dotnet_path, unify_builder_path, eide_tools_dir, toolchain_root = _resolve_required_tools(project_input.workspace_path)

        target_results: list[TargetResult] = []
        transcript_parts: list[str] = []
        for index, target_name in enumerate(model.target_names, start=1):
            target_result = rebuild_target(
                project_root=project_input.project_root,
                project_name=model.project_name,
                target_name=target_name,
                target_index=index,
                target_total=len(model.target_names),
                dotnet_path=dotnet_path,
                unify_builder_path=unify_builder_path,
                eide_tools_dir=eide_tools_dir,
                toolchain_root=toolchain_root,
            )
            target_results.append(target_result)
            if target_result.transcript:
                transcript_parts.append(target_result.transcript)

        finished_at = utc_now()
        result_path = project_input.project_root / "build" / "rebuild_result.json"
        run_result = build_run_result(
            workspace_path=project_input.workspace_path,
            project_root=project_input.project_root,
            project_name=model.project_name,
            platform_name=current_platform(),
            target_names=model.target_names,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=elapsed_ms(started_mark),
            targets=target_results,
            transcript="\n".join(transcript_parts),
            project_uid=model.project_uid,
            result_path=result_path,
        )
        write_run_result(result_path, run_result)
        sys.stdout.write(_render_stdout_result(run_result, stdout_mode))
        return run_result.exit_code
    except ExitError as error:
        finished_at = utc_now()
        run_result = build_error_result(error, started_at, finished_at, elapsed_ms(started_mark))
        sys.stdout.write(_render_stdout_result(run_result, stdout_mode))
        return error.exit_code
    except Exception as error:
        finished_at = utc_now()
        wrapped_error = ExitError(7, str(error), "INTERNAL_ERROR")
        run_result = build_error_result(wrapped_error, started_at, finished_at, elapsed_ms(started_mark))
        sys.stdout.write(_render_stdout_result(run_result, stdout_mode))
        return wrapped_error.exit_code
