from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.evaluate_ai_independent_hard_standard_candidate import (
    GATE_PATH,
    evaluate_candidate,
    validate_gate_record,
    validate_repository_gate,
)


ROOT = Path(__file__).resolve().parent.parent


def complete_synthetic_candidate() -> dict:
    return {
        "id": "synthetic-hard-standard-candidate",
        "candidateClass": "future-hard-standard-candidate",
        "obligation": {
            "statement": "Synthetic bounded obligation for evaluator testing only.",
            "validWithoutAI": True,
            "validWithoutSkills": True,
            "evidenceIds": ["synthetic-obligation-evidence"],
        },
        "accountableOwner": {
            "authorityId": "synthetic-human-or-governed-authority",
            "authorityType": "governed-organization-role",
            "nonAI": True,
            "evidenceIds": ["synthetic-owner-evidence"],
        },
        "executionSurfaces": [
            {
                "id": "synthetic-deterministic-execution",
                "kind": "deterministic-cli",
                "availableWithoutAIOrSkills": True,
                "evidenceIds": ["synthetic-execution-evidence"],
            }
        ],
        "proofSurfaces": [
            {
                "id": "synthetic-deterministic-proof",
                "kind": "deterministic-validator",
                "availableWithoutAIOrSkills": True,
                "evidenceIds": ["synthetic-proof-evidence"],
            }
        ],
        "counterfactualAblation": {
            "removedCapabilities": [
                "AI",
                "model",
                "Skill",
                "Hook",
                "Agent behavior",
            ],
            "obligationPreserved": True,
            "ownerPreserved": True,
            "executionSurfaceIds": ["synthetic-deterministic-execution"],
            "proofSurfaceIds": ["synthetic-deterministic-proof"],
            "evidenceIds": ["synthetic-counterfactual-evidence"],
        },
        "admission": {
            "separateGovernedAdmissionRequired": True,
            "currentStatus": "not-admitted",
        },
    }


