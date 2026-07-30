from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_tdd_exact_candidate_admission_gap_audit import (
    AUDIT_PATH,
    ROOT,
    validate_audit,
)


def load() -> dict:
    return json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))


class HumanAiCollaborationTddExactCandidateAdmissionGapAuditTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_audit_is_valid(self) -> None:
        validate_audit(self.document)

    def test_rejects_candidate_admission_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][0]["assessment"] = "admitted"
        with self.assertRaisesRegex(RuntimeError, "candidate assessment"):
            validate_audit(document)

    def test_rejects_historical_matt_release_as_exact_admission(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][0]["exactCandidateAdmissionPresent"] = True
        with self.assertRaisesRegex(RuntimeError, "Matt boundary"):
            validate_audit(document)

    def test_rejects_removed_superpowers_deletion_conflict(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][1]["blockers"] = [
            blocker
            for blocker in document["candidates"][1]["blockers"]
            if blocker["id"] != "superpowers-delete-existing-code-conflict"
        ]
        with self.assertRaisesRegex(RuntimeError, "blockers id set"):
            validate_audit(document)

    def test_rejects_live_execution_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["candidateTaskTurnStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_audit(document)

    def test_rejects_empty_remaining_gate(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][1]["minimumRemainingGates"] = []
        with self.assertRaisesRegex(RuntimeError, "remaining gate"):
            validate_audit(document)

    def test_rejects_candidate_value_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["candidateValue"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_audit(document)

    def test_rejects_relative_candidate_conclusion(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][0]["passes"][0][
            "finding"
        ] += " This candidate is closer to the gate."
        with self.assertRaisesRegex(RuntimeError, "relative candidate"):
            validate_audit(document)

    def test_rejects_relative_candidate_conclusion_variants(self) -> None:
        variants = (
            "This candidate is nearer to admission.",
            "Matt is ahead of Superpowers.",
            "This candidate is better.",
            "Superpowers is more-ready.",
            "This candidate is preferred.",
            "Matt is less blocked than Superpowers.",
            "Matt has fewer remaining gates than Superpowers.",
            "Matt should go first.",
            "Matt is superior to Superpowers.",
            "Superpowers is the weaker candidate.",
        )
        for variant in variants:
            with self.subTest(variant=variant):
                document = load()
                document["candidates"][0]["passes"][0][
                    "finding"
                ] += f" {variant}"
                with self.assertRaisesRegex(
                    RuntimeError,
                    "relative candidate",
                ):
                    validate_audit(document)

    def test_rejects_relative_conclusions_across_narrative_surfaces(
        self,
    ) -> None:
        mutations = (
            lambda document: document.__setitem__(
                "purpose",
                document["purpose"]
                + " Matt is less blocked than Superpowers.",
            ),
            lambda document: document["candidates"][0]["passes"][0].__setitem__(
                "finding",
                document["candidates"][0]["passes"][0]["finding"]
                + " This candidate is preferred.",
            ),
            lambda document: document["candidates"][0]["passes"][0][
                "evidence"
            ].__setitem__(0, "Matt should go first."),
            lambda document: document["candidates"][0][
                "minimumRemainingGates"
            ].__setitem__(0, "Matt is better positioned for admission."),
        )
        for mutate in mutations:
            with self.subTest(surface=mutate):
                document = load()
                mutate(document)
                with self.assertRaisesRegex(
                    RuntimeError,
                    "relative candidate",
                ):
                    validate_audit(document)

    def test_allows_absolute_facts_and_negative_claim_boundaries(self) -> None:
        controls = (
            "No preference or superiority is established.",
            "Both candidates remain blocked.",
            "Matt has five blockers.",
            "Superpowers has a deletion conflict.",
        )
        for control in controls:
            with self.subTest(control=control):
                document = load()
                document["candidates"][0]["passes"][0][
                    "finding"
                ] += f" {control}"
                validate_audit(document)

    def test_rejects_partial_id_substitution(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][0]["partials"][0][
            "id"
        ] = "matt-unsigned-commit"
        with self.assertRaisesRegex(RuntimeError, "partials id set"):
            validate_audit(document)

    def test_rejects_missing_item_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidates"][1]["partials"][3]["evidence"] = []
        with self.assertRaisesRegex(RuntimeError, "evidence item"):
            validate_audit(document)

    def test_rejects_preflight_snapshot_digest_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceGovernancePreflightSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "immutable input binding"):
            validate_audit(document)

    def test_rejects_candidate_identity_envelope_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateIdentityEnvelopeSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "immutable input binding"):
            validate_audit(document)


if __name__ == "__main__":
    unittest.main()
