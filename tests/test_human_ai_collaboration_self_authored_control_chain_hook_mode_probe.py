from __future__ import annotations

import unittest

from scripts.probe_human_ai_collaboration_self_authored_control_chain_hook_modes import (
    build_report,
)


class SelfAuthoredControlChainHookModeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_report()

    def test_current_probe_classifies_absent_hook_without_crashing(self) -> None:
        self.assertEqual(
            "preflight-unavailable-current-hook-assets-absent",
            self.report["status"],
        )
        self.assertTrue(self.report["decision"]["currentProbeCompleted"])
        self.assertFalse(self.report["decision"]["hookAssetsAvailable"])
        self.assertFalse(
            self.report["decision"]["isolatedHookModePreflightPassed"]
        )
        self.assertEqual(0, self.report["execution"]["modelOrAgentCalls"])
        self.assertFalse(
            self.report["execution"][
                "liveUserHookConfigurationMutationAttempted"
            ]
        )

    def test_absent_hook_runs_no_scenarios_or_handler(self) -> None:
        self.assertEqual([], self.report["observations"])
        self.assertEqual(0, self.report["execution"]["scenarioCount"])
        self.assertEqual(0, self.report["execution"]["modeCount"])
        self.assertIsNone(
            self.report["execution"]["handlerInvocationMechanism"]
        )

    def test_missing_assets_are_explicit(self) -> None:
        self.assertIn("handler", self.report["missingAssets"])
        self.assertFalse(self.report["identity"]["handler"]["exists"])

    def test_no_failure_fallback_is_fabricated(self) -> None:
        self.assertIsNone(self.report["failureFallback"])

    def test_absence_does_not_authorize_reinstallation_or_model_run(self) -> None:
        decision = self.report["decision"]
        self.assertFalse(decision["hookReinstallationAuthorized"])
        self.assertFalse(decision["liveWeakModelRunAuthorized"])
        self.assertFalse(decision["historicalDatedPreflightInvalidated"])


if __name__ == "__main__":
    unittest.main()
