"""Task-specific validator for the registered v1.2 O1 lifecycle suite.

This module is not a reusable evidence framework.  It owns only the fixed
``increment.v12-o1-lifecycle-suite`` registration and its later evidence.
The product verifier supplies the code-owned registration and evidence seams.
"""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
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


INCREMENT_ID = "increment.v12-o1-lifecycle-suite"
VALIDATOR_KIND = "o1-lifecycle-suite-validator-v1"
VALIDATOR_LOCATOR = "harness/task_validator_o1_lifecycle_suite.py"
SUITE_IDENTITY = "o1-lifecycle-coverage.controlled-v1"
SOURCE_REVISION = "e060a08f05361cb4cc9a67be050236cdbbde1de5"
SOURCE_PATH = "common/human-ai-collaboration-shortfalls"
SOURCE_MANIFEST_BLOB = "5b2bb49446c43b5d41bdd14fa6a844abefb7c1cc"
SOURCE_SLICES = tuple(f"SG-{index:02d}" for index in range(1, 13))
EXPECTED_PRE_REGISTRATION_FIELDS = {
    "normativeProfileIdentity",
    "cohortProtocolIdentity",
    "profileSha256",
    "cohortProtocolSha256",
    "environmentAttributionBinding",
    "sourceCustodyRevisionAndPath",
    "sourceSliceIdentity",
    "lifecyclePhaseApplicabilityAndOwner",
    "nativeOfficialExternalDomainOrResidualRoute",
    "claimedControlEffects",
    "controlledScenarioOrCodeValidator",
    "claimLimitAndLifecycle",
}
FIELD_CLAIM_EXCLUSIONS = (
    "comparative-user-burden",
    "broad-real-world-effectiveness",
    "distinct-agent-equivalence",
)


@dataclass(frozen=True)
class Scenario:
    source_slice_identity: str
    scenario_identity: str
    mutation_identity: str
    expected_diagnostic: str
    effect_classes: tuple[str, ...]


SCENARIOS = (
    Scenario(
        "SG-01",
        "o1-lifecycle-coverage.sg-01",
        "replace-bound-program-purpose",
        "program purpose is invalid",
        ("detection", "stop"),
    ),
    Scenario(
        "SG-02",
        "o1-lifecycle-coverage.sg-02",
        "detach-active-increment-identity",
        "activeIncrementId must identify the active increment",
        ("detection", "stop"),
    ),
    Scenario(
        "SG-03",
        "o1-lifecycle-coverage.sg-03",
        "expand-success-definition-beyond-bound-authority",
        "constitution successDefinition is invalid",
        ("detection", "claim-limitation"),
    ),
    Scenario(
        "SG-04",
        "o1-lifecycle-coverage.sg-04",
        "replace-adaptive-route-with-fixed-router",
        "program progressionPolicy is invalid",
        ("detection", "stop", "claim-limitation"),
    ),
    Scenario(
        "SG-05",
        "o1-lifecycle-coverage.sg-05",
        "assign-human-only-operation-to-agent-work",
        "contains an unknown operation",
        ("prevention", "detection", "stop"),
    ),
    Scenario(
        "SG-06",
        "o1-lifecycle-coverage.sg-06",
        "promote-outcome-with-missing-evidence",
        "missing evidence product/evidence/o1-lifecycle-suite-unbound.json",
        ("detection", "stop", "claim-limitation"),
    ),
    Scenario(
        "SG-07",
        "o1-lifecycle-coverage.sg-07",
        "declare-completion-with-active-work",
        "completed program must have no active increment",
        ("detection", "stop"),
    ),
    Scenario(
        "SG-08",
        "o1-lifecycle-coverage.sg-08",
        "remove-accountable-human-acceptance",
        "program userOwns omits a mandatory human authority",
        ("prevention", "detection", "stop"),
    ),
    Scenario(
        "SG-09",
        "o1-lifecycle-coverage.sg-09",
        "drift-environment-attribution-contract",
        "acceptance environmentAttribution is invalid",
        ("detection", "stop", "claim-limitation"),
    ),
    Scenario(
        "SG-10",
        "o1-lifecycle-coverage.sg-10",
        "repeat-correction-class",
        "increments repeat correctionClass",
        ("detection", "stop"),
    ),
    Scenario(
        "SG-11",
        "o1-lifecycle-coverage.sg-11",
        "leave-task-owned-temporary-residue",
        "repository cleanup residue remains: .tmp",
        ("detection", "recovery", "stop"),
    ),
    Scenario(
        "SG-12",
        "o1-lifecycle-coverage.sg-12",
        "expand-outcome-neutral-process-budget",
        "outcome-neutral work budget must be zero or one",
        ("detection", "stop", "claim-limitation"),
    ),
)

