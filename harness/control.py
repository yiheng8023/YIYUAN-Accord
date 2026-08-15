"""Historical-event-neutral product-contract verification for the Harness.

The verifier owns current authority shape, causal-program invariants, evidence
admission, human authority, and bounded process loss. Historical release event
validators live at their accepted Git revisions; they are not carried forward
as current product authority.
"""

from __future__ import annotations

from contextvars import ContextVar
import ctypes
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import tempfile
from threading import Timer
from types import MappingProxyType
from typing import Any, Callable, Mapping


PRODUCT_ID = "agent-autonomy-harness"
CONSTITUTION_ID = "harness-product-constitution-v1"
CURRENT_RELEASE = "v1.0"
COMPLETION_EXPRESSION = "O1 && O2 && O3 && O4 && O5"
EXPECTED_PRODUCT_PURPOSE = (
    "Provide an open, Agent-neutral, demand-driven human-Agent collaboration quality "
    "harness that transfers capability observation, discovery, selection, bounded setup "
    "and task-scoped dispatch, task-topology selection and reconciliation, "
    "context-carrier fitness and transition, recovery, verification, release, and cleanup burden from "
    "the user to the Agent while preserving human authority over goals, domain judgment, "
    "trust, cost, and irreversible effects."
)
EXPECTED_SUCCESS_DEFINITION = (
    "Across repeated real tasks entered at the goal level, a user can provide ideas, "
    "domain facts, bounded authorization, corrections, and accountable final judgment "
    "without needing to know, select, invoke, or manage the underlying Agent, capability "
    "ecosystem, code and conversation topology, or context lifecycle; the Agent observes available capability "
    "and conversation-carrier fitness, discovers beyond its current view only for an evidenced gap, dispatches the smallest "
    "sufficient route and task carrier, transitions before preventable context loss, and returns accepted outcomes with fewer material orchestration interventions "
    "than an ad-hoc path."
)
EXPECTED_PROGRAM_PURPOSE = (
    "Prove the constitution's terminal product proposition through a finite repeated-natural-task "
    "cohort: sustained goal-level delivery, lower user orchestration burden than source-bound "
    "ad-hoc baselines, real demand-driven capability and carrier lifecycles, and live cross-host "
    "open reference delivery. v0.2 remains an immutable bounded calibration milestone and cannot "
    "satisfy this program by inheritance."
)
EXPECTED_PROGRESS_RULE = (
    "Only accepted real-task outcomes O1-O5 in a currently valid authority graph with "
    "G1-G4 passing count as progress. Before any task measurement, one content-addressed "
    "normative profile and prospective cohort protocol must be frozen; the realized cohort "
    "is the earliest eligible registration prefix under that protocol, never a retrospectively "
    "selected task roster. Git ancestry proves repository ordering only; every outcome requires "
    "a task-bound validator to prove natural demand and a source-bound measurement event after "
    "its immutable registration because Git dates and self-reported timestamps are not chronology "
    "authority. Even after O1-O5 task evidence passes, completionState remains in-progress until "
    "the code-owned terminal release gate verifies a clean exact candidate, its predeclared O5 "
    "evidence set, named-human authorization in the local annotated tag, the identical public tag "
    "object and peeled commit, and no ignored or untracked repository residue; this is O5 release "
    "enforcement, not an additional outcome. Documents, tests, inventories, fixtures, memberships, "
    "research volume, and prior-release evidence are supporting inputs only."
)
OUTCOME_IDS = {"O1", "O2", "O3", "O4", "O5"}
GUARDRAIL_IDS = {"G1", "G2", "G3", "G4"}
EXPECTED_CRITERION_IDS = OUTCOME_IDS | GUARDRAIL_IDS
CRITERION_BASE_FIELDS = {
    "id",
    "class",
    "name",
    "statement",
    "metric",
    "threshold",
    "assessment",
}
AUTHORITY_TOP_LEVEL_FIELDS = MappingProxyType(
    {
        "constitution": frozenset(
            {
                "schema",
                "id",
                "productId",
                "purpose",
                "successDefinition",
                "productForm",
                "collaborationModel",
                "capabilityInfluenceBoundary",
                "fixedInvariants",
                "adaptiveSurfaces",
                "planningModel",
                "requiredAuthorityFiles",
                "activeAuthorityGlobs",
                "supportingDocuments",
                "historicalMilestones",
                "bootstrapGuards",
                "historicalEvidenceBoundary",
            }
        ),
        "program": frozenset(
            {
                "schema",
                "id",
                "productId",
                "release",
                "purpose",
                "constitution",
                "acceptance",
                "status",
                "activeIncrementId",
                "progressionPolicy",
                "priorRelease",
                "normativeProfileBinding",
                "terminalReleaseBinding",
                "authorityBoundary",
                "completionExpression",
                "increments",
            }
        ),
        "acceptance": frozenset(
            {
                "schema",
                "id",
                "productId",
                "release",
                "program",
                "completionExpression",
                "progressRule",
                "criteria",
            }
        ),
    }
)
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
        "O1": (6, "finite-stratified-natural-task-cohort"),
        "O2": (6, "same-cohort-source-bound-ad-hoc-baselines"),
        "O3": (4, "real-task-route-lifecycle-cohort"),
        "O4": (4, "predeclared-carrier-fitness-and-transition-cohort"),
        "O5": (2, "same-task-live-matched-cross-host-pairs"),
    }
)
CRITERION_CONTRACT_BASE_FIELDS = CRITERION_BASE_FIELDS - {"assessment"}
EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256 = (
    "e4494ccbd16f29f0013ab05f7521661e3953616b4e6a2de5665595b013554619"
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
EXPECTED_REQUIRED_SUPPORTING_DOCUMENTS = frozenset(
    {
        "README.md",
        "README.zh-CN.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "SUPPORT.md",
        "SUPPORT.zh-CN.md",
        "docs/DEMAND-TO-CAPABILITY-PROFILE.md",
        "docs/architecture.md",
        "docs/strategy/PRODUCT-NORTH-STAR.md",
        "docs/strategy/RESEARCH-AND-POC-PLAN.md",
        "docs/operations/CONTINUATION.md",
        "docs/operations/HISTORY.md",
    }
)
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
    "capability-installation-authorization",
    "account-connection-authorization",
    "persistent-activation-authorization",
    "publication-authorization",
    "release-authorization",
    "accountable-outcome-acceptance",
    "destructive-or-irreversible-action",
}
AUTHORITY_BOUNDARY_FIELDS = {
    "userOwns",
    "agentOwnsWithinBoundedAuthority",
}
HUMAN_ONLY_OPERATIONS = {
    "destructive-action",
    "irreversible-action",
    "new-account-or-data-boundary",
    "new-cost",
    "new-trust",
    "capability-installation-authorization",
    "account-connection-authorization",
    "persistent-activation-authorization",
    "publication-authorization",
    "release-authorization",
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
    "bounded-consumer-configuration-after-explicit-grant": "bounded-local-write",
    "coverage-analysis": "local-read",
    "targeted-capability-discovery": "bounded-public-read",
    "capability-static-review": "local-read",
    "inactive-exact-acquisition": "bounded-local-write",
    "same-goal-carrier-transition": "bounded-host-state-change",
    "authorized-capability-installation": "bounded-local-write",
    "authorized-account-connection": "bounded-external-write",
    "authorized-persistent-activation": "bounded-host-state-change",
    "authorized-publication-execution": "bounded-external-write",
    "authorized-release-execution": "bounded-external-write",
}
NORMATIVE_PROFILE_BINDING_FIELDS = {
    "state",
    "profileIdentity",
    "locator",
    "sha256",
    "cohortProtocolIdentity",
    "cohortProtocolLocator",
    "cohortProtocolSha256",
    "frozenAtRevision",
}
UNFROZEN_NORMATIVE_PROFILE_BINDING = {
    "state": "unfrozen",
    "profileIdentity": None,
    "locator": None,
    "sha256": None,
    "cohortProtocolIdentity": None,
    "cohortProtocolLocator": None,
    "cohortProtocolSha256": None,
    "frozenAtRevision": None,
}
COHORT_PROTOCOL_FIELDS = {
    "schema",
    "id",
    "profileIdentity",
    "cohortProtocolIdentity",
    "eligibilityRule",
    "exclusionRule",
    "taskIdentityRule",
    "strata",
    "enrollmentOrder",
    "stopRule",
    "failedOrMissingSampleDisposition",
    "measurementEventRule",
    "claimLimits",
}
EXPECTED_COHORT_PROTOCOL_RULES = MappingProxyType(
    {
        "eligibilityRule": "all-predeclared-eligible-natural-tasks",
        "exclusionRule": "predeclared-only-no-postmeasurement-exclusion",
        "taskIdentityRule": "stable-source-bound-identity-before-measurement",
        "enrollmentOrder": "strict-git-ancestry-first-eligible",
        "stopRule": "earliest-prefix-satisfying-current-acceptance",
        "failedOrMissingSampleDisposition": "retain-fail-closed-no-replacement",
        "measurementEventRule": "task-bound-source-event-after-registration-required",
    }
)
TERMINAL_RELEASE_BINDING_FIELDS = {
    "state",
    "tag",
    "publicRemote",
    "annotationFormat",
    "o5EvidenceSetSha256",
}
UNREGISTERED_TERMINAL_RELEASE_BINDING = {
    "state": "unregistered",
    "tag": None,
    "publicRemote": None,
    "annotationFormat": None,
    "o5EvidenceSetSha256": None,
}
TERMINAL_RELEASE_ANNOTATION_FIELDS = {
    "schema",
    "format",
    "productId",
    "release",
    "candidateRevision",
    "tag",
    "publicRemote",
    "o5EvidenceSetSha256",
    "authority",
    "acceptedScope",
}
TERMINAL_RELEASE_AUTHORITY_FIELDS = {
    "kind",
    "name",
    "decision",
    "decidedAt",
    "source",
    "validator",
}
TERMINAL_RELEASE_AUTHORITY_SOURCE_FIELDS = {
    "kind",
    "locator",
    "identity",
    "payloadSha256",
}
TERMINAL_RELEASE_AUTHORITY_VALIDATOR_FIELDS = {"kind", "version"}
EXPECTED_TERMINAL_RELEASE_SCOPE = [
    "normative-profile",
    "thin-reference-adapters",
    "privacy-disposition",
    "claim-ceiling",
    "candidate-commit",
    "annotated-tag",
    "public-release",
]
EXPECTED_PUBLIC_REMOTE = "https://github.com/yiheng8023/agent-autonomy-harness.git"
TERMINAL_RELEASE_ANNOTATION_FORMAT = "harness-release-authorization-v1"
PROCESS_LOSS_FIELDS = {
    "maxSameClassUserCorrectionBeforeStop",
    "maxConsecutiveOutcomeNeutralWorkItems",
    "maxMaterialUserCapabilityOrchestrationInterventions",
    "stopOnAuthorityOrIrreversibleIncident",
    "stopOnUnboundedResidue",
}
INCREMENT_FIELDS = {
    "id",
    "state",
    "correctionClass",
    "observedProblem",
    "hypothesis",
    "falsifier",
    "stopCondition",
    "acceptanceIds",
    "taskRegistration",
    "processLossBudget",
    "cleanupBoundary",
    "workItems",
}
TASK_REGISTRATION_BINDING_FIELDS = {
    "locator",
    "sha256",
    "sourceRevision",
    "measurementNotBefore",
    "profileSha256",
    "cohortProtocolSha256",
}
TASK_REGISTRATION_FIELDS = {
    "schema",
    "id",
    "registeredAt",
    "taskIdentity",
    "incrementId",
    "criterionIds",
    "preRegistrationValues",
    "acceptanceAuthority",
    "namedHumanAcceptor",
    "qualitySafetyEvidenceAndResidueFloors",
    "materialInterventionTaxonomy",
    "materialCollaborationLossTaxonomy",
    "sourceCaptureEligibilityAndStopRule",
    "claimLimits",
}
SOURCE_CAPTURE_FIELDS = {
    "measurementStartsAfter",
    "eligibleSources",
    "ineligibleSources",
    "stopRule",
}
ACCEPTANCE_AUTHORITY_FIELDS = {"locator", "criteriaContractSha256"}
TASK_REGISTRATION_VALUE_ALIASES = {
    "registeredAt",
    "taskIdentity",
    "namedHumanAcceptor",
    "qualitySafetyEvidenceAndResidueFloors",
    "materialInterventionTaxonomy",
    "materialCollaborationLossTaxonomy",
}
WORK_ITEM_FIELDS = {
    "id",
    "state",
    "acceptanceIds",
    "operationIds",
    "deliverables",
}
CLEANUP_BOUNDARY_FIELDS = {"repositoryTemporaryPaths"}
PROGRAM_STATES = {"active", "ready", "completed"}
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
EXPECTED_PLANNING_MODEL = {
    "method": "fixed-release-acceptance-with-adaptive-causal-increments",
    "maxActiveIncrements": 1,
    "maxActiveWorkItems": 1,
    "workStateSemantics": EXPECTED_WORK_STATE_SEMANTICS,
    "incrementRequires": [
        "observed problem",
        "causal hypothesis",
        "falsifier",
        "correction class",
        "mapped acceptance criteria",
        "content-addressed task registration for outcome-bearing work",
        "finite stop condition",
        "process-loss budget",
        "cleanup boundary",
    ],
    "replanWhen": [
        "the hypothesis is falsified",
        "new evidence changes the critical path",
        "the user must reassert already-bound direction",
        "the same process-loss class recurs",
        "a phase produces no direct outcome movement",
        "authority, trust, cost, or data boundaries change",
        "the increment reaches its stop condition",
    ],
}
EXPECTED_COLLABORATION_MODEL = {
    "userContributions": [
        "ideas-and-goals",
        "domain-facts-and-judgment",
        "bounded-authorization",
        "corrections",
        "accountable-final-judgment",
    ],
    "agentObligations": [
        "intent-and-omission-detection",
        "available-capability-observation-and-gap-detection",
        "source-bounded-targeted-capability-discovery",
        "capability-selection-and-task-scoped-dispatch",
        "task-topology-selection-reconciliation-merge-release-and-cleanup",
        "context-carrier-fitness-observation-and-proactive-transition",
        "bounded-setup-and-execution",
        "failure-recovery",
        "verification-and-claim-control",
        "task-exposure-release-cleanup-and-continuity",
        "process-loss-detection-and-replanning",
    ],
}
EXPECTED_PRODUCT_FORM = {
    "identity": "open-agent-neutral-demand-driven-human-agent-collaboration-quality-harness",
    "durableOutputs": [
        "methodology",
        "open-quality-conformance-profile",
        "executable-reference-adapter",
    ],
    "portableCore": "testable-demand-authority-capability-task-topology-and-context-carrier-lifecycle-evidence-acceptance-and-burden-semantics",
    "referenceDelivery": "codex-first-reference-slice-then-distinct-host-portability-proof",
}
EXPECTED_FIXED_INVARIANTS = frozenset(
    {
        "product outcomes outrank artifact counts, test counts, inventory counts, and research volume",
        "one release has one explicit finite acceptance expression",
        "guardrails constrain delivery but never count as product progress",
        "every active work item maps to at least one release criterion",
        "only one causal increment and at most one work item may be active",
        "goal-level demand is the default entry; the user need not name a capability, product, discovery channel, or invocation syntax",
        "the portable core is not a capability catalog, capability manager, collaboration wire protocol, audit log, universal runtime, or host projection",
        "capability discovery sources and query strategies are adaptive inputs and no fixed channel can become product authority",
        "user-installed ecosystem breadth is legitimate user freedom and is not a failure explanation",
        "task-time capability and metadata exposure is minimal even when the available portfolio is broad",
        "capability lifecycle is demand-driven: evaluate healthy native and already-authorized routes first, add only for an evidenced residual gap, and end task-scoped exposure when the need ends unless continued activation proves net value",
        "task topology is demand-driven: preserve the current healthy carrier by default; create a branch, worktree, repository fork, conversation fork, or new task only for source-bound causal necessity; the Agent owns identity, synchronization, merge or reconciliation, archive or release, and cleanup while the user retains goal, authority, trust, cost, and irreversible decisions",
        "conversation-carrier fitness is Agent-owned: use source-bound observable host and task signals to keep the current carrier only while it remains safe, choose native compaction or a verified handoff before preventable quality or capacity loss, and when reliable signals are unavailable record that limit and apply a conservative pre-declared transition rule rather than making the user guess",
        "reuse or adapt sufficient external collaboration protocols, human-allocation research, runtimes, discovery, identity, governance, provenance, and evaluation capability before composition or authoring; bind each decision-relevant external substrate to an exact source identity, version or commit, license or applicable terms, maturity, and reuse boundary; new implementation requires an evidenced residual semantic gap",
        "reference-host calibration cannot establish Agent-neutral portability; a distinct-host O5 proof is required",
        "claims and authority transitions are zero-trust while safe reversible work uses bounded default autonomy",
        "memory, consumer projections, historical evidence, and installed payloads cannot become current product authority by existing",
        "unsupported host behavior is reported rather than simulated",
    }
)
EXPECTED_ADAPTIVE_SURFACES = frozenset(
    {
        "module and Skill shape",
        "capability discovery source and query strategy",
        "host and manager adapter sequence",
        "task carrier topology and host primitive",
        "native, official, reviewed external, composed, or authored capability choice",
        "experiment design",
        "delivery order inside the active causal increment",
    }
)
EXPECTED_BOOTSTRAP_GUARDS = frozenset(
    {
        "code-owned authority identity and path validation",
        "active authority cannot include evidence archives, temporary roots, legacy roots, or symlinks",
        "verified outcomes require a code-owned evidence validator",
        "conventional repository residue is detected outside declared cleanup paths",
    }
)
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
CONVENTIONAL_RESIDUE_NAMES = {
    ".tmp",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".coverage",
    ".tox",
    ".nox",
    ".hypothesis",
    ".ipynb_checkpoints",
    ".ds_store",
    "thumbs.db",
}
CONVENTIONAL_RESIDUE_SUFFIXES = (
    ".pyc",
    ".pyo",
    ".log",
    ".bak",
    ".orig",
    ".rej",
)
MAX_DOCUMENT_BYTES = 1_048_576
MAX_JSON_BYTES = MAX_DOCUMENT_BYTES
MAX_VERIFICATION_FILES = 256
MAX_VERIFICATION_TOTAL_BYTES = 16 * 1_048_576
MAX_EVIDENCE_LOCATOR_REFERENCES = 256
MAX_GIT_OUTPUT_BYTES = MAX_DOCUMENT_BYTES
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 100_000
MAX_JSON_CONTAINER_ITEMS = 10_000
MAX_JSON_STRING_CHARACTERS = 262_144
MAX_VERIFICATION_DIAGNOSTICS = 128
MAX_AUTHORITY_WALK_ENTRIES = 4_096
MAX_REPOSITORY_WALK_ENTRIES = 100_000
MAX_REPOSITORY_WALK_DEPTH = 32
DIAGNOSTIC_LIMIT_MESSAGE = "verification diagnostic limit exceeded"
FROZEN_V02_PROFILE_ARTIFACT_SHA256 = MappingProxyType(
    {
        "docs/DEMAND-TO-CAPABILITY-PROFILE.md": (
            "1630f188f5f924fcba7f19b8431b48eac2e4a3ca6d37a5bc99cc1df085d4995a"
        ),
        "adapters/agent-autonomy-harness-codex/skills/"
        "deliver-demand-driven-task/SKILL.md": (
            "abb5906eeface94100b278e4ac182c39893a6be86a5de52577318164dc77103f"
        ),
        "adapters/agent-autonomy-harness-claude/skills/"
        "deliver-demand-driven-task/SKILL.md": (
            "abb5906eeface94100b278e4ac182c39893a6be86a5de52577318164dc77103f"
        ),
    }
)
EXPECTED_PROGRESSION_POLICY = {
    "readyState": "nonterminal-empty-graph-open-to-next-causally-justified-increment",
    "noNaturalTaskDisposition": "outcome-gate-not-program-completion-or-blocker",
    "boundProductDeliveryDemandDisposition": (
        "authorized-product-plan-delivery-is-real-demand-when-its-primary-purpose-is-the-"
        "deliverable-rather-than-exercising-or-diagnosing-the-harness"
    ),
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
    "capabilityCatalogsAndDiscoveryChannels": "adaptive-source-input-only",
    "cannot": [
        "set-product-direction",
        "create-causal-work-without-observed-problem",
        "expand-authority-trust-data-cost-or-side-effects",
        "promote-evidence-acceptance-or-release-state",
        "require-user-capability-product-channel-or-invocation-selection",
        "make-a-fixed-catalog-or-discovery-channel-product-authority",
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
EXPECTED_PRIOR_RELEASE = {
    "release": "v0.2",
    "state": "accepted-bounded-calibration-milestone",
    "revision": "0dbcb0af34197e5c35c75d69a1aeacf4fd91b404",
    "currentAuthority": False,
}
EXPECTED_HISTORICAL_MILESTONES = (
    {
        "release": "v0.1",
        "state": "accepted-repository-control-milestone",
        "revision": "be498f960c9e0587d355291fb24261c91e75cd77",
        "currentAuthority": False,
        "claimLimit": (
            "repository-bound control evidence only; not terminal proposition, "
            "broad user value, software-engineering standard, cross-host, "
            "production, or publication proof"
        ),
    },
    {
        **EXPECTED_PRIOR_RELEASE,
        "claimLimit": (
            "bounded O1-O5 calibration evidence for the fixed natural-task, Codex "
            "reference-host and matched source-gate cohorts only; not the constitution "
            "terminal proposition, sustained live capability and carrier orchestration, "
            "installed product value, universal portability, production, publication, "
            "or release proof"
        ),
    },
)


EvidenceValidator = Callable[[dict[str, Any], str, Path, list[str]], bool]
EvidenceValidatorSpec = tuple[
    frozenset[str],
    frozenset[str],
    EvidenceValidator,
]
HumanAuthorizationValidator = Callable[
    [dict[str, Any], Path, list[str]],
    bool,
]



SUPPORTED_EVIDENCE_VALIDATORS: Mapping[str, EvidenceValidatorSpec] = MappingProxyType({})
SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS: Mapping[
    str, HumanAuthorizationValidator
] = MappingProxyType({})

_EVIDENCE_GIT_CACHE: ContextVar[
    dict[tuple[str, tuple[str, ...]], bytes | None] | None
] = ContextVar("harness_evidence_git_cache", default=None)

_VERIFICATION_READ_BUDGET: ContextVar[dict[str, Any] | None] = ContextVar(
    "harness_verification_read_budget", default=None
)


def _evidence_git(root: Path, *arguments: str) -> bytes | None:
    cache = _EVIDENCE_GIT_CACHE.get()
    key = (str(root.resolve(strict=False)), arguments)
    if cache is not None and key in cache:
        return cache[key]
    executable = shutil.which("git")
    if executable is None:
        result = None
        if cache is not None:
            cache[key] = result
        return result
    try:
        executable_path = Path(executable).resolve(strict=True)
        executable_path.relative_to(root.resolve(strict=True))
    except ValueError:
        pass
    except (OSError, RuntimeError):
        result = None
        if cache is not None:
            cache[key] = result
        return result
    else:
        result = None
        if cache is not None:
            cache[key] = result
        return result
    try:
        metadata = executable_path.lstat()
    except OSError:
        result = None
        if cache is not None:
            cache[key] = result
        return result
    if (
        executable_path.name.casefold() not in {"git", "git.exe"}
        or not stat.S_ISREG(metadata.st_mode)
        or _link_or_reparse(executable_path)
    ):
        result = None
        if cache is not None:
            cache[key] = result
        return result
    if os.name == "nt":
        folded_parts = tuple(part.casefold() for part in executable_path.parts)
        system_directory = ctypes.create_unicode_buffer(32_768)
        system_length = ctypes.windll.kernel32.GetSystemDirectoryW(
            system_directory, len(system_directory)
        )
        system_drive = (
            Path(system_directory.value).drive.casefold()
            if 0 < system_length < len(system_directory)
            else ""
        )
        trusted_install = (
            bool(executable_path.drive)
            and not executable_path.drive.startswith("\\\\")
            and executable_path.drive.casefold() == system_drive
            and len(folded_parts) >= 4
            and folded_parts[1:3]
            in {
                ("program files", "git"),
                ("program files (x86)", "git"),
            }
        )
    else:
        trusted_roots = (
            Path("/usr/bin"),
            Path("/usr/local/bin"),
            Path("/usr/local/Cellar"),
            Path("/opt/homebrew"),
            Path("/opt/local/bin"),
        )
        trusted_install = any(
            executable_path == trusted_root
            or trusted_root in executable_path.parents
            for trusted_root in trusted_roots
        )
    if not trusted_install:
        result = None
        if cache is not None:
            cache[key] = result
        return result

    environment = {
        key: value
        for key, value in os.environ.items()
        if key.casefold()
        in {"systemroot", "windir", "path", "pathext", "temp", "tmp"}
    }
    environment.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_EXTERNAL_DIFF": "",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
    )
    process: subprocess.Popen[bytes] | None = None
    isolated_remote_workspace: tempfile.TemporaryDirectory[str] | None = None
    process_cwd = root
    if arguments and arguments[0] == "ls-remote":
        try:
            isolated_remote_workspace = tempfile.TemporaryDirectory(
                prefix="harness-ls-remote-"
            )
            process_cwd = Path(isolated_remote_workspace.name).resolve()
            environment["GIT_CEILING_DIRECTORIES"] = str(process_cwd)
        except OSError:
            if cache is not None:
                cache[key] = None
            return None

    def stop_process() -> None:
        if process is None:
            return
        try:
            if process.poll() is None:
                process.kill()
        except OSError:
            pass

    try:
        process = subprocess.Popen(
            [
                str(executable_path),
                "--no-optional-locks",
                "-c",
                "core.fsmonitor=false",
                "-c",
                f"core.hooksPath={os.devnull}",
                "-c",
                "core.pager=cat",
                "-c",
                "color.ui=false",
                "-c",
                "diff.external=",
                "-c",
                "credential.helper=",
                "-c",
                "protocol.file.allow=never",
                "-c",
                "http.sslVerify=true",
                *arguments,
            ],
            cwd=process_cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        timer = Timer(10, stop_process)
        timer.daemon = True
        timer.start()
        try:
            if process.stdout is None:
                result = None
            else:
                raw = process.stdout.read(MAX_GIT_OUTPUT_BYTES + 1)
                if len(raw) > MAX_GIT_OUTPUT_BYTES:
                    stop_process()
                    result = None
                else:
                    result = raw if process.wait() == 0 else None
        finally:
            timer.cancel()
            stop_process()
            process.wait()
            if process.stdout is not None:
                process.stdout.close()
    except (OSError, subprocess.SubprocessError):
        result = None
    finally:
        if isolated_remote_workspace is not None:
            try:
                isolated_remote_workspace.cleanup()
            except OSError:
                result = None
    if result is not None:
        budget = _VERIFICATION_READ_BUDGET.get()
        if budget is not None:
            total = budget["bytes"] + len(result)
            if total > MAX_VERIFICATION_TOTAL_BYTES:
                result = None
            else:
                budget["bytes"] = total
    if cache is not None:
        cache[key] = result
    return result


def _committed_blob(
    root: Path, revision: str, locator: str, expected_sha256: str
) -> bool:
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision) is None:
        return False
    if _evidence_git(root, "merge-base", "--is-ancestor", revision, "HEAD") is None:
        return False
    raw_size = _evidence_git(root, "cat-file", "-s", f"{revision}:{locator}")
    try:
        object_size = int(raw_size.decode("ascii").strip()) if raw_size is not None else -1
    except (UnicodeError, ValueError):
        return False
    if object_size < 0 or object_size > MAX_DOCUMENT_BYTES:
        return False
    committed = _evidence_git(root, "show", f"{revision}:{locator}")
    return committed is not None and hashlib.sha256(committed).hexdigest() == expected_sha256


def _strict_git_ancestor(root: Path, ancestor: Any, descendant: Any) -> bool:
    if (
        not isinstance(ancestor, str)
        or not isinstance(descendant, str)
        or ancestor == descendant
        or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", ancestor) is None
        or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", descendant) is None
    ):
        return False
    return (
        _evidence_git(root, "merge-base", "--is-ancestor", ancestor, descendant)
        is not None
    )


def _registration_added_at_revision(root: Path, revision: str, locator: str) -> bool:
    raw = _evidence_git(
        root,
        "diff-tree",
        "--root",
        "--no-commit-id",
        "--name-only",
        "--diff-filter=A",
        "-r",
        revision,
        "--",
        locator,
    )
    if raw is None:
        return False
    try:
        return raw.decode("utf-8").splitlines() == [locator]
    except UnicodeError:
        return False


def _registration_history_paths(
    root: Path, frozen_at_revision: Any, errors: list[str]
) -> set[str] | None:
    if not isinstance(frozen_at_revision, str):
        _error(errors, "cannot enumerate cohort registrations without a freeze revision")
        return None
    raw = _evidence_git(
        root,
        "log",
        "--format=",
        "--name-status",
        "-z",
        f"{frozen_at_revision}..HEAD",
        "--",
        "product/evidence",
    )
    if raw is None:
        _error(errors, "cohort registration history cannot be enumerated")
        return None
    tokens = raw.split(b"\0")
    if tokens and tokens[-1] == b"":
        tokens.pop()
    paths: set[str] = set()
    index = 0
    try:
        while index < len(tokens):
            status = tokens[index].decode("ascii")
            index += 1
            path_count = 2 if status.startswith(("R", "C")) else 1
            if index + path_count > len(tokens):
                raise ValueError
            changed = [tokens[index + offset].decode("utf-8") for offset in range(path_count)]
            index += path_count
            registration_paths = [
                path
                for path in changed
                if PurePosixPath(path).parent == PurePosixPath("product/evidence")
                and PurePosixPath(path).name.endswith("-registration.json")
            ]
            if not registration_paths:
                continue
            if status == "D" or status.startswith(("R", "C")):
                _error(
                    errors,
                    "cohort registration artifacts are append-only and cannot be deleted, renamed or copied",
                )
            paths.update(registration_paths)
    except (UnicodeError, ValueError):
        _error(errors, "cohort registration history is malformed")
        return None
    return paths


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
    if message in errors or DIAGNOSTIC_LIMIT_MESSAGE in errors:
        return
    if len(errors) < MAX_VERIFICATION_DIAGNOSTICS - 1:
        errors.append(message)
    else:
        errors.append(DIAGNOSTIC_LIMIT_MESSAGE)


def _read_bounded_bytes(path: Path, label: str, errors: list[str]) -> bytes | None:
    budget = _VERIFICATION_READ_BUDGET.get()
    try:
        if _link_or_reparse(path):
            _error(errors, f"{label} cannot be a link or reparse point")
            return None
        canonical = os.path.normcase(str(path.resolve(strict=True)))
        if budget is not None:
            cached = budget["files"].get(canonical)
            if cached is not None:
                return cached
        with path.open("rb") as stream:
            raw = stream.read(MAX_DOCUMENT_BYTES + 1)
    except FileNotFoundError:
        _error(errors, f"missing {label}")
        return None
    except OSError as exc:
        _error(errors, f"cannot read {label}: {exc.__class__.__name__}")
        return None
    if len(raw) > MAX_DOCUMENT_BYTES:
        _error(errors, f"cannot read {label}: byte limit exceeded")
        return None
    if budget is not None:
        files = budget["files"]
        if len(files) >= MAX_VERIFICATION_FILES:
            _error(errors, "verification file limit exceeded")
            return None
        total = budget["bytes"] + len(raw)
        if total > MAX_VERIFICATION_TOTAL_BYTES:
            _error(errors, "verification cumulative byte limit exceeded")
            return None
        files[canonical] = raw
        budget["bytes"] = total
    return raw


def _json_within_resource_limits(value: Any) -> bool:
    nodes = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            return False
        if isinstance(current, str):
            if len(current) > MAX_JSON_STRING_CHARACTERS:
                return False
        elif isinstance(current, dict):
            if len(current) > MAX_JSON_CONTAINER_ITEMS:
                return False
            for key, item in current.items():
                if len(key) > MAX_JSON_STRING_CHARACTERS:
                    return False
                stack.append((item, depth + 1))
        elif isinstance(current, list):
            if len(current) > MAX_JSON_CONTAINER_ITEMS:
                return False
            stack.extend((item, depth + 1) for item in current)
    return True


def _parse_json_object_bytes(
    raw: bytes, label: str, errors: list[str]
) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        value = _parse_json(text)
    except (json.JSONDecodeError, _InvalidJson, RecursionError, UnicodeError):
        _error(errors, f"cannot read {label}: invalid JSON")
        return {}
    if not _json_within_resource_limits(value):
        _error(errors, f"cannot read {label}: JSON resource limit exceeded")
        return {}
    if not isinstance(value, dict):
        _error(errors, f"{label} must be a JSON object")
        return {}
    return value


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    raw = _read_bounded_bytes(path, label, errors)
    if raw is None:
        return {}
    return _parse_json_object_bytes(raw, label, errors)


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


def _substantive_registration_value(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return not isinstance(value, bool) and (
            not isinstance(value, float) or math.isfinite(value)
        )
    if isinstance(value, list):
        return bool(value) and all(
            _substantive_registration_value(item) for item in value
        )
    if isinstance(value, dict):
        return bool(value) and all(
            isinstance(key, str)
            and bool(key.strip())
            and _substantive_registration_value(item)
            for key, item in value.items()
        )
    return False


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


def _criteria_contract_digest(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    by_id: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            return None
        criterion_id = item.get("id")
        if not isinstance(criterion_id, str) or criterion_id in by_id:
            return None
        by_id[criterion_id] = item
    if set(by_id) != EXPECTED_CRITERION_IDS:
        return None
    contract: list[dict[str, Any]] = []
    for criterion_id in sorted(EXPECTED_CRITERION_IDS):
        fields = set(CRITERION_CONTRACT_BASE_FIELDS)
        if criterion_id in OUTCOME_IDS:
            fields.add("operationalization")
        item = by_id[criterion_id]
        contract.append({field: item.get(field) for field in sorted(fields)})
    payload = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
                for index, entry in enumerate(entries, start=1):
                    if index > MAX_AUTHORITY_WALK_ENTRIES:
                        _error(errors, "product authority root entry limit exceeded")
                        break
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
        authority_entries = 0
        pending = [harness_root]
        while pending:
            current_path = pending.pop()
            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        authority_entries += 1
                        if authority_entries > MAX_AUTHORITY_WALK_ENTRIES:
                            _error(errors, "Harness authority closure entry limit exceeded")
                            pending.clear()
                            break
                        candidate = Path(entry.path)
                        relative = candidate.relative_to(root).as_posix()
                        if _link_or_reparse(candidate):
                            if (
                                current_path == harness_root
                                and candidate.suffix.casefold() == ".py"
                            ):
                                _inside_root(root, relative, errors, "active authority")
                            else:
                                _error(
                                    errors,
                                    f"undeclared Harness authority link: {relative}",
                                )
                            continue
                        try:
                            is_directory = entry.is_dir(follow_symlinks=False)
                        except OSError:
                            _error(errors, "Harness authority closure cannot be enumerated")
                            continue
                        if is_directory:
                            if entry.name.casefold() != "__pycache__":
                                pending.append(candidate)
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
        raw = _read_bounded_bytes(path, f"active authority {relative}", errors)
        if raw is None:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeError:
            _error(errors, f"active authority cannot be read: {relative}")
            continue
        for pattern in FORBIDDEN_AUTHORITY_PATTERNS:
            if pattern.search(text):
                _error(errors, f"forbidden predecessor identity in active authority: {relative}")
        if path.suffix.casefold() == ".json":
            parse_errors: list[str] = []
            document = _parse_json_object_bytes(
                raw, f"active authority {relative}", parse_errors
            )
            if parse_errors:
                _error(errors, f"active authority JSON is invalid or unbounded: {relative}")
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
    if not _same_typed_value(prior, EXPECTED_PRIOR_RELEASE):
        _error(
            errors,
            "program priorRelease must match the code-owned historical milestone",
        )
    if not _same_typed_value(
        constitution.get("historicalEvidenceBoundary"),
        EXPECTED_HISTORICAL_EVIDENCE_BOUNDARY,
    ):
        _error(errors, "constitution historicalEvidenceBoundary is invalid")
    milestones = constitution.get("historicalMilestones")
    if not isinstance(milestones, list) or not _same_typed_value(
        milestones, list(EXPECTED_HISTORICAL_MILESTONES)
    ):
        _error(
            errors,
            "constitution historical milestones must match the code-owned records",
        )
    return len(errors) == before


def _supporting_documents_exist(
    root: Path, constitution: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    documents = _string_list(constitution.get("supportingDocuments"))
    if documents is None:
        _error(errors, "supportingDocuments must be a non-empty unique string list")
        return False
    if set(documents) != EXPECTED_REQUIRED_SUPPORTING_DOCUMENTS:
        _error(errors, "supportingDocuments must equal the code-owned semantic document set")
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
                continue
        except OSError:
            _error(errors, f"supporting document cannot be inspected: {relative}")
            continue
        raw_document = _read_bounded_bytes(
            candidate, f"supporting document {relative}", errors
        )
        if raw_document is None:
            continue
        try:
            substantive = bool(raw_document.decode("utf-8").strip())
        except UnicodeError:
            _error(errors, f"supporting document cannot be inspected: {relative}")
            continue
        if not substantive:
            _error(errors, f"supporting document is empty: {relative}")
    return len(errors) == before


def _frozen_v02_profile_artifacts_valid(root: Path, errors: list[str]) -> bool:
    before = len(errors)
    for relative, expected_sha256 in FROZEN_V02_PROFILE_ARTIFACT_SHA256.items():
        candidate = _inside_root(root, relative, errors, "frozen v0.2 profile artifact")
        if candidate is None:
            continue
        raw = _read_bounded_bytes(
            candidate, f"frozen v0.2 profile artifact {relative}", errors
        )
        if raw is None:
            continue
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            _error(errors, f"frozen v0.2 profile artifact identity changed: {relative}")
    return len(errors) == before


def _normative_profile_binding_valid(
    root: Path, program: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    binding = program.get("normativeProfileBinding")
    if not isinstance(binding, dict) or set(binding) != NORMATIVE_PROFILE_BINDING_FIELDS:
        _error(errors, "program normativeProfileBinding fields must match the code-owned schema")
        return False
    if binding.get("state") == "unfrozen":
        if not _same_typed_value(binding, UNFROZEN_NORMATIVE_PROFILE_BINDING):
            _error(errors, "unfrozen normative profile binding must contain only null identities")
        return len(errors) == before
    if binding.get("state") != "frozen":
        _error(errors, "program normative profile binding state must be unfrozen or frozen")
        return False
    locator = _relative_locator(binding.get("locator"))
    profile_path = PurePosixPath(locator) if locator is not None else None
    profile_identity = binding.get("profileIdentity")
    cohort_protocol_identity = binding.get("cohortProtocolIdentity")
    cohort_protocol_locator = _relative_locator(binding.get("cohortProtocolLocator"))
    cohort_protocol_path = (
        PurePosixPath(cohort_protocol_locator)
        if cohort_protocol_locator is not None
        else None
    )
    expected_sha256 = binding.get("sha256")
    cohort_protocol_sha256 = binding.get("cohortProtocolSha256")
    revision = binding.get("frozenAtRevision")
    if (
        locator is None
        or profile_path is None
        or not profile_path.parts
        or profile_path.parts[0] != "docs"
        or locator == "docs/DEMAND-TO-CAPABILITY-PROFILE.md"
        or not _nonempty_text(profile_identity)
        or not _nonempty_text(cohort_protocol_identity)
        or cohort_protocol_locator is None
        or cohort_protocol_path is None
        or not cohort_protocol_path.parts
        or cohort_protocol_path.parts[0] != "docs"
        or cohort_protocol_path.suffix != ".json"
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        or not isinstance(cohort_protocol_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", cohort_protocol_sha256) is None
        or not isinstance(revision, str)
    ):
        _error(errors, "frozen normative profile binding shape is invalid")
        return False
    candidate = _inside_root(root, locator, errors, "normative profile")
    if candidate is None:
        return False
    raw = _read_bounded_bytes(candidate, f"normative profile {locator}", errors)
    if raw is None:
        return False
    if (
        hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        != expected_sha256
        or not _committed_blob(root, revision, locator, expected_sha256)
    ):
        _error(errors, "frozen normative profile identity or source revision mismatch")
    protocol_candidate = _inside_root(
        root, cohort_protocol_locator, errors, "cohort protocol"
    )
    if protocol_candidate is None:
        return False
    protocol_raw = _read_bounded_bytes(
        protocol_candidate,
        f"cohort protocol {cohort_protocol_locator}",
        errors,
    )
    if protocol_raw is None:
        return False
    if (
        hashlib.sha256(protocol_raw.replace(b"\r\n", b"\n")).hexdigest()
        != cohort_protocol_sha256
        or not _committed_blob(
            root,
            revision,
            cohort_protocol_locator,
            cohort_protocol_sha256,
        )
    ):
        _error(errors, "frozen cohort protocol identity or source revision mismatch")
        return len(errors) == before
    protocol = _parse_json_object_bytes(
        protocol_raw,
        f"cohort protocol {cohort_protocol_locator}",
        errors,
    )
    protocol_valid = (
        set(protocol) == COHORT_PROTOCOL_FIELDS
        and type(protocol.get("schema")) is int
        and protocol.get("schema") == 1
        and _nonempty_text(protocol.get("id"))
        and protocol.get("profileIdentity") == profile_identity
        and protocol.get("cohortProtocolIdentity") == cohort_protocol_identity
        and all(
            protocol.get(field) == expected
            for field, expected in EXPECTED_COHORT_PROTOCOL_RULES.items()
        )
        and _string_list(protocol.get("strata")) is not None
        and _string_list(protocol.get("claimLimits")) is not None
    )
    if not protocol_valid:
        _error(errors, "frozen cohort protocol shape is invalid")
    return len(errors) == before


def _terminal_release_binding_valid(
    program: dict[str, Any], errors: list[str]
) -> bool:
    before = len(errors)
    binding = program.get("terminalReleaseBinding")
    if not isinstance(binding, dict) or set(binding) != TERMINAL_RELEASE_BINDING_FIELDS:
        _error(errors, "program terminalReleaseBinding fields must match the code-owned schema")
        return False
    if binding.get("state") == "unregistered":
        if not _same_typed_value(binding, UNREGISTERED_TERMINAL_RELEASE_BINDING):
            _error(errors, "unregistered terminal release binding must contain only null identities")
        return len(errors) == before
    tag = binding.get("tag")
    expected_prefix = f"{program.get('release')}."
    if (
        binding.get("state") != "candidate"
        or program.get("status") != "completed"
        or not isinstance(tag, str)
        or re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) is None
        or not tag.startswith(expected_prefix)
        or binding.get("publicRemote") != EXPECTED_PUBLIC_REMOTE
        or binding.get("annotationFormat")
        != TERMINAL_RELEASE_ANNOTATION_FORMAT
        or not isinstance(binding.get("o5EvidenceSetSha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", binding["o5EvidenceSetSha256"])
        is None
    ):
        _error(errors, "terminal release candidate binding shape is invalid")
    return len(errors) == before


def _release_identity_valid(
    constitution: dict[str, Any],
    program: dict[str, Any],
    acceptance: dict[str, Any],
    errors: list[str],
) -> bool:
    before = len(errors)
    for label, document in (
        ("constitution", constitution),
        ("program", program),
        ("acceptance", acceptance),
    ):
        if set(document) != AUTHORITY_TOP_LEVEL_FIELDS[label]:
            _error(
                errors,
                f"{label} top-level fields must match the code-owned schema",
            )
    release = program.get("release")
    if not isinstance(release, str) or RELEASE.fullmatch(release) is None:
        _error(errors, "program release must use v<major>.<minor>")
        release = "invalid"
    expected_program_id = f"harness-product-program-{CURRENT_RELEASE}"
    expected_acceptance_id = f"harness-product-acceptance-{CURRENT_RELEASE}"
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
        (release == CURRENT_RELEASE, f"program release must be {CURRENT_RELEASE}"),
        (acceptance.get("release") == release, "program and acceptance releases must match"),
        (program.get("constitution") == "product/constitution.json", "program constitution path is invalid"),
        (program.get("acceptance") == "product/acceptance.json", "program acceptance path is invalid"),
        (acceptance.get("program") == "product/program.json", "acceptance program path is invalid"),
        (program.get("completionExpression") == COMPLETION_EXPRESSION, "program completionExpression is invalid"),
        (acceptance.get("completionExpression") == COMPLETION_EXPRESSION, "acceptance completionExpression is invalid"),
        (constitution.get("purpose") == EXPECTED_PRODUCT_PURPOSE, "constitution purpose is invalid"),
        (
            constitution.get("successDefinition") == EXPECTED_SUCCESS_DEFINITION,
            "constitution successDefinition is invalid",
        ),
        (program.get("purpose") == EXPECTED_PROGRAM_PURPOSE, "program purpose is invalid"),
        (
            acceptance.get("progressRule") == EXPECTED_PROGRESS_RULE,
            "acceptance progressRule is invalid",
        ),
    )
    for valid, message in checks:
        if not valid:
            _error(errors, message)
    if not _same_typed_value(
        constitution.get("collaborationModel"), EXPECTED_COLLABORATION_MODEL
    ):
        _error(errors, "constitution collaborationModel is invalid")
    if not _same_typed_value(constitution.get("productForm"), EXPECTED_PRODUCT_FORM):
        _error(errors, "constitution productForm is invalid")
    fixed_invariants = _string_list(constitution.get("fixedInvariants"))
    if (
        fixed_invariants is None
        or set(fixed_invariants) != EXPECTED_FIXED_INVARIANTS
    ):
        _error(errors, "constitution fixedInvariants are invalid")
    adaptive_surfaces = _string_list(constitution.get("adaptiveSurfaces"))
    if (
        adaptive_surfaces is None
        or set(adaptive_surfaces) != EXPECTED_ADAPTIVE_SURFACES
    ):
        _error(errors, "constitution adaptiveSurfaces are invalid")
    bootstrap_guards = _string_list(constitution.get("bootstrapGuards"))
    if (
        bootstrap_guards is None
        or set(bootstrap_guards) != EXPECTED_BOOTSTRAP_GUARDS
    ):
        _error(errors, "constitution bootstrapGuards are invalid")
    if not _same_typed_value(
        constitution.get("planningModel"), EXPECTED_PLANNING_MODEL
    ):
        _error(errors, "constitution planningModel is invalid")
    if (
        _criteria_contract_digest(acceptance.get("criteria"))
        != EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256
    ):
        _error(errors, "acceptance criteria contract identity is invalid")
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
        if criterion_id in EXPECTED_CRITERION_IDS:
            expected_fields = set(CRITERION_BASE_FIELDS)
            if criterion_id in OUTCOME_IDS:
                expected_fields.add("operationalization")
                if assessment == "verified":
                    expected_fields.add("evidence")
            if set(item) != expected_fields:
                _error(
                    errors,
                    f"criterion {criterion_id} fields must match the code-owned schema",
                )
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
        _error(errors, "program status must be active, ready, or completed")
    if not increments and program_state != "ready":
        _error(errors, "only a ready program may have an empty current increment graph")
    active_increment_id = program.get("activeIncrementId")
    active_increments: list[dict[str, Any]] = []
    all_work: list[dict[str, Any]] = []
    increment_ids: set[str] = set()
    work_ids: set[str] = set()
    for increment in increments:
        increment_id = increment.get("id")
        if set(increment) != INCREMENT_FIELDS:
            _error(
                errors,
                f"increment {increment_id} fields must match the code-owned schema",
            )
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
            if set(work) != WORK_ITEM_FIELDS:
                _error(
                    errors,
                    f"work item {work_id} fields must match the code-owned schema",
                )
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
    if program_state in {"ready", "completed"} and any(
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
    if set(boundary) != AUTHORITY_BOUNDARY_FIELDS:
        _error(
            errors,
            "program authorityBoundary fields must match the code-owned schema",
        )
    user = _string_list(boundary.get("userOwns"))
    agent = _string_list(boundary.get("agentOwnsWithinBoundedAuthority"))
    if user is None or not REQUIRED_USER_AUTHORITY <= set(user):
        _error(errors, "program userOwns omits a mandatory human authority")
    elif set(user) != REQUIRED_USER_AUTHORITY:
        _error(errors, "program userOwns contains an undeclared human authority")
    if agent is None:
        _error(errors, "program agent authority must be a non-empty string list")
        agent = []
    elif set(agent) != set(OPERATION_EFFECTS):
        _error(errors, "program agent authority must equal the code-owned operation set")
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


def _task_registration_guardrail(
    root: Path,
    increment: dict[str, Any],
    criteria: Mapping[str, dict[str, Any]],
    profile_binding: Mapping[str, Any],
    errors: list[str],
) -> tuple[datetime, str, str, str] | None:
    before = len(errors)
    increment_id = increment.get("id")
    mapped = _string_list(increment.get("acceptanceIds")) or []
    mapped_outcomes = sorted(set(mapped) & OUTCOME_IDS)
    binding = increment.get("taskRegistration")
    if not mapped_outcomes:
        if binding is not None:
            _error(
                errors,
                f"outcome-neutral increment {increment_id} must bind null taskRegistration",
            )
        return None
    if profile_binding.get("state") != "frozen":
        _error(
            errors,
            f"outcome-bearing increment {increment_id} requires a frozen normative profile",
        )
        return None
    if not isinstance(binding, dict) or set(binding) != TASK_REGISTRATION_BINDING_FIELDS:
        _error(
            errors,
            f"outcome-bearing increment {increment_id} requires an exact taskRegistration binding",
        )
        return None
    locator = _relative_locator(binding.get("locator"), allow_evidence=True)
    registration_path = PurePosixPath(locator) if locator is not None else None
    if (
        registration_path is None
        or registration_path.parent != PurePosixPath("product/evidence")
        or not registration_path.name.endswith("-registration.json")
    ):
        _error(errors, f"increment {increment_id} has invalid taskRegistration locator")
        return None
    candidate = _inside_root(root, locator, errors, "task registration")
    if candidate is None:
        return None
    registration_label = f"task registration {locator}"
    raw = _read_bounded_bytes(candidate, registration_label, errors)
    if raw is None:
        return None
    expected_sha256 = binding.get("sha256")
    if (
        not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
    ):
        _error(errors, f"increment {increment_id} taskRegistration identity mismatch")
        return None
    source_revision = binding.get("sourceRevision")
    measurement_not_before = _rfc3339_instant(binding.get("measurementNotBefore"))
    profile_sha256 = binding.get("profileSha256")
    cohort_protocol_sha256 = binding.get("cohortProtocolSha256")
    frozen_at_revision = profile_binding.get("frozenAtRevision")
    if (
        not isinstance(source_revision, str)
        or hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
        != expected_sha256
        or not _committed_blob(root, source_revision, locator, expected_sha256)
        or not _registration_added_at_revision(root, source_revision, locator)
        or measurement_not_before is None
        or profile_sha256 != profile_binding.get("sha256")
        or cohort_protocol_sha256
        != profile_binding.get("cohortProtocolSha256")
    ):
        _error(
            errors,
            f"increment {increment_id} taskRegistration identity or frozen-profile binding mismatch",
        )
        return None
    if not _strict_git_ancestor(root, frozen_at_revision, source_revision):
        _error(
            errors,
            f"increment {increment_id} taskRegistration must strictly descend from the frozen profile and cohort protocol",
        )
        return None
    registration = _parse_json_object_bytes(raw, registration_label, errors)
    if set(registration) != TASK_REGISTRATION_FIELDS:
        _error(errors, f"task registration {locator} fields must match the code-owned schema")
        return None
    criterion_ids = _string_list(registration.get("criterionIds"))
    source_capture = registration.get("sourceCaptureEligibilityAndStopRule")
    acceptance_authority = registration.get("acceptanceAuthority")
    floors = registration.get("qualitySafetyEvidenceAndResidueFloors")
    values = registration.get("preRegistrationValues")
    registered_at = _rfc3339_instant(registration.get("registeredAt"))
    expected_fields: set[str] = set()
    for criterion_id in mapped_outcomes:
        operationalization = criteria.get(criterion_id, {}).get("operationalization")
        if not isinstance(operationalization, dict):
            _error(errors, f"task registration {locator} cannot resolve {criterion_id}")
            continue
        required = _string_list(operationalization.get("preRegistrationFields"))
        if required is None:
            _error(errors, f"task registration {locator} cannot resolve {criterion_id}")
            continue
        expected_fields.update(required)
    shape_valid = (
        type(registration.get("schema")) is int
        and registration.get("schema") == 1
        and _nonempty_text(registration.get("id"))
        and registered_at is not None
        and registered_at <= measurement_not_before
        and _nonempty_text(registration.get("taskIdentity"))
        and registration.get("incrementId") == increment_id
        and criterion_ids == mapped_outcomes
        and isinstance(values, dict)
        and set(values) == expected_fields
        and all(_substantive_registration_value(item) for item in values.values())
        and values.get("normativeProfileIdentity")
        == profile_binding.get("profileIdentity")
        and values.get("cohortProtocolIdentity")
        == profile_binding.get("cohortProtocolIdentity")
        and values.get("profileSha256") == profile_binding.get("sha256")
        and values.get("cohortProtocolSha256")
        == profile_binding.get("cohortProtocolSha256")
        and all(
            _same_typed_value(values[field], registration[field])
            for field in TASK_REGISTRATION_VALUE_ALIASES & expected_fields
        )
        and _nonempty_text(registration.get("namedHumanAcceptor"))
        and isinstance(acceptance_authority, dict)
        and set(acceptance_authority) == ACCEPTANCE_AUTHORITY_FIELDS
        and acceptance_authority.get("locator") == "product/acceptance.json"
        and acceptance_authority.get("criteriaContractSha256")
        == EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256
        and isinstance(floors, dict)
        and bool(floors)
        and all(
            isinstance(key, str)
            and bool(key.strip())
            and _substantive_registration_value(item)
            for key, item in floors.items()
        )
        and _string_list(registration.get("materialInterventionTaxonomy")) is not None
        and _string_list(registration.get("materialCollaborationLossTaxonomy")) is not None
        and isinstance(source_capture, dict)
        and set(source_capture) == SOURCE_CAPTURE_FIELDS
        and _nonempty_text(source_capture.get("measurementStartsAfter"))
        and _string_list(source_capture.get("eligibleSources")) is not None
        and _string_list(source_capture.get("ineligibleSources")) is not None
        and _nonempty_text(source_capture.get("stopRule"))
        and _string_list(registration.get("claimLimits")) is not None
    )
    if not shape_valid:
        _error(errors, f"task registration {locator} shape is invalid")
    task_identity = registration.get("taskIdentity")
    return (
        (measurement_not_before, task_identity, source_revision, locator)
        if len(errors) == before
        and isinstance(task_identity, str)
        and isinstance(source_revision, str)
        else None
    )


def _task_registration_floors(
    root: Path,
    increments: list[dict[str, Any]],
    criteria: Mapping[str, dict[str, Any]],
    profile_binding: Mapping[str, Any],
    errors: list[str],
) -> dict[str, datetime]:
    floors: dict[str, datetime] = {}
    task_identities: set[str] = set()
    bound_registration_paths: set[str] = set()
    prior_registration_revision: str | None = None
    for increment in increments:
        increment_id = increment.get("id")
        registration = _task_registration_guardrail(
            root, increment, criteria, profile_binding, errors
        )
        if isinstance(increment_id, str) and registration is not None:
            floor, task_identity, source_revision, locator = registration
            if task_identity in task_identities:
                _error(
                    errors,
                    f"taskIdentity {task_identity} is reused across outcome registrations",
                )
            task_identities.add(task_identity)
            if prior_registration_revision is not None and not _strict_git_ancestor(
                root, prior_registration_revision, source_revision
            ):
                _error(
                    errors,
                    "outcome registration revisions must form one strict Git ancestry order",
                )
            prior_registration_revision = source_revision
            bound_registration_paths.add(locator)
            floors[increment_id] = floor
    if profile_binding.get("state") == "frozen":
        history_paths = _registration_history_paths(
            root, profile_binding.get("frozenAtRevision"), errors
        )
        if history_paths is not None and history_paths != bound_registration_paths:
            _error(
                errors,
                "every post-freeze cohort registration artifact must bind exactly one outcome increment",
            )
    return floors


def _process_loss_guardrail(
    root: Path,
    increments: list[dict[str, Any]],
    validated_work_outcomes: Mapping[str, set[str]],
    errors: list[str],
) -> bool:
    before = len(errors)
    seen_correction_classes: set[str] = set()
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
            "maxMaterialUserCapabilityOrchestrationInterventions",
        )
        for field in integer_fields:
            value = budget.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                _error(errors, f"process-loss budget {field} must be a non-negative integer")
        if budget.get("maxSameClassUserCorrectionBeforeStop") != 1:
            _error(errors, "same-class user correction budget must stop before recurrence")
        if budget.get("maxMaterialUserCapabilityOrchestrationInterventions") != 0:
            _error(errors, "material user capability orchestration intervention budget must be zero")
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
            and correction_class in seen_correction_classes
        ):
            _error(errors, f"increments repeat correctionClass: {correction_class}")
        if isinstance(correction_class, str) and correction_class:
            seen_correction_classes.add(correction_class)

        cleanup = increment.get("cleanupBoundary")
        if not isinstance(cleanup, dict) or set(cleanup) != CLEANUP_BOUNDARY_FIELDS:
            _error(
                errors,
                f"increment {increment_id} requires the exact cleanup boundary fields",
            )
            continue
        paths = cleanup.get("repositoryTemporaryPaths")
        if (
            not isinstance(paths, list)
            or not all(isinstance(item, str) and item.strip() for item in paths)
            or len(paths) != len(set(paths))
        ):
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
    scanned_entries = 0

    def conventional_directory(name: str) -> bool:
        return name.casefold() in CONVENTIONAL_RESIDUE_NAMES

    def conventional_file(name: str) -> bool:
        folded = name.casefold()
        return folded in CONVENTIONAL_RESIDUE_NAMES or folded.endswith(
            CONVENTIONAL_RESIDUE_SUFFIXES
        )

    pending: list[tuple[Path, int]] = [(root, 0)]
    while pending:
        current_path, depth = pending.pop()
        if depth > MAX_REPOSITORY_WALK_DEPTH:
            _error(errors, "repository residue scan depth limit exceeded")
            break
        try:
            with os.scandir(current_path) as entries:
                for entry in entries:
                    scanned_entries += 1
                    if scanned_entries > MAX_REPOSITORY_WALK_ENTRIES:
                        _error(errors, "repository residue scan entry limit exceeded")
                        pending.clear()
                        break
                    candidate = Path(entry.path)
                    try:
                        relative = candidate.relative_to(root).as_posix()
                    except ValueError:
                        _error(errors, "repository residue scan escaped the repository root")
                        continue
                    if relative == ".git" or relative.startswith(".git/"):
                        continue
                    linked = _link_or_reparse(candidate)
                    try:
                        is_directory = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        _error(errors, "repository residue cannot be enumerated")
                        continue
                    if is_directory:
                        if conventional_directory(entry.name):
                            _error(errors, f"repository cleanup residue remains: {relative}")
                        elif not linked:
                            pending.append((candidate, depth + 1))
                        continue
                    if conventional_file(entry.name):
                        _error(errors, f"repository cleanup residue remains: {relative}")
        except OSError:
            _error(errors, "repository residue cannot be enumerated")
    return len(errors) == before


def _evidence_states(
    root: Path,
    criteria: dict[str, dict[str, Any]],
    work_bindings: Mapping[str, tuple[str, set[str], str]],
    registration_floors: Mapping[str, datetime],
    errors: list[str],
) -> tuple[dict[str, bool], bool, dict[str, set[str]]]:
    states = {criterion_id: False for criterion_id in EXPECTED_CRITERION_IDS}
    validated_work_outcomes: dict[str, set[str]] = {}
    evidence_id_locators: dict[str, str] = {}
    before = len(errors)
    evidence_locator_references = sum(
        len(_string_list(criteria.get(criterion_id, {}).get("evidence")) or [])
        for criterion_id in OUTCOME_IDS
        if criteria.get(criterion_id, {}).get("assessment") == "verified"
    )
    if evidence_locator_references > MAX_EVIDENCE_LOCATOR_REFERENCES:
        _error(errors, "evidence locator reference limit exceeded")
        return states, False, validated_work_outcomes
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
                and increment_id in registration_floors
                and observed_at >= registration_floors[increment_id]
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
            validator_spec = SUPPORTED_EVIDENCE_VALIDATORS.get(validator_kind)
            if validator_spec is None:
                _error(errors, f"criterion {criterion_id} has no code-owned evidence validator: {validator_kind}")
                valid = False
                continue
            supported_criteria, supported_increments, evidence_validator = validator_spec
            if criterion_id not in supported_criteria:
                _error(
                    errors,
                    f"criterion {criterion_id} is not supported by evidence validator: {validator_kind}",
                )
                valid = False
                continue
            if increment_id not in supported_increments:
                _error(
                    errors,
                    f"criterion {criterion_id} evidence validator is not bound to "
                    f"increment {increment_id}: {validator_kind}",
                )
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


def _criterion_evidence_set_sha256(
    root: Path,
    criterion: Mapping[str, Any],
    errors: list[str],
) -> str | None:
    locators = _string_list(criterion.get("evidence"))
    if criterion.get("assessment") != "verified" or locators is None:
        return None
    digest = hashlib.sha256()
    for locator in sorted(locators):
        relative = _relative_locator(locator, allow_evidence=True)
        path = PurePosixPath(relative) if relative is not None else None
        if (
            path is None
            or path.parent != PurePosixPath("product/evidence")
            or path.suffix != ".json"
        ):
            return None
        candidate = _inside_root(root, relative, errors, "terminal evidence")
        if candidate is None:
            return None
        raw = _read_bounded_bytes(candidate, f"terminal evidence {relative}", errors)
        if raw is None:
            return None
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(raw.replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _terminal_checkout_inventory_clean(root: Path, errors: list[str]) -> bool:
    tracked_raw = _evidence_git(root, "ls-files", "-z", "--cached")
    if tracked_raw is None:
        _error(errors, "terminal tracked-file inventory cannot be resolved")
        return False
    try:
        tracked = {
            item.decode("utf-8")
            for item in tracked_raw.split(b"\0")
            if item
        }
    except UnicodeError:
        _error(errors, "terminal tracked-file inventory is malformed")
        return False
    required_directories: set[str] = set()
    for relative in tracked:
        parent = PurePosixPath(relative).parent
        while parent != PurePosixPath("."):
            required_directories.add(parent.as_posix())
            parent = parent.parent
    observed_files: set[str] = set()
    entries_seen = 0
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        if depth > MAX_REPOSITORY_WALK_DEPTH:
            _error(errors, "terminal checkout inventory depth limit exceeded")
            return False
        try:
            with os.scandir(directory) as iterator:
                entries = list(iterator)
        except OSError:
            _error(errors, "terminal checkout inventory cannot be enumerated")
            return False
        for entry in entries:
            entries_seen += 1
            if entries_seen > MAX_REPOSITORY_WALK_ENTRIES:
                _error(errors, "terminal checkout inventory entry limit exceeded")
                return False
            candidate = Path(entry.path)
            try:
                relative = candidate.relative_to(root).as_posix()
            except ValueError:
                _error(errors, "terminal checkout inventory escaped the repository root")
                return False
            if depth == 0 and relative == ".git":
                continue
            try:
                metadata = candidate.lstat()
            except OSError:
                _error(errors, "terminal checkout inventory entry cannot be inspected")
                return False
            if stat.S_ISDIR(metadata.st_mode) and not _link_or_reparse(candidate):
                if relative not in required_directories:
                    _error(errors, f"terminal checkout contains an extra directory: {relative}")
                    return False
                stack.append((candidate, depth + 1))
                continue
            if relative not in tracked:
                _error(errors, f"terminal checkout contains an extra entry: {relative}")
                return False
            observed_files.add(relative)
    if observed_files != tracked:
        _error(errors, "terminal checkout does not materialize the exact tracked file set")
        return False
    return True


def _terminal_release_gate(
    root: Path,
    program: Mapping[str, Any],
    criteria: Mapping[str, Mapping[str, Any]],
    errors: list[str],
) -> tuple[bool, str]:
    binding = program.get("terminalReleaseBinding")
    if not isinstance(binding, dict) or binding.get("state") != "candidate":
        _error(errors, "terminal completion requires a predeclared release candidate binding")
        return False, "invalid"
    expected_evidence_sha256 = _criterion_evidence_set_sha256(
        root, criteria.get("O5", {}), errors
    )
    if expected_evidence_sha256 != binding.get("o5EvidenceSetSha256"):
        _error(errors, "terminal release candidate does not bind the exact O5 evidence set")
        return False, "invalid"
    status = _evidence_git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        "--ignored=matching",
    )
    if status is None:
        _error(
            errors,
            "terminal release candidate checkout status cannot be resolved",
        )
        return False, "invalid"
    if status != b"":
        _error(
            errors,
            "terminal release candidate must be a clean checkout with no ignored or untracked residue",
        )
        return False, "invalid"
    if not _terminal_checkout_inventory_clean(root, errors):
        return False, "invalid"
    head_raw = _evidence_git(root, "rev-parse", "--verify", "HEAD")
    try:
        head = head_raw.decode("ascii").strip() if head_raw is not None else ""
    except UnicodeError:
        head = ""
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head) is None:
        _error(errors, "terminal release candidate HEAD cannot be resolved")
        return False, "invalid"
    tag = binding["tag"]
    tag_ref = f"refs/tags/{tag}"
    local_tag_raw = _evidence_git(root, "rev-parse", "--verify", tag_ref)
    if local_tag_raw is None:
        return False, "candidate-clean-awaiting-authorized-tag"
    try:
        local_tag_object = local_tag_raw.decode("ascii").strip()
    except UnicodeError:
        local_tag_object = ""
    tag_type = _evidence_git(root, "cat-file", "-t", tag_ref)
    tag_commit = _evidence_git(root, "rev-parse", f"{tag_ref}^{{commit}}")
    annotation_raw = _evidence_git(
        root, "for-each-ref", "--format=%(contents)", "--count=1", tag_ref
    )
    try:
        tag_commit_text = tag_commit.decode("ascii").strip() if tag_commit is not None else ""
    except UnicodeError:
        tag_commit_text = ""
    if (
        re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", local_tag_object) is None
        or tag_type is None
        or tag_type.strip() != b"tag"
        or tag_commit_text != head
        or annotation_raw is None
    ):
        _error(errors, "local terminal tag is not one annotated tag over candidate HEAD")
        return False, "invalid"
    annotation = _parse_json_object_bytes(
        annotation_raw.strip(), f"terminal tag annotation {tag}", errors
    )
    authority = annotation.get("authority")
    authorization_source = (
        authority.get("source") if isinstance(authority, dict) else None
    )
    authorization_validator = (
        authority.get("validator") if isinstance(authority, dict) else None
    )
    annotation_valid = (
        set(annotation) == TERMINAL_RELEASE_ANNOTATION_FIELDS
        and type(annotation.get("schema")) is int
        and annotation.get("schema") == 1
        and annotation.get("format") == TERMINAL_RELEASE_ANNOTATION_FORMAT
        and annotation.get("productId") == PRODUCT_ID
        and annotation.get("release") == program.get("release")
        and annotation.get("candidateRevision") == head
        and annotation.get("tag") == tag
        and annotation.get("publicRemote") == EXPECTED_PUBLIC_REMOTE
        and annotation.get("o5EvidenceSetSha256") == expected_evidence_sha256
        and isinstance(authority, dict)
        and set(authority) == TERMINAL_RELEASE_AUTHORITY_FIELDS
        and authority.get("kind") == "named-accountable-human"
        and _nonempty_text(authority.get("name"))
        and authority.get("decision") == "authorized"
        and _rfc3339_instant(authority.get("decidedAt")) is not None
        and isinstance(authorization_source, dict)
        and set(authorization_source)
        == TERMINAL_RELEASE_AUTHORITY_SOURCE_FIELDS
        and all(
            _nonempty_text(authorization_source.get(field))
            for field in ("kind", "locator", "identity")
        )
        and isinstance(authorization_source.get("payloadSha256"), str)
        and re.fullmatch(
            r"[0-9a-f]{64}", authorization_source["payloadSha256"]
        )
        is not None
        and isinstance(authorization_validator, dict)
        and set(authorization_validator)
        == TERMINAL_RELEASE_AUTHORITY_VALIDATOR_FIELDS
        and _nonempty_text(authorization_validator.get("kind"))
        and type(authorization_validator.get("version")) is int
        and authorization_validator.get("version") == 1
        and _same_typed_value(
            annotation.get("acceptedScope"), EXPECTED_TERMINAL_RELEASE_SCOPE
        )
    )
    if not annotation_valid:
        _error(errors, "terminal tag annotation authorization is invalid")
        return False, "invalid"
    validator_kind = authorization_validator["kind"]
    authorization_evaluator = SUPPORTED_HUMAN_AUTHORIZATION_VALIDATORS.get(
        validator_kind
    )
    if authorization_evaluator is None:
        _error(
            errors,
            f"terminal human authorization has no code-owned source validator: {validator_kind}",
        )
        return False, "invalid"
    try:
        authorization_verified = authorization_evaluator(annotation, root, errors)
    except Exception as exc:
        _error(
            errors,
            "terminal human authorization validator failed closed: "
            f"{exc.__class__.__name__}",
        )
        return False, "invalid"
    if authorization_verified is not True:
        _error(errors, "terminal human authorization source was not independently verified")
        return False, "invalid"
    remote_raw = _evidence_git(
        root,
        "ls-remote",
        "--tags",
        EXPECTED_PUBLIC_REMOTE,
        tag_ref,
    )
    if remote_raw is None:
        _error(errors, "public terminal tag cannot be verified")
        return False, "invalid"
    try:
        remote_entries = {
            ref: object_id
            for line in remote_raw.decode("ascii").splitlines()
            for object_id, ref in [line.split("\t", 1)]
        }
    except (UnicodeError, ValueError):
        remote_entries = {}
    if (
        remote_entries
        != {
            tag_ref: local_tag_object,
            f"{tag_ref}^{{}}": head,
        }
    ):
        _error(errors, "public terminal tag object or peeled commit does not match locally")
        return False, "invalid"
    return True, "published-verified"


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
    frozen_v02_profile = _frozen_v02_profile_artifacts_valid(root, errors)
    normative_profile = _normative_profile_binding_valid(root, program, errors)
    terminal_release_binding = _terminal_release_binding_valid(program, errors)
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
        and frozen_v02_profile
        and normative_profile
        and terminal_release_binding
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
    registration_before = len(errors)
    registration_floors = _task_registration_floors(
        root,
        increments,
        criteria,
        program.get("normativeProfileBinding")
        if isinstance(program.get("normativeProfileBinding"), dict)
        else {},
        errors,
    )
    registrations_valid = len(errors) == registration_before
    evidence_states, evidence_valid, validated_work_outcomes = _evidence_states(
        root, criteria, work_bindings, registration_floors, errors
    )
    authority_guardrail = _authority_guardrail(program, all_work, errors)
    process_loss_valid = _process_loss_guardrail(
        root, increments, validated_work_outcomes, errors
    )
    process_guardrail = registrations_valid and process_loss_valid and graph_valid

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
    evidence_outcomes_pass = all(
        states[criterion_id] for criterion_id in OUTCOME_IDS
    )
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
    terminal_release_state = (
        program.get("terminalReleaseBinding", {}).get("state", "invalid")
        if isinstance(program.get("terminalReleaseBinding"), dict)
        else "invalid"
    )
    terminal_release_verified = False
    if guardrails_pass and evidence_outcomes_pass and graph_terminal:
        terminal_release_verified, terminal_release_state = _terminal_release_gate(
            root, program, criteria, errors
        )
        if not terminal_release_verified:
            states["O5"] = False
    outcomes_pass = all(states[criterion_id] for criterion_id in OUTCOME_IDS)
    accepted = (
        not errors
        and guardrails_pass
        and outcomes_pass
        and graph_terminal
        and terminal_release_verified
    )
    valid = not errors and guardrails_pass
    return {
        "productId": PRODUCT_ID,
        "release": program.get("release"),
        "programStatus": program.get("status"),
        "valid": valid,
        "completionState": "accepted" if accepted else "in-progress",
        "terminalReleaseState": terminal_release_state,
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

    cache_token = _EVIDENCE_GIT_CACHE.set({})
    read_budget_token = _VERIFICATION_READ_BUDGET.set({"bytes": 0, "files": {}})
    try:
        try:
            return _verify_product(root)
        except Exception as exc:
            return {
                "productId": PRODUCT_ID,
                "release": None,
                "programStatus": None,
                "valid": False,
                "completionState": "in-progress",
                "terminalReleaseState": "invalid",
                "activeIncrement": None,
                "outcomes": {"verified": 0, "total": len(OUTCOME_IDS)},
                "guardrails": {"passed": 0, "total": len(GUARDRAIL_IDS)},
                "criterionStates": {
                    key: False for key in sorted(EXPECTED_CRITERION_IDS)
                },
                "errors": [f"verifier failed closed: {exc.__class__.__name__}"],
            }
    finally:
        _VERIFICATION_READ_BUDGET.reset(read_budget_token)
        _EVIDENCE_GIT_CACHE.reset(cache_token)
