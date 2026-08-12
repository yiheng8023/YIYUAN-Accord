"""Historical-event-neutral product-control verification for the Harness.

The verifier owns current authority shape, causal-program invariants, evidence
admission, human authority, and bounded process loss. Historical release event
validators live at their accepted Git revisions; they are not carried forward
as current product authority.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
from types import MappingProxyType
from typing import Any, Callable, Mapping


PRODUCT_ID = "agent-autonomy-harness"
CONSTITUTION_ID = "harness-product-constitution-v1"
COMPLETION_EXPRESSION = "O1 && O2 && O3 && O4 && O5"
OUTCOME_IDS = {"O1", "O2", "O3", "O4", "O5"}
GUARDRAIL_IDS = {"G1", "G2", "G3", "G4"}
EXPECTED_CRITERION_IDS = OUTCOME_IDS | GUARDRAIL_IDS
OUTCOME_OPERATIONALIZATION_FIELDS = {
    "sampleUnit",
    "minimumSampleCount",
    "comparisonDesign",
    "preRegistrationFields",
    "requiredMeasures",
    "passRule",
    "falsifiers",
    "humanAuthority",
}
OUTCOME_OPERATIONALIZATION_BASELINES = MappingProxyType(
    {
        "O1": (1, "single-pre-registered-natural-task"),
        "O2": (3, "source-bound-baseline-by-pre-registered-scenario-class"),
        "O3": (3, "bounded-route-cohort-with-retain-option"),
        "O4": (4, "same-version-scorecard-including-pass-and-fail-cases"),
        "O5": (1, "same-task-matched-cross-host-pair"),
    }
)
BOOTSTRAP_REQUIRED_AUTHORITY = {
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/control.py",
}
EXPECTED_AUTHORITY_GLOBS = {"harness/*.py"}
EXCLUDED_AUTHORITY_PARTS = {
    ".git",
    ".tmp",
    "__pycache__",
    "evidence",
    "legacy",
    "fixtures",
}
REQUIRED_USER_AUTHORITY = {
    "product-direction",
    "domain-judgment",
    "new-trust",
    "new-account-or-data-boundary",
    "new-cost",
    "publication",
    "release",
    "accountable-outcome-acceptance",
    "destructive-or-irreversible-action",
}
HUMAN_ONLY_OPERATIONS = {
    "account-connection",
    "destructive-action",
    "irreversible-action",
    "new-account-or-data-boundary",
    "new-cost",
    "new-trust",
    "publication",
    "release",
    "accountable-outcome-acceptance",
}
OPERATION_EFFECTS = {
    "repository-read": "local-read",
    "repository-edit": "bounded-local-write",
    "causal-planning": "bounded-local-write",
    "local-verification": "local-read",
    "progress-accounting": "bounded-local-write",
    "bounded-repository-cleanup": "bounded-local-delete",
    "git-commit": "bounded-local-write",
    "git-push": "bounded-external-write",
    "installed-authorized-capability-use": "bounded-capability-use",
    "coverage-analysis": "local-read",
    "targeted-capability-discovery": "bounded-public-read",
    "capability-static-review": "local-read",
    "inactive-exact-acquisition": "bounded-local-write",
}
PROCESS_LOSS_FIELDS = {
    "maxSameClassUserCorrectionBeforeStop",
    "maxConsecutiveOutcomeNeutralWorkItems",
    "maxMaterialUserToolOrchestrationInterventions",
    "stopOnAuthorityOrIrreversibleIncident",
    "stopOnUnboundedResidue",
}
PROGRAM_STATES = {"active", "paused", "completed"}
INCREMENT_STATES = {"planned", "active", "completed", "cancelled", "stopped"}
WORK_STATES = {"planned", "active", "completed", "cancelled", "stopped"}
TERMINAL_STATES = {"completed", "cancelled", "stopped"}
EXPECTED_WORK_STATE_SEMANTICS = {
    "planned": "bound but not current or executed",
    "active": "current and execution may have started",
    "completed": "execution finished",
    "cancelled": "bound but never active or executed",
    "stopped": "previously active or attempted, then stopped",
}
ASSESSMENTS = {"planned", "computed", "verified"}
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
RELEASE = re.compile(r"^v\d+\.\d+$")
REVISION = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_AUTHORITY_PATTERNS = (
    re.compile(r"agent[-]skills[-]curated", re.IGNORECASE),
    re.compile(r"registry/curation[-]program[-]plan[.]json", re.IGNORECASE),
    re.compile(r"registry/program[-]acceptance[-]map[.]json", re.IGNORECASE),
)
CONVENTIONAL_RESIDUE_NAMES = {".tmp", "__pycache__"}
EXPECTED_PROGRESSION_POLICY = {
    "pausedScope": "no-active-outcome-bearing-increment",
    "agentOwnedWithoutInventedUserTask": [
        "retrospective-counterexample-analysis",
        "bounded-portfolio-curation",
        "mechanism-only-validation",
        "authority-defect-repair",
    ],
    "naturalTaskRequiredFor": [
        "outcome-verification",
        "task-time-capability-activation",
        "behavior-or-value-claim",
    ],
    "historicalFailureRole": "counterevidence-and-replanning-input-only",
    "outcomeClaimBoundary": "O1-O5-require-current-acceptance-evidence",
    "userMustNotInventTasks": True,
}
EXPECTED_CAPABILITY_INFLUENCE_BOUNDARY = {
    "agentsMd": "execution-guidance-only",
    "skillsAndHooks": "advisory-execution-input-only",
    "selfAuthoredSkills": "replaceable-host-projections",
    "peripheralEcosystem": "replaceable-capability-input",
    "cannot": [
        "set-product-direction",
        "create-causal-work-without-observed-problem",
        "expand-authority-trust-data-cost-or-side-effects",
        "promote-evidence-acceptance-or-release-state",
        "override-bound-user-intent-or-current-product-authority",
    ],
    "routeDeltaFields": [
        "goal",
        "input",
        "deliverable",
        "human-round-trip",
        "authority",
        "side-effect",
        "acceptance",
    ],
    "routeDeltaRule": (
        "a capability route may add a requirement only when source-bound evidence "
        "shows it is causally necessary for the bound task; otherwise reject or "
        "downgrade the route"
    ),
    "conflictRule": "bound-user-intent-and-current-product-authority-win",
    "misfitRule": "reject-or-downgrade-the-capability-route",
}
EXPECTED_HISTORICAL_EVIDENCE_BOUNDARY = {
    "role": "non-authoritative evidence and retrospective counterevidence",
    "productAuthority": False,
    "planningAuthority": False,
    "acceptanceAuthority": False,
    "runtimeAuthority": False,
    "releaseAuthority": False,
    "counterevidenceInput": True,
    "mayTriggerReplanning": True,
}


EvidenceValidator = Callable[[dict[str, Any], str, Path, list[str]], bool]
SUPPORTED_EVIDENCE_VALIDATORS: Mapping[str, EvidenceValidator] = MappingProxyType({})


class _InvalidJson(ValueError):
    pass


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidJson(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise _InvalidJson(f"non-finite constant: {value}")


def _parse_json(text: str) -> Any:
    return json.loads(
        text,
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
    )


def _error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        if path.is_symlink():
            _error(errors, f"{label} cannot be a symlink")
            return {}
        value = _parse_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _error(errors, f"missing {label}")
        return {}
    except (json.JSONDecodeError, _InvalidJson):
        _error(errors, f"cannot read {label}: invalid JSON")
        return {}
    except (OSError, UnicodeError) as exc:
        _error(errors, f"cannot read {label}: {exc.__class__.__name__}")
        return {}
    if not isinstance(value, dict):
        _error(errors, f"{label} must be a JSON object")
        return {}
    return value


def _load_authority_json(
    root: Path, relative: str, label: str, errors: list[str]
) -> dict[str, Any]:
    path = _inside_root(root, relative, errors, label)
    if path is None:
        return {}
    return _load_json(path, label, errors)


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        return None
    if len(value) != len(set(value)):
        return None
    return value


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _same_typed_value(value: Any, expected: Any) -> bool:
    if type(value) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(value) == set(expected) and all(
            _same_typed_value(value[key], expected[key]) for key in expected
        )
    if isinstance(expected, list):
        return len(value) == len(expected) and all(
            _same_typed_value(item, expected_item)
            for item, expected_item in zip(value, expected)
        )
    return value == expected


def _relative_locator(value: Any, *, allow_evidence: bool = False) -> str | None:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return None
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        return None
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in parts):
        return None
    folded = {part.casefold() for part in parts}
    excluded = EXCLUDED_AUTHORITY_PARTS - ({"evidence"} if allow_evidence else set())
    if folded & excluded:
        return None
    return PurePosixPath(*parts).as_posix()


def _cleanup_locator(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        return None
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        return None
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", ".."} for part in parts):
        return None
    forbidden = {".git", "evidence", "fixtures", "legacy"}
    if {part.casefold() for part in parts} & forbidden:
        return None
    return PurePosixPath(*parts).as_posix()


def _link_or_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse)


def _inside_root(root: Path, relative: str, errors: list[str], label: str) -> Path | None:
    candidate = root.joinpath(*PurePosixPath(relative).parts)
    try:
        current = root
        for part in PurePosixPath(relative).parts:
            current = current / part
            if _link_or_reparse(current):
                _error(errors, f"{label} cannot traverse a link or reparse point: {relative}")
                return None
        resolved_root = root.resolve(strict=True)
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError):
        _error(errors, f"{label} escapes repository root: {relative}")
        return None
    return candidate


def _path_entry_absent(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _rfc3339_instant(value: Any) -> Decimal | None:
    if not isinstance(value, str) or RFC3339.fullmatch(value) is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    offset_start = len(normalized) - 6
    if offset_start <= 18 or normalized[offset_start] not in {"+", "-"}:
        return None
    head = normalized[:offset_start]
    offset = normalized[offset_start:]
    fraction = ""
    if "." in head:
        prefix, fraction = head.split(".", 1)
        head = prefix
    try:
        moment = datetime.fromisoformat(head + offset).astimezone(timezone.utc)
    except ValueError:
        return None
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = moment - epoch
    seconds = Decimal(delta.days * 86400 + delta.seconds)
    if fraction:
        seconds += Decimal(f"0.{fraction}")
    return seconds
def _authority_files(
    root: Path, constitution: dict[str, Any], errors: list[str]
) -> list[tuple[str, Path]]:
    required = _string_list(constitution.get("requiredAuthorityFiles"))
    globs = _string_list(constitution.get("activeAuthorityGlobs"))
    if required is None or set(required) != BOOTSTRAP_REQUIRED_AUTHORITY:
        _error(errors, "requiredAuthorityFiles must equal the code-owned bootstrap set")
        required = sorted(BOOTSTRAP_REQUIRED_AUTHORITY)
    if globs is None or set(globs) != EXPECTED_AUTHORITY_GLOBS:
        _error(errors, "activeAuthorityGlobs must equal the code-owned lean authority globs")

    found: dict[str, Path] = {}
    product_root = _inside_root(root, "product", errors, "product authority root")
    if product_root is not None:
        try:
            with os.scandir(product_root) as entries:
                for entry in entries:
                    if Path(entry.name).suffix.casefold() != ".json":
                        continue
                    candidate = product_root / entry.name
                    relative = candidate.relative_to(root).as_posix()
                    if relative not in BOOTSTRAP_REQUIRED_AUTHORITY:
                        _error(errors, f"undeclared product authority JSON: {relative}")
        except (OSError, RuntimeError, ValueError):
            _error(errors, "product authority root cannot be enumerated")
    for raw in required:
        relative = _relative_locator(raw)
        if relative is None:
            _error(errors, f"invalid required authority locator: {raw!r}")
            continue
        candidate = _inside_root(root, relative, errors, "authority file")
        if candidate is None:
            continue
        try:
            if not candidate.is_file():
                _error(errors, f"required authority file is missing: {relative}")
                continue
        except OSError:
            _error(errors, f"required authority file cannot be inspected: {relative}")
            continue
        found[relative] = candidate

    harness_root = _inside_root(root, "harness", errors, "Harness authority root")
    if harness_root is not None:
        def record_harness_enumeration_error(error: OSError) -> None:
            _error(errors, "Harness authority closure cannot be enumerated")

        try:
            for current, directories, files in os.walk(
                harness_root,
                topdown=True,
                followlinks=False,
                onerror=record_harness_enumeration_error,
            ):
                current_path = Path(current)
                retained: list[str] = []
                for name in directories:
                    candidate = current_path / name
                    relative = candidate.relative_to(root).as_posix()
                    if name.casefold() == "__pycache__":
                        continue
                    if _link_or_reparse(candidate):
                        _error(errors, f"undeclared Harness authority link: {relative}")
                        continue
                    retained.append(name)
                directories[:] = retained
                for name in files:
                    candidate = current_path / name
                    relative = candidate.relative_to(root).as_posix()
                    if _link_or_reparse(candidate):
                        if current_path == harness_root and candidate.suffix.casefold() == ".py":
                            _inside_root(root, relative, errors, "active authority")
                        else:
                            _error(errors, f"undeclared Harness authority link: {relative}")
                        continue
                    if current_path != harness_root or candidate.suffix.casefold() != ".py":
                        _error(errors, f"undeclared Harness authority file: {relative}")
                        continue
                    checked = _inside_root(root, relative, errors, "active authority")
                    if checked is None:
                        continue
                    try:
                        if not checked.is_file():
                            _error(errors, f"active authority path is invalid: {relative}")
                            continue
                        checked.resolve(strict=True).relative_to(root.resolve(strict=True))
                    except (OSError, RuntimeError, ValueError):
                        _error(errors, f"active authority path is invalid: {relative}")
                        continue
                    found[relative] = checked
        except (OSError, RuntimeError, ValueError):
            _error(errors, "Harness authority closure cannot be enumerated")
    return sorted(found.items())


def _authority_identity_valid(
    files: list[tuple[str, Path]], errors: list[str]
) -> bool:
    before = len(errors)
    for relative, path in files:
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
            if pattern.search(relative):
                _error(errors, f"forbidden predecessor authority path: {relative}")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            _error(errors, f"active authority cannot be read: {relative}")
            continue
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
            if pattern.search(text):
                _error(errors, f"forbidden predecessor identity in active authority: {relative}")
        if path.suffix.casefold() == ".json":
            try:
                document = _parse_json(text)
            except (json.JSONDecodeError, _InvalidJson):
                continue
            stack: list[Any] = [document]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    stack.extend(value.keys())
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)
                elif isinstance(value, str):
                    for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
                        if pattern.search(value):
                            _error(
                                errors,
                                f"forbidden predecessor semantic identity in active authority: {relative}",
                            )
    return len(errors) == before


def _historical_boundary_valid(
    constitution: dict[str, Any], program: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    prior = program.get("priorRelease")
    prior_valid = isinstance(prior, dict) and set(prior) == {
        "release",
        "state",
        "revision",
        "currentAuthority",
    }
    if prior_valid:
        prior_valid = (
            isinstance(prior.get("release"), str)
            and RELEASE.fullmatch(prior["release"]) is not None
            and prior.get("release") != program.get("release")
            and isinstance(prior.get("state"), str)
            and bool(prior["state"].strip())
            and isinstance(prior.get("revision"), str)
            and REVISION.fullmatch(prior["revision"]) is not None
            and prior.get("currentAuthority") is False
        )
    if not prior_valid:
        _error(errors, "program priorRelease must be a non-authoritative historical milestone")
    if not _same_typed_value(
        constitution.get("historicalEvidenceBoundary"),
        EXPECTED_HISTORICAL_EVIDENCE_BOUNDARY,
    ):
        _error(errors, "constitution historicalEvidenceBoundary is invalid")
    milestones = constitution.get("historicalMilestones")
    if not isinstance(milestones, list) or len(milestones) != 1:
        _error(errors, "constitution must retain exactly one historical milestone")
    else:
        milestone = milestones[0]
        expected = dict(prior) if isinstance(prior, dict) else {}
        if not isinstance(milestone, dict) or any(
            milestone.get(key) != value for key, value in expected.items()
        ):
            _error(errors, "constitution historical milestone must match program priorRelease")
        if not isinstance(milestone, dict) or not isinstance(
            milestone.get("claimLimit"), str
        ) or not milestone["claimLimit"].strip():
            _error(errors, "constitution historical milestone requires a claim limit")
    return len(errors) == before


def _supporting_documents_exist(
    root: Path, constitution: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    documents = _string_list(constitution.get("supportingDocuments"))
    if documents is None:
        _error(errors, "supportingDocuments must be a non-empty unique string list")
        return False
    for raw in documents:
        relative = _relative_locator(raw)
        if relative is None:
            _error(errors, f"invalid supporting document locator: {raw!r}")
            continue
        candidate = _inside_root(root, relative, errors, "supporting document")
        if candidate is None:
            continue
        try:
            if not candidate.is_file():
                _error(errors, f"supporting document is missing: {relative}")
        except OSError:
            _error(errors, f"supporting document cannot be inspected: {relative}")
    return len(errors) == before


def _release_identity_valid(
    constitution: dict[str, Any],
    program: dict[str, Any],
    acceptance: dict[str, Any],
    errors: list[str],
) -> bool:
    before = len(errors)
    release = program.get("release")
    if not isinstance(release, str) or RELEASE.fullmatch(release) is None:
        _error(errors, "program release must use v<major>.<minor>")
        release = "invalid"
    expected_program_id = f"harness-product-program-{release}"
    expected_acceptance_id = f"harness-product-acceptance-{release}"
    checks = (
        (
            type(constitution.get("schema")) is int
            and constitution.get("schema") == 1,
            "constitution schema must be integer 1",
        ),
        (
            type(program.get("schema")) is int and program.get("schema") == 1,
            "program schema must be integer 1",
        ),
        (
            type(acceptance.get("schema")) is int
            and acceptance.get("schema") == 1,
            "acceptance schema must be integer 1",
        ),
        (constitution.get("id") == CONSTITUTION_ID, f"constitution id must be {CONSTITUTION_ID}"),
        (program.get("id") == expected_program_id, f"program id must be {expected_program_id}"),
        (acceptance.get("id") == expected_acceptance_id, f"acceptance id must be {expected_acceptance_id}"),
        (constitution.get("productId") == PRODUCT_ID, "constitution productId is invalid"),
        (program.get("productId") == PRODUCT_ID, "program productId is invalid"),
        (acceptance.get("productId") == PRODUCT_ID, "acceptance productId is invalid"),
        (acceptance.get("release") == release, "program and acceptance releases must match"),
        (program.get("constitution") == "product/constitution.json", "program constitution path is invalid"),
        (program.get("acceptance") == "product/acceptance.json", "program acceptance path is invalid"),
        (acceptance.get("program") == "product/program.json", "acceptance program path is invalid"),
        (program.get("completionExpression") == COMPLETION_EXPRESSION, "program completionExpression is invalid"),
        (acceptance.get("completionExpression") == COMPLETION_EXPRESSION, "acceptance completionExpression is invalid"),
        (
            isinstance(constitution.get("purpose"), str) and bool(constitution["purpose"].strip()),
            "constitution purpose is invalid",
        ),
        (
            isinstance(constitution.get("successDefinition"), str)
            and bool(constitution["successDefinition"].strip()),
            "constitution successDefinition is invalid",
        ),
        (
            isinstance(program.get("purpose"), str) and bool(program["purpose"].strip()),
            "program purpose is invalid",
        ),
        (
            isinstance(acceptance.get("progressRule"), str)
            and bool(acceptance["progressRule"].strip()),
            "acceptance progressRule is invalid",
        ),
    )
    for valid, message in checks:
        if not valid:
            _error(errors, message)
    collaboration = constitution.get("collaborationModel")
    if not isinstance(collaboration, dict):
        _error(errors, "constitution collaborationModel is invalid")
    else:
        if _string_list(collaboration.get("userContributions")) is None:
            _error(errors, "constitution userContributions are invalid")
        if _string_list(collaboration.get("agentObligations")) is None:
            _error(errors, "constitution agentObligations are invalid")
    for field in ("fixedInvariants", "adaptiveSurfaces", "bootstrapGuards"):
        if _string_list(constitution.get(field)) is None:
            _error(errors, f"constitution {field} are invalid")
    planning = constitution.get("planningModel")
    if not isinstance(planning, dict):
        _error(errors, "constitution planningModel is invalid")
    else:
        if (
            type(planning.get("maxActiveIncrements")) is not int
            or planning.get("maxActiveIncrements") != 1
            or type(planning.get("maxActiveWorkItems")) is not int
            or planning.get("maxActiveWorkItems") != 1
        ):
            _error(errors, "constitution planningModel active limits are invalid")
        if not _same_typed_value(
            planning.get("workStateSemantics"), EXPECTED_WORK_STATE_SEMANTICS
        ):
            _error(errors, "constitution workStateSemantics is invalid")
        if _string_list(planning.get("incrementRequires")) is None:
            _error(errors, "constitution incrementRequires are invalid")
        if _string_list(planning.get("replanWhen")) is None:
            _error(errors, "constitution replanWhen is invalid")
    return len(errors) == before


def _capability_influence_valid(
    constitution: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    if not _same_typed_value(
        constitution.get("capabilityInfluenceBoundary"),
        EXPECTED_CAPABILITY_INFLUENCE_BOUNDARY,
    ):
        _error(errors, "constitution capabilityInfluenceBoundary is invalid")
    return len(errors) == before


def _criteria(
    acceptance: dict[str, Any], errors: list[str]
) -> dict[str, dict[str, Any]]:
    raw = acceptance.get("criteria")
    if not isinstance(raw, list):
        _error(errors, "acceptance criteria must be a list")
        return {}
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            _error(errors, f"acceptance criterion {index} must be an object")
            continue
        criterion_id = item.get("id")
        if not isinstance(criterion_id, str) or not criterion_id:
            _error(errors, f"acceptance criterion {index} must have a string id")
            continue
        if criterion_id in by_id:
            _error(errors, f"duplicate acceptance criterion {criterion_id}")
            continue
        by_id[criterion_id] = item
    if set(by_id) != EXPECTED_CRITERION_IDS:
        _error(errors, "acceptance criteria must contain exactly O1-O5 and G1-G4")
    for criterion_id, item in by_id.items():
        expected_class = "outcome" if criterion_id in OUTCOME_IDS else "guardrail"
        if item.get("class") != expected_class:
            _error(errors, f"criterion {criterion_id} must be classed as {expected_class}")
        for field in ("name", "statement", "metric", "threshold"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                _error(errors, f"criterion {criterion_id} is missing {field}")
        assessment = item.get("assessment")
        if not isinstance(assessment, str) or assessment not in ASSESSMENTS:
            _error(errors, f"criterion {criterion_id} has invalid assessment")
        if criterion_id in GUARDRAIL_IDS and assessment != "computed":
            _error(errors, f"criterion {criterion_id} must be computed")
        if criterion_id in OUTCOME_IDS and assessment == "computed":
            _error(errors, f"criterion {criterion_id} must be planned or verified")
        operationalization = item.get("operationalization")
        if criterion_id in OUTCOME_IDS:
            if (
                not isinstance(operationalization, dict)
                or set(operationalization) != OUTCOME_OPERATIONALIZATION_FIELDS
            ):
                _error(
                    errors,
                    f"criterion {criterion_id} requires the exact operationalization fields",
                )
            else:
                sample_floor, comparison_design = OUTCOME_OPERATIONALIZATION_BASELINES[
                    criterion_id
                ]
                sample_count = operationalization.get("minimumSampleCount")
                if (
                    type(sample_count) is not int
                    or sample_count < sample_floor
                ):
                    _error(
                        errors,
                        f"criterion {criterion_id} minimumSampleCount must be at least {sample_floor}",
                    )
                if operationalization.get("comparisonDesign") != comparison_design:
                    _error(
                        errors,
                        f"criterion {criterion_id} comparisonDesign is invalid",
                    )
                for field in ("sampleUnit", "passRule", "humanAuthority"):
                    if not _nonempty_text(operationalization.get(field)):
                        _error(
                            errors,
                            f"criterion {criterion_id} operationalization {field} is invalid",
                        )
                for field in (
                    "preRegistrationFields",
                    "requiredMeasures",
                    "falsifiers",
                ):
                    if _string_list(operationalization.get(field)) is None:
                        _error(
                            errors,
                            f"criterion {criterion_id} operationalization {field} is invalid",
                        )
        elif "operationalization" in item:
            _error(errors, f"guardrail {criterion_id} cannot declare operationalization")
        if assessment == "verified" and _string_list(item.get("evidence")) is None:
            _error(errors, f"verified criterion {criterion_id} requires evidence")
        if assessment != "verified" and "evidence" in item:
            _error(errors, f"non-verified criterion {criterion_id} cannot bind evidence")
    return by_id


def _objects(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        _error(errors, f"{label} must be a list")
        return []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            _error(errors, f"{label} item {index} must be an object")
            continue
        result.append(item)
    return result


def _program_graph(
    program: dict[str, Any],
    criteria: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    increments = _objects(program.get("increments"), "program increments", errors)
    program_state = program.get("status")
    if not isinstance(program_state, str) or program_state not in PROGRAM_STATES:
        _error(errors, "program status must be active, paused, or completed")
    if not increments and program_state != "paused":
        _error(errors, "only a paused program may have an empty current increment graph")
    active_increment_id = program.get("activeIncrementId")
    active_increments: list[dict[str, Any]] = []
    all_work: list[dict[str, Any]] = []
    increment_ids: set[str] = set()
    work_ids: set[str] = set()
    for increment in increments:
        increment_id = increment.get("id")
        if not isinstance(increment_id, str) or not increment_id:
            _error(errors, "every increment requires a string id")
            continue
        if increment_id in increment_ids:
            _error(errors, f"duplicate increment id {increment_id}")
        increment_ids.add(increment_id)
        increment_state = increment.get("state")
        if not isinstance(increment_state, str) or increment_state not in INCREMENT_STATES:
            _error(errors, f"increment {increment_id} has invalid state")
        if increment_state == "planned":
            _error(errors, f"current program cannot queue planned increment {increment_id}")
        if increment_state == "active":
            active_increments.append(increment)
        correction_class = increment.get("correctionClass")
        if not isinstance(correction_class, str) or not correction_class.strip():
            _error(errors, f"increment {increment_id} requires a correctionClass")
        for field in ("observedProblem", "hypothesis", "falsifier", "stopCondition"):
            if not isinstance(increment.get(field), str) or not increment[field].strip():
                _error(errors, f"increment {increment_id} is missing {field}")
        mapped = _string_list(increment.get("acceptanceIds"))
        if mapped is None or not set(mapped) <= set(criteria):
            _error(errors, f"increment {increment_id} has invalid acceptanceIds")
        work_items = _objects(increment.get("workItems"), f"increment {increment_id} workItems", errors)
        if not work_items:
            _error(errors, f"increment {increment_id} must contain at least one work item")
        active_work_count = 0
        for work in work_items:
            work_id = work.get("id")
            if not isinstance(work_id, str) or not work_id:
                _error(errors, f"increment {increment_id} has work without a string id")
                continue
            if work_id in work_ids:
                _error(errors, f"duplicate work item id {work_id}")
            work_ids.add(work_id)
            work_state = work.get("state")
            if not isinstance(work_state, str) or work_state not in WORK_STATES:
                _error(errors, f"work item {work_id} has invalid state")
            if work_state == "planned":
                _error(errors, f"current increment cannot queue planned work item {work_id}")
            if work_state == "active":
                active_work_count += 1
                if increment.get("state") != "active":
                    _error(errors, f"active work item {work_id} must belong to the active increment")
            work_mapped = _string_list(work.get("acceptanceIds"))
            if work_mapped is None or not set(work_mapped) <= set(criteria):
                _error(errors, f"work item {work_id} has invalid acceptanceIds")
            elif mapped is not None and not set(work_mapped) <= set(mapped):
                _error(
                    errors,
                    f"work item {work_id} acceptanceIds exceed increment {increment_id}",
                )
            if _string_list(work.get("operationIds")) is None:
                _error(errors, f"work item {work_id} requires non-empty operationIds")
            if _string_list(work.get("deliverables")) is None:
                _error(errors, f"work item {work_id} requires non-empty deliverables")
            all_work.append(work)
        if active_work_count > 1:
            _error(errors, f"increment {increment_id} has more than one active work item")
        if increment_state == "active" and active_work_count != 1:
            _error(errors, f"active increment {increment_id} must have exactly one active work item")
        if increment_state in TERMINAL_STATES and any(
            not isinstance(work.get("state"), str)
            or work.get("state") not in TERMINAL_STATES
            for work in work_items
        ):
            _error(errors, f"terminal increment {increment_id} has non-terminal work")

    if program_state == "active":
        if len(active_increments) != 1:
            _error(errors, "active program must have exactly one active increment")
        elif active_increment_id != active_increments[0].get("id"):
            _error(errors, "activeIncrementId must identify the active increment")
    elif active_increment_id is not None or active_increments:
        _error(errors, f"{program_state} program must have no active increment")
    if program_state in {"paused", "completed"} and any(
        not isinstance(increment.get("state"), str)
        or increment.get("state") not in TERMINAL_STATES
        for increment in increments
    ):
        _error(errors, f"{program_state} program must have a terminal increment graph")
    active = active_increments[0] if len(active_increments) == 1 else None
    return increments, all_work, active


def _progression_policy_valid(program: dict[str, Any], errors: list[str]) -> bool:
    before = len(errors)
    if not _same_typed_value(
        program.get("progressionPolicy"), EXPECTED_PROGRESSION_POLICY
    ):
        _error(errors, "program progressionPolicy is invalid")
    return len(errors) == before


def _authority_guardrail(
    program: dict[str, Any], all_work: list[dict[str, Any]], errors: list[str]
) -> bool:
    before = len(errors)
    boundary = program.get("authorityBoundary")
    if not isinstance(boundary, dict):
        _error(errors, "program authorityBoundary must be an object")
        return False
    user = _string_list(boundary.get("userOwns"))
    agent = _string_list(boundary.get("agentOwnsWithinBoundedAuthority"))
    if user is None or not REQUIRED_USER_AUTHORITY <= set(user):
        _error(errors, "program userOwns omits a mandatory human authority")
    if agent is None:
        _error(errors, "program agent authority must be a non-empty string list")
        agent = []
    unknown_agent_operations = set(agent) - set(OPERATION_EFFECTS)
    if unknown_agent_operations:
        _error(errors, "program agent authority contains an unknown operation")
    if set(agent) & (REQUIRED_USER_AUTHORITY | HUMAN_ONLY_OPERATIONS):
        _error(errors, "agent authority overlaps a human-only authority")
    for work in all_work:
        work_state = work.get("state")
        if not isinstance(work_state, str) or work_state not in {
            "active",
            "completed",
            "stopped",
        }:
            continue
        operations = _string_list(work.get("operationIds")) or []
        if set(operations) - set(OPERATION_EFFECTS):
            _error(errors, f"work item {work.get('id')} contains an unknown operation")
        if not set(operations) <= set(agent):
            _error(errors, f"work item {work.get('id')} exceeds agent authority")
    return len(errors) == before


def _process_loss_guardrail(
    root: Path,
    increments: list[dict[str, Any]],
    validated_work_outcomes: Mapping[str, set[str]],
    errors: list[str],
) -> bool:
    before = len(errors)
    previous_correction_class: str | None = None
    for increment in increments:
        state = increment.get("state")
        if state == "planned":
            continue
        budget = increment.get("processLossBudget")
        increment_id = increment.get("id")
        if not isinstance(budget, dict) or set(budget) != PROCESS_LOSS_FIELDS:
            _error(errors, f"increment {increment_id} requires the exact process-loss budget fields")
            continue
        integer_fields = (
            "maxSameClassUserCorrectionBeforeStop",
            "maxConsecutiveOutcomeNeutralWorkItems",
            "maxMaterialUserToolOrchestrationInterventions",
        )
        for field in integer_fields:
            value = budget.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                _error(errors, f"process-loss budget {field} must be a non-negative integer")
        if budget.get("maxSameClassUserCorrectionBeforeStop") != 1:
            _error(errors, "same-class user correction budget must stop before recurrence")
        neutral_budget = budget.get("maxConsecutiveOutcomeNeutralWorkItems")
        if neutral_budget not in {0, 1}:
            _error(errors, "outcome-neutral work budget must be zero or one")
        for field in ("stopOnAuthorityOrIrreversibleIncident", "stopOnUnboundedResidue"):
            if budget.get(field) is not True:
                _error(errors, f"process-loss budget {field} must be true")

        work_items = increment.get("workItems") if isinstance(increment.get("workItems"), list) else []
        current_neutral = 0
        max_neutral = 0
        increment_has_validated_outcome = False
        for work in work_items:
            if not isinstance(work, dict):
                continue
            work_state = work.get("state")
            if not isinstance(work_state, str):
                continue
            if work_state == "planned":
                continue
            mapped = _string_list(work.get("acceptanceIds")) or []
            mapped_outcomes = set(mapped) & OUTCOME_IDS
            work_outcomes = validated_work_outcomes.get(work.get("id"), set())
            if mapped_outcomes & work_outcomes:
                increment_has_validated_outcome = True
                current_neutral = 0
            else:
                current_neutral += 1
                max_neutral = max(max_neutral, current_neutral)
        if isinstance(neutral_budget, int) and max_neutral > neutral_budget:
            _error(errors, f"increment {increment_id} exceeds its outcome-neutral work budget")
        if state in TERMINAL_STATES:
            if not increment_has_validated_outcome:
                _error(
                    errors,
                    f"closed outcome-neutral increment must leave the current graph: {increment_id}",
                )
            elif state != "completed":
                _error(
                    errors,
                    "only a completed increment may retain validated outcome "
                    f"binding: {increment_id}",
                )
        correction_class = increment.get("correctionClass")
        if (
            isinstance(correction_class, str)
            and correction_class
            and correction_class == previous_correction_class
        ):
            _error(errors, f"adjacent increments repeat correctionClass: {correction_class}")
        if isinstance(correction_class, str) and correction_class:
            previous_correction_class = correction_class

        cleanup = increment.get("cleanupBoundary")
        paths = cleanup.get("repositoryTemporaryPaths") if isinstance(cleanup, dict) else None
        paths = _string_list(paths)
        if paths is None:
            _error(errors, f"increment {increment_id} requires exact repository cleanup paths")
            continue
        for raw in paths:
            relative = _cleanup_locator(raw)
            if relative is None:
                _error(errors, f"invalid repository cleanup path: {raw!r}")
                continue
            candidate = _inside_root(root, relative, errors, "cleanup path")
            if candidate is not None and not _path_entry_absent(candidate):
                _error(errors, f"repository cleanup residue remains: {relative}")
    _repository_residue_absent(root, errors)
    return len(errors) == before


def _repository_residue_absent(root: Path, errors: list[str]) -> bool:
    before = len(errors)

    def record_enumeration_error(error: OSError) -> None:
        _error(errors, "repository residue cannot be enumerated")

    try:
        for current, directories, files in os.walk(
            root,
            topdown=True,
            followlinks=False,
            onerror=record_enumeration_error,
        ):
            current_path = Path(current)
            retained: list[str] = []
            for name in directories:
                candidate = current_path / name
                try:
                    relative = candidate.relative_to(root).as_posix()
                except ValueError:
                    _error(errors, "repository residue scan escaped the repository root")
                    continue
                if relative == ".git" or relative.startswith(".git/"):
                    continue
                if _link_or_reparse(candidate):
                    if name.casefold() in CONVENTIONAL_RESIDUE_NAMES:
                        _error(errors, f"repository cleanup residue remains: {relative}")
                    continue
                if name.casefold() in CONVENTIONAL_RESIDUE_NAMES:
                    _error(errors, f"repository cleanup residue remains: {relative}")
                    continue
                retained.append(name)
            directories[:] = retained
            for name in files:
                if name.casefold() not in CONVENTIONAL_RESIDUE_NAMES:
                    continue
                candidate = current_path / name
                try:
                    relative = candidate.relative_to(root).as_posix()
                except ValueError:
                    continue
                if relative == ".git" or relative.startswith(".git/"):
                    continue
                _error(errors, f"repository cleanup residue remains: {relative}")
    except OSError:
        _error(errors, "repository residue cannot be enumerated")
    return len(errors) == before


def _evidence_states(
    root: Path,
    criteria: dict[str, dict[str, Any]],
    work_bindings: Mapping[str, tuple[str, set[str], str]],
    errors: list[str],
) -> tuple[dict[str, bool], bool, dict[str, set[str]]]:
    states = {criterion_id: False for criterion_id in EXPECTED_CRITERION_IDS}
    validated_work_outcomes: dict[str, set[str]] = {}
    evidence_id_locators: dict[str, str] = {}
    before = len(errors)
    for criterion_id in sorted(OUTCOME_IDS):
        criterion = criteria.get(criterion_id, {})
        if criterion.get("assessment") != "verified":
            continue
        locators = _string_list(criterion.get("evidence")) or []
        valid = bool(locators)
        criterion_work_ids: set[str] = set()
        for raw in locators:
            relative = _relative_locator(raw, allow_evidence=True)
            evidence_path = PurePosixPath(relative) if relative is not None else None
            if (
                evidence_path is None
                or evidence_path.parent != PurePosixPath("product/evidence")
                or evidence_path.suffix != ".json"
            ):
                _error(errors, f"criterion {criterion_id} has invalid evidence locator: {raw!r}")
                valid = False
                continue
            candidate = _inside_root(root, relative, errors, "evidence file")
            if candidate is None:
                valid = False
                continue
            document = _load_json(candidate, f"evidence {relative}", errors)
            validator = document.get("validator")
            validator_kind = validator.get("kind") if isinstance(validator, dict) else None
            criterion_ids = _string_list(document.get("criterionIds"))
            source = document.get("source")
            authority = document.get("authority")
            result = document.get("result")
            increment_id = document.get("incrementId")
            work_id = document.get("workItemId")
            work_binding = work_bindings.get(work_id) if _nonempty_text(work_id) else None
            evidence_id = document.get("id")
            observed_at = _rfc3339_instant(document.get("observedAt"))
            decided_at = (
                _rfc3339_instant(authority.get("decidedAt"))
                if isinstance(authority, dict)
                else None
            )
            prior_locator = (
                evidence_id_locators.get(evidence_id)
                if _nonempty_text(evidence_id)
                else None
            )
            if prior_locator is not None and prior_locator != relative:
                _error(errors, f"duplicate evidence id {evidence_id}: {relative}")
            elif _nonempty_text(evidence_id):
                evidence_id_locators[evidence_id] = relative
            shape_valid = (
                type(document.get("schema")) is int
                and document.get("schema") == 1
                and _nonempty_text(evidence_id)
                and (prior_locator is None or prior_locator == relative)
                and criterion_ids is not None
                and criterion_id in criterion_ids
                and observed_at is not None
                and _nonempty_text(increment_id)
                and _nonempty_text(work_id)
                and work_binding is not None
                and work_binding[0] == increment_id
                and set(criterion_ids) <= OUTCOME_IDS
                and set(criterion_ids) <= work_binding[1]
                and all(
                    declared_id in criteria
                    and criteria[declared_id].get("assessment") == "verified"
                    and relative
                    in (_string_list(criteria[declared_id].get("evidence")) or [])
                    for declared_id in criterion_ids
                )
                and work_binding[2] == "completed"
                and isinstance(source, dict)
                and all(
                    _nonempty_text(source.get(field))
                    for field in ("kind", "locator", "identity")
                )
                and isinstance(authority, dict)
                and authority.get("kind") == "named-accountable-human"
                and _nonempty_text(authority.get("name"))
                and authority.get("decision") == "accepted"
                and decided_at is not None
                and decided_at >= observed_at
                and isinstance(result, dict)
                and result.get("accepted") is True
                and _string_list(document.get("claimLimits")) is not None
                and isinstance(validator_kind, str)
                and type(validator.get("version")) is int
                and validator.get("version") == 1
            )
            if not shape_valid:
                _error(errors, f"criterion {criterion_id} evidence shape is invalid: {relative}")
                valid = False
                continue
            evidence_validator = SUPPORTED_EVIDENCE_VALIDATORS.get(validator_kind)
            if evidence_validator is None:
                _error(errors, f"criterion {criterion_id} has no code-owned evidence validator: {validator_kind}")
                valid = False
                continue
            try:
                validator_result = evidence_validator(document, criterion_id, root, errors)
                if validator_result is not True:
                    _error(
                        errors,
                        f"criterion {criterion_id} evidence validator did not return true: {relative}",
                    )
                    valid = False
                else:
                    criterion_work_ids.add(work_id)
            except Exception as exc:  # fail closed at the public verifier seam
                _error(errors, f"criterion {criterion_id} evidence validator failed closed: {exc.__class__.__name__}")
                valid = False
        states[criterion_id] = valid
        if valid:
            for work_id in criterion_work_ids:
                validated_work_outcomes.setdefault(work_id, set()).add(criterion_id)
    return states, len(errors) == before, validated_work_outcomes


def _verify_product(root: Path) -> dict[str, Any]:
    """Verify the current release contract and return a JSON-serializable report."""

    root = root.resolve()
    errors: list[str] = []
    constitution = _load_authority_json(
        root, "product/constitution.json", "product constitution", errors
    )
    program = _load_authority_json(root, "product/program.json", "product program", errors)
    acceptance = _load_authority_json(
        root, "product/acceptance.json", "product acceptance", errors
    )

    release_identity = _release_identity_valid(constitution, program, acceptance, errors)
    historical_boundary = _historical_boundary_valid(constitution, program, errors)
    capability_influence = _capability_influence_valid(constitution, errors)
    supporting_documents = _supporting_documents_exist(root, constitution, errors)
    criteria_before = len(errors)
    criteria = _criteria(acceptance, errors)
    criteria_valid = len(errors) == criteria_before
    graph_before = len(errors)
    increments, all_work, active_increment = _program_graph(program, criteria, errors)
    graph_valid = len(errors) == graph_before
    progression_policy = _progression_policy_valid(program, errors)
    authority_before = len(errors)
    authority_files = _authority_files(root, constitution, errors)
    authority_identity = _authority_identity_valid(authority_files, errors)
    authority_identity = (
        authority_identity
        and release_identity
        and historical_boundary
        and capability_influence
        and supporting_documents
        and progression_policy
        and len(errors) == authority_before
    )
    work_bindings: dict[str, tuple[str, set[str], str]] = {}
    for increment in increments:
        increment_id = increment.get("id")
        work_items = increment.get("workItems")
        if not isinstance(increment_id, str) or not isinstance(work_items, list):
            continue
        for work in work_items:
            if not isinstance(work, dict) or not isinstance(work.get("id"), str):
                continue
            mapped = _string_list(work.get("acceptanceIds")) or []
            work_state = work.get("state") if isinstance(work.get("state"), str) else ""
            work_bindings[work["id"]] = (increment_id, set(mapped), work_state)
    evidence_states, evidence_valid, validated_work_outcomes = _evidence_states(
        root, criteria, work_bindings, errors
    )
    authority_guardrail = _authority_guardrail(program, all_work, errors)
    process_guardrail = _process_loss_guardrail(
        root, increments, validated_work_outcomes, errors
    ) and graph_valid

    states = {criterion_id: False for criterion_id in EXPECTED_CRITERION_IDS}
    states.update(evidence_states)
    states["G1"] = authority_guardrail
    states["G2"] = criteria_valid and evidence_valid
    states["G3"] = authority_identity
    states["G4"] = process_guardrail

    guardrails_pass = all(states[criterion_id] for criterion_id in GUARDRAIL_IDS)
    if errors or not guardrails_pass:
        for criterion_id in OUTCOME_IDS:
            states[criterion_id] = False
    outcomes_pass = all(states[criterion_id] for criterion_id in OUTCOME_IDS)
    graph_terminal = (
        program.get("status") == "completed"
        and program.get("activeIncrementId") is None
        and all(
            isinstance(increment.get("state"), str)
            and increment.get("state") in TERMINAL_STATES
            for increment in increments
        )
        and all(
            isinstance(work.get("state"), str)
            and work.get("state") in TERMINAL_STATES
            for work in all_work
        )
    )
    accepted = not errors and guardrails_pass and outcomes_pass and graph_terminal
    valid = not errors and guardrails_pass
    return {
        "productId": PRODUCT_ID,
        "release": program.get("release"),
        "valid": valid,
        "completionState": "accepted" if accepted else "in-progress",
        "activeIncrement": program.get("activeIncrementId"),
        "outcomes": {
            "verified": sum(bool(states[item]) for item in OUTCOME_IDS),
            "total": len(OUTCOME_IDS),
        },
        "guardrails": {
            "passed": sum(bool(states[item]) for item in GUARDRAIL_IDS),
            "total": len(GUARDRAIL_IDS),
        },
        "criterionStates": {key: states[key] for key in sorted(states)},
        "errors": errors,
    }


def verify_product(root: Path) -> dict[str, Any]:
    """Verify current product state and fail closed without leaking tracebacks."""

    try:
        return _verify_product(root)
    except Exception as exc:
        return {
            "productId": PRODUCT_ID,
            "release": None,
            "valid": False,
            "completionState": "in-progress",
            "activeIncrement": None,
            "outcomes": {"verified": 0, "total": len(OUTCOME_IDS)},
            "guardrails": {"passed": 0, "total": len(GUARDRAIL_IDS)},
            "criterionStates": {
                key: False for key in sorted(EXPECTED_CRITERION_IDS)
            },
            "errors": [f"verifier failed closed: {exc.__class__.__name__}"],
        }
