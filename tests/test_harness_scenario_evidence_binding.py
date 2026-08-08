import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.harness_decision_packet import DecisionPacketError, load_current_authority_bundle
from scripts.harness_scenario_evidence_binding import (
    BINDING_REGISTRY_PATH,
    load_binding_registry,
    resolve_json_pointer,
    resolve_scenario_evidence_binding,
    validate_binding_registry,
)

ROOT = Path(__file__).resolve().parent.parent


def request_for(scenario_id: str) -> dict[str, object]:
    return {
        "schema": 1,
        "requestId": f"harness.manifest.v1:{scenario_id}",
        "scenarioId": scenario_id,
        "evidenceLane": "mechanism-validation",
        "expectedSemanticAuthorityId": "skill-portfolio-current-authority-v1",
        "observedAvailability": None,
        "taskBinding": None,
        "currentCapabilityGap": None,
        "activationAuthority": None,
    }


class HarnessScenarioEvidenceBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        first = load_current_authority_bundle(ROOT, request_for("GEN-CREATIVE-01"))
        self.coverage = first["coverage"]
        self.registry = load_binding_registry(ROOT)

    def test_registry_matches_exact_current_coverage_order(self) -> None:
        validate_binding_registry(ROOT, self.registry, self.coverage)
        expected = [item["scenarioId"] for item in self.coverage["document"]["scenarioCoverage"]]
        actual = [item["scenarioId"] for item in self.registry["bindings"]]
        self.assertEqual(expected, actual)
        self.assertEqual(11, sum(item["bindingMode"] == "scenario-record" for item in self.registry["bindings"]))
        self.assertEqual(2, sum(item["bindingMode"] == "document-level-support" for item in self.registry["bindings"]))

    def test_all_current_bindings_resolve(self) -> None:
        for row in self.coverage["document"]["scenarioCoverage"]:
            with self.subTest(scenario_id=row["scenarioId"]):
                normalized, sources = resolve_scenario_evidence_binding(ROOT, self.registry, row)
                self.assertEqual(row["scenarioId"], normalized["scenarioId"])
                self.assertEqual(row["evidenceSourcePaths"], [item["path"] for item in sources])

    def test_document_level_bindings_preserve_aggregate_identity(self) -> None:
        for scenario_id in ("SE-ARCH-DESIGN-01", "SE-VERIFY-SECURE-01"):
            row = next(item for item in self.coverage["document"]["scenarioCoverage"] if item["scenarioId"] == scenario_id)
            normalized, _ = resolve_scenario_evidence_binding(ROOT, self.registry, row)
            self.assertEqual("document-level-support", normalized["bindingMode"])
            self.assertFalse(normalized["scenarioIdentityPresentInSource"])
            self.assertEqual("SE-E2E-THIN-01", normalized["sourceScenarioId"])

    def test_source_redirection_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.registry)
        mutated["bindings"][0]["sourcePath"] = "registry/program-acceptance-map.json"
        with self.assertRaises(DecisionPacketError) as raised:
            validate_binding_registry(ROOT, mutated, self.coverage)
        self.assertEqual("binding-source-path-drift", raised.exception.code)

    def test_malformed_pointer_reaches_pointer_syntax_error(self) -> None:
        row = next(
            item
            for item in self.coverage["document"]["scenarioCoverage"]
            if item["scenarioId"] == "GEN-CREATIVE-01"
        )
        mutated = copy.deepcopy(self.registry)
        mutated["bindings"][0]["identityPointers"] = [
            "scenarioBinding/scenarioId"
        ]
        with self.assertRaises(DecisionPacketError) as raised:
            resolve_scenario_evidence_binding(ROOT, mutated, row)
        self.assertEqual("binding-pointer-invalid", raised.exception.code)

    def test_declared_collection_surface_excludes_historical_identity(self) -> None:
        row = next(
            item
            for item in self.coverage["document"]["scenarioCoverage"]
            if item["scenarioId"] == "SE-OPS-INCIDENT-01"
        )
        normalized, _ = resolve_scenario_evidence_binding(ROOT, self.registry, row)
        self.assertEqual(
            [
                "/behaviorallyObservedScenarioCells/2/scenarioId",
                "/behaviorallyObservedScenarioCells/3/scenarioId",
            ],
            [item["pointer"] for item in normalized["resolvedIdentityValues"]],
        )

        mutated = copy.deepcopy(self.registry)
        binding = next(
            item for item in mutated["bindings"] if item["scenarioId"] == "SE-OPS-INCIDENT-01"
        )
        binding["identityPointers"].pop()
        with self.assertRaises(DecisionPacketError) as raised:
            resolve_scenario_evidence_binding(ROOT, mutated, row)
        self.assertEqual("binding-scenario-identity-mismatch", raised.exception.code)

    def test_registry_runtime_validation_matches_schema_scalar_constraints(self) -> None:
        cases = (
            ("schema", True),
            ("status", ""),
            ("status", False),
            ("date", "2026/08/09"),
            ("date", "2026-13-40"),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                mutated = copy.deepcopy(self.registry)
                mutated[field] = value
                with self.assertRaises(DecisionPacketError) as raised:
                    validate_binding_registry(ROOT, mutated, self.coverage)
                self.assertEqual("binding-registry-invalid", raised.exception.code)

    def test_json_pointer_syntax_is_strict_without_changing_valid_resolution(self) -> None:
        document = {"a/b": {"~": "escaped"}, "00": "dictionary key", "items": ["zero"]}
        self.assertEqual("escaped", resolve_json_pointer(document, "/a~1b/~0"))
        self.assertEqual("dictionary key", resolve_json_pointer(document, "/00"))
        self.assertEqual("zero", resolve_json_pointer(document, "/items/0"))

        for pointer, target in (
            ("/a~2b", document),
            ("/a~", document),
            ("/items/00", document),
            ("/items/١", document),
            ("/items/²", document),
        ):
            with self.subTest(pointer=pointer):
                with self.assertRaises(DecisionPacketError) as raised:
                    resolve_json_pointer(target, pointer)
                self.assertEqual("binding-pointer-invalid", raised.exception.code)

    def test_numeric_dictionary_key_stays_an_exact_identity_surface(self) -> None:
        scenario_id = "GEN-NUMERIC-01"
        registry = copy.deepcopy(self.registry)
        binding = registry["bindings"][0]
        binding["scenarioId"] = scenario_id
        binding["sourcePath"] = "registry/numeric-dictionary-key.json"
        binding["identityPointers"] = ["/groups/00/scenarioId"]
        scenario = {
            "scenarioId": scenario_id,
            "evidenceSourcePaths": [binding["sourcePath"]],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source_path = temporary_root / binding["sourcePath"]
            source_path.parent.mkdir(parents=True)
            source_path.write_text(
                json.dumps(
                    {
                        "id": "numeric-dictionary-key-source",
                        "status": "test-only",
                        "groups": {"00": {"scenarioId": scenario_id}},
                    }
                ),
                encoding="utf-8",
            )
            normalized, _ = resolve_scenario_evidence_binding(
                temporary_root, registry, scenario
            )
        self.assertEqual(
            [{"pointer": "/groups/00/scenarioId", "value": scenario_id}],
            normalized["resolvedIdentityValues"],
        )

    def test_unhashable_binding_mode_fails_with_the_stable_mode_error(self) -> None:
        for value in ([], {}):
            with self.subTest(value=value):
                mutated = copy.deepcopy(self.registry)
                mutated["bindings"][0]["bindingMode"] = value
                with self.assertRaises(DecisionPacketError) as raised:
                    validate_binding_registry(ROOT, mutated, self.coverage)
                self.assertEqual("binding-mode-invalid", raised.exception.code)

    def test_oversized_ascii_array_index_is_bounded_in_direct_and_complete_paths(self) -> None:
        oversized_index = "9" * 4301
        with self.assertRaises(DecisionPacketError) as raised:
            resolve_json_pointer({"items": ["zero"]}, f"/items/{oversized_index}")
        self.assertEqual("binding-pointer-unresolved", raised.exception.code)

        scenario_id = "GEN-OVERSIZED-INDEX-01"
        registry = copy.deepcopy(self.registry)
        binding = registry["bindings"][0]
        binding["scenarioId"] = scenario_id
        binding["sourcePath"] = "registry/oversized-index.json"
        binding["identityPointers"] = [
            f"/groups/0/children/{oversized_index}/scenarioId"
        ]
        scenario = {
            "scenarioId": scenario_id,
            "evidenceSourcePaths": [binding["sourcePath"]],
        }
        document = {
            "id": "oversized-index-source",
            "status": "test-only",
            "groups": [
                {"children": {oversized_index: {"scenarioId": scenario_id}}},
                {"children": [{"scenarioId": "GEN-OTHER-01"}]},
            ],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            source_path = temporary_root / binding["sourcePath"]
            source_path.parent.mkdir(parents=True)
            source_path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(DecisionPacketError) as raised:
                resolve_scenario_evidence_binding(temporary_root, registry, scenario)
        self.assertEqual("binding-pointer-unresolved", raised.exception.code)
