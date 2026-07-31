#!/usr/bin/env python3
"""Build a deterministic packet for a later independent engineering review.

The packet freezes an already-committed target through Git object identities
and SHA-256 digests.  It does not run a reviewer, create a review receipt, or
exercise acceptance authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = Path(
    "registry/"
    "multidimensional-software-engineering-independent-review-readiness-"
    "contract-2026-07-31.json"
)
PACKET_PATH = Path(
    "registry/"
    "multidimensional-software-engineering-independent-review-packet-"
    "2026-07-31.json"
)


class IndependentReviewPacketError(RuntimeError):
    """Raised when the review-readiness contract or packet fails closed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IndependentReviewPacketError(message)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"{path.name} must contain one object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _parse_timestamp(value: Any, *, label: str) -> None:
    _require(isinstance(value, str) and bool(value), f"{label} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise IndependentReviewPacketError(f"{label} is invalid") from error
    _require(parsed.tzinfo is not None, f"{label} must include a timezone")


def validate_contract(contract: dict[str, Any]) -> None:
    _require(contract.get("schema") == 1, "Review contract schema drifted")
    _require(
        contract.get("status")
        == "prepared-not-reviewed-deferred-candidate-coverage-first",
        "Review contract status drifted",
    )
    target_revision = contract.get("targetRevision")
    _require(
        isinstance(target_revision, str) and len(target_revision) == 40,
        "Review target revision is invalid",
    )
    target_paths = contract.get("targetPaths")
    _require(
        isinstance(target_paths, list)
        and target_paths
        and target_paths == sorted(set(target_paths)),
        "Review target paths must be one sorted unique set",
    )
    subject_paths: list[str] = []
    for subject in contract.get("subjectPackages", []):
        _require(
            isinstance(subject, dict)
            and isinstance(subject.get("id"), str)
            and bool(subject["id"])
            and isinstance(subject.get("paths"), list)
            and bool(subject["paths"]),
            "Review subject package is incomplete",
        )
        subject_paths.extend(subject["paths"])
    _require(
        set(subject_paths) == set(target_paths),
        "Review subject packages do not cover the exact target path set",
    )

    producer = contract.get("producerBoundary", {})
    _require(
        producer.get("identityEvidenceIsCryptographic") is False
        and producer.get("sameTaskRereadQualifiesAsIndependentReview") is False
        and producer.get("reviewSkillInvocationAloneQualifiesAsIndependentReview")
        is False
        and producer.get("distinctExecutionIdentityRequired") is True
        and producer.get("distinctProcessIdRequired") is True
        and producer.get("privateReasoningTransferAllowed") is False
        and producer.get("reviewerArtifactMutationAllowed") is False,
        "Review independence boundary drifted",
    )
    blocked_identities = {
        producer.get("packetProducerIdentity"),
        *producer.get("reportEvaluatorIdentities", []),
    }
    _require(
        all(isinstance(value, str) and bool(value) for value in blocked_identities),
        "Producer identities are incomplete",
    )
    _require(
        isinstance(producer.get("packetProducerProcessId"), str)
        and bool(producer["packetProducerProcessId"]),
        "Producer process identity is missing",
    )

    axes = contract.get("reviewAxes")
    _require(
        isinstance(axes, list)
        and len(axes) >= 8
        and len({item.get("id") for item in axes}) == len(axes)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and bool(item["id"])
            and isinstance(item.get("question"), str)
            and bool(item["question"])
            for item in axes
        ),
        "Review axes are missing or duplicated",
    )
    required_axis_ids = {
        "spec-and-repository-standards",
        "source-rights-and-bounded-use",
        "source-identity-evidence-strength-and-freshness",
        "conflict-ambiguity-and-counterevidence",
        "dimension-floor-and-profile-judgments",
        "evidence-scope-affected-party-and-authority-boundary",
        "claim-authority-and-acceptance-boundary",
        "provenance-portability-and-line-ending-semantics",
        "deterministic-reproduction-and-negative-controls",
        "capability-reuse-and-residual-gap-boundary",
    }
    _require(
        {item["id"] for item in axes} == required_axis_ids,
        "Review axis vocabulary drifted",
    )

    receipt = contract.get("receiptContract", {})
    _require(
        receipt.get("allReviewAxesRequiredExactlyOnce") is True
        and receipt.get("reviewerIdentityMustDifferFromAllProducerIdentities")
        is True
        and receipt.get("reviewProcessMustDifferFromProducerProcess") is True
        and receipt.get("priorInvolvementDisclosureRequired") is True
        and receipt.get("identityEvidenceRequired") is True
        and receipt.get("findingEvidenceReferencesRequired") is True
        and receipt.get("highAndCriticalFindingDispositionRequired") is True
        and receipt.get("disagreementsMustRemainVisible") is True
        and receipt.get("acceptanceAuthorityMayBeExercisedByReceipt") is False
        and receipt.get("hardStandardMayBePromotedByReceipt") is False
        and receipt.get("skillNecessityMayBeProvedByReceipt") is False,
        "Review receipt boundary drifted",
    )
    _require(
        set(receipt.get("allowedAxisOutcomes", []))
        == {
            "accept-bounded",
            "accept-with-corrections",
            "reject",
            "insufficient-evidence",
        }
        and set(receipt.get("allowedOverallOutcomes", []))
        == set(receipt["allowedAxisOutcomes"]),
        "Review outcome vocabulary drifted",
    )
    state = contract.get("packetState", {})
    _require(
        state
        == {
            "reviewPerformed": False,
            "reviewReceiptPath": None,
            "reviewDeferredUntilCandidateCoverage": True,
            "acceptanceDecisionRequested": False,
            "modelDispatchPerformed": False,
            "externalWritePerformed": False,
        },
        "Review packet state falsely claims execution",
    )
    claims = contract.get("claimBoundary", {})
    _require(
        claims.get("provesTargetArtifactsFrozen") is True
        and claims.get("provesManifestRebuildableFromGit") is True
        and claims.get("provesIndependentReviewPerformed") is False
        and claims.get("provesReviewerIdentityBeyondFutureReceiptEvidence")
        is False
        and claims.get("provesSourceInterpretationCorrect") is False
        and claims.get("provesAssessmentJudgmentsCorrect") is False
        and claims.get("provesBroadPopulationValidity") is False
        and claims.get("provesHardStandardEligibility") is False
        and claims.get("provesEvaluationSkillNecessary") is False
        and claims.get("authorizesAcceptanceOrRelease") is False,
        "Review packet claim boundary drifted",
    )
    authority = contract.get("authorityBoundary", {})
    _require(
        isinstance(authority, dict)
        and authority
        and all(value is False for value in authority.values()),
        "Review readiness contract expanded authority",
    )


