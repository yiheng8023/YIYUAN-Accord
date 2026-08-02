import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = (
    ROOT
    / "registry/cc-switch-3.19.1-default-disabled-install-adjudication-2026-08-03.json"
)


class CcSwitch3191DefaultDisabledInstallAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_installed_binary_and_official_source_are_bound(self) -> None:
        manager = self.decision["manager"]
        source = self.decision["source"]
        self.assertEqual(manager["version"], "3.19.1")
        self.assertEqual(
            manager["binarySha256"],
            "5a027ca870be30d75ae00ac81a821ad7421c5419dd2b1a9959f9900f8dc9f0ed",
        )
        self.assertEqual(source["repository"], "farion1231/cc-switch")
        self.assertEqual(source["tag"], "v3.19.1")
        self.assertEqual(source["tagObject"], "7da48a05f51aa8099bc9dbdfae20d45a33fdc39a")
        self.assertEqual(source["commit"], "28529620f438b2ed25c812f6364825d846a4a9d6")
        self.assertEqual(source["tree"], "d615f1b31ab77880b20d52c9b66e3261174968a8")
        upstream = self.decision["currentUpstreamObservation"]
        self.assertEqual(upstream["commit"], "8383076791f2c0d34f3a249f43f95e8a3906c0a7")
        self.assertEqual(upstream["latestEnumeratedReleaseTag"], "v3.19.1")
        self.assertFalse(upstream["nativeInactiveRepositoryInstallFound"])
        self.assertEqual(len(upstream["relevantFilesByteEqualToV3191"]), 4)

    def test_repository_install_requires_and_enables_one_current_app(self) -> None:
        install = self.decision["repositoryInstallPath"]
        self.assertEqual(install["command"], "install_skill_unified")
        self.assertTrue(install["requiresCurrentApp"])
        self.assertEqual(install["initialAppsConstructor"], "SkillApps::only(current_app)")
        self.assertTrue(install["writesDatabaseBeforeProjection"])
        self.assertTrue(install["projectsToCurrentAppBeforeReturn"])
        self.assertFalse(install["supportsEmptyInitialApps"])

    def test_separate_disable_is_not_an_atomic_default_disabled_install(self) -> None:
        sequence = self.decision["installThenDisableComposition"]
        self.assertEqual(sequence["disableCommand"], "toggle_skill_app")
        self.assertTrue(sequence["transientHostProjectionExists"])
        self.assertTrue(sequence["crashWindowExists"])
        self.assertFalse(sequence["atomicAtCandidateBoundary"])
        self.assertFalse(sequence["eligibleWithoutTransientActivationAuthority"])

    def test_import_can_record_empty_apps_but_is_not_repository_acquisition(self) -> None:
        alternative = self.decision["inactiveImportAlternative"]
        self.assertEqual(alternative["command"], "import_skills_from_apps")
        self.assertTrue(alternative["acceptsExplicitEmptyApps"])
        self.assertTrue(alternative["requiresBytesAlreadyInLiveSearchRoots"])
        self.assertFalse(alternative["acquiresPinnedRepositoryPayload"])
        self.assertFalse(alternative["atomicSourceBackedInstall"])

    def test_manager_reuse_remains_but_candidate_install_stays_held(self) -> None:
        decision = self.decision["decision"]
        self.assertEqual(decision["managerDisposition"], "retain-cc-switch")
        self.assertEqual(
            decision["candidateInstallDisposition"],
            "hold-until-native-or-thin-adapter-default-disabled-transaction-is-proved",
        )
        self.assertFalse(decision["parallelManagerAuthorized"])
        self.assertFalse(decision["liveCandidateMutationExecuted"])

    def test_claim_and_cleanup_boundaries_are_explicit(self) -> None:
        claims = self.decision["claimBoundary"]
        self.assertTrue(claims["officialSourceStaticSemanticsProved"])
        self.assertFalse(claims["defaultDisabledRepositoryInstallProved"])
        self.assertFalse(claims["rollbackExecuted"])
        self.assertFalse(claims["candidateInstalled"])
        self.assertFalse(claims["hostExposureProved"])
        self.assertTrue(self.decision["cleanup"]["sourceReviewRootRemoved"])
        self.assertTrue(self.decision["cleanup"]["repositoryTmpRemovedAfter"])


if __name__ == "__main__":
    unittest.main()
