from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import subprocess
from typing import Any


PRODUCT_ID = "agent-autonomy-harness"
COMPLETION_EXPRESSION = "O1 && O2 && O3 && O4 && O5"
OUTCOME_IDS = tuple(f"O{number}" for number in range(1, 6))
GUARDRAIL_IDS = tuple(f"G{number}" for number in range(1, 5))
EXPECTED_CRITERION_IDS = set(OUTCOME_IDS + GUARDRAIL_IDS)
REQUIRED_USER_CONTRIBUTION_IDS = {
    "goals-and-direction",
    "domain-context",
    "corrections",
    "accountable-final-judgment",
}
REQUIRED_AGENT_OBLIGATION_IDS = {
    "omission-detection",
    "assumption-disclosure",
    "counterexample-search",
    "evidence-reconciliation",
    "coverage-supplementation",
    "bounded-autonomous-execution",
}
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
BOUNDED_CLEANUP_PATTERN = re.compile(
    r"\^\(([A-Za-z0-9._/-]+(?:\|[A-Za-z0-9._/-]+)*)\)\$?"
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
O4_SOURCE_FILES = {
    "AGENTS.md",
    "docs/operations/CONTINUATION.md",
    "docs/operations/CURRENT-GOAL-MODE-PROMPT.md",
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
}
O4_EVENT_ID = "o4-fresh-receiver-2026-08-11-01"
O4_OBSERVED_AT = "2026-08-11T12:02:46.4593609+08:00"
O4_SOURCE_REVISION = "64a0f26fd32ad0b378e3dd836ee6f894a22234ec"
O4_RECEIVER_ID = "/root/o4_fresh_receiver"
O4_PROMPT_SHA256 = "1d2c9acac61fb2aa9609f315d2c25044e99f9d2d60ce1ce0b0eb780dc9a0e1c6"
O4_RECEIVER_CLAIM_BOUNDARY = {
    "proves one fresh read-only receiver recovered the material task contract from the repository without user restatement",
    "does not prove continuity across other hosts, models, providers, repositories, or future events",
    "does not prove O3, v0.1 acceptance, production readiness, release readiness, or broad user value",
}
O4_CLAIM_LIMITS = {
    "records one actual Codex sub-agent receiver event with no inherited conversation turns",
    "the repository verifier checks receipt structure and source binding but does not cryptographically attest the external conversation runtime",
    "remote main was checked by the recorder rather than by the read-only receiver",
    "cleanup covers repository ignored state and direct child matches of the declared bounded pattern only",
    "does not authorize capability installation, enablement, account connection, consumer mutation, release, or publication",
}
TEXT_SUFFIXES = {".json", ".md", ".py", ".yml", ".yaml"}
TEXT_FILENAMES = {".gitignore", "LICENSE", "NOTICE"}
SCAN_EXCLUDED_PARTS = {
    ".git",
    ".tmp",
    "legacy",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}
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
BASE_AGENT_OPERATION_IDS = {
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
PORTFOLIO_CURATION_TASK_BINDING = "agent-autonomy-harness-v0.1-closeout"
PORTFOLIO_CURATION_INCREMENT_ID = "increment.capability-lifecycle-product-slice"
PORTFOLIO_CURATION_CONTRACT_REVISION = (
    "485bfb7919267adb27718f1116039b8011249b68"
)
PORTFOLIO_CURATION_EVIDENCE_PATH = (
    "product/evidence/o3-portfolio-cohort-review-2026-08-11.json"
)
PORTFOLIO_CURATION_FALSIFIER = "The cohort adds no decision-relevant coverage"
PORTFOLIO_CURATION_STOP_SOURCES = {
    "trailofbits-differential-review": {
        "sourceId": "trailofbits-skills",
        "source": "https://github.com/trailofbits/skills.git",
        "revision": "e6066e7db1fd57cb35f9a534781ceec595327feb",
    },
    "obra-superpowers": {
        "sourceId": "obra-superpowers",
        "source": "https://github.com/obra/superpowers.git",
        "revision": "44c9b2d6e889982ac18c27d05a19fefe335194e1",
    },
}
PORTFOLIO_CURATION_CLAIM_LIMITS = {
    "The record proves a bounded exact-source static cohort review and an early-stop decision only.",
    "It does not prove candidate behavior, value, cross-host portability, production readiness, release eligibility, or O3 acceptance.",
    "Current route coverage is decision readiness, not a claim that every lifecycle scenario is complete.",
    "No external candidate was installed, enabled, executed, projected, promoted, or persisted.",
    "Cleanup proves only that the exact bounded review root was absent at the recorded post-delete repository check.",
    "The zero-unique-coverage result triggers the current increment falsifier; it does not authorize automatic activation of its later planned work.",
}
OFFICIAL_KPI_EVENT_CONTRACT_PATH = (
    "product/evidence/o3-official-kpi-event-contract-2026-08-11.json"
)
OFFICIAL_KPI_EVENT_CONTRACT_ID = "o3-official-kpi-event-contract-2026-08-11"
OFFICIAL_KPI_EVENT_BASELINE_REVISION = (
    "467d6f56669258e9e3d65c4b27e6e34259d06e18"
)
OFFICIAL_KPI_PLUGIN_ID = "Plugin_fc9843a6fb34819195d6c7802398a8a7"
OFFICIAL_KPI_PLUGIN_VERSION = "0.2.8-13ceeea1f599"
OFFICIAL_KPI_EVENT_PROMPT_SHA256 = (
    "47fd4365927888f6193ea6910bff9decf3aaba7b853bb2228d0fb7625d289718"
)
OFFICIAL_KPI_EVENT_CONTRACT_SHA256 = (
    "3c3ecc0dd9a93e4e270cb4561b8e19dd7fd7e0ebdcd3113c01a146abe8277abc"
)
OFFICIAL_KPI_EVENT_CONTEXT_SHA256 = (
    "609da2a916a95fc7828918995fa038fb0406703506ad568a14d35c9ff7487f73"
)
OFFICIAL_KPI_EVENT_RECEIPT_PATH = (
    "product/evidence/o3-official-kpi-event-receipt-2026-08-11.json"
)
OFFICIAL_KPI_EVENT_RECEIPT_ID = "o3-official-kpi-event-receipt-2026-08-11"
OFFICIAL_KPI_EVENT_RECEIPT_REVISION = (
    "2df8d85f1e9a8881972d5aa6ac587f11dc37aa79"
)
OFFICIAL_KPI_EVENT_RECEIPT_SHA256 = (
    "08cffdbedcee01400beff68efe738bb5d44ad5c7625f049a84d8fd4a6026ebb0"
)
OFFICIAL_KPI_EVENT_NORMALIZED_PROJECTION_SHA256 = (
    "4fa2c0752f5581debc565c59f012abfdbbf6af9c33fdf24460c257f21c5fa106"
)
OFFICIAL_KPI_EVENT_LIFECYCLE_PROJECTION_SHA256 = (
    "6cf73d4b3d71de579f57155139efa6ec30bedbac28152b8519c3b5610286efd8"
)
OFFICIAL_KPI_SCORECARD_CONTEXT_SHA256 = (
    "b0cca1f837ba09e2bfbda1d364336d1f15f4e867fb6bcf6d454259aeff143f30"
)
O3_SPARSE_SCORECARD_PATH = (
    "product/evidence/o3-sparse-scorecard-2026-08-11.json"
)
O3_SPARSE_SCORECARD_ID = "o3-sparse-scorecard-2026-08-11"
O3_SPARSE_SCORECARD_BASELINE_REVISION = (
    "b9d0ec68ab3bf65652c8a6048186f7e1fb7d59ca"
)
O3_SPARSE_SCORECARD_SHA256 = (
    "960eb6b861e087bf43686e726aa005540190f2e136ca1a8fd1ba185db353a5e6"
)
O3_SPARSE_SCORECARD_EVENT_BASELINE_SHA256 = (
    "9724f31e62f0f48397d7e4fbf4c0173b300bcbd56d6bf8b2f630e8ce26470ecd"
)
O3_SPARSE_SOURCE_SHA256 = (
    "d472ce7271d93ecda46a6013c5650280eb2048b8b7ecaeaca447339b867a6d66"
)
O3_LIFECYCLE_CONTRACT_PATH = (
    "product/evidence/o3-official-lifecycle-transaction-contract-2026-08-11.json"
)
O3_LIFECYCLE_CONTRACT_ID = (
    "o3-official-lifecycle-transaction-contract-attempt-2-2026-08-11"
)
O3_LIFECYCLE_CONTRACT_BASELINE_REVISION = (
    "19ee6f5c2b7feb47cbe41e40f5983c13d5ec2e45"
)
O3_LIFECYCLE_CONTRACT_PROMPT_SHA256 = (
    "c03c607324905794fbc231f3bc424c7ad310e7f0c47a3946795a6d8be9cfe7d9"
)
O3_LIFECYCLE_CONTRACT_SHA256 = (
    "27e7ebcfe9bc510210884e64414be7320de33adc2fd232e5924081ebbc34f160"
)
O3_LIFECYCLE_ATTEMPT_1_INCIDENT_PATH = (
    "product/evidence/o3-official-lifecycle-transaction-attempt-1-incident-2026-08-11.json"
)
O3_LIFECYCLE_ATTEMPT_1_INCIDENT_SHA256 = (
    "a39263ad9ff898c95e30b0563de028719e30100407b56c1cb48138fe6cb8cfb2"
)
O3_LIFECYCLE_RAW_EVIDENCE_PATH = (
    "product/evidence/o3-official-lifecycle-transaction-raw-2026-08-11.json"
)
O3_LIFECYCLE_RAW_EVIDENCE_SHA256 = (
    "7116ea3791119db8c5321c2456d3b24e2da0c242c53621cd7491071e1deb2235"
)
O3_LIFECYCLE_OBSERVED_REVISION = (
    "2fdac84f534117acd60e32a1cf457f04e68b5faf"
)
O3_LIFECYCLE_EVIDENCE_REVISION: str | None = None
O3_LIFECYCLE_TEMPORARY_ROOT = (
    ".tmp/o3-official-lifecycle-transaction-2026-08-11"
)
OFFICIAL_KPI_SKILL_IDENTITIES = [
    {
        "name": "analyze-data-quality",
        "relativePath": "skills/analyze-data-quality/SKILL.md",
        "sha256": "9a3c994f87da0c7a8c5ce37bbf08a59fc6f5b4f368475d3d7438f622b753d5f0",
    },
    {
        "name": "design-kpis",
        "relativePath": "skills/design-kpis/SKILL.md",
        "sha256": "fcefdecacd1d64f847fbb7c45e93a6bd49c679dff66b8966ebc74c4dc39b8f21",
    },
]
OFFICIAL_KPI_EVENT_CLAIM_LIMITS = {
    "This contract authorizes one read-only fresh receiver event on named public local sources only.",
    "The installed Skill metadata and event output may support analytical method attribution, not universal host behavior.",
    "The event does not prove O3, capability value, cross-host portability, production readiness, release readiness, or publication readiness.",
    "No external candidate, account, installation, enablement, manager, consumer, or persistent activation is authorized.",
}
O3_LIFECYCLE_CLAIM_LIMIT_SEQUENCE = (
    "This contract authorizes one bounded fresh receiver transaction on the named public local sources and exact paths only.",
    "Attempt 1 remains failed counterevidence; attempt 2 checkpoints preserve interruption facts but never satisfy O3 or replace the final receipt.",
    "Bounded activation means task-time Skill instruction loading and use in the fresh receiver; it does not prove installation, enablement, exposure, persistent activation, or model behavior.",
    "Rollback proves cessation of the named task route plus unchanged Skill hashes and zero declared capability configuration mutation; it does not prove cryptographic context erasure.",
    "A not-applicable projection receipt proves no projection was needed for this route, not general projection support.",
    "The event may support O3 only together with the separately validated sparse scorecard and public fail-closed verifier.",
    "The prompt path allowlist is a task constraint, not a host sandbox; repository checks cannot prove absence of transient or out-of-scope filesystem effects.",
    "The event does not prove cross-host portability, production readiness, release readiness, publication readiness, broad user value, or v0.1 acceptance.",
)
O3_LIFECYCLE_CONTRACT_CLAIM_LIMITS = set(
    O3_LIFECYCLE_CLAIM_LIMIT_SEQUENCE
)
O3_VERIFIED_EVIDENCE_PATHS = [
    O3_SPARSE_SCORECARD_PATH,
    O3_LIFECYCLE_RAW_EVIDENCE_PATH,
]
PORTFOLIO_CURATION_COVERAGE_OBJECTIVE = (
    "decision-relevant-closeout-demand-coverage-with-reduced-user-orchestration"
)
PORTFOLIO_CURATION_INACTIVE_ROOT = ".tmp/o3-capability-review-2026-08-11"
PORTFOLIO_CURATION_DEMAND_IDS = {
    "SE-DISCOVERY-REQ-01",
    "SE-ARCH-DESIGN-01",
    "SE-IMPLEMENT-REVIEW-01",
    "SE-VERIFY-SECURE-01",
    "SE-RELEASE-CHANGE-01",
    "SE-MAINT-MIGRATE-01",
    "SE-MGMT-PRACTICE-01",
}
PORTFOLIO_CURATION_SOURCE_CLASSES = {
    "visible-native-or-runtime",
    "installed-official-or-curated-metadata",
    "public-first-party-documentation",
    "public-first-party-repository",
    "already-reviewed-upstream",
}
PORTFOLIO_CURATION_ALLOWED_OPERATIONS = {
    "coverage-analysis",
    "targeted-capability-discovery",
    "capability-static-review",
    "inactive-exact-acquisition",
}
PORTFOLIO_CURATION_DENIED_OPERATIONS = {
    "account-connection",
    "acceptance-promotion",
    "consumer-projection",
    "enablement",
    "external-capability-mutation",
    "external-capability-preview",
    "installation",
    "manager-mutation",
    "persistent-activation",
    "publication",
    "release",
    "third-party-execution",
}
PORTFOLIO_CURATION_REVIEW_CRITERIA = {
    "activation-projection-rollback-cleanup-cost",
    "dependencies-and-host-compatibility",
    "exact-source-and-immutable-revision",
    "license-and-redistribution",
    "maintenance-and-upstream-ownership",
    "native-and-official-overlap",
    "security-and-supply-chain",
    "task-demand-coverage-delta",
    "verification-and-claim-ceiling",
}
PORTFOLIO_CURATION_VERIFICATION_REQUIREMENTS = {
    "demand-coverage-delta",
    "deterministic-product-verifier",
    "exact-root-deletion-receipt",
    "exact-source-url",
    "immutable-revision",
    "license-hash",
    "product-tests",
    "repository-hash",
    "route-rationale",
    "static-review-receipt",
}
PORTFOLIO_CURATION_CONTEXT_KEYS = {
    "accountDataPolicy",
    "allowedOperations",
    "candidateSourceClasses",
    "cohortPolicy",
    "coverageObjectiveId",
    "demandIds",
    "deniedOperations",
    "inactiveAcquisitionRoot",
    "mode",
    "requiresExactSource",
    "requiresImmutableRevision",
    "reviewCriteria",
    "taskBinding",
    "verificationRequirements",
}
CAPABILITY_CONTEXT_POLICIES = {
    "task-time": {
        "operationIds": {
            "installed-authorized-capability-use",
            "coverage-analysis",
            "targeted-capability-discovery",
            "capability-static-review",
            "inactive-exact-acquisition",
        },
        "stringFields": {
            "taskBinding",
            "gapOrMaterialBenefit",
            "dataBoundary",
            "authorityBoundary",
            "verificationSurface",
        },
        "listFields": set(),
    },
    "portfolio-curation": {
        "operationIds": PORTFOLIO_CURATION_ALLOWED_OPERATIONS,
        "stringFields": {"inactiveAcquisitionRoot"},
        "listFields": set(),
    },
}
CAPABILITY_CONTEXT_OPERATION_IDS = set().union(
    *(policy["operationIds"] for policy in CAPABILITY_CONTEXT_POLICIES.values())
)
ALLOWED_AGENT_OPERATION_IDS = BASE_AGENT_OPERATION_IDS | CAPABILITY_CONTEXT_OPERATION_IDS
AUTHORITY_GATE_OPERATION_IDS = {
    "bound-task-capability-context-required": CAPABILITY_CONTEXT_POLICIES["task-time"][
        "operationIds"
    ],
    "complete-portfolio-curation-contract-required": CAPABILITY_CONTEXT_POLICIES[
        "portfolio-curation"
    ]["operationIds"],
    "separate-live-capability-lifecycle-authorization-required": {
        "external-capability-preview",
        "external-capability-mutation",
        "consumer-projection",
        "rollback",
    },
}


def _inside_root(root: Path, relative: str, errors: list[str]) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        errors.append("authority path must be a non-empty string")
        return None
    normalized = relative.replace("\\", "/")
    if (
        PurePosixPath(normalized).is_absolute()
        or PureWindowsPath(relative).is_absolute()
        or ".." in normalized.split("/")
    ):
        errors.append(f"authority path escapes the product root: {relative}")
        return None
    candidate = root / relative
    if candidate.is_symlink():
        errors.append(f"authority path cannot be a symlink: {relative}")
        return None
    try:
        path = candidate.resolve()
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
        first_part = normalized.split("/", 1)[0]
        if (
            Path(pattern).is_absolute()
            or re.match(r"^[A-Za-z]:[/\\]", pattern)
            or normalized.startswith("//")
            or ".." in parts
        ):
            errors.append(f"constitution authority glob must be relative: {pattern}")
        elif SCAN_EXCLUDED_PARTS.intersection(parts):
            errors.append(f"constitution cannot activate excluded authority locator: {pattern}")
        elif not first_part or any(marker in first_part for marker in "*?[]"):
            errors.append(
                "constitution authority glob must begin with a literal root: "
                f"{pattern}"
            )
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
            for candidate in root.glob(pattern):
                relative = candidate.relative_to(root).as_posix()
                if candidate.is_symlink():
                    errors.append(
                        f"active authority glob cannot include a symlink: {relative}"
                    )
                    continue
                if SCAN_EXCLUDED_PARTS.intersection(
                    part.casefold() for part in candidate.relative_to(root).parts
                ):
                    errors.append(
                        f"active authority glob expanded into an excluded locator: {relative}"
                    )
                    continue
                if not candidate.is_file():
                    continue
                resolved = candidate.resolve()
                resolved.relative_to(root.resolve())
                files.add(resolved)
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
    return (
        not forbidden_content
        and not forbidden_path
        and len(errors) == initial_error_count
    )


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _exact_string_set(value: Any, expected: set[str]) -> bool:
    return (
        _non_empty_string_list(value)
        and len(value) == len(set(value))
        and set(value) == expected
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


def _valid_capability_context(
    work_item: dict[str, Any], operation_ids: set[str]
) -> bool:
    conditional_operations = operation_ids & CAPABILITY_CONTEXT_OPERATION_IDS
    if not conditional_operations:
        return True
    context = work_item.get("capabilityContext")
    if not isinstance(context, dict):
        return False
    mode = context.get("mode")
    if not isinstance(mode, str):
        return False
    policy = CAPABILITY_CONTEXT_POLICIES.get(mode)
    if not policy or not conditional_operations.issubset(policy["operationIds"]):
        return False
    fields_valid = all(
        isinstance(context.get(field), str) and bool(context[field].strip())
        for field in policy["stringFields"]
    ) and all(_non_empty_string_list(context.get(field)) for field in policy["listFields"])
    if mode == "portfolio-curation":
        root_value = context.get("inactiveAcquisitionRoot")
        normalized_root = (
            root_value.replace("\\", "/") if isinstance(root_value, str) else ""
        )
        account_data_policy = context.get("accountDataPolicy")
        cohort_policy = context.get("cohortPolicy")
        fields_valid = (
            fields_valid
            and set(context) == PORTFOLIO_CURATION_CONTEXT_KEYS
            and context.get("taskBinding") == PORTFOLIO_CURATION_TASK_BINDING
            and context.get("coverageObjectiveId")
            == PORTFOLIO_CURATION_COVERAGE_OBJECTIVE
            and _exact_string_set(
                context.get("demandIds"), PORTFOLIO_CURATION_DEMAND_IDS
            )
            and _exact_string_set(
                context.get("candidateSourceClasses"),
                PORTFOLIO_CURATION_SOURCE_CLASSES,
            )
            and context.get("requiresExactSource") is True
            and context.get("requiresImmutableRevision") is True
            and _exact_string_set(
                context.get("allowedOperations"),
                conditional_operations,
            )
            and _exact_string_set(
                context.get("deniedOperations"),
                PORTFOLIO_CURATION_DENIED_OPERATIONS,
            )
            and _exact_string_set(
                context.get("reviewCriteria"),
                PORTFOLIO_CURATION_REVIEW_CRITERIA,
            )
            and _exact_string_set(
                context.get("verificationRequirements"),
                PORTFOLIO_CURATION_VERIFICATION_REQUIREMENTS,
            )
            and isinstance(account_data_policy, dict)
            and account_data_policy
            == {
                "publicOnly": True,
                "accountConnectionAllowed": False,
                "privateDataAllowed": False,
                "credentialUseAllowed": False,
                "uploadAllowed": False,
                "paidServiceAllowed": False,
            }
            and isinstance(cohort_policy, dict)
            and isinstance(cohort_policy.get("maxCandidates"), int)
            and not isinstance(cohort_policy.get("maxCandidates"), bool)
            and 1 <= cohort_policy["maxCandidates"] <= 8
            and isinstance(
                cohort_policy.get("stopAfterConsecutiveNoUniqueCoverage"), int
            )
            and not isinstance(
                cohort_policy.get("stopAfterConsecutiveNoUniqueCoverage"), bool
            )
            and 1
            <= cohort_policy["stopAfterConsecutiveNoUniqueCoverage"]
            <= cohort_policy["maxCandidates"]
            and cohort_policy.get("earlyStopWhenDemandCovered") is True
            and cohort_policy.get("rejectOnBoundaryFailure") is True
            and cohort_policy.get("cleanupRequired") is True
            and normalized_root == PORTFOLIO_CURATION_INACTIVE_ROOT
        )
    task_gap_operations = {
        "targeted-capability-discovery",
        "capability-static-review",
        "inactive-exact-acquisition",
    }
    if mode == "task-time" and operation_ids & task_gap_operations:
        root_value = context.get("inactiveAcquisitionRoot")
        normalized_root = (
            root_value.replace("\\", "/") if isinstance(root_value, str) else ""
        )
        fields_valid = (
            fields_valid
            and isinstance(context.get("capabilityGap"), str)
            and bool(context["capabilityGap"].strip())
            and isinstance(context.get("candidateSourceBoundary"), str)
            and bool(context["candidateSourceBoundary"].strip())
            and _non_empty_string_list(context.get("reviewCriteria"))
            and isinstance(context.get("cohortStopRule"), str)
            and bool(context["cohortStopRule"].strip())
            and normalized_root.startswith(".tmp/")
            and not any(part == ".." for part in normalized_root.split("/"))
        )
    return fields_valid


def _git_json_at_revision(
    root: Path, revision: str, relative: str
) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    try:
        document = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    return document if isinstance(document, dict) else None


def _git_bytes_at_revision(
    root: Path, revision: str, relative: str
) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def _git_revision_is_on_origin_main(root: Path, revision: str) -> bool:
    try:
        result = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                revision,
                "refs/remotes/origin/main",
            ],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def validate_continuation_receipt(root: Path, document: dict[str, Any]) -> bool:
    invocation = document.get("invocation")
    source_packet = document.get("sourcePacket")
    receiver = document.get("receiver")
    continuation = document.get("continuation")
    cleanup_receipt = document.get("cleanupReceipt")
    if not all(
        isinstance(value, dict)
        for value in (
            invocation,
            source_packet,
            receiver,
            continuation,
            cleanup_receipt,
        )
    ):
        return False
    prompt = invocation.get("prompt")
    if not isinstance(prompt, str):
        return False
    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    revision = source_packet.get("revision")
    source_files = source_packet.get("authorityFiles")
    files_read = receiver.get("filesRead")
    live_git = receiver.get("liveGitFacts")
    receiver_delta = continuation.get("receiverDelta")
    claim_boundary = continuation.get("receiverClaimBoundary")
    if not all(isinstance(value, dict) for value in (live_git, receiver_delta)):
        return False
    recovered = receiver_delta.get("recoveredContract")
    if not isinstance(recovered, dict):
        return False
    rationale = recovered.get("causalRationale")
    authority = recovered.get("authorityBoundary")
    acceptance_state = recovered.get("acceptanceState")
    if not all(
        isinstance(value, dict)
        for value in (rationale, authority, acceptance_state)
    ):
        return False
    constitution_at_source = _git_json_at_revision(
        root, O4_SOURCE_REVISION, "product/constitution.json"
    )
    program_at_source = _git_json_at_revision(
        root, O4_SOURCE_REVISION, "product/program.json"
    )
    acceptance_at_source = _git_json_at_revision(
        root, O4_SOURCE_REVISION, "product/acceptance.json"
    )
    if not all(
        isinstance(value, dict)
        for value in (constitution_at_source, program_at_source, acceptance_at_source)
    ):
        return False
    source_increments = program_at_source.get("increments")
    if not isinstance(source_increments, list):
        return False
    active_increments = [
        item
        for item in source_increments
        if isinstance(item, dict) and item.get("state") == "active"
    ]
    if len(active_increments) != 1:
        return False
    source_increment = active_increments[0]
    source_work_items = source_increment.get("workItems")
    if not isinstance(source_work_items, list):
        return False
    source_open_work_ids = [
        item.get("id")
        for item in source_work_items
        if isinstance(item, dict) and item.get("state") == "active"
    ]
    source_rationale = {
        field: source_increment.get(field)
        for field in ("observedProblem", "hypothesis", "falsifier", "stopCondition")
    }
    source_authority = program_at_source.get("authorityBoundary")
    claim_limits = document.get("claimLimits")
    return (
        document.get("criterionId") == "O4"
        and document.get("eventKind") == "fresh-receiver-continuation"
        and document.get("eventId") == O4_EVENT_ID
        and document.get("observedAt") == O4_OBSERVED_AT
        and datetime.fromisoformat(O4_OBSERVED_AT).tzinfo is not None
        and invocation.get("mechanism") == "Codex collaboration sub-agent task"
        and invocation.get("forkTurns") == "none"
        and invocation.get("promptSha256") == O4_PROMPT_SHA256
        and prompt_sha256 == O4_PROMPT_SHA256
        and invocation.get("materialContractValuesProvided") == []
        and source_packet.get("repository") == PRODUCT_ID
        and revision == O4_SOURCE_REVISION
        and source_packet.get("remoteMain") == O4_SOURCE_REVISION
        and source_packet.get("remoteQuery") == "git ls-remote origin refs/heads/main"
        and source_packet.get("liveTruthRechecked") is True
        and _non_empty_string_list(source_files)
        and O4_SOURCE_FILES.issubset(source_files)
        and isinstance(receiver.get("receiverId"), str)
        and bool(receiver["receiverId"].strip())
        and receiver.get("receiverId") == O4_RECEIVER_ID
        and receiver.get("freshContext") is True
        and receiver.get("contextInheritance") == "none"
        and receiver.get("readOnly") is True
        and _non_empty_string_list(files_read)
        and O4_SOURCE_FILES.issubset(files_read)
        and live_git.get("head") == O4_SOURCE_REVISION
        and live_git.get("originMain") == O4_SOURCE_REVISION
        and live_git.get("branch") == "main"
        and live_git.get("upstream") == "origin/main"
        and live_git.get("ahead") == 0
        and live_git.get("behind") == 0
        and live_git.get("clean") is True
        and isinstance(live_git.get("remoteFreshnessLimit"), str)
        and bool(live_git["remoteFreshnessLimit"].strip())
        and continuation.get("realEvent") is True
        and receiver_delta.get("materialRestatementItems") == 0
        and receiver_delta.get("materialRestatements") == []
        and receiver_delta.get("conflicts") == []
        and recovered.get("productGoal") == constitution_at_source.get("purpose")
        and recovered.get("activeIncrementId")
        == program_at_source.get("activeIncrementId")
        and recovered.get("openWorkItemIds") == source_open_work_ids
        and rationale == source_rationale
        and authority == source_authority
        and acceptance_state.get("verifiedOutcomes") == 3
        and acceptance_state.get("totalOutcomes") == 5
        and acceptance_state.get("passedGuardrails") == 4
        and acceptance_state.get("totalGuardrails") == 4
        and acceptance_state.get("completionState") == "in-progress"
        and isinstance(recovered.get("nextAction"), str)
        and bool(recovered["nextAction"].strip())
        and _non_empty_string_list(claim_boundary)
        and set(claim_boundary) == O4_RECEIVER_CLAIM_BOUNDARY
        and len(claim_boundary) == len(O4_RECEIVER_CLAIM_BOUNDARY)
        and _non_empty_string_list(claim_limits)
        and set(claim_limits) == O4_CLAIM_LIMITS
        and len(claim_limits) == len(O4_CLAIM_LIMITS)
        and isinstance(acceptance_at_source.get("criteria"), list)
        and cleanup_receipt.get("remainingIgnoredRepositoryPaths") == 0
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
        errors.append(
            f"cleanup evidence {relative} must declare a start-anchored "
            "relative literal-alternative targetPattern"
        )
    else:
        pattern_match = BOUNDED_CLEANUP_PATTERN.fullmatch(pattern)
        alternatives = pattern_match.group(1).split("|") if pattern_match else []
        alternatives_bounded = bool(alternatives) and all(
            not PurePosixPath(alternative).is_absolute()
            and not PureWindowsPath(alternative).is_absolute()
            and all(
                part not in {"", ".", ".."} for part in alternative.split("/")
            )
            for alternative in alternatives
        )
        if not alternatives_bounded:
            valid = False
            errors.append(
                f"cleanup evidence {relative} targetPattern must be start-anchored relative literal alternatives"
            )
        try:
            re.compile(pattern)
        except (re.error, OverflowError, RecursionError):
            valid = False
            errors.append(f"cleanup evidence {relative} targetPattern must compile")
    if (
        not isinstance(document.get("operation"), str)
        or not document["operation"].strip()
    ):
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
            if document.get("testFixture") is True:
                verified = False
                errors.append(
                    f"verified criterion {criterion_id} cannot use test fixture evidence {relative}"
                )
            if criterion_id == "O2" and not _valid_route_evidence(document):
                verified = False
                errors.append(f"evidence {relative} must contain a source-bound route and authority boundary")
            if criterion_id == "O4":
                if not validate_continuation_receipt(root, document):
                    verified = False
                    errors.append(
                        f"evidence {relative} is not a real continuation receipt"
                    )
                cleanup_receipt = document.get("cleanupReceipt")
                if not isinstance(cleanup_receipt, dict):
                    verified = False
                    errors.append(
                        f"evidence {relative} must contain a cleanup receipt"
                    )
                elif not _validate_cleanup_evidence(
                    cleanup_receipt,
                    f"{relative} cleanupReceipt",
                    errors,
                ):
                    verified = False
            if criterion_id in {"O5", "G4"} and not _validate_cleanup_evidence(document, relative, errors):
                verified = False
        if criterion_id == "O3":
            raw_receipt = _load(root, O3_LIFECYCLE_RAW_EVIDENCE_PATH, errors)
            verified = (
                evidence_paths == O3_VERIFIED_EVIDENCE_PATHS
                and _valid_o3_lifecycle_receipt(root, raw_receipt, errors)
            )
            if not verified:
                errors.append(
                    "criterion O3 must bind the exact scorecard and successful "
                    "lifecycle receipt"
                )
        states[criterion_id] = verified
    return states, claim_limits_complete


def _valid_falsified_increment_evidence(
    root: Path,
    increment: dict[str, Any],
    evidence_paths: Any,
    errors: list[str],
) -> bool:
    increment_id = increment.get("id", "<missing>")
    paths = _string_list(
        evidence_paths,
        f"stopped increment {increment_id} stopEvidence",
        errors,
    )
    if paths != [PORTFOLIO_CURATION_EVIDENCE_PATH]:
        errors.append(
            f"stopped increment {increment_id} must bind its exact falsifier receipt"
        )
        return False
    document = _load(root, paths[0], errors)
    task_binding = document.get("taskBinding")
    observation = document.get("incrementFalsifierObservation")
    cleanup = document.get("cleanupObservation")
    stop_rule = document.get("stopRuleObservation")
    reviews = document.get("candidateReviews")
    source_snapshots = document.get("sourceSnapshots")
    decision_metrics = document.get("decisionMetrics")
    primary_metrics = (
        decision_metrics.get("primary")
        if isinstance(decision_metrics, dict)
        else None
    )
    zero_coverage_metric = next(
        (
            item
            for item in primary_metrics
            if isinstance(item, dict)
            and item.get("id")
            == "first-two-external-candidate-unique-demand-coverage"
        ),
        {},
    ) if isinstance(primary_metrics, list) else {}
    valid_reviews = (
        reviews
        if isinstance(reviews, list)
        and len(reviews) >= 2
        and all(isinstance(item, dict) for item in reviews)
        else []
    )
    first_two_review_ids = [item.get("id") for item in valid_reviews[:2]]
    post_stop_review_ids = [item.get("id") for item in valid_reviews[2:]]
    valid_sources = (
        source_snapshots
        if isinstance(source_snapshots, list)
        and all(isinstance(item, dict) for item in source_snapshots)
        else []
    )
    sources_by_id = {
        item["id"]: item
        for item in valid_sources
        if isinstance(item.get("id"), str) and item["id"].strip()
    }
    source_bindings_valid = all(
        review.get("id") == candidate_id
        and review.get("sourceId") == expected["sourceId"]
        and isinstance(review.get("treeObject"), str)
        and bool(re.fullmatch(r"[0-9a-f]{40}", review["treeObject"]))
        and isinstance(review.get("skillBlob"), str)
        and bool(re.fullmatch(r"[0-9a-f]{40}", review["skillBlob"]))
        and isinstance(review.get("skillSha256"), str)
        and bool(re.fullmatch(r"[0-9a-f]{64}", review["skillSha256"]))
        and isinstance(sources_by_id.get(expected["sourceId"]), dict)
        and sources_by_id[expected["sourceId"]].get("source")
        == expected["source"]
        and sources_by_id[expected["sourceId"]].get("revision")
        == expected["revision"]
        for review, (candidate_id, expected) in zip(
            valid_reviews[:2], PORTFOLIO_CURATION_STOP_SOURCES.items()
        )
    )
    matched_falsifier = (
        observation.get("matchedFalsifier")
        if isinstance(observation, dict)
        else None
    )
    program_falsifier = increment.get("falsifier")
    source_program = _git_json_at_revision(
        root,
        PORTFOLIO_CURATION_CONTRACT_REVISION,
        "product/program.json",
    )
    source_increments = (
        source_program.get("increments")
        if isinstance(source_program, dict)
        else None
    )
    source_increment = next(
        (
            item
            for item in source_increments
            if isinstance(item, dict)
            and item.get("id") == PORTFOLIO_CURATION_INCREMENT_ID
        ),
        {},
    ) if isinstance(source_increments, list) else {}
    source_work_items = source_increment.get("workItems")
    source_acquisition_work = next(
        (
            item
            for item in source_work_items
            if isinstance(item, dict)
            and item.get("id") == "work.acquire-inactive-portfolio-cohort"
        ),
        {},
    ) if isinstance(source_work_items, list) else {}
    source_context = source_acquisition_work.get("capabilityContext")
    cleanup_root = cleanup.get("root") if isinstance(cleanup, dict) else None
    cleanup_root_parts = (
        [part for part in cleanup_root.replace("\\", "/").split("/") if part]
        if isinstance(cleanup_root, str)
        else []
    )
    resolved_parent = cleanup.get("resolvedParent") if isinstance(cleanup, dict) else None
    normalized_resolved_parent = (
        resolved_parent.replace("\\", "/")
        if isinstance(resolved_parent, str)
        else ""
    )
    claim_limits = document.get("claimLimits")
    return (
        increment_id == PORTFOLIO_CURATION_INCREMENT_ID
        and document.get("id") == "o3-portfolio-cohort-review-2026-08-11"
        and document.get("productId") == PRODUCT_ID
        and document.get("release") == "v0.1"
        and document.get("status")
        == "reviewed-no-live-admission-cleanup-complete"
        and isinstance(task_binding, dict)
        and task_binding.get("id") == PORTFOLIO_CURATION_TASK_BINDING
        and task_binding.get("invented") is False
        and task_binding.get("kind") == "real repository comprehensive closeout"
        and task_binding.get("contractRevision")
        == PORTFOLIO_CURATION_CONTRACT_REVISION
        and task_binding.get("contractPath") == "product/program.json"
        and isinstance(source_program, dict)
        and source_program.get("productId") == PRODUCT_ID
        and source_program.get("release") == "v0.1"
        and source_program.get("activeIncrementId")
        == PORTFOLIO_CURATION_INCREMENT_ID
        and source_increment.get("state") == "active"
        and PORTFOLIO_CURATION_FALSIFIER
        in source_increment.get("falsifier", "")
        and source_acquisition_work.get("state") == "active"
        and isinstance(source_context, dict)
        and source_context.get("taskBinding") == PORTFOLIO_CURATION_TASK_BINDING
        and source_context.get("inactiveAcquisitionRoot")
        == PORTFOLIO_CURATION_INACTIVE_ROOT
        and source_context.get("cohortPolicy", {}).get(
            "stopAfterConsecutiveNoUniqueCoverage"
        )
        == 2
        and isinstance(observation, dict)
        and observation.get("incrementId") == increment_id
        and observation.get("triggered") is True
        and isinstance(matched_falsifier, str)
        and matched_falsifier.rstrip(".") == PORTFOLIO_CURATION_FALSIFIER
        and isinstance(program_falsifier, str)
        and PORTFOLIO_CURATION_FALSIFIER in program_falsifier
        and observation.get("hypothesisDisposition") == "falsified"
        and observation.get("laterWorkActivationAllowed") is False
        and isinstance(stop_rule, dict)
        and stop_rule.get("stopTriggered") is True
        and stop_rule.get("maxCandidates")
        == source_context.get("cohortPolicy", {}).get("maxCandidates")
        and stop_rule.get("acquiredCandidateCount") == len(valid_reviews)
        and stop_rule.get("reviewedSourceRepositoryCount") == len(valid_sources)
        and stop_rule.get("consecutiveCandidatesWithNoUniqueCoverage") == 2
        and stop_rule.get("postStopDiscoveryCount") == 0
        and stop_rule.get("stopSequence") == first_two_review_ids
        and stop_rule.get("alreadyAcquiredBeforeStopConclusion")
        == post_stop_review_ids
        and first_two_review_ids == list(PORTFOLIO_CURATION_STOP_SOURCES)
        and all(item.get("uniqueDemandIds") == [] for item in valid_reviews[:2])
        and len(sources_by_id) == len(valid_sources)
        and source_bindings_valid
        and zero_coverage_metric.get("value") == 0
        and zero_coverage_metric.get("denominator")
        == len(PORTFOLIO_CURATION_DEMAND_IDS)
        and isinstance(cleanup, dict)
        and cleanup.get("deleteCompleted") is True
        and cleanup.get("repositoryRecheckExists") is False
        and cleanup.get("remaining") is False
        and cleanup_root_parts[-2:]
        == [".tmp", PORTFOLIO_CURATION_INACTIVE_ROOT.rsplit("/", 1)[-1]]
        and ".." not in cleanup_root_parts
        and normalized_resolved_parent.endswith("/.tmp")
        and cleanup.get("actor") == "user"
        and cleanup.get("operation")
        == "Remove-Item -LiteralPath $target -Recurse -Force"
        and cleanup.get("userReportedPostDeleteTestPath") is False
        and not (root / PORTFOLIO_CURATION_INACTIVE_ROOT).exists()
        and _non_empty_string_list(claim_limits)
        and set(claim_limits) == PORTFOLIO_CURATION_CLAIM_LIMITS
        and len(claim_limits) == len(PORTFOLIO_CURATION_CLAIM_LIMITS)
    )


def _valid_official_kpi_event_contract(
    root: Path,
    work_item: dict[str, Any],
    errors: list[str],
) -> bool:
    if work_item.get("contractEvidence") != OFFICIAL_KPI_EVENT_CONTRACT_PATH:
        return False
    document = _load(root, OFFICIAL_KPI_EVENT_CONTRACT_PATH, errors)
    task_binding = document.get("taskBinding")
    capability = document.get("capabilityIdentity")
    route = document.get("route")
    data_boundary = document.get("dataBoundary")
    authority = document.get("authorityBoundary")
    event = document.get("eventContract")
    scorecard = document.get("scorecardContract")
    measurement = document.get("measurementFramework")
    cleanup = document.get("cleanup")
    context = work_item.get("capabilityContext")
    if not all(
        isinstance(value, dict)
        for value in (
            task_binding,
            capability,
            route,
            data_boundary,
            authority,
            event,
            scorecard,
            measurement,
            cleanup,
            context,
        )
    ):
        return False
    prompt = event.get("prompt")
    prompt_hash = None
    if isinstance(prompt, str):
        try:
            prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        except UnicodeEncodeError:
            pass
    contract_hash = hashlib.sha256(
        json.dumps(
            document,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    context_hash = hashlib.sha256(
        json.dumps(
            context,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    historical = task_binding.get("historicalBaseline")
    source_program = _git_json_at_revision(
        root,
        OFFICIAL_KPI_EVENT_BASELINE_REVISION,
        "product/program.json",
    )
    source_increments = (
        source_program.get("increments")
        if isinstance(source_program, dict)
        else None
    )
    source_increment = next(
        (
            item
            for item in source_increments
            if isinstance(item, dict)
            and item.get("id")
            == "increment.current-official-route-evaluation-slice"
        ),
        {},
    ) if isinstance(source_increments, list) else {}
    source_work_items = source_increment.get("workItems")
    source_active_work_ids = [
        item.get("id")
        for item in source_work_items
        if isinstance(item, dict) and item.get("state") == "active"
    ] if isinstance(source_work_items, list) else []
    primary = measurement.get("primary")
    drivers = measurement.get("drivers")
    guardrails = measurement.get("guardrails")
    primary_ids = [
        item.get("id") for item in primary if isinstance(item, dict)
    ] if isinstance(primary, list) else []
    driver_ids = [
        item.get("id") for item in drivers if isinstance(item, dict)
    ] if isinstance(drivers, list) else []
    guardrail_ids = [
        item.get("id") for item in guardrails if isinstance(item, dict)
    ] if isinstance(guardrails, list) else []
    claim_limits = document.get("claimLimits")
    return (
        contract_hash == OFFICIAL_KPI_EVENT_CONTRACT_SHA256
        and context_hash == OFFICIAL_KPI_EVENT_CONTEXT_SHA256
        and document.get("id") == OFFICIAL_KPI_EVENT_CONTRACT_ID
        and document.get("productId") == PRODUCT_ID
        and document.get("release") == "v0.1"
        and document.get("status") == "bound-pre-event"
        and task_binding.get("id") == PORTFOLIO_CURATION_TASK_BINDING
        and task_binding.get("invented") is False
        and task_binding.get("kind") == "real repository comprehensive closeout"
        and task_binding.get("baselineRevision")
        == OFFICIAL_KPI_EVENT_BASELINE_REVISION
        and isinstance(historical, dict)
        and historical.get("revision")
        == "c53866726834d79a68c61a5b87b4f7ce90698a2c"
        and historical.get("path")
        == "registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json"
        and isinstance(task_binding.get("decision"), str)
        and bool(task_binding["decision"].strip())
        and isinstance(source_program, dict)
        and source_program.get("activeIncrementId")
        == "increment.current-official-route-evaluation-slice"
        and source_increment.get("state") == "active"
        and source_active_work_ids
        == ["work.bind-current-official-route-evaluation-contract"]
        and capability.get("class") == "installed-openai-plugin-skill"
        and capability.get("pluginId") == OFFICIAL_KPI_PLUGIN_ID
        and capability.get("pluginName") == "data-analytics"
        and capability.get("pluginVersion") == OFFICIAL_KPI_PLUGIN_VERSION
        and capability.get("developerName") == "OpenAI"
        and capability.get("license") == "Proprietary"
        and capability.get("packageLocator")
        == "openai-curated-remote/data-analytics/0.2.8-13ceeea1f599"
        and capability.get("skillChain") == OFFICIAL_KPI_SKILL_IDENTITIES
        and capability.get("payloadPolicy")
        == "load installed exact Skill bodies for this event; do not vendor or rewrite them"
        and route.get("shape") == "sequence"
        and route.get("steps")
        == [
            "native-repository-source-binding",
            "installed-openai-analyze-data-quality",
            "installed-openai-design-kpis",
            "native-evidence-reconciliation-and-deterministic-verification",
        ]
        and _exact_string_set(
            data_boundary.get("denied"),
            {
                "private files outside the named repository and Skill locators",
                "credentials or account data",
                "network source expansion",
                "uploads",
                "paid services",
            },
        )
        and _exact_string_set(
            authority.get("denied"),
            {
                "repository writes by the receiver",
                "installation or enablement",
                "account connection",
                "third-party candidate execution",
                "manager or consumer mutation",
                "publication",
                "release",
                "acceptance promotion",
            },
        )
        and event.get("mechanism") == "Codex collaboration sub-agent task"
        and event.get("forkTurns") == "none"
        and event.get("freshContext") is True
        and event.get("receiverReadOnly") is True
        and event.get("outputFormat") == "one JSON object and no Markdown"
        and prompt_hash == OFFICIAL_KPI_EVENT_PROMPT_SHA256
        and event.get("promptSha256") == OFFICIAL_KPI_EVENT_PROMPT_SHA256
        and scorecard.get("nonCartesian") is True
        and scorecard.get("historicalPartials") == 15
        and scorecard.get("evidenceClusters") == 6
        and scorecard.get("lifecycleSlices") == 14
        and scorecard.get("evaluationDimensions") == 12
        and scorecard.get("harnessScenarios") == 13
        and scorecard.get("routeClasses") == 6
        and _exact_string_set(
            scorecard.get("requiredEntryFields"),
            {
                "disposition",
                "evidence",
                "missingEvidence",
                "claimCeiling",
                "routeComparison",
                "humanJudgment",
                "separateAuthorization",
            },
        )
        and primary_ids
        == [
            "decision-bearing-sparse-entry-coverage",
            "material-user-tool-interventions",
            "reproducible-residual-gap-count",
        ]
        and driver_ids
        == ["source-attribution-coverage", "route-comparison-coverage"]
        and guardrail_ids
        == [
            "unsupported-behavior-or-value-claims",
            "persistent-capability-or-repository-mutations-by-receiver",
        ]
        and cleanup.get("persistentStateAllowed") is False
        and cleanup.get("temporaryRoot") is None
        and context.get("mode") == "task-time"
        and context.get("taskBinding")
        == f"{PORTFOLIO_CURATION_TASK_BINDING}@{OFFICIAL_KPI_EVENT_BASELINE_REVISION}"
        and context.get("pluginId") == OFFICIAL_KPI_PLUGIN_ID
        and context.get("pluginVersion") == OFFICIAL_KPI_PLUGIN_VERSION
        and context.get("skillNames")
        == ["analyze-data-quality", "design-kpis"]
        and context.get("eventPromptSha256")
        == OFFICIAL_KPI_EVENT_PROMPT_SHA256
        and context.get("receiverForkTurns") == "none"
        and context.get("receiverReadOnly") is True
        and _non_empty_string_list(claim_limits)
        and set(claim_limits) == OFFICIAL_KPI_EVENT_CLAIM_LIMITS
        and len(claim_limits) == len(OFFICIAL_KPI_EVENT_CLAIM_LIMITS)
    )




def _valid_official_kpi_event_receipt(
    root: Path,
    work_item: dict[str, Any],
    errors: list[str],
) -> bool:
    if work_item.get("resultEvidence") != OFFICIAL_KPI_EVENT_RECEIPT_PATH:
        return False
    document = _load(root, OFFICIAL_KPI_EVENT_RECEIPT_PATH, errors)
    event = document.get("eventIdentity")
    contract = document.get("contract")
    normalized = document.get("normalizedProjection")
    lifecycle = document.get("lifecyclePhaseReconciliation")
    if not all(
        isinstance(value, dict)
        for value in (event, contract, normalized, lifecycle)
    ):
        return False
    grain_assessment = normalized.get("grainAssessment")
    raw_payload = normalized.get("rawPayload")
    route_decision = normalized.get("routeDecision")
    phases = lifecycle.get("phases")
    zero_residual = lifecycle.get("zeroResidualState")
    if not all(
        isinstance(value, dict)
        for value in (
            grain_assessment,
            raw_payload,
            route_decision,
            phases,
            zero_residual,
        )
    ):
        return False
    try:
        canonical = lambda value: json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        receipt_hash = hashlib.sha256(canonical(document)).hexdigest()
        normalized_hash = hashlib.sha256(canonical(normalized)).hexdigest()
        lifecycle_hash = hashlib.sha256(canonical(lifecycle)).hexdigest()
    except (TypeError, ValueError, UnicodeEncodeError):
        return False
    source_contract = _git_json_at_revision(
        root,
        OFFICIAL_KPI_EVENT_RECEIPT_REVISION,
        OFFICIAL_KPI_EVENT_CONTRACT_PATH,
    )
    source_program = _git_json_at_revision(
        root,
        OFFICIAL_KPI_EVENT_RECEIPT_REVISION,
        "product/program.json",
    )
    source_contract_hash = (
        hashlib.sha256(canonical(source_contract)).hexdigest()
        if isinstance(source_contract, dict)
        else None
    )
    source_increments = (
        source_program.get("increments")
        if isinstance(source_program, dict)
        else None
    )
    source_increment = next(
        (
            item
            for item in source_increments
            if isinstance(item, dict)
            and item.get("id")
            == "increment.current-official-route-evaluation-slice"
        ),
        {},
    ) if isinstance(source_increments, list) else {}
    source_work_items = source_increment.get("workItems")
    source_active_work_ids = [
        item.get("id")
        for item in source_work_items
        if isinstance(item, dict) and item.get("state") == "active"
    ] if isinstance(source_work_items, list) else []
    return (
        receipt_hash == OFFICIAL_KPI_EVENT_RECEIPT_SHA256
        and normalized_hash == OFFICIAL_KPI_EVENT_NORMALIZED_PROJECTION_SHA256
        and lifecycle_hash == OFFICIAL_KPI_EVENT_LIFECYCLE_PROJECTION_SHA256
        and document.get("id") == OFFICIAL_KPI_EVENT_RECEIPT_ID
        and document.get("productId") == PRODUCT_ID
        and document.get("release") == "v0.1"
        and document.get("status") == "normalized-event-record"
        and contract.get("path") == OFFICIAL_KPI_EVENT_CONTRACT_PATH
        and contract.get("canonicalSha256")
        == OFFICIAL_KPI_EVENT_CONTRACT_SHA256
        and event.get("observedRevision")
        == OFFICIAL_KPI_EVENT_RECEIPT_REVISION
        and source_contract_hash == OFFICIAL_KPI_EVENT_CONTRACT_SHA256
        and isinstance(source_program, dict)
        and source_program.get("activeIncrementId")
        == "increment.current-official-route-evaluation-slice"
        and source_active_work_ids
        == ["work.run-fresh-official-kpi-capability-event"]
        and raw_payload.get("sha256") is None
        and isinstance(raw_payload.get("limitation"), str)
        and bool(raw_payload["limitation"].strip())
        and route_decision.get("additionProposed") is False
        and route_decision.get("reproducibleResidualGapCount") == 0
        and set(phases.values()) == {"absent"}
        and len(phases) == 6
        and zero_residual.get("status") == "observed"
        and zero_residual.get("value") is True
        and document.get("normalizedProjectionCanonicalSha256")
        == OFFICIAL_KPI_EVENT_NORMALIZED_PROJECTION_SHA256
        and document.get("lifecycleProjectionCanonicalSha256")
        == OFFICIAL_KPI_EVENT_LIFECYCLE_PROJECTION_SHA256
        and _non_empty_string_list(document.get("claimLimits"))
        and not (root / PORTFOLIO_CURATION_INACTIVE_ROOT).exists()
    )

def _valid_official_kpi_scorecard_context(work_item: dict[str, Any]) -> bool:
    context = work_item.get("capabilityContext")
    if not isinstance(context, dict):
        return False
    try:
        context_hash = hashlib.sha256(
            json.dumps(
                context,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
    except (TypeError, ValueError, UnicodeEncodeError):
        return False
    return (
        context_hash == OFFICIAL_KPI_SCORECARD_CONTEXT_SHA256
        and context.get("mode") == "task-time"
        and context.get("taskBinding")
        == f"{PORTFOLIO_CURATION_TASK_BINDING}@{OFFICIAL_KPI_EVENT_RECEIPT_REVISION}"
        and isinstance(context.get("gapOrMaterialBenefit"), str)
        and bool(context["gapOrMaterialBenefit"].strip())
        and isinstance(context.get("dataBoundary"), str)
        and bool(context["dataBoundary"].strip())
        and isinstance(context.get("authorityBoundary"), str)
        and bool(context["authorityBoundary"].strip())
        and isinstance(context.get("verificationSurface"), str)
        and bool(context["verificationSurface"].strip())
    )


def _valid_official_kpi_scorecard_predecessor(
    root: Path,
    work_items: Any,
    errors: list[str],
) -> bool:
    if not isinstance(work_items, list):
        return False
    event_work = next(
        (
            item
            for item in work_items
            if isinstance(item, dict)
            and item.get("id")
            == "work.run-fresh-official-kpi-capability-event"
        ),
        None,
    )
    if not isinstance(event_work, dict):
        return False
    rationale = event_work.get("cancellationRationale")
    return (
        event_work.get("state") == "cancelled"
        and event_work.get("result") == "evidence-incomplete"
        and isinstance(rationale, str)
        and bool(rationale.strip())
        and _valid_official_kpi_event_receipt(root, event_work, errors)
    )


def _contains_explicit_route_cell_record(value: Any) -> bool:
    if isinstance(value, dict):
        if isinstance(value.get("scenarioId"), str) and any(
            isinstance(value.get(key), str)
            for key in ("routeId", "routeClassId")
        ):
            return True
        return any(
            _contains_explicit_route_cell_record(item)
            for item in value.values()
        )
    if isinstance(value, list):
        return any(_contains_explicit_route_cell_record(item) for item in value)
    return False


def _valid_o3_sparse_scorecard_source_derivation(
    source: dict[str, Any],
    partial_entries: list[dict[str, Any]],
    aggregate_decision: dict[str, Any],
) -> bool:
    source_criteria = source.get("criterionReconciliations")
    inventory = source.get("inputInventory")
    route_classes = source.get("routeClasses")
    coverage_summary = source.get("candidateCoverageSummary")
    if not (
        isinstance(source_criteria, list)
        and all(isinstance(item, dict) for item in source_criteria)
        and isinstance(inventory, dict)
        and isinstance(route_classes, list)
        and all(isinstance(item, dict) for item in route_classes)
        and isinstance(coverage_summary, dict)
        and isinstance(aggregate_decision, dict)
    ):
        return False
    source_ids = [item.get("criterionId") for item in source_criteria]
    actual_ids = [item.get("id") for item in partial_entries]
    if (
        len(source_ids) != 15
        or not all(isinstance(item, str) for item in source_ids)
        or len(set(source_ids)) != len(source_ids)
        or actual_ids != source_ids
    ):
        return False
    expected_corrections: list[str] = []
    actual_corrections: list[str] = []
    for source_item, actual_item in zip(source_criteria, partial_entries):
        dispositions = source_item.get("dispositions")
        route_comparison = source_item.get("routeComparison")
        if not (
            isinstance(dispositions, list)
            and all(isinstance(item, str) for item in dispositions)
            and isinstance(route_comparison, dict)
            and isinstance(route_comparison.get("H"), str)
        ):
            return False
        omitted_human_judgment = (
            route_comparison.get("H") == "needs-human-judgment"
            and "needs-human-judgment" not in dispositions
        )
        expected_disposition = (
            "retain-with-human-judgment-correction-and-claim-narrowing"
            if omitted_human_judgment
            else "retain-with-claim-narrowing"
        )
        if omitted_human_judgment:
            expected_corrections.append(source_item["criterionId"])
        if (
            actual_item.get("disposition")
            == "retain-with-human-judgment-correction-and-claim-narrowing"
        ):
            actual_corrections.append(actual_item["id"])
        if not (
            actual_item.get("routeComparison") == route_comparison
            and actual_item.get("humanJudgment") == route_comparison.get("H")
            and actual_item.get("disposition") == expected_disposition
        ):
            return False
    scenario_ids = inventory.get("scenarioIds")
    route_ids = [item.get("id") for item in route_classes]
    if not (
        isinstance(scenario_ids, list)
        and all(isinstance(item, str) for item in scenario_ids)
        and len(scenario_ids) == 13
        and len(set(scenario_ids)) == len(scenario_ids)
        and len(route_ids) == 6
        and all(isinstance(item, str) for item in route_ids)
        and len(set(route_ids)) == len(route_ids)
    ):
        return False
    route_cell_count = coverage_summary.get("routeCellCount")
    mapped_count = coverage_summary.get("mappedRouteCellCount")
    unassessed_count = coverage_summary.get("unassessedRouteCellCount")
    residual_ineligible_count = coverage_summary.get(
        "residualIneligibleCellCount"
    )
    return (
        expected_corrections == actual_corrections
        and len(expected_corrections) == 7
        and coverage_summary.get("scenarioCount") == len(scenario_ids)
        and route_cell_count == len(scenario_ids) * len(route_ids) == 78
        and mapped_count == 50
        and all(
            isinstance(item, int)
            for item in (mapped_count, unassessed_count, residual_ineligible_count)
        )
        and mapped_count + unassessed_count + residual_ineligible_count
        == route_cell_count
        and not _contains_explicit_route_cell_record(source)
        and aggregate_decision.get("sourceField")
        == "candidateCoverageSummary"
        and aggregate_decision.get("reportedMappedRouteCells") == mapped_count
        and aggregate_decision.get("reportedRouteCells") == route_cell_count
        and aggregate_decision.get("disposition")
        == "subtract-unreproducible-cartesian-aggregate"
        and aggregate_decision.get("missingEvidence")
        == ["explicit-sparse-route-cell-records"]
        and aggregate_decision.get("claimCeiling")
        == "No route-cell coverage percentage is retained."
    )


def _valid_o3_lifecycle_contract(
    root: Path,
    work_item: dict[str, Any],
    errors: list[str],
) -> bool:
    if (
        work_item.get("lifecycleContractEvidence") != O3_LIFECYCLE_CONTRACT_PATH
        or work_item.get("lifecycleAttemptEvidence")
        != O3_LIFECYCLE_ATTEMPT_1_INCIDENT_PATH
    ):
        return False
    document = _load(root, O3_LIFECYCLE_CONTRACT_PATH, errors)
    prior_attempt = _load(root, O3_LIFECYCLE_ATTEMPT_1_INCIDENT_PATH, errors)
    task_binding = document.get("taskBinding")
    authorization = document.get("separateAuthorization")
    capability = document.get("capabilityIdentity")
    owner = document.get("lifecycleOwner")
    host_surface = document.get("hostAuthoritySurface")
    phase_semantics = document.get("phaseSemantics")
    event_contract = document.get("eventContract")
    checkpoint = event_contract.get("checkpointProtocol") if isinstance(event_contract, dict) else None
    expected_raw = document.get("expectedRawEvidence")
    if not all(
        isinstance(value, dict)
        for value in (
            task_binding,
            authorization,
            capability,
            owner,
            host_surface,
            phase_semantics,
            event_contract,
            checkpoint,
            expected_raw,
            prior_attempt,
        )
    ):
        return False
    baseline_program = _git_json_at_revision(
        root,
        O3_LIFECYCLE_CONTRACT_BASELINE_REVISION,
        "product/program.json",
    )
    baseline_scorecard = _git_json_at_revision(
        root,
        O3_LIFECYCLE_CONTRACT_BASELINE_REVISION,
        O3_SPARSE_SCORECARD_PATH,
    )
    if not isinstance(baseline_program, dict) or not isinstance(
        baseline_scorecard, dict
    ):
        return False
    increments = baseline_program.get("increments")
    baseline_increment = next(
        (
            item
            for item in increments
            if isinstance(item, dict)
            and item.get("id")
            == "increment.current-official-route-evaluation-slice"
        ),
        {},
    ) if isinstance(increments, list) else {}
    baseline_work_items = baseline_increment.get("workItems")
    baseline_work = next(
        (
            item
            for item in baseline_work_items
            if isinstance(item, dict)
            and item.get("id")
            == "work.build-sparse-scorecard-and-close-lifecycle"
        ),
        {},
    ) if isinstance(baseline_work_items, list) else {}
    try:
        canonical = lambda value: json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        document_hash = hashlib.sha256(canonical(document)).hexdigest()
        prior_attempt_hash = hashlib.sha256(canonical(prior_attempt)).hexdigest()
        baseline_scorecard_hash = hashlib.sha256(
            canonical(baseline_scorecard)
        ).hexdigest()
        prompt = event_contract.get("prompt")
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    except (AttributeError, TypeError, UnicodeEncodeError):
        return False
    claim_limits = document.get("claimLimits")
    return (
        document_hash == O3_LIFECYCLE_CONTRACT_SHA256
        and document.get("id") == O3_LIFECYCLE_CONTRACT_ID
        and document.get("productId") == PRODUCT_ID
        and document.get("release") == "v0.1"
        and document.get("status") == "bound-pre-event"
        and task_binding.get("id") == PORTFOLIO_CURATION_TASK_BINDING
        and task_binding.get("invented") is False
        and task_binding.get("attempt") == 2
        and task_binding.get("scorecardBaselineRevision")
        == O3_LIFECYCLE_CONTRACT_BASELINE_REVISION
        and _non_empty_string(task_binding.get("contractRevisionRule"))
        and task_binding.get("scorecardPath") == O3_SPARSE_SCORECARD_PATH
        and task_binding.get("scorecardCanonicalSha256")
        == O3_SPARSE_SCORECARD_EVENT_BASELINE_SHA256
        and task_binding.get("priorAttemptEvidence")
        == O3_LIFECYCLE_ATTEMPT_1_INCIDENT_PATH
        and task_binding.get("priorAttemptCanonicalSha256")
        == O3_LIFECYCLE_ATTEMPT_1_INCIDENT_SHA256
        and prior_attempt_hash == O3_LIFECYCLE_ATTEMPT_1_INCIDENT_SHA256
        and prior_attempt.get("status") == "failed-evidence-persistence-incomplete"
        and baseline_scorecard_hash == O3_SPARSE_SCORECARD_EVENT_BASELINE_SHA256
        and baseline_program.get("activeIncrementId")
        == "increment.current-official-route-evaluation-slice"
        and baseline_work.get("state") == "active"
        and baseline_work.get("progressEvidence") == O3_SPARSE_SCORECARD_PATH
        and _non_empty_string(authorization.get("source"))
        and _non_empty_string(authorization.get("scope"))
        and _non_empty_string(authorization.get("repositoryAttestationLimit"))
        and capability.get("pluginId") == OFFICIAL_KPI_PLUGIN_ID
        and capability.get("pluginVersion") == OFFICIAL_KPI_PLUGIN_VERSION
        and capability.get("skillChain") == OFFICIAL_KPI_SKILL_IDENTITIES
        and owner.get("id") == "/root/o3_official_lifecycle_transaction_attempt_2"
        and owner.get("dualOwnerAllowed") is False
        and host_surface.get("host") == "Codex"
        and _non_empty_string(host_surface.get("surface"))
        and _non_empty_string(host_surface.get("constraintAndObservation"))
        and _non_empty_string(host_surface.get("unsupportedAttestation"))
        and set(phase_semantics)
        == {
            "preview",
            "boundedActivation",
            "observation",
            "applicableProjection",
            "rollback",
            "cleanup",
        }
        and all(_non_empty_string(value) for value in phase_semantics.values())
        and event_contract.get("forkTurns") == "none"
        and event_contract.get("freshContext") is True
        and event_contract.get("receiverReadOnly") is False
        and event_contract.get("allowedWritePaths")
        == [O3_LIFECYCLE_TEMPORARY_ROOT, O3_LIFECYCLE_RAW_EVIDENCE_PATH]
        and _non_empty_string(event_contract.get("preflightFailurePolicy"))
        and checkpoint.get("status") == "transaction-checkpoint"
        and checkpoint.get("writeAfterPhases")
        == [
            "preview",
            "boundedActivation",
            "observation",
            "applicableProjection",
            "rollback",
            "cleanup",
        ]
        and checkpoint.get("maxFreshAttempts") == 2
        and _non_empty_string(checkpoint.get("durabilityRule"))
        and _non_empty_string(checkpoint.get("recoveryRule"))
        and event_contract.get("promptSha256")
        == O3_LIFECYCLE_CONTRACT_PROMPT_SHA256
        and prompt_hash == O3_LIFECYCLE_CONTRACT_PROMPT_SHA256
        and expected_raw.get("path") == O3_LIFECYCLE_RAW_EVIDENCE_PATH
        and _non_empty_string_list(document.get("verification"))
        and _non_empty_string_list(claim_limits)
        and set(claim_limits) == O3_LIFECYCLE_CONTRACT_CLAIM_LIMITS
        and len(claim_limits) == len(O3_LIFECYCLE_CONTRACT_CLAIM_LIMITS)
    )


def _rfc3339_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})",
        value,
    ) is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _path_entry_absent(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _valid_o3_lifecycle_receipt(
    root: Path,
    document: Any,
    errors: list[str],
) -> bool:
    local_errors: list[str] = []
    raw_path = _inside_root(root, O3_LIFECYCLE_RAW_EVIDENCE_PATH, local_errors)
    if not isinstance(document, dict) or raw_path is None or not raw_path.is_file():
        errors.append("O3 lifecycle receipt structure or locator is invalid")
        return False
    try:
        raw_bytes = raw_path.read_bytes()
        canonical = lambda value: json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        raw_hash = hashlib.sha256(raw_bytes).hexdigest()
    except (OSError, TypeError, UnicodeEncodeError):
        errors.append("O3 lifecycle receipt bytes cannot be read")
        return False
    if local_errors:
        errors.extend(local_errors)
        return False
    raw_identity_valid = raw_hash == O3_LIFECYCLE_RAW_EVIDENCE_SHA256

    contract_receipt = document.get("contract")
    owner = document.get("lifecycleOwner")
    host_surface = document.get("hostAuthoritySurface")
    capabilities = document.get("capabilityIdentity")
    phases = document.get("phases")
    kpi = document.get("kpiObservation")
    repository = document.get("repositoryState")
    intervention = document.get("userIntervention")
    mutations = document.get("mutations")
    time = document.get("time")
    if not all(
        isinstance(value, dict)
        for value in (
            contract_receipt,
            owner,
            host_surface,
            phases,
            kpi,
            repository,
            intervention,
            mutations,
            time,
        )
    ) or not isinstance(capabilities, list):
        errors.append("O3 lifecycle receipt top-level structure is invalid")
        return False

    observed_revision = contract_receipt.get("observedRevision")
    source_contract = _git_json_at_revision(
        root,
        observed_revision,
        O3_LIFECYCLE_CONTRACT_PATH,
    ) if isinstance(observed_revision, str) else None
    current_contract = _load(root, O3_LIFECYCLE_CONTRACT_PATH, local_errors)
    scorecard = _git_json_at_revision(
        root,
        observed_revision,
        O3_SPARSE_SCORECARD_PATH,
    ) if isinstance(observed_revision, str) else None
    if not all(
        isinstance(value, dict)
        for value in (source_contract, current_contract, scorecard)
    ) or local_errors:
        errors.append("O3 lifecycle receipt source bindings are invalid")
        return False
    try:
        source_contract_hash = hashlib.sha256(canonical(source_contract)).hexdigest()
        current_contract_hash = hashlib.sha256(canonical(current_contract)).hexdigest()
        scorecard_hash = hashlib.sha256(canonical(scorecard)).hexdigest()
    except (TypeError, UnicodeEncodeError):
        errors.append("O3 lifecycle receipt source identity cannot be calculated")
        return False
    evidence_revision = O3_LIFECYCLE_EVIDENCE_REVISION
    durable_raw = (
        _git_bytes_at_revision(root, evidence_revision, O3_LIFECYCLE_RAW_EVIDENCE_PATH)
        if isinstance(evidence_revision, str)
        else None
    )
    durable_scorecard = (
        _git_json_at_revision(root, evidence_revision, O3_SPARSE_SCORECARD_PATH)
        if isinstance(evidence_revision, str)
        else None
    )
    try:
        durable_evidence_valid = (
            isinstance(evidence_revision, str)
            and hashlib.sha256(durable_raw).hexdigest()
            == O3_LIFECYCLE_RAW_EVIDENCE_SHA256
            and isinstance(durable_scorecard, dict)
            and hashlib.sha256(canonical(durable_scorecard)).hexdigest()
            == O3_SPARSE_SCORECARD_SHA256
            and _git_revision_is_on_origin_main(root, evidence_revision)
        )
    except (TypeError, UnicodeEncodeError):
        durable_evidence_valid = False
    schema = source_contract.get("expectedRawEvidence")
    source_host = source_contract.get("hostAuthoritySurface")
    source_claims = source_contract.get("claimLimits")
    if not isinstance(schema, dict) or not isinstance(source_host, dict):
        errors.append("O3 lifecycle receipt contract schema is invalid")
        return False

    started_at = _rfc3339_datetime(time.get("startedAt"))
    ended_at = _rfc3339_datetime(time.get("endedAt"))
    phase_order = schema.get("phaseOrder")
    success_states = schema.get("successPhaseStates")
    phase_operations = schema.get("requiredPhaseOperations")
    if not (
        isinstance(phase_order, list)
        and isinstance(success_states, dict)
        and isinstance(phase_operations, dict)
        and started_at is not None
        and ended_at is not None
        and started_at < ended_at
        and list(phases) == phase_order
    ):
        errors.append("O3 lifecycle receipt phase envelope is invalid")
        return False
    phase_times: list[datetime] = []
    for phase_name in phase_order:
        phase = phases.get(phase_name)
        if not isinstance(phase, dict):
            errors.append("O3 lifecycle receipt phase structure is invalid")
            return False
        observed_at = _rfc3339_datetime(phase.get("observedAt"))
        if (
            phase.get("status") != success_states.get(phase_name)
            or phase.get("operation") != phase_operations.get(phase_name)
            or observed_at is None
            or not started_at <= observed_at <= ended_at
            or not all(
                _non_empty_string(phase.get(field))
                for field in ("result", "authority", "claimCeiling")
            )
            or not isinstance(phase.get("evidence"), dict)
            or not phase["evidence"]
        ):
            errors.append("O3 lifecycle receipt phase semantics are invalid")
            return False
        phase_times.append(observed_at)
    if any(left >= right for left, right in zip(phase_times, phase_times[1:])):
        errors.append("O3 lifecycle receipt phase time order is invalid")
        return False

    expected_capabilities = [
        {
            "name": item["name"],
            "relativePath": item["relativePath"],
            "sha256Before": item["sha256"],
            "sha256After": item["sha256"],
        }
        for item in OFFICIAL_KPI_SKILL_IDENTITIES
    ]
    expected_kpi = schema.get("successKpiObservation")
    metric = kpi.get("metric")
    expected_repository = schema.get("successRepositoryState")
    contract_valid = (
        source_contract_hash == O3_LIFECYCLE_CONTRACT_SHA256
        and current_contract_hash == O3_LIFECYCLE_CONTRACT_SHA256
        and scorecard_hash == O3_SPARSE_SCORECARD_EVENT_BASELINE_SHA256
        and document.get("schema") == 1
        and document.get("id")
        == "o3-official-lifecycle-transaction-raw-2026-08-11"
        and document.get("productId") == PRODUCT_ID
        and document.get("release") == "v0.1"
        and document.get("attempt") == 2
        and document.get("status") == schema.get("successReceiptStatus")
        and set(document) == set(schema.get("requiredTopLevelKeys", []))
        and contract_receipt.get("path") == O3_LIFECYCLE_CONTRACT_PATH
        and observed_revision == O3_LIFECYCLE_OBSERVED_REVISION
        and contract_receipt.get("canonicalSha256")
        == O3_LIFECYCLE_CONTRACT_SHA256
        and contract_receipt.get("promptSha256")
        == O3_LIFECYCLE_CONTRACT_PROMPT_SHA256
        and contract_receipt.get("scorecardBaselineRevision")
        == O3_LIFECYCLE_CONTRACT_BASELINE_REVISION
        and contract_receipt.get("attempt") == 2
        and contract_receipt.get("priorAttemptCanonicalSha256")
        == O3_LIFECYCLE_ATTEMPT_1_INCIDENT_SHA256
    )
    owner_and_host_valid = (
        owner
        == {
            "id": "/root/o3_official_lifecycle_transaction_attempt_2",
            "singleOwner": True,
        }
        and host_surface
        == {
            "host": source_host.get("host"),
            "surface": source_host.get("surface"),
            "constraint": source_host.get("constraintAndObservation"),
            "attestationLimit": source_host.get("unsupportedAttestation"),
        }
    )
    capability_valid = capabilities == expected_capabilities
    kpi_valid = (
        isinstance(expected_kpi, dict)
        and kpi.get("scorecardEntryCount") == expected_kpi.get("scorecardEntryCount")
        and kpi.get("nonCartesian") is expected_kpi.get("nonCartesian")
        and kpi.get("noCapabilityAdditionSupported")
        is expected_kpi.get("noCapabilityAdditionSupported")
        and kpi.get("routeDecision") == expected_kpi.get("routeDecision")
        and isinstance(metric, dict)
        and metric.get("id") == expected_kpi.get("metricId")
        and set(metric) == set(schema.get("requiredMetricFields", []))
        and all(_non_empty_string(value) for value in metric.values())
    )
    repository_valid = (
        isinstance(expected_repository, dict)
        and all(
            repository.get(field) == observed_revision
            for field in (
                "observedHeadBefore",
                "observedHeadAfter",
                "originMainBefore",
                "originMainAfter",
            )
        )
        and all(
            repository.get(field) == value
            for field, value in expected_repository.items()
        )
    )
    intervention_valid = intervention == schema.get("successUserInterventionValues")
    mutations_valid = mutations == schema.get("successMutations")
    claims_valid = (
        document.get("claimLimits") == source_claims
        and document.get("claimLimits") == list(O3_LIFECYCLE_CLAIM_LIMIT_SEQUENCE)
    )
    residue_absent = _path_entry_absent(root / O3_LIFECYCLE_TEMPORARY_ROOT)
    checks = (
        (contract_valid, "O3 lifecycle receipt contract or success identity is invalid"),
        (owner_and_host_valid, "O3 lifecycle receipt owner or host boundary is invalid"),
        (capability_valid, "O3 lifecycle receipt capability identity is invalid"),
        (kpi_valid, "O3 lifecycle receipt KPI observation is invalid"),
        (repository_valid, "O3 lifecycle receipt repository delta is invalid"),
        (intervention_valid, "O3 lifecycle receipt user intervention is invalid"),
        (mutations_valid, "O3 lifecycle receipt mutation set is invalid"),
        (claims_valid, "O3 lifecycle receipt claim limits are invalid"),
        (residue_absent, "O3 lifecycle receipt temporary residue remains"),
        (raw_identity_valid, "O3 lifecycle receipt whole-file identity is invalid"),
        (
            durable_evidence_valid,
            "O3 lifecycle evidence is not bound to an origin/main revision",
        ),
    )
    for valid, message in checks:
        if not valid:
            errors.append(message)
    return all(valid for valid, _ in checks)


def _valid_o3_sparse_scorecard_progress(
    root: Path,
    work_item: dict[str, Any],
    errors: list[str],
) -> bool:
    if work_item.get("progressEvidence") != O3_SPARSE_SCORECARD_PATH:
        return False
    document = _load(root, O3_SPARSE_SCORECARD_PATH, errors)
    entries = document.get("entries")
    counts = document.get("entryCounts")
    task_binding = document.get("taskBinding")
    source_bindings = document.get("sourceBindings")
    lifecycle = document.get("lifecycleTransaction")
    route_decision = document.get("routeDecision")
    if not all(
        isinstance(value, dict)
        for value in (
            entries,
            counts,
            task_binding,
            source_bindings,
            lifecycle,
            route_decision,
        )
    ):
        return False
    source = _git_json_at_revision(
        root,
        "c53866726834d79a68c61a5b87b4f7ce90698a2c",
        "registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json",
    )
    baseline_program = _git_json_at_revision(
        root,
        O3_SPARSE_SCORECARD_BASELINE_REVISION,
        "product/program.json",
    )
    if not isinstance(source, dict) or not isinstance(baseline_program, dict):
        return False
    source_criteria = source.get("criterionReconciliations")
    inventory = source.get("inputInventory")
    if not isinstance(source_criteria, list) or not isinstance(inventory, dict):
        return False
    categories = {
        "partialCriteria": entries.get("partialCriteria"),
        "evidenceClusters": entries.get("evidenceClusters"),
        "lifecycleSlices": entries.get("lifecycleSlices"),
        "evaluationDimensions": entries.get("evaluationDimensions"),
        "harnessScenarios": entries.get("harnessScenarios"),
    }
    if not all(
        isinstance(items, list)
        and all(isinstance(item, dict) for item in items)
        for items in categories.values()
    ):
        return False
    required_entry_fields = {
        "disposition",
        "evidence",
        "missingEvidence",
        "claimCeiling",
        "routeComparison",
        "humanJudgment",
        "separateAuthorization",
    }
    all_entries = [item for items in categories.values() for item in items]
    if not all(required_entry_fields.issubset(item) for item in all_entries):
        return False
    try:
        canonical = lambda value: json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        document_hash = hashlib.sha256(canonical(document)).hexdigest()
        source_hash = hashlib.sha256(canonical(source)).hexdigest()
        expected_criterion_hashes = {
            item["criterionId"]: hashlib.sha256(canonical(item)).hexdigest()
            for item in source_criteria
            if isinstance(item, dict)
            and isinstance(item.get("criterionId"), str)
        }
        actual_criterion_hashes = {
            item["id"]: item.get("evidence", {}).get(
                "historicalRecordCanonicalSha256"
            )
            for item in categories["partialCriteria"]
            if isinstance(item.get("id"), str)
            and isinstance(item.get("evidence"), dict)
        }
    except (KeyError, TypeError, ValueError, UnicodeEncodeError):
        return False
    axis_specs = {
        "evidenceClusters": ("clusterIds", "clusterId"),
        "lifecycleSlices": ("lifecycleSliceIds", "lifecycleSliceIds"),
        "evaluationDimensions": ("evaluationDimensionIds", "dimensionIds"),
        "harnessScenarios": ("scenarioIds", "scenarioIds"),
    }
    axis_members_valid = True
    for category, (inventory_key, source_key) in axis_specs.items():
        expected_ids = inventory.get(inventory_key)
        actual_items = categories[category]
        if (
            not isinstance(expected_ids, list)
            or not all(isinstance(item, str) for item in expected_ids)
            or [item.get("id") for item in actual_items] != expected_ids
        ):
            axis_members_valid = False
            continue
        for axis_item in actual_items:
            axis_id = axis_item.get("id")
            expected_members = [
                criterion.get("criterionId")
                for criterion in source_criteria
                if isinstance(criterion, dict)
                and (
                    criterion.get(source_key) == axis_id
                    if source_key == "clusterId"
                    else isinstance(criterion.get(source_key), list)
                    and axis_id in criterion[source_key]
                )
            ]
            if axis_item.get("memberCriterionIds") != expected_members:
                axis_members_valid = False
    baseline_increments = baseline_program.get("increments")
    baseline_increment = next(
        (
            item
            for item in baseline_increments
            if isinstance(item, dict)
            and item.get("id")
            == "increment.current-official-route-evaluation-slice"
        ),
        {},
    ) if isinstance(baseline_increments, list) else {}
    baseline_work = baseline_increment.get("workItems")
    baseline_active_work = [
        item.get("id")
        for item in baseline_work
        if isinstance(item, dict) and item.get("state") == "active"
    ] if isinstance(baseline_work, list) else []
    aggregate_decisions = document.get("aggregateDecisions")
    lifecycle_phases = lifecycle.get("phases")
    lifecycle_receipt = source_bindings.get("lifecycleTransactionReceipt")
    aggregate_decision = (
        aggregate_decisions[0]
        if isinstance(aggregate_decisions, list)
        and len(aggregate_decisions) == 1
        and isinstance(aggregate_decisions[0], dict)
        else {}
    )
    source_derivation_valid = _valid_o3_sparse_scorecard_source_derivation(
        source,
        categories["partialCriteria"],
        aggregate_decision,
    )
    return (
        document_hash == O3_SPARSE_SCORECARD_SHA256
        and source_hash == O3_SPARSE_SOURCE_SHA256
        and document.get("id") == O3_SPARSE_SCORECARD_ID
        and document.get("productId") == PRODUCT_ID
        and document.get("release") == "v0.1"
        and document.get("status")
        == "scorecard-and-lifecycle-complete-with-runtime-attestation-limit"
        and document.get("nonCartesian") is True
        and task_binding.get("id") == PORTFOLIO_CURATION_TASK_BINDING
        and task_binding.get("invented") is False
        and task_binding.get("sourceRevision")
        == O3_SPARSE_SCORECARD_BASELINE_REVISION
        and baseline_program.get("activeIncrementId")
        == "increment.current-official-route-evaluation-slice"
        and baseline_active_work
        == ["work.build-sparse-scorecard-and-close-lifecycle"]
        and expected_criterion_hashes == actual_criterion_hashes
        and len(expected_criterion_hashes) == 15
        and axis_members_valid
        and counts
        == {
            "partialCriteria": 15,
            "evidenceClusters": 6,
            "lifecycleSlices": 14,
            "evaluationDimensions": 12,
            "harnessScenarios": 13,
            "total": 60,
        }
        and len(all_entries) == 60
        and source_derivation_valid
        and isinstance(aggregate_decisions, list)
        and len(aggregate_decisions) == 1
        and aggregate_decisions[0].get("disposition")
        == "subtract-unreproducible-cartesian-aggregate"
        and aggregate_decisions[0].get("reportedMappedRouteCells") == 50
        and aggregate_decisions[0].get("reportedRouteCells") == 78
        and route_decision.get("selected") == "composition"
        and route_decision.get("reproducibleResidualGapCount") == 0
        and route_decision.get("additionProposed") is False
        and lifecycle.get("status")
        == "completed-instrumented-transaction-with-runtime-attestation-limit"
        and lifecycle.get("lifecycleOwner")
        == "/root/o3_official_lifecycle_transaction_attempt_2"
        and lifecycle.get("hostAuthoritySurface")
        == "fresh sub-agent context plus repository and exact temporary-root filesystem operations"
        and lifecycle_phases
        == {
            "preview": "observed",
            "boundedActivation": "observed",
            "observation": "observed",
            "applicableProjection": "not-applicable",
            "rollback": "observed",
            "cleanup": "observed",
        }
        and lifecycle_receipt
        == {
            "path": O3_LIFECYCLE_RAW_EVIDENCE_PATH,
            "byteSha256": O3_LIFECYCLE_RAW_EVIDENCE_SHA256,
            "observedRevision": O3_LIFECYCLE_OBSERVED_REVISION,
        }
        and lifecycle.get("evidence") == lifecycle_receipt
        and _non_empty_string_list(document.get("claimLimits"))
    )
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
                continue
            criterion_id = criterion.get("id")
            if not isinstance(criterion_id, str) or not criterion_id.strip():
                errors.append(f"acceptance criterion {index} must have a non-empty string id")
                continue
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

    collaboration_model = constitution.get("collaborationModel")
    user_contributions = (
        collaboration_model.get("userContributions")
        if isinstance(collaboration_model, dict)
        else None
    )
    agent_obligations = (
        collaboration_model.get("agentObligations")
        if isinstance(collaboration_model, dict)
        else None
    )
    collaboration_model_valid = (
        _non_empty_string_list(user_contributions)
        and REQUIRED_USER_CONTRIBUTION_IDS.issubset(set(user_contributions))
        and len(user_contributions) == len(set(user_contributions))
        and _non_empty_string_list(agent_obligations)
        and REQUIRED_AGENT_OBLIGATION_IDS.issubset(set(agent_obligations))
        and len(agent_obligations) == len(set(agent_obligations))
    )
    if not collaboration_model_valid:
        errors.append(
            "constitution collaborationModel must preserve user roles and agent obligations"
        )

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
    bounded_capability_contexts_valid = True
    for increment in increments:
        increment_id = increment.get("id", "<missing>")
        if not isinstance(increment_id, str) or not increment_id.strip():
            errors.append("every program increment must have a non-empty id")
        increment_state = increment.get("state")
        if not isinstance(increment_state, str) or increment_state not in {
            "planned",
            "active",
            "completed",
            "stopped",
        }:
            errors.append(f"increment {increment_id} has an unsupported state")
        if increment_state == "stopped":
            if increment.get("result") != "falsified":
                errors.append(
                    f"stopped increment {increment_id} must record result falsified"
                )
            if not _valid_falsified_increment_evidence(
                root,
                increment,
                increment.get("stopEvidence"),
                errors,
            ):
                errors.append(
                    f"stopped increment {increment_id} must bind valid falsifier and cleanup evidence"
                )
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
            work_state = work_item.get("state")
            if not isinstance(work_state, str) or work_state not in {
                "planned",
                "active",
                "completed",
                "cancelled",
            }:
                errors.append(f"work item {work_id} has an unsupported state")
                work_state = "<invalid>"
            if work_state == "active" and increment_state != "active":
                errors.append(
                    f"active work {work_id} must belong to the active increment"
                )
            if increment_state == "completed" and work_state != "completed":
                errors.append(
                    f"completed increment {increment_id} cannot retain open work "
                    f"{work_id}"
                )
            if increment_state == "stopped" and work_state not in {
                "completed",
                "cancelled",
            }:
                errors.append(
                    f"stopped increment {increment_id} cannot retain open work {work_id}"
                )
            operation_id_set = set(operation_ids)
            capability_context_valid = _valid_capability_context(
                work_item, operation_id_set
            )
            if (
                work_id == "work.run-fresh-official-kpi-capability-event"
                and not _valid_official_kpi_event_contract(
                    root,
                    work_item,
                    errors,
                )
            ):
                errors.append(
                    "work item work.run-fresh-official-kpi-capability-event "
                    "must bind the exact official KPI event contract"
                )
            if work_id == "work.run-fresh-official-kpi-capability-event":
                receipt_valid = (
                    _valid_official_kpi_event_receipt(root, work_item, errors)
                    if work_state in {"completed", "cancelled"}
                    else False
                )
                if work_state in {"completed", "cancelled"} and not receipt_valid:
                    errors.append(
                        "closed work item "
                        "work.run-fresh-official-kpi-capability-event must bind "
                        "a valid normalized event receipt"
                    )
                if work_state == "completed" and receipt_valid:
                    errors.append(
                        "work item work.run-fresh-official-kpi-capability-event "
                        "cannot be completed while the contract-required raw "
                        "payload hash is absent"
                    )
                cancellation_rationale = work_item.get("cancellationRationale")
                if work_state == "cancelled" and (
                    work_item.get("result") != "evidence-incomplete"
                    or not isinstance(cancellation_rationale, str)
                    or not cancellation_rationale.strip()
                ):
                    errors.append(
                        "cancelled work item "
                        "work.run-fresh-official-kpi-capability-event must record "
                        "the evidence-incomplete result and rationale"
                    )
            if (
                work_id == "work.build-sparse-scorecard-and-close-lifecycle"
                and work_state in {"active", "completed"}
                and not _valid_official_kpi_scorecard_context(work_item)
            ):
                errors.append(
                    "work item work.build-sparse-scorecard-and-close-lifecycle "
                    "must bind the exact scorecard capabilityContext"
                )
            if (
                work_id == "work.build-sparse-scorecard-and-close-lifecycle"
                and work_state in {"active", "completed"}
                and not _valid_official_kpi_scorecard_predecessor(
                    root,
                    raw_work_items,
                    errors,
                )
            ):
                errors.append(
                    "work item work.build-sparse-scorecard-and-close-lifecycle "
                    "requires a cancelled evidence-incomplete predecessor with "
                    "a valid normalized event receipt"
                )
            if (
                work_id == "work.build-sparse-scorecard-and-close-lifecycle"
                and work_state in {"active", "completed"}
            ):
                scorecard_progress_valid = _valid_o3_sparse_scorecard_progress(
                    root,
                    work_item,
                    errors,
                )
                if not scorecard_progress_valid:
                    errors.append(
                        f"{work_state} work item "
                        "work.build-sparse-scorecard-and-close-lifecycle must bind "
                        "valid source-reconciled scorecard progress evidence"
                    )
                if not _valid_o3_lifecycle_contract(
                    root,
                    work_item,
                    errors,
                ):
                    errors.append(
                        f"{work_state} work item "
                        "work.build-sparse-scorecard-and-close-lifecycle must bind "
                        "the exact bound lifecycle transaction contract"
                    )
            gated_operations = operation_id_set - ALLOWED_AGENT_OPERATION_IDS
            if not capability_context_valid:
                gated_operations.update(
                    operation_id_set & CAPABILITY_CONTEXT_OPERATION_IDS
                )
            if work_state == "planned" and gated_operations:
                authority_gate = work_item.get("authorityGate")
                if not isinstance(authority_gate, str) or not authority_gate.strip():
                    errors.append(
                        f"planned work {work_id} requests unauthorized operations "
                        "without an authorityGate"
                    )
                else:
                    covered_operations = AUTHORITY_GATE_OPERATION_IDS.get(
                        authority_gate, set()
                    )
                    uncovered_operations = sorted(
                        gated_operations - covered_operations
                    )
                    if uncovered_operations:
                        errors.append(
                            f"planned work {work_id} authorityGate {authority_gate} "
                            "does not cover operations: "
                            + ", ".join(uncovered_operations)
                        )
            elif work_state == "planned" and "authorityGate" in work_item:
                authority_gate = work_item.get("authorityGate")
                if (
                    not isinstance(authority_gate, str)
                    or authority_gate not in AUTHORITY_GATE_OPERATION_IDS
                ):
                    errors.append(
                        f"planned work {work_id} has unknown authorityGate "
                        f"{authority_gate}"
                    )
            if work_state in {"active", "completed"}:
                if not operation_ids:
                    bounded_work_operations_valid = False
                bounded_work_operations.update(operation_ids)
                if not capability_context_valid:
                    bounded_capability_contexts_valid = False
                    errors.append(
                        f"active or completed work {work_id} has capability operations "
                        "without an eligible capabilityContext"
                    )
            if work_state == "active":
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
        and bounded_capability_contexts_valid
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

    completed_outcomes_valid = True
    for increment in increments:
        if increment.get("state") != "completed":
            continue
        increment_id = increment.get("id", "<missing>")
        acceptance_ids = increment.get("acceptanceIds")
        if not isinstance(acceptance_ids, list):
            continue
        for criterion_id in acceptance_ids:
            if criterion_id in OUTCOME_IDS and not evidence_states.get(criterion_id):
                completed_outcomes_valid = False
                errors.append(
                    f"completed increment {increment_id} requires verified outcome "
                    f"{criterion_id}"
                )
    if not completed_outcomes_valid:
        evidence_states["O1"] = False

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
