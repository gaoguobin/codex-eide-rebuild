from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from .platform import current_platform, normalize_path


def _resolve_existing_path(path_value: str, expect_dir: bool = False) -> str:
    candidate = Path(path_value).expanduser()
    if expect_dir:
        if candidate.is_dir():
            return normalize_path(candidate.resolve())
    elif candidate.exists():
        return normalize_path(candidate.resolve())
    raise FileNotFoundError(str(candidate))


def _path_if_dir(path_value: Path) -> str | None:
    return normalize_path(path_value.resolve()) if path_value.is_dir() else None


def _version_key(path_value: Path) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+)+)", path_value.name)
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def _iter_existing_dirs(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        normalized = normalize_path(resolved)
        if normalized in seen or not resolved.is_dir():
            continue
        seen.add(normalized)
        result.append(resolved)
    return result


def _extension_roots() -> list[Path]:
    roots: list[Path] = []
    override = os.environ.get("EIDE_REBUILD_VSCODE_EXTENSIONS_ROOT")
    if override:
        roots.append(Path(override))
    home_override = os.environ.get("EIDE_REBUILD_HOME")
    if home_override:
        roots.append(Path(home_override) / ".vscode" / "extensions")
    roots.append(Path.home() / ".vscode" / "extensions")
    return _iter_existing_dirs(roots)


def find_eide_extension_dir() -> str:
    override = os.environ.get("EIDE_REBUILD_EIDE_EXTENSION_DIR")
    if override:
        return _resolve_existing_path(override, expect_dir=True)

    candidates: list[Path] = []
    for root in _extension_roots():
        candidates.extend(path for path in root.glob("cl.eide-*") if path.is_dir())
    if not candidates:
        raise FileNotFoundError("EIDE extension directory")

    best = sorted(
        candidates,
        key=lambda path: (_version_key(path), path.stat().st_mtime),
        reverse=True,
    )[0]
    return normalize_path(best.resolve())


def _candidate_model_dirs(base_dir: Path) -> list[Path]:
    return [
        base_dir,
        base_dir / "models",
        base_dir / "res" / "data" / "models",
        base_dir / "data" / "models",
    ]


def _resolve_model_dir(base_dir: Path) -> str | None:
    for candidate in _candidate_model_dirs(base_dir):
        if (candidate / "arm.gcc.model.json").exists():
            return normalize_path(candidate.resolve())
    return None


def find_dotnet() -> str:
    override = os.environ.get("EIDE_REBUILD_DOTNET") or os.environ.get("DOTNET_HOST_PATH")
    if override:
        return _resolve_existing_path(override)
    command_path = shutil.which("dotnet")
    if command_path:
        return normalize_path(Path(command_path).resolve())
    raise FileNotFoundError("dotnet")


def find_eide_tools_dir() -> str:
    override = os.environ.get("EIDE_REBUILD_EIDE_TOOLS_DIR") or os.environ.get("EIDE_TOOLS_DIR")
    if override:
        resolved = _resolve_model_dir(Path(override).expanduser())
        if resolved:
            return resolved
        raise FileNotFoundError(str(Path(override).expanduser()))

    extension_dir = Path(find_eide_extension_dir())
    resolved = _resolve_model_dir(extension_dir)
    if resolved:
        return resolved
    raise FileNotFoundError("EIDE tools directory")


def _platform_tool_dir(extension_dir: Path) -> Path:
    platform_name = current_platform()
    platform_folder = "win32" if platform_name == "windows" else platform_name
    return extension_dir / "res" / "tools" / platform_folder


def find_unify_builder() -> str:
    override = os.environ.get("EIDE_REBUILD_UNIFY_BUILDER")
    if override:
        return _resolve_existing_path(override)

    tools_override = os.environ.get("EIDE_REBUILD_EIDE_TOOLS_DIR") or os.environ.get("EIDE_TOOLS_DIR")
    if tools_override:
        direct_candidate = Path(tools_override).expanduser() / "unify_builder.dll"
        if direct_candidate.exists():
            return normalize_path(direct_candidate.resolve())

    unify_root = _platform_tool_dir(Path(find_eide_extension_dir())) / "unify_builder"
    candidate_names = ["unify_builder.exe", "unify_builder.dll"] if current_platform() == "windows" else ["unify_builder.dll"]
    for candidate_name in candidate_names:
        candidate = unify_root / candidate_name
        if candidate.exists():
            return normalize_path(candidate.resolve())
    raise FileNotFoundError("unify_builder.dll")


def resolve_unify_builder_dll(unify_builder_path: str) -> str:
    path_obj = Path(unify_builder_path)
    if path_obj.suffix.lower() == ".dll":
        return normalize_path(path_obj.resolve())

    sibling_dll = path_obj.with_suffix(".dll")
    if sibling_dll.exists():
        return normalize_path(sibling_dll.resolve())

    raise FileNotFoundError(str(sibling_dll))


def find_eide_utils_dir() -> str:
    override = os.environ.get("EIDE_REBUILD_EIDE_UTILS_DIR")
    if override:
        return _resolve_existing_path(override, expect_dir=True)

    utils_dir = _platform_tool_dir(Path(find_eide_extension_dir())) / "utils"
    resolved = _path_if_dir(utils_dir)
    if resolved:
        return resolved
    raise FileNotFoundError("EIDE utils directory")


def _toolchain_search_roots() -> list[Path]:
    roots: list[Path] = []
    override = os.environ.get("EIDE_REBUILD_TOOLS_ROOT")
    if override:
        roots.append(Path(override))
    home_override = os.environ.get("EIDE_REBUILD_HOME")
    if home_override:
        roots.append(Path(home_override) / ".eide" / "tools")
    roots.append(Path.home() / ".eide" / "tools")
    return _iter_existing_dirs(roots)


def find_toolchain_root() -> str:
    override = os.environ.get("EIDE_REBUILD_TOOLCHAIN_ROOT") or os.environ.get("COMPILER_DIR")
    if override:
        return _resolve_existing_path(override, expect_dir=True)

    candidates: list[Path] = []
    for root in _toolchain_search_roots():
        for gcc_path in root.glob("**/bin/arm-none-eabi-gcc.exe"):
            candidates.append(gcc_path.parent.parent)
        for gcc_path in root.glob("**/bin/arm-none-eabi-gcc"):
            candidates.append(gcc_path.parent.parent)
    if not candidates:
        raise FileNotFoundError("toolchain root")

    best = sorted(
        candidates,
        key=lambda path: (_version_key(path), path.stat().st_mtime),
        reverse=True,
    )[0]
    return normalize_path(best.resolve())


def build_process_env(extra_env: dict[str, str] | None, toolchain_root: str) -> dict[str, str]:
    env = os.environ.copy()
    if extra_env:
        env.update({str(key): str(value) for key, value in extra_env.items()})

    path_parts: list[str] = []
    try:
        path_parts.append(str(Path(find_eide_utils_dir()).resolve()))
    except FileNotFoundError:
        pass

    toolchain_bin = Path(toolchain_root) / "bin"
    if toolchain_bin.is_dir():
        path_parts.append(str(toolchain_bin.resolve()))

    existing_path = env.get("PATH", "")
    if existing_path:
        path_parts.append(existing_path)
    env["PATH"] = os.pathsep.join(path_parts)
    return env


def check_unify_builder_runtime(dotnet_path: str, unify_builder_path: str) -> dict[str, object]:
    unify_builder_dll = resolve_unify_builder_dll(unify_builder_path)
    runtime_config = Path(unify_builder_dll).with_suffix(".runtimeconfig.json")
    framework_name = ""
    framework_version = ""
    if runtime_config.exists():
        payload = json.loads(runtime_config.read_text(encoding="utf-8"))
        runtime_options = payload.get("runtimeOptions") or {}
        framework = runtime_options.get("framework") or {}
        framework_name = str(framework.get("name") or "")
        framework_version = str(framework.get("version") or "")

    completed = subprocess.run(
        [dotnet_path, "exec", "--roll-forward", "Major", unify_builder_dll, "-v"],
        capture_output=True,
        text=True,
        check=False,
    )
    ok = completed.returncode == 0
    message = ""
    if not ok:
        message = completed.stderr.strip() or completed.stdout.strip() or "Failed to start unify_builder."

    installed_versions: list[str] = []
    runtimes = subprocess.run(
        [dotnet_path, "--list-runtimes"],
        capture_output=True,
        text=True,
        check=False,
    )
    if runtimes.returncode == 0 and framework_name:
        for raw_line in runtimes.stdout.splitlines():
            match = re.match(r"^(?P<name>\S+)\s+(?P<version>\d+\.\d+\.\d+)", raw_line.strip())
            if not match or match.group("name") != framework_name:
                continue
            installed_versions.append(match.group("version"))

    return {
        "ok": ok,
        "requiredFramework": framework_name,
        "requiredVersion": framework_version,
        "installedVersions": installed_versions,
        "message": message,
        "launchCommand": [dotnet_path, "exec", "--roll-forward", "Major", unify_builder_dll, "-v"],
    }


def run_doctor() -> dict[str, object]:
    tools: dict[str, str] = {}
    errors: list[str] = []
    runtime_info: dict[str, object] = {"ok": True}

    checks = {
        "dotnet": find_dotnet,
        "eideExtensionDir": find_eide_extension_dir,
        "eideToolsDir": find_eide_tools_dir,
        "eideUtilsDir": find_eide_utils_dir,
        "unifyBuilder": find_unify_builder,
        "toolchainRoot": find_toolchain_root,
    }

    for name, getter in checks.items():
        try:
            tools[name] = getter()
        except FileNotFoundError as error:
            errors.append(f"{name}: {error}")

    if "dotnet" in tools and "unifyBuilder" in tools:
        runtime_info = check_unify_builder_runtime(tools["dotnet"], tools["unifyBuilder"])
        if not runtime_info.get("ok", False):
            errors.append(str(runtime_info.get("message") or "Unify builder runtime check failed."))

    ok = not errors
    return {
        "ok": ok,
        "exitCode": 0 if ok else 3,
        "errorCode": "OK" if ok else "TOOL_NOT_FOUND",
        "message": "" if ok else "; ".join(errors),
        "platform": current_platform(),
        "tools": tools,
        "runtime": runtime_info,
    }
