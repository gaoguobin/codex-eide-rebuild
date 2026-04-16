from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
README_EN = REPO_ROOT / "README.md"
README_ZH = REPO_ROOT / "README.zh-CN.md"
INSTALL_DOC = REPO_ROOT / ".codex" / "INSTALL.md"
UPDATE_DOC = REPO_ROOT / ".codex" / "UPDATE.md"
UNINSTALL_DOC = REPO_ROOT / ".codex" / "UNINSTALL.md"
INSTALL_URL = "https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md"
UPDATE_URL = "https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md"
UNINSTALL_URL = "https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md"
FALLBACK_COMMAND = "python install-skill-from-github.py --repo gaoguobin/codex-eide-rebuild --path skills/eide-rebuild"


class CodexInstallDocsTests(unittest.TestCase):
    def test_codex_lifecycle_docs_exist(self) -> None:
        self.assertTrue(INSTALL_DOC.exists())
        self.assertTrue(UPDATE_DOC.exists())
        self.assertTrue(UNINSTALL_DOC.exists())

    def test_english_readme_links_codex_install_flow(self) -> None:
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn(INSTALL_URL, content)
        self.assertIn(UPDATE_URL, content)
        self.assertIn(UNINSTALL_URL, content)
        self.assertIn(FALLBACK_COMMAND, content)

    def test_chinese_readme_links_codex_install_flow(self) -> None:
        content = README_ZH.read_text(encoding="utf-8")
        self.assertIn(INSTALL_URL, content)
        self.assertIn(UPDATE_URL, content)
        self.assertIn(UNINSTALL_URL, content)
        self.assertIn(FALLBACK_COMMAND, content)
