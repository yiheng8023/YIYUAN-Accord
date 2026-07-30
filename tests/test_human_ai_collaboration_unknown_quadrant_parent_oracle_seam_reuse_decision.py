from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_human_ai_collaboration_unknown_quadrant_parent_oracle_seam_reuse_decision import (
    DOCUMENTATION_PATH,
    DECISION_PATH,
    NARRATIVE_PATHS,
    ROOT,
    validate_decision,
)


def load() -> dict:
    return json.loads((ROOT / DECISION_PATH).read_text(encoding="utf-8"))


class UnknownQuadrantParentOracleSeamReuseDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load()

    def test_current_decision_is_valid(self) -> None:
        validate_decision(self.document)

    def test_rejects_source_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source binding digest"):
            validate_decision(document)

    def test_rejects_new_adapter_need_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["reuseDecision"]["genericNewOracleAdapterNecessary"] = True
        with self.assertRaisesRegex(RuntimeError, "reuse decision"):
            validate_decision(document)

    def test_rejects_live_integration_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["reuseDecision"][
            "liveProtocolSpecificIntegrationImplemented"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "reuse decision"):
            validate_decision(document)

    def test_rejects_generic_runtime_override(self) -> None:
        document = copy.deepcopy(self.document)
        document["reuseDecision"][
            "genericArbitraryRuntimeOverrideDesirable"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "reuse decision"):
            validate_decision(document)

    def test_rejects_self_authoring_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["reuseDecision"][
            "selfAuthoredSkillOrAdapterAuthorized"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "reuse decision"):
            validate_decision(document)

    def test_rejects_claim_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["liveIntegrationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_decision(document)

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
                    "parent-oracle seam reuse decision",
                    "parent-oracle seam notes",
                )
            target.write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "narrative pointer"):
            validate_decision(self.document, root=root)


if __name__ == "__main__":
    unittest.main()
