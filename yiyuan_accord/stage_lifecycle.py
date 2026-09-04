"""Pure validation for post-v3.1 maintenance-stage transitions."""

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Iterable, Mapping, Optional, Sequence, Tuple


SNAPSHOT_V3_SCHEMA = "yiyuan-accord-stage-closeout-snapshot/v3"
SNAPSHOT_LOCATOR = "product/program.json#/maintenanceCycle/closeoutSnapshot"
LEGACY_SNAPSHOT_LOCATOR = "product/program.json#/increment/closeoutSnapshot"
MIGRATION_PREDECESSOR_REF = (
    "299ae4011b0e48df586a137a2fbdcaff715e55c7:" + LEGACY_SNAPSHOT_LOCATOR
)

MIGRATION_CHANGED_PATHS = (
    "product/program.json",
    "product/acceptance.json",
    "product/reshaping-guidance.json",
    "docs/architecture.md",
    "docs/operations/CONTINUATION.md",
    "yiyuan_accord/control.py",
    "yiyuan_accord/evidence.py",
    "yiyuan_accord/identity.py",
    "yiyuan_accord/stage_lifecycle.py",
    "tests/product/test_product_control.py",
    "tests/product/test_stage_lifecycle.py",
)
PRESENTATION_CHANGED_PATHS = (
    "product/program.json",
    "README.md",
    "README.zh-CN.md",
)
PRESENTATION_SURFACE_SHA256 = {
    "README.md": "7bf61e8b2f60b675175d3452691c88a1ba5236bd1281afe29fb806ca5826a96b",
    "README.zh-CN.md": "02be78cb5157d3eef4a13bf48ff14bc0333a80f6d22dd236f06bcd2631e73f9e",
}
MIGRATION_COMPLEXITY_LIMIT = 960000
MIGRATION_COMPLEXITY_CALIBRATION_RULE = (
    "The 960000-byte product-code-and-test ceiling is a bounded allowance for "
    "the schema-v3 stage-lifecycle migration, committed-lineage integration "
    "and fail-closed carry coverage only; it is not a general growth "
    "entitlement. The verifier still requires at least five percent "
    "code-and-test headroom and at least three tracked-file slots, and later "
    "work must justify, reduce, replace or retire lifecycle cost rather than "
    "consume the allowance by default."
)
MIGRATION_Q4_LATEST_ASSESSMENT_BOUNDARY = (
    "Repository-candidate disposition is lifecycle-derived: active/reopened "
    "plus continuing criteria means reacceptance is incomplete; ready/closed "
    "plus all verified criteria means the state-only close is complete but "
    "remains only a review subject. The post-v3.1 maintenance cycle has no "
    "release intent and is candidate-ineligible; it cannot borrow the "
    "completed release ledger or establish a future candidate. The "
    "code-and-test ceiling is 960000 bytes for the schema-v3 maintenance "
    "transition, committed-lineage integration and fail-closed carry coverage; "
    "the current measurement must retain at least five percent headroom and "
    "the ceiling is not general growth allowance. Exact 7a3950e retains "
    "bounded schema-v6 zero-model lifecycle mechanics; exact f4c0251 and the "
    "admitted schema-v7 v5 record verify the bounded Agent-recovery replay. "
    "The bounded sequence closes the successor baseline, then repository "
    "presentation, then activates a read-only whole-system review; "
    "maintenanceCycle machine fields are the current-boundary authority, and "
    "implementation authority remains absent."
)

