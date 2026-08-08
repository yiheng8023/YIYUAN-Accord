import copy
import json
from pathlib import Path
import unittest

from scripts.harness_decision_packet import DecisionPacketError, load_current_authority_bundle
from scripts.harness_scenario_evidence_binding import (
    BINDING_REGISTRY_PATH,
    load_binding_registry,
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
