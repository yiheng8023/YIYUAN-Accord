from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.validate_mcp_reload_release_version_change_evidence import (
    EVIDENCE_PATH,
    PROGRAM_ACCEPTANCE_PATH,
    PROGRAM_EVIDENCE_ID,
    ROOT,
    load_bound_raw_reports,
    validate_evidence,
    validate_raw_report,
)


class McpReloadReleaseVersionChangeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )
        cls.program_map = json.loads(
            (ROOT / PROGRAM_ACCEPTANCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_version_evidence_passes_with_bounded_native_win(self) -> None:
        validate_evidence(deepcopy(self.document), root=ROOT)
        self.assertEqual(
            "observed-three-repetition-single-host-version-bounded-config-disable-plus-reload-release",
            self.document["status"],
        )
        self.assertTrue(
            self.document["decision"][
                "boundedNativeSameThreadConfigDisablePlusReloadAndReleaseObserved"
            ]
        )
        self.assertFalse(
            self.document["decision"]["selfAuthoredControllerEligible"]
        )

    def test_raw_producer_reload_only_claim_is_explicitly_rejected(self) -> None:
        self.assertEqual(
            {
                "field": "claimBoundary.provesReloadCausedOldRuntimeRelease",
                "recordedValue": True,
                "canonicalDisposition": "rejected-confounded-by-prior-config-disable-no-ablation",
                "rawFilesPreservedUnmodified": True,
                "canonicalAllowedClaim": "release-observed-after-config-disable-plus-reload",
            },
            self.document["rawProducerClaimCorrection"],
        )
        self.assertFalse(
            self.document["claimBoundary"]["reloadAloneCausedReleaseProved"]
        )

    def test_rejects_raw_producer_overclaim_promotion(self) -> None:
        mutated = deepcopy(self.document)
        mutated["rawProducerClaimCorrection"]["canonicalDisposition"] = (
            "accepted-reload-only-causation"
        )
        with self.assertRaisesRegex(RuntimeError, "producer claim correction drifted"):
            validate_evidence(mutated, root=ROOT)
        self.assertTrue(
            all(
                value is False
                for value in self.document["claimBoundary"].values()
            )
        )

    def test_rejects_raw_hash_drift(self) -> None:
        mutated = deepcopy(self.document)
        mutated["formalEvidence"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "hash drifted"):
            validate_evidence(mutated, root=ROOT)

    def test_rejects_official_source_identity_drift(self) -> None:
        mutated = deepcopy(self.document)
        mutated["officialSourceSnapshot"]["releaseCommit"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "official source snapshot"):
            validate_evidence(mutated, root=ROOT)

    def test_rejects_task_end_or_cross_host_promotion(self) -> None:
        for key in ("taskEndImmediateReleaseProved", "crossHostParityProved"):
            mutated = deepcopy(self.document)
            mutated["claimBoundary"][key] = True
            with self.subTest(key=key), self.assertRaisesRegex(
                RuntimeError,
                "claim boundary drifted",
            ):
                validate_evidence(mutated, root=ROOT)

    def test_pid_reuse_does_not_count_as_same_exact_identity(self) -> None:
        raw_reports = load_bound_raw_reports(self.document, root=ROOT)
        summary = validate_raw_report(raw_reports[0], repetition=1)
        self.assertEqual(1, summary["pidReuseDifferentIdentityCount"])
        self.assertTrue(summary["exactBaselineIdentityAbsentByWindowEnd"])
        self.assertTrue(summary["reloadReleaseObserved"])

    def test_rejects_pid_only_release_reasoning(self) -> None:
        raw_reports = load_bound_raw_reports(self.document, root=ROOT)
        raw = deepcopy(raw_reports[0])
        baseline = raw["processObservation"]["baseline"]
        reused = next(
            sample
            for sample in raw["processObservation"]["samples"]
            if sample.get("pid") == baseline["pid"]
            and sample.get("exists") is True
            and sample.get("creationTime100ns")
            != baseline["creationTime100ns"]
        )
        reused["creationTime100ns"] = baseline["creationTime100ns"]
        reused["imagePath"] = baseline["imagePath"]
        reused["parentPid"] = baseline["parentPid"]
        with self.assertRaisesRegex(RuntimeError, "classification drifted"):
            validate_raw_report(raw, repetition=1)

    def test_rejects_missing_program_acceptance_binding(self) -> None:
        program_map = deepcopy(self.program_map)
        acceptance = next(
            item
            for item in program_map["acceptanceCriteria"]
            if item["id"] == "acceptance.dynamic-runtime-control-gap-research"
        )
        acceptance["evidenceIds"].remove(PROGRAM_EVIDENCE_ID)
        with self.assertRaisesRegex(RuntimeError, "acceptance mapping drifted"):
            validate_evidence(
                deepcopy(self.document),
                root=ROOT,
                program_map=program_map,
            )


if __name__ == "__main__":
    unittest.main()
