from __future__ import annotations

from pathlib import Path
import json
import os
import sqlite3
import subprocess
import tempfile
import time
import unittest

import scripts.update_matt_cc_manager_cohort as transaction_module


compute_cc_directory_hash = transaction_module.compute_cc_directory_hash
execute_transaction = getattr(
    transaction_module,
    "execute_transaction",
    lambda *args, **kwargs: {"status": "not-implemented"},
)
rollback_transaction = getattr(
    transaction_module,
    "rollback_transaction",
    lambda *args, **kwargs: {"status": "not-implemented"},
)
ensure_manager_quiesced = getattr(
    transaction_module,
    "ensure_manager_quiesced",
    lambda _process_ids: None,
)


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


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def write_skill(root: Path, name: str, description: str, *, script: bool = False) -> None:
    root.mkdir(parents=True)
    (root / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
        newline="\n",
    )
    if script:
        (root / "template.sh").write_text(
            "echo should-not-run > third-party-script-ran.txt\n",
            encoding="utf-8",
            newline="\n",
        )


def create_source(repository: Path) -> str:
    repository.mkdir()
    run_git(repository, "init")
    run_git(repository, "config", "user.email", "fixture@example.invalid")
    run_git(repository, "config", "user.name", "Fixture")
    paths = {
        "alpha": "skills/engineering/alpha",
        "beta": "skills/productivity/beta",
        "wizard": "skills/engineering/wizard",
    }
    write_skill(repository / paths["alpha"], "alpha", "new alpha")
    write_skill(repository / paths["beta"], "beta", "new beta")
    write_skill(repository / paths["wizard"], "wizard", "dangerous wizard", script=True)
    plugin = repository / ".claude-plugin" / "plugin.json"
    plugin.parent.mkdir()
    plugin.write_text(
        json.dumps({"version": "1.2.2", "skills": list(paths.values())}),
        encoding="utf-8",
        newline="\n",
    )
    run_git(repository, "add", ".")
    run_git(repository, "commit", "-m", "fixture")
    revision = run_git(repository, "rev-parse", "HEAD")
    run_git(repository, "tag", "-a", "v1.2.2", "-m", "fixture release")
    return revision


