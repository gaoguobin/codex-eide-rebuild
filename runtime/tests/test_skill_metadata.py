from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_FILE = REPO_ROOT / "skills" / "eide-rebuild" / "SKILL.md"
OPENAI_YAML = REPO_ROOT / "skills" / "eide-rebuild" / "agents" / "openai.yaml"


class SkillMetadataTests(unittest.TestCase):
    def test_skill_files_exist(self) -> None:
        self.assertTrue(SKILL_FILE.exists())
        self.assertTrue(OPENAI_YAML.exists())

    def test_skill_mentions_natural_language_prompts(self) -> None:
        content = SKILL_FILE.read_text(encoding="utf-8")
        self.assertIn("你自己编译验证下对不对", content)
        self.assertIn("帮我编译确认一下", content)
        self.assertIn("EIDE subagent rebuild", content)
