from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BANNED_SNIPPETS = [
    "d:" + r"\git_ecu",
    "bf_" + "ecu_appswprjtgen3",
    "gao" + ".eide-cli-bridge",
    "eide_" + r"cli\registrations",
    r"c:\users" + "\\" + "cedric" + ".gao",
    "cedric" + "." + "gao",
]
BANNED_LEGACY_BRIDGE_SNIPPETS = [
    "[eide" + "-cli]",
    "eide" + ".project.rebuild",
    "runtime" + "/bridge",
    "runtime" + r"\bridge",
    "named " + "pipe",
    "registration " + "file",
]
TEXT_SUFFIXES = {".md", ".py", ".js", ".json", ".ps1", ".yaml", ".yml", ".txt"}
SKIP_DIR_NAMES = {".git", ".tmp", "__pycache__"}


def _iter_repository_text_files():
    for file_path in REPO_ROOT.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in file_path.relative_to(REPO_ROOT).parts):
            continue
        if file_path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield file_path


class RepositorySanitizationTests(unittest.TestCase):
    def test_repository_text_files_are_sanitized(self) -> None:
        hits = []
        for file_path in _iter_repository_text_files():
            content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for snippet in BANNED_SNIPPETS:
                if snippet in content:
                    hits.append(f"{file_path}: {snippet}")

        self.assertEqual(hits, [])

    def test_legacy_bridge_sources_are_removed(self) -> None:
        removed_paths = [
            REPO_ROOT / "runtime" / "bridge",
            REPO_ROOT / "runtime" / "tests" / "test_bridge_regressions.py",
            REPO_ROOT / "runtime" / "tests" / "fixtures" / "bridge_eaddrinuse_registration.cjs",
        ]

        self.assertEqual([path for path in removed_paths if path.exists()], [])

    def test_legacy_bridge_protocol_references_are_removed(self) -> None:
        hits = []
        for file_path in _iter_repository_text_files():
            content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for snippet in BANNED_LEGACY_BRIDGE_SNIPPETS:
                if snippet in content:
                    hits.append(f"{file_path}: {snippet}")

        self.assertEqual(hits, [])
