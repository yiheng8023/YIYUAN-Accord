from __future__ import annotations

import unittest

from scripts.evaluate_git_guardrails_interception_decision import (
    build_packet,
    evaluate_fixture_document,
    load_fixture_document,
)


class GitGuardrailsInterceptionDecisionTests(unittest.TestCase):
    def test_all_fixtures_match(self) -> None:
        results = evaluate_fixture_document(load_fixture_document())
        self.assertEqual(9, len(results))
        self.assertEqual(
            [],
            [
                item["id"]
                for item in results
                if any(
                    item["actual"].get(key) != value
                    for key, value in item["expected"].items()
                )
            ],
        )

    def test_packet_digest_is_bound(self) -> None:
        packet = build_packet(load_fixture_document())
        self.assertEqual(64, len(packet["packetSha256"]))
        self.assertEqual(["git push"], packet["decision"]["nativeGitHookCoverage"])

    def test_fixtures_never_count_as_live_or_weak_evidence(self) -> None:
        for item in evaluate_fixture_document(load_fixture_document()):
            self.assertFalse(item["actual"]["countsAsLiveInterceptionProof"])
            self.assertFalse(item["actual"]["countsAsCrossCallerProtectionProof"])
            self.assertFalse(item["actual"]["countsAsWeakAgentAcceptance"])


if __name__ == "__main__":
    unittest.main()
