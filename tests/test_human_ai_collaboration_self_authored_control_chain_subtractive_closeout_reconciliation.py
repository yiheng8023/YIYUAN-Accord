from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_self_authored_control_chain_subtractive_closeout_reconciliation import (
    RECORD_PATH,
    ROOT,
    validate_reconciliation,
)


class SelfAuthoredControlChainSubtractiveCloseoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / RECORD_PATH).read_text(encoding="utf-8")
        )

    def test_current_reconciliation_is_valid(self) -> None:
        validate_reconciliation(self.document, root=ROOT)

    def test_rejects_self_authored_product_admission(self) -> None:
        document = copy.deepcopy(self.document)
        document["subtractiveDecisions"][
            "retainThreeSkillsAsPermanentlyAdmittedProductPayloads"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_full_lifecycle_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["lifecycleCoverage"]["notACompleteSoftwareLifecycle"] = False
        with self.assertRaisesRegex(RuntimeError, "lifecycle"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_program_closeout_upgrade(self) -> None:
        document = copy.deepcopy(self.document)
        row = next(
            item
            for item in document["closeoutCoverage"]
            if item["requirement"]
            == "three-lane program acceptance and final cleanup"
        )
        row["status"] = "covered"
        with self.assertRaisesRegex(RuntimeError, "closeout status"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_common_agents_root_removal(self) -> None:
        document = copy.deepcopy(self.document)
        document["rootAndCausalityRecalibration20260729"][
            "commonAgentsSkillsRootMustBeRetained"
        ] = False
        with self.assertRaisesRegex(
            RuntimeError, "root and causality recalibration"
        ):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_native_causation_from_current_turn(self) -> None:
        document = copy.deepcopy(self.document)
        document["rootAndCausalityRecalibration20260729"][
            "nativeRuntimeCauseProved"
        ] = True
        with self.assertRaisesRegex(
            RuntimeError, "root and causality recalibration"
        ):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_native_baseline_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["rootAndCausalityRecalibration20260729"][
            "nativeImplicitInvocationCapabilityProvedCurrentHost"
        ] = False
        with self.assertRaisesRegex(
            RuntimeError, "root and causality recalibration"
        ):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_portfolio_mutation_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["skillInstallUpdateDeleteReplaceOrRetireAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_reconciliation(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
