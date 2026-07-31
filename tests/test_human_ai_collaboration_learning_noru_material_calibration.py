import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_learning_noru_material_calibration import (
    CALIBRATION_PATH,
    PRIVATE_PATH,
    PUBLIC_PATH,
    validate_calibration,
)


class HumanAiCollaborationLearningNoruMaterialCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        cls.public = json.loads(PUBLIC_PATH.read_text(encoding="utf-8"))
        cls.private = json.loads(PRIVATE_PATH.read_text(encoding="utf-8"))

    def test_repository_materials_are_consistent(self) -> None:
        validate_calibration()

    def test_public_answer_leak_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.public)
        mutated["practiceItems"][0]["answer"] = "ava/plain/1"
        with self.assertRaisesRegex(RuntimeError, "leaks assessment keys"):
            validate_calibration(self.calibration, public_packet=mutated)

    def test_wrong_transform_answer_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.private)
        mutated["immediateForm"]["items"][0]["answer"] = "ava/ring/3"
        with self.assertRaisesRegex(RuntimeError, "transform oracle mismatch"):
            validate_calibration(self.calibration, private_oracle=mutated)

    def test_practice_assessment_overlap_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.private)
        mutated["immediateForm"]["items"][0]["id"] = "P1"
        with self.assertRaisesRegex(RuntimeError, "practice and assessment ids overlap"):
            validate_calibration(self.calibration, private_oracle=mutated)

    def test_unresolved_misconception_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.private)
        mutated["delayedForm"]["items"][0]["misconceptionIds"] = ["MISSING"]
        with self.assertRaisesRegex(RuntimeError, "misconception reference is unresolved"):
            validate_calibration(self.calibration, private_oracle=mutated)

    def test_form_equivalence_cannot_be_asserted(self) -> None:
        mutated = copy.deepcopy(self.private)
        mutated["parallelFormBoundary"]["equivalenceProved"] = True
        with self.assertRaisesRegex(RuntimeError, "form equivalence was overclaimed"):
            validate_calibration(self.calibration, private_oracle=mutated)

    def test_cleanup_root_cannot_be_broadened(self) -> None:
        mutated = copy.deepcopy(self.calibration)
        mutated["cleanupManifest"]["trialRootTemplate"] = ".tmp"
        with self.assertRaisesRegex(RuntimeError, "cleanup root broadened"):
            validate_calibration(mutated)

    def test_human_usability_claim_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.calibration)
        mutated["claimBoundary"]["humanUsabilityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "promoted claim"):
            validate_calibration(mutated)


if __name__ == "__main__":
    unittest.main()
