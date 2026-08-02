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
