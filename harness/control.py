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
