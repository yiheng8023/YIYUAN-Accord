from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_human_ai_collaboration_semantic_authority_composition_projection import (
    _pinned_git_object_reader,
    materialize_composition,
)
from scripts.build_source_pinned_skill_projection import (
    git_blob_sha1,
    sha256_bytes,
)


def record(path: str, content: bytes) -> dict[str, object]:
    return {
        "path": path,
        "role": "fixture",
        "bytes": len(content),
        "sha256": sha256_bytes(content),
        "gitBlobSha1": git_blob_sha1(content),
    }


class SemanticAuthorityCompositionProjectionTests(unittest.TestCase):
    def test_git_object_reader_fetches_one_exact_commit_then_reads_blobs(self) -> None:
        revision = "b" * 40
        files = {
            "skills/example/SKILL.md": b"---\nname: example\n---\n",
            "LICENSE": b"MIT\n",
        }
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            if "rev-parse" in command:
                return SimpleNamespace(
                    returncode=0,
                    stdout=(revision + "\n").encode(),
                    stderr=b"",
                )
            if "show" in command:
                path = command[-1].split(":", 1)[1]
                return SimpleNamespace(returncode=0, stdout=files[path], stderr=b"")
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            with _pinned_git_object_reader(
                "mattpocock/skills",
                revision,
                parent,
                command_runner=runner,
            ) as reader:
                self.assertEqual(
                    files["skills/example/SKILL.md"],
                    reader(
                        "mattpocock/skills",
                        revision,
                        "skills/example/SKILL.md",
                    ),
                )
            self.assertEqual([], list(parent.iterdir()))

        fetch_calls = [command for command, _ in calls if "fetch" in command]
        self.assertEqual(1, len(fetch_calls))
        self.assertIn(revision, fetch_calls[0])
        self.assertTrue(any("show" in command for command, _ in calls))
        self.assertTrue(all(kwargs["timeout"] == 60 for _, kwargs in calls))

    def fixture(self) -> tuple[dict, dict[str, bytes]]:
        files = {
            "skills/engineering/grill-with-docs/SKILL.md": (
                b"---\nname: grill-with-docs\n---\n"
            ),
            "skills/engineering/grill-with-docs/agents/openai.yaml": b"policy: {}\n",
            "skills/engineering/domain-modeling/SKILL.md": (
                b"---\nname: domain-modeling\n---\n"
            ),
            "skills/engineering/domain-modeling/CONTEXT-FORMAT.md": b"# Context\n",
            "skills/engineering/domain-modeling/ADR-FORMAT.md": b"# ADR\n",
            "skills/engineering/domain-modeling/agents/openai.yaml": b"interface: {}\n",
            "skills/productivity/grilling/SKILL.md": (
                b"---\nname: grilling\n---\n"
            ),
            "skills/productivity/grilling/agents/openai.yaml": b"interface: {}\n",
            "LICENSE": b"MIT fixture\n",
        }
        admission = {
            "source": {
                "repository": "https://github.com/example/skills",
                "revision": "a" * 40,
            },
            "exactPackageFiles": [
                record(path, content)
                for path, content in files.items()
                if path != "LICENSE"
            ],
            "license": {
                **record("LICENSE", files["LICENSE"]),
                "spdx": "MIT",
            },
        }
        return admission, files

    def test_materializes_three_exact_skill_roots(self) -> None:
        admission, files = self.fixture()
        calls: list[tuple[str, str, str]] = []

        def reader(repository: str, revision: str, path: str) -> bytes:
            calls.append((repository, revision, path))
            return files[path]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "projection"
            manifest = materialize_composition(
                root,
                admission=admission,
                github_reader=reader,
            )
            self.assertEqual(
                ["domain-modeling", "grill-with-docs", "grilling"],
                manifest["requiredSkillNames"],
            )
            self.assertEqual(
                set(manifest["requiredSkillNames"]),
                set(manifest["skillPaths"]),
            )
            for path, content in files.items():
                if path == "LICENSE":
                    continue
                parts = Path(path).parts
                projected = (
                    root
                    / ".agents"
                    / "skills"
                    / parts[2]
                    / Path(*parts[3:])
                )
                self.assertEqual(content, projected.read_bytes())
        self.assertEqual(9, len(calls))

    def test_digest_drift_fails_closed(self) -> None:
        admission, files = self.fixture()
        drifted = copy.deepcopy(admission)
        drifted["exactPackageFiles"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 drifted"):
                materialize_composition(
                    Path(temporary) / "projection",
                    admission=drifted,
                    github_reader=lambda _r, _v, path: files[path],
                )

    def test_nonempty_output_fails_closed(self) -> None:
        admission, files = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "user.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "must not already contain"):
                materialize_composition(
                    root,
                    admission=admission,
                    github_reader=lambda _r, _v, path: files[path],
                )

    def test_read_failure_leaves_no_partial_projection(self) -> None:
        admission, files = self.fixture()
        calls = 0

        def reader(_repository: str, _revision: str, path: str) -> bytes:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected transport failure")
            return files[path]

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "projection"
            with self.assertRaisesRegex(RuntimeError, "injected transport failure"):
                materialize_composition(
                    root,
                    admission=admission,
                    github_reader=reader,
                )
            self.assertFalse(root.exists())

    def test_write_failure_rolls_back_existing_output_without_partial_projection(self) -> None:
        admission, files = self.fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "projection"
            root.mkdir()
            preserved = root / "user.txt"
            preserved.write_text("preserve", encoding="utf-8")
            original_write = Path.write_bytes
            writes = 0

            def fail_second_write(path: Path, content: bytes) -> int:
                nonlocal writes
                writes += 1
                if writes == 2:
                    raise OSError("injected write failure")
                return original_write(path, content)

            with patch.object(Path, "write_bytes", fail_second_write):
                with self.assertRaisesRegex(OSError, "injected write failure"):
                    materialize_composition(
                        root,
                        admission=admission,
                        allow_existing=True,
                        github_reader=lambda _r, _v, path: files[path],
                    )

            self.assertEqual("preserve", preserved.read_text(encoding="utf-8"))
            self.assertFalse((root / ".agents").exists())
            self.assertFalse((root / ".aah-provenance").exists())
            self.assertFalse(
                (root / "SEMANTIC-AUTHORITY-COMPOSITION-PROJECTION.json").exists()
            )


if __name__ == "__main__":
    unittest.main()
