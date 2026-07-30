import json
import unittest
from pathlib import Path

from scripts.evaluate_git_host_preflight_evidence import evaluate_fixture_document


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/git-host-preflight-evidence-2026-07-23.json"


class GitHostPreflightEvidenceTests(unittest.TestCase):
    def test_all_synthetic_fixtures_match_and_never_upgrade_to_live_evidence(self) -> None:
        document = json.loads(FIXTURES.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(23, len(results))
        for result in results:
            with self.subTest(result["id"]):
                self.assertEqual(result["expectedStatus"], result["actualStatus"])
                self.assertEqual(
                    set(result["expectedFailureCodes"]),
                    set(result["actualFailureCodes"]),
                )
                self.assertFalse(result["countsAsLiveHostApprovalEvidence"])
                self.assertFalse(result["countsAsLiveBoundRepositorySafety"])
                self.assertFalse(result["countsAsWeakAgentAcceptance"])


if __name__ == "__main__":
    unittest.main()
