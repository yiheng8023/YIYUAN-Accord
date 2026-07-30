from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.validate_mcp_reload_release_attribution_evidence import (
    EVIDENCE_PATH,
    PROGRAM_ACCEPTANCE_PATH,
    PROGRAM_EVIDENCE_ID,
    ROOT,
    validate_evidence,
)


class McpReloadReleaseAttributionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )
        cls.program_map = json.loads(
            (ROOT / PROGRAM_ACCEPTANCE_PATH).read_text(encoding="utf-8")
        )

    def test_evidence_passes(self) -> None:
        validate_evidence(deepcopy(self.document), root=ROOT)

    def test_rejects_raw_hash_drift(self) -> None:
        document = deepcopy(self.document)
        document["formalEvidence"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "hash drifted"):
            validate_evidence(document, root=ROOT)

    def test_rejects_promoted_runtime_control_claim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["taskEndImmediateReleaseProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            validate_evidence(document, root=ROOT)

    def test_rejects_calibration_in_formal_set(self) -> None:
        document = deepcopy(self.document)
        document["formalEvidence"][0] = deepcopy(
            document["excludedCalibrationRuns"][0]
        )
        with self.assertRaisesRegex(RuntimeError, "Formal reload-release evidence set"):
            validate_evidence(document, root=ROOT)

    def test_rejects_reload_release_promotion(self) -> None:
        document = deepcopy(self.document)
        document["decision"][
            "reloadCausedPriorRuntimeReleaseInTestedWindow"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "decision drifted"):
            validate_evidence(document, root=ROOT)

    def test_audit_readme_preserves_authoritative_evidence(self) -> None:
        text = (
            ROOT
            / "audits"
            / "mcp-reload-release-attribution-0.145.0-2026-07-27"
            / "README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("authoritative host evidence", text)
        self.assertIn("separate cleanup decision", text)

    def test_rejects_missing_direct_program_acceptance_binding(self) -> None:
        program_map = deepcopy(self.program_map)
        acceptance = next(
            item
            for item in program_map["acceptanceCriteria"]
            if item["id"] == "acceptance.dynamic-runtime-control-gap-research"
        )
        acceptance["evidenceIds"].remove(PROGRAM_EVIDENCE_ID)
        with self.assertRaisesRegex(
            RuntimeError,
            "acceptance mapping drifted",
        ):
            validate_evidence(
                deepcopy(self.document),
                root=ROOT,
                program_map=program_map,
            )

    def test_rejects_broadened_program_evidence_support(self) -> None:
        program_map = deepcopy(self.program_map)
        evidence = next(
            item
            for item in program_map["evidence"]
            if item["id"] == PROGRAM_EVIDENCE_ID
        )
        evidence["supports"].append("acceptance.residual-gap-proof")
        with self.assertRaisesRegex(
            RuntimeError,
            "program evidence mapping drifted",
        ):
            validate_evidence(
                deepcopy(self.document),
                root=ROOT,
                program_map=program_map,
            )

    def test_rejects_unauthorized_cross_criterion_reference(self) -> None:
        program_map = deepcopy(self.program_map)
        acceptance = next(
            item
            for item in program_map["acceptanceCriteria"]
            if item["id"] == "acceptance.residual-gap-proof"
        )
        acceptance["evidenceIds"].append(PROGRAM_EVIDENCE_ID)
        with self.assertRaisesRegex(
            RuntimeError,
            "unauthorized acceptance reference",
        ):
            validate_evidence(
                deepcopy(self.document),
                root=ROOT,
                program_map=program_map,
            )


if __name__ == "__main__":
    unittest.main()
