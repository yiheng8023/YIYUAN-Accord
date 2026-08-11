from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Any


PRODUCT_ID = "agent-autonomy-harness"
COMPLETION_EXPRESSION = "O1 && O2 && O3 && O4 && O5"
OUTCOME_IDS = tuple(f"O{number}" for number in range(1, 6))
GUARDRAIL_IDS = tuple(f"G{number}" for number in range(1, 5))
EXPECTED_CRITERION_IDS = set(OUTCOME_IDS + GUARDRAIL_IDS)
AUTHORITY_IDS = {
    "product/constitution.json": "harness-product-constitution-v1",
    "product/program.json": "harness-product-program-v0.1",
    "product/acceptance.json": "harness-product-acceptance-v0.1",
}

# These minimum guards belong to the verifier, not to the document it verifies.
PREDECESSOR_IDENTITY = re.compile(r"agent[-]skills[-]curated", re.IGNORECASE)
LEGACY_AUTHORITY_PATHS = (
    re.compile(r"registry/curation[-]program[-]plan[.]json", re.IGNORECASE),
    re.compile(r"registry/program[-]acceptance[-]map[.]json", re.IGNORECASE),
)
BOOTSTRAP_AUTHORITY_FILES = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "NOTICE",
    "docs/architecture.md",
    "docs/strategy/PRODUCT-NORTH-STAR.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "docs/operations/CURRENT-GOAL-MODE-PROMPT.md",
    "docs/operations/CONTINUATION.md",
    "docs/operations/HISTORY.md",
    ".github/workflows/validate.yml",
    "scripts/verify.py",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/control.py",
)
BOOTSTRAP_AUTHORITY_GLOBS = ("product/**/*.json", "harness/**/*.py")
TEXT_SUFFIXES = {".json", ".md", ".py", ".yml", ".yaml"}
TEXT_FILENAMES = {".gitignore", "LICENSE", "NOTICE"}
SCAN_EXCLUDED_PARTS = {".git", "legacy", "__pycache__", ".pytest_cache", ".mypy_cache"}
REQUIRED_USER_AUTHORITY_IDS = {
    "product-direction",
    "creative-judgment",
    "new-trust",
    "new-account",
    "new-cost",
    "publication",
    "release",
    "irreversible-action",
}
ALLOWED_AGENT_OPERATION_IDS = {
    "repository-read",
    "repository-edit",
    "causal-planning",
    "local-verification",
    "progress-accounting",
    "handoff",
    "bounded-cleanup",
    "git-commit",
    "git-push",
}


