from __future__ import annotations

from copy import deepcopy
from io import StringIO
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
CODEX_PLUGIN_ROOT = ROOT / "adapters/agent-autonomy-harness-codex"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.codex_reference import (  # noqa: E402
    ADAPTER_ID,
    render_session_start_context,
    session_start_hook_output,
)
from harness.control import SUPPORTED_EVIDENCE_VALIDATORS, verify_product  # noqa: E402
from harness.__main__ import main as cli_main  # noqa: E402


AUTHORITY_FILES = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/codex_reference.py",
    "harness/control.py",
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "SUPPORT.zh-CN.md",
    "docs/DEMAND-TO-CAPABILITY-PROFILE.md",
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
        self.reset_program_fixture()

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

    def reset_program_fixture(self) -> None:
        """Keep generic mutation tests independent of the live causal increment."""

        program = json.loads(
            (ROOT / "product/program.json").read_text(encoding="utf-8")
        )
        program["status"] = "ready"
        program["activeIncrementId"] = None
        program["increments"] = []
        self.write_json("product/program.json", program)

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

    @staticmethod
    def validator_registry(
        validator,
        *,
        criterion_ids: frozenset[str] | None = None,
        increment_ids: frozenset[str] | None = None,
    ) -> dict:
        supported_criteria = (
            criterion_ids
            if criterion_ids is not None
            else frozenset({"O1", "O2", "O3", "O4", "O5"})
        )
        supported_increments = (
            increment_ids
            if increment_ids is not None
            else frozenset({FIXTURE_INCREMENT_ID})
        )
        return {
            "test-validator": (
                supported_criteria,
                supported_increments,
                validator,
            )
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
                "maxMaterialUserCapabilityOrchestrationInterventions": 0,
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

    def run_cli(
        self, *, json_output: bool = True, root: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT)
        verification_root = self.root if root is None else root
        command = [
            sys.executable,
            "-B",
            "-m",
            "harness",
            "verify",
            "--root",
            str(verification_root),
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

    def codex_session_start_payload(self, *, source: str = "startup") -> dict:
        return {
            "session_id": "00000000-0000-4000-8000-000000000001",
            "transcript_path": str(self.root / "must-not-be-read.jsonl"),
            "cwd": str(self.root),
            "hook_event_name": "SessionStart",
            "model": "gpt-test",
            "permission_mode": "default",
            "source": source,
        }

    def test_current_v02_contract_is_active_and_in_progress(self) -> None:
        report = verify_product(ROOT)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["release"], "v0.2")
        self.assertEqual(report["programStatus"], "active")
        self.assertEqual(
            report["activeIncrement"],
            "increment.v0.2.context-lifecycle-sample-coverage",
        )
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"], {"verified": 0, "total": 5})
        self.assertEqual(report["guardrails"], {"passed": 4, "total": 4})
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["O2"])

    def test_public_cli_reports_the_same_contract(self) -> None:
        completed = self.run_cli(root=ROOT)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["release"], "v0.2")
        self.assertEqual(report["programStatus"], "active")
        self.assertTrue(report["valid"])

    def test_plain_cli_exposes_program_and_completion_states(self) -> None:
        completed = self.run_cli(json_output=False, root=ROOT)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("v0.2: active, in-progress", completed.stdout)

    def test_codex_session_start_adapter_projects_live_authority(self) -> None:
        payload = self.codex_session_start_payload(source="resume")
        context = render_session_start_context(self.root, payload)
        self.assertIsNotNone(context)
        projection = json.loads(context)
        self.assertEqual(projection["adapter"], ADAPTER_ID)
        self.assertEqual(projection["event"], {"name": "SessionStart", "source": "resume"})
        self.assertEqual(projection["program"]["status"], "ready")
        self.assertEqual(
            projection["program"]["progressionPolicy"][
                "boundProductDeliveryDemandDisposition"
            ],
            "authorized-product-plan-delivery-is-real-demand-when-its-primary-purpose-is-the-deliverable-rather-than-exercising-or-diagnosing-the-harness",
        )
        self.assertEqual(
            projection["nextRoute"],
            "select-smallest-causally-justified-product-delivery-increment-from-current-authority",
        )
        self.assertNotIn("transcript_path", context)
        self.assertNotIn(payload["session_id"], context)

    def test_codex_session_start_adapter_supports_native_continuity_events(self) -> None:
        for source in ("startup", "resume", "clear", "compact"):
            with self.subTest(source=source):
                output = session_start_hook_output(
                    self.root, self.codex_session_start_payload(source=source)
                )
                self.assertEqual(output["continue"], True)
                self.assertEqual(output["suppressOutput"], True)
                context = json.loads(output["hookSpecificOutput"]["additionalContext"])
                self.assertEqual(context["event"]["source"], source)

    def test_codex_session_start_adapter_projects_exact_active_increment(self) -> None:
        self.mutate("product/program.json", self.activate_program)
        context = render_session_start_context(
            self.root, self.codex_session_start_payload(source="compact")
        )
        projection = json.loads(context)
        self.assertEqual(projection["nextRoute"], "continue-current-active-increment")
        self.assertEqual(projection["currentWork"]["id"], FIXTURE_INCREMENT_ID)
        self.assertEqual(
            projection["currentWork"]["correctionClass"], "fixture-correction"
        )

    def test_codex_session_start_adapter_is_noop_outside_bound_repository(self) -> None:
        payload = self.codex_session_start_payload()
        payload["cwd"] = str(self.root.parent)
        self.assertIsNone(render_session_start_context(self.root, payload))
        self.assertEqual(
            session_start_hook_output(self.root, payload),
            {"continue": True, "suppressOutput": True},
        )

    def test_codex_session_start_adapter_rejects_other_events_and_sources(self) -> None:
        wrong_event = self.codex_session_start_payload()
        wrong_event["hook_event_name"] = "UserPromptSubmit"
        self.assertIsNone(render_session_start_context(self.root, wrong_event))

        wrong_source = self.codex_session_start_payload(source="unknown")
        self.assertIsNone(render_session_start_context(self.root, wrong_source))

    def test_codex_session_start_adapter_surfaces_invalid_authority_without_claiming_work(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("completionExpression", "true"),
        )
        context = render_session_start_context(
            self.root, self.codex_session_start_payload(source="compact")
        )
        projection = json.loads(context)
        self.assertFalse(projection["verification"]["valid"])
        self.assertEqual(
            projection["nextRoute"], "repair-current-authority-before-product-mutation"
        )
        self.assertNotIn("product", projection)

    def test_codex_session_start_cli_emits_hook_schema_without_traceback(self) -> None:
        arguments = [
            "python -m harness",
            "codex-session-start",
            "--root",
            str(self.root),
        ]
        stdout = StringIO()
        stderr = StringIO()
        with (
            patch.object(sys, "argv", arguments),
            patch("sys.stdin", new=StringIO(json.dumps(self.codex_session_start_payload()))),
            patch("sys.stdout", new=stdout),
            patch("sys.stderr", new=stderr),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 0)
        self.assertEqual(stderr.getvalue(), "")
        output = json.loads(stdout.getvalue())
        self.assertEqual(set(output), {"continue", "suppressOutput", "hookSpecificOutput"})
        self.assertEqual(
            output["hookSpecificOutput"]["hookEventName"], "SessionStart"
        )

    def test_codex_session_start_cli_malformed_input_is_nonblocking_noop(self) -> None:
        arguments = [
            "python -m harness",
            "codex-session-start",
            "--root",
            str(self.root),
        ]
        stdout = StringIO()
        with (
            patch.object(sys, "argv", arguments),
            patch("sys.stdin", new=StringIO("not-json")),
            patch("sys.stdout", new=stdout),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 0)
        self.assertEqual(
            json.loads(stdout.getvalue()),
            {"continue": True, "suppressOutput": True},
        )

    def test_codex_plugin_projection_is_thin_inactive_and_host_rooted(self) -> None:
        manifest = json.loads(
            (CODEX_PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text(
                encoding="utf-8"
            )
        )
        hooks = json.loads(
            (CODEX_PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "agent-autonomy-harness-codex")
        self.assertEqual(manifest["version"], "0.2.0-candidate.1")
        self.assertFalse((CODEX_PLUGIN_ROOT / "plugin.json").exists())
        self.assertNotIn("skills", manifest)
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("apps", manifest)
        self.assertNotIn("defaultPrompt", manifest["interface"])
        self.assertNotIn("hooks", manifest)
        handlers = hooks["hooks"]["SessionStart"]
        self.assertEqual(len(handlers), 1)
        command = handlers[0]["hooks"][0]
        self.assertEqual(command["type"], "command")
        self.assertIn("${PLUGIN_ROOT}", command["command"])
        self.assertIn("${PLUGIN_ROOT}", command["commandWindows"])
        self.assertIn(" -I ", command["command"])
        self.assertNotIn(str(ROOT), json.dumps(hooks))
        candidate_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                CODEX_PLUGIN_ROOT / ".codex-plugin/plugin.json",
                CODEX_PLUGIN_ROOT / "hooks/hooks.json",
                CODEX_PLUGIN_ROOT / "scripts/session_start.py",
            )
        ).lower()
        self.assertNotIn("cc switch", candidate_text)

    def test_codex_plugin_launcher_projects_from_nested_harness_cwd(self) -> None:
        nested = self.root / "docs/nested"
        nested.mkdir(parents=True)
        payload = self.codex_session_start_payload(source="compact")
        payload["cwd"] = str(nested)
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(CODEX_PLUGIN_ROOT / "scripts/session_start.py"),
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        context = json.loads(output["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(context["adapter"], ADAPTER_ID)
        self.assertEqual(context["event"]["source"], "compact")
        self.assertNotIn("transcript_path", output["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn(payload["session_id"], completed.stdout)

    def test_codex_plugin_launcher_is_noop_without_harness_authority(self) -> None:
        payload = self.codex_session_start_payload()
        payload["cwd"] = str(self.root.parent)
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(CODEX_PLUGIN_ROOT / "scripts/session_start.py"),
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"continue": True, "suppressOutput": True},
        )

    def test_codex_plugin_launcher_rejects_unreviewed_runtime_bytes(self) -> None:
        with (self.root / "harness/control.py").open("a", encoding="utf-8") as handle:
            handle.write("\n# unreviewed runtime drift\n")
        payload = self.codex_session_start_payload()
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(CODEX_PLUGIN_ROOT / "scripts/session_start.py"),
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(
            json.loads(completed.stdout),
            {"continue": True, "suppressOutput": True},
        )

    def test_plain_cli_sends_errors_to_stderr(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("id", "invalid-program"),
        )
        completed = self.run_cli(json_output=False)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("ERROR: program id must be", completed.stderr)
        self.assertNotIn("ERROR:", completed.stdout)

    def test_cli_delegates_root_resolution_to_fail_closed_verifier(self) -> None:
        report = {
            "productId": "agent-autonomy-harness",
            "release": None,
            "programStatus": None,
            "valid": False,
            "completionState": "in-progress",
            "activeIncrement": None,
            "outcomes": {"verified": 0, "total": 5},
            "guardrails": {"passed": 0, "total": 4},
            "criterionStates": {},
            "errors": ["verifier failed closed: OSError"],
        }
        arguments = ["python -m harness", "verify", "--root", "unresolvable", "--json"]
        with (
            patch("harness.__main__.Path.resolve", side_effect=OSError("fixture")),
            patch("harness.__main__.verify_product", return_value=report) as verifier,
            patch.object(sys, "argv", arguments),
            patch("sys.stdout", new=StringIO()),
        ):
            returncode = cli_main()
        self.assertEqual(returncode, 1)
        verifier.assert_called_once()

    def test_release_id_drift_fails_closed(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("id", "renamed-program"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program id must be harness-product-program-v0.2", report["errors"])

    def test_coordinated_release_rename_cannot_self_promote(self) -> None:
        def rename_program(value: dict) -> None:
            value["release"] = "v9.9"
            value["id"] = "harness-product-program-v9.9"

        def rename_acceptance(value: dict) -> None:
            value["release"] = "v9.9"
            value["id"] = "harness-product-acceptance-v9.9"

        self.mutate("product/program.json", rename_program)
        self.mutate("product/acceptance.json", rename_acceptance)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("program release must be v0.2", report["errors"])

    def test_authority_json_rejects_duplicate_keys_and_nonfinite_constants(self) -> None:
        path = self.root / "product" / "program.json"
        baseline = path.read_text(encoding="utf-8")
        variants = {
            "duplicate-key": baseline.replace(
                '"status": "ready",',
                '"status": "ready",\n  "status": "ready",',
                1,
            ),
            "nonfinite-constant": baseline.replace(
                '"schema": 1,',
                '"schema": 1,\n  "nonStandard": NaN,',
                1,
            ),
        }
        for label, content in variants.items():
            with self.subTest(label=label):
                path.write_text(content, encoding="utf-8")
                report = self.report()
                self.assertFalse(report["valid"])
                self.assertIn("cannot read product program: invalid JSON", report["errors"])

    def test_authority_schema_must_be_literal_integer_one(self) -> None:
        for relative, label in (
            ("product/constitution.json", "constitution"),
            ("product/program.json", "program"),
            ("product/acceptance.json", "acceptance"),
        ):
            with self.subTest(relative=relative):
                self.mutate(relative, lambda value: value.__setitem__("schema", True))
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(f"{label} schema must be integer 1", report["errors"])
                shutil.copy2(ROOT / relative, self.root / relative)

    def test_authority_documents_reject_undeclared_top_level_fields(self) -> None:
        variants = (
            (
                "product/constitution.json",
                "currentAuthorityOverride",
                True,
                "constitution",
            ),
            ("product/program.json", "completionState", "accepted", "program"),
            ("product/acceptance.json", "accepted", True, "acceptance"),
        )
        for relative, field, value, label in variants:
            with self.subTest(relative=relative, field=field):
                self.mutate(relative, lambda document: document.__setitem__(field, value))
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(
                    f"{label} top-level fields must match the code-owned schema",
                    report["errors"],
                )
                shutil.copy2(ROOT / relative, self.root / relative)

    def test_planning_active_limits_must_be_literal_integer_one(self) -> None:
        def boolean_limits(value: dict) -> None:
            value["planningModel"]["maxActiveIncrements"] = True
            value["planningModel"]["maxActiveWorkItems"] = True

        self.mutate("product/constitution.json", boolean_limits)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution planningModel is invalid", report["errors"])

    def test_work_state_semantics_cannot_self_disable(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value["planningModel"]["workStateSemantics"].__setitem__(
                "cancelled", "may have executed"
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution planningModel is invalid", report["errors"])

    def test_planning_model_cannot_disable_causality_or_add_workflow(self) -> None:
        variants = (
            (
                "remove causal prerequisites",
                lambda value: value["planningModel"].__setitem__(
                    "incrementRequires", ["none"]
                ),
            ),
            (
                "disable replanning",
                lambda value: value["planningModel"].__setitem__(
                    "replanWhen", ["never"]
                ),
            ),
            (
                "inject workflow",
                lambda value: value["planningModel"].__setitem__(
                    "mandatoryWorkflow", "plan-worktree-review"
                ),
            ),
        )
        for label, mutate_planning_model in variants:
            with self.subTest(label=label):
                self.mutate("product/constitution.json", mutate_planning_model)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(
                    "constitution planningModel is invalid", report["errors"]
                )
                shutil.copy2(
                    ROOT / "product/constitution.json",
                    self.root / "product/constitution.json",
                )

    def test_collaboration_model_cannot_add_user_or_process_burden(self) -> None:
        def inject_workflow(value: dict) -> None:
            model = value["collaborationModel"]
            model["userContributions"].append("skill-and-workflow-selection")
            model["agentObligations"].append("mandatory-external-methodology")
            model["requiredWorkflow"] = "brainstorm-plan-worktree-subagents-review"

        self.mutate("product/constitution.json", inject_workflow)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution collaborationModel is invalid", report["errors"])

    def test_product_form_cannot_collapse_into_a_catalog_or_host_product(self) -> None:
        variants = (
            ("identity", "codex-skill-catalog"),
            ("durableOutputs", ["host-plugin"]),
            ("portableCore", "fixed-plugin-list"),
            ("referenceDelivery", "codex-only-runtime"),
        )
        for field, replacement in variants:
            with self.subTest(field=field):
                self.mutate(
                    "product/constitution.json",
                    lambda value: value["productForm"].__setitem__(
                        field, replacement
                    ),
                )
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn("constitution productForm is invalid", report["errors"])
                shutil.copy2(
                    ROOT / "product/constitution.json",
                    self.root / "product/constitution.json",
                )

    def test_fixed_invariants_and_bootstrap_guards_cannot_self_disable(self) -> None:
        variants = (
            (
                "fixedInvariants",
                ["tests and artifact counts are product outcomes"],
                "constitution fixedInvariants are invalid",
            ),
            (
                "bootstrapGuards",
                ["self-declaration is sufficient evidence"],
                "constitution bootstrapGuards are invalid",
            ),
            (
                "adaptiveSurfaces",
                ["fixed capability catalog"],
                "constitution adaptiveSurfaces are invalid",
            ),
        )
        for field, replacement, expected_error in variants:
            with self.subTest(field=field):
                self.mutate(
                    "product/constitution.json",
                    lambda value: value.__setitem__(field, replacement),
                )
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(expected_error, report["errors"])
                shutil.copy2(
                    ROOT / "product/constitution.json",
                    self.root / "product/constitution.json",
                )

    def test_code_owned_policy_booleans_cannot_be_replaced_by_integers(self) -> None:
        variants = (
            (
                "product/program.json",
                lambda value: value["progressionPolicy"].__setitem__(
                    "userMustNotInventTasks", 1
                ),
                "program progressionPolicy is invalid",
            ),
            (
                "product/constitution.json",
                lambda value: value["historicalEvidenceBoundary"].__setitem__(
                    "productAuthority", 0
                ),
                "constitution historicalEvidenceBoundary is invalid",
            ),
        )
        for relative, mutation, expected_error in variants:
            with self.subTest(relative=relative):
                self.mutate(relative, mutation)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G3"])
                self.assertIn(expected_error, report["errors"])
                shutil.copy2(ROOT / relative, self.root / relative)

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

    def test_product_purpose_and_progress_semantics_cannot_self_downgrade(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value.update(
                {
                    "purpose": "Maximize plans, inventories, and process artifacts.",
                    "successDefinition": "Success means all local tests are green.",
                }
            ),
        )
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__(
                "purpose", "Produce governance files without real outcomes."
            ),
        )
        self.mutate(
            "product/acceptance.json",
            lambda value: value.__setitem__(
                "progressRule", "Every passing test counts as product progress."
            ),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("constitution purpose is invalid", report["errors"])
        self.assertIn("constitution successDefinition is invalid", report["errors"])
        self.assertIn("program purpose is invalid", report["errors"])
        self.assertIn("acceptance progressRule is invalid", report["errors"])

    def test_criteria_must_be_exact_and_unique(self) -> None:
        def duplicate(value: dict) -> None:
            value["criteria"].append(deepcopy(value["criteria"][0]))

        self.mutate("product/acceptance.json", duplicate)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn("duplicate acceptance criterion O1", report["errors"])

    def test_criteria_reject_undeclared_self_promotion_fields(self) -> None:
        variants = (
            ("O1", {"accepted": True, "verified": True}),
            ("G1", {"passed": True}),
        )
        for criterion_id, additions in variants:
            with self.subTest(criterion_id=criterion_id):
                def self_promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == criterion_id
                    )
                    criterion.update(additions)

                self.mutate("product/acceptance.json", self_promote)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G2"])
                self.assertIn(
                    f"criterion {criterion_id} fields must match the code-owned schema",
                    report["errors"],
                )
                shutil.copy2(
                    ROOT / "product/acceptance.json",
                    self.root / "product/acceptance.json",
                )

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

    def test_release_criteria_semantics_cannot_self_downgrade(self) -> None:
        def self_accept(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["threshold"] = "Agent self-declaration is sufficient."
            criterion["operationalization"]["passRule"] = "The Agent declares success."
            criterion["operationalization"]["falsifiers"] = ["none"]
            criterion["operationalization"]["humanAuthority"] = (
                "The Agent owns acceptance."
            )

        self.mutate("product/acceptance.json", self_accept)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "acceptance criteria contract identity is invalid",
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

    def test_outcome_increment_can_observe_source_before_validator_implementation(self) -> None:
        def activate_o2(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O2")
            increment["workItems"][0]["acceptanceIds"].append("O2")

        self.mutate("product/program.json", activate_o2)
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["criterionStates"]["G4"])
        self.assertFalse(report["criterionStates"]["O2"])

    def test_current_release_has_no_prebuilt_outcome_validation_path(self) -> None:
        self.assertEqual(SUPPORTED_EVIDENCE_VALIDATORS, {})

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

    def test_active_increment_requires_exactly_one_active_work_item(self) -> None:
        def stall(value: dict) -> None:
            increment = self.activate_program(value)
            increment["workItems"][0]["state"] = "stopped"

        self.mutate("product/program.json", stall)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "active increment increment.fixture-current must have exactly one active work item",
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

    def test_program_graph_rejects_capability_added_requirements(self) -> None:
        variants = (
            (
                "increment workflow",
                lambda increment: increment.__setitem__(
                    "mandatoryWorkflow", "external-methodology"
                ),
                "increment increment.fixture-current fields must match the code-owned schema",
            ),
            (
                "work human round trip",
                lambda increment: increment["workItems"][0].__setitem__(
                    "humanRoundTrip", "user-selects-tool"
                ),
                "work item work.fixture-current fields must match the code-owned schema",
            ),
            (
                "cleanup shifted to user",
                lambda increment: increment["cleanupBoundary"].__setitem__(
                    "userCleanupRequired", True
                ),
                "increment increment.fixture-current requires the exact cleanup boundary fields",
            ),
        )
        for label, mutate_increment, expected_error in variants:
            with self.subTest(label=label):
                self.mutate(
                    "product/program.json",
                    lambda value: mutate_increment(self.activate_program(value)),
                )
                report = self.report()
                self.assertFalse(report["criterionStates"]["G4"])
                self.assertIn(expected_error, report["errors"])
                self.reset_program_fixture()

    def test_empty_ready_current_graph_is_valid_but_not_product_progress(self) -> None:
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

    def test_explicitly_granted_consumer_configuration_is_agent_executed(self) -> None:
        def add_granted_configuration(value: dict) -> None:
            self.activate_program(value)["workItems"][0]["operationIds"].append(
                "bounded-consumer-configuration-after-explicit-grant"
            )

        self.mutate("product/program.json", add_granted_configuration)
        report = self.report()
        self.assertTrue(report["criterionStates"]["G1"], report["errors"])
        program = json.loads((self.root / "product/program.json").read_text())
        self.assertIn("new-trust", program["authorityBoundary"]["userOwns"])

    def test_stopped_work_cannot_hide_an_authority_violation(self) -> None:
        def hide(value: dict) -> None:
            work = self.activate_program(value)["workItems"][0]
            work["state"] = "stopped"
            work["operationIds"].append("release")

        self.mutate("product/program.json", hide)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "work item work.fixture-current exceeds agent authority",
            report["errors"],
        )

    def test_cancelled_work_does_not_claim_an_authority_attempt(self) -> None:
        def cancel_before_execution(value: dict) -> None:
            increment = self.ensure_increment(value, state="cancelled")
            work = increment["workItems"][0]
            work["state"] = "cancelled"
            work["operationIds"].append("release")

        self.mutate("product/program.json", cancel_before_execution)
        report = self.report()
        self.assertTrue(report["criterionStates"]["G1"], report["errors"])
        self.assertNotIn(
            "work item work.fixture-current exceeds agent authority",
            report["errors"],
        )

    def test_authority_boundary_rejects_undeclared_fields(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value["authorityBoundary"].__setitem__(
                "agentMayPublishWithoutHumanAuthority", True
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "program authorityBoundary fields must match the code-owned schema",
            report["errors"],
        )

    def test_human_authority_cannot_be_removed(self) -> None:
        def remove(value: dict) -> None:
            value["authorityBoundary"]["userOwns"].remove("new-trust")

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program userOwns omits a mandatory human authority", report["errors"])

    def test_user_authority_cannot_absorb_agent_work(self) -> None:
        def add(value: dict) -> None:
            value["authorityBoundary"]["userOwns"].append(
                "skill-and-workflow-selection"
            )

        self.mutate("product/program.json", add)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "program userOwns contains an undeclared human authority",
            report["errors"],
        )

    def test_agent_authority_cannot_silently_drop_owned_operations(self) -> None:
        def remove(value: dict) -> None:
            value["authorityBoundary"]["agentOwnsWithinBoundedAuthority"].remove(
                "git-push"
            )

        self.mutate("product/program.json", remove)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "program agent authority must equal the code-owned operation set",
            report["errors"],
        )

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

    def test_cancelled_and_stopped_work_count_toward_process_loss(self) -> None:
        baseline = self.read_json("product/program.json")
        for terminal_state in ("cancelled", "stopped"):
            with self.subTest(terminal_state=terminal_state):
                program = deepcopy(baseline)
                increment = self.activate_program(program)
                first = increment["workItems"][0]
                first["state"] = terminal_state
                second = deepcopy(first)
                second["id"] = f"work.after-{terminal_state}"
                second["state"] = "active"
                increment["workItems"].append(second)
                self.write_json("product/program.json", program)
                report = self.report()
                self.assertFalse(report["criterionStates"]["G4"])
                self.assertIn(
                    "increment increment.fixture-current exceeds its "
                    "outcome-neutral work budget",
                    report["errors"],
                )

    def test_ready_program_cannot_accumulate_closed_outcome_neutral_queue(self) -> None:
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

    def test_ready_program_retains_completed_validated_outcome_binding(self) -> None:
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
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["criterionStates"]["O1"])
        self.assertTrue(report["criterionStates"]["G4"])

    def test_cancelled_or_stopped_increment_cannot_retain_outcome_binding(self) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(criterion_ids=["O1"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        baseline = self.read_json("product/program.json")
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            for state in ("cancelled", "stopped"):
                with self.subTest(state=state):
                    program = deepcopy(baseline)
                    program["increments"][0]["state"] = state
                    self.write_json("product/program.json", program)
                    report = self.report()
                    self.assertFalse(report["criterionStates"]["O1"])
                    self.assertFalse(report["criterionStates"]["G4"])
                    self.assertIn(
                        "only a completed increment may retain validated outcome "
                        f"binding: {FIXTURE_INCREMENT_ID}",
                        report["errors"],
                    )

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

    def test_invalid_process_graph_suppresses_outcome_and_cannot_reuse_its_evidence(self) -> None:
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
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertEqual(report["outcomes"]["verified"], 0)
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

    def test_conventional_residue_file_fails_closed_with_empty_graph(self) -> None:
        residue = self.root / ".tmp"
        residue.write_text("residue", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository cleanup residue remains: .tmp", report["errors"])

    def test_repository_residue_enumeration_error_fails_closed(self) -> None:
        def unreadable_walk(root, *, topdown, followlinks, onerror=None):
            if onerror is not None:
                onerror(PermissionError("fixture access denied"))
            return []

        with patch("harness.control.os.walk", side_effect=unreadable_walk):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn("repository residue cannot be enumerated", report["errors"])

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

    def test_undeclared_nested_harness_code_cannot_escape_authority_scan(self) -> None:
        nested = self.root / "harness" / "nested" / "authority.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("VALUE = 'hidden authority'\n", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "undeclared Harness authority file: harness/nested/authority.py",
            report["errors"],
        )

    def test_harness_authority_enumeration_error_fails_closed(self) -> None:
        real_walk = os.walk

        def unreadable_harness(root, *, topdown, followlinks, onerror=None):
            if Path(root).name == "harness":
                if onerror is not None:
                    onerror(PermissionError("fixture access denied"))
                return []
            return real_walk(
                root,
                topdown=topdown,
                followlinks=followlinks,
                onerror=onerror,
            )

        with patch("harness.control.os.walk", side_effect=unreadable_harness):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("Harness authority closure cannot be enumerated", report["errors"])

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
        self.assertFalse(report["criterionStates"]["G2"])
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

        def precede_observation_below_microsecond(value: dict) -> None:
            value["observedAt"] = "2026-08-12T03:00:00.0000009+08:00"
            value["authority"]["decidedAt"] = "2026-08-12T03:00:00.0000001+08:00"

        mutations = {
            "boolean schema": lambda value: value.__setitem__("schema", True),
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
            "decision precedes observation": lambda value: value["authority"].__setitem__(
                "decidedAt", "2026-08-12T02:59:59+08:00"
            ),
            "sub-microsecond decision precedes observation": (
                precede_observation_below_microsecond
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

    def test_evidence_validator_must_return_literal_true(self) -> None:
        for validator_result in (False, "truthy-but-not-bool"):
            with self.subTest(validator_result=validator_result):
                self.map_outcome_to_latest_work("O1")
                evidence = self.evidence_document(criterion_ids=["O1"])
                self.write_json("product/evidence/bound.json", evidence)

                def promote(value: dict) -> None:
                    criterion = next(
                        item for item in value["criteria"] if item["id"] == "O1"
                    )
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/bound.json"]

                self.mutate("product/acceptance.json", promote)
                validator = (
                    lambda document, criterion_id, root, errors: validator_result
                )
                with patch(
                    "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
                    self.validator_registry(validator),
                ):
                    report = self.report()
                self.assertFalse(report["criterionStates"]["O1"])
                self.assertFalse(report["criterionStates"]["G2"])
                self.assertIn(
                    "criterion O1 evidence validator did not return true: product/evidence/bound.json",
                    report["errors"],
                )
                self.reset_program_fixture()
                shutil.copy2(
                    ROOT / "product/acceptance.json",
                    self.root / "product/acceptance.json",
                )

    def test_evidence_validator_must_bind_the_evidence_increment(self) -> None:
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
            self.validator_registry(
                validator,
                increment_ids=frozenset({"increment.other-task"}),
            ),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "criterion O1 evidence validator is not bound to "
            f"increment {FIXTURE_INCREMENT_ID}: test-validator",
            report["errors"],
        )

    def test_evidence_cannot_carry_unbound_criterion_claims(self) -> None:
        self.map_outcome_to_latest_work("O1")
        evidence = self.evidence_document(criterion_ids=["O1", "O2"])
        self.write_json("product/evidence/bound.json", evidence)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = ["product/evidence/bound.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "criterion O1 evidence shape is invalid: product/evidence/bound.json",
            report["errors"],
        )

    def test_distinct_evidence_files_cannot_reuse_one_identity(self) -> None:
        self.map_outcome_to_latest_work("O1")
        first = self.evidence_document(criterion_ids=["O1"])
        second = deepcopy(first)
        self.write_json("product/evidence/first.json", first)
        self.write_json("product/evidence/second.json", second)

        def promote(value: dict) -> None:
            criterion = next(item for item in value["criteria"] if item["id"] == "O1")
            criterion["assessment"] = "verified"
            criterion["evidence"] = [
                "product/evidence/first.json",
                "product/evidence/second.json",
            ]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertFalse(report["criterionStates"]["G2"])
        self.assertIn(
            "duplicate evidence id typed-o2: product/evidence/second.json",
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

    def test_ready_program_has_no_active_increment_and_remains_in_progress(self) -> None:
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["activeIncrement"], None)
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"]["verified"], 0)

    def test_obsolete_paused_program_state_is_rejected(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("status", "paused"),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertEqual(report["completionState"], "in-progress")
        self.assertIn(
            "program status must be active, ready, or completed",
            report["errors"],
        )

    def test_ready_program_cannot_report_accepted_with_all_outcomes_verified(self) -> None:
        outcome_ids = ["O1", "O2", "O3", "O4", "O5"]
        for criterion_id in outcome_ids:
            self.map_outcome_to_latest_work(criterion_id)
        evidence = self.evidence_document(criterion_ids=outcome_ids)
        self.write_json("product/evidence/all-outcomes.json", evidence)

        def promote(value: dict) -> None:
            for criterion in value["criteria"]:
                if criterion["id"] in outcome_ids:
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = ["product/evidence/all-outcomes.json"]

        self.mutate("product/acceptance.json", promote)
        validator = lambda document, criterion_id, root, errors: True
        with patch(
            "harness.control.SUPPORTED_EVIDENCE_VALIDATORS",
            self.validator_registry(validator),
        ):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["programStatus"], "ready")
        self.assertEqual(report["outcomes"]["verified"], 5)
        self.assertEqual(report["completionState"], "in-progress")

    def test_ready_program_cannot_erase_agent_owned_non_outcome_progression(self) -> None:
        self.mutate(
            "product/program.json",
            lambda value: value.pop("progressionPolicy", None),
        )
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program progressionPolicy is invalid", report["errors"])

    def test_program_cannot_reclassify_bound_product_delivery_as_missing_demand(self) -> None:
        def erase_product_demand(value: dict) -> None:
            value["progressionPolicy"].pop(
                "boundProductDeliveryDemandDisposition", None
            )

        self.mutate("product/program.json", erase_product_demand)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("program progressionPolicy is invalid", report["errors"])

    def test_ready_program_cannot_retain_active_work(self) -> None:
        def invalid(value: dict) -> None:
            self.activate_program(value)
            value["status"] = "ready"

        self.mutate("product/program.json", invalid)
        report = self.report()
        self.assertFalse(report["valid"])
        self.assertIn("ready program must have no active increment", report["errors"])
        self.assertIn("ready program must have a terminal increment graph", report["errors"])

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
            "only a ready program may have an empty current increment graph",
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
            "program priorRelease must match the code-owned historical milestone",
            report["errors"],
        )

    def test_historical_milestone_identity_is_code_owned(self) -> None:
        fabricated = {
            "release": "v9.9",
            "state": "accepted-terminal-product",
            "revision": "0123456789abcdef0123456789abcdef01234567",
            "currentAuthority": False,
        }
        self.mutate(
            "product/program.json",
            lambda value: value.__setitem__("priorRelease", fabricated.copy()),
        )
        self.mutate(
            "product/constitution.json",
            lambda value: value["historicalMilestones"].__setitem__(
                0,
                {**fabricated, "claimLimit": "fabricated but non-empty"},
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "program priorRelease must match the code-owned historical milestone",
            report["errors"],
        )

    def test_historical_milestone_claim_limit_is_code_owned(self) -> None:
        self.mutate(
            "product/constitution.json",
            lambda value: value["historicalMilestones"][0].__setitem__(
                "claimLimit", "terminal product and cross-host proof"
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "constitution historical milestone must match the code-owned record",
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

    def test_supporting_document_set_cannot_silently_shrink(self) -> None:
        def omit_security_policy(value: dict) -> None:
            value["supportingDocuments"].remove("SECURITY.md")

        self.mutate("product/constitution.json", omit_security_policy)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "supportingDocuments must equal the code-owned semantic document set",
            report["errors"],
        )

    def test_supporting_document_set_cannot_silently_expand(self) -> None:
        (self.root / "docs" / "extra-process.md").write_text(
            "# Extra process\n", encoding="utf-8"
        )
        self.mutate(
            "product/constitution.json",
            lambda value: value["supportingDocuments"].append(
                "docs/extra-process.md"
            ),
        )
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "supportingDocuments must equal the code-owned semantic document set",
            report["errors"],
        )

    def test_empty_supporting_document_is_rejected(self) -> None:
        (self.root / "README.md").write_text("\n", encoding="utf-8")
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("supporting document is empty: README.md", report["errors"])

    def test_undeclared_product_root_json_is_rejected(self) -> None:
        self.write_json("product/extra.json", {"schema": 1})
        report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("undeclared product authority JSON: product/extra.json", report["errors"])

    def test_product_authority_enumeration_error_fails_closed(self) -> None:
        real_scandir = os.scandir

        def unreadable_product(path):
            if Path(path).name == "product":
                raise PermissionError("fixture access denied")
            return real_scandir(path)

        with patch("harness.control.os.scandir", side_effect=unreadable_product):
            report = self.report()
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn("product authority root cannot be enumerated", report["errors"])

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
