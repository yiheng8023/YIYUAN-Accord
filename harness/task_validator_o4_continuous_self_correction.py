"""Task-specific validator for the v1.2 O4 controlled correction suite.

This is deliberately not a generic receipt or carrier runtime.  It owns only
the six scenario classes named by the current O4 acceptance criterion.  Four
scenarios are replayed as real faults in disposable repository checkouts.  The
two carrier scenarios accept only a narrow, public-safe projection of ordered
Codex App Server and canonical repository observations.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable


INCREMENT_ID = "increment.v12-o4-continuous-self-correction"
VALIDATOR_KIND = "o4-continuous-self-correction-validator-v1"
VALIDATOR_LOCATOR = "harness/task_validator_o4_continuous_self_correction.py"
SUITE_IDENTITY = "o4-continuous-self-correction.controlled-v1"
CARRIER_GOAL_LOCATOR = (
    "product/evidence/o4-continuous-self-correction-artifacts/carrier-goal.txt"
)
CARRIER_GOAL_TEXT = (
    "Preserve the registered Agent Autonomy Harness v1.2 O4 carrier-control goal "
    "across native compaction and a full-history same-goal fork. Reconcile product "
    "authority and Git state at each checkpoint without asking the user to restate "
    "the goal or choose topology mechanics.\n"
)
CARRIER_GOAL_SHA256 = "b74f5f85352a1b1e7506d6cc496997fb084b823542fbe86034af13d36239490c"
CARRIER_GOAL_BINDING = {
    "locator": CARRIER_GOAL_LOCATOR,
    "sha256": CARRIER_GOAL_SHA256,
    "nativeStateSource": "codex-thread-goal-get-v0.147.0",
    "requiredStatus": "active",
}

CODEX_SOURCE_BINDING = {
    "repository": "https://github.com/openai/codex",
    "tag": "rust-v0.147.0",
    "tagObject": "3ed6f04f6bf8b7c46299d1cb1ff99c74ce21a51d",
    "peeledCommit": "be6e8eac029b183056b7e4402879f15d2c85f61b",
    "protocolPath": "codex-rs/protocol/src/protocol.rs",
    "appServerPath": "codex-rs/app-server/README.md",
    "forkProtocolPath": "codex-rs/app-server-protocol/src/protocol/v2/thread.rs",
}

EXPECTED_PRE_REGISTRATION_FIELDS = {
    "normativeProfileIdentity",
    "cohortProtocolIdentity",
    "profileSha256",
    "cohortProtocolSha256",
    "environmentAttributionBinding",
    "counterexampleIdentityAndSource",
    "startingAuthorityGoalAndCarrierState",
    "injectedOrObservedFailure",
    "expectedDetectionAndCorrection",
    "transitionAndCleanupBoundary",
    "scenarioValidator",
}

FIELD_CLAIMS_EXCLUDED = (
    "comparative-user-burden",
    "broad-real-world-effectiveness",
    "distinct-agent-equivalence",
    "uncontrolled-production-carrier-reliability",
)


@dataclass(frozen=True)
class FaultScenario:
    scenario_identity: str
    scenario_class: str
    mutation_identity: str
    expected_diagnostic: str


FAULT_SCENARIOS = (
    FaultScenario(
        "o4-continuous-self-correction.repeated-user-correction",
        "repeated-user-correction-detection",
        "duplicate-bound-correction-class",
        "increments repeat correctionClass",
    ),
    FaultScenario(
        "o4-continuous-self-correction.stale-conflicting-instruction",
        "stale-or-conflicting-instruction-rejection",
        "replace-current-program-purpose-with-stale-instruction",
        "program purpose is invalid",
    ),
    FaultScenario(
        "o4-continuous-self-correction.expected-observed-mismatch",
        "expected-versus-observed-effect-mismatch",
        "contradict-accepted-o1-observation-result",
        "O1 lifecycle suite evidence requires an observable twelve-slice replay",
    ),
    FaultScenario(
        "o4-continuous-self-correction.topology-residue-reconciliation",
        "code-topology-or-residue-reconciliation",
        "leave-task-owned-repository-residue",
        "repository cleanup residue remains: .tmp",
    ),
)

CARRIER_SCENARIO_IDENTITIES = (
    "o4-continuous-self-correction.native-compaction-recovery",
    "o4-continuous-self-correction.proactive-same-goal-transition",
)
SCENARIO_IDENTITIES = tuple(item.scenario_identity for item in FAULT_SCENARIOS) + (
    CARRIER_SCENARIO_IDENTITIES
)

COUNTEREXAMPLE_SOURCES = [
    {
        "scenarioIdentity": item.scenario_identity,
        "scenarioClass": item.scenario_class,
        "evidenceClass": "controlled-disposable-checkout-fault",
        "sourceBinding": "current-committed-authority-at-registration-source-revision",
    }
    for item in FAULT_SCENARIOS
] + [
    {
        "scenarioIdentity": CARRIER_SCENARIO_IDENTITIES[0],
        "scenarioClass": "native-compaction-recovery",
        "evidenceClass": "controlled-codex-app-server-host-event-projection",
        "sourceBinding": CODEX_SOURCE_BINDING,
    },
    {
        "scenarioIdentity": CARRIER_SCENARIO_IDENTITIES[1],
        "scenarioClass": "proactive-same-goal-conversation-transition",
        "evidenceClass": "controlled-codex-app-server-host-event-projection",
        "sourceBinding": CODEX_SOURCE_BINDING,
    },
]

FAILURE_BINDINGS = [
    {
        "scenarioIdentity": item.scenario_identity,
        "failure": item.mutation_identity,
        "expectedDiagnostic": item.expected_diagnostic,
    }
    for item in FAULT_SCENARIOS
] + [
    {
        "scenarioIdentity": CARRIER_SCENARIO_IDENTITIES[0],
        "failure": "native-context-compaction-without-post-compaction-reconciliation",
        "expectedDiagnostic": "missing-post-compaction-authority-or-head-verification",
    },
    {
        "scenarioIdentity": CARRIER_SCENARIO_IDENTITIES[1],
        "failure": "source-carrier-release-before-destination-authority-and-head-verification",
        "expectedDiagnostic": "source-release-precedes-verified-destination",
    },
]

CORRECTION_BINDINGS = [
    {
        "scenarioIdentity": item.scenario_identity,
        "detection": "canonical-verifier-rejects-before-further-material-effect",
        "correction": "restore-only-the-mutated-authority-or-residue-target",
        "reverification": "canonical-verifier-valid-after-minimum-correction",
    }
    for item in FAULT_SCENARIOS
] + [
    {
        "scenarioIdentity": CARRIER_SCENARIO_IDENTITIES[0],
        "detection": "codex-context-compaction-started-and-completed-events-observed",
        "correction": "resume-same-goal-from-committed-authority-without-user-reconstruction",
        "reverification": "canonical-authority-and-git-head-reconciled-after-compaction",
    },
    {
        "scenarioIdentity": CARRIER_SCENARIO_IDENTITIES[1],
        "detection": "reliable-risk-or-explicit-unknown-capacity-rule-observed",
        "correction": "codex-native-thread-fork-or-equivalent-same-goal-transition",
        "reverification": "destination-authority-and-git-head-verified-before-source-release",
    },
]

TRANSITION_AND_CLEANUP_BOUNDARY = {
    "sourceReleaseRule": "destination-authority-and-git-head-verified-before-source-release",
    "unknownCapacityRule": "transition-conservatively-at-the-preregistered-material-checkpoint-boundary",
    "userReconstructionEventsAllowed": 0,
    "userTopologyChoiceEventsAllowed": 0,
    "userTaskOwnedCleanupEventsAllowed": 0,
    "temporaryArtifactRule": "exact-task-created-resources-removed-before-scenario-close",
    "persistentRuntime": "none",
    "fieldClaimsExcluded": list(FIELD_CLAIMS_EXCLUDED),
}

PRIVATE_KEY_NAMES = {
    "threadid",
    "turnid",
    "sessionid",
    "messageid",
    "eventid",
    "path",
    "cwd",
    "locator",
    "prompt",
    "text",
    "transcript",
    "credential",
    "authorization",
    "auth",
}
PRIVATE_TEXT_PATTERNS = (
    re.compile(r"(?i)(?<![a-z0-9])[a-z]:[\\/]"),
    re.compile(r"(?i)(?:\\\\[^\\]+\\|/(?:users|home|private/var/folders|tmp)/)"),
    re.compile(r"(?i)codex://threads/"),
    re.compile(
        r"(?i)(?:thread|session|turn|message|event|msg)[_:-]"
        r"(?=[a-z0-9-]*\d)[a-z0-9-]{6,}"
    ),
    re.compile(r"(?i)(?:auth\.json|config\.toml|credentials?\.json|\.claude[/\\]settings\.json)"),
)

PUBLIC_EVENT_FIELDS = {
    "ordinal",
    "sourceClass",
    "eventClass",
    "carrierRole",
    "state",
}

COMPACTION_EVENT_SEQUENCE = (
    (
        "codex-app-server-response",
        "registered-source-goal-observed",
        "source",
        "active",
    ),
    (
        "codex-app-server-notification",
        "context-compaction-started",
        "source",
        "observed",
    ),
    (
        "codex-app-server-notification",
        "context-compaction-completed",
        "source",
        "observed",
    ),
    (
        "codex-app-server-response",
        "registered-source-goal-preserved-after-compaction",
        "source",
        "active",
    ),
    (
        "canonical-verifier-observation",
        "post-compaction-authority-verified",
        "source",
        "valid",
    ),
    (
        "git-observation",
        "post-compaction-head-reconciled",
        "source",
        "matching",
    ),
)

TRANSITION_EVENT_SEQUENCE = (
    (
        "carrier-fitness-observation",
        "capacity-risk-or-unknown-rule-triggered",
        "source",
        "transition-required",
    ),
    (
        "codex-app-server-response",
        "registered-source-goal-observed",
        "source",
        "active",
    ),
    (
        "codex-app-server-response",
        "same-goal-fork-request-accepted",
        "destination",
        "created",
    ),
    (
        "codex-app-server-notification",
        "destination-thread-started",
        "destination",
        "observed",
    ),
    (
        "codex-app-server-response",
        "registered-goal-preserved-in-destination",
        "destination",
        "active",
    ),
    (
        "canonical-verifier-observation",
        "destination-authority-verified",
        "destination",
        "valid",
    ),
    (
        "git-observation",
        "destination-head-reconciled",
        "destination",
        "matching",
    ),
    (
        "harness-source-release-preflight",
        "source-release-allowed",
        "source",
        "allowed",
    ),
    (
        "codex-app-server-response",
        "source-carrier-released",
        "source",
        "released",
    ),
)

FaultExecutor = Callable[[Path, str, FaultScenario], dict[str, Any]]

MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 10_000
MAX_CONTAINER_ITEMS = 256
MAX_STRING_CHARACTERS = 262_144


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _json_within_limits(value: Any) -> bool:
    nodes = 0
    seen_containers: set[int] = set()
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            return False
        if isinstance(current, str):
            if len(current) > MAX_STRING_CHARACTERS:
                return False
        elif isinstance(current, dict):
            identity = id(current)
            if identity in seen_containers or len(current) > MAX_CONTAINER_ITEMS:
                return False
            seen_containers.add(identity)
            for key, item in current.items():
                if not isinstance(key, str) or len(key) > MAX_STRING_CHARACTERS:
                    return False
                stack.append((item, depth + 1))
        elif isinstance(current, list):
            identity = id(current)
            if identity in seen_containers or len(current) > MAX_CONTAINER_ITEMS:
                return False
            seen_containers.add(identity)
            stack.extend((item, depth + 1) for item in current)
        elif current is not None and type(current) not in {bool, int, float}:
            return False
    return True


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    if len(raw) > 1_048_576:
        raise ValueError("JSON object exceeds byte limit")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=lambda _: (_ for _ in ()).throw(
            ValueError("non-finite JSON value")
        ),
    )
    if not isinstance(value, dict) or not _json_within_limits(value):
        raise ValueError("JSON value must be an object")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    return _strict_json_object(path.read_bytes())


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _contains_private_value(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.lower())
            if normalized in PRIVATE_KEY_NAMES:
                return True
            if _contains_private_value(item):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_private_value(item) for item in value)
    if isinstance(value, str):
        return any(pattern.search(value) is not None for pattern in PRIVATE_TEXT_PATTERNS)
    return False


def _run_verifier(checkout: Path) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-m", "harness", "verify", "--root", ".", "--json"],
        cwd=checkout,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
        env=environment,
    )
    if len(completed.stdout) > 1_048_576 or len(completed.stderr) > 1_048_576:
        raise RuntimeError("scenario verifier output limit exceeded")
    return _strict_json_object(completed.stdout)


def _apply_fault(checkout: Path, scenario: FaultScenario) -> tuple[Path, bytes | None]:
    program_path = checkout / "product" / "program.json"
    if scenario.mutation_identity == "duplicate-bound-correction-class":
        program = _read_json(program_path)
        active = next(
            item
            for item in program["increments"]
            if isinstance(item, dict) and item.get("state") == "active"
        )
        duplicate = deepcopy(active)
        duplicate["id"] = "increment.o4-controlled-duplicate-correction"
        duplicate["state"] = "stopped"
        duplicate["taskRegistration"] = None
        for index, work in enumerate(duplicate.get("workItems", []), start=1):
            work["id"] = f"work.o4-controlled-duplicate-correction-{index}"
            work["state"] = "stopped"
        original = program_path.read_bytes()
        program["increments"].append(duplicate)
        _write_json(program_path, program)
        return program_path, original
    if scenario.mutation_identity == "replace-current-program-purpose-with-stale-instruction":
        original = program_path.read_bytes()
        program = _read_json(program_path)
        program["purpose"] = "stale instruction overrides current bound product purpose"
        _write_json(program_path, program)
        return program_path, original
    if scenario.mutation_identity == "contradict-accepted-o1-observation-result":
        evidence_path = checkout / "product" / "evidence" / "o1-lifecycle-suite-accepted.json"
        original = evidence_path.read_bytes()
        evidence = _read_json(evidence_path)
        evidence["result"]["accepted"] = False
        _write_json(evidence_path, evidence)
        return evidence_path, original
    if scenario.mutation_identity == "leave-task-owned-repository-residue":
        residue = checkout / ".tmp"
        residue.mkdir()
        marker = residue / "o4-controlled-residue.marker"
        marker.write_text("bounded O4 residue fault\n", encoding="utf-8", newline="\n")
        return residue, None
    raise ValueError("unknown O4 fault mutation")


def _recover_fault(target: Path, original: bytes | None) -> None:
    if original is not None:
        target.write_bytes(original)
        return
    marker = target / "o4-controlled-residue.marker"
    marker.unlink()
    target.rmdir()


def execute_fault_scenario(
    root: Path,
    source_revision: str,
    scenario: FaultScenario,
) -> dict[str, Any]:
    """Exercise one exact fault, minimum recovery and re-verification."""

    temporary: tempfile.TemporaryDirectory[str] | None = None
    temporary_root: Path | None = None
    result: dict[str, Any] = {
        "baselineValid": False,
        "divergenceDetected": False,
        "expectedDiagnosticObserved": False,
        "recoveredValid": False,
        "recoveredHeadMatches": False,
        "probeCleanupVerified": False,
        "faultReportSha256": "",
        "recoveryReportSha256": "",
    }
    try:
        if re.fullmatch(r"[0-9a-f]{40}", source_revision) is None:
            raise ValueError("invalid source revision")
        temporary = tempfile.TemporaryDirectory(prefix="agent-autonomy-harness-o4-")
        temporary_root = Path(temporary.name)
        checkout = temporary_root / "checkout"
        git = shutil.which("git")
        if git is None:
            raise RuntimeError("git unavailable")
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
            }
        )
        subprocess.run(
            [
                git,
                "clone",
                "--quiet",
                "--no-hardlinks",
                "--no-checkout",
                "--",
                str(root.resolve(strict=True)),
                str(checkout),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            env=environment,
        )
        subprocess.run(
            [git, "-C", str(checkout), "checkout", "--quiet", "--detach", source_revision],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            env=environment,
        )
        baseline = _run_verifier(checkout)
        result["baselineValid"] = baseline.get("valid") is True
        if result["baselineValid"] is not True:
            raise RuntimeError("scenario baseline authority is invalid")

        target, original = _apply_fault(checkout, scenario)
        fault_report = _run_verifier(checkout)
        errors = fault_report.get("errors")
        result["divergenceDetected"] = fault_report.get("valid") is False
        result["expectedDiagnosticObserved"] = (
            isinstance(errors, list)
            and any(
                isinstance(item, str) and scenario.expected_diagnostic in item
                for item in errors
            )
        )
        result["faultReportSha256"] = _canonical_sha256(fault_report)

        _recover_fault(target, original)
        recovery_report = _run_verifier(checkout)
        result["recoveredValid"] = recovery_report.get("valid") is True
        result["recoveryReportSha256"] = _canonical_sha256(recovery_report)
        head = subprocess.run(
            [git, "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=environment,
        ).stdout.decode("ascii").strip()
        status = subprocess.run(
            [git, "-C", str(checkout), "status", "--porcelain=v1"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=environment,
        ).stdout
        result["recoveredHeadMatches"] = head == source_revision and status == b""
    except (
        json.JSONDecodeError,
        OSError,
        RuntimeError,
        StopIteration,
        subprocess.SubprocessError,
        UnicodeError,
        ValueError,
    ):
        pass
    finally:
        try:
            if temporary is not None:
                temporary.cleanup()
            result["probeCleanupVerified"] = (
                temporary_root is not None and not temporary_root.exists()
            )
        except OSError:
            result["probeCleanupVerified"] = False
    return result


def run_fault_suite(
    root: Path,
    source_revision: str,
    *,
    executor: FaultExecutor | None = None,
) -> dict[str, Any]:
    """Run the four repository counterexamples through one injectable seam."""

    selected = execute_fault_scenario if executor is None else executor
    records: list[dict[str, Any]] = []
    for scenario in FAULT_SCENARIOS:
        observed = selected(root, source_revision, scenario)
        records.append(
            {
                "scenarioIdentity": scenario.scenario_identity,
                "scenarioClass": scenario.scenario_class,
                "mutationIdentity": scenario.mutation_identity,
                "expectedDiagnostic": scenario.expected_diagnostic,
                "baselineValid": observed.get("baselineValid"),
                "divergenceDetected": observed.get("divergenceDetected"),
                "expectedDiagnosticObserved": observed.get("expectedDiagnosticObserved"),
                "recoveredValid": observed.get("recoveredValid"),
                "recoveredHeadMatches": observed.get("recoveredHeadMatches"),
                "probeCleanupVerified": observed.get("probeCleanupVerified"),
                "faultReportSha256": observed.get("faultReportSha256"),
                "recoveryReportSha256": observed.get("recoveryReportSha256"),
            }
        )
    required_true = (
        "baselineValid",
        "divergenceDetected",
        "expectedDiagnosticObserved",
        "recoveredValid",
        "recoveredHeadMatches",
        "probeCleanupVerified",
    )
    report_hashes_valid = all(
        isinstance(record.get(field), str)
        and re.fullmatch(r"[0-9a-f]{64}", record[field]) is not None
        for record in records
        for field in ("faultReportSha256", "recoveryReportSha256")
    )
    return {
        "schema": 1,
        "suiteIdentity": SUITE_IDENTITY,
        "sourceRevision": source_revision,
        "faultScenarioResults": records,
        "allFaultControlsObserved": len(records) == 4
        and all(record.get(field) is True for record in records for field in required_true)
        and report_hashes_valid,
        "cleanupVerified": all(
            record.get("probeCleanupVerified") is True for record in records
        ),
    }


def _app_server_record(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"source", "message"}:
        raise ValueError("raw App Server observation envelope is invalid")
    if value.get("source") != "codex-app-server-json-rpc-v0.147.0":
        raise ValueError("raw App Server source identity is invalid")
    message = value.get("message")
    if not isinstance(message, dict) or not _json_within_limits(message):
        raise ValueError("raw App Server message is invalid")
    try:
        raw = json.dumps(
            message,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (RecursionError, TypeError, ValueError) as exc:
        raise ValueError("raw App Server message is not finite JSON") from exc
    if len(raw) > 262_144:
        raise ValueError("raw App Server message exceeds byte limit")
    return message


def _request_observed(value: Any, *, method: str, carrier_id: str) -> int:
    message = _app_server_record(value)
    params = message.get("params")
    request_id = message.get("id")
    if (
        message.get("method") != method
        or type(request_id) is not int
        or request_id < 0
        or not isinstance(params, dict)
        or set(params) != {"threadId"}
        or params.get("threadId") != carrier_id
    ):
        raise ValueError("raw App Server request is invalid")
    return request_id


def _fork_request_observed(value: Any, *, carrier_id: str) -> int:
    message = _app_server_record(value)
    params = message.get("params")
    request_id = message.get("id")
    if (
        message.get("method") != "thread/fork"
        or type(request_id) is not int
        or request_id < 0
        or not isinstance(params, dict)
        or set(params) != {"threadId", "deferGoalContinuation"}
        or params.get("threadId") != carrier_id
        or params.get("deferGoalContinuation") is not True
    ):
        raise ValueError("raw full-history deferred-goal fork request is invalid")
    return request_id


def _empty_response_observed(value: Any, *, request_id: int) -> None:
    message = _app_server_record(value)
    if (
        set(message) != {"id", "result"}
        or message.get("id") != request_id
        or message.get("result") != {}
    ):
        raise ValueError("raw App Server response is invalid")


def _goal_response_observed(
    value: Any,
    *,
    request_id: int,
    carrier_id: str,
) -> tuple[str, str, None]:
    message = _app_server_record(value)
    result = message.get("result")
    goal = result.get("goal") if isinstance(result, dict) else None
    if (
        set(message) != {"id", "result"}
        or message.get("id") != request_id
        or not isinstance(result, dict)
        or set(result) != {"goal"}
        or not isinstance(goal, dict)
        or set(goal)
        != {
            "threadId",
            "objective",
            "status",
            "tokenBudget",
            "tokensUsed",
            "timeUsedSeconds",
            "createdAt",
            "updatedAt",
        }
        or goal.get("threadId") != carrier_id
        or goal.get("objective") != CARRIER_GOAL_TEXT
        or goal.get("status") != CARRIER_GOAL_BINDING["requiredStatus"]
        or goal.get("tokenBudget") is not None
        or type(goal.get("tokensUsed")) is not int
        or goal["tokensUsed"] < 0
        or type(goal.get("timeUsedSeconds")) is not int
        or goal["timeUsedSeconds"] < 0
        or type(goal.get("createdAt")) is not int
        or goal["createdAt"] <= 0
        or type(goal.get("updatedAt")) is not int
        or goal["updatedAt"] < goal["createdAt"]
    ):
        raise ValueError("raw App Server goal response is not the registered active goal")
    return goal["objective"], goal["status"], goal["tokenBudget"]


def _app_item_observed(
    value: Any,
    *,
    method: str,
    carrier_id: str,
) -> tuple[str, str]:
    message = _app_server_record(value)
    params = message.get("params")
    item = params.get("item") if isinstance(params, dict) else None
    turn_id = params.get("turnId") if isinstance(params, dict) else None
    if (
        message.get("method") != method
        or not isinstance(params, dict)
        or params.get("threadId") != carrier_id
        or not isinstance(item, dict)
        or item.get("type") != "contextCompaction"
        or not isinstance(turn_id, str)
        or not turn_id
        or not isinstance(item.get("id"), str)
        or not item["id"]
    ):
        raise ValueError("raw compaction event is invalid")
    return turn_id, item["id"]


def _fork_response_observed(
    value: Any,
    *,
    request_id: int,
    source_carrier_id: str,
    destination_carrier_id: str,
) -> None:
    message = _app_server_record(value)
    result = message.get("result")
    thread = result.get("thread") if isinstance(result, dict) else None
    if (
        message.get("id") != request_id
        or "error" in message
        or not isinstance(thread, dict)
        or thread.get("id") != destination_carrier_id
        or thread.get("forkedFromId") != source_carrier_id
    ):
        raise ValueError("raw fork response is not bound to the source carrier")


def _destination_started_observed(
    value: Any,
    *,
    source_carrier_id: str,
    destination_carrier_id: str,
) -> None:
    message = _app_server_record(value)
    params = message.get("params")
    thread = params.get("thread") if isinstance(params, dict) else None
    if (
        message.get("method") != "thread/started"
        or not isinstance(thread, dict)
        or thread.get("id") != destination_carrier_id
        or thread.get("forkedFromId") != source_carrier_id
    ):
        raise ValueError("raw destination start is not bound to the source carrier")


def _canonical_verifier_observed(value: Any, *, carrier_id: str) -> None:
    if not isinstance(value, dict) or set(value) != {
        "source",
        "carrierId",
        "report",
    }:
        raise ValueError("raw canonical verifier observation envelope is invalid")
    report = value.get("report")
    states = report.get("criterionStates") if isinstance(report, dict) else None
    if (
        value.get("source") != "python--B--m-harness-verify-json"
        or value.get("carrierId") != carrier_id
        or not isinstance(report, dict)
        or report.get("valid") is not True
        or report.get("programStatus") != "active"
        or report.get("completionState") != "in-progress"
        or report.get("activeIncrement") != INCREMENT_ID
        or report.get("errors") != []
        or not isinstance(states, dict)
        or any(states.get(item) is not True for item in ("G1", "G2", "G3", "G4"))
        or states.get("O4") is not False
    ):
        raise ValueError("raw canonical verifier observation is invalid")


def _git_observed(value: Any, *, carrier_id: str, expected_head: str) -> None:
    if not isinstance(value, dict) or set(value) != {
        "source",
        "carrierId",
        "head",
        "expectedHead",
        "statusPorcelainV1",
    }:
        raise ValueError("raw Git observation envelope is invalid")
    if (
        value.get("source") != "git-rev-parse-and-status-v1"
        or value.get("carrierId") != carrier_id
        or value.get("head") != expected_head
        or value.get("expectedHead") != expected_head
        or value.get("statusPorcelainV1") != ""
        or re.fullmatch(r"[0-9a-f]{40}", expected_head) is None
    ):
        raise ValueError("raw Git observation does not match the registered head")


def _carrier_fitness_observed(value: Any, *, source_carrier_id: str) -> None:
    if not isinstance(value, dict) or set(value) != {
        "source",
        "carrierId",
        "remainingCapacityState",
        "ruleIdentity",
        "materialCheckpointCount",
        "transitionTriggered",
    }:
        raise ValueError("raw carrier-fitness observation envelope is invalid")
    count = value.get("materialCheckpointCount")
    if (
        value.get("source") != "task-bound-carrier-fitness-observer-v1"
        or value.get("carrierId") != source_carrier_id
        or value.get("remainingCapacityState") not in {"reliable-risk", "unknown"}
        or value.get("ruleIdentity")
        != TRANSITION_AND_CLEANUP_BOUNDARY["unknownCapacityRule"]
        or type(count) is not int
        or count < 0
        or value.get("transitionTriggered") is not True
    ):
        raise ValueError("raw carrier-fitness observation did not trigger the bound rule")


def _source_release_preflight_observed(value: Any, *, source_carrier_id: str) -> None:
    if not isinstance(value, dict) or set(value) != {
        "source",
        "carrierId",
        "report",
    }:
        raise ValueError("raw source-release preflight envelope is invalid")
    report = value.get("report")
    if (
        value.get("source") != "harness-source-carrier-release-preflight-v1"
        or value.get("carrierId") != source_carrier_id
        or not isinstance(report, dict)
        or report.get("allowed") is not True
        or report.get("state") != "release-eligible"
    ):
        raise ValueError("raw source-release preflight is not release eligible")


def _source_archived_observed(value: Any, *, source_carrier_id: str) -> None:
    message = _app_server_record(value)
    params = message.get("params")
    if (
        message.get("method") != "thread/archived"
        or not isinstance(params, dict)
        or params.get("threadId") != source_carrier_id
    ):
        raise ValueError("raw source carrier archive notification is invalid")


def project_raw_carrier_observations(
    scenario_identity: str,
    raw_observations: list[dict[str, Any]],
    *,
    source_carrier_id: str,
    expected_head: str,
    destination_carrier_id: str | None = None,
) -> dict[str, Any]:
    """Derive the public sequence from raw host and repository observations.

    Private carrier and item identifiers are used only for in-memory relation
    checks.  They are never copied into the returned projection.
    """

    if not isinstance(source_carrier_id, str) or not source_carrier_id:
        raise ValueError("source carrier identity is invalid")
    if scenario_identity == CARRIER_SCENARIO_IDENTITIES[0]:
        if destination_carrier_id is not None or len(raw_observations) != 10:
            raise ValueError("raw compaction observation count is invalid")
        goal_request_id = _request_observed(
            raw_observations[0],
            method="thread/goal/get",
            carrier_id=source_carrier_id,
        )
        before_goal = _goal_response_observed(
            raw_observations[1],
            request_id=goal_request_id,
            carrier_id=source_carrier_id,
        )
        request_id = _request_observed(
            raw_observations[2],
            method="thread/compact/start",
            carrier_id=source_carrier_id,
        )
        _empty_response_observed(raw_observations[3], request_id=request_id)
        started = _app_item_observed(
            raw_observations[4],
            method="item/started",
            carrier_id=source_carrier_id,
        )
        completed = _app_item_observed(
            raw_observations[5],
            method="item/completed",
            carrier_id=source_carrier_id,
        )
        if completed != started:
            raise ValueError("raw compaction lifecycle identities do not match")
        post_goal_request_id = _request_observed(
            raw_observations[6],
            method="thread/goal/get",
            carrier_id=source_carrier_id,
        )
        after_goal = _goal_response_observed(
            raw_observations[7],
            request_id=post_goal_request_id,
            carrier_id=source_carrier_id,
        )
        if after_goal != before_goal:
            raise ValueError("registered goal changed across native compaction")
        _canonical_verifier_observed(
            raw_observations[8], carrier_id=source_carrier_id
        )
        _git_observed(
            raw_observations[9],
            carrier_id=source_carrier_id,
            expected_head=expected_head,
        )
        normalized = [
            {
                "ordinal": ordinal,
                "sourceClass": source_class,
                "eventClass": event_class,
                "carrierRole": carrier_role,
                "state": state,
            }
            for ordinal, (source_class, event_class, carrier_role, state) in enumerate(
                COMPACTION_EVENT_SEQUENCE
            )
        ]
    elif scenario_identity == CARRIER_SCENARIO_IDENTITIES[1]:
        if (
            not isinstance(destination_carrier_id, str)
            or not destination_carrier_id
            or destination_carrier_id == source_carrier_id
            or len(raw_observations) != 14
        ):
            raise ValueError("raw transition carrier identities or count are invalid")
        _carrier_fitness_observed(
            raw_observations[0], source_carrier_id=source_carrier_id
        )
        source_goal_request_id = _request_observed(
            raw_observations[1],
            method="thread/goal/get",
            carrier_id=source_carrier_id,
        )
        source_goal = _goal_response_observed(
            raw_observations[2],
            request_id=source_goal_request_id,
            carrier_id=source_carrier_id,
        )
        fork_request_id = _fork_request_observed(
            raw_observations[3], carrier_id=source_carrier_id
        )
        _fork_response_observed(
            raw_observations[4],
            request_id=fork_request_id,
            source_carrier_id=source_carrier_id,
            destination_carrier_id=destination_carrier_id,
        )
        _destination_started_observed(
            raw_observations[5],
            source_carrier_id=source_carrier_id,
            destination_carrier_id=destination_carrier_id,
        )
        destination_goal_request_id = _request_observed(
            raw_observations[6],
            method="thread/goal/get",
            carrier_id=destination_carrier_id,
        )
        destination_goal = _goal_response_observed(
            raw_observations[7],
            request_id=destination_goal_request_id,
            carrier_id=destination_carrier_id,
        )
        if destination_goal != source_goal:
            raise ValueError("registered goal did not survive the full-history fork")
        _canonical_verifier_observed(
            raw_observations[8], carrier_id=destination_carrier_id
        )
        _git_observed(
            raw_observations[9],
            carrier_id=destination_carrier_id,
            expected_head=expected_head,
        )
        _source_release_preflight_observed(
            raw_observations[10], source_carrier_id=source_carrier_id
        )
        archive_request_id = _request_observed(
            raw_observations[11],
            method="thread/archive",
            carrier_id=source_carrier_id,
        )
        _empty_response_observed(raw_observations[12], request_id=archive_request_id)
        _source_archived_observed(
            raw_observations[13], source_carrier_id=source_carrier_id
        )
        normalized = [
            {
                "ordinal": ordinal,
                "sourceClass": source_class,
                "eventClass": event_class,
                "carrierRole": carrier_role,
                "state": state,
            }
            for ordinal, (source_class, event_class, carrier_role, state) in enumerate(
                TRANSITION_EVENT_SEQUENCE
            )
        ]
    else:
        raise ValueError("unsupported O4 raw carrier scenario")
    projection = project_carrier_events(scenario_identity, normalized)
    if _contains_private_value(projection):
        raise ValueError("raw carrier projection retained private material")
    return projection


def project_carrier_events(
    scenario_identity: str,
    source_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project one exact carrier sequence without retaining private identifiers."""

    if scenario_identity == CARRIER_SCENARIO_IDENTITIES[0]:
        expected = COMPACTION_EVENT_SEQUENCE
    elif scenario_identity == CARRIER_SCENARIO_IDENTITIES[1]:
        expected = TRANSITION_EVENT_SEQUENCE
    else:
        raise ValueError("unsupported O4 carrier scenario")
    if len(source_events) != len(expected):
        raise ValueError("carrier source event count is invalid")
    if _contains_private_value(source_events):
        raise ValueError("carrier source events contain private material")
    projected: list[dict[str, Any]] = []
    for ordinal, (record, expected_values) in enumerate(
        zip(source_events, expected, strict=True)
    ):
        if not isinstance(record, dict) or set(record) != PUBLIC_EVENT_FIELDS:
            raise ValueError("carrier source event shape is invalid")
        actual = (
            record.get("sourceClass"),
            record.get("eventClass"),
            record.get("carrierRole"),
            record.get("state"),
        )
        if type(record.get("ordinal")) is not int or record["ordinal"] != ordinal:
            raise ValueError("carrier source event ordinal is invalid")
        if actual != expected_values:
            raise ValueError("carrier source event chronology is invalid")
        projected.append(dict(record))
    return {
        "schema": 1,
        "scenarioIdentity": scenario_identity,
        "sourceFormat": "public-safe-codex-app-server-goal-observation-v2",
        "codexSourceBinding": CODEX_SOURCE_BINDING,
        "controlledGoalSha256": CARRIER_GOAL_SHA256,
        "eventSequence": projected,
        "eventShapeSha256": _canonical_sha256(projected),
        "retainedPrivateFieldCount": 0,
        "userReconstructionEventCount": 0,
        "userTopologyChoiceEventCount": 0,
        "userCleanupEventCount": 0,
    }