LIFECYCLE_PHASE_BY_SLICE = {
    "SG-01": "intake-and-goal-context-binding",
    "SG-02": "transition-continuity-and-handoff",
    "SG-03": "premise-risk-and-domain-escalation",
    "SG-04": "capability-route-selection-and-retirement",
    "SG-05": "authority-reversibility-and-revocation",
    "SG-06": "evidence-provenance-and-claim-scope",
    "SG-07": "closure-readiness-and-release-transition",
    "SG-08": "human-review-veto-and-accountability",
    "SG-09": "environment-portability-and-evaluation",
    "SG-10": "feedback-correction-and-retirement",
    "SG-11": "governance-privacy-and-projection",
    "SG-12": "proportionality-control-cost-and-subtraction",
}
ROUTE_CLASS_BY_SLICE = {
    "SG-01": "native",
    "SG-02": "residual-harness",
    "SG-03": "accountable-domain",
    "SG-04": "native",
    "SG-05": "native",
    "SG-06": "residual-harness",
    "SG-07": "residual-harness",
    "SG-08": "accountable-domain",
    "SG-09": "residual-harness",
    "SG-10": "residual-harness",
    "SG-11": "residual-harness",
    "SG-12": "native",
}
CLAIM_LIFECYCLE = {
    "evidenceClass": "controlled-fault-injection",
    "claimCeiling": (
        "bounded-v1.2-control-detection-stop-recovery-and-claim-limitation-only"
    ),
    "fieldClaimsExcluded": list(FIELD_CLAIM_EXCLUSIONS),
    "retirementRule": "shrink-or-retire-when-sufficient-native-control-is-observed",
}

