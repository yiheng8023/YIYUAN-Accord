#!/usr/bin/env python3
"""Validate current-host loader and Hook observability admission."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ADMISSION_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-loader-hook-"
    "observability-admission-2026-07-28.json"
)
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-factorial-"
    "ablation-protocol-2026-07-28.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def validate_admission(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == "observed-current-host-observability-gap-no-live-admission",
        "Observability admission identity drifted",
    )
    sources = document.get("sourceBindings", {})
    _require(
        sources.get("factorialProtocol") == str(PROTOCOL_PATH).replace("\\", "/")
        and (root / sources["factorialProtocol"]).is_file()
        and (root / sources["fourCellExposureEvidence"]).is_file()
        and (root / sources["priorHandoffLoaderProbe"]).is_file()
        and sources.get("officialAppServerReadme")
        == "https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md",
        "Observability source binding drifted",
    )

    expected_schema = {
        "SkillsChangedNotification.json": (
            341,
            "d9d3bda6c7fa1ed2bafc2a6145676760972c0220dee6b1d7229f82a25297a1f3",
        ),
        "HookStartedNotification.json": (
            4245,
            "0e720d90c5550ef1ff328523f1cae47f79cdd728d861b1aa6dadf13a51b3f29a",
        ),
        "HookCompletedNotification.json": (
            4247,
            "0808905096256aa064421dc699900f5c86539cbaf1a3133fdce799fa72b672bd",
        ),
        "ServerNotification.json": (
            174324,
            "5c428385a06f41d4de4d26e320efc15bc8c5fcee2e54b5045b87e46aa066e8ab",
        ),
        "codex_app_server_protocol.v2.schemas.json": (
            584366,
            "8758e062a5ff932b3d904b466728c67effec9a4abe561b1633efa67b768240b4",
        ),
    }
    observed = {
        Path(row["path"]).name: (row["bytes"], row["sha256"])
        for row in document.get("schemaEvidence", [])
    }
    _require(observed == expected_schema, "Observability schema pins drifted")

    surface = document.get("surfaceInventory", {})
    _require(
        surface
        == {
            "skillMetadataRequest": "skills/list",
            "skillFilesystemInvalidationNotification": "skills/changed",
            "taskBoundSkillLoaderIdentityOrDigestNotification": None,
            "hookStartedNotification": "hook/started",
            "hookCompletedNotification": "hook/completed",
            "hookRunRequiresTurnToProveHostConsumption": True,
        },
        "Observability surface classification drifted",
    )
    assessment = document.get("admissionAssessment", {})
    _require(
        assessment.get("dependencyCompleteTaskScopedExposureProved") is True
        and assessment.get("hostHookRunNotificationSurfaceAvailable") is True
        and assessment.get("modelDispatchCount") == 0
        and all(
            assessment.get(key) is False
            for key in (
                "independentScenarioRelevantSkillLoaderEventAvailable",
                "noModelHostHookConsumptionProved",
                "skillInvocationAttributionPossibleUnderFrozenProtocol",
                "hookConsumptionAttributionPossibleWithoutTurn",
                "weakModelTurnWouldCloseAllAttributionGaps",
                "liveFactorialAdmission",
            )
        ),
        "Observability admission overclaimed",
    )
    classification = document.get("classification", {})
    _require(
        classification.get("candidateFailure") is False
        and classification.get("codeStackFailure") is False
        and classification.get("currentHostObservabilityConstraint") is True
        and classification.get(
            "protocolAcceptanceBoundaryChangeRequiredToUseBehaviorAssociationInstead"
        )
        is True,
        "Observability blocker classification drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("runWeakModelNow") is False
        and decision.get("preserveExactLoaderEventAcceptance") is True
        and "owner decision" in decision.get("nextGate", ""),
        "Observability decision drifted",
    )
    authority = document.get("authorityBoundary", {})
    _require(
        authority and all(value is False for value in authority.values()),
        "Observability authority expanded",
    )
    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    _require(
        protocol.get("loaderHookObservabilityAdmission")
        == str(ADMISSION_PATH).replace("\\", "/")
        and protocol.get("executionAdmission", {}).get(
            "independentScenarioRelevantSkillLoaderEventAvailable"
        )
        is False
        and protocol.get("executionAdmission", {}).get(
            "liveWeakModelRunAuthorizedByThisRecord"
        )
        is False,
        "Factorial protocol observability binding drifted",
    )
    documentation = document.get("documentation")
    _require(
        isinstance(documentation, str) and (root / documentation).is_file(),
        "Observability documentation binding drifted",
    )


def main() -> int:
    document = json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8"))
    validate_admission(document, root=ROOT)
    print("Self-authored control-chain loader/Hook observability admission verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
