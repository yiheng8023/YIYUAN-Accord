from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.evaluate_human_ai_collaboration_comparative_protocol import (
    FIXTURE_PATH,
    PROTOCOL_PATH,
    evaluate_fixture_document,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class HumanAiCollaborationComparativeProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = load(PROTOCOL_PATH)
        self.fixture = load(FIXTURE_PATH)

    def validate(self, protocol: dict | None = None) -> None:
        validate_protocol(protocol or self.protocol, self.fixture, root=ROOT)

    def test_current_protocol_is_valid(self) -> None:
        self.validate()

    def test_all_fixture_cases_match_expected_status(self) -> None:
        results = evaluate_fixture_document(self.fixture, self.protocol)
        self.assertEqual(
            [],
            [
                item
                for item in results
                if item["expectedStatus"] != item["actualStatus"]
            ],
        )

    def test_rejects_candidate_specific_exposure_overclaim(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["exposureBinding"]["candidateSpecificSelectedExposureProved"] = True
        with self.assertRaisesRegex(RuntimeError, "candidateSpecificSelectedExposureProved"):
            self.validate(protocol)

    def test_rejects_live_execution_rollback(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["decision"]["liveComparativeExecutionStarted"] = False
        with self.assertRaisesRegex(RuntimeError, "live-pair decision"):
            self.validate(protocol)

    def test_rejects_self_authored_change_justification(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["decision"]["selfAuthoredChangeJustified"] = True
        with self.assertRaisesRegex(RuntimeError, "selfAuthoredChangeJustified"):
            self.validate(protocol)

    def test_rejects_matt_tdd_claim_conflation(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        software = next(
            item
            for item in protocol["protocols"]
            if item["id"] == "PROTOCOL-SE-IMPLEMENT-REVIEW-01"
        )
        matt = next(
            item
            for item in software["arms"]
            if item["id"] == "SE-MATT-DISCIPLINED-CODING"
        )
        matt["requiresRedGreen"] = True
        with self.assertRaisesRegex(RuntimeError, "Matt arm"):
            self.validate(protocol)

    def test_rejects_grill_with_docs_forced_into_primary_arm(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        decision = next(
            item
            for item in protocol["suitabilityDecisions"]
            if item["candidateId"] == "cc.grill-with-docs"
        )
        decision["decision"] = "eligible-primary-single-skill-arm"
        with self.assertRaisesRegex(RuntimeError, "near-match exclusion"):
            self.validate(protocol)

    def test_rejects_superiority_without_human_control(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["executionGate"][
            "comparativeSuperiorityClaimAllowedWithoutHumanControl"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "superiority"):
            self.validate(protocol)

    def test_rejects_global_config_authority(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["authorityBoundary"]["globalConfigMutationAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "globalConfigMutationAuthorized"):
            self.validate(protocol)


if __name__ == "__main__":
    unittest.main()
