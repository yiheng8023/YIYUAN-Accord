from __future__ import annotations

import hashlib
import json
import unittest

from scripts.evaluate_skill_overlap_scenarios import (
    build_packet,
    evaluate_examples,
    evaluate_raw_response,
    load_fixture_document,
    public_packet,
)


class SkillOverlapScenarioTests(unittest.TestCase):
    def test_all_examples_match(self) -> None:
        results = evaluate_examples(load_fixture_document())
        self.assertEqual(19, len(results))
        self.assertEqual(
            [],
            [item for item in results if item["actual"] != item["expected"]],
        )

    def test_public_packet_excludes_private_oracle(self) -> None:
        packet = build_packet("int-amb-01-mixed")
        public = public_packet(packet)
        self.assertNotIn("oraclePrivate", public)
        self.assertEqual(64, len(public["packetSha256"]))
        self.assertFalse(public["authorityBoundary"]["write"])

    def test_raw_hash_is_recomputed(self) -> None:
        packet = build_packet("route-min-01-native")
        example = load_fixture_document()["fixtures"][2]["examples"][0]["response"]
        raw = json.dumps(example, sort_keys=True).encode("utf-8")
        result = evaluate_raw_response(
            raw,
            packet,
            {"rawResponseSha256": hashlib.sha256(raw).hexdigest()},
        )
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            result["rawResponseSha256"],
        )
        self.assertFalse(result["countsAsWeakAgentAcceptance"])

    def test_parent_fake_hash_is_rejected(self) -> None:
        packet = build_packet("route-min-01-native")
        example = load_fixture_document()["fixtures"][2]["examples"][0]["response"]
        raw = json.dumps(example, sort_keys=True).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "does not match bytes"):
            evaluate_raw_response(raw, packet, {"rawResponseSha256": "0" * 64})

    def test_unknown_fixture_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown overlap scenario fixture"):
            build_packet("missing")

    def test_deterministic_packet_never_counts_as_live_acceptance(self) -> None:
        packet = build_packet("close-press-01-local-green")
        example = load_fixture_document()["fixtures"][4]["examples"][0]["response"]
        raw = json.dumps(example, sort_keys=True).encode("utf-8")
        result = evaluate_raw_response(
            raw,
            packet,
            {"liveExecutionObserved": True},
        )
        self.assertTrue(result["liveExecutionObserved"])
        self.assertFalse(result["countsAsWeakAgentAcceptance"])

    def test_engineering_hidden_regression_uses_parent_test_evidence(self) -> None:
        packet = build_packet("eng-oracle-02-hidden-regression")
        document = load_fixture_document()
        example = document["fixtures"][7]["examples"][1]
        raw = json.dumps(example["response"], sort_keys=True).encode("utf-8")
        result = evaluate_raw_response(raw, packet, example["parentEvidence"])
        self.assertEqual("fail-eng-hidden-regression", result["status"])

    def test_resume_correction_invalidates_stale_brief(self) -> None:
        packet = build_packet("orch-resume-correction-01-composed")
        document = load_fixture_document()
        example = document["fixtures"][8]["examples"][1]
        raw = json.dumps(example["response"], sort_keys=True).encode("utf-8")
        result = evaluate_raw_response(raw, packet)
        self.assertEqual("fail-orch-stale-brief-dispatch", result["status"])


if __name__ == "__main__":
    unittest.main()
