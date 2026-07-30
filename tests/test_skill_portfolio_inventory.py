from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from scripts.inventory_skill_portfolio import build_inventory


class SkillPortfolioInventoryTests(unittest.TestCase):
    def test_inventory_distinguishes_database_physical_and_missing_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for relative in (
                ".cc-switch/skills/present",
                ".agents/skills/present",
                ".claude/skills",
                ".codex/skills",
                ".cc-switch/skill-backups/one",
            ):
                (home / relative).mkdir(parents=True, exist_ok=True)
            (home / ".cc-switch/skills/present/SKILL.md").write_text(
                "---\nname: present\n---\n", encoding="utf-8"
            )
            (home / ".agents/skills/present/SKILL.md").write_text(
                "---\nname: present\n---\n", encoding="utf-8"
            )
            (home / ".cc-switch/settings.json").write_text(
                json.dumps(
                    {
                        "skillStorageLocation": "cc_switch",
                        "skillSyncMethod": "symlink",
                        "secret": "must-not-escape",
                    }
                ),
                encoding="utf-8",
            )
            database = home / ".cc-switch/cc-switch.db"
            connection = sqlite3.connect(database)
            connection.executescript(
                """
                create table skills (
                  name text, directory text, repo_owner text, repo_name text,
                  enabled_claude boolean, enabled_codex boolean,
                  enabled_gemini boolean, enabled_opencode boolean,
                  enabled_hermes boolean
                );
                create table skill_repos (
                  owner text, name text, branch text, enabled boolean
                );
                insert into skills values
                  ('present','present',null,null,1,1,0,0,0),
                  ('missing','missing',null,null,1,1,0,0,0);
                insert into skill_repos values ('owner','repo','main',1);
                """
            )
            connection.commit()
            connection.close()

            result = build_inventory(home)

            self.assertEqual(2, result["database"]["rows"])
            self.assertEqual(
                1,
                result["database"]["rootPresence"]["ccSwitch"][
                    "databaseRowsWithResolvableSkillMd"
                ],
            )
            self.assertEqual(
                "cc_switch",
                result["settings"]["selected"]["skillStorageLocation"],
            )
            self.assertNotIn("secret", result["settings"]["selected"])
            self.assertFalse(result["claimBoundary"]["authorizesRepairOrCleanup"])


if __name__ == "__main__":
    unittest.main()
