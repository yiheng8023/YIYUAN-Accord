from pathlib import Path
import json
import sqlite3
import tempfile
import unittest

from scripts.reconcile_skill_source_authority import build_reconciliation


class SkillSourceAuthorityReconciliationTests(unittest.TestCase):
    def test_reconciliation_separates_exact_alias_and_unresolved_runtime_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = root / "repo"
            home = root / "home"
            (repository / "registry").mkdir(parents=True)
            (repository / "skills/approved").mkdir(parents=True)
            (repository / "skills/approved/SKILL.md").write_text("approved", encoding="utf-8")
            (repository / "registry/skills.json").write_text(
                json.dumps({"skills": [{"directory": "approved", "status": "approved"}]}),
                encoding="utf-8",
            )
            (home / ".cc-switch/skills/approved").mkdir(parents=True)
            (home / ".cc-switch/skills/approved/SKILL.md").write_text("approved", encoding="utf-8")
            for path in (
                home / ".codex/plugins/cache/vendor/package/1/skills/exact/SKILL.md",
                home / ".codex/plugins/cache/vendor/suite/1/skills/index/SKILL.md",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("runtime", encoding="utf-8")

            database = home / ".cc-switch/cc-switch.db"
            database.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(database)
            connection.execute(
                "create table skills (name text,directory text,repo_owner text,repo_name text)"
            )
            connection.executemany(
                "insert into skills values (?,?,?,?)",
                [
                    ("approved", "approved", None, None),
                    ("exact", "exact", None, None),
                    ("index", "suite-index", None, None),
                    ("gone", "gone", None, None),
                ],
            )
            connection.commit()
            connection.close()

            result = build_reconciliation(repository, home)

            self.assertEqual(1, result["approvedRepositoryPayloads"]["treeEqual"])
            runtime = result["missingCcPhysicalRuntimeReconciliation"]
            self.assertEqual(3, runtime["count"])
            self.assertEqual(1, runtime["exactPluginDirectoryMatches"])
            self.assertEqual(1, runtime["qualifiedPluginAliasMatches"])
            self.assertEqual([{"name": "gone", "directory": "gone"}], runtime["unresolved"])
            self.assertFalse(result["claimBoundary"]["authorizesProjectionRepair"])


if __name__ == "__main__":
    unittest.main()