def insert_skill(connection: sqlite3.Connection, name: str, now: int) -> None:
    connection.execute(
        """
        INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"mattpocock/skills:skills/engineering/{name}",
            name,
            f"old {name}",
            name,
            "mattpocock",
            "skills",
            "main",
            f"https://github.com/mattpocock/skills/blob/main/{name}/SKILL.md",
            1,
            1,
            0,
            0,
            0,
            now,
            None,
            0,
            0,
        ),
    )


def make_link(target: Path, link: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(target, link, target_is_directory=True)


def build_fixture(raw: str) -> dict[str, Path | str]:
    root = Path(raw)
    home = root / "home"
    cc = home / ".cc-switch"
    ssot = cc / "skills"
    backups = cc / "skill-backups"
    backups.mkdir(parents=True)
    write_skill(ssot / "alpha", "alpha", "old alpha")
    write_skill(ssot / "old", "old", "retired")
    write_skill(ssot / "unrelated", "unrelated", "must survive")
    database = cc / "cc-switch.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute(SKILLS_SCHEMA)
        now = int(time.time()) - 100
        insert_skill(connection, "alpha", now)
        insert_skill(connection, "old", now)
        connection.commit()
    finally:
        connection.close()
    for projection in (
        home / ".claude" / "skills",
        home / ".codex" / "skills",
        home / ".agents" / "skills",
    ):
        make_link(ssot / "alpha", projection / "alpha")
        make_link(ssot / "old", projection / "old")
    source = root / "source"
    revision = create_source(source)
    return {
        "home": home,
        "source": source,
        "revision": revision,
        "transaction": backups / "transaction",
    }


class UpdateMattCcManagerCohortTests(unittest.TestCase):
    def test_cc_hash_matches_manager_path_content_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "skill"
            (root / "nested").mkdir(parents=True)
            (root / "a.txt").write_bytes(b"A")
            (root / "nested" / "b.txt").write_bytes(b"B")
            (root / ".ignored").write_bytes(b"not hashed")

            result = compute_cc_directory_hash(root)

        self.assertEqual(
            "96122064ecf1824a3da4b7076fe2f4d1225bf254622809f0386502bdaca4235f",
            result,
        )

    def test_live_transaction_rejects_a_running_manager(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "CC Switch is still running"):
            ensure_manager_quiesced([41304])

    def test_release_tag_must_peel_to_the_requested_commit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = build_fixture(raw)

            with self.assertRaisesRegex(ValueError, "release tag"):
                execute_transaction(
                    home=fixture["home"],
                    source_git=fixture["source"],
                    release_commit="0" * 40,
                    release_tag="v1.2.2",
                    transaction_root=fixture["transaction"],
                    expected_live_names=("alpha", "old"),
                    expected_target_names=("alpha", "beta", "wizard"),
                    require_manager_quiesced=False,
                )

    def test_success_replaces_the_whole_cohort_and_keeps_wizard_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = build_fixture(raw)

            result = execute_transaction(
                home=fixture["home"],
                source_git=fixture["source"],
                release_commit=fixture["revision"],
                release_tag="v1.2.2",
                transaction_root=fixture["transaction"],
                expected_live_names=("alpha", "old"),
                expected_target_names=("alpha", "beta", "wizard"),
                require_manager_quiesced=False,
            )
            self.assertNotEqual("not-implemented", result["status"])

            home = fixture["home"]
            ssot = home / ".cc-switch" / "skills"
            connection = sqlite3.connect(home / ".cc-switch" / "cc-switch.db")
            try:
                rows = connection.execute(
                    "SELECT directory, repo_branch, enabled_claude, enabled_codex "
                    "FROM skills ORDER BY directory"
                ).fetchall()
            finally:
                connection.close()
            projection_results = {}
            for label, projection in {
                "claude": home / ".claude" / "skills",
                "codex": home / ".codex" / "skills",
                "agents": home / ".agents" / "skills",
            }.items():
                projection_results[label] = {
                    name: (projection / name).is_symlink()
                    for name in ("alpha", "beta", "old", "wizard")
                }
            journal = json.loads(
                (fixture["transaction"] / "journal.json").read_text(encoding="utf-8")
            )
            filesystem = {
                "alphaDescription": _description(ssot / "alpha" / "SKILL.md"),
                "betaPresent": (ssot / "beta" / "SKILL.md").is_file(),
                "wizardScriptPresent": (ssot / "wizard" / "template.sh").is_file(),
                "oldPresent": (ssot / "old").exists(),
                "unrelatedPresent": (ssot / "unrelated" / "SKILL.md").is_file(),
                "originalRootPresent": (
                    fixture["transaction"] / "original-skills"
                ).is_dir(),
                "databaseCopies": list(fixture["transaction"].rglob("*.db")),
                "thirdPartyScriptRan": (home / "third-party-script-ran.txt").exists(),
            }

        self.assertEqual("committed", result["status"])
        self.assertEqual("new alpha", filesystem["alphaDescription"])
        self.assertTrue(filesystem["betaPresent"])
        self.assertTrue(filesystem["wizardScriptPresent"])
        self.assertFalse(filesystem["oldPresent"])
        self.assertTrue(filesystem["unrelatedPresent"])
        self.assertEqual(
            [
                ("alpha", "v1.2.2", 1, 1),
                ("beta", "v1.2.2", 1, 1),
                ("wizard", "v1.2.2", 0, 0),
            ],
            rows,
        )
        for topology in projection_results.values():
            self.assertEqual(
                {"alpha": True, "beta": True, "old": False, "wizard": False},
                topology,
            )
        self.assertEqual("committed", journal["status"])
        self.assertTrue(filesystem["originalRootPresent"])
        self.assertEqual([], filesystem["databaseCopies"])
        self.assertFalse(filesystem["thirdPartyScriptRan"])

    def test_failure_after_ssot_swap_restores_the_entire_prior_cohort(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = build_fixture(raw)

            try:
                with self.assertRaisesRegex(RuntimeError, "injected-after-ssot-swap"):
                    execute_transaction(
                        home=fixture["home"],
                        source_git=fixture["source"],
                        release_commit=fixture["revision"],
                        release_tag="v1.2.2",
                        transaction_root=fixture["transaction"],
                        expected_live_names=("alpha", "old"),
                        expected_target_names=("alpha", "beta", "wizard"),
                        require_manager_quiesced=False,
                        failure_point="after-ssot-swap",
                    )
            except TypeError:
                self.fail("failure injection is not implemented")

            state = fixture_state(fixture)

        self.assertEqual(["alpha", "old"], state["databaseNames"])
        self.assertEqual("old alpha", state["alphaDescription"])
        self.assertTrue(state["oldPresent"])
        self.assertFalse(state["betaPresent"])
        self.assertFalse(state["wizardPresent"])
        for topology in state["projections"].values():
            self.assertEqual(
                {"alpha": True, "beta": False, "old": True, "wizard": False},
                topology,
            )
        self.assertEqual("rolled-back-after-error", state["journalStatus"])
        self.assertEqual([], state["databaseCopies"])

    def test_failure_after_database_commit_restores_rows_ssot_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = build_fixture(raw)

            with self.assertRaisesRegex(RuntimeError, "injected-after-database-commit"):
                execute_transaction(
                    home=fixture["home"],
                    source_git=fixture["source"],
                    release_commit=fixture["revision"],
                    release_tag="v1.2.2",
                    transaction_root=fixture["transaction"],
                    expected_live_names=("alpha", "old"),
                    expected_target_names=("alpha", "beta", "wizard"),
                    require_manager_quiesced=False,
                    failure_point="after-database-commit",
                )

            state = fixture_state(fixture)

        self.assertEqual(["alpha", "old"], state["databaseNames"])
        self.assertEqual("old alpha", state["alphaDescription"])
        self.assertTrue(state["oldPresent"])
        self.assertFalse(state["betaPresent"])
        self.assertFalse(state["wizardPresent"])
        for topology in state["projections"].values():
            self.assertEqual(
                {"alpha": True, "beta": False, "old": True, "wizard": False},
                topology,
            )
        self.assertEqual("rolled-back-after-error", state["journalStatus"])

    def test_failure_after_projection_update_restores_every_projection(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = build_fixture(raw)

            with self.assertRaisesRegex(RuntimeError, "injected-after-projection-update"):
                execute_transaction(
                    home=fixture["home"],
                    source_git=fixture["source"],
                    release_commit=fixture["revision"],
                    release_tag="v1.2.2",
                    transaction_root=fixture["transaction"],
                    expected_live_names=("alpha", "old"),
                    expected_target_names=("alpha", "beta", "wizard"),
                    require_manager_quiesced=False,
                    failure_point="after-projection-update",
                )

            state = fixture_state(fixture)

        self.assertEqual(["alpha", "old"], state["databaseNames"])
        self.assertEqual("old alpha", state["alphaDescription"])
        for topology in state["projections"].values():
            self.assertEqual(
                {"alpha": True, "beta": False, "old": True, "wizard": False},
                topology,
            )
        self.assertEqual("rolled-back-after-error", state["journalStatus"])

    def test_explicit_rollback_restores_a_committed_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            fixture = build_fixture(raw)
            execute_transaction(
                home=fixture["home"],
                source_git=fixture["source"],
                release_commit=fixture["revision"],
                release_tag="v1.2.2",
                transaction_root=fixture["transaction"],
                expected_live_names=("alpha", "old"),
                expected_target_names=("alpha", "beta", "wizard"),
                require_manager_quiesced=False,
            )

            result = rollback_transaction(
                home=fixture["home"],
                transaction_root=fixture["transaction"],
                require_manager_quiesced=False,
            )
            self.assertNotEqual("not-implemented", result["status"])
            state = fixture_state(fixture)

        self.assertEqual("rolled-back", result["status"])
        self.assertEqual(["alpha", "old"], state["databaseNames"])
        self.assertEqual("old alpha", state["alphaDescription"])
        for topology in state["projections"].values():
            self.assertEqual(
                {"alpha": True, "beta": False, "old": True, "wizard": False},
                topology,
            )
        self.assertEqual("rolled-back", state["journalStatus"])


def _description(skill_md: Path) -> str:
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("description missing")


def fixture_state(fixture: dict[str, Path | str]) -> dict[str, object]:
    home = fixture["home"]
    ssot = home / ".cc-switch" / "skills"
    connection = sqlite3.connect(home / ".cc-switch" / "cc-switch.db")
    try:
        database_names = [
            row[0]
            for row in connection.execute(
                "SELECT directory FROM skills ORDER BY directory"
            ).fetchall()
        ]
    finally:
        connection.close()
    projections = {}
    for label, projection in {
        "claude": home / ".claude" / "skills",
        "codex": home / ".codex" / "skills",
        "agents": home / ".agents" / "skills",
    }.items():
        projections[label] = {
            name: (projection / name).is_symlink()
            for name in ("alpha", "beta", "old", "wizard")
        }
    journal = json.loads(
        (fixture["transaction"] / "journal.json").read_text(encoding="utf-8")
    )
    return {
        "databaseNames": database_names,
        "alphaDescription": _description(ssot / "alpha" / "SKILL.md"),
        "oldPresent": (ssot / "old").is_dir(),
        "betaPresent": (ssot / "beta").is_dir(),
        "wizardPresent": (ssot / "wizard").is_dir(),
        "projections": projections,
        "journalStatus": journal["status"],
        "databaseCopies": list(fixture["transaction"].rglob("*.db")),
    }


if __name__ == "__main__":
    unittest.main()
