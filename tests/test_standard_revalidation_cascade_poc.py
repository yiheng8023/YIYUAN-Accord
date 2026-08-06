from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.plan_standard_revalidation_cascade import (
    POC_PATH,
    plan_cascade,
    validate_poc_record,
    validate_repository_poc,
)


ROOT = Path(__file__).resolve().parent.parent


def synthetic_cascade_request() -> dict:
    return {
        "id": "synthetic-standard-revalidation-cascade",
        "declaredSynthetic": True,
        "realStandardRepresented": False,
        "standard": {
            "id": "synthetic-standard",
            "version": "1.0.0-synthetic",
            "status": "accepted",
            "ownerAdmissionReceiptId": "synthetic-owner-admission",
            "restartBaselineId": "synthetic-restart-baseline-v1",
            "evidenceIds": ["synthetic-standard-evidence"],
        },
        "graph": {
            "nodes": [
                {
                    "id": "source-a",
                    "kind": "governed-source",
                    "authorityOwnerId": "owner-source-a",
                    "repositoryId": "synthetic-repo-a",
                    "currentRevision": "source-a-r1",
                    "targetRevision": "source-a-r2",
                    "historicalDebtIds": ["debt-source-a"],
                    "migrationFixtureId": "fixture-migrate-source-a",
                    "verificationFixtureId": "fixture-verify-source-a",
                    "rollbackPlanId": "rollback-source-a",
                },
                {
                    "id": "projection-a",
                    "kind": "projection",
                    "authorityOwnerId": "owner-projection-a",
                    "repositoryId": "synthetic-repo-a",
                    "currentRevision": "projection-a-r1",
                    "targetRevision": "projection-a-r2",
                    "historicalDebtIds": ["debt-projection-a"],
                    "migrationFixtureId": "fixture-migrate-projection-a",
                    "verificationFixtureId": "fixture-verify-projection-a",
                    "rollbackPlanId": "rollback-projection-a",
                },
                {
                    "id": "consumer-a",
                    "kind": "consumer",
                    "authorityOwnerId": "owner-consumer-a",
                    "repositoryId": "synthetic-repo-b",
                    "currentRevision": "consumer-a-r1",
                    "targetRevision": "consumer-a-r2",
                    "historicalDebtIds": ["debt-consumer-a"],
                    "migrationFixtureId": "fixture-migrate-consumer-a",
                    "verificationFixtureId": "fixture-verify-consumer-a",
                    "rollbackPlanId": "rollback-consumer-a",
                },
                {
                    "id": "unrelated",
                    "kind": "governed-source",
                    "authorityOwnerId": "owner-unrelated",
                    "repositoryId": "synthetic-repo-c",
                    "currentRevision": "unrelated-r1",
                },
            ],
            "edges": [
                {"from": "source-a", "to": "projection-a", "kind": "feeds"},
                {"from": "projection-a", "to": "consumer-a", "kind": "feeds"},
            ],
        },
        "directlyAffectedNodeIds": ["source-a"],
        "planning": {
            "maxBatchSize": 2,
            "rewriteAll": False,
            "crossRepositoryMutationAuthorized": False,
        },
    }


