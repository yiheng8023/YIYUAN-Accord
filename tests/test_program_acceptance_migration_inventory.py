from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.program_acceptance_authority_v2 import AcceptanceAuthorityError
from scripts.harness_decision_packet import strict_json_equal
from scripts import program_acceptance_migration_inventory as migration_inventory
from scripts.program_acceptance_migration_inventory import (
    LEGACY_ACCEPTANCE_SEARCH_PATTERNS,
    SOURCE_PATTERN_IDS,
    discover_acceptance_reference_occurrences,
    load_migration_inventory,
    migration_inventory_wire_bytes,
    validate_migration_inventory,
)


ROOT = Path(__file__).resolve().parent.parent


class ProgramAcceptanceMigrationInventoryTests(unittest.TestCase):
    def test_discovery_finds_live_tracked_occurrences_with_symbolic_pattern_ids(self) -> None:
        """Dropping tracked legacy references must make discovery visibly incomplete."""

        discovered = discover_acceptance_reference_occurrences(ROOT)

        self.assertTrue(discovered)
        for occurrence in discovered:
            self.assertEqual(
                {"path", "line", "patternId", "lineSha256"}, set(occurrence)
            )
            self.assertIn(
                occurrence["patternId"],
                {"legacy-acceptance-path", "legacy-acceptance-id"},
            )

    def test_inventory_covers_the_fresh_live_occurrence_set_exactly_once(self) -> None:
        """An omitted, duplicated, stale, or reordered row must not pass reconciliation."""

        inventory = load_migration_inventory(ROOT)
        validate_migration_inventory(ROOT, inventory)
        discovered = discover_acceptance_reference_occurrences(ROOT)
        projected = [
            {key: row[key] for key in ("path", "line", "patternId", "lineSha256")}
            for row in inventory["occurrences"]
        ]
        self.assertEqual(discovered, projected)

    def test_missing_occurrence_fails_closed(self) -> None:
        """Removing one governed occurrence must have a stable rejection code."""

        inventory = load_migration_inventory(ROOT)
        inventory["occurrences"].pop()
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            validate_migration_inventory(ROOT, inventory)
        self.assertEqual("migration-inventory-incomplete", raised.exception.code)

    def test_inventory_rejects_exact_set_and_typed_governance_mutations(self) -> None:
        """Changing coverage or a class policy must fail rather than silently reclassify."""

        inventory = load_migration_inventory(ROOT)

        missing = copy.deepcopy(inventory)
        missing["occurrences"].pop()
        duplicate = copy.deepcopy(inventory)
        duplicate["occurrences"].append(copy.deepcopy(duplicate["occurrences"][0]))
        stale = copy.deepcopy(inventory)
        stale["occurrences"][0]["lineSha256"] = "0" * 64
        for mutated in (missing, duplicate, stale):
            with self.subTest(shape="exact-set"):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_migration_inventory(ROOT, mutated)
                self.assertEqual("migration-inventory-incomplete", raised.exception.code)

        def semantic_error(mutated: dict[str, object], code: str) -> None:
            rows = mutated["occurrences"]
            assert isinstance(rows, list)
            projection = [
                {key: row[key] for key in ("path", "line", "patternId", "lineSha256")}
                for row in rows
                if isinstance(row, dict)
            ]
            with mock.patch.object(
                migration_inventory,
                "discover_acceptance_reference_occurrences",
                return_value=projection,
            ):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_migration_inventory(ROOT, mutated)
            self.assertEqual(code, raised.exception.code)

        invalid_class = copy.deepcopy(inventory)
        invalid_class["occurrences"][0]["classification"] = "not-a-class"
        semantic_error(invalid_class, "migration-consumer-class-invalid")

        boolean_alias = copy.deepcopy(inventory)
        boolean_alias["occurrences"][0]["separateAuthorizationRequired"] = 1
        semantic_error(boolean_alias, "migration-consumer-class-invalid")

        historical_repoint = copy.deepcopy(inventory)
        historical = next(
            row
            for row in historical_repoint["occurrences"]
            if row["classification"] == "A-immutable-historical"
        )
        historical["candidateBinding"] = "rehearsal-selector"
        semantic_error(historical_repoint, "acceptance-historical-consumer-repointed")

        current_bypass = copy.deepcopy(inventory)
        current = next(
            row
            for row in current_bypass["occurrences"]
            if row["classification"] == "B-current-authority-consumer"
        )
        current["rehearsalAction"] = "activate legacy-v1"
        semantic_error(current_bypass, "acceptance-current-consumer-legacy-bypass")

        neutral_path_owner = copy.deepcopy(inventory)
        neutral = neutral_path_owner["occurrences"][0]
        neutral["classification"] = "C-version-neutral-component"
        neutral["currentBinding"] = "migration-metadata"
        neutral["candidateBinding"] = "migration-metadata"
        semantic_error(neutral_path_owner, "acceptance-neutral-consumer-path-owned")

    def test_only_the_exact_legacy_host_locator_may_retain_the_raw_path_literal(self) -> None:
        """Moving the path literal out of its host-locator identity must fail closed."""

        inventory = load_migration_inventory(ROOT)
        legacy_path = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-path"]

        def raw_literal_error(field: str) -> None:
            mutated = copy.deepcopy(inventory)
            row = next(
                row for row in mutated["occurrences"] if row["path"] != legacy_path
            )
            row[field] = legacy_path
            with self.assertRaises(AcceptanceAuthorityError) as raised:
                validate_migration_inventory(ROOT, mutated)
            self.assertEqual("migration-consumer-class-invalid", raised.exception.code)

        for field in ("purpose", "rehearsalAction", "lineSha256"):
            with self.subTest(field=field):
                raw_literal_error(field)

        wrong_host = copy.deepcopy(inventory)
        row = next(row for row in wrong_host["occurrences"] if row["path"] != legacy_path)
        row["path"] = legacy_path
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            validate_migration_inventory(ROOT, wrong_host)
        self.assertEqual("migration-inventory-incomplete", raised.exception.code)

    def test_tracked_unclassified_reference_in_a_temporary_git_root_fails_closed(self) -> None:
        """A fresh tracked literal cannot disappear merely because it lacks a reviewed row."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            literal = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-path"]
            (root / "unclassified.txt").write_text(
                f"reference={literal}\n", encoding="utf-8"
            )
            subprocess.run(["git", "-C", str(root), "add", "unclassified.txt"], check=True)
            discovered = discover_acceptance_reference_occurrences(root)
            self.assertEqual(1, len(discovered))
            self.assertEqual("legacy-acceptance-path", discovered[0]["patternId"])
            inventory = {
                "schema": 1,
                "id": "temporary-inventory",
                "date": "2026-08-10",
                "status": "review-required",
                "sourcePatternIds": list(SOURCE_PATTERN_IDS),
                "baselineObservation": {
                    "trackedReferenceCount": 0,
                    "occurrenceCount": 0,
                    "referenceSetSha256": hashlib.sha256(
                        json.dumps([], separators=(",", ":")).encode("utf-8") + b"\n"
                    ).hexdigest(),
                },
                "occurrences": [],
                "claimBoundary": {
                    "provesLiveMigration": False,
                    "provesCurrentSelectorActivation": False,
                    "provesBehavior": False,
                    "provesValue": False,
                    "provesCrossHostPortability": False,
                    "provesProductionReadiness": False,
                    "provesReleaseEligibility": False,
                    "provesOverallHarnessCompletion": False,
                },
            }
            with self.assertRaises(AcceptanceAuthorityError) as raised:
                validate_migration_inventory(root, inventory)
            self.assertEqual("migration-inventory-incomplete", raised.exception.code)

    def test_reviewed_inventory_remains_free_of_raw_legacy_literals(self) -> None:
        """Leaking a raw search literal into the record would make its identity self-referential."""

        inventory = load_migration_inventory(ROOT)
        legacy_path = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-path"]
        raw_host_rows = [row for row in inventory["occurrences"] if row["path"] == legacy_path]
        self.assertTrue(raw_host_rows)
        sanitized = copy.deepcopy(inventory)
        for row in sanitized["occurrences"]:
            if row["path"] == legacy_path:
                row["path"] = "allowed-legacy-host-locator"
        payload = json.dumps(
            sanitized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        for literal in LEGACY_ACCEPTANCE_SEARCH_PATTERNS.values():
            self.assertNotIn(literal.encode("utf-8"), payload)
        self.assertTrue(strict_json_equal(inventory["sourcePatternIds"], SOURCE_PATTERN_IDS))

    def test_inventory_wire_serializer_rebuilds_the_reviewed_bytes_exactly(self) -> None:
        """Changing wire ordering or the narrow host escape must fail this checked replay."""

        inventory = load_migration_inventory(ROOT)
        expected = (
            ROOT
            / "registry/program-acceptance-authority-v2-migration-inventory-2026-08-10.json"
        ).read_bytes()
        self.assertEqual(expected, migration_inventory_wire_bytes(inventory))

    def test_public_loader_rejects_noncanonical_wire_bytes(self) -> None:
        """Appending a byte or changing the narrow escape must not survive public loading."""

        source = (
            ROOT
            / "registry/program-acceptance-authority-v2-migration-inventory-2026-08-10.json"
        ).read_bytes()
        decoded = json.loads(source)
        reordered = {key: decoded[key] for key in reversed(decoded)}
        legacy_path = LEGACY_ACCEPTANCE_SEARCH_PATTERNS["legacy-acceptance-path"]
        escaped_path = legacy_path.replace("/", "\\/").encode("utf-8")
        unescaped_path = legacy_path.encode("utf-8")
        cases = (
            source + b"\n",
            source.replace(escaped_path, unescaped_path),
            json.dumps(reordered, separators=(",", ":")).encode("utf-8") + b"\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = Path("inventory.json")
            for payload in cases:
                (root / path).write_bytes(payload)
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    load_migration_inventory(root, path)
                self.assertEqual("migration-inventory-incomplete", raised.exception.code)

    def test_public_loader_types_invalid_utf8_as_incomplete_inventory(self) -> None:
        """An invalid UTF-8 inventory must not leak a decoder error across the public API."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = Path("inventory.json")
            (root / path).write_bytes(b"\xff")
            with self.assertRaises(Exception) as raised:
                load_migration_inventory(root, path)
        self.assertIsInstance(raised.exception, AcceptanceAuthorityError)
        self.assertEqual("migration-inventory-incomplete", raised.exception.code)

    def test_exact_class_policy_matrix_rejects_each_tuple_member_drift(self) -> None:
        """Every governance member must match its class's complete fixed policy tuple."""

        inventory = load_migration_inventory(ROOT)
        valid_tuples = {
            "A-immutable-historical": (
                "historical",
                "legacy-v1",
                "preserve-legacy-v1",
                "preserve",
                "no-repoint",
                "retain",
                "exact-set",
                False,
                "acceptance-historical-consumer-repointed",
            ),
            "B-current-authority-consumer": (
                "current",
                "legacy-v1",
                "rehearsal-selector",
                "selector",
                "separate-authority",
                "receipt",
                "exact-set",
                True,
                "acceptance-current-consumer-legacy-bypass",
            ),
            "C-version-neutral-component": (
                "version-neutral",
                "explicit-input",
                "explicit-input",
                "validate-input",
                "not-applicable",
                "not-applicable",
                "explicit-input",
                False,
                "acceptance-neutral-consumer-path-owned",
            ),
            "D-migration-governance-and-regression": (
                "governance",
                "migration-metadata",
                "migration-metadata",
                "zero-model",
                "separate-authority",
                "receipt",
                "exact-set",
                True,
                "migration-consumer-class-invalid",
            ),
        }
        fields = (
            "purpose",
            "currentBinding",
            "candidateBinding",
            "rehearsalAction",
            "liveMigrationAction",
            "rollbackAction",
            "verificationSurface",
            "separateAuthorizationRequired",
        )

        def validate_semantics(mutated: dict[str, object], expected_code: str) -> None:
            rows = mutated["occurrences"]
            assert isinstance(rows, list)
            projection = [
                {key: row[key] for key in ("path", "line", "patternId", "lineSha256")}
                for row in rows
                if isinstance(row, dict)
            ]
            with mock.patch.object(
                migration_inventory,
                "discover_acceptance_reference_occurrences",
                return_value=projection,
            ):
                with self.assertRaises(AcceptanceAuthorityError) as raised:
                    validate_migration_inventory(ROOT, mutated)
            self.assertEqual(expected_code, raised.exception.code)

        for classification, (*policy, error_code) in valid_tuples.items():
            candidate = copy.deepcopy(inventory)
            for existing_row in candidate["occurrences"]:
                existing_policy = valid_tuples[existing_row["classification"]]
                for field, value in zip(fields, existing_policy[:-1], strict=True):
                    existing_row[field] = value
            synthetic_row = next(
                row for row in candidate["occurrences"] if row["classification"] != "C-version-neutral-component"
            )
            synthetic_row["classification"] = classification
            for field, value in zip(fields, policy, strict=True):
                synthetic_row[field] = value
            rows = candidate["occurrences"]
            assert isinstance(rows, list)
            projection = [
                {key: item[key] for key in ("path", "line", "patternId", "lineSha256")}
                for item in rows
            ]
            with self.subTest(classification=classification, valid=True), mock.patch.object(
                migration_inventory,
                "discover_acceptance_reference_occurrences",
                return_value=projection,
            ):
                validate_migration_inventory(ROOT, candidate)

            for field, expected_value in zip(fields, policy, strict=True):
                mutated = copy.deepcopy(candidate)
                changed = next(
                    item
                    for item in mutated["occurrences"]
                    if item["path"] == synthetic_row["path"]
                    and item["line"] == synthetic_row["line"]
                    and item["patternId"] == synthetic_row["patternId"]
                )
                changed[field] = (
                    "wrong-policy" if type(expected_value) is str else not expected_value
                )
                with self.subTest(classification=classification, field=field):
                    validate_semantics(mutated, error_code)

    def test_runtime_date_requires_exact_yyyy_mm_dd(self) -> None:
        """A loosely formatted calendar string must not satisfy the inventory contract."""

        inventory = load_migration_inventory(ROOT)
        inventory["date"] = "2026-8-10"
        with self.assertRaises(AcceptanceAuthorityError) as raised:
            validate_migration_inventory(ROOT, inventory)
        self.assertEqual("migration-consumer-class-invalid", raised.exception.code)

    def test_packet_builder_coupled_current_posture_occurrences_are_both_class_b(self) -> None:
        """The current packet path and acceptance identity must transition together."""

        inventory = load_migration_inventory(ROOT)
        rows = [
            row
            for row in inventory["occurrences"]
            if row["path"] == "scripts/harness_decision_packet.py"
        ]
        self.assertEqual(2, len(rows))
        self.assertEqual(
            {"B-current-authority-consumer"},
            {row["classification"] for row in rows},
        )
