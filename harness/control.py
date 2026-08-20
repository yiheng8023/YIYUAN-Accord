from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable

from .guardrails import (
    criterion_observation_decision,
    forbidden_path_present,
    known_task_residue,
    manifest_shape_errors,
    marketplace_errors,
    projection_evidence_binding_errors,
    repository_release_authorization_errors,
    repository_relative_path,
    validate_projection_package,
    validate_runtime_release_authorization,
)


AUTHORITY_FILES = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
)
GOLDEN_TASKS_FILE = "evals/golden-tasks.json"
MAX_JSON_BYTES = 1_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
ASSESSMENTS = {"planned", "verified", "blocked", "continuing"}
PROGRAM_STATES = {"active", "ready", "blocked", "released"}


class ContractDataError(ValueError):
    pass


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ContractDataError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ContractDataError(f"non-finite JSON number: {value}")


def _safe_file(root: Path, locator: str, errors: list[str]) -> Path | None:
    if not isinstance(locator, str) or not locator or "\\" in locator:
        errors.append(f"invalid repository locator: {locator!r}")
        return None
    relative = Path(locator)
    if relative.is_absolute() or ".." in relative.parts:
        errors.append(f"repository locator escapes root: {locator!r}")
        return None
    candidate = root / relative
    try:
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        errors.append(f"missing repository file {locator}: {exc}")
        return None
    if not resolved.is_relative_to(resolved_root):
        errors.append(f"repository locator resolves outside root: {locator}")
        return None
    if not resolved.is_file() or candidate.is_symlink():
        errors.append(f"repository locator is not a regular owned file: {locator}")
        return None
    return resolved


def _read_json(root: Path, locator: str, errors: list[str]) -> dict[str, Any]:
    path = _safe_file(root, locator, errors)
    if path is None:
        return {}
    try:
        raw = path.read_bytes()
        if len(raw) > MAX_JSON_BYTES:
            raise ContractDataError(f"JSON exceeds {MAX_JSON_BYTES} bytes")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(value, dict):
            raise ContractDataError("top-level JSON value is not an object")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, ContractDataError) as exc:
        errors.append(f"invalid JSON {locator}: {exc}")
        return {}


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    if any(not _nonempty_string(item) for item in value):
        return None
    return value


