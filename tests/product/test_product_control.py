from __future__ import annotations

from copy import deepcopy
import hashlib
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
CLAUDE_PLUGIN_ROOT = ROOT / "adapters/agent-autonomy-harness-claude"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import harness.control as control  # noqa: E402
from harness.continuation import _serialize_bounded  # noqa: E402
from harness.claude_reference import (  # noqa: E402
    ADAPTER_ID as CLAUDE_ADAPTER_ID,
    render_session_start_context as render_claude_session_start_context,
)
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
    "harness/claude_reference.py",
    "harness/codex_reference.py",
    "harness/continuation.py",
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
        registration = self.root / "product/evidence/fixture-registration.json"
        if registration.exists():
            registration.unlink()
        self.reset_acceptance_fixture()

    def reset_acceptance_fixture(self) -> None:
        """Keep generic tests independent of live outcome evidence and validators."""

        acceptance = json.loads(
            (ROOT / "product/acceptance.json").read_text(encoding="utf-8")
        )
        for criterion in acceptance["criteria"]:
            if criterion["id"] in {"O1", "O2", "O3", "O4", "O5"}:
                criterion["assessment"] = "planned"
                criterion.pop("evidence", None)
        self.write_json("product/acceptance.json", acceptance)

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
            "taskRegistration": None,
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
            self.bind_fixture_registration(increment)

        self.mutate("product/program.json", add_mapping)

    def bind_fixture_registration(self, increment: dict) -> None:
        outcome_ids = sorted(
            set(increment["acceptanceIds"]) & {"O1", "O2", "O3", "O4", "O5"}
        )
        if not outcome_ids:
            increment["taskRegistration"] = None
            return
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        fields = {
            field
            for criterion_id in outcome_ids
            for field in criteria[criterion_id]["operationalization"][
                "preRegistrationFields"
            ]
        }
        floors = {
            "quality": "fixture quality floor",
            "safety": "fixture safety floor",
            "evidence": "fixture evidence floor",
            "residue": "fixture residue floor",
        }
        interventions = ["fixture material intervention"]
        losses = ["fixture material collaboration loss"]
        aliases = {
            "registeredAt": "2026-08-12T02:59:00+08:00",
            "taskIdentity": "natural-task.fixture-current",
            "namedHumanAcceptor": "fixture reviewer",
            "qualitySafetyEvidenceAndResidueFloors": floors,
            "materialInterventionTaxonomy": interventions,
            "materialCollaborationLossTaxonomy": losses,
        }
        registration = {
            "schema": 1,
            "id": "registration.fixture-current",
            "registeredAt": aliases["registeredAt"],
            "taskIdentity": aliases["taskIdentity"],
            "incrementId": increment["id"],
            "criterionIds": outcome_ids,
            "preRegistrationValues": {
                field: aliases.get(field, f"fixture value for {field}")
                for field in sorted(fields)
            },
            "acceptanceAuthority": {
                "locator": "product/acceptance.json",
                "criteriaContractSha256": (
                    "c3993f40052ac2de75193c5cf923d98d6bd0b899aa7fc42ddeb772103932baf6"
                ),
            },
            "namedHumanAcceptor": aliases["namedHumanAcceptor"],
            "qualitySafetyEvidenceAndResidueFloors": floors,
            "materialInterventionTaxonomy": interventions,
            "materialCollaborationLossTaxonomy": losses,
            "sourceCaptureEligibilityAndStopRule": {
                "measurementStartsAfter": "the committed registration binding",
                "eligibleSources": ["fixture source after registration"],
                "ineligibleSources": ["fixture source before registration"],
                "stopRule": "stop on any fixture floor failure",
            },
            "claimLimits": ["fixture task only"],
        }
        relative = "product/evidence/fixture-registration.json"
        self.write_json(relative, registration)
        increment["taskRegistration"] = {
            "locator": relative,
            "sha256": hashlib.sha256((self.root / relative).read_bytes()).hexdigest(),
        }

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

    def claude_session_start_payload(self, *, source: str = "startup") -> dict:
        return {
            "session_id": "00000000-0000-4000-8000-000000000002",
            "transcript_path": str(self.root / "must-not-be-read.jsonl"),
            "cwd": str(self.root),
            "hook_event_name": "SessionStart",
            "source": source,
            "model": "claude-test",
        }

    def test_current_v02_contract_has_four_verified_outcomes_and_input_bound_o5_work(
        self,
    ) -> None:
        report = verify_product(ROOT)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["release"], "v0.2")
        self.assertEqual(report["programStatus"], "active")
        self.assertEqual(
            report["activeIncrement"],
            "increment.v0.2.portable-source-candidate-gate-input-bound",
        )
        self.assertEqual(report["completionState"], "in-progress")
        self.assertEqual(report["outcomes"], {"verified": 4, "total": 5})
        self.assertEqual(report["guardrails"], {"passed": 4, "total": 4})
        self.assertTrue(report["criterionStates"]["O1"])
        self.assertTrue(report["criterionStates"]["O3"])
        self.assertTrue(report["criterionStates"]["O2"])
        self.assertTrue(report["criterionStates"]["O4"])
        self.assertFalse(report["criterionStates"]["O5"])

    def test_codex_reference_cohort_must_cross_context_lifecycle_boundary(
        self,
    ) -> None:
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}
        o2 = criteria["O2"]
        o4 = criteria["O4"]
        self.assertIn(
            "contextLifecycleBoundaryAndContinuityFloor",
            o2["operationalization"]["preRegistrationFields"],
        )
        self.assertIn(
            "contextLifecycleTransitionAndRecovery",
            o2["operationalization"]["requiredMeasures"],
        )
        self.assertIn("native compaction", o2["operationalization"]["passRule"])
        self.assertIn(
            "reduces available conversation history or changes the task container",
            o2["operationalization"]["passRule"],
        )
        self.assertNotIn("resume", o2["operationalization"]["passRule"])
        self.assertIn(
            "referenceHostContextLifecycleCoverageRule",
            o4["operationalization"]["preRegistrationFields"],
        )
        self.assertIn(
            "referenceHostContextLifecycleTransitionAndRecovery",
            o4["operationalization"]["requiredMeasures"],
        )
        self.assertIn("native compaction", o4["operationalization"]["passRule"])
        self.assertNotIn("resume", o4["operationalization"]["passRule"])

    def test_task_topology_lifecycle_is_agent_owned(self) -> None:
        constitution = self.read_json("product/constitution.json")
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}

        self.assertIn(
            "task-topology-selection-reconciliation-merge-release-and-cleanup",
            constitution["collaborationModel"]["agentObligations"],
        )
        self.assertTrue(
            any(
                invariant.startswith("task topology is demand-driven:")
                for invariant in constitution["fixedInvariants"]
            )
        )
        for criterion_id in ("O1", "O2", "O4"):
            criterion = criteria[criterion_id]
            self.assertIn("topology", criterion["threshold"])
            self.assertIn("merge or conclusion reconciliation", criterion["operationalization"]["passRule"])
        for criterion_id in ("O1", "O2"):
            operationalization = criteria[criterion_id]["operationalization"]
            self.assertIn(
                "taskTopologyBoundaryAndLifecycleFloor",
                operationalization["preRegistrationFields"],
            )
            self.assertIn(
                "taskTopologyLifecycleEvents",
                operationalization["requiredMeasures"],
            )
        self.assertIn(
            "taskTopologyLifecycleAndBurden",
            criteria["O4"]["operationalization"]["requiredMeasures"],
        )
        self.assertIn(
            "commonTaskTopologyLifecycle",
            criteria["O5"]["operationalization"]["preRegistrationFields"],
        )
        self.assertIn(
            "taskTopologyParity",
            criteria["O5"]["operationalization"]["requiredMeasures"],
        )

    def test_context_carrier_fitness_and_transition_is_agent_owned(self) -> None:
        constitution = self.read_json("product/constitution.json")
        acceptance = self.read_json("product/acceptance.json")
        criteria = {item["id"]: item for item in acceptance["criteria"]}

        self.assertIn(
            "context-carrier-fitness-observation-and-proactive-transition",
            constitution["collaborationModel"]["agentObligations"],
        )
        self.assertTrue(
            any(
                invariant.startswith("conversation-carrier fitness is Agent-owned:")
                for invariant in constitution["fixedInvariants"]
            )
        )
        for criterion_id in ("O1", "O2", "O4"):
            operationalization = criteria[criterion_id]["operationalization"]
            self.assertIn(
                "contextCarrierFitnessSignalsAndTransitionRule",
                operationalization["preRegistrationFields"],
            )
            self.assertIn(
                "contextCarrierFitnessObservationsAndTransitions",
                operationalization["requiredMeasures"],
            )
            self.assertIn("preventable context quality or capacity loss", operationalization["passRule"])
            self.assertIn("unknown", operationalization["passRule"])
        self.assertIn(
            "commonContextCarrierFitnessAndTransitionLifecycle",
            criteria["O5"]["operationalization"]["preRegistrationFields"],
        )
        self.assertIn(
            "contextCarrierFitnessAndTransitionParity",
            criteria["O5"]["operationalization"]["requiredMeasures"],
        )

    def test_public_cli_reports_the_same_contract(self) -> None:
        completed = self.run_cli(root=ROOT)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["release"], "v0.2")
        self.assertEqual(report["programStatus"], "active")
        self.assertEqual(
            report["activeIncrement"],
            "increment.v0.2.portable-source-candidate-gate-input-bound",
        )
        self.assertEqual(report["outcomes"], {"verified": 4, "total": 5})
        self.assertTrue(report["valid"])

    def test_evidence_git_cache_is_bounded_to_one_verification_context(self) -> None:
        token = control._EVIDENCE_GIT_CACHE.set({})
        try:
            with patch("harness.control.subprocess.run", wraps=subprocess.run) as run:
                self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
                self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
                self.assertEqual(run.call_count, 1)
        finally:
            control._EVIDENCE_GIT_CACHE.reset(token)

        with patch("harness.control.subprocess.run", wraps=subprocess.run) as run:
            self.assertIsNone(control._evidence_git(self.root, "rev-parse", "HEAD"))
            self.assertEqual(run.call_count, 1)

    def test_plain_cli_exposes_program_and_completion_states(self) -> None:
        completed = self.run_cli(json_output=False, root=ROOT)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("v0.2: active, in-progress (4/5 outcomes)", completed.stdout)

    def test_codex_session_start_adapter_projects_live_authority(self) -> None:
        payload = self.codex_session_start_payload(source="resume")
        context = render_session_start_context(self.root, payload)
        self.assertIsNotNone(context)
        projection = json.loads(context)
        self.assertEqual(projection["adapter"], ADAPTER_ID)
        self.assertEqual(projection["event"], {"name": "SessionStart", "source": "resume"})
        self.assertEqual(projection["program"]["status"], "ready")
        self.assertEqual(
            projection["authorityPaths"],
            [
                "product/constitution.json",
                "product/program.json",
                "product/acceptance.json",
            ],
        )
        self.assertEqual(projection["remainingContextCapacity"], "unknown")
        self.assertEqual(projection["repositoryCheckpoint"]["state"], "unknown")
        self.assertEqual(projection["projectionBudget"]["characters"], len(context))
        self.assertLessEqual(len(context), 3072)
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
            projection["currentWork"]["workItem"],
            {"id": FIXTURE_WORK_ID, "state": "active"},
        )
        self.assertEqual(
            projection["currentWork"]["cleanupPaths"],
            [".tmp", "harness/__pycache__", "tests/product/__pycache__"],
        )
        self.assertLessEqual(len(context), 3072)

    def test_common_projection_does_not_copy_unbounded_active_work_prose(self) -> None:
        def activate_long_work(program: dict) -> None:
            increment = self.activate_program(program)
            for field in ("observedProblem", "hypothesis", "falsifier", "stopCondition"):
                increment[field] = field + ":" + ("x" * 10000)

        self.mutate("product/program.json", activate_long_work)
        context = render_session_start_context(
            self.root, self.codex_session_start_payload(source="compact")
        )
        projection = json.loads(context)
        self.assertEqual(projection["currentWork"]["id"], FIXTURE_INCREMENT_ID)
        self.assertNotIn("observedProblem", projection["currentWork"])
        self.assertNotIn("hypothesis", projection["currentWork"])
        self.assertLessEqual(len(context), 3072)

    def test_common_projection_has_a_bounded_second_level_fallback(self) -> None:
        context = _serialize_bounded(
            {
                "schema": 1,
                "adapter": "fixture-adapter",
                "role": "derived-read-only-continuation-context",
                "event": {"name": "SessionStart", "source": "compact"},
                "authorityPaths": ["product/program.json"],
                "verification": {
                    "valid": True,
                    "completionState": "in-progress",
                    "errors": ["verification:" + ("x" * 10000)],
                },
                "repositoryCheckpoint": {"state": "observed"},
                "program": {"status": "active"},
                "currentWork": {
                    "id": FIXTURE_INCREMENT_ID,
                    "workItem": {"id": FIXTURE_WORK_ID, "state": "active"},
                    "taskRegistration": "registration:" + ("x" * 10000),
                },
                "claimBoundary": "fixture claim boundary",
            }
        )
        projection = json.loads(context)
        self.assertLessEqual(len(context), 3072)
        self.assertEqual(
            projection["projectionBudget"]["state"], "fallback-overflow"
        )
        self.assertEqual(
            projection["currentWorkIdentity"]["incrementId"], FIXTURE_INCREMENT_ID
        )
        self.assertNotIn("registration:" + ("x" * 100), context)

    def test_common_projection_reports_git_checkpoint_without_dirty_path_names(self) -> None:
        def git(*arguments: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["git", "-C", str(self.root), *arguments],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )

        initialized = git("init", "-b", "main")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertEqual(git("add", ".").returncode, 0)
        committed = git(
            "-c",
            "user.name=Harness Test",
            "-c",
            "user.email=harness-test@example.invalid",
            "commit",
            "-m",
            "fixture",
        )
        self.assertEqual(committed.returncode, 0, committed.stderr)

        clean_context = render_session_start_context(
            self.root, self.codex_session_start_payload(source="startup")
        )
        clean = json.loads(clean_context)["repositoryCheckpoint"]
        self.assertEqual(clean["state"], "observed")
        self.assertEqual(clean["branch"], "main")
        self.assertRegex(clean["head"], r"^[0-9a-f]{40}$")
        self.assertEqual(clean["upstream"], "absent")
        self.assertEqual(clean["aheadBehind"], "unknown-no-upstream")
        self.assertEqual(clean["worktreeCount"], 1)
        self.assertEqual(clean["dirtyEntryCount"], 0)

        private_path = self.root / "private-reconciliation-secret.txt"
        private_path.write_text("must not enter projection", encoding="utf-8")
        dirty_context = render_session_start_context(
            self.root, self.codex_session_start_payload(source="compact")
        )
        dirty = json.loads(dirty_context)["repositoryCheckpoint"]
        self.assertEqual(dirty["dirtyEntryCount"], 1)
        self.assertNotEqual(dirty["statusSha256"], clean["statusSha256"])
        self.assertNotIn(private_path.name, dirty_context)
        private_path.unlink()

        detached = git("checkout", "--detach")
        self.assertEqual(detached.returncode, 0, detached.stderr)
        detached_context = render_session_start_context(
            self.root, self.codex_session_start_payload(source="resume")
        )
        checkpoint = json.loads(detached_context)["repositoryCheckpoint"]
        self.assertEqual(checkpoint["branch"], "detached")
        self.assertRegex(checkpoint["head"], r"^[0-9a-f]{40}$")
        self.assertLessEqual(len(detached_context), 3072)

    def test_common_projection_keeps_unavailable_git_explicit(self) -> None:
        with patch("harness.continuation._git_output", return_value=None):
            context = render_session_start_context(
                self.root, self.codex_session_start_payload(source="compact")
            )
        checkpoint = json.loads(context)["repositoryCheckpoint"]
        self.assertEqual(checkpoint["state"], "unknown")
        self.assertEqual(checkpoint["reason"], "git-status-unavailable")
        self.assertEqual(checkpoint["dirtyEntryCount"], "unknown")
        self.assertLessEqual(len(context), 3072)

    def test_common_projection_keeps_malformed_git_explicit(self) -> None:
        with patch(
            "harness.continuation._git_output",
            return_value=b"# branch.oid \xff\0",
        ):
            context = render_session_start_context(
                self.root, self.codex_session_start_payload(source="resume")
            )
        checkpoint = json.loads(context)["repositoryCheckpoint"]
        self.assertEqual(checkpoint["state"], "unknown")
        self.assertEqual(checkpoint["reason"], "git-status-malformed")
        self.assertLessEqual(len(context), 3072)

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
        self.assertLessEqual(len(context), 3072)

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
        payload_identity = hashlib.sha256()
        payload_files = (
            "hooks/hooks.json",
            "scripts/session_start.py",
            "skills/deliver-demand-driven-task/SKILL.md",
            "skills/deliver-demand-driven-task/agents/openai.yaml",
            "skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
        )
        for relative in payload_files:
            payload_identity.update(relative.encode("utf-8"))
            payload_identity.update(b"\0")
            payload_identity.update((CODEX_PLUGIN_ROOT / relative).read_bytes())
            payload_identity.update(b"\0")
        self.assertEqual(
            manifest["version"],
            "0.2.0-candidate.6+codex.payload-"
            f"{payload_identity.hexdigest()[:12]}",
        )
        self.assertFalse((CODEX_PLUGIN_ROOT / "plugin.json").exists())
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("apps", manifest)
        self.assertEqual(
            manifest["interface"]["defaultPrompt"],
            [
                "Tell me the result you want. I will own the capability route, continuity, verification, and cleanup."
            ],
        )
        self.assertEqual(
            manifest["interface"]["capabilities"], ["Interactive", "Read"]
        )
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
                *(CODEX_PLUGIN_ROOT / relative for relative in payload_files),
            )
        ).lower()
        self.assertNotIn("cc switch", candidate_text)

    def test_codex_plugin_skill_is_implicit_thin_and_profile_bound(self) -> None:
        skill_root = (
            CODEX_PLUGIN_ROOT / "skills/deliver-demand-driven-task"
        )
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        interface = (skill_root / "agents/openai.yaml").read_text(
            encoding="utf-8"
        )
        projected_profile = (
            skill_root / "references/demand-to-capability-profile.md"
        ).read_bytes()

        self.assertLessEqual(len(skill.splitlines()), 60)
        self.assertNotIn("TODO", skill)
        self.assertIn("do not use for simple conversation", skill.lower())
        self.assertIn("read\n`references/demand-to-capability-profile.md` completely", skill)
        self.assertIn("Do not teach or expose capability", skill)
        self.assertIn("treat unavailable capacity as\n   unknown", skill)
        self.assertIn("allow_implicit_invocation: true", interface)
        self.assertNotIn("dependencies:", interface)
        self.assertEqual(
            projected_profile,
            (ROOT / "docs/DEMAND-TO-CAPABILITY-PROFILE.md").read_bytes(),
        )
        self.assertFalse((CODEX_PLUGIN_ROOT / ".mcp.json").exists())
        self.assertFalse((CODEX_PLUGIN_ROOT / ".app.json").exists())

    def test_codex_workspace_marketplace_exposes_only_the_thin_projection(
        self,
    ) -> None:
        marketplace = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        self.assertEqual(marketplace["name"], "agent-autonomy-harness")
        self.assertEqual(
            marketplace["interface"], {"displayName": "Agent Autonomy Harness"}
        )
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "agent-autonomy-harness-codex")
        self.assertEqual(
            entry["source"],
            {
                "source": "local",
                "path": "./adapters/agent-autonomy-harness-codex",
            },
        )
        self.assertEqual(
            entry["policy"],
            {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        )
        source = (ROOT / entry["source"]["path"]).resolve(strict=True)
        self.assertEqual(source, CODEX_PLUGIN_ROOT.resolve(strict=True))
        self.assertNotEqual(source, ROOT.resolve(strict=True))

    def test_claude_reference_adapter_preserves_common_projection_semantics(
        self,
    ) -> None:
        codex = json.loads(
            render_session_start_context(
                self.root, self.codex_session_start_payload(source="compact")
            )
        )
        claude = json.loads(
            render_claude_session_start_context(
                self.root, self.claude_session_start_payload(source="compact")
            )
        )
        self.assertEqual(claude["adapter"], CLAUDE_ADAPTER_ID)
        self.assertEqual(
            claude["referenceHostSubstrate"]["version"], "2.1.232"
        )
        self.assertIn(
            "Commercial Terms and Privacy Policy",
            claude["referenceHostSubstrate"]["licenseOrTerms"],
        )
        self.assertIn(
            "package README.md",
            claude["referenceHostSubstrate"]["licenseOrTerms"],
        )
        for projection in (codex, claude):
            projection.pop("adapter")
            projection.pop("referenceHostSubstrate")
            projection.pop("projectionBudget")
        self.assertEqual(claude, codex)

    def test_package_exports_explicit_host_adapters_and_keeps_codex_aliases(
        self,
    ) -> None:
        import harness

        self.assertIs(
            harness.render_codex_session_start_context,
            render_session_start_context,
        )
        self.assertIs(
            harness.render_claude_session_start_context,
            render_claude_session_start_context,
        )
        self.assertIs(
            harness.render_session_start_context,
            render_session_start_context,
        )
        self.assertIs(harness.session_start_hook_output, session_start_hook_output)

    def test_claude_reference_adapter_supports_native_continuity_events(self) -> None:
        for source in ("startup", "resume", "clear", "compact"):
            with self.subTest(source=source):
                context = render_claude_session_start_context(
                    self.root, self.claude_session_start_payload(source=source)
                )
                projection = json.loads(context)
                self.assertEqual(
                    projection["event"], {"name": "SessionStart", "source": source}
                )

    def test_claude_reference_adapter_is_noop_for_unsupported_input(self) -> None:
        outside = self.claude_session_start_payload()
        outside["cwd"] = str(self.root.parent)
        self.assertIsNone(render_claude_session_start_context(self.root, outside))
        wrong_event = self.claude_session_start_payload()
        wrong_event["hook_event_name"] = "UserPromptSubmit"
        self.assertIsNone(render_claude_session_start_context(self.root, wrong_event))

    def test_claude_plugin_projection_is_thin_skill_hook_and_payload_bound(self) -> None:
        manifest = json.loads(
            (CLAUDE_PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text(
                encoding="utf-8"
            )
        )
        hooks = json.loads(
            (CLAUDE_PLUGIN_ROOT / "hooks/hooks.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "agent-autonomy-harness-claude")
        payload_identity = hashlib.sha256()
        payload_files = (
            "hooks/hooks.json",
            "scripts/session_start.py",
            "skills/deliver-demand-driven-task/SKILL.md",
            "skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
        )
        for relative in payload_files:
            payload_identity.update(relative.encode("utf-8"))
            payload_identity.update(b"\0")
            payload_identity.update((CLAUDE_PLUGIN_ROOT / relative).read_bytes())
            payload_identity.update(b"\0")
        self.assertEqual(
            manifest["version"],
            "0.2.0-candidate.6+claude.payload-"
            f"{payload_identity.hexdigest()[:12]}",
        )
        self.assertFalse((CLAUDE_PLUGIN_ROOT / "CLAUDE.md").exists())
        for component in ("commands", "agents", "mcpServers"):
            self.assertNotIn(component, manifest)
        self.assertNotIn("skills", manifest)
        self.assertTrue(
            (CLAUDE_PLUGIN_ROOT / "skills/deliver-demand-driven-task/SKILL.md").is_file()
        )
        self.assertEqual(set(hooks["hooks"]), {"SessionStart"})
        handlers = hooks["hooks"]["SessionStart"]
        self.assertEqual(len(handlers), 1)
        command = handlers[0]["hooks"][0]
        self.assertEqual(command["type"], "command")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", json.dumps(command))
        self.assertNotIn(str(ROOT), json.dumps(hooks))

    def test_claude_plugin_skill_reuses_exact_implicit_common_method(self) -> None:
        codex_skill_root = CODEX_PLUGIN_ROOT / "skills/deliver-demand-driven-task"
        claude_skill_root = CLAUDE_PLUGIN_ROOT / "skills/deliver-demand-driven-task"
        claude_skill = (claude_skill_root / "SKILL.md").read_text(encoding="utf-8")

        self.assertEqual(
            (claude_skill_root / "SKILL.md").read_bytes(),
            (codex_skill_root / "SKILL.md").read_bytes(),
        )
        self.assertEqual(
            (
                claude_skill_root
                / "references/demand-to-capability-profile.md"
            ).read_bytes(),
            (ROOT / "docs/DEMAND-TO-CAPABILITY-PROFILE.md").read_bytes(),
        )
        self.assertIn("Use implicitly", claude_skill)
        self.assertIn("do not use for simple conversation", claude_skill.lower())
        self.assertFalse((CLAUDE_PLUGIN_ROOT / ".mcp.json").exists())
        self.assertFalse((CLAUDE_PLUGIN_ROOT / "CLAUDE.md").exists())

    def test_claude_plugin_launcher_projects_from_nested_harness_cwd(self) -> None:
        nested = self.root / "docs/nested"
        nested.mkdir(parents=True)
        payload = self.claude_session_start_payload(source="compact")
        payload["cwd"] = str(nested)
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(CLAUDE_PLUGIN_ROOT / "scripts/session_start.py"),
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        projection = json.loads(completed.stdout)
        self.assertEqual(projection["adapter"], CLAUDE_ADAPTER_ID)
        self.assertEqual(projection["event"]["source"], "compact")
        self.assertNotIn("transcript_path", completed.stdout)
        self.assertNotIn(payload["session_id"], completed.stdout)

    def test_claude_plugin_launcher_is_silent_on_unsupported_or_drift(self) -> None:
        payload = self.claude_session_start_payload()
        payload["cwd"] = str(self.root.parent)
        for case in ("outside-root", "runtime-drift"):
            with self.subTest(case=case):
                if case == "runtime-drift":
                    payload["cwd"] = str(self.root)
                    with (self.root / "harness/control.py").open(
                        "a", encoding="utf-8"
                    ) as handle:
                        handle.write("\n# unreviewed runtime drift\n")
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        str(CLAUDE_PLUGIN_ROOT / "scripts/session_start.py"),
                    ],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stdout, "")

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
                if relative == "product/acceptance.json":
                    self.reset_acceptance_fixture()
                else:
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
                if relative == "product/acceptance.json":
                    self.reset_acceptance_fixture()
                else:
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
                self.reset_acceptance_fixture()

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

        self.reset_acceptance_fixture()

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
            self.bind_fixture_registration(increment)

        self.mutate("product/program.json", activate_o2)
        report = self.report()
        self.assertTrue(report["valid"], report["errors"])
        self.assertTrue(report["criterionStates"]["G4"])
        self.assertFalse(report["criterionStates"]["O2"])

    def test_outcome_increment_requires_content_addressed_task_registration(
        self,
    ) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "outcome-bearing increment increment.fixture-current requires an exact "
            "taskRegistration binding",
            report["errors"],
        )

    def test_task_registration_rejects_drift_or_missing_criterion_fields(self) -> None:
        def activate_o5(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].extend(["O1", "O5"])
            increment["workItems"][0]["acceptanceIds"].extend(["O1", "O5"])
            self.bind_fixture_registration(increment)

        self.mutate("product/program.json", activate_o5)
        baseline = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"

        registration = self.read_json(relative)
        registration["preRegistrationValues"].pop("equivalenceTolerance")
        self.write_json(relative, registration)
        baseline["increments"][0]["taskRegistration"]["sha256"] = hashlib.sha256(
            (self.root / relative).read_bytes()
        ).hexdigest()
        self.write_json("product/program.json", baseline)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            f"task registration {relative} shape is invalid",
            report["errors"],
        )

        self.bind_fixture_registration(baseline["increments"][0])
        self.write_json("product/program.json", baseline)
        registration = self.read_json(relative)
        registration["claimLimits"].append("unbound post-registration drift")
        self.write_json(relative, registration)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current taskRegistration identity mismatch",
            report["errors"],
        )

    def test_task_registration_binds_current_acceptance_contract(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(increment)

        self.mutate("product/program.json", activate_o1)
        program = self.read_json("product/program.json")
        relative = "product/evidence/fixture-registration.json"
        registration = self.read_json(relative)
        registration["acceptanceAuthority"]["criteriaContractSha256"] = "0" * 64
        self.write_json(relative, registration)
        program["increments"][0]["taskRegistration"]["sha256"] = hashlib.sha256(
            (self.root / relative).read_bytes()
        ).hexdigest()
        self.write_json("product/program.json", program)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            f"task registration {relative} shape is invalid",
            report["errors"],
        )

    def test_task_registration_locator_is_canonical_and_non_nested(self) -> None:
        def activate_o1(value: dict) -> None:
            increment = self.activate_program(value)
            increment["acceptanceIds"].append("O1")
            increment["workItems"][0]["acceptanceIds"].append("O1")
            self.bind_fixture_registration(increment)
            increment["taskRegistration"]["locator"] = (
                "product/evidence/nested/fixture-registration.json"
            )

        self.mutate("product/program.json", activate_o1)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "increment increment.fixture-current has invalid taskRegistration locator",
            report["errors"],
        )

    def test_outcome_neutral_increment_rejects_registration_binding(self) -> None:
        def bind(value: dict) -> None:
            increment = self.activate_program(value)
            increment["taskRegistration"] = {
                "locator": "product/evidence/fixture-registration.json",
                "sha256": "0" * 64,
            }

        self.mutate("product/program.json", bind)
        report = self.report()
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "outcome-neutral increment increment.fixture-current must bind null "
            "taskRegistration",
            report["errors"],
        )

    def test_current_release_has_only_the_observed_task_bound_validators(self) -> None:
        self.assertEqual(
            set(SUPPORTED_EVIDENCE_VALIDATORS),
            {
                "public-intake-zero-knowledge-o1",
                "codex-demand-skill-plugin-o1",
                "claude-demand-skill-plugin-o1-o3",
                "continuation-reconciliation-o2",
                "codex-reference-calibration-o4",
            },
        )
        criteria, increments, validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "public-intake-zero-knowledge-o1"
        ]
        self.assertEqual(criteria, frozenset({"O1"}))
        self.assertEqual(
            increments,
            frozenset({"increment.v0.2.public-intake-zero-knowledge"}),
        )
        self.assertTrue(callable(validator))

        criteria, increments, validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "codex-reference-calibration-o4"
        ]
        self.assertEqual(criteria, frozenset({"O4"}))
        self.assertEqual(
            increments,
            frozenset({"increment.v0.2.codex-reference-calibration"}),
        )
        self.assertTrue(callable(validator))

        criteria, increments, validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "continuation-reconciliation-o2"
        ]
        self.assertEqual(criteria, frozenset({"O2"}))
        self.assertEqual(
            increments,
            frozenset(
                {"increment.v0.2.continuation-reconciliation-projection"}
            ),
        )
        self.assertTrue(callable(validator))

        criteria, increments, validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "codex-demand-skill-plugin-o1"
        ]
        self.assertEqual(criteria, frozenset({"O1"}))
        self.assertEqual(
            increments,
            frozenset({"increment.v0.2.codex-demand-skill-plugin"}),
        )
        self.assertTrue(callable(validator))

        criteria, increments, validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "claude-demand-skill-plugin-o1-o3"
        ]
        self.assertEqual(criteria, frozenset({"O1", "O3"}))
        self.assertEqual(
            increments,
            frozenset({"increment.v0.2.claude-demand-skill-plugin"}),
        )
        self.assertTrue(callable(validator))

    def test_public_intake_o1_validator_binds_observed_sources_and_result(self) -> None:
        document = json.loads(
            (
                ROOT
                / "product/evidence/public-intake-zero-knowledge-accepted-2026-08-14.json"
            ).read_text(encoding="utf-8")
        )
        validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "public-intake-zero-knowledge-o1"
        ][2]
        errors: list[str] = []
        self.assertTrue(validator(document, "O1", ROOT, errors), errors)

        mutations = {
            "wrong criterion": lambda value: None,
            "different human message": lambda value: value["authority"].__setitem__(
                "sourceMessageSha256", "0" * 64
            ),
            "different result blob": lambda value: value["artifacts"]["documents"][
                0
            ].__setitem__("resultBlob", "0" * 40),
            "broadened claim": lambda value: value["claimLimits"].clear(),
        }
        for label, mutate_document in mutations.items():
            with self.subTest(label=label):
                candidate = deepcopy(document)
                mutate_document(candidate)
                candidate_errors: list[str] = []
                candidate_criterion = "O2" if label == "wrong criterion" else "O1"
                self.assertFalse(
                    validator(candidate, candidate_criterion, ROOT, candidate_errors)
                )
                self.assertTrue(candidate_errors)

    def test_codex_skill_o1_validator_binds_source_result_and_process_cost(self) -> None:
        document = json.loads(
            (
                ROOT
                / "product/evidence/codex-demand-skill-plugin-accepted-2026-08-14.json"
            ).read_text(encoding="utf-8")
        )
        validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "codex-demand-skill-plugin-o1"
        ][2]
        errors: list[str] = []
        self.assertTrue(validator(document, "O1", ROOT, errors), errors)

        mutations = {
            "wrong criterion": lambda value: None,
            "different human record": lambda value: value["authority"].__setitem__(
                "sourceRecordSha256", "0" * 64
            ),
            "hidden process cost": lambda value: value["measures"][
                "materialCollaborationLossEvents"
            ]["nonMaterialHostGoalProcessNoise"].__setitem__("count", 0),
            "different Skill blob": lambda value: value["artifacts"][
                "taskFacingFiles"
            ][0].__setitem__("resultBlob", "0" * 40),
            "broadened claim": lambda value: value["claimLimits"].clear(),
        }
        for label, mutate_document in mutations.items():
            with self.subTest(label=label):
                candidate = deepcopy(document)
                mutate_document(candidate)
                candidate_errors: list[str] = []
                candidate_criterion = "O2" if label == "wrong criterion" else "O1"
                self.assertFalse(
                    validator(candidate, candidate_criterion, ROOT, candidate_errors)
                )
                self.assertTrue(candidate_errors)

    def test_claude_skill_validator_binds_source_result_and_o3_cohort(self) -> None:
        document = json.loads(
            (
                ROOT
                / "product/evidence/claude-demand-skill-plugin-accepted-2026-08-14.json"
            ).read_text(encoding="utf-8")
        )
        validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "claude-demand-skill-plugin-o1-o3"
        ][2]
        for criterion_id in ("O1", "O3"):
            with self.subTest(criterion_id=criterion_id):
                errors: list[str] = []
                self.assertTrue(validator(document, criterion_id, ROOT, errors), errors)

        mutations = {
            "wrong criterion": lambda value: None,
            "different human record": lambda value: value["authority"].__setitem__(
                "sourceRecordSha256", "0" * 64
            ),
            "hidden route gap": lambda value: value["measures"][
                "availableCapabilityAndGapResult"
            ][1].__setitem__("routeClass", "no-gap-retain-native"),
            "activated projection": lambda value: value["measures"][
                "provisionalProjectionDisposition"
            ].__setitem__("claude", "persistent-activation"),
            "broadened claim": lambda value: value["claimLimits"].clear(),
        }
        for label, mutate_document in mutations.items():
            with self.subTest(label=label):
                candidate = deepcopy(document)
                mutate_document(candidate)
                candidate_errors: list[str] = []
                candidate_criterion = "O2" if label == "wrong criterion" else "O3"
                self.assertFalse(
                    validator(
                        candidate,
                        candidate_criterion,
                        ROOT,
                        candidate_errors,
                    )
                )
                self.assertTrue(candidate_errors)

    def test_continuation_o2_validator_binds_accepted_task_and_cohort(self) -> None:
        document = json.loads(
            (
                ROOT
                / "product/evidence/continuation-reconciliation-projection-2026-08-14.json"
            ).read_text(encoding="utf-8")
        )
        validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "continuation-reconciliation-o2"
        ][2]
        cache_token = control._EVIDENCE_GIT_CACHE.set({})
        self.addCleanup(control._EVIDENCE_GIT_CACHE.reset, cache_token)
        errors: list[str] = []
        self.assertTrue(validator(document, "O2", ROOT, errors), errors)

        mutations = {
            "missing human decision": lambda value: value["authority"].__setitem__(
                "decisionState", "pending"
            ),
            "different active baseline": lambda value: value["artifacts"][
                "baselineActiveProjection"
            ].__setitem__("characters", 4096),
            "dirty path exposure": lambda value: value["artifacts"][
                "dirtyCodexProjection"
            ].__setitem__("dirtyPathNamesExposed", True),
            "hidden intervention": lambda value: value["measures"][
                "materialUserCapabilityOrchestrationInterventions"
            ].__setitem__("count", 1),
            "lost strict reduction": lambda value: value["measures"][
                "outcomeComparison"
            ].__setitem__("strictReduction", False),
            "broadened claim": lambda value: value["claimLimits"].clear(),
        }
        for label, mutate_document in mutations.items():
            with self.subTest(label=label):
                candidate = deepcopy(document)
                mutate_document(candidate)
                candidate_errors: list[str] = []
                self.assertFalse(
                    validator(candidate, "O2", ROOT, candidate_errors)
                )
                self.assertTrue(candidate_errors)

    def test_codex_reference_o4_validator_binds_accepted_fixed_mixed_cohort(
        self,
    ) -> None:
        document = json.loads(
            (
                ROOT
                / "product/evidence/codex-reference-calibration-2026-08-14.json"
            ).read_text(encoding="utf-8")
        )
        cache_token = control._EVIDENCE_GIT_CACHE.set({})
        self.addCleanup(control._EVIDENCE_GIT_CACHE.reset, cache_token)
        validator = SUPPORTED_EVIDENCE_VALIDATORS[
            "codex-reference-calibration-o4"
        ][2]
        errors: list[str] = []
        self.assertTrue(validator(document, "O4", ROOT, errors), errors)

        mutations = {
            "missing human decision": lambda value: value["authority"].__setitem__(
                "decisionState", "pending"
            ),
            "different accepted receipt": lambda value: value["cohort"][
                "acceptedReceipts"
            ][0].__setitem__("sha256", "0" * 64),
            "normalized stopped receipt": lambda value: value["cohort"][
                "stoppedReceipt"
            ].__setitem__("state", "accepted"),
            "changed profile": lambda value: value["measures"][
                "scorecardAndProfileIdentity"
            ].__setitem__("profileSha256", "0" * 64),
            "lost strict advantage": lambda value: value["measures"][
                "userOrchestrationBurden"
            ].__setitem__("strictAdvantage", False),
            "changed external cohort": lambda value: value["measures"][
                "externalComparisonAndReuseDecision"
            ].__setitem__("externalSubstrateCohortCanonicalSha256", "0" * 64),
            "broadened claim": lambda value: value["claimLimits"].clear(),
        }
        for label, mutate_document in mutations.items():
            with self.subTest(label=label):
                candidate = deepcopy(document)
                mutate_document(candidate)
                candidate_errors: list[str] = []
                self.assertFalse(
                    validator(candidate, "O4", ROOT, candidate_errors)
                )
                self.assertTrue(candidate_errors)

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
            self.bind_fixture_registration(increment)
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
            self.bind_fixture_registration(increment)
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
                self.reset_acceptance_fixture()

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
                self.reset_acceptance_fixture()

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
                self.reset_acceptance_fixture()

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
                self.reset_acceptance_fixture()

if __name__ == "__main__":
    unittest.main()
