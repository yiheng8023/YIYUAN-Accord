#!/usr/bin/env python3
"""Validate durable evidence from the body-only Skill delivery assay."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.probe_codex_app_server_skill_treatment_fidelity import (
        ARM_ORDERS,
        FALLBACK,
        PUBLIC_PROMPT,
        render_canary_skill_body,
    )
    from scripts.probe_codex_app_server_skill_exposure import canonical_sha256
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from probe_codex_app_server_skill_treatment_fidelity import (
        ARM_ORDERS,
        FALLBACK,
        PUBLIC_PROMPT,
        render_canary_skill_body,
    )
    from probe_codex_app_server_skill_exposure import canonical_sha256


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/"
    "codex-app-server-skill-treatment-fidelity-evidence-2026-07-24.json"
)
PROTOCOL_PATH = (
    "registry/"
    "codex-app-server-skill-treatment-fidelity-protocol-2026-07-24.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_treatment_fidelity_evidence(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
    protocol: dict[str, Any] | None = None,
) -> None:
    _require(document.get("schema") == 1, "Treatment evidence schema must be 1")
    _require(
        document.get("status")
        == "synthetic-body-only-delivery-proved-on-bound-host-independent-loader-event-absent",
        "Treatment evidence status overclaimed or drifted",
    )
    _require(
        document.get("protocol") == PROTOCOL_PATH,
        "Treatment evidence protocol binding drifted",
    )
    host = document.get("host", {})
    _require(
        host.get("runtimeVersion") == "0.145.0"
        and host.get("model") == "gpt-5.3-codex-spark"
        and host.get("reasoningEffort") == "low"
        and host.get("providerFallbackAllowed") is False
        and host.get("approvalPolicy") == "never"
        and host.get("sandbox") == "read-only"
        and host.get("networkAllowed") is False,
        "Treatment evidence host binding drifted",
    )
    pins = document.get("atRunPins", {})
    for key in (
        "probeSha256",
        "protocolSha256",
        "preflightInternalReportSha256",
        "preflightReportFileSha256",
        "liveInternalReportSha256",
        "liveReportFileSha256",
        "publicPromptSha256",
    ):
        _require(
            isinstance(pins.get(key), str) and len(pins[key]) == 64,
            f"Treatment evidence digest missing: {key}",
        )
    _require(
        pins.get("publicPromptSha256") == sha256_text(PUBLIC_PROMPT),
        "Treatment evidence public prompt digest drifted",
    )

    preflight = document.get("preflight", {})
    _require(
        preflight.get("status") == "preflight-pass-no-turn"
        and preflight.get("canaryInventoryScope") == "repo"
        and preflight.get("controlEnabledConfigurableSkillCount") == 0
        and preflight.get("selectedEnabledConfigurableSkillCount") == 1
        and preflight.get("sameIdentitySetAcrossArms") is True
        and preflight.get("tokenAbsentFromPublicSurfaces") is True
        and preflight.get("bodyStable") is True
        and preflight.get("globalConfigStable") is True
        and preflight.get("repositoryStatusStable") is True
        and preflight.get("threadOrTurnStarted") is False,
        "Treatment evidence preflight drifted",
    )
    live = document.get("liveAssay", {})
    _require(
        live.get("status")
        == "synthetic-body-only-delivery-assay-pass-independent-loader-event-absent"
        and live.get("pairCount") == 3
        and live.get("controlExactFallbackCount") == 3
        and live.get("selectedExactBodyTokenCount") == 3
        and live.get("distinctThreadCount") == 6
        and live.get("distinctTurnCount") == 6
        and live.get("forbiddenItemCount") == 0
        and live.get("allInventoryIdentitySetsStable") is True
        and live.get("allCanaryBodiesStable") is True
        and live.get("allTokensAbsentFromPublicSurfacesBeforeTurn") is True
        and live.get("globalConfigStable") is True
        and live.get("repositoryStatusStable") is True,
        "Treatment evidence live aggregate drifted",
    )

    pairs = document.get("pairs", [])
    _require(len(pairs) == 3, "Treatment evidence pair count drifted")
    tokens: set[str] = set()
    threads: set[str] = set()
    turns: set[str] = set()
    fallback_sha = canonical_sha256([FALLBACK])
    for index, pair in enumerate(pairs):
        expected_pair_id = f"pair-{index + 1}"
        token = pair.get("token")
        _require(
            pair.get("pairId") == expected_pair_id
            and pair.get("armOrder") == list(ARM_ORDERS[index]),
            f"Treatment evidence pair order drifted: {expected_pair_id}",
        )
        _require(
            isinstance(token, str)
            and token.startswith("AAH_BODY_ONLY_")
            and token not in tokens,
            f"Treatment evidence token drifted: {expected_pair_id}",
        )
        tokens.add(token)
        _require(
            pair.get("tokenSha256") == sha256_text(token)
            and pair.get("skillBodySha256")
            == sha256_text(render_canary_skill_body(token)),
            f"Treatment evidence body or token digest drifted: {expected_pair_id}",
        )
        control = pair.get("control", {})
        selected = pair.get("selected", {})
        _require(
            control.get("exactFallbackMatched") is True
            and control.get("agentMessageSha256") == fallback_sha
            and control.get("enabledConfigurableSkillCount") == 0,
            f"Treatment evidence control drifted: {expected_pair_id}",
        )
        _require(
            selected.get("structuredSkillInputSent") is True
            and selected.get("exactBodyTokenMatched") is True
            and selected.get("agentMessageSha256")
            == canonical_sha256([token])
            and selected.get("enabledConfigurableSkillCount") == 1,
            f"Treatment evidence selected arm drifted: {expected_pair_id}",
        )
        for arm in (control, selected):
            thread_id = arm.get("threadId")
            turn_id = arm.get("turnId")
            _require(
                isinstance(thread_id, str)
                and thread_id not in threads
                and isinstance(turn_id, str)
                and turn_id not in turns,
                f"Treatment evidence identity reused: {expected_pair_id}",
            )
            threads.add(thread_id)
            turns.add(turn_id)
    _require(
        len(tokens) == 3 and len(threads) == 6 and len(turns) == 6,
        "Treatment evidence uniqueness counts drifted",
    )

    claims = document.get("claimBoundary", {})
    _require(
        claims.get(
            "provesBodyOnlyContentReachedModelForSyntheticCanaryOnBoundHost"
        )
        is True
        and claims.get("provesProjectScopedStructuredSkillDeliveryMechanism")
        is True,
        "Treatment evidence bounded positive claim is missing",
    )
    for key in (
        "provesIndependentLoaderEvent",
        "provesInstalledDiagnoseBodyDelivery",
        "provesInstalledDiagnoseCausation",
        "provesCurrentMattValue",
        "provesSkillSuperiority",
        "provesPortfolioDecisionReadiness",
        "provesCrossHostBehavior",
    ):
        _require(
            claims.get(key) is False,
            f"Treatment evidence claim promoted: {key}",
        )
    decision = document.get("decision", {})
    _require(
        decision.get("syntheticCanaryEvidenceLadderLevel")
        == "L3-body-only-content-response"
        and decision.get("installedCandidateAttributionAllowed") is False,
        "Treatment evidence decision overclaimed or drifted",
    )

    documentation = " ".join(
        (root / str(document.get("documentation")))
        .read_text(encoding="utf-8")
        .split()
    )
    for phrase in (
        "body-only content from a project-scoped synthetic Skill reached the model",
        "does not create an independent loader notification",
        "does not prove that the installed historical `diagnose` body",
    ):
        _require(
            phrase in documentation,
            f"Treatment evidence documentation boundary missing: {phrase}",
        )
    if protocol is not None:
        _require(
            protocol.get("liveEvidence") == EVIDENCE_PATH
            and protocol.get("decision", {}).get("liveAssayPassed") is True,
            "Treatment evidence protocol projection drifted",
        )


def main() -> int:
    document = json.loads((ROOT / EVIDENCE_PATH).read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))
    validate_treatment_fidelity_evidence(
        document,
        root=ROOT,
        protocol=protocol,
    )
    print("Codex Skill treatment-fidelity evidence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
