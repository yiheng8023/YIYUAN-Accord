from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest

from scripts.build_human_ai_collaboration_learning_noru_independent_review_packet import (
    CONTRACT_PATH,
    PACKET_PATH,
    ROOT,
    build_packet,
    validate_contract,
)
from scripts.validate_human_ai_collaboration_learning_noru_independent_review_packet import (
    LEARNING_NORU_INDEPENDENT_REVIEW_REQUIRED_FILES,
    validate_packet,
    validate_review_receipt,
)


class HumanAiCollaborationLearningNoruIndependentReviewPacketTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.contract = json.loads(
            (ROOT / CONTRACT_PATH).read_text(encoding="utf-8")
        )

    def test_contract_prepares_review_without_claiming_it_occurred(self) -> None:
        validate_contract(self.contract)
        self.assertEqual(
            "prepared-not-reviewed-live-trial-blocked",
            self.contract["status"],
        )
        self.assertFalse(self.contract["packetState"]["reviewPerformed"])
        self.assertFalse(
            self.contract["claimBoundary"]["provesIndependentReviewPerformed"]
        )
        self.assertTrue(
            all(value is False for value in self.contract["authorityBoundary"].values())
        )

    def test_contract_rejects_an_incomplete_authority_boundary(self) -> None:
        mutated = copy.deepcopy(self.contract)
        del mutated["authorityBoundary"]["participantContactOrTrialAuthorized"]
        with self.assertRaisesRegex(
            RuntimeError,
            "authority boundary drifted",
        ):
            validate_contract(mutated)

    def test_contract_rejects_an_incomplete_claim_boundary(self) -> None:
        mutated = copy.deepcopy(self.contract)
        del mutated["claimBoundary"]["provesCandidateValue"]
        with self.assertRaisesRegex(
            RuntimeError,
            "claim boundary drifted",
        ):
            validate_contract(mutated)

    def test_contract_rejects_a_receipt_that_could_authorize_live_trial(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["receiptContract"]["liveTrialMayBeAuthorizedByReceipt"] = True
        with self.assertRaisesRegex(
            RuntimeError,
            "receipt contract drifted",
        ):
            validate_contract(mutated)

    def test_contract_rejects_an_incomplete_producer_identity_boundary(self) -> None:
        mutated = copy.deepcopy(self.contract)
        del mutated["producerBoundary"]["packetProducerProcessId"]
        with self.assertRaisesRegex(
            RuntimeError,
            "producer boundary drifted",
        ):
            validate_contract(mutated)

    def test_contract_rejects_a_duplicated_review_axis(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["reviewAxes"].append(copy.deepcopy(mutated["reviewAxes"][0]))
        with self.assertRaisesRegex(
            RuntimeError,
            "exactly once",
        ):
            validate_contract(mutated)

    def test_builder_freezes_exact_git_objects_without_review_execution(self) -> None:
        packet = build_packet(self.contract)
        target = packet["targetBinding"]
        self.assertEqual(self.contract["targetRevision"], target["revision"])
        self.assertEqual(10, target["pathCount"])
        self.assertEqual(
            self.contract["targetPaths"],
            [row["path"] for row in target["files"]],
        )
        self.assertFalse(packet["packetState"]["reviewPerformed"])
        self.assertFalse(packet["reproduction"]["networkRequired"])
        self.assertFalse(packet["reproduction"]["modelRequired"])

    def test_checked_in_packet_matches_the_exact_rebuild(self) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        validate_packet(packet)
        self.assertEqual(build_packet(self.contract), packet)

    def test_builder_check_cli_rebuilds_the_checked_in_packet(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    ROOT
                    / "scripts/build_human_ai_collaboration_learning_noru_independent_review_packet.py"
                ),
                "--check",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("Noru independent-review packet is current.", completed.stdout)

    def _valid_receipt(self, packet: dict) -> dict:
        return {
            "schema": 1,
            "id": "synthetic-review-receipt",
            "packetId": packet["id"],
            "packetManifestSha256": packet["targetBinding"]["manifestSha256"],
            "packetSha256": packet["packetSha256"],
            "reviewStatus": "performed",
            "reviewedAt": "2026-08-01T12:00:00+08:00",
            "reviewer": {
                "identity": "synthetic-distinct-reviewer",
                "kind": "test-only-accountable-human",
                "accountableForReview": True,
            },
            "independence": {
                "processId": "synthetic-distinct-review-process",
                "distinctExecutionIdentity": True,
                "sameTaskOrThread": False,
                "priorInvolvementDisclosure": "No prior involvement.",
                "identityEvidence": ["test-only-declaration"],
                "privateReasoningTransferReceived": False,
                "artifactMutationPerformed": False,
            },
            "axisResults": [
                {
                    "axisId": axis["id"],
                    "outcome": "insufficient-evidence",
                    "summary": "Synthetic shape-only result.",
                    "evidenceRefs": [self.contract["targetPaths"][0]],
                    "limitations": ["No real review occurred."],
                }
                for axis in self.contract["reviewAxes"]
            ],
            "findings": [],
            "disagreements": [],
            "correctionsRequired": [],
            "overallOutcome": "insufficient-evidence",
            "limitations": ["Synthetic validator fixture only."],
            "claimBoundary": {
                "acceptanceAuthorityExercised": False,
                "hardStandardPromoted": False,
                "skillNecessityProved": False,
                "liveTrialAuthorized": False,
                "broadPopulationValidityProved": False,
                "independentReviewProvedBeyondDeclaredIdentityEvidence": False,
            },
        }

    def test_distinct_reviewer_receipt_shape_is_valid_but_authorizes_nothing(
        self,
    ) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        validate_review_receipt(
            self._valid_receipt(packet),
            packet=packet,
            contract=self.contract,
        )

    def test_review_receipt_cannot_authorize_a_live_trial(self) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        receipt = self._valid_receipt(packet)
        receipt["claimBoundary"]["liveTrialAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "exceeded review authority"):
            validate_review_receipt(
                receipt,
                packet=packet,
                contract=self.contract,
            )

    def test_review_receipt_must_bind_the_exact_packet_digest(self) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        receipt = self._valid_receipt(packet)
        receipt["packetSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "packet binding drifted"):
            validate_review_receipt(
                receipt,
                packet=packet,
                contract=self.contract,
            )

    def test_review_receipt_cannot_cancel_a_rejected_axis(self) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        receipt = self._valid_receipt(packet)
        receipt["axisResults"][0]["outcome"] = "reject"
        receipt["overallOutcome"] = "accept-bounded"
        with self.assertRaisesRegex(RuntimeError, "cancels a weaker axis"):
            validate_review_receipt(
                receipt,
                packet=packet,
                contract=self.contract,
            )

    def test_review_receipt_rejects_evidence_outside_the_frozen_manifest(
        self,
    ) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        receipt = self._valid_receipt(packet)
        receipt["axisResults"][0]["evidenceRefs"] = ["not/a/frozen/path.json"]
        with self.assertRaisesRegex(RuntimeError, "outside the packet manifest"):
            validate_review_receipt(
                receipt,
                packet=packet,
                contract=self.contract,
            )

    def test_review_findings_and_disagreements_use_frozen_evidence(self) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        cases = (
            (
                "findings",
                [
                    {
                        "id": "finding-1",
                        "axisId": self.contract["reviewAxes"][0]["id"],
                        "severity": "low",
                        "statement": "Synthetic finding.",
                        "evidenceRefs": ["not/a/frozen/path.json"],
                        "disposition": "Synthetic disposition.",
                    }
                ],
            ),
            (
                "disagreements",
                [
                    {
                        "id": "disagreement-1",
                        "statement": "Synthetic disagreement.",
                        "evidenceRefs": ["not/a/frozen/path.json"],
                        "disposition": "Synthetic disposition.",
                    }
                ],
            ),
        )
        for field, value in cases:
            with self.subTest(field=field):
                receipt = self._valid_receipt(packet)
                receipt[field] = value
                with self.assertRaises(RuntimeError):
                    validate_review_receipt(
                        receipt,
                        packet=packet,
                        contract=self.contract,
                    )

    def test_review_receipt_cannot_accept_bounded_with_a_critical_finding(
        self,
    ) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        receipt = self._valid_receipt(packet)
        receipt["axisResults"] = [
            {**result, "outcome": "accept-bounded"}
            for result in receipt["axisResults"]
        ]
        receipt["overallOutcome"] = "accept-bounded"
        receipt["findings"] = [
            {
                "id": "critical-1",
                "axisId": receipt["axisResults"][0]["axisId"],
                "severity": "critical",
                "statement": "Synthetic unresolved critical finding.",
                "evidenceRefs": [self.contract["targetPaths"][0]],
                "disposition": "todo",
            }
        ]
        with self.assertRaisesRegex(RuntimeError, "critical finding"):
            validate_review_receipt(
                receipt,
                packet=packet,
                contract=self.contract,
            )

    def test_accept_with_corrections_requires_a_frozen_correction_record(
        self,
    ) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        receipt = self._valid_receipt(packet)
        receipt["axisResults"] = [
            {
                **result,
                "outcome": (
                    "accept-with-corrections"
                    if index == 0
                    else "accept-bounded"
                ),
            }
            for index, result in enumerate(receipt["axisResults"])
        ]
        receipt["overallOutcome"] = "accept-with-corrections"
        with self.assertRaisesRegex(RuntimeError, "correction record"):
            validate_review_receipt(
                receipt,
                packet=packet,
                contract=self.contract,
            )

        receipt["correctionsRequired"] = [
            {
                "id": "correction-1",
                "axisId": receipt["axisResults"][0]["axisId"],
                "statement": "Synthetic required correction.",
                "evidenceRefs": [self.contract["targetPaths"][0]],
            }
        ]
        validate_review_receipt(
            receipt,
            packet=packet,
            contract=self.contract,
        )

    def test_each_correction_axis_requires_its_own_record(self) -> None:
        packet = json.loads((ROOT / PACKET_PATH).read_text(encoding="utf-8"))
        receipt = self._valid_receipt(packet)
        receipt["axisResults"] = [
            {
                **result,
                "outcome": (
                    "accept-with-corrections"
                    if index == 0
                    else "accept-bounded"
                ),
            }
            for index, result in enumerate(receipt["axisResults"])
        ]
        receipt["overallOutcome"] = "accept-with-corrections"
        receipt["correctionsRequired"] = [
            {
                "id": "correction-for-wrong-axis",
                "axisId": receipt["axisResults"][1]["axisId"],
                "statement": "Synthetic mismatched correction.",
                "evidenceRefs": [self.contract["targetPaths"][0]],
            }
        ]
        with self.assertRaisesRegex(RuntimeError, "does not cover each axis"):
            validate_review_receipt(
                receipt,
                packet=packet,
                contract=self.contract,
            )

    def test_program_projection_keeps_both_acceptances_partial(self) -> None:
        plan = json.loads(
            (ROOT / "registry/curation-program-plan.json").read_text(
                encoding="utf-8"
            )
        )
        initiatives = {row["id"]: row for row in plan["currentInitiatives"]}
        for initiative_id in {
            "initiative.capability-survey-gap-proof",
            "initiative.human-ai-collaboration-coverage-rebaseline",
        }:
            with self.subTest(initiative=initiative_id):
                initiative = initiatives[initiative_id]
                self.assertEqual(
                    CONTRACT_PATH.as_posix(),
                    initiative["currentLearningIndependentReviewReadinessContract"],
                )
                self.assertEqual(
                    PACKET_PATH.as_posix(),
                    initiative["currentLearningIndependentReviewPacket"],
                )
                self.assertEqual(
                    "prepared-not-reviewed-live-trial-blocked",
                    initiative["currentLearningIndependentReviewState"],
                )

        program = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(
                encoding="utf-8"
            )
        )
        evidence_id = (
            "evidence.human-ai-collaboration-learning-noru-independent-review-"
            "readiness-2026-08-01"
        )
        criteria = {row["id"]: row for row in program["acceptanceCriteria"]}
        expected_acceptances = {
            "acceptance.solution-neutral-collaboration-rebaseline",
            "acceptance.residual-gap-proof",
        }
        for acceptance_id in expected_acceptances:
            with self.subTest(acceptance=acceptance_id):
                self.assertEqual("partial", criteria[acceptance_id]["assessment"])
                self.assertIn(evidence_id, criteria[acceptance_id]["evidenceIds"])
        evidence = {row["id"]: row for row in program["evidence"]}[evidence_id]
        self.assertEqual(PACKET_PATH.as_posix(), evidence["path"])
        self.assertEqual(expected_acceptances, set(evidence["supports"]))

    def test_validator_exports_the_stable_verify_integration_surface(self) -> None:
        self.assertEqual(
            (
                CONTRACT_PATH.as_posix(),
                PACKET_PATH.as_posix(),
                "docs/strategy/HUMAN-AI-COLLABORATION-LEARNING-NORU-"
                "INDEPENDENT-REVIEW-READINESS-2026-08-01.md",
                "scripts/build_human_ai_collaboration_learning_noru_"
                "independent_review_packet.py",
                "scripts/validate_human_ai_collaboration_learning_noru_"
                "independent_review_packet.py",
                "tests/test_human_ai_collaboration_learning_noru_independent_"
                "review_packet.py",
            ),
            LEARNING_NORU_INDEPENDENT_REVIEW_REQUIRED_FILES,
        )


if __name__ == "__main__":
    unittest.main()
