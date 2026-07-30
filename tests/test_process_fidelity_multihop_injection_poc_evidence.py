import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_fidelity_multihop_injection_poc_evidence import (
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = (
    ROOT
    / "registry"
    / "process-fidelity-multihop-injection-poc-"
    "evidence-2026-07-26.json"
)


class ProcessFidelityMultihopInjectionPocEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.evidence, root=ROOT)

    def test_live_agent_claim_cannot_be_promoted(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["claimBoundary"]["liveAgentBehaviorProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(mutated, root=ROOT)

    def test_source_hash_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["sourceArtifacts"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source bytes"):
            validate_evidence(mutated, root=ROOT)

    def test_supported_conclusion_cannot_bypass_claim_boundary(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["supportedConclusions"] = ["live Agent behavior is proven"]
        with self.assertRaisesRegex(RuntimeError, "conclusion boundary"):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
