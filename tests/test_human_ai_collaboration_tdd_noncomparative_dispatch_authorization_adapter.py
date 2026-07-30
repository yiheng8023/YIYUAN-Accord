from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.human_ai_collaboration_tdd_noncomparative_dispatch_authorization_adapter import (
    DispatchAuthorizationError,
    build_dispatch_reservation_input,
)
from scripts.human_ai_collaboration_tdd_noncomparative_dispatch_identity_ledger import (
    DispatchIdentityLedger,
)


ROOT = Path(__file__).resolve().parent.parent
CANDIDATE_ID = "tdd.matt.current"
OBSERVED_AT = "2026-07-26T23:30:00+08:00"


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_identity(candidate: dict) -> dict:
    return {
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


class Bundle:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.protocol_path = root / "protocol.json"
        self.preflight_path = root / "preflight.json"
        self.audit_path = root / "audit.json"
        self.admission_path = root / "admission.json"
        self.ledger_authority_path = root / "ledger-authority.json"
        self.ledger_path = root / "state" / "dispatch-ledger.jsonl"
        self.ledger_authority = {
            "schema": 1,
            "kind": "single-dispatch-ledger-authority",
            "authorityId": "tdd-noncomparative-ledger-authority-01",
            "ledgerRelativePath": "state/dispatch-ledger.jsonl",
            "replacementLedgerAllowed": False,
            "automaticReleaseAllowed": False,
            "automaticRetryAllowed": False,
            "manualReconciliationRequired": True,
        }
        self.candidate = {
            "candidateId": CANDIDATE_ID,
            "sourceRevisionOrVersion": "revision-01",
            "license": {"sha256": "1" * 64},
            "files": [
                {"path": ".agents/skills/tdd/SKILL.md", "sha256": "2" * 64}
            ],
            "projectionTreeSha256": "3" * 64,
        }
        self.protocol = {
            "schema": 1,
            "candidates": [self.candidate],
            "diagnosticDesign": {
                "maximumDispatchesPerCandidate": 1,
                "replacementDispatchAllowed": False,
                "pairwiseComparisonAllowed": False,
            },
            "decision": {
                "protocolPreregistered": True,
                "liveDiagnosticStarted": False,
                "anyExactCandidateExecutionEligibleNow": True,
                "governanceAdmissionStillRequired": False,
                "candidateAdmissionDecisionMade": True,
                "runtimeDispatchCapEnforced": False,
            },
        }
        self.preflight = {
            "schema": 1,
            "observedAt": "2026-07-26T23:25:00+08:00",
            "candidateObservations": [
                {
                    "candidateId": CANDIDATE_ID,
                    "liveBytesMatchProtocol": True,
                }
            ],
            "rawEvidenceBoundary": {
                "freshForDispatch": True,
                "freshRevalidationStillRequiredAtDispatch": False,
            },
            "decision": {
                "currentToolchainIdentityRevalidated": True,
                "freshForDispatch": True,
                "liveDiagnosticStarted": False,
                "modelRequestSent": False,
                "candidateInstructionExecutionPerformed": False,
            },
        }
        self.audit = {
            "schema": 1,
            "candidateIdentityEnvelopeSha256": canonical_sha256(
                [candidate_identity(self.candidate)]
            ),
            "candidates": [
                {
                    "candidateId": CANDIDATE_ID,
                    "sourceRevisionOrVersion": "revision-01",
                    "skillSha256": "2" * 64,
                }
            ],
            "decision": {
                "staticGapAuditCompleted": True,
                "candidateTaskTurnStarted": False,
                "modelRequestSent": False,
                "candidateSkillInvoked": False,
            },
        }
        self.write()

    def write(self) -> None:
        self.ledger_authority_path.write_text(
            json.dumps(self.ledger_authority, indent=2) + "\n",
            encoding="utf-8",
        )
        self.protocol["dispatchLedgerAuthority"] = {
            "document": self.ledger_authority_path.name,
            "sha256": file_sha256(self.ledger_authority_path),
        }
        self.protocol_path.write_text(
            json.dumps(self.protocol, indent=2) + "\n",
            encoding="utf-8",
        )
        self.preflight_path.write_text(
            json.dumps(self.preflight, indent=2) + "\n",
            encoding="utf-8",
        )
        self.audit["sourceGovernancePreflightSha256"] = file_sha256(
            self.preflight_path
        )
        self.audit_path.write_text(
            json.dumps(self.audit, indent=2) + "\n",
            encoding="utf-8",
        )
        self.admission = {
            "schema": 1,
            "kind": "diagnostic-only-exact-candidate-execution-admission",
            "admissionId": "admission-01",
            "candidateId": CANDIDATE_ID,
            "candidateIdentitySha256": canonical_sha256(
                candidate_identity(self.candidate)
            ),
            "protocolFileSha256": file_sha256(self.protocol_path),
            "sourceGovernancePreflightFileSha256": file_sha256(
                self.preflight_path
            ),
            "staticGapAuditFileSha256": file_sha256(self.audit_path),
            "sourceRevalidatedAt": self.preflight["observedAt"],
            "validFrom": "2026-07-26T23:20:00+08:00",
            "validUntil": "2026-07-26T23:40:00+08:00",
            "disposition": "admit-one-noncomparative-diagnostic",
            "exactCandidateExecutionAdmitted": True,
            "maximumDispatches": 1,
            "replacementAllowed": False,
            "comparisonAllowed": False,
            "portfolioMutationAllowed": False,
        }
        self.admission_path.write_text(
            json.dumps(self.admission, indent=2) + "\n",
            encoding="utf-8",
        )


class HumanAiCollaborationTddNoncomparativeDispatchAuthorizationAdapterTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.bundle = Bundle(Path(self.temporary.name))

    def build(self, observed_at: str = OBSERVED_AT) -> dict:
        return build_dispatch_reservation_input(
            protocol_path=self.bundle.protocol_path,
            source_governance_preflight_path=self.bundle.preflight_path,
            static_gap_audit_path=self.bundle.audit_path,
            diagnostic_admission_path=self.bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            observed_at=observed_at,
        )

    def test_valid_bound_bundle_produces_digest_bound_input(self) -> None:
        result = self.build()
        self.assertEqual(CANDIDATE_ID, result["candidateId"])
        self.assertTrue(result["exactCandidateExecutionAdmitted"])
        self.assertTrue(result["sourceAndToolchainReverifiedAtDispatch"])
        self.assertEqual(
            file_sha256(self.bundle.admission_path),
            result["diagnosticAdmissionFileSha256"],
        )
        self.assertEqual(64, len(result["authorizationSha256"]))

    def test_current_repository_documents_remain_blocked(self) -> None:
        protocol_path = ROOT / (
            "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
            "diagnostic-protocol-2026-07-26.json"
        )
        preflight_path = ROOT / (
            "registry/human-ai-collaboration-tdd-noncomparative-treatment-"
            "diagnostic-source-governance-preflight-2026-07-26.json"
        )
        audit_path = ROOT / (
            "registry/human-ai-collaboration-tdd-exact-candidate-admission-"
            "gap-audit-2026-07-26.json"
        )
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        candidate = next(
            item
            for item in protocol["candidates"]
            if item["candidateId"] == CANDIDATE_ID
        )
        admission = self.bundle.admission
        admission.update(
            {
                "candidateIdentitySha256": canonical_sha256(
                    candidate_identity(candidate)
                ),
                "protocolFileSha256": file_sha256(protocol_path),
                "sourceGovernancePreflightFileSha256": file_sha256(
                    preflight_path
                ),
                "staticGapAuditFileSha256": file_sha256(audit_path),
            }
        )
        self.bundle.admission_path.write_text(
            json.dumps(admission, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            DispatchAuthorizationError,
            "protocol execution eligibility",
        ):
            build_dispatch_reservation_input(
                protocol_path=protocol_path,
                source_governance_preflight_path=preflight_path,
                static_gap_audit_path=audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                observed_at="2026-07-26T23:30:00+08:00",
            )

    def test_rejects_stale_preflight(self) -> None:
        self.bundle.preflight["decision"]["freshForDispatch"] = False
        self.bundle.write()
        with self.assertRaisesRegex(
            DispatchAuthorizationError,
            "source freshness",
        ):
            self.build()

    def test_rejects_admission_digest_mismatch(self) -> None:
        self.bundle.admission["protocolFileSha256"] = "0" * 64
        self.bundle.admission_path.write_text(
            json.dumps(self.bundle.admission, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            DispatchAuthorizationError,
            "admission digest binding",
        ):
            self.build()

    def test_rejects_expired_admission(self) -> None:
        with self.assertRaisesRegex(
            DispatchAuthorizationError,
            "validity window",
        ):
            self.build("2026-07-27T00:00:00+08:00")

    def test_rejects_candidate_mismatch(self) -> None:
        with self.assertRaisesRegex(
            DispatchAuthorizationError,
            "candidate",
        ):
            build_dispatch_reservation_input(
                protocol_path=self.bundle.protocol_path,
                source_governance_preflight_path=self.bundle.preflight_path,
                static_gap_audit_path=self.bundle.audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id="tdd.superpowers.6.2.0",
                observed_at=OBSERVED_AT,
            )

    def test_rejects_comparison_authority(self) -> None:
        self.bundle.admission["comparisonAllowed"] = True
        self.bundle.admission_path.write_text(
            json.dumps(self.bundle.admission, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            DispatchAuthorizationError,
            "admission boundary",
        ):
            self.build()

    def test_ledger_reserves_only_from_bound_documents(self) -> None:
        ledger, event = DispatchIdentityLedger.reserve_from_repository_documents(
            protocol_path=self.bundle.protocol_path,
            source_governance_preflight_path=self.bundle.preflight_path,
            static_gap_audit_path=self.bundle.audit_path,
            diagnostic_admission_path=self.bundle.admission_path,
            candidate_id=CANDIDATE_ID,
            reservation_id="reservation-01",
            observed_at=OBSERVED_AT,
        )
        self.assertEqual(
            file_sha256(self.bundle.admission_path),
            event["diagnosticAdmissionFileSha256"],
        )
        with self.assertRaisesRegex(RuntimeError, "candidate dispatch cap"):
            DispatchIdentityLedger.reserve_from_repository_documents(
                protocol_path=self.bundle.protocol_path,
                source_governance_preflight_path=self.bundle.preflight_path,
                static_gap_audit_path=self.bundle.audit_path,
                diagnostic_admission_path=self.bundle.admission_path,
                candidate_id=CANDIDATE_ID,
                reservation_id="reservation-02",
                observed_at=OBSERVED_AT,
            )


if __name__ == "__main__":
    unittest.main()
