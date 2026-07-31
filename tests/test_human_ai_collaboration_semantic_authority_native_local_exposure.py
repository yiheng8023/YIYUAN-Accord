from __future__ import annotations

import copy
import tempfile
from pathlib import Path
import unittest

from scripts.probe_human_ai_collaboration_semantic_authority_native_local_exposure import (
    LOCAL_SKILL_SHA256,
    materialize_local_treatment,
    validate_report,
)


class SemanticAuthorityNativeLocalExposureTests(unittest.TestCase):
    def report(self) -> dict:
        common_inventory = {
            "sameIdentitySet": True,
            "onlyExpectedConfigurableSkillsEnabled": True,
            "allNonConfigurableStatesPreserved": True,
        }
        return {
            "schema": 1,
            "probeId": "semantic-authority-native-local-no-model-exposure-v1",
            "status": "preflight-pass-no-turn",
            "host": {"userAgent": "Codex Desktop/test"},
            "localTreatment": {
                "identity": "cc.grill-with-docs",
                "skillName": "grill-with-docs",
                "bytes": 5340,
                "sha256": LOCAL_SKILL_SHA256,
                "allRequiredExactPathsPresent": True,
            },
            "publicPacketOracleIsolation": {
                "positivePacketFailureCodes": [],
                "fullOracleLeakFailureCodes": [
                    "hard-fail-unmanifested-public-file",
                    "hard-fail-private-oracle-leak",
                ],
                "partialCanaryLeakFailureCodes": [
                    "hard-fail-private-oracle-leak",
                    "hard-fail-public-file-digest-drift",
                ],
                "publicPacketPrivateOracleLeakageRejected": True,
            },
            "arms": [
                {
                    "arm": "native-configurable-skills-disabled",
                    "inventory": {
                        **common_inventory,
                        "enabledConfigurableSkillCount": 0,
                    },
                },
                {
                    "arm": "local-adapted-monolith-selected",
                    "inventory": {
                        **common_inventory,
                        "enabledConfigurableSkillCount": 1,
                    },
                },
            ],
            "threadStarted": False,
            "turnStarted": False,
            "modelRequestSent": False,
            "runtimeIsolation": {
                "codexHomeMode": "temporary-empty-under-treatment-root",
                "temporaryCodexHomeRetained": False,
                "treatmentRootMode": "temporary-under-repository-tmp",
                "temporaryTreatmentRootRetained": False,
                "mcpConfigurationMode": "empty-table-override",
                "inheritedGlobalConfigExecuted": False,
            },
            "stability": {
                "localTreatmentBytesStable": True,
                "globalConfigStable": True,
                "repositoryStatusStable": True,
            },
            "claimBoundary": {
                "skillLoaderInvocationProved": False,
                "skillInstructionsReachedModelProved": False,
                "behavioralCausationProved": False,
                "semanticContinuityProved": False,
                "localMonolithValueProved": False,
                "nativeRouteValueProved": False,
            },
        }

    def test_valid_offline_report_passes(self) -> None:
        self.assertEqual([], validate_report(self.report()))

    def test_rejects_enabled_configurable_skill_in_native_arm(self) -> None:
        report = copy.deepcopy(self.report())
        report["arms"][0]["inventory"]["enabledConfigurableSkillCount"] = 1
        self.assertIn(
            "fail-enabled-count:native-configurable-skills-disabled",
            validate_report(report),
        )

    def test_rejects_extra_enabled_skill_in_local_arm(self) -> None:
        report = copy.deepcopy(self.report())
        report["arms"][1]["inventory"]["enabledConfigurableSkillCount"] = 2
        self.assertIn(
            "fail-enabled-count:local-adapted-monolith-selected",
            validate_report(report),
        )

    def test_rejects_claim_promotion(self) -> None:
        report = copy.deepcopy(self.report())
        report["claimBoundary"]["skillLoaderInvocationProved"] = True
        self.assertIn("hard-fail-claim-promotion", validate_report(report))

    def test_rejects_missing_private_oracle_leakage_rejection(self) -> None:
        report = copy.deepcopy(self.report())
        report["publicPacketOracleIsolation"][
            "fullOracleLeakFailureCodes"
        ] = []
        report["publicPacketOracleIsolation"][
            "publicPacketPrivateOracleLeakageRejected"
        ] = False
        self.assertIn(
            "hard-fail-public-packet-oracle-isolation",
            validate_report(report),
        )

    def test_materialized_treatment_is_exact_and_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "treatment"
            receipt = materialize_local_treatment(root)
            target = root / ".agents" / "skills" / "grill-with-docs" / "SKILL.md"
            self.assertEqual(target.resolve().as_posix(), receipt["path"])
            self.assertEqual(5340, receipt["bytes"])
            self.assertEqual(LOCAL_SKILL_SHA256, receipt["sha256"])
            self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
