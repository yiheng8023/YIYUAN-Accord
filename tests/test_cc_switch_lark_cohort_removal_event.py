from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_cc_switch_lark_cohort_removal_event import (
    EVIDENCE_PATH,
    ROOT,
    validate_event,
)


class CcSwitchLarkCohortRemovalEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_event_passes(self) -> None:
        validate_event(deepcopy(self.document), root=ROOT)

    def test_rejects_partial_cohort(self) -> None:
        document = deepcopy(self.document)
        document["removedSkills"].pop()
        with self.assertRaisesRegex(RuntimeError, "cohort drifted"):
            validate_event(document, root=ROOT)

    def test_rejects_agents_as_second_store(self) -> None:
        document = deepcopy(self.document)
        document["directoryAuthority"]["agentsRole"] = "second entity store"
        with self.assertRaisesRegex(RuntimeError, "directory authority"):
            validate_event(document, root=ROOT)

    def test_rejects_trae_mutation(self) -> None:
        document = deepcopy(self.document)
        document["foreignRootSentinels"]["traePluginLarkEntriesAfter"] = 0
        with self.assertRaisesRegex(RuntimeError, "foreign-root sentinels"):
            validate_event(document, root=ROOT)

    def test_rejects_residual_lark_row(self) -> None:
        document = deepcopy(self.document)
        document["postState"]["databaseLarkRows"] = 1
        with self.assertRaisesRegex(RuntimeError, "post-state"):
            validate_event(document, root=ROOT)

    def test_rejects_loader_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["freshTaskCatalogRefreshObserved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_event(document, root=ROOT)

    def test_rejects_retained_process_recovery_root(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["agentRecoveryRootAbsent"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup evidence"):
            validate_event(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
