from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_codex_common_root_doc_pdf_host_disable_transaction import (
    EVIDENCE_PATH,
    ROOT,
    validate_transaction,
)


class CodexCommonRootDocPdfHostDisableTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_transaction_passes(self) -> None:
        validate_transaction(deepcopy(self.document), root=ROOT)

    def test_rejects_missing_authorization(self) -> None:
        document = deepcopy(self.document)
        document["authorityBoundary"]["explicitUserAuthorizationObserved"] = False
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_transaction(document, root=ROOT)

    def test_rejects_false_target_state(self) -> None:
        document = deepcopy(self.document)
        document["liveNoModelExposureProbe"]["pluginFeaturesEnabledArm"]["doc"][
            "enabled"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "live no-model exposure"):
            validate_transaction(document, root=ROOT)

    def test_rejects_missing_runtime_alternative(self) -> None:
        document = deepcopy(self.document)
        document["liveNoModelExposureProbe"]["pluginFeaturesEnabledArm"][
            "runtimePdf"
        ]["enabled"] = False
        with self.assertRaisesRegex(RuntimeError, "live no-model exposure"):
            validate_transaction(document, root=ROOT)

    def test_rejects_carrier_deletion(self) -> None:
        document = deepcopy(self.document)
        document["carrierPreservation"]["agentsDocAndPdfLinksPresent"] = False
        with self.assertRaisesRegex(RuntimeError, "carrier preservation"):
            validate_transaction(document, root=ROOT)

    def test_rejects_model_dispatch(self) -> None:
        document = deepcopy(self.document)
        document["authorityBoundary"]["modelDispatch"] = True
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_transaction(document, root=ROOT)

    def test_rejects_retained_backup_claim(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["exactRollbackBackupAbsent"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup state"):
            validate_transaction(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
