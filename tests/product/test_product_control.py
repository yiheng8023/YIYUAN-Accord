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
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.control import verify_product  # noqa: E402


AUTHORITY_FILES = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/control.py",
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "docs/architecture.md",
    "docs/strategy/PRODUCT-NORTH-STAR.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "docs/operations/CONTINUATION.md",
    "docs/operations/HISTORY.md",
)
FIXTURE_INCREMENT_ID = "increment.fixture-current"
FIXTURE_WORK_ID = "work.fixture-current"


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

    def evidence_document(
        self,
        *,
        criterion_ids: object | None = None,
        validator_kind: str = "test-validator",
    ) -> dict:
        return {
            "schema": 1,
            "id": "typed-o2",
            "criterionIds": ["O2"] if criterion_ids is None else criterion_ids,
            "observedAt": "2026-08-12T03:00:00+08:00",
            "incrementId": FIXTURE_INCREMENT_ID,
            "workItemId": FIXTURE_WORK_ID,
            "source": {
                "kind": "repository-task-receipt",
                "locator": "task-receipt-001",
                "identity": "sha256:fixture",
            },
            "authority": {
                "kind": "named-accountable-human",
                "name": "fixture reviewer",
                "decision": "accepted",
                "decidedAt": "2026-08-12T03:01:00+08:00",
            },
            "result": {"accepted": True},
            "claimLimits": ["fixture only"],
            "validator": {"kind": validator_kind, "version": 1},
        }

    def increment_fixture(self, *, state: str = "planned") -> dict:
        work_state = "completed" if state == "completed" else "planned"
        return {
            "id": FIXTURE_INCREMENT_ID,
            "state": state,
            "correctionClass": "fixture-correction",
            "observedProblem": "fixture observed problem",
            "hypothesis": "fixture causal hypothesis",
            "falsifier": "fixture falsifier",
            "stopCondition": "fixture finite stop",
            "acceptanceIds": ["G4"],
            "processLossBudget": {
                "maxSameClassUserCorrectionBeforeStop": 1,
                "maxConsecutiveOutcomeNeutralWorkItems": 1,
                "maxMaterialUserToolOrchestrationInterventions": 0,
                "stopOnAuthorityOrIrreversibleIncident": True,
                "stopOnUnboundedResidue": True,
            },
            "cleanupBoundary": {
                "repositoryTemporaryPaths": [
                    ".tmp",
                    "harness/__pycache__",
                    "tests/product/__pycache__",
                ]
            },
            "workItems": [
                {
                    "id": FIXTURE_WORK_ID,
                    "state": work_state,
                    "acceptanceIds": ["G4"],
                    "operationIds": ["repository-read", "local-verification"],
                    "deliverables": ["fixture deliverable"],
                }
            ],
        }

    def ensure_increment(self, program: dict, *, state: str = "planned") -> dict:
        if not program["increments"]:
            program["increments"].append(self.increment_fixture(state=state))
        return program["increments"][-1]

    def map_outcome_to_latest_work(self, criterion_id: str) -> None:
        def add_mapping(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            increment["acceptanceIds"].append(criterion_id)
            increment["workItems"][0]["acceptanceIds"].append(criterion_id)

        self.mutate("product/program.json", add_mapping)

    def activate_program(self, program: dict) -> dict:
        increment = self.ensure_increment(program)
        program["status"] = "active"
        program["activeIncrementId"] = increment["id"]
        increment["state"] = "active"
        increment["workItems"][0]["state"] = "active"
        return increment

    def run_cli(self, *, json_output: bool = True) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT)
        command = [
            sys.executable,
            "-B",
            "-m",
            "harness",
            "verify",
            "--root",
            str(self.root),
        ]
        if json_output:
            command.append("--json")
        return subprocess.run(
            command,
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

    def test_plain_cli_sends_errors_to_stderr(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("id", "invalid-program"),
        )
        completed = self.run_cli(json_output=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ERROR: program id must be", completed.stderr)
        self.assertNotIn("ERROR:", completed.stdout)

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

    def test_outcomes_require_exact_operationalization_fields(self) -> None:
        def remove(value: dict) -> None:
            value["criteria"][0]["operationalization"].pop("passRule")

        self.mutate("product/acceptance.json", remove)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "criterion O1 requires the exact operationalization fields",
            report["errors"],
        )

    def test_outcome_sample_floor_and_comparison_design_are_code_owned(self) -> None:
        def dilute(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O2")
            criterion["operationalization"]["minimumSampleCount"] = 2

        self.mutate("product/acceptance.json", dilute)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "criterion O2 minimumSampleCount must be at least 3",
            report["errors"],
        )

        shutil.copy2(ROOT / "product/acceptance.json", self.root / "product/acceptance.json")

        def change_design(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O5")
            criterion["operationalization"]["comparisonDesign"] = "unrelated-host-tasks"

        self.mutate("product/acceptance.json", change_design)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("criterion O5 comparisonDesign is invalid", report["errors"])

    def test_outcome_operationalization_lists_are_typed_and_unique(self) -> None:
        def duplicate(value: dict) -> None:
            fields = value["criteria"][0]["operationalization"]["requiredMeasures"]
            fields.append(fields[0])

        self.mutate("product/acceptance.json", duplicate)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "criterion O1 operationalization requiredMeasures is invalid",
            report["errors"],
        )

    def test_guardrails_cannot_self_declare_outcome_operationalization(self) -> None:
        def add(value: dict) -> None:
            guardrail = next(item for item in value["criteria"] if item["id"] == "G1")
            guardrail["operationalization"] = deepcopy(
                value["criteria"][0]["operationalization"]
            )

        self.mutate("product/acceptance.json", add)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "guardrail G1 cannot declare operationalization",
            report["errors"],
        )

    def test_active_program_requires_exactly_one_active_increment(self) -> None:
        def close(value: dict) -> None:
            increment = self.activate_program(value)
            increment["state"] = "planned"

        self.mutate("product/program.json", close)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("active program must have exactly one active increment", report["errors"])

    def test_clean_active_fixture_is_valid(self) -> None:
        self.mutate("product/program.json", self.activate_program)
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])

    def test_active_increment_id_must_match(self) -> None:
        def mismatch(value: dict) -> None:
            self.activate_program(value)
            value["activeIncrementId"] = "increment.missing"

        self.mutate("product/program.json", mismatch)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("activeIncrementId must identify the active increment", report["errors"])

    def test_only_one_work_item_may_be_active(self) -> None:
        def duplicate_work(value: dict) -> None:
            increment = self.activate_program(value)
            other = deepcopy(increment["workItems"][0])
            other["id"] = "work.second"
            increment["workItems"].append(other)

        self.mutate("product/program.json", duplicate_work)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.fixture-current has more than one active work item",
            report["errors"],
        )

    def test_active_program_cannot_queue_planned_increment(self) -> None:
        def queue(value: dict) -> None:
            self.activate_program(value)
            planned = self.increment_fixture()
            planned["id"] = "increment.queued"
            planned["correctionClass"] = "queued-correction"
            planned["workItems"][0]["id"] = "work.queued"
            value["increments"].append(planned)

        self.mutate("product/program.json", queue)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "current program cannot queue planned increment increment.queued",
            report["errors"],
        )

    def test_active_increment_cannot_queue_planned_work_item(self) -> None:
        def queue(value: dict) -> None:
            increment = self.activate_program(value)
            planned = deepcopy(increment["workItems"][0])
            planned["id"] = "work.queued"
            planned["state"] = "planned"
            increment["workItems"].append(planned)

        self.mutate("product/program.json", queue)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "current increment cannot queue planned work item work.queued",
            report["errors"],
        )

    def test_increment_requires_a_correction_class(self) -> None:
        def remove(value: dict) -> None:
            self.activate_program(value).pop("correctionClass")

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.fixture-current requires a correctionClass",
            report["errors"],
        )

    def test_work_acceptance_must_be_contained_by_increment(self) -> None:
        def exceed(value: dict) -> None:
            increment = self.activate_program(value)
            increment["workItems"][0]["acceptanceIds"].append("G1")

        self.mutate("product/program.json", exceed)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "work item work.fixture-current "
            "acceptanceIds exceed increment "
            "increment.fixture-current",
            report["errors"],
        )

    def test_empty_paused_current_graph_is_valid_but_not_product_progress(self) -> None:
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_malformed_work_state_fails_without_traceback(self) -> None:
        def malformed(value: dict) -> None:
            self.activate_program(value)["workItems"][0]["state"] = []

        self.mutate("product/program.json", malformed)
        completed = self.run_cli()
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertFalse(report["valid"])
        self.assertIn(
            "work item work.fixture-current has invalid state",
            report["errors"],
        )

    def test_active_work_operations_must_stay_inside_agent_authority(self) -> None:
        def exceed(value: dict) -> None:
            self.activate_program(value)["workItems"][0]["operationIds"].append("release")

        self.mutate("product/program.json", exceed)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "work item work.fixture-current exceeds agent authority",
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
            del self.activate_program(value)["processLossBudget"][
                "stopOnUnboundedResidue"
            ]

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current requires the exact process-loss budget fields",
            report["errors"],
        )

    def test_same_correction_class_must_stop_before_recurrence(self) -> None:
        def loosen(value: dict) -> None:
            self.activate_program(value)["processLossBudget"][
                "maxSameClassUserCorrectionBeforeStop"
            ] = 2

        self.mutate("product/program.json", loosen)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "same-class user correction budget must stop before recurrence",
            report["errors"],
        )

    def test_adjacent_increments_cannot_repeat_a_correction_class(self) -> None:
        def repeat(value: dict) -> None:
            first = self.ensure_increment(value, state="completed")
            duplicate = deepcopy(first)
            duplicate["id"] = "increment.repeated-correction"
            duplicate["workItems"][0]["id"] = "work.repeated-correction"
            value["increments"].append(duplicate)

        self.mutate("product/program.json", repeat)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "adjacent increments repeat correctionClass: "
            "fixture-correction",
            report["errors"],
        )

    def test_outcome_neutral_work_budget_cannot_exceed_one(self) -> None:
        def loosen(value: dict) -> None:
            self.activate_program(value)["processLossBudget"][
                "maxConsecutiveOutcomeNeutralWorkItems"
            ] = 2

        self.mutate("product/program.json", loosen)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("outcome-neutral work budget must be zero or one", report["errors"])

    def test_paused_program_cannot_accumulate_closed_outcome_neutral_queue(self) -> None:
        def queue(value: dict) -> None:
            first = self.ensure_increment(value, state="completed")
            second = deepcopy(first)
            second["id"] = "increment.second-neutral"
            second["correctionClass"] = "second-neutral-correction"
            second["workItems"][0]["id"] = "work.second-neutral"
            value["increments"].append(second)

        self.mutate("product/program.json", queue)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "closed outcome-neutral increment must leave the current graph: increment.fixture-current",
            report["errors"],
        )
        self.assertIn(
            "closed outcome-neutral increment must leave the current graph: increment.second-neutral",
            report["errors"],
        )

    def test_paused_program_retains_completed_validated_outcome_binding(self) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(criterion_ids=["O1"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            {"test-validator": validator},
        ):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["criterionStates"]["O1"])
        self.assertTrue(report["criterionStates"]["G4"])

    def test_outcome_label_without_validated_evidence_cannot_reset_neutral_count(self) -> None:
        def label_arbitrage(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            first = increment["workItems"][0]
            first["acceptanceIds"].append("O1")
            first["state"] = "completed"
            second = deepcopy(first)
            second["id"] = "work.second-labeled-neutral-item"
            second["state"] = "active"
            increment["workItems"].append(second)

        self.mutate("product/program.json", label_arbitrage)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "increment increment.fixture-current exceeds its outcome-neutral work budget",
            report["errors"],
        )

    def test_validated_outcome_evidence_cannot_reset_another_labeled_work(self) -> None:
        def reuse_evidence(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            first = increment["workItems"][0]
            first["acceptanceIds"].append("O1")
            first["state"] = "completed"
            second = deepcopy(first)
            second["id"] = "work.second-labeled-item"
            third = deepcopy(first)
            third["id"] = "work.third-labeled-item"
            third["state"] = "active"
            increment["workItems"].extend([second, third])

        self.mutate("product/program.json", reuse_evidence)
        evidence = self.evidence_document(criterion_ids=["O1"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            {"test-validator": validator},
        ):
            report = self.report()
        self.assertTrue(report["criterionStates"]["O1"], report["errors"])
        self.assertTrue(report["criterionStates"]["G2"], report["errors"])
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current exceeds its outcome-neutral work budget",
            report["errors"],
        )

    def test_declared_repository_residue_fails_closed(self) -> None:
        residue = self.root / ".tmp"
        residue.mkdir()
        (residue / "leftover.txt").write_text("residue", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository cleanup residue remains: .tmp", report["errors"])

    def test_undeclared_conventional_residue_fails_closed_repository_wide(self) -> None:
        cache = self.root / "unlisted" / "__pycache__"
        cache.mkdir(parents=True)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "repository cleanup residue remains: unlisted/__pycache__",
            report["errors"],
        )

    def test_dangling_cleanup_symlink_is_residue(self) -> None:
        self.mutate("product/program.json", self.activate_program)
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
            self.activate_program(value)["cleanupBoundary"][
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
        evidence = self.evidence_document(validator_kind="missing-validator")
        evidence["id"] = "self-declared-o2"
        self.write_json("product/evidence/self.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O2")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/self.json"]

        self.mutate("product/acceptance.json", promote)
        self.map_outcome_to_latest_work("O2")
        report = self.report()
        self.assertFalse(report["criterionStates"]["O2"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "criterion O2 has no code-owned evidence validator: missing-validator",
            report["errors"],
        )

    def test_weak_generic_evidence_identity_authority_or_result_fails_closed(self) -> None:
        self.map_outcome_to_latest_work("O2")
        mutations = {
            "missing work binding": lambda value: value.pop("workItemId"),
            "wrong increment binding": lambda value: value.__setitem__(
                "incrementId", "increment.other"
            ),
            "missing source locator": lambda value: value["source"].pop("locator"),
            "unnamed authority kind": lambda value: value["authority"].__setitem__(
                "kind", "user"
            ),
            "blank human name": lambda value: value["authority"].__setitem__("name", " "),
            "unaccepted human decision": lambda value: value["authority"].__setitem__(
                "decision", "rejected"
            ),
            "invalid decision time": lambda value: value["authority"].__setitem__(
                "decidedAt", "today"
            ),
            "unaccepted result": lambda value: value["result"].__setitem__(
                "accepted", False
            ),
        }
        for label, mutate_evidence in mutations.items():
            with self.subTest(label=label):
                evidence = self.evidence_document(validator_kind="missing-validator")
                mutate_evidence(evidence)
                self.write_json("product/evidence/weak.json", evidence)

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O2"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/weak.json"]

                self.mutate("product/acceptance.json", promote)
                report = self.report()
                self.assertFalse(report["criterionStates"]["O2"])
                self.assertFalse(report["criterionStates"]["G2"])
                self.assertIn(
                    "criterion O2 evidence shape is invalid: product/evidence/weak.json",
                    report["errors"],
                )
                self.assertNotIn(
                    "criterion O2 has no code-owned evidence validator: missing-validator",
                    report["errors"],
                )
                shutil.copy2(
                    ROOT / "product/acceptance.json",
                    self.root / "product/acceptance.json",
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

    def test_completed_program_without_validated_outcome_binding_is_invalid(self) -> None:
        def close(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            value["status"] = "completed"
            value["activeIncrementId"] = None
            increment["state"] = "completed"
            increment["workItems"][0]["state"] = "completed"

        self.mutate("product/program.json", close)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"]["verified"], 0)
        self.assertIn(
            "closed outcome-neutral increment must leave the current graph: increment.fixture-current",
            report["errors"],
        )

    def test_paused_program_has_no_active_increment_and_remains_in_progress(self) -> None:
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["activeIncrement"], None)
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_paused_program_cannot_erase_agent_owned_non_outcome_progression(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.pop("progressionPolicy", None),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program progressionPolicy is invalid", report["errors"])

    def test_paused_program_cannot_retain_active_work(self) -> None:
        def invalid(value: dict) -> None:
            self.activate_program(value)
            value["status"] = "paused"

        self.mutate("product/program.json", invalid)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("paused program must have no active increment", report["errors"])
        self.assertIn("paused program must have a terminal increment graph", report["errors"])

    def test_completed_increment_cannot_retain_active_work(self) -> None:
        def invalid(value: dict) -> None:
            increment = self.activate_program(value)
            value["status"] = "completed"
            value["activeIncrementId"] = None
            increment["state"] = "completed"

        self.mutate("product/program.json", invalid)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "active work item work.fixture-current must belong to the active increment",
            report["errors"],
        )
        self.assertIn(
            "terminal increment increment.fixture-current has non-terminal work",
            report["errors"],
        )

    def test_completed_program_still_checks_repository_residue(self) -> None:
        def close(value: dict) -> None:
            increment = self.ensure_increment(value, state="completed")
            value["status"] = "completed"
            value["activeIncrementId"] = None
            increment["state"] = "completed"
            increment["workItems"][0]["state"] = "completed"

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
        self.assertIn(
            "only a paused program may have an empty current increment graph",
            report["errors"],
        )

    def test_increment_requires_non_empty_work_graph(self) -> None:
        def empty(value: dict) -> None:
            self.activate_program(value)["workItems"] = []

        self.mutate("product/program.json", empty)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn(
            "increment increment.fixture-current must contain at least one work item",
            report["errors"],
        )

    def test_unknown_operation_alias_cannot_bypass_human_authority(self) -> None:
        def alias(value: dict) -> None:
            value["authorityBoundary"]["agentOwnsWithinBoundedAuthority"].append("publish")
            self.activate_program(value)["workItems"][0]["operationIds"].append("publish")

        self.mutate("product/program.json", alias)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program agent authority contains an unknown operation", report["errors"])
        self.assertIn(
            "work item work.fixture-current contains an unknown operation",
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

    def test_capability_guidance_cannot_become_product_authority(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value.pop("capabilityInfluenceBoundary", None),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "constitution capabilityInfluenceBoundary is invalid",
            report["errors"],
        )

    def test_historical_milestone_cannot_become_current_authority(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value["priorRelease"].__setitem__("currentAuthority", True),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "program priorRelease must be a non-authoritative historical milestone",
            report["errors"],
        )

    def test_historical_failure_remains_non_authoritative_counterevidence(self) -> None:
        def erase_counterevidence(value: dict) -> None:
            value["historicalEvidenceBoundary"]["counterevidenceInput"] = False

        self.mutate("product/constitution.json", erase_counterevidence)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "constitution historicalEvidenceBoundary is invalid",
            report["errors"],
        )

    def test_declared_supporting_document_must_exist(self) -> None:
        (self.root / "README.md").unlink()
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("supporting document is missing: README.md", report["errors"])

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
        self.map_outcome_to_latest_work("O2")
        for malformed in (123, {"O2": True}, "O2", ["O2", "O2"]):
            with self.subTest(malformed=malformed):
                evidence = self.evidence_document(criterion_ids=malformed)
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

if __name__ == "__main__":
    unittest.main()
