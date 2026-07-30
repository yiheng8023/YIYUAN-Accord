from __future__ import annotations

import copy
import unittest

from scripts.probe_requirements_domain_exposure_preflight import validate_report


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
            "name": "grill-with-docs",
            "sha256": "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035",
            "prePostStable": True,
        },
        "nativeDisabledProfile": {
            "sameIdentitySet": True,
            "allConfigurableSkillsDisabled": True,
            "enabledConfigurableSkillCount": 0,
            "allNonConfigurableStatesPreserved": True,
        },
        "selectedProfile": {
            "sameIdentitySet": True,
            "onlyExpectedConfigurableSkillEnabled": True,
            "enabledConfigurableSkillCount": 1,
            "allNonConfigurableStatesPreserved": True,
        },
        "threadProfiles": {
            "native": copy.deepcopy(thread),
            "selected": copy.deepcopy(thread),
        },
        "promptBoundary": {
            "samePublicTaskPrompt": True,
            "nativeSelectedSkillAbsent": True,
            "candidateSelectedSkillName": "grill-with-docs",
            "privateSentinelsPresentInTrialFiles": [],
            "privateOracleFilePresent": False,
        },
        "mutationBoundary": {
            "globalConfigStable": True,
            "candidateFileStable": True,
            "nativeFixtureFilesStable": True,
            "candidateFixtureFilesStable": True,
        },
        "processBoundary": {"turnStarted": False, "modelRequestSent": False},
        "claimBoundary": {
            "provesSkillLoaderInvocation": False,
            "provesRequirementsCompleteness": False,
        },
    }


class RequirementsDomainExposurePreflightTests(unittest.TestCase):
    def test_valid_report_passes(self) -> None:
        self.assertEqual([], validate_report(valid_report()))

    def test_rejects_task_turn(self) -> None:
        report = valid_report()
        report["processBoundary"]["turnStarted"] = True
        self.assertIn("hard-fail-task-turn-started", validate_report(report))

    def test_rejects_private_oracle_leak(self) -> None:
        report = valid_report()
        report["promptBoundary"]["privateSentinelsPresentInTrialFiles"] = [
            "requiredQuestionTopicGroups"
        ]
        self.assertIn("hard-fail-prompt-or-oracle-boundary", validate_report(report))

    def test_rejects_candidate_digest_drift(self) -> None:
        report = valid_report()
        report["candidate"]["sha256"] = "0" * 64
        self.assertIn("fail-candidate-digest", validate_report(report))


if __name__ == "__main__":
    unittest.main()
