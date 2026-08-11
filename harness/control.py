"""Historical-event-neutral product-control verification for the Harness.

The verifier owns current authority shape, causal-program invariants, evidence
admission, human authority, and bounded process loss. Historical release event
validators live at their accepted Git revisions; they are not carried forward
as current product authority.
"""

from __future__ import annotations

from datetime import datetime
import json
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
BOOTSTRAP_REQUIRED_AUTHORITY = {
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
    "harness/__init__.py",
    "harness/__main__.py",
    "harness/control.py",
    "scripts/verify.py",
}
EXPECTED_AUTHORITY_GLOBS = {"harness/*.py"}
SUPPORTING_DOCUMENTS = {
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "docs/architecture.md",
    "docs/strategy/PRODUCT-NORTH-STAR.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "docs/operations/CURRENT-GOAL-MODE-PROMPT.md",
    "docs/operations/CONTINUATION.md",
    "docs/operations/HISTORY.md",
}
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
ASSESSMENTS = {"planned", "computed", "verified"}
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
RELEASE = re.compile(r"^v\d+\.\d+$")
FORBIDDEN_AUTHORITY_PATTERNS = (
    re.compile(r"agent[-]skills[-]curated", re.IGNORECASE),
    re.compile(r"registry/curation[-]program[-]plan[.]json", re.IGNORECASE),
    re.compile(r"registry/program[-]acceptance[-]map[.]json", re.IGNORECASE),
)
V01_CONTROL_AND_TEST_BYTES = 260_917
CURRENT_CONTROL_AND_TEST_MAX_BYTES = V01_CONTROL_AND_TEST_BYTES // 2
V01_RELEASE = "v0.1"
V01_ACCEPTED_REVISION = "be498f960c9e0587d355291fb24261c91e75cd77"
V01_ACCEPTED_STATE = "accepted-repository-control-milestone"
REQUIRED_REPOSITORY_CLEANUP_PATHS = {
    ".tmp",
    "harness/__pycache__",
    "tests/product/__pycache__",
}
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


def _error(errors: list[str], message: str) -> None:
    if message not in errors:
        errors.append(message)


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        if path.is_symlink():
            _error(errors, f"{label} cannot be a symlink")
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _error(errors, f"missing {label}")
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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


def _rfc3339(value: Any) -> bool:
    if not isinstance(value, str) or RFC3339.fullmatch(value) is None:
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    head, separator, offset = normalized.rpartition("+")
    if not separator:
        minus = normalized.rfind("-", 19)
        if minus > 18:
            head, offset = normalized[:minus], normalized[minus:]
            separator = ""
    if "." in head:
        prefix, fraction = head.split(".", 1)
        head = prefix + "." + fraction[:6]
    normalized = head + ("+" + offset if separator else offset)
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


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
        globs = sorted(EXPECTED_AUTHORITY_GLOBS)

    found: dict[str, Path] = {}
    product_root = _inside_root(root, "product", errors, "product authority root")
    try:
        candidates = product_root.glob("*.json") if product_root is not None else []
        for candidate in candidates:
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

    for pattern in globs:
        relative_pattern = _relative_locator(pattern)
        if relative_pattern is None:
            _error(errors, f"invalid active authority glob: {pattern!r}")
            continue
        authority_root = _inside_root(
            root, PurePosixPath(pattern).parts[0], errors, "active authority root"
        )
        if authority_root is None:
            continue
        try:
            candidates = root.glob(relative_pattern)
            for candidate in candidates:
                try:
                    relative = candidate.relative_to(root).as_posix()
                except ValueError:
                    _error(errors, f"authority glob escaped repository root: {pattern}")
                    continue
                parts = {part.casefold() for part in PurePosixPath(relative).parts}
                if parts & EXCLUDED_AUTHORITY_PARTS:
                    _error(errors, f"authority glob activated excluded path: {relative}")
                    continue
                checked = _inside_root(root, relative, errors, "active authority")
                if checked is None:
                    continue
                try:
                    if not checked.is_file():
                        continue
                    checked.resolve(strict=True).relative_to(root.resolve(strict=True))
                except (OSError, RuntimeError, ValueError):
                    _error(errors, f"active authority path is invalid: {relative}")
                    continue
                found[relative] = checked
        except (OSError, RuntimeError, ValueError):
            _error(errors, f"active authority glob cannot be evaluated: {pattern}")
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
                document = json.loads(text)
            except json.JSONDecodeError:
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
    expected = {
        "release": V01_RELEASE,
        "state": V01_ACCEPTED_STATE,
        "revision": V01_ACCEPTED_REVISION,
        "currentAuthority": False,
    }
    if program.get("priorRelease") != expected:
        _error(errors, "program priorRelease must retain the code-owned v0.1 milestone")
    if (
        constitution.get("historicalEvidenceBoundary")
        != EXPECTED_HISTORICAL_EVIDENCE_BOUNDARY
    ):
        _error(errors, "constitution historicalEvidenceBoundary is invalid")
    milestones = constitution.get("historicalMilestones")
    if not isinstance(milestones, list) or len(milestones) != 1:
        _error(errors, "constitution must retain exactly one v0.1 historical milestone")
    else:
        milestone = milestones[0]
        if not isinstance(milestone, dict) or any(
            milestone.get(key) != value for key, value in expected.items()
        ):
            _error(errors, "constitution v0.1 historical milestone identity is invalid")
        if not isinstance(milestone.get("claimLimit"), str) or not milestone[
            "claimLimit"
        ].strip():
            _error(errors, "constitution v0.1 historical milestone requires a claim limit")
    return len(errors) == before