class AIIndependentHardStandardBoundaryGateTests(unittest.TestCase):
    def test_repository_gate_contract_is_valid(self) -> None:
        record = validate_repository_gate()

        self.assertEqual("ai-independent-hard-standard-boundary-gate-v1", record["id"])
        self.assertEqual("verified-synthetic-gate-mechanism-only", record["status"])
        self.assertEqual(
            "registry/ai-independent-hard-standard-boundary-gate-2026-08-07.json",
            str(GATE_PATH).replace("\\", "/"),
        )
        self.assertTrue((ROOT / record["documentation"]).is_file())

    def test_gate_declares_the_complete_failure_injection_ledger(self) -> None:
        record = json.loads((ROOT / GATE_PATH).read_text(encoding="utf-8"))

        self.assertEqual(
            [
                "wrong-candidate-class",
                "obligation-statement",
                "obligation-without-ai",
                "obligation-without-skills",
                "obligation-evidence",
                "owner-type",
                "owner-non-ai",
                "owner-evidence",
                "execution-skill-only",
                "execution-evidence",
                "proof-skill-only",
                "proof-evidence",
                "ablation-removal",
                "ablation-obligation",
                "ablation-owner",
                "ablation-execution-reference",
                "ablation-proof-reference",
                "ablation-evidence",
                "separate-admission",
                "current-admitted",
            ],
            record["failureInjectionCaseIds"],
        )

    def test_gate_validator_rejects_mutation_ledger_drift(self) -> None:
        record = json.loads((ROOT / GATE_PATH).read_text(encoding="utf-8"))
        record["failureInjectionCaseIds"].pop()

        with self.assertRaisesRegex(RuntimeError, "mutation ledger"):
            validate_gate_record(record, root=ROOT)

    def test_acceptance_map_verifies_only_the_boundary_mechanism(self) -> None:
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criteria = {row["id"]: row for row in acceptance["acceptanceCriteria"]}
        evidence = {row["id"]: row for row in acceptance["evidence"]}
        evidence_id = "evidence.ai-independent-hard-standard-boundary-gate-2026-08-07"

        criterion = criteria["acceptance.ai-independent-hard-standard-boundary"]
        self.assertEqual("verified", criterion["assessment"])
        self.assertIn(evidence_id, criterion["evidenceIds"])
        self.assertEqual(
            "registry/ai-independent-hard-standard-boundary-gate-2026-08-07.json",
            evidence[evidence_id]["path"],
        )
        self.assertEqual(
            ["acceptance.ai-independent-hard-standard-boundary"],
            evidence[evidence_id]["supports"],
        )

    def test_gate_validator_rejects_acceptance_downgrade(self) -> None:
        record = json.loads((ROOT / GATE_PATH).read_text(encoding="utf-8"))
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criterion = next(
            row
            for row in acceptance["acceptanceCriteria"]
            if row["id"] == "acceptance.ai-independent-hard-standard-boundary"
        )
        criterion["assessment"] = "partial"

        with self.assertRaisesRegex(RuntimeError, "acceptance binding"):
            validate_gate_record(record, acceptance=acceptance, root=ROOT)

    def test_gate_validator_rejects_source_gate_drift(self) -> None:
        record = json.loads((ROOT / GATE_PATH).read_text(encoding="utf-8"))
        rebaseline = json.loads(
            (
                ROOT
                / "registry/human-ai-collaboration-coverage-rebaseline-2026-07-24.json"
            ).read_text(encoding="utf-8")
        )
        gate = next(
            row
            for row in rebaseline["gates"]
            if row["id"] == "gate.ai-independent-hard-standard"
        )
        gate["falsifier"] = "A Skill may be the only proof surface."

        with self.assertRaisesRegex(RuntimeError, "source gate"):
            validate_gate_record(record, rebaseline=rebaseline, root=ROOT)

    def test_gate_validator_rejects_evidence_truth_promotion(self) -> None:
        record = json.loads((ROOT / GATE_PATH).read_text(encoding="utf-8"))
        record["claimBoundary"]["provesEvidenceTruth"] = True

        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_gate_record(record, root=ROOT)

    def test_gate_validator_rejects_public_seam_drift(self) -> None:
        record = json.loads((ROOT / GATE_PATH).read_text(encoding="utf-8"))
        record["publicSeam"]["mode"] = "model-mediated"

        with self.assertRaisesRegex(RuntimeError, "public seam"):
            validate_gate_record(record, root=ROOT)

    def test_complete_fixture_is_boundary_eligible_but_not_admitted(self) -> None:
        result = evaluate_candidate(complete_synthetic_candidate())

        self.assertEqual("boundary-eligible", result["decision"])
        self.assertEqual([], result["blockers"])
        self.assertFalse(result["admissionAuthorized"])
        self.assertEqual("synthetic-gate-mechanism-only", result["claimBoundary"])

    def test_skill_only_execution_surface_fails_closed(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["executionSurfaces"][0]["kind"] = "Skill"

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("no-ai-independent-execution-surface", result["blockers"])
        self.assertFalse(result["admissionAuthorized"])

    def test_model_named_owner_cannot_self_declare_non_ai(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["accountableOwner"]["authorityType"] = "model"

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("accountable-owner-missing", result["blockers"])

    def test_execution_surface_without_evidence_fails_closed(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["executionSurfaces"][0]["evidenceIds"] = []

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("no-ai-independent-execution-surface", result["blockers"])

    def test_proof_surface_without_evidence_fails_closed(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["proofSurfaces"][0]["evidenceIds"] = []

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("no-ai-independent-proof-surface", result["blockers"])

    def test_obligation_without_evidence_fails_closed(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["obligation"]["evidenceIds"] = []

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("obligation-not-ai-independent", result["blockers"])

    def test_owner_without_evidence_fails_closed(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["accountableOwner"]["evidenceIds"] = []

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("accountable-owner-missing", result["blockers"])

    def test_counterfactual_without_evidence_fails_closed(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["counterfactualAblation"]["evidenceIds"] = []

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("counterfactual-evidence-missing", result["blockers"])


if __name__ == "__main__":
    unittest.main()
