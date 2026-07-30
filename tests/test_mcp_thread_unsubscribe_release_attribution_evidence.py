from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from scripts.validate_mcp_thread_unsubscribe_release_attribution_evidence import (
    DOC_PATH,
    EVIDENCE_PATH,
    PROGRAM_ACCEPTANCE_PATH,
    PROGRAM_EVIDENCE_ID,
    ROOT,
    validate_evidence,
)


class McpThreadUnsubscribeReleaseAttributionEvidenceTests(
    unittest.TestCase
):
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

    def test_rejects_claim_promotion(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["unsubscribeIsTaskEndProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            validate_evidence(document, root=ROOT)

    def test_rejects_release_promotion(self) -> None:
        document = deepcopy(self.document)
        document["decision"][
            "unsubscribeImmediateReleaseInTestedWindowObserved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "decision drifted"):
            validate_evidence(document, root=ROOT)

    def test_rejects_calibration_in_formal_set(self) -> None:
        document = deepcopy(self.document)
        document["formalEvidence"][0] = deepcopy(
            document["excludedCalibrationRuns"][0]
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "Formal thread-unsubscribe evidence set",
        ):
            validate_evidence(document, root=ROOT)

    def test_rejects_mixed_pair_summary(self) -> None:
        document = deepcopy(self.document)
        document["formalEvidence"][1][
            "pairClassification"
        ] = "unsubscribe-release-associated-bounded"
        with self.assertRaisesRegex(RuntimeError, "paired classification"):
            validate_evidence(document, root=ROOT)

    def test_rejects_missing_direct_program_acceptance_binding(self) -> None:
        program_map = deepcopy(self.program_map)
        acceptance = next(
            item
            for item in program_map["acceptanceCriteria"]
            if item["id"]
            == "acceptance.dynamic-runtime-control-gap-research"
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

    def test_rejects_missing_document_boundary(self) -> None:
        document_path = (ROOT / DOC_PATH).resolve()
        original = type(document_path).read_text

        def altered_read_text(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path.resolve() == document_path:
                return value.replace(
                    "This is not a synonym for task end.",
                    "Subscription status is recorded.",
                )
            return value

        with patch.object(
            type(document_path),
            "read_text",
            altered_read_text,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "documentation boundary missing",
            ):
                validate_evidence(deepcopy(self.document), root=ROOT)


if __name__ == "__main__":
    unittest.main()
