from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_program_final_closeout_readiness_reconciliation import (
    RECORD_PATH,
    ROOT,
    validate_reconciliation,
)


class ProgramFinalCloseoutReadinessReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / RECORD_PATH).read_text(encoding="utf-8")
        )

    def test_current_reconciliation_is_valid(self) -> None:
        validate_reconciliation(self.document, root=ROOT)

    def test_reconciliation_binds_repository_authored_gap_fill_gate(self) -> None:
        self.assertEqual(
            "registry/repository-authored-gap-fill-gate-2026-08-06.json",
            self.document["sourceBindings"]["repositoryAuthoredGapFillGate"],
        )

    def test_reconciliation_binds_ai_independent_hard_standard_gate(self) -> None:
        self.assertEqual(
            "registry/ai-independent-hard-standard-boundary-gate-2026-08-07.json",
            self.document["sourceBindings"]["aiIndependentHardStandardBoundaryGate"],
        )

    def test_reconciliation_binds_standard_revalidation_cascade_poc(self) -> None:
        self.assertEqual(
            "registry/standard-revalidation-cascade-poc-2026-08-07.json",
            self.document["sourceBindings"]["standardRevalidationCascadePoc"],
        )

    def test_reconciliation_binds_codex_consumer_skill_mapping_snapshot(self) -> None:
        self.assertEqual(
            "registry/codex-consumer-skill-mapping-snapshot-2026-08-07.json",
            self.document["sourceBindings"]["codexConsumerSkillMappingSnapshot"],
        )

    def test_reconciliation_binds_claude_consumer_skill_projection_snapshot(self) -> None:
        self.assertEqual(
            "registry/claude-consumer-skill-projection-snapshot-2026-08-07.json",
            self.document["sourceBindings"]["claudeConsumerSkillProjectionSnapshot"],
        )

    def test_reconciliation_binds_claude_plugin_inventory_preflight(self) -> None:
        self.assertEqual(
            "registry/claude-plugin-skill-root-readonly-inventory-preflight-2026-08-07.json",
            self.document["sourceBindings"]["claudePluginSkillRootInventoryPreflight"],
        )

    def test_rejects_acceptance_count_upgrade(self) -> None:
        document = copy.deepcopy(self.document)
        document["acceptanceSnapshot"]["verified"] = 61
        with self.assertRaisesRegex(RuntimeError, "snapshot"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_omitted_open_criterion(self) -> None:
        document = copy.deepcopy(self.document)
        document["openCriteria"].pop()
        with self.assertRaisesRegex(RuntimeError, "open-criteria"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_single_gate_closeout_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["closeoutDecision"][
            "exactLoaderDecisionAloneCanCloseProgram"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_goal_status_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["goalStatusMutationAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_reconciliation(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