_MIGRATION = "transition-contract-migration"
_PRESENTATION = "repository-presentation"
_KINDS = frozenset({_MIGRATION, _PRESENTATION})
_CRITERION_IDS = ("R1", "R2", "R3", "R4", "Q1", "Q2", "Q3", "Q4")
_PRESENTATION_CRITERION_IDS = ("R1", "R4", "Q2", "Q3", "Q4")
_V2_SCHEMA = "yiyuan-accord-stage-closeout-snapshot/v2"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SNAPSHOT_REF_RE = re.compile(
    r"^[0-9a-f]{40}:product/program\.json#/maintenanceCycle/closeoutSnapshot$"
)
_NODE_FIELDS = frozenset((
    "schema id stage state revisionBinding predecessorSnapshotRef authorityRefs "
    "surfaceRefs evidenceRefs evidenceCutoff invalidationTriggerRefs "
    "acceptanceTransition evaluationContractSha256 closedGateId nextGateId "
    "cycle claimCeilingRef unknownsRef"
).split())
_TRANSITION_FIELDS = frozenset({
    "kind", "rationaleRef", "affectedCriterionIds", "processRef", "changedPaths",
})
_PRESENTATION_TRANSITION_FIELDS = frozenset({
    *_TRANSITION_FIELDS, "surfaceSha256",
})
_CYCLE = {
    "id": "post-v3.1-maintenance",
    "kind": "maintenance",
    "contractRef": "product/program.json#/maintenanceCycle",
    "releaseBasisRef": "product/program.json#/historicalRelease",
    "releaseIntent": None,
    "candidateEligible": False,
}
_REVISION_BINDING = {
    "kind": "containing-git-commit",
    "selfLocator": SNAPSHOT_LOCATOR,
    "exactLocatorRule": (
        "After commit, prefix selfLocator with the immutable containing commit "
        "SHA; never store that SHA inside this object."
    ),
}
_AUTHORITY_REFS = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
)
_SURFACE_REFS = {
    "baseline": "product/reshaping-guidance.json#/wholeSystemBalanceReview",
    "plan": "product/program.json#/maintenanceCycle/plan",
    "process": "product/program.json#/maintenanceCycle/orderedTransitions",
    "acceptance": "product/acceptance.json#/criteria",
    "goalProjection": "product/program.json#/maintenanceCycle/goalProjection",
}
_EVIDENCE_REFS = (
    "product/program.json#/inputEvidence",
    "product/acceptance.json#/criteria",
    "evals/golden-tasks.json",
    "product/program.json#/historicalRelease",
)
_EVIDENCE_CUTOFF = {
    "kind": "containing-git-commit",
    "rule": (
        "Only evidenceRefs resolved inside the immutable containing commit belong "
        "to this snapshot; later repository or task-time facts require a successor "
        "node."
    ),
}
_INVALIDATION_REFS = (
    "product/constitution.json#/evolutionPolicy/feedbackRule",
    "product/program.json#/maintenanceCycle/refreshTriggers",
    "product/program.json#/processLossControl/correctionRule",
)
_RATIONALE_REF = "product/program.json#/maintenanceCycle/plan"
_PROCESS_REF = "product/program.json#/maintenanceCycle/orderedTransitions"
_CLAIM_CEILING_REF = "product/acceptance.json#/claimCeiling"
_UNKNOWNS_REF = "product/program.json#/maintenanceCycle/unknowns"

_MAINTENANCE_SCHEMA = "yiyuan-accord-maintenance-cycle/v1"
_MAINTENANCE_FIELDS = frozenset({
    "schema", "id", "kind", "state", "releaseBasisRef", "releaseIntent",
    "candidateEligible", "plan", "orderedTransitions", "currentBoundaryId",
    "goalProjection", "unknowns", "refreshTriggers", "closeoutSnapshot",
})
_PLAN = {
    "outcome": (
        "close-two-batch-post-v3.1-maintenance-then-stop-at-review-only-boundary"
    ),
    "allowedScope": [
        "transition-contract-migration",
        "bilingual-repository-presentation",
        "whole-system-read-only-review",
    ],
    "excludedScope": [
        "main-mutation",
        "tag-or-release",
        "grok-zcode-or-host-adapter-implementation",
        "runtime-skill-or-hook-functionality-change",
        "whole-system-review-follow-on-implementation",
    ],
    "finiteStopCondition": (
        "the exact two maintenance transitions pass and whole-system-review "
        "remains review-only with implementation authority absent"
    ),
}
_GOAL_PROJECTION_BASE = {
    "outcome": (
        "complete-bounded-post-v3.1-maintenance-without-release-or-feature-implementation"
    ),
    "repositoryRef": "product/constitution.json#/identity/repository",
    "branch": "phase/post-v3.1-successor",
    "baseRevision": "299ae4011b0e48df586a137a2fbdcaff715e55c7",
    "mainMutation": False,
    "postPresentationMode": "whole-system-review-only",
    "implementationAuthority": "absent",
}
_UNKNOWNS = [
    "current-host-entry-instance-behavior",
    "macos-linux-field-behavior",
    "future-host-compatibility",
    "runtime-need",
    "minimum-sufficient-skill-hook-set",
]
_REFRESH_TRIGGERS = [
    "user-correction",
    "material-evidence-change",
    "host-client-or-extension-drift",
    "cycle-scope-or-authority-change",
    "validation-or-hosted-ci-failure",
]
_TRANSITION_SPECS = (
    {
        "id": "successor-baseline",
        "dependsOn": [],
        "acceptanceIds": list(_CRITERION_IDS),
        "stopCondition": (
            "exact-299ae401-predecessor-v3-lineage-valid-and-release-package-history-frozen"
        ),
    },
    {
        "id": "repository-presentation",
        "dependsOn": ["successor-baseline"],
        "acceptanceIds": list(_PRESENTATION_CRITERION_IDS),
        "targetArtifacts": dict(PRESENTATION_SURFACE_SHA256),
        "stopCondition": (
            "only-lifecycle-bookkeeping-plus-the-two-preauthorized-readme-blobs-change"
        ),
    },
    {
        "id": "whole-system-review",
        "dependsOn": ["repository-presentation"],
        "acceptanceIds": list(_CRITERION_IDS),
        "targetArtifacts": {},
        "stopCondition": (
            "read-only-review-produces-one-evidence-bound-next-decision-or-no-op-"
            "and-authorizes-no-implementation"
        ),
    },
)
_PROGRESS_BY_KIND = {
    _MIGRATION: (
        ("completed", "active", "pending"),
        "repository-presentation",
        "successor-baseline",
        "repository-presentation",
    ),
    _PRESENTATION: (
        ("completed", "completed", "active"),
        "whole-system-review",
        "repository-presentation",
        "whole-system-review",
    ),
}


