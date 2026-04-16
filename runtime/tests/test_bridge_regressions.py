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
