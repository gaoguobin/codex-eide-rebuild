from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import yaml

from .eide_model import load_eide_model


SOURCE_EXTS = {".c", ".cpp", ".cc", ".cxx", ".s", ".a", ".o", ".lib", ".obj"}
_CPP_EXTS = {".cpp", ".cc", ".cxx"}
_ARM_TOOL_PREFIX = "arm-none-eabi-"


def _to_posix(path_value: Path | str) -> str:
    return str(path_value).replace("\\", "/")


def _join_posix(root_dir: Path, path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return _to_posix(path)
    return _to_posix(root_dir / path)


def _is_excluded(vpath: str, exclude_list: list[Any]) -> bool:
    normalized = _to_posix(vpath).strip("/")
    for entry in exclude_list:
        excluded = _to_posix(str(entry)).strip("/")
        if normalized == excluded or normalized.startswith(f"{excluded}/"):
            return True
    return False


def collect_sources(folder: dict[str, Any], exclude_list: list[Any], parent_vpath: str = "<virtual_root>") -> list[str]:
    sources: list[str] = []

    for file_entry in folder.get("files") or []:
        file_path = _to_posix(str((file_entry or {}).get("path", "")))
        if Path(file_path).suffix.lower() not in SOURCE_EXTS:
            continue
        file_name = str((file_entry or {}).get("name") or Path(file_path).name)
        file_vpath = f"{parent_vpath}/{file_name}"
        if _is_excluded(file_vpath, exclude_list):
            continue
        sources.append(file_path)

    for child in folder.get("folders") or []:
        child_folder = child or {}
        child_name = str(child_folder.get("name") or "")
        child_vpath = f"{parent_vpath}/{child_name}" if child_name else parent_vpath
        if _is_excluded(child_vpath, exclude_list):
            continue
        sources.extend(collect_sources(child_folder, exclude_list, child_vpath))

    return sorted(sources)


def _pre_handle_options(
    options: dict[str, Any],
    source_list: list[str],
    cpu_type: str,
    fp_hardware: str,
    arch_extensions: str,
    scatter_path: str,
    root_dir: Path,
) -> None:
    global_options = options.setdefault("global", {})
    linker_options = options.setdefault("linker", {})

    global_options["toolPrefix"] = _ARM_TOOL_PREFIX
    linker_options["$toolName"] = "g++" if any(Path(source).suffix.lower() in _CPP_EXTS for source in source_list) else "gcc"

    fpu_suffix = {"single": "-sp", "double": "-dp"}.get(str(fp_hardware or "").lower(), "")
    cpu_fpu_id = f"{str(cpu_type).lower()}{fpu_suffix}"
    global_options["microcontroller-cpu"] = cpu_fpu_id
    global_options["microcontroller-fpu"] = cpu_fpu_id
    global_options["microcontroller-float"] = cpu_fpu_id
    global_options["$arch-extensions"] = arch_extensions or ""
    global_options["$clang-arch-extensions"] = ""
    global_options["$armlink-arch-extensions"] = ""

    if str(linker_options.get("output-format") or "").lower() == "lib":
        linker_options["$use"] = "linker-lib"
        linker_options.pop("link-scatter", None)
    elif scatter_path:
        linker_options["link-scatter"] = [_join_posix(root_dir, scatter_path)]

    before_build_tasks = options.get("beforeBuildTasks")
    after_build_tasks = options.get("afterBuildTasks")
    options["beforeBuildTasks"] = list(before_build_tasks) if isinstance(before_build_tasks, list) else []
    options["afterBuildTasks"] = list(after_build_tasks) if isinstance(after_build_tasks, list) else []


def _build_env(project_name: str, target: str, root_dir: Path, toolchain_loc: str) -> dict[str, str]:
    root = _to_posix(root_dir)
    is_windows = os.name == "nt"
    dir_sep = "\\" if is_windows else "/"
    path_sep = ";" if is_windows else ":"
    out_dir = f"{root}/build/{target}"
    return {
        "workspaceFolder": root,
        "workspaceFolderBasename": os.path.basename(root),
        "OutDir": out_dir,
        "OutDirRoot": "build",
        "OutDirBase": f"build/{target}",
        "ProjectName": project_name,
        "ConfigName": target,
        "ProjectRoot": root,
        "ExecutableName": f"{root}/build/{target}/{project_name}",
        "ChipPackDir": "",
        "ChipName": "",
        "SYS_Platform": "windows" if is_windows else "linux",
        "SYS_DirSep": dir_sep,
        "SYS_DirSeparator": dir_sep,
        "SYS_PathSep": path_sep,
        "SYS_PathSeparator": path_sep,
        "SYS_EOL": "\n",
        "ToolchainRoot": toolchain_loc,
    }


def _load_source_params(eide_dir: Path, target: str) -> dict[str, Any]:
    files_options_path = eide_dir / "files.options.yml"
    if not files_options_path.exists():
        return {}
    with files_options_path.open("r", encoding="utf-8") as stream:
        files_opts = yaml.safe_load(stream) or {}
    source_params = (((files_opts.get("options") or {}).get(target) or {}).get("files") or {})
    if isinstance(source_params, dict):
        return source_params
    return {}


def generate_builder_params(project_root: Path, target: str, eide_tools_dir: str, toolchain_root: str) -> dict[str, Any]:
    root_dir = Path(project_root).resolve()
    eide_dir = root_dir / ".eide"
    model = load_eide_model(eide_dir / "eide.yml")
    target_data = (model.payload.get("targets") or {})[target]
    toolchain = str(target_data.get("toolchain") or "GCC")
    toolchain_cfg = ((target_data.get("toolchainConfigMap") or {}).get(toolchain) or {})
    cpp_attrs = target_data.get("cppPreprocessAttrs") or {}
    relative_sources = collect_sources(model.payload.get("virtualFolder") or {}, list(target_data.get("excludeList") or []))
    source_list = relative_sources
    options = copy.deepcopy(toolchain_cfg.get("options") or {})

    _pre_handle_options(
        options,
        source_list,
        str(toolchain_cfg.get("cpuType") or ""),
        str(toolchain_cfg.get("floatingPointHardware") or ""),
        str(toolchain_cfg.get("archExtensions") or ""),
        str(toolchain_cfg.get("scatterFilePath") or ""),
        root_dir,
    )

    dump_path = f"build/{target}"
    return {
        "name": model.project_name,
        "target": target,
        "toolchain": toolchain,
        "toolchainLocation": _to_posix(toolchain_root),
        "toolchainCfgFile": _to_posix(f"{eide_tools_dir.rstrip('/').rstrip('\\\\')}/arm.gcc.model.json"),
        "buildMode": "fast|multhread",
        "showRepathOnLog": True,
        "threadNum": os.cpu_count() or 4,
        "rootDir": _to_posix(root_dir),
        "dumpPath": dump_path,
        "outDir": dump_path,
        "incDirs": list(cpp_attrs.get("incList") or []),
        "libDirs": list(cpp_attrs.get("libList") or []),
        "defines": list(cpp_attrs.get("defineList") or []),
        "sourceList": source_list,
        "alwaysInBuildSources": [],
        "sourceParams": _load_source_params(eide_dir, target),
        "options": options,
        "env": _build_env(model.project_name, target, root_dir, toolchain_root),
        "sysPaths": [],
    }


def write_builder_params(project_root: Path, target: str, params: dict[str, Any]) -> Path:
    output_path = Path(project_root).resolve() / "build" / target / "builder.params"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(params, stream, indent=4, ensure_ascii=False)
    return output_path
