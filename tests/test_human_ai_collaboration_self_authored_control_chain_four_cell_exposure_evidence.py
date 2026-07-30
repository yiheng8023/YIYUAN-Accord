from __future__ import annotations

import copy
import json
import unittest

from scripts.probe_codex_app_server_skill_exposure import canonical_sha256
from scripts.validate_human_ai_collaboration_self_authored_control_chain_four_cell_exposure_evidence import (
    REPORT_PATH,
    ROOT,
    validate_evidence,
)


class SelfAuthoredControlChainFourCellExposureEvidenceTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / REPORT_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_evidence(document or self.document, root=ROOT)

    @staticmethod
    def resign(document: dict) -> None:
        document.pop("reportSha256", None)
        document["reportSha256"] = canonical_sha256(document)

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_report_digest_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["status"] = "changed"
        with self.assertRaisesRegex(RuntimeError, "report digest"):
            self.validate(document)

    def test_rejects_body_only_projection(self) -> None:
        document = copy.deepcopy(self.document)
        document["projection"]["projectedFiles"].pop()
        self.resign(document)
        with self.assertRaisesRegex(RuntimeError, "projection pins"):
            self.validate(document)

    def test_rejects_hard_cell_exposure(self) -> None:
        document = copy.deepcopy(self.document)
        hard = next(
            row
            for row in document["cells"]
            if row["cellId"] == "CHAIN-HARD-HOOK-OFF"
        )
        hard["inventory"]["enabledConfigurableSkillCount"] = 3
        self.resign(document)
        with self.assertRaisesRegex(RuntimeError, "report contract"):
            self.validate(document)

    def test_rejects_hook_value_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["hookNetValueProved"] = True
        self.resign(document)
        with self.assertRaisesRegex(RuntimeError, "report contract"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
