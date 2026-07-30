from __future__ import annotations

import unittest

from scripts.evaluate_software_lifecycle_architecture_security_suboracle import (
    build_architecture_security_suboracle_pack,
)


class SoftwareLifecycleArchitectureSecuritySuboracleTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = build_architecture_security_suboracle_pack()

    def test_positive_controls_are_accepted(self) -> None:
        self.assertTrue(self.pack["allPositiveAccepted"])
        self.assertTrue(
            all(self.pack["positiveAcceptance"].values())
        )
        self.assertEqual(
            "accept",
            self.pack["results"]["architecture"]["positive"][
                "decision"
            ],
        )
        self.assertEqual(
            "accept",
            self.pack["results"]["independentSecurityReview"][
                "positive"
            ]["decision"],
        )

    def test_negative_controls_are_rejected_for_declared_reasons(
        self,
    ) -> None:
        self.assertTrue(self.pack["allNegativeControlsRejected"])
        self.assertTrue(
            all(self.pack["negativeControlRejection"].values())
        )
        architecture_controls = self.pack["results"][
            "architecture"
        ]["negativeControls"]
        self.assertIn(
            "required-constraint-missing",
            architecture_controls[
                "coherent-but-constraint-violating"
            ]["failureCodes"],
        )
        self.assertIn(
            "real-seam-has-fewer-than-two-adapters",
            architecture_controls[
                "hypothetical-seam-promoted-to-real"
            ]["failureCodes"],
        )
        security_controls = self.pack["results"][
            "independentSecurityReview"
        ]["negativeControls"]
        self.assertIn(
            "reviewer-not-independent",
            security_controls["producer-self-review"][
                "failureCodes"
            ],
        )
        self.assertIn(
            "artifact-digest-mismatch",
            security_controls["artifact-digest-drift"][
                "failureCodes"
            ],
        )
        self.assertIn(
            "predeclared-fault-missed",
            security_controls["green-suite-misses-fault"][
                "failureCodes"
            ],
        )
        self.assertIn(
            "unresolved-high-finding",
            security_controls[
                "high-finding-hidden-by-summary"
            ]["failureCodes"],
        )

    def test_pack_is_deterministic_and_claims_stay_bounded(
        self,
    ) -> None:
        self.assertEqual(
            self.pack,
            build_architecture_security_suboracle_pack(),
        )
        self.assertTrue(
            all(
                value is False
                for value in self.pack["claimBoundary"].values()
            )
        )
        self.assertEqual(0, self.pack["execution"]["modelCallCount"])
        self.assertEqual(0, self.pack["execution"]["agentDispatchCount"])
        self.assertFalse(self.pack["execution"]["networkAccessUsed"])
        self.assertFalse(self.pack["execution"]["gitMutationUsed"])
        self.assertFalse(self.pack["execution"]["externalWriteUsed"])


if __name__ == "__main__":
    unittest.main()
