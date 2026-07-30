from __future__ import annotations

import copy
import unittest

from scripts.evaluate_human_ai_collaboration_self_authored_control_chain_factorial_evidence import (
    build_synthetic_evidence,
    evaluate_factorial_run,
    validate_adapter_contract,
)


class SelfAuthoredControlChainFactorialEvidenceTests(unittest.TestCase):
    def evaluate(
        self,
        scenario: str = "INT-AMB-01",
        cell: str = "CHAIN-HARD-HOOK-OFF",
        *,
        mutate=None,
    ) -> dict:
        raw, evidence = build_synthetic_evidence(scenario, cell)
        if mutate:
            mutate(evidence)
        return evaluate_factorial_run(raw, evidence)

    def test_all_scenario_cell_contracts_are_valid_but_not_live(self) -> None:
        validate_adapter_contract()

    def test_hard_only_rejects_exposed_skill(self) -> None:
        result = self.evaluate(
            mutate=lambda evidence: evidence["skillExposureManifest"][0].update(
                {"state": "present"}
            )
        )
        self.assertIn(
            "hard-fail-hard-only-exposure-confounded", result["failureCodes"]
        )

    def test_exact_chain_requires_scenario_relevant_loader(self) -> None:
        result = self.evaluate(
            cell="CHAIN-EXACT-HOOK-OFF",
            mutate=lambda evidence: evidence.update({"skillLoaderEvents": []}),
        )
        self.assertIn("fail-scenario-relevant-loader-event", result["failureCodes"])

    def test_wrong_skill_pin_fails_closed(self) -> None:
        result = self.evaluate(
            cell="CHAIN-EXACT-HOOK-OFF",
            mutate=lambda evidence: evidence["skillExposureManifest"][0].update(
                {"sha256": "0" * 64}
            ),
        )
        self.assertIn("fail-skill-exposure-shape", result["failureCodes"])

    def test_hook_off_rejects_output(self) -> None:
        def mutate(evidence: dict) -> None:
            hook = evidence["hookEvidence"]
            hook["stdoutUtf8"] = "x"
            hook["stdoutBytes"] = 1
            import hashlib

            hook["stdoutSha256"] = hashlib.sha256(b"x").hexdigest()

        result = self.evaluate(mutate=mutate)
        self.assertIn("hard-fail-hook-off-isolation", result["failureCodes"])

    def test_hook_auto_requires_invocation(self) -> None:
        result = self.evaluate(
            cell="CHAIN-HARD-HOOK-AUTO",
            mutate=lambda evidence: evidence["hookEvidence"].update(
                {"invoked": False}
            ),
        )
        self.assertIn("fail-hook-auto-invocation", result["failureCodes"])

    def test_silent_model_substitution_fails_closed(self) -> None:
        result = self.evaluate(
            mutate=lambda evidence: evidence["modelRoute"].update(
                {"actualModel": "gpt-5.6"}
            )
        )
        self.assertIn("hard-fail-model-route", result["failureCodes"])

    def test_shared_hard_standard_credit_fails_closed(self) -> None:
        result = self.evaluate(
            mutate=lambda evidence: evidence.update(
                {"sharedHardStandardsCreditedAsTreatmentValue": True}
            )
        )
        self.assertIn(
            "hard-fail-shared-standard-boundary", result["failureCodes"]
        )

    def test_repository_drift_fails_closed(self) -> None:
        def mutate(evidence: dict) -> None:
            after = copy.deepcopy(evidence["repositoryTruthAfter"])
            after["status"] = ["?? unexpected"]
            evidence["repositoryTruthAfter"] = after

        result = self.evaluate(mutate=mutate)
        self.assertIn("hard-fail-repository-drift", result["failureCodes"])

    def test_synthetic_evidence_never_counts_as_live(self) -> None:
        result = self.evaluate(cell="CHAIN-EXACT-HOOK-AUTO")
        self.assertEqual(
            "evidence-contract-ready-not-live-host-proved", result["status"]
        )
        self.assertFalse(result["countsAsLiveHostProof"])
        self.assertFalse(result["countsAsWeakAgentAcceptance"])


if __name__ == "__main__":
    unittest.main()
