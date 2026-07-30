#!/usr/bin/env python3
"""Validate a built three-arm trial package without dispatching an Agent."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from scripts.build_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
        BUILD_MANIFEST_NAME,
        PACKAGE_FILE_NAMES,
        PUBLIC_BUNDLE_NAME,
        TRIAL_PACKET_NAME,
        _arm_envelope,
        build_private_oracle_payload,
        build_public_bundle,
    )
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
    from build_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
        BUILD_MANIFEST_NAME,
        PACKAGE_FILE_NAMES,
        PUBLIC_BUNDLE_NAME,
        TRIAL_PACKET_NAME,
        _arm_envelope,
        build_private_oracle_payload,
        build_public_bundle,
    )
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


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected JSON object: {path}")
    return value


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _append(failures: list[str], condition: bool, code: str) -> None:
    if not condition and code not in failures:
        failures.append(code)


def evaluate_packet_package(
    output: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Return a fail-closed zero-dispatch report for a built package."""
    output = output.resolve()
    failures: list[str] = []
    if not output.is_dir():
        failures.append("fail-package-directory-missing")
        return {
            "schema": 1,
            "status": "blocked-zero-dispatch",
            "failureCodes": failures,
            "dispatchCount": 0,
            "scoredArmIds": [],
            "liveTaskCreationAuthorized": False,
        }

    actual_names = sorted(
        item.name for item in output.iterdir() if item.is_file()
    )
    _append(
        failures,
        actual_names == sorted(PACKAGE_FILE_NAMES),
        "fail-package-file-set",
    )
    if any(item.is_dir() for item in output.iterdir()):
        failures.append("fail-package-file-set")

    documents: dict[str, dict[str, Any]] = {}
    for name in PACKAGE_FILE_NAMES:
        path = output / name
        if not path.is_file():
            if "fail-package-file-set" not in failures:
                failures.append("fail-package-file-set")
            continue
        try:
            documents[name] = _load_json(path)
        except Exception:
            failures.append(f"fail-json-shape:{name}")

    try:
        protocol = _load_json(root / PROTOCOL_PATH)
        validate_protocol(protocol, root=root)
    except Exception:
        protocol = {}
        failures.append("fail-current-protocol-validation")
    try:
        oracle = load_oracle(
            "researchOracle",
            root / SOURCE_FIXTURE_PATH,
        )
        public_bundle_expected = build_public_bundle(oracle)
        private_oracle_expected = build_private_oracle_payload(oracle)
    except Exception:
        oracle = {}
        public_bundle_expected = {}
        private_oracle_expected = {}
        failures.append("fail-current-source-fixture")

    public_bundle = documents.get(PUBLIC_BUNDLE_NAME, {})
    packet = documents.get(TRIAL_PACKET_NAME, {})
    manifest = documents.get(BUILD_MANIFEST_NAME, {})
    public_bundle_sha256 = canonical_sha256(public_bundle_expected)
    private_oracle_sha256 = canonical_sha256(private_oracle_expected)

    _append(
        failures,
        public_bundle == public_bundle_expected,
        "fail-public-information-bundle",
    )
    _append(
        failures,
        set(packet)
        == {
            "schema",
            "id",
            "status",
            "protocolBinding",
            "sourceFixtureBinding",
            "agentVisibleProjection",
            "informationManifest",
            "privateOracle",
            "arms",
            "cohortBoundary",
            "authorityBoundary",
            "buildEffects",
        }
        and packet.get("schema") == 1
        and packet.get("id")
        == (
            "human-ai-collaboration-process-fidelity-information-"
            "equivalent-trial-packet"
        )
        and packet.get("status")
        == "prepared-zero-dispatch-live-authority-still-required",
        "fail-trial-packet-shape",
    )

    if protocol:
        _append(
            failures,
            packet.get("protocolBinding")
            == {
                "path": PROTOCOL_PATH,
                "sha256": _file_sha256(root / PROTOCOL_PATH),
                "id": protocol.get("id"),
                "date": protocol.get("date"),
            },
            "fail-protocol-binding",
        )
    if oracle:
        binding = protocol.get("sourceAndOracleBinding", {})
        _append(
            failures,
            packet.get("sourceFixtureBinding")
            == {
                "path": SOURCE_FIXTURE_PATH,
                "sha256": _file_sha256(root / SOURCE_FIXTURE_PATH),
                "fixtureKey": "researchOracle",
                "fixtureId": oracle.get("fixtureId"),
            },
            "fail-source-fixture-binding",
        )
        _append(
            failures,
            packet.get("agentVisibleProjection")
            == {
                "parentEvidenceRootIsRuntimeWorkspaceRoot": False,
                "directAndIncrementalFileNames": [],
                "sourceBackedFileNames": [PUBLIC_BUNDLE_NAME],
                "sourceBackedScopedReadToolName": (
                    "read_public_information_bundle"
                ),
                "shellOrCommandExecutionAllowed": False,
            },
            "fail-agent-visible-projection",
        )
        _append(
            failures,
            packet.get("informationManifest")
            == {
                "sourceIds": binding.get("sourceIds"),
                "claimIds": binding.get("claimIds"),
                "sourcePacketCanonicalSha256": binding.get(
                    "sourcePacketCanonicalSha256"
                ),
                "publicClaimsToAssessCanonicalSha256": binding.get(
                    "publicClaimsToAssessCanonicalSha256"
                ),
                "publicTaskInstructionSha256": binding.get(
                    "publicTaskInstructionSha256"
                ),
                "publicInformationBundleCanonicalSha256": (
                    public_bundle_sha256
                ),
            },
            "fail-information-manifest",
        )
        _append(
            failures,
            packet.get("privateOracle")
            == {
                "owner": "parent-harness",
                "sha256": private_oracle_sha256,
                "contentWrittenIntoTrialPackage": False,
                "contentWrittenIntoAnyPublicMessage": False,
            },
            "fail-private-oracle-boundary",
        )
        expected_arms = [
            _arm_envelope(
                arm,
                public_bundle_expected,
                public_bundle_sha256,
            )
            for arm in protocol.get("trialArms", [])
        ]
        _append(
            failures,
            packet.get("arms") == expected_arms,
            "fail-arm-information-equivalence-or-confound",
        )
        repetition = protocol.get("repetitionAndOrderingContract", {})
        _append(
            failures,
            packet.get("cohortBoundary")
            == {
                "minimumValidRepetitionsPerArm": repetition.get(
                    "minimumValidRepetitionsPerArm"
                ),
                "balancedOrder": repetition.get("balancedOrder"),
                "onlyPermittedVariation": (
                    "predeclared delivery topology, including the scoped "
                    "source-backed read transport"
                ),
                "cohortInvalidatedBySourceProtocolModelOrAuthorityDrift": True,
                "incompleteOrOpaqueArmOutcome": repetition.get(
                    "incompleteOrOpaqueArmOutcome"
                ),
            },
            "fail-cohort-boundary",
        )

    expected_authority = {
        "liveTaskCreationAuthorizedByPacket": False,
        "dispatchAuthorizedByPacket": False,
        "automaticCompressionClaimed": False,
        "automaticThreadCreationClaimed": False,
        "handoffSkillInvocationClaimed": False,
        "candidateComparisonAuthorized": False,
        "repositoryMutationAuthorized": False,
    }
    _append(
        failures,
        packet.get("authorityBoundary") == expected_authority,
        "fail-authority-promotion",
    )
    expected_effects = {
        "agentRunStarted": False,
        "dispatchCount": 0,
        "networkUsed": False,
        "accountAccessed": False,
        "configurationMutated": False,
        "gitMutated": False,
    }
    _append(
        failures,
        packet.get("buildEffects") == expected_effects,
        "fail-build-effect-promotion",
    )

    expected_manifest_files: list[dict[str, str]] = []
    for name in (PUBLIC_BUNDLE_NAME, TRIAL_PACKET_NAME):
        path = output / name
        if path.is_file():
            expected_manifest_files.append(
                {"name": name, "sha256": _file_sha256(path)}
            )
    _append(
        failures,
        manifest
        == {
            "schema": 1,
            "id": "information-equivalent-trial-packet-build-manifest",
            "status": "prepared-zero-dispatch",
            "files": expected_manifest_files,
            "privateOracleCanonicalSha256": private_oracle_sha256,
            "privateOracleContentWritten": False,
            "agentRunStartedAtBuildTime": False,
            "dispatchCount": 0,
        },
        "fail-build-manifest",
    )

    return {
        "schema": 1,
        "status": (
            "passed-zero-dispatch-live-authority-still-required"
            if not failures
            else "blocked-zero-dispatch"
        ),
        "failureCodes": failures,
        "dispatchCount": 0,
        "scoredArmIds": [],
        "liveTaskCreationAuthorized": False,
        "publicInformationBundleCanonicalSha256": public_bundle_sha256,
        "privateOracleCanonicalSha256": private_oracle_sha256,
    }


def validate_packet_package(
    output: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    report = evaluate_packet_package(output, root=root)
    if report["failureCodes"]:
        raise RuntimeError(
            "Information-equivalent trial packet preflight failed: "
            + report["failureCodes"][0]
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate_packet_package(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
