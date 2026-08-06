import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = (
    ROOT
    / "registry/skill-portfolio-three-domain-current-capability-screen-2026-08-06.json"
)


class SkillPortfolioThreeDomainCurrentCapabilityScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_repository_source_bindings_are_byte_frozen(self) -> None:
        for binding in self.evidence["sourceBindings"]:
            payload = (ROOT / binding["path"]).read_bytes()
            self.assertEqual(len(payload), binding["bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), binding["sha256"])

    def test_screen_is_exactly_one_representative_per_previously_unmapped_domain(self) -> None:
        candidates = self.evidence["candidates"]
        domains = [candidate["domainId"] for candidate in candidates]
        self.assertEqual(
            domains,
            [
                "daily-life-and-personal-productivity",
                "education-and-training",
                "security-privacy-and-compliance",
            ],
        )
        self.assertEqual(len(candidates), len(set(domains)))
        self.assertEqual(self.evidence["decision"]["screenedCandidateCount"], 3)

    def test_current_official_metadata_is_not_vendored_or_promoted(self) -> None:
        official = [
            candidate
            for candidate in self.evidence["candidates"]
            if candidate["sourceClass"]
            == "openai-maintained-current-plugin-metadata"
        ]
        self.assertEqual(len(official), 2)
        for candidate in official:
            self.assertEqual(
                candidate["disposition"],
                "retain-as-current-official-baseline-metadata-not-a-vendored-candidate",
            )
            self.assertEqual(
                candidate["claimCeiling"],
                "package-and-static-component-coverage-only",
            )

    def test_anki_is_exact_upstream_review_only_and_license_conflict_stays_visible(self) -> None:
        anki = next(
            candidate
            for candidate in self.evidence["candidates"]
            if candidate["name"] == "anki-connect"
        )
        self.assertEqual(
            anki["source"]["revision"],
            "9b0e00ad1b941165e2506545bbfddafa34cf2cb8",
        )
        self.assertTrue(anki["source"]["remoteMainMatchedPinnedRevisionAtReview"])
        self.assertTrue(anki["component"]["canonicalAndGeneratedBytesEqual"])
        self.assertEqual(anki["licenseReview"]["rootLicenseDeclared"], "CC0-1.0")
        self.assertEqual(anki["licenseReview"]["pluginManifestDeclared"], "MIT")
        self.assertFalse(anki["licenseReview"]["consistent"])
        self.assertEqual(
            anki["disposition"],
            "review-only-hold-license-runtime-account-data-and-mutation-boundaries",
        )

    def test_stop_rule_and_cleanup_forbid_activation_or_retained_payload(self) -> None:
        decision = self.evidence["decision"]
        self.assertFalse(decision["newPayloadRetainedInRepository"])
        self.assertFalse(decision["newCandidateAdmitted"])
        self.assertFalse(decision["newCandidateInstalled"])
        self.assertFalse(decision["managerTransactionPrepared"])
        self.assertFalse(decision["residualGapInferred"])
        self.assertFalse(decision["selfAuthoredWorkEligible"])
        cleanup = self.evidence["cleanup"]
        self.assertTrue(cleanup["isolatedExternalReviewRootOriginalPathAbsentAfterReview"])
        self.assertTrue(cleanup["isolatedExternalReviewRootSentToRecycleBin"])
        self.assertFalse(cleanup["thirdPartyBodyExecuted"])
        self.assertFalse(cleanup["liveCapabilityRootMutated"])

    def test_all_broad_claims_remain_false(self) -> None:
        self.assertTrue(self.evidence["claimBoundary"])
        self.assertTrue(
            all(value is False for value in self.evidence["claimBoundary"].values())
        )

    def test_program_acceptance_map_links_the_bounded_evidence_without_status_upgrade(self) -> None:
        program = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        evidence_id = (
            "evidence.skill-portfolio-three-domain-current-capability-screen-2026-08-06"
        )
        evidence = next(item for item in program["evidence"] if item["id"] == evidence_id)
        expected = {
            "acceptance.multi-domain-coverage",
            "acceptance.discovery-reuse-before-authoring",
            "acceptance.cc-switch-source-preserving-skill-pool",
        }
        self.assertEqual(set(evidence["supports"]), expected)
        criteria = {
            item["id"]: item
            for item in program["acceptanceCriteria"]
            if item["id"] in expected
        }
        self.assertEqual(
            criteria["acceptance.multi-domain-coverage"]["assessment"],
            "verified",
        )
        self.assertEqual(
            criteria["acceptance.discovery-reuse-before-authoring"]["assessment"],
            "verified",
        )
        self.assertEqual(
            criteria["acceptance.cc-switch-source-preserving-skill-pool"]["assessment"],
            "partial",
        )
        for criterion in criteria.values():
            self.assertIn(evidence_id, criterion["evidenceIds"])


if __name__ == "__main__":
    unittest.main()