def _supporting_documents_valid(
    root: Path,
    constitution: dict[str, Any],
    program: dict[str, Any],
    errors: list[str],
) -> bool:
    before = len(errors)
    documents = _string_list(constitution.get("supportingDocuments"))
    if documents is None or set(documents) != SUPPORTING_DOCUMENTS:
        _error(errors, "supportingDocuments must equal the code-owned explanatory set")
        documents = sorted(SUPPORTING_DOCUMENTS)
    release = program.get("release")
    active_increment = program.get("activeIncrementId")
    active_increment_marker = (
        active_increment if isinstance(active_increment, str) else "no active increment"
    )
    marker_map: dict[str, tuple[str, ...]] = {
        "README.md": (
            str(release),
            "`0/5`",
            "in-progress",
            "cannot pass O5",
        ),
        "README.zh-CN.md": (
            str(release),
            "`0/5`",
            "in-progress",
            "同宿主第二适配器只能作为一致性证据",
        ),
        "AGENTS.md": ("This file is execution guidance only.",),
        "docs/architecture.md": (str(release),),
        "docs/strategy/PRODUCT-NORTH-STAR.md": (
            str(release),
            "cannot pass O5",
        ),
        "docs/strategy/RESEARCH-AND-POC-PLAN.md": (
            str(release),
            "cannot pass O5",
        ),
        "docs/operations/CURRENT-GOAL-MODE-PROMPT.md": (
            str(release),
            active_increment_marker,
            "O1-O5 false",
        ),
        "docs/operations/CONTINUATION.md": (
            str(release),
            active_increment_marker,
            "`0/5`",
        ),
        "docs/operations/HISTORY.md": (V01_ACCEPTED_REVISION, "product/evidence"),
    }
    for raw in documents:
        relative = _relative_locator(raw)
        if relative is None:
            _error(errors, f"invalid supporting document locator: {raw!r}")
            continue
        candidate = _inside_root(root, relative, errors, "supporting document")
        if candidate is None:
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            _error(errors, f"supporting document cannot be read: {relative}")
            continue
        for marker in marker_map.get(relative, ()):
            if marker not in text:
                _error(errors, f"supporting document parity marker is missing: {relative}: {marker}")
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
        if planning.get("maxActiveIncrements") != 1 or planning.get("maxActiveWorkItems") != 1:
            _error(errors, "constitution planningModel active limits are invalid")
        if _string_list(planning.get("incrementRequires")) is None:
            _error(errors, "constitution incrementRequires are invalid")
        if _string_list(planning.get("replanWhen")) is None:
            _error(errors, "constitution replanWhen is invalid")
    return len(errors) == before


