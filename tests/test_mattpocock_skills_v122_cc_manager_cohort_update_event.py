from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVENT = (
    ROOT
    / "registry/mattpocock-skills-v1.2.2-cc-manager-cohort-update-event-2026-08-06.json"
)


class MattPocockSkillsV122CcManagerCohortUpdateEventTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = json.loads(EVENT.read_text(encoding="utf-8"))
        self.report_path = ROOT / self.event["verification"]["noModelReport"]
        self.report = json.loads(self.report_path.read_text(encoding="utf-8"))

    def test_event_binds_exact_no_model_report(self) -> None:
        verification = self.event["verification"]
        self.assertEqual(
            verification["noModelReportFileSha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            verification["noModelReportSha256"], self.report["reportSha256"]
        )
        self.assertEqual("pass", self.report["status"])
        self.assertEqual(
            ["initialize", "initialized", "skills/list"],
            self.report["requestBoundary"]["sentMethods"],
        )
        self.assertEqual(0, self.report["requestBoundary"]["threadStartCount"])
        self.assertEqual(0, self.report["requestBoundary"]["turnStartCount"])
        self.assertEqual(0, self.report["requestBoundary"]["modelRequestCount"])
        self.assertTrue(
            self.report["mutationBoundary"]["allObservedSurfacesStable"]
        )

    def test_exact_twenty_five_and_default_disabled_wizard_are_preserved(self) -> None:
        transaction = self.event["transaction"]
        self.assertEqual(25, len(transaction["targetNames"]))
        self.assertEqual(25, len(set(transaction["targetNames"])))
        self.assertEqual(["writing-great-skills"], transaction["removedNames"])
        self.assertEqual(25, transaction["exactReleaseDirectoryCount"])
        self.assertEqual(
            {"agents": 24, "claude": 24, "codex": 24},
            transaction["enabledProjectionCountByRoot"],
        )
        self.assertFalse(transaction["wizardProjectionPresent"])
        self.assertEqual({False}, set(transaction["wizardEnabledByHost"].values()))
        self.assertTrue(
            self.report["cohortExposure"]["allExpectedNamesListedOnce"]
        )
        self.assertTrue(self.report["cohortExposure"]["allPathsCanonicalCcRoot"])
        self.assertEqual(
            {"wizard": 0, "writing-great-skills": 0},
            self.report["cohortExposure"]["absentNameRowCounts"],
        )

    def test_recoverability_is_not_mislabeled_atomicity_or_live_rollback(self) -> None:
        transaction = self.event["transaction"]
        self.assertTrue(transaction["wholeCohortRecoverable"])
        self.assertTrue(transaction["rollbackMechanismUnitTested"])
        self.assertFalse(transaction["crossFilesystemDatabaseAtomicCommitProved"])
        self.assertFalse(transaction["transientPartialStateImpossibleProved"])
        self.assertFalse(transaction["liveRollbackExecuted"])
        self.assertFalse(transaction["rawDatabaseCopied"])
        self.assertEqual(0, self.event["source"]["thirdPartyScriptsExecuted"])

    def test_auto_update_and_semantic_claim_limits_remain_explicit(self) -> None:
        runtime = self.event["managerRuntime"]
        self.assertEqual("3.19.1", runtime["versionBeforeOrdinaryRestart"])
        self.assertEqual("3.19.2", runtime["versionAfterOrdinaryRestart"])
        self.assertTrue(runtime["autoUpdateObservedDuringOrdinaryRestart"])
        self.assertFalse(runtime["manualManagerUpgradePerformedByHarness"])
        claims = self.event["claimBoundary"]
        self.assertFalse(claims["skillLoaderInvocationProved"])
        self.assertFalse(claims["instructionDeliveryProved"])
        self.assertFalse(claims["skillBehaviorProved"])
        self.assertFalse(claims["skillValueProved"])
        self.assertFalse(claims["crossHostExposureProved"])
        self.assertFalse(claims["modelDispatched"])


if __name__ == "__main__":
    unittest.main()
