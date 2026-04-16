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
TEXT_SUFFIXES = {".md", ".py", ".js", ".json", ".ps1", ".yaml", ".yml", ".txt"}


class RepositorySanitizationTests(unittest.TestCase):
    def test_repository_text_files_are_sanitized(self) -> None:
        hits = []
        for file_path in REPO_ROOT.rglob("*"):
            if file_path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore").lower()
            for snippet in BANNED_SNIPPETS:
                if snippet in content:
                    hits.append(f"{file_path}: {snippet}")

        self.assertEqual(hits, [])