def _object_entries(
    owner: dict[str, Any],
    field: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    value = owner.get(field)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        errors.append(f"{field} must be a list of objects")
        return []
    if not value:
        errors.append(f"{field} must not be empty")
    return value


def _entry_ids(
    entries: Iterable[dict[str, Any]],
    label: str,
    errors: list[str],
) -> list[str]:
    ids: list[str] = []
    for index, entry in enumerate(entries):
        value = entry.get("id")
        if not _nonempty_string(value):
            errors.append(f"{label}[{index}].id must be a non-empty string")
            continue
        ids.append(value)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        errors.append(f"{label} contains duplicate ids: {duplicates}")
    return ids


def _validate_mapping(
    entry: dict[str, Any],
    label: str,
    allowed: set[str],
    errors: list[str],
) -> None:
    mapped = _string_list(entry.get("mapsTo"))
    if not mapped:
        errors.append(f"{label}.mapsTo must be a non-empty string list")
        return
    if len(mapped) != len(set(mapped)):
        errors.append(f"{label}.mapsTo contains duplicates")
    unknown = sorted(set(mapped) - allowed)
    if unknown:
        errors.append(f"{label}.mapsTo contains unknown ids: {unknown}")


def _validate_constitution(
    constitution: dict[str, Any],
    errors: list[str],
) -> dict[str, list[str]]:
    if constitution.get("schema") != 2:
        errors.append("constitution.schema must be 2")
    for field in ("id", "productId", "purpose", "successDefinition"):
        if not _nonempty_string(constitution.get(field)):
            errors.append(f"constitution.{field} must be a non-empty string")

    kernel = _object_entries(constitution, "kernel", errors)
    hosts = _object_entries(constitution, "hostAdapterStandard", errors)
    lessons = _object_entries(constitution, "learnedFailureStandards", errors)
    kernel_ids = _entry_ids(kernel, "kernel", errors)
    host_ids = _entry_ids(hosts, "hostAdapterStandard", errors)
    lesson_ids = _entry_ids(lessons, "learnedFailureStandards", errors)

    for index, entry in enumerate(kernel):
        for field in ("name", "commitment"):
            if not _nonempty_string(entry.get(field)):
                errors.append(f"kernel[{index}].{field} must be a non-empty string")
    for label, entries in (
        ("hostAdapterStandard", hosts),
        ("learnedFailureStandards", lessons),
    ):
        for index, entry in enumerate(entries):
            if not _nonempty_string(entry.get("rule")):
                errors.append(f"{label}[{index}].rule must be a non-empty string")
            _validate_mapping(
                entry,
                f"{label}[{index}]",
                set(kernel_ids),
                errors,
            )

    invariants = _string_list(constitution.get("qualityInvariants"))
    if not invariants:
        errors.append("constitution.qualityInvariants must be non-empty")
    elif len(invariants) != len(set(invariants)):
        errors.append("constitution.qualityInvariants contains duplicates")

    evidence = constitution.get("evidenceBoundary")
    if not isinstance(evidence, dict) or not _string_list(evidence.get("classes")):
        errors.append("constitution.evidenceBoundary.classes must be non-empty")

    authority = constitution.get("authority")
    if not isinstance(authority, dict):
        errors.append("constitution.authority must be an object")
    else:
        if authority.get("semantic") != list(AUTHORITY_FILES):
            errors.append("constitution.authority.semantic must name the three authority files")
        if authority.get("executableVerifier") != "python -B -m harness verify":
            errors.append(
                "constitution.authority.executableVerifier must be the public harness command"
            )

    return {
        "kernel": kernel_ids,
        "host": host_ids,
        "lessons": lesson_ids,
    }


def _validate_input_evidence(
    root: Path,
    program: dict[str, Any],
    errors: list[str],
) -> None:
    inputs = _object_entries(program, "inputEvidence", errors)
    _entry_ids(inputs, "inputEvidence", errors)
    for index, item in enumerate(inputs):
        locator = item.get("repositoryLocator")
        if locator is not None:
            path = _safe_file(root, locator, errors)
            expected = item.get("repositorySha256")
            if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
                errors.append(f"inputEvidence[{index}].repositorySha256 is invalid")
            elif path is not None and _hash(path) != expected:
                errors.append(f"inputEvidence[{index}] repository digest mismatch")
        revision = item.get("revision")
        if revision is not None and (
            not isinstance(revision, str) or not REVISION_RE.fullmatch(revision)
        ):
            errors.append(f"inputEvidence[{index}].revision is not an exact Git revision")


def _fallback_repository_files(root: Path) -> list[str]:
    files: list[str] = []
    ignored_parts = {".git", ".tmp", "__pycache__"}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in ignored_parts for part in relative.parts):
            continue
        files.append(relative.as_posix())
    return sorted(files)


