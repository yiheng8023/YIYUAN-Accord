#!/usr/bin/env python3
"""Build and validate source-bound Harness decision packets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ROUTE_CLASSES = ("N", "O", "E", "C", "H", "R")
EVIDENCE_LANES = {"portfolio-curation", "mechanism-validation", "task-time"}
REQUEST_FIELDS = {
    "schema",
    "requestId",
    "scenarioId",
    "evidenceLane",
    "expectedSemanticAuthorityId",
    "observedAvailability",
    "taskBinding",
    "currentCapabilityGap",
    "activationAuthority",
}
SCENARIO_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]*$")


class DecisionPacketError(ValueError):
    """A stable machine-readable decision-packet failure."""

    def __init__(self, code: str, message: str, *, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.path = path

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "status": "error",
            "code": self.code,
            "message": str(self),
        }
        if self.path is not None:
            result["path"] = self.path
        return result


def canonical_json_bytes(value: object) -> bytes:
    """Return the UTF-8 canonical JSON representation used for packet hashes."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    """Return a SHA-256 digest of canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_exact_fields(value: object, fields: set[str]) -> bool:
    return isinstance(value, dict) and set(value) == fields


def _is_string_list(
    value: object,
    *,
    allowed: set[str] | None = None,
    require_nonempty: bool = False,
) -> bool:
    if not isinstance(value, list) or (require_nonempty and not value):
        return False
    if not all(_is_nonempty_string(item) for item in value):
        return False
    if len(value) != len(set(value)):
        return False
    return allowed is None or set(value).issubset(allowed)


def _validate_nullable_object(
    value: object,
    *,
    fields: set[str],
    code: str,
    validators: dict[str, Any],
) -> None:
    if value is None:
        return
    if not _has_exact_fields(value, fields):
        raise DecisionPacketError(code, f"{code} must contain exactly its v1 fields.")
    assert isinstance(value, dict)
    for field, validator in validators.items():
        if not validator(value[field]):
            raise DecisionPacketError(code, f"{code} has an invalid {field} field.")


def validate_decision_request(request: object) -> None:
    """Validate the exact v1 request shape and its evidence-bearing fields."""

    if not isinstance(request, dict) or set(request) != REQUEST_FIELDS:
        raise DecisionPacketError(
            "invalid-request-shape",
            "Decision request must contain exactly the v1 request fields.",
        )
    if isinstance(request["activationAuthority"], bool):
        raise DecisionPacketError(
            "invalid-activation-authority",
            "Activation authority must be null or an evidence-backed object.",
        )
    if request["schema"] != 1:
        raise DecisionPacketError("invalid-request-schema", "Request schema must be 1.")
    if not _is_nonempty_string(request["requestId"]):
        raise DecisionPacketError("invalid-request-id", "Request ID must be non-empty.")
    if not isinstance(request["scenarioId"], str) or not SCENARIO_ID_PATTERN.fullmatch(
        request["scenarioId"]
    ):
        raise DecisionPacketError(
            "invalid-scenario-id",
            "Scenario ID must use upper-case letters, digits, and hyphens.",
        )
    if request["evidenceLane"] not in EVIDENCE_LANES:
        raise DecisionPacketError(
            "invalid-evidence-lane",
            "Evidence lane is not recognized by the v1 contract.",
        )
    if not _is_nonempty_string(request["expectedSemanticAuthorityId"]):
        raise DecisionPacketError(
            "invalid-authority-id",
            "Expected semantic authority ID must be non-empty.",
        )

    _validate_nullable_object(
        request["observedAvailability"],
        fields={"asOf", "host", "availableRouteClasses", "evidencePaths"},
        code="invalid-observed-availability",
        validators={
            "asOf": _is_nonempty_string,
            "host": _is_nonempty_string,
            "availableRouteClasses": lambda value: _is_string_list(
                value, allowed=set(ROUTE_CLASSES)
            ),
            "evidencePaths": lambda value: _is_string_list(
                value, require_nonempty=True
            ),
        },
    )
    _validate_nullable_object(
        request["taskBinding"],
        fields={"taskId", "goal", "target", "verificationSurface"},
        code="invalid-task-binding",
        validators={
            "taskId": _is_nonempty_string,
            "goal": _is_nonempty_string,
            "target": _is_nonempty_string,
            "verificationSurface": _is_nonempty_string,
        },
    )
    _validate_nullable_object(
        request["currentCapabilityGap"],
        fields={"requiredCapability", "observedLimitation", "evidencePaths"},
        code="invalid-capability-gap",
        validators={
            "requiredCapability": _is_nonempty_string,
            "observedLimitation": _is_nonempty_string,
            "evidencePaths": lambda value: _is_string_list(
                value, require_nonempty=True
            ),
        },
    )
    _validate_nullable_object(
        request["activationAuthority"],
        fields={"evidencePath", "scope"},
        code="invalid-activation-authority",
        validators={
            "evidencePath": _is_nonempty_string,
            "scope": _is_nonempty_string,
        },
    )
