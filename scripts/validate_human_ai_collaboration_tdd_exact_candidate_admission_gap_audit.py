#!/usr/bin/env python3
"""Validate the exact-candidate TDD diagnostic admission gap audit."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-exact-candidate-admission-gap-audit-"
    "2026-07-26.json"
)
PROTOCOL_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "protocol-2026-07-26.json"
)
PREFLIGHT_PATH = (
    "registry/"
    "human-ai-collaboration-tdd-noncomparative-treatment-diagnostic-"
    "source-governance-preflight-2026-07-26.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/"
    "HUMAN-AI-COLLABORATION-TDD-EXACT-CANDIDATE-ADMISSION-GAP-AUDIT-"
    "2026-07-26.md"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_identity_envelope(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "candidateId": candidate["candidateId"],
            "sourceRevisionOrVersion": candidate["sourceRevisionOrVersion"],
            "licenseSha256": candidate["license"]["sha256"],
            "files": [
                {
                    "path": item["path"],
                    "sha256": item["sha256"],
                }
                for item in candidate["files"]
            ],
            "projectionTreeSha256": candidate["projectionTreeSha256"],
        }
        for candidate in protocol["candidates"]
    ]


def _relative_claim_surfaces(
    document: dict[str, Any],
    *,
    documentation: str,
) -> list[str]:
    surfaces = [
        str(document.get("purpose", "")),
        *[
            str(item)
            for item in document.get("criteria", [])
            if isinstance(item, str)
        ],
        str(document.get("decision", {}).get("nextBoundedAction", "")),
        documentation,
    ]
    for candidate in document.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        for evidence_class in ("passes", "partials", "blockers"):
            for entry in candidate.get(evidence_class, []):
                if not isinstance(entry, dict):
                    continue
                surfaces.append(str(entry.get("finding", "")))
                surfaces.extend(
                    str(item)
                    for item in entry.get("evidence", [])
                    if isinstance(item, str)
                )
        surfaces.extend(
            str(item)
            for item in candidate.get("minimumRemainingGates", [])
            if isinstance(item, str)
        )
    return surfaces


def _require_no_relative_candidate_conclusions(surfaces: list[str]) -> None:
    comparative_text = " ".join(surfaces)
    relative_patterns = (
        r"\b(?:this|that|the)\s+candidate\s+is\s+"
        r"(?:closer|nearer|better|more[- ]ready|preferred|"
        r"less[- ]blocked|superior|inferior|stronger|weaker)\b",
        r"\b(?:matt|superpowers)\s+is\s+"
        r"(?:closer|nearer|ahead\s+of|better|more[- ]ready|preferred|"
        r"less[- ]blocked(?:\s+than)?|superior(?:\s+to)?|"
        r"inferior(?:\s+to)?|stronger|weaker)\b",
        r"\b(?:closer|nearer|better|more[- ]ready|preferred|"
        r"less[- ]blocked)\s+(?:candidate|positioned|for|to)\b",
        r"\bfewer\s+(?:remaining\s+)?(?:gates|blockers|gaps)\b",
        r"\b(?:matt|superpowers)\s+(?:should|must)\s+"
        r"(?:go|run|dispatch|be admitted)\s+first\b",
        r"\b(?:stronger|weaker|preferred)\s+candidate\b",
    )
    _require(
        not any(
            re.search(pattern, comparative_text, flags=re.IGNORECASE)
            for pattern in relative_patterns
        ),
        "audit introduced a relative candidate conclusion",
    )


def validate_audit(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(document.get("schema") == 1, "audit schema must be 1")
    _require(
        document.get("status")
        == "static-gap-audit-complete-both-candidates-blocked-no-admission-decision",
        "audit status drifted or was promoted",
    )
    _require(
        document.get("parentProtocol") == PROTOCOL_PATH
        and document.get("sourceGovernancePreflight") == PREFLIGHT_PATH,
        "audit parent binding drifted",
    )
    protocol = _load(root, PROTOCOL_PATH)
    preflight = _load(root, PREFLIGHT_PATH)
    _require(
        document.get("sourceGovernancePreflightSha256")
        == hashlib.sha256((root / PREFLIGHT_PATH).read_bytes()).hexdigest()
        and document.get("candidateIdentityEnvelopeSha256")
        == _canonical_sha256(_candidate_identity_envelope(protocol)),
        "audit immutable input binding drifted",
    )
    protocol_candidates = {
        item["candidateId"]: item for item in protocol["candidates"]
    }
    preflight_candidates = {
        item["candidateId"]: item for item in preflight["candidateObservations"]
    }

    authority = document.get("authorityBoundary", {})
    _require(
        authority
        == {
            "readOnlyExactSourceReviewPerformed": True,
            "repositoryGovernanceReviewPerformed": True,
            "candidateSkillInvoked": False,
            "candidateTaskTurnStarted": False,
            "modelRequestSent": False,
            "projectionMaterialized": False,
            "candidateAdmissionMutationAuthorized": False,
            "portfolioMutationAuthorized": False,
            "installedSkillOrPluginMutationAuthorized": False,
            "globalConfigurationOrCcSwitchMutationAuthorized": False,
            "gitMutationAuthorized": False,
        },
        "audit authority boundary drifted",
    )
    _require(
        set(document.get("criteria", []))
        == {
            "exact source and license identity",
            "notice and attribution",
            "security and executable or permission surface",
            "portability and host or language assumptions",
            "overlap and conflict with hard standards and approved adapted TDD",
            "validation and bounded diagnostic compatibility",
            "identity-bound execution admission",
        },
        "audit criteria drifted",
    )

    candidates = {
        item.get("candidateId"): item
        for item in document.get("candidates", [])
        if isinstance(item, dict)
    }
    _require(
        set(candidates) == set(protocol_candidates) == set(preflight_candidates),
        "audit candidate set drifted",
    )
    expected_ids = {
        "tdd.matt.current": {
            "passes": {
                "matt-exact-source-and-mit",
                "matt-no-bundled-execution-surface",
                "matt-shared-hard-standard-alignment",
            },
            "partials": {
                "matt-attestation-not-bound",
                "matt-seam-confirmation-precontrolled",
                "matt-optional-and-excluded-dependencies",
            },
            "blockers": {
                "matt-current-is-not-approved-release",
                "matt-exact-revision-review-missing",
                "matt-notice-attribution-missing",
                "matt-refactor-stage-conflict-unadmitted",
                "matt-no-identity-bound-diagnostic-admission",
            },
        },
        "tdd.superpowers.6.2.0": {
            "passes": {
                "superpowers-local-package-and-mit",
                "superpowers-no-hook-or-external-service-requirement",
                "superpowers-shared-hard-standard-alignment",
            },
            "partials": {
                "superpowers-distribution-provenance-only",
                "superpowers-notice-attribution-missing",
                "superpowers-language-and-unprojected-reference",
                "superpowers-manifest-capability-surface",
            },
            "blockers": {
                "superpowers-no-repository-admission",
                "superpowers-python-command-conflict",
                "superpowers-delete-existing-code-conflict",
                "superpowers-other-tests-scope-conflict",
                "superpowers-exact-review-missing",
                "superpowers-no-identity-bound-diagnostic-admission",
            },
        },
    }
    finding_markers = {
        "matt-exact-source-and-mit": "pinned revision matched",
        "matt-no-bundled-execution-surface": "no bundled script",
        "matt-shared-hard-standard-alignment": "align with the frozen TDD hard gates",
        "matt-attestation-not-bound": "no signature or distribution attestation evidence",
        "matt-seam-confirmation-precontrolled": "pre-agrees one seam",
        "matt-optional-and-excluded-dependencies": "unprojected code-review Skill",
        "matt-current-is-not-approved-release": "six-file adapted payload",
        "matt-exact-revision-review-missing": "not current ed37663",
        "matt-notice-attribution-missing": "does not bind the current revision",
        "matt-refactor-stage-conflict-unadmitted": "moves refactor out of the loop",
        "matt-no-identity-bound-diagnostic-admission": "No admission record authorizes",
        "superpowers-local-package-and-mit": "matched the dated observation",
        "superpowers-no-hook-or-external-service-requirement": "empty hooks object",
        "superpowers-shared-hard-standard-alignment": "align with frozen TDD hard gates",
        "superpowers-distribution-provenance-only": "no immutable upstream commit",
        "superpowers-notice-attribution-missing": "No repository notice binds",
        "superpowers-language-and-unprojected-reference": "unprojected superpowers:writing-skills",
        "superpowers-manifest-capability-surface": "Interactive, Read, and Write",
        "superpowers-no-repository-admission": "No exact repository Skill",
        "superpowers-python-command-conflict": "immutable Python standard-library test commands",
        "superpowers-delete-existing-code-conflict": "must be deleted and started over",
        "superpowers-other-tests-scope-conflict": "expand writes beyond the three mutable files",
        "superpowers-exact-review-missing": "conflict-disposition review is absent",
        "superpowers-no-identity-bound-diagnostic-admission": "No admission record authorizes",
    }
    for candidate_id, candidate in candidates.items():
        protocol_candidate = protocol_candidates[candidate_id]
        _require(
            candidate.get("assessment")
            == "blocked-for-exact-candidate-execution-admission"
            and candidate.get("sourceRevisionOrVersion")
            == protocol_candidate.get("sourceRevisionOrVersion")
            and candidate.get("skillSha256")
            == protocol_candidate["files"][0]["sha256"]
            and preflight_candidates[candidate_id].get(
                "liveBytesMatchProtocol"
            )
            is True,
            f"audit candidate assessment drifted: {candidate_id}",
        )
        for evidence_class in ("passes", "partials", "blockers"):
            entries = candidate.get(evidence_class, [])
            _require(
                isinstance(entries, list)
                and {entry.get("id") for entry in entries}
                == expected_ids[candidate_id][evidence_class],
                f"audit {evidence_class} id set drifted: {candidate_id}",
            )
            for entry in entries:
                evidence = entry.get("evidence")
                marker = finding_markers[entry["id"]]
                _require(
                    isinstance(evidence, list)
                    and bool(evidence)
                    and all(
                        isinstance(item, str) and bool(item.strip())
                        for item in evidence
                    )
                    and marker in str(entry.get("finding", "")),
                    f"audit evidence item drifted: {entry['id']}",
                )
        _require(
            len(candidate.get("minimumRemainingGates", [])) >= 5,
            f"audit remaining gate set incomplete: {candidate_id}",
        )

    matt = candidates["tdd.matt.current"]
    matt_blockers = {item["id"] for item in matt["blockers"]}
    _require(
        matt.get("exactCandidateAdmissionPresent") is False
        and {
            "matt-current-is-not-approved-release",
            "matt-exact-revision-review-missing",
            "matt-notice-attribution-missing",
            "matt-refactor-stage-conflict-unadmitted",
            "matt-no-identity-bound-diagnostic-admission",
        }
        <= matt_blockers
        and preflight["governanceObservation"][
            "mattCurrentProjectionEqualsApprovedReleasePayload"
        ]
        is False,
        "audit Matt boundary drifted",
    )

    superpowers = candidates["tdd.superpowers.6.2.0"]
    superpowers_blockers = {item["id"] for item in superpowers["blockers"]}
    _require(
        superpowers.get("exactCandidateAdmissionPresent") is False
        and {
            "superpowers-no-repository-admission",
            "superpowers-python-command-conflict",
            "superpowers-delete-existing-code-conflict",
            "superpowers-other-tests-scope-conflict",
            "superpowers-exact-review-missing",
            "superpowers-no-identity-bound-diagnostic-admission",
        }
        <= superpowers_blockers,
        "audit Superpowers blocker set drifted",
    )
    governance = preflight["governanceObservation"]
    _require(
        governance["superpowers620RepositorySkillEntryPresent"] is False
        and governance["superpowers620RepositoryAdmissionPresent"] is False
        and governance["superpowers620RepositoryReleaseEntryPresent"] is False,
        "audit Superpowers repository boundary drifted",
    )

    decision = document.get("decision", {})
    _require(
        decision
        == {
            "staticGapAuditCompleted": True,
            "mattExactCandidateAdmitted": False,
            "superpowers620ExactCandidateAdmitted": False,
            "candidateAdmissionDecisionMade": False,
            "candidateTaskTurnStarted": False,
            "modelRequestSent": False,
            "candidateSkillInvoked": False,
            "liveTransitionAllowed": False,
            "runtimeDispatchGateAvailable": False,
            "nextBoundedAction": (
                "Use the candidate-specific remaining gates as inputs to a "
                "separate admission decision. Do not run either candidate, "
                "and do not treat this audit as admission, rejection, "
                "preference, or portfolio mutation."
            ),
        },
        "audit decision boundary drifted",
    )
    claims = document.get("claimBoundary", {})
    _require(
        len(claims) >= 15 and all(value is False for value in claims.values()),
        "audit claim boundary was promoted",
    )
    _require(
        document.get("documentation") == DOCUMENTATION_PATH
        and (root / DOCUMENTATION_PATH).is_file(),
        "audit documentation binding drifted",
    )
    documentation = " ".join(
        (root / DOCUMENTATION_PATH).read_text(encoding="utf-8").split()
    )
    for phrase in (
        "Neither candidate is admitted or rejected by this audit",
        "Matt's current record contains three static pass observations and five blocking gates",
        "not the approved six-file adapted release payload",
        "Superpowers has a concrete deletion conflict",
        "immutable Python test commands",
        "fix other failing tests",
        "No candidate Skill was invoked",
        "runner and append-only identity ledger",
    ):
        _require(
            phrase in documentation,
            f"audit documentation boundary missing: {phrase}",
        )
    _require_no_relative_candidate_conclusions(
        _relative_claim_surfaces(
            document,
            documentation=documentation,
        )
    )


def main() -> int:
    validate_audit(_load(ROOT, AUDIT_PATH))
    print("human-AI TDD exact-candidate admission gap audit: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