ScenarioExecutor = Callable[[Path, str, Scenario], dict[str, Any]]


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


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("scenario authority must be a JSON object")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _apply_fault(checkout: Path, scenario: Scenario) -> None:
    program_path = checkout / "product" / "program.json"
    acceptance_path = checkout / "product" / "acceptance.json"
    constitution_path = checkout / "product" / "constitution.json"
    mutation = scenario.mutation_identity
    if mutation == "replace-bound-program-purpose":
        program = _read_json(program_path)
        program["purpose"] = "unbound replacement purpose"
        _write_json(program_path, program)
    elif mutation == "detach-active-increment-identity":
        program = _read_json(program_path)
        program["activeIncrementId"] = "increment.unbound"
        _write_json(program_path, program)
    elif mutation == "expand-success-definition-beyond-bound-authority":
        constitution = _read_json(constitution_path)
        constitution["successDefinition"] = "universal autonomous success"
        _write_json(constitution_path, constitution)
    elif mutation == "replace-adaptive-route-with-fixed-router":
        program = _read_json(program_path)
        program["progressionPolicy"]["taskTimeAdaptationDisposition"] = (
            "always-route-every-task-through-one-fixed-model"
        )
        _write_json(program_path, program)
    elif mutation == "assign-human-only-operation-to-agent-work":
        program = _read_json(program_path)
        work = program["increments"][0]["workItems"][0]
        work["operationIds"].append("release-authorization")
        _write_json(program_path, program)
    elif mutation == "promote-outcome-with-missing-evidence":
        acceptance = _read_json(acceptance_path)
        criterion = next(item for item in acceptance["criteria"] if item["id"] == "O1")
        criterion["assessment"] = "verified"
        criterion["evidence"] = [
            "product/evidence/o1-lifecycle-suite-unbound.json"
        ]
        _write_json(acceptance_path, acceptance)
    elif mutation == "declare-completion-with-active-work":
        program = _read_json(program_path)
        program["status"] = "completed"
        _write_json(program_path, program)
    elif mutation == "remove-accountable-human-acceptance":
        program = _read_json(program_path)
        program["authorityBoundary"]["userOwns"].remove(
            "accountable-outcome-acceptance"
        )
        _write_json(program_path, program)
    elif mutation == "drift-environment-attribution-contract":
        acceptance = _read_json(acceptance_path)
        acceptance["environmentAttribution"]["scope"] = "unbound environment scope"
        _write_json(acceptance_path, acceptance)
    elif mutation == "repeat-correction-class":
        program = _read_json(program_path)
        duplicate = deepcopy(program["increments"][0])
        duplicate["id"] = "increment.duplicated-correction-class"
        duplicate["state"] = "stopped"
        duplicate["taskRegistration"] = None
        for index, work in enumerate(duplicate["workItems"], start=1):
            work["id"] = f"work.duplicated-correction-class-{index}"
            work["state"] = "stopped"
        program["increments"].append(duplicate)
        _write_json(program_path, program)
    elif mutation == "leave-task-owned-temporary-residue":
        residue = checkout / ".tmp"
        residue.mkdir()
        (residue / "sg-11-residue.marker").write_text(
            "controlled residue fault\n", encoding="utf-8", newline="\n"
        )
    elif mutation == "expand-outcome-neutral-process-budget":
        program = _read_json(program_path)
        program["increments"][0]["processLossBudget"][
            "maxConsecutiveOutcomeNeutralWorkItems"
        ] = 2
        _write_json(program_path, program)
    else:
        raise ValueError("unknown O1 lifecycle suite mutation")


def _isolated_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return environment


