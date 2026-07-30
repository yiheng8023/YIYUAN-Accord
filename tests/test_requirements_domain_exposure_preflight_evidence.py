from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_requirements_domain_exposure_preflight_evidence import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class RequirementsDomainExposurePreflightEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))

    def validate(self, document: dict | None = None) -> None:
        validate_evidence(document or self.document, root=ROOT)

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_task_turn_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["processBoundary"]["turnStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "process boundary"):
            self.validate(document)

    def test_rejects_loader_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesSkillLoaderInvocation"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            self.validate(document)

    def test_rejects_selected_count_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["selectedProfile"]["enabledConfigurableSkillCount"] = 2
        with self.assertRaisesRegex(RuntimeError, "selected profile"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
