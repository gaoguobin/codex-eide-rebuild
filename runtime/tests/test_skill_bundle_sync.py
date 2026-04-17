from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_SOURCE = REPO_ROOT / "runtime" / "python" / "eide_rebuild.py"
RUNNER_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "scripts" / "eide_rebuild.py"
PACKAGE_SOURCE = REPO_ROOT / "runtime" / "python" / "eide_rebuild"
PACKAGE_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "scripts" / "eide_rebuild"


def _collect_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class SkillBundleSyncTests(unittest.TestCase):
    def test_runner_copy_matches_runtime(self) -> None:
        self.assertTrue(RUNNER_TARGET.exists())
        self.assertEqual(RUNNER_SOURCE.read_bytes(), RUNNER_TARGET.read_bytes())

    def test_runner_support_package_matches_runtime(self) -> None:
        self.assertTrue(PACKAGE_TARGET.exists())
        self.assertEqual(_collect_files(PACKAGE_SOURCE), _collect_files(PACKAGE_TARGET))
