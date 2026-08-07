from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_loss_longhorizon_safe_adapter_upstream_design import (
    ACCEPTANCE_PATH,
    ADAPTER_IDS,
    EVIDENCE_ID,
    FORBIDDEN,
    PHASES,
    RECORD_PATH,
    UPSTREAM_IDS,
    validate_record,
    validate_repository_design,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class LongHorizonSafeAdapterUpstreamDesignTests(unittest.TestCase):
    def test_repository_design_is_valid(self) -> None:
        self.assertEqual(
            "owner-authorized-design-complete-no-implementation-or-upstream-write",
            validate_repository_design(ROOT)["status"],
        )

    def test_responsibility_sets_and_phase_gates_are_exact(self) -> None:
        record = load(RECORD_PATH)
        self.assertEqual(UPSTREAM_IDS, {item["id"] for item in record["upstreamChangeCandidates"]})
        self.assertEqual(ADAPTER_IDS, {item["id"] for item in record["thinAdapterResponsibilities"]})
        self.assertEqual(FORBIDDEN, set(record["forbiddenAdapterResponsibilities"]))
        self.assertEqual(
            PHASES,
            {
                item["id"]: (item["status"], item["requiresRealTask"], item["allowedNow"])
                for item in record["phaseGates"]
            },
        )

    def test_direct_adoption_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["decision"]["directAdoption"] = "allowed"
        with self.assertRaisesRegex(RuntimeError, "design decision"):
            validate_record(record, acceptance=load(ACCEPTANCE_PATH), root=ROOT)

    def test_equivalent_coordinator_scope_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["forbiddenAdapterResponsibilities"].remove("reimplement-manage-execute-audit-loop")
        with self.assertRaisesRegex(RuntimeError, "adapter non-goal"):
            validate_record(record, acceptance=load(ACCEPTANCE_PATH), root=ROOT)

    def test_real_task_is_not_required_for_design(self) -> None:
        record = load(RECORD_PATH)
        record["phaseGates"][0]["requiresRealTask"] = True
        with self.assertRaisesRegex(RuntimeError, "phase gate"):
            validate_record(record, acceptance=load(ACCEPTANCE_PATH), root=ROOT)

    def test_implementation_authority_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["authorityBoundary"]["adapterImplementationAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_record(record, acceptance=load(ACCEPTANCE_PATH), root=ROOT)

    def test_behavior_claim_promotion_fails_closed(self) -> None:
        record = load(RECORD_PATH)
        record["claimBoundary"]["provesBehavior"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_record(record, acceptance=load(ACCEPTANCE_PATH), root=ROOT)

    def test_acceptance_registration_is_required(self) -> None:
        acceptance = copy.deepcopy(load(ACCEPTANCE_PATH))
        acceptance["evidence"] = [item for item in acceptance["evidence"] if item["id"] != EVIDENCE_ID]
        with self.assertRaisesRegex(RuntimeError, "acceptance evidence registration"):
            validate_record(load(RECORD_PATH), acceptance=acceptance, root=ROOT)

    def test_goal_prompt_projection_is_required(self) -> None:
        record = load(RECORD_PATH)
        prompt_path = ROOT / "docs/operations/CURRENT-GOAL-MODE-PROMPT.md"
        original = prompt_path.read_text(encoding="utf-8")
        self.assertIn(RECORD_PATH.as_posix(), original)


if __name__ == "__main__":
    unittest.main()
