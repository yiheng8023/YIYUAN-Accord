from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts.probe_codex_app_server_skill_treatment_fidelity import (
    ARM_ORDERS,
    EFFORT,
    MODEL,
    SKILL_NAME,
    build_canary_skill,
    classify_report,
    compare_effective_inventory,
    select_canary,
)


def passing_report() -> dict:
    repetitions = []
    for pair_index, order in enumerate(ARM_ORDERS, start=1):
        arms = []
        for arm_index, arm in enumerate(order, start=1):
            selected = arm == "selected-structured-skill"
            arms.append(
                {
                    "arm": arm,
                    "exactResponseMatched": True,
                    "thread": {
                        "threadId": f"thread-{pair_index}-{arm_index}",
                        "model": MODEL,
                        "reasoningEffort": EFFORT,
                        "approvalPolicy": "never",
                        "providerFallbackAllowed": False,
                    },
                    "inventory": {
                        "sameIdentitySet": True,
                        "canaryIdentityCount": 1,
                        "enabledConfigurableSkillCount": 1 if selected else 0,
                        "expectedOnlyCanaryEnabled": True,
                        "allNonConfigurableStatesPreserved": True,
                    },
                    "turn": {"forbiddenItemTypesObserved": []},
                }
            )
        repetitions.append(
            {
                "pairId": f"pair-{pair_index}",
                "armOrder": list(order),
                "tokenAbsentFromPublicSurfaces": True,
                "arms": arms,
                "privateOracleRevealedAfterRun": {
                    "token": f"AAH_BODY_ONLY_TOKEN_{pair_index}"
                },
            }
        )
    return {
        "repetitions": repetitions,
        "globalConfigStable": True,
        "repositoryStatusStable": True,
        "allCanaryBodiesStable": True,
    }


class CodexSkillTreatmentFidelityProbeTests(unittest.TestCase):
    def test_canary_token_exists_only_in_body(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            pair_root = Path(raw) / "pair"
            token = "AAH_BODY_ONLY_0123456789ABCDEF"
            canary = build_canary_skill(pair_root, token)
            body = Path(canary["skillPath"]).read_text(encoding="utf-8")
            self.assertIn(token, body)
            self.assertNotIn(
                token,
                str(canary["publicSurfaces"]),
            )

    def test_canary_builder_refuses_nonempty_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            pair_root = Path(raw) / "pair"
            pair_root.mkdir()
            (pair_root / "existing.txt").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "must not already"):
                build_canary_skill(pair_root, "TOKEN")

    def test_select_canary_accepts_repo_scope(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = (
                Path(raw)
                / ".agents"
                / "skills"
                / SKILL_NAME
                / "SKILL.md"
            )
            inventory = [
                {
                    "name": SKILL_NAME,
                    "path": str(path),
                    "scope": "repo",
                    "enabled": True,
                }
            ]
            selected = select_canary(inventory, expected_path=path)
            self.assertEqual(selected["scope"], "repo")

    def test_select_canary_accepts_equivalent_short_path_alias(self) -> None:
        expected = Path("C:/Users/runneradmin/AppData/Local/Temp/canary/SKILL.md")
        inventory = [
            {
                "name": SKILL_NAME,
                "path": "C:/Users/RUNNER~1/AppData/Local/Temp/canary/SKILL.md",
                "scope": "repo",
                "enabled": True,
            }
        ]
        with mock.patch("os.path.samefile", return_value=True):
            selected = select_canary(inventory, expected_path=expected)
        self.assertEqual(selected["scope"], "repo")

    def test_inventory_comparison_isolates_repo_canary(self) -> None:
        canary_path = "C:/tmp/trial/.agents/skills/treatment-fidelity-canary/SKILL.md"
        control = [
            {
                "name": SKILL_NAME,
                "path": canary_path,
                "scope": "repo",
                "enabled": True,
            },
            {
                "name": "other",
                "path": "C:/Users/example/.agents/skills/other/SKILL.md",
                "scope": "user",
                "enabled": True,
            },
            {
                "name": "system",
                "path": "C:/runtime/system/SKILL.md",
                "scope": "system",
                "enabled": True,
            },
        ]
        effective = copy.deepcopy(control)
        effective[1]["enabled"] = False
        comparison = compare_effective_inventory(
            control,
            effective,
            canary_path=canary_path,
            selected=True,
        )
        self.assertTrue(comparison["sameIdentitySet"])
        self.assertTrue(comparison["expectedOnlyCanaryEnabled"])
        self.assertTrue(comparison["allNonConfigurableStatesPreserved"])

    def test_classifier_accepts_three_clean_pairs(self) -> None:
        self.assertEqual(classify_report(passing_report()), [])

    def test_classifier_rejects_control_token_leak(self) -> None:
        report = passing_report()
        report["repetitions"][0]["arms"][0]["exactResponseMatched"] = False
        self.assertIn("fail-exact-response", classify_report(report))

    def test_classifier_rejects_reused_thread(self) -> None:
        report = passing_report()
        report["repetitions"][1]["arms"][0]["thread"]["threadId"] = (
            report["repetitions"][0]["arms"][0]["thread"]["threadId"]
        )
        self.assertIn("fail-distinct-thread", classify_report(report))

    def test_classifier_rejects_global_config_drift(self) -> None:
        report = passing_report()
        report["globalConfigStable"] = False
        self.assertIn("fail-global-config-drift", classify_report(report))


if __name__ == "__main__":
    unittest.main()
