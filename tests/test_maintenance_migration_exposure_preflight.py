from __future__ import annotations

import copy
import unittest

from scripts.probe_maintenance_migration_exposure_preflight import (
    compare_profile,
    validate_report,
)


def valid_report() -> dict:
    thread = {
        "model": "gpt-5.3-codex-spark",
        "reasoningEffort": "low",
        "modelProvider": "openai",
        "approvalPolicy": "never",
        "sandbox": {"type": "readOnly", "networkAccess": False},
    }
    return {
        "candidate": {
            "name": "deprecation-and-migration",
            "sha256": (
                "52ef07de05726292c0f5e9fe666cc30e6"
                "efbe580ed775621e785a49ec80bd4ea"
            ),
            "prePostStable": True,
        },
        "nativeDisabledProfile": {
            "sameIdentitySet": True,
            "allConfigurableSkillsDisabled": True,
            "allNonConfigurableStatesPreserved": True,
            "enabledConfigurableSkillCount": 0,
        },
        "selectedProfile": {
            "sameIdentitySet": True,
            "onlyExpectedConfigurableSkillEnabled": True,
            "allNonConfigurableStatesPreserved": True,
            "enabledConfigurableSkillCount": 1,
        },
        "threadProfiles": {
            "native": copy.deepcopy(thread),
            "selected": copy.deepcopy(thread),
        },
        "promptBoundary": {
            "samePublicTaskPrompt": True,
            "nativeSelectedSkillAbsent": True,
            "candidateSelectedSkillName": "deprecation-and-migration",
            "privateSentinelsPresentInTrialFiles": [],
            "privateOracleFilePresent": False,
        },
        "mutationBoundary": {
            "globalConfigStable": True,
            "candidateFileStable": True,
            "nativeFixtureFilesStable": True,
            "candidateFixtureFilesStable": True,
        },
        "processBoundary": {
            "turnStarted": False,
            "modelRequestSent": False,
        },
        "claimBoundary": {
            "provesSkillLoaderInvocation": False,
            "provesSkillBehavior": False,
        },
    }


class MaintenanceMigrationExposurePreflightTests(unittest.TestCase):
    def test_valid_report_passes(self) -> None:
        self.assertEqual([], validate_report(valid_report()))

    def test_rejects_private_oracle_leak(self) -> None:
        report = valid_report()
        report["promptBoundary"]["privateSentinelsPresentInTrialFiles"] = [
            "Mira"
        ]
        self.assertIn(
            "hard-fail-prompt-or-oracle-boundary",
            validate_report(report),
        )

    def test_rejects_task_turn(self) -> None:
        report = valid_report()
        report["processBoundary"]["turnStarted"] = True
        self.assertIn("hard-fail-task-turn-started", validate_report(report))

    def test_rejects_candidate_digest_drift(self) -> None:
        report = valid_report()
        report["candidate"]["sha256"] = "0" * 64
        self.assertIn("fail-candidate-digest", validate_report(report))

    def test_compare_profile_distinguishes_disabled_and_selected(self) -> None:
        control = [
            {
                "name": "deprecation-and-migration",
                "path": "C:/skills/deprecation-and-migration/SKILL.md",
                "scope": "user",
                "enabled": True,
            },
            {
                "name": "other",
                "path": "C:/skills/other/SKILL.md",
                "scope": "user",
                "enabled": True,
            },
            {
                "name": "system",
                "path": "C:/skills/system/SKILL.md",
                "scope": "system",
                "enabled": True,
            },
        ]
        disabled = [
            {**row, "enabled": False}
            if row["scope"] == "user"
            else dict(row)
            for row in control
        ]
        selected = [
            {
                **row,
                "enabled": row["name"] == "deprecation-and-migration",
            }
            if row["scope"] == "user"
            else dict(row)
            for row in control
        ]

        disabled_result = compare_profile(
            control,
            disabled,
            selected_path=None,
        )
        selected_result = compare_profile(
            control,
            selected,
            selected_path="C:/skills/deprecation-and-migration/SKILL.md",
        )

        self.assertTrue(disabled_result["allConfigurableSkillsDisabled"])
        self.assertTrue(
            selected_result["onlyExpectedConfigurableSkillEnabled"]
        )


if __name__ == "__main__":
    unittest.main()
