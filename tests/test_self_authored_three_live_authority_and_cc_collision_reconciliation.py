from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_self_authored_three_live_authority_and_cc_collision_reconciliation import (
    EVIDENCE_PATH,
    ROOT,
    validate_reconciliation,
)


class SelfAuthoredThreeLiveAuthorityAndCcCollisionReconciliationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_reconciliation_passes(self) -> None:
        validate_reconciliation(deepcopy(self.document), root=ROOT)

    def test_rejects_cc_as_source_authority(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["ccRowsAreNotSourceAuthority"] = False
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_ordinary_manager_action_as_safe(self) -> None:
        document = deepcopy(self.document)
        document["managerCollision"][
            "ordinaryCcUninstallToggleOrSyncSafeForTheseThree"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "manager collision"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_current_and_legacy_tree_conflation(self) -> None:
        document = deepcopy(self.document)
        document["packages"][0]["legacyCcProjection"][
            "matchesCurrentSourceProjection"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "legacy tree"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_claude_loader_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claudeExposure"]["freshClaudeLoaderExposureProved"] = True
        with self.assertRaisesRegex(RuntimeError, "Claude exposure"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_retirement_authority(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["firstPartyCcRetirementMutationAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_stale_318_preview_as_execution_current(self) -> None:
        document = deepcopy(self.document)
        document["decision"][
            "priorFourteenPreviewRequiresManager319RefreshBeforeExecution"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_behavior_value_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["behavioralValueOrSuperiorityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_reconciliation(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
