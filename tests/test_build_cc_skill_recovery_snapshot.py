from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_cc_skill_recovery_snapshot import build_snapshot


def write_skill(root: Path, name: str, body: str = "# Skill\n") -> None:
    target = root / name
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text(body, encoding="utf-8")


def build_fixture(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    canonical = tmp_path / "canonical"
    for name in ("cc", "agents", "claude", "codex"):
        mapping = {
            "cc": home / ".cc-switch/skills",
            "agents": home / ".agents/skills",
            "claude": home / ".claude/skills",
            "codex": home / ".codex/skills",
        }
        mapping[name].mkdir(parents=True)

    for name in ("ordinary", *("intent-contract", "capability-router", "closure-contract")):
        write_skill(home / ".cc-switch/skills", name)
    for name in ("intent-contract", "capability-router", "closure-contract", "lark-doc"):
        write_skill(home / ".agents/skills", name)
    for name in ("intent-contract", "capability-router", "closure-contract"):
        write_skill(canonical / "skills", name)
    backup = home / ".cc-switch/skill-backups/backup-001"
    write_skill(backup, "skill")
    (backup / "meta.json").write_text(
        '{"skill":{"directory":"ordinary"}}', encoding="utf-8"
    )

    database = home / ".cc-switch/cc-switch.db"
    connection = sqlite3.connect(database)
    connection.execute(
        """
        create table skills (
          id text, name text, description text, directory text,
          repo_owner text, repo_name text, repo_branch text, readme_url text,
          enabled_claude integer, enabled_codex integer, enabled_gemini integer,
          enabled_opencode integer, enabled_hermes integer, installed_at text,
          content_hash text, updated_at text, enabled_grokbuild integer
        )
        """
    )
    connection.execute(
        "create table skill_repos (owner text, name text, branch text, enabled integer)"
    )
    connection.execute(
        "insert into skills values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "1",
            "ordinary",
            "fixture",
            "ordinary",
            "owner",
            "repo",
            "main",
            "https://example.test",
            1,
            1,
            0,
            0,
            0,
            "now",
            "hash",
            "now",
            0,
        ),
    )
    connection.execute("insert into skill_repos values ('owner','repo','main',1)")
    connection.commit()
    connection.close()
    return home, canonical


class CcSkillRecoverySnapshotTests(unittest.TestCase):
    def test_snapshot_excludes_settings_and_raw_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            home, canonical = build_fixture(tmp_path)
            (home / ".cc-switch/settings.json").write_text(
                '{"password":"must-not-appear"}', encoding="utf-8"
            )
            output = tmp_path / "recovery.zip"

            result = build_snapshot(home, canonical, output)

            self.assertTrue(
                result["verification"]["extractedPayloadHashesMatched"]
            )
            with zipfile.ZipFile(output) as bundle:
                names = set(bundle.namelist())
                self.assertIn("metadata/snapshot.json", names)
                self.assertFalse(any("settings.json" in name for name in names))
                self.assertFalse(any(name.endswith("cc-switch.db") for name in names))
                metadata = json.loads(bundle.read("metadata/snapshot.json"))
            self.assertFalse(metadata["secretScan"]["settingsRead"])
            self.assertFalse(metadata["secretScan"]["rawDatabaseCopied"])
            self.assertEqual(len(metadata["databaseMetadata"]["skills"]), 1)
            self.assertEqual(metadata["scope"]["ccExistingBackups"], ["backup-001"])
            self.assertTrue(
                any(name.startswith("payload/cc-existing-backups/") for name in names)
            )
            self.assertTrue(
                result["verification"]["archiveSecretRescanPassed"]
            )
            self.assertTrue(all(result["sourceConsistency"].values()))
            self.assertTrue((tmp_path / "recovery.manifest.json").is_file())

    def test_snapshot_rejects_high_confidence_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            home, canonical = build_fixture(tmp_path)
            (home / ".cc-switch/skills/ordinary/SKILL.md").write_text(
                "token = sk-proj-abcdefghijklmnopqrstuvwxyz123456",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "openai-key"):
                build_snapshot(home, canonical, tmp_path / "recovery.zip")

    def test_snapshot_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            home, canonical = build_fixture(tmp_path)
            output = tmp_path / "recovery.zip"
            output.write_bytes(b"existing")

            with self.assertRaises(FileExistsError):
                build_snapshot(home, canonical, output)

    def test_snapshot_rejects_sensitive_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tmp_path = Path(temporary)
            home, canonical = build_fixture(tmp_path)
            (home / ".cc-switch/skills/ordinary/.env").write_text(
                "EXAMPLE=value", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "sensitive filename"):
                build_snapshot(home, canonical, tmp_path / "recovery.zip")


if __name__ == "__main__":
    unittest.main()
