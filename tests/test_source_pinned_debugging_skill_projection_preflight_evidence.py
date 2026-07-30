from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_source_pinned_debugging_skill_projection_preflight_evidence import (
    ROOT,
    validate_evidence,
)


class SourcePinnedDebuggingSkillProjectionPreflightEvidenceTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.evidence = json.loads(
            (
                ROOT
                / "registry"
                / "source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24.json"
            ).read_text(encoding="utf-8")
        )
        self.protocol = json.loads(
            (
                ROOT
                / "registry"
                / "source-pinned-debugging-skill-projection-protocol-2026-07-24.json"
            ).read_text(encoding="utf-8")
        )

    def test_current_evidence_is_valid(self) -> None:
        self.assertEqual(
            [],
            validate_evidence(self.evidence, protocol=self.protocol),
        )

    def test_rejects_turn_promotion(self) -> None:
        document = copy.deepcopy(self.evidence)
        document["results"][0]["turnStarted"] = True
        self.assertIn(
            "hard-fail-turn:matt.current-diagnosing-bugs",
            validate_evidence(document, protocol=self.protocol),
        )

    def test_rejects_superiority_claim(self) -> None:
        document = copy.deepcopy(self.evidence)
        document["claimBoundary"]["candidateSuperiorityProved"] = True
        self.assertIn(
            "hard-fail-claim-promotion",
            validate_evidence(document, protocol=self.protocol),
        )


if __name__ == "__main__":
    unittest.main()
