import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
OBSERVATION = (
    ROOT
    / "registry/cc-switch-sixteen-codex-claude-enablement-observation-2026-08-05.json"
)
INSTALL_EVENT = (
    ROOT
    / "registry/cc-switch-exact-upstream-sixteen-sequential-inactive-install-event-2026-08-04.json"
)


class CcSwitchSixteenDualHostEnablementObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.observation = json.loads(OBSERVATION.read_text(encoding="utf-8"))
        self.install_event = json.loads(INSTALL_EVENT.read_text(encoding="utf-8"))

    def test_event_reuses_the_exact_installed_candidate_set(self) -> None:
        expected = {
            item["name"]
            for item in self.install_event["transaction"]["candidates"]
        }
        self.assertEqual(set(self.observation["candidateNames"]), expected)
        self.assertEqual(len(expected), 16)
        authority = self.observation["authority"]
        self.assertTrue(authority["userSelectedEnablementReported"])
        self.assertTrue(authority["userAuthorizedDisableIfNegativeImpact"])
        self.assertFalse(authority["harnessPerformedEnablement"])
        self.assertTrue(authority["harnessPerformedAuthorizedDisablement"])

    def test_transient_manager_flags_and_projections_are_host_specific(self) -> None:
        before = self.observation["transientPreObservation"]
        self.assertEqual(before["enabledCandidateCounts"]["codex"], 16)
        self.assertEqual(before["enabledCandidateCounts"]["claude"], 16)
        for host in ("gemini", "opencode", "hermes", "grokbuild"):
            self.assertEqual(before["enabledCandidateCounts"][host], 0)
        self.assertEqual(before["consumerProjectionCounts"]["codex"], 16)
        self.assertEqual(before["consumerProjectionCounts"]["claude"], 16)
        self.assertTrue(before["allObservedProjectionsWereManagerSymlinks"])
        self.assertTrue(before["customerResearchAbsent"])

    def test_no_model_probe_records_transient_exposure_without_overclaim(self) -> None:
        probe = self.observation["transientCodexNoModelExposureObservation"]
        self.assertEqual(probe["hostVersion"], "0.146.0")
        self.assertEqual(probe["sessionCount"], 2)
        self.assertEqual(probe["threadStartCount"], 0)
        self.assertEqual(probe["turnStartCount"], 0)
        self.assertEqual(probe["modelRequestCount"], 0)
        self.assertEqual(probe["candidateCountWithPluginsDisabled"], 16)
        self.assertEqual(probe["candidateCountWithRuntimeDefaults"], 16)
        self.assertTrue(probe["allCandidatesReportedEnabledUserScope"])
        self.assertTrue(probe["configurationHashStable"])
        self.assertTrue(probe["repositoryStateStable"])
        self.assertTrue(probe["probeProcessesReleased"])

    def test_authorized_restoration_keeps_payloads_and_returns_to_zero_projection(self) -> None:
        transaction = self.observation["restorationTransaction"]
        after = self.observation["restoredPostObservation"]
        self.assertFalse(transaction["directDatabaseWrite"])
        self.assertFalse(transaction["skillPayloadDeleted"])
        self.assertFalse(transaction["candidateRowsDeleted"])
        self.assertEqual(transaction["requestedToggleCount"], 32)
        self.assertEqual(transaction["successfulToggleCount"], 32)
        self.assertEqual(transaction["failedToggleCount"], 0)
        self.assertTrue(transaction["rollbackOnFailureImplemented"])
        self.assertFalse(transaction["rollbackExecuted"])
        self.assertTrue(transaction["ordinaryManagerRestartPerformed"])
        self.assertTrue(transaction["temporaryDebugPortClosed"])

        self.assertEqual(after["managerSsotCandidateCount"], 16)
        self.assertEqual(after["databaseCandidateRowCount"], 16)
        self.assertTrue(after["allSixAppFlagsDisabledForAllCandidates"])
        self.assertEqual(set(after["consumerProjectionCounts"].values()), {0})
        self.assertEqual(after["codexCandidateCountWithPluginsDisabled"], 0)
        self.assertEqual(after["codexCandidateCountWithRuntimeDefaults"], 0)
        self.assertTrue(after["customerResearchAbsent"])

    def test_real_task_intake_stays_private_and_opens_no_candidate_arm(self) -> None:
        intake = self.observation["naturalisticTaskIntake"]
        self.assertEqual(intake["observedTaskCount"], 2)
        self.assertFalse(intake["threadLocatorsPersisted"])
        self.assertFalse(intake["privateArtifactsPersisted"])
        self.assertEqual(intake["candidateRelevantGapCount"], 0)
        self.assertFalse(intake["candidateArmOpened"])
        self.assertEqual(
            set(intake["boundedGapClasses"]),
            {
                "human-domain-input-or-judgment-gap",
                "current-capability-sufficient-with-separate-source-access-or-provenance-gap",
            },
        )
        text = OBSERVATION.read_text(encoding="utf-8")
        self.assertNotIn("codex://threads/", text)
        self.assertNotIn("C:\\\\Projects\\\\mqbz-autocad", text)

    def test_claims_and_next_gate_remain_narrow(self) -> None:
        claims = self.observation["claimBoundary"]
        self.assertTrue(claims["transientManagerEnablementProved"])
        self.assertTrue(claims["transientCodexSkillsListExposureProved"])
        self.assertTrue(claims["authorizedStableInactiveRestorationProved"])
        for field in (
            "claudeHostExposureProved",
            "candidateInvoked",
            "instructionDeliveryProved",
            "behaviorProved",
            "valueProved",
            "crossHostPortabilityProved",
            "oneCandidateAttributionProved",
        ):
            self.assertFalse(claims[field])

        implication = self.observation["experimentImplication"]
        self.assertEqual(
            implication["currentNormalUserEnvironment"],
            "sixteen-candidates-manager-installed-and-inactive",
        )
        self.assertEqual(
            implication["futureFormalComparisonIsolation"],
            "process-scoped-or-disposable-runtime",
        )
        self.assertFalse(implication["globalBulkEnablementDefault"])
        self.assertFalse(implication["modelDispatchAuthorized"])
        self.assertEqual(
            implication["nextGate"],
            "one real task with a candidate-relevant current-capability gap",
        )

    def test_cleanup_is_explicit_and_recoverable(self) -> None:
        cleanup = self.observation["cleanup"]
        self.assertTrue(cleanup["temporaryDebugSurfaceClosed"])
        self.assertTrue(cleanup["ordinaryManagerProcessRestored"])
        self.assertTrue(cleanup["probeAppServerProcessesReleased"])
        self.assertEqual(
            cleanup["prestateDatabaseBackupDisposition"],
            "sent-to-Windows-Recycle-Bin-after-poststate-verification",
        )
        self.assertTrue(cleanup["temporaryRollbackRootAbsent"])


if __name__ == "__main__":
    unittest.main()
