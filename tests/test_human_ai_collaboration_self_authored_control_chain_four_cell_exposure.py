from __future__ import annotations

import copy
import unittest

from scripts.probe_human_ai_collaboration_self_authored_control_chain_four_cell_exposure import (
    CELL_FACTORS,
    _isolated_strict_command,
    validate_report,
)


class SelfAuthoredControlChainFourCellExposureTests(unittest.TestCase):
    def test_strict_config_is_inserted_once(self) -> None:
        command = _isolated_strict_command(["codex", "app-server", "--stdio"])
        self.assertEqual(
            ["codex", "app-server", "--stdio", "--strict-config"],
            command,
        )
        self.assertEqual(command, _isolated_strict_command(command))

    def test_isolated_command_removes_incomplete_mcp_disable_tables(self) -> None:
        command = _isolated_strict_command(
            [
                "codex",
                "app-server",
                "--stdio",
                "-c",
                "skills.config=[]",
                "-c",
                "mcp_servers.codegraph.enabled=false",
                "-c",
                "analytics.enabled=false",
            ]
        )
        self.assertNotIn("mcp_servers.codegraph.enabled=false", command)
        self.assertIn("skills.config=[]", command)
        self.assertIn("analytics.enabled=false", command)

    def base_report(self) -> dict:
        cells = []
        for cell_id, (chain, hook) in CELL_FACTORS.items():
            cells.append(
                {
                    "cellId": cell_id,
                    "chainFactor": chain,
                    "hookFactor": hook,
                    "inventory": {
                        "enabledConfigurableSkillCount": (
                            0 if chain == "hard-only" else 3
                        ),
                        "sameIdentitySet": True,
                        "onlyExpectedConfigurableSkillsEnabled": True,
                        "allNonConfigurableStatesPreserved": True,
                    },
                    "hookDirectEvidence": {
                        "returnCode": 0,
                        "stderrBytes": 0,
                        "stdoutBytes": 0 if hook == "off" else 428,
                    },
                }
            )
        return {
            "schema": 1,
            "probeId": "self-authored-control-chain-four-cell-exposure-v1",
            "status": "preflight-pass-no-turn",
            "projection": {"requiredFileCount": 5, "requiredSkillCount": 3},
            "cells": cells,
            "threadStarted": False,
            "turnStarted": False,
            "modelRequestSent": False,
            "stability": {
                "projectionTreeStable": True,
                "globalConfigStable": True,
                "liveHookRegistrationStable": True,
                "repositoryStatusStableDuringProbe": True,
                "projectionRemovedAfterEvidenceCapture": True,
                "isolatedCodexHomeRemovedAfterEvidenceCapture": True,
            },
            "decision": {
                "dependencyCompleteFourCellExposureProved": True,
                "loaderInvocationProved": False,
                "skillInstructionsReachedModelProved": False,
                "hookHostConsumptionProved": False,
                "behavioralCausationProved": False,
                "hookNetValueProved": False,
                "selfAuthoredChainValueProved": False,
                "weakModelRunAuthorized": False,
                "programCloseoutSupported": False,
            },
        }

    def test_valid_report_shape_passes(self) -> None:
        self.assertEqual([], validate_report(self.base_report()))

    def test_missing_cell_fails_closed(self) -> None:
        report = self.base_report()
        report["cells"].pop()
        self.assertIn("fail-cell-coverage", validate_report(report))

    def test_body_only_projection_fails_closed(self) -> None:
        report = self.base_report()
        report["projection"]["requiredFileCount"] = 3
        self.assertIn(
            "fail-dependency-complete-projection", validate_report(report)
        )

    def test_hard_only_exposure_fails_closed(self) -> None:
        report = self.base_report()
        report["cells"][0]["inventory"]["enabledConfigurableSkillCount"] = 3
        failures = validate_report(report)
        self.assertTrue(
            any(code.startswith("fail-enabled-count:") for code in failures)
        )

    def test_hook_off_output_fails_closed(self) -> None:
        report = self.base_report()
        off = next(
            row for row in report["cells"] if row["hookFactor"] == "off"
        )
        off["hookDirectEvidence"]["stdoutBytes"] = 428
        failures = validate_report(report)
        self.assertTrue(
            any(code.startswith("fail-hook-off-output:") for code in failures)
        )

    def test_claim_promotion_fails_closed(self) -> None:
        report = self.base_report()
        report["decision"]["hookNetValueProved"] = True
        failures = validate_report(report)
        self.assertIn(
            "hard-fail-claim-promotion:hookNetValueProved", failures
        )


if __name__ == "__main__":
    unittest.main()
