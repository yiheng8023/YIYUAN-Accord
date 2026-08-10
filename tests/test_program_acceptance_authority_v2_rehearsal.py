from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock
import subprocess
import os
import shutil

from scripts.program_acceptance_authority_v2 import AcceptanceAuthorityError
from scripts.program_acceptance_authority_v2_rehearsal import (
    RECORD_PATH,
    REQUIRED_FAILURE_CASES,
    REQUIRED_TYPED_CODES,
    build_rehearsal_bundle,
    replace_selector_atomically,
    run_rehearsal,
    validate_repository_record,
    write_rehearsal_bundle,
)


ROOT = Path(__file__).resolve().parent.parent
_BATCH_ONE_EXPECTED_CASES = (
    ("inventory-duplicate-row", "migration-inventory-incomplete"),
    ("inventory-extra-row", "migration-inventory-incomplete"),
    ("inventory-reordered-rows", "migration-inventory-incomplete"),
    ("inventory-bool-line", "migration-consumer-class-invalid"),
    ("inventory-float-line", "migration-consumer-class-invalid"),
    ("selector-absolute", "acceptance-selector-target-invalid"),
    ("selector-parent-escape", "acceptance-selector-target-invalid"),
    ("selector-symlink-escape", "acceptance-selector-target-invalid"),
    ("selector-snapshot-digest", "acceptance-selector-target-invalid"),
    ("selector-receipt-digest", "acceptance-transition-receipt-invalid"),
    ("selector-plan-digest", "acceptance-selector-target-invalid"),
    ("selector-mode", "acceptance-selector-target-invalid"),
    ("selector-activation-bool", "acceptance-activation-not-authorized"),
    ("selector-counter-float", "acceptance-side-effect-counter-nonzero"),
    ("atomic-sentinel-preserved", "acceptance-atomic-output-preserved"),
    ("cli-protected-output", "acceptance-activation-not-authorized"),
    ("cleanup-fault", "acceptance-rehearsal-cleanup-incomplete"),
)


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

    def test_atomic_selector_double_fault_preserves_sentinel_and_original_cause(self) -> None:
        """A failed cleanup cannot replace the primary atomic-write rejection."""

        with tempfile.TemporaryDirectory() as parent:
            selector = Path(parent) / "current.json"
            sentinel = b"sentinel-selector-bytes\n"
            selector.write_bytes(sentinel)
            with (
                mock.patch("os.replace", side_effect=OSError("replace denied")),
                mock.patch.object(Path, "unlink", side_effect=OSError("cleanup denied")),
            ):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    replace_selector_atomically(selector, b"candidate-selector-bytes\n")
            self.assertEqual("acceptance-atomic-output-preserved", raised.exception.code)
            self.assertIsInstance(raised.exception.__cause__, OSError)
            self.assertEqual("replace denied", str(raised.exception.__cause__))
            self.assertEqual(sentinel, selector.read_bytes())

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

    def test_cleanup_refuses_a_timing_swapped_external_symlink(self) -> None:
        """A swap before cleanup must fail closed without descending into an external sentinel."""

        with tempfile.TemporaryDirectory() as parent:
            parent_path = Path(parent)
            output = parent_path / "rehearsal"
            external = parent_path / "external"
            external.mkdir()
            sentinel = external / "sentinel.txt"
            sentinel.write_bytes(b"external-sentinel\n")
            original_replace = os.replace

            def swap_before_cleanup(source: object, destination: object) -> None:
                if Path(source) == output:
                    parking = parent_path / "parking"
                    original_replace(output, parking)
                    os.symlink(external, output, target_is_directory=True)
                original_replace(source, destination)

            with mock.patch("os.replace", side_effect=swap_before_cleanup):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    run_rehearsal(ROOT, output)
            self.assertEqual("acceptance-rehearsal-cleanup-incomplete", raised.exception.code)
            self.assertEqual(b"external-sentinel\n", sentinel.read_bytes())
            if (parent_path / "parking").exists():
                shutil.rmtree(parent_path / "parking")

    def test_repository_record_is_canonical_and_replays_the_required_matrix(self) -> None:
        """The tracked evidence record is a wire-checked replay, not a trusted summary."""

        record = validate_repository_record(ROOT)
        self.assertEqual(
            (ROOT / RECORD_PATH).read_bytes(),
            __import__("scripts.program_acceptance_authority_v2", fromlist=["canonical_file_bytes"]).canonical_file_bytes(record),
        )
        self.assertEqual(
            REQUIRED_FAILURE_CASES,
            tuple((row["caseId"], row["expectedCode"]) for row in record["failureMatrix"]),
        )
        self.assertIn("scripts/harness_decision_packet.py", record["fileDigests"])
        unique_codes: list[str] = []
        for row in record["failureMatrix"]:
            if row["expectedCode"] not in unique_codes:
                unique_codes.append(row["expectedCode"])
        self.assertEqual(REQUIRED_TYPED_CODES, tuple(unique_codes))
        self.assertEqual(
            {
                "g000001": {"criteriaCount": 61, "assessmentInventory": {"verified": 46, "partial": 15, "planned": 0}},
                "g000002": {"criteriaCount": 61, "assessmentInventory": {"verified": 46, "partial": 15, "planned": 0}},
            },
            record["generationProjections"],
        )
        self.assertEqual("partial", record["targetCriterion"])
        actual_cases = {row["caseId"]: row["expectedCode"] for row in record["failureMatrix"]}
        self.assertEqual(dict(_BATCH_ONE_EXPECTED_CASES), {case_id: actual_cases[case_id] for case_id, _ in _BATCH_ONE_EXPECTED_CASES})

    def test_record_validator_cli_types_invalid_utf8(self) -> None:
        """The standalone replay CLI must envelope malformed record bytes."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / RECORD_PATH
            record.parent.mkdir(parents=True)
            record.write_bytes(b"\xff")
            completed = subprocess.run(
                ["python", "-B", str(ROOT / "scripts/validate_program_acceptance_authority_v2_rehearsal.py")],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(2, completed.returncode)
        self.assertEqual("acceptance-rehearsal-record-invalid", __import__("json").loads(completed.stderr)["code"])

    def test_public_writer_types_stage_cleanup_fault_and_removes_stage(self) -> None:
        """A failed stage cleanup must not leak OSError or leave a sibling stage root."""

        with tempfile.TemporaryDirectory() as parent:
            parent_path = Path(parent)
            output = parent_path / "rehearsal"
            bundle = build_rehearsal_bundle(ROOT)
            bundle["curation-program-plan-v2.json"] += b"\n"
            original_rmtree = shutil.rmtree
            failed_once = False

            def fail_once(path: object, *args: object, **kwargs: object) -> None:
                nonlocal failed_once
                if Path(path).name.startswith(".rehearsal.stage-") and not failed_once:
                    failed_once = True
                    raise OSError("stage cleanup denied")
                original_rmtree(path, *args, **kwargs)

            with mock.patch("scripts.program_acceptance_authority_v2_rehearsal.shutil.rmtree", side_effect=fail_once):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    write_rehearsal_bundle(output, bundle)
            self.assertEqual("acceptance-rehearsal-cleanup-incomplete", raised.exception.code)
            self.assertEqual([], list(parent_path.glob(".rehearsal.stage-*")))