def _repository_files(root: Path) -> tuple[list[str], str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        if result.returncode == 0:
            indexed = [
                item.decode("utf-8")
                for item in result.stdout.split(b"\0")
                if item
            ]
            return (
                sorted(
                    {
                        item
                        for item in indexed
                        if (root / item).is_file()
                        and not (root / item).is_symlink()
                    }
                    | set(_fallback_repository_files(root))
                ),
                "git-index-plus-worktree",
            )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        pass
    return _fallback_repository_files(root), "filesystem-fallback"


def _python_bytes(root: Path, relative_root: str) -> int:
    base = root / relative_root
    if not base.is_dir():
        return 0
    return sum(
        path.stat().st_size
        for path in base.rglob("*.py")
        if path.is_file() and not path.is_symlink()
    )


def _validate_complexity(
    root: Path,
    program: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    budget = program.get("complexityBudget")
    if not isinstance(budget, dict):
        errors.append("program.complexityBudget must be an object")
        return {}
    targets = budget.get("targets")
    if not isinstance(targets, dict):
        errors.append("program.complexityBudget.targets must be an object")
        return {}

    files, inventory_source = _repository_files(root)
    harness_and_tests = _python_bytes(root, "harness") + _python_bytes(
        root, "tests/product"
    )
    control = root / "harness/control.py"
    control_bytes = control.stat().st_size if control.is_file() else 0
    instruction_paths = _string_list(budget.get("primaryInstructionPaths")) or []
    instruction_bytes = 0
    for locator in instruction_paths:
        path = _safe_file(root, locator, errors)
        if path is not None:
            instruction_bytes += path.stat().st_size

    metrics = {
        "inventorySource": inventory_source,
        "trackedFiles": len(files),
        "harnessAndProductTestBytes": harness_and_tests,
        "controlBytes": control_bytes,
        "primaryInstructionBytes": instruction_bytes,
    }
    target_map = {
        "maxTrackedFiles": "trackedFiles",
        "maxHarnessAndProductTestBytes": "harnessAndProductTestBytes",
        "maxControlBytes": "controlBytes",
        "maxPrimaryInstructionBytes": "primaryInstructionBytes",
    }
    for target_name, metric_name in target_map.items():
        limit = targets.get(target_name)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            errors.append(f"complexity target {target_name} must be a positive integer")
        elif metrics[metric_name] > limit:
            errors.append(
                f"complexity target exceeded: {metric_name}="
                f"{metrics[metric_name]} > {limit}"
            )

    forbidden = _string_list(budget.get("forbiddenActivePaths"))
    if forbidden is None:
        errors.append("program.complexityBudget.forbiddenActivePaths must be a string list")
    else:
        for index, locator in enumerate(forbidden):
            path = repository_relative_path(root, locator)
            if path is None:
                errors.append(
                    "program.complexityBudget.forbiddenActivePaths"
                    f"[{index}] is not a repository-relative path"
                )
            elif forbidden_path_present(path):
                errors.append(f"forbidden active path remains: {locator}")
    return metrics


def _validate_program(
    root: Path,
    program: dict[str, Any],
    criterion_ids: list[str],
    all_contract_ids: set[str],
    errors: list[str],
) -> None:
    if program.get("schema") != 2:
        errors.append("program.schema must be 2")
    for field in ("id", "productId", "release", "releaseIntent"):
        if not _nonempty_string(program.get(field)):
            errors.append(f"program.{field} must be a non-empty string")
    if program.get("constitution") != AUTHORITY_FILES[0]:
        errors.append("program.constitution locator is invalid")
    if program.get("acceptance") != AUTHORITY_FILES[2]:
        errors.append("program.acceptance locator is invalid")
    if program.get("status") not in PROGRAM_STATES:
        errors.append(f"program.status must be one of {sorted(PROGRAM_STATES)}")

    _validate_input_evidence(root, program, errors)
    increment = program.get("activeIncrement")
    if program.get("status") == "active":
        if not isinstance(increment, dict) or increment.get("state") != "active":
            errors.append("active program requires one activeIncrement")
        else:
            mapped = _string_list(increment.get("acceptanceIds"))
            if mapped is None or set(mapped) != set(criterion_ids):
                errors.append("activeIncrement.acceptanceIds must map every criterion exactly")
            for field in (
                "id",
                "observedProblem",
                "hypothesis",
                "finiteStopCondition",
            ):
                if not _nonempty_string(increment.get(field)):
                    errors.append(f"activeIncrement.{field} must be a non-empty string")
            falsifiers = _string_list(increment.get("falsifiers"))
            if not falsifiers:
                errors.append("activeIncrement.falsifiers must be non-empty")
            work_items = _object_entries(increment, "workItems", errors)
            _entry_ids(work_items, "activeIncrement.workItems", errors)
            active = [item for item in work_items if item.get("state") == "active"]
            if len(active) != 1:
                errors.append("activeIncrement must contain exactly one active work item")
            for index, item in enumerate(work_items):
                mapped_item = _string_list(item.get("acceptanceIds"))
                if mapped_item is None or not set(mapped_item).issubset(
                    set(criterion_ids)
                ):
                    errors.append(
                        f"activeIncrement.workItems[{index}].acceptanceIds is invalid"
                    )
    elif increment is not None:
        errors.append("non-active program must not carry activeIncrement")

    prompt = program.get("goalModePrompt")
    if not isinstance(prompt, dict):
        errors.append("program.goalModePrompt must be an object")
    else:
        if prompt.get("state") not in {
            "prepared-host-goal-paused",
            "active-in-host",
            "retired",
        }:
            errors.append("program.goalModePrompt.state is invalid")
        if not _nonempty_string(prompt.get("objective")):
            errors.append("program.goalModePrompt.objective must be non-empty")
        mapped = _string_list(prompt.get("mapsTo"))
        if mapped is None or set(mapped) != set(criterion_ids):
            errors.append("program.goalModePrompt.mapsTo must map every criterion exactly")
        triggers = _string_list(prompt.get("refreshTriggers"))
        if not triggers:
            errors.append("program.goalModePrompt.refreshTriggers must be non-empty")

    process = program.get("processLossControl")
    if not isinstance(process, dict):
        errors.append("program.processLossControl must be an object")
    else:
        for field in (
            "maxActiveIncrements",
            "maxActiveWorkItems",
            "samePurposeRepairBeforeReplan",
        ):
            if process.get(field) != 1:
                errors.append(f"program.processLossControl.{field} must be 1")
        if process.get("prohibitedAgentWorkTransfer") != 0:
            errors.append("program prohibits all avoidable Agent-work transfer")
        if process.get("taskResidueAtCheckpoint") != 0:
            errors.append("program requires zero task residue at checkpoints")

    projections = _object_entries(program, "hostProjections", errors)
    projection_ids = _entry_ids(projections, "hostProjections", errors)
    if len(projection_ids) < 2:
        errors.append("program.hostProjections must include at least two references")
    for index, projection in enumerate(projections):
        for field in ("manifest", "contract", "skill"):
            if not _nonempty_string(projection.get(field)):
                errors.append(f"hostProjections[{index}].{field} must be non-empty")
        if "marketplace" in projection and not _nonempty_string(
            projection.get("marketplace")
        ):
            errors.append(f"hostProjections[{index}].marketplace must be non-empty")
        if _string_list(projection.get("metadataFiles")) is None:
            errors.append(
                f"hostProjections[{index}].metadataFiles must be a string list"
            )
        forbidden = projection.get("forbiddenPaths")
        if _string_list(forbidden) is None:
            errors.append(f"hostProjections[{index}].forbiddenPaths must be a string list")
        markers = projection.get("requiredSkillMarkers")
        if not _string_list(markers):
            errors.append(
                f"hostProjections[{index}].requiredSkillMarkers must be non-empty"
            )
        max_bytes = projection.get("maxSkillBytes")
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            errors.append(f"hostProjections[{index}].maxSkillBytes must be positive")

    unknown_contract_ids = set(criterion_ids) - all_contract_ids
    if unknown_contract_ids:
        errors.append(f"program references unknown contract ids: {sorted(unknown_contract_ids)}")


def _validate_evidence_item(
    root: Path,
    item: dict[str, Any],
    label: str,
    errors: list[str],
    expected_evidence_class: str | None = None,
) -> dict[str, Any]:
    locator = item.get("locator")
    expected = item.get("sha256")
    path = _safe_file(root, locator, errors) if isinstance(locator, str) else None
    if not _nonempty_string(item.get("claim")):
        errors.append(f"{label}.claim must be a non-empty string")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        errors.append(f"{label}.sha256 is invalid")
    elif path is not None and _hash(path) != expected:
        errors.append(f"{label} digest mismatch")
    observation: dict[str, Any] = {}
    if path is not None:
        if path.suffix.lower() != ".json":
            errors.append(f"{label} direct evidence must be a JSON observation")
        else:
            observation = _read_json(root, locator, errors)
            if (
                expected_evidence_class is not None
                and observation.get("evidenceClass") != expected_evidence_class
            ):
                errors.append(
                    f"{label} evidenceClass does not match its criterion"
                )
    return observation


def _validate_acceptance(
    root: Path,
    acceptance: dict[str, Any],
    contract_ids: set[str],
    evidence_classes: set[str],
    runtime_release_authorization: dict[str, Any] | None,
    errors: list[str],
) -> tuple[list[str], bool, list[str], list[str]]:
    if acceptance.get("schema") != 2:
        errors.append("acceptance.schema must be 2")
    for field in ("id", "productId", "release"):
        if not _nonempty_string(acceptance.get(field)):
            errors.append(f"acceptance.{field} must be a non-empty string")
    if acceptance.get("constitution") != AUTHORITY_FILES[0]:
        errors.append("acceptance.constitution locator is invalid")
    if acceptance.get("program") != AUTHORITY_FILES[1]:
        errors.append("acceptance.program locator is invalid")

    criteria = _object_entries(acceptance, "criteria", errors)
    criterion_ids = _entry_ids(criteria, "criteria", errors)
    golden = _read_json(root, GOLDEN_TASKS_FILE, [])
    task_mappings = {
        task.get("id"): set(_string_list(task.get("mapsTo")) or [])
        for task in golden.get("tasks", [])
        if isinstance(task, dict) and _nonempty_string(task.get("id"))
    }
    verified = True
    for index, criterion in enumerate(criteria):
        label = f"criteria[{index}]"
        for field in ("class", "name", "statement", "passRule", "evidenceClass"):
            if not _nonempty_string(criterion.get(field)):
                errors.append(f"{label}.{field} must be a non-empty string")
        _validate_mapping(criterion, label, contract_ids, errors)
        if criterion.get("evidenceClass") not in evidence_classes:
            errors.append(f"{label}.evidenceClass is not declared by the constitution")
        assessment = criterion.get("assessment")
        if assessment not in ASSESSMENTS:
            errors.append(f"{label}.assessment must be one of {sorted(ASSESSMENTS)}")
        evidence = criterion.get("evidence")
        if not isinstance(evidence, list) or any(
            not isinstance(item, dict) for item in evidence
        ):
            errors.append(f"{label}.evidence must be a list of objects")
            evidence = []
        accepted_decision = False
        for evidence_index, item in enumerate(evidence):
            observation = _validate_evidence_item(
                root,
                item,
                f"{label}.evidence[{evidence_index}]",
                errors,
                criterion.get("evidenceClass"),
            )
            if assessment != "verified":
                continue
            accepted, decision_errors = criterion_observation_decision(
                criterion.get("id"),
                item,
                observation,
                task_mappings,
                f"{label}.evidence[{evidence_index}]",
            )
            accepted_decision |= accepted
            errors.extend(decision_errors)
        if assessment == "verified" and not evidence:
            errors.append(f"{label} is verified without direct evidence")
        elif assessment == "verified" and not accepted_decision:
            errors.append(
                f"{label} verified evidence lacks an accepted "
                f"{criterion.get('id')} decision"
            )
        if assessment != "verified":
            verified = False

    expression = acceptance.get("completionExpression")
    if not _nonempty_string(expression):
        errors.append("acceptance.completionExpression must be non-empty")
    else:
        operands = [part.strip() for part in expression.split("&&")]
        expected = set(criterion_ids) | {"namedHumanReleaseAuthorization"}
        if len(operands) != len(set(operands)) or set(operands) != expected:
            errors.append("acceptance.completionExpression does not map all criteria and authorization exactly")

    lanes = acceptance.get("evidenceLanes")
    if not isinstance(lanes, dict):
        errors.append("acceptance.evidenceLanes must be an object")
    else:
        required = _string_list(lanes.get("requiredForFiniteRelease"))
        continuing = _string_list(lanes.get("continuingAfterRelease"))
        if not required or not continuing or set(required) & set(continuing):
            errors.append("acceptance evidence lanes must be non-empty and disjoint")
        elif set(required) | set(continuing) != evidence_classes:
            errors.append("acceptance evidence lanes must partition constitution evidence classes")

    required_sample_ids: list[str] = []
    post_release_task_ids: list[str] = []
    representative_policy = acceptance.get("representativeBehaviorPolicy")
    if not isinstance(representative_policy, dict):
        errors.append("acceptance.representativeBehaviorPolicy must be an object")
    else:
        required_sample = _string_list(
            representative_policy.get("requiredTaskIdsForV12Release")
        )
        post_release = _string_list(representative_policy.get("postReleaseTasks"))
        if not required_sample:
            errors.append("representative release sample must not be empty")
        else:
            required_sample_ids = required_sample
            if len(required_sample_ids) != len(set(required_sample_ids)):
                errors.append("representative release sample contains duplicates")
        if post_release is None:
            errors.append("representative post-release tasks must be a string list")
            post_release = []
        else:
            post_release_task_ids = post_release
            if len(post_release_task_ids) != len(set(post_release_task_ids)):
                errors.append("representative post-release tasks contain duplicates")
        if set(required_sample_ids) & set(post_release):
            errors.append("representative release and post-release tasks must be disjoint")
        for field in (
            "sampleRationale",
            "taskDecisionRule",
            "releaseDecisionRule",
        ):
            if not _nonempty_string(representative_policy.get(field)):
                errors.append(
                    f"acceptance.representativeBehaviorPolicy.{field} "
                    "must be non-empty"
                )

    authorization = acceptance.get("releaseAuthorization")
    authorization_valid = False
    errors.extend(repository_release_authorization_errors(authorization))
    if runtime_release_authorization is not None:
        if isinstance(authorization, dict) and authorization.get("state") != "requested":
            errors.append(
                "runtime release authorization requires repository state requested"
            )
        authorization_valid = validate_runtime_release_authorization(
            root, runtime_release_authorization, errors
        )

    return (
        criterion_ids,
        verified and authorization_valid,
        required_sample_ids,
        post_release_task_ids,
    )


def _validate_representative_sample_evidence(
    root: Path,
    acceptance: dict[str, Any],
    required_task_ids: list[str],
    required_fields: list[str],
    errors: list[str],
) -> None:
    criteria = acceptance.get("criteria")
    if not isinstance(criteria, list):
        return
    representative = next(
        (
            criterion
            for criterion in criteria
            if isinstance(criterion, dict) and criterion.get("id") == "R3"
        ),
        None,
    )
    if not isinstance(representative, dict):
        errors.append("acceptance must contain representative criterion R3")
        return
    observed: dict[str, int] = {}
    nonterminal: list[str] = []
    evidence = representative.get("evidence")
    if not isinstance(evidence, list):
        return
    for index, item in enumerate(evidence):
        if not isinstance(item, dict) or not isinstance(item.get("locator"), str):
            continue
        local_errors: list[str] = []
        observation = _read_json(root, item["locator"], local_errors)
        if local_errors:
            continue
        missing_fields = [field for field in required_fields if field not in observation]
        if missing_fields:
            errors.append(f"R3 evidence[{index}] omits fields: {missing_fields}")
        task_id = observation.get("taskId")
        if not _nonempty_string(task_id):
            errors.append(f"R3 evidence[{index}] lacks taskId")
            continue
        if task_id in required_task_ids and not _nonempty_string(
            item.get("bindsProjection")
        ):
            errors.append(
                f"R3 evidence[{index}] required sample observation is not "
                "projection-bound"
            )
        decision = observation.get("decision")
        state = decision.get("state") if isinstance(decision, dict) else None
        if state not in {
            "passed",
            "failed",
            "failed-repeated-same-purpose",
            "candidate-pass-awaiting-human-review",
        }:
            errors.append(f"R3 evidence[{index}] lacks an explicit task decision")
        elif (
            representative.get("assessment") == "verified"
            and task_id in required_task_ids
            and state == "candidate-pass-awaiting-human-review"
        ):
            nonterminal.append(task_id)
        observed[task_id] = observed.get(task_id, 0) + 1
    missing = sorted(set(required_task_ids) - set(observed))
    if missing:
        errors.append(
            f"representative release sample missing task observations: {missing}"
        )
    ambiguous = sorted(
        task_id
        for task_id in required_task_ids
        if observed.get(task_id, 0) > 1
    )
    if ambiguous:
        errors.append(
            f"representative release sample has multiple current observations: "
            f"{ambiguous}"
        )
    if nonterminal:
        errors.append(
            f"R3 verified sample has nonterminal task decisions: "
            f"{sorted(nonterminal)}"
        )


def _validate_golden_tasks(
    root: Path,
    all_ids: set[str],
    kernel_host_lesson_ids: set[str],
    required_release_task_ids: list[str],
    post_release_task_ids: list[str],
    errors: list[str],
) -> dict[str, Any]:
    suite = _read_json(root, GOLDEN_TASKS_FILE, errors)
    if suite.get("schema") != 1:
        errors.append("golden tasks schema must be 1")
    protocol = suite.get("evaluationProtocol")
    if not isinstance(protocol, dict):
        errors.append("golden tasks evaluationProtocol must be an object")
        protocol = {}
    if protocol.get("staticSuiteIsNotBehaviorEvidence") is not True:
        errors.append("golden tasks must reject static-suite-as-behavior-evidence")
    if not _nonempty_string(protocol.get("taskFailureRule")):
        errors.append("golden tasks must define how task failure limits claims")
    required_fields = _string_list(protocol.get("requiredObservationFields")) or []
    if not required_fields:
        errors.append("golden tasks must define required observation fields")
    tasks = _object_entries(suite, "tasks", errors)
    task_ids = _entry_ids(tasks, "golden tasks", errors)
    kinds: set[str] = set()
    coverage: set[str] = set()
    for index, task in enumerate(tasks):
        label = f"golden tasks[{index}]"
        for field in ("name", "kind", "prompt", "startingState"):
            if not _nonempty_string(task.get(field)):
                errors.append(f"{label}.{field} must be a non-empty string")
        kinds.add(task.get("kind", ""))
        _validate_mapping(task, label, all_ids, errors)
        coverage.update(_string_list(task.get("mapsTo")) or [])
        if not _string_list(task.get("required")):
            errors.append(f"{label}.required must be non-empty")
        if not _string_list(task.get("prohibited")):
            errors.append(f"{label}.prohibited must be non-empty")
    if "help" not in kinds or "non-interference" not in kinds:
        errors.append("golden tasks must include help and non-interference cases")
    missing = sorted(kernel_host_lesson_ids - coverage)
    if missing:
        errors.append(f"golden tasks do not cover contract ids: {missing}")
    declared_partition = set(required_release_task_ids) | set(post_release_task_ids)
    unknown_required = sorted(declared_partition - set(task_ids))
    if unknown_required:
        errors.append(
            f"representative policy names unknown tasks: {unknown_required}"
        )
    omitted = sorted(set(task_ids) - declared_partition)
    if omitted:
        errors.append(
            f"representative policy does not classify golden tasks: {omitted}"
        )
    return {
        "id": suite.get("id"),
        "tasks": len(task_ids),
        "kinds": sorted(kind for kind in kinds if kind),
        "requiredObservationFields": required_fields,
        "behaviorEvidence": "not-established-by-static-suite",
    }


def _validate_projection(
    root: Path,
    projection: dict[str, Any],
    contract_ids: dict[str, list[str]],
    errors: list[str],
) -> dict[str, Any]:
    initial_error_count = len(errors)
    adapter_id = projection.get("id")
    manifest_locator = projection.get("manifest")
    marketplace_locator = projection.get("marketplace")
    contract_locator = projection.get("contract")
    skill_locator = projection.get("skill")
    metadata_locators = _string_list(projection.get("metadataFiles")) or []
    manifest = (
        _read_json(root, manifest_locator, errors)
        if isinstance(manifest_locator, str)
        else {}
    )
    contract = (
        _read_json(root, contract_locator, errors)
        if isinstance(contract_locator, str)
        else {}
    )
    skill_path = (
        _safe_file(root, skill_locator, errors)
        if isinstance(skill_locator, str)
        else None
    )
    if not _nonempty_string(manifest.get("name")):
        errors.append(f"adapter {adapter_id} manifest name must be non-empty")
    errors.extend(manifest_shape_errors(adapter_id, manifest))
    if isinstance(marketplace_locator, str):
        marketplace = _read_json(root, marketplace_locator, errors)
        expected_path = (
            f"./{Path(manifest_locator).parent.parent.as_posix()}"
            if isinstance(manifest_locator, str)
            else None
        )
        errors.extend(
            marketplace_errors(
                adapter_id, marketplace, manifest.get("name"), expected_path
            )
        )
    if contract.get("schema") != 1:
        errors.append(f"adapter {adapter_id} contract schema must be 1")
    if contract.get("adapterId") != adapter_id:
        errors.append(f"adapter {adapter_id} contract identity mismatch")
    expected_fields = {
        "kernelIds": contract_ids["kernel"],
        "hostStandardIds": contract_ids["host"],
        "learnedFailureIds": contract_ids["lessons"],
    }
    for field, expected in expected_fields.items():
        if contract.get(field) != expected:
            errors.append(f"adapter {adapter_id} {field} does not match constitution order")
    if contract.get("goldenTasks") != GOLDEN_TASKS_FILE:
        errors.append(f"adapter {adapter_id} goldenTasks locator is invalid")
    if contract.get("runtimeAdded") is not False:
        errors.append(f"adapter {adapter_id} must not add a runtime")
    if contract.get("requiresFixedHostVersion") is not False:
        errors.append(f"adapter {adapter_id} must not require a fixed host version")
    behavior_state = contract.get("behaviorEvidenceState")
    if behavior_state not in {"unverified", "observed"}:
        errors.append(f"adapter {adapter_id} behaviorEvidenceState is invalid")
    elif behavior_state == "observed":
        evidence = contract.get("behaviorEvidence")
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(item, dict) for item in evidence
        ):
            errors.append(
                f"adapter {adapter_id} observed behavior lacks direct evidence"
            )
        else:
            for index, item in enumerate(evidence):
                _validate_evidence_item(
                    root,
                    item,
                    f"adapter {adapter_id} behaviorEvidence[{index}]",
                    errors,
                )

    skill_bytes = 0
    if skill_path is not None:
        skill_bytes = skill_path.stat().st_size
        max_bytes = projection.get("maxSkillBytes")
        if isinstance(max_bytes, int) and skill_bytes > max_bytes:
            errors.append(
                f"adapter {adapter_id} Skill exceeds budget: {skill_bytes} > {max_bytes}"
            )
        try:
            skill_text = skill_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"adapter {adapter_id} Skill is unreadable: {exc}")
            skill_text = ""
        markers = _string_list(projection.get("requiredSkillMarkers")) or []
        for marker in markers:
            if marker not in skill_text:
                errors.append(f"adapter {adapter_id} Skill omits marker {marker}")

    package_digest, package_errors = validate_projection_package(
        root,
        adapter_id,
        manifest_locator,
        contract_locator,
        skill_locator,
        metadata_locators,
    )
    errors.extend(package_errors)

    forbidden = _string_list(projection.get("forbiddenPaths")) or []
    for index, locator in enumerate(forbidden):
        path = repository_relative_path(root, locator)
        if path is None:
            errors.append(
                f"adapter {adapter_id} forbiddenPaths[{index}] is not a "
                "repository-relative path"
            )
        elif forbidden_path_present(path):
            errors.append(f"adapter {adapter_id} forbidden path remains: {locator}")

    identity: dict[str, str] = {}
    for field, locator in (
        ("manifestSha256", manifest_locator),
        ("marketplaceSha256", marketplace_locator),
        ("contractSha256", contract_locator),
        ("skillSha256", skill_locator),
    ):
        if isinstance(locator, str):
            path = _safe_file(root, locator, [])
            if path is not None:
                identity[field] = _hash(path)
    if package_digest is not None:
        identity["packageSha256"] = package_digest
    return {
        "id": adapter_id,
        "staticReady": len(errors) == initial_error_count,
        "behaviorEvidenceState": behavior_state,
        "skillBytes": skill_bytes,
        "manifest": manifest_locator,
        "marketplace": marketplace_locator,
        "contract": contract_locator,
        "skill": skill_locator,
        "metadataFiles": metadata_locators,
        "identity": identity,
    }


