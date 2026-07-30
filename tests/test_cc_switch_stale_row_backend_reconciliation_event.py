from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_cc_switch_stale_row_backend_reconciliation_event import (
    EVIDENCE_PATH,
    ROOT,
    validate_event,
)


class CcSwitchStaleRowBackendReconciliationEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_event_passes(self) -> None:
        validate_event(deepcopy(self.document), root=ROOT)

    def test_rejects_physical_body_deletion(self) -> None:
        document = deepcopy(self.document)
        document["authorityBoundary"]["physicalSsotDeletion"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_event(document, root=ROOT)

    def test_rejects_unresolved_row(self) -> None:
        document = deepcopy(self.document)
        document["postVerification"]["missingBodyDatabaseRows"] = 1
        with self.assertRaisesRegex(RuntimeError, "post-verification"):
            validate_event(document, root=ROOT)

    def test_rejects_cross_device_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["cloudSyncObservation"]["crossDeviceRestoreEqualityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "cloud-sync boundary"):
            validate_event(document, root=ROOT)

    def test_rejects_value_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["behavioralValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_event(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
