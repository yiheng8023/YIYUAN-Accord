import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import unittest

from scripts.harness_decision_packet import DecisionPacketError, canonical_sha256
from scripts.harness_decision_packet_v2 import (
    build_decision_packet_v2,
    load_v2_bundle,
    serialize_decision_packet_v2,
    validate_decision_packet_v2,
)
from tests.test_harness_scenario_evidence_binding import request_for

ROOT = Path(__file__).resolve().parent.parent
PACKET_V2_FIELDS = {
    "schema",
    "packetId",
    "authorityBinding",
    "request",
    "sourceEvidence",
    "scenarioEvidenceBinding",
    "routeCoverage",
    "fallbackOrder",
    "decisionState",
    "selectedRoute",
    "authorizationGates",
    "claimBoundary",
    "recheckTriggers",
    "projectionBoundary",
    "packetSha256",
}
SCENARIO_EVIDENCE_BINDING_FIELDS = {
    "registry",
    "scenarioId",
    "sourcePath",
    "bindingMode",
    "identityPointers",
    "resolvedIdentityValues",
    "aggregateScenarioPointer",
    "sourceScenarioId",
    "scenarioIdentityPresentInSource",
    "bindingEvidenceCeiling",
}
EXPECTED_PROJECTION_BOUNDARY = {
    "derivedProjectionNotAuthority": True,
    "legacyRoutingIsCurrentAuthority": False,
    "portableCoreDependsOnCcSwitch": False,
    "pluginReleaseEligible": False,
}
EXPECTED_BINDING_MODE_RULES = {
    "scenario-record": {
        "identityPointers": {"minItems": 1},
        "resolvedIdentityValues": {"minItems": 1},
        "aggregateScenarioPointer": {"const": None},
        "scenarioIdentityPresentInSource": {"const": True},
    },
    "document-level-support": {
        "identityPointers": {"maxItems": 0},
        "resolvedIdentityValues": {"maxItems": 0},
        "aggregateScenarioPointer": {"type": "string", "minLength": 1},
        "scenarioIdentityPresentInSource": {"const": False},
    },
}


