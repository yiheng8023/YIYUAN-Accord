#!/usr/bin/env python3
"""Validate the offline Noru learning-material calibration package."""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CALIBRATION_PATH = (
    ROOT / "registry/human-ai-collaboration-learning-noru-material-calibration-2026-07-31.json"
)
PUBLIC_PATH = ROOT / "tests/fixtures/human-ai-learning-noru-public-packet-2026-07-31.json"
PRIVATE_PATH = ROOT / "tests/fixtures/human-ai-learning-noru-private-oracle-2026-07-31.json"
PROGRAM_PLAN_PATH = ROOT / "registry/curation-program-plan.json"
FORBIDDEN_PUBLIC_KEYS = {
    "answer",
    "answerCriteria",
    "maximumPoints",
    "misconceptionIds",
    "oracleCase",
    "points",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key) for key in value)
        for child in value.values():
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def _parse_state(value: str) -> tuple[str, str, int]:
    band, mark, count_text = value.split("/")
    count = int(count_text)
    _require(band in {"ava", "bor"}, f"Unknown Noru band: {band}")
    _require(mark in {"plain", "ring"}, f"Unknown Noru mark: {mark}")
    _require(count in {1, 2, 3}, f"Unknown Noru count: {count}")
    return band, mark, count


def _render_state(state: tuple[str, str, int]) -> str:
    return f"{state[0]}/{state[1]}/{state[2]}"


def _apply(state: tuple[str, str, int], operation: str) -> tuple[str, str, int]:
    band, mark, count = state
    if operation == "flip":
        return ("bor" if band == "ava" else "ava", mark, count)
    _require(operation == "echo", f"Unknown Noru operation: {operation}")
    if mark == "plain":
        return band, "ring", 1 if count == 3 else count + 1
    return band, "plain", count


def _transform(start: str, operations: list[str]) -> str:
    state = _parse_state(start)
    for operation in operations:
        state = _apply(state, operation)
    return _render_state(state)


def _compatible(left: str, right: str) -> bool:
    left_band, left_mark, left_count = _parse_state(left)
    right_band, right_mark, right_count = _parse_state(right)
    if left_mark == right_mark == "ring":
        return False
    return (
        left_band == right_band and left_count + right_count == 4
    ) or (
        left_band != right_band and left_mark == right_mark
    )


def _inverse(target: str, operation: str) -> list[str]:
    matches = []
    for band, mark, count in product(("ava", "bor"), ("plain", "ring"), (1, 2, 3)):
        candidate = _render_state((band, mark, count))
        if _transform(candidate, [operation]) == target:
            matches.append(candidate)
    return sorted(matches)


