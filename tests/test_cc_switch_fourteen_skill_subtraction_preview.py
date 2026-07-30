from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_cc_switch_fourteen_skill_subtraction_preview import (
    EVIDENCE_PATH,
    ROOT,
    validate_preview,
)


class CcSwitchFourteenSkillSubtractionPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_preview_passes(self) -> None:
        validate_preview(deepcopy(self.document), root=ROOT)

    def test_rejects_live_uninstall_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["liveUninstallExecuted"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_preview(document, root=ROOT)

    def test_rejects_diagnose_inclusion(self) -> None:
        document = deepcopy(self.document)
        document["candidateCohort"]["names"][0] = "diagnose"
        with self.assertRaisesRegex(RuntimeError, "candidate manifest"):
            validate_preview(document, root=ROOT)

    def test_rejects_single_host_restore_assumption(self) -> None:
        document = deepcopy(self.document)
        document["managerSemantics"][
            "dualHostRollbackRequiresRestoreThenSecondHostToggle"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "manager semantics"):
            validate_preview(document, root=ROOT)

    def test_rejects_hidden_backup_eviction(self) -> None:
        document = deepcopy(self.document)
        document["backupRotationProjection"][
            "evictionRequiresExplicitAuthorization"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "backup rotation"):
            validate_preview(document, root=ROOT)

    def test_rejects_database_in_recovery_archive(self) -> None:
        document = deepcopy(self.document)
        document["recoveryPreflight"][
            "excludeRawDatabaseSettingsCredentialsAccountAndSessionData"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "recovery preflight"):
            validate_preview(document, root=ROOT)

    def test_rejects_premature_agents_cleanup(self) -> None:
        document = deepcopy(self.document)
        document["rollbackPlan"]["agentsLinksRemainUntilFullBatchSuccess"] = False
        with self.assertRaisesRegex(RuntimeError, "rollback plan"):
            validate_preview(document, root=ROOT)

    def test_rejects_post_count_drift(self) -> None:
        document = deepcopy(self.document)
        document["expectedPostState"]["databaseRows"] = 42
        with self.assertRaisesRegex(RuntimeError, "expected post-state"):
            validate_preview(document, root=ROOT)

    def test_rejects_retained_source_clone(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["ccSwitchSourceTempRootAbsent"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup evidence"):
            validate_preview(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
