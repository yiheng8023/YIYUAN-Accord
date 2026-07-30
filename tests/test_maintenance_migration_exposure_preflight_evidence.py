from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_maintenance_migration_exposure_preflight_evidence import (
    EVIDENCE_PATH,
    validate_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class MaintenanceMigrationExposurePreflightEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_evidence(document or self.document, root=ROOT)

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_selected_skill_leak(self) -> None:
        document = copy.deepcopy(self.document)
        document["selectedProfile"]["enabledConfigurableSkillCount"] = 2
        with self.assertRaisesRegex(RuntimeError, "selected exposure"):
            self.validate(document)

    def test_rejects_private_oracle_leak(self) -> None:
        document = copy.deepcopy(self.document)
        document["promptBoundary"]["privateSentinelsPresentInTrialFiles"] = [
            "Mira"
        ]
        with self.assertRaisesRegex(RuntimeError, "prompt/oracle"):
            self.validate(document)

    def test_rejects_invalid_attempt_counting(self) -> None:
        document = copy.deepcopy(self.document)
        document["invalidAttempts"][0]["countsAsCandidateResult"] = True
        with self.assertRaisesRegex(RuntimeError, "invalid-attempt"):
            self.validate(document)

    def test_rejects_loader_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesSkillLoaderInvocation"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