def execute_scenario(
    root: Path,
    source_revision: str,
    scenario: Scenario,
) -> dict[str, Any]:
    """Exercise one registered fault in a disposable isolated checkout."""

    report: dict[str, Any] = {
        "valid": None,
        "completionState": "unknown",
        "errors": ["O1 lifecycle scenario failed closed: setup incomplete"],
    }
    temporary: tempfile.TemporaryDirectory[str] | None = None
    repository_temporary = root / ".tmp"
    temporary_root: Path | None = None
    temporary_parent_created = False
    cleanup_verified = False
    try:
        if re.fullmatch(r"[0-9a-f]{40}", source_revision) is None:
            raise ValueError("invalid source revision")
        repository_temporary.mkdir()
        temporary_parent_created = True
        temporary = tempfile.TemporaryDirectory(
            prefix="agent-autonomy-harness-o1-",
            dir=repository_temporary,
        )
        temporary_root = Path(temporary.name)
        checkout = temporary_root / "checkout"
        git = shutil.which("git")
        if git is None:
            raise RuntimeError("git unavailable")
        environment = _isolated_environment()
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
            timeout=30,
            env=environment,
        )
        subprocess.run(
            [git, "-C", str(checkout), "checkout", "--quiet", "--detach", source_revision],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            env=environment,
        )
        _apply_fault(checkout, scenario)
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "harness",
                "verify",
                "--root",
                ".",
                "--json",
            ],
            cwd=checkout,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
            env=environment,
        )
        if len(completed.stdout) > 1_048_576 or len(completed.stderr) > 1_048_576:
            raise RuntimeError("scenario output limit exceeded")
        decoded = json.loads(completed.stdout.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("scenario verifier report must be an object")
        report = decoded
    except (
        FileExistsError,
        json.JSONDecodeError,
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        UnicodeError,
        ValueError,
    ) as exc:
        report = {
            "valid": None,
            "completionState": "unknown",
            "errors": [f"O1 lifecycle scenario failed closed: {exc.__class__.__name__}"],
        }
    finally:
        try:
            if temporary is not None:
                temporary.cleanup()
            if temporary_parent_created:
                repository_temporary.rmdir()
            cleanup_verified = (
                (temporary_root is None or not temporary_root.exists())
                and temporary_parent_created
                and not repository_temporary.exists()
            )
        except OSError:
            cleanup_verified = False
    report["probeCleanupVerified"] = cleanup_verified
    return report


def run_suite(
    root: Path,
    source_revision: str,
    *,
    executor: ScenarioExecutor | None = None,
) -> dict[str, Any]:
    """Run the twelve predeclared faults through one local-substitutable seam."""

    selected_executor = execute_scenario if executor is None else executor
    results: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        report = selected_executor(root, source_revision, scenario)
        errors = report.get("errors") if isinstance(report, dict) else None
        observed = (
            isinstance(report, dict)
            and report.get("valid") is False
            and isinstance(errors, list)
            and any(
                isinstance(item, str)
                and scenario.expected_diagnostic in item
                for item in errors
            )
        )
        results.append(
            {
                "sourceSliceIdentity": scenario.source_slice_identity,
                "scenarioIdentity": scenario.scenario_identity,
                "mutationIdentity": scenario.mutation_identity,
                "effectClasses": list(scenario.effect_classes),
                "expectedDiagnostic": scenario.expected_diagnostic,
                "expectedDiagnosticObserved": observed,
                "verifierValid": report.get("valid") if isinstance(report, dict) else None,
                "completionState": (
                    report.get("completionState") if isinstance(report, dict) else None
                ),
                "probeCleanupVerified": (
                    report.get("probeCleanupVerified")
                    if isinstance(report, dict)
                    else False
                ),
                "reportSha256": _canonical_sha256(report),
            }
        )
    return {
        "schema": 1,
        "suiteIdentity": SUITE_IDENTITY,
        "sourceRevision": source_revision,
        "sourceCustodyRevision": SOURCE_REVISION,
        "sourceCustodyPath": SOURCE_PATH,
        "sourceSliceResults": results,
        "accepted": len(results) == 12
        and all(item["expectedDiagnosticObserved"] for item in results)
        and all(item["probeCleanupVerified"] is True for item in results),
        "cleanupVerified": all(
            item["probeCleanupVerified"] is True for item in results
        ),
        "fieldClaimsExcluded": list(FIELD_CLAIM_EXCLUSIONS),
    }


def _slice_records(value: Any, required_fields: set[str]) -> dict[str, dict[str, Any]] | None:
    if not isinstance(value, list) or len(value) != len(SOURCE_SLICES):
        return None
    records: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict) or set(item) != required_fields:
            return None
        source_slice = item.get("sourceSliceIdentity")
        if not isinstance(source_slice, str) or source_slice in records:
            return None
        records[source_slice] = item
    return records if set(records) == set(SOURCE_SLICES) else None


def _expected_phase_records() -> list[dict[str, Any]]:
    return [
        {
            "sourceSliceIdentity": source_slice,
            "lifecyclePhase": LIFECYCLE_PHASE_BY_SLICE[source_slice],
            "productOwner": "agent-autonomy-harness-v1.2",
            "applicability": "applicable",
        }
        for source_slice in SOURCE_SLICES
    ]


def _expected_route_records() -> list[dict[str, Any]]:
    scenarios = {item.source_slice_identity: item for item in SCENARIOS}
    return [
        {
            "sourceSliceIdentity": source_slice,
            "routeClass": ROUTE_CLASS_BY_SLICE[source_slice],
            "routeIdentity": (
                f"{ROUTE_CLASS_BY_SLICE[source_slice]}:{source_slice.lower()}-with-"
                f"task-specific-{scenarios[source_slice].mutation_identity}-guard"
            ),
            "sourceBoundJustification": (
                f"{source_slice} at {SOURCE_REVISION}:{SOURCE_PATH} is exercised by "
                f"{scenarios[source_slice].scenario_identity}"
            ),
            "residualOrUnsupportedBoundary": (
                "controlled verifier effect only; no comparative burden, broad "
                "effectiveness, distinct-Agent or untested-platform claim"
            ),
        }
        for source_slice in SOURCE_SLICES
    ]


