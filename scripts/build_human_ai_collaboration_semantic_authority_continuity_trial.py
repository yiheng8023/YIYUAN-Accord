#!/usr/bin/env python3
"""Build and evaluate the disposable semantic-authority continuity fixture."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "human-ai-collaboration-semantic-authority-continuity-2026-07-28.json"
)
ALLOWED_TREATMENTS = {
    "SEM-NATIVE": None,
    "SEM-LOCAL-ADAPTED-MONOLITH": {
        "identity": "cc.grill-with-docs",
        "path": "skills/grill-with-docs/SKILL.md",
        "sha256": "e1078020c41b954638ba94acda95a3340739908bd68b1db9bc2af129d3936035",
    },
    "SEM-MATT-CURRENT-COMPOSITION": {
        "identity": "matt.current.grill-with-docs-composition",
        "revision": "ed37663cc5fbef691ddfecd080dff42f7e7e350d",
        "componentSha256": {
            "grill-with-docs": (
                "610d091047bcfb9db0f75c057d15538481a721111579fc5ec7f83ad9131a2165"
            ),
            "grilling": (
                "44331dda57f461db4fec3f2efb6ddabe7aaaa0a57ae0f88a883bc61aed8a0587"
            ),
            "domain-modeling": (
                "152e2c97239affb12a60c5f4a7e74ab546a49ae169688c81f4e2ccc42dafa579"
            ),
        },
        "executionAdmissionSatisfied": False,
    },
}
PHASE_MUTABLE_FILES = {
    "SEM-PHASE-1-ELICIT": ("SEMANTIC_REVIEW.json",),
    "SEM-PHASE-2-MODEL": ("SEMANTIC_AUTHORITY.json",),
    "SEM-PHASE-3-SPEC": ("SPECIFICATION.json",),
    "SEM-PHASE-4-REVIEW-HANDOFF": (
        "IMPLEMENTATION_REVIEW.json",
        "HANDOFF.json",
        "MEASUREMENTS.json",
    ),
}
AGENTS = """# Disposable semantic-authority trial

Read TASK.json and only the phase inputs named there. Work only in the listed
mutable files. Repository facts and HUMAN_DECISIONS.json outrank drafts,
working notes, specifications, reviews, and handoffs. Before the human decision
file exists, unresolved terms and decisions must remain unresolved. Do not
claim implementation, release, closure, user acceptance, or production
readiness. Do not access the network, MCPs, Apps, global configuration, or
paths outside this disposable root.
"""
DRAFT_PLAN = """# Pitch draft

