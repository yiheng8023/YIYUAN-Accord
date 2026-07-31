from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_access_comms_capability_baseline import (
    BASELINE_PATH,
    SCENARIO_MATRIX_PATH,
    validate_baseline,
)


class HumanAiCollaborationAccessCommsCapabilityBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        cls.scenario_matrix = json.loads(
            SCENARIO_MATRIX_PATH.read_text(encoding="utf-8")
        )

    def test_repository_baseline_is_consistent(self) -> None:
        validate_baseline()

    def test_existing_gate_cannot_become_free_form_translation_proof(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["existingZeroModelGate"]["freeFormLanguageCorrectnessProved"] = True
        with self.assertRaisesRegex(RuntimeError, "promoted freeFormLanguageCorrectnessProved"):
            validate_baseline(mutated)

    def test_documents_structural_checks_cannot_become_wcag_engine(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["officialDocumentsObservation"]["fullWcagEngineClaimedBySource"] = True
        with self.assertRaisesRegex(RuntimeError, "Documents boundary was promoted"):
            validate_baseline(mutated)

    def test_static_baseline_cannot_promote_scenario_evidence(self) -> None:
        mutated_matrix = copy.deepcopy(self.scenario_matrix)
        scenario = next(
            item
            for item in mutated_matrix["scenarios"]
            if item["id"] == "GEN-ACCESS-COMMS-01"
        )
        scenario["evidenceState"] = "verified"
        with self.assertRaisesRegex(RuntimeError, "promoted scenario evidence"):
            validate_baseline(self.baseline, scenario_matrix=mutated_matrix)

    def test_external_service_discovery_cannot_become_execution(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        azure = next(
            item
            for item in mutated["targetedExternalDiscovery"]
            if item["id"] == "external.microsoft-azure-ai-translation-text-py"
        )
        azure["installedOrExecuted"] = True
        with self.assertRaisesRegex(RuntimeError, "Azure translation discovery boundary drifted"):
            validate_baseline(mutated)

    def test_candidate_or_self_authored_expansion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["comparisonDecision"]["selfAuthoredSkillNeededNow"] = True
        with self.assertRaisesRegex(RuntimeError, "expanded scope"):
            validate_baseline(mutated)

    def test_stable_neutrality_cannot_be_rewritten_as_a_change(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["neutralityAndHumanAuthority"]["projectNeutralityChanged"] = True
        with self.assertRaisesRegex(RuntimeError, "misrepresented as a change"):
            validate_baseline(mutated)

    def test_release_authority_cannot_be_promoted_to_agent(self) -> None:
        mutated = copy.deepcopy(self.baseline)
        mutated["neutralityAndHumanAuthority"]["legallyConsequentialReleaseOwner"] = "agent"
        with self.assertRaisesRegex(RuntimeError, "human authority drifted"):
            validate_baseline(mutated)


if __name__ == "__main__":
    unittest.main()