@dataclass(frozen=True)
class StageTransitionDecision:
    """Structured result; callers need not parse error text."""

    observation_categories: Tuple[str, ...]
    changed_paths: Tuple[str, ...]
    affected_criterion_ids: Tuple[str, ...]
    candidate_eligible: bool
    errors: Tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors


def _evaluation_contract_sha256(acceptance: Mapping, golden: Mapping) -> str:
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
            and isinstance(item.get("requiredEvidenceClasses"), list)
            and "representative-behavior" in item.get(
                "requiredEvidenceClasses", []
            )
        ] if isinstance(criteria, list) else [],
        "evaluationProtocol": golden.get("evaluationProtocol"),
        "metrics": golden.get("metrics"),
    }
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _documents(value: Sequence[Mapping]) -> Optional[Tuple[Mapping, ...]]:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or len(value) != 5
        or any(not isinstance(item, dict) for item in value)
    ):
        return None
    return tuple(value)


def _snapshot(program: Mapping) -> Optional[Mapping]:
    if "maintenanceCycle" in program:
        cycle = program.get("maintenanceCycle")
        node = cycle.get("closeoutSnapshot") \
            if isinstance(cycle, dict) else None
        return node if isinstance(node, dict) else None
    increment = program.get("increment")
    node = increment.get("closeoutSnapshot") \
        if isinstance(increment, dict) else None
    return node if isinstance(node, dict) else None


def _program_without_snapshot(program: Mapping) -> Mapping:
    normalized = dict(program)
    cycle = program.get("maintenanceCycle")
    if isinstance(cycle, dict):
        normalized_cycle = dict(cycle)
        normalized_cycle.pop("closeoutSnapshot", None)
        normalized["maintenanceCycle"] = normalized_cycle
    return normalized


def _normalized_paths(paths: Iterable[object]) -> Optional[Tuple[str, ...]]:
    if isinstance(paths, (str, bytes)):
        return None
    try:
        values = tuple(paths)
    except TypeError:
        return None
    normalized = []
    for value in values:
        if not isinstance(value, str):
            return None
        path = value.replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        if (
            not path or path.startswith("/") or re.match(r"^[A-Za-z]:/", path)
            or any(part in ("", ".", "..") for part in path.split("/"))
        ):
            return None
        normalized.append(path)
    if len(normalized) != len(set(normalized)):
        return None
    return tuple(normalized)


def _normalized_surface_sha256(value: Optional[Mapping]) -> Optional[Mapping]:
    if value is None:
        return {}
    if not isinstance(value, dict) or any(
        not isinstance(path, str)
        or not isinstance(digest, str)
        or _SHA256_RE.fullmatch(digest) is None
        for path, digest in value.items()
    ):
        return None
    normalized = {}
    for path, digest in value.items():
        paths = _normalized_paths((path,))
        if paths is None or paths[0] in normalized:
            return None
        normalized[paths[0]] = digest
    return normalized


