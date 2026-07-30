from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_human_ai_collaboration_unknown_quadrant_packet_overlay_poc_evidence import (
    DOCUMENTATION_PATH,
    EVIDENCE_PATH,
    NARRATIVE_PATHS,
    ROOT,
    validate_evidence,
)


def load() -> dict:
    return json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))


class UnknownQuadrantPacketOverlayPocEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load()

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document)

    def test_rejects_source_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source binding digest"):
            validate_evidence(document)

    def test_rejects_fault_rejection_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["compatibilityResult"]["expectedFaultRejectionCount"] = 6
        with self.assertRaisesRegex(RuntimeError, "fault rejection"):
            validate_evidence(document)

    def test_rejects_fixture_gap_as_product_gap(self) -> None:
        document = copy.deepcopy(self.document)
        document["unknownKnownsPacketResult"][
            "productCapabilityResidualGapProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "Unknown Knowns"):
            validate_evidence(document)

    def test_rejects_live_dispatch_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["readyForLiveWeakDispatch"] = True
        with self.assertRaisesRegex(RuntimeError, "live or self-build"):
            validate_evidence(document)

    def test_rejects_self_authoring_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["selfAuthoringAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "live or self-build"):
            validate_evidence(document)

    def test_rejects_claim_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["humanPreferenceProved"] = True
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
        overlay = json.loads(
            (
                ROOT
                / "tests/fixtures/human-ai-collaboration-unknown-quadrant-"
                "packet-overlay-2026-07-27.json"
            ).read_text(encoding="utf-8")
        )
        for binding in overlay["sourceBindings"]:
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
                    "unknown-quadrant packet-overlay PoC",
                    "unknown-quadrant packet notes",
                )
            target.write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "narrative pointer"):
            validate_evidence(self.document, root=root)


if __name__ == "__main__":
    unittest.main()
