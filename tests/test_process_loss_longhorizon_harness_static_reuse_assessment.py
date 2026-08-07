from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_loss_longhorizon_harness_static_reuse_assessment import (
    ACCEPTANCE_PATH,
    EVIDENCE_ID,
    EXPECTED_ACCEPTANCE_ASSESSMENTS,
    EXPECTED_BLOCKER_IDS,
    EXPECTED_GIT_OBJECTS,
    RECORD_PATH,
    REVISION,
    SUPPORTED_ACCEPTANCE_IDS,
    validate_assessment_record,
    validate_repository_assessment,
)


ROOT = Path(__file__).resolve().parent.parent


def load_record() -> dict:
    return json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))


def load_acceptance() -> dict:
    return json.loads((ROOT / ACCEPTANCE_PATH).read_text(encoding="utf-8"))


class ProcessLossLongHorizonHarnessStaticReuseAssessmentTests(unittest.TestCase):
    def test_repository_assessment_is_valid(self) -> None:
        record = validate_repository_assessment(ROOT)

        self.assertEqual(
            "exact-revision-static-reuse-candidate-review-complete-no-adoption",
            record["status"],
        )
        self.assertEqual(
            REVISION,
            record["sourceSnapshot"]["repository"]["revision"],
        )

    def test_exact_source_objects_are_frozen_without_payload_retention(self) -> None:
        record = load_record()
        repository = record["sourceSnapshot"]["repository"]
        objects = {
            item["path"]: (item["oid"], item["size"])
            for item in repository["selectedGitObjects"]
        }

        self.assertEqual(EXPECTED_GIT_OBJECTS, objects)
        self.assertEqual("MIT", repository["license"])
        self.assertFalse(record["sourceSnapshot"]["rawThirdPartyBodyRetained"])
        self.assertFalse(record["sourceSnapshot"]["thirdPartyCodeExecuted"])
        self.assertFalse(record["sourceSnapshot"]["dependenciesInstalled"])

    def test_reuse_decision_keeps_harness_authority_and_blocks_adoption(self) -> None:
        record = load_record()
        fit = record["harnessFit"]
        authority = record["authorityBoundary"]
        claims = record["claimBoundary"]

        self.assertEqual(
            EXPECTED_BLOCKER_IDS,
            {item["id"] for item in fit["adoptionBlockers"]},
        )
        self.assertEqual(
            "not-authorized-and-not-supported",
            fit["directReplacementDecision"],
        )
        self.assertFalse(authority["installAuthorized"])
        self.assertFalse(authority["executeAuthorized"])
        self.assertFalse(authority["modelDispatchAuthorized"])
        self.assertFalse(authority["managerSubstitutionAuthorized"])
        self.assertFalse(claims["provesRuntimeBehavior"])
        self.assertFalse(claims["provesUserValue"])
        self.assertFalse(claims["provesResidualGap"])

    def test_acceptance_map_binds_evidence_without_promotion(self) -> None:
        acceptance = load_acceptance()
        criteria = {
            item["id"]: item for item in acceptance["acceptanceCriteria"]
        }
        evidence = {item["id"]: item for item in acceptance["evidence"]}

        for acceptance_id in SUPPORTED_ACCEPTANCE_IDS:
            self.assertEqual(
                EXPECTED_ACCEPTANCE_ASSESSMENTS[acceptance_id],
                criteria[acceptance_id]["assessment"],
            )
            self.assertIn(EVIDENCE_ID, criteria[acceptance_id]["evidenceIds"])

        self.assertEqual(
            set(SUPPORTED_ACCEPTANCE_IDS),
            set(evidence[EVIDENCE_ID]["supports"]),
        )

    def test_revision_mutation_fails_closed(self) -> None:
        record = load_record()
        record["sourceSnapshot"]["repository"]["revision"] = "0" * 40

        with self.assertRaisesRegex(RuntimeError, "repository identity"):
            validate_assessment_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_benchmark_replication_promotion_fails_closed(self) -> None:
        record = load_record()
        record["reportedBenchmarkObservations"][
            "independentlyReplicatedInThisAssessment"
        ] = True

        with self.assertRaisesRegex(RuntimeError, "benchmark boundary"):
            validate_assessment_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_execution_authority_promotion_fails_closed(self) -> None:
        record = load_record()
        record["authorityBoundary"]["executeAuthorized"] = True

        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_assessment_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_adoption_blocker_removal_fails_closed(self) -> None:
        record = load_record()
        record["harnessFit"]["adoptionBlockers"].pop()

        with self.assertRaisesRegex(RuntimeError, "adoption-blocker"):
            validate_assessment_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_acceptance_promotion_fails_closed(self) -> None:
        record = load_record()
        acceptance = copy.deepcopy(load_acceptance())
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["assessment"] = "verified"

        with self.assertRaisesRegex(RuntimeError, "acceptance boundary"):
            validate_assessment_record(record, acceptance=acceptance, root=ROOT)


if __name__ == "__main__":
    unittest.main()
