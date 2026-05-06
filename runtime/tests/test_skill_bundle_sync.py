from __future__ import annotations

import importlib.util
import shutil
import unittest
import uuid
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_SOURCE = REPO_ROOT / "runtime" / "python" / "eide_rebuild.py"
RUNNER_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "scripts" / "eide_rebuild.py"
PACKAGE_SOURCE = REPO_ROOT / "runtime" / "python" / "eide_rebuild"
PACKAGE_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "scripts" / "eide_rebuild"
TEST_TMP_ROOT = REPO_ROOT / ".tmp" / "tests"


def _collect_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    }


def _load_sync_module():
    module_path = REPO_ROOT / "scripts" / "sync_skill_runtime.py"
    spec = importlib.util.spec_from_file_location("sync_skill_runtime_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load sync_skill_runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_temp_root() -> Path:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    temp_root = TEST_TMP_ROOT / f"sync-{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=False)
    return temp_root


class SkillBundleSyncTests(unittest.TestCase):
    def test_runner_copy_matches_runtime(self) -> None:
        self.assertTrue(RUNNER_TARGET.exists())
        self.assertEqual(RUNNER_SOURCE.read_bytes(), RUNNER_TARGET.read_bytes())

    def test_runner_support_package_matches_runtime(self) -> None:
        self.assertTrue(PACKAGE_TARGET.exists())
        self.assertEqual(_collect_files(PACKAGE_SOURCE), _collect_files(PACKAGE_TARGET))

    def test_sync_copy_preserves_existing_package_when_staging_fails(self) -> None:
        sync_module = _load_sync_module()
        temp_root = _make_temp_root()
        try:
            runner_source = temp_root / "source" / "eide_rebuild.py"
            runner_target = temp_root / "target" / "eide_rebuild.py"
            package_source = temp_root / "source" / "eide_rebuild"
            package_target = temp_root / "target" / "eide_rebuild"
            legacy_vsix = temp_root / "target" / "assets" / "legacy.vsix"
            runner_source.parent.mkdir(parents=True)
            package_source.mkdir(parents=True)
            package_target.mkdir(parents=True)
            legacy_vsix.parent.mkdir(parents=True)
            runner_source.write_text("new runner\n", encoding="utf-8")
            runner_target.write_text("old runner\n", encoding="utf-8")
            (package_source / "module.py").write_text("new package\n", encoding="utf-8")
            (package_target / "module.py").write_text("old package\n", encoding="utf-8")
            legacy_vsix.write_text("legacy\n", encoding="utf-8")

            def failing_copytree(source, target, **kwargs):
                raise OSError("copy failed")

            with (
                mock.patch.object(sync_module, "RUNNER_SOURCE", runner_source),
                mock.patch.object(sync_module, "RUNNER_TARGET", runner_target),
                mock.patch.object(sync_module, "PACKAGE_SOURCE", package_source),
                mock.patch.object(sync_module, "PACKAGE_TARGET", package_target),
                mock.patch.object(sync_module, "LEGACY_VSIX_TARGET", legacy_vsix),
                mock.patch.object(sync_module.shutil, "copytree", side_effect=failing_copytree),
            ):
                with self.assertRaises(OSError):
                    sync_module.sync_copy()

            self.assertEqual(runner_target.read_text(encoding="utf-8"), "old runner\n")
            self.assertEqual((package_target / "module.py").read_text(encoding="utf-8"), "old package\n")
            self.assertTrue(legacy_vsix.exists())
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)

    def test_sync_copy_replaces_package_after_successful_staging(self) -> None:
        sync_module = _load_sync_module()
        temp_root = _make_temp_root()
        try:
            runner_source = temp_root / "source" / "eide_rebuild.py"
            runner_target = temp_root / "target" / "eide_rebuild.py"
            package_source = temp_root / "source" / "eide_rebuild"
            package_target = temp_root / "target" / "eide_rebuild"
            legacy_vsix = temp_root / "target" / "assets" / "legacy.vsix"
            runner_source.parent.mkdir(parents=True)
            package_source.mkdir(parents=True)
            package_target.mkdir(parents=True)
            legacy_vsix.parent.mkdir(parents=True)
            runner_source.write_text("new runner\n", encoding="utf-8")
            runner_target.write_text("old runner\n", encoding="utf-8")
            (package_source / "module.py").write_text("new package\n", encoding="utf-8")
            (package_target / "module.py").write_text("old package\n", encoding="utf-8")
            legacy_vsix.write_text("legacy\n", encoding="utf-8")

            with (
                mock.patch.object(sync_module, "RUNNER_SOURCE", runner_source),
                mock.patch.object(sync_module, "RUNNER_TARGET", runner_target),
                mock.patch.object(sync_module, "PACKAGE_SOURCE", package_source),
                mock.patch.object(sync_module, "PACKAGE_TARGET", package_target),
                mock.patch.object(sync_module, "LEGACY_VSIX_TARGET", legacy_vsix),
            ):
                self.assertEqual(sync_module.sync_copy(), 0)

            self.assertEqual(runner_target.read_text(encoding="utf-8"), "new runner\n")
            self.assertEqual((package_target / "module.py").read_text(encoding="utf-8"), "new package\n")
            self.assertFalse(legacy_vsix.exists())
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
