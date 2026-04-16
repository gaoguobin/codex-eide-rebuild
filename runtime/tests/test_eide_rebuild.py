from __future__ import annotations

import io
import shutil
import sys
import unittest
import uuid
from contextlib import contextmanager
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


RUNTIME_PYTHON = Path(__file__).resolve().parents[1] / "python"
TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp" / "tests"
if str(RUNTIME_PYTHON) not in sys.path:
    sys.path.insert(0, str(RUNTIME_PYTHON))

import eide_rebuild


@contextmanager
def make_temp_dir() -> str:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    temp_dir = TEST_TMP_ROOT / f"tmp-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield str(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class ResolveWorkspacePathTests(unittest.TestCase):
    def test_accepts_workspace_file(self) -> None:
        with make_temp_dir() as temp_dir:
            workspace_file = Path(temp_dir) / "demo.code-workspace"
            workspace_file.write_text("{}", encoding="utf-8")

            result = eide_rebuild.resolve_workspace_path(str(workspace_file))

            self.assertEqual(result, workspace_file.resolve())

    def test_resolves_single_workspace_in_directory(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            workspace_file = project_dir / "demo.code-workspace"
            workspace_file.write_text("{}", encoding="utf-8")

            result = eide_rebuild.resolve_workspace_path(str(project_dir))

            self.assertEqual(result, workspace_file.resolve())

    def test_rejects_multiple_workspace_files(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "a.code-workspace").write_text("{}", encoding="utf-8")
            (project_dir / "b.code-workspace").write_text("{}", encoding="utf-8")

            with self.assertRaises(eide_rebuild.ExitError) as error:
                eide_rebuild.resolve_workspace_path(str(project_dir))

            self.assertEqual(error.exception.exit_code, 2)


class ProtocolTests(unittest.TestCase):
    def test_render_protocol_appends_newline_after_log(self) -> None:
        state = eide_rebuild.ProtocolState(
            workspace=r"C:\work\demo\project.code-workspace",
            target="Debug",
            log_path=r"C:\work\demo\build\Debug\compiler.log",
            result="failure",
            duration_ms="321",
            exit_code=6,
            compiler_log="line-1",
        )

        rendered = eide_rebuild.render_protocol(state)

        self.assertIn("line-1\n[EIDE-CLI] compiler-log-end", rendered)

    def test_resolve_exit_code_mapping(self) -> None:
        self.assertEqual(eide_rebuild.resolve_exit_code({"ok": True}), 0)
        self.assertEqual(eide_rebuild.resolve_exit_code({"ok": False, "errorCode": "BUILD_FAILED"}), 6)
        self.assertEqual(eide_rebuild.resolve_exit_code({"ok": False, "errorCode": "LOG_MISSING"}), 8)


class MainFlowTests(unittest.TestCase):
    def test_main_emits_failure_protocol_with_full_log(self) -> None:
        with make_temp_dir() as temp_dir:
            workspace_file = Path(temp_dir) / "demo.code-workspace"
            workspace_file.write_text("{}", encoding="utf-8")
            log_file = Path(temp_dir) / "compiler.log"
            log_file.write_text("compile failed", encoding="utf-8")

            response = {
                "ok": False,
                "workspacePath": str(workspace_file),
                "target": "Debug",
                "logPath": str(log_file),
                "durationMs": 1234,
                "errorCode": "BUILD_FAILED",
                "message": "rebuild failed",
            }

            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with (
                mock.patch.object(eide_rebuild, "get_code_command_path", return_value=Path(r"C:\Tools\code.cmd")),
                mock.patch.object(eide_rebuild, "discover_vsix_path", return_value=Path(r"C:\bundle\eide-rebuild.cli-bridge-0.1.0.vsix")),
                mock.patch.object(eide_rebuild, "ensure_bridge_installed", return_value=False),
                mock.patch.object(eide_rebuild, "read_registration", return_value={"pipeName": "demo"}),
                mock.patch.object(eide_rebuild, "test_registration_alive", return_value=True),
                mock.patch.object(eide_rebuild, "invoke_bridge_request", return_value=response),
                redirect_stdout(stdout_buffer),
                redirect_stderr(stderr_buffer),
            ):
                exit_code = eide_rebuild.main(["rebuild", str(workspace_file)])

            self.assertEqual(exit_code, 6)
            self.assertIn("[EIDE-CLI] result=failure", stdout_buffer.getvalue())
            self.assertIn("compile failed", stdout_buffer.getvalue())
            self.assertIn("rebuild failed", stderr_buffer.getvalue())

    def test_wait_for_registration_removes_stale_entry(self) -> None:
        workspace_file = Path(r"C:\work\demo\demo.code-workspace")
        stale = {"pipeName": "stale"}
        live = {"pipeName": "live"}

        with (
            mock.patch.object(eide_rebuild, "read_registration", side_effect=[stale, live]),
            mock.patch.object(eide_rebuild, "test_registration_alive", side_effect=[False, True]),
            mock.patch.object(eide_rebuild, "remove_registration") as remove_registration,
            mock.patch.object(eide_rebuild.time, "sleep", return_value=None),
        ):
            result = eide_rebuild.wait_for_registration(workspace_file, 1000)

        self.assertEqual(result, live)
        remove_registration.assert_called_once_with(workspace_file)
