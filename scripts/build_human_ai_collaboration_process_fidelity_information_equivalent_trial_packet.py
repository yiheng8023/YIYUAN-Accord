#!/usr/bin/env python3
"""Build a zero-dispatch public packet for the three-arm fidelity trial."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.build_human_ai_collaboration_weak_agent_trial import (
        canonical_sha256,
        load_oracle,
    )
    from scripts.validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_protocol import (
        PROTOCOL_PATH,
        SOURCE_FIXTURE_PATH,
        validate_protocol,
    )
except ModuleNotFoundError:
    from build_human_ai_collaboration_weak_agent_trial import (
        canonical_sha256,
        load_oracle,
    )
    from validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_protocol import (
        PROTOCOL_PATH,
        SOURCE_FIXTURE_PATH,
        validate_protocol,
    )


ROOT = Path(__file__).resolve().parent.parent
PUBLIC_BUNDLE_NAME = "PUBLIC-SOURCE-BUNDLE.json"
TRIAL_PACKET_NAME = "TRIAL-PACKET.json"
BUILD_MANIFEST_NAME = "BUILD-MANIFEST.json"
PACKAGE_FILE_NAMES = [
    PUBLIC_BUNDLE_NAME,
    TRIAL_PACKET_NAME,
    BUILD_MANIFEST_NAME,
]


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_public_bundle(oracle: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixtureId": oracle["fixtureId"],
        "semanticContractVersion": oracle["semanticContractVersion"],
        "publicPrompt": oracle["publicPrompt"],
        "sourcePacket": oracle["sourcePacket"],
        "claimsToAssess": [
            {
                "id": claim["id"],
                "meaning": claim["meaning"],
                "requiredSourceIds": claim["requiredSourceIds"],
            }
            for claim in oracle["claims"]
        ],
    }


def build_private_oracle_payload(oracle: dict[str, Any]) -> dict[str, Any]:
    return {
        "claims": [
            {
                "id": claim["id"],
                "state": claim["state"],
                "sourceIds": claim["sourceIds"],
            }
            for claim in oracle["claims"]
        ],
        "unsupportedConclusionCount": 0,
        "externalAccessUsed": False,
        "writePerformed": False,
    }


def _single_turn_plan(public_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "sequence": 1,
            "role": "user",
            "kind": "complete-public-task",
            "payload": public_bundle,
        }
    ]


def _incremental_plan(public_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [
        {
            "sequence": 1,
            "role": "user",
            "kind": "transport-control",
            "payload": {
                "instruction": (
                    "Four source shards will follow. Reply with exactly ACK "
                    "after each shard and do not analyze or answer the task "
                    "until the final run instruction."
                )
            },
            "expectedAssistantReply": "ACK",
        }
    ]
    for source in public_bundle["sourcePacket"]:
        messages.append(
            {
                "sequence": len(messages) + 1,
                "role": "user",
                "kind": "source-shard",
                "payload": source,
                "expectedAssistantReply": "ACK",
            }
        )
    messages.append(
        {
            "sequence": len(messages) + 1,
            "role": "user",
            "kind": "final-public-task",
            "payload": {
                "runMarker": "RUN",
                "fixtureId": public_bundle["fixtureId"],
                "publicPrompt": public_bundle["publicPrompt"],
                "claimsToAssess": public_bundle["claimsToAssess"],
            },
        }
    )
    return messages


def _fresh_session_plan(public_bundle_sha256: str) -> list[dict[str, Any]]:
    return [
        {
            "sequence": 1,
            "role": "user",
            "kind": "source-backed-fresh-session-task",
            "payload": {
                "stableRelativeLocator": PUBLIC_BUNDLE_NAME,
                "requiredCanonicalSha256": public_bundle_sha256,
                "instruction": (
                    "Call the dynamic tool read_public_information_bundle "
                    "exactly once with the stable relative locator. Use only "
                    "the returned public bundle and perform its public task. "
                    "Do not use shell or general filesystem reads. Return raw "
                    "JSON only. Do not infer automatic thread creation, "
                    "automatic compression, or handoff Skill invocation."
                ),
            },
        }
    ]


def _arm_envelope(
    arm: dict[str, Any],
    public_bundle: dict[str, Any],
    public_bundle_sha256: str,
) -> dict[str, Any]:
    arm_id = arm["informationArmId"]
    if arm_id == "complete-single-turn":
        messages = _single_turn_plan(public_bundle)
    elif arm_id == "same-thread-incremental-information":
        messages = _incremental_plan(public_bundle)
    elif arm_id == "source-backed-fresh-session-recovery":
        messages = _fresh_session_plan(public_bundle_sha256)
    else:
        raise RuntimeError(f"Unsupported information arm: {arm_id}")
    return {
        "informationArmId": arm_id,
        "deliveryTopology": arm["deliveryTopology"],
        "requestedModel": arm["modelId"],
        "requestedReasoningEffort": arm["reasoningEffort"],
        "providerFallbackAllowed": False,
        "selectedCapabilityIds": [],
        "networkAllowed": False,
        "repositoryWriteAllowed": False,
        "externalWriteAllowed": False,
        "gitMutationAllowed": False,
        "freshTaskRequired": True,
        "publicInformationBundleCanonicalSha256": public_bundle_sha256,
        "privateOracleCanonicalSha256": arm[
            "privateOracleCanonicalSha256"
        ],
        "publicMessagePlan": messages,
        "agentRunStartedAtBuildTime": False,
        "dispatchAuthorizedByPacket": False,
    }


def build_packet_package(
    output: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Write a deterministic public package without dispatching any Agent."""
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("trial packet output must be an empty directory")
    else:
        output.mkdir(parents=True)

    protocol_path = root / PROTOCOL_PATH
    protocol = _load_json(protocol_path)
    validate_protocol(protocol, root=root)
    oracle = load_oracle(
        "researchOracle",
        root / SOURCE_FIXTURE_PATH,
    )
    public_bundle = build_public_bundle(oracle)
    private_oracle_payload = build_private_oracle_payload(oracle)
    public_bundle_sha256 = canonical_sha256(public_bundle)
    private_oracle_sha256 = canonical_sha256(private_oracle_payload)

    binding = protocol["sourceAndOracleBinding"]
    if (
        public_bundle_sha256
        != binding["publicInformationBundleCanonicalSha256"]
        or private_oracle_sha256
        != binding["privateOracleCanonicalSha256"]
    ):
        raise RuntimeError("protocol source or private-oracle binding drifted")

    packet = {
        "schema": 1,
        "id": (
            "human-ai-collaboration-process-fidelity-information-"
            "equivalent-trial-packet"
        ),
        "status": "prepared-zero-dispatch-live-authority-still-required",
        "protocolBinding": {
            "path": PROTOCOL_PATH,
            "sha256": _file_sha256(protocol_path),
            "id": protocol["id"],
            "date": protocol["date"],
        },
        "sourceFixtureBinding": {
            "path": SOURCE_FIXTURE_PATH,
            "sha256": _file_sha256(root / SOURCE_FIXTURE_PATH),
            "fixtureKey": binding["fixtureKey"],
            "fixtureId": binding["fixtureId"],
        },
        "agentVisibleProjection": {
            "parentEvidenceRootIsRuntimeWorkspaceRoot": False,
            "directAndIncrementalFileNames": [],
            "sourceBackedFileNames": [PUBLIC_BUNDLE_NAME],
            "sourceBackedScopedReadToolName": (
                "read_public_information_bundle"
            ),
            "shellOrCommandExecutionAllowed": False,
        },
        "informationManifest": {
            "sourceIds": binding["sourceIds"],
            "claimIds": binding["claimIds"],
            "sourcePacketCanonicalSha256": binding[
                "sourcePacketCanonicalSha256"
            ],
            "publicClaimsToAssessCanonicalSha256": binding[
                "publicClaimsToAssessCanonicalSha256"
            ],
            "publicTaskInstructionSha256": binding[
                "publicTaskInstructionSha256"
            ],
            "publicInformationBundleCanonicalSha256": public_bundle_sha256,
        },
        "privateOracle": {
            "owner": "parent-harness",
            "sha256": private_oracle_sha256,
            "contentWrittenIntoTrialPackage": False,
            "contentWrittenIntoAnyPublicMessage": False,
        },
        "arms": [
            _arm_envelope(arm, public_bundle, public_bundle_sha256)
            for arm in protocol["trialArms"]
        ],
        "cohortBoundary": {
            "minimumValidRepetitionsPerArm": protocol[
                "repetitionAndOrderingContract"
            ]["minimumValidRepetitionsPerArm"],
            "balancedOrder": protocol["repetitionAndOrderingContract"][
                "balancedOrder"
            ],
            "onlyPermittedVariation": (
                "predeclared delivery topology, including the scoped "
                "source-backed read transport"
            ),
            "cohortInvalidatedBySourceProtocolModelOrAuthorityDrift": True,
            "incompleteOrOpaqueArmOutcome": protocol[
                "repetitionAndOrderingContract"
            ]["incompleteOrOpaqueArmOutcome"],
        },
        "authorityBoundary": {
            "liveTaskCreationAuthorizedByPacket": False,
            "dispatchAuthorizedByPacket": False,
            "automaticCompressionClaimed": False,
            "automaticThreadCreationClaimed": False,
            "handoffSkillInvocationClaimed": False,
            "candidateComparisonAuthorized": False,
            "repositoryMutationAuthorized": False,
        },
        "buildEffects": {
            "agentRunStarted": False,
            "dispatchCount": 0,
            "networkUsed": False,
            "accountAccessed": False,
            "configurationMutated": False,
            "gitMutated": False,
        },
    }

    public_bundle_path = output / PUBLIC_BUNDLE_NAME
    packet_path = output / TRIAL_PACKET_NAME
    _write_json(public_bundle_path, public_bundle)
    _write_json(packet_path, packet)
    build_manifest = {
        "schema": 1,
        "id": "information-equivalent-trial-packet-build-manifest",
        "status": "prepared-zero-dispatch",
        "files": [
            {
                "name": PUBLIC_BUNDLE_NAME,
                "sha256": _file_sha256(public_bundle_path),
            },
            {
                "name": TRIAL_PACKET_NAME,
                "sha256": _file_sha256(packet_path),
            },
        ],
        "privateOracleCanonicalSha256": private_oracle_sha256,
        "privateOracleContentWritten": False,
        "agentRunStartedAtBuildTime": False,
        "dispatchCount": 0,
    }
    manifest_path = output / BUILD_MANIFEST_NAME
    _write_json(manifest_path, build_manifest)
    return {
        "schema": 1,
        "id": "information-equivalent-trial-packet-build",
        "status": "prepared-zero-dispatch-live-authority-still-required",
        "output": output.as_posix(),
        "packageFileNames": PACKAGE_FILE_NAMES,
        "packageFileSha256": {
            name: _file_sha256(output / name)
            for name in PACKAGE_FILE_NAMES
        },
        "publicInformationBundleCanonicalSha256": public_bundle_sha256,
        "privateOracleCanonicalSha256": private_oracle_sha256,
        "privateOracleContentWritten": False,
        "agentRunStartedAtBuildTime": False,
        "dispatchCount": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_packet_package(args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
