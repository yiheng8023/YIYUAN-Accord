from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_cc_switch_subtraction_cohort_and_codex_shadow_disable_event import (
    EVIDENCE_PATH,
    ROOT,
    validate_event,
)


class CcSwitchSubtractionAndShadowDisableEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_event_passes(self) -> None:
        validate_event(deepcopy(self.document), root=ROOT)

    def test_rejects_partial_removal_cohort(self) -> None:
        document = deepcopy(self.document)
        document["removedSkills"].pop()
        with self.assertRaisesRegex(RuntimeError, "cohort drifted"):
            validate_event(document, root=ROOT)

    def test_rejects_shared_root_removal(self) -> None:
        document = deepcopy(self.document)
        document["authorityBoundary"]["sharedRootPreserved"] = False
        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_event(document, root=ROOT)

    def test_rejects_cross_host_doc_pdf_disable(self) -> None:
        document = deepcopy(self.document)
        document["postState"]["docAndPdfRemainInCcAgentsClaude"] = False
        with self.assertRaisesRegex(RuntimeError, "post-state"):
            validate_event(document, root=ROOT)

    def test_rejects_trae_hash_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["foreignRootObservation"]["prePostContentHashSentinelAvailable"] = True
        with self.assertRaisesRegex(RuntimeError, "foreign-root boundary"):
            validate_event(document, root=ROOT)

    def test_rejects_retained_process_recovery_root(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["temporaryRecoveryRootRetained"] = True
        with self.assertRaisesRegex(RuntimeError, "cleanup evidence"):
            validate_event(document, root=ROOT)

    def test_rejects_loader_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["loaderInvocationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_event(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
