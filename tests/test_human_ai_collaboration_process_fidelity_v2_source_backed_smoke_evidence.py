import copy
import json
from pathlib import Path
import unittest

from scripts.validate_human_ai_collaboration_process_fidelity_v2_source_backed_smoke_evidence import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityV2SourceBackedSmokeEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document, root=ROOT)

    def test_single_repetition_cannot_be_promoted_to_completed_arm(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["decision"]["countsAsCompletedInformationArm"] = True
        with self.assertRaisesRegex(RuntimeError, "decision"):
            validate_evidence(mutated, root=ROOT)

    def test_transport_repetition_cannot_be_promoted_to_process_trace(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["decision"]["countsAsProcessTraceValidRepetition"] = True
        with self.assertRaisesRegex(RuntimeError, "decision"):
            validate_evidence(mutated, root=ROOT)

    def test_at_dispatch_protocol_identity_is_required(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["durableRunEvidence"]["atDispatchProtocolFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "at-dispatch"):
            validate_evidence(mutated, root=ROOT)

    def test_durable_raw_report_hash_is_required(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["durableRunEvidence"]["rawReportFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "durable file hash"):
            validate_evidence(mutated, root=ROOT)

    def test_general_filesystem_authority_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["inputAndReadBoundary"][
            "generalFilesystemAuthorityGranted"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "scoped-read"):
            validate_evidence(mutated, root=ROOT)

    def test_private_oracle_leakage_scan_cannot_be_overclaimed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["inputAndReadBoundary"]["privateOracleLeakageScanComplete"] = True
        with self.assertRaisesRegex(RuntimeError, "scoped-read"):
            validate_evidence(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
