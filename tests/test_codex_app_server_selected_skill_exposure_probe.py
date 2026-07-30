from __future__ import annotations

import copy
from pathlib import Path
import unittest

from scripts.probe_codex_app_server_selected_skill_exposure import (
    EFFORT,
    EXPECTED_SELECTED_PATH,
    EXPECTED_SELECTED_SHA256,
    MODEL,
    SELECTED_SKILL_NAME,
    compare_selected_inventory,
    select_exact_skill,
    validate_report,
)


def row(
    name: str,
    path: str,
    *,
    scope: str = "user",
    enabled: bool = True,
) -> dict:
    return {
        "name": name,
        "path": path,
        "scope": scope,
        "enabled": enabled,
    }


def passing_report() -> dict:
    return {
        "exposureComparison": {
            "sameIdentitySet": True,
            "controlUserSkillCount": 105,
            "selectedEnabledUserSkillCount": 1,
            "onlySelectedUserSkillEnabled": True,
            "allOtherUserSkillsDisabled": True,
            "allNonUserStatesPreserved": True,
        },
        "selectedSkill": {
            "name": SELECTED_SKILL_NAME,
            "path": EXPECTED_SELECTED_PATH.as_posix(),
            "sha256": EXPECTED_SELECTED_SHA256,
            "prePostStable": True,
        },
        "threadTelemetry": {
            "model": MODEL,
            "reasoningEffort": EFFORT,
            "modelProvider": "openai",
            "approvalPolicy": "never",
            "sandbox": {"type": "readOnly", "networkAccess": False},
        },
        "mutationBoundary": {
            "configPrePostStable": True,
            "repositoryStatusPrePostStable": True,
        },
        "claimBoundary": {
            "provesSkillLoaderInvocation": False,
            "provesSkillInstructionsReachedModel": False,
            "provesSkillBehavior": False,
            "provesSkillNetValueOrSuperiority": False,
            "provesFiveArmAblationOutcome": False,
            "provesCrossHostPortability": False,
            "provesProductionReadiness": False,
        },
    }


class CodexAppServerSelectedSkillExposureProbeTests(unittest.TestCase):
    def test_select_exact_skill_requires_name_path_and_scope(self) -> None:
        target = Path("C:/skills/grill-me/SKILL.md")
        skills = [
            row("grill-me", target.as_posix()),
            row("grill-me", "C:/other/grill-me/SKILL.md"),
        ]

        selected = select_exact_skill(
            skills,
            name="grill-me",
            expected_path=target,
        )

        self.assertEqual(target.as_posix(), selected["path"])

    def test_compare_selected_inventory_accepts_one_enabled_user(self) -> None:
        path = "C:/skills/grill-me/SKILL.md"
        control = [
            row("grill-me", path),
            row("other", "C:/skills/other/SKILL.md"),
            row(
                "system",
                "C:/system/SKILL.md",
                scope="system",
            ),
        ]
        selected = [
            row("grill-me", path),
            row("other", "C:/skills/other/SKILL.md", enabled=False),
            row(
                "system",
                "C:/system/SKILL.md",
                scope="system",
            ),
        ]

        comparison = compare_selected_inventory(
            control,
            selected,
            selected_path=path,
        )

        self.assertTrue(comparison["sameIdentitySet"])
        self.assertTrue(comparison["onlySelectedUserSkillEnabled"])
        self.assertTrue(comparison["allOtherUserSkillsDisabled"])

    def test_validator_accepts_exposure_only_report(self) -> None:
        self.assertEqual([], validate_report(passing_report()))

    def test_validator_accepts_explicit_candidate_binding(self) -> None:
        report = passing_report()
        candidate_path = Path("C:/skills/disciplined-coding/SKILL.md")
        report["exposureComparison"]["controlUserSkillCount"] = 106
        report["selectedSkill"].update(
            {
                "name": "disciplined-coding",
                "path": candidate_path.as_posix(),
                "sha256": "a" * 64,
            }
        )

        self.assertEqual(
            [],
            validate_report(
                report,
                expected_name="disciplined-coding",
                expected_path=candidate_path,
                expected_sha256="a" * 64,
                expected_control_user_skill_count=106,
            ),
        )

    def test_validator_rejects_explicit_candidate_digest_drift(self) -> None:
        report = passing_report()

        self.assertIn(
            "fail-selected-skill-digest",
            validate_report(report, expected_sha256="b" * 64),
        )

    def test_validator_rejects_unselected_skill_leak(self) -> None:
        report = passing_report()
        report["exposureComparison"]["allOtherUserSkillsDisabled"] = False

        self.assertIn(
            "fail-unselected-user-skill-leak",
            validate_report(report),
        )

    def test_validator_rejects_loader_invocation_overclaim(self) -> None:
        report = copy.deepcopy(passing_report())
        report["claimBoundary"]["provesSkillLoaderInvocation"] = True

        self.assertIn("hard-fail-claim-boundary", validate_report(report))


if __name__ == "__main__":
    unittest.main()
