import json
from pathlib import Path
import unittest

from scripts.evaluate_mcp_task_lifecycle_evidence import (
    evaluate_fixture_document,
    evaluate_task_lifecycle_evidence,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "tests/fixtures/mcp-task-lifecycle-evidence-2026-07-23.json"


class McpTaskLifecycleEvidenceTests(unittest.TestCase):
    def test_predeclared_fixtures_match(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(22, len(results))
        self.assertEqual([], [item for item in results if item["expected"] != item["actual"]])

    def test_synthetic_never_becomes_live_proof(self) -> None:
        result = evaluate_task_lifecycle_evidence(
            {
                "evidenceMode": "synthetic-offline",
                "scenarioBound": True,
                "evidenceSchemaPinned": True,
            }
        )
        self.assertFalse(result["countsAsLiveHostProof"])
        self.assertFalse(result["countsAsWeakAgentAcceptance"])

    def test_unknown_dimension_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported lifecycle dimensions"):
            evaluate_task_lifecycle_evidence(
                {
                    "evidenceMode": "synthetic-offline",
                    "scenarioBound": True,
                    "evidenceSchemaPinned": True,
                    "claimedDimensions": ["magic"],
                }
            )


if __name__ == "__main__":
    unittest.main()
