"""Pure validation for repository-external independent review bundles.

The bundle is a task-time input, not a repository observation.  This module
therefore accepts already-loaded values, performs no I/O, and has no locator or
digest vocabulary that could turn a checked-in receipt into self-attestation.
"""

from datetime import datetime
import re


REVIEW_AXES = (
    "product",
    "specification",
    "implementation",
    "standards",
)
REVIEW_BUNDLE_SCHEMA = "yiyuan-accord-external-review-bundle/v1"
DEVELOPMENT_REVIEW_SCHEMA = "yiyuan-accord-development-review-bundle/v1"

_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{40}$")
_UTC_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
_BUNDLE_FIELDS = frozenset(("schema", "subject", "reviews", "decision"))
_SUBJECT_FIELDS = frozenset(("revision", "tree"))
_REVIEW_FIELDS = frozenset((
    "axis",
    "reviewerId",
    "context",
    "subject",
    "reviewedAt",
    "findings",
    "disposition",
    "decision",
))
_CONTEXT_FIELDS = frozenset((
    "isolation", "history", "environment", "accordExposure",
))
_FINDING_FIELDS = frozenset(("severity", "disposition"))
_SEVERITIES = frozenset(("P0", "P1", "P2", "P3"))
_CONTEXT_VALUES = {
    "isolation": ("context-isolated",),
    "history": ("zero-inherited-history", "inherited-history-disclosed"),
    "environment": ("isolated-no-accord", "shared-environment-disclosed"),
    "accordExposure": ("absent", "present-disclosed"),
}


def review_policy_errors(policy):
    """Check explicit review requirements, not their adequacy or authenticity."""
    if (not isinstance(policy, dict)
            or set(policy) != {"requiredAxes", "minimumReviewers", "independentAxes", "contexts", "rule"}
            or not isinstance(policy["rule"], str) or not policy["rule"].strip()
            or not isinstance(policy["requiredAxes"], list)
            or not policy["requiredAxes"]
            or any(v not in REVIEW_AXES for v in policy["requiredAxes"])
            or len(set(policy["requiredAxes"])) != len(policy["requiredAxes"])
            or type(policy["minimumReviewers"]) is not int
            or not 1 <= policy["minimumReviewers"] <= len(policy["requiredAxes"])
            or not isinstance(policy["independentAxes"], list)
            or any(not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1]
                   or any(axis not in policy["requiredAxes"] for axis in pair)
                   for pair in policy["independentAxes"])
            or not isinstance(policy["contexts"], dict)
            or set(policy["contexts"]) != _CONTEXT_FIELDS
            or any(not isinstance(values, list) or not values
                   or any(v not in _CONTEXT_VALUES[k] for v in values)
                   or len(values) != len(set(values))
                   for k, values in policy["contexts"].items())):
        return ["review policy must bind perspectives, reviewer count, disclosed contexts and rationale"]
    return []


