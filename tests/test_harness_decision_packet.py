import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.harness_decision_packet import (
    DecisionPacketError,
    canonical_sha256,
    load_authority_bundle,
    validate_decision_request,
    validate_authority_bundle,
    validate_bound_source_digests,
)

ROOT = Path(__file__).resolve().parent.parent
REQUEST_PATH = Path("tests/fixtures/harness-decision-request-gen-research-01.json")


class HarnessDecisionPacketContractTests(unittest.TestCase):
    def load_request(self) -> dict[str, object]:
        return json.loads((ROOT / REQUEST_PATH).read_text(encoding="utf-8"))

    def test_portfolio_request_is_valid_and_canonical(self) -> None:
        request = self.load_request()
        validate_decision_request(request)
        self.assertEqual(64, len(canonical_sha256(request)))

    def test_boolean_activation_authority_is_rejected(self) -> None:
        request = self.load_request()
        request["activationAuthority"] = True
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-activation-authority", raised.exception.code)

    def test_unknown_request_field_is_rejected(self) -> None:
        request = self.load_request()
        request["selectedSkill"] = "skill.curated.grill-with-docs"
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-request-shape", raised.exception.code)

    def test_task_time_request_accepts_complete_evidence_objects(self) -> None:
        request = self.load_request()
        request["evidenceLane"] = "task-time"
        request["observedAvailability"] = {
            "asOf": "2026-08-08T00:00:00Z",
            "host": "codex-desktop",
            "availableRouteClasses": ["N", "C", "H"],
            "evidencePaths": ["tests/fixtures/live-availability.json"],
        }
        request["taskBinding"] = {
            "taskId": "task.example",
            "goal": "Produce a source-bound decision packet.",
            "target": "GEN-RESEARCH-01",
            "verificationSurface": "focused unittest",
        }
        request["currentCapabilityGap"] = {
            "requiredCapability": "source-bound route evaluation",
            "observedLimitation": "no validated route decision exists",
            "evidencePaths": ["tests/fixtures/gap-evidence.json"],
        }
        request["activationAuthority"] = {
            "evidencePath": "tests/fixtures/authority.json",
            "scope": "evaluate-only",
        }

        validate_decision_request(request)

    def test_missing_request_field_is_rejected(self) -> None:
        request = self.load_request()
        del request["currentCapabilityGap"]
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-request-shape", raised.exception.code)

    def test_invalid_nullable_evidence_objects_are_rejected(self) -> None:
        invalid_cases = (
            ("observedAvailability", {}, "invalid-observed-availability"),
            ("taskBinding", {}, "invalid-task-binding"),
            ("currentCapabilityGap", {}, "invalid-capability-gap"),
            ("activationAuthority", {}, "invalid-activation-authority"),
        )
        for field, value, expected_code in invalid_cases:
            with self.subTest(field=field):
                request = self.load_request()
                request[field] = value
                with self.assertRaises(DecisionPacketError) as raised:
                    validate_decision_request(request)
                self.assertEqual(expected_code, raised.exception.code)


class HarnessDecisionPacketAuthorityTests(HarnessDecisionPacketContractTests):
    def test_current_gen_research_authority_reopens_original_evidence(self) -> None:
        request = self.load_request()
        bundle = load_authority_bundle(ROOT, request)
        validate_authority_bundle(bundle, request)
        self.assertEqual("GEN-RESEARCH-01", bundle["scenario"]["scenarioId"])
        self.assertEqual(
            [
                "registry/human-ai-collaboration-scenario-evidence-matrix-"
                "batch-01-2026-07-24.json"
            ],
            [item["path"] for item in bundle["sourceEvidence"]],
        )
        self.assertFalse(
            bundle["semanticAuthority"]["document"]["legacyAdaptedRelease"]
            ["routingProjectionCurrentAuthority"]
        )

    def test_unknown_scenario_fails_closed(self) -> None:
        request = self.load_request()
        request["scenarioId"] = "GEN-UNKNOWN-01"
        with self.assertRaises(DecisionPacketError) as raised:
            load_authority_bundle(ROOT, request)
        self.assertEqual("unknown-scenario", raised.exception.code)

    def test_expected_authority_id_must_match(self) -> None:
        request = self.load_request()
        request["expectedSemanticAuthorityId"] = "stale-authority"
        with self.assertRaises(DecisionPacketError) as raised:
            load_authority_bundle(ROOT, request)
        self.assertEqual("semantic-authority-id-mismatch", raised.exception.code)

    def test_bound_original_evidence_digest_drift_is_rejected(self) -> None:
        request = self.load_request()
        bundle = load_authority_bundle(ROOT, request)
        records = [
            bundle["semanticAuthority"],
            bundle["coverage"],
            bundle["scheduler"],
            bundle["acceptance"],
            *bundle["sourceEvidence"],
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            for record in records:
                source = ROOT / record["path"]
                destination = temporary_root / record["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            evidence_path = temporary_root / bundle["sourceEvidence"][0]["path"]
            evidence_path.write_bytes(evidence_path.read_bytes() + b"\n")

            with self.assertRaises(DecisionPacketError) as raised:
                validate_bound_source_digests(temporary_root, bundle)
            self.assertEqual("evidence-source-digest-drift", raised.exception.code)

    def test_invalid_scalar_fields_are_rejected(self) -> None:
        invalid_cases = (
            ("schema", 2, "invalid-request-schema"),
            ("requestId", "", "invalid-request-id"),
            ("scenarioId", "lowercase", "invalid-scenario-id"),
            ("evidenceLane", "production", "invalid-evidence-lane"),
            ("expectedSemanticAuthorityId", "", "invalid-authority-id"),
        )
        for field, value, expected_code in invalid_cases:
            with self.subTest(field=field):
                request = self.load_request()
                request[field] = value
                with self.assertRaises(DecisionPacketError) as raised:
                    validate_decision_request(request)
                self.assertEqual(expected_code, raised.exception.code)