def _expected_effect_records() -> list[dict[str, Any]]:
    return [
        {
            "sourceSliceIdentity": scenario.source_slice_identity,
            "effectClasses": list(scenario.effect_classes),
            "expectedObservableEffect": (
                f"canonical verifier rejects {scenario.mutation_identity} with "
                f"{scenario.expected_diagnostic}"
            ),
        }
        for scenario in SCENARIOS
    ]


def validate_registration(
    registration: dict[str, Any],
    increment: dict[str, Any],
    mapped_outcomes: tuple[str, ...],
    root: Path,
    errors: list[str],
) -> bool:
    """Validate the exact O1 suite before any scenario execution."""

    del root
    before = len(errors)
    values = registration.get("preRegistrationValues")
    if (
        increment.get("id") != INCREMENT_ID
        or registration.get("incrementId") != INCREMENT_ID
        or mapped_outcomes != ("O1",)
        or registration.get("criterionIds") != ["O1"]
        or not isinstance(values, dict)
        or set(values) != EXPECTED_PRE_REGISTRATION_FIELDS
    ):
        _error(errors, "O1 lifecycle suite registration identity is invalid")
        return False

    custody = values.get("sourceCustodyRevisionAndPath")
    if custody != {
        "revision": SOURCE_REVISION,
        "path": SOURCE_PATH,
        "manifestBlob": SOURCE_MANIFEST_BLOB,
    }:
        _error(errors, "O1 lifecycle suite source custody is invalid")

    slices = values.get("sourceSliceIdentity")
    if slices != list(SOURCE_SLICES) or len(set(slices if isinstance(slices, list) else [])) != 12:
        _error(errors, "O1 lifecycle suite must bind SG-01 through SG-12 exactly once")

    phase_records = _slice_records(
        values.get("lifecyclePhaseApplicabilityAndOwner"),
        {
            "sourceSliceIdentity",
            "lifecyclePhase",
            "productOwner",
            "applicability",
        },
    )
    if phase_records is None or values.get(
        "lifecyclePhaseApplicabilityAndOwner"
    ) != _expected_phase_records():
        _error(errors, "O1 lifecycle suite phase applicability and ownership are invalid")

    route_records = _slice_records(
        values.get("nativeOfficialExternalDomainOrResidualRoute"),
        {
            "sourceSliceIdentity",
            "routeClass",
            "routeIdentity",
            "sourceBoundJustification",
            "residualOrUnsupportedBoundary",
        },
    )
    if route_records is None or values.get(
        "nativeOfficialExternalDomainOrResidualRoute"
    ) != _expected_route_records():
        _error(errors, "O1 lifecycle suite route dispositions are invalid")

    effect_records = _slice_records(
        values.get("claimedControlEffects"),
        {
            "sourceSliceIdentity",
            "effectClasses",
            "expectedObservableEffect",
        },
    )
    if effect_records is None or values.get(
        "claimedControlEffects"
    ) != _expected_effect_records():
        _error(errors, "O1 lifecycle suite claimed effects must be observable control effects")

    scenario_binding = values.get("controlledScenarioOrCodeValidator")
    expected_scenarios = [
        f"o1-lifecycle-coverage.{source_slice.lower()}" for source_slice in SOURCE_SLICES
    ]
    if scenario_binding != {
        "suiteIdentity": SUITE_IDENTITY,
        "scenarioIdentities": expected_scenarios,
        "validatorIdentity": VALIDATOR_KIND,
    }:
        _error(errors, "O1 lifecycle suite scenario binding is invalid")

    claim_lifecycle = values.get("claimLimitAndLifecycle")
    if claim_lifecycle != CLAIM_LIFECYCLE:
        _error(errors, "O1 lifecycle suite claim limit and lifecycle are invalid")

    validator = registration.get("preMeasurementValidator")
    if not isinstance(validator, dict) or (
        validator.get("kind") != VALIDATOR_KIND
        or validator.get("version") != 1
        or validator.get("locator") != VALIDATOR_LOCATOR
    ):
        _error(errors, "O1 lifecycle suite validator binding is invalid")

    return len(errors) == before


