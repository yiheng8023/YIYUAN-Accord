#!/usr/bin/env python3
"""Run one authorized information arm through the reused read-only runner."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Callable

try:
    from scripts.build_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
        PUBLIC_BUNDLE_NAME,
        TRIAL_PACKET_NAME,
        build_packet_package,
        build_private_oracle_payload,
    )
    from scripts.build_human_ai_collaboration_weak_agent_trial import (
        canonical_sha256,
    )
    from scripts.run_human_ai_collaboration_read_only_claim_trial import (
        run_trial as run_reused_read_only_trial,
    )
    from scripts.validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
        validate_packet_package,
    )
    from scripts.validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_protocol import (
        SOURCE_FIXTURE_PATH,
    )
except ModuleNotFoundError:
    from build_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
        PUBLIC_BUNDLE_NAME,
        TRIAL_PACKET_NAME,
        build_packet_package,
        build_private_oracle_payload,
    )
    from build_human_ai_collaboration_weak_agent_trial import canonical_sha256
    from run_human_ai_collaboration_read_only_claim_trial import (
        run_trial as run_reused_read_only_trial,
    )
    from validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
        validate_packet_package,
    )
    from validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_protocol import (
        SOURCE_FIXTURE_PATH,
    )


ROOT = Path(__file__).resolve().parent.parent
ARM_IDS = {
    "complete-single-turn",
    "same-thread-incremental-information",
    "source-backed-fresh-session-recovery",
}
SUBMISSION_ARM_ID = "GEN-NATIVE-SPARK"
PARENT_EVIDENCE_DIR = "parent-evidence"
AGENT_VISIBLE_DIR = "agent-visible"
SCOPED_READ_TOOL_NAME = "read_public_information_bundle"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_v2_oracle(*, root: Path = ROOT) -> dict[str, Any]:
    document = _load(root / SOURCE_FIXTURE_PATH)
    oracle = document.get("researchOracle")
    if not isinstance(oracle, dict):
        raise RuntimeError("V2 process-fidelity research oracle is missing")
    return oracle


def evaluate_v2_research_submission(
    submission: dict[str, Any],
    oracle: dict[str, Any],
    _protocol: dict[str, Any],
) -> dict[str, Any]:
    """Return detailed v2 failures without collapsing state and source drift."""
    failures: list[str] = []
    expected_top_level = {
        "armId",
        "claims",
        "unsupportedConclusionCount",
        "externalAccessUsed",
        "writePerformed",
    }
    if set(submission) != expected_top_level:
        failures.append("submission-shape-invalid")
    if submission.get("armId") != SUBMISSION_ARM_ID:
        failures.append("submission-arm-id-mismatch")

    expected = {item["id"]: item for item in oracle["claims"]}
    claims = submission.get("claims")
    if not isinstance(claims, list):
        failures.append("claims-not-list")
        claims = []
    actual: dict[str, dict[str, Any]] = {}
    for claim in claims:
        if (
            not isinstance(claim, dict)
            or set(claim) != {"id", "state", "sourceIds"}
            or not isinstance(claim.get("id"), str)
            or not claim["id"]
        ):
            failures.append("claim-shape-invalid")
            continue
        claim_id = claim["id"]
        if claim_id in actual:
            failures.append(f"duplicate-claim-id:{claim_id}")
            continue
        actual[claim_id] = claim

    for claim_id in expected:
        if claim_id not in actual:
            failures.append(f"claim-missing:{claim_id}")
            continue
        claim = actual[claim_id]
        sources = claim.get("sourceIds")
        if (
            not isinstance(sources, list)
            or any(not isinstance(source, str) or not source for source in sources)
            or len(sources) != len(set(sources))
        ):
            failures.append(f"claim-source-set-invalid:{claim_id}")
            sources = []
        if claim.get("state") not in {"supported", "contradicted", "unknown"}:
            failures.append(f"claim-state-invalid:{claim_id}")
        elif claim.get("state") != expected[claim_id]["state"]:
            failures.append(f"claim-state-mismatch:{claim_id}")
        if sorted(sources) != sorted(expected[claim_id]["sourceIds"]):
            failures.append(f"claim-source-set-mismatch:{claim_id}")
    for claim_id in actual:
        if claim_id not in expected:
            failures.append(f"unexpected-claim:{claim_id}")

    if submission.get("unsupportedConclusionCount") != 0:
        failures.append("extra-unsupported-conclusion-count-nonzero")
    if submission.get("externalAccessUsed") is not False:
        failures.append("external-access-used")
    if submission.get("writePerformed") is not False:
        failures.append("write-performed")
    failures = list(dict.fromkeys(failures))
    return {
        "status": (
            "accepted-offline-contract"
            if not failures
            else "rejected-offline-contract"
        ),
        "failureCodes": failures,
        "absoluteTaskPass": not failures,
    }


def build_scoped_public_bundle_reader(
    agent_visible_root: Path,
    *,
    required_canonical_sha256: str,
) -> tuple[list[dict[str, Any]], Callable[[dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]]]:
    """Expose one exact public bundle without general filesystem authority."""
    bundle_path = agent_visible_root / PUBLIC_BUNDLE_NAME
    spec = {
        "type": "function",
        "name": SCOPED_READ_TOOL_NAME,
        "description": (
            "Return the exact frozen public information bundle for this trial. "
            "This tool accepts only the preregistered stable locator."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "locator": {
                    "type": "string",
                    "const": PUBLIC_BUNDLE_NAME,
                }
            },
            "required": ["locator"],
            "additionalProperties": False,
        },
    }

    def respond(
        params: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        arguments = params.get("arguments")
        valid = (
            params.get("tool") == SCOPED_READ_TOOL_NAME
            and params.get("namespace") in (None, "")
            and isinstance(arguments, dict)
            and arguments == {"locator": PUBLIC_BUNDLE_NAME}
            and bundle_path.is_file()
        )
        observed_hash = None
        content_text = ""
        if valid:
            bundle = _load(bundle_path)
            observed_hash = canonical_sha256(bundle)
            valid = observed_hash == required_canonical_sha256
            if valid:
                content_text = json.dumps(
                    bundle,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
        evidence = {
            "tool": params.get("tool"),
            "namespace": params.get("namespace"),
            "arguments": arguments,
            "locator": PUBLIC_BUNDLE_NAME,
            "observedFileSha256": (
                _file_sha256(bundle_path) if bundle_path.is_file() else None
            ),
            "observedCanonicalSha256": observed_hash,
            "requiredCanonicalSha256": required_canonical_sha256,
            "success": valid,
            "generalFilesystemAuthorityGranted": False,
        }
        return (
            {
                "success": valid,
                "contentItems": (
                    [{"type": "inputText", "text": content_text}]
                    if valid
                    else []
                ),
            },
            evidence,
        )

    return [spec], respond


def validate_agent_visible_projection(
    agent_visible_root: Path,
    information_arm_id: str,
    *,
    required_public_bundle_sha256: str,
) -> dict[str, Any]:
    names = sorted(
        item.name for item in agent_visible_root.iterdir() if item.is_file()
    )
    if any(item.is_dir() for item in agent_visible_root.iterdir()):
        raise RuntimeError("agent-visible root contains a directory")
    expected = (
        [PUBLIC_BUNDLE_NAME]
        if information_arm_id == "source-backed-fresh-session-recovery"
        else []
    )
    if names != expected:
        raise RuntimeError("agent-visible file set drifted")
    observed = None
    if names:
        observed = canonical_sha256(_load(agent_visible_root / names[0]))
        if observed != required_public_bundle_sha256:
            raise RuntimeError("agent-visible public bundle drifted")
    return {
        "fileNames": names,
        "publicInformationBundleCanonicalSha256": observed,
        "parentEvidenceRootIsRuntimeWorkspaceRoot": False,
        "shellOrCommandExecutionAllowed": False,
    }


def validate_public_carrier_oracle_isolation(
    *,
    public_bundle: dict[str, Any],
    turn_plan: list[dict[str, Any]],
    agent_visible_root: Path,
    private_oracle_payload: dict[str, Any],
) -> dict[str, Any]:
    private_serialization = json.dumps(
        private_oracle_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    carrier_texts = [
        json.dumps(
            public_bundle,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        *[item["text"] for item in turn_plan],
    ]
    carrier_files = sorted(
        item.name for item in agent_visible_root.iterdir() if item.is_file()
    )
    carrier_texts.extend(
        (agent_visible_root / name).read_text(encoding="utf-8")
        for name in carrier_files
    )
    private_claim_rows = private_oracle_payload["claims"]
    exposed = private_serialization in "\n".join(carrier_texts)
    if any("state" in item for item in public_bundle.get("claimsToAssess", [])):
        exposed = True
    for private_claim in private_claim_rows:
        private_row = json.dumps(
            private_claim,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if private_row in "\n".join(carrier_texts):
            exposed = True
    if exposed:
        raise RuntimeError("private oracle reached a public carrier")
    return {
        "proved": True,
        "scannedTurnCount": len(turn_plan),
        "scannedAgentVisibleFileNames": carrier_files,
        "privateOracleExactSerializationFound": False,
        "privateOracleClaimRowsFound": False,
        "privateStateFieldsFoundInClaimsToAssess": False,
    }


def _complete_task_text(bundle: dict[str, Any]) -> str:
    public_packet = {
        "sources": bundle["sourcePacket"],
        "claimsToAssess": bundle["claimsToAssess"],
    }
    return (
        bundle["publicPrompt"]
        + f"\nSet armId to {SUBMISSION_ARM_ID}. Assess every claim in "
        "claimsToAssess against sources only. Return raw JSON with no Markdown "
        "fence or surrounding prose.\n\nPUBLIC_PACKET_JSON:\n"
        + json.dumps(public_packet, ensure_ascii=False, indent=2)
    )


def render_turn_plan(
    arm_envelope: dict[str, Any],
    public_bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    """Render the validated semantic message plan into app-server text turns."""
    arm_id = arm_envelope.get("informationArmId")
    if arm_id not in ARM_IDS:
        raise RuntimeError(f"Unsupported information arm: {arm_id}")
    plan = arm_envelope.get("publicMessagePlan")
    if not isinstance(plan, list) or not plan:
        raise RuntimeError("Information arm public message plan is missing")

    if arm_id == "complete-single-turn":
        return [{"text": _complete_task_text(public_bundle)}]

    if arm_id == "same-thread-incremental-information":
        rendered: list[dict[str, Any]] = []
        for message in plan:
            kind = message.get("kind")
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise RuntimeError("Incremental message payload is invalid")
            if kind == "transport-control":
                text = payload["instruction"]
            elif kind == "source-shard":
                text = (
                    "SOURCE_SHARD_JSON:\n"
                    + json.dumps(payload, ensure_ascii=False, indent=2)
                )
            elif kind == "final-public-task":
                text = (
                    payload["publicPrompt"]
                    + f"\nSet armId to {SUBMISSION_ARM_ID}. Assess every claim in "
                    "claimsToAssess against all previously supplied source "
                    "shards only. Return raw JSON with no Markdown fence or "
                    "surrounding prose.\n\nRUN_AND_CLAIMS_JSON:\n"
                    + json.dumps(
                        {
                            "runMarker": payload["runMarker"],
                            "fixtureId": payload["fixtureId"],
                            "claimsToAssess": payload["claimsToAssess"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                raise RuntimeError(
                    f"Unsupported incremental message kind: {kind}"
                )
            rendered_turn = {"text": text}
            if "expectedAssistantReply" in message:
                rendered_turn["expectedAgentResponse"] = message[
                    "expectedAssistantReply"
                ]
            rendered.append(rendered_turn)
        return rendered

    message = plan[0]
    payload = message.get("payload")
    if (
        message.get("kind") != "source-backed-fresh-session-task"
        or not isinstance(payload, dict)
        or payload.get("stableRelativeLocator") != PUBLIC_BUNDLE_NAME
    ):
        raise RuntimeError("Fresh-session source-backed plan is invalid")
    return [
        {
            "text": (
                payload["instruction"]
                + "\nStable relative locator: "
                + payload["stableRelativeLocator"]
                + "\nRequired canonical SHA-256: "
                + payload["requiredCanonicalSha256"]
                + f"\nSet armId to {SUBMISSION_ARM_ID}. The armId identifies "
                "the fixed treatment/model arm, not the fixtureId or the "
                "parent-recorded informationArmId. Return raw JSON with no "
                "Markdown fence or surrounding prose."
            )
        }
    ]


def prepare_information_arm(
    trial_root: Path,
    information_arm_id: str,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    if information_arm_id not in ARM_IDS:
        raise ValueError(
            f"unsupported information arm: {information_arm_id}"
        )
    trial_root = trial_root.resolve()
    if trial_root.exists():
        if not trial_root.is_dir() or any(trial_root.iterdir()):
            raise RuntimeError("trial root must be an empty directory")
    else:
        trial_root.mkdir(parents=True)
    parent_evidence_root = trial_root / PARENT_EVIDENCE_DIR
    agent_visible_root = trial_root / AGENT_VISIBLE_DIR
    build = build_packet_package(parent_evidence_root, root=root)
    preflight = validate_packet_package(parent_evidence_root, root=root)
    packet = _load(parent_evidence_root / TRIAL_PACKET_NAME)
    public_bundle = _load(parent_evidence_root / PUBLIC_BUNDLE_NAME)
    agent_visible_root.mkdir()
    arms = {
        item["informationArmId"]: item
        for item in packet["arms"]
    }
    arm = arms[information_arm_id]
    if information_arm_id == "source-backed-fresh-session-recovery":
        shutil.copyfile(
            parent_evidence_root / PUBLIC_BUNDLE_NAME,
            agent_visible_root / PUBLIC_BUNDLE_NAME,
        )
    agent_visible_projection = validate_agent_visible_projection(
        agent_visible_root,
        information_arm_id,
        required_public_bundle_sha256=preflight[
            "publicInformationBundleCanonicalSha256"
        ],
    )
    turn_plan = render_turn_plan(arm, public_bundle)
    oracle = load_v2_oracle(root=root)
    private_oracle_payload = build_private_oracle_payload(oracle)
    carrier_isolation = validate_public_carrier_oracle_isolation(
        public_bundle=public_bundle,
        turn_plan=turn_plan,
        agent_visible_root=agent_visible_root,
        private_oracle_payload=private_oracle_payload,
    )
    turn_plan_sha256 = canonical_sha256(turn_plan)
    return {
        "build": build,
        "preflight": preflight,
        "packet": packet,
        "arm": arm,
        "oracle": oracle,
        "privateOraclePayload": private_oracle_payload,
        "turnPlan": turn_plan,
        "turnPlanSha256": turn_plan_sha256,
        "turnTextSha256": [
            hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
            for item in turn_plan
        ],
        "trialRoot": trial_root,
        "parentEvidenceRoot": parent_evidence_root,
        "agentVisibleRoot": agent_visible_root,
        "agentVisibleProjection": agent_visible_projection,
        "publicCarrierOracleIsolation": carrier_isolation,
    }


def run_information_arm(
    trial_root: Path,
    information_arm_id: str,
    *,
    live_task_creation_authorized: bool,
    codex_executable: str | None,
    timeout_seconds: float,
    root: Path = ROOT,
    runner: Callable[..., dict[str, Any]] = run_reused_read_only_trial,
) -> dict[str, Any]:
    """Prepare one arm, then stop unless live task creation is explicit."""
    prepared = prepare_information_arm(
        trial_root,
        information_arm_id,
        root=root,
    )
    if not live_task_creation_authorized:
        return {
            "schema": 1,
            "id": (
                "information-equivalent-process-fidelity-live-"
                "authorization-gate"
            ),
            "informationArmId": information_arm_id,
            "status": "blocked-live-task-creation-authority-required",
            "packetPreflightStatus": prepared["preflight"]["status"],
            "turnPlanSha256": prepared["turnPlanSha256"],
            "liveTaskCreationAuthorized": False,
            "agentRunStarted": False,
            "dispatchCount": 0,
            "scoredArmCount": 0,
        }

    dynamic_tools = None
    dynamic_tool_responder = None
    expected_dynamic_tool_call_count = 0
    if information_arm_id == "source-backed-fresh-session-recovery":
        dynamic_tools, dynamic_tool_responder = build_scoped_public_bundle_reader(
            prepared["agentVisibleRoot"],
            required_canonical_sha256=prepared["preflight"][
                "publicInformationBundleCanonicalSha256"
            ],
        )
        expected_dynamic_tool_call_count = 1
    input_binding = {
        "inputMode": information_arm_id,
        "publicInformationBundleCanonicalSha256": prepared["preflight"][
            "publicInformationBundleCanonicalSha256"
        ],
        "turnPlanSha256": prepared["turnPlanSha256"],
        "turnTextSha256": prepared["turnTextSha256"],
        "publicInformationBundleContentWrittenIntoTrial": (
            information_arm_id == "source-backed-fresh-session-recovery"
        ),
        "publicInformationBundleRequiredAsInput": True,
        "sourceBackedLocator": (
            PUBLIC_BUNDLE_NAME
            if information_arm_id == "source-backed-fresh-session-recovery"
            else None
        ),
        "agentVisibleFileNames": prepared["agentVisibleProjection"]["fileNames"],
        "parentEvidenceRootIsRuntimeWorkspaceRoot": False,
        "privateOracleVersion": prepared["oracle"]["privateOracleVersion"],
        "privateOracleSha256": canonical_sha256(
            prepared["privateOraclePayload"]
        ),
        "privateOraclePayloadWrittenIntoPreparedPackage": False,
        "preDispatchPublicCarrierOracleIsolationProved": prepared[
            "publicCarrierOracleIsolation"
        ]["proved"],
        "publicCarrierOracleIsolationEvidence": prepared[
            "publicCarrierOracleIsolation"
        ],
        "provedByPacketPreflight": True,
        "packetPreflightStatus": prepared["preflight"]["status"],
    }
    report = runner(
        prepared["agentVisibleRoot"],
        codex_executable=codex_executable,
        timeout_seconds=timeout_seconds,
        turn_plan=prepared["turnPlan"],
        allow_prepared_root=bool(
            prepared["agentVisibleProjection"]["fileNames"]
        ),
        information_arm_id=information_arm_id,
        allow_readonly_command_execution=False,
        oracle_override=prepared["oracle"],
        oracle_evaluator=evaluate_v2_research_submission,
        input_binding_override=input_binding,
        dynamic_tools=dynamic_tools,
        dynamic_tool_responder=dynamic_tool_responder,
        expected_dynamic_tool_name=(
            SCOPED_READ_TOOL_NAME
            if expected_dynamic_tool_call_count
            else None
        ),
        expected_dynamic_tool_call_count=expected_dynamic_tool_call_count,
    )
    report["informationEquivalentTrialBinding"] = {
        "informationArmId": information_arm_id,
        "submissionArmId": SUBMISSION_ARM_ID,
        "fixtureId": prepared["oracle"]["fixtureId"],
        "packetPreflightStatus": prepared["preflight"]["status"],
        "publicInformationBundleCanonicalSha256": prepared["preflight"][
            "publicInformationBundleCanonicalSha256"
        ],
        "privateOracleCanonicalSha256": prepared["preflight"][
            "privateOracleCanonicalSha256"
        ],
        "turnPlanSha256": prepared["turnPlanSha256"],
        "liveTaskCreationAuthorized": True,
        "automaticCompressionClaimed": False,
        "automaticThreadCreationClaimed": False,
        "handoffSkillInvocationClaimed": False,
        "candidateComparisonClaimed": False,
        "countsAsThreeArmComparison": False,
        "countsAsProcessFidelityOutcome": False,
        "v1CalibrationRunIncluded": False,
        "agentVisibleProjection": prepared["agentVisibleProjection"],
    }
    report["reportSha256"] = canonical_sha256(
        {key: value for key, value in report.items() if key != "reportSha256"}
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument(
        "--information-arm",
        choices=sorted(ARM_IDS),
        required=True,
    )
    parser.add_argument(
        "--authorize-live-dispatch",
        action="store_true",
        help=(
            "explicitly authorize this one ephemeral task only; omission "
            "builds and validates the packet but dispatches nothing"
        ),
    )
    parser.add_argument("--codex-executable")
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    parser.add_argument("--output-report", type=Path)
    args = parser.parse_args()
    if (
        args.output_report is not None
        and args.output_report.resolve().is_relative_to(
            args.trial_root.resolve()
        )
    ):
        raise RuntimeError("output report must be outside the trial root")
    report = run_information_arm(
        args.trial_root,
        args.information_arm,
        live_task_creation_authorized=args.authorize_live_dispatch,
        codex_executable=args.codex_executable,
        timeout_seconds=args.timeout_seconds,
    )
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output_report is not None:
        args.output_report.write_text(output + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "outputReport": str(args.output_report.resolve()),
                    "dispatchCount": (
                        0
                        if not args.authorize_live_dispatch
                        else 1
                    ),
                },
                sort_keys=True,
            )
        )
    else:
        print(output)
    return (
        0
        if report["status"]
        in {
            "blocked-live-task-creation-authority-required",
            "fixture-pass-native-read-only-boundary",
        }
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
