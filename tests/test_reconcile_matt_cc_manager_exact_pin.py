from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

from scripts.reconcile_matt_cc_manager_exact_pin import (
    reconcile_exact_pin,
    rollback_exact_pin,
)
from scripts.update_matt_cc_manager_cohort import SKILL_COLUMNS


SKILLS_SCHEMA = """
CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    directory TEXT NOT NULL,
    repo_owner TEXT,
    repo_name TEXT,
    repo_branch TEXT DEFAULT 'main',
    readme_url TEXT,
    enabled_claude BOOLEAN NOT NULL DEFAULT 0,
    enabled_codex BOOLEAN NOT NULL DEFAULT 0,
    enabled_gemini BOOLEAN NOT NULL DEFAULT 0,
    enabled_opencode BOOLEAN NOT NULL DEFAULT 0,
    enabled_hermes BOOLEAN NOT NULL DEFAULT 0,
    installed_at INTEGER NOT NULL DEFAULT 0,
    content_hash TEXT,
    updated_at INTEGER NOT NULL DEFAULT 0,
    enabled_grokbuild BOOLEAN NOT NULL DEFAULT 0
)
"""


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def write_skill(root: Path, name: str, body: str = "payload") -> None:
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {name}\n---\n\n{body}\n",
        encoding="utf-8",
        newline="\n",
    )


def make_source(root: Path) -> str:
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "fixture@example.invalid")
    git(root, "config", "user.name", "Fixture")
    write_skill(root / "skills" / "engineering" / "alpha", "alpha")
    write_skill(root / "skills" / "engineering" / "wizard", "wizard")
    manifest = root / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "version": "1.2.3",
                "skills": [
                    "skills/engineering/alpha",
                    "skills/engineering/wizard",
                ],
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    revision = git(root, "rev-parse", "HEAD")
    git(root, "tag", "-a", "v1.2.3", "-m", "fixture")
    return revision


def insert_row(connection: sqlite3.Connection, home: Path, name: str) -> None:
    skill_root = home / ".cc-switch" / "skills" / name
    enabled = int(name != "wizard")
    values = {
        "id": f"mattpocock/skills:skills/engineering/{name}",
        "name": name,
        "description": name,
        "directory": name,
        "repo_owner": "mattpocock",
        "repo_name": "skills",
        "repo_branch": "main",
        "readme_url": (
            "https://github.com/mattpocock/skills/blob/main/"
            f"skills/engineering/{name}/SKILL.md"
        ),
        "enabled_claude": enabled,
        "enabled_codex": enabled,
        "enabled_gemini": 0,
        "enabled_opencode": 0,
        "enabled_hermes": 0,
        "installed_at": 100,
        # CC Switch owns this field's internal contract. The pin transaction
        # must preserve it instead of assuming it is a portable tree digest.
        "content_hash": f"opaque-manager-hash-{name}",
        "updated_at": 200,
        "enabled_grokbuild": 0,
    }
    connection.execute(
        f"INSERT INTO skills ({', '.join(SKILL_COLUMNS)}) VALUES ({', '.join('?' for _ in SKILL_COLUMNS)})",
        [values[column] for column in SKILL_COLUMNS],
    )


def link(target: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target, destination, target_is_directory=True)


def make_fixture(raw: str) -> dict[str, Path | str]:
    root = Path(raw)
    home = root / "home"
    ssot = home / ".cc-switch" / "skills"
    for name in ("alpha", "wizard"):
        write_skill(ssot / name, name)
    backups = home / ".cc-switch" / "skill-backups"
    backups.mkdir()
    database = home / ".cc-switch" / "cc-switch.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute(SKILLS_SCHEMA)
        for name in ("alpha", "wizard"):
            insert_row(connection, home, name)
        connection.commit()
    finally:
        connection.close()
    for projection in (".claude", ".codex", ".agents"):
        link(ssot / "alpha", home / projection / "skills" / "alpha")
    source = root / "source"
    revision = make_source(source)
    return {
        "home": home,
        "source": source,
        "revision": revision,
        "transaction": backups / "pin-transaction",
    }


def rows(home: Path) -> list[dict[str, object]]:
    connection = sqlite3.connect(home / ".cc-switch" / "cc-switch.db")
    connection.row_factory = sqlite3.Row
    try:
        return [
            dict(row)
            for row in connection.execute(
                f"SELECT {', '.join(SKILL_COLUMNS)} FROM skills ORDER BY directory"
            )
        ]
    finally:
        connection.close()


