from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.build_human_ai_collaboration_tdd_noncomparative_dispatch_bundle_v2 import (
    BundleContractError,
    CONTRACT_PATH,
    PARENT_PROTOCOL_PATH,
    ROOT,
    _validate_grant,
    _validate_ledger_authority,
    _validate_preflight,
    _validate_source_files,
    build_offline_dispatch_bundle,
    canonical_sha256,
    current_repository_decision,
    file_sha256,
    load_contract,
)
from scripts.validate_human_ai_collaboration_tdd_noncomparative_dispatch_successor_contract_v2 import (
    validate_contract,
)


class TddDispatchSuccessorContractV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract(ROOT)
        cls.now = datetime(
            2026,
            7,
            27,
            12,
            0,
            tzinfo=timezone(timedelta(hours=8)),
        )

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        temp_root = Path(self.temp.name)
        self.control_root = temp_root / "control"
        self.trial_root = temp_root / "trial"
        self.control_root.mkdir()
        self.trial_root.mkdir()
        self.candidate = copy.deepcopy(
            self.contract["candidateBindings"][0]
        )
        parent = json.loads(
            (ROOT / PARENT_PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        self.parent_candidate = next(
            item
            for item in parent["candidates"]
            if item["candidateId"] == self.candidate["candidateId"]
        )
        self.snapshot = self.make_snapshot()
        self.preflight = self.make_preflight()
        self.ledger = self.make_ledger_authority()
        self.grant = self.make_grant()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_snapshot(self) -> dict:
        return {
            "schema": 1,
            "id": "synthetic-snapshot-for-offline-test",
            "candidateId": self.candidate["candidateId"],
            "candidateIdentitySha256": self.candidate[
                "candidateIdentitySha256"
            ],
            "capturedAt": "2026-07-27T11:50:00+08:00",
            "controlRoot": str(self.control_root.resolve()),
            "trialRoot": str(self.trial_root.resolve()),
            "sourceFiles": [
                {
                    "path": item["path"],
                    "bytes": item["bytes"],
                    "sha256": item["sha256"],
                }
                for item in self.parent_candidate["files"]
            ],
        }

    def make_preflight(self) -> dict:
        return {
            "schema": 1,
            "id": "synthetic-fresh-preflight-for-offline-test",
            "candidateId": self.candidate["candidateId"],
            "candidateIdentitySha256": self.candidate[
                "candidateIdentitySha256"
            ],
            "observedAt": "2026-07-27T11:55:00+08:00",
            "sourceSnapshotManifestSha256": canonical_sha256(
                self.snapshot
            ),
            "sourceFiles": copy.deepcopy(self.snapshot["sourceFiles"]),
            "toolchain": {
                "codexExecutableSha256": "b" * 64,
                "codexCliVersion": "synthetic-test-only",
                "expectedAppServerInterface": "Codex app-server",
                "projectionBuilderSha256": "c" * 64,
                "normalizerSha256": "d" * 64,
                "diagnosticRunnerCoreSha256": "e" * 64,
            },
            "freshForDispatch": True,
            "freshRevalidationStillRequiredAtDispatch": False,
            "candidateMaterialized": False,
            "candidateInstructionExecuted": False,
            "appServerStarted": False,
            "threadStarted": False,
            "turnStarted": False,
            "modelRequestSent": False,
        }

    def make_ledger_authority(self) -> dict:
        ledger_contract = self.contract["ledgerAuthorityContract"]
        return {
            "schema": 1,
            "id": "synthetic-ledger-authority-for-offline-test",
            "experimentId": ledger_contract["experimentId"],
            "authorityId": "one-synthetic-shared-authority",
            "candidateIds": copy.deepcopy(
                ledger_contract["candidateIds"]
            ),
            "authorityScope": ledger_contract["authorityScope"],
            "issuedAt": "2026-07-27T11:49:00+08:00",
            "liveLedgerCreated": False,
            "reservationCreated": False,
        }

    def make_grant(self) -> dict:
        grant_contract = self.contract["separateAuthorityGrantContract"]
        return {
            "schema": 1,
            "id": "synthetic-independent-grant-for-offline-test",
            "kind": grant_contract["kind"],
            "authorityEvidenceLocator": (
                "user-confirmation:synthetic-offline-test-only"
            ),
            "issuedAt": "2026-07-27T11:57:00+08:00",
            "validFrom": "2026-07-27T11:58:00+08:00",
            "validUntil": "2026-07-27T12:10:00+08:00",
            "sourceRevalidatedAt": self.preflight["observedAt"],
            "candidateId": self.candidate["candidateId"],
            "candidateIdentitySha256": self.candidate[
                "candidateIdentitySha256"
            ],
            "successorContractSha256": file_sha256(
                ROOT / CONTRACT_PATH
            ),
            "parentProtocolSha256": file_sha256(
                ROOT / PARENT_PROTOCOL_PATH
            ),
            "freshPreflightSha256": canonical_sha256(self.preflight),
            "sourceSnapshotManifestSha256": canonical_sha256(
                self.snapshot
            ),
            "staticAdmissionDecisionSha256": self.candidate[
                "staticAdmissionSha256"
            ],
            "ledgerAuthoritySha256": canonical_sha256(self.ledger),
            "authorizedEffects": copy.deepcopy(
                grant_contract["authorizedEffects"]
            ),
            "hostBinding": copy.deepcopy(grant_contract["hostBinding"]),
            "maximumDispatches": 1,
            "replacementAllowed": False,
            "comparisonAllowed": False,
            "formalAcceptanceContribution": False,
            "portfolioMutationAllowed": False,
        }

    def make_repository_root_with_contract(
        self,
        mutate,
    ) -> Path:
        repository_root = Path(self.temp.name) / "repository"
        for binding in self.contract["sourceBindings"]:
            source = ROOT / binding["path"]
            target = repository_root / binding["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        documentation_path = Path(self.contract["documentation"])
        documentation_target = repository_root / documentation_path
        documentation_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / documentation_path, documentation_target)
        contract = copy.deepcopy(self.contract)
        mutate(contract)
        contract_target = repository_root / CONTRACT_PATH
        contract_target.parent.mkdir(parents=True, exist_ok=True)
        contract_target.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return repository_root

    def build(self, *, grant=...):
        if grant is ...:
            grant = self.grant
        return build_offline_dispatch_bundle(
            candidate_id=self.candidate["candidateId"],
            source_snapshot_manifest=copy.deepcopy(self.snapshot),
            fresh_preflight=copy.deepcopy(self.preflight),
            ledger_authority=copy.deepcopy(self.ledger),
            separate_authority_grant=copy.deepcopy(grant),
            now=self.now,
            root=ROOT,
        )

    def validate_preflight(self) -> tuple[datetime, str]:
        return _validate_preflight(
            self.preflight,
            self.contract,
            self.candidate,
            self.snapshot,
            canonical_sha256(self.snapshot),
            datetime.fromisoformat(self.snapshot["capturedAt"]),
            now=self.now,
        )

    def validate_grant(self) -> None:
        observed_at, preflight_sha256 = self.validate_preflight()
        _validate_grant(
            self.grant,
            self.contract,
            self.candidate,
            root=ROOT,
            snapshot_sha256=canonical_sha256(self.snapshot),
            preflight_sha256=preflight_sha256,
            ledger_authority_sha256=canonical_sha256(self.ledger),
            ledger_issued_at=datetime.fromisoformat(
                self.ledger["issuedAt"]
            ),
            captured_at=datetime.fromisoformat(
                self.snapshot["capturedAt"]
            ),
            observed_at=observed_at,
            now=self.now,
        )

    def test_repository_contract_is_valid(self) -> None:
        validate_contract(copy.deepcopy(self.contract), root=ROOT)

    def test_current_repository_decision_remains_no_go(self) -> None:
        decision = current_repository_decision(ROOT)
        self.assertEqual("NO-GO", decision["decision"])
        self.assertFalse(decision["currentLiveDispatchEligible"])
        self.assertFalse(decision["candidateMaterialized"])
        self.assertFalse(decision["appServerStarted"])
        self.assertFalse(decision["modelRequestSent"])
        self.assertIn(
            "Do not create a grant or live ledger",
            decision["nextBoundedAction"],
        )

    def test_missing_grant_returns_no_go_without_synthesizing_one(self) -> None:
        result = self.build(grant=None)
        self.assertEqual("NO-GO", result["decision"])
        self.assertEqual(
            "independent-separate-authority-grant-is-missing",
            result["reason"],
        )
        self.assertNotIn("authorityGrantSha256", result)
        self.assertFalse(result["liveDispatchEligible"])

    def test_metadata_only_manifest_cannot_substitute_for_candidate_bytes(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            BundleContractError,
            "escapes controlRoot or is missing",
        ):
            self.build()

    def test_no_go_bundle_is_deterministic_for_identical_inputs(self) -> None:
        self.assertEqual(self.build(grant=None), self.build(grant=None))

    def test_contract_source_hash_drift_fails_closed(self) -> None:
        document = copy.deepcopy(self.contract)
        document["sourceBindings"][0]["sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            validate_contract(document, root=ROOT)

    def test_duplicate_candidate_binding_fails_closed(self) -> None:
        document = copy.deepcopy(self.contract)
        document["candidateBindings"].append(
            copy.deepcopy(document["candidateBindings"][0])
        )
        with self.assertRaises(RuntimeError):
            validate_contract(document, root=ROOT)

    def test_singular_replacement_alias_cannot_enter_policy(self) -> None:
        document = copy.deepcopy(self.contract)
        document["normalizedDispatchPolicy"][
            "replacementDispatchAllowed"
        ] = False
        with self.assertRaises(RuntimeError):
            validate_contract(document, root=ROOT)

    def test_formal_policy_shell_cannot_be_promoted(self) -> None:
        document = copy.deepcopy(self.contract)
        document["runnerPolicyBoundary"][
            "formalRunnerPolicyShellExcluded"
        ] = False
        with self.assertRaises(RuntimeError):
            validate_contract(document, root=ROOT)

    def test_repository_contract_rejects_live_authorization_envelope_promotion(
        self,
    ) -> None:
        def mutate(contract: dict) -> None:
            envelope = contract["authorizationEnvelopeContract"]
            envelope["offlineBundleItselfAuthorizesLiveEffects"] = True
            envelope["mustBindFreshPreflight"] = False

        repository_root = self.make_repository_root_with_contract(mutate)
        with self.assertRaisesRegex(
            RuntimeError,
            "Authorization-envelope contract drifted",
        ):
            validate_contract(
                load_contract(repository_root),
                root=repository_root,
            )

    def test_repository_contract_rejects_runner_shadow_acceptance_field(
        self,
    ) -> None:
        def mutate(contract: dict) -> None:
            contract["runnerPolicyBoundary"][
                "successorDiagnosticCountsTowardWeakAcceptance"
            ] = True

        repository_root = self.make_repository_root_with_contract(mutate)
        with self.assertRaisesRegex(
            RuntimeError,
            "Runner policy boundary drifted",
        ):
            validate_contract(
                load_contract(repository_root),
                root=repository_root,
            )

    def test_repository_contract_rejects_state_shadow_formal_acceptance(
        self,
    ) -> None:
        def mutate(contract: dict) -> None:
            contract["stateMachine"]["statesInOrder"].insert(
                -1,
                "formal-acceptance-contributed",
            )

        repository_root = self.make_repository_root_with_contract(mutate)
        with self.assertRaisesRegex(
            RuntimeError,
            "State machine drifted",
        ):
            validate_contract(
                load_contract(repository_root),
                root=repository_root,
            )

    def test_repository_contract_rejects_conflicting_next_action(
        self,
    ) -> None:
        def mutate(contract: dict) -> None:
            contract["decision"]["nextBoundedAction"] = (
                "Start app-server and send a live model request now."
            )

        repository_root = self.make_repository_root_with_contract(mutate)
        with self.assertRaisesRegex(
            RuntimeError,
            "Decision boundary drifted",
        ):
            current_repository_decision(repository_root)

    def test_control_and_trial_roots_must_be_disjoint(self) -> None:
        self.snapshot["trialRoot"] = self.snapshot["controlRoot"]
        self.preflight = self.make_preflight()
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "must be disjoint",
        ):
            self.build()

    def test_snapshot_parent_traversal_fails_closed(self) -> None:
        self.snapshot["sourceFiles"][0]["path"] = "../private.txt"
        self.preflight = self.make_preflight()
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "normalized POSIX relative path",
        ):
            self.build()

    def test_stale_preflight_fails_parent_recomputation(self) -> None:
        self.snapshot["capturedAt"] = "2026-07-27T11:00:00+08:00"
        self.preflight = self.make_preflight()
        self.preflight["observedAt"] = "2026-07-27T11:10:00+08:00"
        with self.assertRaisesRegex(
            BundleContractError,
            "exceeds the maximum age",
        ):
            self.validate_preflight()

    def test_snapshot_to_preflight_interval_is_bounded(self) -> None:
        self.snapshot["capturedAt"] = "2026-07-27T11:00:00+08:00"
        self.preflight = self.make_preflight()
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "maximum preflight interval",
        ):
            self.validate_preflight()

    def test_declared_freshness_cannot_be_false(self) -> None:
        self.preflight["freshForDispatch"] = False
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "declared freshness drifted",
        ):
            self.validate_preflight()

    def test_preflight_source_file_mismatch_fails_closed(self) -> None:
        self.preflight["sourceFiles"][0]["sha256"] = "f" * 64
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "source-file binding drifted",
        ):
            self.validate_preflight()

    def test_preflight_execution_promotion_fails_closed(self) -> None:
        self.preflight["candidateMaterialized"] = True
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "unexpectedly records execution",
        ):
            self.validate_preflight()

    def test_builder_labeled_grant_is_rejected(self) -> None:
        self.grant["authorityEvidenceLocator"] = "builder:self-issued"
        with self.assertRaisesRegex(
            BundleContractError,
            "not independently bound",
        ):
            self.validate_grant()

    def test_grant_scope_expansion_fails_closed(self) -> None:
        self.grant["authorizedEffects"].append("network-source-read")
        with self.assertRaisesRegex(
            BundleContractError,
            "scope drifted",
        ):
            self.validate_grant()

    def test_provider_fallback_promotion_fails_closed(self) -> None:
        self.grant["hostBinding"]["providerFallbackAllowed"] = True
        with self.assertRaisesRegex(
            BundleContractError,
            "scope drifted",
        ):
            self.validate_grant()

    def test_formal_acceptance_promotion_fails_closed(self) -> None:
        self.grant["formalAcceptanceContribution"] = True
        with self.assertRaisesRegex(
            BundleContractError,
            "scope drifted",
        ):
            self.validate_grant()

    def test_grant_contract_digest_mismatch_fails_closed(self) -> None:
        self.grant["successorContractSha256"] = "0" * 64
        with self.assertRaisesRegex(
            BundleContractError,
            "digest binding drifted",
        ):
            self.validate_grant()

    def test_grant_ttl_over_maximum_fails_closed(self) -> None:
        self.grant["validUntil"] = "2026-07-27T12:30:01+08:00"
        with self.assertRaisesRegex(
            BundleContractError,
            "TTL exceeds the maximum",
        ):
            self.validate_grant()

    def test_ledger_authority_must_precede_snapshot_capture(self) -> None:
        self.ledger["issuedAt"] = "2026-07-27T11:59:00+08:00"
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "time binding drifted",
        ):
            self.validate_grant()

    def test_ledger_authority_age_is_bounded(self) -> None:
        self.ledger["issuedAt"] = "2020-07-27T11:49:00+08:00"
        with self.assertRaisesRegex(
            BundleContractError,
            "maximum age",
        ):
            _validate_ledger_authority(
                self.ledger,
                self.contract,
                now=self.now,
            )

    def test_candidate_identity_mismatch_fails_closed(self) -> None:
        self.grant["candidateIdentitySha256"] = "0" * 64
        with self.assertRaisesRegex(
            BundleContractError,
            "candidate binding drifted",
        ):
            self.validate_grant()

    def test_second_ledger_authority_shape_is_not_accepted(self) -> None:
        self.ledger["candidateIds"] = [
            self.candidate["candidateId"],
        ]
        self.grant = self.make_grant()
        with self.assertRaisesRegex(
            BundleContractError,
            "Ledger authority boundary drifted",
        ):
            _validate_ledger_authority(
                self.ledger,
                self.contract,
                now=self.now,
            )

    def test_source_file_verifier_reads_exact_bytes(self) -> None:
        path = self.control_root / "synthetic.txt"
        path.write_bytes(b"exact synthetic bytes")
        expected = [
            {
                "path": "synthetic.txt",
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        ]
        self.assertEqual(
            expected,
            _validate_source_files(
                copy.deepcopy(expected),
                label="Synthetic source files",
                control_root=self.control_root.resolve(),
                expected_candidate_files=copy.deepcopy(expected),
            ),
        )

    def test_source_file_verifier_rejects_byte_drift(self) -> None:
        path = self.control_root / "synthetic.txt"
        path.write_bytes(b"actual bytes")
        expected = [
            {
                "path": "synthetic.txt",
                "bytes": 999,
                "sha256": "a" * 64,
            }
        ]
        with self.assertRaisesRegex(
            BundleContractError,
            "bytes do not match",
        ):
            _validate_source_files(
                copy.deepcopy(expected),
                label="Synthetic source files",
                control_root=self.control_root.resolve(),
                expected_candidate_files=copy.deepcopy(expected),
            )

    def test_claim_boundary_cannot_advance_weak_acceptance(self) -> None:
        document = copy.deepcopy(self.contract)
        document["claimBoundary"]["weakAgentAcceptanceAdvanced"] = True
        with self.assertRaises(RuntimeError):
            validate_contract(document, root=ROOT)

    def test_document_authorization_append_fails_closed(self) -> None:
        repository_root = self.make_repository_root_with_contract(
            lambda document: None
        )
        contract = load_contract(repository_root)
        documentation_path = repository_root / contract["documentation"]
        with documentation_path.open("a", encoding="utf-8", newline="") as stream:
            stream.write(
                "\nTHIS DOCUMENT AUTHORIZES LIVE MODEL DISPATCH AND FORMAL "
                "ACCEPTANCE.\n"
            )
        with self.assertRaisesRegex(
            RuntimeError,
            "Documentation (bytes|hash) drifted",
        ):
            validate_contract(contract, root=repository_root)

    def test_toolchain_authenticity_remains_unproved(self) -> None:
        self.assertFalse(
            self.contract["freshPreflightContract"][
                "toolchainAuthenticityVerifiedByBuilder"
            ]
        )
        self.assertFalse(
            self.contract["claimBoundary"][
                "realToolchainFreshnessProved"
            ]
        )


if __name__ == "__main__":
    unittest.main()
