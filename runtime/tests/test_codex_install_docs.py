from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
README_EN = REPO_ROOT / "README.md"
README_ZH = REPO_ROOT / "README.zh-CN.md"
CODEX_INSTALL_DOC = REPO_ROOT / ".codex" / "INSTALL.md"
CODEX_UPDATE_DOC = REPO_ROOT / ".codex" / "UPDATE.md"
CODEX_UNINSTALL_DOC = REPO_ROOT / ".codex" / "UNINSTALL.md"
CC_INSTALL_DOC = REPO_ROOT / "integrations" / "claude-code" / "INSTALL.md"
CC_UPDATE_DOC = REPO_ROOT / "integrations" / "claude-code" / "UPDATE.md"
CC_UNINSTALL_DOC = REPO_ROOT / "integrations" / "claude-code" / "UNINSTALL.md"

_BASE = "https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main"
CODEX_INSTALL_URL = f"{_BASE}/.codex/INSTALL.md"
CODEX_UPDATE_URL = f"{_BASE}/.codex/UPDATE.md"
CODEX_UNINSTALL_URL = f"{_BASE}/.codex/UNINSTALL.md"
CC_INSTALL_URL = f"{_BASE}/integrations/claude-code/INSTALL.md"
CC_UPDATE_URL = f"{_BASE}/integrations/claude-code/UPDATE.md"
CC_UNINSTALL_URL = f"{_BASE}/integrations/claude-code/UNINSTALL.md"


class CodexInstallDocsTests(unittest.TestCase):
    def test_codex_lifecycle_docs_exist(self) -> None:
        self.assertTrue(CODEX_INSTALL_DOC.exists())
        self.assertTrue(CODEX_UPDATE_DOC.exists())
        self.assertTrue(CODEX_UNINSTALL_DOC.exists())

    def test_claude_code_lifecycle_docs_exist(self) -> None:
        self.assertTrue(CC_INSTALL_DOC.exists())
        self.assertTrue(CC_UPDATE_DOC.exists())
        self.assertTrue(CC_UNINSTALL_DOC.exists())

    def test_english_readme_links_codex_install_flow(self) -> None:
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn(CODEX_INSTALL_URL, content)
        self.assertIn(CODEX_UPDATE_URL, content)
        self.assertIn(CODEX_UNINSTALL_URL, content)

    def test_english_readme_links_claude_code_install_flow(self) -> None:
        content = README_EN.read_text(encoding="utf-8")
        self.assertIn(CC_INSTALL_URL, content)
        self.assertIn(CC_UPDATE_URL, content)
        self.assertIn(CC_UNINSTALL_URL, content)

    def test_chinese_readme_links_codex_install_flow(self) -> None:
        content = README_ZH.read_text(encoding="utf-8")
        self.assertIn(CODEX_INSTALL_URL, content)
        self.assertIn(CODEX_UPDATE_URL, content)
        self.assertIn(CODEX_UNINSTALL_URL, content)

    def test_chinese_readme_links_claude_code_install_flow(self) -> None:
        content = README_ZH.read_text(encoding="utf-8")
        self.assertIn(CC_INSTALL_URL, content)
        self.assertIn(CC_UPDATE_URL, content)
        self.assertIn(CC_UNINSTALL_URL, content)

    def test_install_does_not_require_vscode_cli(self) -> None:
        content = CODEX_INSTALL_DOC.read_text(encoding="utf-8")
        self.assertNotIn("Get-Command code", content)
        self.assertNotIn("VS Code CLI command `code` is required before installing", content)
