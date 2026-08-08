import json
from pathlib import Path
import unittest

from scripts.harness_decision_packet import (
    DecisionPacketError,
    canonical_sha256,
    validate_decision_request,
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
