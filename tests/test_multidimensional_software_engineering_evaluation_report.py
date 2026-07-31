import copy
import json
import unittest

from scripts.validate_multidimensional_software_engineering_evaluation_report import (
    BOUNDED_ASSESSMENT_PATH,
    FIXTURE_PATH,
    validate_bounded_assessment_provenance,
    validate_report,
)


class MultidimensionalSoftwareEngineeringEvaluationReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.bounded_assessment = json.loads(
            BOUNDED_ASSESSMENT_PATH.read_text(encoding="utf-8")
        )

    def test_positive_fixture_is_valid(self) -> None:
        validate_report()

    def test_bounded_commit_assessment_is_valid(self) -> None:
        validate_bounded_assessment_provenance(self.bounded_assessment)

    def test_bounded_commit_manifest_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.bounded_assessment)
        manifest = next(
            item
            for item in mutated["evidence"]
            if item["id"] == "evidence.bb65a26-eight-file-git-object-manifest"
        )
        manifest["scope"] = manifest["scope"].replace(
            "9a9772709ee72753af6bdec9fc0eb6224444192a13cb2abd52c48e60c7db0289",
            "0" * 64,
        )
        with self.assertRaisesRegex(RuntimeError, "manifest digest drifted"):
            validate_bounded_assessment_provenance(mutated)

    def test_bounded_self_assessment_stays_unaccepted(self) -> None:
        self.assertEqual(
            self.bounded_assessment["independentReview"]["status"],
            "not-performed",
        )
        self.assertEqual(
            self.bounded_assessment["acceptanceAuthority"]["status"],
            "not-sought",
        )
        self.assertEqual(self.bounded_assessment["statusClaim"], "needs-verification")

    def test_total_score_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["totalScore"] = 95
        with self.assertRaisesRegex(RuntimeError, "missing or hidden fields"):
            validate_report(mutated)

    def test_dimension_result_mismatch_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["dimensionResults"].pop()
        with self.assertRaisesRegex(RuntimeError, "one exact set"):
            validate_report(mutated)

    def test_unknown_evidence_reference_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["dimensionResults"][0]["evidenceIds"] = ["evidence.missing"]
        with self.assertRaisesRegex(RuntimeError, "unknown evidence"):
            validate_report(mutated)

    def test_accepted_status_cannot_hide_incomplete_dimension(self) -> None:
        mutated = copy.deepcopy(self.report)
        mutated["statusClaim"] = "accepted"
        mutated["independentReview"]["status"] = "performed"
        mutated["independentReview"]["reviewer"] = "independent reviewer"
        mutated["acceptanceAuthority"]["status"] = "accepted"
        with self.assertRaisesRegex(RuntimeError, "incomplete dimension or floor"):
            validate_report(mutated)

    def test_accepted_status_requires_independent_review(self) -> None:
        mutated = copy.deepcopy(self.report)
        for result in mutated["dimensionResults"]:
            result["assessment"] = "adequate"
        mutated["statusClaim"] = "accepted"
        mutated["acceptanceAuthority"]["status"] = "accepted"
        with self.assertRaisesRegex(RuntimeError, "lacks independent review"):
            validate_report(mutated)

    def test_accepted_status_requires_acceptance_authority(self) -> None:
        mutated = copy.deepcopy(self.report)
        for result in mutated["dimensionResults"]:
            result["assessment"] = "adequate"
        mutated["statusClaim"] = "accepted"
        mutated["independentReview"]["status"] = "performed"
        mutated["independentReview"]["reviewer"] = "independent reviewer"
        with self.assertRaisesRegex(RuntimeError, "lacks acceptance authority"):
            validate_report(mutated)


if __name__ == "__main__":
    unittest.main()
