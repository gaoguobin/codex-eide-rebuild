from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .eide_model import load_eide_model, require_yaml_module


SOURCE_EXTS = {".c", ".cpp", ".cc", ".cxx", ".s", ".a", ".o", ".lib", ".obj"}
_CPP_EXTS = {".cpp", ".cc", ".cxx"}
_MODEL_FILE_ALIASES = {
    ("8051", "keil"): ["8051.keil.model.json"],
    ("any", "gcc"): ["any.gcc.model.json"],
    ("arm", "ac5"): ["arm.v5.model.json"],
    ("arm", "ac6"): ["arm.v6.model.json", "arm.llvm.model.json"],
    ("arm", "armcc"): ["arm.v5.model.json"],
    ("arm", "armclang"): ["arm.v6.model.json", "arm.llvm.model.json"],
    ("arm", "gcc"): ["arm.gcc.model.json"],
    ("arm", "iar"): ["arm.iar.model.json"],
    ("arm", "llvm"): ["arm.llvm.model.json"],
    ("mcs51", "sdcc"): ["sdcc.mcs51.model.json", "sdcc.model.json"],
    ("mips", "gcc"): ["mips.mti.gcc.model.json"],
    ("riscv", "gcc"): ["riscv.gcc.model.json"],
    ("sdcc", "sdcc"): ["sdcc.model.json"],
    ("stm8", "cosmic"): ["stm8.cosmic.model.json"],
    ("stm8", "iar"): ["stm8.iar.model.json"],
}
_FALLBACK_TOOL_PREFIX = {
    ("arm", "gcc"): "arm-none-eabi-",
    ("mips", "gcc"): "mips-mti-elf-",
    ("riscv", "gcc"): "riscv-none-elf-",
}


def _to_posix(path_value: Path | str) -> str:
    return str(path_value).replace("\\", "/")


def _normalize_model_key(value: str) -> str:
    token = str(value or "").strip().lower()
    for separator in (" ", "-", "_", "/", "\\"):
        token = token.replace(separator, ".")
    while ".." in token:
        token = token.replace("..", ".")
    return token.strip(".")


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


def _build_target_path(root_path: str, target: str) -> str:
    normalized_root = _to_posix(root_path).strip("/")
    if not normalized_root:
        return target
    root_obj = Path(normalized_root)
    if root_obj.is_absolute():
        return _to_posix(root_obj / target)
    return f"{normalized_root}/{target}"


def _resolve_output_dir(project_root: Path, output_path: str) -> Path:
    path_obj = Path(output_path)
    if path_obj.is_absolute():
        return path_obj.resolve()
    return (project_root / path_obj).resolve()


def _candidate_model_names(project_type: str, toolchain: str) -> list[str]:
    project_key = _normalize_model_key(project_type) or "arm"
    toolchain_key = _normalize_model_key(toolchain) or "gcc"
    candidates = list(_MODEL_FILE_ALIASES.get((project_key, toolchain_key), []))
    generic = f"{project_key}.{toolchain_key}.model.json"
    if generic not in candidates:
        candidates.append(generic)
    return candidates


def _resolve_toolchain_cfg_file(eide_tools_dir: str, project_type: str, toolchain: str) -> str:
    eide_tools_root = Path(str(eide_tools_dir).rstrip("/\\"))
    candidate_names = _candidate_model_names(project_type, toolchain)
    if eide_tools_root.is_dir():
        for candidate_name in candidate_names:
            candidate_path = eide_tools_root / candidate_name
            if candidate_path.exists():
                return _to_posix(candidate_path.resolve())
    return _to_posix(eide_tools_root / candidate_names[0])


