import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable
import unittest

from scripts.harness_decision_packet import canonical_sha256
from scripts.harness_decision_packet_manifest import (
    BatchBindingError,
    build_decision_packet_manifest,
    build_canonical_probe_request,
    serialize_decision_packet_manifest,
    validate_decision_packet_manifest,
    write_manifest_atomically,
)

ROOT = Path(__file__).resolve().parent.parent
AUTHORITY_PATHS = (
    "registry/skill-portfolio-current-authority.json",
    "registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json",
    "registry/portfolio-tasktime-projection-contract-2026-08-06.json",
    "registry/program-acceptance-map.json",
    "registry/harness-scenario-evidence-bindings-v1.json",
)
SOURCE_MUTATION_EXPECTATIONS = {
    "test_registry_missing_scenario_is_rejected": "binding-scenario-set-drift",
    "test_registry_extra_scenario_is_rejected": "binding-scenario-set-drift",
    "test_registry_reordering_is_rejected": "binding-scenario-set-drift",
    "test_source_redirection_is_rejected": "binding-source-path-drift",
    "test_malformed_pointer_is_rejected": "binding-pointer-invalid",
    "test_unresolved_pointer_is_rejected": "binding-pointer-unresolved",
    "test_wrong_identity_is_rejected": "binding-scenario-identity-mismatch",
    "test_missing_second_ops_pointer_is_rejected": "binding-scenario-identity-mismatch",
    "test_document_level_mode_promotion_is_rejected": "document-level-identity-promotion",
    "test_aggregate_identity_drift_is_rejected": "binding-aggregate-identity-drift",
    "test_document_level_identity_appearance_is_rejected": "document-level-identity-promotion",
    "test_authority_digest_drift_is_rejected": "authority-source-digest-drift",
    "test_source_digest_drift_is_rejected": "evidence-source-digest-drift",
}


