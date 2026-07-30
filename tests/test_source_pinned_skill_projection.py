from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.build_source_pinned_skill_projection import (
    git_blob_sha1,
    materialize_candidate,
    sha256_bytes,
)
from scripts.validate_source_pinned_debugging_skill_projection_protocol import (
    ROOT,
    validate_protocol,
)


def file_record(source: str, projection: str, content: bytes) -> dict[str, object]:
    return {
        "sourceRelativePath": source,
        "projectionRelativePath": projection,
        "bytes": len(content),
        "sha256": sha256_bytes(content),
        "gitBlobSha1": git_blob_sha1(content),
        "publicUpstreamMatch": True,
    }


class SourcePinnedSkillProjectionTests(unittest.TestCase):
    def test_current_protocol_is_valid(self) -> None:
        path = (
            ROOT
            / "registry"
            / "source-pinned-debugging-skill-projection-protocol-2026-07-24.json"
        )
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([], validate_protocol(document))

    def test_local_package_projection_is_byte_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "package"
            output = base / "output"
            skill = b"---\nname: demo\n---\n\n# Demo\n"
            license_content = b"MIT test license\n"
            manifest = b'{"name":"demo","version":"1"}\n'
            (package / "skills" / "demo").mkdir(parents=True)
            (package / ".codex-plugin").mkdir(parents=True)
            (package / "skills" / "demo" / "SKILL.md").write_bytes(skill)
            (package / "LICENSE").write_bytes(license_content)
            (package / ".codex-plugin" / "plugin.json").write_bytes(manifest)
            candidate = {
                "candidateId": "test.demo",
                "skillName": "demo",
                "sourceClass": "openai-curated-runtime-distributed-third-party",
                "source": {
                    "packageRoot": package.as_posix(),
                    "packageVersion": "1",
                    "pluginManifestRelativePath": ".codex-plugin/plugin.json",
                    "pluginManifestBytes": len(manifest),
                    "pluginManifestSha256": sha256_bytes(manifest),
                    "readMode": "test-local-package",
                },
                "license": {
                    **file_record("LICENSE", "LICENSE", license_content),
                    "spdx": "MIT",
                },
                "files": [
                    file_record(
                        "skills/demo/SKILL.md",
                        "SKILL.md",
                        skill,
                    )
                ],
            }
            result = materialize_candidate(
                candidate,
                output,
                superpowers_package_root=package,
            )
            self.assertEqual(
                skill,
                (output / ".agents" / "skills" / "demo" / "SKILL.md").read_bytes(),
            )
            self.assertFalse(result["sourceMutated"])
            self.assertFalse(result["hostTurnStarted"])

    def test_git_projection_reads_pinned_object_not_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo = base / "repo"
            output = base / "output"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Projection Test"],
                check=True,
            )
            source_path = repo / "skills" / "demo"
            source_path.mkdir(parents=True)
            original = b"---\nname: demo\n---\n\n# Original\n"
            license_content = b"MIT test license\n"
            (source_path / "SKILL.md").write_bytes(original)
            (repo / "LICENSE").write_bytes(license_content)
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-qm", "fixture"],
                check=True,
            )
            revision = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            (source_path / "SKILL.md").write_bytes(b"working-tree drift\n")
            candidate = {
                "candidateId": "test.git-demo",
                "skillName": "demo",
                "sourceClass": "reviewed-maintained-external-public-git",
                "source": {
                    "revision": revision,
                    "readMode": "git-show-immutable-revision-never-working-tree",
                },
                "license": {
                    **file_record("LICENSE", "LICENSE", license_content),
                    "spdx": "MIT",
                },
                "files": [
                    file_record(
                        "skills/demo/SKILL.md",
                        "SKILL.md",
                        original,
                    )
                ],
            }
            materialize_candidate(
                candidate,
                output,
                matt_checkout=repo,
            )
            self.assertEqual(
                original,
                (output / ".agents" / "skills" / "demo" / "SKILL.md").read_bytes(),
            )

    def test_github_api_projection_uses_exact_revision_and_hashes(self) -> None:
        skill = b"---\nname: remote-demo\n---\n\n# Remote\n"
        license_content = b"MIT remote license\n"
        candidate = {
            "candidateId": "test.remote-demo",
            "skillName": "remote-demo",
            "sourceClass": "reviewed-maintained-external-public-github-api",
            "source": {
                "githubRepository": "example/skills",
                "revision": "a" * 40,
                "readMode": "test-reader",
            },
            "license": {
                **file_record("LICENSE", "LICENSE", license_content),
                "spdx": "MIT",
            },
            "files": [
                file_record(
                    "skills/remote-demo/SKILL.md",
                    "SKILL.md",
                    skill,
                )
            ],
        }
        calls = []

        def reader(repository: str, revision: str, path: str) -> bytes:
            calls.append((repository, revision, path))
            return {
                "LICENSE": license_content,
                "skills/remote-demo/SKILL.md": skill,
            }[path]

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            manifest = materialize_candidate(
                candidate,
                output,
                github_reader=reader,
            )
            self.assertEqual(
                skill,
                (
                    output
                    / ".agents"
                    / "skills"
                    / "remote-demo"
                    / "SKILL.md"
                ).read_bytes(),
            )
        self.assertEqual(
            {
                (
                    "example/skills",
                    "a" * 40,
                    "skills/remote-demo/SKILL.md",
                ),
                ("example/skills", "a" * 40, "LICENSE"),
            },
            set(calls),
        )
        self.assertTrue(manifest["sourceLocator"]["externalReadOnly"])

    def test_projection_refuses_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "existing.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "must not already"):
                materialize_candidate(
                    {
                        "candidateId": "unused",
                        "skillName": "unused",
                        "sourceClass": "unsupported",
                        "source": {},
                        "files": [],
                        "license": {},
                    },
                    output,
                )

    def test_projection_can_add_reserved_namespaces_without_overwriting_fixture(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "package"
            output = base / "output"
            output.mkdir()
            (output / "TASK.json").write_text("preserve\n", encoding="utf-8")
            skill = b"---\nname: demo\n---\n"
            license_content = b"MIT\n"
            manifest = b"{}\n"
            (package / "skills" / "demo").mkdir(parents=True)
            (package / ".codex-plugin").mkdir(parents=True)
            (package / "skills" / "demo" / "SKILL.md").write_bytes(skill)
            (package / "LICENSE").write_bytes(license_content)
            (package / ".codex-plugin" / "plugin.json").write_bytes(manifest)
            candidate = {
                "candidateId": "test.demo",
                "skillName": "demo",
                "sourceClass": "openai-curated-runtime-distributed-third-party",
                "source": {
                    "packageVersion": "1",
                    "pluginManifestRelativePath": ".codex-plugin/plugin.json",
                    "pluginManifestBytes": len(manifest),
                    "pluginManifestSha256": sha256_bytes(manifest),
                    "readMode": "test",
                },
                "license": {
                    **file_record("LICENSE", "LICENSE", license_content),
                    "spdx": "MIT",
                },
                "files": [
                    file_record(
                        "skills/demo/SKILL.md",
                        "SKILL.md",
                        skill,
                    )
                ],
            }
            materialize_candidate(
                candidate,
                output,
                superpowers_package_root=package,
                allow_existing=True,
            )
            self.assertEqual(
                "preserve\n",
                (output / "TASK.json").read_text(encoding="utf-8"),
            )

    def test_digest_drift_fails_closed(self) -> None:
        content = b"real\n"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "package"
            output = base / "output"
            (package / "skills" / "demo").mkdir(parents=True)
            (package / ".codex-plugin").mkdir(parents=True)
            (package / "skills" / "demo" / "SKILL.md").write_bytes(content)
            (package / "LICENSE").write_bytes(b"MIT\n")
            manifest = b"{}\n"
            (package / ".codex-plugin" / "plugin.json").write_bytes(manifest)
            candidate = {
                "candidateId": "test.demo",
                "skillName": "demo",
                "sourceClass": "openai-curated-runtime-distributed-third-party",
                "source": {
                    "packageVersion": "1",
                    "pluginManifestRelativePath": ".codex-plugin/plugin.json",
                    "pluginManifestBytes": len(manifest),
                    "pluginManifestSha256": sha256_bytes(manifest),
                    "readMode": "test",
                },
                "license": {
                    **file_record("LICENSE", "LICENSE", b"MIT\n"),
                    "spdx": "MIT",
                },
                "files": [
                    {
                        **file_record(
                            "skills/demo/SKILL.md",
                            "SKILL.md",
                            content,
                        ),
                        "sha256": hashlib.sha256(b"wrong").hexdigest(),
                    }
                ],
            }
            with self.assertRaisesRegex(RuntimeError, "SHA-256 drifted"):
                materialize_candidate(
                    candidate,
                    output,
                    superpowers_package_root=package,
                )


if __name__ == "__main__":
    unittest.main()
