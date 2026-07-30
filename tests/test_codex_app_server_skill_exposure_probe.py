from __future__ import annotations

import copy
from pathlib import Path
import unittest

from scripts.probe_codex_app_server_skill_exposure import (
    EFFORT,
    MARKER,
    MODEL,
    build_command,
    build_disable_override,
    build_skill_config_override,
    compare_inventories,
    extract_turn,
    initialize,
    summarize_turn,
    validate_probe_report,
)


def skill(
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
    repository = Path.cwd().resolve()
    return {
        "repository": {"path": repository.as_posix()},
        "exposureComparison": {
            "sameIdentitySet": True,
            "userSkillCount": 2,
            "allControlUserSkillsEnabled": True,
            "allDisabledUserSkillsDisabled": True,
            "userStateTransitionCount": 2,
            "nonUserSkillCount": 1,
            "allNonUserStatesPreserved": True,
        },
        "threadTelemetry": {
            "model": MODEL,
            "reasoningEffort": EFFORT,
            "modelProvider": "openai",
            "approvalPolicy": "never",
            "sandbox": {"type": "readOnly", "networkAccess": False},
            "instructionSources": [
                (Path.home() / ".codex" / "AGENTS.md").as_posix(),
                (repository / "AGENTS.md").as_posix(),
            ],
        },
        "markerTurn": {
            "status": "completed",
            "exactMarkerMatch": True,
            "forbiddenItemTypesObserved": [],
        },
        "mutationBoundary": {
            "configPrePostStable": True,
            "repositoryStatusPrePostStable": True,
        },
        "claimBoundary": {
            "provesCrossHostPortability": False,
            "provesMattOrSuperpowersBehavior": False,
            "provesFiveArmAblationOutcome": False,
            "provesDynamicMcpLifecycle": False,
            "provesAutomaticThreadCreation": False,
            "provesGlobalConfigTransaction": False,
            "provesProductionReadiness": False,
        },
    }


class CodexAppServerSkillExposureProbeTests(unittest.TestCase):
    def test_initialize_opts_into_experimental_api_only_when_requested(self) -> None:
        class Session:
            def __init__(self) -> None:
                self.messages: list[dict] = []

            def send(self, message: dict) -> None:
                self.messages.append(message)

            def wait_for_response(self, request_id: int) -> dict:
                self.assert_request_id = request_id
                return {"userAgent": "test"}

        default_session = Session()
        initialize(default_session)
        experimental_session = Session()
        initialize(experimental_session, experimental_api=True)

        self.assertNotIn(
            "capabilities",
            default_session.messages[0]["params"],
        )
        self.assertEqual(
            {"experimentalApi": True},
            experimental_session.messages[0]["params"]["capabilities"],
        )
        self.assertEqual({"method": "initialized"}, default_session.messages[1])
        self.assertEqual(
            {"method": "initialized"},
            experimental_session.messages[1],
        )

    def test_build_command_can_keep_local_plugins_only(self) -> None:
        command = build_command(
            "C:/tools/codex.exe",
            plugin_features_to_disable=(
                "remote_plugin",
                "apps",
                "plugin_sharing",
            ),
        )

        self.assertNotIn("plugins", command)
        self.assertIn("remote_plugin", command)
        self.assertIn("apps", command)
        self.assertIn("plugin_sharing", command)

    def test_disable_override_is_deterministic_and_deduplicates_paths(self) -> None:
        rows = [
            skill("zeta", r"C:\skills\zeta\SKILL.md"),
            skill("alpha", r"C:\skills\alpha\SKILL.md"),
            skill("ALPHA-COPY", r"c:\skills\alpha\SKILL.md"),
        ]

        override = build_disable_override(rows)

        self.assertTrue(override.startswith("skills.config=["))
        self.assertEqual(2, override.count("enabled=false"))
        self.assertLess(override.index("alpha/SKILL.md"), override.index("zeta/SKILL.md"))
        self.assertNotIn("\\", override)

    def test_selected_override_enables_only_exact_selected_path(self) -> None:
        rows = [
            skill("alpha", r"C:\skills\alpha\SKILL.md"),
            skill("beta", r"C:\skills\beta\SKILL.md"),
        ]

        override = build_skill_config_override(
            rows,
            enabled_paths={"C:/skills/beta/SKILL.md"},
        )

        self.assertIn(
            '{path="C:/skills/alpha/SKILL.md",enabled=false}',
            override,
        )
        self.assertIn(
            '{path="C:/skills/beta/SKILL.md",enabled=true}',
            override,
        )
        self.assertEqual(1, override.count("enabled=true"))

    def test_selected_override_rejects_path_outside_inventory(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "absent from the inventory"):
            build_skill_config_override(
                [skill("alpha", "C:/skills/alpha/SKILL.md")],
                enabled_paths={"C:/skills/missing/SKILL.md"},
            )

    def test_compare_inventories_requires_exact_user_transition(self) -> None:
        control = [
            skill("alpha", "C:/alpha/SKILL.md"),
            skill(
                "system",
                "C:/system/SKILL.md",
                scope="system",
                enabled=True,
            ),
        ]
        disabled = [
            skill("alpha", "C:/alpha/SKILL.md", enabled=False),
            skill(
                "system",
                "C:/system/SKILL.md",
                scope="system",
                enabled=True,
            ),
        ]

        comparison = compare_inventories(control, disabled)

        self.assertTrue(comparison["sameIdentitySet"])
        self.assertTrue(comparison["allDisabledUserSkillsDisabled"])
        self.assertTrue(comparison["allNonUserStatesPreserved"])
        self.assertEqual(1, comparison["userStateTransitionCount"])

    def test_summarize_turn_uses_completed_item_notifications(self) -> None:
        notifications = [
            {"item": {"id": "u", "type": "userMessage", "content": []}},
            {"item": {"id": "r", "type": "reasoning", "summary": []}},
            {"item": {"id": "a", "type": "agentMessage", "text": MARKER}},
        ]
        turn = {
            "id": "turn",
            "status": "completed",
            "itemsView": "eventStreamCompletedItems",
            "items": [row["item"] for row in notifications],
        }

        summary = summarize_turn(turn, notifications)

        self.assertTrue(summary["exactMarkerMatch"])
        self.assertEqual([], summary["forbiddenItemTypesObserved"])
        self.assertEqual(
            ["userMessage", "reasoning", "agentMessage"],
            summary["itemCompletedNotificationTypes"],
        )

    def test_extract_turn_rejects_missing_target(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exactly one target turn"):
            extract_turn({"thread": {"turns": []}}, "missing")

    def test_validator_accepts_narrow_passing_report(self) -> None:
        self.assertEqual([], validate_probe_report(passing_report()))

    def test_validator_rejects_model_or_effort_substitution(self) -> None:
        report = passing_report()
        report["threadTelemetry"]["model"] = "gpt-5.6-sol"
        report["threadTelemetry"]["reasoningEffort"] = "high"

        failures = validate_probe_report(report)

        self.assertIn("fail-model-mismatch", failures)
        self.assertIn("fail-reasoning-effort-mismatch", failures)

    def test_validator_rejects_user_skill_leak(self) -> None:
        report = passing_report()
        report["exposureComparison"]["allDisabledUserSkillsDisabled"] = False
        report["exposureComparison"]["userStateTransitionCount"] = 1

        failures = validate_probe_report(report)

        self.assertIn("fail-disabled-user-skill-leak", failures)
        self.assertIn("fail-user-skill-transition-count", failures)

    def test_validator_rejects_forbidden_tool_action(self) -> None:
        report = passing_report()
        report["markerTurn"]["forbiddenItemTypesObserved"] = ["mcpToolCall"]

        self.assertIn(
            "hard-fail-forbidden-action-observed",
            validate_probe_report(report),
        )

    def test_validator_rejects_global_or_repository_drift(self) -> None:
        report = passing_report()
        report["mutationBoundary"]["configPrePostStable"] = False
        report["mutationBoundary"]["repositoryStatusPrePostStable"] = False

        failures = validate_probe_report(report)

        self.assertIn("hard-fail-global-config-drift", failures)
        self.assertIn("hard-fail-repository-posture-drift", failures)

    def test_validator_rejects_claim_promotion(self) -> None:
        report = copy.deepcopy(passing_report())
        report["claimBoundary"]["provesFiveArmAblationOutcome"] = True

        self.assertIn(
            "hard-fail-claim-boundary",
            validate_probe_report(report),
        )


if __name__ == "__main__":
    unittest.main()
