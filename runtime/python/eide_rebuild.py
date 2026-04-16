#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import hashlib
import json
import locale
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

if os.name == "nt":
    import msvcrt


# --- Constants ---

CLI_PREFIX = "[EIDE-CLI]"
BRIDGE_PUBLISHER = "eide-rebuild"
BRIDGE_NAME = "cli-bridge"
BRIDGE_ID = f"{BRIDGE_PUBLISHER}.{BRIDGE_NAME}"
BRIDGE_VERSION = "0.1.0"
BRIDGE_READY_TIMEOUT_MS = 30_000
PIPE_CONNECT_TIMEOUT_MS = 5_000

if os.name == "nt":
    KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3
    ERROR_PIPE_BUSY = 231
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


# --- Errors ---

class ExitError(RuntimeError):
    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# --- Data ---

@dataclass
class ProtocolState:
    workspace: str = ""
    target: str = ""
    log_path: str = ""
    result: str = "error"
    duration_ms: str = ""
    exit_code: int = 7
    compiler_log: str = ""


# --- Protocol ---

def write_stderr_line(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def render_protocol(state: ProtocolState) -> str:
    lines = [
        f"{CLI_PREFIX} begin workspace={state.workspace}",
        f"{CLI_PREFIX} target={state.target}",
        f"{CLI_PREFIX} logPath={state.log_path}",
        f"{CLI_PREFIX} result={state.result}",
        f"{CLI_PREFIX} durationMs={state.duration_ms}",
        f"{CLI_PREFIX} compiler-log-begin",
    ]
    output = "\n".join(lines) + "\n"
    if state.compiler_log:
        output += state.compiler_log
        if not state.compiler_log.endswith("\n") and not state.compiler_log.endswith("\r"):
            output += "\n"
    output += f"{CLI_PREFIX} compiler-log-end\n"
    output += f"{CLI_PREFIX} end exitCode={state.exit_code}\n"
    return output


def show_usage() -> None:
    write_stderr_line("Usage: python eide_rebuild.py rebuild <workspace-or-project-path>")


# --- Paths ---

def ensure_windows() -> None:
    if os.name != "nt":
        raise ExitError(7, "This runner supports Windows only.")


def get_local_appdata_root() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata)
    return Path.home() / "AppData" / "Local"


def get_registration_root() -> Path:
    override = os.environ.get("EIDE_REBUILD_REGISTRATION_ROOT")
    if override:
        return Path(override)
    return Path.home() / ".vscode" / "eide-rebuild" / "registrations"


def get_registration_roots() -> list[Path]:
    roots = [get_registration_root()]
    legacy_root = get_local_appdata_root() / ("EIDE" + "_CLI") / "registrations"
    if legacy_root not in roots:
        roots.append(legacy_root)
    return roots


def get_extensions_root() -> Path:
    override = os.environ.get("EIDE_REBUILD_EXTENSIONS_ROOT")
    if override:
        return Path(override)
    return Path.home() / ".vscode" / "extensions"


def resolve_full_path(path_value: str) -> Path:
    path_obj = Path(path_value).expanduser()
    if not path_obj.exists():
        raise ExitError(2, f"Path does not exist: {path_value}")
    return path_obj.resolve()


def resolve_workspace_path(input_path: str) -> Path:
    resolved_path = resolve_full_path(input_path)
    if resolved_path.is_dir():
        workspace_files = sorted(resolved_path.glob("*.code-workspace"))
        if len(workspace_files) == 1:
            return workspace_files[0].resolve()
        if not workspace_files:
            raise ExitError(2, f"No .code-workspace file found in directory: {resolved_path}")
        raise ExitError(2, f"Multiple .code-workspace files found in directory: {resolved_path}")

    if resolved_path.suffix.lower() == ".code-workspace":
        return resolved_path

    raise ExitError(2, f"Expected a .code-workspace file or a project directory: {resolved_path}")


def normalize_workspace_path(workspace_path: Path | str) -> str:
    return str(Path(workspace_path).resolve()).replace("/", "\\").lower()


def get_workspace_hash(workspace_path: Path | str) -> str:
    normalized = normalize_workspace_path(workspace_path)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def get_registration_path(workspace_path: Path | str) -> Path:
    return get_registration_root() / f"{get_workspace_hash(workspace_path)}.json"


def get_registration_paths(workspace_path: Path | str) -> list[Path]:
    workspace_hash = get_workspace_hash(workspace_path)
    return [root / f"{workspace_hash}.json" for root in get_registration_roots()]


def get_bridge_vsix_name() -> str:
    return f"{BRIDGE_ID}-{BRIDGE_VERSION}.vsix"


