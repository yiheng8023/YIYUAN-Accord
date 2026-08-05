import copy
import json
import unittest

from scripts.validate_autoresearch_method_reference_evaluation import (
    EVALUATION_PATH,
    EXPECTED_REVISION,
    SNAPSHOT_PATH,
    validate_autoresearch_evaluation,
)


class AutoresearchMethodReferenceEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        cls.evaluation = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))

    def test_exact_source_snapshot_and_evaluation_are_valid(self) -> None:
        validate_autoresearch_evaluation()

    def test_snapshot_binds_exact_revision_and_six_git_blobs(self) -> None:
        self.assertEqual(self.snapshot["revision"], EXPECTED_REVISION)
        self.assertEqual(len(self.snapshot["gitObjects"]), 6)
        self.assertEqual(
            self.snapshot["gitObjectManifestSha256"],
            "5a16f3c29ebe513afa5be3bbf3dec1a2c323c1428d64da9ad9d961bddc3afa93",
        )

    def test_snapshot_does_not_promote_mutable_issue_or_license_claim(self) -> None:
        issue = self.snapshot["mutableObservations"][0]
        self.assertEqual(issue["locator"], "https://github.com/karpathy/autoresearch/issues/599")
        self.assertEqual(issue["claimUse"], "external-observational-counterevidence-only")
        self.assertEqual(self.snapshot["licenseArtifactStatus"], "not-observed-at-revision")

    def test_evaluation_blocks_direct_adoption_without_claiming_execution(self) -> None:
        floors = {
            item["floorId"]: item["result"]
            for item in self.evaluation["floorResults"]
        }
        self.assertEqual(floors["evidence-truth-and-provenance"], "blocked")
        self.assertEqual(floors["authority-and-data-boundary"], "blocked")
        self.assertEqual(self.evaluation["statusClaim"], "research-only")
        self.assertIn("not installed", self.evaluation["claimBoundary"])
        self.assertIn("not executed", self.evaluation["claimBoundary"])

    def test_manifest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.snapshot)
        mutated["gitObjectManifestSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "Git object manifest digest drifted"):
            validate_autoresearch_evaluation(snapshot=mutated, evaluation=self.evaluation)


if __name__ == "__main__":
    unittest.main()
