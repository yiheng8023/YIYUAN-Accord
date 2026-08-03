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

    def test_bridge_repository_text_hash_is_required(self) -> None:
        document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
        changed = deepcopy(document)
        changed["hostBinding"]["bridgeScript"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "bridgeScript binding drifted"):
            validate_document(ROOT, changed)

    def test_missing_repository_relative_schema_is_rejected(self) -> None:
        document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
        changed = deepcopy(document)
        changed["hostBinding"]["stableSchemaEvidence"][0]["path"] = (
            "registry/missing-schema.json"
        )
        with self.assertRaisesRegex(RuntimeError, "schema binding 1 is missing"):
            validate_document(ROOT, changed)

    def test_historical_external_schema_requires_a_digest(self) -> None:
        document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
        changed = deepcopy(document)
        changed["hostBinding"]["stableSchemaEvidence"][0]["sha256"] = "invalid"
        with self.assertRaisesRegex(RuntimeError, "schema binding 1 hash is invalid"):
            validate_document(ROOT, changed)


if __name__ == "__main__":
    unittest.main()
