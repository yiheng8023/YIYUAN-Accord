from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_cc_switch_fourteen_skill_subtraction_preview_319_refresh import (
    EVIDENCE_PATH,
    ROOT,
    validate_refresh,
)


class CcSwitchFourteenSkillSubtractionPreview319RefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_refresh_passes(self) -> None:
        validate_refresh(deepcopy(self.document), root=ROOT)

    def test_rejects_stale_manager_version(self) -> None:
        document = deepcopy(self.document)
        document["manager"]["binaryFileVersion"] = "3.18.0"
        with self.assertRaisesRegex(RuntimeError, "manager identity"):
            validate_refresh(document, root=ROOT)

    def test_rejects_first_party_collision_in_cohort(self) -> None:
        document = deepcopy(self.document)
        document["managerSemantics"][
            "ordinaryUninstallHasNoFirstPartyPhysicalDirectoryCollisionForThisCohort"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "manager semantics"):
            validate_refresh(document, root=ROOT)

    def test_rejects_backup_eviction_without_authorization_gate(self) -> None:
        document = deepcopy(self.document)
        document["backupRotation"]["evictionRequiresExplicitAuthorization"] = False
        with self.assertRaisesRegex(RuntimeError, "backup rotation"):
            validate_refresh(document, root=ROOT)

    def test_rejects_live_uninstall_authority(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["liveUninstallAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_refresh(document, root=ROOT)

    def test_rejects_post_state_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["postStateProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_refresh(document, root=ROOT)

    def test_rejects_missing_common_link_cleanup(self) -> None:
        document = deepcopy(self.document)
        document["transactionAndRollback"][
            "removeExactFourteenBrokenAgentsLinksOnlyAfterFullManagerSuccess"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "transaction or rollback"):
            validate_refresh(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
