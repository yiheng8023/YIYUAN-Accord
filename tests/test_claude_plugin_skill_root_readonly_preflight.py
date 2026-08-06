from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.evaluate_claude_plugin_skill_root_readonly_preflight import (
    RECORD_PATH,
    evaluate_preflight,
    validate_repository_preflight,
    validate_preflight_record,
)


ROOT = Path(__file__).resolve().parent.parent


class ClaudePluginSkillRootReadonlyPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))
        self.request = self.record["syntheticFixture"]["request"]

    def test_repository_preflight_is_valid(self) -> None:
        record = validate_repository_preflight(ROOT)

        self.assertEqual("blocked-awaiting-explicit-readonly-authorization", record["status"])

    def test_complete_synthetic_contract_is_mechanism_eligible_but_nonexecuting(self) -> None:
        result = evaluate_preflight(self.request)

        self.assertEqual("eligible-synthetic-mechanism-only", result["decision"])
        self.assertEqual([], result["blockers"])
        self.assertFalse(result["inventoryExecutionAuthorized"])

    def test_network_or_plugin_execution_fails_closed(self) -> None:
        for path in (
            ("dataBoundary", "networkAccessAllowed"),
            ("authority", "pluginExecutionAuthorized"),
            ("authority", "externalWriteAuthorized"),
        ):
            with self.subTest(path=path):
                request = copy.deepcopy(self.request)
                request[path[0]][path[1]] = True

                result = evaluate_preflight(request)

                self.assertEqual("blocked", result["decision"])
                self.assertFalse(result["inventoryExecutionAuthorized"])

    def test_sensitive_or_payload_content_expansion_fails_closed(self) -> None:
        request = copy.deepcopy(self.request)
        request["dataBoundary"]["forbiddenContentClasses"].remove("plugin-payload-body")

        result = evaluate_preflight(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("forbidden-content-boundary-incomplete", result["blockers"])

    def test_output_must_remain_repository_local_and_nonpromotional(self) -> None:
        request = copy.deepcopy(self.request)
        request["verification"]["outputPath"] = "C:/Users/15521/.claude/plugins/result.json"

        result = evaluate_preflight(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("verification-surface-invalid", result["blockers"])

    def test_validator_rejects_live_authorization_claim(self) -> None:
        record = copy.deepcopy(self.record)
        record["currentDecision"]["readOnlyInventoryAuthorized"] = True

        with self.assertRaisesRegex(RuntimeError, "current decision"):
            validate_preflight_record(record, root=ROOT)

    def test_validator_rejects_acceptance_promotion(self) -> None:
        record = copy.deepcopy(self.record)
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criterion = next(
            row
            for row in acceptance["acceptanceCriteria"]
            if row["id"] == "acceptance.consumer-mapping-evidence"
        )
        criterion["assessment"] = "verified"

        with self.assertRaisesRegex(RuntimeError, "acceptance boundary"):
            validate_preflight_record(record, acceptance=acceptance, root=ROOT)


if __name__ == "__main__":
    unittest.main()
