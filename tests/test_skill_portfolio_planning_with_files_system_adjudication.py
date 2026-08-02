import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
DECISION = ROOT / "registry/skill-portfolio-planning-with-files-system-adjudication-2026-08-03.json"


class SkillPortfolioPlanningWithFilesSystemAdjudicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))

    def test_exact_current_source_and_license_are_bound(self) -> None:
        source = self.decision["source"]
        self.assertEqual(source["repository"], "OthmanAdi/planning-with-files")
        self.assertEqual(source["commit"], "0e2b00ce4e8d1789cbcb16a41f7c9510b212b942")
        self.assertEqual(source["tree"], "3e0fcc7dbe1e7f12ca92653aff87268a423daa49")
        self.assertTrue(source["remoteHeadMatchesPin"])
        self.assertTrue(source["releaseTagPeeledCommitMatches"])
        self.assertEqual(source["license"], "MIT")
        self.assertFalse(source["thirdPartyCodeExecuted"])

    def test_eighteen_skill_paths_are_not_eighteen_independent_capabilities(self) -> None:
        surface = self.decision["payloadSurface"]
        self.assertEqual(surface["skillMdPathCount"], 18)
        self.assertEqual(surface["hostProjectionCount"], 12)
        self.assertEqual(surface["languageVariantCountIncludingCanonical"], 6)
        self.assertEqual(surface["uniqueDeclaredNames"], 7)
        self.assertEqual(surface["uniqueSkillMdHashes"], 18)
        self.assertFalse(surface["codexSkill"]["byteEqualToCanonical"])

    def test_mechanisms_are_split_instead_of_whole_system_admission(self) -> None:
        dispositions = {
            item["id"]: item["disposition"]
            for item in self.decision["mechanismSlices"]
        }
        self.assertEqual(
            dispositions["durable-three-file-working-state"],
            "advance-to-isolated-behavior-comparison",
        )
        self.assertEqual(
            dispositions["cross-session-transcript-catchup"],
            "hold-for-privacy-schema-and-current-session-attribution-review",
        )
        self.assertEqual(
            dispositions["multi-host-distribution"],
            "architecture-reference-not-one-portable-skill",
        )

    def test_skill_only_manager_projection_is_dependency_incomplete(self) -> None:
        manager = self.decision["managerBoundary"]
        self.assertFalse(manager["skillOnlyProjectionDependencyComplete"])
        self.assertFalse(manager["atomicDefaultDisabledInstallProved"])
        self.assertFalse(manager["repositoryRegistrationExecuted"])
        self.assertFalse(manager["candidateInstallationExecuted"])
        self.assertIn("Codex Hook manifest", manager["reason"])

    def test_transcript_and_hook_authority_are_explicit(self) -> None:
        boundary = self.decision["authorityAndDataBoundaries"]
        self.assertTrue(boundary["readsCodexSessionRollouts"])
        self.assertTrue(boundary["mayReadClaudeSessionTranscripts"])
        self.assertTrue(boundary["mayReadOpenCodeSqlite"])
        self.assertTrue(boundary["injectsFileAndTranscriptContentIntoModelContext"])
        self.assertTrue(boundary["registersAutomaticHostHooksWhenFullyIntegrated"])

    def test_acceptance_check_claim_is_not_promoted(self) -> None:
        finding = self.decision["documentationImplementationFinding"]
        self.assertEqual(
            finding["disposition"],
            "unimplemented-or-unproved-pending-upstream-clarification",
        )
        self.assertFalse(finding["candidateFailure"])

    def test_source_is_not_failed_but_full_install_remains_held(self) -> None:
        self.assertEqual(
            self.decision["disposition"],
            "split-advance-continuity-mechanisms-to-isolated-comparison-hold-full-system-manager-install",
        )
        self.assertFalse(self.decision["candidateFailure"])
        self.assertFalse(self.decision["authorReportedEvaluation"]["independentlyReexecutedByHarness"])

    def test_cleanup_and_claim_boundaries_are_explicit(self) -> None:
        self.assertTrue(self.decision["cleanup"]["reviewRootRemoved"])
        self.assertTrue(self.decision["cleanup"]["repositoryTmpRemovedAfter"])
        for value in self.decision["claimBoundary"].values():
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
