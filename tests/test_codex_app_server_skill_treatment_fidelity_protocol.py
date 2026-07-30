from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_codex_app_server_skill_treatment_fidelity_protocol import (
    PROTOCOL_PATH,
    validate_treatment_fidelity_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


class CodexSkillTreatmentFidelityProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_treatment_fidelity_protocol(
            document or self.document,
            root=ROOT,
        )

    def test_current_protocol_is_valid(self) -> None:
        self.validate()

    def test_rejects_installed_candidate_attribution(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["installedCandidateAttributionAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "decision overclaimed"):
            self.validate(document)

    def test_rejects_loader_event_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"][
            "assayPassMayProveIndependentLoaderEvent"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "claim promoted"):
            self.validate(document)

    def test_rejects_token_in_public_prompt(self) -> None:
        document = copy.deepcopy(self.document)
        document["assay"]["tokenForbiddenLocations"].remove("public prompt")
        with self.assertRaisesRegex(RuntimeError, "token isolation"):
            self.validate(document)

    def test_rejects_fewer_repetitions(self) -> None:
        document = copy.deepcopy(self.document)
        document["assay"]["repetitions"] = 1
        with self.assertRaisesRegex(RuntimeError, "paired assay"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