def host_check(root: Path, adapter_id: str) -> dict[str, Any]:
    product_report = verify_product(Path(root))
    errors = list(product_report["errors"])
    details = product_report["hostChecks"].get(adapter_id)
    if details is None:
        errors.append(f"unknown host projection: {adapter_id}")
        details = {"id": adapter_id}
    return {
        "adapter": adapter_id,
        "valid": not errors,
        "staticReady": not errors and details.get("staticReady") is True,
        "behaviorEvidenceState": details.get(
            "behaviorEvidenceState", "unverified"
        ),
        "claim": "static host-admission conformance only",
        "details": details,
        "errors": errors,
    }


def verify_product(
    root: Path,
    release_authorization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root)
    errors: list[str] = []
    constitution = _read_json(root, AUTHORITY_FILES[0], errors)
    program = _read_json(root, AUTHORITY_FILES[1], errors)
    acceptance = _read_json(root, AUTHORITY_FILES[2], errors)

    contract_ids = _validate_constitution(constitution, errors)
    kernel_host_lesson_ids = set(
        contract_ids["kernel"] + contract_ids["host"] + contract_ids["lessons"]
    )
    evidence_boundary = constitution.get("evidenceBoundary")
    evidence_classes = set(
        _string_list(evidence_boundary.get("classes"))
        if isinstance(evidence_boundary, dict)
        and _string_list(evidence_boundary.get("classes")) is not None
        else []
    )
    (
        criterion_ids,
        release_complete,
        required_release_task_ids,
        post_release_task_ids,
    ) = _validate_acceptance(
        root,
        acceptance,
        kernel_host_lesson_ids,
        evidence_classes,
        release_authorization,
        errors,
    )
    all_ids = kernel_host_lesson_ids | set(criterion_ids)
    _validate_program(root, program, criterion_ids, all_ids, errors)
    golden = _validate_golden_tasks(
        root,
        all_ids,
        kernel_host_lesson_ids,
        required_release_task_ids,
        post_release_task_ids,
        errors,
    )

    host_reports: dict[str, Any] = {}
    projections = program.get("hostProjections")
    if isinstance(projections, list):
        for projection in projections:
            if not isinstance(projection, dict) or not _nonempty_string(
                projection.get("id")
            ):
                continue
            local_errors: list[str] = []
            details = _validate_projection(
                root,
                projection,
                contract_ids,
                local_errors,
            )
            errors.extend(local_errors)
            host_reports[projection["id"]] = {
                **details,
                "errors": local_errors,
            }

    errors.extend(
        projection_evidence_binding_errors(
            root, acceptance, host_reports, _read_json
        )
    )
    _validate_representative_sample_evidence(
        root,
        acceptance,
        required_release_task_ids,
        golden.get("requiredObservationFields", []),
        errors,
    )

    complexity = _validate_complexity(root, program, errors)
    residue = known_task_residue(root)
    if residue:
        errors.append(f"known task residue remains: {residue}")
    verified_count = sum(
        1
        for criterion in acceptance.get("criteria", [])
        if isinstance(criterion, dict) and criterion.get("assessment") == "verified"
    )
    completion = (
        release_complete
        and program.get("status") in {"ready", "released"}
        and program.get("activeIncrement") is None
        and not errors
    )
    return {
        "productId": constitution.get("productId"),
        "release": program.get("release"),
        "programStatus": program.get("status"),
        "contractValid": not errors,
        "releaseComplete": completion,
        "completionState": "complete" if completion else "incomplete",
        "criteria": {
            "verified": verified_count,
            "total": len(criterion_ids),
            "ids": criterion_ids,
        },
        "goalModePromptState": (
            program.get("goalModePrompt", {}).get("state")
            if isinstance(program.get("goalModePrompt"), dict)
            else None
        ),
        "goldenTasks": golden,
        "hostChecks": host_reports,
        "complexity": complexity,
        "valid": not errors,
        "errors": errors,
    }


__all__ = ["host_check", "verify_product"]
