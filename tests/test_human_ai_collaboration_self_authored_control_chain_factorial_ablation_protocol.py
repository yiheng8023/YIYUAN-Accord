from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_self_authored_control_chain_factorial_ablation_protocol import (
    PROTOCOL_PATH,
    ROOT,
    validate_protocol,
)


class SelfAuthoredControlChainFactorialAblationProtocolTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_protocol(document or self.document, root=ROOT)

    def test_current_protocol_is_valid(self) -> None:
        self.validate()

    def test_rejects_missing_factorial_cell(self) -> None:
        document = copy.deepcopy(self.document)
        document["factorialCells"].pop()
        with self.assertRaisesRegex(RuntimeError, "cell coverage"):
            self.validate(document)

    def test_rejects_chain_credit_for_shared_hard_standards(self) -> None:
        document = copy.deepcopy(self.document)
        document["heldConstant"]["hardStandardsCreditedAsTreatmentValue"] = True
        with self.assertRaisesRegex(RuntimeError, "held-constant"):
            self.validate(document)

    def test_rejects_skill_pin_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["factors"]["chain"]["exactSkillPins"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "Skill pins"):
            self.validate(document)

    def test_rejects_dependency_pin_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["factors"]["chain"]["exactDependencyPins"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "dependency pins"):
            self.validate(document)

    def test_rejects_hook_pin_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["factors"]["hook"]["exactPins"]["handlerSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "Hook pins"):
            self.validate(document)

    def test_rejects_live_user_hook_mutation(self) -> None:
        document = copy.deepcopy(self.document)
        document["factors"]["hook"]["isolationBoundary"][
            "liveUserHookConfigurationMutationAllowed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "Hook isolation"):
            self.validate(document)

    def test_rejects_silent_model_substitution(self) -> None:
        document = copy.deepcopy(self.document)
        document["modelPolicy"]["silentModelSubstitutionAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "model route"):
            self.validate(document)

    def test_rejects_live_admission_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["admittedForLiveExecution"] = True
        with self.assertRaisesRegex(RuntimeError, "admission overclaimed"):
            self.validate(document)

    def test_rejects_preflight_evidence_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["zeroModelFailureFallbackProbePassed"] = False
        with self.assertRaisesRegex(RuntimeError, "admission overclaimed"):
            self.validate(document)

    def test_rejects_factorial_adapter_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["factorialEvidenceAdapterImplemented"] = False
        with self.assertRaisesRegex(RuntimeError, "admission overclaimed"):
            self.validate(document)

    def test_rejects_four_cell_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["taskScopedFourCellExposureProved"] = False
        with self.assertRaisesRegex(RuntimeError, "admission overclaimed"):
            self.validate(document)

    def test_rejects_model_dispatch_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["modelDispatchAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority expanded"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
