from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_deprecation_and_migration_local_adaptation_review import (
    REVIEW_PATH,
    validate_review,
)


ROOT = Path(__file__).resolve().parent.parent


class DeprecationMigrationLocalAdaptationReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / REVIEW_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_review(document or self.document, root=ROOT)

    def test_current_review_is_valid(self) -> None:
        self.validate()

    def test_rejects_upstream_equivalence_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["localPin"]["equalsPinnedUpstream"] = True
        with self.assertRaisesRegex(RuntimeError, "local pin"):
            self.validate(document)

    def test_rejects_signature_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["upstreamPin"]["commitSignatureVerified"] = True
        with self.assertRaisesRegex(RuntimeError, "signature boundary"):
            self.validate(document)

    def test_rejects_live_eligibility_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["disposition"]["eligibleForLiveWeakAgentRunNow"] = True
        with self.assertRaisesRegex(RuntimeError, "gate disposition"):
            self.validate(document)

    def test_rejects_behavioral_value_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesBehavioralValue"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            self.validate(document)

    def test_rejects_vendoring_authority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["licenseAndProvenanceReview"][
            "vendoringIntoThisRepositoryAuthorized"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "provenance or authority"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
