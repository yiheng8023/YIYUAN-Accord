from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_codex_app_server_skill_treatment_fidelity_evidence import (
    EVIDENCE_PATH,
    PROTOCOL_PATH,
    validate_treatment_fidelity_evidence,
)


ROOT = Path(__file__).resolve().parent.parent


class CodexSkillTreatmentFidelityEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )
        self.protocol = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_treatment_fidelity_evidence(
            document or self.document,
            root=ROOT,
            protocol=self.protocol,
        )

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_control_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["pairs"][0]["control"]["agentMessageSha256"] = (
            document["pairs"][0]["selected"]["agentMessageSha256"]
        )
        with self.assertRaisesRegex(RuntimeError, "control drifted"):
            self.validate(document)

    def test_rejects_body_digest_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["pairs"][1]["skillBodySha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "body or token digest"):
            self.validate(document)

    def test_rejects_installed_diagnose_delivery_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"][
            "provesInstalledDiagnoseBodyDelivery"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "claim promoted"):
            self.validate(document)

    def test_rejects_thread_reuse(self) -> None:
        document = copy.deepcopy(self.document)
        document["pairs"][2]["selected"]["threadId"] = (
            document["pairs"][0]["control"]["threadId"]
        )
        with self.assertRaisesRegex(RuntimeError, "identity reused"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