class StandardRevalidationCascadePocTests(unittest.TestCase):
    def test_repository_poc_contract_is_valid(self) -> None:
        record = validate_repository_poc()

        self.assertEqual("standard-revalidation-cascade-poc-v1", record["id"])
        self.assertEqual("verified-synthetic-poc-mechanism-only", record["status"])
        self.assertEqual(
            "registry/standard-revalidation-cascade-poc-2026-08-07.json",
            str(POC_PATH).replace("\\", "/"),
        )

    def test_poc_declares_the_complete_failure_injection_ledger(self) -> None:
        record = json.loads((ROOT / POC_PATH).read_text(encoding="utf-8"))

        self.assertEqual(
            [
                "synthetic-boundary",
                "standard-shape",
                "graph-shape",
                "planning-shape",
                "edges-shape",
                "direct-node-shape",
                "standard-status",
                "standard-receipt",
                "standard-evidence",
                "direct-node",
                "rewrite-all",
                "cross-repository",
                "batch-bound",
                "edge-target",
                "edge-kind",
                "node-kind",
                "authority",
                "identity",
                "migration",
                "duplicate-node",
                "cycle",
            ],
            record["failureInjectionCaseIds"],
        )

    def test_poc_validator_rejects_mutation_ledger_drift(self) -> None:
        record = json.loads((ROOT / POC_PATH).read_text(encoding="utf-8"))
        record["failureInjectionCaseIds"].pop()

        with self.assertRaisesRegex(RuntimeError, "mutation ledger"):
            validate_poc_record(record, root=ROOT)

    def test_acceptance_map_adds_poc_evidence_but_keeps_criterion_partial(self) -> None:
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criteria = {row["id"]: row for row in acceptance["acceptanceCriteria"]}
        evidence = {row["id"]: row for row in acceptance["evidence"]}
        evidence_id = "evidence.standard-revalidation-cascade-poc-2026-08-07"

        criterion = criteria["acceptance.standard-revalidation-cascade"]
        self.assertEqual("partial", criterion["assessment"])
        self.assertIn(evidence_id, criterion["evidenceIds"])
        self.assertEqual(
            "registry/standard-revalidation-cascade-poc-2026-08-07.json",
            evidence[evidence_id]["path"],
        )
        self.assertEqual(
            ["acceptance.standard-revalidation-cascade"],
            evidence[evidence_id]["supports"],
        )

    def test_poc_validator_rejects_criterion_promotion(self) -> None:
        record = json.loads((ROOT / POC_PATH).read_text(encoding="utf-8"))
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(encoding="utf-8")
        )
        criterion = next(
            row
            for row in acceptance["acceptanceCriteria"]
            if row["id"] == "acceptance.standard-revalidation-cascade"
        )
        criterion["assessment"] = "verified"

        with self.assertRaisesRegex(RuntimeError, "acceptance boundary"):
            validate_poc_record(record, acceptance=acceptance, root=ROOT)

    def test_poc_validator_rejects_source_open_boundary_promotion(self) -> None:
        record = json.loads((ROOT / POC_PATH).read_text(encoding="utf-8"))
        layered = json.loads(
            (
                ROOT
                / "registry/layered-reliability-projection-reconciliation-2026-07-18.json"
            ).read_text(encoding="utf-8")
        )
        item = next(
            row
            for row in layered["keptOpen"]
            if row["acceptanceId"] == "acceptance.standard-revalidation-cascade"
        )
        item["assessment"] = "verified"

        with self.assertRaisesRegex(RuntimeError, "source boundary"):
            validate_poc_record(record, layered=layered, root=ROOT)

    def test_planner_scopes_the_cascade_and_excludes_unrelated_nodes(self) -> None:
        result = plan_cascade(synthetic_cascade_request())

        self.assertEqual("plan-ready", result["decision"])
        self.assertEqual(
            ["source-a", "projection-a", "consumer-a"],
            result["affectedNodeIds"],
        )
        self.assertEqual(["unrelated"], result["unaffectedNodeIds"])
        self.assertEqual(
            [
                {"index": 1, "nodeIds": ["source-a"]},
                {"index": 2, "nodeIds": ["projection-a"]},
                {"index": 3, "nodeIds": ["consumer-a"]},
            ],
            result["batches"],
        )
        self.assertEqual(
            "synthetic-restart-baseline-v1", result["restartBaselineId"]
        )
        self.assertEqual(
            "after-all-affected-verification",
            result["oldProjectionDeprecation"],
        )
        self.assertFalse(result["executionAuthorized"])
        self.assertEqual("synthetic-planner-mechanism-only", result["claimBoundary"])

    def test_dependency_cycle_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        request["graph"]["edges"].append(
            {"from": "consumer-a", "to": "source-a", "kind": "feeds"}
        )

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("affected-graph-cycle", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_unknown_edge_kind_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        request["graph"]["edges"][0]["kind"] = "decorates"

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("graph-edge-kind-invalid", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_unknown_affected_node_kind_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        request["graph"]["nodes"][0]["kind"] = "mystery"

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("affected-node-kind-invalid", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_duplicate_node_identity_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        duplicate = dict(request["graph"]["nodes"][0])
        duplicate["currentRevision"] = "silently-overwriting-revision"
        request["graph"]["nodes"].append(duplicate)

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("graph-node-identity-invalid", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_malformed_container_shapes_fail_closed(self) -> None:
        cases = (
            ("standard", None, "accepted-standard-boundary-missing"),
            ("graph", None, "graph-node-identity-invalid"),
            ("planning", None, "batch-bound-invalid"),
        )
        for field, replacement, blocker in cases:
            with self.subTest(field=field):
                request = synthetic_cascade_request()
                request[field] = replacement

                result = plan_cascade(request)

                self.assertEqual("blocked", result["decision"])
                self.assertIn(blocker, result["blockers"])
                self.assertFalse(result["executionAuthorized"])

    def test_malformed_edges_container_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        request["graph"]["edges"] = {"not": "a-list"}

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("graph-edge-invalid", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_non_string_direct_node_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        request["directlyAffectedNodeIds"] = [{"not": "an-id"}]

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("directly-affected-node-invalid", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_affected_node_without_authority_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        request["graph"]["nodes"][1]["authorityOwnerId"] = ""

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("affected-node-authority-missing", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_node_waits_for_all_affected_predecessors(self) -> None:
        request = synthetic_cascade_request()
        request["graph"]["edges"].append(
            {"from": "source-a", "to": "consumer-a", "kind": "feeds"}
        )

        result = plan_cascade(request)

        self.assertEqual("plan-ready", result["decision"])
        self.assertEqual(
            [
                {"index": 1, "nodeIds": ["source-a"]},
                {"index": 2, "nodeIds": ["projection-a"]},
                {"index": 3, "nodeIds": ["consumer-a"]},
            ],
            result["batches"],
        )

    def test_plan_preserves_migration_verification_and_rollback(self) -> None:
        result = plan_cascade(synthetic_cascade_request())

        self.assertEqual(
            [
                {
                    "nodeId": "source-a",
                    "fromRevision": "source-a-r1",
                    "targetRevision": "source-a-r2",
                    "historicalDebtIds": ["debt-source-a"],
                    "migrationFixtureId": "fixture-migrate-source-a",
                    "verificationFixtureId": "fixture-verify-source-a",
                    "rollbackPlanId": "rollback-source-a",
                },
                {
                    "nodeId": "projection-a",
                    "fromRevision": "projection-a-r1",
                    "targetRevision": "projection-a-r2",
                    "historicalDebtIds": ["debt-projection-a"],
                    "migrationFixtureId": "fixture-migrate-projection-a",
                    "verificationFixtureId": "fixture-verify-projection-a",
                    "rollbackPlanId": "rollback-projection-a",
                },
                {
                    "nodeId": "consumer-a",
                    "fromRevision": "consumer-a-r1",
                    "targetRevision": "consumer-a-r2",
                    "historicalDebtIds": ["debt-consumer-a"],
                    "migrationFixtureId": "fixture-migrate-consumer-a",
                    "verificationFixtureId": "fixture-verify-consumer-a",
                    "rollbackPlanId": "rollback-consumer-a",
                },
            ],
            result["nodePlans"],
        )

    def test_accepted_standard_without_evidence_fails_closed(self) -> None:
        request = synthetic_cascade_request()
        request["standard"]["evidenceIds"] = []

        result = plan_cascade(request)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("accepted-standard-boundary-missing", result["blockers"])
        self.assertFalse(result["executionAuthorized"])


if __name__ == "__main__":
    unittest.main()
