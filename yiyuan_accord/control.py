from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from .evidence import (
    FROZEN_GT20_21_REPRESENTATIVE_LANES,
    evaluation_contract_history_valid,
    frozen_gt20_21_promotion_errors,
    historical_representative_errors,
    provisional_gt20_21_source_errors,
    representative_contract_sha256,
    representative_sample_errors,
)
from .guardrails import (
    EXTERNAL_COMPLETION_OPERANDS,
    GATE_SEQUENCE,
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
    RELEASE_RE,
    _bounded_git_bytes,
    _bounded_regular_bytes,
    _nonempty_string,
    _strict_json_object,
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
GUIDANCE_FILE = "product/reshaping-guidance.json"
MAX_JSON_BYTES = 1_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
ASSESSMENTS = {"planned", "verified", "blocked", "continuing"}
PROGRAM_STATES = {"active", "ready", "blocked"}

_SNAPSHOT_V1_SCHEMA = "yiyuan-accord-stage-closeout-snapshot/v1"
_SNAPSHOT_V2_SCHEMA = "yiyuan-accord-stage-closeout-snapshot/v2"
_SNAPSHOT_V1_AUTHORITY_REFS = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
)
_SNAPSHOT_V1_GUIDANCE_FILE = "product/reshaping-guidance.json"
_SNAPSHOT_V1_GOLDEN_TASKS_FILE = "evals/golden-tasks.json"
_SNAPSHOT_V1_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SNAPSHOT_V1_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SNAPSHOT_V1_PACKAGE_ID_RE = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)
_SNAPSHOT_V1_SEMVER_PRERELEASE = (
    r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*"
)
_SNAPSHOT_V1_SEMVER_BUILD = r"[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*"
_SNAPSHOT_V1_RELEASE_RE = re.compile(
    rf"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\."
    rf"(0|[1-9][0-9]*)(?:-({_SNAPSHOT_V1_SEMVER_PRERELEASE}))?"
    rf"(?:\+({_SNAPSHOT_V1_SEMVER_BUILD}))?$"
)
_SNAPSHOT_V1_MAX_LINEAGE_DEPTH = 512
_SNAPSHOT_V1_MAX_JSON_DEPTH = 512
_SNAPSHOT_V1_MAX_HISTORY_REVISIONS = 4096
_SNAPSHOT_V1_HISTORY_BYTES = 67_108_864
_SNAPSHOT_V1_BLOB_BYTES = 1_000_000
_SNAPSHOT_V1_PROJECTION_FIELDS = frozenset((
    "id packageId packageVersion packageSha256 manifest marketplace contract "
    "skill metadataFiles mechanismFiles activationContext interfaceDefaultPrompt "
    "maxSkillBytes requiredSkillMarkers forbiddenPaths"
).split())
_SNAPSHOT_V1_PROJECTION_LEGAL_FIELDS = frozenset({"legalFiles"})
_SNAPSHOT_V1_IO_EXCEPTIONS = (
    OSError, subprocess.SubprocessError, UnicodeError, ValueError,
)
_SNAPSHOT_V1_STRUCTURE_EXCEPTIONS = (
    TypeError, AttributeError, KeyError, IndexError, RecursionError,
)
_SNAPSHOT_V1_FAILURES = (
    *_SNAPSHOT_V1_IO_EXCEPTIONS, *_SNAPSHOT_V1_STRUCTURE_EXCEPTIONS,
)


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
        value = _strict_json_object(raw.decode("utf-8"))
        return value
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"invalid JSON {locator}: {exc}")
        return {}


