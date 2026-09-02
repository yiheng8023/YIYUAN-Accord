from hashlib import sha256
from contextvars import ContextVar
from functools import wraps
import json
from pathlib import Path
import re
import subprocess

from .evidence import (
    FROZEN_GT20_21_REPRESENTATIVE_LANES,
    evaluation_contract_history_valid,
    frozen_gt20_21_promotion_errors,
    gt20_exact_lifecycle_invalidated,
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
from .reviews import evaluate_review_bundle


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
_PRIVATE_EVIDENCE_KEYS = frozenset({
    "hook_id", "hookId", "installationId", "memory_paths",
    "messaging_socket_path", "serverName", "session_id", "sessionId",
    "threadId", "turnId", "uuid",
})
_PRIVATE_EVIDENCE_JSON_KEY_RE = re.compile(
    r"(?i)[\"'](?:" + "|".join(
        re.escape(value) for value in sorted(_PRIVATE_EVIDENCE_KEYS)
    ) + r")[\"']\s*:"
)
_PRIVATE_EVIDENCE_PATH_RES = (
    re.compile(
        r"(?i)[a-z]:(?:[\\/]+)(?:users|documents and settings)(?:[\\/]+)"
    ),
    re.compile(
        r"(?i)(?:^|[^a-z0-9])[a-z]--(?:users|documents-and-settings)-"
    ),
    re.compile(r"(?i)(?:^|[\s\"'=(:,\[])[a-z]:[\\/]"),
    re.compile(r"(?:^|[\s\"'=(:,\[])[\\]{2,}[^\\/\s\"']+[\\/]"),
    re.compile(r"(?i)(?:^|[\s\"'=(:,\[])file:(?:/{1,3}|[\\]{1,3})"),
    re.compile(
        r"(?:^|[\s\"'=(:,\[])/(?!/)(?:"
        r"(?:home|users|private|tmp|var|opt|usr|etc|root|mnt|volumes|srv)"
        r"(?:/|$)|(?:[^/\s\"'<>]+/)+[^/\s\"'<>]+)"
    ),
)
ASSESSMENTS = {"planned", "verified", "blocked", "continuing"}
PROGRAM_STATES = {"active", "ready", "blocked"}

_SNAPSHOT_V1_SCHEMA = "yiyuan-accord-stage-closeout-snapshot/v1"
_SNAPSHOT_V2_SCHEMA = "yiyuan-accord-stage-closeout-snapshot/v2"
_SNAPSHOT_V2_GT20_CORRECTION_ID = (
    "public-evidence-privacy-and-candidate-staging-attribution-v1"
)
_SNAPSHOT_V2_GT20_REVIEW_CORRECTION_ID = (
    "independent-evidence-recomputability-and-portable-path-privacy-v2"
)
_SNAPSHOT_V2_GT20_AGENT_RECOVERY_CORRECTION_ID = (
    "one-intent-agent-decision-and-bounded-compensation-v3"
)
_SNAPSHOT_V2_GT20_CORRECTION_IDS = frozenset({
    _SNAPSHOT_V2_GT20_CORRECTION_ID,
    _SNAPSHOT_V2_GT20_REVIEW_CORRECTION_ID,
    _SNAPSHOT_V2_GT20_AGENT_RECOVERY_CORRECTION_ID,
})
_GT20_LIFECYCLE_PREFIX = "yiyuan-accord-exact-package-evidence-lifecycle/"
_GT20_REPLAY_BOUNDARIES = {
    f"{_GT20_LIFECYCLE_PREFIX}v1": "complete-host-projection-package-identity",
    f"{_GT20_LIFECYCLE_PREFIX}v2": "exact-package-evaluator-failure-closure",
    f"{_GT20_LIFECYCLE_PREFIX}v3":
        "exact-package-evaluator-privacy-termination-cleanup-closure",
    f"{_GT20_LIFECYCLE_PREFIX}v4":
        "exact-package-command-contract-host-neighbor-and-brand-surface-closure",
    f"{_GT20_LIFECYCLE_PREFIX}v5":
        "exact-package-evaluator-privacy-ownership-and-native-host-adaptation-closure",
    f"{_GT20_LIFECYCLE_PREFIX}v6":
        "exact-package-host-activation-and-mutation-phase-failed-update-recovery-closure",
    f"{_GT20_LIFECYCLE_PREFIX}v7":
        "single-intent-agent-decision-and-bounded-failed-update-recovery-closure",
}
_GT20_V6_PREDECESSOR = "c5a06688feee7e93edc58a309679594bcc32bed6"
_GT20_V6_REVIEW_CORRECTION_PREDECESSOR = (
    "644e01a86a2870c358774d82080a2d916d00251c"
)
_GT20_V5_EVIDENCE_LOCATOR = (
    "evals/evidence/2026-09-01-v310-gt20-exact-package-source.json"
)
_GT20_V6_EVIDENCE_LOCATOR = (
    "evals/evidence/2026-09-02-v310-gt20-exact-package-v4-source.json"
)
_GT20_V7_PREDECESSOR = "732325e0b00911d295203468faed717bf29db3e2"
_GT20_V7_EVIDENCE_LOCATOR = (
    "evals/evidence/2026-09-02-v310-gt20-exact-package-v5-source.json"
)
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
_SNAPSHOT_V1_TREE_BYTES = 1_048_576
_SNAPSHOT_V1_MAX_TREE_ENTRIES = 8_192
_SNAPSHOT_V1_TREE_CACHE_BYTES = _SNAPSHOT_V1_HISTORY_BYTES
_SNAPSHOT_V1_MAX_CACHED_TREE_ENTRIES = 262_144
_SNAPSHOT_V1_BLOB_CACHE_BYTES = _SNAPSHOT_V1_HISTORY_BYTES
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
_SNAPSHOT_READ_CACHE = ContextVar("snapshot-read-cache", default=None)


def _public_evidence_contains_private_material(value):
    """Reject raw host/session material from a publishable evidence record."""

    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if any(key in _PRIVATE_EVIDENCE_KEYS for key in item):
                return True
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
        elif isinstance(item, str) and (
            _PRIVATE_EVIDENCE_JSON_KEY_RE.search(item)
            or any(pattern.search(item) for pattern in _PRIVATE_EVIDENCE_PATH_RES)
        ):
            return True
    return False


def _canonical_json_sha256(value):
    """Hash the UTF-8 compact JSON form shared with the PowerShell runner."""

    return sha256(json.dumps(
        value, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _candidate_package_identity_sha256(behavior_subject, adapter):
    """Derive one package file graph from the revision-bound subject map."""

    if adapter not in {"codex", "claude"} or not isinstance(
        behavior_subject, dict,
    ):
        return None
    prefix = f"plugins/yiyuan-accord-{adapter}/"
    facts = []
    for locator, digest in behavior_subject.items():
        if not isinstance(locator, str) or not locator.startswith(prefix):
            continue
        relative = locator[len(prefix):]
        if (
            not relative or "\\" in relative or relative.startswith("/")
            or any(part in {"", ".", ".."} for part in relative.split("/"))
            or SHA256_RE.fullmatch(digest or "") is None
        ):
            return None
        facts.append({"locator": relative, "sha256": digest})
    if not facts:
        return None
    facts.sort(key=lambda item: item["locator"])
    return _canonical_json_sha256(facts)


def _candidate_relative_receipt_facts_valid(
    receipt, behavior_subject, adapter,
):
    expected_identity = _candidate_package_identity_sha256(
        behavior_subject, adapter,
    )
    if expected_identity is None:
        return False
    prefix = f"plugins/yiyuan-accord-{adapter}/"
    candidate_locators = sorted(
        locator[len(prefix):]
        for locator in behavior_subject
        if isinstance(locator, str) and locator.startswith(prefix)
    )
    candidate_set = set(candidate_locators)
    candidate_directories = {"."}
    for locator in candidate_locators:
        parts = locator.split("/")
        candidate_directories.update(
            "/".join(parts[:index]) for index in range(1, len(parts))
        )
    observed = receipt.get("observedLocators")
    events = receipt.get("eventRelativePaths")
    manifest = f".{adapter}-plugin/plugin.json"
    if (
        not isinstance(observed, list) or not observed
        or observed != sorted(set(observed))
        or not all(isinstance(item, str) for item in observed)
        or not set(observed) <= candidate_set
        or "adapter.json" not in observed or manifest not in observed
        or receipt.get("observedLocatorCount") != len(observed)
        or receipt.get("observedLocatorSetSha256")
            != _canonical_json_sha256(observed)
        or not isinstance(events, list) or not events
        or events != sorted(set(events))
        or not all(isinstance(item, str) for item in events)
        or not set(events) <= candidate_set | candidate_directories
        or set(observed) != set(events) & candidate_set
        or receipt.get("eventPathSetSha256")
            != _canonical_json_sha256(events)
        or receipt.get("eventPathCount") != len(events)
        or receipt.get("candidateIdentityDigest") != expected_identity
        or receipt.get("eventCount", 0) < len(events)
    ):
        return False
    return True


def _gt20_replay(boundary, state, evidence=None):
    return {
        "earliestAffectedBoundary": boundary,
        "invalidatedTaskIds": ["GT-20"],
        "preservedTaskIds": ["GT-21"],
        "evidenceState": state,
        "evidenceRef": evidence,
    }


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


def _snapshot_batch_blobs(root, requests, limit, bind_ids=False):
    encoded = [item.encode("ascii") for item in requests]
    batch = _bounded_git_bytes(
        root, ["cat-file", "--batch"], limit,
        b"".join(item + b"\n" for item in encoded),
    )
    blobs, offset = [], 0
    for request in encoded:
        end = batch.find(b"\n", offset)
        if end < 0:
            raise ValueError("invalid Git batch header")
        header = batch[offset:end].split()
        offset = end + 1
        if len(header) == 2 and header[1] == b"missing":
            blobs.append(None)
            continue
        if len(header) != 3 or header[1] != b"blob" or (
            bind_ids and header[0] != request
        ):
            raise ValueError("invalid Git batch header")
        size = int(header[2])
        if size < 0 or size > _SNAPSHOT_V1_BLOB_BYTES:
            raise ValueError("snapshot blob bound is invalid")
        content = batch[offset:offset + size]
        offset += size + 1
        if len(content) != size or batch[offset - 1:offset] != b"\n":
            raise ValueError("invalid Git batch body")
        blobs.append(content)
    if offset != len(batch):
        raise ValueError("unexpected Git batch suffix")
    return blobs


class _SnapshotBlobCache:
    """Bounded revision tree and immutable blob cache for one validation scope."""

    def __init__(self):
        self._trees = {}
        self._blobs = {}
        self._tree_bytes = 0
        self._tree_entries = 0
        self._blob_bytes = 0

    @staticmethod
    def _root_key(root):
        return str(Path(root).resolve())

    def _tree(self, root, revision):
        root_key = self._root_key(root)
        key = (root_key, revision)
        cached = self._trees.get(key)
        if cached is not None:
            return cached, root_key
        listing = _bounded_git_bytes(
            root,
            ["ls-tree", "-r", "-z", "--full-tree", revision],
            _SNAPSHOT_V1_TREE_BYTES,
        )
        if self._tree_bytes + len(listing) > _SNAPSHOT_V1_TREE_CACHE_BYTES:
            raise ValueError("snapshot tree cache aggregate bound is invalid")
        tree = {}
        for raw_record in listing.split(b"\0"):
            if not raw_record:
                continue
            if len(tree) >= _SNAPSHOT_V1_MAX_TREE_ENTRIES:
                raise ValueError("snapshot revision tree entry bound is invalid")
            metadata, separator, raw_locator = raw_record.partition(b"\t")
            fields = metadata.split()
            locator = raw_locator.decode("utf-8")
            if (
                not separator or len(fields) != 3 or not locator
                or locator in tree
                or _SNAPSHOT_V1_REVISION_RE.fullmatch(
                    fields[2].decode("ascii")
                ) is None
            ):
                raise ValueError("snapshot revision tree is invalid")
            tree[locator] = (
                fields[0], fields[1], fields[2].decode("ascii"),
            )
        if (
            self._tree_entries + len(tree)
            > _SNAPSHOT_V1_MAX_CACHED_TREE_ENTRIES
        ):
            raise ValueError("snapshot tree cache aggregate bound is invalid")
        self._trees[key] = tree
        self._tree_bytes += len(listing)
        self._tree_entries += len(tree)
        return tree, root_key

    def read(self, root, locator, revision):
        return self.read_many(root, (locator,), revision)[locator]

    def read_many(self, root, locators, revision):
        tree, root_key = self._tree(root, revision)
        locator_keys, object_ids = {}, []
        for locator in dict.fromkeys(locators):
            entry = tree.get(locator)
            if entry is None or entry[0] not in {b"100644", b"100755"} \
                    or entry[1] != b"blob":
                raise ValueError("snapshot file is not an owned regular blob")
            key = (root_key, entry[2])
            locator_keys[locator] = key
            if key not in self._blobs and entry[2] not in object_ids:
                object_ids.append(entry[2])
        if object_ids:
            contents = _snapshot_batch_blobs(
                root, object_ids,
                _SNAPSHOT_V1_BLOB_CACHE_BYTES - self._blob_bytes
                + len(object_ids) * 96,
                True,
            )
            if any(item is None for item in contents):
                raise ValueError("snapshot blob is unavailable")
            additions = {
                (root_key, object_id): content
                for object_id, content in zip(object_ids, contents)
            }
            added_bytes = sum(map(len, contents))
            if self._blob_bytes + added_bytes > _SNAPSHOT_V1_BLOB_CACHE_BYTES:
                raise ValueError("snapshot blob cache aggregate bound is invalid")
            self._blobs.update(additions)
            self._blob_bytes += added_bytes
        return {locator: self._blobs[key] for locator, key in locator_keys.items()}


def _snapshot_read_scope(function):
    """Share bounded immutable Git reads across one verifier call graph."""
    @wraps(function)
    def scoped(*args, **kwargs):
        if _SNAPSHOT_READ_CACHE.get() is not None:
            return function(*args, **kwargs)
        token = _SNAPSHOT_READ_CACHE.set(_SnapshotBlobCache())
        try:
            return function(*args, **kwargs)
        finally:
            _SNAPSHOT_READ_CACHE.reset(token)
    return scoped


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
    cache = _SNAPSHOT_READ_CACHE.get()
    if cache is not None:
        return cache.read(root, locator, revision)
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
    contents = _snapshot_batch_blobs(
        root, [
            f"{revision}:{_SNAPSHOT_V1_AUTHORITY_REFS[1]}"
            for revision in revisions
        ],
        _SNAPSHOT_V1_HISTORY_BYTES,
    )
    records = []
    for revision, content in zip(revisions, contents):
        if content is None:
            records.append((revision, None))
            continue
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
            for field in ("composerIcon", "logo", "logoDark"):
                value = interface.get(field) if isinstance(interface, dict) else None
                if isinstance(value, str) and value.startswith("./"):
                    relative = Path(value[2:])
                    if (
                        not relative.is_absolute() and ".." not in relative.parts
                        and relative.parts[:1] == ("assets",)
                        and relative.suffix.lower() in {".png", ".svg"}
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


@_snapshot_read_scope
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
    lifecycle = increment.get("exactPackageEvidenceLifecycle", {})
    replay_boundary = _GT20_REPLAY_BOUNDARIES.get(
        lifecycle.get("schema")
    ) if isinstance(lifecycle, dict) else None
    replay_fields = {
        "earliestAffectedBoundary", "invalidatedTaskIds",
        "preservedTaskIds", "evidenceState", "evidenceRef",
    }
    if (
        not isinstance(replay, dict)
        or frozenset(replay) not in {
            frozenset(replay_fields),
            frozenset(replay_fields | {"correctionId"}),
        }
        or replay.get("earliestAffectedBoundary") != replay_boundary
        or replay.get("invalidatedTaskIds") != ["GT-20"]
        or replay.get("preservedTaskIds") != ["GT-21"]
        or (
            "correctionId" in replay
            and replay.get("correctionId") not in _SNAPSHOT_V2_GT20_CORRECTION_IDS
        )
    ):
        errors.append("revision-bound v2 replay boundary is invalid")
        replay = {}
    r3 = next((item for item in criteria or [] if isinstance(item, dict)
               and item.get("id") == "R3"), {})
    expected_next = gate_ids[gate_index + 1] \
        if 0 <= gate_index < len(gate_ids) - 1 else None
    if state == "reopened":
        evidence_state = replay.get("evidenceState")
        evidence_ref = replay.get("evidenceRef")
        if (
            node.get("nextGateId") != gate
            or evidence_state not in {"pending", "verified"}
            or (evidence_state == "pending" and evidence_ref is not None)
            or (evidence_state == "verified"
                and not _nonempty_string(evidence_ref))
            or lifecycle.get("state") != evidence_state
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


@_snapshot_read_scope
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
        current_replay = current.get("replay")
        prior_replay = predecessor.get("replay")
        reopened_successor = (
            prior_schema == _SNAPSHOT_V2_SCHEMA
            and prior_state == "reopened"
            and isinstance(current_replay, dict)
            and isinstance(prior_replay, dict)
            and prior_replay.get("evidenceState") == "pending"
            and prior_replay.get("evidenceRef") is None
            and current_replay.get("evidenceState") == "verified"
            and _nonempty_string(current_replay.get("evidenceRef"))
            and {
                key: current_replay.get(key) for key in (
                    "earliestAffectedBoundary", "invalidatedTaskIds",
                    "preservedTaskIds", "correctionId",
                )
            } == {
                key: prior_replay.get(key) for key in (
                    "earliestAffectedBoundary", "invalidatedTaskIds",
                    "preservedTaskIds", "correctionId",
                )
            }
        )
        reopened_correction = (
            prior_schema == _SNAPSHOT_V2_SCHEMA
            and prior_state == "reopened"
            and isinstance(current_replay, dict)
            and isinstance(prior_replay, dict)
            and prior_replay == _gt20_replay(
                _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v6"],
                "pending",
            )
            and current_replay == {
                **_gt20_replay(
                    _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v6"],
                    "pending",
                ),
                "correctionId": _SNAPSHOT_V2_GT20_CORRECTION_ID,
            }
        )
        reopened_review_correction = (
            prior_schema == _SNAPSHOT_V2_SCHEMA
            and prior_state == "reopened"
            and isinstance(current_replay, dict)
            and isinstance(prior_replay, dict)
            and prior_replay == {
                **_gt20_replay(
                    _GT20_REPLAY_BOUNDARIES[
                        f"{_GT20_LIFECYCLE_PREFIX}v6"
                    ],
                    "pending",
                ),
                "correctionId": _SNAPSHOT_V2_GT20_CORRECTION_ID,
            }
            and current_replay == {
                **_gt20_replay(
                    _GT20_REPLAY_BOUNDARIES[
                        f"{_GT20_LIFECYCLE_PREFIX}v6"
                    ],
                    "pending",
                ),
                "correctionId": _SNAPSHOT_V2_GT20_REVIEW_CORRECTION_ID,
            }
        )
        reopened_agent_recovery_correction = (
            prior_schema == _SNAPSHOT_V2_SCHEMA
            and prior_state == "reopened"
            and isinstance(current_replay, dict)
            and isinstance(prior_replay, dict)
            and prior_replay == {
                **_gt20_replay(
                    _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v6"],
                    "verified", _GT20_V6_EVIDENCE_LOCATOR,
                ),
                "correctionId": _SNAPSHOT_V2_GT20_REVIEW_CORRECTION_ID,
            }
            and current_replay == {
                **_gt20_replay(
                    _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v7"],
                    "pending",
                ),
                "correctionId":
                    _SNAPSHOT_V2_GT20_AGENT_RECOVERY_CORRECTION_ID,
            }
        )
        reopened_rebaseline = (
            prior_schema == _SNAPSHOT_V2_SCHEMA
            and prior_state == "reopened"
            and isinstance(current_replay, dict)
            and isinstance(prior_replay, dict)
            and prior_replay == _gt20_replay(
                _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v3"],
                "pending",
            )
            and current_replay == _gt20_replay(
                _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v4"],
                "pending",
            )
        ) or (
            prior_schema == _SNAPSHOT_V2_SCHEMA
            and prior_state == "reopened"
            and isinstance(current_replay, dict)
            and isinstance(prior_replay, dict)
            and prior_replay == _gt20_replay(
                _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v4"],
                "pending",
            )
            and current_replay == _gt20_replay(
                _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v5"],
                "pending",
            )
        )
        reopened_invalidation = (
            prior_schema == _SNAPSHOT_V2_SCHEMA
            and prior_state == "reopened"
            and isinstance(current_replay, dict)
            and isinstance(prior_replay, dict)
            and prior_replay == _gt20_replay(
                _GT20_REPLAY_BOUNDARIES[f"{_GT20_LIFECYCLE_PREFIX}v5"],
                "verified", _GT20_V5_EVIDENCE_LOCATOR,
            )
            and current_replay in (
                _gt20_replay(
                    _GT20_REPLAY_BOUNDARIES[
                        f"{_GT20_LIFECYCLE_PREFIX}v6"
                    ],
                    "pending",
                ),
                {
                    **_gt20_replay(
                        _GT20_REPLAY_BOUNDARIES[
                            f"{_GT20_LIFECYCLE_PREFIX}v6"
                        ],
                        "pending",
                    ),
                    "correctionId": _SNAPSHOT_V2_GT20_CORRECTION_ID,
                },
            )
        )
        reopening_closed = (
            prior_state == "closed" and prior_schema in {
                _SNAPSHOT_V1_SCHEMA, _SNAPSHOT_V2_SCHEMA,
            }
        )
        if not reopening_closed and not reopened_successor \
                and not reopened_correction and not reopened_review_correction \
                and not reopened_agent_recovery_correction \
                and not reopened_rebaseline \
                and not reopened_invalidation:
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


@_snapshot_read_scope
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


@_snapshot_read_scope
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
        for field in ("composerIcon", "logo", "logoDark"):
            value = interface.get(field) if isinstance(interface, dict) else None
            if isinstance(value, str) and value.startswith("./assets/"):
                declared.add((
                    Path(manifest_locator).parent.parent / value[2:]
                ).as_posix())
    return declared


def _claude_command_distribution_identity(command):
    """Accept either the legacy npm shim or the native executable layout.

    The lifecycle record binds exact executable bytes in both cases.  The npm
    layout additionally binds its package manifest; the recommended native
    Windows distribution has no npm manifest and must resolve directly to
    ``claude.exe`` rather than an unbound shim.
    """

    manifest = command.get("packageManifest")
    manifest_sha = command.get("packageManifestSha256")
    if _nonempty_string(manifest):
        return SHA256_RE.fullmatch(manifest_sha or "") is not None
    terminal = command.get("terminalExecutable")
    return (
        manifest is None
        and manifest_sha is None
        and _nonempty_string(terminal)
        and Path(terminal.replace("\\", "/")).name.casefold() == "claude.exe"
        and command.get("resolvedCommand") == terminal
        and command.get("resolvedCommandSha256")
            == command.get("terminalExecutableSha256")
    )


def _gt20_v4_overlay_shape_valid(contract):
    try:
        commands = contract["commands"]
        roles = {item["role"]: item for item in commands}
        replacements = {
            item["replacesRole"]: item["role"]
            for item in commands if "replacesRole" in item
        }
        inserts = {
            (item["insertBeforeRole"], item["role"])
            for item in commands if "insertBeforeRole" in item
        }
        edits = contract["commandEdits"]
        prefixes = edits["prependArgumentsByRole"]
        activation = contract["activationProof"]
        failure = contract["failedUpdateProof"]
        return (
            set(contract) == {
                "schema", "baseContract", "priorRelease", "activationProof",
                "failedUpdateProof", "commandEdits", "commands",
            }
            and contract["schema"]
                == "yiyuan-accord-gt20-command-contract-overlay/v1"
            and contract["baseContract"] == {
                "locator": "evals/contracts/gt20-v3-command-contract.json",
                "sha256": (
                    "53b8281282f876b7298da20577de3859ef107cc689c7aa2de99866a70d52355c"
                ),
            }
            and contract["priorRelease"] == {
                "tag": "v3.0.1",
                "revision": "24cf9f3750ecd700944988e81a519db54b67b8e8",
            }
            and len(commands) == len(roles) == 8
            and set(edits) == {"replaceRoles", "prependArgumentsByRole"}
            and set(edits["replaceRoles"]) == set(replacements)
            and len(edits["replaceRoles"]) == 6
            and inserts == {
                ("codexHookStartup", "codexHostActivation"),
                ("codexHookStartup", "claudeHostActivation"),
            }
            and set(prefixes) == {
                "neighborCodexMarketplaceAdd", "neighborCodexInstall",
                "accordCodexMarketplaceAdd", "accordCodexInstallPrior",
                "accordCodexUpdateCandidate",
            }
            and all(value == ["--dangerously-bypass-hook-trust"]
                    for value in prefixes.values())
            and activation["codex"]["qualifyingCommandRole"]
                == "codexHostActivation"
            and activation["claude"]["qualifyingCommandRole"]
                == "claudeHostActivation"
            and activation["codex"]["lifecycleTriggerTurns"] == 2
            and activation["codex"]["externalModelTurns"] == 0
            and activation["codex"]["publicTranscriptPolicy"]
                == "digest-only-private-host-transcript-not-retained"
            and activation["codex"]["identifierPolicy"] == "sha256-only"
            and activation["codex"]["credentialEnvironmentInherited"] is False
            and activation["claude"]["lifecycleTriggerTurns"] == 2
            and activation["claude"]["externalModelTurns"] == 0
            and activation["claude"]["minimumLoopbackHttpRequests"] == 2
            and activation["claude"]["publicTranscriptPolicy"]
                == "digest-only-private-host-transcript-not-retained"
            and activation["claude"]["identifierPolicy"] == "sha256-only"
            and activation["claude"]["requiredLoadedPlugin"] == {
                "name": "yiyuan-accord-claude", "version": "3.1.0",
            }
            and activation["claude"]["credentialEnvironmentInherited"] is False
            and failure["minimumAcceptedPhase"]
                == "host-accepted-update-with-task-owned-staging-observed"
            and failure["forbiddenFailureCategory"] == "source-path-absent"
            and failure["observationScope"]
                == "candidate-bound-staging-route"
            and failure["candidateIdentityAlgorithm"]
                == "ordinal-compact-json-package-file-facts-v1"
            and failure["publicPathPolicy"]
                == "root-marker-or-host-leaf-no-unmarked-absolute-path"
            and failure["requiredReceiptFacts"] == [
                "candidateIdentityDigest", "observedLocators",
                "observedLocatorSetSha256", "eventRelativePaths",
                "eventPathSetSha256",
            ]
            and failure["allowedPathScopes"] == [
                "exact-target", "verified-temp-sibling",
            ]
            and failure["targetVersion"] == "3.1.0"
            and failure["unexpectedSiblingDelta"] == []
            and failure["priorInventoryCommandRoles"] == {
                "codex": "rollbackCodexInventory",
                "claude": "rollbackClaudeInventory",
            }
            and "fresh-host-inventory-selects-prior-version"
                in failure["requiredPoststate"]
        )
    except (AttributeError, KeyError, TypeError):
        return False


def _resolve_gt20_v4_command_contract(overlay, base):
    """Resolve the bounded v4 overlay without trusting the runner's result."""

    if (
        not _gt20_v4_overlay_shape_valid(overlay)
        or not isinstance(base, dict)
        or base.get("schema") != "yiyuan-accord-gt20-command-contract/v1"
        or not isinstance(base.get("commands"), list)
    ):
        return None
    value = json.loads(json.dumps(base))
    overlay_commands = overlay["commands"]
    replacements = {
        item["replacesRole"]: item
        for item in overlay_commands if "replacesRole" in item
    }
    inserts = {}
    for item in overlay_commands:
        if "insertBeforeRole" in item:
            inserts.setdefault(item["insertBeforeRole"], []).append(item)
    effective = []
    base_roles = {item.get("role") for item in value["commands"]}
    if not set(replacements) <= base_roles or not set(inserts) <= base_roles:
        return None
    for base_spec in value["commands"]:
        for item in inserts.get(base_spec.get("role"), []):
            inserted = json.loads(json.dumps(item))
            inserted.pop("insertBeforeRole", None)
            effective.append(inserted)
        replacement = replacements.get(base_spec.get("role"))
        if replacement is None:
            effective.append(base_spec)
            continue
        merged = json.loads(json.dumps(base_spec))
        merged.update({
            key: json.loads(json.dumps(item))
            for key, item in replacement.items() if key != "replacesRole"
        })
        effective.append(merged)
    prefixes = overlay["commandEdits"]["prependArgumentsByRole"]
    by_role = {item.get("role"): item for item in effective}
    if len(by_role) != len(effective) or not set(prefixes) <= set(by_role):
        return None
    for role, prefix in prefixes.items():
        argv = by_role[role].get("argv")
        if not isinstance(argv, list) or not argv:
            return None
        if argv[1:1 + len(prefix)] != prefix:
            by_role[role]["argv"] = [argv[0], *prefix, *argv[1:]]
    value["commands"] = effective
    return value


def _gt20_v4_activation_receipt_valid(command, host, version):
    """Validate host-native startup/resume receipts, independent of the runner."""

    if not isinstance(command, dict) or host not in {"codex", "claude"}:
        return False
    receipt = command.get("activationReceipt")
    if not isinstance(receipt, dict) or version not in {"3.0.1", "3.1.0"}:
        return False
    digest_only = (
        command.get("stdout") == ""
        and command.get("stderr") == ""
        and receipt.get("rawStreamPolicy")
            == "digest-only-private-host-transcript-not-retained"
        and SHA256_RE.fullmatch(receipt.get("rawStdoutSha256") or "")
            is not None
        and SHA256_RE.fullmatch(receipt.get("rawStderrSha256") or "")
            is not None
    )
    if not digest_only:
        return False
    if host == "codex":
        expected_path = (
            "%TASK_ROOT%/codex-host/plugins/cache/yiyuan-accord/"
            f"yiyuan-accord-codex/{version}/hooks/hooks.json"
        )
        if (
            command.get("exitCode") != 0
            or command.get("failureCategory") is not None
            or set(receipt) != {
                "transport", "rpcMethods", "lifecycleTriggerTurns",
                "externalModelTurns", "loopbackModelRequests", "startup",
                "resume", "rawStreamPolicy", "rawStdoutSha256",
                "rawStderrSha256",
            }
            or receipt.get("transport") != "app-server-stdio-jsonl"
            or receipt.get("rpcMethods") != [
                "hooks/list", "thread/start", "turn/start", "thread/resume",
            ]
            or receipt.get("lifecycleTriggerTurns") != 2
            or receipt.get("externalModelTurns") != 0
            or receipt.get("loopbackModelRequests") != 2
        ):
            return False
        thread_ids = []
        for source, rpc_method in (("startup", "thread/start"),
                                   ("resume", "thread/resume")):
            item = receipt.get(source)
            if not isinstance(item, dict) or set(item) != {
                "rpcMethod", "responseId", "threadIdSha256",
                "lifecycleTrigger", "discovery", "hookStarted",
                "hookCompleted",
            }:
                return False
            discovery = item.get("discovery")
            trigger = item.get("lifecycleTrigger")
            started = item.get("hookStarted")
            completed = item.get("hookCompleted")
            normalized_paths = [
                part.get("sourcePath", "").replace("\\", "/")
                for part in (discovery, started, completed)
                if isinstance(part, dict)
            ]
            if (
                item.get("rpcMethod") != rpc_method
                or type(item.get("responseId")) is not int
                or SHA256_RE.fullmatch(item.get("threadIdSha256") or "")
                    is None
                or not isinstance(trigger, dict)
                or trigger.get("rpcMethod") != "turn/start"
                or type(trigger.get("responseId")) is not int
                or set(trigger) != {
                    "rpcMethod", "responseId", "turnIdSha256",
                    "terminalStatus", "modelProvider", "requiresOpenAIAuth",
                }
                or SHA256_RE.fullmatch(trigger.get("turnIdSha256") or "")
                    is None
                or trigger.get("terminalStatus") != "failed"
                or trigger.get("modelProvider")
                    != "task-owned-loopback-responses-failure"
                or trigger.get("requiresOpenAIAuth") is not False
                or not isinstance(discovery, dict)
                or discovery.get("rpcMethod") != "hooks/list"
                or str(discovery.get("eventName", "")).casefold()
                    != "sessionstart"
                or discovery.get("source") != "plugin"
                or discovery.get("handlerType") != "command"
                or discovery.get("enabled") is not True
                or discovery.get("trustStatus") != "untrusted"
                or not isinstance(started, dict)
                or not isinstance(completed, dict)
                or str(started.get("eventName", "")).casefold()
                    != "sessionstart"
                or str(completed.get("eventName", "")).casefold()
                    != "sessionstart"
                or started.get("source") != "plugin"
                or completed.get("source") != "plugin"
                or started.get("status") != "running"
                or completed.get("status") != "completed"
                or SHA256_RE.fullmatch(started.get("idSha256") or "") is None
                or started.get("idSha256") != completed.get("idSha256")
                or normalized_paths != [expected_path] * 3
            ):
                return False
            thread_ids.append(item["threadIdSha256"])
        return len(set(thread_ids)) == 1

    expected_runtime = (
        "%TASK_ROOT%/mutable-source/plugins/yiyuan-accord-claude/"
        "runtime/accord-hook.cjs"
    )
    if (
        command.get("exitCode") == 0
        or command.get("failureCategory") is not None
        or set(receipt) != {
            "transport", "lifecycleTriggerTurns", "externalModelTurns",
            "loopbackHttpRequests", "credentialEnvironmentInherited",
            "networkEndpoint", "terminalStatus", "hostRuns", "native",
            "hooks", "rawStreamPolicy", "rawStdoutSha256",
            "rawStderrSha256",
        }
        or receipt.get("transport") != (
            "headless-stream-json-with-loopback-trigger-and-task-owned-"
            "node-observer"
        )
        or receipt.get("lifecycleTriggerTurns") != 2
        or receipt.get("externalModelTurns") != 0
        or type(receipt.get("loopbackHttpRequests")) is not int
        or receipt["loopbackHttpRequests"] < 2
        or receipt.get("credentialEnvironmentInherited") is not False
        or receipt.get("networkEndpoint") != "ipv4-loopback"
        or receipt.get("terminalStatus") != "api_error"
    ):
        return False
    host_runs = receipt.get("hostRuns")
    if not isinstance(host_runs, list) or len(host_runs) != 2:
        return False
    expected_runs = (
        ("startup", "task-owned-session-id"),
        ("resume", "same-task-owned-session-id"),
    )
    request_total = 0
    for run, (source, binding) in zip(host_runs, expected_runs, strict=True):
        if (
            not isinstance(run, dict)
            or set(run) != {
                "source", "sessionBinding", "exitCode", "loopbackHttpRequests",
            }
            or run.get("source") != source
            or run.get("sessionBinding") != binding
            or type(run.get("exitCode")) is not int
            or run["exitCode"] == 0
            or type(run.get("loopbackHttpRequests")) is not int
            or run["loopbackHttpRequests"] < 1
        ):
            return False
        request_total += run["loopbackHttpRequests"]
    if request_total != receipt["loopbackHttpRequests"]:
        return False
    native = receipt.get("native")
    hooks = receipt.get("hooks")
    if (
        not isinstance(native, dict) or set(native) != {"startup", "resume"}
        or not isinstance(hooks, list) or len(hooks) != 2
    ):
        return False
    for source in ("startup", "resume"):
        item = native.get(source)
        started = item.get("nativeHookStarted") \
            if isinstance(item, dict) else None
        response = item.get("nativeHookResponse") \
            if isinstance(item, dict) else None
        plugin = item.get("loadedPlugin") if isinstance(item, dict) else None
        terminal = item.get("terminal") if isinstance(item, dict) else None
        if (
            not isinstance(item, dict)
            or set(item) != {
                "sessionSource", "nativeHookStarted", "nativeHookResponse",
                "loadedPlugin", "terminal",
            }
            or item.get("sessionSource") != source
            or not isinstance(started, dict) or not isinstance(response, dict)
            or started.get("subtype") != "hook_started"
            or response.get("subtype") != "hook_response"
            or started.get("hookEvent") != "SessionStart"
            or response.get("hookEvent") != "SessionStart"
            or started.get("hookName") != f"SessionStart:{source}"
            or response.get("hookName") != f"SessionStart:{source}"
            or set(started) != {
                "subtype", "hookEvent", "hookName", "hookIdSha256",
            }
            or set(response) != {
                "subtype", "hookEvent", "hookName", "hookIdSha256",
                "exitCode", "outcome",
            }
            or SHA256_RE.fullmatch(started.get("hookIdSha256") or "") is None
            or started.get("hookIdSha256") != response.get("hookIdSha256")
            or response.get("exitCode") != 0
            or response.get("outcome") != "success"
            or plugin != {
                "name": "yiyuan-accord-claude",
                "version": version,
                "source": "yiyuan-accord-claude@yiyuan-accord",
                "path": "%TASK_ROOT%/mutable-source/plugins/"
                        "yiyuan-accord-claude",
            }
            or terminal != {
                "status": "api_error", "apiErrorStatus": 400,
                "isError": True, "totalCostUsd": 0, "turns": 1,
            }
        ):
            return False
    by_source = {item.get("source"): item for item in hooks
                 if isinstance(item, dict)}
    if set(by_source) != {"startup", "resume"}:
        return False
    return all(
        set(item) == {
            "hookEventName", "source", "runtimePath", "inputSha256",
            "stdoutSha256", "stderrSha256", "exitCode",
        }
        and item.get("hookEventName") == "SessionStart"
        and item.get("runtimePath", "").replace("\\", "/")
            == expected_runtime
        and item.get("exitCode") == 0
        and all(SHA256_RE.fullmatch(item.get(key) or "") is not None for key in (
            "inputSha256", "stdoutSha256", "stderrSha256",
        ))
        for item in by_source.values()
    )


def _gt20_v4_failed_update_receipts_valid(
    commands, fixture, behavior_subject,
):
    """Validate mutation reached staging and recovery claims remain factual."""

    if not isinstance(commands, dict) or not isinstance(fixture, dict):
        return False
    for adapter, role in (
        ("codex", "accordCodexFailedUpdateAfterStaging"),
        ("claude", "accordClaudeFailedUpdateAfterStaging"),
    ):
        command = commands.get(role)
        receipt = command.get("mutationReceipt") \
            if isinstance(command, dict) else None
        if (
            not isinstance(command, dict) or command.get("exitCode") == 0
            or command.get("failureCategory")
                != "task-owned-candidate-lock-after-staging"
            or not isinstance(receipt, dict)
            or set(receipt) != {
                "stagingObserved", "eventCount", "observationScope",
                "pathScope", "targetVersion", "preexisting",
                "postCommandAbsent", "candidateIdentityDigest",
                "observedLocatorCount", "observedLocators",
                "observedLocatorSetSha256", "eventPathCount",
                "eventRelativePaths",
                "eventPathSetSha256", "unexpectedSiblingDelta", "eventKinds",
            }
            or receipt.get("stagingObserved") is not True
            or type(receipt.get("eventCount")) is not int
            or receipt["eventCount"] < 1
            or receipt.get("observationScope")
                != "candidate-bound-staging-route"
            or receipt.get("pathScope") not in {
                "exact-target", "verified-temp-sibling",
            }
            or receipt.get("targetVersion") != "3.1.0"
            or receipt.get("preexisting") is not False
            or type(receipt.get("postCommandAbsent")) is not bool
            or not _candidate_relative_receipt_facts_valid(
                receipt, behavior_subject, adapter,
            )
            or receipt.get("unexpectedSiblingDelta") != []
            or not isinstance(receipt.get("eventKinds"), list)
            or receipt.get("eventKinds") != sorted(set(receipt["eventKinds"]))
            or not set(receipt["eventKinds"]) <= {"Changed", "Created", "Renamed"}
            or "Created" not in receipt["eventKinds"]
        ):
            return False
    recovery = fixture.get("failedUpdateRecovery")
    codex = recovery.get("codex") if isinstance(recovery, dict) else None
    claude = recovery.get("claude") if isinstance(recovery, dict) else None
    codex_mutation = commands["accordCodexFailedUpdateAfterStaging"][
        "mutationReceipt"
    ]
    claude_mutation = commands["accordClaudeFailedUpdateAfterStaging"][
        "mutationReceipt"
    ]
    difference = claude.get("difference") if isinstance(claude, dict) else None
    try:
        codex_inventory = json.loads(commands["rollbackCodexInventory"]["stdout"])
        claude_inventory = json.loads(commands["rollbackClaudeInventory"]["stdout"])
        codex_prior = [
            item for item in codex_inventory.get("installed", [])
            if isinstance(item, dict)
            and item.get("pluginId") == "yiyuan-accord-codex@yiyuan-accord"
        ]
        claude_prior = [
            item for item in claude_inventory
            if isinstance(item, dict)
            and item.get("id") == "yiyuan-accord-claude@yiyuan-accord"
        ]
        fresh_inventory_valid = (
            len(codex_prior) == len(claude_prior) == 1
            and codex_prior[0].get("version") == "3.0.1"
            and codex_prior[0].get("installed") is True
            and codex_prior[0].get("enabled") is True
            and claude_prior[0].get("version") == "3.0.1"
            and claude_prior[0].get("enabled") is True
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        fresh_inventory_valid = False
    return (
        fixture.get("sourceFailureMode")
            == "task-owned-candidate-lock-after-staging"
        and fixture.get("failedUpdateDisposition") == (
            "prior-remained-active-with-host-cleaned-or-explicit-task-owned-"
            "staging-cleanup"
        )
        and fixture.get("automaticRollbackClaimed") is False
        and codex_mutation.get("postCommandAbsent") is True
        and claude_mutation.get("postCommandAbsent") is False
        and fixture.get("priorInstalledBytesPreservedAfterFailedUpdate") is True
        and fixture.get("freshPriorInventoryVerified") is True
        and fresh_inventory_valid
        and isinstance(recovery, dict) and set(recovery) == {"codex", "claude"}
        and codex == {
            "disposition": "prior-remained-active-host-cleaned-observed-staging",
            "stagedFileCount": None, "difference": None,
            "stagingCleanupVerified": True, "postRepairAbsent": True,
        }
        and isinstance(claude, dict)
        and set(claude) == {
            "disposition", "stagedFileCount", "difference",
            "stagingCleanupVerified", "postRepairAbsent",
        }
        and claude.get("disposition") == (
            "prior-remained-active-with-explicit-task-owned-staging-cleanup"
        )
        and type(claude.get("stagedFileCount")) is int
        and claude["stagedFileCount"] > 0
        and claude.get("stagingCleanupVerified") is True
        and claude.get("postRepairAbsent") is True
        and isinstance(difference, dict)
        and set(difference) == {"missing", "extra", "changed"}
        and isinstance(difference.get("missing"), list)
        and bool(difference["missing"])
        and difference.get("extra") == [] and difference.get("changed") == []
        and all(_nonempty_string(item) and not Path(item).is_absolute()
                for item in difference["missing"])
    )


def _validate_exact_package_evidence_lifecycle(
    root, program, errors, revision=None,
):
    increment = program.get("increment") if isinstance(program, dict) else None
    lifecycle = increment.get("exactPackageEvidenceLifecycle") \
        if isinstance(increment, dict) else None
    fields = {
        "schema", "state", "taskId", "earliestAffectedBoundary",
        "subjectBinding", "preservedTaskIds", "evidence",
    }
    contracts = {
        "yiyuan-accord-exact-package-evidence-lifecycle/v1": (
            "complete-host-projection-package-identity",
            "evals/evidence/2026-08-30-v310-gt20-21-source.json"
            "#/records/GT-20-transactional-lifecycle-4c8bcc3", None,
        ),
        "yiyuan-accord-exact-package-evidence-lifecycle/v2": (
            "exact-package-evaluator-failure-closure",
            "7ef757ddf6d852ea6c55d99b7f88fbee179f4500:"
            "evals/evidence/2026-09-01-v310-gt20-exact-package-source.json",
            "7ea91dad811d337f00f75eb521cffacabd73b05f",
        ),
        "yiyuan-accord-exact-package-evidence-lifecycle/v3": (
            "exact-package-evaluator-privacy-termination-cleanup-closure",
            "90501145346f81e02ebdc88fcf3001b39bfdf3d4:"
            "evals/evidence/2026-09-01-v310-gt20-exact-package-source.json",
            "7ea91dad811d337f00f75eb521cffacabd73b05f",
        ),
        "yiyuan-accord-exact-package-evidence-lifecycle/v4": (
            "exact-package-command-contract-host-neighbor-and-brand-surface-closure",
            None, None,
        ),
        "yiyuan-accord-exact-package-evidence-lifecycle/v5": (
            "exact-package-evaluator-privacy-ownership-and-native-host-adaptation-closure",
            None, None,
        ),
        "yiyuan-accord-exact-package-evidence-lifecycle/v6": (
            "exact-package-host-activation-and-mutation-phase-failed-update-"
            "recovery-closure",
            None, None,
        ),
        "yiyuan-accord-exact-package-evidence-lifecycle/v7": (
            "single-intent-agent-decision-and-bounded-failed-update-recovery-"
            "closure",
            None, None,
        ),
    }
    contract = contracts.get(lifecycle.get("schema")) \
        if isinstance(lifecycle, dict) else None
    is_v4 = isinstance(lifecycle, dict) and lifecycle.get("schema") == (
        "yiyuan-accord-exact-package-evidence-lifecycle/v4"
    )
    is_v5 = isinstance(lifecycle, dict) and lifecycle.get("schema") == (
        "yiyuan-accord-exact-package-evidence-lifecycle/v5"
    )
    is_v6 = isinstance(lifecycle, dict) and lifecycle.get("schema") == (
        "yiyuan-accord-exact-package-evidence-lifecycle/v6"
    )
    is_v7 = isinstance(lifecycle, dict) and lifecycle.get("schema") == (
        "yiyuan-accord-exact-package-evidence-lifecycle/v7"
    )
    snapshot_replay = increment.get("closeoutSnapshot", {}).get("replay", {}) \
        if isinstance(increment.get("closeoutSnapshot"), dict) else {}
    is_v6_review_correction = (
        is_v6 and isinstance(snapshot_replay, dict)
        and snapshot_replay.get("correctionId")
            == _SNAPSHOT_V2_GT20_REVIEW_CORRECTION_ID
    )
    is_modern = is_v4 or is_v5 or is_v6 or is_v7
    expected_fields = fields | (
        {
            "predecessorLifecycleRef", "commandContractLocator",
            "commandContractSha256",
        } if is_modern else {"priorEvidenceRef"}
    ) | (
        {"subjectRevision"} if contract and (
            contract[2] or is_modern and lifecycle.get("state") == "verified"
        ) else set()
    )
    if contract is None or set(lifecycle) != expected_fields:
        errors.append("exact package evidence lifecycle is invalid")
        return
    boundary, prior_evidence, subject_revision = contract
    if (
        lifecycle.get("state") not in {"pending", "verified"}
        or lifecycle.get("taskId") != "GT-20"
        or lifecycle.get("earliestAffectedBoundary") != boundary
        or lifecycle.get("subjectBinding")
        != "containing-git-commit-complete-declared-packages"
        or lifecycle.get("preservedTaskIds") != ["GT-21"]
        or (not is_modern and lifecycle.get("priorEvidenceRef") != prior_evidence)
        or (subject_revision and lifecycle.get("subjectRevision") != subject_revision)
    ):
        errors.append("exact package evidence lifecycle contract is invalid")
    if is_modern:
        predecessor = lifecycle.get("predecessorLifecycleRef")
        match = re.fullmatch(
            r"([0-9a-f]{40}):product/program\.json#/increment/"
            r"exactPackageEvidenceLifecycle",
            predecessor or "",
        )
        predecessor_program = {}
        try:
            predecessor_program = _snapshot_json(
                root, AUTHORITY_BOOTSTRAP[1], match.group(1),
            ) \
                if match else {}
            predecessor_lifecycle = predecessor_program.get(
                "increment", {},
            ).get("exactPackageEvidenceLifecycle")
        except _SNAPSHOT_V1_FAILURES:
            predecessor_lifecycle = None
        predecessor_revision = match.group(1) if match else None
        base_predecessor_ref = (
            f"{_GT20_V7_PREDECESSOR}:"
            "product/program.json#/increment/exactPackageEvidenceLifecycle"
            if is_v7 else
            f"{_GT20_V6_REVIEW_CORRECTION_PREDECESSOR}:"
            "product/program.json#/increment/exactPackageEvidenceLifecycle"
            if is_v6_review_correction else
            f"{_GT20_V6_PREDECESSOR}:"
            "product/program.json#/increment/exactPackageEvidenceLifecycle"
            if is_v6 else
            "fc9c1a7a64257ddf315f862a091a081c4104d81b:"
            "product/program.json#/increment/exactPackageEvidenceLifecycle"
            if is_v5 else
            "fecbdbc3c557e5145e4f037eb9876a09875f9eba:"
            "product/program.json#/increment/exactPackageEvidenceLifecycle"
        )
        modern_pending = {
            "schema": lifecycle.get("schema"),
            "state": "pending",
            "taskId": "GT-20",
            "earliestAffectedBoundary": boundary,
            "subjectBinding": (
                "containing-git-commit-complete-declared-packages"
            ),
            "preservedTaskIds": ["GT-21"],
            "predecessorLifecycleRef": base_predecessor_ref,
            "commandContractLocator": lifecycle.get(
                "commandContractLocator"
            ),
            "commandContractSha256": lifecycle.get(
                "commandContractSha256"
            ),
            "evidence": None,
        }
        predecessor_shape_valid = True
        if lifecycle.get("state") == "verified":
            expected_predecessor = modern_pending
            expected_predecessor_revision = lifecycle.get("subjectRevision")
        elif is_v6_review_correction:
            expected_predecessor = predecessor_lifecycle
            expected_predecessor_revision = (
                _GT20_V6_REVIEW_CORRECTION_PREDECESSOR
            )
            predecessor_snapshot = predecessor_program.get(
                "increment", {},
            ).get("closeoutSnapshot", {}) \
                if isinstance(predecessor_program, dict) else {}
            predecessor_shape_valid = (
                predecessor_lifecycle == {
                    "schema": f"{_GT20_LIFECYCLE_PREFIX}v6",
                    "state": "pending",
                    "taskId": "GT-20",
                    "earliestAffectedBoundary": boundary,
                    "subjectBinding": (
                        "containing-git-commit-complete-declared-packages"
                    ),
                    "preservedTaskIds": ["GT-21"],
                    "predecessorLifecycleRef": (
                        f"{_GT20_V6_PREDECESSOR}:product/program.json#/"
                        "increment/exactPackageEvidenceLifecycle"
                    ),
                    "commandContractLocator": (
                        "evals/contracts/gt20-v4-command-contract.json"
                    ),
                    "commandContractSha256": (
                        "57b7d80ccf1671007c13fce17e2c5c64a6a3c058c50a7ce99711f208075f2edd"
                    ),
                    "evidence": None,
                }
                and isinstance(predecessor_snapshot, dict)
                and predecessor_snapshot.get("replay") == {
                    **_gt20_replay(
                        _GT20_REPLAY_BOUNDARIES[
                            f"{_GT20_LIFECYCLE_PREFIX}v6"
                        ],
                        "pending",
                    ),
                    "correctionId": _SNAPSHOT_V2_GT20_CORRECTION_ID,
                }
            )
        elif is_v7:
            expected_predecessor = predecessor_lifecycle
            expected_predecessor_revision = _GT20_V7_PREDECESSOR
            predecessor_shape_valid = (
                isinstance(predecessor_lifecycle, dict)
                and predecessor_lifecycle.get("schema")
                    == f"{_GT20_LIFECYCLE_PREFIX}v6"
                and predecessor_lifecycle.get("state") == "verified"
                and predecessor_lifecycle.get("taskId") == "GT-20"
                and predecessor_lifecycle.get("evidence", {}).get(
                    "evaluatedRevision"
                ) == predecessor_lifecycle.get("subjectRevision")
            )
        elif is_v6:
            expected_predecessor = predecessor_lifecycle
            expected_predecessor_revision = _GT20_V6_PREDECESSOR
            predecessor_shape_valid = (
                isinstance(predecessor_lifecycle, dict)
                and predecessor_lifecycle.get("schema")
                    == f"{_GT20_LIFECYCLE_PREFIX}v5"
                and predecessor_lifecycle.get("state") == "verified"
                and predecessor_lifecycle.get("taskId") == "GT-20"
                and predecessor_lifecycle.get("evidence", {}).get(
                    "evaluatedRevision"
                ) == predecessor_lifecycle.get("subjectRevision")
            )
        elif is_v5:
            expected_predecessor = {
                "schema": "yiyuan-accord-exact-package-evidence-lifecycle/v4",
                "state": "pending",
                "taskId": "GT-20",
                "earliestAffectedBoundary": (
                    "exact-package-command-contract-host-neighbor-and-brand-"
                    "surface-closure"
                ),
                "subjectBinding": (
                    "containing-git-commit-complete-declared-packages"
                ),
                "preservedTaskIds": ["GT-21"],
                "predecessorLifecycleRef": (
                    "fecbdbc3c557e5145e4f037eb9876a09875f9eba:"
                    "product/program.json#/increment/exactPackageEvidenceLifecycle"
                ),
                "commandContractLocator": lifecycle.get(
                    "commandContractLocator"
                ),
                "commandContractSha256": lifecycle.get(
                    "commandContractSha256"
                ),
                "evidence": None,
            }
            expected_predecessor_revision = (
                "fc9c1a7a64257ddf315f862a091a081c4104d81b"
            )
        else:
            expected_predecessor = {
                "schema": "yiyuan-accord-exact-package-evidence-lifecycle/v3",
                "state": "pending",
                "taskId": "GT-20",
                "earliestAffectedBoundary": (
                    "exact-package-evaluator-privacy-termination-cleanup-closure"
                ),
                "subjectBinding": (
                    "containing-git-commit-complete-declared-packages"
                ),
                "preservedTaskIds": ["GT-21"],
                "priorEvidenceRef": (
                    "90501145346f81e02ebdc88fcf3001b39bfdf3d4:"
                    "evals/evidence/2026-09-01-v310-gt20-exact-package-source.json"
                ),
                "subjectRevision": (
                    "7ea91dad811d337f00f75eb521cffacabd73b05f"
                ),
                "evidence": None,
            }
            expected_predecessor_revision = (
                "fecbdbc3c557e5145e4f037eb9876a09875f9eba"
            )
        try:
            _bounded_git_bytes(
                root,
                (
                    "merge-base", "--is-ancestor", predecessor_revision,
                    revision or "HEAD",
                ),
            )
            predecessor_is_ancestor = True
        except _SNAPSHOT_V1_FAILURES:
            predecessor_is_ancestor = False
        if (
            predecessor_lifecycle != expected_predecessor
            or predecessor_revision != expected_predecessor_revision
            or not predecessor_is_ancestor
            or not predecessor_shape_valid
        ):
            errors.append("exact package lifecycle predecessor is invalid")
        command_contract_locator = lifecycle.get("commandContractLocator")
        command_contract_sha256 = lifecycle.get("commandContractSha256")
        if (
            command_contract_locator
            != (
                "evals/contracts/gt20-v4-command-contract.json"
                if is_v6 or is_v7
                else "evals/contracts/gt20-v3-command-contract.json"
            )
            or SHA256_RE.fullmatch(command_contract_sha256 or "") is None
        ):
            errors.append("exact package lifecycle command contract is invalid")
        else:
            try:
                command_contract_raw = _snapshot_or_worktree_bytes(
                    root, command_contract_locator, revision,
                )
                command_contract_object = _strict_json_object(
                    command_contract_raw
                )
                if sha256(command_contract_raw).hexdigest() \
                        != command_contract_sha256:
                    errors.append(
                        "exact package lifecycle command contract digest mismatch"
                    )
                if is_v6 or is_v7:
                    shape_valid = _gt20_v4_overlay_shape_valid(
                        command_contract_object
                    )
                    base = command_contract_object.get("baseContract", {})
                    base_raw = _snapshot_or_worktree_bytes(
                        root, base.get("locator"), revision,
                    )
                    shape_valid = shape_valid and sha256(base_raw).hexdigest() \
                        == base.get("sha256")
                else:
                    commands = command_contract_object.get("commands")
                    roles = {
                        item.get("role") for item in commands or []
                        if isinstance(item, dict)
                    }
                    shape_valid = (
                        command_contract_object.get("schema")
                            == "yiyuan-accord-gt20-command-contract/v1"
                        and command_contract_object.get("budgets") == {
                        "executionTimeoutSeconds": 60,
                        "endToEndTimeoutSeconds": 70,
                        "outputLimitBytes": 4194304,
                        }
                        and isinstance(commands, list)
                        and len(commands) == len(roles) == 54
                        and {
                            "processTreeTerminationProbe",
                            "neighborCodexInstall", "neighborClaudeInstall",
                            "accordCodexFailedUpdate", "accordClaudeFailedUpdate",
                            "codexHookStartup", "codexHookResume",
                            "claudeHookStartup", "claudeHookResume",
                            "accordCodexRemove", "accordClaudeRemove",
                            "afterRemoveCodexMarketplaces",
                            "afterRemoveClaudeMarketplaces",
                            "cleanupCodexNeighborRemove",
                            "cleanupClaudeNeighborRemove",
                            "cleanupCodexMarketplaces",
                            "cleanupClaudeMarketplaces",
                        } <= roles
                    )
                if not shape_valid:
                    errors.append(
                        "exact package lifecycle command contract shape is invalid"
                    )
            except _SNAPSHOT_V1_FAILURES:
                errors.append(
                    "exact package lifecycle command contract is unavailable"
                )
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
    predecessor_ref = snapshot.get("predecessorSnapshotRef") \
        if isinstance(snapshot, dict) else None
    predecessor_revision = predecessor_ref.split(":", 1)[0] \
        if isinstance(predecessor_ref, str) else None
    subject_revision = (
        lifecycle.get("subjectRevision") if is_modern
        else subject_revision or predecessor_revision
    )
    verified_reopened = (
        is_modern and isinstance(snapshot, dict)
        and snapshot.get("state") == "reopened"
        and program.get("status") == "active"
    )
    verified_closed = (
        isinstance(snapshot, dict) and snapshot.get("state") == "closed"
        and program.get("status") == "ready"
    )
    if (
        not isinstance(evidence, dict)
        or set(evidence) != {"locator", "sha256", "evaluatedRevision"}
        or not _nonempty_string(evidence.get("locator"))
        or SHA256_RE.fullmatch(evidence.get("sha256") or "") is None
        or REVISION_RE.fullmatch(evidence.get("evaluatedRevision") or "") is None
        or evidence.get("evaluatedRevision") != subject_revision
        or (is_modern and evidence.get("locator") != (
            _GT20_V7_EVIDENCE_LOCATOR if is_v7
            else
            _GT20_V6_EVIDENCE_LOCATOR if is_v6
            else _GT20_V5_EVIDENCE_LOCATOR
        ))
        or not (verified_reopened or verified_closed)
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
    record_schema = record.get("schema")
    expected_record_schema = (
        "yiyuan-accord-gt20-exact-package-evidence/v5" if is_v7
        else
        "yiyuan-accord-gt20-exact-package-evidence/v4" if is_v6
        else "yiyuan-accord-gt20-exact-package-evidence/v3"
        if is_modern else None
    )
    if is_modern and record_schema != expected_record_schema:
        errors.append("exact package lifecycle record schema is invalid")
    commands = record.get("commands")
    record_contract = {
        "yiyuan-accord-gt20-exact-package-evidence/v1": (
            29, "0e3614bb42d1a4eda9c6b0bb4e8d291f95878084e8a5eff4f17e5e562441d266",
            {"codexCliVersion": 4, "claudeCliVersion": 5, "nodeVersion": 6},
            set(),
        ),
        "yiyuan-accord-gt20-exact-package-evidence/v2": (
            31, "488fb399df972b40a8ebab0fe3901c19f65e82a408f7c728248dcfc8b1e4c417",
            {"gitVersion": 0, "tarVersion": 1, "codexCliVersion": 6,
             "claudeCliVersion": 7, "nodeVersion": 8},
            {"powerShellVersion", "powerShellEdition", "powerShellExecutable",
             "powerShellExecutableSha256"},
        ),
        "yiyuan-accord-gt20-exact-package-evidence/v3": (
            None, None,
            {"gitVersion": "gitVersion", "tarVersion": "tarVersion",
             "codexCliVersion": "codexVersion",
             "claudeCliVersion": "claudeVersion",
             "nodeVersion": "nodeVersion"},
            {"powerShellVersion", "powerShellEdition", "powerShellExecutable",
             "powerShellExecutableSha256", "claudePackageManifest",
             "claudePackageManifestSha256", "claudeTerminalExecutable",
             "claudeTerminalExecutableSha256"},
        ),
        "yiyuan-accord-gt20-exact-package-evidence/v4": (
            None, None,
            {"gitVersion": "gitVersion", "tarVersion": "tarVersion",
             "codexCliVersion": "codexVersion",
             "claudeCliVersion": "claudeVersion",
             "nodeVersion": "nodeVersion"},
            {"powerShellVersion", "powerShellEdition", "powerShellExecutable",
             "powerShellExecutableSha256", "claudePackageManifest",
             "claudePackageManifestSha256", "claudeTerminalExecutable",
             "claudeTerminalExecutableSha256"},
        ),
    }.get(record_schema)
    command_count, command_digest, versions, environment = record_contract or (
        None, None, {}, set(),
    )
    v3_command_fields = {
        "role", "failureCategory", "argv", "resolvedCommand",
        "resolvedCommandSha256",
        "launcher", "launcherSha256", "terminalExecutable",
        "terminalExecutableSha256", "packageManifest",
        "packageManifestSha256", "environmentProfile", "environmentKeys",
        "environmentBindings",
        "inputSha256", "executionTimeoutSeconds", "endToEndTimeoutSeconds",
        "outputLimitBytes", "elapsedMilliseconds", "stdoutBytes",
        "stderrBytes", "timedOut", "terminationRequested",
        "terminationConfirmed", "streamsDrained", "jobActiveProcesses",
        "exitCode", "stdout", "stderr",
    }
    contract_locator = record.get("commandContractLocator")
    contract_raw = current_contract_raw = None
    base_contract_raw = current_base_contract_raw = None
    command_spec = {}
    if record_schema in {
        "yiyuan-accord-gt20-exact-package-evidence/v3",
        "yiyuan-accord-gt20-exact-package-evidence/v4",
    }:
        try:
            expected_locator = (
                "evals/contracts/gt20-v4-command-contract.json"
                if record_schema.endswith("/v4")
                else "evals/contracts/gt20-v3-command-contract.json"
            )
            if contract_locator != expected_locator:
                raise ValueError("command contract locator")
            contract_raw = _snapshot_bytes(
                root, contract_locator, evidence["evaluatedRevision"],
            )
            current_contract_raw = _snapshot_or_worktree_bytes(
                root, contract_locator, revision,
            )
            raw_spec = _strict_json_object(contract_raw)
            if record_schema.endswith("/v4"):
                base_locator = raw_spec.get("baseContract", {}).get("locator")
                if record.get("baseCommandContractLocator") != base_locator:
                    raise ValueError("base command contract locator")
                base_contract_raw = _snapshot_bytes(
                    root, base_locator, evidence["evaluatedRevision"],
                )
                current_base_contract_raw = _snapshot_or_worktree_bytes(
                    root, base_locator, revision,
                )
                if (
                    sha256(base_contract_raw).hexdigest()
                        != raw_spec.get("baseContract", {}).get("sha256")
                    or record.get("baseCommandContractSha256")
                        != sha256(base_contract_raw).hexdigest()
                ):
                    raise ValueError("base command contract digest")
                command_spec = _resolve_gt20_v4_command_contract(
                    raw_spec, _strict_json_object(base_contract_raw),
                ) or {}
            else:
                command_spec = raw_spec
        except _SNAPSHOT_V1_FAILURES:
            command_spec = {}

    contract_profiles = command_spec.get("environmentProfiles") \
        if isinstance(command_spec, dict) else None
    contract_base = contract_profiles.get("base") \
        if isinstance(contract_profiles, dict) else None
    contract_commands = command_spec.get("commands") \
        if isinstance(command_spec, dict) else None
    contract_budgets = command_spec.get("budgets") \
        if isinstance(command_spec, dict) else None
    prior_release = command_spec.get("priorRelease") \
        if isinstance(command_spec, dict) else None
    def _string_set(value):
        return set(value) if (
            isinstance(value, list)
            and all(_nonempty_string(item) for item in value)
        ) else set()

    base_allowed_items = contract_base.get("allowedKeys") \
        if isinstance(contract_base, dict) else None
    base_required_items = contract_base.get("requiredKeys") \
        if isinstance(contract_base, dict) else None
    base_allowed = _string_set(base_allowed_items)
    base_required = _string_set(base_required_items)
    role_commands = {
        command.get("role"): command for command in commands or []
        if isinstance(command, dict) and _nonempty_string(command.get("role"))
    }

    def _expanded_contract_argv(spec):
        argv = spec.get("argv") if isinstance(spec, dict) else None
        if not isinstance(argv, list):
            return None
        prior_revision = prior_release.get("revision") \
            if isinstance(prior_release, dict) else ""
        return [
            item.replace(
                "%CANDIDATE_REVISION%", evidence.get("evaluatedRevision", ""),
            ).replace("%PRIOR_RELEASE_REVISION%", prior_revision)
            if isinstance(item, str) else None
            for item in argv
        ]

    def _v3_command_matches(command, spec):
        is_v4_record = record_schema == (
            "yiyuan-accord-gt20-exact-package-evidence/v4"
        )
        profile_name = spec.get("environmentProfile") \
            if isinstance(spec, dict) else None
        profile = contract_profiles.get(profile_name) \
            if isinstance(contract_profiles, dict) else None
        additional = _string_set(profile.get("additionalKeys")) \
            if isinstance(profile, dict) else set()
        required_additional = _string_set(
            profile.get("requiredAdditionalKeys")
        ) if isinstance(profile, dict) else set()
        if is_v4_record and isinstance(spec, dict):
            additional |= _string_set(spec.get("additionalEnvironmentKeys"))
            required_additional |= _string_set(
                spec.get("requiredEnvironmentKeys")
            )
        environment_keys = command.get("environmentKeys") \
            if isinstance(command, dict) else None
        environment_bindings = command.get("environmentBindings") \
            if isinstance(command, dict) else None
        allowed = base_allowed | additional
        required = base_required | required_additional
        stdout = command.get("stdout") if isinstance(command, dict) else None
        stderr = command.get("stderr") if isinstance(command, dict) else None
        expected_exit = spec.get("expectedExit") \
            if isinstance(spec, dict) else None
        expected_budgets = spec.get("budgets", contract_budgets) \
            if isinstance(spec, dict) else None
        expected_timed_out = expected_exit == "timeout"
        executable = command.get("argv", [None])[0] \
            if isinstance(command.get("argv"), list) and command.get("argv") \
            else None
        expected_profile = (
            "isolated-codex" if executable == "codex"
            else "isolated-claude" if executable == "claude"
            else "preflight-base" if command.get("role") in {
                "candidateCommitCheck", "priorReleaseRevision",
            }
            else "isolated-base"
        )
        spec_fields = {
            "role", "argv", "environmentProfile", "inputSha256",
            "expectedExit",
        }
        if isinstance(spec, dict) and "expectedFailureCategory" in spec:
            spec_fields.add("expectedFailureCategory")
        if isinstance(spec, dict) and "budgets" in spec:
            spec_fields.add("budgets")
        if is_v4_record and isinstance(spec, dict):
            spec_fields |= {
                field for field in (
                    "inputPolicy", "additionalEnvironmentKeys",
                    "requiredEnvironmentKeys", "expectedLoadedPluginVersion",
                ) if field in spec
            }
            if "inputSha256" not in spec:
                spec_fields.remove("inputSha256")
        expected_command_fields = set(v3_command_fields)
        if is_v4_record and isinstance(spec, dict):
            if "inputPolicy" in spec:
                expected_command_fields.add("activationReceipt")
            if spec.get("role") in {
                "accordCodexFailedUpdateAfterStaging",
                "accordClaudeFailedUpdateAfterStaging",
            }:
                expected_command_fields.add("mutationReceipt")
        return (
            set(command) == expected_command_fields
            and set(spec) == spec_fields
            and command.get("role") == spec.get("role")
            and command.get("failureCategory")
                == spec.get("expectedFailureCategory")
            and command.get("argv") == _expanded_contract_argv(spec)
            and command.get("environmentProfile") == profile_name
            and profile_name == expected_profile
            and isinstance(profile, dict)
            and isinstance(environment_keys, list)
            and all(_nonempty_string(item) for item in environment_keys)
            and len(environment_keys) == len(set(environment_keys))
            and set(environment_keys) <= allowed
            and required <= set(environment_keys)
            and isinstance(environment_bindings, dict)
            and environment_bindings == profile.get("bindings")
            and (
                SHA256_RE.fullmatch(command.get("inputSha256") or "")
                    is not None
                if is_v4_record and "inputPolicy" in spec
                else command.get("inputSha256") == spec.get("inputSha256")
            )
            and isinstance(expected_budgets, dict)
            and set(expected_budgets) == {
                "executionTimeoutSeconds", "endToEndTimeoutSeconds",
                "outputLimitBytes",
            }
            and all(type(expected_budgets.get(key)) is int for key in (
                "executionTimeoutSeconds", "endToEndTimeoutSeconds",
                "outputLimitBytes",
            ))
            and (
                expected_budgets == {
                    "executionTimeoutSeconds": 2,
                    "endToEndTimeoutSeconds": 8,
                    "outputLimitBytes": 65536,
                }
                if command.get("role") == "processTreeTerminationProbe"
                else expected_budgets == contract_budgets
            )
            and expected_exit in {"zero", "nonzero", "timeout"}
            and command.get("failureCategory")
                == spec.get("expectedFailureCategory")
            and command.get("executionTimeoutSeconds")
                == expected_budgets.get("executionTimeoutSeconds")
            and command.get("endToEndTimeoutSeconds")
                == expected_budgets.get("endToEndTimeoutSeconds")
            and command.get("outputLimitBytes")
                == expected_budgets.get("outputLimitBytes")
            and isinstance(command.get("elapsedMilliseconds"), (int, float))
            and not isinstance(command.get("elapsedMilliseconds"), bool)
            and 0 <= command["elapsedMilliseconds"]
                <= 1000 * expected_budgets.get("endToEndTimeoutSeconds", -1)
            and isinstance(stdout, str) and isinstance(stderr, str)
            and type(command.get("stdoutBytes")) is int
            and type(command.get("stderrBytes")) is int
            and command.get("stdoutBytes") == len(stdout.encode("utf-8"))
            and command.get("stderrBytes") == len(stderr.encode("utf-8"))
            and 0 <= command["stdoutBytes"] <= command["outputLimitBytes"]
            and 0 <= command["stderrBytes"] <= command["outputLimitBytes"]
            and _nonempty_string(command.get("resolvedCommand"))
            and SHA256_RE.fullmatch(command.get("resolvedCommandSha256") or "")
                is not None
            and command.get("launcher") == command.get("terminalExecutable")
            and command.get("launcherSha256")
                == command.get("terminalExecutableSha256")
            and _nonempty_string(command.get("terminalExecutable"))
            and SHA256_RE.fullmatch(
                command.get("terminalExecutableSha256") or ""
            ) is not None
            and (
                _claude_command_distribution_identity(command)
                if executable == "claude"
                else command.get("packageManifest") is None
                and command.get("packageManifestSha256") is None
            )
            and command.get("timedOut") is expected_timed_out
            and command.get("terminationRequested") is expected_timed_out
            and command.get("terminationConfirmed") is True
            and command.get("streamsDrained") is True
            and type(command.get("jobActiveProcesses")) is int
            and command.get("jobActiveProcesses") == 0
            and type(command.get("exitCode")) is int
            and (
                command["exitCode"] == 0 if expected_exit == "zero"
                else command["exitCode"] != 0
                if expected_exit == "nonzero"
                else command["exitCode"] == 124
                if expected_exit == "timeout" else False
            )
        )

    contract_shape = (
        isinstance(command_spec, dict)
        and set(command_spec) == {
            "schema", "priorRelease", "budgets", "environmentProfiles",
            "commands",
        }
        and command_spec.get("schema")
            == "yiyuan-accord-gt20-command-contract/v1"
        and prior_release == {
            "tag": "v3.0.1",
            "revision": "24cf9f3750ecd700944988e81a519db54b67b8e8",
        }
        and contract_budgets == {
            "executionTimeoutSeconds": 60,
            "endToEndTimeoutSeconds": 70,
            "outputLimitBytes": 4194304,
        }
        and isinstance(contract_profiles, dict)
        and set(contract_profiles) == {
            "base", "preflight-base", "isolated-base", "isolated-codex",
            "isolated-claude",
        }
        and isinstance(contract_base, dict)
        and set(contract_base) == {"allowedKeys", "requiredKeys"}
        and isinstance(base_allowed_items, list)
        and isinstance(base_required_items, list)
        and len(base_allowed_items) == len(base_allowed)
        and len(base_required_items) == len(base_required)
        and base_allowed == {
            "COMSPEC", "PATH", "PATHEXT", "ProgramData", "ProgramFiles",
            "ProgramFiles(x86)", "ProgramW6432", "SystemDrive",
            "SystemRoot", "TEMP", "TMP", "WINDIR",
        }
        and base_required == {
            "COMSPEC", "PATH", "PATHEXT", "SystemRoot", "TEMP", "TMP",
            "WINDIR",
        }
        and base_required <= base_allowed
        and isinstance(contract_commands, list) and contract_commands
        and all(isinstance(item, dict) for item in contract_commands)
        and all(_nonempty_string(item.get("role"))
                for item in contract_commands)
        and len({item.get("role") for item in contract_commands})
            == len(contract_commands)
        and all(
            isinstance(contract_profiles.get(name), dict)
            and set(contract_profiles[name]) == {
                "additionalKeys", "requiredAdditionalKeys", "bindings",
            }
            and isinstance(contract_profiles[name]["additionalKeys"], list)
            and isinstance(
                contract_profiles[name]["requiredAdditionalKeys"], list,
            )
            and len(contract_profiles[name]["additionalKeys"])
                == len(_string_set(contract_profiles[name]["additionalKeys"]))
            and len(contract_profiles[name]["requiredAdditionalKeys"])
                == len(_string_set(
                    contract_profiles[name]["requiredAdditionalKeys"]
                ))
            and _string_set(contract_profiles[name]["requiredAdditionalKeys"])
                <= _string_set(contract_profiles[name]["additionalKeys"])
            and _string_set(contract_profiles[name]["additionalKeys"])
                == {
                    "preflight-base": set(),
                    "isolated-base": set(),
                    "isolated-codex": {"CODEX_HOME"},
                    "isolated-claude": {"CLAUDE_CONFIG_DIR"},
                }[name]
            and _string_set(contract_profiles[name]["requiredAdditionalKeys"])
                == {
                    "preflight-base": set(),
                    "isolated-base": set(),
                    "isolated-codex": {"CODEX_HOME"},
                    "isolated-claude": {"CLAUDE_CONFIG_DIR"},
                }[name]
            and contract_profiles[name]["bindings"] == {
                "preflight-base": {"TEMP": "%TEMP%", "TMP": "%TEMP%"},
                "isolated-base": {
                    "TEMP": "%TASK_ROOT%/command-temp",
                    "TMP": "%TASK_ROOT%/command-temp",
                },
                "isolated-codex": {
                    "CODEX_HOME": "%TASK_ROOT%/codex-host",
                    "TEMP": "%TASK_ROOT%/command-temp",
                    "TMP": "%TASK_ROOT%/command-temp",
                },
                "isolated-claude": {
                    "CLAUDE_CONFIG_DIR": "%TASK_ROOT%/claude-host",
                    "TEMP": "%TASK_ROOT%/command-temp",
                    "TMP": "%TASK_ROOT%/command-temp",
                },
            }[name]
            for name in (
                "preflight-base", "isolated-base", "isolated-codex",
                "isolated-claude",
            )
        )
        and (
            {
                "neighborCodexMarketplaceAdd", "neighborClaudeMarketplaceAdd",
                "neighborCodexInstall", "neighborClaudeInstall",
                "accordCodexInstallPrior", "accordClaudeInstallPrior",
                "accordCodexUpdateCandidate", "accordClaudeUpdateCandidate",
                "processTreeTerminationProbe", "accordCodexRemove",
                "accordClaudeRemove", "afterRemoveCodexMarketplaces",
                "afterRemoveClaudeMarketplaces", "cleanupCodexNeighborRemove",
                "cleanupClaudeNeighborRemove", "cleanupCodexMarketplaces",
                "cleanupClaudeMarketplaces",
            }
            | ({
                "accordCodexFailedUpdateAfterStaging",
                "accordClaudeFailedUpdateAfterStaging",
                "codexHostActivation", "claudeHostActivation",
                "codexHookRuntimeUnitStartup", "codexHookRuntimeUnitResume",
                "claudeHookRuntimeUnitStartup", "claudeHookRuntimeUnitResume",
            } if record_schema == "yiyuan-accord-gt20-exact-package-evidence/v4"
               else {
                "accordCodexFailedUpdate", "accordClaudeFailedUpdate",
                "codexHookStartup", "codexHookResume", "claudeHookStartup",
                "claudeHookResume",
            })
        ) <= {item.get("role") for item in contract_commands}
    )

    def _command_executable(item):
        argv = item.get("argv") if isinstance(item, dict) else None
        return argv[0] if isinstance(argv, list) and argv else None

    same_identity = all(
        len({
            (
                item.get("resolvedCommandSha256"),
                item.get("terminalExecutableSha256"),
                item.get("packageManifestSha256"),
            )
            for item in commands or [] if isinstance(item, dict)
            and _command_executable(item) == executable
        }) == 1
        for executable in ("git", "tar", "codex", "claude", "node")
    )
    modern_commands = (
        record_schema in {
            "yiyuan-accord-gt20-exact-package-evidence/v3",
            "yiyuan-accord-gt20-exact-package-evidence/v4",
        }
        and contract_shape
        and isinstance(commands, list)
        and len(commands) == len(contract_commands)
        and len(role_commands) == len(commands)
        and all(
            _v3_command_matches(command, spec)
            for command, spec in zip(commands, contract_commands, strict=True)
        )
        and same_identity
        and contract_raw == current_contract_raw
        and record.get("commandContractSha256")
            == sha256(contract_raw or b"").hexdigest()
        and (
            record_schema != "yiyuan-accord-gt20-exact-package-evidence/v4"
            or (
                base_contract_raw == current_base_contract_raw
                and record.get("baseCommandContractLocator")
                    == "evals/contracts/gt20-v3-command-contract.json"
                and record.get("baseCommandContractSha256")
                    == sha256(base_contract_raw or b"").hexdigest()
            )
        )
        and (not is_modern or (
            record.get("commandContractLocator")
                == lifecycle.get("commandContractLocator")
            and record.get("commandContractSha256")
                == lifecycle.get("commandContractSha256")
        ))
    )

    def _command_at(index):
        if (
            not isinstance(index, int) or isinstance(index, bool)
            or not isinstance(commands, list)
            or index < 0 or index >= len(commands)
        ):
            return None
        command = commands[index]
        return command if isinstance(command, dict) else None

    def _strict_json_equal(actual, expected):
        if type(actual) is not type(expected):
            return False
        if isinstance(expected, dict):
            return set(actual) == set(expected) and all(
                _strict_json_equal(actual[key], value)
                for key, value in expected.items()
            )
        if isinstance(expected, list):
            return len(actual) == len(expected) and all(
                _strict_json_equal(left, right)
                for left, right in zip(actual, expected, strict=True)
            )
        return actual == expected

    command_contract = (
        modern_commands if record_schema in {
            "yiyuan-accord-gt20-exact-package-evidence/v3",
            "yiyuan-accord-gt20-exact-package-evidence/v4",
        }
        else (isinstance(commands, list) and len(commands) == command_count
              and _snapshot_v1_node_key(commands) == command_digest)
    )
    fixture = record.get("fixture")
    fixture_value = fixture if isinstance(fixture, dict) else {}
    fixed_fixture = {
        "platform": "windows", "priorVersion": "3.0.1",
        "targetVersion": "3.1.0", "userStatePreserved": True,
        "concurrentEditsPreserved": True,
        "unrelatedPluginStatePreserved": True,
        "unrelatedPluginOwnership": "evaluator-owned-fixture",
        "unmanagedSentinelsPreserved": True,
        "credentialEnvironmentInherited": False,
        "hostConfigRootsIsolated": True, "sessionInputsProvided": False,
        "modelTurns": 0,
        "sourceFailureMode": "registered-source-package-path-absent",
        "codexUpdateMechanism": "plugin-add-replaces-installed-version",
        "claudeUpdateMechanism": "plugin-update", "rollbackBytesMatchPriorRelease": True,
        "installedBytesMatchDeclaredPackages": True, "startupHookSilent": True,
        "resumeHookTypedContext": True,
    }
    if record_schema == "yiyuan-accord-gt20-exact-package-evidence/v4":
        fixed_fixture.pop("modelTurns")
        fixed_fixture.pop("rollbackBytesMatchPriorRelease")
        fixed_fixture.update({
            "sessionInputsProvided": True,
            "lifecycleTriggerTurns": 4,
            "externalModelTurns": 0,
            "taskOwnedLoopbackCredential": True,
            "sourceFailureMode": "task-owned-candidate-lock-after-staging",
            "failedUpdateDisposition": (
                "prior-remained-active-with-host-cleaned-or-explicit-task-"
                "owned-staging-cleanup"
            ),
            "automaticRollbackClaimed": False,
            "priorInstalledBytesPreservedAfterFailedUpdate": True,
            "freshPriorInventoryVerified": True,
        })
    if record_schema in {
        "yiyuan-accord-gt20-exact-package-evidence/v3",
        "yiyuan-accord-gt20-exact-package-evidence/v4",
    }:
        fixed_fixture["priorRevision"] = (
            "24cf9f3750ecd700944988e81a519db54b67b8e8"
        )
    if record_schema == "yiyuan-accord-gt20-exact-package-evidence/v4":
        fixed_fixture["failedUpdateRecovery"] = fixture_value.get(
            "failedUpdateRecovery"
        )
    counts = ("codexInstalledFileCount", "claudeInstalledFileCount") + (
        ("neighborCodexInstalledFileCount", "neighborClaudeInstalledFileCount")
        if record_schema in {
            "yiyuan-accord-gt20-exact-package-evidence/v3",
            "yiyuan-accord-gt20-exact-package-evidence/v4",
        } else ()
    )
    version_commands = {
        key: (_command_at(reference) if isinstance(reference, int)
              else role_commands.get(reference))
        for key, reference in versions.items()
    }
    fixture_contract = (
        isinstance(fixture, dict)
        and set(fixture) == set(fixed_fixture) | set(versions) | environment | set(counts)
        and all(
            _strict_json_equal(fixture.get(key), value)
            for key, value in fixed_fixture.items()
        )
        and command_contract
        and all(
            isinstance(version_commands.get(key), dict)
            and fixture.get(key) == version_commands[key]["stdout"].strip()
            for key in versions
        )
        and (not environment or (
            fixture.get("powerShellEdition") == "Core"
            and all(_nonempty_string(fixture.get(key)) for key in environment - {
                "powerShellExecutableSha256", "claudePackageManifestSha256",
                "claudeTerminalExecutableSha256",
            })
            and all(
                SHA256_RE.fullmatch(fixture.get(key) or "") is not None
                for key in environment
                if key.endswith("Sha256")
                and key != "claudePackageManifestSha256"
            )
            and _claude_command_distribution_identity(
                version_commands.get("claudeCliVersion") or {}
            )
        ))
        and (record_schema not in {
                 "yiyuan-accord-gt20-exact-package-evidence/v3",
                 "yiyuan-accord-gt20-exact-package-evidence/v4",
             }
             or (
                 fixture.get("claudePackageManifest")
                    == (version_commands.get("claudeCliVersion") or {}).get(
                        "packageManifest"
                    )
                 and fixture.get("claudePackageManifestSha256")
                    == (version_commands.get("claudeCliVersion") or {}).get(
                        "packageManifestSha256"
                    )
                 and fixture.get("claudeTerminalExecutable")
                    == (version_commands.get("claudeCliVersion") or {}).get(
                        "terminalExecutable"
                    )
                 and fixture.get("claudeTerminalExecutableSha256")
                    == (version_commands.get("claudeCliVersion") or {}).get(
                        "terminalExecutableSha256"
                    )
             ))
        and all(isinstance(fixture.get(key), int) and not isinstance(fixture[key], bool)
                and fixture[key] > 0 for key in counts)
    )
    activation_receipts_contract = True
    failed_update_receipts_contract = True
    frozen_subject = None
    try:
        if not isinstance(subjects, list) or not isinstance(evidence, dict):
            raise ValueError("GT-20 frozen subject is unavailable")
        frozen_subject = {
            locator: sha256(_snapshot_bytes(
                root, locator, evidence.get("evaluatedRevision"),
            )).hexdigest()
            for locator in subjects
        }
    except _SNAPSHOT_V1_FAILURES:
        frozen_subject = None
    if record_schema == "yiyuan-accord-gt20-exact-package-evidence/v4":
        activation_receipts_contract = all(
            _gt20_v4_activation_receipt_valid(
                role_commands.get(role), host, version,
            )
            for role, host, version in (
                ("codexHostActivation", "codex", "3.1.0"),
                ("claudeHostActivation", "claude", "3.1.0"),
            )
        )
        failed_update_receipts_contract = (
            _gt20_v4_failed_update_receipts_valid(
                role_commands, fixture_value, frozen_subject,
            )
        )
    post_state = record.get("postState")
    if record_schema in {
        "yiyuan-accord-gt20-exact-package-evidence/v3",
        "yiyuan-accord-gt20-exact-package-evidence/v4",
    }:
        after_accord = post_state.get("afterAccordRemoval") \
            if isinstance(post_state, dict) else None
        after_cleanup = post_state.get("afterEvaluatorCleanup") \
            if isinstance(post_state, dict) else None
        post_contract = (
            isinstance(post_state, dict)
            and set(post_state) == {
                "afterAccordRemoval", "afterEvaluatorCleanup",
            }
            and _strict_json_equal(after_accord, {
                "codexAccordInstalledEntries": 0,
                "claudeAccordInstalledEntries": 0,
                "codexNeighborInstalledEntries": 1,
                "claudeNeighborInstalledEntries": 1,
                "codexAccordMarketplaceEntries": 0,
                "claudeAccordMarketplaceEntries": 0,
                "codexNeighborMarketplaceEntries": 1,
                "claudeNeighborMarketplaceEntries": 1,
                "taskProcesses": 0,
                "codexAccordCacheFiles": [],
                "claudeAccordCacheFiles": [],
                "neighborInstalledBytesPreserved": True,
                "unmanagedSentinelsPreserved": True,
                "concurrentUserEditsPreserved": True,
            })
            and _strict_json_equal(after_cleanup, {
                "codexInstalledEntries": 0,
                "claudeInstalledEntries": 0,
                "codexMarketplaceEntries": 0,
                "claudeMarketplaceEntries": 0,
                "taskProcesses": 0,
                "taskRootRemoved": True,
            })
        )
    else:
        cache_fields = ("codexCacheFiles", "claudeCacheFiles")
        fixed_post = {
            "codexInstalledEntries": 0, "claudeInstalledEntries": 0,
            "taskProcesses": 0, "taskRootRemoved": True,
        }
        post_contract = (
            isinstance(post_state, dict)
            and set(post_state) == set(fixed_post) | set(cache_fields)
            and all(_strict_json_equal(post_state.get(key), value)
                    for key, value in fixed_post.items())
            and all(
                isinstance(post_state.get(key), list)
                and all(_nonempty_string(item) for item in post_state[key])
                and len(post_state[key]) == len(set(post_state[key]))
                for key in cache_fields
            )
        )
    host_cache_contract = True
    if record_schema in {
        "yiyuan-accord-gt20-exact-package-evidence/v3",
        "yiyuan-accord-gt20-exact-package-evidence/v4",
    }:
        disposition = record.get("hostCacheDisposition")
        codex_disposition = disposition.get("codex", {}) \
            if isinstance(disposition, dict) else {}
        claude_disposition = disposition.get("claude", {}) \
            if isinstance(disposition, dict) else {}
        host_identity = claude_disposition.get("hostIdentity") \
            if isinstance(claude_disposition, dict) else None
        official_contract = claude_disposition.get("officialContract") \
            if isinstance(claude_disposition, dict) else None
        exact_probe = claude_disposition.get("exactHostProbe") \
            if isinstance(claude_disposition, dict) else None
        prior_probe = exact_probe.get("priorVersion") \
            if isinstance(exact_probe, dict) else None
        candidate_probe = exact_probe.get("candidateVersion") \
            if isinstance(exact_probe, dict) else None
        grace_period = exact_probe.get("observedGracePeriodMilliseconds") \
            if isinstance(exact_probe, dict) else None
        role_positions = {
            command.get("role"): index
            for index, command in enumerate(commands or [])
            if isinstance(command, dict) and _nonempty_string(command.get("role"))
        }

        def _probe_pair(value, young_role, expired_role):
            if not isinstance(value, dict) or set(value) != {"young", "expired"}:
                return False
            young = value.get("young")
            expired = value.get("expired")
            return (
                isinstance(young, dict) and isinstance(expired, dict)
                and set(young)
                    == {"ageMilliseconds", "disposition", "commandRole"}
                and set(expired)
                    == {"ageMilliseconds", "disposition", "commandRole"}
                and young.get("disposition") == "retained"
                and expired.get("disposition") == "removed"
                and young.get("commandRole") == young_role
                and expired.get("commandRole") == expired_role
                and isinstance(young.get("ageMilliseconds"), int)
                and not isinstance(young.get("ageMilliseconds"), bool)
                and isinstance(expired.get("ageMilliseconds"), int)
                and not isinstance(expired.get("ageMilliseconds"), bool)
                and 0 <= young["ageMilliseconds"]
                    < grace_period < expired["ageMilliseconds"]
                and role_positions.get(young_role, -1)
                    < role_positions.get(expired_role, -1)
            )

        host_cache_contract = (
            isinstance(post_state, dict)
            and isinstance(commands, list)
            and post_contract
            and isinstance(disposition, dict)
            and set(disposition) == {"codex", "claude"}
            and codex_disposition == {
                "classification": "no-retained-accord-package-cache",
                "hostCallable": False,
            }
            and set(claude_disposition) == {
                "classification", "observedVersions", "retainedVersions",
                "exactAllowlistVerified", "listedOrEnabled", "hostCallable",
                "dataStatePresent", "hostIdentity", "officialContract",
                "exactHostProbe",
            }
            and claude_disposition.get("classification")
                == "host-owned-orphan-cache-swept-to-zero-with-installed-neighbor"
            and claude_disposition.get("observedVersions")
                == ["3.0.1", "3.1.0"]
            and claude_disposition.get("retainedVersions") == []
            and claude_disposition.get("exactAllowlistVerified") is True
            and claude_disposition.get("listedOrEnabled") is False
            and claude_disposition.get("hostCallable") is False
            and claude_disposition.get("dataStatePresent") is False
            and host_identity == {
                "cliVersion": fixture_value.get("claudeCliVersion"),
                "packageManifestSha256": fixture_value.get(
                    "claudePackageManifestSha256"
                ),
                "terminalExecutableSha256": fixture_value.get(
                    "claudeTerminalExecutableSha256"
                ),
            }
            and official_contract == {
                "source": (
                    "https://code.claude.com/docs/en/plugins-reference"
                    "#plugin-caching-and-file-resolution"
                ),
                "gracePeriod": "roughly-14-days",
                "requiresInstalledPlugin": True,
            }
            and isinstance(exact_probe, dict)
            and set(exact_probe) == {
                "ageSignal", "observedGracePeriodMilliseconds", "trigger",
                "priorVersion", "candidateVersion",
                "liveSessionBehavior",
            }
            and exact_probe.get("ageSignal")
                == "orphan-marker-filesystem-mtime"
            and exact_probe.get("trigger") == "plugin-initialization"
            and exact_probe.get("liveSessionBehavior") == "unverified"
            and isinstance(grace_period, int)
            and not isinstance(grace_period, bool) and grace_period > 0
            and _probe_pair(
                prior_probe, "claudeOldYoungSweep", "claudeOldExpiredSweep",
            )
            and _probe_pair(
                candidate_probe, "claudeCandidateYoungSweep",
                "claudeCandidateExpiredSweep",
            )
            and role_positions.get("claudeOldExpiredSweep", -1)
                < role_positions.get("accordClaudeRemove", -1)
                < role_positions.get("claudeCandidateYoungSweep", -1)
                < role_positions.get("claudeCandidateExpiredSweep", -1)
                < role_positions.get("cleanupClaudeNeighborRemove", -1)
        )
    subject_map = record.get("behaviorSubject")
    subject_contract = (
        isinstance(subject_map, dict) and set(subject_map) == set(subjects or [])
        and frozen_subject is not None and subject_map == frozen_subject
        and all(_nonempty_string(locator)
                and isinstance(digest, str) and SHA256_RE.fullmatch(digest) is not None
                for locator, digest in subject_map.items())
    )
    try:
        runner_digest = sha256(_snapshot_or_worktree_bytes(
            root, "scripts/run-gt20-exact-package.ps1", revision,
        )).hexdigest()
        evaluated_runner_digest = sha256(_snapshot_bytes(
            root, "scripts/run-gt20-exact-package.ps1",
            evidence["evaluatedRevision"],
        )).hexdigest()
        runner_digests_valid = all(
            SHA256_RE.fullmatch(value) is not None
            for value in (runner_digest, evaluated_runner_digest)
        )
    except _SNAPSHOT_V1_FAILURES:
        runner_digest = None
        evaluated_runner_digest = None
        runner_digests_valid = False
    expected_record_fields = {
        "schema", "taskId", "evaluatedRevision", "packageSha256",
        "behaviorSubject", "lifecycle", "claimLimit", "runnerSha256",
        "fixture", "commands", "postState",
    }
    expected_claim = (
        "Bounded zero-model Windows lifecycle evidence for exact Commit A "
        "Codex and Claude package bytes in disposable non-empty scopes; "
        "production, unmanaged or cross-OS hosts, ordinary model behavior, "
        "product value and release readiness remain unclaimed."
    )
    if record_schema == "yiyuan-accord-gt20-exact-package-evidence/v3":
        expected_record_fields |= {
            "commandContractLocator", "commandContractSha256",
            "hostCacheDisposition",
        }
        expected_claim = (
            "Bounded zero-model Windows lifecycle, exact command-contract "
            "execution, command privacy and end-to-end process termination "
            "for exact subject Codex and Claude package bytes in disposable "
            "non-empty scopes containing a real evaluator-owned unrelated "
            "plugin and unmanaged sentinels; Claude host-owned "
            "approximately-14-day orphan cleanup was probed for prior and "
            "candidate Accord versions while the unrelated plugin remained "
            "installed, leaving zero Accord cache. Production, real unmanaged "
            "or cross-OS hosts, live-session cache behavior, ordinary model "
            "behavior, product value and release readiness remain unclaimed."
        )
    if record_schema == "yiyuan-accord-gt20-exact-package-evidence/v4":
        expected_record_fields |= {
            "commandContractLocator", "commandContractSha256",
            "baseCommandContractLocator", "baseCommandContractSha256",
            "hostCacheDisposition",
        }
        expected_claim = (
            "Bounded Windows exact-package lifecycle evidence for exact "
            "subject Codex and Claude package bytes in disposable isolated "
            "host roots: mutation-phase failed updates preserved prior "
            "installed bytes and fresh-process inventories selected 3.0.1, "
            "task-owned staging was closed, successful updates "
            "selected 3.1.0 startup/resume, and command privacy, "
            "neighbor/unmanaged state preservation, removal, cache "
            "disposition, process termination, and zero task residue were "
            "verified. The 3.0.1 prior release is Skill-only and no Hook "
            "activation is claimed. All lifecycle triggers used task-owned loopback "
            "failure endpoints with no external model turns. Real account "
            "sessions, current desktop or unmanaged hosts, cross-OS behavior, "
            "comparative product value, release readiness, publication, and "
            "production remain unclaimed."
        )
    expected_lifecycle = {
        "install": "verified",
        (
            "failedUpdateRecovery" if record_schema
            == "yiyuan-accord-gt20-exact-package-evidence/v4"
            else "failedUpdateRollback"
        ): "verified",
        "successfulUpdate": "verified",
        "activation": "verified",
        "remove": "verified",
        "postState": "verified",
        "cleanup": "verified",
    }
    record_checks = {
        "fields": set(record) == expected_record_fields,
        "task": record.get("taskId") == "GT-20",
        "revision": (
            record.get("evaluatedRevision") == evidence.get("evaluatedRevision")
        ),
        "runner": (
            runner_digests_valid
            and SHA256_RE.fullmatch(record.get("runnerSha256") or "") is not None
            and record.get("runnerSha256") == runner_digest
            == evaluated_runner_digest
        ),
        "commands": command_contract,
        "packages": record.get("packageSha256") == packages,
        "subjects": subject_contract,
        "lifecycle": record.get("lifecycle") == expected_lifecycle,
        "claim": record.get("claimLimit") == expected_claim,
        "fixture": fixture_contract,
        "activation": activation_receipts_contract,
        "failed-update": failed_update_receipts_contract,
        "poststate": post_contract,
        "host-cache": host_cache_contract,
        "privacy": not _public_evidence_contains_private_material(record),
    }
    failed_record_checks = [
        name for name, valid in record_checks.items() if not valid
    ]
    if failed_record_checks:
        errors.append(
            "exact package evidence record contract is invalid: "
            + ",".join(failed_record_checks)
        )
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
        closed_stage_state = (
            "latest-closed-stage-snapshot-prepared-for-containing-commit-binding"
        )
        replay_stage_state = (
            "latest-recorded-stage-snapshot-with-successor-replay-active"
        )
        expected_stage_snapshot_states = {
            "active": {closed_stage_state, replay_stage_state},
            "blocked": {closed_stage_state, replay_stage_state},
            "completed": {closed_stage_state},
        }.get(increment_state, set())
        if process.get("stageSnapshotState") not in expected_stage_snapshot_states \
                or not _contains_markers(process.get("currentStageRule"), (
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
    independent_review_decision=None,
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
        if (
            criterion.get("id") == "R4"
            and assessment == "verified"
            and not evidence
            and independent_review_decision != "pass"
        ):
            errors.append(
                f"{label} R4 cannot self-attest independent review completion"
            )
            verified = False
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


def _external_review_decision(root, acceptance, review_bundle, errors):
    r4 = next((
        criterion for criterion in acceptance.get("criteria", [])
        if isinstance(criterion, dict) and criterion.get("id") == "R4"
    ), None)
    if (
        not isinstance(r4, dict)
        or r4.get("assessment") != "verified"
        or r4.get("evidence") != []
        or review_bundle is None
    ):
        return None
    try:
        revision = _bounded_git_bytes(
            root, ["rev-parse", "--verify", "HEAD^{commit}"], 64,
        ).decode("ascii").strip()
        tree = _bounded_git_bytes(
            root, ["rev-parse", "--verify", "HEAD^{tree}"], 64,
        ).decode("ascii").strip()
        if REVISION_RE.fullmatch(revision) is None or REVISION_RE.fullmatch(tree) is None:
            raise ValueError("invalid Git object id")
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        errors.append("external review bundle: exact HEAD subject is unavailable")
        return "fail"

    result = evaluate_review_bundle(review_bundle, revision, tree)
    errors.extend(
        f"external review bundle: {error}"
        for error in result["errors"]
    )
    return result["decision"]


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


def _snapshot_v1_evidence_errors(
    root, program, acceptance, revision, require_verified_criteria=True,
):
    errors, bindings = [], []

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
            bindings.append((prefix, locator, expected, require_json))

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
        if require_verified_criteria and criterion.get("assessment") != "verified":
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
    cache = _SNAPSHOT_READ_CACHE.get()
    try:
        content = cache.read_many(
            root, [item[1] for item in bindings], revision,
        ) if cache is not None else {
            item[1]: _snapshot_bytes(root, item[1], revision) for item in bindings
        }
    except _SNAPSHOT_V1_FAILURES:
        content = {}
        for locator in dict.fromkeys(item[1] for item in bindings):
            try:
                content[locator] = (
                    cache.read(root, locator, revision)
                    if cache is not None
                    else _snapshot_bytes(root, locator, revision)
                )
            except _SNAPSHOT_V1_FAILURES:
                pass
    for prefix, locator, expected, require_json in bindings:
        try:
            raw = content[locator]
            if sha256(raw).hexdigest() != expected:
                errors.append(f"{prefix} digest mismatch")
            if require_json:
                _strict_json_object(raw)
        except _SNAPSHOT_V1_FAILURES:
            errors.append(f"{prefix} repository evidence is unavailable")
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
    closed = isinstance(node, dict) and node.get("state") == "closed"
    verified_replay = isinstance(node, dict) and isinstance(
        node.get("replay"), dict,
    ) and node["replay"].get("evidenceState") == "verified"
    if closed or verified_replay:
        errors.extend(_snapshot_v1_evidence_errors(
            root, program, acceptance, revision, closed,
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


@_snapshot_read_scope
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


def verify_product(root, review_bundle=None):
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
    promotion_lanes = FROZEN_GT20_21_REPRESENTATIVE_LANES
    independent_review_decision = _external_review_decision(
        root, acceptance, review_bundle, errors,
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
        independent_review_decision=independent_review_decision,
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
    exact_lifecycle = program.get("increment")
    exact_lifecycle = exact_lifecycle.get("exactPackageEvidenceLifecycle") \
        if isinstance(exact_lifecycle, dict) else None
    errors.extend(
        representative_sample_errors(
            root,
            acceptance,
            required_release_task_ids,
            golden_suite,
            _read_json,
            require_complete=program.get("status") == "ready",
            current_subject_replays={"GT-20"} if gt20_exact_lifecycle_invalidated(
                exact_lifecycle
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
