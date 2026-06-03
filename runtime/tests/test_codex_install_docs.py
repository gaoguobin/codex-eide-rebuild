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
CC_AGENT_DOC = REPO_ROOT / "integrations" / "claude-code" / "agents" / "eide-rebuild.md"
CODEX_AGENT_DOC = REPO_ROOT / "integrations" / "codex" / "agents" / "eide-rebuild.toml"

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
        self.assertTrue(CODEX_AGENT_DOC.exists())

    def test_claude_code_lifecycle_docs_exist(self) -> None:
        self.assertTrue(CC_INSTALL_DOC.exists())
        self.assertTrue(CC_UPDATE_DOC.exists())
        self.assertTrue(CC_UNINSTALL_DOC.exists())

    def test_claude_code_lifecycle_docs_name_shell_environment(self) -> None:
        for doc in (CC_INSTALL_DOC, CC_UPDATE_DOC, CC_UNINSTALL_DOC):
            with self.subTest(doc=doc.name):
                content = doc.read_text(encoding="utf-8")
                self.assertIn("Claude Code's Bash tool", content)
                self.assertIn("Git Bash", content)

    def test_claude_code_install_updates_existing_repo(self) -> None:
        content = CC_INSTALL_DOC.read_text(encoding="utf-8")
        self.assertIn("git -C ~/.codex/codex-eide-rebuild pull --ff-only", content)
        self.assertIn("git clone https://github.com/gaoguobin/codex-eide-rebuild.git", content)

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

    def test_readmes_use_block_lifecycle_prompts(self) -> None:
        for readme in (README_EN, README_ZH):
            with self.subTest(readme=readme.name):
                content = readme.read_text(encoding="utf-8")
                self.assertNotIn("`Fetch and follow instructions from", content)

    def test_readmes_name_codex_restart_and_claude_reload(self) -> None:
        english = README_EN.read_text(encoding="utf-8")
        chinese = README_ZH.read_text(encoding="utf-8")
        self.assertIn("restart Codex", english)
        self.assertIn("`/reload-plugins` in Claude Code", english)
        self.assertIn("Codex 需要重启", chinese)
        self.assertIn("Claude Code 运行 `/reload-plugins`", chinese)

    def test_claude_code_lifecycle_docs_use_consistent_prompt_format(self) -> None:
        for doc in (CC_INSTALL_DOC, CC_UPDATE_DOC, CC_UNINSTALL_DOC):
            with self.subTest(doc=doc.name):
                content = doc.read_text(encoding="utf-8")
                self.assertIn("## One-paste prompt for engineers", content)
                self.assertIn("Paste this into Claude Code:", content)

    def test_claude_code_lifecycle_docs_use_reload_plugins(self) -> None:
        for doc in (CC_INSTALL_DOC, CC_UPDATE_DOC, CC_UNINSTALL_DOC):
            with self.subTest(doc=doc.name):
                content = doc.read_text(encoding="utf-8")
                self.assertIn("/reload-plugins", content)
                self.assertNotIn("restart Claude Code", content)

    def test_chinese_readme_keeps_core_sections_in_sync(self) -> None:
        content = README_ZH.read_text(encoding="utf-8")
        for heading in (
            "## 输出协议",
            "## 目录",
            "## 开发",
            "## 安全和隐私",
            "## 上游参考",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, content)

    def test_claude_code_integration_readme_uses_current_status(self) -> None:
        content = (REPO_ROOT / "integrations" / "claude-code" / "README.md").read_text(encoding="utf-8")
        self.assertIn("Claude Code command and subagent templates", content)
        self.assertNotIn("phase 2", content.lower())

    def test_install_does_not_require_vscode_cli(self) -> None:
        content = CODEX_INSTALL_DOC.read_text(encoding="utf-8")
        self.assertNotIn("Get-Command code", content)
        self.assertNotIn("VS Code CLI command `code` is required before installing", content)

    def test_codex_lifecycle_docs_manage_custom_agent_template(self) -> None:
        install = CODEX_INSTALL_DOC.read_text(encoding="utf-8")
        update = CODEX_UPDATE_DOC.read_text(encoding="utf-8")
        uninstall = CODEX_UNINSTALL_DOC.read_text(encoding="utf-8")
        for content in (install, update):
            with self.subTest(doc="install/update"):
                self.assertIn(".codex\\agents", content)
                self.assertIn("integrations\\codex\\agents\\eide-rebuild.toml", content)
                self.assertIn("Copy-Item", content)
        self.assertIn(".codex\\agents\\eide-rebuild.toml", uninstall)
        self.assertIn("custom agent", uninstall)

    def test_uninstall_does_not_require_vscode_cli_or_bridge_cleanup(self) -> None:
        content = CODEX_UNINSTALL_DOC.read_text(encoding="utf-8")
        self.assertNotIn("Get-Command code", content)
        self.assertNotIn("code --uninstall-extension", content)
        self.assertNotIn("cli-bridge", content.lower())

    def test_claude_code_subagent_has_required_frontmatter(self) -> None:
        content = CC_AGENT_DOC.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        frontmatter = content.split("---", 2)[1]
        keys = {
            line.split(":", 1)[0].strip()
            for line in frontmatter.splitlines()
            if ":" in line
        }
        self.assertIn("name", keys)
        self.assertIn("description", keys)

    def test_codex_custom_agent_has_required_fields(self) -> None:
        content = CODEX_AGENT_DOC.read_text(encoding="utf-8")
        self.assertIn('name = "eide-rebuild"', content)
        self.assertIn("description =", content)
        self.assertIn("developer_instructions =", content)
        self.assertIn("--stdout minimal", content)
        self.assertIn("identity/provenance", content)
        self.assertNotIn("hooks", content.lower())

    def test_claude_command_defaults_to_direct_single_project_rebuild(self) -> None:
        content = (
            REPO_ROOT / "integrations" / "claude-code" / "commands" / "eide-rebuild.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Default to direct execution", content)
        self.assertIn("Use the `eide-rebuild` subagent only when the user explicitly asks", content)
        self.assertIn("Do not paste full logs or long artifact lists on success", content)
