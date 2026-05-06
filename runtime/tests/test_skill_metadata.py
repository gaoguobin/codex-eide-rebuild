from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
README_EN = REPO_ROOT / "README.md"
README_ZH = REPO_ROOT / "README.zh-CN.md"
PLUGIN_MANIFEST = REPO_ROOT / ".codex-plugin" / "plugin.json"
SKILL_FILE = REPO_ROOT / "skills" / "eide-rebuild" / "SKILL.md"
OPENAI_YAML = REPO_ROOT / "skills" / "eide-rebuild" / "agents" / "openai.yaml"


def _skill_frontmatter() -> dict[str, str]:
    content = SKILL_FILE.read_text(encoding="utf-8")
    frontmatter = content.split("---", 2)[1]
    values: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


class SkillMetadataTests(unittest.TestCase):
    def test_skill_files_exist(self) -> None:
        self.assertTrue(SKILL_FILE.exists())
        self.assertTrue(OPENAI_YAML.exists())
        self.assertTrue(PLUGIN_MANIFEST.exists())

    def test_skill_frontmatter_is_search_friendly(self) -> None:
        frontmatter = _skill_frontmatter()
        self.assertEqual(frontmatter["name"], "eide-rebuild")
        description = frontmatter["description"]
        for term in ("EIDE", "Embedded IDE for VS Code", "Agent Skill", "JSON"):
            with self.subTest(term=term):
                self.assertIn(term, description)

    def test_skill_mentions_natural_language_prompts(self) -> None:
        content = SKILL_FILE.read_text(encoding="utf-8")
        self.assertIn("你自己编译验证下对不对", content)
        self.assertIn("帮我编译确认一下", content)
        self.assertIn("EIDE subagent rebuild", content)

    def test_plugin_manifest_points_to_bundled_skills(self) -> None:
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "codex-eide-rebuild")
        self.assertEqual(manifest["skills"], "./skills/")
        for keyword in ("agent-skills", "skillsmp", "codex", "codex-skill", "eide", "embedded-ide", "firmware"):
            with self.subTest(keyword=keyword):
                self.assertIn(keyword, manifest["keywords"])

    def test_plugin_manifest_is_metadata_only(self) -> None:
        manifest = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
        for runtime_key in ("hooks", "mcpServers", "apps"):
            with self.subTest(runtime_key=runtime_key):
                self.assertNotIn(runtime_key, manifest)

    def test_readmes_list_agent_skill_name_and_path(self) -> None:
        english = README_EN.read_text(encoding="utf-8")
        chinese = README_ZH.read_text(encoding="utf-8")
        self.assertIn("Skill name: `eide-rebuild`", english)
        self.assertIn("Skill path: `skills/eide-rebuild/SKILL.md`", english)
        self.assertIn("SkillsMP-style GitHub indexers", english)
        self.assertIn("Skill 名称：`eide-rebuild`", chinese)
        self.assertIn("Skill 路径：`skills/eide-rebuild/SKILL.md`", chinese)
        self.assertIn("SkillsMP-style GitHub indexers", chinese)

    def test_readmes_keep_marketplace_claims_absent(self) -> None:
        for readme in (README_EN, README_ZH):
            content = readme.read_text(encoding="utf-8").lower()
            with self.subTest(readme=readme.name):
                self.assertNotIn("official openai plugin", content)
                self.assertNotIn("listed on skillsmp", content)