def discover_vsix_path(script_dir: Path) -> Path:
    override = os.environ.get("EIDE_REBUILD_BRIDGE_VSIX")
    if override:
        vsix_path = Path(override)
        if vsix_path.exists():
            return vsix_path.resolve()
        raise ExitError(7, f"Bundled bridge VSIX not found: {vsix_path}")

    candidates = [
        script_dir.parent / "assets" / get_bridge_vsix_name(),
        script_dir.parent / "bridge" / "dist" / get_bridge_vsix_name(),
        script_dir.parent.parent / "runtime" / "bridge" / "dist" / get_bridge_vsix_name(),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    raise ExitError(7, f"Bundled bridge VSIX not found: {candidates[-1]}")


# --- Commands ---

def get_code_command_path() -> Path:
    override = os.environ.get("EIDE_REBUILD_CODE_CMD")
    if override:
        code_path = Path(override)
        if code_path.exists():
            return code_path.resolve()
        raise ExitError(3, f"Configured VS Code CLI command does not exist: {code_path}")

    for command_name in ("code", "code.cmd"):
        command_path = shutil.which(command_name)
        if command_path:
            return Path(command_path)

    fallback_paths = [
        get_local_appdata_root() / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd",
        Path(os.environ.get("ProgramFiles", "")) / "Microsoft VS Code" / "bin" / "code.cmd",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft VS Code" / "bin" / "code.cmd",
    ]

    for candidate in fallback_paths:
        if str(candidate) and candidate.exists():
            return candidate.resolve()

    raise ExitError(3, "Cannot find VS Code CLI command 'code'.")


def run_code_command(command_path: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    command_text = str(command_path)
    if command_path.suffix.lower() in {".cmd", ".bat"}:
        command = ["cmd.exe", "/d", "/c", command_text, *arguments]
    else:
        command = [command_text, *arguments]

    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# --- Bridge install ---

def is_bridge_installed() -> bool:
    extensions_root = get_extensions_root()
    if not extensions_root.exists():
        return False
    return any(extensions_root.glob(f"{BRIDGE_ID}-*"))


def install_bridge_from_vsix_fallback(vsix_path: Path) -> None:
    extensions_root = get_extensions_root()
    target_dir = extensions_root / f"{BRIDGE_ID}-{BRIDGE_VERSION}"
    temp_root = Path(tempfile.mkdtemp(prefix="eide-rebuild-bridge-"))
    archive_root = temp_root / "archive"
    extension_root = archive_root / "extension"

    try:
        archive_root.mkdir(parents=True, exist_ok=True)
        extensions_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(vsix_path, "r") as archive:
            archive.extractall(archive_root)
        if not (extension_root / "package.json").exists():
            raise ExitError(7, f"Bundled bridge VSIX is missing extension payload: {vsix_path}")
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(extension_root, target_dir)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def ensure_bridge_installed(code_command: Path, vsix_path: Path) -> bool:
    if is_bridge_installed():
        return False

    result = run_code_command(code_command, ["--install-extension", str(vsix_path), "--force"])
    if result.returncode == 0 and is_bridge_installed():
        return True

    install_bridge_from_vsix_fallback(vsix_path)
    if not is_bridge_installed():
        raise ExitError(7, f"Failed to install bridge extension from: {vsix_path}")
    return True


# --- Registration ---

def read_registration(workspace_path: Path) -> dict[str, Any] | None:
    for registration_path in get_registration_paths(workspace_path):
        if not registration_path.exists():
            continue

        try:
            return json.loads(registration_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            registration_path.unlink(missing_ok=True)

    return None


def remove_registration(workspace_path: Path) -> None:
    for registration_path in get_registration_paths(workspace_path):
        registration_path.unlink(missing_ok=True)


# --- Named pipe ---

@contextmanager
def open_named_pipe(pipe_name: str, timeout_ms: int) -> Iterator[Any]:
    if os.name != "nt":
        raise OSError("Named pipes require Windows.")
    if not pipe_name:
        raise OSError("Pipe name is missing.")

    pipe_path = fr"\\.\pipe\{pipe_name}"
    deadline = time.monotonic() + (timeout_ms / 1000.0)

    while True:
        handle = KERNEL32.CreateFileW(
            pipe_path,
            GENERIC_READ | GENERIC_WRITE,
            0,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if handle != INVALID_HANDLE_VALUE:
            file_descriptor = msvcrt.open_osfhandle(handle, os.O_BINARY)
            stream = os.fdopen(file_descriptor, "r+b", buffering=0)
            try:
                yield stream
            finally:
                stream.close()
            return

        error_code = ctypes.get_last_error()
        remaining_ms = int(max(0, (deadline - time.monotonic()) * 1000))
        if remaining_ms <= 0:
            raise ctypes.WinError(error_code)
        if error_code == ERROR_PIPE_BUSY and KERNEL32.WaitNamedPipeW(pipe_path, remaining_ms):
            continue
        raise ctypes.WinError(error_code)


def read_pipe_line(stream: Any) -> str:
    buffer = bytearray()
    while True:
        chunk = stream.read(1)
        if not chunk:
            break
        if chunk == b"\n":
            break
        buffer.extend(chunk)
    return buffer.decode("utf-8")


def test_registration_alive(registration: dict[str, Any]) -> bool:
    pipe_name = str(registration.get("pipeName", ""))
    try:
        with open_named_pipe(pipe_name, 400):
            return True
    except OSError:
        return False


def wait_for_registration(workspace_path: Path, timeout_ms: int) -> dict[str, Any]:
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        registration = read_registration(workspace_path)
        if registration:
            if test_registration_alive(registration):
                return registration
            remove_registration(workspace_path)
        time.sleep(0.5)
    raise ExitError(4, "Timed out waiting for VS Code bridge registration.")


def invoke_bridge_request(registration: dict[str, Any], workspace_path: Path) -> dict[str, Any]:
    request = json.dumps(
        {
            "requestId": f"req-{int(time.time() * 1000)}",
            "action": "rebuild",
            "workspacePath": str(workspace_path),
        },
        separators=(",", ":"),
    )
    pipe_name = str(registration.get("pipeName", ""))

    try:
        with open_named_pipe(pipe_name, PIPE_CONNECT_TIMEOUT_MS) as stream:
            stream.write(request.encode("utf-8") + b"\n")
            stream.flush()
            response_line = read_pipe_line(stream)
    except OSError as error:
        raise ExitError(4, f"Failed to communicate with VS Code bridge: {error}") from error

    if not response_line:
        raise ExitError(4, "Bridge returned an empty response.")

    try:
        return json.loads(response_line)
    except json.JSONDecodeError as error:
        raise ExitError(4, f"Bridge returned invalid JSON: {error}") from error


# --- Build flow ---

def start_workspace_window(code_command: Path, workspace_path: Path, new_window: bool) -> None:
    open_flag = "-n" if new_window else "-r"
    result = run_code_command(code_command, [open_flag, str(workspace_path)])
    if result.returncode != 0:
        raise ExitError(3, f"Failed to open workspace in VS Code: {workspace_path}")


def read_compiler_log_text(log_path: str) -> str:
    path_obj = Path(log_path)
    if not path_obj.exists():
        raise ExitError(8, f"compiler.log not found: {path_obj}")
    try:
        payload = path_obj.read_bytes()
    except OSError as error:
        raise ExitError(8, f"Failed to read compiler.log: {path_obj} ({error})") from error

    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return payload.decode(locale.getpreferredencoding(False), errors="replace")


def resolve_exit_code(response: dict[str, Any]) -> int:
    if response.get("ok"):
        return 0

    error_code = str(response.get("errorCode", ""))
    mapping = {
        "BUILD_FAILED": 6,
        "BUILD_NOT_STARTED": 5,
        "BUSY": 4,
        "WRONG_WORKSPACE": 4,
        "EIDE_MISSING": 7,
        "LOG_MISSING": 8,
    }
    return mapping.get(error_code, 7)


# --- Entry point ---

def main(argv: list[str] | None = None) -> int:
    ensure_windows()
    arguments = list(sys.argv[1:] if argv is None else argv)
    state = ProtocolState()
    started_at = time.perf_counter()

    try:
        if len(arguments) < 2:
            show_usage()
            raise ExitError(2, "Missing command or path.")

        command_name = arguments[0]
        if command_name != "rebuild":
            show_usage()
            raise ExitError(2, f"Unsupported command: {command_name}")

        workspace_path = resolve_workspace_path(arguments[1])
        state.workspace = str(workspace_path)

        code_command = get_code_command_path()
        vsix_path = discover_vsix_path(Path(__file__).resolve().parent)
        bridge_installed_now = ensure_bridge_installed(code_command, vsix_path)

        registration = read_registration(workspace_path)
        if not registration or not test_registration_alive(registration):
            remove_registration(workspace_path)
            start_workspace_window(code_command, workspace_path, new_window=bridge_installed_now)
            registration = wait_for_registration(workspace_path, BRIDGE_READY_TIMEOUT_MS)

        response = invoke_bridge_request(registration, workspace_path)
        exit_code = resolve_exit_code(response)

        if response.get("workspacePath"):
            state.workspace = str(response["workspacePath"])
        if response.get("target"):
            state.target = str(response["target"])
        if response.get("logPath"):
            state.log_path = str(response["logPath"])
        if response.get("durationMs") is not None:
            state.duration_ms = str(response["durationMs"])

        state.exit_code = exit_code
        state.result = "success" if exit_code == 0 else "failure" if exit_code == 6 else "error"

        if state.log_path and exit_code in {0, 6}:
            state.compiler_log = read_compiler_log_text(state.log_path)

        if exit_code == 8:
            write_stderr_line(f"compiler.log missing or unreadable: {state.log_path}")
        elif not response.get("ok"):
            write_stderr_line(str(response.get("message", "")))

    except ExitError as error:
        state.exit_code = error.exit_code
        state.result = "error"
        write_stderr_line(str(error))
    except Exception as error:
        state.exit_code = 7
        state.result = "error"
        write_stderr_line(str(error))
    finally:
        if not state.duration_ms:
            state.duration_ms = str(int((time.perf_counter() - started_at) * 1000))
        sys.stdout.write(render_protocol(state))

    return state.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
