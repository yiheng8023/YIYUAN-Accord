import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "registry/skill-portfolio-current-authority.json"


def load(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


class SkillPortfolioCurrentAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_legacy_nineteen_are_deprecated_without_live_consumer_mutation(self) -> None:
        legacy = self.policy["legacyAdaptedRelease"]
        manifest_path = ROOT / legacy["manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        registry = load(legacy["skillRegistry"])["skills"]

        self.assertEqual(self.policy["schema"], 1)
        self.assertIsNone(self.policy["activeRelease"])
        self.assertEqual(legacy["status"], "deprecated-transition-evidence")
        self.assertEqual(legacy["skillCount"], 19)
        self.assertEqual(legacy["fileCount"], 40)
        self.assertEqual(legacy["skillCount"], manifest["skillCount"])
        self.assertEqual(legacy["fileCount"], manifest["fileCount"])
        self.assertEqual(
            legacy["manifestSha256"],
            hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            set(legacy["skillIds"]), {item["id"] for item in registry}
        )
        self.assertEqual(self.policy["activeAdaptedThirdPartyPayloadReleaseCount"], 0)
        self.assertFalse(legacy["routingProjectionCurrentAuthority"])
        self.assertFalse(legacy["consumerMutationAuthorized"])
        self.assertFalse(legacy["sameNameLiveSkillAutoRemovalAuthorized"])
        self.assertTrue(legacy["historicalEvidenceRetained"])

    def test_third_party_payload_policy_is_source_preserving(self) -> None:
        policy = self.policy["thirdPartyPayloadPolicy"]
        self.assertEqual(policy["ownership"], "upstream")
        self.assertEqual(policy["bodyTreatment"], "exact-upstream-unchanged")
        self.assertTrue(policy["modifiedDerivativeRequiresSeparateIdentity"])
        self.assertNotIn("neutralization", policy["allowedHarnessArtifacts"])
        self.assertNotIn("generalization", policy["allowedHarnessArtifacts"])

    def test_current_manager_state_binds_the_restored_inactive_event(self) -> None:
        state = self.policy["currentObservedManagerState"]
        event_path = ROOT / state["event"]
        event = json.loads(event_path.read_text(encoding="utf-8"))

        self.assertEqual(self.policy["asOf"], "2026-08-08")
        self.assertEqual(state["reviewedCandidateCount"], 17)
        self.assertEqual(state["managerInstalledDependencyCompleteCandidateCount"], 16)
        self.assertEqual(state["reviewOnlyCandidates"], ["customer-research"])
        self.assertEqual(set(state["enabledCandidateCountByHost"].values()), {0})
        self.assertEqual(state["consumerProjectionCount"], 0)
        self.assertTrue(state["ordinaryRestartPersistenceObserved"])
        self.assertTrue(state["transientUserEnablementRestoredToInactive"])
        self.assertTrue(
            event["claimBoundary"]["authorizedStableInactiveRestorationProved"]
        )
        for field in (
            "candidateInvocationProved",
            "instructionDeliveryProved",
            "behaviorProved",
            "valueProved",
        ):
            self.assertFalse(state[field])

    def test_current_matt_suite_is_bound_to_exact_recoverable_v123_pin(self) -> None:
        state = self.policy["currentObservedMattSuiteState"]
        event = load(state["event"])

        self.assertEqual(state["sourceRowCount"], 25)
        self.assertEqual(
            state["enabledCountByHost"],
            event["postRestartVerification"]["enabledCountByHost"],
        )
        self.assertTrue(state["singleExactRevisionExplainsLivePayload"])
        self.assertEqual(state["upstreamReleaseTag"], "v1.2.3")
        self.assertEqual(
            state["upstreamReleaseCommit"],
            "6acc160e4e0cd062dbbbd7a1b26ae92855edf07e",
        )
        self.assertTrue(state["databaseSourceMetadataPinnedToExactRelease"])
        self.assertTrue(state["metadataOnlyExactPinReconciliationExecuted"])
        self.assertTrue(state["metadataOnlyExactPinReconciliationRecoverable"])
        self.assertEqual(
            state["metadataOnlyChangedColumns"],
            ["repo_branch", "readme_url", "updated_at"],
        )
        self.assertFalse(state["payloadBytesWrittenByExactPin"])
        self.assertFalse(state["consumerProjectionsWrittenByExactPin"])
        self.assertFalse(state["enabledFlagsWrittenByExactPin"])
        self.assertEqual(state["currentPromotedCount"], 25)
        self.assertEqual(state["currentRecursiveSkillCount"], 35)
        self.assertEqual(
            state["payloadClassificationCounts"],
            {
                "exactRelease": 25,
                "missing": 0,
            },
        )
        self.assertEqual(state["currentPromotedNamesMissingFromManager"], 0)
        self.assertFalse(state["removedUpstreamNameRetainedByManager"])
        reconciliation = load(state["commonRootReconciliationEvent"])
        self.assertEqual(state["directSameNameCommonRootDirectoryCount"], 0)
        self.assertFalse(state["directSameNameCommonRootOwnershipProved"])
        self.assertTrue(state["directSameNameCommonRootListingCollisionProved"])
        self.assertTrue(state["directSameNameCommonRootPayloadLineageProved"])
        self.assertTrue(state["directSameNameCommonRootMutationAuthorized"])
        self.assertTrue(state["commonRootReconciliationExecuted"])
        self.assertTrue(state["commonRootReconciliationRecoverable"])
        self.assertEqual(state["reconciledRetainedManagerSymlinkCount"], 12)
        self.assertEqual(state["reconciledRetiredCommonRootCopyCount"], 1)
        self.assertEqual(
            state["existingManagerSymlinkCanonicalDeduplicationObservedCount"],
            9,
        )
        self.assertEqual(
            state["currentManagerSymlinkCanonicalDeduplicationObservedCount"],
            24,
        )
        self.assertTrue(state["singleCcManagedListingPathAcrossReconciledNamesProved"])
        self.assertTrue(
            reconciliation["claimBoundary"][
                "singleCcManagedListingPathForTheThirteenProved"
            ]
        )
        self.assertFalse(reconciliation["decision"]["mattV122ManagerUpdateExecuted"])
        self.assertFalse(reconciliation["transaction"]["cohortAtomicFilesystemCommitProved"])
        self.assertFalse(state["newWizardAmbientEnablementAllowed"])
        self.assertFalse(state["automaticRefreshAuthorized"])
        self.assertTrue(state["atomicCohortPreviewRequired"])
        self.assertTrue(state["atomicCohortPreviewBuilt"])
        self.assertTrue(state["atomicCohortExecutionAuthorized"])
        self.assertTrue(state["recoverableAdapterCohortUpdateExecuted"])
        self.assertTrue(state["wholeCohortRecoverable"])
        self.assertFalse(
            state["wholeCohortCrossFilesystemDatabaseAtomicCommitProved"]
        )
        self.assertFalse(state["liveRollbackExecuted"])
        self.assertTrue(state["failureInjectionRollbackProved"])
        self.assertTrue(state["explicitSyntheticRollbackProved"])
        self.assertFalse(state["releasedManagerAtomicCohortUpdateProved"])
        self.assertTrue(state["singleManagerRevisionClosureAcrossConsumersProved"])
        self.assertEqual(
            state["singleManagerRevisionClosureScope"],
            "exact-payload-projection-and-no-model-listing-path-only",
        )
        self.assertEqual(state["managerVersionAfterOrdinaryRestart"], "3.19.2")
        self.assertTrue(state["exactPinPersistenceAfterOrdinaryRestartProved"])
        self.assertTrue(state["managerAutoUpdateObservedDuringOrdinaryRestart"])
        self.assertFalse(event["claimBoundary"]["loaderInvocationProved"])
        self.assertFalse(event["claimBoundary"]["behaviorProved"])
        self.assertFalse(event["claimBoundary"]["valueProved"])

    def test_portfolio_curation_and_task_activation_are_separate_modes(self) -> None:
        modes = self.policy["operatingModes"]
        curation = modes["portfolioCuration"]
        activation = modes["taskTimeActivation"]
        self.assertFalse(curation["requiresOneEndUserTask"])
        self.assertEqual(
            set(curation["requiredBindings"]),
            {
                "coverage-objective-or-demand-taxonomy",
                "candidate-and-source-boundary",
                "account-and-data-boundary",
                "inactive-acquisition-isolation",
                "review-and-admission-criteria",
                "authority-boundary",
                "verification-surface",
                "cohort-or-stop-rule",
                "cleanup-and-rollback",
            },
        )
        self.assertIn("discover", curation["allowedActions"])
        self.assertIn("acquire-exact-revision-into-inactive-root", curation["allowedActions"])
        self.assertNotIn("install", curation["allowedActions"])
        self.assertTrue(activation["requiresBoundTaskAndGap"])
        self.assertEqual(activation["defaultState"], "minimal-task-scoped")

    def test_disabled_consumer_projection_observation_stays_read_only_and_bounded(self) -> None:
        state = self.policy["currentDisabledConsumerProjectionObservation"]
        event = load(state["event"])

        self.assertEqual(
            state["hosts"], ["gemini", "grokbuild", "opencode", "hermes"]
        )
        self.assertTrue(state["allRootsAbsent"])
        self.assertTrue(state["allMattFlagsDisabled"])
        self.assertEqual(0, state["mattProjectionCount"])
        self.assertTrue(state["privacyMinimized"])
        self.assertTrue(state["databaseAndRootsReadOnly"])
        for field in (
            "hostInstallationProved",
            "loaderInvocationProved",
            "instructionDeliveryProved",
            "backupRestoreProved",
            "crossDeviceConvergenceProved",
            "behaviorProved",
            "valueProved",
        ):
            self.assertFalse(state[field])
        self.assertEqual(
            "four-disabled-consumer-roots-readonly-observed-absent-zero-matt-projections",
            event["status"],
        )

    def test_decision_surfaces_state_the_new_boundary(self) -> None:
        surfaces = {
            "AGENTS.md": ("portfolio curation", "exact upstream"),
            "README.md": ("deprecated transition evidence", "active adapted third-party payload release: `0`"),
            "docs/strategy/PRODUCT-NORTH-STAR.md": ("portfolio-level curation", "exact upstream"),
            "docs/strategy/RESEARCH-AND-POC-PLAN.md": ("portfolio curation mode", "task-time activation"),
        }
        for relative, phrases in surfaces.items():
            text = (ROOT / relative).read_text(encoding="utf-8").lower()
            for phrase in phrases:
                with self.subTest(relative=relative, phrase=phrase):
                    self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
