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


def evaluate_review_bundle(bundle, subject_revision, subject_tree):
    """Return deterministic ``errors`` and a fail-closed ``decision``.

    ``subject_revision`` and ``subject_tree`` are the caller's exact candidate
    bindings.  Every independent receipt must bind the same pair.  The function
    deliberately neither discovers Git state nor reads receipt files.
    """

    errors = []
    _object_id(subject_revision, "subject_revision", errors)
    _object_id(subject_tree, "subject_tree", errors)

    if not _exact_object(bundle, _BUNDLE_FIELDS, "bundle", errors):
        return {"errors": errors, "decision": "fail"}
    if bundle.get("schema") != REVIEW_BUNDLE_SCHEMA:
        errors.append(f"bundle.schema must be {REVIEW_BUNDLE_SCHEMA}")
    _subject(bundle.get("subject"), "bundle.subject", subject_revision, subject_tree, errors)

    reviews = bundle.get("reviews")
    if not isinstance(reviews, list):
        errors.append("bundle.reviews must be a list")
        reviews = []
    if len(reviews) != len(REVIEW_AXES):
        errors.append("bundle.reviews must contain exactly four reviews")

    axes = []
    reviewers = []
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
        if (
            not _exact_object(context, _CONTEXT_FIELDS, f"{label}.context", errors)
            or context.get("isolation") != "context-isolated"
            or context.get("history") != "zero-inherited-history"
            or context.get("environment") != "isolated-no-accord"
            or context.get("accordExposure") != "absent"
        ):
            errors.append(
                f"{label}.context must declare context-isolated, "
                "zero-inherited-history and isolated-no-accord with absent exposure"
            )
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

    if len(axes) != len(REVIEW_AXES) or set(axes) != set(REVIEW_AXES):
        errors.append(f"review axes must be exactly {list(REVIEW_AXES)}")
    if len(reviewers) != len(REVIEW_AXES) or len(set(reviewers)) != len(REVIEW_AXES):
        errors.append("reviewerId values must be four unique identifiers")
    if bundle.get("decision") != "pass":
        errors.append("bundle.decision must be pass")

    return {"errors": errors, "decision": "fail" if errors else "pass"}
