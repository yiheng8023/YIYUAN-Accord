"""Historical-event-neutral product-contract verification for the Harness.

The verifier owns current authority shape, causal-program invariants, evidence
admission, human authority, and bounded process loss. Historical release event
validators live at their accepted Git revisions; they are not carried forward
as current product authority.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import subprocess
from types import MappingProxyType
from typing import Any, Callable, Mapping


PRODUCT_ID = "agent-autonomy-harness"
CONSTITUTION_ID = "harness-product-constitution-v1"
CURRENT_RELEASE = "v0.2"
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
    "Prove the open Agent-neutral demand-driven human-Agent collaboration quality harness "
    "through goal-level natural-task dogfooding, dynamic capability, task-topology, and context-carrier "
    "lifecycle arbitration, an accepted methodology and open quality-conformance profile, "
    "and thin cross-host reference adapters that reuse sufficient external protocol, "
    "runtime, identity, audit, provenance, and evaluation layers."
)
EXPECTED_PROGRESS_RULE = (
    "Only accepted real-task outcomes O1-O5 in a currently valid authority graph with "
    "G1-G4 passing count as progress. Documents, tests, inventories, fixtures, "
    "memberships, and research volume are supporting evidence only."
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
        "O1": (1, "single-pre-registered-natural-task"),
        "O2": (3, "source-bound-baseline-by-pre-registered-scenario-class"),
        "O3": (3, "bounded-route-cohort-with-retain-option"),
        "O4": (4, "same-version-scorecard-with-source-bound-comparator-and-pass-fail-cases"),
        "O5": (1, "same-task-matched-cross-host-pair"),
    }
)
CRITERION_CONTRACT_BASE_FIELDS = CRITERION_BASE_FIELDS - {"assessment"}
EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256 = (
    "c3993f40052ac2de75193c5cf923d98d6bd0b899aa7fc42ddeb772103932baf6"
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
    "publication",
    "release",
    "accountable-outcome-acceptance",
    "destructive-or-irreversible-action",
}
AUTHORITY_BOUNDARY_FIELDS = {
    "userOwns",
    "agentOwnsWithinBoundedAuthority",
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
    "bounded-consumer-configuration-after-explicit-grant": "bounded-local-write",
    "coverage-analysis": "local-read",
    "targeted-capability-discovery": "bounded-public-read",
    "capability-static-review": "local-read",
    "inactive-exact-acquisition": "bounded-local-write",
}
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
TASK_REGISTRATION_BINDING_FIELDS = {"locator", "sha256"}
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
CONVENTIONAL_RESIDUE_NAMES = {".tmp", "__pycache__"}
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
    "release": "v0.1",
    "state": "accepted-repository-control-milestone",
    "revision": "be498f960c9e0587d355291fb24261c91e75cd77",
    "currentAuthority": False,
}
EXPECTED_HISTORICAL_MILESTONE = {
    **EXPECTED_PRIOR_RELEASE,
    "claimLimit": (
        "repository-bound control evidence only; not terminal proposition, "
        "broad user value, software-engineering standard, cross-host, "
        "production, or publication proof"
    ),
}


EvidenceValidator = Callable[[dict[str, Any], str, Path, list[str]], bool]
EvidenceValidatorSpec = tuple[
    frozenset[str],
    frozenset[str],
    EvidenceValidator,
]


_PUBLIC_INTAKE_INCREMENT_ID = "increment.v0.2.public-intake-zero-knowledge"
_PUBLIC_INTAKE_WORK_ID = "work.v0.2.public-intake-zero-knowledge"
_PUBLIC_INTAKE_REGISTRATION = (
    "product/evidence/public-intake-zero-knowledge-registration.json"
)
_PUBLIC_INTAKE_REGISTRATION_SHA256 = (
    "125397f528f7042b82973a2aa47e6f429bd24d4b85ceeb29e7baa1c334c0a89f"
)
_PUBLIC_INTAKE_BASELINE_COMMIT = "a2d291f0cbe5a53d1c5beb68ae1591efd5bdfdce"
_PUBLIC_INTAKE_REGISTRATION_COMMIT = "25ddc0cb6493bb7bce0cc722b29387d1a9155ee3"
_PUBLIC_INTAKE_RESULT_COMMIT = "2008d0d4a5b44caa32652f2a15ba12d403348ce2"
_PUBLIC_INTAKE_RECEIPT_SHA256 = (
    "1359e130bb1ac9afec6f0159a0c9661e3a2c822fea3c402ff0b9c67e548dea45"
)
_PUBLIC_INTAKE_SOURCE_IDENTITY = (
    "sha256:f7c68b722f7824d5c57ff0e25fa1f725508600c1cd48264390b1aec77ad3dc2a"
)
_PUBLIC_INTAKE_ACCEPTANCE_MESSAGE_SHA256 = (
    "a5417defbb630b5e051a37aeb14aa523b2dcf6d6c29c9f4da587ef03dec6efc0"
)
_PUBLIC_INTAKE_SOURCE_EVENTS = (
    "goal-level-demand-received",
    "registration-committed-and-pushed",
    "native-context-compacted",
    "post-compaction-task-recovered",
    "deliverable-committed-and-pushed",
    "bounded-human-judgment-requested",
    "public-result-identity-confirmed",
    "named-human-accepted",
)
_PUBLIC_INTAKE_DOCUMENTS = MappingProxyType(
    {
        "CONTRIBUTING.md": (
            "bb700a5833de4861d459493d9f8a6aa0b93833e9",
            "0c7f6ae6479956983c8025ee44fb450b2654bde3",
            "190cc5f8a3551b01d740a5944646e2678e9dbdb14f168d99ccf79d5e504b78ed",
            "For a change that affects purpose, behavior, acceptance",
            "You do not need to know the Harness criteria",
            "Do not submit credentials, private memory, account state",
        ),
        "SUPPORT.md": (
            "9df45cf2d43a78d460c6d5e5356f04e20f1bd256",
            "eadf2127fad52fcd10c9f4064e330c8c0a7cb1f9",
            "dd02723f0d52be6a8a180ca415d30faa221f8343632119f9b2786dec68c5d4c7",
            "identify the exact repository revision and affected artifact",
            "You do not need to identify a Git revision",
            "The project does not provide a support SLA",
        ),
        "SUPPORT.zh-CN.md": (
            "3bd9e87c015b7d89029b1e5f861e8477619f6a37",
            "5fd0410ccbf9bee8a981967acfa0b9bebf2ed721",
            "2801340c7679a2c3e6c4ddc786d1df51050cefaa9ad1da80f0034bba10e7b933",
            "标明准确的仓库 revision 和受影响产物",
            "你不需要先查 Git revision",
            "本项目不提供支持 SLA",
        ),
    }
)

_CODEX_SKILL_INCREMENT_ID = "increment.v0.2.codex-demand-skill-plugin"
_CODEX_SKILL_WORK_ID = "work.v0.2.codex-demand-skill-plugin"
_CODEX_SKILL_REGISTRATION = (
    "product/evidence/codex-demand-skill-plugin-registration.json"
)
_CODEX_SKILL_REGISTRATION_SHA256 = (
    "16e737b569c41f5b7f2c847d67bb70c2eb7ca0491481fec7c533a498d4051824"
)
_CODEX_SKILL_BASELINE_COMMIT = "784c26dd813a8a38764c896bbcda1d2ec7385001"
_CODEX_SKILL_REGISTRATION_COMMIT = "aa7effd4de8739a63418f826f5f4d927973d024d"
_CODEX_SKILL_RESULT_COMMIT = "6892fef39e88f17d628bee7ff0f837a4d051665d"
_CODEX_SKILL_RECEIPT_SHA256 = (
    "266115dd0f5e030afc3be41920b3ac4d15a0b3d91193f1e0bbcbf2851149f904"
)
_CODEX_SKILL_SOURCE_IDENTITY = (
    "sha256:3074a4feb2877a8be9129c2eb15b0f75249991a84b084abd8716693f43564e6a"
)
_CODEX_SKILL_ACCEPTANCE_MESSAGE_SHA256 = (
    "a5417defbb630b5e051a37aeb14aa523b2dcf6d6c29c9f4da587ef03dec6efc0"
)
_CODEX_SKILL_ACCEPTANCE_RECORD_SHA256 = (
    "35afae0352cb00c13c80c328a3c46f8fc233c6223f9d220f609b0da6ca120372"
)
_CODEX_SKILL_JUDGMENT_REQUEST_SHA256 = (
    "80f78659b62bd2601b6030c54f84e2327816b5ea20363e752597fe542c1029d3"
)
_CODEX_SKILL_SOURCE_EVENTS = (
    "goal-level-demand-received",
    "registration-committed",
    "registration-pushed",
    "native-context-compacted",
    "post-compaction-task-and-source-recovered",
    "deliverable-committed",
    "deliverable-pushed",
    "bounded-human-judgment-requested",
    "goal-mode-continuation-commentary-one",
    "goal-mode-continuation-final-one",
    "goal-mode-continuation-commentary-two",
    "goal-mode-temporary-blocked-final",
    "named-human-accepted",
)
_CODEX_SKILL_RESULT_PATHS = (
    "README.md",
    "README.zh-CN.md",
    "adapters/agent-autonomy-harness-codex/.codex-plugin/plugin.json",
    "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/SKILL.md",
    "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/agents/openai.yaml",
    "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
    "docs/architecture.md",
    "docs/operations/CONTINUATION.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "tests/product/test_product_control.py",
)
_CODEX_SKILL_TASK_FILES = MappingProxyType(
    {
        "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/SKILL.md": (
            "e34d2299a9ef6e3abded16b88fab2396cfefb361",
            None,
        ),
        "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/agents/openai.yaml": (
            "87d0ec0ac486d5a3cc2d451d0ae1c247cb5455e3",
            None,
        ),
        "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/references/demand-to-capability-profile.md": (
            "e3ac88f8d8e38b6ee673738801962d9ef35149e8",
            "1630f188f5f924fcba7f19b8431b48eac2e4a3ca6d37a5bc99cc1df085d4995a",
        ),
    }
)

_CLAUDE_SKILL_INCREMENT_ID = "increment.v0.2.claude-demand-skill-plugin"
_CLAUDE_SKILL_WORK_ID = "work.v0.2.claude-demand-skill-plugin"
_CLAUDE_SKILL_REGISTRATION = (
    "product/evidence/claude-demand-skill-plugin-registration.json"
)
_CLAUDE_SKILL_REGISTRATION_SHA256 = (
    "67a34f4c83abcc364738816d62bdb84e0130be70ffe3cda15ed167f4ebe3e53d"
)
_CLAUDE_SKILL_BASELINE_COMMIT = "d167bc81a89cfade2739fdc98c4978b4270b4c36"
_CLAUDE_SKILL_REGISTRATION_COMMIT = "3b346c2f2abccae406cf282fcb8a90b778a7636a"
_CLAUDE_SKILL_RESULT_COMMIT = "9d704b948d615ba55b3db9badd300a4ad7ad6541"
_CLAUDE_SKILL_RECEIPT_SHA256 = (
    "26279bc2f93ceb52bb13f6d11155b2de485c6b576381eeac1f5fa5aaef97461e"
)
_CLAUDE_SKILL_SOURCE_IDENTITY = (
    "sha256:5551e40698276d98bd6c0cd8b934f0876453691768e8f8b12816525d4858904f"
)
_CLAUDE_SKILL_ACCEPTANCE_MESSAGE_SHA256 = (
    "a5417defbb630b5e051a37aeb14aa523b2dcf6d6c29c9f4da587ef03dec6efc0"
)
_CLAUDE_SKILL_ACCEPTANCE_RECORD_SHA256 = (
    "268bfa4c52c009551da6cce3e46408cf6590529062b1dbe0aeef5fcfb4111a06"
)
_CLAUDE_SKILL_JUDGMENT_REQUEST_SHA256 = (
    "6371383a66d965ab052c75be1af4c21b5087cf48cc0d1f9fcbbefb3f57b8d3af"
)
_CLAUDE_SKILL_SOURCE_EVENTS = (
    "goal-level-demand-received",
    "registration-committed",
    "registration-pushed",
    "registered-source-route-started",
    "deliverable-committed",
    "deliverable-pushed",
    "bounded-human-judgment-requested",
    "named-human-accepted-source-and-o3-boundary",
)
_CLAUDE_SKILL_RESULT_PATHS = (
    "README.md",
    "README.zh-CN.md",
    "adapters/agent-autonomy-harness-claude/.claude-plugin/plugin.json",
    "adapters/agent-autonomy-harness-claude/scripts/session_start.py",
    "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/SKILL.md",
    "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
    "docs/architecture.md",
    "docs/operations/CONTINUATION.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "harness/claude_reference.py",
    "tests/product/test_product_control.py",
)
_CLAUDE_SKILL_TASK_FILES = MappingProxyType(
    {
        "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/SKILL.md": (
            "e34d2299a9ef6e3abded16b88fab2396cfefb361",
            "e1fd84ac1985672a5bd9a402a8789d8dae296e9ce007f1b1401ff200156404d7",
        ),
        "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/references/demand-to-capability-profile.md": (
            "e3ac88f8d8e38b6ee673738801962d9ef35149e8",
            "1630f188f5f924fcba7f19b8431b48eac2e4a3ca6d37a5bc99cc1df085d4995a",
        ),
        "adapters/agent-autonomy-harness-claude/scripts/session_start.py": (
            "880b69dc5592547da92e87b69bf0d1a35797c0a7",
            "2d5c5e47d89b462d980cbb16e89e13b8523e4b56bb1c1443dd18293edde34652",
        ),
        "harness/claude_reference.py": (
            "528046bdad4138b365c06197751cce2412ee235c",
            "9d70662c5bc33fe0f16a28b7da95123f4277d62933cedfb0caccd5ac147cab2a",
        ),
    }
)
_PUBLIC_INTAKE_RECEIPT = (
    "product/evidence/public-intake-zero-knowledge-accepted-2026-08-14.json"
)
_CODEX_SKILL_RECEIPT = (
    "product/evidence/codex-demand-skill-plugin-accepted-2026-08-14.json"
)
_CONTINUATION_INCREMENT_ID = (
    "increment.v0.2.continuation-reconciliation-projection"
)
_CONTINUATION_WORK_ID = "work.v0.2.continuation-reconciliation-projection"
_CONTINUATION_RECEIPT = (
    "product/evidence/continuation-reconciliation-projection-2026-08-14.json"
)
_CONTINUATION_REGISTRATION = (
    "product/evidence/continuation-reconciliation-projection-registration.json"
)
_CONTINUATION_REGISTRATION_SHA256 = (
    "d809c2107d1ccd8c91284971a05ab47cfd3920ef4688aff39fb27f5e6d244140"
)
_CONTINUATION_BASELINE_COMMIT = "e35a86f7550494b4efbf12f89efc5447f8951920"
_CONTINUATION_REGISTRATION_COMMIT = "19f189341b51147e60b7f48299f0562c35a398ee"
_CONTINUATION_RESULT_COMMIT = "8f3b08502d85b23d4101c8c2550a3954963b1de9"
_CONTINUATION_DECISION_SCOPE_SHA256 = (
    "3a67a213b652c20c3b4fbaf657d06630a28c534b8ae3fec078a60e75fff71850"
)
_CONTINUATION_ACCEPTANCE_MESSAGE_SHA256 = (
    "10f21bea505ccff8000c243554fd132ba131a8125b83b2e5122fa8196a60cda7"
)
_CONTINUATION_PRE_HUMAN_SOURCE_IDENTITY = (
    "sha256:6443578495bd932e6e5b072a4e5bc04e04afad88882a7a88195bfaac18e9d133"
)
_CONTINUATION_SOURCE_EVENTS = (
    "goal-level-context-and-topology-demand-bound",
    "registration-committed-and-pushed",
    "active-work-baseline-measured",
    "deliverable-committed-and-pushed",
    "clean-delivery-reconciliation-verified",
)
_CONTINUATION_RESULT_PATHS = (
    "README.md",
    "README.zh-CN.md",
    "adapters/agent-autonomy-harness-claude/.claude-plugin/plugin.json",
    "adapters/agent-autonomy-harness-claude/scripts/session_start.py",
    "adapters/agent-autonomy-harness-codex/.codex-plugin/plugin.json",
    "adapters/agent-autonomy-harness-codex/scripts/session_start.py",
    "docs/architecture.md",
    "docs/operations/CONTINUATION.md",
    "docs/operations/HISTORY.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "harness/continuation.py",
    "harness/control.py",
    "tests/product/test_product_control.py",
)
_CONTINUATION_TASK_FILES = MappingProxyType(
    {
        "harness/continuation.py": (
            "1b3385200765aa1df92d90193a79883244650e53",
            "7151a0fdfab1703374fdc42871d4dc7b68f68e1dc175238a577240fa2ae80bb7",
        ),
        "harness/control.py": (
            "df2df63294dff153dbebb3524768cfded2029f15",
            "31d4683756f8d380ae3d95fa2b8850cd6aef0b09e743f53606a9d6c27f5ff4d3",
        ),
        "adapters/agent-autonomy-harness-codex/scripts/session_start.py": (
            "fd6f46ec3e7b8c35dc5781aab6ba0b9a105ad22f",
            "b8ef23facd120bf48623b763c39d7333cc308906b1c47ded3d9d0e56645156e0",
        ),
        "adapters/agent-autonomy-harness-claude/scripts/session_start.py": (
            "43b11f82aeee45884e193de9c6b26fd7235b126b",
            "ed834a577108c394e98bcfbfbb2597b443e6b89c5ef6c12ade6e53a0dadc49bc",
        ),
    }
)
_CODEX_CALIBRATION_INCREMENT_ID = "increment.v0.2.codex-reference-calibration"
_CODEX_CALIBRATION_WORK_ID = "work.v0.2.codex-reference-calibration"
_CODEX_CALIBRATION_RECEIPT = (
    "product/evidence/codex-reference-calibration-2026-08-14.json"
)
_CODEX_CALIBRATION_REGISTRATION = (
    "product/evidence/codex-reference-calibration-registration.json"
)
_CODEX_CALIBRATION_REGISTRATION_SHA256 = (
    "01fd3723f35747174d54701affffd7b9211780cdc0d3105c6df0326c8bc815b6"
)
_CODEX_CALIBRATION_REGISTRATION_COMMIT = (
    "31d62d425df813dc76de860646f6a961acad32d3"
)
_CODEX_CALIBRATION_REGISTRATION_PARENT = (
    "29b520d01c1b85da1fd0c8905bba2922fb3e33d0"
)
_CODEX_CALIBRATION_DECISION_SCOPE_SHA256 = (
    "e11a0b8eafe60dda3ab11502c0214c497d016172515a4649465ca356cd6c53b9"
)
_CODEX_CALIBRATION_ACCEPTANCE_MESSAGE_SHA256 = (
    "6309471b550b44accb4853659b421186325c84dd4b8b5a1d9ea9bb4fc05d0d1c"
)
_CODEX_CALIBRATION_INPUT_IDENTITY = (
    "sha256:3c8bc530e65e1d7a6859a9933d73c654e7d0f2279259635756ea0aefeb427ce5"
)
_CODEX_CALIBRATION_PROFILE_BLOB = "e3ac88f8d8e38b6ee673738801962d9ef35149e8"
_CODEX_CALIBRATION_PROFILE_SHA256 = (
    "1630f188f5f924fcba7f19b8431b48eac2e4a3ca6d37a5bc99cc1df085d4995a"
)
_CODEX_CALIBRATION_O4_REGISTERED_SHA256 = (
    "63aa85b31339d988e49dac5932bda292c542bcbb67caa628d01e9c51dbf4a828"
)
_CODEX_CALIBRATION_ACCEPTED_RECEIPTS = MappingProxyType(
    {
        _PUBLIC_INTAKE_RECEIPT: (
            "04ff48d3bb65dcb11bcbe1be41ee4b26ef9b76f34e7019b9b24e0cbda952adb5",
            "natural-task.2026-08-14.public-intake-zero-knowledge",
            "public-support-and-contribution-intake-for-zero-knowledge-users",
            "public-intake-zero-knowledge-o1",
            "O1",
        ),
        _CODEX_SKILL_RECEIPT: (
            "7d8a02d8b54e723d9606c679fcc47f7590a5fdb9301f7c886bfa1364ac95b323",
            "natural-task.2026-08-14.codex-demand-skill-plugin",
            "codex-plugin-skill-reference-adapter-delivery",
            "codex-demand-skill-plugin-o1",
            "O1",
        ),
        _CONTINUATION_RECEIPT: (
            "3754dfe6e1fb8cff7c400e8ad7a1c4bacb2ebcc714f3b08c55a82b9197cae952",
            "natural-task.2026-08-14.continuation-reconciliation-projection",
            "host-neutral-continuation-reconciliation-adapter-implementation",
            "continuation-reconciliation-o2",
            "O2",
        ),
    }
)
_CODEX_CALIBRATION_STOPPED_RECEIPT = (
    "product/evidence/codex-plugin-context-rollover-stopped-2026-08-14.json"
)
_CODEX_CALIBRATION_STOPPED_RECEIPT_SHA256 = (
    "71df89f236f974b22dc44cc59f73ded945b88b4cc9b53ecd0851f35aa5d23173"
)
_CODEX_CALIBRATION_REGISTRATIONS = MappingProxyType(
    {
        "product/evidence/public-intake-zero-knowledge-registration.json": (
            "125397f528f7042b82973a2aa47e6f429bd24d4b85ceeb29e7baa1c334c0a89f",
            "public-support-and-contribution-intake-for-zero-knowledge-users",
        ),
        "product/evidence/codex-demand-skill-plugin-registration.json": (
            "16e737b569c41f5b7f2c847d67bb70c2eb7ca0491481fec7c533a498d4051824",
            "codex-plugin-skill-reference-adapter-delivery",
        ),
        _CONTINUATION_REGISTRATION: (
            _CONTINUATION_REGISTRATION_SHA256,
            "host-neutral-continuation-reconciliation-adapter-implementation",
        ),
        "product/evidence/codex-plugin-context-rollover-registration.json": (
            "b44bebeed83d629f6716d5e4d424195dd10c42564af2a8936fc7c41fbb018f29",
            "long-horizon-software-product-continuity-through-agent-owned-conversation-rollover",
        ),
    }
)
_CODEX_CALIBRATION_CANONICAL_SOURCE_VALUES = MappingProxyType(
    {
        "referenceHostProfileAndEligibleReceiptSet": (
            "036a697e6eda36e250bc1e037d4f14fc4f01fa4481d359dc4fe5b094b43a60e3"
        ),
        "externalSubstrateCohortSourcesVersionsLicensesOrTermsMaturityAndReuseBoundaries": (
            "6fe3e3f056addc663b1c6784df405a3ad56027bfc36b569933c8a93f874ecea3"
        ),
        "outcomeComparatorCohortSourcesVersionsLicensesOrTermsMaturityEligibilityAndMatchingRules": (
            "563967495af6d8400f8c4a1f6ae5f983f866a2f2aad953569a23d75cbdfe00c9"
        ),
        "comparatorBaselineResultsComparisonAxesAndDecisionRule": (
            "d4f23577da4f57828a49fe1c1bf5950a677811de5a2bd744767c06549be30f24"
        ),
        "mandatoryFloorsAndMissingDataRules": (
            "4d152c2ed10be2a22073c0514d473d2306be3723f55017e541319c2207ce705b"
        ),
    }
)
_EVIDENCE_GIT_CACHE: ContextVar[
    dict[tuple[str, tuple[str, ...]], bytes | None] | None
] = ContextVar("harness_evidence_git_cache", default=None)


def _evidence_git(root: Path, *arguments: str) -> bytes | None:
    cache = _EVIDENCE_GIT_CACHE.get()
    key = (str(root.resolve(strict=False)), arguments)
    if cache is not None and key in cache:
        return cache[key]
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        result = None
    else:
        result = completed.stdout if completed.returncode == 0 else None
    if cache is not None:
        cache[key] = result
    return result


def _validate_public_intake_o1(
    document: dict[str, Any], criterion_id: str, root: Path, errors: list[str]
) -> bool:
    """Validate only the observed public-intake task against its frozen sources."""

    before = len(errors)

    def reject(message: str) -> None:
        _error(errors, f"public-intake O1 evidence {message}")

    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    if hashlib.sha256(canonical).hexdigest() != _PUBLIC_INTAKE_RECEIPT_SHA256:
        reject("serialization differs from the observed task receipt")
        return False

    if (
        criterion_id != "O1"
        or document["incrementId"] != _PUBLIC_INTAKE_INCREMENT_ID
        or document["workItemId"] != _PUBLIC_INTAKE_WORK_ID
        or document["source"]["identity"] != _PUBLIC_INTAKE_SOURCE_IDENTITY
        or document["authority"]["name"] != "yiheng8023"
        or document["authority"]["sourceMessageSha256"]
        != _PUBLIC_INTAKE_ACCEPTANCE_MESSAGE_SHA256
        or hashlib.sha256("认可。\n".encode()).hexdigest()
        != _PUBLIC_INTAKE_ACCEPTANCE_MESSAGE_SHA256
    ):
        reject("criterion, task source, or named-human decision identity changed")

    records = document["sourceRecords"]
    if tuple(item["event"] for item in records) != _PUBLIC_INTAKE_SOURCE_EVENTS:
        reject("source chronology events changed")
    instants = [_rfc3339_instant(item["observedAt"]) for item in records]
    if any(item is None for item in instants) or instants != sorted(instants):
        reject("source chronology is not ordered")
    if any(
        not item["locator"].startswith(
            "codex://threads/019ffaa8-b44a-7bf2-97de-65875bceec33/"
        )
        for item in records
    ):
        reject("source chronology left the bound task")
    identities = [item["identity"].removeprefix("sha256:") for item in records]
    combined = hashlib.sha256(("\n".join(identities) + "\n").encode()).hexdigest()
    if document["source"]["identity"] != f"sha256:{combined}":
        reject("source chronology identity changed")

    measures = document["measures"]
    orchestration = measures["materialUserCapabilityOrchestrationInterventions"]
    losses = measures["materialCollaborationLossEvents"]
    repeats = measures["repeatedAlreadyBoundRequests"]
    context = measures["contextCarrierFitnessObservationsAndTransitions"]
    topology = measures["taskTopologyLifecycleEvents"]
    floors = measures["taskFloorResults"]
    residue = measures["residueAndClaimLimits"]
    floor_names = {
        "outcomeQuality",
        "intentAndCompleteness",
        "interfaceSimplicity",
        "authorityAndSafety",
        "scope",
        "evidence",
        "residue",
    }
    if (
        orchestration["count"] != 0
        or orchestration["taskTopologyInterventions"] != 0
        or losses["count"] != 0
        or losses["repeatedSameClassCorrections"] != 0
        or repeats["count"] != 0
    ):
        reject("zero user-intervention or collaboration-loss floor changed")
    if (
        context["reliableRemainingCapacitySignal"] != "unknown"
        or context["transition"]
        != "one native compaction at 2026-08-14T00:56:49.178Z"
        or context["preventableContextLoss"] is not False
        or topology["isolatedCarrierCreated"] is not False
        or topology["userTopologyOperationCount"] != 0
        or topology["codeCarrier"] != "existing main checkout retained"
    ):
        reject("context-carrier or task-topology lifecycle changed")
    if (
        any(floors[name] != "pass" for name in floor_names)
        or floors["missingData"] != []
        or any(
            residue[name] != []
            for name in (
                "repositoryTemporaryResidue",
                "externalWritesBeyondAuthorizedGitPush",
                "consumerOrHostMutation",
                "remainingTaskScopedExposure",
            )
        )
    ):
        reject("a mandatory quality, safety, evidence, or residue floor failed")
    if len(measures["selectedRouteSubstrates"]) != 4 or set(
        measures["capabilityLifecycleEvents"]
    ) != {"observation", "gapAssessment", "discovery", "dispatch", "release"}:
        reject("capability lifecycle or substrate binding is incomplete")
    claims = document["claimLimits"]
    if (
        len(claims) != 5
        or not any("does not itself verify O2 or O4" in item for item in claims)
        or not any("does not verify repeated burden transfer" in item for item in claims)
    ):
        reject("claim limits changed or broadened")

    registration_path = root / _PUBLIC_INTAKE_REGISTRATION
    try:
        registration_raw = registration_path.read_bytes()
    except OSError:
        registration_raw = None
    if (
        registration_raw is None
        or hashlib.sha256(registration_raw).hexdigest()
        != _PUBLIC_INTAKE_REGISTRATION_SHA256
    ):
        reject("registration bytes changed")

    registration_parent = _evidence_git(
        root, "rev-parse", f"{_PUBLIC_INTAKE_REGISTRATION_COMMIT}^"
    )
    result_parent = _evidence_git(
        root, "rev-parse", f"{_PUBLIC_INTAKE_RESULT_COMMIT}^"
    )
    committed_registration = _evidence_git(
        root,
        "show",
        f"{_PUBLIC_INTAKE_REGISTRATION_COMMIT}:{_PUBLIC_INTAKE_REGISTRATION}",
    )
    committed_program = _evidence_git(
        root, "show", f"{_PUBLIC_INTAKE_REGISTRATION_COMMIT}:product/program.json"
    )
    result_is_ancestor = _evidence_git(
        root, "merge-base", "--is-ancestor", _PUBLIC_INTAKE_RESULT_COMMIT, "HEAD"
    )
    if (
        registration_parent is None
        or registration_parent.decode().strip() != _PUBLIC_INTAKE_BASELINE_COMMIT
        or result_parent is None
        or result_parent.decode().strip() != _PUBLIC_INTAKE_REGISTRATION_COMMIT
        or committed_registration is None
        or hashlib.sha256(committed_registration).hexdigest()
        != _PUBLIC_INTAKE_REGISTRATION_SHA256
        or result_is_ancestor is None
    ):
        reject("Git registration-to-result chronology changed")

    if committed_program is None:
        reject("committed active registration binding is unavailable")
    else:
        try:
            registered_program = _parse_json(committed_program.decode())
            registered_increment = next(
                item
                for item in registered_program["increments"]
                if item.get("id") == _PUBLIC_INTAKE_INCREMENT_ID
            )
        except (KeyError, StopIteration, UnicodeDecodeError, _InvalidJson, TypeError):
            reject("committed active registration binding is invalid")
        else:
            if (
                registered_program.get("status") != "active"
                or registered_program.get("activeIncrementId")
                != _PUBLIC_INTAKE_INCREMENT_ID
                or registered_increment.get("state") != "active"
                or registered_increment.get("taskRegistration")
                != {
                    "locator": _PUBLIC_INTAKE_REGISTRATION,
                    "sha256": _PUBLIC_INTAKE_REGISTRATION_SHA256,
                }
            ):
                reject("registration was not active before the result commit")

    changed_paths = _evidence_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        _PUBLIC_INTAKE_RESULT_COMMIT,
    )
    if changed_paths is None or changed_paths.decode().splitlines() != list(
        _PUBLIC_INTAKE_DOCUMENTS
    ):
        reject("result commit is not scoped to the three registered documents")
    scoped_diff = _evidence_git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-color",
        _PUBLIC_INTAKE_BASELINE_COMMIT,
        _PUBLIC_INTAKE_RESULT_COMMIT,
        "--",
        *_PUBLIC_INTAKE_DOCUMENTS,
    )
    if (
        scoped_diff is None
        or hashlib.sha256(scoped_diff).hexdigest()
        != document["artifacts"]["scopedDiffSha256"]
    ):
        reject("scoped result diff changed")

    for path, expected in _PUBLIC_INTAKE_DOCUMENTS.items():
        baseline_blob, result_blob, result_sha256, old_phrase, new_phrase, safety = (
            expected
        )
        baseline_identity = _evidence_git(
            root, "rev-parse", f"{_PUBLIC_INTAKE_BASELINE_COMMIT}:{path}"
        )
        result_identity = _evidence_git(
            root, "rev-parse", f"{_PUBLIC_INTAKE_RESULT_COMMIT}:{path}"
        )
        baseline_bytes = _evidence_git(
            root, "show", f"{_PUBLIC_INTAKE_BASELINE_COMMIT}:{path}"
        )
        result_bytes = _evidence_git(
            root, "show", f"{_PUBLIC_INTAKE_RESULT_COMMIT}:{path}"
        )
        try:
            current_bytes = (root / path).read_bytes()
        except OSError:
            current_bytes = None
        if (
            baseline_identity is None
            or baseline_identity.decode().strip() != baseline_blob
            or result_identity is None
            or result_identity.decode().strip() != result_blob
            or baseline_bytes is None
            or old_phrase.encode() not in baseline_bytes
            or result_bytes is None
            or old_phrase.encode() in result_bytes
            or new_phrase.encode() not in result_bytes
            or safety.encode() not in result_bytes
            or hashlib.sha256(result_bytes).hexdigest() != result_sha256
            or current_bytes != result_bytes
        ):
            reject(f"baseline or accepted document content changed: {path}")

    return len(errors) == before


def _validate_codex_skill_o1(
    document: dict[str, Any], criterion_id: str, root: Path, errors: list[str]
) -> bool:
    """Validate only the observed Codex Skill source task and bounded decision."""

    before = len(errors)

    def reject(message: str) -> None:
        _error(errors, f"Codex Skill O1 evidence {message}")

    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    if hashlib.sha256(canonical).hexdigest() != _CODEX_SKILL_RECEIPT_SHA256:
        reject("serialization differs from the observed task receipt")
        return False

    authority = document["authority"]
    result = document["result"]
    if (
        criterion_id != "O1"
        or document["incrementId"] != _CODEX_SKILL_INCREMENT_ID
        or document["workItemId"] != _CODEX_SKILL_WORK_ID
        or document["taskIdentity"]
        != "natural-task.2026-08-14.codex-demand-skill-plugin"
        or document["source"]["identity"] != _CODEX_SKILL_SOURCE_IDENTITY
        or authority["name"] != "yiheng8023"
        or authority["sourceThreadId"]
        != "019ffaa8-b44a-7bf2-97de-65875bceec33"
        or authority["sourceMessageId"]
        != "msg_019ffe0c-2d1e-7cd2-96d4-caf5be0e94bb"
        or authority["sourceMessageSha256"]
        != _CODEX_SKILL_ACCEPTANCE_MESSAGE_SHA256
        or authority["sourceRecordSha256"]
        != _CODEX_SKILL_ACCEPTANCE_RECORD_SHA256
        or authority["responseToMessageSha256"]
        != _CODEX_SKILL_JUDGMENT_REQUEST_SHA256
        or hashlib.sha256("认可。\n".encode()).hexdigest()
        != _CODEX_SKILL_ACCEPTANCE_MESSAGE_SHA256
        or result["deliverableCommit"] != _CODEX_SKILL_RESULT_COMMIT
        or result["accepted"] is not True
    ):
        reject("criterion, task source, result, or named-human decision changed")

    records = document["sourceRecords"]
    if tuple(item["event"] for item in records) != _CODEX_SKILL_SOURCE_EVENTS:
        reject("source chronology events changed")
    instants = [_rfc3339_instant(item["observedAt"]) for item in records]
    if any(item is None for item in instants) or instants != sorted(instants):
        reject("source chronology is not ordered")
    if any(
        not item["locator"].startswith(
            "codex://threads/019ffaa8-b44a-7bf2-97de-65875bceec33/"
        )
        for item in records
    ):
        reject("source chronology left the bound task")
    identities = [item["identity"].removeprefix("sha256:") for item in records]
    combined = hashlib.sha256(("\n".join(identities) + "\n").encode()).hexdigest()
    if document["source"]["identity"] != f"sha256:{combined}":
        reject("source chronology identity changed")

    measures = document["measures"]
    orchestration = measures["materialUserCapabilityOrchestrationInterventions"]
    losses = measures["materialCollaborationLossEvents"]
    process_noise = losses["nonMaterialHostGoalProcessNoise"]
    repeats = measures["repeatedAlreadyBoundRequests"]
    context = measures["contextCarrierFitnessObservationsAndTransitions"]
    topology = measures["taskTopologyLifecycleEvents"]
    floors = measures["taskFloorResults"]
    residue = measures["residueAndClaimLimits"]
    floor_names = {
        "outcomeQuality",
        "intentAndCompleteness",
        "interfaceSimplicity",
        "authorityAndSafety",
        "scope",
        "minimality",
        "packageIntegrity",
        "evidence",
        "residue",
    }
    if (
        orchestration["count"] != 0
        or orchestration["taskTopologyInterventions"] != 0
        or losses["count"] != 0
        or losses["repeatedSameClassCorrections"] != 0
        or repeats["count"] != 0
    ):
        reject("zero user-intervention or material collaboration-loss floor changed")
    if (
        process_noise["count"] != 1
        or process_noise["visibleAssistantMessagesAfterJudgmentRequest"] != 4
        or process_noise["automaticFinalReminders"] != 2
        or process_noise["temporaryGoalBlocked"] is not True
        or process_noise["additionalHumanInputsOrActionsBeyondRegisteredJudgment"]
        != 0
        or "not evidence of product value" not in process_noise["classification"]
    ):
        reject("observed host goal-mode process cost was hidden or reclassified")
    if (
        context["reliableRemainingCapacitySignal"] != "unknown"
        or context["transition"]
        != "one native compaction at 2026-08-14T02:01:32.757Z"
        or context["preventableContextLoss"] is not False
        or topology["isolatedCarrierCreated"] is not False
        or topology["userTopologyOperationCount"] != 0
        or topology["codeCarrier"] != "existing main checkout retained"
    ):
        reject("context-carrier or task-topology lifecycle changed")
    if (
        set(floors) != floor_names | {"missingData"}
        or any(floors[name] != "pass" for name in floor_names)
        or floors["missingData"] != []
        or any(
            residue[name] != []
            for name in (
                "repositoryTemporaryResidue",
                "externalWritesBeyondAuthorizedGitPush",
                "consumerOrHostMutation",
                "remainingTaskScopedExposure",
            )
        )
    ):
        reject("a mandatory quality, safety, package, evidence, or residue floor failed")
    if len(measures["selectedRouteSubstrates"]) != 6 or set(
        measures["capabilityLifecycleEvents"]
    ) != {"observation", "gapAssessment", "discovery", "dispatch", "release"}:
        reject("capability lifecycle or substrate binding is incomplete")
    claims = document["claimLimits"]
    if (
        len(claims) != 6
        or not any("does not itself verify O2 or O4" in item for item in claims)
        or not any("goal-mode continuation noise" in item for item in claims)
        or not any("does not verify live Skill triggering" in item for item in claims)
    ):
        reject("claim limits changed or broadened")

    try:
        registration_raw = (root / _CODEX_SKILL_REGISTRATION).read_bytes()
    except OSError:
        registration_raw = None
    if (
        registration_raw is None
        or hashlib.sha256(registration_raw).hexdigest()
        != _CODEX_SKILL_REGISTRATION_SHA256
    ):
        reject("registration bytes changed")

    registration_parent = _evidence_git(
        root, "rev-parse", f"{_CODEX_SKILL_REGISTRATION_COMMIT}^"
    )
    result_parent = _evidence_git(root, "rev-parse", f"{_CODEX_SKILL_RESULT_COMMIT}^")
    committed_registration = _evidence_git(
        root,
        "show",
        f"{_CODEX_SKILL_REGISTRATION_COMMIT}:{_CODEX_SKILL_REGISTRATION}",
    )
    committed_program = _evidence_git(
        root, "show", f"{_CODEX_SKILL_REGISTRATION_COMMIT}:product/program.json"
    )
    result_is_ancestor = _evidence_git(
        root, "merge-base", "--is-ancestor", _CODEX_SKILL_RESULT_COMMIT, "HEAD"
    )
    if (
        registration_parent is None
        or registration_parent.decode().strip() != _CODEX_SKILL_BASELINE_COMMIT
        or result_parent is None
        or result_parent.decode().strip() != _CODEX_SKILL_REGISTRATION_COMMIT
        or committed_registration is None
        or hashlib.sha256(committed_registration).hexdigest()
        != _CODEX_SKILL_REGISTRATION_SHA256
        or result_is_ancestor is None
    ):
        reject("Git registration-to-result chronology changed")

    if committed_program is None:
        reject("committed active registration binding is unavailable")
    else:
        try:
            registered_program = _parse_json(committed_program.decode())
            registered_increment = next(
                item
                for item in registered_program["increments"]
                if item.get("id") == _CODEX_SKILL_INCREMENT_ID
            )
        except (KeyError, StopIteration, UnicodeDecodeError, _InvalidJson, TypeError):
            reject("committed active registration binding is invalid")
        else:
            if (
                registered_program.get("status") != "active"
                or registered_program.get("activeIncrementId")
                != _CODEX_SKILL_INCREMENT_ID
                or registered_increment.get("state") != "active"
                or registered_increment.get("taskRegistration")
                != {
                    "locator": _CODEX_SKILL_REGISTRATION,
                    "sha256": _CODEX_SKILL_REGISTRATION_SHA256,
                }
            ):
                reject("registration was not active before the result commit")

    changed_paths = _evidence_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        _CODEX_SKILL_RESULT_COMMIT,
    )
    if changed_paths is None or tuple(changed_paths.decode().splitlines()) != (
        _CODEX_SKILL_RESULT_PATHS
    ):
        reject("result commit changed paths differ from the registered source task")
    scoped_diff = _evidence_git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-color",
        _CODEX_SKILL_BASELINE_COMMIT,
        _CODEX_SKILL_RESULT_COMMIT,
        "--",
        *_CODEX_SKILL_RESULT_PATHS,
    )
    if (
        scoped_diff is None
        or hashlib.sha256(scoped_diff).hexdigest()
        != document["artifacts"]["scopedDiffSha256"]
    ):
        reject("scoped result diff changed")

    baseline_tree = _evidence_git(
        root,
        "rev-parse",
        f"{_CODEX_SKILL_BASELINE_COMMIT}:adapters/agent-autonomy-harness-codex",
    )
    baseline_manifest = _evidence_git(
        root,
        "rev-parse",
        f"{_CODEX_SKILL_BASELINE_COMMIT}:adapters/agent-autonomy-harness-codex/.codex-plugin/plugin.json",
    )
    result_tree = _evidence_git(
        root,
        "rev-parse",
        f"{_CODEX_SKILL_RESULT_COMMIT}:adapters/agent-autonomy-harness-codex",
    )
    result_manifest_identity = _evidence_git(
        root,
        "rev-parse",
        f"{_CODEX_SKILL_RESULT_COMMIT}:adapters/agent-autonomy-harness-codex/.codex-plugin/plugin.json",
    )
    result_manifest_bytes = _evidence_git(
        root,
        "show",
        f"{_CODEX_SKILL_RESULT_COMMIT}:adapters/agent-autonomy-harness-codex/.codex-plugin/plugin.json",
    )
    if (
        baseline_tree is None
        or baseline_tree.decode().strip() != "5af87a619fbd8a020f2751eafa3cc4a8dedf002d"
        or baseline_manifest is None
        or baseline_manifest.decode().strip()
        != "08c5b063e3f03e00b5dc4df5cbab910344710bce"
        or result_tree is None
        or result_tree.decode().strip() != "3cf400757dd74c1a6bac01bbf88337572934ffa3"
        or result_manifest_identity is None
        or result_manifest_identity.decode().strip()
        != "9cd4115bad162255741848969db0d345b4c60461"
        or result_manifest_bytes is None
    ):
        reject("baseline or result plugin identity changed")
    else:
        try:
            result_manifest = _parse_json(result_manifest_bytes.decode())
        except (UnicodeDecodeError, _InvalidJson, TypeError):
            reject("result plugin manifest is invalid")
        else:
            if (
                result_manifest.get("version")
                != "0.2.0-candidate.2+codex.payload-69031aa1e26c"
                or result_manifest.get("skills") != "./skills/"
                or any(
                    field in result_manifest for field in ("mcpServers", "apps", "hooks")
                )
            ):
                reject("result plugin manifest boundary changed")

    for path, expected in _CODEX_SKILL_TASK_FILES.items():
        result_blob, result_sha256 = expected
        result_identity = _evidence_git(
            root, "rev-parse", f"{_CODEX_SKILL_RESULT_COMMIT}:{path}"
        )
        result_bytes = _evidence_git(
            root, "show", f"{_CODEX_SKILL_RESULT_COMMIT}:{path}"
        )
        try:
            current_bytes = (root / path).read_bytes()
        except OSError:
            current_bytes = None
        if (
            result_identity is None
            or result_identity.decode().strip() != result_blob
            or result_bytes is None
            or current_bytes != result_bytes
            or (
                result_sha256 is not None
                and hashlib.sha256(result_bytes).hexdigest() != result_sha256
            )
        ):
            reject(f"accepted task-facing source changed: {path}")

    profile_path = (
        root
        / "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/"
        "references/demand-to-capability-profile.md"
    )
    try:
        if profile_path.read_bytes() != (
            root / "docs/DEMAND-TO-CAPABILITY-PROFILE.md"
        ).read_bytes():
            reject("projected profile is not byte-identical to the registered profile")
    except OSError:
        reject("projected or registered profile is unavailable")

    return len(errors) == before


def _validate_claude_skill_o1_o3(
    document: dict[str, Any], criterion_id: str, root: Path, errors: list[str]
) -> bool:
    """Validate the observed Claude source result and its exact O3 route cohort."""

    before = len(errors)

    def reject(message: str) -> None:
        _error(errors, f"Claude Skill {criterion_id} evidence {message}")

    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    if hashlib.sha256(canonical).hexdigest() != _CLAUDE_SKILL_RECEIPT_SHA256:
        reject("serialization differs from the observed task receipt")
        return False

    authority = document["authority"]
    result = document["result"]
    if (
        criterion_id not in {"O1", "O3"}
        or document["criterionIds"] != ["O1", "O3"]
        or document["incrementId"] != _CLAUDE_SKILL_INCREMENT_ID
        or document["workItemId"] != _CLAUDE_SKILL_WORK_ID
        or document["taskIdentity"]
        != "natural-task.2026-08-14.claude-demand-skill-plugin"
        or document["source"]["identity"] != _CLAUDE_SKILL_SOURCE_IDENTITY
        or authority["name"] != "yiheng8023"
        or authority["sourceThreadId"]
        != "019ffaa8-b44a-7bf2-97de-65875bceec33"
        or authority["sourceTurnId"]
        != "616cab65-9517-46e7-8676-a9a528423833"
        or authority["sourceMessageId"]
        != "msg_019ffe8c-a9a8-7fa0-8033-a486fa053e4f"
        or authority["sourceMessageSha256"]
        != _CLAUDE_SKILL_ACCEPTANCE_MESSAGE_SHA256
        or authority["sourceRecordSha256"]
        != _CLAUDE_SKILL_ACCEPTANCE_RECORD_SHA256
        or authority["responseToMessageSha256"]
        != _CLAUDE_SKILL_JUDGMENT_REQUEST_SHA256
        or hashlib.sha256("认可。\n".encode()).hexdigest()
        != _CLAUDE_SKILL_ACCEPTANCE_MESSAGE_SHA256
        or result["deliverableCommit"] != _CLAUDE_SKILL_RESULT_COMMIT
        or result["accepted"] is not True
        or "explicitly rejecting material-distinction credit for O2"
        not in result["humanJudgment"]
    ):
        reject("criterion, task source, result, or named-human decision changed")

    records = document["sourceRecords"]
    if tuple(item["event"] for item in records) != _CLAUDE_SKILL_SOURCE_EVENTS:
        reject("source chronology events changed")
    instants = [_rfc3339_instant(item["observedAt"]) for item in records]
    if any(item is None for item in instants) or instants != sorted(instants):
        reject("source chronology is not ordered")
    if any(
        not item["locator"].startswith(
            "codex://threads/019ffaa8-b44a-7bf2-97de-65875bceec33/"
        )
        for item in records
    ):
        reject("source chronology left the bound task")
    identities = [item["identity"].removeprefix("sha256:") for item in records]
    combined = hashlib.sha256(("\n".join(identities) + "\n").encode()).hexdigest()
    if document["source"]["identity"] != f"sha256:{combined}":
        reject("source chronology identity changed")

    measures = document["measures"]
    orchestration = measures["materialUserCapabilityOrchestrationInterventions"]
    losses = measures["materialCollaborationLossEvents"]
    process_noise = losses["nonMaterialHostGoalProcessNoise"]
    context = measures["contextCarrierFitnessObservationsAndTransitions"]
    topology = measures["taskTopologyLifecycleEvents"]
    floors = measures["taskFloorResults"]
    residue = measures["residueAndClaimLimits"]
    floor_names = {
        "outcomeQuality",
        "intentAndCompleteness",
        "interfaceSimplicity",
        "authorityAndSafety",
        "scope",
        "minimality",
        "packageIntegrity",
        "evidence",
        "residue",
    }
    if (
        orchestration["count"] != 0
        or orchestration["taskTopologyInterventions"] != 0
        or losses["count"] != 0
        or losses["repeatedSameClassCorrections"] != 0
        or measures["repeatedAlreadyBoundRequests"]["count"] != 0
    ):
        reject("zero user-intervention or material collaboration-loss floor changed")
    if (
        process_noise["count"] != 1
        or process_noise["visibleAssistantMessagesAfterJudgmentRequest"] != 1
        or process_noise["automaticGoalContinuations"] != 1
        or process_noise["temporaryGoalBlocked"] is not False
        or process_noise["additionalHumanInputsOrActionsBeyondRegisteredJudgment"]
        != 0
        or "not evidence of product value" not in process_noise["classification"]
    ):
        reject("observed host goal-mode process cost was hidden or reclassified")
    if (
        context["reliableRemainingCapacitySignal"] != "unknown"
        or not context["transition"].startswith("none during this registered")
        or context["preventableContextLoss"] is not False
        or topology["isolatedCarrierCreated"] is not False
        or topology["userTopologyOperationCount"] != 0
        or topology["codeCarrier"] != "existing main checkout retained"
    ):
        reject("context-carrier or task-topology lifecycle changed")
    if (
        set(floors) != floor_names | {"missingData"}
        or any(floors[name] != "pass" for name in floor_names)
        or floors["missingData"] != []
        or any(
            residue[name] != []
            for name in (
                "repositoryTemporaryResidue",
                "externalWritesBeyondAuthorizedGitPush",
                "consumerOrHostMutation",
                "remainingTaskScopedExposure",
            )
        )
    ):
        reject("a mandatory quality, safety, package, evidence, or residue floor failed")
    validation = measures["validationResults"]
    if (
        len(measures["selectedRouteSubstrates"]) != 7
        or set(measures["capabilityLifecycleEvents"])
        != {"observation", "gapAssessment", "discovery", "dispatch", "release"}
        or validation["commonSkillQuickValidation"] != "pass"
        or validation["claudeStrictPluginValidation"] != "pass"
        or validation["canonicalVerifier"] != "valid=true"
        or validation["fullProductTests"] != "143/143 PASS"
        or validation["commonSkillBytesSha256"]
        != "e1fd84ac1985672a5bd9a402a8789d8dae296e9ce007f1b1401ff200156404d7"
        or validation["commonProfileBytesSha256"]
        != "1630f188f5f924fcba7f19b8431b48eac2e4a3ca6d37a5bc99cc1df085d4995a"
    ):
        reject("capability lifecycle, substrate binding, or validation record changed")
    claims = document["claimLimits"]
    if (
        len(claims) != 6
        or not any("too similar to count as materially different O2" in item for item in claims)
        or not any("does not verify O2 or O4" in item for item in claims)
        or not any("no installed or enabled Claude behavior" in item for item in claims)
    ):
        reject("claim limits changed or broadened")

    try:
        registration_raw = (root / _CLAUDE_SKILL_REGISTRATION).read_bytes()
    except OSError:
        registration_raw = None
    if (
        registration_raw is None
        or hashlib.sha256(registration_raw).hexdigest()
        != _CLAUDE_SKILL_REGISTRATION_SHA256
    ):
        reject("registration bytes changed")

    registration_parent = _evidence_git(
        root, "rev-parse", f"{_CLAUDE_SKILL_REGISTRATION_COMMIT}^"
    )
    result_parent = _evidence_git(root, "rev-parse", f"{_CLAUDE_SKILL_RESULT_COMMIT}^")
    committed_registration = _evidence_git(
        root,
        "show",
        f"{_CLAUDE_SKILL_REGISTRATION_COMMIT}:{_CLAUDE_SKILL_REGISTRATION}",
    )
    committed_program = _evidence_git(
        root, "show", f"{_CLAUDE_SKILL_REGISTRATION_COMMIT}:product/program.json"
    )
    result_is_ancestor = _evidence_git(
        root, "merge-base", "--is-ancestor", _CLAUDE_SKILL_RESULT_COMMIT, "HEAD"
    )
    if (
        registration_parent is None
        or registration_parent.decode().strip() != _CLAUDE_SKILL_BASELINE_COMMIT
        or result_parent is None
        or result_parent.decode().strip() != _CLAUDE_SKILL_REGISTRATION_COMMIT
        or committed_registration is None
        or hashlib.sha256(committed_registration).hexdigest()
        != _CLAUDE_SKILL_REGISTRATION_SHA256
        or result_is_ancestor is None
    ):
        reject("Git registration-to-result chronology changed")

    if committed_program is None:
        reject("committed active registration binding is unavailable")
    else:
        try:
            registered_program = _parse_json(committed_program.decode())
            registered_increment = next(
                item
                for item in registered_program["increments"]
                if item.get("id") == _CLAUDE_SKILL_INCREMENT_ID
            )
        except (KeyError, StopIteration, UnicodeDecodeError, _InvalidJson, TypeError):
            reject("committed active registration binding is invalid")
        else:
            if (
                registered_program.get("status") != "active"
                or registered_program.get("activeIncrementId")
                != _CLAUDE_SKILL_INCREMENT_ID
                or registered_increment.get("state") != "active"
                or registered_increment.get("taskRegistration")
                != {
                    "locator": _CLAUDE_SKILL_REGISTRATION,
                    "sha256": _CLAUDE_SKILL_REGISTRATION_SHA256,
                }
            ):
                reject("registration was not active before the result commit")

    changed_paths = _evidence_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        _CLAUDE_SKILL_RESULT_COMMIT,
    )
    if changed_paths is None or tuple(changed_paths.decode().splitlines()) != (
        _CLAUDE_SKILL_RESULT_PATHS
    ):
        reject("result commit changed paths differ from the registered source task")
    scoped_diff = _evidence_git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-color",
        _CLAUDE_SKILL_BASELINE_COMMIT,
        _CLAUDE_SKILL_RESULT_COMMIT,
        "--",
        *_CLAUDE_SKILL_RESULT_PATHS,
    )
    if (
        scoped_diff is None
        or hashlib.sha256(scoped_diff).hexdigest()
        != document["artifacts"]["scopedDiffSha256"]
    ):
        reject("scoped result diff changed")

    expected_plugin_identities = (
        (f"{_CLAUDE_SKILL_BASELINE_COMMIT}:adapters/agent-autonomy-harness-claude", "0ac34b8ae516d5a9485f81cf5daa660c65994d23"),
        (f"{_CLAUDE_SKILL_BASELINE_COMMIT}:adapters/agent-autonomy-harness-claude/.claude-plugin/plugin.json", "769d4d090577518c5b6f4143167ac77c9f69daa4"),
        (f"{_CLAUDE_SKILL_RESULT_COMMIT}:adapters/agent-autonomy-harness-claude", "298fc3d90d18dffc754251d3825bcecd18ad1001"),
        (f"{_CLAUDE_SKILL_RESULT_COMMIT}:adapters/agent-autonomy-harness-claude/.claude-plugin/plugin.json", "53f8764a30821ee2ab126e5648b4292a766792fd"),
    )
    for locator, expected_identity in expected_plugin_identities:
        identity = _evidence_git(root, "rev-parse", locator)
        if identity is None or identity.decode().strip() != expected_identity:
            reject(f"plugin identity changed: {locator}")

    manifest_bytes = _evidence_git(
        root,
        "show",
        f"{_CLAUDE_SKILL_RESULT_COMMIT}:adapters/agent-autonomy-harness-claude/.claude-plugin/plugin.json",
    )
    if manifest_bytes is None:
        reject("result plugin manifest is unavailable")
    else:
        try:
            manifest = _parse_json(manifest_bytes.decode())
        except (UnicodeDecodeError, _InvalidJson, TypeError):
            reject("result plugin manifest is invalid")
        else:
            if (
                manifest.get("version")
                != "0.2.0-candidate.2+claude.payload-523b4e76b034"
                or manifest.get("license") != "Apache-2.0"
                or any(field in manifest for field in ("mcpServers", "apps", "agents"))
            ):
                reject("result plugin manifest boundary changed")

    for path, expected in _CLAUDE_SKILL_TASK_FILES.items():
        result_blob, result_sha256 = expected
        result_identity = _evidence_git(
            root, "rev-parse", f"{_CLAUDE_SKILL_RESULT_COMMIT}:{path}"
        )
        result_bytes = _evidence_git(root, "show", f"{_CLAUDE_SKILL_RESULT_COMMIT}:{path}")
        try:
            current_bytes = (root / path).read_bytes()
        except OSError:
            current_bytes = None
        if (
            result_identity is None
            or result_identity.decode().strip() != result_blob
            or result_bytes is None
            or (
                path
                != "adapters/agent-autonomy-harness-claude/scripts/session_start.py"
                and current_bytes != result_bytes
            )
            or hashlib.sha256(result_bytes).hexdigest() != result_sha256
        ):
            reject(f"accepted task-facing source changed: {path}")

    common_pairs = (
        (
            "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/SKILL.md",
            "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/SKILL.md",
        ),
        (
            "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
            "docs/DEMAND-TO-CAPABILITY-PROFILE.md",
        ),
        (
            "adapters/agent-autonomy-harness-claude/skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
            "adapters/agent-autonomy-harness-codex/skills/deliver-demand-driven-task/references/demand-to-capability-profile.md",
        ),
    )
    for left, right in common_pairs:
        try:
            if (root / left).read_bytes() != (root / right).read_bytes():
                reject(f"common source bytes diverged: {left} != {right}")
        except OSError:
            reject(f"common source is unavailable: {left} or {right}")

    if criterion_id == "O3":
        prior_documents: list[dict[str, Any]] = []
        for relative, validator in (
            (_PUBLIC_INTAKE_RECEIPT, _validate_public_intake_o1),
            (_CODEX_SKILL_RECEIPT, _validate_codex_skill_o1),
        ):
            try:
                prior = _parse_json((root / relative).read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, _InvalidJson, TypeError):
                reject(f"prior accepted route receipt is unavailable or invalid: {relative}")
                continue
            if validator(prior, "O1", root, errors) is not True:
                reject(f"prior route receipt no longer passes its task validator: {relative}")
            prior_documents.append(prior)

        routes = measures["availableCapabilityAndGapResult"]
        expected_routes = (
            (
                "natural-task.2026-08-14.public-intake-zero-knowledge",
                "no-gap-retain-native",
            ),
            (
                "natural-task.2026-08-14.codex-demand-skill-plugin",
                "reproducible-gap-bounded-official-discovery",
            ),
            (
                "natural-task.2026-08-14.claude-demand-skill-plugin",
                "reproducible-gap-bounded-official-adaptation",
            ),
        )
        if tuple((item["taskIdentity"], item["routeClass"]) for item in routes) != expected_routes:
            reject("the three-route O3 cohort identity or class changed")
        if len(prior_documents) == 2:
            public_route, codex_route = prior_documents
            if (
                public_route["taskIdentity"] != expected_routes[0][0]
                or "No capability discovery or addition was needed"
                not in public_route["measures"]["capabilityLifecycleEvents"]["discovery"]
                or codex_route["taskIdentity"] != expected_routes[1][0]
                or "Finite source-bound review"
                not in codex_route["measures"]["capabilityLifecycleEvents"]["discovery"]
                or "MCP, App, runtime, manager"
                not in codex_route["claimLimits"][2]
            ):
                reject("the prior no-gap or bounded-discovery route classification changed")

        human = measures["humanOutcomeDecision"]
        marginal = measures["marginalOutcomeProcessAndCostDelta"]
        dispositions = measures["postTaskExposureAndCandidateLifecycleDisposition"]
        projections = measures["provisionalProjectionDisposition"]
        if (
            human["acceptedO3Boundary"]
            != "three route decisions across no-gap retain and reproducible-gap bounded official discovery or adaptation"
            or not human["rejectedPromotionBoundary"].startswith(
                "Claude and Codex Skill source deliveries are not materially different O2"
            )
            or marginal["capabilityCountAsValue"] is not False
            or marginal["humanRouteSelectionCount"] != 0
            or marginal["meaningfulExternalCost"] != "none"
            or len(dispositions) != 6
            or not any("CC Switch" in item and "remain off" in item for item in dispositions)
            or not any("CHAP, Human Tool and Agentlas OS" in item for item in dispositions)
            or not projections["codex"].startswith("inactive-retention")
            or not projections["claude"].startswith("inactive-retention")
            or projections["mcpAppsManagers"] != "off"
            or not projections["crossHostExecution"].startswith("not executed")
        ):
            reject("O3 marginal-value, human-authority, or lifecycle disposition changed")

    return len(errors) == before


def _validate_continuation_reconciliation_o2_candidate(
    document: dict[str, Any],
    root: Path,
    errors: list[str],
    *,
    require_human: bool,
) -> bool:
    """Validate this exact continuation result and its fixed O2 cohort."""

    before = len(errors)

    def reject(message: str) -> None:
        _error(errors, f"continuation reconciliation O2 evidence {message}")

    expected_top_level = {
        "schema",
        "id",
        "observedAt",
        "taskIdentity",
        "criterionIds",
        "incrementId",
        "workItemId",
        "registration",
        "source",
        "authority",
        "result",
        "sourceRecords",
        "artifacts",
        "measures",
        "claimLimits",
        "validator",
    }
    if set(document) != expected_top_level:
        reject("top-level receipt shape changed")
        return False

    try:
        registration_ref = document["registration"]
        source = document["source"]
        authority = document["authority"]
        result = document["result"]
        records = document["sourceRecords"]
        artifacts = document["artifacts"]
        measures = document["measures"]
        human = measures["humanOutcomeDecision"]
        orchestration = measures[
            "materialUserCapabilityOrchestrationInterventions"
        ]
        losses = measures["materialCollaborationLossEvents"]
        context = measures["contextCarrierFitnessObservationsAndTransitions"]
        lifecycle = measures["contextLifecycleTransitionAndRecovery"]
        topology = measures["taskTopologyLifecycleEvents"]
        validation = measures["validationResults"]
        floors = measures["taskFloorResults"]
        comparison = measures["outcomeComparison"]
        residue = measures["residueAndClaimLimits"]
    except (KeyError, TypeError):
        reject("required receipt structure is missing")
        return False

    decision_scope = (
        "Accept or reject the delivered compact continuation-reconciliation "
        "source result, whether it is materially distinct from the public-intake "
        "and Codex-Skill source scenarios, and only the registered three-scenario "
        "Codex reference-host O2 burden-reduction claim ceiling."
    )
    required_response = "接受该结果、第三场景区分和上述有界 O2 声明。"
    if (
        document["schema"] != 1
        or document["id"]
        != "evidence.continuation-reconciliation-projection.2026-08-14"
        or document["taskIdentity"]
        != "natural-task.2026-08-14.continuation-reconciliation-projection"
        or document["criterionIds"] != ["O2"]
        or document["incrementId"] != _CONTINUATION_INCREMENT_ID
        or document["workItemId"] != _CONTINUATION_WORK_ID
        or registration_ref
        != {
            "locator": _CONTINUATION_REGISTRATION,
            "sha256": _CONTINUATION_REGISTRATION_SHA256,
            "commit": _CONTINUATION_REGISTRATION_COMMIT,
        }
        or source.get("threadId") != "019ffaa8-b44a-7bf2-97de-65875bceec33"
        or source.get("identityBeforeHumanDecision")
        != _CONTINUATION_PRE_HUMAN_SOURCE_IDENTITY
        or authority.get("namedHuman") != "yiheng8023"
        or authority.get("decisionScope") != decision_scope
        or authority.get("decisionScopeSha256")
        != _CONTINUATION_DECISION_SCOPE_SHA256
        or hashlib.sha256((decision_scope + "\n").encode()).hexdigest()
        != _CONTINUATION_DECISION_SCOPE_SHA256
        or authority.get("requiredResponse") != required_response
        or authority.get("requiredResponseSha256")
        != _CONTINUATION_ACCEPTANCE_MESSAGE_SHA256
        or hashlib.sha256((required_response + "\n").encode()).hexdigest()
        != _CONTINUATION_ACCEPTANCE_MESSAGE_SHA256
        or result.get("baselineCommit") != _CONTINUATION_BASELINE_COMMIT
        or result.get("registrationCommit")
        != _CONTINUATION_REGISTRATION_COMMIT
        or result.get("deliverableCommit") != _CONTINUATION_RESULT_COMMIT
        or result.get("scenarioClass")
        != "host-neutral-continuation-reconciliation-adapter-implementation"
    ):
        reject("task, registration, decision scope, or result identity changed")

    if len(records) < len(_CONTINUATION_SOURCE_EVENTS):
        reject("source chronology is incomplete")
    else:
        prefix_records = records[: len(_CONTINUATION_SOURCE_EVENTS)]
        if (
            tuple(item.get("order") for item in prefix_records)
            != tuple(range(1, 6))
            or tuple(item.get("event") for item in prefix_records)
            != _CONTINUATION_SOURCE_EVENTS
        ):
            reject("source chronology order or events changed")
        identities = [
            item.get("identity", "").removeprefix("sha256:")
            for item in prefix_records
        ]
        combined = hashlib.sha256(("\n".join(identities) + "\n").encode()).hexdigest()
        if f"sha256:{combined}" != _CONTINUATION_PRE_HUMAN_SOURCE_IDENTITY:
            reject("pre-human source chronology identity changed")

    baseline_ready = artifacts.get("baselineReadyProjection", {})
    baseline_active = artifacts.get("baselineActiveProjection", {})
    delivered = artifacts.get("deliveredSource", {})
    clean_codex = artifacts.get("cleanCodexProjection", {})
    dirty_codex = artifacts.get("dirtyCodexProjection", {})
    dirty_claude = artifacts.get("dirtyClaudeProjection", {})
    if (
        baseline_ready
        != {"characters": 3643, "hasLiveRepositoryCheckpoint": False}
        or baseline_active
        != {
            "characters": 6301,
            "limit": 4096,
            "sha256": "75d4a5881cbc7ee45ac14f67b3011670fcc2a01244f290a8dcbed07698ef8c66",
            "hasLiveRepositoryCheckpoint": False,
        }
        or delivered.get("continuationBlob")
        != _CONTINUATION_TASK_FILES["harness/continuation.py"][0]
        or delivered.get("continuationSha256")
        != _CONTINUATION_TASK_FILES["harness/continuation.py"][1]
        or delivered.get("controlBlob")
        != _CONTINUATION_TASK_FILES["harness/control.py"][0]
        or delivered.get("controlSha256")
        != _CONTINUATION_TASK_FILES["harness/control.py"][1]
        or delivered.get("scopedDiffSha256")
        != "1c29743c3d8508b293afac885add732e2b320c22c08fa993e40004372bc83650"
        or clean_codex
        != {
            "characters": 2728,
            "limit": 3072,
            "valid": True,
            "branch": "main",
            "head": _CONTINUATION_RESULT_COMMIT,
            "upstream": "origin/main",
            "ahead": 0,
            "behind": 0,
            "worktreeCount": 1,
            "dirtyEntryCount": 0,
        }
        or dirty_codex
        != {
            "characters": 2730,
            "limit": 3072,
            "valid": True,
            "dirtyPathNamesExposed": False,
        }
        or dirty_claude
        != {
            "characters": 2922,
            "limit": 3072,
            "valid": True,
            "commonSemanticsMatchCodex": True,
        }
    ):
        reject("registered baseline or measured result changed")

    floor_names = {
        "outcomeQuality",
        "intentAndCommunication",
        "contextCarrierFitness",
        "taskTopology",
        "reliabilityAndRecovery",
        "authorityAndSafety",
        "scopeAndMinimality",
        "evidence",
        "residue",
    }
    if (
        orchestration.get("count") != 0
        or orchestration.get("taskTopologyInterventions") != 0
        or losses.get("count") != 0
        or losses.get("repeatedSameClassCorrections") != 0
        or measures.get("repeatedAlreadyBoundRequests", {}).get("count") != 0
        or context.get("reliableRemainingCapacitySignal") != "unknown"
        or context.get("preventableContextLoss") is not False
        or lifecycle.get("crossedInThisTask") is not False
        or lifecycle.get("userReconstructionCount") != 0
        or lifecycle.get("cohortCoverage")
        != [
            "public-intake receipt native compaction at 2026-08-14T00:56:49.178Z",
            "Codex Skill receipt native compaction at 2026-08-14T02:01:32.757Z",
        ]
        or topology.get("isolatedCarrierCreated") is not False
        or topology.get("userTopologyOperationCount") != 0
        or topology.get("codeCarrier") != "existing main checkout retained"
        or len(measures.get("selectedRouteSubstrates", [])) != 4
        or set(measures.get("capabilityLifecycleEvents", {}))
        != {"observation", "gapAssessment", "discovery", "dispatch", "release"}
        or validation
        != {
            "canonicalVerifier": "valid=true; O1=true; O2=false; O3=true; O4=false; O5=false",
            "fullProductTests": "150/150 PASS",
            "claudeStrictPluginValidation": "pass",
            "codexLauncher": "exit=0; 2728 characters on clean main; valid=true",
            "claudeLauncher": "exit=0; 2922 characters while dirty; valid=true",
            "fallbackOverflowTest": "pass",
            "gitPrivacyAndUnknownStateTests": "pass",
        }
        or set(floors) != floor_names | {"missingData"}
        or any(floors.get(name) != "pass" for name in floor_names)
        or any(
            residue.get(name) != []
            for name in (
                "repositoryTemporaryResidue",
                "externalWritesBeyondAuthorizedGitPush",
                "consumerOrHostMutation",
                "remainingTaskScopedExposure",
                "codeOrConversationCarriersCreated",
            )
        )
    ):
        reject("a mandatory zero-loss, lifecycle, validation, floor, or residue value changed")

    expected_tasks = [
        "natural-task.2026-08-14.public-intake-zero-knowledge",
        "natural-task.2026-08-14.codex-demand-skill-plugin",
        "natural-task.2026-08-14.continuation-reconciliation-projection",
    ]
    expected_scenarios = [
        "public-support-and-contribution-intake-for-zero-knowledge-users",
        "codex-plugin-skill-reference-adapter-delivery",
        "host-neutral-continuation-reconciliation-adapter-implementation",
    ]
    if (
        comparison.get("taskIdentities") != expected_tasks
        or comparison.get("scenarioClasses") != expected_scenarios
        or len(set(expected_scenarios)) != 3
        or comparison.get("baselineMaterialInterventions") != [3, 2, 3]
        or comparison.get("observedMaterialInterventions") != [0, 0, 0]
        or comparison.get("aggregateBaseline") != 8
        or comparison.get("aggregateObserved") != 0
        or comparison.get("strictReduction") is not True
        or comparison.get("minimumScenarioCount") != 3
    ):
        reject("three-scenario cohort or strict burden reduction changed")

    prior_documents: list[dict[str, Any]] = []
    for relative, validator in (
        (_PUBLIC_INTAKE_RECEIPT, _validate_public_intake_o1),
        (_CODEX_SKILL_RECEIPT, _validate_codex_skill_o1),
    ):
        try:
            prior = _parse_json((root / relative).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, _InvalidJson, TypeError):
            reject(f"prior O2 receipt is unavailable or invalid: {relative}")
            continue
        if validator(prior, "O1", root, errors) is not True:
            reject(f"prior O2 receipt no longer passes its validator: {relative}")
        prior_documents.append(prior)

    if len(prior_documents) == 2:
        for index, prior in enumerate(prior_documents):
            prior_measures = prior.get("measures", {})
            prior_orchestration = prior_measures.get(
                "materialUserCapabilityOrchestrationInterventions", {}
            )
            if (
                prior.get("taskIdentity") != expected_tasks[index]
                or prior_orchestration.get("count") != 0
                or prior_orchestration.get("taskTopologyInterventions") != 0
                or prior_measures.get("materialCollaborationLossEvents", {}).get(
                    "count"
                )
                != 0
                or prior_measures.get("repeatedAlreadyBoundRequests", {}).get("count")
                != 0
                or prior_measures.get("humanOutcomeDecision", {}).get("accepted")
                is not True
            ):
                reject("a prior cohort result or zero-loss floor changed")
        public_events = tuple(
            item.get("event") for item in prior_documents[0].get("sourceRecords", [])
        )
        codex_events = tuple(
            item.get("event") for item in prior_documents[1].get("sourceRecords", [])
        )
        if (
            "native-context-compacted" not in public_events
            or "post-compaction-task-recovered" not in public_events
            or "native-context-compacted" not in codex_events
            or "post-compaction-task-and-source-recovered" not in codex_events
        ):
            reject("registered context-lifecycle crossing coverage changed")

        registration_expectations = (
            (
                prior_documents[0].get("registration", {}).get("locator"),
                expected_scenarios[0],
                3,
            ),
            (
                prior_documents[1].get("registration", {}).get("locator"),
                expected_scenarios[1],
                2,
            ),
            (
                _CONTINUATION_REGISTRATION,
                expected_scenarios[2],
                3,
            ),
        )
        for locator, scenario, baseline_count in registration_expectations:
            try:
                registered = _parse_json(
                    (root / locator).read_text(encoding="utf-8")
                )
                values = registered["preRegistrationValues"]
                registered_scenario = values["scenarioClass"]
                registered_baseline = values[
                    "matchedOrHistoricalBaselineIdentityAndRule"
                ]["baselineMaterialInterventions"]
            except (OSError, KeyError, TypeError, UnicodeError, _InvalidJson):
                reject(f"cohort registration is unavailable or invalid: {locator}")
                continue
            if (
                registered_scenario != scenario
                or registered_baseline != baseline_count
            ):
                reject(f"cohort scenario or baseline changed: {locator}")

    try:
        registration_raw = (root / _CONTINUATION_REGISTRATION).read_bytes()
    except OSError:
        registration_raw = None
    if (
        registration_raw is None
        or hashlib.sha256(registration_raw).hexdigest()
        != _CONTINUATION_REGISTRATION_SHA256
    ):
        reject("registration bytes changed")

    registration_parent = _evidence_git(
        root, "rev-parse", f"{_CONTINUATION_REGISTRATION_COMMIT}^"
    )
    result_parent = _evidence_git(root, "rev-parse", f"{_CONTINUATION_RESULT_COMMIT}^")
    committed_registration = _evidence_git(
        root,
        "show",
        f"{_CONTINUATION_REGISTRATION_COMMIT}:{_CONTINUATION_REGISTRATION}",
    )
    committed_program = _evidence_git(
        root, "show", f"{_CONTINUATION_REGISTRATION_COMMIT}:product/program.json"
    )
    result_is_ancestor = _evidence_git(
        root, "merge-base", "--is-ancestor", _CONTINUATION_RESULT_COMMIT, "HEAD"
    )
    if (
        registration_parent is None
        or registration_parent.decode().strip() != _CONTINUATION_BASELINE_COMMIT
        or result_parent is None
        or result_parent.decode().strip() != _CONTINUATION_REGISTRATION_COMMIT
        or committed_registration is None
        or hashlib.sha256(committed_registration).hexdigest()
        != _CONTINUATION_REGISTRATION_SHA256
        or result_is_ancestor is None
    ):
        reject("Git registration-to-result chronology changed")

    if committed_program is None:
        reject("committed active registration binding is unavailable")
    else:
        try:
            registered_program = _parse_json(committed_program.decode())
            registered_increment = next(
                item
                for item in registered_program["increments"]
                if item.get("id") == _CONTINUATION_INCREMENT_ID
            )
        except (KeyError, StopIteration, UnicodeError, _InvalidJson, TypeError):
            reject("committed active registration binding is invalid")
        else:
            if (
                registered_program.get("status") != "active"
                or registered_program.get("activeIncrementId")
                != _CONTINUATION_INCREMENT_ID
                or registered_increment.get("state") != "active"
                or registered_increment.get("taskRegistration")
                != {
                    "locator": _CONTINUATION_REGISTRATION,
                    "sha256": _CONTINUATION_REGISTRATION_SHA256,
                }
            ):
                reject("registration was not active before the result commit")

    changed_paths = _evidence_git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        _CONTINUATION_RESULT_COMMIT,
    )
    if changed_paths is None or tuple(changed_paths.decode().splitlines()) != (
        _CONTINUATION_RESULT_PATHS
    ):
        reject("result commit changed paths differ from the registered task")
    scoped_diff = _evidence_git(
        root,
        "diff",
        "--no-ext-diff",
        "--no-color",
        _CONTINUATION_REGISTRATION_COMMIT,
        _CONTINUATION_RESULT_COMMIT,
    )
    if (
        scoped_diff is None
        or hashlib.sha256(scoped_diff).hexdigest()
        != delivered.get("scopedDiffSha256")
    ):
        reject("scoped result diff changed")

    for path, expected in _CONTINUATION_TASK_FILES.items():
        result_blob, result_sha256 = expected
        result_identity = _evidence_git(
            root, "rev-parse", f"{_CONTINUATION_RESULT_COMMIT}:{path}"
        )
        result_bytes = _evidence_git(
            root, "show", f"{_CONTINUATION_RESULT_COMMIT}:{path}"
        )
        if (
            result_identity is None
            or result_identity.decode().strip() != result_blob
            or result_bytes is None
            or hashlib.sha256(result_bytes).hexdigest() != result_sha256
        ):
            reject(f"delivered task source changed: {path}")
        if path == "harness/continuation.py":
            try:
                current_bytes = (root / path).read_bytes()
            except OSError:
                current_bytes = None
            if current_bytes != result_bytes:
                reject("accepted continuation behavior no longer matches the result")

    claims = document.get("claimLimits", [])
    if (
        len(claims) != 5
        or not any("At most one candidate.5 Codex reference-host O2 cohort" in item for item in claims)
        or not any("not proof of installed Hook value" in item for item in claims)
        or not any("does not establish O5 portability" in item for item in claims)
        or not any("cannot verify O4" in item for item in claims)
    ):
        reject("claim ceiling changed or broadened")

    if require_human:
        if (
            authority.get("decisionState") != "accepted"
            or result.get("accepted") is not True
            or result.get("humanJudgment")
            != "accepted task result, material third-scenario distinction, and bounded O2 claim"
            or human
            != {
                "accepted": True,
                "namedHuman": "yiheng8023",
                "decisionMessageLocator": (
                    "codex://threads/019ffaa8-b44a-7bf2-97de-65875bceec33/"
                    "messages/by-content-sha256/"
                    + _CONTINUATION_ACCEPTANCE_MESSAGE_SHA256
                ),
                "decisionMessageIdentity": (
                    "sha256:" + _CONTINUATION_ACCEPTANCE_MESSAGE_SHA256
                ),
                "acceptedTaskResult": True,
                "acceptedMaterialThirdScenarioDistinction": True,
                "acceptedBoundedO2Claim": True,
            }
            or comparison.get("materialDistinctionState")
            != "accepted-by-yiheng8023"
            or floors.get("missingData") != []
            or residue.get("claim")
            != "O2 only for the exact registered three-scenario Codex reference-host cohort"
            or document.get("validator", {}).get("state") != "accepted"
            or len(records) != 6
            or records[-1].get("order") != 6
            or records[-1].get("event") != "named-human-accepted"
            or records[-1].get("identity")
            != "sha256:" + _CONTINUATION_ACCEPTANCE_MESSAGE_SHA256
            or not records[-1].get("locator", "").startswith(
                "codex://threads/019ffaa8-b44a-7bf2-97de-65875bceec33/"
            )
            or source.get("identityWithHumanDecision")
            != "sha256:63b44f9d54b8fd2ba8d32d10a68c0a8ea0b6a3fda46f7cbae93d318ba664ab55"
        ):
            reject("named-human result, distinction, or bounded O2 decision is absent")
    else:
        if (
            authority.get("decisionState") != "pending"
            or result.get("accepted") is not None
            or result.get("humanJudgment") != "pending"
            or human.get("accepted") is not None
            or any(
                human.get(name) is not None
                for name in (
                    "decisionMessageLocator",
                    "decisionMessageIdentity",
                    "acceptedTaskResult",
                    "acceptedMaterialThirdScenarioDistinction",
                    "acceptedBoundedO2Claim",
                )
            )
            or comparison.get("materialDistinctionState")
            != "pending-named-human-judgment"
            or floors.get("missingData")
            != ["named-human outcome, material-distinction, and bounded O2 judgment"]
            or residue.get("claim") != "pending named-human judgment; no O2 credit yet"
            or document.get("validator", {}).get("state")
            != "machine-eligible-human-pending"
            or len(records) != 5
        ):
            reject("pending human gate was hidden or pre-accepted")

    return len(errors) == before


def _validate_continuation_reconciliation_o2(
    document: dict[str, Any], criterion_id: str, root: Path, errors: list[str]
) -> bool:
    if criterion_id != "O2":
        _error(errors, "continuation reconciliation evidence used for non-O2 criterion")
        return False
    return _validate_continuation_reconciliation_o2_candidate(
        document, root, errors, require_human=True
    )


def _validate_codex_reference_calibration_o4_candidate(
    document: dict[str, Any],
    root: Path,
    errors: list[str],
    *,
    require_human: bool,
) -> bool:
    """Validate the exact registered O4 mixed cohort without inventing a result."""

    before = len(errors)

    def reject(message: str) -> None:
        _error(errors, f"Codex reference calibration O4 evidence {message}")

    expected_top_level = {
        "schema",
        "id",
        "observedAt",
        "taskIdentity",
        "criterionIds",
        "incrementId",
        "workItemId",
        "registration",
        "source",
        "authority",
        "result",
        "cohort",
        "measures",
        "claimLimits",
        "validator",
    }
    if set(document) != expected_top_level:
        reject("top-level receipt shape changed")
        return False

    try:
        registration_ref = document["registration"]
        source = document["source"]
        authority = document["authority"]
        result = document["result"]
        cohort = document["cohort"]
        accepted_cohort = cohort["acceptedReceipts"]
        stopped_cohort = cohort["stoppedReceipt"]
        measures = document["measures"]
        identity = measures["scorecardAndProfileIdentity"]
        outcome = measures["outcomeQuality"]
        burden = measures["userOrchestrationBurden"]
        topology = measures["taskTopologyLifecycleAndBurden"]
        intent = measures["intentCommunicationAndDecisionCompleteness"]
        reliability = measures["routeReliabilityRecoveryTimeAndCallCost"]
        safety = measures["authoritySafetyEvidenceAndResidue"]
        resource = measures["resourceContinuityContextAndProcessCost"]
        context = measures["contextCarrierFitnessObservationsAndTransitions"]
        lifecycle = measures["referenceHostContextLifecycleTransitionAndRecovery"]
        comparator = measures["comparatorOutcomeAndProcessResults"]
        external = measures["externalComparisonAndReuseDecision"]
        applicability = measures["applicabilityLimitsAndHumanDecision"]
        floors = measures["mandatoryFloorResults"]
    except (KeyError, TypeError):
        reject("required receipt structure is missing")
        return False

    decision_scope = (
        "Accept or reject the unchanged candidate.5 methodology and open minimum "
        "quality-conformance profile, exact three-pass/one-stopped Codex "
        "reference-host calibration, fixed comparator and external-reuse "
        "conclusion, applicability limits, and only the registered bounded O4 claim."
    )
    required_response = (
        "接受上述 candidate.5 方法与最低质量 profile、混合通过/停止校准、"
        "适用边界和有界 O4 声明。"
    )
    input_parts = (
        _CODEX_CALIBRATION_REGISTRATION_SHA256,
        _CODEX_CALIBRATION_ACCEPTED_RECEIPTS[_PUBLIC_INTAKE_RECEIPT][0],
        _CODEX_CALIBRATION_ACCEPTED_RECEIPTS[_CODEX_SKILL_RECEIPT][0],
        _CODEX_CALIBRATION_ACCEPTED_RECEIPTS[_CONTINUATION_RECEIPT][0],
        _CODEX_CALIBRATION_STOPPED_RECEIPT_SHA256,
        _CODEX_CALIBRATION_PROFILE_SHA256,
        EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256,
        _CODEX_CALIBRATION_REGISTRATION_COMMIT,
    )
    input_identity = "sha256:" + hashlib.sha256(
        ("\n".join(input_parts) + "\n").encode()
    ).hexdigest()
    if (
        document["schema"] != 1
        or document["id"] != "evidence.codex-reference-calibration.2026-08-14"
        or document["taskIdentity"]
        != "natural-task.2026-08-14.codex-reference-calibration"
        or document["criterionIds"] != ["O4"]
        or document["incrementId"] != _CODEX_CALIBRATION_INCREMENT_ID
        or document["workItemId"] != _CODEX_CALIBRATION_WORK_ID
        or registration_ref
        != {
            "locator": _CODEX_CALIBRATION_REGISTRATION,
            "sha256": _CODEX_CALIBRATION_REGISTRATION_SHA256,
            "commit": _CODEX_CALIBRATION_REGISTRATION_COMMIT,
        }
        or source.get("threadId") != "019ffaa8-b44a-7bf2-97de-65875bceec33"
        or source.get("machineEvaluationInputIdentity")
        != _CODEX_CALIBRATION_INPUT_IDENTITY
        or input_identity != _CODEX_CALIBRATION_INPUT_IDENTITY
        or source.get("evaluationMode")
        != (
            "one post-registration source-only evaluation of the exact fixed cohort; "
            "no natural-task rerun, model call, host change, consumer mutation, or "
            "new carrier"
        )
        or authority.get("namedHuman") != "yiheng8023"
        or authority.get("decisionScope") != decision_scope
        or authority.get("decisionScopeSha256")
        != _CODEX_CALIBRATION_DECISION_SCOPE_SHA256
        or hashlib.sha256((decision_scope + "\n").encode()).hexdigest()
        != _CODEX_CALIBRATION_DECISION_SCOPE_SHA256
        or authority.get("requiredResponse") != required_response
        or authority.get("requiredResponseSha256")
        != _CODEX_CALIBRATION_ACCEPTANCE_MESSAGE_SHA256
        or hashlib.sha256((required_response + "\n").encode()).hexdigest()
        != _CODEX_CALIBRATION_ACCEPTANCE_MESSAGE_SHA256
    ):
        reject("task, registration, source, or human-decision identity changed")

    expected_accepted = []
    for locator, expected in _CODEX_CALIBRATION_ACCEPTED_RECEIPTS.items():
        receipt_sha256, task, scenario, validator_kind, required_criterion = expected
        expected_accepted.append(
            {
                "taskIdentity": task,
                "scenarioClass": scenario,
                "locator": locator,
                "sha256": receipt_sha256,
                "validator": validator_kind,
                "requiredCriterion": required_criterion,
                "state": "accepted",
            }
        )
    expected_stopped = {
        "taskIdentity": "natural-task.2026-08-14.codex-plugin-context-rollover",
        "scenarioClass": (
            "long-horizon-software-product-continuity-through-agent-owned-"
            "conversation-rollover"
        ),
        "locator": _CODEX_CALIBRATION_STOPPED_RECEIPT,
        "sha256": _CODEX_CALIBRATION_STOPPED_RECEIPT_SHA256,
        "registrationSha256": (
            "b44bebeed83d629f6716d5e4d424195dd10c42564af2a8936fc7c41fbb018f29"
        ),
        "state": "stopped",
        "eligibleForOutcomeProgress": False,
        "missingMandatoryEvidence": [
            "native HookStarted chronology",
            "native HookCompleted chronology",
        ],
    }
    if accepted_cohort != expected_accepted or stopped_cohort != expected_stopped:
        reject("fixed three-pass/one-stopped cohort changed")

    try:
        registration_raw = (root / _CODEX_CALIBRATION_REGISTRATION).read_bytes()
        registration = _parse_json(registration_raw.decode())
    except (OSError, UnicodeError, _InvalidJson, TypeError):
        reject("calibration registration is unavailable or invalid")
        registration_raw = None
        registration = {}
    if (
        registration_raw is None
        or hashlib.sha256(registration_raw).hexdigest()
        != _CODEX_CALIBRATION_REGISTRATION_SHA256
        or registration.get("taskIdentity")
        != "natural-task.2026-08-14.codex-reference-calibration"
        or registration.get("incrementId") != _CODEX_CALIBRATION_INCREMENT_ID
        or registration.get("criterionIds") != ["O4"]
    ):
        reject("calibration registration bytes or identity changed")

    registration_parent = _evidence_git(
        root, "rev-parse", f"{_CODEX_CALIBRATION_REGISTRATION_COMMIT}^"
    )
    committed_registration = _evidence_git(
        root,
        "show",
        f"{_CODEX_CALIBRATION_REGISTRATION_COMMIT}:{_CODEX_CALIBRATION_REGISTRATION}",
    )
    committed_program = _evidence_git(
        root,
        "show",
        f"{_CODEX_CALIBRATION_REGISTRATION_COMMIT}:product/program.json",
    )
    committed_acceptance = _evidence_git(
        root,
        "show",
        f"{_CODEX_CALIBRATION_REGISTRATION_COMMIT}:product/acceptance.json",
    )
    registration_is_local = _evidence_git(
        root,
        "merge-base",
        "--is-ancestor",
        _CODEX_CALIBRATION_REGISTRATION_COMMIT,
        "HEAD",
    )
    registration_is_pushed = _evidence_git(
        root,
        "merge-base",
        "--is-ancestor",
        _CODEX_CALIBRATION_REGISTRATION_COMMIT,
        "origin/main",
    )
    if (
        registration_parent is None
        or registration_parent.decode().strip()
        != _CODEX_CALIBRATION_REGISTRATION_PARENT
        or committed_registration is None
        or hashlib.sha256(committed_registration).hexdigest()
        != _CODEX_CALIBRATION_REGISTRATION_SHA256
        or registration_is_local is None
        or registration_is_pushed is None
    ):
        reject("registration was not immutably committed and pushed before evaluation")

    if committed_program is None:
        reject("committed active program binding is unavailable")
    else:
        try:
            registered_program = _parse_json(committed_program.decode())
            registered_increment = next(
                item
                for item in registered_program["increments"]
                if item.get("id") == _CODEX_CALIBRATION_INCREMENT_ID
            )
        except (KeyError, StopIteration, TypeError, UnicodeError, _InvalidJson):
            reject("committed active program binding is invalid")
        else:
            if (
                registered_program.get("status") != "active"
                or registered_program.get("activeIncrementId")
                != _CODEX_CALIBRATION_INCREMENT_ID
                or registered_increment.get("state") != "active"
                or registered_increment.get("taskRegistration")
                != {
                    "locator": _CODEX_CALIBRATION_REGISTRATION,
                    "sha256": _CODEX_CALIBRATION_REGISTRATION_SHA256,
                }
            ):
                reject("registration was not active before the calibration")

    try:
        accepted_contract = _parse_json((root / "product/acceptance.json").read_text())
    except (OSError, UnicodeError, _InvalidJson, TypeError):
        reject("current acceptance contract is unavailable or invalid")
        accepted_contract = {}
    if (
        _criteria_contract_digest(accepted_contract.get("criteria"))
        != EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256
    ):
        reject("current scorecard contract changed")

    if committed_acceptance is None:
        reject("registered O4 criterion is unavailable")
    else:
        try:
            registered_acceptance = _parse_json(committed_acceptance.decode())
            registered_o4 = next(
                item
                for item in registered_acceptance["criteria"]
                if item.get("id") == "O4"
            )
            registered_o4_sha256 = hashlib.sha256(
                json.dumps(
                    registered_o4,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        except (KeyError, StopIteration, TypeError, UnicodeError, _InvalidJson):
            reject("registered O4 criterion is invalid")
        else:
            if registered_o4_sha256 != _CODEX_CALIBRATION_O4_REGISTERED_SHA256:
                reject("registered O4 criterion changed")

    try:
        profile_raw = (root / "docs/DEMAND-TO-CAPABILITY-PROFILE.md").read_bytes()
    except OSError:
        profile_raw = None
    profile_blob = _evidence_git(
        root, "rev-parse", "HEAD:docs/DEMAND-TO-CAPABILITY-PROFILE.md"
    )
    if (
        profile_raw is None
        or hashlib.sha256(profile_raw).hexdigest()
        != _CODEX_CALIBRATION_PROFILE_SHA256
        or profile_blob is None
        or profile_blob.decode().strip() != _CODEX_CALIBRATION_PROFILE_BLOB
    ):
        reject("candidate.5 profile bytes or Git identity changed")

    source_registrations: dict[str, dict[str, Any]] = {}
    expected_scorecard = (
        "harness-acceptance-v0.2-contract-sha256-"
        + EXPECTED_CURRENT_CRITERIA_CONTRACT_SHA256
    )
    for locator, expected in _CODEX_CALIBRATION_REGISTRATIONS.items():
        expected_sha256, expected_scenario = expected
        try:
            raw = (root / locator).read_bytes()
            registered = _parse_json(raw.decode())
            values = registered["preRegistrationValues"]
            scorecard = values["scorecardVersion"]
            profile = values["methodologyAndQualityProfileVersion"]
            scenario = values["scenarioClass"]
        except (OSError, KeyError, TypeError, UnicodeError, _InvalidJson):
            reject(f"source registration is unavailable or invalid: {locator}")
            continue
        if (
            hashlib.sha256(raw).hexdigest() != expected_sha256
            or scorecard != expected_scorecard
            or "harness-demand-to-capability-v0.2-candidate.5" not in profile
            or _CODEX_CALIBRATION_PROFILE_BLOB not in profile
            or _CODEX_CALIBRATION_PROFILE_SHA256 not in profile
            or scenario != expected_scenario
        ):
            reject(f"source registration identity or fixed rule changed: {locator}")
        source_registrations[locator] = registered

    accepted_validators = {
        _PUBLIC_INTAKE_RECEIPT: (_validate_public_intake_o1, "O1"),
        _CODEX_SKILL_RECEIPT: (_validate_codex_skill_o1, "O1"),
        _CONTINUATION_RECEIPT: (_validate_continuation_reconciliation_o2, "O2"),
    }
    for locator, expected in _CODEX_CALIBRATION_ACCEPTED_RECEIPTS.items():
        expected_sha256, expected_task, _, _, _ = expected
        validator, criterion = accepted_validators[locator]
        try:
            raw = (root / locator).read_bytes()
            accepted_receipt = _parse_json(raw.decode())
        except (OSError, UnicodeError, _InvalidJson, TypeError):
            reject(f"accepted cohort receipt is unavailable or invalid: {locator}")
            continue
        if (
            hashlib.sha256(raw).hexdigest() != expected_sha256
            or accepted_receipt.get("taskIdentity") != expected_task
        ):
            reject(f"accepted cohort receipt identity changed: {locator}")
        if validator(accepted_receipt, criterion, root, errors) is not True:
            reject(f"accepted cohort receipt no longer passes its validator: {locator}")

    try:
        stopped_raw = (root / _CODEX_CALIBRATION_STOPPED_RECEIPT).read_bytes()
        stopped = _parse_json(stopped_raw.decode())
        stopped_floor = next(
            item
            for item in stopped["chronology"]
            if item.get("event") == "mandatory-native-hook-event-floor-evaluated"
        )
        stopped_safety = stopped["safetyAndCleanup"]
    except (OSError, KeyError, StopIteration, TypeError, UnicodeError, _InvalidJson):
        reject("stopped cohort receipt is unavailable or invalid")
        stopped_raw = None
        stopped = {}
        stopped_floor = {}
        stopped_safety = {}
    if (
        stopped_raw is None
        or hashlib.sha256(stopped_raw).hexdigest()
        != _CODEX_CALIBRATION_STOPPED_RECEIPT_SHA256
        or stopped.get("state") != "stopped"
        or stopped.get("eligibleForOutcomeProgress") is not False
        or stopped.get("outcomeProgress") != []
        or stopped.get("taskIdentity")
        != "natural-task.2026-08-14.codex-plugin-context-rollover"
        or stopped.get("registration", {}).get("sha256")
        != "b44bebeed83d629f6716d5e4d424195dd10c42564af2a8936fc7c41fbb018f29"
        or stopped_floor.get("hookStartedPayloadTypeCount") != 0
        or stopped_floor.get("hookCompletedPayloadTypeCount") != 0
        or stopped_floor.get("result") != "stopped"
        or stopped_safety.get("childArchived") is not True
        or stopped_safety.get("temporaryPluginRetained") is not False
        or stopped_safety.get("temporaryTrustEntryRetained") is not False
        or stopped_safety.get("temporaryPluginCacheRetained") is not False
        or stopped_safety.get("consumerConfigRestoredExactly") is not True
    ):
        reject("stopped receipt was changed, normalized, or left unclean")

    continuation_registration = source_registrations.get(_CONTINUATION_REGISTRATION)
    if continuation_registration is None:
        reject("fixed comparator and external source registration is unavailable")
        continuation_values = {}
    else:
        continuation_values = continuation_registration["preRegistrationValues"]
    canonical_values: dict[str, str] = {}
    for name, expected_sha256 in _CODEX_CALIBRATION_CANONICAL_SOURCE_VALUES.items():
        value = continuation_values.get(name)
        canonical_sha256 = hashlib.sha256(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        canonical_values[name] = canonical_sha256
        if canonical_sha256 != expected_sha256:
            reject(f"pre-registered comparator, floor, or external value changed: {name}")

    if identity != {
        "scorecardVersion": expected_scorecard,
        "o4CriterionCanonicalSha256": _CODEX_CALIBRATION_O4_REGISTERED_SHA256,
        "methodologyAndQualityProfileVersion": (
            "harness-demand-to-capability-v0.2-candidate.5"
        ),
        "profileBlob": _CODEX_CALIBRATION_PROFILE_BLOB,
        "profileSha256": _CODEX_CALIBRATION_PROFILE_SHA256,
        "bytesAndSemanticRulesChangedAfterResults": False,
    }:
        reject("reported scorecard or profile identity changed")

    if outcome != {
        "acceptedScenarioCount": 3,
        "materiallyDistinctAcceptedScenarioCount": 3,
        "stoppedScenarioCount": 1,
        "acceptedTaskValidatorsPass": True,
        "stoppedReceiptRemainsStopped": True,
    }:
        reject("mixed cohort outcome result changed")

    if burden != {
        "baselineMaterialInterventions": [3, 2, 3],
        "observedMaterialInterventions": [0, 0, 0],
        "aggregateBaseline": 8,
        "aggregateObserved": 0,
        "strictAdvantage": True,
        "userCapabilityOrTopologyOperationsForCalibration": 0,
    }:
        reject("strict user-orchestration advantage changed")

    if (
        topology.get("acceptedReceiptUserTopologyOperations") != 0
        or topology.get("stoppedChildCreatedByAgent") is not True
        or topology.get("stoppedChildArchivedByAgent") is not True
        or topology.get("stoppedChildWorktreeCreated") is not False
        or topology.get("newCarrierForCalibration") is not False
        or not topology.get("currentConversationCarrier", "").startswith("Codex task ")
        or topology.get("currentCodeCarrier")
        != "C:/Projects/agent-autonomy-harness main retained"
    ):
        reject("task-topology lifecycle or burden result changed")

    if (
        intent.get("acceptedReceiptMaterialCollaborationLossCounts") != [0, 0, 0]
        or intent.get("acceptedReceiptRepeatedBoundRequestCounts") != [0, 0, 0]
        or intent.get("calibrationMaterialCollaborationLossCount") != 0
        or intent.get("pendingHumanInput")
        != "one accountable bounded O4 judgment only"
    ):
        reject("intent, communication, or decision-completeness floor changed")

    try:
        codex_package_version = _parse_json(
            (
                root
                / "adapters/agent-autonomy-harness-codex/.codex-plugin/plugin.json"
            ).read_text(encoding="utf-8")
        )["version"]
        claude_package_version = _parse_json(
            (
                root
                / "adapters/agent-autonomy-harness-claude/.claude-plugin/plugin.json"
            ).read_text(encoding="utf-8")
        )["version"]
    except (OSError, KeyError, TypeError, UnicodeError, _InvalidJson):
        reject("inactive projection integrity metadata is unavailable")
        codex_package_version = None
        claude_package_version = None
    integrity_refresh = reliability.get("inactiveProjectionIntegrityRefresh", {})
    if (
        reliability.get("acceptedReceiptValidatorsReexecuted") != 3
        or reliability.get("acceptedReceiptValidatorFailures") != 0
        or reliability.get("newModelCalls") != 0
        or reliability.get("newHostExecutions") != 0
        or reliability.get("naturalTaskReruns") != 0
        or reliability.get("stoppedTaskReruns") != 0
        or set(integrity_refresh)
        != {
            "reason",
            "codexPackageVersion",
            "claudePackageVersion",
            "evaluatedHistoricalPluginSnapshotsChanged",
            "methodProfileSkillOrHookSemanticsChanged",
            "installedEnabledOrConsumerStateChanged",
        }
        or integrity_refresh.get("reason")
        != (
            "the new criterion-scoped repository validator changed "
            "harness/control.py, so both inactive launchers refreshed only their "
            "control.py integrity pin and payload identity"
        )
        or integrity_refresh.get("codexPackageVersion") != codex_package_version
        or integrity_refresh.get("claudePackageVersion") != claude_package_version
        or not str(codex_package_version).startswith(
            "0.2.0-candidate.5+codex.payload-"
        )
        or not str(claude_package_version).startswith(
            "0.2.0-candidate.5+claude.payload-"
        )
        or integrity_refresh.get("evaluatedHistoricalPluginSnapshotsChanged")
        is not False
        or integrity_refresh.get("methodProfileSkillOrHookSemanticsChanged")
        is not False
        or integrity_refresh.get("installedEnabledOrConsumerStateChanged")
        is not False
        or "no value imputed"
        not in reliability.get("recoveryAndCallCostDataSource", "")
    ):
        reject("reliability, recovery, time, or call-cost result changed")

    if (
        safety.get("acceptedReceiptMandatoryFloorsPass") is not True
        or safety.get("stoppedReceiptSafetyCleanupPass") is not True
        or any(
            safety.get(name) != []
            for name in (
                "repositoryTemporaryResidue",
                "consumerOrHostMutation",
                "remainingTaskScopedExposure",
                "externalWritesBeyondAuthorizedGitPush",
            )
        )
        or safety.get("newTrustDataCostReleaseOrPublicationBoundary") is not False
    ):
        reject("authority, safety, evidence, or residue floor changed")

    if resource != {
        "acceptedNativeCompactionCrossings": 2,
        "userContextReconstructionCount": 0,
        "userTopologyRecoveryCount": 0,
        "continuationBaselineCharacters": 6301,
        "continuationDeliveredCharacters": 2728,
        "continuationCharacterReduction": 3573,
        "calibrationProcessArtifactsCountAsOutcome": False,
    }:
        reject("resource, continuity, context, or process cost changed")

    if (
        context.get("reliableRemainingCapacitySignal") != "unknown"
        or not context.get("conservativeRule", "").startswith(
            "retain the current task while goal, registration, cohort, Git"
        )
        or context.get("preventableContextLossObserved") is not False
        or context.get("userSelectedTransition") is not False
    ):
        reject("context-carrier fitness or conservative transition rule changed")

    expected_crossings = [
        {
            "receipt": "public-intake",
            "transition": "native compaction at 2026-08-14T00:56:49.178Z",
            "sameTaskRecovery": True,
            "userReconstructionOrTopologyOperationCount": 0,
        },
        {
            "receipt": "Codex Skill",
            "transition": "native compaction at 2026-08-14T02:01:32.757Z",
            "sameTaskRecovery": True,
            "userReconstructionOrTopologyOperationCount": 0,
        },
    ]
    if (
        lifecycle.get("acceptedCrossings") != expected_crossings
        or lifecycle.get("stoppedCrossing")
        != {
            "startupProjectionObserved": True,
            "postCompactionProjectionObserved": True,
            "nativeHookStartedPayloadTypeCount": 0,
            "nativeHookCompletedPayloadTypeCount": 0,
            "classification": "stopped-not-normalized",
        }
    ):
        reject("reference-host context lifecycle evidence changed")

    if (
        comparator.get("sourceRegistration") != _CONTINUATION_REGISTRATION
        or comparator.get("referenceHostCohortCanonicalSha256")
        != canonical_values.get("referenceHostProfileAndEligibleReceiptSet")
        or comparator.get("outcomeComparatorCohortCanonicalSha256")
        != canonical_values.get(
            "outcomeComparatorCohortSourcesVersionsLicensesOrTermsMaturityEligibilityAndMatchingRules"
        )
        or comparator.get("comparisonDecisionCanonicalSha256")
        != canonical_values.get("comparatorBaselineResultsComparisonAxesAndDecisionRule")
        or comparator.get("mandatoryFloorsCanonicalSha256")
        != canonical_values.get("mandatoryFloorsAndMissingDataRules")
        or comparator.get("strictBurdenAdvantage") is not True
        or comparator.get("stoppedReceiptHiddenByAggregate") is not False
    ):
        reject("comparator cohort, decision rule, or result changed")

    if (
        external.get("sourceRegistration") != _CONTINUATION_REGISTRATION
        or external.get("externalSubstrateCohortCanonicalSha256")
        != canonical_values.get(
            "externalSubstrateCohortSourcesVersionsLicensesOrTermsMaturityAndReuseBoundaries"
        )
        or external.get("layersReused")
        != [
            "Codex host and native context lifecycle",
            "Git repository identity and delivery",
            "CHAP collaboration-wire concepts",
            "Human Tool human-allocation pattern",
            "NIST AI 800-2 evaluation probes",
        ]
        or external.get("harnessOwnedResidual")
        != (
            "demand-to-capability methodology, open minimum quality-conformance "
            "profile, and thin reference adapters"
        )
        or external.get("sufficientExternalLayerRemovedResidualValue") is not False
        or external.get("reauthoredProtocolRuntimeIdentityAuditOrEvaluator") is not False
    ):
        reject("external comparison or reuse decision changed")

    expected_scenario_limits = [
        "public support and contribution intake for zero-knowledge users",
        "Codex plugin Skill reference-adapter delivery",
        "host-neutral continuation-reconciliation adapter implementation",
    ]
    if (
        applicability.get("host") != "OpenAI Codex CLI 0.147.0 on Windows"
        or applicability.get("profile") != "software engineering"
        or applicability.get("acceptedScenarioClasses") != expected_scenario_limits
        or applicability.get("stoppedScenarioClass")
        != (
            "long-horizon software-product continuity through Agent-owned "
            "conversation rollover"
        )
        or applicability.get("sourcesAsOf") != "2026-08-14"
        or applicability.get("namedHuman") != "yiheng8023"
    ):
        reject("applicability limits or human identity changed")

    floor_names = {
        "outcomeQuality",
        "userOrchestrationBurden",
        "taskTopologyLifecycleAndBurden",
        "intentCommunicationAndDecisionCompleteness",
        "routeReliabilityRecoveryTimeAndCallCost",
        "authoritySafetyEvidenceAndResidue",
        "resourceContinuityContextAndProcessCost",
        "contextCarrierFitnessObservationsAndTransitions",
        "referenceHostContextLifecycleTransitionAndRecovery",
        "comparatorOutcomeAndProcessResults",
        "externalComparisonAndReuseDecision",
    }
    if (
        set(floors) != floor_names | {"applicabilityLimitsAndHumanDecision", "missingData"}
        or any(floors.get(name) != "pass" for name in floor_names)
    ):
        reject("one or more mandatory machine floors changed or failed")

    expected_claims = [
        (
            "At most the unchanged candidate.5 methodology and minimum profile are "
            "calibrated on OpenAI Codex CLI 0.147.0 on Windows for the exact three "
            "accepted scenario classes and one stopped plugin-rollover case on 2026-08-14."
        ),
        (
            "The comparison demonstrates only a bounded advantage in registered user "
            "orchestration burden and cross-layer continuation coherence against the "
            "fixed task comparators."
        ),
        (
            "The stopped receipt remains failed on missing native Hook chronology; no "
            "installed-plugin, general context-management, universal-superiority, release, "
            "publication, production, or v0.2 completion claim is made."
        ),
        (
            "This O4 calibration does not establish Agent-neutral or cross-host "
            "portability; O5 remains separate and false."
        ),
    ]
    if document.get("claimLimits") != expected_claims:
        reject("claim ceiling changed or broadened")

    if require_human:
        decision_locator = (
            "codex://threads/019ffaa8-b44a-7bf2-97de-65875bceec33/"
            "messages/by-content-sha256/"
            + _CODEX_CALIBRATION_ACCEPTANCE_MESSAGE_SHA256
        )
        decision_identity = "sha256:" + _CODEX_CALIBRATION_ACCEPTANCE_MESSAGE_SHA256
        combined_identity = "sha256:" + hashlib.sha256(
            (
                _CODEX_CALIBRATION_INPUT_IDENTITY.removeprefix("sha256:")
                + "\n"
                + _CODEX_CALIBRATION_ACCEPTANCE_MESSAGE_SHA256
                + "\n"
            ).encode()
        ).hexdigest()
        if (
            authority.get("decisionState") != "accepted"
            or result.get("state") != "accepted"
            or result.get("accepted") is not True
            or result.get("humanJudgment")
            != (
                "accepted methodology, profile, mixed calibration, applicability, "
                "and bounded O4 claim"
            )
            or result.get("machineComparisonPassed") is not True
            or not result.get("profileDisposition", "").startswith(
                "candidate.5 bytes and semantics remain immutable; accepted"
            )
            or source.get("identityWithHumanDecision") != combined_identity
            or applicability.get("accepted") is not True
            or applicability.get("decisionMessageLocator") != decision_locator
            or applicability.get("decisionMessageIdentity") != decision_identity
            or applicability.get("acceptedMethodologyAndProfile") is not True
            or applicability.get("acceptedMixedCalibration") is not True
            or applicability.get("acceptedApplicabilityAndBoundedO4Claim") is not True
            or floors.get("applicabilityLimitsAndHumanDecision") != "pass"
            or floors.get("missingData") != []
            or document.get("validator", {}).get("state") != "accepted"
        ):
            reject("named-human methodology, profile, calibration, or bounded O4 decision is absent")
    else:
        if (
            authority.get("decisionState") != "pending"
            or result.get("state") != "machine-eligible-human-pending"
            or result.get("accepted") is not None
            or result.get("humanJudgment") != "pending"
            or result.get("machineComparisonPassed") is not True
            or source.get("identityWithHumanDecision") is not None
            or applicability.get("accepted") is not None
            or any(
                applicability.get(name) is not None
                for name in (
                    "decisionMessageLocator",
                    "decisionMessageIdentity",
                    "acceptedMethodologyAndProfile",
                    "acceptedMixedCalibration",
                    "acceptedApplicabilityAndBoundedO4Claim",
                )
            )
            or floors.get("applicabilityLimitsAndHumanDecision") != "pending"
            or floors.get("missingData")
            != [
                "named-human methodology, profile, mixed-calibration, applicability, and bounded O4 judgment"
            ]
            or document.get("validator", {}).get("state")
            != "machine-eligible-human-pending"
        ):
            reject("pending human gate was hidden or pre-accepted")

    return len(errors) == before


def _validate_codex_reference_calibration_o4(
    document: dict[str, Any], criterion_id: str, root: Path, errors: list[str]
) -> bool:
    if criterion_id != "O4":
        _error(errors, "Codex reference calibration evidence used for non-O4 criterion")
        return False
    return _validate_codex_reference_calibration_o4_candidate(
        document, root, errors, require_human=True
    )


SUPPORTED_EVIDENCE_VALIDATORS: Mapping[str, EvidenceValidatorSpec] = MappingProxyType(
    {
        "public-intake-zero-knowledge-o1": (
            frozenset({"O1"}),
            frozenset({_PUBLIC_INTAKE_INCREMENT_ID}),
            _validate_public_intake_o1,
        ),
        "codex-demand-skill-plugin-o1": (
            frozenset({"O1"}),
            frozenset({_CODEX_SKILL_INCREMENT_ID}),
            _validate_codex_skill_o1,
        ),
        "claude-demand-skill-plugin-o1-o3": (
            frozenset({"O1", "O3"}),
            frozenset({_CLAUDE_SKILL_INCREMENT_ID}),
            _validate_claude_skill_o1_o3,
        ),
        "continuation-reconciliation-o2": (
            frozenset({"O2"}),
            frozenset({_CONTINUATION_INCREMENT_ID}),
            _validate_continuation_reconciliation_o2,
        ),
        "codex-reference-calibration-o4": (
            frozenset({"O4"}),
            frozenset({_CODEX_CALIBRATION_INCREMENT_ID}),
            _validate_codex_reference_calibration_o4,
        ),
    }
)

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
    if not isinstance(milestones, list) or len(milestones) != 1:
        _error(errors, "constitution must retain exactly one historical milestone")
    elif not _same_typed_value(milestones[0], EXPECTED_HISTORICAL_MILESTONE):
        _error(
            errors,
            "constitution historical milestone must match the code-owned record",
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
            if not candidate.read_text(encoding="utf-8").strip():
                _error(errors, f"supporting document is empty: {relative}")
        except (OSError, UnicodeError):
            _error(errors, f"supporting document cannot be inspected: {relative}")
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
    errors: list[str],
) -> bool:
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
        return len(errors) == before
    if not isinstance(binding, dict) or set(binding) != TASK_REGISTRATION_BINDING_FIELDS:
        _error(
            errors,
            f"outcome-bearing increment {increment_id} requires an exact taskRegistration binding",
        )
        return False
    locator = _relative_locator(binding.get("locator"), allow_evidence=True)
    registration_path = PurePosixPath(locator) if locator is not None else None
    if (
        registration_path is None
        or registration_path.parent != PurePosixPath("product/evidence")
        or not registration_path.name.endswith("-registration.json")
    ):
        _error(errors, f"increment {increment_id} has invalid taskRegistration locator")
        return False
    candidate = _inside_root(root, locator, errors, "task registration")
    if candidate is None:
        return False
    try:
        raw = candidate.read_bytes()
    except OSError as exc:
        _error(errors, f"cannot read task registration {locator}: {exc.__class__.__name__}")
        return False
    expected_sha256 = binding.get("sha256")
    if (
        not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        or hashlib.sha256(raw).hexdigest() != expected_sha256
    ):
        _error(errors, f"increment {increment_id} taskRegistration identity mismatch")
        return False
    registration = _load_json(candidate, f"task registration {locator}", errors)
    if set(registration) != TASK_REGISTRATION_FIELDS:
        _error(errors, f"task registration {locator} fields must match the code-owned schema")
        return False
    criterion_ids = _string_list(registration.get("criterionIds"))
    source_capture = registration.get("sourceCaptureEligibilityAndStopRule")
    acceptance_authority = registration.get("acceptanceAuthority")
    floors = registration.get("qualitySafetyEvidenceAndResidueFloors")
    values = registration.get("preRegistrationValues")
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
        and _rfc3339_instant(registration.get("registeredAt")) is not None
        and _nonempty_text(registration.get("taskIdentity"))
        and registration.get("incrementId") == increment_id
        and criterion_ids == mapped_outcomes
        and isinstance(values, dict)
        and set(values) == expected_fields
        and all(_substantive_registration_value(item) for item in values.values())
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
    return len(errors) == before


def _process_loss_guardrail(
    root: Path,
    increments: list[dict[str, Any]],
    criteria: Mapping[str, dict[str, Any]],
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
        _task_registration_guardrail(root, increment, criteria, errors)
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
        if not isinstance(cleanup, dict) or set(cleanup) != CLEANUP_BOUNDARY_FIELDS:
            _error(
                errors,
                f"increment {increment_id} requires the exact cleanup boundary fields",
            )
            continue
        paths = cleanup.get("repositoryTemporaryPaths")
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
        root, increments, criteria, validated_work_outcomes, errors
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
        "programStatus": program.get("status"),
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

    cache_token = _EVIDENCE_GIT_CACHE.set({})
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
                "activeIncrement": None,
                "outcomes": {"verified": 0, "total": len(OUTCOME_IDS)},
                "guardrails": {"passed": 0, "total": len(GUARDRAIL_IDS)},
                "criterionStates": {
                    key: False for key in sorted(EXPECTED_CRITERION_IDS)
                },
                "errors": [f"verifier failed closed: {exc.__class__.__name__}"],
            }
    finally:
        _EVIDENCE_GIT_CACHE.reset(cache_token)
