import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_mattpocock_skills_manifest_update_preview.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MattPocockSkillsManifestUpdatePreviewTests(unittest.TestCase):
    def build_fixture(self, root: Path) -> dict[str, object]:
        source = root / "source"
        cc_home = root / "cc-home"
        consumer = root / "consumer"
        source.mkdir()
        (cc_home / "skills").mkdir(parents=True)
        consumer.mkdir()

        subprocess.run(["git", "init", "-q", str(source)], check=True)
        subprocess.run(
            ["git", "-C", str(source), "config", "user.email", "fixture@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(source), "config", "user.name", "Fixture"],
            check=True,
        )

        self.write_skill(source, "skills/engineering/alpha", "alpha old\n")
        (source / "skills/engineering/alpha/CONTEXT.md").write_text(
            "context\n", encoding="utf-8"
        )
        (source / "skills/engineering/alpha/agents").mkdir()
        (source / "skills/engineering/alpha/agents/openai.yaml").write_text(
            "name: alpha\n", encoding="utf-8"
        )
        self.write_skill(source, "skills/productivity/old-skill", "old skill\n")
        self.write_skill(source, "skills/productivity/shared", "shared unchanged\n")
        (source / "LICENSE").write_text("MIT fixture\n", encoding="utf-8")
        self.write_manifest(
            source,
            "0.1.0",
            [
                "./skills/engineering/alpha",
                "./skills/productivity/old-skill",
                "./skills/productivity/shared",
            ],
        )
        subprocess.run(["git", "-C", str(source), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(source), "commit", "-q", "-m", "prior"],
            check=True,
        )
        prior = self.git(source, "rev-parse", "HEAD")

        (source / "skills/productivity/old-skill/SKILL.md").unlink()
        (source / "skills/productivity/old-skill").rmdir()
        self.write_skill(source, "skills/engineering/alpha", "alpha release\n")
        self.write_skill(source, "skills/productivity/beta", "beta release\n")
        self.write_skill(source, "skills/in-progress/gamma", "gamma not promoted\n")
        self.write_manifest(
            source,
            "1.2.2",
            [
                "./skills/engineering/alpha",
                "./skills/productivity/beta",
                "./skills/productivity/shared",
            ],
        )
        subprocess.run(["git", "-C", str(source), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(source), "commit", "-q", "-m", "release"],
            check=True,
        )
        release = self.git(source, "rev-parse", "HEAD")
        subprocess.run(
            ["git", "-C", str(source), "tag", "-a", "v1.2.2", "-m", "v1.2.2"],
            check=True,
        )
        tag_object = self.git(source, "rev-parse", "v1.2.2^{tag}")

        self.write_skill(cc_home, "skills/alpha", "alpha old\r\n")
        (cc_home / "skills/alpha/CONTEXT.md").write_text(
            "context\r\n", encoding="utf-8", newline=""
        )
        (cc_home / "skills/alpha/agents").mkdir()
        (cc_home / "skills/alpha/agents/openai.yaml").write_text(
            "name: alpha\r\n", encoding="utf-8", newline=""
        )
        self.write_skill(cc_home, "skills/old-skill", "old skill\r\n")
        self.write_skill(cc_home, "skills/shared", "shared unchanged\r\n")
        self.write_skill(consumer, "alpha", "consumer marker\n")

        database = cc_home / "cc-switch.db"
        connection = sqlite3.connect(database)
        try:
            connection.execute(
                "CREATE TABLE skills (id TEXT, name TEXT, directory TEXT, "
                "repo_owner TEXT, repo_name TEXT, enabled_claude INTEGER, "
                "enabled_codex INTEGER, enabled_gemini INTEGER, "
                "enabled_grokbuild INTEGER, enabled_opencode INTEGER, "
                "enabled_hermes INTEGER)"
            )
            connection.executemany(
                "INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("alpha", "alpha", "alpha", "mattpocock", "skills", 1, 1, 0, 0, 0, 0),
                    (
                        "old-skill",
                        "old-skill",
                        "old-skill",
                        "mattpocock",
                        "skills",
                        1,
                        1,
                        0,
                        0,
                        0,
                        0,
                    ),
                    (
                        "shared",
                        "shared",
                        "shared",
                        "mattpocock",
                        "skills",
                        1,
                        1,
                        0,
                        0,
                        0,
                        0,
                    ),
                ],
            )
            connection.commit()
        finally:
            connection.close()

        return {
            "source": source,
            "cc_home": cc_home,
            "consumer": consumer,
            "database": database,
            "prior": prior,
            "release": release,
            "tag_object": tag_object,
        }

    @staticmethod
    def write_skill(root: Path, relative: str, body: str) -> None:
        directory = root / relative
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "SKILL.md").write_text(body, encoding="utf-8", newline="")

    @staticmethod
    def write_manifest(root: Path, version: str, skills: list[str]) -> None:
        path = root / ".claude-plugin/plugin.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"name": "fixture", "version": version, "skills": skills}),
            encoding="utf-8",
        )

    @staticmethod
    def git(repository: Path, *args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(repository), *args], text=True
        ).strip()

    def test_builds_manifest_aware_zero_write_atomic_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.build_fixture(Path(temporary))
            database = paths["database"]
            consumer = paths["consumer"]
            self.assertIsInstance(database, Path)
            self.assertIsInstance(consumer, Path)
            database_before = digest(database)
            consumer_before = sorted(
                (path.relative_to(consumer).as_posix(), digest(path))
                for path in consumer.rglob("*")
                if path.is_file()
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--source-git",
                    str(paths["source"]),
                    "--release-tag",
                    "v1.2.2",
                    "--release-tag-object",
                    str(paths["tag_object"]),
                    "--release-commit",
                    str(paths["release"]),
                    "--observed-main-revision",
                    str(paths["release"]),
                    "--prior-revision",
                    str(paths["prior"]),
                    "--observed-at",
                    "2026-08-06T12:00:00+08:00",
                    "--cc-home",
                    str(paths["cc_home"]),
                    "--consumer-root",
                    str(consumer),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["status"], "preview-only-zero-live-mutation")
            self.assertEqual(report["source"]["releaseVersion"], "1.2.2")
            self.assertTrue(report["source"]["tagObjectPeelsToReleaseCommit"])
            self.assertTrue(report["source"]["observedMainEqualsReleaseCommit"])
            self.assertEqual(report["discovery"]["promotedCount"], 3)
            self.assertEqual(report["discovery"]["recursiveSkillCount"], 4)
            self.assertEqual(report["discovery"]["nonPromotedNames"], ["gamma"])
            self.assertEqual(report["liveManager"]["sourceRowCount"], 3)
            self.assertEqual(
                report["liveManager"]["enabledCountByHost"],
                {
                    "claude": 3,
                    "codex": 3,
                    "gemini": 0,
                    "grokbuild": 0,
                    "opencode": 0,
                    "hermes": 0,
                },
            )
            self.assertEqual(report["transition"]["add"], ["beta"])
            self.assertEqual(report["transition"]["remove"], ["old-skill"])
            self.assertEqual(report["transition"]["retainOrReplace"], ["alpha", "shared"])
            self.assertEqual(
                report["liveManager"]["payloadClassificationCounts"],
                {
                    "both-prior-and-release": 1,
                    "prior-only": 2,
                    "release-only": 0,
                    "neither": 0,
                    "missing": 0,
                },
            )
            self.assertFalse(report["transaction"]["executionEligible"])
            self.assertEqual(report["transaction"]["atomicPromotedCohortCount"], 3)
            self.assertEqual(report["consumerTopology"]["roots"][0]["presentCount"], 1)
            self.assertEqual(report["consumerTopology"]["roots"][0]["directoryCount"], 1)
            self.assertEqual(report["consumerTopology"]["roots"][0]["symlinkCount"], 0)
            self.assertEqual(report["consumerTopology"]["directDirectoryCountTotal"], 1)
            self.assertFalse(report["consumerTopology"]["singleManagerRevisionClosureProved"])
            self.assertFalse(
                report["claimBoundary"]["singleManagerRevisionClosureAcrossConsumersProved"]
            )
            self.assertEqual(report["executionCounters"]["managerMutations"], 0)
            self.assertEqual(report["executionCounters"]["consumerWrites"], 0)
            self.assertEqual(digest(database), database_before)
            self.assertEqual(
                sorted(
                    (path.relative_to(consumer).as_posix(), digest(path))
                    for path in consumer.rglob("*")
                    if path.is_file()
                ),
                consumer_before,
            )

    def test_rejects_wrong_tag_or_database_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.build_fixture(Path(temporary))
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--source-git",
                    str(paths["source"]),
                    "--release-tag",
                    "v1.2.2",
                    "--release-tag-object",
                    "0" * 40,
                    "--release-commit",
                    str(paths["release"]),
                    "--observed-main-revision",
                    str(paths["release"]),
                    "--prior-revision",
                    str(paths["prior"]),
                    "--observed-at",
                    "2026-08-06T12:00:00+08:00",
                    "--cc-home",
                    str(paths["cc_home"]),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("release tag object", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