def _load_toolchain_model(toolchain_cfg_file: str) -> dict[str, Any]:
    path_obj = Path(toolchain_cfg_file)
    if not path_obj.exists():
        return {}
    try:
        payload = json.loads(path_obj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _fallback_tool_prefix(project_type: str, toolchain: str) -> str:
    return _FALLBACK_TOOL_PREFIX.get((_normalize_model_key(project_type), _normalize_model_key(toolchain)), "")


def _load_project_env(eide_dir: Path, target: str) -> dict[str, str]:
    env_path = eide_dir / "env.ini"
    if not env_path.exists():
        return {}

    global_values: dict[str, str] = {}
    target_values: dict[str, str] = {}
    current_section = ""
    target_section = str(target or "").strip().lower()

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().lower()
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if not current_section:
            global_values[key] = value
        elif current_section == target_section:
            target_values[key] = value

    merged = dict(global_values)
    merged.update(target_values)
    return merged


def _pre_handle_options(
    options: dict[str, Any],
    source_list: list[str],
    cpu_type: str,
    fp_hardware: str,
    arch_extensions: str,
    scatter_path: str,
    root_dir: Path,
    *,
    tool_prefix: str = "",
    toolchain_name: str = "gcc",
) -> None:
    global_options = options.setdefault("global", {})
    linker_options = options.setdefault("linker", {})

    if tool_prefix:
        global_options["toolPrefix"] = tool_prefix
    if _normalize_model_key(toolchain_name) == "gcc":
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


def _build_env(
    project_name: str,
    target: str,
    root_dir: Path,
    toolchain_loc: str,
    *,
    out_dir_root: str,
    chip_pack_dir: str,
    chip_name: str,
    extra_env: dict[str, str],
) -> dict[str, str]:
    root = _to_posix(root_dir)
    is_windows = os.name == "nt"
    dir_sep = "\\" if is_windows else "/"
    path_sep = ";" if is_windows else ":"
    out_dir_root_value = _to_posix(out_dir_root).strip("/") or "build"
    out_dir_base = _build_target_path(out_dir_root_value, target)
    out_dir = _join_posix(root_dir, out_dir_base)
    env = {
        "workspaceFolder": root,
        "workspaceFolderBasename": os.path.basename(root),
        "OutDir": out_dir,
        "OutDirRoot": out_dir_root_value,
        "OutDirBase": out_dir_base,
        "ProjectName": project_name,
        "ConfigName": target,
        "ProjectRoot": root,
        "ExecutableName": _join_posix(root_dir, f"{out_dir_base}/{project_name}"),
        "ChipPackDir": chip_pack_dir,
        "ChipName": chip_name,
        "SYS_Platform": "windows" if is_windows else "linux",
        "SYS_DirSep": dir_sep,
        "SYS_DirSeparator": dir_sep,
        "SYS_PathSep": path_sep,
        "SYS_PathSeparator": path_sep,
        "SYS_EOL": "\n",
        "ToolchainRoot": toolchain_loc,
    }
    env.update(extra_env)
    return env


def _load_source_params(eide_dir: Path, target: str) -> dict[str, Any]:
    files_options_path = eide_dir / "files.options.yml"
    if not files_options_path.exists():
        return {}
    yaml_module = require_yaml_module()
    with files_options_path.open("r", encoding="utf-8") as stream:
        files_opts = yaml_module.safe_load(stream) or {}
    source_params = (((files_opts.get("options") or {}).get(target) or {}).get("files") or {})
    if isinstance(source_params, dict):
        return source_params
    return {}


def generate_builder_params(project_root: Path, target: str, eide_tools_dir: str, toolchain_root: str) -> dict[str, Any]:
    root_dir = Path(project_root).resolve()
    eide_dir = root_dir / ".eide"
    model = load_eide_model(eide_dir / "eide.yml")
    target_data = (model.payload.get("targets") or {})[target]
    project_type = str(model.payload.get("type") or "ARM")
    out_dir_root = str(model.payload.get("outDir") or "build")
    chip_pack_dir = str(model.payload.get("packDir") or "")
    chip_name = str(model.payload.get("deviceName") or "")
    toolchain = str(target_data.get("toolchain") or "GCC")
    toolchain_cfg = ((target_data.get("toolchainConfigMap") or {}).get(toolchain) or {})
    cpp_attrs = target_data.get("cppPreprocessAttrs") or {}
    relative_sources = collect_sources(model.payload.get("virtualFolder") or {}, list(target_data.get("excludeList") or []))
    source_list = relative_sources
    options = copy.deepcopy(toolchain_cfg.get("options") or {})
    toolchain_cfg_file = _resolve_toolchain_cfg_file(eide_tools_dir, project_type, toolchain)
    toolchain_model = _load_toolchain_model(toolchain_cfg_file)
    tool_prefix = str(
        (options.get("global") or {}).get("toolPrefix")
        or toolchain_model.get("toolPrefix")
        or _fallback_tool_prefix(project_type, toolchain)
    )

    _pre_handle_options(
        options,
        source_list,
        str(toolchain_cfg.get("cpuType") or ""),
        str(toolchain_cfg.get("floatingPointHardware") or ""),
        str(toolchain_cfg.get("archExtensions") or ""),
        str(toolchain_cfg.get("scatterFilePath") or ""),
        root_dir,
        tool_prefix=tool_prefix,
        toolchain_name=toolchain,
    )

    dump_path = _build_target_path(out_dir_root, target)
    return {
        "name": model.project_name,
        "target": target,
        "toolchain": toolchain,
        "toolchainLocation": _to_posix(toolchain_root),
        "toolchainCfgFile": toolchain_cfg_file,
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
        "env": _build_env(
            model.project_name,
            target,
            root_dir,
            toolchain_root,
            out_dir_root=out_dir_root,
            chip_pack_dir=chip_pack_dir,
            chip_name=chip_name,
            extra_env=_load_project_env(eide_dir, target),
        ),
        "sysPaths": [],
    }


def write_builder_params(project_root: Path, target: str, params: dict[str, Any]) -> Path:
    dump_path = str(params.get("dumpPath") or _build_target_path("build", target))
    output_path = _resolve_output_dir(Path(project_root).resolve(), dump_path) / "builder.params"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(params, stream, indent=4, ensure_ascii=False)
    return output_path