def validate_calibration(
    calibration: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    public_packet: dict[str, Any] | None = None,
    private_oracle: dict[str, Any] | None = None,
    program_plan: dict[str, Any] | None = None,
) -> None:
    calibration = calibration or _load(
        root
        / "registry/human-ai-collaboration-learning-noru-material-calibration-2026-07-31.json"
    )
    public_packet = public_packet or _load(
        root / "tests/fixtures/human-ai-learning-noru-public-packet-2026-07-31.json"
    )
    private_oracle = private_oracle or _load(
        root / "tests/fixtures/human-ai-learning-noru-private-oracle-2026-07-31.json"
    )
    program_plan = program_plan or _load(root / "registry/curation-program-plan.json")

    _require(calibration.get("schema") == 1, "Noru calibration schema drifted")
    _require(
        calibration.get("status")
        == "offline-structural-and-oracle-logic-calibrated-independent-human-review-open",
        "Noru calibration status drifted",
    )
    _require(calibration.get("scenarioId") == "GEN-LEARNING-01", "Noru scenario drifted")
    for source_key in ("publicPacket", "privateOracle", "parentProtocol"):
        source = calibration.get("materialIdentity", {}).get(source_key, {})
        path = root / str(source.get("path", ""))
        _require(path.is_file(), f"Noru bound material is missing: {source.get('path')}")
        _require(path.stat().st_size == source.get("bytes"), f"Noru material size drifted: {source.get('path')}")
        _require(_sha256(path) == source.get("sha256"), f"Noru material hash drifted: {source.get('path')}")

    _require(public_packet.get("visibility") == "learner-and-tutor-public", "Public visibility drifted")
    _require(private_oracle.get("visibility") == "independent-evaluator-only-never-tutor-or-learner", "Private visibility drifted")
    _require(private_oracle.get("publicPacketId") == public_packet.get("id"), "Public/private binding drifted")
    leaked_keys = _walk_keys(public_packet) & FORBIDDEN_PUBLIC_KEYS
    _require(not leaked_keys, f"Public packet leaks assessment keys: {sorted(leaked_keys)}")
    _require(len(public_packet.get("rules", [])) == 5, "Noru public rule count drifted")
    _require(len(public_packet.get("workedExamples", [])) == 4, "Noru worked-example count drifted")
    practice = public_packet.get("practiceItems", [])
    _require(len(practice) == 8, "Noru practice-item count drifted")

    pretest = private_oracle.get("baselinePretest", {})
    immediate = private_oracle.get("immediateForm", {})
    delayed = private_oracle.get("delayedForm", {})
    transfer = private_oracle.get("novelTransfer", {})
    _require(len(pretest.get("items", [])) == 3 and pretest.get("maximumPoints") == 5, "Noru pretest drifted")
    _require(len(immediate.get("items", [])) == 6 and immediate.get("maximumPoints") == 14, "Noru immediate form drifted")
    _require(len(delayed.get("items", [])) == 6 and delayed.get("maximumPoints") == 14, "Noru delayed form drifted")
    _require(len(transfer.get("items", [])) == 3 and transfer.get("maximumPoints") == 12, "Noru transfer form drifted")

    public_ids = {
        item.get("id")
        for key in ("workedExamples", "practiceItems")
        for item in public_packet.get(key, [])
    }
    assessment_items = (
        pretest.get("items", [])
        + immediate.get("items", [])
        + delayed.get("items", [])
        + transfer.get("items", [])
    )
    assessment_ids = {item.get("id") for item in assessment_items}
    _require(len(assessment_ids) == len(assessment_items), "Noru assessment ids are not unique")
    _require(not (public_ids & assessment_ids), "Noru practice and assessment ids overlap")

    misconception_ids = {
        item.get("id") for item in private_oracle.get("misconceptions", [])
    }
    _require(len(misconception_ids) == 8, "Noru misconception inventory drifted")
    for item in immediate.get("items", []) + delayed.get("items", []) + transfer.get("items", []):
        _require(
            set(item.get("misconceptionIds", [])) <= misconception_ids,
            f"Noru misconception reference is unresolved: {item.get('id')}",
        )
        case = item.get("oracleCase")
        if not case:
            continue
        if case.get("kind") == "transform":
            computed = _transform(case.get("start"), case.get("operations", []))
            _require(computed == item.get("answer"), f"Noru transform oracle mismatch: {item.get('id')}")
        elif case.get("kind") == "compatibility":
            computed = _compatible(case.get("left"), case.get("right"))
            _require(computed is case.get("expected"), f"Noru compatibility oracle mismatch: {item.get('id')}")
            _require(item.get("answer", "").startswith("Yes" if computed else "No"), f"Noru compatibility answer mismatch: {item.get('id')}")
        elif case.get("kind") == "inverse":
            computed = _inverse(case.get("target"), case.get("operation"))
            _require(computed == sorted(item.get("answer", [])), f"Noru inverse oracle mismatch: {item.get('id')}")
        else:
            raise RuntimeError(f"Unknown Noru oracle case: {item.get('id')}")

    accessibility = public_packet.get("accessibility", {})
    _require(accessibility.get("textLabelsCarryAllMeaning") is True, "Noru text accessibility drifted")
    for key in ("colorRequired", "imageRequired", "audioRequired"):
        _require(accessibility.get(key) is False, f"Noru gained a non-text dependency: {key}")
    data = public_packet.get("dataBoundary", {})
    for key in (
        "participantIdentityRequired",
        "educationalRecordRequired",
        "employmentRecordRequired",
        "freeTextPersonalHistoryRequired",
    ):
        _require(data.get(key) is False, f"Noru expanded participant data: {key}")

    parallel = private_oracle.get("parallelFormBoundary", {})
    _require(parallel.get("equivalenceProved") is False, "Noru form equivalence was overclaimed")
    _require(parallel.get("sharedExactBlueprintCount") == 4, "Noru exact blueprint pairing drifted")
    cleanup = calibration.get("cleanupManifest", {})
    _require(
        cleanup.get("trialRootTemplate") == ".tmp/aah-learning-noru/<trial-id>",
        "Noru cleanup root broadened",
    )
    for key in (
        "rootMustResolveInsideRepositoryTmp",
        "beforeManifestRequired",
        "afterManifestRequired",
        "externalProcessReceiptRequiredIfUsed",
        "exactRootRemovalOrGovernedRetentionDecisionRequired",
        "uncertainOwnershipFailsClosed",
    ):
        _require(cleanup.get(key) is True, f"Noru cleanup control weakened: {key}")

    claims = calibration.get("claimBoundary", {})
    _require(claims.get("deterministicRuleOracleConsistencyProved") is True, "Noru deterministic claim drifted")
    _require(claims.get("publicPrivateStructuralSeparationProved") is True, "Noru separation claim drifted")
    for key, value in claims.items():
        if key not in {
            "deterministicRuleOracleConsistencyProved",
            "publicPrivateStructuralSeparationProved",
        }:
            _require(value is False, f"Noru calibration promoted claim: {key}")
    authority = calibration.get("authorityBoundary", {})
    _require(authority.get("repositoryMaterialAndValidatorWritesAuthorized") is True, "Noru repository authority drifted")
    for key, value in authority.items():
        if key != "repositoryMaterialAndValidatorWritesAuthorized":
            _require(value is False, f"Noru calibration expanded authority: {key}")

    initiatives = {item.get("id"): item for item in program_plan.get("currentInitiatives", [])}
    expected_path = "registry/human-ai-collaboration-learning-noru-material-calibration-2026-07-31.json"
    for initiative_id in (
        "initiative.capability-survey-gap-proof",
        "initiative.human-ai-collaboration-coverage-rebaseline",
    ):
        _require(
            initiatives.get(initiative_id, {}).get("currentLearningMaterialCalibration") == expected_path,
            f"Noru program-plan pointer is missing: {initiative_id}",
        )

    document = (
        root
        / "docs/strategy/HUMAN-AI-COLLABORATION-LEARNING-NORU-MATERIAL-CALIBRATION-2026-07-31.md"
    ).read_text(encoding="utf-8")
    normalized = " ".join(document.split())
    for phrase in (
        "Public assessment answer leakage is zero",
        "This is not empirical form equivalence",
        "An accessibility barrier is not a domain misconception",
        ".tmp/aah-learning-noru/<trial-id>",
        "independent content review remains open",
    ):
        _require(phrase in normalized, f"Noru calibration document missing: {phrase}")


def main() -> int:
    validate_calibration()
    print("Human-AI Noru learning-material calibration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
