from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_fidelity_cumulative_loss_accounting_poc_evidence import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityCumulativeLossAccountingEvidenceTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_evidence_passes(self) -> None:
        validate_evidence(copy.deepcopy(self.document), root=ROOT)

    def test_live_claim_promotion_fails(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["liveAgentBehaviorProved"] = True
        with self.assertRaises(RuntimeError):
            validate_evidence(document, root=ROOT)

    def test_missing_claim_boundary_fails(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"].pop("softwareLifecycleCoverageProved")
        with self.assertRaises(RuntimeError):
            validate_evidence(document, root=ROOT)

    def test_subgate_closure_fails(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["subgateClosed"] = True
        with self.assertRaises(RuntimeError):
            validate_evidence(document, root=ROOT)

    def test_frozen_evaluator_hash_drift_fails(self) -> None:
        document = copy.deepcopy(self.document)
        document["bindings"]["frozenTraceEvaluator"]["fileSha256"] = (
            "0" * 64
        )
        with self.assertRaises(RuntimeError):
            validate_evidence(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
