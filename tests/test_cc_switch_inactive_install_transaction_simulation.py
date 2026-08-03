import json
from pathlib import Path
import unittest

from scripts.simulate_cc_switch_inactive_install_transaction import run_failure_matrix


ROOT = Path(__file__).resolve().parent.parent
DECISION = ROOT / "registry/cc-switch-inactive-install-transaction-simulation-2026-08-03.json"


class CcSwitchInactiveInstallTransactionSimulationTests(unittest.TestCase):
    def test_disposable_home_matrix_fails_closed(self) -> None:
        report = run_failure_matrix()
        self.assertEqual(report["caseCount"], 15)
        self.assertEqual(report["passedCaseCount"], 15)
        self.assertEqual(report["liveManagerInvocations"], 0)
        self.assertEqual(report["candidateExecutions"], 0)
        self.assertTrue(report["allFailureCasesRestoredPreState"])
        self.assertTrue(report["allSuccessRowsDefaultDisabled"])
        self.assertTrue(report["allConsumerRootsUnchanged"])
        self.assertTrue(report["freshRecoveryProcessSimulated"])

    def test_governed_decision_matches_the_executable_matrix(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        report = run_failure_matrix()
        self.assertEqual(decision["matrix"], report)
        self.assertEqual(decision["status"], "verified-zero-live-state-design-only")
        self.assertEqual(
            decision["decision"]["disposition"],
            "upstream-change-preferred-live-install-still-held",
        )
        self.assertFalse(decision["claimBoundary"]["ccSwitchRuntimeBehaviorProved"])
        self.assertFalse(decision["claimBoundary"]["candidateInstallAuthorized"])
        self.assertFalse(decision["claimBoundary"]["thinAdapterJustified"])


if __name__ == "__main__":
    unittest.main()
