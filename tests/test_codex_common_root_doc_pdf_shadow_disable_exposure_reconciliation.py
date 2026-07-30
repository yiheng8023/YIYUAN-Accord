from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_codex_common_root_doc_pdf_shadow_disable_exposure_reconciliation import (
    EVIDENCE_PATH,
    ROOT,
    validate_reconciliation,
)


class CodexCommonRootDocPdfReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_reconciliation_passes(self) -> None:
        validate_reconciliation(deepcopy(self.document), root=ROOT)

    def test_rejects_false_host_disable(self) -> None:
        document = deepcopy(self.document)
        document["causalAssessment"]["codexHostExposureDisableSucceeded"] = True
        with self.assertRaisesRegex(RuntimeError, "causal assessment"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_live_config_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["liveGlobalDisableApplied"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_common_root_deletion_preference(self) -> None:
        document = deepcopy(self.document)
        document["optionAssessment"][0]["result"] = "preferred"
        with self.assertRaisesRegex(RuntimeError, "option judgment"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_model_dispatch(self) -> None:
        document = deepcopy(self.document)
        document["authorityBoundary"]["modelDispatch"] = True
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_retained_temporary_projection(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["temporaryProjectionRootAbsent"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup evidence"):
            validate_reconciliation(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