class ReconcileMattCcManagerExactPinTests(unittest.TestCase):
    def test_metadata_only_transaction_preserves_payloads_links_and_other_columns(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = make_fixture(raw)
            home = fixture["home"]
            assert isinstance(home, Path)
            before_rows = rows(home)
            before_payloads = {
                name: (home / ".cc-switch" / "skills" / name / "SKILL.md").read_bytes()
                for name in ("alpha", "wizard")
            }
            before_links = {
                projection: os.readlink(home / projection / "skills" / "alpha")
                for projection in (".claude", ".codex", ".agents")
            }

            result = reconcile_exact_pin(
                home=home,
                source_git=fixture["source"],
                release_commit=str(fixture["revision"]),
                release_tag="v1.2.3",
                transaction_root=fixture["transaction"],
                expected_names=("alpha", "wizard"),
                require_manager_quiesced=False,
                updated_at=300,
            )

            after_rows = rows(home)
            self.assertEqual("committed", result["status"])
            self.assertEqual({"v1.2.3"}, {row["repo_branch"] for row in after_rows})
            self.assertTrue(all("/blob/v1.2.3/" in str(row["readme_url"]) for row in after_rows))
            for before, after in zip(before_rows, after_rows, strict=True):
                for column in SKILL_COLUMNS:
                    if column not in {"repo_branch", "readme_url", "updated_at"}:
                        self.assertEqual(before[column], after[column], column)
                self.assertEqual(300, after["updated_at"])
            self.assertEqual(
                before_payloads,
                {
                    name: (home / ".cc-switch" / "skills" / name / "SKILL.md").read_bytes()
                    for name in ("alpha", "wizard")
                },
            )
            self.assertEqual(
                before_links,
                {
                    projection: os.readlink(home / projection / "skills" / "alpha")
                    for projection in (".claude", ".codex", ".agents")
                },
            )
            journal = json.loads((fixture["transaction"] / "journal.json").read_text())
            self.assertEqual("committed", journal["status"])
            self.assertFalse(journal["payloadsWritten"])
            self.assertFalse(journal["projectionsWritten"])

    def test_payload_drift_is_rejected_before_database_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = make_fixture(raw)
            home = fixture["home"]
            assert isinstance(home, Path)
            before = rows(home)
            (home / ".cc-switch" / "skills" / "alpha" / "SKILL.md").write_text(
                "drift", encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "payload does not match exact release"):
                reconcile_exact_pin(
                    home=home,
                    source_git=fixture["source"],
                    release_commit=str(fixture["revision"]),
                    release_tag="v1.2.3",
                    transaction_root=fixture["transaction"],
                    expected_names=("alpha", "wizard"),
                    require_manager_quiesced=False,
                )
            self.assertEqual(before, rows(home))
            self.assertFalse(Path(fixture["transaction"]).exists())

    def test_failure_after_commit_restores_original_rows(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = make_fixture(raw)
            home = fixture["home"]
            assert isinstance(home, Path)
            before = rows(home)
            with self.assertRaisesRegex(RuntimeError, "injected-after-database-commit"):
                reconcile_exact_pin(
                    home=home,
                    source_git=fixture["source"],
                    release_commit=str(fixture["revision"]),
                    release_tag="v1.2.3",
                    transaction_root=fixture["transaction"],
                    expected_names=("alpha", "wizard"),
                    require_manager_quiesced=False,
                    failure_point="after-database-commit",
                )
            self.assertEqual(before, rows(home))
            journal = json.loads((fixture["transaction"] / "journal.json").read_text())
            self.assertEqual("rolled-back-after-error", journal["status"])

    def test_explicit_rollback_restores_only_pin_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = make_fixture(raw)
            home = fixture["home"]
            assert isinstance(home, Path)
            before = rows(home)
            reconcile_exact_pin(
                home=home,
                source_git=fixture["source"],
                release_commit=str(fixture["revision"]),
                release_tag="v1.2.3",
                transaction_root=fixture["transaction"],
                expected_names=("alpha", "wizard"),
                require_manager_quiesced=False,
            )

            result = rollback_exact_pin(
                home=home,
                transaction_root=fixture["transaction"],
                require_manager_quiesced=False,
            )

            self.assertEqual("rolled-back", result["status"])
            self.assertEqual(before, rows(home))


if __name__ == "__main__":
    unittest.main()
