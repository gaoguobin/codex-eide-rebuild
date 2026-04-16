from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BRIDGE_ROOT = REPO_ROOT / "runtime" / "bridge"
TEST_FIXTURE = REPO_ROOT / "runtime" / "tests" / "fixtures" / "bridge_eaddrinuse_registration.cjs"
TEST_TMP_ROOT = REPO_ROOT / ".tmp" / "tests"


@contextmanager
def make_temp_dir() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    temp_dir = TEST_TMP_ROOT / f"tmp-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class BridgeRegressionTests(unittest.TestCase):
    def test_build_vsix_is_deterministic(self) -> None:
        with make_temp_dir() as temp_dir:
            bridge_copy = temp_dir / "bridge"
            shutil.copytree(
                BRIDGE_ROOT,
                bridge_copy,
                ignore=shutil.ignore_patterns(".build", "dist"),
            )

            script_path = bridge_copy / "build-vsix.ps1"
            vsix_path = bridge_copy / "dist" / "eide-rebuild.cli-bridge-0.1.0.vsix"

            self.run_powershell(script_path)
            first_hash = hashlib.sha256(vsix_path.read_bytes()).hexdigest()

            time.sleep(1.2)

            self.run_powershell(script_path)
            second_hash = hashlib.sha256(vsix_path.read_bytes()).hexdigest()

            self.assertEqual(first_hash, second_hash)

    def test_build_vsix_is_stable_across_line_endings(self) -> None:
        with make_temp_dir() as temp_dir:
            lf_bridge = temp_dir / "bridge-lf"
            crlf_bridge = temp_dir / "bridge-crlf"

            shutil.copytree(
                BRIDGE_ROOT,
                lf_bridge,
                ignore=shutil.ignore_patterns(".build", "dist"),
            )
            shutil.copytree(
                BRIDGE_ROOT,
                crlf_bridge,
                ignore=shutil.ignore_patterns(".build", "dist"),
            )

            self.normalize_bridge_line_endings(lf_bridge, "\n")
            self.normalize_bridge_line_endings(crlf_bridge, "\r\n")

            lf_hash = self.build_vsix_hash(lf_bridge)
            crlf_hash = self.build_vsix_hash(crlf_bridge)

            self.assertEqual(lf_hash, crlf_hash)

    def test_bridge_skips_registration_updates_when_pipe_is_owned_elsewhere(self) -> None:
        completed = subprocess.run(
            ["node", str(TEST_FIXTURE)],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(
            completed.returncode,
            0,
            msg=completed.stdout + completed.stderr,
        )

    @staticmethod
    def run_powershell(script_path: Path) -> None:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            cwd=script_path.parent,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout + completed.stderr)

    @classmethod
    def normalize_bridge_line_endings(cls, bridge_root: Path, newline: str) -> None:
        for relative_path in (
            "extension.js",
            "package.json",
            "README.md",
            "build-vsix.ps1",
        ):
            cls.rewrite_text_with_newline(bridge_root / relative_path, newline)

    @classmethod
    def build_vsix_hash(cls, bridge_root: Path) -> str:
        script_path = bridge_root / "build-vsix.ps1"
        vsix_path = bridge_root / "dist" / "eide-rebuild.cli-bridge-0.1.0.vsix"
        cls.run_powershell(script_path)
        return hashlib.sha256(vsix_path.read_bytes()).hexdigest()

    @staticmethod
    def rewrite_text_with_newline(file_path: Path, newline: str) -> None:
        text = file_path.read_text(encoding="utf-8")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        file_path.write_text(normalized, encoding="utf-8", newline=newline)
