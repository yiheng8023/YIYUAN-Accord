import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = (
    ROOT
    / "registry"
    / "skill-portfolio-system-manager-reference-cohort-2026-08-06.json"
)
PROGRAM_ACCEPTANCE_PATH = ROOT / "registry" / "program-acceptance-map.json"
PORTFOLIO_AUTHORITY_PATH = (
    ROOT / "registry" / "skill-portfolio-current-authority.json"
)
EVIDENCE_ID = "evidence.skill-portfolio-system-manager-reference-cohort-2026-08-06"


def load_report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


class SkillPortfolioSystemManagerReferenceCohortTests(unittest.TestCase):
    def test_cohort_is_exactly_the_three_prebound_manager_sources(self) -> None:
        report = load_report()
        sources = {source["id"]: source for source in report["sources"]}

        self.assertEqual(report["schema"], 1)
        self.assertEqual(
            report["status"],
            "three-source-exact-revision-static-reference-review-complete",
        )
        self.assertEqual(
            set(sources),
            {
                "github:stellarlinkco/myclaude",
                "github:vercel-labs/skills",
                "github:affaan-m/ECC",
            },
        )
        self.assertEqual(
            report["cohortContract"]["sourceBoundary"], list(sources)
        )

    def test_revisions_and_selected_git_objects_are_immutable_identities(self) -> None:
        report = load_report()
        expected_revisions = {
            "github:stellarlinkco/myclaude": (
                "f2e75c1263a2d5f09cdc4bb3dfe3635c635ff296"
            ),
            "github:vercel-labs/skills": (
                "a4d243c3d4f86cdf9385dd1b6a0733f6937e70b5"
            ),
            "github:affaan-m/ECC": (
                "623f2c020f052319657674e4e6c29ab5d0ad566b"
            ),
        }
        sha1 = re.compile(r"^[0-9a-f]{40}$")
        sha256 = re.compile(r"^[0-9a-f]{64}$")

        for source in report["sources"]:
            self.assertEqual(source["revision"], expected_revisions[source["id"]])
            self.assertRegex(source["revision"], sha1)
            self.assertRegex(source["gitObjectManifestSha256"], sha256)
            self.assertGreater(len(source["gitObjects"]), 0)
            self.assertEqual(
                len({item["path"] for item in source["gitObjects"]}),
                len(source["gitObjects"]),
            )
            for item in source["gitObjects"]:
                self.assertEqual(item["type"], "blob")
                self.assertRegex(item["oid"], sha1)
                self.assertGreater(item["size"], 0)

    def test_dispositions_keep_whole_systems_out_of_skill_and_manager_routes(self) -> None:
        report = load_report()
        dispositions = {
            source["id"]: source["disposition"] for source in report["sources"]
        }

        self.assertEqual(
            dispositions,
            {
                "github:stellarlinkco/myclaude": (
                    "architecture-and-negative-control-reference-only"
                ),
                "github:vercel-labs/skills": (
                    "discovery-and-consumer-topology-adapter-input-only"
                ),
                "github:affaan-m/ECC": (
                    "high-value-method-and-adapter-reference-only"
                ),
            },
        )
        decision = report["portfolioDecision"]
        self.assertFalse(decision["ordinarySkillCandidateAdded"])
        self.assertFalse(decision["currentSeventeenCandidatePoolChanged"])
        self.assertFalse(decision["managerReplacementSelected"])
        self.assertFalse(decision["repositoryAuthoredImplementationJustified"])
        self.assertFalse(decision["hardStandardPromotionJustified"])

    def test_acquisition_and_claim_boundaries_remain_non_active(self) -> None:
        report = load_report()
        observation = report["acquisitionObservation"]
        authority = report["authorityBoundary"]
        claims = report["claimBoundary"]

        self.assertFalse(observation["temporaryAcquisitionRootRetained"])
        self.assertTrue(observation["temporaryAcquisitionRootRemovedAfterReview"])
        self.assertFalse(observation["upstreamBodyVendoredIntoHarness"])
        self.assertFalse(observation["thirdPartyCodeExecuted"])
        self.assertFalse(observation["dependenciesInstalled"])
        self.assertFalse(observation["liveStateMutated"])

        for key in (
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
            "provesRuntimeBehavior",
            "provesSecurity",
            "provesCrossHostPortability",
            "provesUserValue",
            "provesManagerSuitability",
            "provesResidualGap",
            "authorizesInstallationActivationOrExecution",
        ):
            self.assertFalse(claims[key])

    def test_current_authority_and_acceptance_map_bind_the_reference_event(self) -> None:
        authority = json.loads(PORTFOLIO_AUTHORITY_PATH.read_text(encoding="utf-8"))
        program = json.loads(PROGRAM_ACCEPTANCE_PATH.read_text(encoding="utf-8"))
        current = authority["currentSystemManagerReferenceCohort"]

        self.assertEqual(
            current["event"],
            "registry/skill-portfolio-system-manager-reference-cohort-2026-08-06.json",
        )
        self.assertEqual(current["sourceCount"], 3)
        self.assertFalse(current["managerReplacementSelected"])
        self.assertFalse(current["directAdoptionAuthorized"])

        expected_acceptances = {
            "acceptance.solution-neutral-collaboration-rebaseline",
            "acceptance.capability-survey-result-package",
            "acceptance.cross-agent-claim-limits",
            "acceptance.residual-gap-proof",
        }
        criteria = {item["id"]: item for item in program["acceptanceCriteria"]}
        for acceptance_id in expected_acceptances:
            self.assertIn(EVIDENCE_ID, criteria[acceptance_id]["evidenceIds"])

        evidence = {item["id"]: item for item in program["evidence"]}[EVIDENCE_ID]
        self.assertEqual(set(evidence["supports"]), expected_acceptances)
        self.assertEqual(
            evidence["path"],
            "registry/skill-portfolio-system-manager-reference-cohort-2026-08-06.json",
        )


if __name__ == "__main__":
    unittest.main()
