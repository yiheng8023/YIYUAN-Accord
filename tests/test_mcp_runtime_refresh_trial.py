from pathlib import Path
import json
import unittest

from scripts.evaluate_mcp_runtime_refresh_trial import (
    evaluate_fixture_document,
    evaluate_refresh_trial,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests/fixtures/mcp-runtime-refresh-trial-2026-07-19.json"


class McpRuntimeRefreshTrialTests(unittest.TestCase):
    def test_all_predeclared_decision_fixtures_pass(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(17, len(results))
        self.assertEqual([], [item for item in results if item["expected"] != item["actual"]])

    def test_rejects_unknown_process_ownership_state(self) -> None:
        facts = {
            "hostBound": True,
            "protocolSurfacePinned": True,
            "statusListInvoked": True,
            "appServerStartupAuthorized": True,
            "statusBeforeRecorded": True,
            "processOwnershipState": "guessed",
        }
        with self.assertRaisesRegex(ValueError, "unsupported process ownership state"):
            evaluate_refresh_trial(facts)

    def test_static_schema_never_proves_live_refresh(self) -> None:
        self.assertEqual(
            "fail-static-interface-promoted-to-live-behavior",
            evaluate_refresh_trial(
                {
                    "hostBound": True,
                    "protocolSurfacePinned": True,
                    "midSessionRefreshClaimed": True,
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
