#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
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


def sync_copy() -> int:
    RUNNER_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUNNER_SOURCE, RUNNER_TARGET)
    if PACKAGE_TARGET.exists():
        shutil.rmtree(PACKAGE_TARGET)
    shutil.copytree(PACKAGE_SOURCE, PACKAGE_TARGET)
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
