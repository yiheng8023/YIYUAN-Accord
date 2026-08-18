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
    re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\[^\\]+\\|/(?:users|home|private/var/folders|tmp)/)"),
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
    if not isinstance(value, dict):
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
        "sourceFormat": "public-safe-codex-app-server-observation-v1",
        "codexSourceBinding": CODEX_SOURCE_BINDING,
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
        "goalBoundary": "current-v1.2-completion-expression-under-named-human-authority",
        "carrierState": {
            "repository": "single-main-checkout-clean-at-scenario-start",
            "conversation": "same-goal-current-carrier-before-controlled-event",
            "capacitySignal": "reliable-risk-or-explicit-unknown-rule-only",
        },
    }


def _scenario_validator_binding_valid(value: Any) -> bool:
    return value == {
        "suiteIdentity": SUITE_IDENTITY,
        "scenarioIdentities": list(SCENARIO_IDENTITIES),
        "validatorIdentity": VALIDATOR_KIND,
        "validatorLocator": VALIDATOR_LOCATOR,
        "hostProjectionBuilder": f"{VALIDATOR_LOCATOR}:project_carrier_events",
        "codexSourceBinding": CODEX_SOURCE_BINDING,
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

    del root
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
    "run_fault_suite",
    "validate_evidence",
    "validate_registration",
]
