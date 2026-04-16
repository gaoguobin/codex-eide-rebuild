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
VSIX_SOURCE = REPO_ROOT / "runtime" / "bridge" / "dist" / "eide-rebuild.cli-bridge-0.1.0.vsix"
VSIX_TARGET = REPO_ROOT / "skills" / "eide-rebuild" / "assets" / "eide-rebuild.cli-bridge-0.1.0.vsix"


# --- Helpers ---

def files_match(left_path: Path, right_path: Path) -> bool:
    if not left_path.exists() or not right_path.exists():
        return False
    return left_path.read_bytes() == right_path.read_bytes()


def sync_copy() -> int:
    RUNNER_TARGET.parent.mkdir(parents=True, exist_ok=True)
    VSIX_TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUNNER_SOURCE, RUNNER_TARGET)
    shutil.copy2(VSIX_SOURCE, VSIX_TARGET)
    print("Synchronized runtime artifacts into the skill bundle.")
    return 0


def sync_check() -> int:
    mismatches = []
    if not files_match(RUNNER_SOURCE, RUNNER_TARGET):
        mismatches.append(f"Runner mismatch: {RUNNER_SOURCE} -> {RUNNER_TARGET}")
    if not files_match(VSIX_SOURCE, VSIX_TARGET):
        mismatches.append(f"VSIX mismatch: {VSIX_SOURCE} -> {VSIX_TARGET}")

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
    mode.add_argument("--copy", action="store_true", help="Copy the runtime runner and VSIX into the skill bundle.")
    mode.add_argument("--check", action="store_true", help="Verify that the skill bundle is synchronized.")
    arguments = parser.parse_args(argv)

    if arguments.copy:
        return sync_copy()
    return sync_check()


if __name__ == "__main__":
    raise SystemExit(main())
