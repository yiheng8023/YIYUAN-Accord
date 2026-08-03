import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_fidelity_chained_transform_adapter_evaluator_poc_evidence import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityChainedTransformAdapterEvaluatorPocEvidenceTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document, root=ROOT)

    def test_live_route_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["execution"]["actualRouteObserved"] = True
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_evidence(mutated, root=ROOT)

    def test_formal_count_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["decision"]["formalProcessCohortCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(mutated, root=ROOT)

    def test_end_to_end_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["decision"][
            "endToEndProcessFidelityAssessment"
        ] = "verified"
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_evidence(mutated, root=ROOT)

    def test_cleanup_reclassification_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["auditEvidence"]["cleanupDisposition"] = "delete"
        with self.assertRaisesRegex(RuntimeError, "audit evidence boundary"):
            validate_evidence(mutated, root=ROOT)

    def test_repository_manifest_hash_is_required(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["auditEvidence"]["manifestRepositoryFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "audit evidence hash"):
            validate_evidence(mutated, root=ROOT)

    def test_capture_manifest_hash_is_still_required(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["auditEvidence"]["manifestFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "capture hash"):
            validate_evidence(mutated, root=ROOT)

    def test_claim_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["claimBoundary"]["liveAgentBehaviorProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
