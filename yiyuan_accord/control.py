from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from .evidence import historical_representative_errors, representative_sample_errors
from .guardrails import (
    EXTERNAL_COMPLETION_OPERANDS,
    clean_git_checkout,
    closeout_sequence_errors,
    criterion_observation_decision,
    external_release_contract_errors,
    forbidden_path_present,
    known_task_residue,
    projection_evidence_binding_errors,
    release_procedure_errors,
    repository_relative_path,
    validate_host_projection,
)
from .identity import (
    _bounded_git_bytes,
    _bounded_regular_bytes,
    _nonempty_string,
    _string_list,
    active_tree_errors,
    authority_contract_errors,
    domain_model_errors,
    identity_contract_errors,
    module_layout_errors,
    operating_model_errors,
    release_identity_errors,
)


AUTHORITY_BOOTSTRAP = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
)
GOLDEN_TASKS_FILE = "evals/golden-tasks.json"
MAX_JSON_BYTES = 1_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
ASSESSMENTS = {"planned", "verified", "blocked", "continuing"}
PROGRAM_STATES = {"active", "ready", "blocked"}


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError(f"non-finite JSON number: {value}")


def _safe_file(root, locator, errors):
    candidate = repository_relative_path(root, locator)
    if candidate is None:
        errors.append(f"invalid repository locator: {locator!r}")
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        errors.append(f"missing repository file {locator}: {exc}")
        return None
    if not resolved.is_file() or candidate.is_symlink():
        errors.append(f"repository locator is not a regular owned file: {locator}")
        return None
    return resolved


def _read_json(root, locator, errors):
    path = _safe_file(root, locator, errors)
    if path is None:
        return {}
    try:
        raw, read_state = _bounded_regular_bytes(path)
        if read_state == "oversized":
            raise ValueError(f"JSON exceeds {MAX_JSON_BYTES} bytes")
        if read_state is not None:
            raise ValueError(f"JSON source is {read_state}")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("top-level JSON value is not an object")
        return value
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"invalid JSON {locator}: {exc}")
        return {}


def _hash(path, errors, label):
    raw, read_state = _bounded_regular_bytes(path)
    if read_state is not None:
        errors.append(f"{label} digest source is {read_state}")
        return None
    return sha256(raw).hexdigest()


def _object_entries(owner, field, errors):
    value = owner.get(field)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        errors.append(f"{field} must be a list of objects")
        return []
    if not value:
        errors.append(f"{field} must not be empty")
    return value


def _entry_ids(entries, label, errors):
    ids = []
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


def _validate_mapping(entry, label, allowed, errors):
    mapped = _string_list(entry.get("mapsTo"))
    if not mapped:
        errors.append(f"{label}.mapsTo must be a non-empty string list")
        return
    unknown = sorted(set(mapped) - allowed)
    if unknown:
        errors.append(f"{label}.mapsTo contains unknown ids: {unknown}")


def _require_texts(owner, fields, label, errors):
    errors.extend(
        f"{label}.{field} must be a non-empty string"
        for field in fields if not _nonempty_string(owner.get(field))
    )


def _validate_constitution(constitution, errors):
    if constitution.get("schema") != 3:
        errors.append("constitution.schema must be 3")
    _require_texts(constitution, ("id", "productId", "purpose", "successDefinition"),
                   "constitution", errors)
    identity = constitution.get("identity")
    errors.extend(identity_contract_errors(constitution.get("productId"), identity))
    if not isinstance(identity, dict):
        identity = {}

    domain = constitution.get("domainModel")
    errors.extend(domain_model_errors(domain))
    errors.extend(operating_model_errors(constitution))

    kernel = _object_entries(constitution, "kernel", errors)
    hosts = _object_entries(constitution, "hostAdapterStandard", errors)
    lessons = _object_entries(constitution, "learnedFailureStandards", errors)
    kernel_ids = _entry_ids(kernel, "kernel", errors)
    host_ids = _entry_ids(hosts, "hostAdapterStandard", errors)
    lesson_ids = _entry_ids(lessons, "learnedFailureStandards", errors)

    for index, entry in enumerate(kernel):
        _require_texts(entry, ("name", "commitment"), f"kernel[{index}]", errors)
    for label, entries in (
        ("hostAdapterStandard", hosts),
        ("learnedFailureStandards", lessons),
    ):
        for index, entry in enumerate(entries):
            _require_texts(entry, ("rule",), f"{label}[{index}]", errors)
            _validate_mapping(
                entry,
                f"{label}[{index}]",
                set(kernel_ids),
                errors,
            )

    invariants = _string_list(constitution.get("qualityInvariants"))
    if not invariants:
        errors.append("constitution.qualityInvariants must be non-empty")

    return {
        "kernel": kernel_ids,
        "host": host_ids,
        "lessons": lesson_ids,
        "identity": identity,
    }


