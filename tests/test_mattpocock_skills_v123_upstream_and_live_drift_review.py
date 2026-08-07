from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_mattpocock_skills_v123_upstream_and_live_drift_review import (
    ACCEPTANCE_PATH,
    EVIDENCE_ID,
    RECORD_PATH,
    RELEASE_CHANGED_SKILLS,
    validate_record,
    validate_repository_review,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MattPocockSkillsV123UpstreamAndLiveDriftReviewTests(unittest.TestCase):
    def test_repository_review_is_valid(self) -> None:
        review = validate_repository_review(ROOT)
        self.assertEqual(
            "exact-release-reviewed-live-payloads-match-release-mutable-main-metadata-drift-held",
            review["status"],
        )

    def test_changed_payload_set_and_live_release_identity_are_exact(self) -> None:
        review = load(RECORD_PATH)
        self.assertEqual(RELEASE_CHANGED_SKILLS, set(review["releaseDelta"]["changedPromotedSkills"]))
        self.assertEqual(20, review["liveObservation"]["bothV122AndV123PayloadCount"])
        self.assertEqual(5, review["liveObservation"]["v123OnlyPayloadCount"])
        self.assertTrue(review["liveObservation"]["allTwentyFivePayloadsMatchV123"])
        self.assertEqual("main", review["liveObservation"]["databaseRepoBranch"])

    def test_blind_refresh_or_behavior_promotion_fails_closed(self) -> None:
        review = load(RECORD_PATH)
        review["decision"]["blindRefreshAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_record(review, acceptance=load(ACCEPTANCE_PATH), root=ROOT)

        review = load(RECORD_PATH)
        review["claimBoundary"]["behaviorProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_record(review, acceptance=load(ACCEPTANCE_PATH), root=ROOT)

    def test_acceptance_registration_is_required(self) -> None:
        acceptance = copy.deepcopy(load(ACCEPTANCE_PATH))
        acceptance["evidence"] = [
            item for item in acceptance["evidence"] if item.get("id") != EVIDENCE_ID
        ]
        with self.assertRaisesRegex(RuntimeError, "acceptance evidence"):
            validate_record(load(RECORD_PATH), acceptance=acceptance, root=ROOT)


if __name__ == "__main__":
    unittest.main()
