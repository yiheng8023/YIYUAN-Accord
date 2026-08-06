import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = (
    ROOT
    / "registry"
    / "skill-portfolio-discovery-index-reference-cohort-2026-08-06.json"
)
PROGRAM_ACCEPTANCE_PATH = ROOT / "registry" / "program-acceptance-map.json"
PORTFOLIO_AUTHORITY_PATH = (
    ROOT / "registry" / "skill-portfolio-current-authority.json"
)
EVIDENCE_ID = (
    "evidence.skill-portfolio-discovery-index-reference-cohort-2026-08-06"
)


def load_report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


class SkillPortfolioDiscoveryIndexReferenceCohortTests(unittest.TestCase):
    def test_cohort_is_exactly_the_six_prebound_discovery_indexes(self) -> None:
        report = load_report()
        sources = {source["id"]: source for source in report["sources"]}
        expected = {
            "github:ComposioHQ/awesome-claude-skills",
            "github:github/awesome-copilot",
            "github:alirezarezvani/claude-skills",
            "github:VoltAgent/awesome-agent-skills",
            "github:sickn33/agentic-awesome-skills",
            "github:helloianneo/awesome-claude-code-skills",
        }

        self.assertEqual(report["schema"], 1)
        self.assertEqual(
            report["status"],
            "six-source-exact-revision-discovery-reference-review-complete",
        )
        self.assertEqual(set(sources), expected)
        self.assertEqual(report["cohortContract"]["sourceBoundary"], list(sources))

    def test_revisions_trees_and_selected_objects_are_immutable(self) -> None:
        report = load_report()
        expected_revisions = {
            "github:ComposioHQ/awesome-claude-skills": (
                "be2a406907dbc61b73e6827ded415c96139d13a2"
            ),
            "github:github/awesome-copilot": (
                "a7fdcd50062528c9ba5e3ecb662e2c5dc53355f8"
            ),
            "github:alirezarezvani/claude-skills": (
                "aa8d778811a557a2c28ccadda4cf3d0bd028a4cc"
            ),
            "github:VoltAgent/awesome-agent-skills": (
                "5241ad954d2880330d9f3a7df086f8d943c4c988"
            ),
            "github:sickn33/agentic-awesome-skills": (
                "fb4655797cd8450878d7c870a81321fa5106feda"
            ),
            "github:helloianneo/awesome-claude-code-skills": (
                "37cf1a830b904f9fd2b995455f3b00fdae17bdc0"
            ),
        }
        sha1 = re.compile(r"^[0-9a-f]{40}$")

        for source in report["sources"]:
            self.assertEqual(source["revision"], expected_revisions[source["id"]])
            self.assertRegex(source["revision"], sha1)
            self.assertRegex(source["treeOid"], sha1)
            self.assertGreater(len(source["gitObjects"]), 0)
            self.assertEqual(
                len({item["path"] for item in source["gitObjects"]}),
                len(source["gitObjects"]),
            )
            for item in source["gitObjects"]:
                self.assertEqual(item["type"], "blob")
                self.assertRegex(item["oid"], sha1)
                self.assertGreater(item["size"], 0)

    def test_drift_is_bounded_and_does_not_promote_candidates(self) -> None:
        report = load_report()
        changed = {
            source["id"]
            for source in report["sources"]
            if source["revisionChangedFromPriorInventory"]
        }

        self.assertEqual(
            changed,
            {
                "github:github/awesome-copilot",
                "github:VoltAgent/awesome-agent-skills",
                "github:sickn33/agentic-awesome-skills",
            },
        )
        decision = report["portfolioDecision"]
        self.assertEqual(decision["revisionsChangedCount"], 3)
        self.assertEqual(decision["revisionsUnchangedCount"], 3)
        self.assertEqual(decision["childSourceFollowupsOpened"], 0)
        self.assertFalse(decision["ordinarySkillCandidateAdded"])
        self.assertFalse(decision["currentSeventeenCandidatePoolChanged"])
        self.assertFalse(decision["managerReplacementSelected"])
        self.assertFalse(decision["repositoryAuthoredImplementationJustified"])
        self.assertFalse(decision["hardStandardPromotionJustified"])

    def test_dispositions_preserve_index_and_control_plane_boundaries(self) -> None:
        report = load_report()
        dispositions = {
            source["id"]: source["disposition"] for source in report["sources"]
        }
        self.assertEqual(
            dispositions,
            {
                "github:ComposioHQ/awesome-claude-skills": (
                    "integration-index-and-bundled-payload-reference-only"
                ),
                "github:github/awesome-copilot": (
                    "official-community-index-and-copilot-payload-reference-only"
                ),
                "github:alirezarezvani/claude-skills": (
                    "large-mixed-multihost-catalog-reference-only"
                ),
                "github:VoltAgent/awesome-agent-skills": (
                    "child-source-lead-index-only"
                ),
                "github:sickn33/agentic-awesome-skills": (
                    "aggregate-and-external-control-plane-reference-only"
                ),
                "github:helloianneo/awesome-claude-code-skills": (
                    "curated-lead-index-only"
                ),
            },
        )

    def test_acquisition_authority_and_claim_boundaries_remain_non_active(self) -> None:
        report = load_report()
        observation = report["acquisitionObservation"]
        authority = report["authorityBoundary"]
        claims = report["claimBoundary"]

        self.assertFalse(observation["temporaryAcquisitionRootRetained"])
        self.assertTrue(observation["temporaryAcquisitionRootSentToRecycleBinAfterReview"])
        self.assertFalse(observation["upstreamBodyVendoredIntoHarness"])
        self.assertFalse(observation["thirdPartyCodeExecuted"])
        self.assertFalse(observation["dependenciesInstalled"])
        self.assertFalse(observation["childSourcesAcquired"])
        self.assertFalse(observation["liveStateMutated"])

        for key in (
            "childSourceExpansionAuthorized",
            "installAuthorized",
            "enableAuthorized",
            "executeAuthorized",
            "managerMutationAuthorized",
            "consumerMutationAuthorized",
            "pluginAppMcpHookMutationAuthorized",
            "accountConnectionAuthorized",
            "modelDispatchAuthorized",
            "directAdoptionAuthorized",
        ):
            self.assertFalse(authority[key])

        for key in (
            "provesChildSourceIdentityOrQuality",
            "provesCandidateSuitability",
            "provesRuntimeBehavior",
            "provesSecurity",
            "provesCrossHostPortability",
            "provesUserValue",
            "provesManagerSuitability",
            "provesResidualGap",
            "authorizesInstallationActivationOrExecution",
        ):
            self.assertFalse(claims[key])

    def test_current_authority_and_acceptance_bind_the_reference_event(self) -> None:
        authority = json.loads(PORTFOLIO_AUTHORITY_PATH.read_text(encoding="utf-8"))
        program = json.loads(PROGRAM_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        current = authority["currentDiscoveryIndexReferenceCohort"]

        self.assertEqual(
            current["event"],
            "registry/skill-portfolio-discovery-index-reference-cohort-2026-08-06.json",
        )
        self.assertEqual(current["sourceCount"], 6)
        self.assertEqual(current["revisionChangedCount"], 3)
        self.assertFalse(current["childSourceFollowupOpened"])
        self.assertFalse(current["candidatePoolChanged"])
        self.assertFalse(current["managerReplacementSelected"])

        expected_acceptances = {
            "acceptance.residual-gap-proof",
            "acceptance.cc-switch-source-preserving-skill-pool",
            "acceptance.broad-capability-ecosystem-boundary",
            "acceptance.discovery-reuse-before-authoring",
        }
        criteria = {item["id"]: item for item in program["acceptanceCriteria"]}
        for acceptance_id in expected_acceptances:
            self.assertIn(EVIDENCE_ID, criteria[acceptance_id]["evidenceIds"])

        evidence = {item["id"]: item for item in program["evidence"]}[EVIDENCE_ID]
        self.assertEqual(set(evidence["supports"]), expected_acceptances)
        self.assertEqual(
            evidence["path"],
            "registry/skill-portfolio-discovery-index-reference-cohort-2026-08-06.json",
        )


if __name__ == "__main__":
    unittest.main()
