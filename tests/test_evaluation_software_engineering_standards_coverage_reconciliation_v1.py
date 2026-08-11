from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from scripts.validate_evaluation_software_engineering_standards_coverage_reconciliation_v1 import (
    RECORD_PATH,
    validate_reconciliation,
)


ROOT = Path(__file__).resolve().parent.parent


def load(path: Path) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected object at {path}")
    return value


class EvaluationSoftwareEngineeringStandardsCoverageReconciliationV1Tests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load(RECORD_PATH)

    def assert_rejected(self, document: dict[str, object], message: str) -> None:
        with self.assertRaisesRegex(RuntimeError, message):
            validate_reconciliation(document, root=ROOT)

    def test_repository_record_reconciles_exact_current_coordinate_sets(self) -> None:
        validate_reconciliation(self.document, root=ROOT)
        inventory = self.document["inputInventory"]
        self.assertEqual(15, inventory["partialCriterionCount"])
        self.assertEqual(6, inventory["clusterCount"])
        self.assertEqual(14, inventory["lifecycleSliceCount"])
        self.assertEqual(12, inventory["evaluationDimensionCount"])
        self.assertEqual(13, inventory["scenarioCount"])
        self.assertEqual(15, len(self.document["criterionReconciliations"]))
        self.assertEqual(
            ["N", "O", "E", "C", "H", "R"],
            [row["id"] for row in self.document["routeClasses"]],
        )

    def test_repository_record_has_precise_role_bindings_without_coordinate_drift(
        self,
    ) -> None:
        generic_ids = {"evidence.program-plan", "evidence.readme"}
        projection = []
        for row in self.document["criterionReconciliations"]:
            roles = row["evidenceRoleBindings"]
            self.assertEqual(
                {
                    "coordinateBasisIds",
                    "boundaryBasisIds",
                    "nextEvidenceBasisIds",
                },
                set(roles),
            )
            self.assertTrue(set(roles["coordinateBasisIds"]) - generic_ids)
            projection.append(
                {
                    key: value
                    for key, value in row.items()
                    if key not in {"evidenceIds", "evidenceRoleBindings"}
                }
            )

        encoded = json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(
            "5f9ccfaf9572ae99b2f9f63ffb4394be8c9b148309d5b772f40f18eba905f9b6",
            hashlib.sha256(encoded).hexdigest(),
        )

    def test_missing_evidence_role_bindings_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0].pop("evidenceRoleBindings")
        self.assert_rejected(document, "evidence role binding drifted")

    def test_unknown_evidence_role_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "inventedBasisIds"
        ] = ["evidence.human-ai-collaboration-coverage-rebaseline"]
        self.assert_rejected(document, "evidence role binding drifted")

    def test_empty_evidence_role_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "boundaryBasisIds"
        ] = []
        self.assert_rejected(document, "evidence role binding drifted")

    def test_duplicate_role_evidence_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        role = document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "coordinateBasisIds"
        ]
        role.append(role[0])
        self.assert_rejected(document, "evidence role binding drifted")

    def test_cross_criterion_role_evidence_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "coordinateBasisIds"
        ] = ["evidence.round03-native-runtime-baseline"]
        self.assert_rejected(document, "unknown evidence identity")

    def test_role_evidence_authority_order_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        role = document["criterionReconciliations"][0]["evidenceRoleBindings"][
            "coordinateBasisIds"
        ]
        role.reverse()
        self.assert_rejected(document, "evidence role order drifted")

    def test_generic_only_coordinate_basis_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        row = next(
            row
            for row in document["criterionReconciliations"]
            if row["criterionId"]
            == "acceptance.decision-ready-consumer-projection"
        )
        row["evidenceRoleBindings"]["coordinateBasisIds"] = [
            "evidence.program-plan"
        ]
        self.assert_rejected(document, "coordinate evidence is generic-only")

    def test_flat_evidence_projection_drift_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceIds"].pop()
        self.assert_rejected(document, "evidence projection drifted")

    def test_missing_partial_criterion_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"].pop()
        self.assert_rejected(document, "partial criterion coverage drifted")

    def test_duplicate_partial_criterion_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][-1] = copy.deepcopy(
            document["criterionReconciliations"][0]
        )
        self.assert_rejected(document, "partial criterion coverage drifted")

    def test_wrong_closeout_cluster_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["clusterId"] = "final-cleanup"
        self.assert_rejected(document, "cluster assignment drifted")

    def test_missing_evaluation_dimension_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["inputInventory"]["evaluationDimensionIds"].pop()
        document["inputInventory"]["evaluationDimensionCount"] = 11
        self.assert_rejected(document, "evaluation dimension inventory drifted")

    def test_missing_lifecycle_slice_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["inputInventory"]["lifecycleSliceIds"].pop()
        document["inputInventory"]["lifecycleSliceCount"] = 13
        self.assert_rejected(document, "lifecycle slice inventory drifted")

    def test_missing_scenario_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["inputInventory"]["scenarioIds"].pop()
        document["inputInventory"]["scenarioCount"] = 12
        self.assert_rejected(document, "scenario inventory drifted")

    def test_missing_human_route_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["routeComparison"].pop("H")
        self.assert_rejected(document, "route comparison drifted")

    def test_unknown_coordinate_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["dimensionIds"].append(
            "invented-dimension"
        )
        self.assert_rejected(document, "unknown coordinate")

    def test_each_governed_coordinate_must_be_mapped_by_a_criterion(self) -> None:
        document = copy.deepcopy(self.document)
        for row in document["criterionReconciliations"]:
            row["dimensionIds"] = [
                value
                for value in row["dimensionIds"]
                if value != "implementation-and-code-quality"
            ]
        self.assert_rejected(document, "mapped coordinate coverage drifted")

    def test_unexplained_empty_coordinate_set_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        row = document["criterionReconciliations"][0]
        row["scenarioIds"] = []
        row["coordinatePosture"] = "mapped"
        row["dispositions"] = [
            value for value in row["dispositions"] if value != "not-applicable"
        ]
        self.assert_rejected(document, "empty coordinate set is unexplained")

    def test_unknown_evidence_id_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["evidenceIds"].append(
            "evidence.invented"
        )
        self.assert_rejected(document, "unknown evidence identity")

    def test_unknown_disposition_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["dispositions"].append(
            "probably-covered"
        )
        self.assert_rejected(document, "disposition vocabulary drifted")

    def test_unassessed_route_cannot_become_residual_gap(self) -> None:
        document = copy.deepcopy(self.document)
        document["criterionReconciliations"][0]["routeComparison"][
            "R"
        ] = "eligible-residual-gap"
        self.assert_rejected(document, "residual route overclaimed")

    def test_behavior_claim_promotion_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["behaviorProved"] = True
        self.assert_rejected(document, "claim boundary overclaimed")

    def test_nonzero_execution_counter_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionCounters"]["modelRequestCount"] = 1
        self.assert_rejected(document, "execution counter is nonzero")

    def test_live_migration_authority_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"]["liveV2MigrationAuthorized"] = True
        self.assert_rejected(document, "authority expanded")

    def test_source_digest_drift_fails_closed(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"]["programAcceptanceMap"]["sha256"] = "0" * 64
        self.assert_rejected(document, "source binding drifted")


if __name__ == "__main__":
    unittest.main()
