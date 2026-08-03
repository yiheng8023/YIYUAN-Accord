import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.assess_process_fidelity_raw_event_trace_eligibility import (
    ASSESSMENT_EVIDENCE_PATH,
    SMOKE_EVIDENCE_PATH,
    assess_smoke,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityRawEventTraceEligibilityAssessmentTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.evidence = json.loads(
            (ROOT / ASSESSMENT_EVIDENCE_PATH).read_text(encoding="utf-8")
        )
        self.smoke = json.loads(
            (ROOT / SMOKE_EVIDENCE_PATH).read_text(encoding="utf-8")
        )
        durable = self.smoke["durableRunEvidence"]
        self.raw = json.loads(
            (ROOT / durable["rawReportPath"]).read_text(encoding="utf-8")
        )
        self.packet = json.loads(
            (ROOT / durable["trialPacketPath"]).read_text(encoding="utf-8")
        )

    def test_current_assessment_is_valid(self) -> None:
        validate_evidence(self.evidence, root=ROOT)

    def test_existing_smoke_is_not_process_trace_eligible(self) -> None:
        result = assess_smoke(self.smoke, self.raw, self.packet)
        self.assertFalse(result["eligibleForProcessTraceRepetition"])
        self.assertFalse(result["processHopLedgerPresent"])
        self.assertEqual(
            ["scoped-read-result-to-agent-structured-response"],
            result["opaqueMaterialEdgeIds"],
        )
        self.assertEqual(
            0,
            result["formalProcessCohortStartingValidRepetitionCount"],
        )

    def test_missing_edge_cannot_be_filled_manually(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["assessment"]["manualSupplementationUsed"] = True
        with self.assertRaisesRegex(RuntimeError, "assessment drifted"):
            validate_evidence(mutated, root=ROOT)

    def test_transport_pilot_cannot_be_promoted_to_process_trace(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["decision"]["existingSmokeCountsAsProcessTrace"] = True
        with self.assertRaisesRegex(RuntimeError, "decision"):
            validate_evidence(mutated, root=ROOT)

    def test_formal_cohort_cannot_inherit_the_transport_smoke(self) -> None:
        mutated = copy.deepcopy(self.evidence)
        mutated["decision"]["formalProcessCohortMustStartFromZero"] = False
        with self.assertRaisesRegex(RuntimeError, "decision"):
            validate_evidence(mutated, root=ROOT)

    def test_durable_input_repository_hash_is_required(self) -> None:
        mutated_smoke = copy.deepcopy(self.smoke)
        mutated_smoke["durableRunEvidence"][
            "rawReportRepositoryFileSha256"
        ] = "0" * 64

        def load_with_mutated_smoke(path: Path) -> dict:
            if path == ROOT / SMOKE_EVIDENCE_PATH:
                return mutated_smoke
            return json.loads(path.read_text(encoding="utf-8"))

        with patch(
            "scripts.assess_process_fidelity_raw_event_trace_eligibility._load",
            side_effect=load_with_mutated_smoke,
        ):
            with self.assertRaisesRegex(RuntimeError, "repository input hash"):
                validate_evidence(self.evidence, root=ROOT)

    def test_durable_input_capture_hash_is_still_required(self) -> None:
        mutated_smoke = copy.deepcopy(self.smoke)
        mutated_smoke["durableRunEvidence"]["rawReportFileSha256"] = "0" * 64

        def load_with_mutated_smoke(path: Path) -> dict:
            if path == ROOT / SMOKE_EVIDENCE_PATH:
                return mutated_smoke
            return json.loads(path.read_text(encoding="utf-8"))

        with patch(
            "scripts.assess_process_fidelity_raw_event_trace_eligibility._load",
            side_effect=load_with_mutated_smoke,
        ):
            with self.assertRaisesRegex(RuntimeError, "capture input hash"):
                validate_evidence(self.evidence, root=ROOT)


if __name__ == "__main__":
    unittest.main()
