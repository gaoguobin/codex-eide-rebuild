from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_SOURCE = REPO_ROOT / "runtime" / "python" / "eide_rebuild.py"
RUNNER_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "scripts" / "eide_rebuild.py"
VSIX_SOURCE = REPO_ROOT / "runtime" / "bridge" / "dist" / "eide-rebuild.cli-bridge-0.1.0.vsix"
VSIX_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "assets" / "eide-rebuild.cli-bridge-0.1.0.vsix"


class SkillBundleSyncTests(unittest.TestCase):
    def test_runner_copy_matches_runtime(self) -> None:
        self.assertTrue(RUNNER_TARGET.exists())
        self.assertEqual(RUNNER_SOURCE.read_bytes(), RUNNER_TARGET.read_bytes())

    def test_vsix_copy_matches_runtime(self) -> None:
        self.assertTrue(VSIX_TARGET.exists())
        self.assertEqual(VSIX_SOURCE.read_bytes(), VSIX_TARGET.read_bytes())
