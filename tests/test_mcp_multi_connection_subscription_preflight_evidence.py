from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.validate_mcp_multi_connection_subscription_preflight_evidence import (
    EVIDENCE_PATH,
    validate_document,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


class MultiConnectionSubscriptionPreflightEvidenceTests(unittest.TestCase):
    def test_current_evidence_validates(self) -> None:
        summary = validate_evidence(ROOT, ROOT / EVIDENCE_PATH)
        self.assertEqual(summary["status"], "validated")
        self.assertEqual(summary["formalRuns"], 3)
        self.assertFalse(summary["overlappingSubscriptionObserved"])
        self.assertFalse(summary["finalReleaseTrialShouldProceed"])

    def test_aggregate_promotion_is_rejected(self) -> None:
        document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
        changed = deepcopy(document)
        changed["aggregateObservation"]["overlappingSubscriptionObservedCount"] = 3
        with self.assertRaisesRegex(RuntimeError, "Aggregate observation drifted"):
            validate_document(ROOT, changed)

    def test_claim_promotion_is_rejected(self) -> None:
        document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
        changed = deepcopy(document)
        changed["claimBoundary"]["leaseOrReferenceCountCorrectnessProved"] = True
        with self.assertRaisesRegex(RuntimeError, "Claim boundary"):
            validate_document(ROOT, changed)


if __name__ == "__main__":
    unittest.main()
