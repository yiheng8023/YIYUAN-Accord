from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_loss_longhorizon_harness_interface_gap_mapping import (
    ACCEPTANCE_PATH,
    EVIDENCE_ID,
    EXPECTED_COVERAGE_COUNTS,
    EXPECTED_DISPOSITION_COUNTS,
    EXPECTED_ROWS,
    EXTERNAL_ASSESSMENT_PATH,
    RECORD_PATH,
    SUPPORTED_ACCEPTANCE_ASSESSMENTS,
    validate_mapping_record,
    validate_repository_mapping,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ProcessLossLongHorizonHarnessInterfaceGapMappingTests(unittest.TestCase):
    def test_repository_mapping_is_valid(self) -> None:
        record = validate_repository_mapping(ROOT)

        self.assertEqual(
            "verified-zero-model-interface-gap-mapping-no-execution",
            record["status"],
        )
        self.assertTrue(record["decision"]["mappingCompleteForFrozenRevision"])
        self.assertTrue(record["decision"]["stopSelfAuthoringEquivalentCoordinator"])

    def test_interface_rows_and_counts_are_exact(self) -> None:
        record = load(RECORD_PATH)
        rows = {item["interfaceId"]: item for item in record["interfaceRows"]}

        self.assertEqual(set(EXPECTED_ROWS), set(rows))
        for interface_id, (coverage, disposition) in EXPECTED_ROWS.items():
            self.assertEqual(coverage, rows[interface_id]["coverage"])
            self.assertEqual(disposition, rows[interface_id]["disposition"])
        self.assertEqual(
            EXPECTED_COVERAGE_COUNTS,
            record["mappingSummary"]["coverageCounts"],
        )
        self.assertEqual(
            EXPECTED_DISPOSITION_COUNTS,
            record["mappingSummary"]["dispositionCounts"],
        )

    def test_mapping_remains_zero_model_and_non_activating(self) -> None:
        record = load(RECORD_PATH)
        contract = record["mappingContract"]
        authority = record["authorityBoundary"]
        claims = record["claimBoundary"]

        self.assertEqual(0, contract["modelCallCount"])
        self.assertFalse(contract["thirdPartyCodeAcquired"])
        self.assertFalse(contract["thirdPartyCodeExecuted"])
        self.assertFalse(authority["installAuthorized"])
        self.assertFalse(authority["executeAuthorized"])
        self.assertFalse(authority["adapterImplementationAuthorized"])
        self.assertFalse(claims["provesInterfaceCompatibility"])
        self.assertFalse(claims["provesSafeExecution"])
        self.assertFalse(claims["provesResidualGap"])

    def test_acceptance_evidence_is_bound_without_promotion(self) -> None:
        acceptance = load(ACCEPTANCE_PATH)
        criteria = {
            item["id"]: item for item in acceptance["acceptanceCriteria"]
        }
        evidence = {item["id"]: item for item in acceptance["evidence"]}

        for acceptance_id, assessment in SUPPORTED_ACCEPTANCE_ASSESSMENTS.items():
            self.assertEqual(assessment, criteria[acceptance_id]["assessment"])
            self.assertIn(EVIDENCE_ID, criteria[acceptance_id]["evidenceIds"])
        self.assertEqual(
            set(SUPPORTED_ACCEPTANCE_ASSESSMENTS),
            set(evidence[EVIDENCE_ID]["supports"]),
        )

    def test_missing_interface_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["interfaceRows"].pop()

        with self.assertRaisesRegex(RuntimeError, "row identity"):
            validate_mapping_record(
                record,
                external_assessment=load(EXTERNAL_ASSESSMENT_PATH),
                acceptance=load(ACCEPTANCE_PATH),
                root=ROOT,
            )

    def test_permission_coverage_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        item = next(
            row
            for row in record["interfaceRows"]
            if row["interfaceId"] == "host-owned-permission-enforcement"
        )
        item["coverage"] = "present"

        with self.assertRaisesRegex(RuntimeError, "interface row"):
            validate_mapping_record(
                record,
                external_assessment=load(EXTERNAL_ASSESSMENT_PATH),
                acceptance=load(ACCEPTANCE_PATH),
                root=ROOT,
            )

    def test_adapter_authority_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["authorityBoundary"]["adapterImplementationAuthorized"] = True

        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_mapping_record(
                record,
                external_assessment=load(EXTERNAL_ASSESSMENT_PATH),
                acceptance=load(ACCEPTANCE_PATH),
                root=ROOT,
            )

    def test_external_revision_drift_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        external = load(EXTERNAL_ASSESSMENT_PATH)
        external["sourceSnapshot"]["repository"]["revision"] = "0" * 40

        with self.assertRaisesRegex(RuntimeError, "external source identity"):
            validate_mapping_record(
                record,
                external_assessment=external,
                acceptance=load(ACCEPTANCE_PATH),
                root=ROOT,
            )

    def test_acceptance_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        acceptance = copy.deepcopy(load(ACCEPTANCE_PATH))
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["assessment"] = "verified"

        with self.assertRaisesRegex(RuntimeError, "acceptance boundary"):
            validate_mapping_record(
                record,
                external_assessment=load(EXTERNAL_ASSESSMENT_PATH),
                acceptance=acceptance,
                root=ROOT,
            )


if __name__ == "__main__":
    unittest.main()