def _validate_input_evidence(root, program, errors):
    inputs = _object_entries(program, "inputEvidence", errors)
    _entry_ids(inputs, "inputEvidence", errors)
    for index, item in enumerate(inputs):
        locator = item.get("repositoryLocator")
        if locator is not None:
            path = _safe_file(root, locator, errors)
            expected = item.get("repositorySha256")
            if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
                errors.append(f"inputEvidence[{index}].repositorySha256 is invalid")
            elif path is not None:
                actual = _hash(path, errors, f"inputEvidence[{index}]")
                if actual is not None and actual != expected:
                    errors.append(f"inputEvidence[{index}] repository digest mismatch")
        revision = item.get("revision")
        if revision is not None and (
            not isinstance(revision, str) or not REVISION_RE.fullmatch(revision)
        ):
            errors.append(f"inputEvidence[{index}].revision is not an exact Git revision")


def _repository_files(root):
    try:
        output = _bounded_git_bytes(root, ("ls-files", "--stage", "-z"))
        files, errors = set(), set()
        for raw_record in output.split(b"\0"):
            if not raw_record:
                continue
            record = raw_record.decode("utf-8")
            metadata, separator, locator = record.partition("\t")
            fields = metadata.split()
            if not separator or not locator or len(fields) != 3:
                raise ValueError("invalid Git index record")
            mode, _object_id, stage = fields
            if stage != "0":
                errors.add(
                    f"tracked repository entry is unmerged: {locator} (stage {stage})"
                )
            elif mode in {"100644", "100755"}:
                files.add(locator)
            elif mode == "120000":
                errors.add(
                    "symbolic link is not admitted in tracked repository surface: "
                    f"{locator} (mode {mode})"
                )
            else:
                errors.add(
                    "tracked repository entry is not a regular file: "
                    f"{locator} (mode {mode})"
                )
        return sorted(files), sorted(errors)
    except (OSError, ValueError, subprocess.SubprocessError, UnicodeError):
        return [], ["tracked repository surface is unavailable"]


def _python_bytes(root, relative_root):
    base = root / relative_root
    if not base.is_dir():
        return 0
    return sum(
        path.stat().st_size
        for path in base.rglob("*.py")
        if path.is_file() and not path.is_symlink()
    )


