from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.probe_codex_app_server_skill_root_collision import (
    build_readonly_inventory_command,
    classify_collision_rows,
    observe_tree,
    validate_report,
    write_report,
)


def skill(name: str, path: Path, *, enabled: bool = True) -> dict:
    return {
        "name": name,
        "path": path.as_posix(),
        "scope": "user",
        "enabled": enabled,
    }


class CodexAppServerSkillRootCollisionProbeTests(unittest.TestCase):
    def test_command_disables_plugins_and_static_mcps_without_model_config(self) -> None:
        command = build_readonly_inventory_command("C:/tools/codex.exe")

        self.assertIn("app-server", command)
        self.assertIn("plugins", command)
        self.assertIn("mcp_servers={}", command)
        self.assertNotIn("model_reasoning_effort", " ".join(command))
        self.assertNotIn("skills.config", " ".join(command))

    def test_classifies_common_and_cc_canonical_target_as_both_listed(self) -> None:
        home = Path("C:/Users/fixture")
        rows = [
            skill(
                "code-review",
                home / ".agents" / "skills" / "code-review" / "SKILL.md",
            ),
            skill(
                "code-review",
                home / ".cc-switch" / "skills" / "code-review" / "SKILL.md",
            ),
        ]

        result = classify_collision_rows(rows, ["code-review"], home=home)

        self.assertEqual("both-listed", result[0]["listingClassification"])
        self.assertTrue(result[0]["commonRootListed"])
        self.assertTrue(result[0]["dedicatedConsumerListed"])
        self.assertFalse(result[0]["provesInstructionDeliveryPrecedence"])

    def test_classifies_deduplicated_ambiguous_path(self) -> None:
        home = Path("C:/Users/fixture")
        rows = [skill("code-review", Path("C:/elsewhere/code-review/SKILL.md"))]

        result = classify_collision_rows(rows, ["code-review"], home=home)

        self.assertEqual(
            "deduplicated-ambiguous",
            result[0]["listingClassification"],
        )

    def test_classifies_cc_canonical_target_as_codex_only(self) -> None:
        home = Path("C:/Users/fixture")
        rows = [
            skill(
                "handoff",
                home / ".cc-switch" / "skills" / "handoff" / "SKILL.md",
            )
        ]

        result = classify_collision_rows(rows, ["handoff"], home=home)

        self.assertEqual("codex-only", result[0]["listingClassification"])
        self.assertFalse(result[0]["commonRootListed"])
        self.assertTrue(result[0]["dedicatedConsumerListed"])

    def test_tree_observation_changes_when_direct_payload_changes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "skills"
            payload = root / "alpha" / "SKILL.md"
            payload.parent.mkdir(parents=True)
            payload.write_text("one", encoding="utf-8")
            before = observe_tree(root)

            payload.write_text("two", encoding="utf-8")
            after = observe_tree(root)

        self.assertNotEqual(before["manifestSha256"], after["manifestSha256"])

    def test_report_rejects_any_thread_turn_model_or_mutation(self) -> None:
        report = {
            "requestBoundary": {
                "sentMethods": ["initialize", "initialized", "skills/list"],
                "threadStartCount": 0,
                "turnStartCount": 0,
                "modelRequestCount": 0,
            },
            "mutationBoundary": {
                "allObservedSurfacesStable": True,
                "globalConfigWritten": False,
                "managerWritten": False,
                "consumerRootsWritten": False,
            },
            "claimBoundary": {
                "provesListingPathIdentity": True,
                "provesInstructionDeliveryPrecedence": False,
                "provesSkillLoaderInvocation": False,
                "provesSkillBehavior": False,
                "provesManagerUpdateSafety": False,
            },
        }

        self.assertEqual([], validate_report(report))
        report["requestBoundary"]["threadStartCount"] = 1
        self.assertIn("hard-fail-thread-created", validate_report(report))

    def test_report_writer_uses_repository_lf_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "REPORT.json"

            write_report(output, {"status": "pass"})

            payload = output.read_bytes()
        self.assertTrue(payload.endswith(b"\n"))
        self.assertNotIn(b"\r\n", payload)


if __name__ == "__main__":
    unittest.main()
