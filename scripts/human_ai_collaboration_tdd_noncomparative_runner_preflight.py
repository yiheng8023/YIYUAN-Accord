#!/usr/bin/env python3
"""Record one authorized diagnostic candidate before a construction callback."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

try:
    from .human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger import (
        DispatchGateError,
        DispatchIdentityLedger,
    )
except ImportError:
    from human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger import (
        DispatchGateError,
        DispatchIdentityLedger,
    )


@dataclass(frozen=True)
class HandleValidationResult:
    valid: bool
    reason_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.valid, bool):
            raise TypeError("handle validation result valid must be bool")
        if not (
            isinstance(self.reason_code, str)
            and bool(self.reason_code.strip())
        ):
            raise ValueError(
                "handle validation result reason code must be non-empty"
            )


@dataclass
class _OwnedResourceScope:
    resources: list[tuple[str, Callable[[], None]]] = field(
        default_factory=list
    )
    resource_ids: set[str] = field(default_factory=set)
    closed: bool = False
    transferred: bool = False

    def register(
        self,
        resource_id: str,
        cleanup: Callable[[], None],
    ) -> None:
        if self.closed or self.transferred:
            raise DispatchGateError("owned resource scope is closed")
        if not (
            isinstance(resource_id, str)
            and bool(resource_id.strip())
        ):
            raise DispatchGateError("owned resource identity is invalid")
        if resource_id in self.resource_ids:
            raise DispatchGateError("owned resource identity already used")
        if not callable(cleanup):
            raise TypeError("owned resource cleanup must be callable")
        self.resource_ids.add(resource_id)
        self.resources.append((resource_id, cleanup))

    def cleanup(self) -> tuple[Exception, ...]:
        if self.closed or self.transferred:
            return ()
        self.closed = True
        errors: list[Exception] = []
        for _resource_id, cleanup in reversed(self.resources):
            try:
                cleanup()
            except Exception as error:
                errors.append(error)
        return tuple(errors)

    def transfer(self) -> None:
        if self.closed:
            raise DispatchGateError(
                "cleaned resources cannot transfer ownership"
            )
        self.transferred = True


def _attach_secondary_errors(
    primary: Exception,
    secondary_errors: list[Exception],
) -> None:
    if not secondary_errors:
        return
    try:
        primary.dispatch_secondary_errors = tuple(secondary_errors)
    except Exception:
        pass
    for secondary in secondary_errors:
        try:
            BaseException.add_note(
                primary,
                (
                    "secondary dispatch error: "
                    f"{type(secondary).__name__}"
                ),
            )
        except Exception:
            pass


def _cleanup_and_record_failure(
    *,
    scope: _OwnedResourceScope,
    ledger: DispatchIdentityLedger,
    reservation_id: str,
    failure_id: str,
    observed_at: str,
    failure_class: str,
    primary: Exception,
) -> None:
    secondary_errors = list(scope.cleanup())
    try:
        ledger.record_construction_failure(
            reservation_id=reservation_id,
            failure_id=failure_id,
            observed_at=observed_at,
            failure_class=failure_class,
        )
    except Exception as recording_error:
        secondary_errors.append(recording_error)
    _attach_secondary_errors(primary, secondary_errors)


def construct_after_dispatch_reservation(
    *,
    protocol_path: Path,
    source_governance_preflight_path: Path,
    static_gap_audit_path: Path,
    diagnostic_admission_path: Path,
    candidate_id: str,
    reservation_id: str,
    observed_at: str,
    app_server_factory: Callable[
        [dict[str, Any], Callable[[str, Callable[[], None]], None]],
        Any,
    ],
    app_server_handle_validator: Callable[
        [Any],
        HandleValidationResult,
    ],
) -> dict[str, Any]:
    """Call the injected factory only after a same-ledger reservation write."""

    if not callable(app_server_factory):
        raise TypeError("app-server factory must be callable")
    if not callable(app_server_handle_validator):
        raise TypeError("app-server handle validator must be callable")

    ledger, reservation = DispatchIdentityLedger.reserve_from_repository_documents(
        protocol_path=protocol_path,
        source_governance_preflight_path=source_governance_preflight_path,
        static_gap_audit_path=static_gap_audit_path,
        diagnostic_admission_path=diagnostic_admission_path,
        candidate_id=candidate_id,
        reservation_id=reservation_id,
        observed_at=observed_at,
    )

    resource_scope = _OwnedResourceScope()
    failure_id = f"{reservation_id}:construction-failed"
    construction_id = f"{reservation_id}:construction-succeeded"
    try:
        app_server_handle = app_server_factory(
            reservation,
            resource_scope.register,
        )
    except Exception as factory_error:
        _cleanup_and_record_failure(
            scope=resource_scope,
            ledger=ledger,
            reservation_id=reservation_id,
            failure_id=failure_id,
            observed_at=observed_at,
            failure_class="factory-raised",
            primary=factory_error,
        )
        raise

    try:
        validation = app_server_handle_validator(app_server_handle)
    except Exception as validation_error:
        _cleanup_and_record_failure(
            scope=resource_scope,
            ledger=ledger,
            reservation_id=reservation_id,
            failure_id=failure_id,
            observed_at=observed_at,
            failure_class="handle-validation-raised",
            primary=validation_error,
        )
        raise
    if not isinstance(validation, HandleValidationResult):
        invalid_result_error = DispatchGateError(
            "handle validator returned an invalid result"
        )
        _cleanup_and_record_failure(
            scope=resource_scope,
            ledger=ledger,
            reservation_id=reservation_id,
            failure_id=failure_id,
            observed_at=observed_at,
            failure_class="handle-validation-result-invalid",
            primary=invalid_result_error,
        )
        raise invalid_result_error
    if not validation.valid:
        rejected_handle_error = DispatchGateError(
            (
                "app-server handle validation rejected: "
                f"{validation.reason_code}"
            )
        )
        _cleanup_and_record_failure(
            scope=resource_scope,
            ledger=ledger,
            reservation_id=reservation_id,
            failure_id=failure_id,
            observed_at=observed_at,
            failure_class="handle-validation-rejected",
            primary=rejected_handle_error,
        )
        raise rejected_handle_error

    try:
        construction = ledger.record_construction_success(
            reservation_id=reservation_id,
            construction_id=construction_id,
            observed_at=observed_at,
        )
    except Exception as construction_recording_error:
        persisted_construction = None
        confirmation_errors: list[Exception] = []
        try:
            persisted_construction = next(
                (
                    event
                    for event in ledger.read_events()
                    if event["eventType"] == "construction-succeeded"
                    and event.get("reservationId") == reservation_id
                    and event.get("constructionId") == construction_id
                ),
                None,
            )
        except Exception as confirmation_error:
            confirmation_errors.append(confirmation_error)
        if persisted_construction is None:
            confirmation_errors.extend(resource_scope.cleanup())
            _attach_secondary_errors(
                construction_recording_error,
                confirmation_errors,
            )
            raise
        construction = persisted_construction

    resource_scope.transfer()
    return {
        "reservation": reservation,
        "construction": construction,
        "appServerHandle": app_server_handle,
    }