def _inside_root(root: Path, relative: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        errors.append("authority path must be a non-empty string")
        return None
    try:
        path = (root / relative).resolve()
        path.relative_to(root.resolve())
    except (OSError, ValueError):
        errors.append(f"authority path escapes the product root: {relative}")
        return None
    return path


def _load(root: Path, relative: str, errors: list[str]) -> dict[str, Any]:
    path = _inside_root(root, relative, errors)
    if path is None:
        return {}
    if not path.is_file():
        errors.append(f"missing product authority file: {relative}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot decode {relative}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"product authority file must contain an object: {relative}")
        return {}
    return value


def _string_list(value: Any, label: str, errors: list[str]) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        errors.append(f"{label} must be a list of non-empty strings")
        return []
    return value


def _active_files(root: Path, constitution: dict[str, Any], errors: list[str]) -> list[Path]:
    declared_files = _string_list(
        constitution.get("requiredAuthorityFiles"),
        "constitution requiredAuthorityFiles",
        errors,
    )
    declared_globs = _string_list(
        constitution.get("activeAuthorityGlobs"),
        "constitution activeAuthorityGlobs",
        errors,
    )
    safe_declared_files: list[str] = []
    safe_declared_globs: list[str] = []
    for locator in declared_files:
        parts = {part.casefold() for part in locator.replace("\\", "/").split("/")}
        if SCAN_EXCLUDED_PARTS.intersection(parts):
            errors.append(f"constitution cannot activate excluded authority locator: {locator}")
        else:
            safe_declared_files.append(locator)
    for pattern in declared_globs:
        normalized = pattern.replace("\\", "/")
        parts = {part.casefold() for part in normalized.split("/")}
        if (
            Path(pattern).is_absolute()
            or re.match(r"^[A-Za-z]:[/\\]", pattern)
            or normalized.startswith("//")
            or ".." in parts
        ):
            errors.append(f"constitution authority glob must be relative: {pattern}")
        elif SCAN_EXCLUDED_PARTS.intersection(parts):
            errors.append(f"constitution cannot activate excluded authority locator: {pattern}")
        else:
            safe_declared_globs.append(pattern)

    missing_bootstrap = sorted(set(BOOTSTRAP_AUTHORITY_FILES) - set(safe_declared_files))
    for relative in missing_bootstrap:
        errors.append(f"constitution cannot remove bootstrap authority file: {relative}")
    missing_globs = sorted(set(BOOTSTRAP_AUTHORITY_GLOBS) - set(safe_declared_globs))
    for pattern in missing_globs:
        errors.append(f"constitution cannot remove bootstrap authority glob: {pattern}")

    files: set[Path] = set()
    for relative in sorted(set(safe_declared_files) | set(BOOTSTRAP_AUTHORITY_FILES)):
        path = _inside_root(root, relative, errors)
        if path is None:
            continue
        if not path.is_file():
            errors.append(f"missing active authority file: {relative}")
        else:
            files.add(path)
    for pattern in sorted(set(safe_declared_globs) | set(BOOTSTRAP_AUTHORITY_GLOBS)):
        try:
            files.update(path for path in root.glob(pattern) if path.is_file())
        except (OSError, ValueError, NotImplementedError) as exc:
            errors.append(f"cannot expand active authority glob {pattern}: {exc}")
    return sorted(files)


def _checkout_files(root: Path, errors: list[str]) -> list[Path]:
    try:
        candidates = root.rglob("*")
        return sorted(
            path
            for path in candidates
            if path.is_file()
            and not path.is_symlink()
            and not SCAN_EXCLUDED_PARTS.intersection(
                part.casefold() for part in path.relative_to(root).parts
            )
            and path.suffix.lower() not in {".pyc", ".pyo"}
        )
    except (OSError, ValueError) as exc:
        errors.append(f"cannot enumerate current checkout: {exc}")
        return []


def _validate_identity(root: Path, active_files: list[Path], errors: list[str]) -> bool:
    initial_error_count = len(errors)
    forbidden_content = False
    forbidden_path = False
    scan_files = set(active_files) | set(_checkout_files(root, errors))
    for path in sorted(scan_files):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            errors.append(f"active authority file escapes the product root: {path}")
            continue
        if any(pattern.search(relative) for pattern in LEGACY_AUTHORITY_PATHS):
            forbidden_path = True
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_FILENAMES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot read current checkout file {relative}: {exc}")
            continue
        if PREDECESSOR_IDENTITY.search(text) or any(
            pattern.search(text) for pattern in LEGACY_AUTHORITY_PATHS
        ):
            forbidden_content = True
    if forbidden_content:
        errors.append("active product authority contains a forbidden predecessor identity")
    if forbidden_path:
        errors.append("current checkout contains a forbidden predecessor authority path")
    return not forbidden_content and not forbidden_path and len(errors) == initial_error_count


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _valid_route_evidence(document: dict[str, Any]) -> bool:
    task = document.get("task")
    route = document.get("selectedRoute")
    authority = document.get("authority")
    return (
        isinstance(task, dict)
        and task.get("invented") is False
        and isinstance(task.get("kind"), str)
        and isinstance(route, dict)
        and isinstance(route.get("id"), str)
        and _non_empty_string_list(route.get("capabilities"))
        and isinstance(authority, dict)
        and _non_empty_string_list(authority.get("allowed"))
        and _non_empty_string_list(authority.get("notGranted"))
    )


def _valid_lifecycle_evidence(document: dict[str, Any]) -> bool:
    transaction = document.get("transaction")
    if not isinstance(transaction, dict):
        return False
    receipts = transaction.get("phaseReceipts")
    required_receipts = {"preview", "activation", "observation", "rollback", "cleanup"}
    owners = transaction.get("lifecycleOwners")
    return (
        transaction.get("accepted") is True
        and isinstance(receipts, dict)
        and required_receipts.issubset(receipts)
        and all(bool(receipts[item]) for item in required_receipts)
        and isinstance(owners, list)
        and len(owners) == 1
        and isinstance(owners[0], str)
        and bool(owners[0].strip())
        and transaction.get("residualProjectionCount") == 0
        and transaction.get("dualAuthority") is False
    )


def _valid_continuation_evidence(document: dict[str, Any]) -> bool:
    continuation = document.get("continuation")
    if not isinstance(continuation, dict):
        return False
    receiver_delta = continuation.get("receiverDelta")
    claim_boundary = continuation.get("receiverClaimBoundary")
    return (
        continuation.get("realEvent") is True
        and isinstance(receiver_delta, dict)
        and receiver_delta.get("materialRestatementItems") == 0
        and (
            isinstance(claim_boundary, str)
            and bool(claim_boundary.strip())
            or _non_empty_string_list(claim_boundary)
        )
    )


def _resolved_absolute_roots(value: Any) -> bool:
    def resolved_absolute(item: Any) -> bool:
        if not isinstance(item, str) or not item.strip():
            return False
        if any(marker in item for marker in ("%", "$", "~")):
            return False
        return bool(
            PurePosixPath(item).is_absolute()
            or PureWindowsPath(item).is_absolute()
        )

    return (
        isinstance(value, list)
        and bool(value)
        and all(resolved_absolute(item) for item in value)
    )


def _validate_cleanup_evidence(
    document: dict[str, Any], relative: str, errors: list[str]
) -> bool:
    valid = True
    if not _resolved_absolute_roots(document.get("roots")):
        valid = False
        errors.append(f"cleanup evidence {relative} must declare resolved absolute roots")
    pattern = document.get("targetPattern")
    if not isinstance(pattern, str) or not pattern.strip():
        valid = False
        errors.append(f"cleanup evidence {relative} must declare an exact targetPattern")
    else:
        try:
            re.compile(pattern)
        except re.error:
            valid = False
            errors.append(f"cleanup evidence {relative} targetPattern must compile")
    if not isinstance(document.get("operation"), str) or not document["operation"].strip():
        valid = False
        errors.append(f"cleanup evidence {relative} must describe the bounded operation")
    if document.get("remainingMatches") != 0:
        valid = False
        errors.append(f"evidence {relative} must report zero remainingMatches")
    return valid


def _validate_evidence(
    root: Path,
    criteria: list[dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, bool], bool]:
    states: dict[str, bool] = {}
    claim_limits_complete = True
    for criterion in criteria:
        criterion_id = criterion.get("id")
        assessment = criterion.get("assessment")
        if assessment == "planned":
            states[criterion_id] = False
            continue
        if assessment == "computed":
            continue
        if assessment != "verified":
            errors.append(f"criterion {criterion_id} has unsupported assessment {assessment!r}")
            states[criterion_id] = False
            continue
        evidence_paths = criterion.get("evidence")
        if not _non_empty_string_list(evidence_paths):
            errors.append(f"verified criterion {criterion_id} has no valid evidence paths")
            states[criterion_id] = False
            continue
        verified = True
        for relative in evidence_paths:
            document = _load(root, relative, errors)
            if not document:
                verified = False
                continue
            limits = document.get("claimLimits")
            if not _non_empty_string_list(limits):
                claim_limits_complete = False
                verified = False
                errors.append(f"evidence {relative} must declare non-empty claimLimits")
            if criterion_id == "O2" and not _valid_route_evidence(document):
                verified = False
                errors.append(f"evidence {relative} must contain a source-bound route and authority boundary")
            if criterion_id == "O3" and not _valid_lifecycle_evidence(document):
                verified = False
                errors.append(f"evidence {relative} is not an accepted capability lifecycle transaction")
            if criterion_id == "O4" and not _valid_continuation_evidence(document):
                verified = False
                errors.append(f"evidence {relative} is not a real continuation receipt")
            if criterion_id in {"O5", "G4"} and not _validate_cleanup_evidence(document, relative, errors):
                verified = False
        states[criterion_id] = verified
    return states, claim_limits_complete


def verify_product(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    constitution = _load(root, "product/constitution.json", errors)
    program = _load(root, "product/program.json", errors)
    acceptance = _load(root, "product/acceptance.json", errors)

    for relative, expected_id in AUTHORITY_IDS.items():
        document = {
            "product/constitution.json": constitution,
            "product/program.json": program,
            "product/acceptance.json": acceptance,
        }[relative]
        if document.get("id") != expected_id:
            errors.append(f"{relative} must retain authority id {expected_id}")

    product_id = constitution.get("productId", program.get("productId", "unknown"))
    release = program.get("release", acceptance.get("release", "unknown"))
    if (
        product_id != PRODUCT_ID
        or program.get("productId") != PRODUCT_ID
        or acceptance.get("productId") != PRODUCT_ID
    ):
        errors.append(f"all product authorities must bind product identity {PRODUCT_ID}")
    if program.get("constitution") != "product/constitution.json":
        errors.append("program must bind product/constitution.json")
    if program.get("acceptance") != "product/acceptance.json":
        errors.append("program must bind product/acceptance.json")
    if acceptance.get("program") != "product/program.json":
        errors.append("acceptance must bind product/program.json")
    if program.get("release") != acceptance.get("release"):
        errors.append("program and acceptance releases must match")
    if program.get("completionExpression") != COMPLETION_EXPRESSION:
        errors.append(f"program completion expression must be {COMPLETION_EXPRESSION}")
    if acceptance.get("completionExpression") != program.get("completionExpression"):
        errors.append("program and acceptance completion expressions must match")

    raw_criteria = acceptance.get("criteria")
    criteria: list[dict[str, Any]] = []
    if not isinstance(raw_criteria, list):
        errors.append("acceptance criteria must be a list")
    else:
        for index, criterion in enumerate(raw_criteria):
            if not isinstance(criterion, dict):
                errors.append(f"acceptance criterion {index} must be an object")
            else:
                criteria.append(criterion)
    criterion_ids = [
        criterion.get("id")
        for criterion in criteria
        if isinstance(criterion.get("id"), str)
    ]
    criterion_by_id = {
        criterion["id"]: criterion
        for criterion in criteria
        if isinstance(criterion.get("id"), str)
    }
    if (
        set(criterion_by_id) != EXPECTED_CRITERION_IDS
        or len(criterion_ids) != len(EXPECTED_CRITERION_IDS)
    ):
        errors.append("acceptance criteria must contain exactly one each of O1-O5 and G1-G4")
    for criterion_id, criterion in criterion_by_id.items():
        expected_class = "outcome" if criterion_id.startswith("O") else "guardrail"
        if criterion.get("class") != expected_class:
            errors.append(f"criterion {criterion_id} must be classed as {expected_class}")
        for field in ("statement", "metric", "threshold", "assessment"):
            if not isinstance(criterion.get(field), str) or not criterion[field].strip():
                errors.append(f"criterion {criterion_id} is missing {field}")

    planning_model = constitution.get("planningModel")
    if not isinstance(planning_model, dict):
        planning_model = {}
        errors.append("constitution planningModel must be an object")
    if planning_model.get("maxActiveIncrements") != 1:
        errors.append("constitution must keep maxActiveIncrements at one")
    if planning_model.get("maxActiveWorkItems") != 1:
        errors.append("constitution must keep maxActiveWorkItems at one")

    raw_increments = program.get("increments")
    increments: list[dict[str, Any]] = []
    if not isinstance(raw_increments, list):
        errors.append("program increments must be a list")
    else:
        for index, increment in enumerate(raw_increments):
            if not isinstance(increment, dict):
                errors.append(f"program increment {index} must be an object")
            else:
                increments.append(increment)
    active_increments = [item for item in increments if item.get("state") == "active"]
    if len(active_increments) != 1:
        errors.append("program must have exactly one active causal increment")
    active_increment_id = program.get("activeIncrementId")
    if len(active_increments) == 1 and active_increments[0].get("id") != active_increment_id:
        errors.append("activeIncrementId must identify the active causal increment")

    mapped_criteria: set[str] = set()
    active_work_items = 0
    bounded_work_operations: set[str] = set()
    bounded_work_operations_valid = True
    for increment in increments:
        increment_id = increment.get("id", "<missing>")
        if not isinstance(increment_id, str) or not increment_id.strip():
            errors.append("every program increment must have a non-empty id")
        for field in ("observedProblem", "hypothesis", "falsifier", "stopCondition"):
            if not isinstance(increment.get(field), str) or not increment[field].strip():
                errors.append(f"increment {increment_id} is missing {field}")
        increment_acceptance = _string_list(
            increment.get("acceptanceIds"),
            f"increment {increment_id} acceptanceIds",
            errors,
        )
        mapped_criteria.update(increment_acceptance)
        for criterion_id in increment_acceptance:
            if criterion_id not in criterion_by_id:
                errors.append(f"increment {increment_id} maps unknown criterion {criterion_id}")
        raw_work_items = increment.get("workItems")
        if not isinstance(raw_work_items, list):
            errors.append(f"increment {increment_id} workItems must be a list")
            continue
        for index, work_item in enumerate(raw_work_items):
            if not isinstance(work_item, dict):
                errors.append(f"increment {increment_id} work item {index} must be an object")
                continue
            work_id = work_item.get("id", "<missing>")
            if not isinstance(work_id, str) or not work_id.strip():
                errors.append(f"increment {increment_id} has a work item without an id")
            work_acceptance = _string_list(
                work_item.get("acceptanceIds"),
                f"work item {work_id} acceptanceIds",
                errors,
            )
            if not work_acceptance:
                errors.append(f"work item {work_id} must map to at least one acceptance criterion")
            for criterion_id in work_acceptance:
                if criterion_id not in criterion_by_id:
                    errors.append(f"work item {work_id} maps unknown criterion {criterion_id}")
            operation_ids = _string_list(
                work_item.get("operationIds"),
                f"work item {work_id} operationIds",
                errors,
            )
            if work_item.get("state") in {"active", "completed"}:
                if not operation_ids:
                    bounded_work_operations_valid = False
                bounded_work_operations.update(operation_ids)
            if work_item.get("state") == "active":
                active_work_items += 1
    if not set(OUTCOME_IDS).issubset(mapped_criteria):
        errors.append("every product outcome must be mapped by at least one causal increment")
    if active_work_items > 1:
        errors.append("program exceeds the active work-item limit")

    active_files = _active_files(root, constitution, errors)
    structure_valid = not errors
    evidence_states, claim_limits_complete = _validate_evidence(root, criteria, errors)
    identity_valid = _validate_identity(root, active_files, errors)

    authority_boundary = program.get("authorityBoundary")
    user_authority = (
        authority_boundary.get("userOwns") if isinstance(authority_boundary, dict) else None
    )
    agent_authority = (
        authority_boundary.get("agentOwnsWithinBoundedAuthority")
        if isinstance(authority_boundary, dict)
        else None
    )
    authority_contract_valid = (
        _non_empty_string_list(user_authority)
        and set(user_authority) == REQUIRED_USER_AUTHORITY_IDS
        and len(user_authority) == len(REQUIRED_USER_AUTHORITY_IDS)
        and _non_empty_string_list(agent_authority)
        and set(agent_authority) == ALLOWED_AGENT_OPERATION_IDS
        and len(agent_authority) == len(ALLOWED_AGENT_OPERATION_IDS)
    )
    unauthorized_operations = sorted(
        bounded_work_operations - ALLOWED_AGENT_OPERATION_IDS
    )
    authority_valid = (
        authority_contract_valid
        and bounded_work_operations_valid
        and not unauthorized_operations
    )
    if not authority_contract_valid:
        errors.append("program authority boundary is incomplete or conflicting")
    if unauthorized_operations:
        errors.append(
            "active work requests unauthorized operations: "
            + ", ".join(unauthorized_operations)
        )
    if not bounded_work_operations_valid:
        errors.append("active or completed work must bind at least one operation")

    evidence_states["O1"] = structure_valid
    evidence_states["G1"] = authority_valid
    evidence_states["G2"] = claim_limits_complete
    evidence_states["G3"] = identity_valid

    verified_outcomes = sum(bool(evidence_states.get(item)) for item in OUTCOME_IDS)
    passed_guardrails = sum(bool(evidence_states.get(item)) for item in GUARDRAIL_IDS)
    complete = (
        not errors
        and verified_outcomes == len(OUTCOME_IDS)
        and passed_guardrails == len(GUARDRAIL_IDS)
    )

    return {
        "valid": not errors,
        "productId": product_id,
        "release": release,
        "activeIncrement": active_increment_id,
        "outcomes": {"total": len(OUTCOME_IDS), "verified": verified_outcomes},
        "guardrails": {"total": len(GUARDRAIL_IDS), "passed": passed_guardrails},
        "completionState": "accepted" if complete else "in-progress",
        "criterionStates": {
            item: bool(evidence_states.get(item)) for item in OUTCOME_IDS + GUARDRAIL_IDS
        },
        "errors": errors,
    }
