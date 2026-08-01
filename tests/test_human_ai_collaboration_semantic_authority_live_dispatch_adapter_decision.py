from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_semantic_authority_live_dispatch_adapter_decision import (
    canonical_sha256,
    validate_decision,
)


ROOT = Path(__file__).resolve().parent.parent
DECISION_PATH = (
    ROOT
    / "registry"
    / "human-ai-collaboration-semantic-authority-live-dispatch-adapter-decision-2026-08-01.json"
)


class SemanticAuthorityLiveDispatchAdapterDecisionTests(unittest.TestCase):
    def test_governed_decision_is_valid_and_keeps_dispatch_denied(self) -> None:
        decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))

        self.assertEqual([], validate_decision(decision))
        self.assertEqual(
            "separate-thin-live-adapter-justified-not-implemented",
            decision["decision"]["outcome"],
        )
        self.assertFalse(decision["authorityBoundary"]["modelDispatchAuthorized"])
        self.assertFalse(decision["implementationState"]["liveAdapterImplemented"])
        self.assertTrue(decision["implementationState"]["offlineAuthorityGateImplemented"])
        self.assertTrue(decision["implementationState"]["simulatedTransportTestsPass"])

    def test_source_snapshot_identity_drift_fails_after_digest_recomputed(self) -> None:
        decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
        decision["sourceSnapshot"]["codexCliVersion"] = "0.999.0"
        body = dict(decision)
        body.pop("decisionSha256")
        decision["decisionSha256"] = canonical_sha256(body)

        self.assertIn(
            "hard-fail-live-adapter-source-snapshot",
            validate_decision(decision),
        )

    def test_stop_and_parent_injection_drift_fail_after_digest_recomputed(self) -> None:
        decision = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
        contract = decision["requiredLiveAdapterContract"]
        contract["stopSequence"] = []
        contract["humanDecisionInjection"]["performedByParent"] = False
        body = dict(decision)
        body.pop("decisionSha256")
        decision["decisionSha256"] = canonical_sha256(body)

        failures = validate_decision(decision)
        self.assertIn("hard-fail-live-adapter-stop-sequence", failures)
        self.assertIn("hard-fail-live-adapter-human-authority", failures)


if __name__ == "__main__":
    unittest.main()
