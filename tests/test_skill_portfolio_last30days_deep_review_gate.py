import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = ROOT / "registry/skill-portfolio-last30days-deep-review-gate-2026-08-03.json"


class SkillPortfolioLast30DaysDeepReviewGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_source_and_license_are_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "mvanhorn/last30days-skill")
        self.assertEqual(source["commit"], "52f53312ff2f272e16bbc1785e1c04f9d9c19b31")
        self.assertEqual(source["tree"], "efedede937eb771d144f4416e8a8da108a9c6e8e")
        self.assertEqual(source["license"], "MIT")
        self.assertEqual(source["licenseSha256"], "31803213a789825dc419de43542381e1d570b4408cf2bcf2e8a9947a6d3fd2ab")
        self.assertFalse(source["thirdPartyCodeExecuted"])

    def test_one_skill_identity_is_not_low_lifecycle_cost(self) -> None:
        surface = self.decision["payloadSurface"]
        self.assertEqual(surface["declaredSkillCount"], 1)
        self.assertEqual(surface["skillDirectoryFileCount"], 123)
        self.assertEqual(surface["skillDirectoryScriptLikeFileCount"], 110)
        self.assertEqual(surface["skillMdBytes"], 222241)
        self.assertGreater(len(surface["optionalCredentialNames"]), 10)
        self.assertEqual(surface["pyprojectRuntimeDependencies"], [])
        self.assertGreater(len(surface["operationalDependencies"]), 0)

    def test_positive_controls_do_not_erase_broader_authority_surface(self) -> None:
        controls = self.decision["positiveControls"]
        self.assertIn("preflight permission summary", controls)
        self.assertIn("browser-cookie opt-in", controls)
        self.assertIn("explicit publish opt-in", controls)
        boundaries = self.decision["authorityAndDataBoundaries"]
        self.assertTrue(boundaries["mayReadBrowserCookiesWithConsent"])
        self.assertTrue(boundaries["mayWritePersistentResearchState"])
        self.assertTrue(boundaries["mayUsePaidExternalProviders"])
        self.assertTrue(boundaries["mayPublishPublicHtmlWithOptIn"])

    def test_source_is_held_for_deep_review_not_rejected_as_failed(self) -> None:
        self.assertEqual(
            self.decision["disposition"],
            "hold-deep-executable-external-data-and-host-lifecycle-review",
        )
        self.assertFalse(self.decision["candidateFailure"])
        self.assertFalse(self.decision["managerBoundary"]["repositoryRegistrationExecuted"])
        self.assertFalse(self.decision["managerBoundary"]["candidateInstallationExecuted"])

    def test_cleanup_and_claim_boundaries_are_explicit(self) -> None:
        self.assertTrue(self.decision["cleanup"]["reviewRootRemoved"])
        self.assertTrue(self.decision["cleanup"]["repositoryTmpRemovedAfter"])
        for value in self.decision["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