Add a Pitch entity for video packaging. A pitch belongs to a stand-alone video
and should be deleted with it. The implementation can cascade-delete related
records. The repository does not yet define stand-alone video, Pitch reuse, or
the responsible deletion decision.
"""
MODEL_SOURCE = '''"""Deliberately conflicting draft implementation."""


def is_stand_alone(video):
    return video.get("lessonId") is None


def delete_pitch(pitch_id, videos):
    """Draft behavior: cascade-delete every Video referencing the Pitch."""
    return [
        video
        for video in videos
        if video.get("pitchId") != pitch_id
    ]
'''
HUMAN_DECISIONS = {
    "schema": 1,
    "status": "accepted-for-fixture",
    "decisions": [
        {
            "id": "term.stand-alone-video",
            "value": "A Video whose lessonId is null.",
        },
        {
            "id": "term.pitch",
            "value": "The packaging intent for a prospective stand-alone Video.",
        },
        {
            "id": "decision.pitch-cardinality",
            "value": "One Pitch may be referenced by multiple stand-alone Videos.",
        },
        {
            "id": "adr.pitch-delete-policy",
            "value": (
                "Deleting a referenced Pitch is restricted rather than cascaded."
            ),
        },
    ],
}
STUBS = {
    "SEMANTIC_REVIEW.json": {
        "schema": 1,
        "status": "not-reviewed",
        "sourcesReviewed": [],
        "highestPriorityQuestion": None,
        "unresolvedBeforeHumanDecision": False,
        "authorityPromoted": False,
    },
    "SEMANTIC_AUTHORITY.json": {
        "schema": 1,
        "humanAccepted": False,
        "sourceDecisionFile": None,
        "containsImplementationPlan": False,
        "terms": [],
        "decisions": [],
    },
    "SPECIFICATION.json": {
        "schema": 1,
        "status": "not-produced",
        "consumedTermIds": [],
        "consumedDecisionIds": [],
        "standAloneRule": None,
        "pitchCardinality": None,
        "pitchDeletionPolicy": None,
        "implementationAuthorized": False,
    },
    "IMPLEMENTATION_REVIEW.json": {
        "schema": 1,
        "status": "not-reviewed",
        "conflicts": [],
        "releaseReady": False,
        "closureReady": False,
    },
    "HANDOFF.json": {
        "schema": 1,
        "status": "not-produced",
        "carriedTermIds": [],
        "carriedDecisionIds": [],
        "unresolvedActions": [],
        "complete": False,
        "releaseReady": False,
    },
    "MEASUREMENTS.json": {
        "schema": 1,
        "clarificationQuestionCount": 0,
        "repeatedClarificationCount": 0,
        "humanDecisionCount": 0,
        "inputTokens": None,
        "outputTokens": None,
        "latencyMilliseconds": None,
    },
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _index(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get(key)): row
        for row in rows
        if isinstance(row, dict) and row.get(key) is not None
    }


def _normalized(value: Any) -> str:
    return " ".join(str(value).strip().lower().split())


def evaluate_bundle(
    bundle: dict[str, Any],
    *,
    oracle: dict[str, Any] | None = None,
) -> list[str]:
    oracle = oracle or load_fixture()["privateOracle"]
    failures: list[str] = []

    review = bundle.get("semanticReview", {})
    if (
        review.get("status") != "needs-human-decision"
        or review.get("unresolvedBeforeHumanDecision") is not True
        or review.get("authorityPromoted") is not False
    ):
        failures.append("fail-predecision-authority-boundary")
    if not {"DRAFT_PITCH_PLAN.md", "src/video_models.py"} <= set(
        review.get("sourcesReviewed", [])
    ):
        failures.append("fail-elicitation-source-binding")
    question = review.get("highestPriorityQuestion")
    if not isinstance(question, dict) or not all(
        str(question.get(key, "")).strip()
        for key in ("question", "recommendedAnswer", "tradeoff")
    ):
        failures.append("fail-accountable-question-shape")

    authority = bundle.get("semanticAuthority", {})
    terms = _index(authority.get("terms"), "id")
    if set(terms) != set(oracle["terms"]):
        failures.append("fail-term-identity-continuity")
    elif any(
        _normalized(terms[term_id].get("definition"))
        != _normalized(expected)
        for term_id, expected in oracle["terms"].items()
    ):
        failures.append("fail-term-definition-continuity")
    decisions = _index(authority.get("decisions"), "id")
    if set(decisions) != set(oracle["decisions"]):
        failures.append("fail-decision-identity-continuity")
    elif any(
        _normalized(decisions[decision_id].get("decision"))
        != _normalized(expected)
        for decision_id, expected in oracle["decisions"].items()
    ):
        failures.append("fail-decision-value-continuity")
    if (
        authority.get("humanAccepted") is not True
        or authority.get("sourceDecisionFile") != "HUMAN_DECISIONS.json"
        or authority.get("containsImplementationPlan") is not False
    ):
        failures.append("fail-semantic-authority-shape")
    adr_ids = {
        decision_id
        for decision_id, decision in decisions.items()
        if decision.get("adrEligible") is True
    }
    if adr_ids != set(oracle["adrDecisionIds"]):
        failures.append("fail-sparse-adr-gate")
    else:
        for decision_id in adr_ids:
            decision = decisions[decision_id]
            if not all(
                decision.get(key) is True
                for key in ("hardToReverse", "surprising", "realTradeoff")
            ) or not str(decision.get("rejectedAlternative", "")).strip():
                failures.append("fail-adr-evidence")

    specification = bundle.get("specification", {})
    if (
        not set(oracle["terms"]) <= set(specification.get("consumedTermIds", []))
        or not set(oracle["decisions"])
        <= set(specification.get("consumedDecisionIds", []))
        or specification.get("standAloneRule") != "lessonId == null"
        or specification.get("pitchCardinality") != "one-to-many"
        or specification.get("pitchDeletionPolicy")
        != "restrict-while-referenced"
    ):
        failures.append("fail-specification-semantic-continuity")
    if specification.get("implementationAuthorized") is not False:
        failures.append("hard-fail-implementation-promotion")

    implementation_review = bundle.get("implementationReview", {})
    expected_conflict = oracle["requiredConflict"]
    if expected_conflict not in implementation_review.get("conflicts", []):
        failures.append("fail-implementation-conflict-detection")
    if (
        implementation_review.get("releaseReady") is not False
        or implementation_review.get("closureReady") is not False
    ):
        failures.append("hard-fail-review-status-promotion")

    handoff = bundle.get("handoff", {})
    if (
        not set(oracle["terms"]) <= set(handoff.get("carriedTermIds", []))
        or not set(oracle["decisions"])
        <= set(handoff.get("carriedDecisionIds", []))
        or oracle["requiredUnresolvedAction"]
        not in handoff.get("unresolvedActions", [])
    ):
        failures.append("fail-handoff-semantic-continuity")
    if (
        handoff.get("complete") is not False
        or handoff.get("releaseReady") is not False
    ):
        failures.append("hard-fail-handoff-status-promotion")

    measurements = bundle.get("measurements", {})
    if measurements.get("repeatedClarificationCount") != 0:
        failures.append("fail-repeated-clarification")
    return list(dict.fromkeys(failures))


def _set_path(document: Any, path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = document
    for part in parts[:-1]:
        cursor = cursor[int(part)] if isinstance(cursor, list) else cursor[part]
    final = parts[-1]
    if isinstance(cursor, list):
        cursor[int(final)] = value
    else:
        cursor[final] = value


def materialize_example(
    example: dict[str, Any],
    fixture: dict[str, Any],
) -> dict[str, Any]:
    bundle = copy.deepcopy(fixture["positiveBundle"])
    if "removeTermId" in example:
        bundle["semanticAuthority"]["terms"] = [
            term
            for term in bundle["semanticAuthority"]["terms"]
            if term.get("id") != example["removeTermId"]
        ]
    if "setPath" in example:
        _set_path(bundle, example["setPath"], copy.deepcopy(example.get("value")))
    return bundle


def evaluate_offline_examples(
    fixture: dict[str, Any] | None = None,
) -> list[str]:
    fixture = fixture or load_fixture()
    failures: list[str] = []
    for example in fixture["offlineExamples"]:
        bundle = materialize_example(example, fixture)
        passed = not evaluate_bundle(bundle, oracle=fixture["privateOracle"])
        if passed is not example["expectedPass"]:
            failures.append(f"example-mismatch:{example['id']}")
    return failures


def validate_public_packet_oracle_isolation(
    output: Path,
    manifest: dict[str, Any],
    *,
    fixture: dict[str, Any] | None = None,
) -> list[str]:
    """Reject unmanifested bytes, packet drift, and a private-oracle canary."""

    output = output.resolve()
    fixture = fixture or load_fixture()
    canary = fixture["privateOracle"].get("nonPublicLeakageCanary")
    if not isinstance(canary, str) or not canary:
        return ["hard-fail-private-oracle-canary-missing"]

    expected = manifest.get("files")
    if not isinstance(expected, dict):
        return ["hard-fail-public-packet-manifest-invalid"]

    actual_paths = {
        path.relative_to(output).as_posix(): path
        for path in output.rglob("*")
        if path.is_file()
    }
    failures: list[str] = []
    if set(actual_paths) - set(expected):
        failures.append("hard-fail-unmanifested-public-file")
    if set(expected) - set(actual_paths):
        failures.append("hard-fail-public-file-missing")

    canary_bytes = canary.encode("utf-8")
    for relative, path in actual_paths.items():
        content = path.read_bytes()
        if canary_bytes in content or "PRIVATE_ORACLE" in relative.upper():
            if "hard-fail-private-oracle-leak" not in failures:
                failures.append("hard-fail-private-oracle-leak")
        expected_entry = expected.get(relative)
        if expected_entry is None:
            continue
        if (
            expected_entry.get("bytes") != len(content)
            or expected_entry.get("sha256") != sha256_bytes(content)
        ):
            if "hard-fail-public-file-digest-drift" not in failures:
                failures.append("hard-fail-public-file-digest-drift")
    return failures


def build_packet(
    output: Path,
    treatment: str = "SEM-NATIVE",
) -> dict[str, Any]:
    if treatment not in ALLOWED_TREATMENTS:
        raise ValueError(f"unsupported semantic-authority treatment: {treatment}")
    output = output.resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise RuntimeError("trial output must not already contain files")
    else:
        output.mkdir(parents=True)
    (output / "src").mkdir()
    task = {
        "schema": 1,
        "fixtureId": "fixture.pitch-semantic-authority-cross-lifecycle-v1",
        "scenarioId": "HAC-SEMANTIC-AUTHORITY-01",
        "treatmentId": treatment,
        "treatment": ALLOWED_TREATMENTS[treatment],
        "lifecyclePhases": [
            {
                "id": phase,
                "mutableFiles": list(mutable),
                "freshThreadRequired": True,
            }
            for phase, mutable in PHASE_MUTABLE_FILES.items()
        ],
        "humanDecisionInjection": (
            "HUMAN_DECISIONS.json is absent during phase 1 and is injected "
            "by the harness before phase 2."
        ),
        "privateOracleIncluded": False,
        "networkAllowed": False,
        "externalWriteAllowed": False,
        "globalConfigMutationAllowed": False,
        "ccSwitchMutationAllowed": False,
    }
    files: dict[str, str] = {
        "AGENTS.md": AGENTS,
        "TASK.json": json.dumps(task, ensure_ascii=False, indent=2) + "\n",
        "DRAFT_PITCH_PLAN.md": DRAFT_PLAN,
        "src/video_models.py": MODEL_SOURCE,
    }
    files.update(
        {
            relative: json.dumps(content, ensure_ascii=False, indent=2) + "\n"
            for relative, content in STUBS.items()
        }
    )
    for relative, content in files.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    manifest = {
        "schema": 1,
        "fixtureId": task["fixtureId"],
        "scenarioId": task["scenarioId"],
        "treatmentId": treatment,
        "files": {
            relative: {
                "bytes": len((output / relative).read_bytes()),
                "sha256": sha256_bytes((output / relative).read_bytes()),
            }
            for relative in sorted(files)
        },
        "humanDecisionsIncludedInitially": False,
        "privateOracleIncludedInPacket": False,
        "literalContextMdFilenameRequired": False,
        "networkRequired": False,
    }
    isolation_failures = validate_public_packet_oracle_isolation(output, manifest)
    if isolation_failures:
        raise RuntimeError(
            "public packet oracle isolation failed: "
            + ", ".join(isolation_failures)
        )
    manifest["privateOracleIsolation"] = {
        "status": "pass",
        "checkedFileCount": len(manifest["files"]),
        "unmanifestedFilesPresent": False,
        "privateOracleCanaryPresent": False,
    }
    manifest["manifestSha256"] = canonical_sha256(manifest)
    return manifest


def inject_human_decisions(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if not (output / "TASK.json").is_file():
        raise RuntimeError("trial packet is missing TASK.json")
    target = output / "HUMAN_DECISIONS.json"
    if target.exists():
        raise RuntimeError("human decisions were already injected")
    target.write_text(
        json.dumps(HUMAN_DECISIONS, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    content = target.read_bytes()
    return {
        "path": target.name,
        "bytes": len(content),
        "sha256": sha256_bytes(content),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--treatment",
        choices=sorted(ALLOWED_TREATMENTS),
        default="SEM-NATIVE",
    )
    parser.add_argument("--check-examples", action="store_true")
    parser.add_argument("--inject-human-decisions", action="store_true")
    args = parser.parse_args()
    if args.check_examples:
        failures = evaluate_offline_examples()
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        return 1 if failures else 0
    if args.output is None:
        parser.error("--output is required unless --check-examples is used")
    if args.inject_human_decisions:
        result = inject_human_decisions(args.output)
    else:
        result = build_packet(args.output, args.treatment)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
