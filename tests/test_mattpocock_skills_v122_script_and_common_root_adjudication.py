import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
ADJUDICATION = ROOT / "registry/mattpocock-skills-v1.2.2-script-and-common-root-adjudication-2026-08-06.json"


class MattPocockSkillsV122ScriptAndCommonRootAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(ADJUDICATION.read_text(encoding="utf-8"))

    def test_scripts_are_distinguished_by_actual_authority_surface(self) -> None:
        scripts = {item["skill"]: item for item in self.document["scriptAdjudications"]}
        self.assertEqual(set(scripts), {"diagnosing-bugs", "wizard"})
        self.assertFalse(scripts["diagnosing-bugs"]["externalAccountWriteSurfaceObserved"])
        self.assertTrue(scripts["wizard"]["credentialHandlingSurface"])
        self.assertIn("GitHub Actions secret through gh", scripts["wizard"]["externalAccountWriteSurfaces"])
        for item in scripts.values():
            self.assertFalse(item["automaticExecutionRequiredForSkillLoading"])
            self.assertFalse(item["automaticExecutionDirectedBySkill"])
            self.assertTrue(item["humanInteractionRequiredWhenUsed"])

    def test_common_root_ambiguous_ownership_blocks_automatic_reconciliation(self) -> None:
        root = self.document["commonRootAdjudication"]
        self.assertTrue(root["directoryContainerMustRemain"])
        self.assertEqual(root["directDirectoryCount"], 13)
        self.assertFalse(root["directDirectoryOwnershipProved"])
        self.assertFalse(root["automaticDeleteAuthorized"])
        self.assertFalse(root["automaticReplaceAuthorized"])
        self.assertFalse(root["automaticMigrationAuthorized"])

    def test_no_runtime_or_value_claim_is_promoted(self) -> None:
        self.assertFalse(self.document["decision"]["atomicManagerUpdateReady"])
        self.assertFalse(self.document["decision"]["ambientEnablementOfNewWizardAllowed"])
        self.assertFalse(self.document["decision"]["runtimeMutationAuthorized"])
        self.assertFalse(self.document["dependencyDecision"]["thirdPartyScriptExecuted"])
        for field in (
            "scriptBehaviorExecutedOrProved",
            "credentialsReadOrWritten",
            "accountMutationPerformed",
            "commonRootOwnershipProved",
            "consumerDiscoveryPrecedenceProved",
            "managerUpdateSuitabilityProved",
            "valueProved",
        ):
            self.assertFalse(self.document["claimBoundary"][field])


if __name__ == "__main__":
    unittest.main()