def _acceptance_without_complexity_assessment(acceptance: Mapping) -> Mapping:
    normalized = deepcopy(acceptance)
    criteria = normalized.get("criteria")
    if isinstance(criteria, list):
        for criterion in criteria:
            if isinstance(criterion, dict) and criterion.get("id") == "Q4":
                criterion.pop("latestAssessmentBoundary", None)
    return normalized


def _migration_complexity_calibration_is_exact(
    program: Mapping, acceptance: Mapping,
) -> bool:
    budget = program.get("complexityBudget")
    targets = budget.get("targets") if isinstance(budget, dict) else None
    criteria = acceptance.get("criteria")
    q4 = [
        criterion for criterion in criteria
        if isinstance(criterion, dict) and criterion.get("id") == "Q4"
    ] if isinstance(criteria, list) else []
    return (
        isinstance(targets, dict)
        and targets.get("maxProductCodeAndTestBytes")
        == MIGRATION_COMPLEXITY_LIMIT
        and budget.get("targetCalibrationRule")
        == MIGRATION_COMPLEXITY_CALIBRATION_RULE
        and len(q4) == 1
        and q4[0].get("latestAssessmentBoundary")
        == MIGRATION_Q4_LATEST_ASSESSMENT_BOUNDARY
    )


def _transition_document_errors(
    current: Tuple[Mapping, ...], predecessor: Tuple[Mapping, ...], kind: object,
) -> list:
    errors = []
    constitution, _, acceptance, guidance, golden = current
    prior_constitution, _, prior_acceptance, prior_guidance, prior_golden = (
        predecessor
    )
    if constitution != prior_constitution or golden != prior_golden:
        errors.append("immutable transition documents drifted")
    if kind == _MIGRATION:
        if not _migration_complexity_calibration_is_exact(
            current[1], acceptance,
        ):
            errors.append("migration complexity calibration is invalid")
        if _acceptance_without_complexity_assessment(
            acceptance
        ) != _acceptance_without_complexity_assessment(prior_acceptance):
            errors.append("migration acceptance delta is invalid")
    elif kind == _PRESENTATION:
        if acceptance != prior_acceptance or guidance != prior_guidance:
            errors.append("presentation authority documents drifted")
    return errors


def _maintenance_cycle_errors(program: Mapping, kind: Optional[str]) -> list:
    errors = []
    cycle = program.get("maintenanceCycle")
    if not isinstance(cycle, dict) or set(cycle) != _MAINTENANCE_FIELDS:
        return ["maintenance cycle contract is invalid"]
    if (
        cycle.get("schema") != _MAINTENANCE_SCHEMA
        or cycle.get("id") != _CYCLE["id"]
        or cycle.get("kind") != _CYCLE["kind"]
        or cycle.get("state") != "active"
        or cycle.get("releaseBasisRef") != _CYCLE["releaseBasisRef"]
        or cycle.get("releaseIntent") is not None
        or cycle.get("candidateEligible") is not False
        or cycle.get("plan") != _PLAN
        or cycle.get("unknowns") != _UNKNOWNS
        or cycle.get("refreshTriggers") != _REFRESH_TRIGGERS
    ):
        errors.append("maintenance cycle contract is invalid")
    progress = _PROGRESS_BY_KIND.get(kind)
    transitions = cycle.get("orderedTransitions")
    if progress is None:
        errors.append("maintenance transition kind is invalid")
        return errors
    states, current_boundary, _, _ = progress
    if not isinstance(transitions, list) or len(transitions) != len(
        _TRANSITION_SPECS
    ):
        errors.append("maintenance transition sequence is invalid")
    else:
        for index, (transition, spec, state) in enumerate(zip(
            transitions, _TRANSITION_SPECS, states,
        )):
            expected = {**spec, "state": state}
            if transition != expected:
                errors.append(
                    f"maintenance transition sequence[{index}] is invalid"
                )
    goal = cycle.get("goalProjection")
    expected_goal = {
        **_GOAL_PROJECTION_BASE,
        "currentBoundaryId": current_boundary,
    }
    if (
        cycle.get("currentBoundaryId") != current_boundary
        or goal != expected_goal
    ):
        errors.append("maintenance goal projection is invalid")
    return errors