class HarnessDecisionPacketManifestTests(unittest.TestCase):
    def copy_bound_sources(self, temporary_root: Path) -> None:
        coverage = json.loads(
            (ROOT / AUTHORITY_PATHS[1]).read_text(encoding="utf-8")
        )
        source_paths = {
            path
            for scenario in coverage["scenarioCoverage"]
            for path in scenario["evidenceSourcePaths"]
        }
        for relative in (*AUTHORITY_PATHS, *sorted(source_paths)):
            destination = temporary_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

    def rewrite_json(
        self, root: Path, relative: str, mutate: Callable[[dict[str, Any]], None]
    ) -> None:
        path = root / relative
        value = json.loads(path.read_text(encoding="utf-8"))
        mutate(value)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def assert_source_build_issue(
        self,
        mutate: Callable[[Path], None],
        expected_code: str,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            self.copy_bound_sources(temporary_root)
            mutate(temporary_root)
            with self.assertRaises(BatchBindingError) as raised:
                build_decision_packet_manifest(temporary_root)
        self.assertIn(
            expected_code, [item["code"] for item in raised.exception.issues]
        )

    def assert_source_validation_issue(
        self,
        mutate: Callable[[Path], None],
        expected_code: str,
    ) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            self.copy_bound_sources(temporary_root)
            mutate(temporary_root)
            with self.assertRaises(BatchBindingError) as raised:
                validate_decision_packet_manifest(temporary_root, manifest)
        self.assertIn(
            expected_code, [item["code"] for item in raised.exception.issues]
        )

    def assert_manifest_issue(
        self, mutate: Callable[[dict[str, Any]], None], expected_code: str
    ) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        mutated = copy.deepcopy(manifest)
        mutate(mutated)
        mutated["manifestSha256"] = canonical_sha256(
            {key: value for key, value in mutated.items() if key != "manifestSha256"}
        )
        with self.assertRaises(BatchBindingError) as raised:
            validate_decision_packet_manifest(ROOT, mutated)
        self.assertIn(
            expected_code, [item["code"] for item in raised.exception.issues]
        )

    def test_canonical_request_is_zero_model_and_unbound(self) -> None:
        request = build_canonical_probe_request("GEN-CREATIVE-01")
        self.assertEqual("mechanism-validation", request["evidenceLane"])
        self.assertEqual(
            "harness.manifest.v1:GEN-CREATIVE-01", request["requestId"]
        )
        for field in (
            "observedAvailability",
            "taskBinding",
            "currentCapabilityGap",
            "activationAuthority",
        ):
            self.assertIsNone(request[field])

    def test_manifest_contains_all_scenarios_in_current_order(self) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        validate_decision_packet_manifest(ROOT, manifest)
        coverage = json.loads(
            (
                ROOT
                / "registry/human-ai-collaboration-current-candidate-capability-coverage-reconciliation-2026-08-01.json"
            ).read_text(encoding="utf-8")
        )
        expected = [item["scenarioId"] for item in coverage["scenarioCoverage"]]
        self.assertEqual(expected, [item["scenarioId"] for item in manifest["entries"]])
        self.assertEqual(13, manifest["scenarioCount"])
        self.assertEqual(
            11,
            sum(
                item["bindingMode"] == "scenario-record"
                for item in manifest["entries"]
            ),
        )
        self.assertEqual(
            2,
            sum(
                item["bindingMode"] == "document-level-support"
                for item in manifest["entries"]
            ),
        )
        self.assertTrue(manifest["atomic"])
        self.assertTrue(
            all(item["selectedRoute"] is None for item in manifest["entries"])
        )
        self.assertTrue(all(value == 0 for value in manifest["executionCounters"].values()))
        self.assertFalse(any(manifest["authorizationGates"].values()))
        self.assertFalse(any(manifest["claimBoundary"].values()))

    def test_live_schema_contract_accepts_generated_manifest(self) -> None:
        schema = json.loads(
            (
                ROOT / "schemas/harness-decision-packet-manifest-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        manifest = build_decision_packet_manifest(ROOT)
        self.assertIs(False, schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(manifest))
        self.assertEqual(set(schema["properties"]), set(manifest))
        self.assertEqual(1, schema["properties"]["schema"]["const"])
        self.assertEqual(2, schema["properties"]["packetSchema"]["const"])
        self.assertIs(True, schema["properties"]["atomic"]["const"])
        self.assertEqual(13, schema["properties"]["scenarioCount"]["const"])
        entry_schema = schema["$defs"]["manifestEntry"]
        self.assertIs(False, entry_schema["additionalProperties"])
        self.assertEqual(set(entry_schema["required"]), set(manifest["entries"][0]))
        self.assertEqual(set(entry_schema["properties"]), set(manifest["entries"][0]))
        self.assertIsNone(entry_schema["properties"]["selectedRoute"]["const"])

        for field in (
            "executionCounters",
            "authorizationGates",
            "claimBoundary",
            "projectionBoundary",
        ):
            field_schema = schema["properties"][field]
            self.assertIs(False, field_schema["additionalProperties"])
            self.assertEqual(set(field_schema["required"]), set(manifest[field]))
            self.assertEqual(set(field_schema["properties"]), set(manifest[field]))
            for name, rule in field_schema["properties"].items():
                self.assertEqual(rule["const"], manifest[field][name])

    def test_repeated_manifest_is_byte_identical(self) -> None:
        first = serialize_decision_packet_manifest(
            build_decision_packet_manifest(ROOT)
        )
        second = serialize_decision_packet_manifest(
            build_decision_packet_manifest(ROOT)
        )
        self.assertEqual(first, second)

    def test_manifest_entry_removal_is_rejected(self) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        mutated = copy.deepcopy(manifest)
        mutated["entries"].pop()
        mutated["manifestSha256"] = canonical_sha256(
            {key: value for key, value in mutated.items() if key != "manifestSha256"}
        )
        with self.assertRaises(BatchBindingError) as raised:
            validate_decision_packet_manifest(ROOT, mutated)
        self.assertEqual("batch-binding-failed", raised.exception.code)

    def test_manifest_entry_duplication_is_rejected(self) -> None:
        self.assert_manifest_issue(
            lambda value: value["entries"].insert(
                1, copy.deepcopy(value["entries"][0])
            ),
            "manifest-entry-set-drift",
        )

    def test_manifest_entry_reordering_is_rejected(self) -> None:
        def swap(value: dict[str, Any]) -> None:
            value["entries"][0], value["entries"][1] = (
                value["entries"][1],
                value["entries"][0],
            )

        self.assert_manifest_issue(swap, "manifest-entry-order-drift")

    def test_manifest_digest_drift_is_rejected(self) -> None:
        manifest = build_decision_packet_manifest(ROOT)
        manifest["manifestSha256"] = "0" * 64
        with self.assertRaises(BatchBindingError) as raised:
            validate_decision_packet_manifest(ROOT, manifest)
        self.assertIn(
            "manifest-digest-mismatch",
            [item["code"] for item in raised.exception.issues],
        )

    def test_registry_missing_scenario_is_rejected(self) -> None:
        def mutate(root: Path) -> None:
            self.rewrite_json(
                root,
                AUTHORITY_PATHS[4],
                lambda value: value["bindings"].pop(),
            )

        self.assert_source_build_issue(
            mutate, SOURCE_MUTATION_EXPECTATIONS[self._testMethodName]
        )

    def test_registry_extra_scenario_is_rejected(self) -> None:
        def add_extra(value: dict[str, Any]) -> None:
            extra = copy.deepcopy(value["bindings"][-1])
            extra["scenarioId"] = "SE-EXTRA-01"
            value["bindings"].append(extra)

        self.assert_source_build_issue(
            lambda root: self.rewrite_json(root, AUTHORITY_PATHS[4], add_extra),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_registry_reordering_is_rejected(self) -> None:
        def reorder(value: dict[str, Any]) -> None:
            value["bindings"][0], value["bindings"][1] = (
                value["bindings"][1],
                value["bindings"][0],
            )

        self.assert_source_build_issue(
            lambda root: self.rewrite_json(root, AUTHORITY_PATHS[4], reorder),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_source_redirection_is_rejected(self) -> None:
        self.assert_source_build_issue(
            lambda root: self.rewrite_json(
                root,
                AUTHORITY_PATHS[4],
                lambda value: value["bindings"][0].__setitem__(
                    "sourcePath", AUTHORITY_PATHS[3]
                ),
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_malformed_pointer_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            self.copy_bound_sources(temporary_root)
            self.rewrite_json(
                temporary_root,
                AUTHORITY_PATHS[4],
                lambda value: value["bindings"][0].__setitem__(
                    "identityPointers", ["scenarioBinding/scenarioId"]
                ),
            )
            with self.assertRaises(BatchBindingError) as raised:
                build_decision_packet_manifest(temporary_root)
        self.assertEqual(1, len(raised.exception.issues))
        self.assertEqual(
            "GEN-CREATIVE-01", raised.exception.issues[0]["scenarioId"]
        )
        self.assertEqual(
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
            raised.exception.issues[0]["code"],
        )
        self.assertEqual(
            {"scenarioId", "code", "message", "path"},
            set(raised.exception.issues[0]),
        )
        self.assertEqual(
            "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json",
            raised.exception.issues[0]["path"],
        )

    def test_unresolved_pointer_is_rejected(self) -> None:
        self.assert_source_build_issue(
            lambda root: self.rewrite_json(
                root,
                AUTHORITY_PATHS[4],
                lambda value: value["bindings"][0].__setitem__(
                    "identityPointers", ["/missing/scenarioId"]
                ),
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_wrong_identity_is_rejected(self) -> None:
        relative = "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json"
        self.assert_source_build_issue(
            lambda root: self.rewrite_json(
                root,
                relative,
                lambda value: value["scenarioBinding"].__setitem__(
                    "scenarioId", "GEN-WRONG-01"
                ),
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_missing_second_ops_pointer_is_rejected(self) -> None:
        def remove_pointer(value: dict[str, Any]) -> None:
            binding = next(
                item
                for item in value["bindings"]
                if item["scenarioId"] == "SE-OPS-INCIDENT-01"
            )
            binding["identityPointers"].pop()

        self.assert_source_build_issue(
            lambda root: self.rewrite_json(
                root, AUTHORITY_PATHS[4], remove_pointer
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_document_level_mode_promotion_is_rejected(self) -> None:
        def promote(value: dict[str, Any]) -> None:
            binding = next(
                item
                for item in value["bindings"]
                if item["scenarioId"] == "SE-ARCH-DESIGN-01"
            )
            binding["bindingMode"] = "scenario-record"

        self.assert_source_build_issue(
            lambda root: self.rewrite_json(root, AUTHORITY_PATHS[4], promote),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_aggregate_identity_drift_is_rejected(self) -> None:
        relative = "registry/human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-evidence-2026-07-27.json"
        self.assert_source_build_issue(
            lambda root: self.rewrite_json(
                root,
                relative,
                lambda value: value.__setitem__("scenarioId", "SE-E2E-OTHER-01"),
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_document_level_identity_appearance_is_rejected(self) -> None:
        relative = "registry/human-ai-collaboration-software-lifecycle-thin-slice-zero-model-calibration-evidence-2026-07-27.json"
        self.assert_source_build_issue(
            lambda root: self.rewrite_json(
                root,
                relative,
                lambda value: value.__setitem__(
                    "scenarios", [{"id": "SE-ARCH-DESIGN-01"}]
                ),
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_authority_digest_drift_is_rejected(self) -> None:
        self.assert_source_validation_issue(
            lambda root: (root / AUTHORITY_PATHS[1]).write_bytes(
                (root / AUTHORITY_PATHS[1]).read_bytes() + b"\n"
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_source_digest_drift_is_rejected(self) -> None:
        relative = "registry/human-ai-collaboration-creative-capability-baseline-2026-07-31.json"
        self.assert_source_validation_issue(
            lambda root: (root / relative).write_bytes(
                (root / relative).read_bytes() + b"\n"
            ),
            SOURCE_MUTATION_EXPECTATIONS[self._testMethodName],
        )

    def test_failed_cli_leaves_existing_output_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "manifest.json"
            output.write_bytes(b"known-good\n")
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "scripts/build_harness_decision_packet_manifest.py",
                    "--root",
                    str(Path(temporary_directory) / "missing-root"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual(b"known-good\n", output.read_bytes())
            self.assertEqual(b"", result.stdout)
            self.assertEqual([], list(output.parent.glob(f".{output.name}.*.tmp")))
            error = json.loads(result.stderr)
            self.assertEqual("batch-binding-failed", error["code"])

    def test_successful_cli_writes_exact_canonical_bytes_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "manifest.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "scripts/build_harness_decision_packet_manifest.py",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
            self.assertEqual(0, result.returncode)
            self.assertEqual(b"", result.stdout)
            self.assertEqual(b"", result.stderr)
            self.assertEqual(
                serialize_decision_packet_manifest(
                    build_decision_packet_manifest(ROOT)
                ),
                output.read_bytes(),
            )
            self.assertEqual([], list(output.parent.glob(f".{output.name}.*.tmp")))

    def test_atomic_helper_cleans_temporary_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "manifest.json"
            output.mkdir()
            with self.assertRaises(OSError):
                write_manifest_atomically(output, b"replacement\n")
            self.assertTrue(output.is_dir())
            self.assertEqual([], list(output.parent.glob(f".{output.name}.*.tmp")))

    def test_stdout_cli_is_canonical_and_does_not_write_repository(self) -> None:
        before = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        result = subprocess.run(
            [sys.executable, "-B", "scripts/build_harness_decision_packet_manifest.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        after = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stderr)
        self.assertEqual(before, after)
        manifest = json.loads(result.stdout)
        self.assertEqual(result.stdout, serialize_decision_packet_manifest(manifest))
