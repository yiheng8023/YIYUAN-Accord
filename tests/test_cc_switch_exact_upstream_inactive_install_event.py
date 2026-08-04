import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVENT = ROOT / "registry/cc-switch-exact-upstream-sixteen-sequential-inactive-install-event-2026-08-04.json"
ADJUDICATION = ROOT / "registry/cc-switch-3.19.1-exact-zip-sequential-inactive-install-adjudication-2026-08-04.json"


class CcSwitchExactUpstreamInactiveInstallEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(EVENT.read_text(encoding="utf-8"))
        self.adjudication = json.loads(ADJUDICATION.read_text(encoding="utf-8"))

    def test_event_binds_released_manager_and_raw_git_identity(self) -> None:
        manager = self.event["manager"]
        transport = self.event["transport"]
        self.assertEqual(manager["version"], "3.19.1")
        self.assertEqual(
            manager["commit"], "28529620f438b2ed25c812f6364825d846a4a9d6"
        )
        self.assertEqual(transport["identityAuthority"], "raw Git blob objects at the reviewed revision")
        self.assertTrue(transport["fetchAndVerifyBeforeManagerWrite"])
        self.assertFalse(transport["thirdPartyBodyRewritten"])

    def test_sixteen_unique_candidates_have_exact_identity_and_expected_actions(self) -> None:
        candidates = self.event["transaction"]["candidates"]
        self.assertEqual(len(candidates), 16)
        self.assertEqual(len({item["name"] for item in candidates}), 16)
        self.assertEqual(
            sum(item["action"] == "corrected-nonraw-archive-materialization" for item in candidates),
            9,
        )
        self.assertEqual(sum(item["action"] == "installed-new" for item in candidates), 7)
        for item in candidates:
            self.assertRegex(item["revision"], r"^[0-9a-f]{40}$")
            for field in (
                "zipSha256",
                "entrypointSha256",
                "rawPayloadTreeSha256",
                "rawSourceTreeHash",
            ):
                self.assertRegex(item[field], r"^[0-9a-f]{64}$")
            self.assertTrue(item["allAppsDisabled"])
            self.assertEqual(item["consumerProjectionCount"], 0)

    def test_stopped_snapshot_and_ordinary_restart_preserve_inactive_state(self) -> None:
        transaction = self.event["transaction"]
        verification = self.event["verification"]
        self.assertEqual(transaction["prestate"]["rowCount"], 42)
        self.assertEqual(transaction["poststate"]["rowCount"], 58)
        self.assertEqual(transaction["poststate"]["candidateRows"], 16)
        self.assertFalse(transaction["atomicDefaultDisabledInstall"])
        self.assertTrue(verification["allSixAppFlagsDisabledForAllCandidates"])
        self.assertEqual(verification["consumerProjectionCount"], 0)
        self.assertTrue(verification["statePersistedAfterOrdinaryRestart"])
        self.assertTrue(verification["customerResearchAbsent"])

    def test_cleanup_and_claim_boundaries_remain_narrow(self) -> None:
        cleanup = self.event["cleanup"]
        claims = self.event["claimBoundary"]
        self.assertTrue(cleanup["correctionBackupsRemovedThroughManagerApi"])
        self.assertTrue(cleanup["temporaryProcessRootRemovedAfterEvidenceFreeze"])
        self.assertTrue(cleanup["transientGeminiRootRemovedIfEmptyAndCreatedByTransaction"])
        self.assertTrue(claims["exactUpstreamManagerInstallationProved"])
        self.assertTrue(claims["stableAllAppsDisabledStateProved"])
        for field in (
            "atomicCohortInstallProved",
            "rollbackExecuted",
            "candidateEnabled",
            "candidateExposedToRunningHost",
            "candidateInvoked",
            "instructionDeliveryProved",
            "behaviorProved",
            "valueProved",
            "crossHostPortabilityProved",
        ):
            self.assertFalse(claims[field])

    def test_adjudication_links_the_live_event_without_requiring_pr_6086(self) -> None:
        decision = self.adjudication["decision"]
        claims = self.adjudication["claimBoundary"]
        self.assertFalse(decision["pr6086IsRequiredToUseManager"])
        self.assertTrue(decision["sequentialInactiveCohortInstalled"])
        self.assertEqual(decision["liveEvent"], EVENT.relative_to(ROOT).as_posix())
        self.assertTrue(claims["releasedExactZipPayloadRuntimeInstalled"])
        self.assertTrue(claims["candidateInstalled"])
        self.assertFalse(claims["candidateEnabled"])


if __name__ == "__main__":
    unittest.main()
