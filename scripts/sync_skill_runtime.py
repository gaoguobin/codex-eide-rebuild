#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import sys
import uuid
from pathlib import Path


# --- Paths ---

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_SOURCE = REPO_ROOT / "runtime" / "python" / "eide_rebuild.py"
RUNNER_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "scripts" / "eide_rebuild.py"
PACKAGE_SOURCE = REPO_ROOT / "runtime" / "python" / "eide_rebuild"
PACKAGE_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "scripts" / "eide_rebuild"
LEGACY_VSIX_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "assets" / "eide-rebuild.cli-bridge-0.1.0.vsix"


# --- Helpers ---

def files_match(left_path: Path, right_path: Path) -> bool:
    if not left_path.exists() or not right_path.exists():
        return False
    return left_path.read_bytes() == right_path.read_bytes()


def trees_match(left_root: Path, right_root: Path) -> bool:
    if not left_root.exists() or not right_root.exists():
        return False

    def collect(root: Path) -> dict[str, bytes]:
        return {
            str(path.relative_to(root)).replace("\\", "/"): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    return collect(left_root) == collect(right_root)


def _temp_sibling(path: Path, suffix: str) -> Path:
    return path.parent / f".{path.name}.sync-{uuid.uuid4().hex}{suffix}"


def _safe_remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def _stage_file_copy(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = _temp_sibling(target, ".tmp")
    try:
        shutil.copy2(source, staged)
        return staged
    except Exception:
        staged.unlink(missing_ok=True)
        raise


def _stage_tree_copy(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = _temp_sibling(target, ".tmp")
    try:
        shutil.copytree(source, staged)
        return staged
    except Exception:
        if staged.exists():
            shutil.rmtree(staged, ignore_errors=True)
        raise


def _swap_tree(staged: Path, target: Path) -> Path | None:
    backup: Path | None = None
    if target.exists():
        backup = _temp_sibling(target, ".bak")
        target.replace(backup)
    staged.replace(target)
    return backup


def sync_copy() -> int:
    staged_package = _stage_tree_copy(PACKAGE_SOURCE, PACKAGE_TARGET)
    staged_runner = _stage_file_copy(RUNNER_SOURCE, RUNNER_TARGET)
    package_backup: Path | None = None
    package_swapped = False

    try:
        package_backup = _swap_tree(staged_package, PACKAGE_TARGET)
        package_swapped = True
        os.replace(staged_runner, RUNNER_TARGET)
    except Exception:
        staged_runner.unlink(missing_ok=True)
        if staged_package.exists():
            shutil.rmtree(staged_package, ignore_errors=True)
        if package_swapped:
            if PACKAGE_TARGET.exists():
                _safe_remove(PACKAGE_TARGET)
            if package_backup is not None and package_backup.exists():
                package_backup.replace(PACKAGE_TARGET)
        raise
    finally:
        if package_backup is not None and package_backup.exists():
            shutil.rmtree(package_backup, ignore_errors=True)

    LEGACY_VSIX_TARGET.unlink(missing_ok=True)
    print("Synchronized runtime artifacts into the skill bundle.")
    return 0


def sync_check() -> int:
    mismatches = []
    if not files_match(RUNNER_SOURCE, RUNNER_TARGET):
        mismatches.append(f"Runner mismatch: {RUNNER_SOURCE} -> {RUNNER_TARGET}")
    if not trees_match(PACKAGE_SOURCE, PACKAGE_TARGET):
        mismatches.append(f"Runner package mismatch: {PACKAGE_SOURCE} -> {PACKAGE_TARGET}")

    if mismatches:
        for message in mismatches:
            print(message, file=sys.stderr)
        return 1

    print("Runtime artifacts are synchronized.")
    return 0


# --- Entry point ---

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize the shared runtime into the skill bundle.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--copy", action="store_true", help="Copy the runtime runner and support package into the skill bundle.")
    mode.add_argument("--check", action="store_true", help="Verify that the skill bundle is synchronized.")
    arguments = parser.parse_args(argv)

    if arguments.copy:
        return sync_copy()
    return sync_check()


if __name__ == "__main__":
    raise SystemExit(main())