def _node_errors(program: Mapping, acceptance: Mapping, golden: Mapping) -> list:
    errors = []
    node = _snapshot(program)
    if not isinstance(node, dict):
        return ["snapshot shape is invalid"]
    if set(node) != _NODE_FIELDS:
        return ["snapshot shape is invalid"]
    transition = node.get("acceptanceTransition")
    kind = transition.get("kind") if isinstance(transition, dict) else None
    progress = _PROGRESS_BY_KIND.get(kind)
    stage = progress[2] if progress is not None else None
    next_gate = progress[3] if progress is not None else None
    if (
        node.get("schema") != SNAPSHOT_V3_SCHEMA
        or stage is None
        or node.get("id") != f"stage.post-v3.1-maintenance.{stage}.closed"
        or node.get("stage") != stage
        or node.get("state") != "closed"
        or node.get("closedGateId") != stage
        or node.get("nextGateId") != next_gate
    ):
        errors.append("snapshot identity is invalid")
    if node.get("revisionBinding") != _REVISION_BINDING:
        errors.append("revision binding is invalid")
    if node.get("authorityRefs") != list(_AUTHORITY_REFS):
        errors.append("authority references are invalid")
    if node.get("surfaceRefs") != _SURFACE_REFS:
        errors.append("surface references are invalid")
    if (
        node.get("evidenceRefs") != list(_EVIDENCE_REFS)
        or node.get("evidenceCutoff") != _EVIDENCE_CUTOFF
        or node.get("invalidationTriggerRefs") != list(_INVALIDATION_REFS)
    ):
        errors.append("evidence references are invalid")
    if (
        node.get("cycle") != _CYCLE
        or node.get("claimCeilingRef") != _CLAIM_CEILING_REF
        or node.get("unknownsRef") != _UNKNOWNS_REF
    ):
        errors.append("maintenance cycle is invalid")
    errors.extend(_maintenance_cycle_errors(program, kind))
    digest = node.get("evaluationContractSha256")
    if (
        not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None
        or digest != _evaluation_contract_sha256(acceptance, golden)
    ):
        errors.append("evaluation contract digest is invalid")
    expected_transition_fields = _PRESENTATION_TRANSITION_FIELDS \
        if kind == _PRESENTATION else _TRANSITION_FIELDS
    if (
        not isinstance(transition, dict)
        or set(transition) != expected_transition_fields
    ):
        errors.append("acceptance transition shape is invalid")
        return errors
    expected_affected = _CRITERION_IDS if kind == _MIGRATION \
        else _PRESENTATION_CRITERION_IDS
    expected_paths = MIGRATION_CHANGED_PATHS \
        if kind == _MIGRATION else PRESENTATION_CHANGED_PATHS
    if (
        kind not in _KINDS
        or transition.get("rationaleRef") != _RATIONALE_REF
        or transition.get("processRef") != _PROCESS_REF
        or transition.get("affectedCriterionIds") != list(expected_affected)
        or transition.get("changedPaths") != list(expected_paths)
    ):
        errors.append("acceptance transition is invalid")
    if kind == _PRESENTATION and transition.get(
        "surfaceSha256"
    ) != PRESENTATION_SURFACE_SHA256:
        errors.append("presentation surface authorization is invalid")
    return errors


def _frozen_release_errors(current: Tuple[Mapping, ...],
                           predecessor: Tuple[Mapping, ...]) -> list:
    errors = []
    program, acceptance = current[1], current[2]
    prior_program, prior_acceptance = predecessor[1], predecessor[2]
    if (
        not isinstance(program.get("historicalRelease"), dict)
        or program.get("historicalRelease") != prior_program.get(
            "historicalRelease"
        )
    ):
        errors.append("historical release is not frozen")
    if (
        not all(isinstance(program.get(key), str) for key in (
            "release", "distributionVersion",
        ))
        or any(program.get(key) != prior_program.get(key) for key in (
            "release", "distributionVersion",
        ))
    ):
        errors.append("release identity is not frozen")
    if (
        not isinstance(acceptance.get("publicRelease"), dict)
        or acceptance.get("publicRelease") != prior_acceptance.get(
            "publicRelease"
        )
    ):
        errors.append("public release is not frozen")
    if (
        not isinstance(program.get("hostProjections"), list)
        or program.get("hostProjections") != prior_program.get("hostProjections")
    ):
        errors.append("host projections are not frozen")
    increment = program.get("increment")
    prior_increment = prior_program.get("increment")
    lifecycle = increment.get("exactPackageEvidenceLifecycle") \
        if isinstance(increment, dict) else None
    prior_lifecycle = prior_increment.get("exactPackageEvidenceLifecycle") \
        if isinstance(prior_increment, dict) else None
    if not isinstance(lifecycle, dict) or lifecycle != prior_lifecycle:
        errors.append("exact-package evidence lifecycle is not frozen")
    if _release_basis_projection(program) != _release_basis_projection(
        prior_program
    ):
        errors.append("v3.1 release-basis program surfaces are not frozen")
    return errors


