import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import scripts.validate_harness_decision_packet_manifest_poc as manifest_poc

from scripts.validate_harness_decision_packet_manifest_poc import (
    EXPECTED_MANIFEST_PATH,
    MUTATION_CASE_IDS,
    run_failure_matrix,
    validate_repository_record,
)

ROOT = Path(__file__).resolve().parent.parent


class HarnessDecisionPacketManifestPocTests(unittest.TestCase):
    def current_isolated_record(self) -> dict[str, object]:
        record = json.loads((ROOT / manifest_poc.EVIDENCE_PATH).read_bytes())
        for key in ("design", "plan", "documentation", "manifestFixture"):
            binding = record[key]
            binding["sha256"] = hashlib.sha256(
                (ROOT / binding["path"]).read_bytes()
            ).hexdigest()
        for collection in ("schemas", "scripts"):
            for binding in record[collection]:
                binding["sha256"] = hashlib.sha256(
                    (ROOT / binding["path"]).read_bytes()
                ).hexdigest()
        return record

    def assert_isolated_record_mutation_rejected(
        self,
        path: tuple[str, ...],
        replacement: object,
        message: str,
    ) -> None:
        record = self.current_isolated_record()
        expected_matrix = copy.deepcopy(record["mutationResults"])
        target = record
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        original_load = manifest_poc._load_object

        def load_with_isolated_record(
            root: Path,
            relative: Path,
        ) -> dict[str, object]:
            if relative == manifest_poc.EVIDENCE_PATH:
                return copy.deepcopy(record)
            return original_load(root, relative)

        with patch.object(
            manifest_poc,
            "_load_object",
            side_effect=load_with_isolated_record,
        ), patch.object(
            manifest_poc,
            "run_failure_matrix",
            return_value=expected_matrix,
        ):
            with self.assertRaisesRegex(RuntimeError, message):
                validate_repository_record(ROOT)

    def test_direct_validator_cli_replays_repository_record(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "scripts/validate_harness_decision_packet_manifest_poc.py",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(
            "17 fail-closed mutations",
            result.stdout,
        )

    def test_all_manifest_mutations_fail_closed(self) -> None:
        with patch.object(
            manifest_poc.subprocess,
            "run",
            wraps=subprocess.run,
        ) as run_subprocess:
            results = run_failure_matrix(ROOT)

        self.assertEqual(MUTATION_CASE_IDS, [item["caseId"] for item in results])
        self.assertTrue(all(item["status"] == "rejected" for item in results))
        cli_calls = [
            call
            for call in run_subprocess.call_args_list
            if "build_harness_decision_packet_manifest.py"
            in str(call.args[0][2])
        ]
        self.assertEqual(1, len(cli_calls))
        command = cli_calls[0].args[0]
        self.assertEqual(sys.executable, command[0])
        self.assertEqual("-B", command[1])
        self.assertIn("--root", command)
        self.assertIn("--output", command)
        failing_root = Path(command[command.index("--root") + 1])
        output = Path(command[command.index("--output") + 1])
        self.assertEqual("missing-root", failing_root.name)
        self.assertEqual("manifest.json", output.name)
        self.assertEqual(failing_root.parent, output.parent)
        self.assertFalse(cli_calls[0].kwargs["check"])
        self.assertTrue(cli_calls[0].kwargs["capture_output"])

    def test_repository_record_replays_canonical_manifest(self) -> None:
        record = validate_repository_record(ROOT)
        self.assertEqual(
            "verified-zero-model-thirteen-scenario-binding-and-atomic-manifest-mechanism-only",
            record["status"],
        )
        self.assertTrue((ROOT / EXPECTED_MANIFEST_PATH).is_file())

    def test_repository_record_rejects_json_type_aliases(self) -> None:
        identity_error = "Manifest PoC evidence identity or scenario boundary drifted"
        projection_error = "Manifest PoC manifest or authority projection drifted"
        claim_error = "Manifest PoC claim or lifecycle authority was promoted"
        acceptance_error = "Manifest PoC acceptance boundary or 46/15/0 inventory drifted"
        frozen_error = (
            "Frozen acceptance-map, packet-v1 fixture, or non-registration boundary drifted"
        )
        cases = (
            ("schema-bool", ("schema",), True, identity_error),
            ("schema-float", ("schema",), 1.0, identity_error),
            ("scenario-count-float", ("scenarioCount",), 13.0, identity_error),
            (
                "binding-count-float",
                ("bindingCounts", "scenarioRecord"),
                11.0,
                identity_error,
            ),
            (
                "counter-bool",
                ("executionCounters", "modelRequestCount"),
                False,
                projection_error,
            ),
            (
                "counter-float",
                ("executionCounters", "pluginExecutionCount"),
                0.0,
                projection_error,
            ),
            (
                "claim-number",
                ("claimBoundary", "behaviorProved"),
                0,
                claim_error,
            ),
            (
                "authority-number",
                ("authorityBoundary", "releaseAuthorized"),
                0,
                claim_error,
            ),
            (
                "inventory-bool",
                ("acceptanceInventory", "planned"),
                False,
                acceptance_error,
            ),
            (
                "inventory-float",
                ("acceptanceInventory", "verified"),
                46.0,
                acceptance_error,
            ),
            (
                "registration-number",
                ("acceptanceRegistration", "futureMigrationAuthorized"),
                0,
                frozen_error,
            ),
        )
        for name, path, replacement, message in cases:
            with self.subTest(name=name):
                self.assert_isolated_record_mutation_rejected(
                    path,
                    replacement,
                    message,
                )

    def test_acceptance_remains_frozen_and_evidence_is_not_registered(self) -> None:
        acceptance_bytes = (
            ROOT / "registry/program-acceptance-map.json"
        ).read_bytes()
        acceptance = json.loads(
            acceptance_bytes
        )
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.decision-ready-consumer-projection"
        )
        self.assertEqual("partial", criterion["assessment"])
        self.assertNotIn(
            "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09",
            criterion["evidenceIds"],
        )
        self.assertFalse(
            any(
                item["id"]
                == "evidence.harness-decision-packet-thirteen-scenario-manifest-poc-2026-08-09"
                for item in acceptance["evidence"]
            )
        )
        self.assertEqual(
            "c9d0fb437fb3eae93ffd144a2e3ee418dca90d96e5a266b61d7c7ec3efa6079f",
            hashlib.sha256(acceptance_bytes).hexdigest(),
        )
        self.assertEqual(
            "58410f9576fbbc2f006135d97184d29a9996b1eb11abeaf07988a3a5acf4fc22",
            hashlib.sha256(
                (
                    ROOT
                    / "tests/fixtures/harness-decision-packet-gen-research-01.json"
                ).read_bytes()
            ).hexdigest(),
        )
        counts = {
            state: sum(
                item["assessment"] == state
                for item in acceptance["acceptanceCriteria"]
            )
            for state in ("verified", "partial", "planned")
        }
        self.assertEqual(
            {"verified": 46, "partial": 15, "planned": 0}, counts
        )


if __name__ == "__main__":
    unittest.main()
