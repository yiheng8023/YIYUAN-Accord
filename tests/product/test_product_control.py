from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.control import (  # noqa: E402
    CURRENT_CONTROL_AND_TEST_MAX_BYTES,
    verify_product,
)


AUTHORITY_FILES = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/control.py",
    "scripts/verify.py",
    "tests/product/test_product_control.py",
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "docs/architecture.md",
    "docs/strategy/PRODUCT-NORTH-STAR.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "docs/operations/CURRENT-GOAL-MODE-PROMPT.md",
    "docs/operations/CONTINUATION.md",
    "docs/operations/HISTORY.md",
)


class ProductControlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative in AUTHORITY_FILES:
            source = ROOT / relative
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def read_json(self, relative: str) -> dict:
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def write_json(self, relative: str, value: object) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def mutate(self, relative: str, callback) -> None:
        value = self.read_json(relative)
        callback(value)
        self.write_json(relative, value)

    def report(self) -> dict:
        return verify_product(self.root)

    def active_increment(self, program: dict) -> dict:
        return next(
            item
            for item in program["increments"]
            if item["id"] == program["activeIncrementId"]
        )

    def mark_supporting_docs_no_active_increment(self) -> None:
        active = "increment.v0.2-causal-authority-reset"
        for relative in (
            "docs/operations/CURRENT-GOAL-MODE-PROMPT.md",
            "docs/operations/CONTINUATION.md",
        ):
            path = self.root / relative
            path.write_text(
                path.read_text(encoding="utf-8").replace(active, "None"),
                encoding="utf-8",
            )

    def run_cli(self) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT)
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "harness",
                "verify",
                "--root",
                str(self.root),
                "--json",
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def test_current_v02_contract_is_valid_and_in_progress(self) -> None:
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["release"], "v0.2")
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"], {"verified": 0, "total": 5})
        self.assertEqual(report["guardrails"], {"passed": 4, "total": 4})
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["O2"])

    def test_public_cli_reports_the_same_contract(self) -> None:
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["release"], "v0.2")
        self.assertTrue(report["valid"])

    def test_label_only_release_bump_fails_document_parity(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("release", "v0.3"),
        )
        self.mutate(
            "product/acceptance.json",
            lambda value: value.update(
                {"release": "v0.3", "id": "harness-product-acceptance-v0.3"}
            ),
        )
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("id", "harness-product-program-v0.3"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertEqual(report["release"], "v0.3")
        self.assertTrue(
            any("supporting document parity marker is missing" in item for item in report["errors"]),
            report["errors"],
        )

    def test_release_id_drift_fails_closed(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("id", "renamed-program"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program id must be harness-product-program-v0.2", report["errors"])

    def test_acceptance_release_must_match_program(self) -> None:
        self.mutate(
            "product/acceptance.json",
            lambda value: value.__setitem__("release", "v9.9"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program and acceptance releases must match", report["errors"])

    def test_completion_expression_cannot_drift(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("completionExpression", "O1"),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn("program completionExpression is invalid", report["errors"])

    def test_criteria_must_be_exact_and_unique(self) -> None:
        def duplicate(value: dict) -> None:
            value["criteria"].append(deepcopy(value["criteria"][0]))

        self.mutate("product/acceptance.json", duplicate)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("duplicate acceptance criterion O1", report["errors"])

    def test_malformed_criterion_id_fails_without_traceback(self) -> None:
        def malformed(value: dict) -> None:
            value["criteria"][1]["id"] = []

        self.mutate("product/acceptance.json", malformed)
        completed = self.run_cli()
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertFalse(report["valid"])

    def test_active_program_requires_exactly_one_active_increment(self) -> None:
        def close(value: dict) -> None:
            value["increments"][0]["state"] = "planned"

        self.mutate("product/program.json", close)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("active program must have exactly one active increment", report["errors"])

    def test_active_increment_id_must_match(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("activeIncrementId", "increment.missing"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("activeIncrementId must identify the active increment", report["errors"])

    def test_only_one_work_item_may_be_active(self) -> None:
        def duplicate_work(value: dict) -> None:
            increment = self.active_increment(value)
            other = deepcopy(increment["workItems"][0])
            other["id"] = "work.second"
            increment["workItems"].append(other)

        self.mutate("product/program.json", duplicate_work)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.v0.2-causal-authority-reset has more than one active work item",
            report["errors"],
        )

    def test_one_guardrail_only_reset_is_valid_but_not_product_progress(self) -> None:
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_malformed_work_state_fails_without_traceback(self) -> None:
        def malformed(value: dict) -> None:
            self.active_increment(value)["workItems"][0]["state"] = []

        self.mutate("product/program.json", malformed)
        completed = self.run_cli()
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse(json.loads(completed.stdout)["valid"])

    def test_active_work_operations_must_stay_inside_agent_authority(self) -> None:
        def exceed(value: dict) -> None:
            self.active_increment(value)["workItems"][0]["operationIds"].append("release")

        self.mutate("product/program.json", exceed)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "work item work.bind-v0.2-outcomes-and-neutral-kernel exceeds agent authority",
            report["errors"],
        )

    def test_human_authority_cannot_be_removed(self) -> None:
        def remove(value: dict) -> None:
            value["authorityBoundary"]["userOwns"].remove("new-trust")

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program userOwns omits a mandatory human authority", report["errors"])

    def test_agent_authority_cannot_claim_human_only_release(self) -> None:
        def add(value: dict) -> None:
            value["authorityBoundary"]["agentOwnsWithinBoundedAuthority"].append("release")

        self.mutate("product/program.json", add)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("agent authority overlaps a human-only authority", report["errors"])

    def test_process_loss_budget_fields_are_exact(self) -> None:
        def remove(value: dict) -> None:
            del self.active_increment(value)["processLossBudget"][
                "stopOnUnboundedResidue"
            ]

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.v0.2-causal-authority-reset requires the exact process-loss budget fields",
            report["errors"],
        )

    def test_same_correction_class_must_stop_before_recurrence(self) -> None:
        def loosen(value: dict) -> None:
            self.active_increment(value)["processLossBudget"][
                "maxSameClassUserCorrectionBeforeStop"
            ] = 2

        self.mutate("product/program.json", loosen)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "same-class user correction budget must stop before recurrence",
            report["errors"],
        )

    def test_guardrail_only_work_budget_cannot_exceed_one(self) -> None:
        def loosen(value: dict) -> None:
            self.active_increment(value)["processLossBudget"][
                "maxConsecutiveOutcomeNeutralWorkItems"
            ] = 2

        self.mutate("product/program.json", loosen)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("guardrail-only work budget must be zero or one", report["errors"])

    def test_declared_repository_residue_fails_closed(self) -> None:
        residue = self.root / ".tmp"
        residue.mkdir()
        (residue / "leftover.txt").write_text("residue", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository cleanup residue remains: .tmp", report["errors"])

    def test_dangling_cleanup_symlink_is_residue(self) -> None:
        link = self.root / ".tmp"
        try:
            link.symlink_to(self.root / "missing-target", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("cleanup path cannot traverse a link or reparse point: .tmp", report["errors"])

    def test_cleanup_locator_cannot_traverse(self) -> None:
        def traverse(value: dict) -> None:
            self.active_increment(value)["cleanupBoundary"][
                "repositoryTemporaryPaths"
            ] = ["../outside"]

        self.mutate("product/program.json", traverse)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("invalid repository cleanup path: '../outside'", report["errors"])

    def test_bootstrap_authority_set_cannot_self_disable(self) -> None:
        def remove(value: dict) -> None:
            value["requiredAuthorityFiles"].remove("product/acceptance.json")

        self.mutate("product/constitution.json", remove)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "requiredAuthorityFiles must equal the code-owned bootstrap set",
            report["errors"],
        )

    def test_active_authority_globs_cannot_broaden_into_archives(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value.__setitem__("activeAuthorityGlobs", ["**/*"]),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "activeAuthorityGlobs must equal the code-owned lean authority globs",
            report["errors"],
        )

    def test_active_authority_symlink_is_rejected(self) -> None:
        target = self.root / "harness" / "control-real.py"
        original = self.root / "harness" / "control.py"
        original.rename(target)
        try:
            original.symlink_to(target)
        except OSError as exc:
            target.rename(original)
            self.skipTest(f"symlink unavailable: {exc}")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertTrue(
            any("active authority cannot traverse a link or reparse point" in item for item in report["errors"]),
            report["errors"],
        )

    def test_forbidden_predecessor_identity_is_rejected_from_current_authority(self) -> None:
        predecessor = "agent" + "-skills" + "-curated"
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("purpose", predecessor),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "forbidden predecessor identity in active authority: product/program.json",
            report["errors"],
        )

    def test_historical_evidence_is_not_current_authority(self) -> None:
        predecessor = "agent" + "-skills" + "-curated"
        self.write_json(
            "product/evidence/history.json",
            {"schema": 1, "historicalIdentity": predecessor},
        )
        report = self.report()
        self.assertTrue(report["criterionStates"]["G3"], report["errors"])
        self.assertTrue(report["valid"], report["errors"])

    def test_planned_criterion_cannot_bind_evidence(self) -> None:
        def add(value: dict) -> None:
            next(item for item in value["criteria"] if item["id"] == "O2")[
                "evidence"
            ] = ["product/evidence/self.json"]

        self.mutate("product/acceptance.json", add)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("non-verified criterion O2 cannot bind evidence", report["errors"])

    def test_verified_criterion_requires_evidence(self) -> None:
        def promote(value: dict) -> None:
            next(item for item in value["criteria"] if item["id"] == "O2")[
                "assessment"
            ] = "verified"

        self.mutate("product/acceptance.json", promote)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("verified criterion O2 requires evidence", report["errors"])

    def test_self_declared_evidence_cannot_promote_without_code_validator(self) -> None:
        evidence = {
            "schema": 1,
            "id": "self-declared-o2",
            "criterionIds": ["O2"],
            "observedAt": "2026-08-12T03:00:00+08:00",
            "source": {"kind": "test"},
            "authority": {"kind": "user"},
            "result": {"accepted": True},
            "claimLimits": ["fixture only"],
            "validator": {"kind": "missing-validator", "version": 1},
        }
        self.write_json("product/evidence/self.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O2")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/self.json"]

        self.mutate("product/acceptance.json", promote)
        report = self.report()
        self.assertFalse(report["criterionStates"]["O2"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "criterion O2 has no code-owned evidence validator: missing-validator",
            report["errors"],
        )

    def test_malformed_evidence_fails_without_traceback(self) -> None:
        self.write_json("product/evidence/malformed.json", {"schema": 1})

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O2")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/malformed.json"]

        self.mutate("product/acceptance.json", promote)
        completed = self.run_cli()
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse(json.loads(completed.stdout)["valid"])

    def test_completed_program_with_planned_outcomes_is_not_accepted(self) -> None:
        def close(value: dict) -> None:
            value["status"] = "completed"
            value["activeIncrementId"] = None
            value["increments"][0]["state"] = "completed"
            value["increments"][0]["workItems"][0]["state"] = "completed"

        self.mutate("product/program.json", close)
        self.mark_supporting_docs_no_active_increment()
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_paused_program_has_no_active_increment_and_remains_in_progress(self) -> None:
        def pause(value: dict) -> None:
            value["status"] = "paused"
            value["activeIncrementId"] = None
            value["increments"][0]["state"] = "completed"
            value["increments"][0]["workItems"][0]["state"] = "completed"

        self.mutate("product/program.json", pause)
        self.mark_supporting_docs_no_active_increment()
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["activeIncrement"], None)
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_paused_program_cannot_retain_active_work(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("status", "paused"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("paused program must have no active increment", report["errors"])
        self.assertIn("paused program must have a terminal increment graph", report["errors"])

    def test_completed_program_cannot_retain_active_work(self) -> None:
        def invalid(value: dict) -> None:
            value["status"] = "completed"
            value["activeIncrementId"] = None
            value["increments"][0]["state"] = "completed"

        self.mutate("product/program.json", invalid)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "terminal increment increment.v0.2-causal-authority-reset has non-terminal work",
            report["errors"],
        )

    def test_completed_program_still_checks_repository_residue(self) -> None:
        def close(value: dict) -> None:
            value["status"] = "completed"
            value["activeIncrementId"] = None
            value["increments"][0]["state"] = "completed"
            value["increments"][0]["workItems"][0]["state"] = "completed"

        self.mutate("product/program.json", close)
        (self.root / ".tmp").mkdir()
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository cleanup residue remains: .tmp", report["errors"])

    def test_empty_completed_graph_is_invalid(self) -> None:
        def empty(value: dict) -> None:
            value["status"] = "completed"
            value["activeIncrementId"] = None
            value["increments"] = []

        self.mutate("product/program.json", empty)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program must contain at least one causal increment", report["errors"])

    def test_increment_requires_non_empty_work_graph(self) -> None:
        def empty(value: dict) -> None:
            self.active_increment(value)["workItems"] = []

        self.mutate("product/program.json", empty)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.v0.2-causal-authority-reset must contain at least one work item",
            report["errors"],
        )

    def test_unknown_operation_alias_cannot_bypass_human_authority(self) -> None:
        def alias(value: dict) -> None:
            value["authorityBoundary"]["agentOwnsWithinBoundedAuthority"].append("publish")
            self.active_increment(value)["workItems"][0]["operationIds"].append("publish")

        self.mutate("product/program.json", alias)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program agent authority contains an unknown operation", report["errors"])
        self.assertIn(
            "work item work.bind-v0.2-outcomes-and-neutral-kernel contains an unknown operation",
            report["errors"],
        )

    def test_accountable_outcome_acceptance_is_human_owned(self) -> None:
        def remove(value: dict) -> None:
            value["authorityBoundary"]["userOwns"].remove(
                "accountable-outcome-acceptance"
            )

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program userOwns omits a mandatory human authority", report["errors"])

    def test_historical_milestone_cannot_become_current_authority(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value["priorRelease"].__setitem__("currentAuthority", True),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "program priorRelease must retain the code-owned v0.1 milestone",
            report["errors"],
        )

    def test_supporting_document_release_drift_fails_parity(self) -> None:
        readme = self.root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace("v0.2", "v9.9"),
            encoding="utf-8",
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertTrue(
            any("supporting document parity marker is missing: README.md: v0.2" in item for item in report["errors"]),
            report["errors"],
        )

    def test_same_host_adapter_cannot_reappear_as_o5_documentary_proof(self) -> None:
        readme = self.root / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8").replace(
                "cannot pass O5",
                "can pass O5",
            ),
            encoding="utf-8",
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertTrue(
            any(
                "supporting document parity marker is missing: README.md: "
                "cannot pass O5" in item
                for item in report["errors"]
            ),
            report["errors"],
        )

    def test_undeclared_product_root_json_is_rejected(self) -> None:
        self.write_json("product/extra.json", {"schema": 1})
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("undeclared product authority JSON: product/extra.json", report["errors"])

    def test_parent_authority_symlink_is_rejected(self) -> None:
        product = self.root / "product"
        real = self.root / "product-real"
        product.rename(real)
        try:
            product.symlink_to(real, target_is_directory=True)
        except OSError as exc:
            real.rename(product)
            self.skipTest(f"directory symlink unavailable: {exc}")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertTrue(
            any("cannot traverse a link or reparse point" in item for item in report["errors"]),
            report["errors"],
        )

    def test_unicode_escaped_predecessor_identity_is_rejected_semantically(self) -> None:
        value = self.read_json("product/program.json")
        value["purpose"] = "agent" + "-skills" + "-curated"
        serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        serialized = serialized.replace(
            "agent-skills-curated", "agent\\u002dskills\\u002dcurated"
        )
        (self.root / "product/program.json").write_text(serialized, encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "forbidden predecessor semantic identity in active authority: product/program.json",
            report["errors"],
        )

    def test_evidence_criterion_ids_must_be_a_unique_string_list(self) -> None:
        for malformed in (123, {"O2": True}, "O2", ["O2", "O2"]):
            with self.subTest(malformed=malformed):
                evidence = {
                    "schema": 1,
                    "id": "typed-o2",
                    "criterionIds": malformed,
                    "observedAt": "2026-08-12T03:00:00+08:00",
                    "source": {"kind": "test"},
                    "authority": {"kind": "user"},
                    "result": {"accepted": True},
                    "claimLimits": ["fixture only"],
                    "validator": {"kind": "test-validator", "version": 1},
                }
                self.write_json("product/evidence/typed.json", evidence)

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O2"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/typed.json"]

                self.mutate("product/acceptance.json", promote)
                completed = self.run_cli()
                self.assertNotEqual(completed.returncode, 0)
                self.assertNotIn("Traceback", completed.stderr)
                report = json.loads(completed.stdout)
                self.assertFalse(report["valid"])
                self.assertIn(
                    "criterion O2 evidence shape is invalid: product/evidence/typed.json",
                    report["errors"],
                )
                shutil.copy2(ROOT / "product/acceptance.json", self.root / "product/acceptance.json")

    def test_evidence_locator_must_be_canonical_and_non_nested(self) -> None:
        for relative in (
            "product/Evidence/typed.json",
            "product/evidence/nested/typed.json",
        ):
            with self.subTest(relative=relative):
                self.write_json(relative, {"schema": 1})

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O2"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = [relative]

                self.mutate("product/acceptance.json", promote)
                report = self.report()
                self.assertFalse(report["valid"])
                self.assertIn(
                    f"criterion O2 has invalid evidence locator: '{relative}'",
                    report["errors"],
                )
                shutil.copy2(ROOT / "product/acceptance.json", self.root / "product/acceptance.json")

    def test_current_control_and_test_surface_is_materially_smaller(self) -> None:
        report = self.report()
        current = sum(
            (ROOT / relative).stat().st_size
            for relative in (
                "harness/control.py",
                "tests/product/test_product_control.py",
            )
        )
        baseline_sizes = [
            int(
                subprocess.check_output(
                    ["git", "cat-file", "-s", f"be498f960c9e0587d355291fb24261c91e75cd77:{relative}"],
                    cwd=ROOT,
                    text=True,
                ).strip()
            )
            for relative in (
                "harness/control.py",
                "tests/product/test_product_control.py",
            )
        ]
        self.assertEqual(baseline_sizes, [136602, 124315])
        self.assertEqual(sum(baseline_sizes), 260917)
        self.assertEqual(CURRENT_CONTROL_AND_TEST_MAX_BYTES, 130458)
        self.assertEqual(report["currentControlAndTestBytes"], current)
        self.assertLessEqual(current, CURRENT_CONTROL_AND_TEST_MAX_BYTES)
        self.assertFalse(report["criterionStates"]["O1"])


if __name__ == "__main__":
    unittest.main()
