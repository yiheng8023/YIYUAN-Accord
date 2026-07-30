from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_user_starred_huashu_pm_current_component_delta_research import (
    EVIDENCE_PATH,
    ROOT,
    validate_research,
)


class UserStarredHuashuPmCurrentComponentDeltaResearchTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_research_passes(self) -> None:
        validate_research(deepcopy(self.document), root=ROOT)

    def test_rejects_huashu_atomic_candidate_promotion(self) -> None:
        document = deepcopy(self.document)
        document["sources"]["huashuDesign"]["currentAtomicCandidate"] = True
        with self.assertRaisesRegex(RuntimeError, "atomic-candidate boundary"):
            validate_research(document, root=ROOT)

    def test_rejects_extra_pm_component(self) -> None:
        document = deepcopy(self.document)
        document["sources"]["pmSkills"]["selectedComponents"].append(
            {
                "name": "pre-mortem",
                "path": "pm-execution/skills/pre-mortem/SKILL.md",
                "blob": "0" * 40,
                "bytes": 1,
                "status": "static-protocol-candidate-only",
                "hardRuntimeDependency": False,
            }
        )
        with self.assertRaisesRegex(RuntimeError, "component coverage"):
            validate_research(document, root=ROOT)

    def test_rejects_selected_component_install_authority(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["selectedComponentInstallAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_research(document, root=ROOT)

    def test_rejects_model_dispatch_authority(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["modelDispatchAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_research(document, root=ROOT)

    def test_rejects_behavioral_increment_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["behavioralIncrementProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_research(document, root=ROOT)

    def test_rejects_residual_gap_and_self_authored_eligibility(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["residualCapabilityGapProved"] = True
        document["decision"]["selfAuthoredWorkEligible"] = True
        with self.assertRaisesRegex(
            RuntimeError, "decision boundary|claim boundary"
        ):
            validate_research(document, root=ROOT)

    def test_rejects_temporary_source_root_drift(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["temporarySourceRootCreated"] = True
        document["cleanup"]["temporarySourceRootAbsent"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup evidence"):
            validate_research(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
