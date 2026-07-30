from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_human_ai_collaboration_release_change_current_cc_codex_no_model_preflight import (
    EVIDENCE_PATH,
    ROOT,
    validate_preflight,
)


class ReleaseChangeCurrentCcCodexNoModelPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_preflight_passes(self) -> None:
        validate_preflight(deepcopy(self.document), root=ROOT)

    def test_rejects_candidate_drift_attribution(self) -> None:
        document = deepcopy(self.document)
        document["driftAttribution"][
            "candidateCohortCausedWholeStateFailure"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "counterfactual"):
            validate_preflight(document, root=ROOT)

    def test_rejects_frozen_baseline_refresh(self) -> None:
        document = deepcopy(self.document)
        document["driftAttribution"][
            "oldFrozenBaselineShouldBeRefreshedFromThisObservation"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "baseline boundary"):
            validate_preflight(document, root=ROOT)

    def test_rejects_candidate_hash_drift(self) -> None:
        document = deepcopy(self.document)
        document["candidateObservations"][0]["ccSkillMdSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "candidate identity"):
            validate_preflight(document, root=ROOT)

    def test_rejects_cli_desktop_equivalence_promotion(self) -> None:
        document = deepcopy(self.document)
        document["hostCarrierObservations"]["carrierEquivalenceProved"] = True
        with self.assertRaisesRegex(RuntimeError, "Desktop carrier"):
            validate_preflight(document, root=ROOT)

    def test_rejects_fresh_desktop_exposure_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["preflightDecision"][
            "independentFreshDesktopExposureReproduced"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_preflight(document, root=ROOT)

    def test_rejects_behavioral_value_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["preflightDecision"]["candidateBehaviorOrValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_preflight(document, root=ROOT)

    def test_rejects_self_authored_eligibility(self) -> None:
        document = deepcopy(self.document)
        document["preflightDecision"]["selfAuthoredWorkEligible"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_preflight(document, root=ROOT)

    def test_rejects_hidden_model_request(self) -> None:
        document = deepcopy(self.document)
        document["executionCounters"]["modelRequestCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "execution counter"):
            validate_preflight(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