class HarnessDecisionPacketV2Tests(unittest.TestCase):
    def load_v2_schema(self) -> dict[str, Any]:
        return json.loads(
            (ROOT / "schemas/harness-decision-packet-v2.schema.json").read_text(
                encoding="utf-8"
            )
        )

    def assert_packet_matches_v2_schema_contract(
        self, schema: dict[str, Any], packet: dict[str, Any]
    ) -> None:
        def assert_exact_object(
            object_schema: dict[str, Any], value: dict[str, Any]
        ) -> None:
            self.assertIs(False, object_schema["additionalProperties"])
            self.assertEqual(set(object_schema["required"]), set(value))
            self.assertEqual(set(object_schema["properties"]), set(value))

        properties = schema["properties"]
        assert_exact_object(schema, packet)
        self.assertEqual(properties["schema"]["const"], packet["schema"])
        self.assertEqual(
            properties["selectedRoute"]["const"], packet["selectedRoute"]
        )

        for field in ("authorizationGates", "claimBoundary", "projectionBoundary"):
            object_schema = properties[field]
            value = packet[field]
            assert_exact_object(object_schema, value)
            for name, rule in object_schema["properties"].items():
                self.assertEqual(rule["const"], value[name])

        binding_schema = properties["scenarioEvidenceBinding"]
        binding = packet["scenarioEvidenceBinding"]
        assert_exact_object(binding_schema, binding)
        self.assertIn(
            binding["bindingMode"],
            binding_schema["properties"]["bindingMode"]["enum"],
        )

        matching_branches = [
            branch
            for branch in binding_schema["allOf"]
            if branch["if"]["properties"]["bindingMode"]["const"]
            == binding["bindingMode"]
        ]
        self.assertEqual(1, len(matching_branches))
        for field, rule in matching_branches[0]["then"]["properties"].items():
            value = binding[field]
            if "const" in rule:
                self.assertEqual(rule["const"], value)
            if "minItems" in rule:
                self.assertGreaterEqual(len(value), rule["minItems"])
            if "maxItems" in rule:
                self.assertLessEqual(len(value), rule["maxItems"])
            if rule.get("type") == "string":
                self.assertIsInstance(value, str)
                self.assertGreaterEqual(len(value), rule.get("minLength", 0))

    def test_actual_schema_contract_accepts_generated_binding_modes(self) -> None:
        schema = self.load_v2_schema()
        properties = schema["properties"]
        self.assertIs(False, schema["additionalProperties"])
        self.assertEqual(PACKET_V2_FIELDS, set(schema["required"]))
        self.assertEqual(PACKET_V2_FIELDS, set(properties))

        binding_schema = properties["scenarioEvidenceBinding"]
        self.assertIs(False, binding_schema["additionalProperties"])
        self.assertEqual(
            SCENARIO_EVIDENCE_BINDING_FIELDS, set(binding_schema["required"])
        )
        self.assertEqual(
            SCENARIO_EVIDENCE_BINDING_FIELDS, set(binding_schema["properties"])
        )
        self.assertEqual(2, properties["schema"]["const"])
        self.assertIsNone(properties["selectedRoute"]["const"])
        actual_mode_rules = {
            branch["if"]["properties"]["bindingMode"]["const"]: branch["then"][
                "properties"
            ]
            for branch in binding_schema["allOf"]
        }
        self.assertEqual(EXPECTED_BINDING_MODE_RULES, actual_mode_rules)

        for scenario_id in ("GEN-CREATIVE-01", "SE-ARCH-DESIGN-01"):
            with self.subTest(scenario_id=scenario_id):
                packet = build_decision_packet_v2(ROOT, request_for(scenario_id))
                self.assertEqual(
                    EXPECTED_PROJECTION_BOUNDARY, packet["projectionBoundary"]
                )
                self.assert_packet_matches_v2_schema_contract(schema, packet)

    def test_resealed_identity_promotion_violates_runtime_and_schema_contract(self) -> None:
        schema = self.load_v2_schema()
        packet = build_decision_packet_v2(ROOT, request_for("SE-VERIFY-SECURE-01"))
        mutated = copy.deepcopy(packet)
        mutated["scenarioEvidenceBinding"]["bindingMode"] = "scenario-record"
        mutated["packetSha256"] = canonical_sha256(
            {key: value for key, value in mutated.items() if key != "packetSha256"}
        )

        with self.assertRaises(DecisionPacketError) as runtime_raised:
            validate_decision_packet_v2(ROOT, mutated)
        self.assertEqual(
            "document-level-identity-promotion", runtime_raised.exception.code
        )
        with self.assertRaises(AssertionError):
            self.assert_packet_matches_v2_schema_contract(schema, mutated)

    def test_public_binding_projection_has_exact_shape(self) -> None:
        _, binding = load_v2_bundle(ROOT, request_for("GEN-CREATIVE-01"))
        self.assertEqual(SCENARIO_EVIDENCE_BINDING_FIELDS, set(binding))
        self.assertEqual(
            {
                "path": "registry/harness-scenario-evidence-bindings-v1.json",
                "id": "harness-scenario-evidence-bindings-v1",
            },
            {key: binding["registry"][key] for key in ("path", "id")},
        )
        self.assertEqual(64, len(binding["registry"]["sha256"]))

    def test_scenario_record_packet_is_source_bound(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("GEN-CREATIVE-01"))
        validate_decision_packet_v2(ROOT, packet)
        self.assertEqual(PACKET_V2_FIELDS, set(packet))
        self.assertEqual(2, packet["schema"])
        self.assertEqual("scenario-record", packet["scenarioEvidenceBinding"]["bindingMode"])
        self.assertTrue(packet["scenarioEvidenceBinding"]["scenarioIdentityPresentInSource"])
        self.assertEqual("mechanism-evidence-only", packet["decisionState"])
        self.assertIsNone(packet["selectedRoute"])
        self.assertFalse(any(packet["authorizationGates"].values()))
        self.assertFalse(any(packet["claimBoundary"].values()))

    def test_document_level_packet_keeps_aggregate_ceiling(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("SE-ARCH-DESIGN-01"))
        binding = packet["scenarioEvidenceBinding"]
        self.assertEqual("document-level-support", binding["bindingMode"])
        self.assertFalse(binding["scenarioIdentityPresentInSource"])
        self.assertEqual("SE-E2E-THIN-01", binding["sourceScenarioId"])
        self.assertEqual(
            "document-level-support-no-independent-scenario-identity",
            binding["bindingEvidenceCeiling"],
        )

    def test_binding_promotion_is_rejected_after_resealing(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("SE-VERIFY-SECURE-01"))
        mutated = copy.deepcopy(packet)
        mutated["scenarioEvidenceBinding"]["bindingMode"] = "scenario-record"
        mutated["packetSha256"] = canonical_sha256(
            {key: value for key, value in mutated.items() if key != "packetSha256"}
        )
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_packet_v2(ROOT, mutated)
        self.assertEqual("document-level-identity-promotion", raised.exception.code)

    def test_registry_binding_drift_is_rejected_after_resealing(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("GEN-LEARNING-01"))
        mutated = copy.deepcopy(packet)
        mutated["scenarioEvidenceBinding"]["registry"]["sha256"] = "0" * 64
        mutated["packetSha256"] = canonical_sha256(
            {key: value for key, value in mutated.items() if key != "packetSha256"}
        )
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_packet_v2(ROOT, mutated)
        self.assertEqual("historical-authority-promotion", raised.exception.code)

    def test_packet_digest_mutation_is_rejected(self) -> None:
        packet = build_decision_packet_v2(ROOT, request_for("GEN-LEARNING-01"))
        packet["packetSha256"] = "0" * 64
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_packet_v2(ROOT, packet)
        self.assertEqual("packet-digest-mismatch", raised.exception.code)

    def test_repeated_v2_build_is_byte_identical(self) -> None:
        request = request_for("GEN-LEARNING-01")
        self.assertEqual(
            serialize_decision_packet_v2(build_decision_packet_v2(ROOT, request)),
            serialize_decision_packet_v2(build_decision_packet_v2(ROOT, request)),
        )

    def test_cli_emits_canonical_v2_packet_without_repository_writes(self) -> None:
        before = subprocess.run(
            ["git", "status", "--short"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        with tempfile.TemporaryDirectory() as temporary_directory:
            request_path = Path(temporary_directory) / "request.json"
            request_path.write_text(
                json.dumps(request_for("SE-VERIFY-SECURE-01"), ensure_ascii=False),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "scripts/build_harness_decision_packet_v2.py",
                    str(request_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
        after = subprocess.run(
            ["git", "status", "--short"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stderr)
        self.assertEqual(before, after)
        packet = json.loads(result.stdout)
        self.assertEqual(2, packet["schema"])
        self.assertEqual(result.stdout, serialize_decision_packet_v2(packet))
        self.assertIsNone(packet["selectedRoute"])

    def test_cli_invalid_request_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            request_path = Path(temporary_directory) / "invalid.json"
            request_path.write_text("{", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "scripts/build_harness_decision_packet_v2.py",
                    str(request_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertEqual("request-read-failed", json.loads(result.stderr)["code"])
