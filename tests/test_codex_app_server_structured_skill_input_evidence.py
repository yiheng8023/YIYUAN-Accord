from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_codex_app_server_structured_skill_input_evidence import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class CodexStructuredSkillInputEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_evidence_is_valid(self) -> None:
        validate_evidence(self.document, root=ROOT)

    def test_rejects_loader_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesSkillLoaderInvocation"] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_evidence(document, root=ROOT)

    def test_rejects_text_fallback_as_structured(self) -> None:
        document = copy.deepcopy(self.document)
        document["treatment"]["structuredSkillInputSent"] = False
        with self.assertRaisesRegex(RuntimeError, "treatment fidelity"):
            validate_evidence(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
