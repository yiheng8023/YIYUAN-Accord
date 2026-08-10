from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock
import subprocess

from scripts.program_acceptance_authority_v2 import AcceptanceAuthorityError
from scripts.program_acceptance_authority_v2_rehearsal import (
    replace_selector_atomically,
    run_rehearsal,
)


ROOT = Path(__file__).resolve().parent.parent


class ProgramAcceptanceAuthorityRehearsalTests(unittest.TestCase):
    def test_rehearsal_builds_selects_rolls_back_and_cleans_disposable_root(self) -> None:
        """A broken rehearsal must not report a verified rollback lifecycle."""

        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "rehearsal"
            result = run_rehearsal(ROOT, output)
            self.assertFalse(output.exists())
        self.assertEqual(
            "verified-zero-model-versioning-and-migration-rehearsal-only",
            result["status"],
        )
        self.assertEqual(2, result["highestGeneration"])
        self.assertEqual(1, result["rollbackGeneration"])
        self.assertEqual(
            {"verified": 46, "partial": 15, "planned": 0},
            result["acceptanceInventory"],
        )

    def test_file_output_rejects_repository_authority_root(self) -> None:
        """A caller must not turn the tracked authority area into rehearsal output."""

        with self.assertRaises(AcceptanceAuthorityError) as raised:
            run_rehearsal(ROOT, ROOT / "registry/program-acceptance-authority")
        self.assertEqual("acceptance-activation-not-authorized", raised.exception.code)

    def test_atomic_selector_failure_preserves_existing_sentinel(self) -> None:
        """A failed final replace must retain the already-selected byte stream exactly."""

        with tempfile.TemporaryDirectory() as parent:
            selector = Path(parent) / "current.json"
            sentinel = b"sentinel-selector-bytes\n"
            selector.write_bytes(sentinel)
            with mock.patch("os.replace", side_effect=OSError("replace denied")):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    replace_selector_atomically(selector, b"candidate-selector-bytes\n")
            self.assertEqual("acceptance-atomic-output-preserved", raised.exception.code)
            self.assertEqual(sentinel, selector.read_bytes())
            self.assertEqual([], list(Path(parent).glob(".current.json.*.tmp")))

    def test_builder_cli_emits_one_clean_zero_counter_result(self) -> None:
        """The public subprocess entrypoint must retain the no-surviving-root contract."""

        completed = subprocess.run(
            [
                "python",
                "-B",
                "scripts/build_program_acceptance_authority_v2_rehearsal.py",
                "--root",
                ".",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("", completed.stderr)
        result = __import__("json").loads(completed.stdout)
        self.assertEqual("verified-zero-model-versioning-and-migration-rehearsal-only", result["status"])
        self.assertTrue(all(value == 0 for value in result["executionCounters"].values()))
