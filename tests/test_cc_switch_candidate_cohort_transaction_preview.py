import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_cc_switch_candidate_cohort_transaction_preview.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CcSwitchCandidateCohortTransactionPreviewTests(unittest.TestCase):
    def build_fixture(self, fixture: Path) -> dict[str, Path | str]:
        authority = fixture / "authority"
        sources = fixture / "sources"
        cc_home = fixture / "cc-home"
        consumer = fixture / "consumer"
        authority.mkdir()
        sources.mkdir()
        (cc_home / "skills").mkdir(parents=True)
        consumer.mkdir()

        repo = sources / "example__repo"
        (repo / "skills" / "alpha" / "references").mkdir(parents=True)
        (repo / "skills" / "beta").mkdir(parents=True)
        (repo / "skills" / "alpha" / "SKILL.md").write_text(
            "---\nname: alpha\n---\nSee [rules](references/rules.md).\n",
            encoding="utf-8",
        )
        (repo / "skills" / "alpha" / "references" / "rules.md").write_text(
            "alpha rules\n", encoding="utf-8"
        )
        (repo / "skills" / "beta" / "SKILL.md").write_text(
            "---\nname: beta\n---\nbeta body\n", encoding="utf-8"
        )
        (repo / "LICENSE").write_text("fixture license\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.email", "fixture@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "config", "user.name", "Fixture"], check=True
        )
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "fixture"], check=True
        )
        commit = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip()

        gate = authority / "gate.json"
        gate.write_text(
            json.dumps(
                {
                    "items": [
                        {
                            "name": "alpha",
                            "path": "skills/alpha",
                            "dependencyFiles": [
                                {"path": "skills/alpha/references/rules.md"}
                            ],
                            "disposition": "manager-install-candidate-default-disabled",
                        },
                        {
                            "name": "beta",
                            "path": "skills/beta/SKILL.md",
                            "disposition": "manager-install-candidate-default-disabled",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        cohort = authority / "cohort.json"
        cohort.write_text(
            json.dumps(
                {
                    "sourceGateCoverage": {
                        "sources": [
                            {
                                "repository": "example/repo",
                                "commit": commit,
                                "gateRecord": "gate.json",
                            }
                        ]
                    },
                    "staticDefaultDisabledCandidates": {
                        "count": 2,
                        "bySource": {"example/repo": ["alpha", "beta"]},
                    },
                }
            ),
            encoding="utf-8",
        )
        mapping = authority / "mapping.json"
        mapping.write_text(
            json.dumps(
                {
                    "candidateMappings": [
                        {"name": "alpha", "effectGroupId": "effect.alpha"},
                        {"name": "beta", "effectGroupId": "effect.beta"},
                    ]
                }
            ),
            encoding="utf-8",
        )

        database = cc_home / "cc-switch.db"
        conn = sqlite3.connect(database)
        try:
            conn.execute(
                "CREATE TABLE skills (id TEXT, name TEXT, directory TEXT, "
                "repo_owner TEXT, repo_name TEXT, enabled_claude INTEGER, "
                "enabled_codex INTEGER, enabled_gemini INTEGER, "
                "enabled_grokbuild INTEGER, enabled_opencode INTEGER, "
                "enabled_hermes INTEGER)"
            )
            conn.commit()
        finally:
            conn.close()
        return {
            "authority": authority,
            "sources": sources,
            "cc_home": cc_home,
            "consumer": consumer,
            "repo": repo,
            "cohort": cohort,
            "mapping": mapping,
            "database": database,
            "commit": commit,
        }

    def run_preview(self, paths: dict[str, Path | str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--authority-root",
                str(paths["authority"]),
                "--cohort",
                str(paths["cohort"]),
                "--mapping",
                str(paths["mapping"]),
                "--source-root",
                str(paths["sources"]),
                "--cc-home",
                str(paths["cc_home"]),
                "--consumer-root",
                str(paths["consumer"]),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_builds_disabled_preview_without_mutating_manager_or_consumers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp)
            paths = self.build_fixture(fixture)
            database = paths["database"]
            consumer = paths["consumer"]
            self.assertIsInstance(database, Path)
            self.assertIsInstance(consumer, Path)
            before_database = sha256(database)
            before_consumer = list(consumer.rglob("*"))

            result = self.run_preview(paths)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["candidateCount"], 2)
            self.assertEqual(report["sourceCount"], 1)
            self.assertEqual(report["collisionCount"], 0)
            self.assertTrue(report["allInitialAppsDisabled"])
            self.assertFalse(report["transaction"]["executionEligible"])
            self.assertEqual(
                report["status"],
                "preview-built-zero-live-mutation-manager-fork-unmerged",
            )
            self.assertEqual(
                report["managerContribution"]["forkHead"],
                "3db0288c2e3d34d26578839c3c14296eed7c6476",
            )
            self.assertEqual(
                report["managerContribution"]["draftPullRequest"],
                "https://github.com/farion1231/cc-switch/pull/6086",
            )
            self.assertTrue(
                report["claimBoundary"]["managerBatchTransactionImplementedInFork"]
            )
            self.assertFalse(
                report["claimBoundary"]["managerBatchTransactionMergedOrReleased"]
            )
            self.assertEqual(report["executionCounters"]["managerMutations"], 0)
            self.assertEqual(
                [candidate["name"] for candidate in report["candidates"]],
                ["alpha", "beta"],
            )
            self.assertEqual(report["candidates"][0]["outOfRootMarkdownLinks"], [])
            admission = report["candidates"][0]["managerAdmission"]
            self.assertEqual(len(admission["sourceTreeHash"]), 64)
            self.assertEqual(len(admission["dependencyClosureDigest"]), 64)
            self.assertTrue(admission["dependencyComplete"])
            self.assertEqual(
                report["managerContribution"]["trustBoundary"],
                {
                    "revisionObjectTypeIndependentlyProved": False,
                    "dependencyClosureSemanticallyProvedByManager": False,
                    "materializedSourceTreeHashVerifiedByManager": True,
                    "exactNestedSourcePathRequired": True,
                    "repositoryRootSkillSupported": False,
                    "recoveryDurability": "interrupted-process-only",
                },
            )
            self.assertEqual(sha256(database), before_database)
            self.assertEqual(list(consumer.rglob("*")), before_consumer)

    def test_rejects_source_revision_drift_without_mutating_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.build_fixture(Path(tmp))
            database = paths["database"]
            cohort = paths["cohort"]
            self.assertIsInstance(database, Path)
            self.assertIsInstance(cohort, Path)
            document = json.loads(cohort.read_text(encoding="utf-8"))
            document["sourceGateCoverage"]["sources"][0]["commit"] = "0" * 40
            cohort.write_text(json.dumps(document), encoding="utf-8")
            before_database = sha256(database)

            result = self.run_preview(paths)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Source revision mismatch", result.stderr)
            self.assertEqual(sha256(database), before_database)

    def test_reports_live_collisions_without_overwriting_any_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.build_fixture(Path(tmp))
            database = paths["database"]
            cc_home = paths["cc_home"]
            consumer = paths["consumer"]
            self.assertIsInstance(database, Path)
            self.assertIsInstance(cc_home, Path)
            self.assertIsInstance(consumer, Path)
            conn = sqlite3.connect(database)
            try:
                conn.execute(
                    "INSERT INTO skills (id, name, directory, repo_owner, repo_name) "
                    "VALUES (?, ?, ?, ?, ?)",
                    ("existing", "existing-alpha", "alpha", "old", "repo"),
                )
                conn.commit()
            finally:
                conn.close()
            ssot_marker = cc_home / "skills" / "alpha" / "marker.txt"
            consumer_marker = consumer / "alpha" / "marker.txt"
            ssot_marker.parent.mkdir()
            consumer_marker.parent.mkdir()
            ssot_marker.write_text("keep ssot\n", encoding="utf-8")
            consumer_marker.write_text("keep consumer\n", encoding="utf-8")
            before_database = sha256(database)

            result = self.run_preview(paths)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["collisionCount"], 3)
            self.assertFalse(report["transaction"]["executionEligible"])
            self.assertEqual(report["executionCounters"]["managerMutations"], 0)
            self.assertEqual(sha256(database), before_database)
            self.assertEqual(ssot_marker.read_text(encoding="utf-8"), "keep ssot\n")
            self.assertEqual(
                consumer_marker.read_text(encoding="utf-8"), "keep consumer\n"
            )

    def test_reports_out_of_root_markdown_links_as_dependency_debt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.build_fixture(Path(tmp))
            repo = paths["repo"]
            self.assertIsInstance(repo, Path)
            skill = repo / "skills" / "alpha" / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8")
                + "See [external](../../../tools/external.md).\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-m", "external link"],
                check=True,
            )
            cohort = paths["cohort"]
            self.assertIsInstance(cohort, Path)
            document = json.loads(cohort.read_text(encoding="utf-8"))
            document["sourceGateCoverage"]["sources"][0]["commit"] = (
                subprocess.check_output(
                    ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
                ).strip()
            )
            cohort.write_text(json.dumps(document), encoding="utf-8")

            result = self.run_preview(paths)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            alpha = report["candidates"][0]
            self.assertEqual(
                alpha["outOfRootMarkdownLinks"],
                [
                    {
                        "source": "SKILL.md",
                        "target": "../../../tools/external.md",
                    }
                ],
            )
            self.assertFalse(report["claimBoundary"]["operationalDependencyClosureProved"])
            self.assertFalse(alpha["managerAdmission"]["dependencyComplete"])


if __name__ == "__main__":
    unittest.main()