def _validate_complexity(root, program, python_module, files, errors):
    budget = program.get("complexityBudget")
    if not isinstance(budget, dict):
        errors.append("program.complexityBudget must be an object")
        return {}
    targets = budget.get("targets")
    if not isinstance(targets, dict):
        errors.append("program.complexityBudget.targets must be an object")
        return {}
    headroom_percent = budget.get("minimumProductCodeAndTestHeadroomPercent")
    valid_headroom = (
        isinstance(headroom_percent, int) and not isinstance(headroom_percent, bool)
        and 5 <= headroom_percent <= 50
    )
    if not valid_headroom:
        errors.append(
            "minimumProductCodeAndTestHeadroomPercent must be an integer from 5 to 50"
        )

    errors.extend(module_layout_errors(
        root, python_module, Path(__file__).resolve().parent.name,
        _string_list(budget.get("requiredTestMarkers")),
        budget.get("minimumTestCount"),
    ))

    product_code_and_tests = _python_bytes(root, python_module) + _python_bytes(
        root, "tests/product"
    )
    instruction_paths = _string_list(budget.get("primaryInstructionPaths"))
    if not instruction_paths:
        errors.append("primaryInstructionPaths must be non-empty")
    instruction_bytes = len(
        str(program.get("goalModePrompt", {}).get("objective", "")).encode("utf-8")
    )
    for locator in instruction_paths or []:
        path = _safe_file(root, locator, errors)
        if path is not None:
            instruction_bytes += path.stat().st_size

    if not isinstance(budget.get("digestBoundBinaryAssets"), dict):
        errors.append("program.complexityBudget.digestBoundBinaryAssets must be an object")

    metrics = {
        "trackedFiles": len(files),
        "productCodeAndTestBytes": product_code_and_tests,
        "primaryInstructionBytes": instruction_bytes,
    }
    for metric_name, measured in metrics.items():
        target_name = f"max{metric_name[0].upper()}{metric_name[1:]}"
        limit = targets.get(target_name)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            errors.append(f"complexity target {target_name} must be a positive integer")
        elif measured > limit:
            errors.append(
                f"complexity target exceeded: {metric_name}="
                f"{measured} > {limit}"
            )
        elif metric_name == "productCodeAndTestBytes" and valid_headroom:
            required = (limit * headroom_percent + 99) // 100
            if limit - measured < required:
                errors.append(
                    "complexity headroom too small: productCodeAndTestBytes="
                    f"{measured}, limit={limit}, required={required}"
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


def _validate_four_surface_mapping(increment, criterion_ids, errors):
    outcome = increment.get("representativeOutcome")
    outcome_fields = {
        "id", "statement", "startingState", "completion", "claimLimit",
        "firstEvidenceSurfaces",
    }
    if not isinstance(outcome, dict) or set(outcome) != outcome_fields:
        errors.append("increment.representativeOutcome shape is invalid")
        return
    _require_texts(
        outcome,
        ("id", "statement", "startingState", "completion", "claimLimit"),
        "increment.representativeOutcome",
        errors,
    )
    if not _string_list(outcome.get("firstEvidenceSurfaces")):
        errors.append("increment.representativeOutcome firstEvidenceSurfaces is invalid")

    mapping = increment.get("fourSurfaceMapping")
    if not isinstance(mapping, dict) or set(mapping) != {
        "outcomeId", "plan", "process", "acceptance", "goalMode",
    }:
        errors.append("increment.fourSurfaceMapping shape is invalid")
        return
    if mapping.get("outcomeId") != outcome.get("id"):
        errors.append("increment.fourSurfaceMapping outcomeId does not match")

    plan = mapping.get("plan")
    if not isinstance(plan, dict) or set(plan) != {
        "hypothesis", "earliestAffectedBoundary", "slice", "stopCondition",
    }:
        errors.append("increment.fourSurfaceMapping.plan shape is invalid")
    else:
        _require_texts(
            plan,
            ("hypothesis", "earliestAffectedBoundary", "slice", "stopCondition"),
            "increment.fourSurfaceMapping.plan",
            errors,
        )

    process = mapping.get("process")
    if not isinstance(process, dict) or set(process) != {
        "routeRule", "phases", "orderedSteps", "degradationRule",
    }:
        errors.append("increment.fourSurfaceMapping.process shape is invalid")
    else:
        _require_texts(
            process, ("routeRule", "degradationRule"),
            "increment.fourSurfaceMapping.process", errors,
        )
        if not _string_list(process.get("phases")):
            errors.append("increment.fourSurfaceMapping.process phases are invalid")
        ordered = process.get("orderedSteps")
        if not isinstance(ordered, list) or not ordered:
            errors.append("increment.fourSurfaceMapping.process orderedSteps are invalid")
        else:
            seen, states = [], []
            allowed = set(criterion_ids) - {"R4"}
            for index, step in enumerate(ordered):
                label = f"increment.fourSurfaceMapping.process.orderedSteps[{index}]"
                if not isinstance(step, dict) or set(step) != {
                    "id", "state", "dependsOn", "acceptanceIds", "completion",
                }:
                    errors.append(f"{label} shape is invalid")
                    continue
                _require_texts(step, ("id", "completion"), label, errors)
                state = step.get("state")
                if state not in {"completed", "active", "pending", "blocked"}:
                    errors.append(f"{label}.state is invalid")
                states.append(state)
                if step.get("id") in seen:
                    errors.append(f"{label}.id is duplicated")
                expected_dependency = [] if index == 0 else [seen[-1]]
                if step.get("dependsOn") != expected_dependency:
                    errors.append(f"{label}.dependsOn must name only the previous step")
                mapped_step = _string_list(step.get("acceptanceIds"))
                if not mapped_step or not set(mapped_step).issubset(allowed):
                    errors.append(f"{label}.acceptanceIds are invalid")
                if _nonempty_string(step.get("id")):
                    seen.append(step["id"])
            current_state = increment.get("state")
            current = [
                index for index, state in enumerate(states)
                if state == current_state
            ]
            if current_state == "completed":
                expected_states = ["completed"] * len(states)
            elif current_state in {"active", "blocked"} and len(current) == 1:
                current_index = current[0]
                expected_states = (
                    ["completed"] * current_index + [current_state]
                    + ["pending"] * (len(states) - current_index - 1)
                )
            else:
                expected_states = None
                errors.append(
                    "increment.fourSurfaceMapping.process orderedSteps current state is invalid"
                )
            if expected_states is not None and states != expected_states:
                errors.append(
                    "increment.fourSurfaceMapping.process orderedSteps lifecycle is invalid"
                )

    acceptance = mapping.get("acceptance")
    if not isinstance(acceptance, dict) or set(acceptance) != {
        "criterionIds", "requiredObservations", "passRule",
    }:
        errors.append("increment.fourSurfaceMapping.acceptance shape is invalid")
    else:
        expected = set(criterion_ids) - {"R4"}
        mapped = _string_list(acceptance.get("criterionIds"))
        if mapped is None or set(mapped) != expected:
            errors.append("increment.fourSurfaceMapping.acceptance criterionIds are invalid")
        if not _string_list(acceptance.get("requiredObservations")):
            errors.append("increment.fourSurfaceMapping.acceptance observations are invalid")
        _require_texts(
            acceptance, ("passRule",),
            "increment.fourSurfaceMapping.acceptance", errors,
        )

    goal_mode = mapping.get("goalMode")
    if not isinstance(goal_mode, dict) or set(goal_mode) != {
        "directive", "completion", "pauseOnlyFor",
    }:
        errors.append("increment.fourSurfaceMapping.goalMode shape is invalid")
    else:
        _require_texts(
            goal_mode, ("directive", "completion"),
            "increment.fourSurfaceMapping.goalMode", errors,
        )
        if not _string_list(goal_mode.get("pauseOnlyFor")):
            errors.append("increment.fourSurfaceMapping.goalMode pauseOnlyFor is invalid")


def _validate_program(
    root, program, criterion_ids, all_contract_ids, identity, authority,
    goal_digest, required_task_ids, errors,
):
    if program.get("schema") != 3:
        errors.append("program.schema must be 3")
    _require_texts(program, ("id", "productId", "releaseIntent", "maintenancePlan"),
                   "program", errors)
    if program.get("constitution") != AUTHORITY_BOOTSTRAP[0]:
        errors.append("program.constitution locator is invalid")
    if program.get("acceptance") != AUTHORITY_BOOTSTRAP[2]:
        errors.append("program.acceptance locator is invalid")
    if program.get("status") not in PROGRAM_STATES:
        errors.append(f"program.status must be one of {sorted(PROGRAM_STATES)}")

    _validate_input_evidence(root, program, errors)
    work_items = []
    increment = program.get("increment")
    program_state = program.get("status")
    allowed_increment_states = {
        "active": {"active", "completed"},
        "ready": {"completed"},
        "blocked": {"blocked"},
    }.get(program_state, set())
    increment_state = increment.get("state") if isinstance(increment, dict) else None
    if increment_state not in allowed_increment_states:
        errors.append("program.increment does not match program status")
    else:
        mapped = _string_list(increment.get("acceptanceIds"))
        if mapped is None or set(mapped) != set(criterion_ids):
            errors.append("increment.acceptanceIds must map every criterion exactly")
        _require_texts(increment, ("id", "observedProblem", "hypothesis", "finiteStopCondition"),
                       "increment", errors)
        _validate_four_surface_mapping(increment, set(criterion_ids), errors)
        if not _string_list(increment.get("falsifiers")):
            errors.append("increment.falsifiers must be non-empty")
        work_items = _object_entries(increment, "workItems", errors)
        _entry_ids(work_items, "increment.workItems", errors)
        if len(work_items) != 1 or work_items[0].get("state") != increment_state:
            errors.append("increment must retain one work item matching its lifecycle")
        for index, item in enumerate(work_items):
            mapped_item = _string_list(item.get("acceptanceIds"))
            if (
                mapped_item is None or set(mapped_item) != set(criterion_ids)
            ):
                errors.append(f"increment.workItems[{index}].acceptanceIds is invalid")
            errors.extend(closeout_sequence_errors(item, set(criterion_ids)))

    prompt = program.get("goalModePrompt")
    errors.extend(release_procedure_errors(
        root, program, authority, set(criterion_ids), prompt, goal_digest,
        required_task_ids,
    ))
    if not isinstance(prompt, dict):
        errors.append("program.goalModePrompt must be an object")
    else:
        if set(prompt) != {
            "state", "authority", "objective", "releaseGateIds", "workStageIds",
            "mapsTo", "refreshTriggers", "hostLifecycleNote",
        }:
            errors.append("program.goalModePrompt shape is invalid")
        if prompt.get("state") not in {
            "prepared-host-goal-paused",
            "active-in-host",
            "retired",
        }:
            errors.append("program.goalModePrompt.state is invalid")
        goal_states = {
            "active": {"prepared-host-goal-paused", "active-in-host"},
            "blocked": {"prepared-host-goal-paused"},
            "completed": {"retired"},
        }.get(increment_state, set())
        if prompt.get("state") not in goal_states:
            errors.append("program.goalModePrompt does not match increment lifecycle")
        _require_texts(prompt, ("authority", "objective", "hostLifecycleNote"),
                       "program.goalModePrompt", errors)
        mapped = _string_list(prompt.get("mapsTo"))
        if mapped is None or set(mapped) != set(criterion_ids):
            errors.append("program.goalModePrompt.mapsTo must map every criterion exactly")
        triggers = _string_list(prompt.get("refreshTriggers"))
        if not triggers:
            errors.append("program.goalModePrompt.refreshTriggers must be non-empty")
        stages = work_items[0].get("closeoutSequence", []) if len(work_items) == 1 else []
        if prompt.get("workStageIds") != [
            stage.get("id") for stage in stages if isinstance(stage, dict)
        ]:
            errors.append("program.goalModePrompt.workStageIds must match closeoutSequence")

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
    package_ids = []
    for index, projection in enumerate(projections):
        _require_texts(projection, ("packageId", "packageVersion", "manifest", "contract", "skill"),
                       f"hostProjections[{index}]", errors)
        if not isinstance(projection.get("packageSha256"), str) or not SHA256_RE.fullmatch(
            projection["packageSha256"]
        ):
            errors.append(f"hostProjections[{index}].packageSha256 is invalid")
        if _nonempty_string(projection.get("packageId")):
            package_ids.append(projection["packageId"])
        if "marketplace" in projection and not _nonempty_string(projection.get("marketplace")):
            errors.append(f"hostProjections[{index}].marketplace must be non-empty")
        for field in ("metadataFiles", "mechanismFiles", "forbiddenPaths"):
            if _string_list(projection.get(field)) is None:
                errors.append(f"hostProjections[{index}].{field} must be a string list")
        if not _nonempty_string(projection.get("activationContext")):
            errors.append(
                f"hostProjections[{index}].activationContext must be non-empty"
            )
        if projection.get("id") == "codex" and not _string_list(projection.get("interfaceDefaultPrompt")):
            errors.append("hostProjections codex interfaceDefaultPrompt must be non-empty")
        markers = projection.get("requiredSkillMarkers")
        if not _string_list(markers):
            errors.append(f"hostProjections[{index}].requiredSkillMarkers must be non-empty")
        max_bytes = projection.get("maxSkillBytes")
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            errors.append(f"hostProjections[{index}].maxSkillBytes must be positive")
    expected_package_ids = _string_list(identity.get("pluginIds")) or []
    if len(package_ids) != len(set(package_ids)) or set(package_ids) != set(expected_package_ids):
        errors.append("program host projection packages do not match product identity")

    unknown_contract_ids = set(criterion_ids) - all_contract_ids
    if unknown_contract_ids:
        errors.append(f"program references unknown contract ids: {sorted(unknown_contract_ids)}")


def _validate_evidence_item(
    root, item, label, errors, expected_evidence_classes=None,
):
    locator = item.get("locator")
    expected = item.get("sha256")
    path = _safe_file(root, locator, errors) if isinstance(locator, str) else None
    if not _nonempty_string(item.get("claim")):
        errors.append(f"{label}.claim must be a non-empty string")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        errors.append(f"{label}.sha256 is invalid")
    elif path is not None:
        actual = _hash(path, errors, label)
        if actual is not None and actual != expected:
            errors.append(f"{label} digest mismatch")
    observation = {}
    if path is not None:
        if Path(locator).parts[:2] != ("evals", "observations"):
            errors.append(f"{label} direct evidence must use evals/observations")
        if path.suffix.lower() != ".json":
            errors.append(f"{label} direct evidence must be a JSON observation")
        else:
            observation = _read_json(root, locator, errors)
            if observation.get("evidenceClass") == "deterministic-conformance":
                errors.append(
                    f"{label} deterministic conformance is computed live, not accepted from repository observations"
                )
            if (
                expected_evidence_classes is not None
                and observation.get("evidenceClass") not in expected_evidence_classes
            ):
                errors.append(
                    f"{label} evidenceClass is not required by its criterion"
                )
    return observation


def _validate_acceptance(root, acceptance, contract_ids, evidence_classes, golden, errors):
    if acceptance.get("schema") != 3:
        errors.append("acceptance.schema must be 3")
    _require_texts(acceptance, ("id", "productId"), "acceptance", errors)
    if acceptance.get("constitution") != AUTHORITY_BOOTSTRAP[0]:
        errors.append("acceptance.constitution locator is invalid")
    if acceptance.get("program") != AUTHORITY_BOOTSTRAP[1]:
        errors.append("acceptance.program locator is invalid")

    criteria = _object_entries(acceptance, "criteria", errors)
    criterion_ids = _entry_ids(criteria, "criteria", errors)
    task_mappings = {
        task.get("id"): set(_string_list(task.get("mapsTo")) or [])
        for task in golden.get("tasks", [])
        if isinstance(task, dict) and _nonempty_string(task.get("id"))
    }
    verified = True
    declared_classes = set()
    for index, criterion in enumerate(criteria):
        label = f"criteria[{index}]"
        _require_texts(criterion, ("class", "name", "statement", "passRule"), label, errors)
        _validate_mapping(criterion, label, contract_ids, errors)
        required_classes = _string_list(criterion.get("requiredEvidenceClasses"))
        if (
            not required_classes or not set(required_classes).issubset(evidence_classes)
        ):
            errors.append(f"{label}.requiredEvidenceClasses is invalid")
            required_classes = []
        declared_classes.update(required_classes)
        assessment = criterion.get("assessment")
        if assessment not in ASSESSMENTS:
            errors.append(f"{label}.assessment must be one of {sorted(ASSESSMENTS)}")
        evidence = criterion.get("evidence")
        if not isinstance(evidence, list) or any(
            not isinstance(item, dict) for item in evidence
        ):
            errors.append(f"{label}.evidence must be a list of objects")
            evidence = []
        required_class_set = set(required_classes)
        stored_classes = required_class_set - {"deterministic-conformance"}
        accepted_classes = required_class_set - stored_classes
        for evidence_index, item in enumerate(evidence):
            observation = _validate_evidence_item(
                root,
                item,
                f"{label}.evidence[{evidence_index}]",
                errors,
                stored_classes,
            )
            accepted, decision_errors = criterion_observation_decision(
                criterion.get("id"),
                item,
                observation,
                task_mappings,
                f"{label}.evidence[{evidence_index}]",
            )
            if accepted and isinstance(observation.get("evidenceClass"), str):
                accepted_classes.add(observation["evidenceClass"])
            errors.extend(decision_errors)
        if assessment == "verified" and stored_classes and not evidence:
            errors.append(f"{label} is verified without direct evidence")
        elif assessment == "verified" and accepted_classes != required_class_set:
            errors.append(f"{label} verified evidence does not satisfy every required lane")
        if assessment != "verified":
            verified = False

    expression = acceptance.get("completionExpression")
    if not _nonempty_string(expression):
        errors.append("acceptance.completionExpression must be non-empty")
    else:
        operands = [part.strip() for part in expression.split("&&")]
        expected = set(criterion_ids) | set(EXTERNAL_COMPLETION_OPERANDS)
        if len(operands) != len(set(operands)) or set(operands) != expected:
            errors.append(
                "acceptance.completionExpression does not map all criteria "
                "and external completion gates exactly"
            )

    lanes = acceptance.get("evidenceLanes")
    if not isinstance(lanes, dict):
        errors.append("acceptance.evidenceLanes must be an object")
    else:
        required = _string_list(lanes.get("requiredForFiniteRelease"))
        continuing = _string_list(lanes.get("continuingAfterRelease"))
        if (
            not required or not continuing or set(required) != {
                "deterministic-conformance", "representative-behavior"
            }
            or set(required) & set(continuing)
        ):
            errors.append("finite-release evidence lanes invalid")
        elif set(required) | set(continuing) != evidence_classes:
            errors.append("acceptance evidence lanes must partition constitution evidence classes")
        elif not set(required).issubset(declared_classes):
            errors.append("finite-release evidence lanes must be required by criteria")

    required_sample_ids = []
    post_release_task_ids = []
    representative_policy = acceptance.get("representativeBehaviorPolicy")
    if not isinstance(representative_policy, dict):
        errors.append("acceptance.representativeBehaviorPolicy must be an object")
    else:
        if set(representative_policy) != {
            "requiredTaskIdsForRelease", "mustPassTaskIdsForRelease",
            "sampleRationale", "taskDecisionRule", "releaseDecisionRule",
            "postReleaseTasks", "postSessionBindingContracts",
            "evaluationContractHistory",
            "historicalEvidenceContractSha256", "historicalEvidence",
            "historicalTaskContracts",
        }:
            errors.append("acceptance.representativeBehaviorPolicy shape is invalid")
        required_sample = _string_list(
            representative_policy.get("requiredTaskIdsForRelease")
        )
        must_pass = _string_list(
            representative_policy.get("mustPassTaskIdsForRelease")
        )
        post_release = _string_list(representative_policy.get("postReleaseTasks"))
        if not required_sample:
            errors.append("representative release sample must not be empty")
        else:
            required_sample_ids = required_sample
        if post_release is None:
            errors.append("representative post-release tasks must be a string list")
            post_release = []
        else:
            post_release_task_ids = post_release
        if set(required_sample_ids) & set(post_release):
            errors.append("representative release and post-release tasks must be disjoint")
        if (
            not must_pass or not set(must_pass).issubset(set(required_sample_ids))
        ):
            errors.append("representative must-pass tasks are invalid")
        binding_contracts = representative_policy.get("postSessionBindingContracts")
        if (
            not isinstance(binding_contracts, dict) or not binding_contracts
            or not set(binding_contracts).issubset(set(task_mappings))
            or any(
                not isinstance(contract, list) or not contract or any(
                    not isinstance(spec, dict)
                    or set(spec) != {"kind", "location", "bindingCount"}
                    or not _nonempty_string(spec.get("kind"))
                    or not _nonempty_string(spec.get("location"))
                    or not isinstance(spec.get("bindingCount"), int)
                    or isinstance(spec.get("bindingCount"), bool)
                    or spec["bindingCount"] < 1
                    for spec in contract
                )
                for contract in binding_contracts.values()
            )
        ):
            errors.append("representative post-session binding contracts are invalid")
        evaluation_history = representative_policy.get("evaluationContractHistory")
        if (
            not isinstance(evaluation_history, list) or not evaluation_history
            or any(
                not isinstance(item, dict)
                or set(item) != {"kind", "sha256", "preservedTaskIds", "reason"}
                or item.get("kind") != "scoped-evaluation-contract-supersession"
                or not isinstance(item.get("sha256"), str)
                or not SHA256_RE.fullmatch(item["sha256"])
                or not _string_list(item.get("preservedTaskIds"))
                or not set(item["preservedTaskIds"]).issubset(set(task_mappings))
                or not _nonempty_string(item.get("reason"))
                for item in evaluation_history
            )
        ):
            errors.append("representative evaluation contract history is invalid")
        historical_contract = representative_policy.get(
            "historicalEvidenceContractSha256"
        )
        historical = representative_policy.get("historicalEvidence")
        historical_tasks = representative_policy.get("historicalTaskContracts")
        if (
            not isinstance(historical_contract, str)
            or not SHA256_RE.fullmatch(historical_contract)
            or not isinstance(historical, list)
            or not historical
            or any(not isinstance(item, dict) for item in historical)
            or not isinstance(historical_tasks, dict)
            or any(
                not _nonempty_string(task_id)
                or not isinstance(contract, dict)
                or set(contract) != {"goldenTaskSha256", "task"}
                or not isinstance(contract.get("goldenTaskSha256"), str)
                or not SHA256_RE.fullmatch(contract["goldenTaskSha256"])
                or not isinstance(contract.get("task"), dict)
                or contract["task"].get("id") != task_id
                for task_id, contract in historical_tasks.items()
            )
        ):
            errors.append("representative historical evidence policy is invalid")
        else:
            locators = []
            for index, item in enumerate(historical):
                label = f"historicalEvidence[{index}]"
                observation = _validate_evidence_item(
                    root, item, label, errors, {"representative-behavior"}
                )
                locator = item.get("locator")
                if isinstance(locator, str):
                    locators.append(locator)
                if (
                    item.get("supportsCriterion") != "R3"
                    or not _nonempty_string(item.get("bindsProjection"))
                    or observation.get("evaluationContractSha256")
                    != historical_contract
                ):
                    errors.append(f"{label} historical binding is invalid")
            if len(locators) != len(set(locators)):
                errors.append("representative historical evidence locators are duplicated")
        _require_texts(representative_policy, (
            "sampleRationale", "taskDecisionRule", "releaseDecisionRule",
        ), "acceptance.representativeBehaviorPolicy", errors)

    errors.extend(external_release_contract_errors(root, acceptance))
    return (
        criterion_ids,
        verified,
        required_sample_ids,
        post_release_task_ids,
    )


def _validate_golden_tasks(
    suite, all_ids, kernel_host_lesson_ids, required_release_task_ids,
    post_release_task_ids, errors,
):
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
    metrics = suite.get("metrics")
    burden = metrics.get("humanBurden") if isinstance(metrics, dict) else None
    if (
        not isinstance(metrics, dict) or set(metrics) != {"humanBurden"}
        or not _string_list(burden)
    ):
        errors.append("golden tasks humanBurden metrics are invalid")
    tasks = _object_entries(suite, "tasks", errors)
    task_ids = _entry_ids(tasks, "golden tasks", errors)
    kinds, coverage = set(), set()
    for index, task in enumerate(tasks):
        label = f"golden tasks[{index}]"
        _require_texts(task, ("name", "kind", "prompt", "startingState"), label, errors)
        kinds.add(task.get("kind", ""))
        _validate_mapping(task, label, all_ids, errors)
        coverage.update(_string_list(task.get("mapsTo")) or [])
        if not _string_list(task.get("required")):
            errors.append(f"{label}.required must be non-empty")
        if not _string_list(task.get("prohibited")):
            errors.append(f"{label}.prohibited must be non-empty")
        if task.get("id") == "GT-13":
            prompt = task.get("prompt", "")
            starting_state = task.get("startingState", "")
            workspace = task.get("workspaceContract")
            if (
                not isinstance(workspace, dict)
                or set(workspace) != {
                    "mode", "preserveUserState", "releaseScope",
                    "promptSha256", "startingStateSha256",
                    "supersedesGoldenTaskSha256",
                }
                or workspace.get("mode") != "bound-reviewable"
                or workspace.get("preserveUserState") is not True
                or workspace.get("releaseScope") != "task-attributable-only"
                or re.fullmatch(r"[0-9a-f]{64}", workspace.get(
                    "supersedesGoldenTaskSha256", "")) is None
                or workspace.get("promptSha256") != sha256(
                    prompt.encode("utf-8")
                ).hexdigest()
                or workspace.get("startingStateSha256") != sha256(
                    starting_state.encode("utf-8")
                ).hexdigest()
                or "reviewable, explicitly bound workspace" not in prompt
                or "bound workspace or checkout" not in starting_state
                or "disposable" in prompt
                or "disposable" in starting_state
            ):
                errors.append(
                    f"{label} must model the bound reviewable GT-13 workspace"
                )
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


def host_check(root, adapter_id):
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


def verify_product(root):
    root = Path(root)
    errors = []
    constitution = _read_json(root, AUTHORITY_BOOTSTRAP[0], errors)
    program = _read_json(root, AUTHORITY_BOOTSTRAP[1], errors)
    acceptance = _read_json(root, AUTHORITY_BOOTSTRAP[2], errors)

    authority_product_id = constitution.get("productId")
    product_ids = {
        constitution.get("productId"),
        program.get("productId"),
        acceptance.get("productId"),
    }
    if not _nonempty_string(authority_product_id) or product_ids != {
        authority_product_id
    }:
        errors.append("authority files do not share the canonical product id")
    if program.get("release") != acceptance.get("release"):
        errors.append("program and acceptance release identities differ")

    contract_ids = _validate_constitution(constitution, errors)
    identity = contract_ids.get("identity")
    if not isinstance(identity, dict):
        identity = {}
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
    golden_suite = _read_json(root, GOLDEN_TASKS_FILE, errors)
    (
        criterion_ids,
        criteria_verified,
        required_release_task_ids,
        post_release_task_ids,
    ) = _validate_acceptance(
        root,
        acceptance,
        kernel_host_lesson_ids,
        evidence_classes,
        golden_suite,
        errors,
    )
    all_ids = kernel_host_lesson_ids | set(criterion_ids)
    _validate_program(
        root, program, criterion_ids, all_ids, identity,
        constitution.get("authority"),
        acceptance.get("canonicalGoalObjectiveSha256"),
        required_release_task_ids, errors,
    )
    maintenance_plan = program.get("maintenancePlan")
    release_notes = acceptance.get("publicRelease", {}).get("releaseNotes")
    errors.extend(
        authority_contract_errors(
            root,
            constitution.get("authority"),
            identity.get("pythonModule"),
            AUTHORITY_BOOTSTRAP,
            (GOLDEN_TASKS_FILE, maintenance_plan, release_notes),
        )
    )
    errors.extend(release_identity_errors(identity, program, acceptance))
    golden = _validate_golden_tasks(
        golden_suite,
        all_ids,
        kernel_host_lesson_ids,
        required_release_task_ids,
        post_release_task_ids,
        errors,
    )

    host_reports = {}
    projections = program.get("hostProjections")
    if isinstance(projections, list):
        for projection in projections:
            if not isinstance(projection, dict) or not _nonempty_string(
                projection.get("id")
            ):
                continue
            local_errors = []
            details = validate_host_projection(
                root,
                projection,
                contract_ids,
                authority_product_id,
                identity,
                local_errors,
                _read_json,
                GOLDEN_TASKS_FILE,
            )
            errors.extend(local_errors)
            host_reports[projection["id"]] = {
                **details,
                "errors": local_errors,
            }

    repository_files, repository_file_errors = _repository_files(root)
    errors.extend(repository_file_errors)
    errors.extend(
        projection_evidence_binding_errors(
            root, acceptance, host_reports, _read_json
        )
    )
    errors.extend(
        historical_representative_errors(
            root,
            acceptance,
            golden_suite,
            _read_json,
        )
    )
    errors.extend(
        representative_sample_errors(
            root,
            acceptance,
            required_release_task_ids,
            golden_suite,
            _read_json,
            require_complete=program.get("status") == "ready",
        )
    )

    historical_revision = next((
        item.get("revision") for item in program.get("inputEvidence", [])
        if isinstance(item, dict)
        and item.get("kind") == "historical-release-and-counterevidence-boundary"
    ), None)
    historical_references = {
        item.get("repositoryLocator")
        for item in program.get("inputEvidence", [])
        if isinstance(item, dict)
        and isinstance(item.get("repositoryLocator"), str)
        and isinstance(item.get("repositorySha256"), str)
    }
    errors.extend(active_tree_errors(
        root,
        repository_files,
        historical_revision,
        historical_references,
        program.get("complexityBudget", {}).get("digestBoundBinaryAssets")
        if isinstance(program.get("complexityBudget"), dict) else None,
    ))

    python_module = identity.get("pythonModule")
    complexity = _validate_complexity(
        root,
        program,
        python_module if isinstance(python_module, str) else "__invalid__",
        repository_files,
        errors,
    )
    residue = known_task_residue(root)
    if residue:
        errors.append(f"known task residue remains: {residue}")
    verified_count = sum(
        1
        for criterion in acceptance.get("criteria", [])
        if isinstance(criterion, dict) and criterion.get("assessment") == "verified"
    )
    checkout_clean = clean_git_checkout(root)
    repository_ready = (
        criteria_verified
        and program.get("status") == "ready"
        and isinstance(program.get("increment"), dict)
        and program["increment"].get("state") == "completed"
        and checkout_clean
        and not errors
    )
    return {
        "productId": constitution.get("productId"),
        "release": program.get("release"),
        "programStatus": program.get("status"),
        "contractValid": not errors,
        "checkoutClean": checkout_clean,
        "repositoryCandidateReady": repository_ready,
        "completionState": "external-gates-required" if repository_ready else "repository-incomplete",
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
        "externalGates": {
            operand: "not-evaluated-by-verifier"
            for operand in EXTERNAL_COMPLETION_OPERANDS
        },
        "goldenTasks": golden,
        "hostChecks": host_reports,
        "complexity": complexity,
        "valid": not errors,
        "errors": errors,
    }
