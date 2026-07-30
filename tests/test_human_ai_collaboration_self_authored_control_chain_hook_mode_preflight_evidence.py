from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_self_authored_control_chain_hook_mode_preflight_evidence import (
    REPORT_PATH,
    ROOT,
    validate_evidence,
)


class SelfAuthoredControlChainHookModePreflightEvidenceTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / REPORT_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_evidence(document or self.document, root=ROOT)

    def test_current_evidence_is_valid(self) -> None:
        self.validate()

    def test_rejects_report_digest_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["status"] = "changed"
        with self.assertRaisesRegex(RuntimeError, "identity drifted"):
            self.validate(document)

    def test_rejects_off_mode_output(self) -> None:
        document = copy.deepcopy(self.document)
        off = next(row for row in document["observations"] if row["mode"] == "off")
        off["stdoutUtf8"] = "x"
        with self.assertRaisesRegex(RuntimeError, "report digest"):
            self.validate(document)

    def test_rejects_missing_auto_invocation(self) -> None:
        document = copy.deepcopy(self.document)
        document["observations"].pop()
        document.pop("reportSha256")
        from scripts.validate_human_ai_collaboration_self_authored_control_chain_hook_mode_preflight_evidence import (
            _canonical_sha256,
        )

        document["reportSha256"] = _canonical_sha256(document)
        with self.assertRaisesRegex(RuntimeError, "observation coverage"):
            self.validate(document)

    def test_rejects_failure_fallback_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["failureFallback"]["returnCode"] = 1
        document.pop("reportSha256")
        from scripts.validate_human_ai_collaboration_self_authored_control_chain_hook_mode_preflight_evidence import (
            _canonical_sha256,
        )

        document["reportSha256"] = _canonical_sha256(document)
        with self.assertRaisesRegex(RuntimeError, "failure-fallback"):
            self.validate(document)

    def test_rejects_hook_value_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["hookNetValueProved"] = True
        document.pop("reportSha256")
        from scripts.validate_human_ai_collaboration_self_authored_control_chain_hook_mode_preflight_evidence import (
            _canonical_sha256,
        )

        document["reportSha256"] = _canonical_sha256(document)
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