def _release_basis_projection(program: Mapping) -> Mapping:
    increment = deepcopy(program.get("increment"))
    return {
        "increment": increment,
        "goalModePrompt": program.get("goalModePrompt"),
        "releaseProcedure": program.get("releaseProcedure"),
    }


def _program_without_presentation_progress(program: Mapping) -> Mapping:
    normalized = deepcopy(program)
    increment = normalized.get("increment")
    if isinstance(increment, dict):
        increment.pop("closeoutSnapshot", None)
    cycle = normalized.get("maintenanceCycle")
    if isinstance(cycle, dict):
        cycle.pop("closeoutSnapshot", None)
        cycle.pop("currentBoundaryId", None)
        goal = cycle.get("goalProjection")
        if isinstance(goal, dict):
            goal.pop("currentBoundaryId", None)
        transitions = cycle.get("orderedTransitions")
        if isinstance(transitions, list):
            for transition in transitions:
                if isinstance(transition, dict):
                    transition.pop("state", None)
    return normalized


def closed_maintenance_snapshot_errors(
    program: Mapping, acceptance: Mapping, golden: Mapping,
) -> Tuple[str, ...]:
    """Check the complete local v3 shape without claiming Git lineage."""

    if not all(isinstance(item, dict) for item in (
        program, acceptance, golden,
    )):
        return ("maintenance snapshot documents are invalid",)
    errors = list(_node_errors(program, acceptance, golden))
    increment = program.get("increment")
    node = _snapshot(program)
    if (
        not isinstance(increment, dict)
        or increment.get("state") != "completed"
        or program.get("status") != "active"
    ):
        errors.append("maintenance program state is invalid")
    if not isinstance(node, dict):
        return tuple(errors)
    transition = node.get("acceptanceTransition")
    kind = transition.get("kind") if isinstance(transition, dict) else None
    predecessor_ref = node.get("predecessorSnapshotRef")
    valid_predecessor = (
        kind == _MIGRATION
        and predecessor_ref == MIGRATION_PREDECESSOR_REF
    ) or (
        kind == _PRESENTATION
        and isinstance(predecessor_ref, str)
        and _SNAPSHOT_REF_RE.fullmatch(predecessor_ref) is not None
    )
    if not valid_predecessor:
        errors.append("maintenance snapshot predecessor is invalid")
    return tuple(errors)


def is_structurally_valid_closed_maintenance_snapshot(
    program: Mapping, acceptance: Mapping, golden: Mapping,
) -> bool:
    return not closed_maintenance_snapshot_errors(program, acceptance, golden)