def _run_git(
    arguments: list[str],
    *,
    root: Path,
    text: bool,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=text,
        encoding="utf-8" if text else None,
    )


def _git_manifest(
    revision: str,
    paths: list[str],
    *,
    root: Path,
) -> list[dict[str, str]]:
    resolved_revision = _run_git(
        ["rev-parse", f"{revision}^{{commit}}"],
        root=root,
        text=True,
    ).stdout.strip()
    _require(
        resolved_revision == revision,
        "Review target revision did not resolve to the exact pinned commit",
    )
    process = _run_git(
        ["ls-tree", revision, "--", *paths],
        root=root,
        text=True,
    )
    records: dict[str, dict[str, str]] = {}
    for line in process.stdout.splitlines():
        metadata, path = line.split("\t", maxsplit=1)
        mode, object_type, object_id = metadata.split(" ", maxsplit=2)
        _require(path not in records, f"Duplicate Git path: {path}")
        blob_bytes = _run_git(
            ["show", f"{revision}:{path}"],
            root=root,
            text=False,
        ).stdout
        records[path] = {
            "path": path,
            "mode": mode,
            "objectType": object_type,
            "gitObjectId": object_id,
            "contentSha256": hashlib.sha256(blob_bytes).hexdigest(),
        }
    _require(
        set(records) == set(paths),
        "Review target Git object inventory is incomplete",
    )
    _require(
        all(record["objectType"] == "blob" for record in records.values()),
        "Review target contains a non-blob path",
    )
    return [records[path] for path in paths]


def build_packet(
    contract: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    root = root.resolve()
    contract_path = root / CONTRACT_PATH
    contract = contract or _load(contract_path)
    validate_contract(contract)
    manifest = _git_manifest(
        contract["targetRevision"],
        contract["targetPaths"],
        root=root,
    )
    manifest_digest = canonical_sha256(manifest)
    result = {
        "schema": 1,
        "id": "multidimensional-software-engineering-independent-review-packet-2026-07-31",
        "asOf": contract["asOf"],
        "status": "prepared-not-reviewed-deferred",
        "contractBinding": {
            "path": CONTRACT_PATH.as_posix(),
            "sha256": file_sha256(contract_path),
        },
        "targetBinding": {
            "revision": contract["targetRevision"],
            "pathCount": len(manifest),
            "manifestSha256": manifest_digest,
            "files": manifest,
        },
        "subjectPackages": contract["subjectPackages"],
        "producerBoundary": contract["producerBoundary"],
        "reviewAxes": contract["reviewAxes"],
        "receiptContract": contract["receiptContract"],
        "packetState": contract["packetState"],
        "reproduction": {
            "requiresRepositoryWithTargetGitObjects": True,
            "networkRequired": False,
            "modelRequired": False,
            "commands": [
                "python -B scripts/build_multidimensional_software_engineering_independent_review_packet.py --check",
                "python -B scripts/validate_multidimensional_software_engineering_independent_review_packet.py",
                "python -B -m unittest tests.test_multidimensional_software_engineering_independent_review_packet",
            ],
        },
        "claimBoundary": contract["claimBoundary"],
        "authorityBoundary": contract["authorityBoundary"],
    }
    result["packetSha256"] = canonical_sha256(result)
    return result


def _serialized(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--print",
        action="store_true",
        help="Print the deterministic packet without writing a file.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail when the checked-in packet differs from a rebuild.",
    )
    arguments = parser.parse_args()
    expected = build_packet()
    if arguments.print:
        print(_serialized(expected), end="")
        return 0
    actual = _load(ROOT / PACKET_PATH)
    _require(actual == expected, "Checked-in independent-review packet is stale")
    print("Independent-review packet is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
