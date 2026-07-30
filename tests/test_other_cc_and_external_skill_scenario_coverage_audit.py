from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_other_cc_and_external_skill_scenario_coverage_audit import (
    AUDIT_PATH,
    DOCUMENTATION_PATH,
    ROOT,
    validate_audit,
)


def load() -> dict:
    return json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))


class OtherCcAndExternalSkillScenarioCoverageAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load()

    def test_current_audit_is_valid(self) -> None:
        validate_audit(self.document)

    def test_rejects_source_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source binding digest"):
            validate_audit(document)

    def test_rejects_unobserved_candidate_as_behavioral(self) -> None:
        document = copy.deepcopy(self.document)
        document["behaviorallyObservedScenarioCells"].append(
            {
                "scenarioId": "SE-RELEASE-CHANGE-01",
                "candidateId": "skill.curated.shipping-and-launch",
                "validRepetitions": 3,
                "classification": "pass",
                "currentBehavioralEvidence": True,
                "independentLoaderEventProved": False,
                "candidateInstructionsReachedModelProved": False,
                "candidateCausationProved": False,
            }
        )
        with self.assertRaisesRegex(RuntimeError, "observed candidate cell set"):
            validate_audit(document)

    def test_rejects_loader_invocation_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["behaviorallyObservedScenarioCells"][0][
            "independentLoaderEventProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "observed cell was promoted"):
            validate_audit(document)

    def test_rejects_historical_superpowers_as_current(self) -> None:
        document = copy.deepcopy(self.document)
        document["historicalBehaviorOnly"][0][
            "currentBehavioralEvidence"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "historical behavior"):
            validate_audit(document)

    def test_rejects_cc_count_as_per_skill_coverage(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceExposureOrProtocolOnly"]["aggregateCcInventoryOnly"][
            "perSkillScenarioCoverageDerivableFromCounts"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "aggregate CC inventory"):
            validate_audit(document)

    def test_rejects_approved_payload_as_current_cc_body(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceExposureOrProtocolOnly"][
            "approvedReleaseScenarioCandidateMetadata"
        ][0]["currentCcBodyIdentityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "metadata was promoted"):
            validate_audit(document)

    def test_rejects_approved_payload_value_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceExposureOrProtocolOnly"][
            "approvedReleaseScenarioCandidateMetadata"
        ][0]["behavioralValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "metadata was promoted"):
            validate_audit(document)

    def test_rejects_duplicate_candidate_metadata_shadow(self) -> None:
        document = copy.deepcopy(self.document)
        metadata = document["sourceExposureOrProtocolOnly"][
            "approvedReleaseScenarioCandidateMetadata"
        ]
        duplicate = copy.deepcopy(metadata[0])
        duplicate["behavioralValueProved"] = True
        metadata.insert(0, duplicate)

        with self.assertRaisesRegex(RuntimeError, "duplicate identity"):
            validate_audit(document)

    def test_rejects_missing_planned_only_scenario(self) -> None:
        document = copy.deepcopy(self.document)
        document["highPriorityCoverageGaps"][
            "plannedOnlyNoAgentOrDomainEvidence"
        ].remove("GEN-ACCESS-COMMS-01")
        with self.assertRaisesRegex(RuntimeError, "coverage gap set"):
            validate_audit(document)

    def test_rejects_live_arm_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["nextNamedScenarioDecision"][
            "liveComparativeArmReady"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "scenario decision boundary"):
            validate_audit(document)

    def test_rejects_dispatch_or_cc_authority_promotion(self) -> None:
        for key in (
            "modelDispatchAuthorized",
            "ccMutationAuthorized",
            "portfolioMutationAuthorized",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(self.document)
                document["nextNamedScenarioDecision"][key] = True
                with self.assertRaisesRegex(
                    RuntimeError, "scenario decision boundary"
                ):
                    validate_audit(document)

    def test_rejects_execution_side_effect(self) -> None:
        for key in (
            "externalDiscoveryPerformed",
            "installationPerformed",
            "ccSwitchReadOrMutationPerformed",
            "globalConfigurationChanged",
            "programMapChanged",
            "globalVerifierChanged",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(self.document)
                document["executionBoundary"][key] = True
                with self.assertRaisesRegex(
                    RuntimeError, "execution boundary"
                ):
                    validate_audit(document)

    def test_rejects_residual_gap_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["residualSelfAuthoredGapProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_audit(document)

    def test_rejects_missing_documented_live_boundary(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for binding in self.document["sourceBindings"]:
            source = ROOT / binding["path"]
            target = root / binding["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        documentation = (ROOT / DOCUMENTATION_PATH).read_text(encoding="utf-8")
        documentation = documentation.replace(
            "does not make a live comparative arm ready",
            "makes a live comparative arm ready",
        )
        target = root / DOCUMENTATION_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(documentation, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "documentation boundary"):
            validate_audit(self.document, root=root)


if __name__ == "__main__":
    unittest.main()
