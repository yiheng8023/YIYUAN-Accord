from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_requirements_domain_challenge_protocol import (
    PROTOCOL_PATH,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


class RequirementsDomainChallengeProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))

    def validate(self, document: dict | None = None) -> None:
        validate_protocol(document or self.document, root=ROOT)

    def test_current_protocol_is_valid(self) -> None:
        self.validate()

    def test_rejects_mutable_live_candidate_path(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidatePin"]["path"] = (
            "C:/Users/15521/.cc-switch/skills/grill-with-docs/SKILL.md"
        )
        with self.assertRaisesRegex(RuntimeError, "candidate pin drifted"):
            self.validate(document)

    def test_rejects_live_run_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveExecutionStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "decision overclaimed"):
            self.validate(document)

    def test_rejects_fixture_gate_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionGate"]["privateOracleImplemented"] = False
        with self.assertRaisesRegex(RuntimeError, "implementation gate rolled back"):
            self.validate(document)

    def test_rejects_self_authored_arm_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["selectionDecision"]["selfAuthoredArmEligibleNow"] = True
        with self.assertRaisesRegex(RuntimeError, "selection boundary"):
            self.validate(document)

    def test_rejects_authority_document_mutation(self) -> None:
        document = copy.deepcopy(self.document)
        document["fixtureDesign"]["allowedMutableFiles"].append("CONTEXT.md")
        with self.assertRaisesRegex(RuntimeError, "fixture contract"):
            self.validate(document)

    def test_rejects_requirements_completeness_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesRequirementsCompleteness"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