def validate_evidence(
    document: dict[str, Any],
    criterion_id: str,
    root: Path,
    errors: list[str],
) -> bool:
    """Replay and compare the exact content-addressed O1 suite observation."""

    before = len(errors)
    source = document.get("source")
    result = document.get("result")
    if (
        criterion_id != "O1"
        or document.get("criterionIds") != ["O1"]
        or document.get("incrementId") != INCREMENT_ID
        or not isinstance(source, dict)
        or source.get("kind")
        != "controlled-o1-lifecycle-suite-observation"
        or source.get("locator")
        != "product/evidence/o1-lifecycle-suite-observation.json"
        or not isinstance(source.get("identity"), str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", source["identity"]) is None
        or not isinstance(result, dict)
        or set(result)
        != {
            "accepted",
            "suiteIdentity",
            "sourceRevision",
            "observationSha256",
            "replayVerified",
        }
        or result.get("accepted") is not True
        or result.get("suiteIdentity") != SUITE_IDENTITY
        or result.get("replayVerified") is not True
        or not isinstance(result.get("sourceRevision"), str)
        or re.fullmatch(r"[0-9a-f]{40}", result["sourceRevision"]) is None
        or not isinstance(result.get("observationSha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", result["observationSha256"]) is None
        or source.get("identity") != "sha256:" + result.get("observationSha256", "")
    ):
        _error(
            errors,
            "O1 lifecycle suite evidence requires an observable twelve-slice replay",
        )
        return False

    try:
        program = _read_json(root / "product" / "program.json")
        increment = next(
            item
            for item in program.get("increments", [])
            if isinstance(item, dict) and item.get("id") == INCREMENT_ID
        )
        registration_binding = increment.get("taskRegistration")
        source_revision = (
            registration_binding.get("sourceRevision")
            if isinstance(registration_binding, dict)
            else None
        )
        if source_revision != result["sourceRevision"]:
            raise ValueError("evidence revision does not match registration")
        observation_path = (
            root / "product" / "evidence" / "o1-lifecycle-suite-observation.json"
        )
        observation_raw = observation_path.read_bytes()
        if len(observation_raw) > 1_048_576:
            raise ValueError("observation exceeds byte limit")
        observation_sha256 = hashlib.sha256(observation_raw).hexdigest()
        if observation_sha256 != result["observationSha256"]:
            raise ValueError("observation digest mismatch")

        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            value: dict[str, Any] = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate observation key")
                value[key] = item
            return value

        observation = json.loads(
            observation_raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("non-finite observation value")
            ),
        )
        replay = run_suite(root, source_revision)
        if observation != replay:
            raise ValueError("observation does not match independent replay")
        if (
            replay.get("accepted") is not True
            or replay.get("cleanupVerified") is not True
            or [
                item.get("sourceSliceIdentity")
                for item in replay.get("sourceSliceResults", [])
                if isinstance(item, dict)
            ]
            != list(SOURCE_SLICES)
            or replay.get("fieldClaimsExcluded") != list(FIELD_CLAIM_EXCLUSIONS)
        ):
            raise ValueError("replay does not meet the registered claim limit")
    except (
        json.JSONDecodeError,
        OSError,
        RecursionError,
        StopIteration,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        _error(errors, "O1 lifecycle suite evidence replay failed closed")
    return len(errors) == before


__all__ = [
    "INCREMENT_ID",
    "SCENARIOS",
    "VALIDATOR_KIND",
    "VALIDATOR_LOCATOR",
    "execute_scenario",
    "run_suite",
    "validate_evidence",
    "validate_registration",
]
