import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_human_ai_collaboration_process_fidelity_v2_source_backed_smoke_evidence import (
    EVIDENCE_PATH,
    validate_evidence,
)
from scripts.repository_text_identity import repository_text_bytes


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityV2SourceBackedSmokeEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document, root=ROOT)

    def _materialize_checkout(self, root: Path, *, crlf_json: bool) -> None:
        durable = self.document["durableRunEvidence"]
        paths = [
            durable["rawReportPath"],
            durable["trialPacketPath"],
            durable["buildManifestPath"],
            durable["publicSourceBundlePath"],
            self.document["documentation"],
        ]
        for relative in paths:
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            data = source.read_bytes()
            if crlf_json and source.suffix == ".json":
                data = repository_text_bytes(source).replace(b"\n", b"\r\n")
            target.write_bytes(data)

    def test_deterministic_crlf_checkout_projection_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._materialize_checkout(root, crlf_json=True)
            validate_evidence(self.document, root=root)

    def test_mixed_line_endings_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._materialize_checkout(root, crlf_json=True)
            raw_path = root / self.document["durableRunEvidence"]["rawReportPath"]
            data = raw_path.read_bytes()
            raw_path.write_bytes(data.replace(b"\r\n", b"\n", 1))

            with self.assertRaisesRegex(RuntimeError, "deterministic LF or CRLF"):
                validate_evidence(self.document, root=root)

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

    def test_durable_raw_report_repository_hash_is_required(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["durableRunEvidence"]["rawReportRepositoryFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "durable file hash"):
            validate_evidence(mutated, root=ROOT)

    def test_durable_raw_report_capture_hash_is_still_required(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["durableRunEvidence"]["rawReportFileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "capture file hash"):
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
