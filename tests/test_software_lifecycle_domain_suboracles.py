from __future__ import annotations

import unittest

from scripts.evaluate_software_lifecycle_domain_suboracles import (
    build_domain_suboracle_pack,
    stage_suboracle_bindings,
)


class SoftwareLifecycleDomainSuboracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = build_domain_suboracle_pack()

    def test_existing_classifiers_accept_positives_and_reject_controls(
        self,
    ) -> None:
        pack = self.pack
        self.assertTrue(pack["allPositiveAccepted"])
        self.assertTrue(pack["allNegativeControlsRejected"])
        self.assertTrue(
            all(pack["positiveAcceptance"].values())
        )
        self.assertTrue(
            all(pack["negativeControlRejection"].values())
        )
        self.assertTrue(
            all(
                value is False
                for value in pack["claimBoundary"].values()
            )
        )

    def test_only_relevant_stages_receive_suboracle_bindings(
        self,
    ) -> None:
        pack = self.pack
        expected = {
            "requirements-domain": [],
            "architecture-design": ["architecture"],
            "implementation-tdd": ["tdd"],
            "independent-review-test-security": [
                "independentSecurityReview"
            ],
            "release-rollback-gating": ["releaseRollback"],
            "observation-incident-handling": ["incident"],
            "maintenance-evolution": [
                "maintenance",
                "cumulativeLoss",
            ],
        }
        for stage_class, keys in expected.items():
            with self.subTest(stage_class=stage_class):
                bindings = stage_suboracle_bindings(
                    stage_class,
                    pack,
                )
                self.assertEqual(
                    keys,
                    [item["resultKey"] for item in bindings],
                )

    def test_disposable_domain_fixtures_observe_red_then_green(
        self,
    ) -> None:
        for result_key in ("incident", "maintenance"):
            with self.subTest(result_key=result_key):
                execution = self.pack["results"][result_key][
                    "disposableFixtureExecution"
                ]
                self.assertFalse(
                    execution["redBeforeFix"]["visible"]["passed"]
                )
                self.assertFalse(
                    execution["redBeforeFix"]["hidden"]["passed"]
                )
                self.assertEqual(
                    "expected-behavior-assertion",
                    execution["redBeforeFix"]["visible"][
                        "failureClass"
                    ],
                )
                self.assertEqual(
                    "expected-behavior-assertion",
                    execution["redBeforeFix"]["hidden"][
                        "failureClass"
                    ],
                )
                self.assertEqual(
                    "accept-red",
                    execution["redBeforeFix"]["gate"]["decision"],
                )
                self.assertTrue(
                    execution["greenAfterFix"]["visible"]["passed"]
                )
                self.assertTrue(
                    execution["greenAfterFix"]["hidden"]["passed"]
                )
                self.assertEqual(
                    "green",
                    execution["greenAfterFix"]["focusedVisible"][
                        "failureClass"
                    ],
                )
                self.assertEqual(
                    "green",
                    execution["greenAfterFix"]["hiddenBehavior"][
                        "failureClass"
                    ],
                )
                self.assertTrue(execution["stageReceiptChainValid"])
                self.assertTrue(
                    execution["redImplementationHashStable"]
                )
                self.assertTrue(execution["redStageScopeExact"])
                self.assertTrue(execution["fixStageScopeExact"])
                self.assertTrue(execution["greenStageTreeStable"])
                self.assertTrue(execution["changedFileScopeExact"])
                self.assertTrue(execution["immutableInputsStable"])
                self.assertEqual(0, execution["agentDispatchCount"])
                self.assertEqual(0, execution["modelCallCount"])
                side_effects = execution["sideEffectObservation"]
                self.assertFalse(
                    side_effects["networkInstrumentationAvailable"]
                )
                self.assertFalse(
                    side_effects["networkAbsenceProved"]
                )
                self.assertFalse(
                    side_effects[
                        "outsideTemporaryRootInstrumentationAvailable"
                    ]
                )
                self.assertFalse(
                    side_effects["externalWriteAbsenceProved"]
                )
                self.assertFalse(
                    side_effects["gitMutationAbsenceProved"]
                )
                self.assertTrue(
                    all(
                        value is False
                        for value in execution[
                            "claimBoundary"
                        ].values()
                    )
                )

    def test_domain_suboracle_pack_is_recomputably_deterministic(
        self,
    ) -> None:
        self.assertEqual(
            self.pack,
            build_domain_suboracle_pack(),
        )


if __name__ == "__main__":
    unittest.main()
