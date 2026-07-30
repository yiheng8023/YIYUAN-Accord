from pathlib import Path
import tempfile
import unittest

from scripts.probe_codex_app_server_mcp_startup_profiles import (
    PROFILES,
    build_profile_config,
    classify_profile_result,
    run_probe,
)


ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / "scripts/mcp_lifecycle_sentinel.py"


class CodexAppServerMcpStartupProfilesProbeTests(unittest.TestCase):
    def test_profile_config_encodes_full_filtered_and_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            values = {
                name: build_profile_config(
                    Path("C:/Python/python.exe"),
                    SENTINEL,
                    root / f"{name}.jsonl",
                    root / f"{name}.marker",
                    profile,
                )
                for name, profile in PROFILES.items()
            }
        self.assertIn("enabled = true", values["full"])
        self.assertNotIn("enabled_tools", values["full"])
        self.assertIn('enabled_tools = ["identity", "hold"]', values["filtered"])
        self.assertIn('disabled_tools = ["hold"]', values["filtered"])
        self.assertIn("enabled = false", values["disabled"])

    def test_classifier_requires_each_profile_function_boundary(self) -> None:
        self.assertTrue(
            classify_profile_result("full", True, True, True, True, False, True)
        )
        self.assertTrue(
            classify_profile_result(
                "filtered", True, False, True, True, False, True
            )
        )
        self.assertTrue(
            classify_profile_result(
                "disabled", False, False, False, True, False, True
            )
        )
        self.assertFalse(
            classify_profile_result(
                "filtered", True, True, True, True, False, True
            )
        )
        self.assertFalse(
            classify_profile_result("disabled", False, False, True, True, False, True)
        )

    def test_probe_requires_two_repetitions_before_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, "at least two repetitions"):
                run_probe(Path(temp) / "probe", SENTINEL, None, 1, 1)


if __name__ == "__main__":
    unittest.main()
