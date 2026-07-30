from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger_poc_evidence import (
    EVIDENCE_PATH,
    ROOT,
    validate_evidence,
)


def load() -> dict:
    return json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))


class HumanAiCollaborationTddNoncomparativeDispatchIdentityLedgerPocEvidenceTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document)

    def test_rejects_live_runtime_enforcement_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["runtimeDispatchCapEnforcedForLiveRunner"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(document)

    def test_rejects_crash_recovery_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["crashRecoveryProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_cross_process_concurrency_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["crossProcessConcurrencyProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_module_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["artifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "artifact binding"):
            validate_evidence(document)


if __name__ == "__main__":
    unittest.main()