def _carrier_projection_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "scenarioIdentity",
        "sourceFormat",
        "codexSourceBinding",
        "controlledGoalSha256",
        "eventSequence",
        "eventShapeSha256",
        "retainedPrivateFieldCount",
        "userReconstructionEventCount",
        "userTopologyChoiceEventCount",
        "userCleanupEventCount",
    }:
        return False
    try:
        replay = project_carrier_events(
            value["scenarioIdentity"],
            value["eventSequence"],
        )
    except (KeyError, TypeError, ValueError):
        return False
    return value == replay and not _contains_private_value(value)


def _starting_state_valid(value: Any, source_revision: Any) -> bool:
    return value == {
        "sourceRevision": source_revision,
        "authorityPaths": [
            "product/constitution.json",
            "product/program.json",
            "product/acceptance.json",
        ],
        "goalBoundary": "registered-o4-controlled-carrier-goal-under-current-v1.2-acceptance",
        "controlledGoalArtifact": CARRIER_GOAL_BINDING,
        "carrierState": {
            "repository": "single-main-checkout-clean-at-scenario-start",
            "conversation": "native-active-goal-observed-before-and-after-each-controlled-carrier-event",
            "capacitySignal": "reliable-risk-or-explicit-unknown-rule-only",
        },
    }


def _goal_artifact_committed(root: Path, source_revision: Any) -> bool:
    if (
        not isinstance(source_revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", source_revision) is None
    ):
        return False
    expected = CARRIER_GOAL_TEXT.encode("utf-8")
    if hashlib.sha256(expected).hexdigest() != CARRIER_GOAL_SHA256:
        return False
    try:
        resolved_root = root.resolve(strict=True)
        lexical_candidate = resolved_root / CARRIER_GOAL_LOCATOR
        if lexical_candidate.is_symlink():
            return False
        candidate = lexical_candidate.resolve(strict=True)
        if (
            not candidate.is_relative_to(resolved_root)
            or not candidate.is_file()
            or candidate.read_bytes() != expected
        ):
            return False
        git = shutil.which("git")
        if git is None:
            return False
        common = {
            "cwd": resolved_root,
            "check": False,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "timeout": 30,
            "env": {
                **os.environ,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
            },
        }
        tree = subprocess.run(
            [git, "ls-tree", source_revision, "--", CARRIER_GOAL_LOCATOR],
            **common,
        )
        size = subprocess.run(
            [git, "cat-file", "-s", f"{source_revision}:{CARRIER_GOAL_LOCATOR}"],
            **common,
        )
        if (
            tree.returncode != 0
            or size.returncode != 0
            or len(tree.stdout) > 1_024
            or len(tree.stderr) > 16_384
            or len(size.stdout) > 64
            or len(size.stderr) > 16_384
            or re.fullmatch(
                rb"100644 blob [0-9a-f]{40,64}\t"
                + re.escape(CARRIER_GOAL_LOCATOR.encode("ascii"))
                + rb"\r?\n",
                tree.stdout,
            )
            is None
            or size.stdout.strip() != str(len(expected)).encode("ascii")
        ):
            return False
        completed = subprocess.run(
            [git, "cat-file", "blob", f"{source_revision}:{CARRIER_GOAL_LOCATOR}"],
            cwd=resolved_root,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env={
                **os.environ,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return (
        completed.returncode == 0
        and len(completed.stdout) == len(expected)
        and len(completed.stderr) <= 16_384
        and completed.stdout == expected
    )


def _scenario_validator_binding_valid(value: Any) -> bool:
    return value == {
        "suiteIdentity": SUITE_IDENTITY,
        "scenarioIdentities": list(SCENARIO_IDENTITIES),
        "validatorIdentity": VALIDATOR_KIND,
        "validatorLocator": VALIDATOR_LOCATOR,
        "hostProjectionBuilder": (
            f"{VALIDATOR_LOCATOR}:project_raw_carrier_observations"
        ),
        "codexSourceBinding": CODEX_SOURCE_BINDING,
        "controlledGoalArtifact": CARRIER_GOAL_BINDING,
        "receiptOnlyAccepted": False,
    }


def validate_registration(
    registration: dict[str, Any],
    increment: dict[str, Any],
    mapped_outcomes: tuple[str, ...],
    root: Path,
    errors: list[str],
) -> bool:
    """Validate the exact O4 suite before any controlled measurement."""

    before = len(errors)
    values = registration.get("preRegistrationValues")
    registration_binding = increment.get("taskRegistration")
    source_revision = (
        registration_binding.get("sourceRevision")
        if isinstance(registration_binding, dict)
        else None
    )
    if (
        increment.get("id") != INCREMENT_ID
        or registration.get("incrementId") != INCREMENT_ID
        or mapped_outcomes != ("O4",)
        or registration.get("criterionIds") != ["O4"]
        or not isinstance(values, dict)
        or set(values) != EXPECTED_PRE_REGISTRATION_FIELDS
    ):
        _error(errors, "O4 correction suite registration identity is invalid")
        return False
    if values.get("counterexampleIdentityAndSource") != COUNTEREXAMPLE_SOURCES:
        _error(errors, "O4 correction suite must bind all six counterexample sources exactly once")
    if not _goal_artifact_committed(root, source_revision):
        _error(errors, "O4 controlled carrier goal artifact is not committed exactly")
    if not _starting_state_valid(
        values.get("startingAuthorityGoalAndCarrierState"), source_revision
    ):
        _error(errors, "O4 correction suite starting authority and carrier state are invalid")
    if values.get("injectedOrObservedFailure") != FAILURE_BINDINGS:
        _error(errors, "O4 correction suite failure bindings are invalid")
    if values.get("expectedDetectionAndCorrection") != CORRECTION_BINDINGS:
        _error(errors, "O4 correction suite detection and correction bindings are invalid")
    if values.get("transitionAndCleanupBoundary") != TRANSITION_AND_CLEANUP_BOUNDARY:
        _error(errors, "O4 correction suite transition and cleanup boundary is invalid")
    if not _scenario_validator_binding_valid(values.get("scenarioValidator")):
        _error(errors, "O4 correction suite validator and projection binding is invalid")
    validator = registration.get("preMeasurementValidator")
    if not isinstance(validator, dict) or (
        validator.get("kind") != VALIDATOR_KIND
        or validator.get("version") != 1
        or validator.get("locator") != VALIDATOR_LOCATOR
    ):
        _error(errors, "O4 correction suite pre-measurement validator binding is invalid")
    return len(errors) == before


def _observation_valid(
    root: Path,
    observation: dict[str, Any],
    source_revision: str,
) -> bool:
    if set(observation) != {
        "schema",
        "suiteIdentity",
        "sourceRevision",
        "faultSuite",
        "carrierProjections",
        "claimCeiling",
        "cleanupVerified",
    }:
        return False
    projections = observation.get("carrierProjections")
    if (
        observation.get("schema") != 1
        or observation.get("suiteIdentity") != SUITE_IDENTITY
        or observation.get("sourceRevision") != source_revision
        or not isinstance(projections, list)
        or len(projections) != 2
        or [item.get("scenarioIdentity") for item in projections if isinstance(item, dict)]
        != list(CARRIER_SCENARIO_IDENTITIES)
        or not all(_carrier_projection_valid(item) for item in projections)
        or observation.get("claimCeiling")
        != "bounded-v1.2-controlled-self-correction-and-carrier-evidence-only"
        or observation.get("cleanupVerified") is not True
    ):
        return False
    replay = run_fault_suite(root, source_revision)
    return (
        observation.get("faultSuite") == replay
        and replay.get("allFaultControlsObserved") is True
        and replay.get("cleanupVerified") is True
    )


def validate_evidence(
    document: dict[str, Any],
    criterion_id: str,
    root: Path,
    errors: list[str],
) -> bool:
    """Replay four faults and validate two ordered public-safe host projections."""

    before = len(errors)
    source = document.get("source")
    result = document.get("result")
    if (
        criterion_id != "O4"
        or document.get("criterionIds") != ["O4"]
        or document.get("incrementId") != INCREMENT_ID
        or not isinstance(source, dict)
        or source.get("kind") != "controlled-o4-self-correction-suite-observation"
        or source.get("locator")
        != "product/evidence/o4-continuous-self-correction-observation.json"
        or not isinstance(source.get("identity"), str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", source["identity"]) is None
        or not isinstance(result, dict)
        or set(result)
        != {
            "accepted",
            "suiteIdentity",
            "sourceRevision",
            "observationSha256",
            "independentReplayVerified",
            "destinationBeforeSourceReleaseVerified",
            "cleanupVerified",
            "claimCeiling",
        }
        or result.get("accepted") is not True
        or result.get("suiteIdentity") != SUITE_IDENTITY
        or not isinstance(result.get("sourceRevision"), str)
        or re.fullmatch(r"[0-9a-f]{40}", result["sourceRevision"]) is None
        or not isinstance(result.get("observationSha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", result["observationSha256"]) is None
        or source.get("identity") != "sha256:" + result.get("observationSha256", "")
        or result.get("independentReplayVerified") is not True
        or result.get("destinationBeforeSourceReleaseVerified") is not True
        or result.get("cleanupVerified") is not True
        or result.get("claimCeiling")
        != "bounded-v1.2-controlled-self-correction-and-carrier-evidence-only"
    ):
        _error(errors, "O4 evidence requires replayed fault behavior and ordered host events")
        return False
    try:
        observation_path = (
            root / "product" / "evidence" / "o4-continuous-self-correction-observation.json"
        )
        raw = observation_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != result["observationSha256"]:
            raise ValueError("O4 observation digest mismatch")
        observation = _strict_json_object(raw)
        if not _observation_valid(root, observation, result["sourceRevision"]):
            raise ValueError("O4 observation replay failed")
    except (
        json.JSONDecodeError,
        OSError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        _error(errors, "O4 correction suite evidence replay failed closed")
    return len(errors) == before


__all__ = [
    "CARRIER_SCENARIO_IDENTITIES",
    "CODEX_SOURCE_BINDING",
    "FAULT_SCENARIOS",
    "INCREMENT_ID",
    "SCENARIO_IDENTITIES",
    "SUITE_IDENTITY",
    "VALIDATOR_KIND",
    "VALIDATOR_LOCATOR",
    "project_carrier_events",
    "project_raw_carrier_observations",
    "run_fault_suite",
    "validate_evidence",
    "validate_registration",
]
