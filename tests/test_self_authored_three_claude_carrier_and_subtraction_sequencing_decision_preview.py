from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_self_authored_three_claude_carrier_and_subtraction_sequencing_decision_preview import (
    EVIDENCE_PATH,
    ROOT,
    validate_preview,
)


class SelfAuthoredThreeClaudeCarrierDecisionPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))

    def test_current_preview_passes(self) -> None:
        validate_preview(copy.deepcopy(self.document), root=ROOT)

    def test_rejects_agents_direct_discovery_overclaim(self) -> None:
        document = copy.deepcopy(self.document)
        document["officialClaudeCodeContract"][
            "directAgentsRootDiscoveryDocumented"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "official carrier"):
            validate_preview(document, root=ROOT)

    def test_rejects_symlink_version_mismatch(self) -> None:
        document = copy.deepcopy(self.document)
        document["officialClaudeCodeContract"][
            "currentVersionMeetsDocumentedSymlinkMinimum"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "official carrier"):
            validate_preview(document, root=ROOT)

    def test_rejects_documented_precedence_as_runtime_proof(self) -> None:
        document = copy.deepcopy(self.document)
        document["officialClaudeCodeContract"][
            "documentedPrecedenceIndependentlyVerifiedAgainstCurrentRuntime"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "official carrier"):
            validate_preview(document, root=ROOT)

    def test_rejects_plugin_substitution(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceOwnedAdapter"]["requiresPluginPackaging"] = True
        with self.assertRaisesRegex(RuntimeError, "adapter decision"):
            validate_preview(document, root=ROOT)

    def test_rejects_line_guidance_as_hard_loader_gate(self) -> None:
        document = copy.deepcopy(self.document)
        document["localClaudeState"][
            "official500LineGuidanceIsKnownHardLoaderLimit"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "local carrier"):
            validate_preview(document, root=ROOT)

    def test_rejects_unsafe_ordinary_uninstall(self) -> None:
        document = copy.deepcopy(self.document)
        document["collisionSafeFirstPartyTransactionPreview"][
            "ordinaryCcUninstallWithoutCodexQuarantineAllowed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "collision-safe"):
            validate_preview(document, root=ROOT)

    def test_rejects_hidden_additional_backup_eviction(self) -> None:
        document = copy.deepcopy(self.document)
        document["transactionSequencing"]["phase2FirstPartyThree"][
            "additionalOriginalBackupEvictionsIfNoConcurrentBackup"
        ] = []
        with self.assertRaisesRegex(RuntimeError, "sequencing"):
            validate_preview(document, root=ROOT)

    def test_rejects_incorrect_final_retained_backup_order(self) -> None:
        document = copy.deepcopy(self.document)
        retained = document["transactionSequencing"]["phase2FirstPartyThree"][
            "finalOriginalBackupsRetained"
        ]
        retained[0:2] = reversed(retained[0:2])
        with self.assertRaisesRegex(RuntimeError, "sequencing"):
            validate_preview(document, root=ROOT)

    def test_rejects_live_exposure_overclaim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["recommendedAdapterLiveExposureProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_preview(document, root=ROOT)

    def test_rejects_poststate_as_proved(self) -> None:
        document = copy.deepcopy(self.document)
        document["projectedFinalTopologyIfRecommendedBThenSucceeds"][
            "forecastOnly"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "topology projection"):
            validate_preview(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