def _exact_object(value, fields, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return False
    if set(value) != fields:
        errors.append(f"{label} fields must be exactly {sorted(fields)}")
        return False
    return True


def _object_id(value, label, errors):
    if not isinstance(value, str) or _OBJECT_ID_RE.fullmatch(value) is None:
        errors.append(f"{label} must be a 40-character lowercase hex id")
        return False
    return True


def _subject(value, label, expected_revision, expected_tree, errors):
    if not _exact_object(value, _SUBJECT_FIELDS, label, errors):
        return
    revision_valid = _object_id(value.get("revision"), f"{label}.revision", errors)
    tree_valid = _object_id(value.get("tree"), f"{label}.tree", errors)
    if (
        revision_valid
        and tree_valid
        and (value["revision"], value["tree"])
            != (expected_revision, expected_tree)
    ):
        errors.append(f"{label} does not match exact subject")


def _canonical_utc(value):
    if not isinstance(value, str) or _UTC_RE.fullmatch(value) is None:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def _findings(value, label, errors):
    if not isinstance(value, list):
        errors.append(f"{label} must be a list")
        return
    for index, finding in enumerate(value):
        finding_label = f"{label}[{index}]"
        if not _exact_object(finding, _FINDING_FIELDS, finding_label, errors):
            continue
        severity = finding.get("severity")
        if severity not in _SEVERITIES:
            errors.append(f"{finding_label}.severity must be one of {sorted(_SEVERITIES)}")
        elif severity in {"P0", "P1"}:
            errors.append(f"{finding_label} contains blocking {severity} finding")
        if finding.get("disposition") != "pass":
            errors.append(f"{finding_label}.disposition must be pass")


def evaluate_review_bundle(bundle, subject_revision, subject_tree, *, policy=None):
    """Return deterministic ``errors`` and a fail-closed ``decision``.

    ``subject_revision`` and ``subject_tree`` are the caller's exact candidate
    bindings.  Every independent receipt must bind the same pair.  The function
    deliberately neither discovers Git state nor reads receipt files. A bound
    development policy uses its own schema; omission preserves the historical
    four-reviewer contract. Context disclosures still require caller verification.
    """

    errors = []
    if policy is not None and (errors := review_policy_errors(policy)):
        return {"errors": errors, "decision": "fail"}
    axes_required = REVIEW_AXES if policy is None else policy["requiredAxes"]
    schema = REVIEW_BUNDLE_SCHEMA if policy is None else DEVELOPMENT_REVIEW_SCHEMA
    _object_id(subject_revision, "subject_revision", errors)
    _object_id(subject_tree, "subject_tree", errors)

    if not _exact_object(bundle, _BUNDLE_FIELDS, "bundle", errors):
        return {"errors": errors, "decision": "fail"}
    if bundle.get("schema") != schema:
        errors.append(f"bundle.schema must be {schema}")
    _subject(bundle.get("subject"), "bundle.subject", subject_revision, subject_tree, errors)

    reviews = bundle.get("reviews")
    if not isinstance(reviews, list):
        errors.append("bundle.reviews must be a list")
        reviews = []
    if len(reviews) != len(axes_required):
        errors.append("bundle.reviews must contain exactly four reviews" if policy is None
                      else "bundle.reviews must contain one review per required axis")

    axes = []
    reviewers = []
    assignments = {}
    for index, review in enumerate(reviews):
        label = f"reviews[{index}]"
        if not _exact_object(review, _REVIEW_FIELDS, label, errors):
            continue

        axis = review.get("axis")
        if isinstance(axis, str):
            axes.append(axis)
        reviewer = review.get("reviewerId")
        if (
            isinstance(reviewer, str)
            and reviewer == reviewer.strip()
            and 0 < len(reviewer) <= 128
        ):
            reviewers.append(reviewer)
        else:
            errors.append(f"{label}.reviewerId must be a non-empty external identifier")

        context = review.get("context")
        allowed = ({k: values[:1] for k, values in _CONTEXT_VALUES.items()}
                   if policy is None else policy["contexts"])
        if (not _exact_object(context, _CONTEXT_FIELDS, f"{label}.context", errors)
                or any(context[k] not in values for k, values in allowed.items())
                or (context["environment"] == "isolated-no-accord"
                    and context["accordExposure"] != "absent")):
            errors.append(
                f"{label}.context must declare context-isolated, "
                "zero-inherited-history and isolated-no-accord with absent exposure"
                if policy is None else f"{label}.context differs from the bound review policy"
            )
        if policy is not None and isinstance(reviewer, str):
            if isinstance(axis, str):
                assignments[axis] = reviewer
        _subject(
            review.get("subject"),
            f"{label}.subject",
            subject_revision,
            subject_tree,
            errors,
        )
        if not _canonical_utc(review.get("reviewedAt")):
            errors.append(f"{label}.reviewedAt must be canonical UTC")
        _findings(review.get("findings"), f"{label}.findings", errors)
        if review.get("disposition") != "pass":
            errors.append(f"{label}.disposition must be pass")
        if review.get("decision") != "pass":
            errors.append(f"{label}.decision must be pass")

    if len(axes) != len(axes_required) or set(axes) != set(axes_required):
        errors.append(f"review axes must be exactly {list(axes_required)}")
    if policy is None and (len(reviewers) != len(REVIEW_AXES) or len(set(reviewers)) != len(REVIEW_AXES)):
        errors.append("reviewerId values must be four unique identifiers")
    elif policy is not None and len(set(reviewers)) < policy["minimumReviewers"]:
        errors.append("reviewer count is below the bound review policy")
    if policy is not None and any(assignments.get(a) == assignments.get(b)
                                  for a, b in policy["independentAxes"]):
        errors.append("required independent review axes share a reviewer")
    if bundle.get("decision") != "pass":
        errors.append("bundle.decision must be pass")

    return {"errors": errors, "decision": "fail" if errors else "pass"}