def _read_text(root, locator, errors):
    path = _safe_file(root, locator, errors)
    if path is None:
        return ""
    try:
        raw, read_state = _bounded_regular_bytes(path)
        if read_state is not None:
            raise ValueError(f"text source is {read_state}")
        return raw.decode("utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"invalid text {locator}: {exc}")
        return ""


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


def _contains_markers(value, markers):
    return _nonempty_string(value) and all(marker in value for marker in markers)


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


def _validate_stage_guidance(guidance, errors):
    adaptive = guidance.get("adaptiveSystem") if isinstance(guidance, dict) else None
    stage = adaptive.get("stageStateContract") if isinstance(adaptive, dict) else None
    horizon = adaptive.get("evolutionHorizon") if isinstance(adaptive, dict) else None
    if not isinstance(stage, dict) or set(stage) != {
        "role", "dynamicSurfaces", "changeRule", "closeoutSnapshotRule", "historyRule",
    } or stage.get("role") != "derived-referenceable-node-not-authority-or-release-evidence" \
            or stage.get("dynamicSurfaces") != [
                "baseline", "plan", "process-and-ordered-work",
                "acceptance-contract", "goal-mode-projection",
            ] or not _contains_markers(stage.get("changeRule"), (
                "versioned, evidence-bound and rebuildable", "prior version",
                "evidence cutoff", "affected criteria", "earliest replay boundary",
                "silently weaken acceptance", "erase failed evidence", "future stage",
            )) or not _contains_markers(stage.get("closeoutSnapshotRule"), (
                "stage identity", "parent node", "authority and surface locators",
                "acceptance transition", "evaluation contract", "invalidation triggers",
                "containing-git-commit", "never stores its own SHA",
                "<containing-sha>:<self-locator>", "successor cites", "cannot self-attest",
                "next gate is null only", "later version starts a new ordered cycle",
                "terminal predecessor",
            )) or not _contains_markers(stage.get("historyRule"), (
                "latest accepted stage projection", "Git history",
                "predecessor locator", "do not add a snapshot registry",
            )):
        errors.append("reshaping guidance stage snapshot contract is invalid")
    if not isinstance(horizon, dict) or set(horizon) != {
        "inputs", "candidateClasses", "rule", "storageRule",
    } or horizon.get("inputs") != [
        "whole-project-panorama-and-live-obligations",
        "latest-accepted-stage-snapshot",
        "fresh-environment-host-evidence-and-user-corrections",
    ] or horizon.get("candidateClasses") != [
        "maintenance-and-health", "iteration-and-quality-improvement",
        "dependency-standard-and-distribution-update",
        "bounded-refactoring-and-complexity-reduction",
        "host-client-model-route-and-interface-adaptation",
        "retirement-replacement-and-degradation",
        "later-outcome-driven-development",
    ] or not _contains_markers(horizon.get("rule"), (
        "sparse, on-demand derived view",
        "not a second authority source, frozen roadmap, Cartesian precomputation or automatic commitment",
        "Refresh only affected candidates", "at most the next bounded increment",
        "hypothetical, deferred, retired or unknown",
    )) or not _contains_markers(horizon.get("storageRule"), (
        "Do not persist unpromoted horizon items", "horizon registry",
        "only the one candidate admitted as a versioned bounded increment",
    )):
        errors.append("reshaping guidance evolution horizon contract is invalid")


def _validate_input_evidence(root, program, errors, revision=None):
    inputs = _object_entries(program, "inputEvidence", errors)
    _entry_ids(inputs, "inputEvidence", errors)
    for index, item in enumerate(inputs):
        locator = item.get("repositoryLocator")
        if locator is not None:
            expected = item.get("repositorySha256")
            if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
                errors.append(f"inputEvidence[{index}].repositorySha256 is invalid")
            elif revision is None:
                path = _safe_file(root, locator, errors)
                if path is not None:
                    actual = _hash(path, errors, f"inputEvidence[{index}]")
                    if actual is not None and actual != expected:
                        errors.append(f"inputEvidence[{index}] repository digest mismatch")
            else:
                try:
                    actual = sha256(_snapshot_bytes(root, locator, revision)).hexdigest()
                    if actual != expected:
                        errors.append(f"inputEvidence[{index}] repository digest mismatch")
                except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
                    errors.append(f"inputEvidence[{index}] repository file is unavailable")
        item_revision = item.get("revision")
        if item_revision is not None and (
            not isinstance(item_revision, str) or not REVISION_RE.fullmatch(item_revision)
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


def _snapshot_v1_semantic_version_precedence(value):
    match = _SNAPSHOT_V1_RELEASE_RE.fullmatch(value) \
        if isinstance(value, str) else None
    if match is None:
        return None
    major, minor, patch, prerelease, _build = match.groups()
    identifiers = tuple(
        (0, len(item), item) if item.isdigit() else (1, 0, item)
        for item in prerelease.split(".")
    ) if prerelease is not None else ()
    return tuple((len(item), item) for item in (major, minor, patch)) + (
        prerelease is None, identifiers,
    )


def _semantic_version_precedence(value):
    """Current-rule compatibility entrypoint; v1 calls its frozen helper directly."""
    return _snapshot_v1_semantic_version_precedence(value)


def _snapshot_bytes(root, locator, revision):
    if (
        not isinstance(revision, str)
        or _SNAPSHOT_V1_REVISION_RE.fullmatch(revision) is None
    ):
        raise ValueError("snapshot revision is invalid")
    relative = Path(locator) if isinstance(locator, str) else None
    if relative is None or not locator or "\\" in locator or relative.is_absolute() \
            or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("snapshot locator is invalid")
    listing = _bounded_git_bytes(
        root, ["ls-tree", "-z", revision, "--", locator], 4096,
    )
    metadata, separator, resolved = listing.rstrip(b"\0").partition(b"\t")
    fields = metadata.split()
    if not separator or resolved.decode("utf-8") != locator or len(fields) != 3 \
            or fields[0] not in {b"100644", b"100755"} or fields[1] != b"blob":
        raise ValueError("snapshot file is not an owned regular blob")
    return _bounded_git_bytes(
        root, ["show", "--end-of-options", f"{revision}:{locator}"],
        _SNAPSHOT_V1_BLOB_BYTES,
    )


def _snapshot_json(root, locator, revision=None):
    if revision is None:
        read_errors = []
        value = _read_json(root, locator, read_errors)
        if read_errors:
            raise ValueError("snapshot JSON is unavailable")
        return value
    return _strict_json_object(_snapshot_bytes(root, locator, revision))


def _snapshot_v1_node_key(node):
    return sha256(json.dumps(
        node, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _snapshot_v1_json_structure_is_bounded(value):
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        if depth > _SNAPSHOT_V1_MAX_JSON_DEPTH:
            return False
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return True


def _snapshot_v1_history_index(root, anchor, cache):
    if not isinstance(cache, dict):
        raise TypeError("snapshot lineage cache is invalid")
    if anchor != "HEAD" and (
        not isinstance(anchor, str)
        or _SNAPSHOT_V1_REVISION_RE.fullmatch(anchor) is None
    ):
        raise ValueError("snapshot lineage anchor is invalid")
    resolved = anchor
    if anchor == "HEAD":
        resolved = _bounded_git_bytes(
            root, ["rev-parse", "--verify", "HEAD^{commit}"], 64,
        ).decode("ascii").strip()
        if _SNAPSHOT_V1_REVISION_RE.fullmatch(resolved) is None:
            raise ValueError("snapshot lineage HEAD is invalid")
    root_key = str(Path(root).resolve())
    cache_key = ("snapshot-v1-history-index", root_key, resolved)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached, resolved
    revisions = _bounded_git_bytes(
        root, [
            "log", "--first-parent",
            f"--max-count={_SNAPSHOT_V1_MAX_HISTORY_REVISIONS + 1}",
            "--format=%H", resolved,
        ]
    ).decode("ascii").splitlines()
    if (
        not revisions
        or len(revisions) > _SNAPSHOT_V1_MAX_HISTORY_REVISIONS
        or any(_SNAPSHOT_V1_REVISION_RE.fullmatch(item) is None
               for item in revisions)
    ):
        raise ValueError("snapshot lineage revision bound is invalid")
    requests = b"".join(
        f"{revision}:{_SNAPSHOT_V1_AUTHORITY_REFS[1]}\n".encode("ascii")
        for revision in revisions
    )
    batch = _bounded_git_bytes(
        root, ["cat-file", "--batch"], _SNAPSHOT_V1_HISTORY_BYTES, requests,
    )
    records, offset = [], 0
    for revision in revisions:
        end = batch.find(b"\n", offset)
        if end < 0:
            raise ValueError("invalid Git batch header")
        header = batch[offset:end].split()
        offset = end + 1
        if len(header) == 2 and header[1] == b"missing":
            records.append((revision, None))
            continue
        if len(header) != 3 or header[1] != b"blob":
            raise ValueError("invalid Git batch header")
        size = int(header[2])
        if size < 0 or size > _SNAPSHOT_V1_BLOB_BYTES:
            raise ValueError("snapshot lineage blob bound is invalid")
        content = batch[offset:offset + size]
        offset += size + 1
        if len(content) != size or batch[offset - 1:offset] != b"\n":
            raise ValueError("invalid Git batch body")
        try:
            historical = _strict_json_object(content)
        except _SNAPSHOT_V1_STRUCTURE_EXCEPTIONS as exc:
            raise ValueError(
                "snapshot lineage program structure is invalid"
            ) from exc
        if not _snapshot_v1_json_structure_is_bounded(historical):
            raise ValueError("snapshot lineage program structure is invalid")
        increment = historical.get("increment")
        node = increment.get("closeoutSnapshot") \
            if isinstance(increment, dict) else None
        records.append((revision, node))
    if offset != len(batch):
        raise ValueError("unexpected Git batch suffix")
    groups = []
    for revision, node in records:
        if groups and groups[-1][1] == node:
            groups[-1][0].append(revision)
        else:
            groups.append(([revision], node))
    frozen_groups, positions, occurrences = [], {}, {}
    for group_index, (group_revisions, node) in enumerate(groups):
        node_key = _snapshot_v1_node_key(node)
        frozen_revisions = tuple(group_revisions)
        frozen_groups.append((frozen_revisions, node, node_key))
        occurrences.setdefault(node_key, []).append(group_index)
        for position, revision in enumerate(frozen_revisions):
            positions[revision] = (group_index, position)
    history = {
        "groups": tuple(frozen_groups),
        "positions": positions,
        "occurrences": {
            key: tuple(value) for key, value in occurrences.items()
        },
    }
    for revision in positions:
        cache[("snapshot-v1-history-index", root_key, revision)] = history
    cache[cache_key] = history
    return history, resolved


def _snapshot_v1_lineage(root, current, anchor="HEAD", cache=None):
    cache = {} if cache is None else cache
    history, resolved = _snapshot_v1_history_index(root, anchor, cache)
    groups = history["groups"]
    group_index, position = history["positions"][resolved]
    group_revisions, group_node, _ = groups[group_index]
    first_revisions = group_revisions[position:]
    current_key = _snapshot_v1_node_key(current)
    origin, current_run = None, ()
    if group_node == current:
        current_run = first_revisions
        origin, predecessor_index = current_run[-1], group_index + 1
    else:
        predecessor_index = group_index
    replay = any(
        index >= predecessor_index and groups[index][1] == current
        for index in history["occurrences"].get(current_key, ())
    )
    predecessor = None
    if predecessor_index < len(groups) and groups[predecessor_index][1] is not None:
        revisions, node, _ = groups[predecessor_index]
        if predecessor_index == group_index:
            revisions = first_revisions
        predecessor = (revisions[-1], node, revisions)
    elif any(node is not None for _, node, _ in groups[predecessor_index:]):
        replay = True
    return origin, predecessor, replay, current_run


def _snapshot_or_worktree_bytes(root, locator, revision=None):
    if revision is not None:
        return _snapshot_bytes(root, locator, revision)
    path = repository_relative_path(root, locator)
    if path is None:
        raise ValueError("snapshot locator is invalid")
    raw, reason = _bounded_regular_bytes(path)
    if raw is None:
        raise ValueError(f"snapshot file is {reason}")
    return raw


def _snapshot_v1_surface_digests(root, program, acceptance, revision=None):
    if not isinstance(program, dict) or not isinstance(acceptance, dict):
        raise TypeError("revision-bound v1 authority is not an object")
    locators = [
        *_SNAPSHOT_V1_AUTHORITY_REFS,
        _SNAPSHOT_V1_GUIDANCE_FILE,
        _SNAPSHOT_V1_GOLDEN_TASKS_FILE,
    ]
    release_notes = acceptance.get("publicRelease", {}).get("releaseNotes") \
        if isinstance(acceptance.get("publicRelease"), dict) else None
    if isinstance(release_notes, str):
        locators.append(release_notes)
    projections = program.get("hostProjections") \
        if isinstance(program, dict) else None
    for projection in projections if isinstance(projections, list) else []:
        marketplace = projection.get("marketplace") \
            if isinstance(projection, dict) else None
        if isinstance(marketplace, str):
            locators.append(marketplace)
    return {
        locator: sha256(
            _snapshot_or_worktree_bytes(root, locator, revision)
        ).hexdigest()
        for locator in sorted(set(locators))
    }


def _snapshot_v1_binding_state(
    root, program, acceptance, guidance, constitution, golden, revision=None,
):
    if any(not isinstance(item, dict) for item in (
        program, acceptance, guidance, constitution, golden,
    )):
        raise TypeError("revision-bound v1 document is not an object")
    increment = program.get("increment")
    increment = increment if isinstance(increment, dict) else {}
    snapshot = increment.get("closeoutSnapshot")
    procedure = program.get("releaseProcedure")
    gates = procedure.get("orderedGates") \
        if isinstance(procedure, dict) else []
    gates = gates if isinstance(gates, list) else []
    closed = snapshot.get("closedGateId") if isinstance(snapshot, dict) else None
    gate = next((item for item in gates if isinstance(item, dict)
                 and item.get("id") == closed), None)
    adaptive = guidance.get("adaptiveSystem") \
        if isinstance(guidance, dict) else None
    return {
        "authority": [constitution, program, acceptance],
        "baseline": guidance.get("wholeSystemBalanceReview"),
        "stageContract": adaptive.get("stageStateContract") \
            if isinstance(adaptive, dict) else None,
        "evidence": [program.get("inputEvidence"), acceptance.get("criteria"),
                     golden, gate],
        "surfaceDigests": _snapshot_v1_surface_digests(
            root, program, acceptance, revision,
        ),
    }


def _snapshot_v1_documents(root, revision=None):
    constitution, program, acceptance, guidance, golden = (
        _snapshot_json(root, locator, revision) for locator in (
            _SNAPSHOT_V1_AUTHORITY_REFS[0], _SNAPSHOT_V1_AUTHORITY_REFS[1],
            _SNAPSHOT_V1_AUTHORITY_REFS[2], _SNAPSHOT_V1_GUIDANCE_FILE,
            _SNAPSHOT_V1_GOLDEN_TASKS_FILE,
        )
    )
    return constitution, program, acceptance, guidance, golden


def _snapshot_documents(root, revision=None):
    """Compatibility reader; revision predicates call the frozen v1 reader."""
    return _snapshot_v1_documents(root, revision)


def _snapshot_v1_marketplace_errors(
    adapter, marketplace, manifest, expected_path, product_id, identity,
):
    if not isinstance(identity, dict):
        identity = {}
    prefix = f"adapter {adapter} revision marketplace"
    entries = marketplace.get("plugins") if isinstance(marketplace, dict) else None
    if not isinstance(entries, list) or len(entries) != 1:
        return [f"{prefix} entry is not unique"]
    entry = entries[0]
    if not isinstance(entry, dict) or entry.get("name") != manifest.get("name"):
        return [f"{prefix} entry is not unique"]
    errors = []
    if adapter == "codex":
        if set(marketplace) != {"name", "interface", "plugins"} or (
            marketplace.get("name") != product_id
            or marketplace.get("interface") != {
                "displayName": identity.get("displayName")
            }
        ):
            errors.append(f"{prefix} shape or identity is invalid")
        if set(entry) != {"name", "source", "policy", "category"}:
            errors.append(f"{prefix} entry shape is invalid")
        if entry.get("source") != {"source": "local", "path": expected_path}:
            errors.append(f"{prefix} source is invalid")
        if entry.get("policy") != {
            "installation": "AVAILABLE", "authentication": "ON_INSTALL",
        }:
            errors.append(f"{prefix} policy is invalid")
    elif adapter == "claude-code":
        match = re.fullmatch(
            r"https://github\.com/([^/]+)/[^/]+", identity.get("repository") or "",
        )
        publisher = match.group(1) if match else None
        if set(marketplace) != {"name", "description", "owner", "plugins"} or (
            marketplace.get("name") != product_id
            or marketplace.get("description") != (
                f"Official {identity.get('displayName')} plugin marketplace."
            )
            or marketplace.get("owner") != {"name": publisher}
        ):
            errors.append(f"{prefix} shape or identity is invalid")
        if set(entry) != {"name", "source", "description", "version"}:
            errors.append(f"{prefix} entry shape is invalid")
        if entry.get("source") != expected_path:
            errors.append(f"{prefix} source is invalid")
        if entry.get("description") != manifest.get("description") or (
            entry.get("version") != manifest.get("version")
        ):
            errors.append(f"{prefix} presentation is invalid")
    else:
        errors.append(f"{prefix} adapter is invalid")
    return errors


def _snapshot_v1_projection_shape_errors(program, constitution):
    errors = []
    projections = program.get("hostProjections") \
        if isinstance(program, dict) else None
    identity = constitution.get("identity") \
        if isinstance(constitution, dict) else None
    plugin_ids = identity.get("pluginIds") \
        if isinstance(identity, dict) else None
    distribution = program.get("distributionVersion") \
        if isinstance(program, dict) else None
    expected_version = distribution[1:] if (
        isinstance(distribution, str)
        and _SNAPSHOT_V1_RELEASE_RE.fullmatch(distribution)
    ) else None
    if (
        not isinstance(projections, list) or not projections
        or any(not isinstance(item, dict) for item in projections)
    ):
        return ["revision-bound v1 host projections are invalid"]

    adapter_ids, package_ids = [], []
    locator_values = {field: [] for field in (
        "manifest", "marketplace", "contract", "skill",
    )}
    for index, projection in enumerate(projections):
        prefix = f"hostProjections[{index}]"
        expected_fields = _SNAPSHOT_V1_PROJECTION_FIELDS \
            if projection.get("id") == "codex" else (
                _SNAPSHOT_V1_PROJECTION_FIELDS - {"interfaceDefaultPrompt"}
            )
        if set(projection) not in (
            expected_fields,
            expected_fields | _SNAPSHOT_V1_PROJECTION_LEGAL_FIELDS,
        ):
            errors.append(f"{prefix} shape is invalid")
        for field in (
            "id", "packageId", "packageVersion", "manifest", "marketplace",
            "contract", "skill", "activationContext",
        ):
            if not _nonempty_string(projection.get(field)):
                errors.append(f"{prefix}.{field} is invalid")
        adapter_ids.append(projection.get("id"))
        package_ids.append(projection.get("packageId"))
        for field, values in locator_values.items():
            values.append(projection.get(field))

        for field in (
            "metadataFiles", "mechanismFiles", "forbiddenPaths",
            "requiredSkillMarkers",
        ):
            items = projection.get(field)
            if (
                not isinstance(items, list)
                or any(not _nonempty_string(item) for item in items)
                or len(items) != len(set(items))
                or field == "requiredSkillMarkers" and not items
            ):
                errors.append(f"{prefix}.{field} shape is invalid")
        if projection.get("id") == "codex":
            prompts = projection.get("interfaceDefaultPrompt")
            if (
                not isinstance(prompts, list) or not prompts
                or any(not _nonempty_string(item) for item in prompts)
                or len(prompts) != len(set(prompts))
            ):
                errors.append(f"{prefix}.interfaceDefaultPrompt shape is invalid")
        max_skill_bytes = projection.get("maxSkillBytes")
        if (
            isinstance(max_skill_bytes, bool)
            or not isinstance(max_skill_bytes, int)
            or max_skill_bytes <= 0
            or _SNAPSHOT_V1_SHA256_RE.fullmatch(
                projection.get("packageSha256") or ""
            ) is None
        ):
            errors.append(f"{prefix} package bounds are invalid")
        if projection.get("packageVersion") != expected_version:
            errors.append(f"{prefix} package version is invalid")

        package_id = projection.get("packageId")
        package_root = f"plugins/{package_id}" \
            if _nonempty_string(package_id) else None
        if "legalFiles" in projection and projection.get("legalFiles") != [
            f"{package_root}/LICENSE", f"{package_root}/NOTICE",
        ]:
            errors.append(f"{prefix}.legalFiles is invalid")
        manifest = projection.get("manifest")
        contract = projection.get("contract")
        skill = projection.get("skill")
        if (
            package_root is None
            or not isinstance(manifest, str)
            or not manifest.startswith(f"{package_root}/.")
            or not manifest.endswith("-plugin/plugin.json")
            or not isinstance(contract, str)
            or not contract.startswith(f"{package_root}/")
            or not contract.endswith("/adapter.json")
            or not isinstance(skill, str)
            or not skill.startswith(f"{package_root}/skills/")
            or not skill.endswith("/SKILL.md")
        ):
            errors.append(f"{prefix} package locator shape is invalid")

    if (
        any(
            not _nonempty_string(item)
            or _SNAPSHOT_V1_PACKAGE_ID_RE.fullmatch(item) is None
            for item in adapter_ids
        )
        or len(adapter_ids) != len(set(adapter_ids))
    ):
        errors.append("revision-bound v1 adapter ids are invalid")
    if (
        not isinstance(plugin_ids, list) or not plugin_ids
        or any(
            not _nonempty_string(item)
            or _SNAPSHOT_V1_PACKAGE_ID_RE.fullmatch(item) is None
            for item in plugin_ids
        )
        or len(plugin_ids) != len(set(plugin_ids))
        or any(
            not _nonempty_string(item)
            or _SNAPSHOT_V1_PACKAGE_ID_RE.fullmatch(item) is None
            for item in package_ids
        )
        or len(package_ids) != len(set(package_ids))
        or set(package_ids) != set(plugin_ids)
    ):
        errors.append("revision-bound v1 projection package ids are invalid")
    for field, values in locator_values.items():
        if (
            any(not _nonempty_string(item) for item in values)
            or len(values) != len(set(values))
        ):
            errors.append(f"revision-bound v1 projection {field} locators are not unique")
    return errors


def _snapshot_v1_projection_package_errors(
    root, program, constitution, revision,
):
    errors = []
    projections = program.get("hostProjections") \
        if isinstance(program, dict) else None
    if not isinstance(projections, list) or not projections:
        return ["revision-bound v1 host projections are unavailable"]
    identity = constitution.get("identity") \
        if isinstance(constitution, dict) else None
    identity = identity if isinstance(identity, dict) else {}
    product_id = constitution.get("productId") \
        if isinstance(constitution, dict) else None
    for index, projection in enumerate(
        projections
    ):
        if not isinstance(projection, dict):
            errors.append(f"hostProjections[{index}] is not an object")
            continue
        adapter = projection.get("id")
        prefix = f"hostProjections[{index}]"
        manifest_locator = projection.get("manifest")
        locators = [
            projection.get(field) for field in ("manifest", "contract", "skill")
        ]
        for field in ("metadataFiles", "mechanismFiles"):
            value = projection.get(field)
            locators.extend(value if isinstance(value, list) else [])
        try:
            manifest = _snapshot_json(root, manifest_locator, revision)
        except _SNAPSHOT_V1_FAILURES:
            manifest = {}
            errors.append(f"{prefix} revision package manifest is unavailable")
        if (
            manifest.get("name") != projection.get("packageId")
            or manifest.get("version") != projection.get("packageVersion")
            or manifest.get("repository") != identity.get("repository")
        ):
            errors.append(f"{prefix} revision package manifest binding is invalid")
        interface = manifest.get("interface") if isinstance(manifest, dict) else None
        if adapter == "codex" and isinstance(manifest_locator, str):
            for field in ("composerIcon", "logo"):
                value = interface.get(field) if isinstance(interface, dict) else None
                if isinstance(value, str) and value.startswith("./"):
                    relative = Path(value[2:])
                    if (
                        not relative.is_absolute() and ".." not in relative.parts
                        and relative.parts[:1] == ("assets",)
                        and relative.suffix.lower() == ".png"
                    ):
                        locators.append(
                            (Path(manifest_locator).parent.parent / relative).as_posix()
                        )
        if (
            not isinstance(manifest_locator, str)
            or any(not isinstance(locator, str) or not locator for locator in locators)
        ):
            errors.append(f"{prefix} revision package declaration is invalid")
            continue
        package_id = projection.get("packageId")
        package_root = f"plugins/{package_id}" \
            if _nonempty_string(package_id) else None
        if (
            package_root is None
            or Path(manifest_locator).parent.parent.as_posix() != package_root
        ):
            errors.append(f"{prefix} revision package root is invalid")
            continue
        legal_locators = projection.get("legalFiles")
        if "legalFiles" in projection:
            expected_legal_locators = [
                f"{package_root}/LICENSE", f"{package_root}/NOTICE",
            ]
            if legal_locators != expected_legal_locators:
                errors.append(f"{prefix} revision legal files are invalid")
                continue
            locators.extend(legal_locators)
            for package_locator, authority_locator in zip(
                legal_locators, ("LICENSE", "NOTICE"), strict=True,
            ):
                try:
                    if _snapshot_bytes(
                        root, package_locator, revision,
                    ) != _snapshot_bytes(root, authority_locator, revision):
                        errors.append(
                            f"{prefix} revision {authority_locator} differs from "
                            "repository authority"
                        )
                except _SNAPSHOT_V1_FAILURES:
                    errors.append(
                        f"{prefix} revision {authority_locator} is unavailable"
                    )
        marketplace_locator = projection.get("marketplace")
        try:
            marketplace = _snapshot_json(root, marketplace_locator, revision)
            errors.extend(_snapshot_v1_marketplace_errors(
                adapter, marketplace, manifest, f"./{package_root}",
                product_id, identity,
            ))
        except _SNAPSHOT_V1_FAILURES:
            errors.append(f"{prefix} revision marketplace is unavailable")
        try:
            contract = _snapshot_json(
                root, projection.get("contract"), revision,
            )
            if (
                contract.get("schema") != 1
                or contract.get("productId") != product_id
                or contract.get("packageId") != projection.get("packageId")
                or contract.get("adapterId") != adapter
            ):
                errors.append(f"{prefix} revision contract binding is invalid")
        except _SNAPSHOT_V1_FAILURES:
            errors.append(f"{prefix} revision contract is unavailable")
        try:
            skill_raw = _snapshot_bytes(root, projection.get("skill"), revision)
            skill = skill_raw.decode("utf-8")
            markers = projection.get("requiredSkillMarkers")
            if (
                not skill.strip()
                or len(skill_raw) > projection.get("maxSkillBytes")
                or not isinstance(markers, list)
                or any(marker not in skill for marker in markers)
            ):
                errors.append(f"{prefix} revision skill binding is invalid")
        except _SNAPSHOT_V1_FAILURES:
            errors.append(f"{prefix} revision skill is unavailable")
        try:
            listing = _bounded_git_bytes(
                root, ["ls-tree", "-r", "-z", revision, "--", package_root],
                1_048_576,
            )
            actual = set()
            for record in (item for item in listing.split(b"\0") if item):
                metadata, separator, raw_locator = record.partition(b"\t")
                fields = metadata.split()
                locator = raw_locator.decode("utf-8")
                if (
                    not separator or len(fields) != 3
                    or fields[0] not in {b"100644", b"100755"}
                    or fields[1] != b"blob"
                    or not locator.startswith(f"{package_root}/")
                ):
                    raise ValueError("revision package tree is invalid")
                actual.add(locator)
            declared = set(locators)
            if actual != declared:
                errors.append(f"{prefix} revision package file set is invalid")
            digest = sha256()
            for locator in sorted(declared):
                digest.update(locator.encode("utf-8"))
                digest.update(b"\0")
                digest.update(sha256(
                    _snapshot_bytes(root, locator, revision)
                ).digest())
            if digest.hexdigest() != projection.get("packageSha256"):
                errors.append(f"{prefix} revision package digest mismatch")
        except _SNAPSHOT_V1_FAILURES:
            errors.append(f"{prefix} revision package is unavailable")
    return errors


def _snapshot_v1_run_status(root, expected, revisions, cache):
    frozen, contract_valid = True, True
    for revision in revisions:
        documents = _snapshot_v1_documents(root, revision)
        constitution, program, acceptance, guidance, golden = documents
        if _snapshot_v1_binding_state(
            root, program, acceptance, guidance, constitution, golden, revision,
        ) != expected:
            frozen = False
        if contract_valid:
            key = ("revision-bound-snapshot-contract", revision)
            if key not in cache:
                cache[key] = not _snapshot_revision_contract_errors(
                    root, revision, documents,
                )
            contract_valid = cache[key]
    return frozen, contract_valid


def _snapshot_v1_node_errors(program, acceptance):
    errors = []
    increment = program.get("increment") if isinstance(program, dict) else None
    node = increment.get("closeoutSnapshot") \
        if isinstance(increment, dict) else None
    fields = set((
        "schema id stage state revisionBinding predecessorSnapshotRef authorityRefs "
        "surfaceRefs evidenceRefs evidenceCutoff invalidationTriggerRefs "
        "acceptanceTransition evaluationContractSha256 closedGateId nextGateId "
        "claimCeilingRef unknownsRef"
    ).split())
    if not isinstance(node, dict) or set(node) != fields:
        return ["revision-bound v1 snapshot shape is invalid"]
    if (
        node.get("schema") != _SNAPSHOT_V1_SCHEMA
        or node.get("id") != (
            f"stage.{program.get('distributionVersion')}.{node.get('stage')}.closed"
        )
        or node.get("revisionBinding") != {
            "kind": "containing-git-commit",
            "selfLocator": "product/program.json#/increment/closeoutSnapshot",
            "exactLocatorRule": "After commit, prefix selfLocator with the immutable containing commit SHA; never store that SHA inside this object.",
        }
        or node.get("authorityRefs") != list(_SNAPSHOT_V1_AUTHORITY_REFS)
        or node.get("surfaceRefs") != {
            "baseline": "product/reshaping-guidance.json#/wholeSystemBalanceReview",
            "plan": "product/program.json#/increment/fourSurfaceMapping/plan",
            "process": "product/program.json#/increment/fourSurfaceMapping/process",
            "acceptance": "product/acceptance.json",
            "goalProjection": "product/program.json#/goalModePrompt",
        }
    ):
        errors.append("revision-bound v1 snapshot identity is invalid")
    gates = program.get("releaseProcedure", {}).get("orderedGates", []) \
        if isinstance(program.get("releaseProcedure"), dict) else []
    gate_ids = [item.get("id") for item in gates if isinstance(item, dict)]
    if (
        not gate_ids or len(gate_ids) != len(gates)
        or len(gate_ids) != len(set(gate_ids))
        or any(not _nonempty_string(item) for item in gate_ids)
    ):
        errors.append("revision-bound v1 gate sequence is invalid")
    closed = node.get("closedGateId")
    try:
        closed_index = gate_ids.index(closed)
    except ValueError:
        closed_index = -1
    if node.get("evidenceRefs") != [
        "product/program.json#/inputEvidence",
        "product/acceptance.json#/criteria",
        _SNAPSHOT_V1_GOLDEN_TASKS_FILE,
        f"product/program.json#/releaseProcedure/orderedGates/{closed_index}",
    ] or node.get("evidenceCutoff") != {
        "kind": "containing-git-commit",
        "rule": "Only evidenceRefs resolved inside the immutable containing commit belong to this snapshot; later repository or task-time facts require a successor node.",
    } or node.get("invalidationTriggerRefs") != [
        "product/constitution.json#/evolutionPolicy/feedbackRule",
        "product/program.json#/goalModePrompt/refreshTriggers",
        "product/program.json#/processLossControl/correctionRule",
    ]:
        errors.append("revision-bound v1 snapshot references are invalid")
    transition = node.get("acceptanceTransition")
    kind = transition.get("kind") if isinstance(transition, dict) else None
    predecessor = node.get("predecessorSnapshotRef")
    predecessor_match = re.fullmatch(
        r"([0-9a-f]{40}):product/program\.json#/increment/closeoutSnapshot",
        predecessor or "",
    )
    criteria = acceptance.get("criteria") if isinstance(acceptance, dict) else None
    criterion_ids = {
        item.get("id") for item in criteria or [] if isinstance(item, dict)
        and _nonempty_string(item.get("id"))
    }
    affected_list = transition.get("affectedCriterionIds") \
        if isinstance(transition, dict) else None
    affected = set(affected_list) if isinstance(affected_list, list) and all(
        _nonempty_string(item) for item in affected_list
    ) else None
    if (
        not isinstance(transition, dict)
        or set(transition) != {
            "kind", "rationaleRef", "affectedCriterionIds", "replayRef",
        }
        or kind not in {"snapshot-bootstrap", "unchanged", "changed"}
        or transition.get("rationaleRef") != (
            "product/program.json#/increment/fourSurfaceMapping/plan"
        )
        or transition.get("replayRef") != (
            "product/program.json#/increment/fourSurfaceMapping/process/orderedSteps"
        )
        or (predecessor is None) != (kind == "snapshot-bootstrap")
        or (predecessor is not None and predecessor_match is None)
        or affected is None or len(affected) != len(affected_list)
        or not affected.issubset(criterion_ids)
        or (kind == "snapshot-bootstrap" and affected != criterion_ids)
        or (kind == "unchanged" and affected)
        or (kind == "changed" and not affected)
    ):
        errors.append("revision-bound v1 acceptance transition is invalid")
    expected_next = gate_ids[closed_index + 1] \
        if 0 <= closed_index < len(gate_ids) - 1 else None
    if (
        node.get("state") != "closed" or node.get("stage") != closed
        or closed_index < 0 or node.get("nextGateId") != expected_next
        or node.get("claimCeilingRef") != "product/acceptance.json#/claimCeiling"
        or node.get("unknownsRef") != (
            "product/program.json#/increment/hostCapabilityRefresh/unknowns"
        )
        or not _SNAPSHOT_V1_SHA256_RE.fullmatch(
            node.get("evaluationContractSha256") or ""
        )
    ):
        errors.append("revision-bound v1 snapshot state is invalid")
    return errors


def _snapshot_v2_node_errors(program, acceptance):
    """Validate the narrow reopen/close successor without changing v1 history."""
    errors = []
    increment = program.get("increment") if isinstance(program, dict) else None
    node = increment.get("closeoutSnapshot") \
        if isinstance(increment, dict) else None
    fields = set((
        "schema id stage state revisionBinding predecessorSnapshotRef authorityRefs "
        "surfaceRefs evidenceRefs evidenceCutoff invalidationTriggerRefs "
        "acceptanceTransition evaluationContractSha256 gateId nextGateId "
        "claimCeilingRef unknownsRef replay"
    ).split())
    if not isinstance(node, dict) or set(node) != fields:
        return ["revision-bound v2 snapshot shape is invalid"]
    state = node.get("state")
    gate = node.get("gateId")
    if (
        node.get("schema") != _SNAPSHOT_V2_SCHEMA
        or state not in {"reopened", "closed"}
        or node.get("id") != (
            f"stage.{program.get('distributionVersion')}.{node.get('stage')}.{state}"
        )
        or node.get("stage") != gate
        or node.get("revisionBinding") != {
            "kind": "containing-git-commit",
            "selfLocator": "product/program.json#/increment/closeoutSnapshot",
            "exactLocatorRule": "After commit, prefix selfLocator with the immutable containing commit SHA; never store that SHA inside this object.",
        }
        or node.get("authorityRefs") != list(_SNAPSHOT_V1_AUTHORITY_REFS)
        or node.get("surfaceRefs") != {
            "baseline": "product/reshaping-guidance.json#/wholeSystemBalanceReview",
            "plan": "product/program.json#/increment/fourSurfaceMapping/plan",
            "process": "product/program.json#/increment/fourSurfaceMapping/process",
            "acceptance": "product/acceptance.json",
            "goalProjection": "product/program.json#/goalModePrompt",
        }
    ):
        errors.append("revision-bound v2 snapshot identity is invalid")
    gates = program.get("releaseProcedure", {}).get("orderedGates", []) \
        if isinstance(program.get("releaseProcedure"), dict) else []
    gate_ids = [item.get("id") for item in gates if isinstance(item, dict)]
    try:
        gate_index = gate_ids.index(gate)
    except ValueError:
        gate_index = -1
    if node.get("evidenceRefs") != [
        "product/program.json#/inputEvidence",
        "product/acceptance.json#/criteria",
        _SNAPSHOT_V1_GOLDEN_TASKS_FILE,
        f"product/program.json#/releaseProcedure/orderedGates/{gate_index}",
    ] or node.get("evidenceCutoff") != {
        "kind": "containing-git-commit",
        "rule": "Only evidenceRefs resolved inside the immutable containing commit belong to this snapshot; later repository or task-time facts require a successor node.",
    } or node.get("invalidationTriggerRefs") != [
        "product/constitution.json#/evolutionPolicy/feedbackRule",
        "product/program.json#/goalModePrompt/refreshTriggers",
        "product/program.json#/processLossControl/correctionRule",
    ]:
        errors.append("revision-bound v2 snapshot references are invalid")
    predecessor = node.get("predecessorSnapshotRef")
    if re.fullmatch(
        r"[0-9a-f]{40}:product/program\.json#/increment/closeoutSnapshot",
        predecessor or "",
    ) is None:
        errors.append("revision-bound v2 snapshot predecessor is invalid")
    transition = node.get("acceptanceTransition")
    criteria = acceptance.get("criteria") if isinstance(acceptance, dict) else None
    criterion_ids = {
        item.get("id") for item in criteria or [] if isinstance(item, dict)
        and _nonempty_string(item.get("id"))
    }
    if (
        not isinstance(transition, dict)
        or set(transition) != {
            "kind", "rationaleRef", "affectedCriterionIds", "replayRef",
        }
        or transition.get("kind") != "changed"
        or transition.get("rationaleRef") != (
            "product/program.json#/increment/fourSurfaceMapping/plan"
        )
        or transition.get("replayRef") != (
            "product/program.json#/increment/fourSurfaceMapping/process/orderedSteps"
        )
        or set(transition.get("affectedCriterionIds", [])) != {
            "R2", "R3", "R4", "Q1", "Q2", "Q3", "Q4",
        }
        or len(transition.get("affectedCriterionIds", [])) != 7
    ):
        errors.append("revision-bound v2 acceptance transition is invalid")
    replay = node.get("replay")
    if (
        not isinstance(replay, dict)
        or set(replay) != {
            "earliestAffectedBoundary", "invalidatedTaskIds",
            "preservedTaskIds", "evidenceState", "evidenceRef",
        }
        or replay.get("earliestAffectedBoundary")
        != "complete-host-projection-package-identity"
        or replay.get("invalidatedTaskIds") != ["GT-20"]
        or replay.get("preservedTaskIds") != ["GT-21"]
    ):
        errors.append("revision-bound v2 replay boundary is invalid")
        replay = {}
    r3 = next((item for item in criteria or [] if isinstance(item, dict)
               and item.get("id") == "R3"), {})
    expected_next = gate_ids[gate_index + 1] \
        if 0 <= gate_index < len(gate_ids) - 1 else None
    if state == "reopened":
        if (
            node.get("nextGateId") != gate
            or replay.get("evidenceState") != "pending"
            or replay.get("evidenceRef") is not None
            or program.get("status") != "active"
            or not isinstance(increment, dict) or increment.get("state") != "active"
            or r3.get("assessment") != "continuing"
        ):
            errors.append("revision-bound v2 reopened state is invalid")
    elif state == "closed":
        if (
            node.get("nextGateId") != expected_next
            or replay.get("evidenceState") != "verified"
            or not _nonempty_string(replay.get("evidenceRef"))
            or program.get("status") != "ready"
            or not isinstance(increment, dict) or increment.get("state") != "completed"
            or r3.get("assessment") != "verified"
        ):
            errors.append("revision-bound v2 closed state is invalid")
    if (
        gate_index < 0
        or node.get("claimCeilingRef") != "product/acceptance.json#/claimCeiling"
        or node.get("unknownsRef") != (
            "product/program.json#/increment/hostCapabilityRefresh/unknowns"
        )
        or _SNAPSHOT_V1_SHA256_RE.fullmatch(
            node.get("evaluationContractSha256") or ""
        ) is None
    ):
        errors.append("revision-bound v2 snapshot state is invalid")
    return errors


def _snapshot_v1_transition_errors(
    root, current_revision, prior_revision,
    program, acceptance, guidance, constitution, golden,
    prior_program, prior_acceptance, prior_guidance, prior_constitution,
    prior_golden,
):
    errors = []
    if any(not isinstance(item, dict) for item in (
        program, acceptance, guidance, constitution, golden,
        prior_program, prior_acceptance, prior_guidance, prior_constitution,
        prior_golden,
    )):
        return ["revision-bound v1 transition documents are invalid"]
    increment = program.get("increment")
    prior_increment = prior_program.get("increment")
    node = increment.get("closeoutSnapshot") \
        if isinstance(increment, dict) else None
    prior = prior_increment.get("closeoutSnapshot") \
        if isinstance(prior_increment, dict) else None
    if not isinstance(node, dict) or not isinstance(prior, dict):
        return ["revision-bound v1 transition nodes are unavailable"]
    procedure = program.get("releaseProcedure")
    prior_procedure = prior_program.get("releaseProcedure")
    gates = procedure.get("orderedGates") \
        if isinstance(procedure, dict) else None
    prior_gates = prior_procedure.get("orderedGates") \
        if isinstance(prior_procedure, dict) else None
    if not isinstance(gates, list) or not isinstance(prior_gates, list):
        return ["revision-bound v1 transition gates are invalid"]
    gate_ids = [item.get("id") for item in gates if isinstance(item, dict)]
    prior_gate_ids = [item.get("id") for item in prior_gates if isinstance(item, dict)]
    try:
        closed_index = gate_ids.index(node.get("closedGateId"))
        prior_index = prior_gate_ids.index(prior.get("closedGateId"))
    except ValueError:
        return ["revision-bound v1 transition gate is unavailable"]
    same_distribution = (
        prior_program.get("distributionVersion") == program.get("distributionVersion")
    )
    gate_transition = (
        prior.get("closedGateId") == node.get("closedGateId")
        or prior.get("nextGateId") == node.get("closedGateId")
    ) if same_distribution else (
        prior.get("nextGateId") is None and closed_index == 0
        and _snapshot_v1_semantic_version_precedence(
            prior_program.get("distributionVersion")
        )
        is not None
        and _snapshot_v1_semantic_version_precedence(
            program.get("distributionVersion")
        )
        is not None
        and _snapshot_v1_semantic_version_precedence(
            program.get("distributionVersion")
        ) > _snapshot_v1_semantic_version_precedence(
            prior_program.get("distributionVersion")
        )
    )
    expected_prior_next = prior_gate_ids[prior_index + 1] \
        if prior_index < len(prior_gate_ids) - 1 else None
    if not gate_transition or prior.get("nextGateId") != expected_prior_next:
        errors.append("revision-bound v1 predecessor gate transition is invalid")
    transition = node.get("acceptanceTransition", {})
    if transition.get("kind") == "unchanged" and prior.get(
        "evaluationContractSha256"
    ) != node.get("evaluationContractSha256"):
        errors.append("revision-bound v1 unchanged evaluation contract drifted")
    prior_items = prior_acceptance.get("criteria")
    current_items = acceptance.get("criteria")
    if not isinstance(prior_items, list) or not isinstance(current_items, list):
        return errors + ["revision-bound v1 predecessor criteria are invalid"]
    old = {item.get("id"): item for item in prior_items if isinstance(item, dict)}
    new = {item.get("id"): item for item in current_items if isinstance(item, dict)}
    actual_affected = {
        item_id for item_id in set(old) | set(new)
        if old.get(item_id) != new.get(item_id)
    }
    if _snapshot_v1_transition_projection(
        root, prior_revision, prior_program, prior_acceptance,
        prior_guidance, prior_constitution, prior_golden,
    ) != _snapshot_v1_transition_projection(
        root, current_revision, program, acceptance, guidance,
        constitution, golden,
    ):
        actual_affected.update(set(old) | set(new))
    if set(transition.get("affectedCriterionIds", [])) != actual_affected:
        errors.append("revision-bound v1 affected criteria are invalid")
    return errors


def _snapshot_v1_lineage_errors(
    root, origin, node, revisions, lineage, cache,
):
    if not isinstance(lineage, (list, tuple)) or not isinstance(cache, dict):
        return ["revision-bound v1 lineage state is invalid"]
    if len(lineage) >= _SNAPSHOT_V1_MAX_LINEAGE_DEPTH:
        return ["revision-bound v1 lineage exceeds supported depth"]
    if (
        not isinstance(origin, str)
        or _SNAPSHOT_V1_REVISION_RE.fullmatch(origin) is None
        or not isinstance(revisions, (list, tuple))
        or not revisions
        or any(
            not isinstance(revision, str)
            or _SNAPSHOT_V1_REVISION_RE.fullmatch(revision) is None
            for revision in revisions
        )
        or not isinstance(node, dict)
    ):
        return ["revision-bound v1 lineage identity is invalid"]
    if origin in lineage:
        return ["revision-bound v1 lineage contains a cycle"]
    try:
        node_key = _snapshot_v1_node_key(node)
    except _SNAPSHOT_V1_FAILURES:
        return ["revision-bound v1 lineage node is malformed"]
    key = (
        "snapshot-v1-lineage", origin, node_key, tuple(revisions),
    )
    if key in cache:
        return [] if cache[key] else ["revision-bound v1 lineage is invalid"]
    errors = []
    try:
        documents = _snapshot_v1_documents(root, origin)
        constitution, program, acceptance, guidance, golden = documents
        historical = program.get("increment", {}).get("closeoutSnapshot")
        if historical != node or not revisions or revisions[-1] != origin:
            raise ValueError("revision-bound v1 origin is not canonical")
        errors.extend(_snapshot_v1_node_errors(program, acceptance))
        expected = _snapshot_v1_binding_state(
            root, program, acceptance, guidance, constitution, golden, origin,
        )
        frozen, valid = _snapshot_v1_run_status(
            root, expected, revisions, cache,
        )
        if not frozen or not valid:
            errors.append("revision-bound v1 carry run is invalid")
        canonical, latest, replay, _ = _snapshot_v1_lineage(
            root, node, origin, cache,
        )
        if canonical != origin or replay:
            errors.append("revision-bound v1 canonical origin is invalid")
    except _SNAPSHOT_V1_FAILURES:
        cache[key] = False
        return ["revision-bound v1 lineage is unavailable"]
    transition = node.get("acceptanceTransition", {})
    predecessor = node.get("predecessorSnapshotRef")
    if transition.get("kind") == "snapshot-bootstrap":
        if latest is not None:
            errors.append("revision-bound v1 bootstrap has a predecessor")
    else:
        match = re.fullmatch(
            r"([0-9a-f]{40}):product/program\.json#/increment/closeoutSnapshot",
            predecessor or "",
        )
        if match is None or latest is None or match.group(1) != latest[0]:
            errors.append("revision-bound v1 predecessor origin is invalid")
        else:
            prior_origin, prior_node, prior_revisions = latest
            try:
                prior_documents = _snapshot_v1_documents(root, prior_origin)
                errors.extend(_snapshot_v1_transition_errors(
                    root, origin, prior_origin,
                    program, acceptance, guidance, constitution, golden,
                    prior_documents[1], prior_documents[2], prior_documents[3],
                    prior_documents[0], prior_documents[4],
                ))
            except _SNAPSHOT_V1_FAILURES:
                errors.append("revision-bound v1 predecessor is unavailable")
            errors.extend(_snapshot_v1_lineage_errors(
                root, prior_origin, prior_node, prior_revisions,
                (*lineage, origin), cache,
            ))
    cache[key] = not errors
    return errors


def _snapshot_v2_transition_errors(current, predecessor):
    errors = []
    if not isinstance(current, dict) or not isinstance(predecessor, dict):
        return ["revision-bound v2 transition nodes are unavailable"]
    prior_schema = predecessor.get("schema")
    prior_state = predecessor.get("state")
    prior_gate = predecessor.get("gateId") \
        if prior_schema == _SNAPSHOT_V2_SCHEMA else predecessor.get("closedGateId")
    if current.get("gateId") != prior_gate:
        errors.append("revision-bound v2 predecessor gate is invalid")
    if current.get("state") == "reopened":
        if prior_state != "closed" or prior_schema not in {
            _SNAPSHOT_V1_SCHEMA, _SNAPSHOT_V2_SCHEMA,
        }:
            errors.append("revision-bound v2 reopen transition is invalid")
    elif current.get("state") == "closed":
        if prior_schema != _SNAPSHOT_V2_SCHEMA or prior_state != "reopened":
            errors.append("revision-bound v2 close transition is invalid")
        current_replay = current.get("replay")
        prior_replay = predecessor.get("replay")
        if (
            not isinstance(current_replay, dict)
            or not isinstance(prior_replay, dict)
            or {
                key: current_replay.get(key) for key in (
                    "earliestAffectedBoundary", "invalidatedTaskIds",
                    "preservedTaskIds",
                )
            } != {
                key: prior_replay.get(key) for key in (
                    "earliestAffectedBoundary", "invalidatedTaskIds",
                    "preservedTaskIds",
                )
            }
        ):
            errors.append("revision-bound v2 replay scope drifted before close")
    return errors


def _snapshot_v2_lineage_errors(
    root, origin, node, revisions, lineage, cache,
):
    if not isinstance(lineage, (list, tuple)) or not isinstance(cache, dict):
        return ["revision-bound v2 lineage state is invalid"]
    if len(lineage) >= _SNAPSHOT_V1_MAX_LINEAGE_DEPTH:
        return ["revision-bound v2 lineage exceeds supported depth"]
    if (
        not isinstance(origin, str)
        or _SNAPSHOT_V1_REVISION_RE.fullmatch(origin) is None
        or not isinstance(revisions, (list, tuple)) or not revisions
        or any(_SNAPSHOT_V1_REVISION_RE.fullmatch(item or "") is None
               for item in revisions)
        or not isinstance(node, dict)
    ):
        return ["revision-bound v2 lineage identity is invalid"]
    if origin in lineage:
        return ["revision-bound v2 lineage contains a cycle"]
    key = (
        "snapshot-v2-lineage", origin, _snapshot_v1_node_key(node),
        tuple(revisions),
    )
    if key in cache:
        return [] if cache[key] else ["revision-bound v2 lineage is invalid"]
    errors = []
    try:
        documents = _snapshot_v1_documents(root, origin)
        program, acceptance = documents[1], documents[2]
        historical = program.get("increment", {}).get("closeoutSnapshot")
        if historical != node or revisions[-1] != origin:
            raise ValueError("revision-bound v2 origin is not canonical")
        errors.extend(_snapshot_v2_node_errors(program, acceptance))
        expected = _snapshot_v1_binding_state(
            root, program, acceptance, documents[3], documents[0],
            documents[4], origin,
        )
        frozen, valid = _snapshot_v1_run_status(
            root, expected, revisions, cache,
        )
        if not frozen or not valid:
            errors.append("revision-bound v2 carry run is invalid")
        canonical, latest, replay, _ = _snapshot_v1_lineage(
            root, node, origin, cache,
        )
        if canonical != origin or replay:
            errors.append("revision-bound v2 canonical origin is invalid")
    except _SNAPSHOT_V1_FAILURES:
        cache[key] = False
        return ["revision-bound v2 lineage is unavailable"]
    predecessor_ref = node.get("predecessorSnapshotRef")
    match = re.fullmatch(
        r"([0-9a-f]{40}):product/program\.json#/increment/closeoutSnapshot",
        predecessor_ref or "",
    )
    if match is None or latest is None or match.group(1) != latest[0]:
        errors.append("revision-bound v2 predecessor origin is invalid")
    else:
        prior_origin, prior_node, prior_revisions = latest
        errors.extend(_snapshot_v2_transition_errors(node, prior_node))
        errors.extend(_snapshot_lineage_contract_errors(
            root, prior_origin, prior_node, prior_revisions,
            (*lineage, origin), cache,
        ))
    cache[key] = not errors
    return errors


def _snapshot_lineage_contract_errors(
    root, origin, node, revisions, lineage, cache,
):
    try:
        schema = node.get("schema") if isinstance(node, dict) else None
        if schema == _SNAPSHOT_V1_SCHEMA:
            return _snapshot_v1_lineage_errors(
                root, origin, node, revisions, lineage, cache,
            )
        if schema == _SNAPSHOT_V2_SCHEMA:
            return _snapshot_v2_lineage_errors(
                root, origin, node, revisions, lineage, cache,
            )
        return [f"unsupported revision-bound snapshot schema: {schema!r}"]
    except _SNAPSHOT_V1_IO_EXCEPTIONS:
        return ["revision-bound snapshot lineage is unavailable"]
    except _SNAPSHOT_V1_STRUCTURE_EXCEPTIONS:
        return ["revision-bound snapshot lineage is malformed"]


def _snapshot_v1_transition_projection(
    root, revision, program, acceptance, guidance, constitution, golden,
):
    if any(not isinstance(item, dict) for item in (
        program, acceptance, guidance, constitution, golden,
    )):
        raise TypeError("revision-bound v1 document is not an object")
    increment = program.get("increment")
    if not isinstance(increment, dict):
        raise TypeError("revision-bound v1 increment is not an object")
    normalized_increment = dict(increment)
    normalized_increment.pop("closeoutSnapshot", None)
    normalized_program = dict(program)
    normalized_program["increment"] = normalized_increment
    normalized_acceptance = dict(acceptance)
    normalized_acceptance.pop("criteria", None)
    projections = program.get("hostProjections")
    if not isinstance(projections, list):
        raise TypeError("revision-bound v1 host projections are not a list")
    marketplaces = {}
    for projection in projections:
        locator = projection.get("marketplace") \
            if isinstance(projection, dict) else None
        if not _nonempty_string(locator):
            raise TypeError("revision-bound v1 marketplace locator is invalid")
        marketplaces[locator] = sha256(_snapshot_or_worktree_bytes(
            root, locator, revision,
        )).hexdigest()
    return {
        "constitution": constitution,
        "program": normalized_program,
        "acceptance": normalized_acceptance,
        "guidance": guidance,
        "golden": golden,
        "marketplaceDigests": marketplaces,
    }


def _validate_closeout_snapshot_v2(
    root, program, acceptance, evaluation_digest, errors,
    revision=None, lineage=(), cache=None,
):
    cache = {} if cache is None else cache
    node = program.get("increment", {}).get("closeoutSnapshot") \
        if isinstance(program.get("increment"), dict) else None
    errors.extend(_snapshot_v2_node_errors(program, acceptance))
    if not isinstance(node, dict):
        return
    if node.get("evaluationContractSha256") != evaluation_digest:
        errors.append("increment.closeoutSnapshot evaluation contract drifted")
    try:
        origin, latest, replay, current_run = _snapshot_v1_lineage(
            root, node, revision or "HEAD", cache,
        )
    except _SNAPSHOT_V1_FAILURES:
        errors.append("increment.closeoutSnapshot predecessor lineage is unavailable")
        return
    if replay:
        errors.append("increment.closeoutSnapshot lineage replays a non-current node")
    match = re.fullmatch(
        r"([0-9a-f]{40}):product/program\.json#/increment/closeoutSnapshot",
        node.get("predecessorSnapshotRef") or "",
    )
    if latest is None or match is None or match.group(1) != latest[0]:
        errors.append("increment.closeoutSnapshot predecessor is not latest accepted snapshot")
        return
    errors.extend(_snapshot_v2_transition_errors(node, latest[1]))
    errors.extend(_snapshot_lineage_contract_errors(
        root, latest[0], latest[1], latest[2], lineage, cache,
    ))
    if origin is not None:
        errors.extend(_snapshot_v2_lineage_errors(
            root, origin, node, current_run, lineage, cache,
        ))


def _validate_closeout_snapshot(
    root, program, acceptance, criterion_ids, evaluation_digest, errors,
    _revision=None, _lineage=(), _cache=None,
):
    _cache = {} if _cache is None else _cache
    increment = program.get("increment", {})
    value = increment.get("closeoutSnapshot")
    if isinstance(value, dict) and value.get("schema") == _SNAPSHOT_V2_SCHEMA:
        _validate_closeout_snapshot_v2(
            root, program, acceptance, evaluation_digest, errors,
            _revision, _lineage, _cache,
        )
        return
    fields = set((
        "schema id stage state revisionBinding predecessorSnapshotRef authorityRefs "
        "surfaceRefs evidenceRefs evidenceCutoff invalidationTriggerRefs "
        "acceptanceTransition evaluationContractSha256 closedGateId nextGateId "
        "claimCeilingRef unknownsRef"
    ).split())
    if not isinstance(value, dict) or set(value) != fields:
        errors.append("increment.closeoutSnapshot shape is invalid")
        return
    if value.get("schema") != _SNAPSHOT_V1_SCHEMA or value.get(
        "id"
    ) != f"stage.{program.get('distributionVersion')}.{value.get('stage')}.closed":
        errors.append("increment.closeoutSnapshot schema is invalid")
    _require_texts(
        value, ("id", "stage", "state", "closedGateId",
                "claimCeilingRef", "unknownsRef"),
        "increment.closeoutSnapshot", errors,
    )
    binding = value.get("revisionBinding")
    if binding != {
        "kind": "containing-git-commit",
        "selfLocator": "product/program.json#/increment/closeoutSnapshot",
        "exactLocatorRule": "After commit, prefix selfLocator with the immutable containing commit SHA; never store that SHA inside this object.",
    }:
        errors.append("increment.closeoutSnapshot revision binding is invalid")
    if value.get("authorityRefs") != list(_SNAPSHOT_V1_AUTHORITY_REFS):
        errors.append("increment.closeoutSnapshot authority references are invalid")
    if value.get("surfaceRefs") != {
        "baseline": "product/reshaping-guidance.json#/wholeSystemBalanceReview",
        "plan": "product/program.json#/increment/fourSurfaceMapping/plan",
        "process": "product/program.json#/increment/fourSurfaceMapping/process",
        "acceptance": "product/acceptance.json",
        "goalProjection": "product/program.json#/goalModePrompt",
    }:
        errors.append("increment.closeoutSnapshot surface references are invalid")
    gates = program.get("releaseProcedure", {}).get("orderedGates", [])
    gate_ids = [item.get("id") for item in gates if isinstance(item, dict)]
    if gate_ids != [gate_id for gate_id, _ in GATE_SEQUENCE]:
        errors.append("increment.closeoutSnapshot release gate sequence is invalid")
    closed = value.get("closedGateId")
    try:
        closed_index = gate_ids.index(closed)
    except ValueError:
        closed_index = -1
    if value.get("evidenceRefs") != [
        "product/program.json#/inputEvidence",
        "product/acceptance.json#/criteria",
        _SNAPSHOT_V1_GOLDEN_TASKS_FILE,
        f"product/program.json#/releaseProcedure/orderedGates/{closed_index}",
    ]:
        errors.append("increment.closeoutSnapshot evidence references are invalid")
    cutoff = value.get("evidenceCutoff")
    if cutoff != {
        "kind": "containing-git-commit",
        "rule": "Only evidenceRefs resolved inside the immutable containing commit belong to this snapshot; later repository or task-time facts require a successor node.",
    }:
        errors.append("increment.closeoutSnapshot evidence cutoff is invalid")
    if value.get("invalidationTriggerRefs") != [
        "product/constitution.json#/evolutionPolicy/feedbackRule",
        "product/program.json#/goalModePrompt/refreshTriggers",
        "product/program.json#/processLossControl/correctionRule",
    ]:
        errors.append("increment.closeoutSnapshot invalidation triggers are invalid")
    transition = value.get("acceptanceTransition")
    if not isinstance(transition, dict) or set(transition) != {
        "kind", "rationaleRef", "affectedCriterionIds", "replayRef",
    } or transition.get("kind") not in {
        "snapshot-bootstrap", "unchanged", "changed",
    } or transition.get("rationaleRef") != (
        "product/program.json#/increment/fourSurfaceMapping/plan"
    ) or transition.get("replayRef") != (
        "product/program.json#/increment/fourSurfaceMapping/process/orderedSteps"
    ):
        errors.append("increment.closeoutSnapshot acceptance transition is invalid")
    predecessor = value.get("predecessorSnapshotRef")
    kind = transition.get("kind") if isinstance(transition, dict) else None
    actual_affected = None
    predecessor_match = re.fullmatch(
        r"([0-9a-f]{40}):product/program\.json#/increment/closeoutSnapshot",
        predecessor or "",
    )
    if (predecessor is None) != (kind == "snapshot-bootstrap") or (
        predecessor is not None and predecessor_match is None
    ):
        errors.append("increment.closeoutSnapshot predecessor is invalid")
    try:
        current_constitution, _, _, current_guidance, current_golden = (
            _snapshot_v1_documents(root, _revision)
        )
        context_errors = []
        _validate_stage_guidance(current_guidance, context_errors)
        if context_errors:
            errors.append("increment.closeoutSnapshot stage guidance is invalid")
    except _SNAPSHOT_V1_FAILURES:
        current_constitution, current_guidance, current_golden = {}, {}, {}
        errors.append("increment.closeoutSnapshot bound state is unavailable")
    try:
        origin, latest, replay, current_run = _snapshot_v1_lineage(
            root, value, _revision or "HEAD", _cache,
        )
    except _SNAPSHOT_V1_FAILURES:
        origin, latest, replay, current_run = None, None, False, ()
        errors.append("increment.closeoutSnapshot predecessor lineage is unavailable")
    if replay:
        errors.append("increment.closeoutSnapshot lineage replays a non-current node")
    if origin is not None:
        try:
            origin_constitution, origin_program, origin_acceptance, \
                origin_guidance, origin_golden = _snapshot_v1_documents(root, origin)
            origin_state = _snapshot_v1_binding_state(
                root, origin_program, origin_acceptance, origin_guidance,
                origin_constitution, origin_golden, origin,
            )
            current_frozen, current_contract_valid = _snapshot_v1_run_status(
                root, origin_state, current_run, _cache,
            )
            if _snapshot_v1_binding_state(
                root, program, acceptance, current_guidance,
                current_constitution, current_golden, _revision,
            ) != origin_state or not current_frozen:
                errors.append(
                    "increment.closeoutSnapshot snapshot-bound state drifted without successor"
                )
            if not current_contract_valid:
                errors.append(
                    "increment.closeoutSnapshot revision-bound repository contract is invalid"
                )
        except _SNAPSHOT_V1_FAILURES:
            errors.append("increment.closeoutSnapshot origin state is unavailable")
    if kind == "snapshot-bootstrap":
        if latest is not None:
            errors.append("increment.closeoutSnapshot bootstrap breaks predecessor lineage")
    elif predecessor_match is not None:
        revision = predecessor_match.group(1)
        latest_revision = latest[0] if latest is not None else None
        if revision != latest_revision:
            errors.append("increment.closeoutSnapshot predecessor is not latest accepted snapshot")
            prior_constitution, prior_program, prior_acceptance, prior_guidance, \
                prior_golden = {}, {}, {}, {}, {}
        else:
            try:
                prior_constitution, prior_program, prior_acceptance, \
                    prior_guidance, prior_golden = _snapshot_v1_documents(
                        root, revision,
                    )
                prior_node = prior_program.get("increment", {}).get("closeoutSnapshot")
                if latest is None or prior_node != latest[1]:
                    raise ValueError("predecessor origin does not contain the lineage node")
            except _SNAPSHOT_V1_FAILURES:
                prior_constitution, prior_program, prior_acceptance, prior_guidance, \
                    prior_golden = {}, {}, {}, {}, {}
        prior_increment = prior_program.get("increment") \
            if isinstance(prior_program, dict) else None
        prior = prior_increment.get("closeoutSnapshot") \
            if isinstance(prior_increment, dict) else None
        prior_binding = prior.get("revisionBinding") if isinstance(prior, dict) else None
        prior_gates = prior_program.get("releaseProcedure", {}).get("orderedGates", []) \
            if isinstance(prior_program.get("releaseProcedure"), dict) else []
        prior_gate_ids = [item.get("id") for item in prior_gates if isinstance(item, dict)]
        prior_closed = prior.get("closedGateId") if isinstance(prior, dict) else None
        try:
            prior_index = prior_gate_ids.index(prior_closed)
        except ValueError:
            prior_index = -1
        prior_next = prior_gate_ids[prior_index + 1] \
            if 0 <= prior_index < len(prior_gate_ids) - 1 else None
        try:
            prior_evaluation = _snapshot_v1_evaluation_digest(
                prior_acceptance, prior_golden,
            ) if isinstance(prior, dict) and prior.get("schema") == (
                "yiyuan-accord-stage-closeout-snapshot/v1"
            ) else representative_contract_sha256(prior_acceptance, prior_golden)
        except _SNAPSHOT_V1_FAILURES:
            prior_evaluation = None
        prior_items = prior_acceptance.get("criteria") \
            if isinstance(prior_acceptance, dict) else None
        prior_ids = {
            item.get("id") for item in prior_items or []
            if isinstance(item, dict) and _nonempty_string(item.get("id"))
        }
        prior_valid = False
        try:
            prior_state = _snapshot_v1_binding_state(
                root, prior_program, prior_acceptance, prior_guidance,
                prior_constitution, prior_golden, revision,
            )
            prior_run_frozen, prior_run_contract_valid = _snapshot_v1_run_status(
                root, prior_state, latest[2], _cache,
            ) if latest is not None else (False, False)
        except _SNAPSHOT_V1_FAILURES:
            prior_run_frozen, prior_run_contract_valid = False, False
        if revision == latest_revision and prior_evaluation is not None \
                and isinstance(prior_items, list) and len(prior_ids) == len(prior_items) \
                and prior_run_frozen and prior_run_contract_valid \
                and revision not in _lineage:
            prior_valid = not _snapshot_lineage_contract_errors(
                root, revision, latest[1], latest[2], _lineage, _cache,
            )
        if not prior_valid:
            errors.append(
                "increment.closeoutSnapshot predecessor is not a valid revision-bound snapshot node"
            )
        prior_distribution = prior_program.get("distributionVersion")
        current_distribution = program.get("distributionVersion")
        same_distribution = prior_distribution == current_distribution
        prior_precedence = _snapshot_v1_semantic_version_precedence(
            prior_distribution,
        )
        current_precedence = _snapshot_v1_semantic_version_precedence(
            current_distribution,
        )
        gate_transition = (
            prior.get("closedGateId") == value.get("closedGateId")
            or prior.get("nextGateId") == value.get("closedGateId")
        ) if same_distribution and isinstance(prior, dict) else (
            isinstance(prior, dict) and prior.get("nextGateId") is None
            and closed_index == 0 and prior_precedence is not None
            and current_precedence is not None and current_precedence > prior_precedence
        )
        if not isinstance(prior, dict) or prior.get("state") != "closed" \
                or not gate_transition or not isinstance(prior_binding, dict) \
                or prior_binding.get("selfLocator") != (
            "product/program.json#/increment/closeoutSnapshot"
        ) or prior_index < 0 or prior.get("nextGateId") != prior_next \
                or prior.get("evaluationContractSha256") != prior_evaluation:
            errors.append("increment.closeoutSnapshot predecessor cannot be resolved")
        elif kind == "unchanged" and prior.get(
            "evaluationContractSha256"
        ) != evaluation_digest:
            errors.append("increment.closeoutSnapshot unchanged contract drifted")
        current_items = acceptance.get("criteria") if isinstance(acceptance, dict) else None
        if isinstance(prior_items, list) and isinstance(current_items, list) and all(
            isinstance(item, dict) and _nonempty_string(item.get("id"))
            for item in prior_items + current_items
        ):
            old = {item["id"]: item for item in prior_items}
            new = {item["id"]: item for item in current_items}
            actual_affected = {
                item_id for item_id in set(old) | set(new) if old.get(item_id) != new.get(item_id)
            }
            try:
                transition_changed = _snapshot_v1_transition_projection(
                    root, revision, prior_program, prior_acceptance,
                    prior_guidance, prior_constitution, prior_golden,
                ) != _snapshot_v1_transition_projection(
                    root, _revision, program, acceptance, current_guidance,
                    current_constitution, current_golden,
                )
            except _SNAPSHOT_V1_FAILURES:
                transition_changed = True
                errors.append(
                    "increment.closeoutSnapshot transition state is unavailable"
                )
            if transition_changed:
                actual_affected.update(set(old) | set(new))
        else:
            errors.append("increment.closeoutSnapshot predecessor acceptance is invalid")
    affected_list = _string_list(transition.get("affectedCriterionIds")) \
        if isinstance(transition, dict) else None
    affected = set(affected_list or ())
    if affected_list is None or (
        kind == "snapshot-bootstrap" and affected != criterion_ids
    ) or (kind == "unchanged" and affected) or (kind == "changed" and not affected) or (
        kind in {"unchanged", "changed"}
        and (actual_affected is None or affected != actual_affected)
    ):
        errors.append("increment.closeoutSnapshot affected criteria are invalid")
    if value.get("evaluationContractSha256") != evaluation_digest:
        errors.append("increment.closeoutSnapshot evaluation contract drifted")
    if value.get("claimCeilingRef") != "product/acceptance.json#/claimCeiling" or value.get(
        "unknownsRef"
    ) != "product/program.json#/increment/hostCapabilityRefresh/unknowns":
        errors.append("increment.closeoutSnapshot claim and unknown references are invalid")
    expected_next = gate_ids[closed_index + 1] \
        if 0 <= closed_index < len(gate_ids) - 1 else None
    if value.get("state") != "closed" or value.get("stage") != closed \
            or closed_index < 0 or value.get("nextGateId") != expected_next:
        errors.append("increment.closeoutSnapshot gate transition is invalid")


def _exact_package_subject_files(root, program, errors, revision=None):
    declared = set()
    projections = program.get("hostProjections") \
        if isinstance(program, dict) else None
    if not isinstance(projections, list):
        return declared
    for projection in projections:
        if not isinstance(projection, dict):
            continue
        for field in ("marketplace", "manifest", "contract", "skill"):
            locator = projection.get(field)
            if isinstance(locator, str):
                declared.add(locator)
        for field in ("metadataFiles", "legalFiles", "mechanismFiles"):
            value = projection.get(field)
            if isinstance(value, list):
                declared.update(item for item in value if isinstance(item, str))
        manifest_locator = projection.get("manifest")
        try:
            manifest = _snapshot_json(root, manifest_locator, revision)
        except _SNAPSHOT_V1_FAILURES:
            errors.append("exact package lifecycle manifest is unavailable")
            continue
        interface = manifest.get("interface") if isinstance(manifest, dict) else None
        for field in ("composerIcon", "logo"):
            value = interface.get(field) if isinstance(interface, dict) else None
            if isinstance(value, str) and value.startswith("./assets/"):
                declared.add((
                    Path(manifest_locator).parent.parent / value[2:]
                ).as_posix())
    return declared


def _validate_exact_package_evidence_lifecycle(
    root, program, errors, revision=None,
):
    increment = program.get("increment") if isinstance(program, dict) else None
    lifecycle = increment.get("exactPackageEvidenceLifecycle") \
        if isinstance(increment, dict) else None
    fields = {
        "schema", "state", "taskId", "earliestAffectedBoundary",
        "subjectBinding", "preservedTaskIds", "priorEvidenceRef", "evidence",
    }
    if not isinstance(lifecycle, dict) or set(lifecycle) != fields:
        errors.append("exact package evidence lifecycle is invalid")
        return
    if (
        lifecycle.get("schema")
        != "yiyuan-accord-exact-package-evidence-lifecycle/v1"
        or lifecycle.get("state") not in {"pending", "verified"}
        or lifecycle.get("taskId") != "GT-20"
        or lifecycle.get("earliestAffectedBoundary")
        != "complete-host-projection-package-identity"
        or lifecycle.get("subjectBinding")
        != "containing-git-commit-complete-declared-packages"
        or lifecycle.get("preservedTaskIds") != ["GT-21"]
        or lifecycle.get("priorEvidenceRef") != (
            "evals/evidence/2026-08-30-v310-gt20-21-source.json"
            "#/records/GT-20-transactional-lifecycle-4c8bcc3"
        )
    ):
        errors.append("exact package evidence lifecycle contract is invalid")
    try:
        golden = _snapshot_json(root, GOLDEN_TASKS_FILE, revision)
    except _SNAPSHOT_V1_FAILURES:
        golden = {}
        errors.append("exact package lifecycle Golden Tasks are unavailable")
    tasks = golden.get("tasks") if isinstance(golden, dict) else None
    gt20 = next((item for item in tasks or [] if isinstance(item, dict)
                 and item.get("id") == "GT-20"), {})
    subjects = gt20.get("behaviorSubjectFiles")
    declared = _exact_package_subject_files(root, program, errors, revision)
    if (
        not isinstance(subjects, list) or len(subjects) != len(set(subjects))
        or set(subjects) != declared
    ):
        errors.append("exact package lifecycle GT-20 subject is invalid")
    snapshot = increment.get("closeoutSnapshot") \
        if isinstance(increment, dict) else None
    if lifecycle.get("state") == "pending":
        if (
            lifecycle.get("evidence") is not None
            or not isinstance(snapshot, dict) or snapshot.get("state") != "reopened"
            or program.get("status") != "active"
        ):
            errors.append("exact package evidence pending state is invalid")
        return
    evidence = lifecycle.get("evidence")
    predecessor_revision = snapshot.get("predecessorSnapshotRef", "").split(
        ":", 1,
    )[0] if isinstance(snapshot, dict) else None
    if (
        not isinstance(evidence, dict)
        or set(evidence) != {"locator", "sha256", "evaluatedRevision"}
        or not _nonempty_string(evidence.get("locator"))
        or SHA256_RE.fullmatch(evidence.get("sha256") or "") is None
        or REVISION_RE.fullmatch(evidence.get("evaluatedRevision") or "") is None
        or evidence.get("evaluatedRevision") != predecessor_revision
        or not isinstance(snapshot, dict) or snapshot.get("state") != "closed"
        or program.get("status") != "ready"
    ):
        errors.append("exact package evidence verified state is invalid")
        return
    try:
        raw = _snapshot_or_worktree_bytes(root, evidence["locator"], revision)
        record = _strict_json_object(raw)
    except _SNAPSHOT_V1_FAILURES:
        errors.append("exact package evidence record is unavailable")
        return
    if sha256(raw).hexdigest() != evidence.get("sha256"):
        errors.append("exact package evidence record digest mismatch")
    packages = {
        item.get("id"): item.get("packageSha256")
        for item in program.get("hostProjections", []) if isinstance(item, dict)
    }
    commands = record.get("commands")
    expected_command_digest = (
        "0e3614bb42d1a4eda9c6b0bb4e8d291f95878084e8a5eff4f17e5e562441d266"
    )
    command_contract = (
        isinstance(commands, list) and len(commands) == 29
        and sha256(json.dumps(
            commands, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest() == expected_command_digest
    )
    fixture = record.get("fixture")
    fixed_fixture = {
        "platform": "windows", "priorVersion": "3.0.1", "targetVersion": "3.1.0",
        "userStatePreserved": True, "concurrentEditsPreserved": True,
        "foreignStatePreserved": True, "credentialsRead": False,
        "sessionsRead": False, "modelTurns": 0,
        "sourceFailureMode": "registered-source-package-path-absent",
        "codexUpdateMechanism": "plugin-add-replaces-installed-version",
        "claudeUpdateMechanism": "plugin-update", "rollbackBytesMatchPriorRelease": True,
        "installedBytesMatchDeclaredPackages": True, "startupHookSilent": True,
        "resumeHookTypedContext": True,
    }
    versions = ("codexCliVersion", "claudeCliVersion", "nodeVersion")
    counts = ("codexInstalledFileCount", "claudeInstalledFileCount")
    fixture_contract = (
        isinstance(fixture, dict) and set(fixture) == set(fixed_fixture) | set(versions) | set(counts)
        and all(fixture.get(key) == value for key, value in fixed_fixture.items())
        and command_contract
        and all(fixture.get(key) == commands[index]["stdout"].strip()
                for key, index in zip(versions, (4, 5, 6)))
        and all(isinstance(fixture.get(key), int) and not isinstance(fixture[key], bool)
                and fixture[key] > 0 for key in counts)
    )
    post_state = record.get("postState")
    cache_fields = ("codexCacheFiles", "claudeCacheFiles")
    fixed_post = {"codexInstalledEntries": 0, "claudeInstalledEntries": 0,
                  "taskProcesses": 0, "taskRootRemoved": True}
    post_contract = (
        isinstance(post_state, dict) and set(post_state) == set(fixed_post) | set(cache_fields)
        and all(post_state.get(key) == value for key, value in fixed_post.items())
        and all(isinstance(post_state.get(key), list)
                and all(_nonempty_string(item) for item in post_state[key])
                and len(post_state[key]) == len(set(post_state[key]))
                for key in cache_fields)
    )
    subject_map = record.get("behaviorSubject")
    subject_contract = (
        isinstance(subject_map, dict) and set(subject_map) == set(subjects or [])
        and all(_nonempty_string(locator)
                and isinstance(digest, str) and SHA256_RE.fullmatch(digest) is not None
                for locator, digest in subject_map.items())
    )
    try:
        runner_digest = sha256(_snapshot_or_worktree_bytes(
            root, "scripts/run-gt20-exact-package.ps1", revision,
        )).hexdigest()
    except _SNAPSHOT_V1_FAILURES:
        runner_digest = None
    if (
        set(record) != {
            "schema", "taskId", "evaluatedRevision", "packageSha256",
            "behaviorSubject", "lifecycle", "claimLimit", "runnerSha256",
            "fixture", "commands", "postState",
        }
        or record.get("schema") != "yiyuan-accord-gt20-exact-package-evidence/v1"
        or record.get("taskId") != "GT-20"
        or record.get("evaluatedRevision") != evidence.get("evaluatedRevision")
        or record.get("runnerSha256") != runner_digest
        or record.get("packageSha256") != packages
        or not subject_contract
        or record.get("lifecycle") != {
            "install": "verified",
            "failedUpdateRollback": "verified",
            "successfulUpdate": "verified",
            "activation": "verified",
            "remove": "verified",
            "postState": "verified",
            "cleanup": "verified",
        }
        or record.get("claimLimit") != (
            "Bounded zero-model Windows lifecycle evidence for exact Commit A "
            "Codex and Claude package bytes in disposable non-empty scopes; "
            "production, unmanaged or cross-OS hosts, ordinary model behavior, "
            "product value and release readiness remain unclaimed."
        )
        or not fixture_contract
        or not command_contract
        or not post_contract
    ):
        errors.append("exact package evidence record contract is invalid")
        return
    try:
        for locator, digest in record["behaviorSubject"].items():
            evaluated = sha256(_snapshot_bytes(
                root, locator, evidence["evaluatedRevision"],
            )).hexdigest()
            candidate = sha256(_snapshot_or_worktree_bytes(
                root, locator, revision,
            )).hexdigest()
            if evaluated != digest or candidate != digest:
                raise ValueError("subject digest mismatch")
    except _SNAPSHOT_V1_FAILURES:
        errors.append("exact package evidence subject binding is invalid")


def _validate_program(
    root, program, acceptance, criterion_ids, all_contract_ids, identity, authority,
    goal_digest, required_task_ids, evaluation_digest, errors,
    revision=None, validate_snapshot=True,
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

    _validate_input_evidence(root, program, errors, revision)
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
        if validate_snapshot:
            _validate_closeout_snapshot(
                root, program, acceptance, set(criterion_ids), evaluation_digest,
                errors, revision,
            )
        _validate_exact_package_evidence_lifecycle(
            root, program, errors, revision,
        )

    prompt = program.get("goalModePrompt")
    errors.extend(release_procedure_errors(
        root, program, authority, set(criterion_ids), prompt, goal_digest,
        required_task_ids,
        (lambda locator: _snapshot_bytes(root, locator, revision).decode("utf-8"))
        if revision is not None else None,
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
        _require_texts(
            process,
            ("currentStageRule", "stageSnapshotState", "stageSnapshotRule",
             "evolutionHorizonRule", "continuingCalibration"),
            "program.processLossControl", errors,
        )
        if process.get("stageSnapshotState") != (
            "latest-closed-stage-snapshot-prepared-for-containing-commit-binding"
        ) or not _contains_markers(process.get("currentStageRule"), (
            "current stage", "owns current execution",
            "cannot silently enter its release scope", "borrow its evidence",
        )) or not _contains_markers(process.get("stageSnapshotRule"), (
            "versioned stage projections", "containing-git-commit",
            "exact external locator", "successor cites", "Git preserves",
            "terminal release gate", "new ordered cycle", "never self-attests",
        )) or not _contains_markers(process.get("evolutionHorizonRule"), (
            "recomputed on demand", "whole-project panorama",
            "latest accepted stage snapshot", "fresh user, host and environment facts",
            "maintenance and health", "iteration", "updates", "bounded refactoring",
            "host adaptation", "retirement or replacement",
            "later outcome-driven development", "non-authoritative non-commitment",
            "next bounded increment",
        )):
            errors.append("program stage snapshot and evolution horizon rules are invalid")
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
        for field in (
            "metadataFiles", "legalFiles", "mechanismFiles", "forbiddenPaths",
        ):
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
    promotion_lanes=None, revision=None,
):
    locator = item.get("locator")
    expected = item.get("sha256")
    raw = None
    if isinstance(locator, str) and revision is None:
        path = _safe_file(root, locator, errors)
    elif isinstance(locator, str):
        try:
            raw = _snapshot_bytes(root, locator, revision)
            path = Path(locator)
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            path = None
            errors.append(f"{label} repository file is unavailable")
    else:
        path = None
    if not _nonempty_string(item.get("claim")):
        errors.append(f"{label}.claim must be a non-empty string")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        errors.append(f"{label}.sha256 is invalid")
    elif path is not None:
        actual = sha256(raw).hexdigest() if raw is not None else _hash(path, errors, label)
        if actual is not None and actual != expected:
            errors.append(f"{label} digest mismatch")
    observation = {}
    if path is not None:
        if Path(locator).parts[:2] != ("evals", "observations"):
            errors.append(f"{label} direct evidence must use evals/observations")
        if path.suffix.lower() != ".json":
            errors.append(f"{label} direct evidence must be a JSON observation")
        else:
            if raw is None:
                observation = _read_json(root, locator, errors)
            else:
                try:
                    observation = _strict_json_object(raw)
                except (UnicodeError, ValueError):
                    observation = {}
                    errors.append(f"{label} observation JSON is invalid")
            lane = promotion_lanes.get(locator) \
                if isinstance(promotion_lanes, dict) else None
            if (
                isinstance(lane, dict)
                and observation.get("taskId") == lane.get("taskId")
                and observation.get("evidenceClass") == lane.get("sourceClass")
                and lane.get("targetClass") == "representative-behavior"
            ):
                observation = {
                    **observation,
                    "evidenceClass": lane["targetClass"],
                }
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


def _validate_acceptance(
    root, acceptance, contract_ids, evidence_classes, golden, errors,
    promotion_lanes=None, revision=None, evaluation_digest=None,
):
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
                promotion_lanes,
                revision,
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
                or set(item) not in (
                    {"kind", "sha256", "preservedTaskIds", "reason"},
                    {"kind", "sha256", "sourceRevision", "preservedTaskIds", "reason"},
                )
                or item.get("kind") != "scoped-evaluation-contract-supersession"
                or not isinstance(item.get("sha256"), str)
                or not SHA256_RE.fullmatch(item["sha256"])
                or not _string_list(item.get("preservedTaskIds"))
                or not set(item["preservedTaskIds"]).issubset(set(task_mappings))
                or not _nonempty_string(item.get("reason"))
                or "sourceRevision" in item and (
                    not isinstance(item["sourceRevision"], str)
                    or not REVISION_RE.fullmatch(item["sourceRevision"])
                )
                for item in evaluation_history
            )
            or not evaluation_contract_history_valid(
                representative_policy, evaluation_digest,
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
                    root, item, label, errors, {"representative-behavior"},
                    revision=revision,
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

    errors.extend(external_release_contract_errors(
        root, acceptance,
        (lambda locator: _snapshot_bytes(root, locator, revision))
        if revision is not None else None,
    ))
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
    candidate_fields = _string_list(
        protocol.get("requiredCandidateObservationFields")
    ) or []
    if candidate_fields != ["evaluatedRevision"]:
        errors.append("golden tasks candidate observation fields are invalid")
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
        if task.get("id") in required_release_task_ids:
            subject_files = _string_list(task.get("behaviorSubjectFiles"))
            if (
                not subject_files or len(subject_files) != len(set(subject_files))
                or any(
                    Path(locator).is_absolute() or "\\" in locator
                    or any(part in {"", ".", ".."} for part in locator.split("/"))
                    for locator in subject_files
                )
            ):
                errors.append(f"{label}.behaviorSubjectFiles is invalid")
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
        "requiredCandidateObservationFields": candidate_fields,
        "behaviorEvidence": "not-established-by-static-suite",
    }


def _snapshot_v1_evaluation_digest(acceptance, golden):
    if not isinstance(acceptance, dict) or not isinstance(golden, dict):
        raise TypeError("revision-bound v1 evaluation input is not an object")
    semantic_fields = (
        "id", "class", "name", "mapsTo", "statement", "passRule",
        "requiredEvidenceClasses",
    )
    criteria = acceptance.get("criteria")
    policy = acceptance.get("representativeBehaviorPolicy")
    digest_policy = dict(policy) if isinstance(policy, dict) else policy
    if isinstance(digest_policy, dict):
        digest_policy.pop("evaluationContractHistory", None)
    claim_ceiling = acceptance.get("claimCeiling")
    claim_ceiling = claim_ceiling if isinstance(claim_ceiling, dict) else {}
    value = {
        "productId": acceptance.get("productId"),
        "release": acceptance.get("release"),
        "evidenceLanes": acceptance.get("evidenceLanes"),
        "representativeBehaviorPolicy": digest_policy,
        "claimCeiling": {
            field: claim_ceiling.get(field)
            for field in ("finiteReleaseClaims", "notImplied")
        },
        "criteria": [
            {field: item.get(field) for field in semantic_fields}
            for item in criteria if isinstance(item, dict)
            and "representative-behavior" in item.get("requiredEvidenceClasses", [])
        ] if isinstance(criteria, list) else [],
        "evaluationProtocol": golden.get("evaluationProtocol"),
        "metrics": golden.get("metrics"),
    }
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return sha256(canonical.encode()).hexdigest()


def _snapshot_v1_evaluation_history_errors(acceptance, golden):
    policy = acceptance.get("representativeBehaviorPolicy") \
        if isinstance(acceptance, dict) else None
    history = policy.get("evaluationContractHistory") \
        if isinstance(policy, dict) else None
    tasks = golden.get("tasks") if isinstance(golden, dict) else None
    task_ids = {
        item.get("id") for item in tasks if isinstance(item, dict)
        and _nonempty_string(item.get("id"))
    } if isinstance(tasks, list) else set()
    if not isinstance(history, list) or not history:
        return ["revision-bound v1 evaluation history is invalid"]
    errors, digests = [], []
    for index, item in enumerate(history):
        prefix = f"revision-bound v1 evaluation history[{index}]"
        source_revision = item.get("sourceRevision") \
            if isinstance(item, dict) else None
        fields = {
            "kind", "sha256", "preservedTaskIds", "reason",
        } | ({"sourceRevision"} if source_revision is not None else set())
        preserved = item.get("preservedTaskIds") \
            if isinstance(item, dict) else None
        if (
            not isinstance(item, dict) or set(item) != fields
            or item.get("kind") != "scoped-evaluation-contract-supersession"
            or _SNAPSHOT_V1_SHA256_RE.fullmatch(item.get("sha256") or "") is None
            or not _nonempty_string(item.get("reason"))
            or not isinstance(preserved, list) or not preserved
            or any(not _nonempty_string(task_id) for task_id in preserved)
            or len(preserved) != len(set(preserved))
            or not set(preserved).issubset(task_ids)
            or source_revision is not None and (
                not isinstance(source_revision, str)
                or _SNAPSHOT_V1_REVISION_RE.fullmatch(source_revision) is None
            )
        ):
            errors.append(f"{prefix} shape is invalid")
            continue
        digests.append(item["sha256"])
    if len(digests) != len(set(digests)):
        errors.append("revision-bound v1 evaluation history digests are not unique")
    return errors


def _snapshot_v1_evidence_errors(root, program, acceptance, revision):
    errors = []

    def validate(items, locator_field, digest_field, label, require_json=False):
        if not isinstance(items, list):
            errors.append(f"{label} is not a list")
            return
        for index, item in enumerate(items):
            prefix = f"{label}[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} is not an object")
                continue
            locator = item.get(locator_field)
            if locator is None and locator_field == "repositoryLocator":
                continue
            expected = item.get(digest_field)
            if (
                not isinstance(locator, str)
                or not isinstance(expected, str)
                or _SNAPSHOT_V1_SHA256_RE.fullmatch(expected) is None
            ):
                errors.append(f"{prefix} binding is invalid")
                continue
            try:
                raw = _snapshot_bytes(root, locator, revision)
                if sha256(raw).hexdigest() != expected:
                    errors.append(f"{prefix} digest mismatch")
                if require_json:
                    _strict_json_object(raw)
            except _SNAPSHOT_V1_FAILURES:
                errors.append(f"{prefix} repository evidence is unavailable")

    validate(
        program.get("inputEvidence"), "repositoryLocator", "repositorySha256",
        "revision-bound inputEvidence",
    )
    criteria = acceptance.get("criteria")
    if not isinstance(criteria, list):
        errors.append("revision-bound criteria are unavailable")
        return errors
    criterion_ids = []
    for index, criterion in enumerate(criteria):
        if not isinstance(criterion, dict) or not _nonempty_string(
            criterion.get("id")
        ):
            errors.append(f"revision-bound criteria[{index}] identity is invalid")
            continue
        criterion_ids.append(criterion["id"])
        if criterion.get("assessment") != "verified":
            errors.append(f"revision-bound criteria[{index}] is not verified")
        validate(
            criterion.get("evidence"), "locator", "sha256",
            f"revision-bound criteria[{index}].evidence", True,
        )
    if len(criterion_ids) != len(set(criterion_ids)):
        errors.append("revision-bound criterion ids are not unique")
    policy = acceptance.get("representativeBehaviorPolicy")
    historical = policy.get("historicalEvidence") \
        if isinstance(policy, dict) else None
    if not isinstance(historical, list) or not historical:
        errors.append("revision-bound historicalEvidence is unavailable")
    else:
        validate(
            historical, "locator", "sha256",
            "revision-bound historicalEvidence", True,
        )
    return errors


def _snapshot_v1_contract_errors(root, revision, documents):
    constitution, program, acceptance, guidance, golden = documents
    errors = list(_snapshot_v1_node_errors(program, acceptance))
    product_id = constitution.get("productId")
    if any(item.get("schema") != 3 for item in (
        constitution, program, acceptance,
    )):
        errors.append("revision-bound v1 authority schema is invalid")
    if not _nonempty_string(product_id) or {
        product_id, program.get("productId"), acceptance.get("productId"),
        guidance.get("productId"),
    } != {product_id}:
        errors.append("revision-bound v1 product identities differ")
    if (
        program.get("release") != acceptance.get("release")
        or program.get("distributionVersion") != acceptance.get("distributionVersion")
        or program.get("constitution") != _SNAPSHOT_V1_AUTHORITY_REFS[0]
        or program.get("acceptance") != _SNAPSHOT_V1_AUTHORITY_REFS[2]
        or acceptance.get("constitution") != _SNAPSHOT_V1_AUTHORITY_REFS[0]
        or acceptance.get("program") != _SNAPSHOT_V1_AUTHORITY_REFS[1]
    ):
        errors.append("revision-bound v1 authority references differ")
    identity = constitution.get("identity")
    identity_fields = {
        "displayName", "repository", "pythonModule", "pluginIds",
        "compatibilityAliases",
    }
    plugin_ids = identity.get("pluginIds") if isinstance(identity, dict) else None
    if (
        not isinstance(identity, dict) or set(identity) != identity_fields
        or not _nonempty_string(identity.get("displayName"))
        or re.fullmatch(r"https://github\.com/[^/]+/[^/]+", identity.get(
            "repository", ""
        )) is None
        or re.fullmatch(r"[a-z][a-z0-9_]*", identity.get(
            "pythonModule", ""
        )) is None
        or not isinstance(plugin_ids, list) or not plugin_ids
        or any(not _nonempty_string(item) for item in plugin_ids)
        or len(plugin_ids) != len(set(plugin_ids))
        or any(not item.startswith(f"{product_id}-") for item in plugin_ids)
        or identity.get("compatibilityAliases") != []
    ):
        errors.append("revision-bound v1 identity is invalid")
    adaptive = guidance.get("adaptiveSystem") \
        if isinstance(guidance, dict) else None
    if (
        guidance.get("schema") != 1
        or not isinstance(guidance.get("wholeSystemBalanceReview"), dict)
        or not isinstance(adaptive, dict)
        or not isinstance(adaptive.get("stageStateContract"), dict)
    ):
        errors.append("revision-bound v1 guidance is invalid")
    tasks = golden.get("tasks") if isinstance(golden, dict) else None
    task_ids = [item.get("id") for item in tasks or [] if isinstance(item, dict)]
    if (
        golden.get("schema") != 1 or not isinstance(tasks, list) or not tasks
        or len(task_ids) != len(tasks) or len(task_ids) != len(set(task_ids))
        or any(not _nonempty_string(item) for item in task_ids)
    ):
        errors.append("revision-bound v1 Golden Tasks are invalid")
    errors.extend(_snapshot_v1_projection_shape_errors(program, constitution))
    errors.extend(_snapshot_v1_evaluation_history_errors(acceptance, golden))
    errors.extend(_snapshot_v1_evidence_errors(
        root, program, acceptance, revision,
    ))
    public_release = acceptance.get("publicRelease")
    if not isinstance(public_release, dict):
        errors.append("revision-bound v1 public release record is invalid")
    else:
        locator = public_release.get("releaseNotes")
        expected = public_release.get("releaseNotesSha256")
        try:
            actual = sha256(_snapshot_bytes(root, locator, revision)).hexdigest()
            if actual != expected or not _SNAPSHOT_V1_SHA256_RE.fullmatch(
                expected or ""
            ):
                errors.append("revision-bound v1 release notes digest mismatch")
        except _SNAPSHOT_V1_FAILURES:
            errors.append("revision-bound v1 release notes are unavailable")
    errors.extend(_snapshot_v1_projection_package_errors(
        root, program, constitution, revision,
    ))
    node = program.get("increment", {}).get("closeoutSnapshot") \
        if isinstance(program.get("increment"), dict) else None
    if not isinstance(node, dict) or node.get(
        "evaluationContractSha256"
    ) != _snapshot_v1_evaluation_digest(acceptance, golden):
        errors.append("revision-bound v1 evaluation contract digest mismatch")
    return errors


def _snapshot_v2_contract_errors(root, revision, documents):
    constitution, program, acceptance, guidance, golden = documents
    errors = list(_snapshot_v2_node_errors(program, acceptance))
    product_id = constitution.get("productId")
    if any(item.get("schema") != 3 for item in (
        constitution, program, acceptance,
    )):
        errors.append("revision-bound v2 authority schema is invalid")
    if not _nonempty_string(product_id) or {
        product_id, program.get("productId"), acceptance.get("productId"),
        guidance.get("productId"),
    } != {product_id}:
        errors.append("revision-bound v2 product identities differ")
    if (
        program.get("release") != acceptance.get("release")
        or program.get("distributionVersion") != acceptance.get("distributionVersion")
        or program.get("constitution") != _SNAPSHOT_V1_AUTHORITY_REFS[0]
        or program.get("acceptance") != _SNAPSHOT_V1_AUTHORITY_REFS[2]
        or acceptance.get("constitution") != _SNAPSHOT_V1_AUTHORITY_REFS[0]
        or acceptance.get("program") != _SNAPSHOT_V1_AUTHORITY_REFS[1]
    ):
        errors.append("revision-bound v2 authority references differ")
    identity = constitution.get("identity")
    plugin_ids = identity.get("pluginIds") if isinstance(identity, dict) else None
    if (
        not isinstance(identity, dict)
        or set(identity) != {
            "displayName", "repository", "pythonModule", "pluginIds",
            "compatibilityAliases",
        }
        or not _nonempty_string(identity.get("displayName"))
        or re.fullmatch(r"https://github\.com/[^/]+/[^/]+", identity.get(
            "repository", ""
        )) is None
        or re.fullmatch(r"[a-z][a-z0-9_]*", identity.get(
            "pythonModule", ""
        )) is None
        or not isinstance(plugin_ids, list) or not plugin_ids
        or any(not _nonempty_string(item) for item in plugin_ids)
        or len(plugin_ids) != len(set(plugin_ids))
        or any(not item.startswith(f"{product_id}-") for item in plugin_ids)
        or identity.get("compatibilityAliases") != []
    ):
        errors.append("revision-bound v2 identity is invalid")
    adaptive = guidance.get("adaptiveSystem") \
        if isinstance(guidance, dict) else None
    if (
        guidance.get("schema") != 1
        or not isinstance(guidance.get("wholeSystemBalanceReview"), dict)
        or not isinstance(adaptive, dict)
        or not isinstance(adaptive.get("stageStateContract"), dict)
    ):
        errors.append("revision-bound v2 guidance is invalid")
    tasks = golden.get("tasks") if isinstance(golden, dict) else None
    task_ids = [item.get("id") for item in tasks or [] if isinstance(item, dict)]
    if (
        golden.get("schema") != 1 or not isinstance(tasks, list) or not tasks
        or len(task_ids) != len(tasks) or len(task_ids) != len(set(task_ids))
        or any(not _nonempty_string(item) for item in task_ids)
    ):
        errors.append("revision-bound v2 Golden Tasks are invalid")
    errors.extend(_snapshot_v1_projection_shape_errors(program, constitution))
    errors.extend(_snapshot_v1_evaluation_history_errors(acceptance, golden))
    node = program.get("increment", {}).get("closeoutSnapshot") \
        if isinstance(program.get("increment"), dict) else None
    if isinstance(node, dict) and node.get("state") == "closed":
        errors.extend(_snapshot_v1_evidence_errors(
            root, program, acceptance, revision,
        ))
    public_release = acceptance.get("publicRelease")
    if not isinstance(public_release, dict):
        errors.append("revision-bound v2 public release record is invalid")
    else:
        locator = public_release.get("releaseNotes")
        expected = public_release.get("releaseNotesSha256")
        try:
            actual = sha256(_snapshot_bytes(root, locator, revision)).hexdigest()
            if actual != expected or not _SNAPSHOT_V1_SHA256_RE.fullmatch(
                expected or ""
            ):
                errors.append("revision-bound v2 release notes digest mismatch")
        except _SNAPSHOT_V1_FAILURES:
            errors.append("revision-bound v2 release notes are unavailable")
    errors.extend(_snapshot_v1_projection_package_errors(
        root, program, constitution, revision,
    ))
    if not isinstance(node, dict) or node.get(
        "evaluationContractSha256"
    ) != _snapshot_v1_evaluation_digest(acceptance, golden):
        errors.append("revision-bound v2 evaluation contract digest mismatch")
    return errors


def _snapshot_revision_contract_errors(root, revision, documents=None):
    if (
        not isinstance(revision, str)
        or _SNAPSHOT_V1_REVISION_RE.fullmatch(revision) is None
    ):
        return ["revision-bound snapshot revision is invalid"]
    try:
        documents = _snapshot_v1_documents(root, revision) \
            if documents is None else documents
        if (
            not isinstance(documents, (list, tuple))
            or len(documents) != 5
            or any(not isinstance(item, dict) for item in documents)
        ):
            raise TypeError("revision-bound snapshot documents are malformed")
        program = documents[1]
        increment = program.get("increment")
        node = increment.get("closeoutSnapshot") \
            if isinstance(increment, dict) else None
        schema = node.get("schema") if isinstance(node, dict) else None
        if schema == _SNAPSHOT_V1_SCHEMA:
            return _snapshot_v1_contract_errors(root, revision, documents)
        if schema == _SNAPSHOT_V2_SCHEMA:
            return _snapshot_v2_contract_errors(root, revision, documents)
        return [f"unsupported revision-bound snapshot schema: {schema!r}"]
    except _SNAPSHOT_V1_IO_EXCEPTIONS:
        return ["revision-bound snapshot authority documents are unavailable"]
    except _SNAPSHOT_V1_STRUCTURE_EXCEPTIONS:
        return ["revision-bound snapshot authority documents are malformed"]


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
    _validate_stage_guidance(_read_json(root, GUIDANCE_FILE, errors), errors)

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
    promotion_errors = frozen_gt20_21_promotion_errors(
        root, program, acceptance, golden_suite, _read_json,
    )
    errors.extend(promotion_errors)
    promotion_lanes = (
        FROZEN_GT20_21_REPRESENTATIVE_LANES
        if not promotion_errors else {}
    )
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
        promotion_lanes,
    )
    all_ids = kernel_host_lesson_ids | set(criterion_ids)
    _validate_program(
        root, program, acceptance, criterion_ids, all_ids, identity,
        constitution.get("authority"),
        acceptance.get("canonicalGoalObjectiveSha256"),
        required_release_task_ids,
        representative_contract_sha256(acceptance, golden_suite), errors,
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
    errors.extend(release_identity_errors(
        identity,
        program,
        acceptance,
        _read_text(root, "docs/operations/HISTORY.md", errors),
    ))
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
            root, acceptance, host_reports, _read_json, promotion_lanes
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
        provisional_gt20_21_source_errors(
            root, program, acceptance, golden_suite, _read_json,
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
            current_subject_replays={"GT-20"} if (
                isinstance(program.get("increment"), dict)
                and isinstance(program["increment"].get(
                    "exactPackageEvidenceLifecycle"
                ), dict)
                and program["increment"]["exactPackageEvidenceLifecycle"].get(
                    "state"
                ) == "verified"
            ) else set(),
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
