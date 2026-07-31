import copy
import json
import unittest

from scripts.validate_multidimensional_software_engineering_evaluation_report import (
    FIXTURE_PATH,
    validate_report,
)


class MultidimensionalSoftwareEngineeringEvaluationReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_positive_fixture_is_valid(self) -> None:
        validate_report()

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
