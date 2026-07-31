import copy
import json
import unittest

from scripts.build_multidimensional_software_engineering_independent_review_packet import (
    CONTRACT_PATH,
    PACKET_PATH,
    ROOT,
    IndependentReviewPacketError,
    build_packet,
    validate_contract,
)
from scripts.validate_multidimensional_software_engineering_independent_review_packet import (
    validate_packet,
    validate_packet_integrity,
    validate_review_receipt,
)


class MultidimensionalSoftwareEngineeringIndependentReviewPacketTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(
            (ROOT / CONTRACT_PATH).read_text(encoding="utf-8")
        )
        cls.packet = json.loads(
            (ROOT / PACKET_PATH).read_text(encoding="utf-8")
        )

    def _valid_receipt(self) -> dict:
        return {
            "schema": 1,
            "id": "synthetic-review-receipt-for-validator-test-only",
            "packetId": self.packet["id"],
            "packetManifestSha256": self.packet["targetBinding"][
                "manifestSha256"
            ],
            "reviewStatus": "performed",
            "reviewedAt": "2026-07-31T18:00:00+08:00",
            "reviewer": {
                "identity": "synthetic-distinct-reviewer-for-validator-test",
                "kind": "synthetic-test-identity",
                "accountableForReview": True,
            },
            "independence": {
                "processId": "synthetic-distinct-process-for-validator-test",
                "distinctExecutionIdentity": True,
                "sameTaskOrThread": False,
                "priorInvolvementDisclosure": "No prior production involvement declared.",
                "identityEvidence": [
                    "synthetic unit-test evidence only; not a real review receipt"
                ],
                "privateReasoningTransferReceived": False,
                "artifactMutationPerformed": False,
            },
            "axisResults": [
                {
                    "axisId": axis["id"],
                    "outcome": "insufficient-evidence",
                    "summary": "Synthetic shape validation only.",
                    "evidenceRefs": [
                        self.packet["targetBinding"]["files"][0]["path"]
                    ],
                    "limitations": [
                        "This row is not a substantive review conclusion."
                    ],
                }
                for axis in self.contract["reviewAxes"]
            ],
            "findings": [],
            "disagreements": [],
            "correctionsRequired": [],
            "overallOutcome": "insufficient-evidence",
            "limitations": [
                "Synthetic receipt used only to test the deterministic validator."
            ],
            "claimBoundary": {
                "acceptanceAuthorityExercised": False,
                "hardStandardPromoted": False,
                "skillNecessityProved": False,
                "broadPopulationValidityProved": False,
                "independentReviewProvedBeyondDeclaredIdentityEvidence": False,
            },
        }

    def test_checked_in_packet_matches_git_rebuild(self) -> None:
        validate_packet()

    def test_checked_in_packet_has_archive_verifiable_integrity(self) -> None:
        validate_packet_integrity()

    def test_contract_subjects_must_cover_exact_target_set(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["subjectPackages"][0]["paths"].pop()
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "exact target path set",
        ):
            validate_contract(mutated)

    def test_same_task_reread_cannot_be_relabelled_independent(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["producerBoundary"][
            "sameTaskRereadQualifiesAsIndependentReview"
        ] = True
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "independence boundary",
        ):
            validate_contract(mutated)

    def test_review_skill_invocation_cannot_be_relabelled_independent(
        self,
    ) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["producerBoundary"][
            "reviewSkillInvocationAloneQualifiesAsIndependentReview"
        ] = True
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "independence boundary",
        ):
            validate_contract(mutated)

    def test_packet_manifest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.packet)
        mutated["targetBinding"]["manifestSha256"] = "0" * 64
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "packet digest drifted",
        ):
            validate_packet(mutated, check_projections=False)

    def test_packet_cannot_claim_review_performed(self) -> None:
        mutated = copy.deepcopy(self.packet)
        mutated["packetState"]["reviewPerformed"] = True
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "contract projection drifted: packetState",
        ):
            validate_packet(mutated, check_projections=False)

    def test_synthetic_receipt_shape_is_valid(self) -> None:
        validate_review_receipt(self._valid_receipt())

    def test_receipt_reusing_producer_identity_is_rejected(self) -> None:
        mutated = self._valid_receipt()
        mutated["reviewer"]["identity"] = self.contract["producerBoundary"][
            "packetProducerIdentity"
        ]
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "reuses a producer",
        ):
            validate_review_receipt(mutated)

    def test_receipt_reusing_producer_process_is_rejected(self) -> None:
        mutated = self._valid_receipt()
        mutated["independence"]["processId"] = self.contract[
            "producerBoundary"
        ]["packetProducerProcessId"]
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "not distinct",
        ):
            validate_review_receipt(mutated)

    def test_receipt_same_task_declaration_is_rejected(self) -> None:
        mutated = self._valid_receipt()
        mutated["independence"]["sameTaskOrThread"] = True
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "independence declaration",
        ):
            validate_review_receipt(mutated)

    def test_receipt_missing_axis_is_rejected(self) -> None:
        mutated = self._valid_receipt()
        mutated["axisResults"].pop()
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "every axis exactly once",
        ):
            validate_review_receipt(mutated)

    def test_receipt_cannot_hide_disagreement_field(self) -> None:
        mutated = self._valid_receipt()
        del mutated["disagreements"]
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "top-level field set",
        ):
            validate_review_receipt(mutated)

    def test_high_finding_requires_disposition(self) -> None:
        mutated = self._valid_receipt()
        mutated["findings"] = [
            {
                "id": "synthetic-high-finding",
                "axisId": self.contract["reviewAxes"][0]["id"],
                "severity": "high",
                "statement": "Synthetic high finding.",
                "evidenceRefs": [
                    self.packet["targetBinding"]["files"][0]["path"]
                ],
                "disposition": "",
            }
        ]
        with self.assertRaisesRegex(
            IndependentReviewPacketError,
            "lacks disposition",
        ):
            validate_review_receipt(mutated)

    def test_receipt_cannot_exercise_acceptance_or_promotion(self) -> None:
        for key in (
            "acceptanceAuthorityExercised",
            "hardStandardPromoted",
            "skillNecessityProved",
        ):
            with self.subTest(key=key):
                mutated = self._valid_receipt()
                mutated["claimBoundary"][key] = True
                with self.assertRaisesRegex(
                    IndependentReviewPacketError,
                    "exceeded review authority",
                ):
                    validate_review_receipt(mutated)

    def test_builder_reproduces_checked_in_packet(self) -> None:
        self.assertEqual(build_packet(), self.packet)


if __name__ == "__main__":
    unittest.main()
