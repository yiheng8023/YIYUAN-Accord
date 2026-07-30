from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_human_ai_collaboration_unknown_quadrant_attribution_oracle_poc_evidence import (
    DOCUMENTATION_PATH,
    EVIDENCE_PATH,
    NARRATIVE_PATHS,
    ROOT,
    validate_evidence,
)


def load() -> dict:
    return json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))


class UnknownQuadrantAttributionOraclePocEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load()

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document)

    def test_rejects_source_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source binding digest"):
            validate_evidence(document)

    def test_rejects_fixture_count_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["fixtureResult"]["matchedExpectedCount"] = 23
        with self.assertRaisesRegex(RuntimeError, "fixture result"):
            validate_evidence(document)

    def test_rejects_hard_standard_credit(self) -> None:
        document = copy.deepcopy(self.document)
        document["attributionContract"][
            "hardStandardInterceptionCanCreditMethod"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "attribution firewall"):
            validate_evidence(document)

    def test_rejects_terminal_correctness_rescue(self) -> None:
        document = copy.deepcopy(self.document)
        document["attributionContract"][
            "terminalCorrectnessCanRescueProcessLoss"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "attribution firewall"):
            validate_evidence(document)

    def test_rejects_luna_promoted_to_weak_acceptance(self) -> None:
        document = copy.deepcopy(self.document)
        document["weakRouteContract"]["primaryWeakAcceptanceModel"] = (
            "gpt-5.6-luna"
        )
        with self.assertRaisesRegex(RuntimeError, "weak-route"):
            validate_evidence(document)

    def test_rejects_self_authoring_authority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["residualGapContract"][
            "thresholdSatisfactionAuthorizesSelfAuthoring"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "residual-gap"):
            validate_evidence(document)

    def test_rejects_live_dispatch_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["readyForLiveWeakDispatch"] = True
        with self.assertRaisesRegex(RuntimeError, "live or self-build"):
            validate_evidence(document)

    def test_rejects_claim_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["mattBehaviorOrValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_evidence(document)

    def test_rejects_missing_narrative_pointer(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for binding in self.document["sourceBindings"]:
            source = ROOT / binding["path"]
            target = root / binding["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        documentation = root / DOCUMENTATION_PATH
        documentation.parent.mkdir(parents=True, exist_ok=True)
        documentation.write_bytes((ROOT / DOCUMENTATION_PATH).read_bytes())
        first = sorted(NARRATIVE_PATHS)[0]
        for path in NARRATIVE_PATHS:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            content = (ROOT / path).read_text(encoding="utf-8")
            if path == first:
                content = content.replace(
                    "unknown-quadrant attribution-oracle PoC",
                    "unknown-quadrant oracle notes",
                )
            target.write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "narrative pointer"):
            validate_evidence(self.document, root=root)


if __name__ == "__main__":
    unittest.main()
