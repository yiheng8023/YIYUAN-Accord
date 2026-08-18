"""Second-generation task validator for the v1.2 O4 controlled suite.

The first-generation validator is frozen by an immutable stopped registration.
This module reuses its fault execution and carrier projection only through
generation-checking adapters, while binding a distinct increment, registration,
observation and validator identity.  It is not a generic evidence runtime.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable

from . import task_validator_o4_continuous_self_correction as v1


INCREMENT_ID = "increment.v12-o4-continuous-self-correction-second-generation"
VALIDATOR_KIND = "o4-continuous-self-correction-validator-v2"
VALIDATOR_LOCATOR = "harness/task_validator_o4_continuous_self_correction_v2.py"
SUITE_IDENTITY = "o4-continuous-self-correction.controlled-v2"
REGISTRATION_LOCATOR = (
    "product/evidence/o4-continuous-self-correction-second-generation-registration.json"
)
OBSERVATION_LOCATOR = (
    "product/evidence/o4-continuous-self-correction-second-generation-observation.json"
)
CLAIM_CEILING = "bounded-v1.2-controlled-self-correction-and-carrier-evidence-only"


FAULT_SCENARIOS = tuple(
    v1.FaultScenario(
        item.scenario_identity,
        item.scenario_class,
        item.mutation_identity,
        (
            "criterion O1 evidence shape is invalid: "
            "product/evidence/o1-lifecycle-suite-accepted.json"
            if item.scenario_identity
            == "o4-continuous-self-correction.expected-observed-mismatch"
            else item.expected_diagnostic
        ),
    )
    for item in v1.FAULT_SCENARIOS
)
SCENARIO_IDENTITIES = tuple(item.scenario_identity for item in FAULT_SCENARIOS) + (
    v1.CARRIER_SCENARIO_IDENTITIES
)
COUNTEREXAMPLE_SOURCES = deepcopy(v1.COUNTEREXAMPLE_SOURCES)
FAILURE_BINDINGS = deepcopy(v1.FAILURE_BINDINGS)
FAILURE_BINDINGS[2]["expectedDiagnostic"] = FAULT_SCENARIOS[2].expected_diagnostic
CORRECTION_BINDINGS = deepcopy(v1.CORRECTION_BINDINGS)


def _scenario_validator_binding_valid(value: Any) -> bool:
    return value == {
        "suiteIdentity": SUITE_IDENTITY,
        "scenarioIdentities": list(SCENARIO_IDENTITIES),
        "validatorIdentity": VALIDATOR_KIND,
        "validatorLocator": VALIDATOR_LOCATOR,
        "hostProjectionBuilder": f"{VALIDATOR_LOCATOR}:project_raw_carrier_observations",
        "codexSourceBinding": v1.CODEX_SOURCE_BINDING,
        "controlledGoalArtifact": v1.CARRIER_GOAL_BINDING,
        "receiptOnlyAccepted": False,
    }


def validate_registration(
    registration: dict[str, Any],
    increment: dict[str, Any],
    mapped_outcomes: tuple[str, ...],
    root: Path,
    errors: list[str],
) -> bool:
    """Validate the distinct second-generation suite before measurement."""

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
        or not isinstance(registration_binding, dict)
        or registration_binding.get("locator") != REGISTRATION_LOCATOR
        or mapped_outcomes != ("O4",)
        or registration.get("criterionIds") != ["O4"]
        or not isinstance(values, dict)
        or set(values) != v1.EXPECTED_PRE_REGISTRATION_FIELDS
    ):
        v1._error(errors, "O4 second-generation registration identity is invalid")
        return False
    if values.get("counterexampleIdentityAndSource") != COUNTEREXAMPLE_SOURCES:
        v1._error(errors, "O4 second-generation suite must bind all six sources exactly once")
    if not v1._goal_artifact_committed(root, source_revision):
        v1._error(errors, "O4 controlled carrier goal artifact is not committed exactly")
    if not v1._starting_state_valid(values.get("startingAuthorityGoalAndCarrierState")):
        v1._error(errors, "O4 second-generation starting state is invalid")
    if values.get("injectedOrObservedFailure") != FAILURE_BINDINGS:
        v1._error(errors, "O4 second-generation failure bindings are invalid")
    if values.get("expectedDetectionAndCorrection") != CORRECTION_BINDINGS:
        v1._error(errors, "O4 second-generation correction bindings are invalid")
    if values.get("transitionAndCleanupBoundary") != v1.TRANSITION_AND_CLEANUP_BOUNDARY:
        v1._error(errors, "O4 second-generation cleanup boundary is invalid")
    if not _scenario_validator_binding_valid(values.get("scenarioValidator")):
        v1._error(errors, "O4 second-generation validator binding is invalid")
    validator = registration.get("preMeasurementValidator")
    if not isinstance(validator, dict) or (
        validator.get("kind") != VALIDATOR_KIND
        or validator.get("version") != 1
        or validator.get("locator") != VALIDATOR_LOCATOR
    ):
        v1._error(errors, "O4 second-generation pre-measurement validator is invalid")
    return len(errors) == before


FaultExecutor = Callable[[Path, str, v1.FaultScenario], dict[str, Any]]


def run_fault_suite(
    root: Path,
    source_revision: str,
    *,
    executor: FaultExecutor | None = None,
) -> dict[str, Any]:
    """Replay the four registered repository faults under v2 bindings."""

    selected = v1.execute_fault_scenario if executor is None else executor
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


def project_raw_carrier_observations(
    scenario_identity: str,
    raw_observations: list[dict[str, Any]],
    *,
    source_carrier_id: str,
    expected_head: str,
    destination_carrier_id: str | None = None,
    expected_cwd: str | None = None,
) -> dict[str, Any]:
    """Reuse the frozen projector only after rejecting cross-generation input."""

    copied = deepcopy(raw_observations)
    verifier_reports = [
        item.get("report")
        for item in copied
        if isinstance(item, dict)
        and item.get("source") == "python--B--m-harness-verify-json"
    ]
    if (
        len(verifier_reports) != 1
        or not isinstance(verifier_reports[0], dict)
        or verifier_reports[0].get("activeIncrement") != INCREMENT_ID
    ):
        raise ValueError("raw canonical verifier observation has wrong O4 generation")
    verifier_reports[0]["activeIncrement"] = v1.INCREMENT_ID
    return v1.project_raw_carrier_observations(
        scenario_identity,
        copied,
        source_carrier_id=source_carrier_id,
        expected_head=expected_head,
        destination_carrier_id=destination_carrier_id,
        expected_cwd=expected_cwd,
    )


def _measurement_baseline_valid(root: Path, baseline_revision: Any) -> bool:
    if (
        not isinstance(baseline_revision, str)
        or re.fullmatch(r"[0-9a-f]{40}", baseline_revision) is None
    ):
        return False
    try:
        resolved_root = root.resolve(strict=True)
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
        ancestry = subprocess.run(
            [git, "rev-list", "--parents", "-n", "1", baseline_revision], **common
        )
        if (
            ancestry.returncode != 0
            or len(ancestry.stdout) > 256
            or len(ancestry.stderr) > 16_384
        ):
            return False
        parts = ancestry.stdout.decode("ascii").strip().split()
        if len(parts) != 2 or parts[0] != baseline_revision:
            return False
        registration_revision = parts[1]
        head_ancestry = subprocess.run(
            [git, "merge-base", "--is-ancestor", baseline_revision, "HEAD"], **common
        )
        if (
            head_ancestry.returncode != 0
            or head_ancestry.stdout
            or len(head_ancestry.stderr) > 16_384
        ):
            return False
        changed = subprocess.run(
            [git, "diff-tree", "--no-commit-id", "--name-only", "-r", baseline_revision],
            **common,
        )
        if (
            changed.returncode != 0
            or len(changed.stdout) > 4_096
            or len(changed.stderr) > 16_384
            or changed.stdout.decode("utf-8").splitlines() != ["product/program.json"]
        ):
            return False
        program_object = f"{baseline_revision}:product/program.json"
        size = subprocess.run([git, "cat-file", "-s", program_object], **common)
        if size.returncode != 0 or len(size.stdout) > 32 or len(size.stderr) > 16_384:
            return False
        program_size = int(size.stdout.decode("ascii").strip())
        if program_size <= 0 or program_size > 1_048_576:
            return False
        blob = subprocess.run([git, "cat-file", "blob", program_object], **common)
        if (
            blob.returncode != 0
            or len(blob.stdout) != program_size
            or len(blob.stderr) > 16_384
        ):
            return False
        program = v1._strict_json_object(blob.stdout)
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        return False

    increments = program.get("increments")
    if not isinstance(increments, list):
        return False
    active = [
        item
        for item in increments
        if isinstance(item, dict) and item.get("state") == "active"
    ]
    if len(active) != 1 or active[0].get("id") != INCREMENT_ID:
        return False
    increment = active[0]
    registration = increment.get("taskRegistration")
    work_items = increment.get("workItems")
    active_work = (
        [
            item
            for item in work_items
            if isinstance(item, dict) and item.get("state") == "active"
        ]
        if isinstance(work_items, list)
        else []
    )
    return (
        program.get("status") == "active"
        and program.get("activeIncrementId") == INCREMENT_ID
        and isinstance(registration, dict)
        and registration.get("locator") == REGISTRATION_LOCATOR
        and registration.get("sourceRevision") == registration_revision
        and len(active_work) == 1
    )


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
        != list(v1.CARRIER_SCENARIO_IDENTITIES)
        or not all(v1._carrier_projection_valid(item) for item in projections)
        or observation.get("claimCeiling") != CLAIM_CEILING
        or observation.get("cleanupVerified") is not True
        or not _measurement_baseline_valid(root, source_revision)
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
    """Replay v2 faults and validate its two ordered carrier projections."""

    before = len(errors)
    source = document.get("source")
    result = document.get("result")
    if (
        criterion_id != "O4"
        or document.get("criterionIds") != ["O4"]
        or document.get("incrementId") != INCREMENT_ID
        or not isinstance(source, dict)
        or source.get("kind") != "controlled-o4-self-correction-suite-observation"
        or source.get("locator") != OBSERVATION_LOCATOR
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
        or result.get("claimCeiling") != CLAIM_CEILING
    ):
        v1._error(errors, "O4 second-generation evidence is incomplete")
        return False
    try:
        raw = (root / OBSERVATION_LOCATOR).read_bytes()
        if hashlib.sha256(raw).hexdigest() != result["observationSha256"]:
            raise ValueError("O4 second-generation observation digest mismatch")
        observation = v1._strict_json_object(raw)
        if not _observation_valid(root, observation, result["sourceRevision"]):
            raise ValueError("O4 second-generation observation replay failed")
    except (
        json.JSONDecodeError,
        OSError,
        RecursionError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        v1._error(errors, "O4 second-generation evidence replay failed closed")
    return len(errors) == before


__all__ = [
    "COUNTEREXAMPLE_SOURCES",
    "FAILURE_BINDINGS",
    "FAULT_SCENARIOS",
    "INCREMENT_ID",
    "OBSERVATION_LOCATOR",
    "REGISTRATION_LOCATOR",
    "SCENARIO_IDENTITIES",
    "SUITE_IDENTITY",
    "VALIDATOR_KIND",
    "VALIDATOR_LOCATOR",
    "project_raw_carrier_observations",
    "run_fault_suite",
    "validate_evidence",
    "validate_registration",
]