def evaluate_stage_transition(
    current_documents: Sequence[Mapping],
    predecessor_documents: Optional[Sequence[Mapping]] = None,
    changed_paths: Iterable[object] = (),
    changed_surface_sha256: Optional[Mapping] = None,
) -> StageTransitionDecision:
    """Evaluate one v3 maintenance transition without repository I/O."""

    errors = []
    current = _documents(current_documents)
    predecessor = _documents(predecessor_documents) \
        if predecessor_documents is not None else None
    observed_paths = _normalized_paths(changed_paths)
    observed_surface_sha256 = _normalized_surface_sha256(
        changed_surface_sha256
    )
    if current is None:
        errors.append("current transition documents are invalid")
    if predecessor is None:
        errors.append("predecessor transition documents are invalid")
    if observed_paths is None:
        errors.append("observed changed paths are malformed")
        observed_paths = ()
    if observed_surface_sha256 is None:
        errors.append("observed surface digests are malformed")
        observed_surface_sha256 = {}
    if current is None or predecessor is None:
        return StageTransitionDecision(
            ("invalid-transition",), tuple(observed_paths), (), False,
            tuple(errors),
        )

    program, acceptance, golden = current[1], current[2], current[4]
    node = _snapshot(program)
    if node is None:
        errors.append("snapshot is unavailable")
        return StageTransitionDecision(
            ("invalid-transition",), tuple(observed_paths), (), False,
            tuple(errors),
        )
    errors.extend(closed_maintenance_snapshot_errors(
        program, acceptance, golden,
    ))
    transition = node.get("acceptanceTransition")
    transition = transition if isinstance(transition, dict) else {}
    kind = transition.get("kind")
    affected = transition.get("affectedCriterionIds")
    affected = tuple(affected) if isinstance(affected, list) and all(
        isinstance(item, str) for item in affected
    ) else ()

    prior_program = predecessor[1]
    prior_node = _snapshot(prior_program)
    predecessor_ref = node.get("predecessorSnapshotRef")
    if kind == _MIGRATION:
        if (
            predecessor_ref != MIGRATION_PREDECESSOR_REF
            or not isinstance(prior_node, dict)
            or prior_node.get("schema") != _V2_SCHEMA
            or prior_node.get("state") != "closed"
        ):
            errors.append("migration predecessor is invalid")
    elif kind == _PRESENTATION:
        prior_transition = prior_node.get("acceptanceTransition") \
            if isinstance(prior_node, dict) else None
        predecessor_errors = closed_maintenance_snapshot_errors(
            prior_program, predecessor[2], predecessor[4],
        )
        if (
            not isinstance(predecessor_ref, str)
            or _SNAPSHOT_REF_RE.fullmatch(predecessor_ref) is None
            or not isinstance(prior_node, dict)
            or prior_node.get("schema") != SNAPSHOT_V3_SCHEMA
            or prior_node.get("cycle") != _CYCLE
            or not isinstance(prior_transition, dict)
            or prior_transition.get("kind") != _MIGRATION
            or predecessor_errors
        ):
            errors.append("presentation predecessor is invalid")
        if observed_surface_sha256 != PRESENTATION_SURFACE_SHA256:
            errors.append("observed presentation surface digests are invalid")
        if _program_without_presentation_progress(
            program
        ) != _program_without_presentation_progress(prior_program):
            errors.append("presentation program delta is invalid")
    if kind != _PRESENTATION and observed_surface_sha256:
        errors.append("unexpected transition surface digests")

    errors.extend(_frozen_release_errors(current, predecessor))
    errors.extend(_transition_document_errors(current, predecessor, kind))
    if (
        isinstance(prior_node, dict)
        and prior_node.get("evaluationContractSha256")
        != node.get("evaluationContractSha256")
    ):
        errors.append("evaluation contract is not frozen")

    normalized_path_set = set(observed_paths)
    if (
        program != prior_program
        and _program_without_snapshot(program)
        == _program_without_snapshot(prior_program)
    ):
        normalized_path_set.discard("product/program.json")
    expected_paths = MIGRATION_CHANGED_PATHS if kind == _MIGRATION \
        else PRESENTATION_CHANGED_PATHS if kind == _PRESENTATION else ()
    if set(expected_paths) != normalized_path_set:
        errors.append("observed changed paths are invalid")
        normalized_paths = tuple(sorted(normalized_path_set))
    else:
        normalized_paths = tuple(expected_paths)

    categories = ["maintenance-stage", kind or "unknown-transition"]
    categories.append(
        "affected-acceptance" if affected else "no-acceptance-impact"
    )
    categories.append("candidate-ineligible")
    return StageTransitionDecision(
        tuple(categories), normalized_paths, affected, False, tuple(errors),
    )


__all__ = [
    "MIGRATION_COMPLEXITY_CALIBRATION_RULE",
    "MIGRATION_COMPLEXITY_LIMIT",
    "MIGRATION_CHANGED_PATHS",
    "MIGRATION_PREDECESSOR_REF",
    "MIGRATION_Q4_LATEST_ASSESSMENT_BOUNDARY",
    "LEGACY_SNAPSHOT_LOCATOR",
    "PRESENTATION_CHANGED_PATHS",
    "PRESENTATION_SURFACE_SHA256",
    "SNAPSHOT_V3_SCHEMA",
    "StageTransitionDecision",
    "closed_maintenance_snapshot_errors",
    "evaluate_stage_transition",
    "is_structurally_valid_closed_maintenance_snapshot",
]
