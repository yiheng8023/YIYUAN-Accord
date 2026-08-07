from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_loss_longhorizon_harness_exact_source_static_review import (
    ACCEPTANCE_PATH,
    EXPECTED_FINDING_IDS,
    EXPECTED_OBJECTS,
    PATH_HASH,
    RECORD_PATH,
    REVISION,
    TREE_OID,
    validate_record,
    validate_repository_review,
)


ROOT = Path(__file__).resolve().parent.parent


def load_record() -> dict:
    return json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))


def load_acceptance() -> dict:
    return json.loads((ROOT / ACCEPTANCE_PATH).read_text(encoding="utf-8"))


class LongHorizonExactSourceStaticReviewTests(unittest.TestCase):
    def test_repository_review_is_valid(self) -> None:
        self.assertEqual(
            "exact-source-acquired-static-review-complete-temp-recycled-no-execution",
            validate_repository_review(ROOT)["status"],
        )

    def test_exact_checkout_and_objects_are_frozen(self) -> None:
        record = load_record()
        acquisition = record["sourceAcquisition"]
        objects = {
            item["path"]: (item["oid"], item["size"])
            for item in record["sourceSnapshot"]["selectedGitObjects"]
        }
        self.assertEqual(REVISION, acquisition["revision"])
        self.assertEqual(TREE_OID, acquisition["treeOid"])
        self.assertEqual(PATH_HASH, acquisition["normalizedPathSha256"])
        self.assertEqual(EXPECTED_OBJECTS, objects)
        self.assertTrue(acquisition["checkout"]["clean"])

    def test_fetch_recovery_is_not_candidate_resume_evidence(self) -> None:
        fetch = load_record()["sourceAcquisition"]["fetch"]
        self.assertTrue(fetch["fullFsckPassedBeforeCheckout"])
        self.assertTrue(fetch["detachedCheckoutRecoveredFromVerifiedObject"])
        self.assertFalse(fetch["candidateCrashRecoveryEvidence"])

    def test_cleanup_is_exact_and_recoverable(self) -> None:
        cleanup = load_record()["sourceAcquisition"]["cleanup"]
        self.assertFalse(cleanup["originalPathExistsAfterCleanup"])
        self.assertTrue(cleanup["recycleBinEntryMatchedNameAndDeletedFromOsTemp"])
        self.assertTrue(cleanup["recoverableByUserFromRecycleBin"])
        self.assertFalse(cleanup["otherPathsRemoved"])

    def test_all_refined_blockers_are_retained(self) -> None:
        record = load_record()
        self.assertEqual(EXPECTED_FINDING_IDS, {item["id"] for item in record["staticFindings"]})
        self.assertEqual("blocked", record["decision"]["directAdoption"])
        self.assertTrue(record["decision"]["stopEquivalentCoordinatorAuthoring"])

    def test_revision_mutation_fails_closed(self) -> None:
        record = load_record()
        record["sourceAcquisition"]["revision"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "acquisition identity"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_cleanup_promotion_fails_closed(self) -> None:
        record = load_record()
        record["sourceAcquisition"]["cleanup"]["recycleBinEntryMatchedNameAndDeletedFromOsTemp"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup receipt"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_static_blocker_removal_fails_closed(self) -> None:
        record = load_record()
        record["staticFindings"].pop()
        with self.assertRaisesRegex(RuntimeError, "static findings"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_execution_authority_promotion_fails_closed(self) -> None:
        record = load_record()
        record["authorityBoundary"]["executeAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_behavior_claim_promotion_fails_closed(self) -> None:
        record = load_record()
        record["claimBoundary"]["provesRuntimeBehavior"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_acceptance_promotion_fails_closed(self) -> None:
        record = load_record()
        acceptance = copy.deepcopy(load_acceptance())
        acceptance["acceptanceCriteria"][0]["assessment"] = "partial"
        with self.assertRaisesRegex(RuntimeError, "acceptance non-promotion"):
            validate_record(record, acceptance=acceptance, root=ROOT)


if __name__ == "__main__":
    unittest.main()