def _capability_influence_valid(
    constitution: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    if (
        constitution.get("capabilityInfluenceBoundary")
        != EXPECTED_CAPABILITY_INFLUENCE_BOUNDARY
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
    if not increments:
        _error(errors, "program must contain at least one causal increment")
    program_state = program.get("status")
    if not isinstance(program_state, str) or program_state not in PROGRAM_STATES:
        _error(errors, "program status must be active, paused, or completed")
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
        if increment_state == "active":
            active_increments.append(increment)
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
            if work_state == "active":
                active_work_count += 1
                if increment.get("state") != "active":
                    _error(errors, f"active work item {work_id} must belong to the active increment")
            work_mapped = _string_list(work.get("acceptanceIds"))
            if work_mapped is None or not set(work_mapped) <= set(criteria):
                _error(errors, f"work item {work_id} has invalid acceptanceIds")
            if _string_list(work.get("operationIds")) is None:
                _error(errors, f"work item {work_id} requires non-empty operationIds")
            if _string_list(work.get("deliverables")) is None:
                _error(errors, f"work item {work_id} requires non-empty deliverables")
            all_work.append(work)
        if active_work_count > 1:
            _error(errors, f"increment {increment_id} has more than one active work item")
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
    if program.get("progressionPolicy") != EXPECTED_PROGRESSION_POLICY:
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
        if not isinstance(work_state, str) or work_state not in {"active", "completed"}:
            continue
        operations = _string_list(work.get("operationIds")) or []
        if set(operations) - set(OPERATION_EFFECTS):
            _error(errors, f"work item {work.get('id')} contains an unknown operation")
        if not set(operations) <= set(agent):
            _error(errors, f"work item {work.get('id')} exceeds agent authority")
    return len(errors) == before


def _process_loss_guardrail(
    root: Path, increments: list[dict[str, Any]], errors: list[str]
) -> bool:
    before = len(errors)
    previous_guardrail_only = False
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
            _error(errors, "guardrail-only work budget must be zero or one")
        for field in ("stopOnAuthorityOrIrreversibleIncident", "stopOnUnboundedResidue"):
            if budget.get(field) is not True:
                _error(errors, f"process-loss budget {field} must be true")

        work_items = increment.get("workItems") if isinstance(increment.get("workItems"), list) else []
        current_neutral = 0
        max_neutral = 0
        increment_guardrail_only = True
        for work in work_items:
            if not isinstance(work, dict):
                continue
            work_state = work.get("state")
            if not isinstance(work_state, str):
                continue
            if work_state in {"planned", "cancelled"}:
                continue
            mapped = _string_list(work.get("acceptanceIds")) or []
            if set(mapped) & OUTCOME_IDS:
                increment_guardrail_only = False
                current_neutral = 0
            else:
                current_neutral += 1
                max_neutral = max(max_neutral, current_neutral)
        if isinstance(neutral_budget, int) and max_neutral > neutral_budget:
            _error(errors, f"increment {increment_id} exceeds its guardrail-only work budget")
        if increment_guardrail_only and previous_guardrail_only:
            _error(errors, "consecutive guardrail-only increments are not allowed")
        previous_guardrail_only = increment_guardrail_only

        cleanup = increment.get("cleanupBoundary")
        paths = cleanup.get("repositoryTemporaryPaths") if isinstance(cleanup, dict) else None
        paths = _string_list(paths)
        if paths is None:
            _error(errors, f"increment {increment_id} requires the baseline repository cleanup paths")
            continue
        if not REQUIRED_REPOSITORY_CLEANUP_PATHS <= set(paths):
            _error(errors, f"increment {increment_id} requires the baseline repository cleanup paths")
        for raw in paths:
            relative = _cleanup_locator(raw)
            if relative is None:
                _error(errors, f"invalid repository cleanup path: {raw!r}")
                continue
            candidate = _inside_root(root, relative, errors, "cleanup path")
            if candidate is not None and not _path_entry_absent(candidate):
                _error(errors, f"repository cleanup residue remains: {relative}")
    return len(errors) == before


def _evidence_states(
    root: Path,
    criteria: dict[str, dict[str, Any]],
    errors: list[str],
) -> tuple[dict[str, bool], bool]:
    states = {criterion_id: False for criterion_id in EXPECTED_CRITERION_IDS}
    before = len(errors)
    for criterion_id in sorted(OUTCOME_IDS):
        criterion = criteria.get(criterion_id, {})
        if criterion.get("assessment") != "verified":
            continue
        locators = _string_list(criterion.get("evidence")) or []
        valid = bool(locators)
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
            shape_valid = (
                document.get("schema") == 1
                and isinstance(document.get("id"), str)
                and criterion_ids is not None
                and criterion_id in criterion_ids
                and _rfc3339(document.get("observedAt"))
                and isinstance(document.get("source"), dict)
                and bool(document.get("source"))
                and isinstance(document.get("authority"), dict)
                and bool(document.get("authority"))
                and isinstance(document.get("result"), dict)
                and bool(document.get("result"))
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
                if not evidence_validator(document, criterion_id, root, errors):
                    valid = False
            except Exception as exc:  # fail closed at the public verifier seam
                _error(errors, f"criterion {criterion_id} evidence validator failed closed: {exc.__class__.__name__}")
                valid = False
        states[criterion_id] = valid
    return states, len(errors) == before


def _implementation_is_smaller(root: Path, errors: list[str]) -> tuple[bool, int]:
    paths = (root / "harness/control.py", root / "tests/product/test_product_control.py")
    try:
        total = sum(path.stat().st_size for path in paths)
    except OSError:
        _error(errors, "current control and product-test size cannot be measured")
        return False, 0
    if total > CURRENT_CONTROL_AND_TEST_MAX_BYTES:
        _error(errors, "current control and product tests are not materially smaller than v0.1")
        return False, total
    return True, total


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

    _release_identity_valid(constitution, program, acceptance, errors)
    historical_boundary = _historical_boundary_valid(constitution, program, errors)
    capability_influence = _capability_influence_valid(constitution, errors)
    supporting_documents = _supporting_documents_valid(root, constitution, program, errors)
    criteria = _criteria(acceptance, errors)
    increments, all_work, active_increment = _program_graph(program, criteria, errors)
    progression_policy = _progression_policy_valid(program, errors)
    authority_before = len(errors)
    authority_files = _authority_files(root, constitution, errors)
    authority_identity = _authority_identity_valid(authority_files, errors)
    authority_identity = (
        authority_identity
        and historical_boundary
        and capability_influence
        and supporting_documents
        and progression_policy
        and len(errors) == authority_before
    )
    _, authority_bytes = _implementation_is_smaller(root, errors)

    evidence_states, evidence_valid = _evidence_states(root, criteria, errors)
    authority_guardrail = _authority_guardrail(program, all_work, errors)
    process_guardrail = _process_loss_guardrail(root, increments, errors)

    states = {criterion_id: False for criterion_id in EXPECTED_CRITERION_IDS}
    states.update(evidence_states)
    states["G1"] = authority_guardrail
    states["G2"] = evidence_valid
    states["G3"] = authority_identity
    states["G4"] = process_guardrail

    guardrails_pass = all(states[criterion_id] for criterion_id in GUARDRAIL_IDS)
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
        "currentControlAndTestBytes": authority_bytes,
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
            "currentControlAndTestBytes": 0,
            "errors": [f"verifier failed closed: {exc.__class__.__name__}"],
        }
