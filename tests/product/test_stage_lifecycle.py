import copy
import unittest

from yiyuan_accord import stage_lifecycle


LOCATOR = stage_lifecycle.SNAPSHOT_LOCATOR


def _acceptance():
    return {
        "productId": "yiyuan-accord",
        "release": "v3.1",
        "evidenceLanes": ["representative"],
        "representativeBehaviorPolicy": {
            "evaluationContractHistory": ["excluded-from-digest"],
        },
        "claimCeiling": {"finiteReleaseClaims": [], "notImplied": []},
        "criteria": [
            {
                "id": "R1",
                "class": "required",
                "name": "representative",
                "mapsTo": ["goal"],
                "statement": "observable behavior",
                "passRule": "pass",
                "requiredEvidenceClasses": ["representative-behavior"],
            },
            {
                "id": "Q4",
                "requiredEvidenceClasses": [],
                "latestAssessmentBoundary": (
                    stage_lifecycle.MIGRATION_Q4_LATEST_ASSESSMENT_BOUNDARY
                ),
            },
        ],
        "publicRelease": {"tag": "v3.1.0", "revision": "2" * 40},
    }


def _golden():
    return {"evaluationProtocol": {"kind": "bounded"}, "metrics": ["pass"]}


def _base_program(node):
    return {
        "release": "v3.1",
        "distributionVersion": "v3.1.0",
        "historicalRelease": {"recommendedPublicRelease": "v3.1.0"},
        "status": "ready",
        "hostProjections": [{"id": "codex"}, {"id": "claude"}],
        "increment": {
            "state": "completed",
            "exactPackageEvidenceLifecycle": {"schema": "frozen/v1"},
            "closeoutSnapshot": node,
        },
        "goalModePrompt": {"state": "retired"},
        "releaseProcedure": {"orderedGates": []},
        "complexityBudget": {
            "targets": {
                "maxProductCodeAndTestBytes": (
                    stage_lifecycle.MIGRATION_COMPLEXITY_LIMIT
                ),
            },
            "targetCalibrationRule": (
                stage_lifecycle.MIGRATION_COMPLEXITY_CALIBRATION_RULE
            ),
        },
    }


def _transition(kind, paths, affected):
    transition = {
        "kind": kind,
        "rationaleRef": "product/program.json#/maintenanceCycle/plan",
        "affectedCriterionIds": list(affected),
        "processRef": "product/program.json#/maintenanceCycle/orderedTransitions",
        "changedPaths": list(paths),
    }
    if kind == "repository-presentation":
        transition["surfaceSha256"] = dict(
            stage_lifecycle.PRESENTATION_SURFACE_SHA256
        )
    return transition


def _maintenance_cycle(kind):
    presentation_state = "active" \
        if kind == "transition-contract-migration" else "completed"
    review_state = "pending" \
        if kind == "transition-contract-migration" else "active"
    current_boundary = "repository-presentation" \
        if kind == "transition-contract-migration" else "whole-system-review"
    all_criteria = ["R1", "R2", "R3", "R4", "Q1", "Q2", "Q3", "Q4"]
    return {
        "schema": "yiyuan-accord-maintenance-cycle/v1",
        "id": "post-v3.1-maintenance",
        "kind": "maintenance",
        "state": "active",
        "releaseBasisRef": "product/program.json#/historicalRelease",
        "releaseIntent": None,
        "candidateEligible": False,
        "plan": {
            "outcome": (
                "close-two-batch-post-v3.1-maintenance-then-stop-at-review-only-boundary"
            ),
            "allowedScope": [
                "transition-contract-migration",
                "bilingual-repository-presentation",
                "whole-system-read-only-review",
            ],
            "excludedScope": [
                "main-mutation", "tag-or-release",
                "grok-zcode-or-host-adapter-implementation",
                "runtime-skill-or-hook-functionality-change",
                "whole-system-review-follow-on-implementation",
            ],
            "finiteStopCondition": (
                "the exact two maintenance transitions pass and whole-system-review "
                "remains review-only with implementation authority absent"
            ),
        },
        "orderedTransitions": [
            {
                "id": "successor-baseline",
                "dependsOn": [],
                "acceptanceIds": all_criteria,
                "stopCondition": (
                    "exact-299ae401-predecessor-v3-lineage-valid-and-release-"
                    "package-history-frozen"
                ),
                "state": "completed",
            },
            {
                "id": "repository-presentation",
                "dependsOn": ["successor-baseline"],
                "acceptanceIds": ["R1", "R4", "Q2", "Q3", "Q4"],
                "targetArtifacts": dict(
                    stage_lifecycle.PRESENTATION_SURFACE_SHA256
                ),
                "stopCondition": (
                    "only-lifecycle-bookkeeping-plus-the-two-preauthorized-"
                    "readme-blobs-change"
                ),
                "state": presentation_state,
            },
            {
                "id": "whole-system-review",
                "dependsOn": ["repository-presentation"],
                "acceptanceIds": all_criteria,
                "targetArtifacts": {},
                "stopCondition": (
                    "read-only-review-produces-one-evidence-bound-next-decision-"
                    "or-no-op-and-authorizes-no-implementation"
                ),
                "state": review_state,
            },
        ],
        "currentBoundaryId": current_boundary,
        "goalProjection": {
            "outcome": (
                "complete-bounded-post-v3.1-maintenance-without-release-or-"
                "feature-implementation"
            ),
            "repositoryRef": "product/constitution.json#/identity/repository",
            "branch": "phase/post-v3.1-successor",
            "baseRevision": "299ae4011b0e48df586a137a2fbdcaff715e55c7",
            "mainMutation": False,
            "postPresentationMode": "whole-system-review-only",
            "implementationAuthority": "absent",
            "currentBoundaryId": current_boundary,
        },
        "unknowns": [
            "current-host-entry-instance-behavior",
            "macos-linux-field-behavior",
            "future-host-compatibility",
            "runtime-need",
            "minimum-sufficient-skill-hook-set",
        ],
        "refreshTriggers": [
            "user-correction",
            "material-evidence-change",
            "host-client-or-extension-drift",
            "cycle-scope-or-authority-change",
            "validation-or-hosted-ci-failure",
        ],
    }


def _v3_node(acceptance, golden, kind="transition-contract-migration"):
    paths = stage_lifecycle.MIGRATION_CHANGED_PATHS \
        if kind == "transition-contract-migration" \
        else stage_lifecycle.PRESENTATION_CHANGED_PATHS
    affected = ("R1", "R2", "R3", "R4", "Q1", "Q2", "Q3", "Q4") \
        if kind == "transition-contract-migration" \
        else ("R1", "R4", "Q2", "Q3", "Q4")
    stage = "successor-baseline" if kind == "transition-contract-migration" \
        else "repository-presentation"
    next_gate = "repository-presentation" \
        if kind == "transition-contract-migration" else "whole-system-review"
    return {
        "schema": stage_lifecycle.SNAPSHOT_V3_SCHEMA,
        "id": f"stage.post-v3.1-maintenance.{stage}.closed",
        "stage": stage,
        "state": "closed",
        "revisionBinding": {
            "kind": "containing-git-commit",
            "selfLocator": LOCATOR,
            "exactLocatorRule": (
                "After commit, prefix selfLocator with the immutable containing "
                "commit SHA; never store that SHA inside this object."
            ),
        },
        "predecessorSnapshotRef": stage_lifecycle.MIGRATION_PREDECESSOR_REF,
        "authorityRefs": [
            "product/constitution.json", "product/program.json",
            "product/acceptance.json",
        ],
        "surfaceRefs": {
            "baseline": (
                "product/reshaping-guidance.json#/wholeSystemBalanceReview"
            ),
            "plan": "product/program.json#/maintenanceCycle/plan",
            "process": "product/program.json#/maintenanceCycle/orderedTransitions",
            "acceptance": "product/acceptance.json#/criteria",
            "goalProjection": "product/program.json#/maintenanceCycle/goalProjection",
        },
        "evidenceRefs": [
            "product/program.json#/inputEvidence",
            "product/acceptance.json#/criteria",
            "evals/golden-tasks.json",
            "product/program.json#/historicalRelease",
        ],
        "evidenceCutoff": {
            "kind": "containing-git-commit",
            "rule": (
                "Only evidenceRefs resolved inside the immutable containing "
                "commit belong to this snapshot; later repository or task-time "
                "facts require a successor node."
            ),
        },
        "invalidationTriggerRefs": [
            "product/constitution.json#/evolutionPolicy/feedbackRule",
            "product/program.json#/maintenanceCycle/refreshTriggers",
            "product/program.json#/processLossControl/correctionRule",
        ],
        "acceptanceTransition": _transition(kind, paths, affected),
        "evaluationContractSha256": (
            stage_lifecycle._evaluation_contract_sha256(acceptance, golden)
        ),
        "closedGateId": stage,
        "nextGateId": next_gate,
        "cycle": {
            "id": "post-v3.1-maintenance",
            "kind": "maintenance",
            "contractRef": "product/program.json#/maintenanceCycle",
            "releaseBasisRef": "product/program.json#/historicalRelease",
            "releaseIntent": None,
            "candidateEligible": False,
        },
        "claimCeilingRef": "product/acceptance.json#/claimCeiling",
        "unknownsRef": "product/program.json#/maintenanceCycle/unknowns",
    }


def _migration_documents():
    acceptance, golden = _acceptance(), _golden()
    prior_node = {
        "schema": "yiyuan-accord-stage-closeout-snapshot/v2",
        "state": "closed",
        "evaluationContractSha256": (
            stage_lifecycle._evaluation_contract_sha256(acceptance, golden)
        ),
    }
    predecessor = ({}, _base_program(prior_node), acceptance, {}, golden)
    current = copy.deepcopy(predecessor)
    current[1]["status"] = "active"
    current[1]["maintenanceCycle"] = _maintenance_cycle(
        "transition-contract-migration"
    )
    current[1]["maintenanceCycle"]["closeoutSnapshot"] = _v3_node(
        current[2], current[4]
    )
    return current, predecessor


def _presentation_documents():
    predecessor, _ = _migration_documents()
    current = copy.deepcopy(predecessor)
    current[1]["maintenanceCycle"] = _maintenance_cycle(
        "repository-presentation"
    )
    node = _v3_node(current[2], current[4], "repository-presentation")
    node["predecessorSnapshotRef"] = "1" * 40 + ":" + LOCATOR
    current[1]["maintenanceCycle"]["closeoutSnapshot"] = node
    return current, predecessor


class StageLifecycleTests(unittest.TestCase):
    def test_transition_contract_migration_is_candidate_ineligible(self):
        current, predecessor = _migration_documents()
        decision = stage_lifecycle.evaluate_stage_transition(
            current, predecessor, stage_lifecycle.MIGRATION_CHANGED_PATHS,
        )
        self.assertTrue(decision.valid, decision.errors)
        self.assertEqual(decision.affected_criterion_ids, (
            "R1", "R2", "R3", "R4", "Q1", "Q2", "Q3", "Q4",
        ))
        self.assertIn("yiyuan_accord/evidence.py", decision.changed_paths)
        self.assertFalse(decision.candidate_eligible)

    def test_presentation_normalizes_snapshot_only_program_change(self):
        current, predecessor = _presentation_documents()
        decision = stage_lifecycle.evaluate_stage_transition(
            current,
            predecessor,
            stage_lifecycle.PRESENTATION_CHANGED_PATHS,
            stage_lifecycle.PRESENTATION_SURFACE_SHA256,
        )
        self.assertTrue(decision.valid, decision.errors)
        self.assertEqual(
            decision.changed_paths, stage_lifecycle.PRESENTATION_CHANGED_PATHS,
        )
        self.assertEqual(
            decision.affected_criterion_ids, ("R1", "R4", "Q2", "Q3", "Q4"),
        )
        cycle = current[1]["maintenanceCycle"]
        self.assertEqual(
            [item["state"] for item in cycle["orderedTransitions"]],
            ["completed", "completed", "active"],
        )
        self.assertEqual(cycle["currentBoundaryId"], "whole-system-review")
        self.assertEqual(
            cycle["goalProjection"]["currentBoundaryId"],
            "whole-system-review",
        )

    def test_extra_path_and_changed_frozen_lifecycle_fail_closed(self):
        current, predecessor = _migration_documents()
        current[1]["increment"]["exactPackageEvidenceLifecycle"]["drift"] = True
        decision = stage_lifecycle.evaluate_stage_transition(
            current,
            predecessor,
            (*stage_lifecycle.MIGRATION_CHANGED_PATHS, "runtime/new-service.py"),
        )
        self.assertIn(
            "exact-package evidence lifecycle is not frozen", decision.errors,
        )
        self.assertIn("observed changed paths are invalid", decision.errors)
        self.assertFalse(decision.valid)

    def test_candidate_eligibility_and_affected_set_are_strict(self):
        current, predecessor = _migration_documents()
        node = current[1]["maintenanceCycle"]["closeoutSnapshot"]
        node["cycle"]["candidateEligible"] = True
        node["acceptanceTransition"]["affectedCriterionIds"].pop()
        decision = stage_lifecycle.evaluate_stage_transition(
            current, predecessor, stage_lifecycle.MIGRATION_CHANGED_PATHS,
        )
        self.assertIn("maintenance cycle is invalid", decision.errors)
        self.assertIn("acceptance transition is invalid", decision.errors)

    def test_migration_requires_the_frozen_v2_predecessor(self):
        current, predecessor = _migration_documents()
        predecessor[1]["increment"]["closeoutSnapshot"]["schema"] = "other/v1"
        decision = stage_lifecycle.evaluate_stage_transition(
            current, predecessor, stage_lifecycle.MIGRATION_CHANGED_PATHS,
        )
        self.assertIn("migration predecessor is invalid", decision.errors)

    def test_legacy_increment_and_goal_drift_fail_closed(self):
        mutations = (
            (
                "legacy increment",
                ("increment", "closeoutSnapshot", "state"),
                "open",
            ),
            ("legacy goal", ("goalModePrompt",), {"drift": True}),
            (
                "legacy release procedure",
                ("releaseProcedure", "orderedGates"),
                [{"id": "drift"}],
            ),
        )
        for label, path, value in mutations:
            with self.subTest(label=label):
                current, predecessor = _migration_documents()
                target = current[1]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                decision = stage_lifecycle.evaluate_stage_transition(
                    current,
                    predecessor,
                    stage_lifecycle.MIGRATION_CHANGED_PATHS,
                )
                self.assertIn(
                    "v3.1 release-basis program surfaces are not frozen",
                    decision.errors,
                )
                self.assertFalse(decision.valid)

    def test_presentation_requires_an_exact_valid_migration_predecessor(self):
        cases = ("wrong-ref", "malformed-prior")
        for case in cases:
            with self.subTest(case=case):
                current, predecessor = _presentation_documents()
                if case == "wrong-ref":
                    current[1]["maintenanceCycle"]["closeoutSnapshot"][
                        "predecessorSnapshotRef"
                    ] = "1" * 40 + ":" + stage_lifecycle.LEGACY_SNAPSHOT_LOCATOR
                else:
                    predecessor[1]["maintenanceCycle"]["id"] = "other-cycle"
                decision = stage_lifecycle.evaluate_stage_transition(
                    current,
                    predecessor,
                    stage_lifecycle.PRESENTATION_CHANGED_PATHS,
                    stage_lifecycle.PRESENTATION_SURFACE_SHA256,
                )
                self.assertIn("presentation predecessor is invalid", decision.errors)
                self.assertFalse(decision.valid)

    def test_presentation_requires_observed_readme_hashes(self):
        current, predecessor = _presentation_documents()
        observed = dict(stage_lifecycle.PRESENTATION_SURFACE_SHA256)
        observed["README.md"] = "0" * 64
        decision = stage_lifecycle.evaluate_stage_transition(
            current,
            predecessor,
            stage_lifecycle.PRESENTATION_CHANGED_PATHS,
            observed,
        )
        self.assertIn(
            "observed presentation surface digests are invalid",
            decision.errors,
        )
        self.assertFalse(decision.valid)

    def test_presentation_rejects_extra_program_delta(self):
        current, predecessor = _presentation_documents()
        current[1]["unapprovedMaintenanceDelta"] = True
        decision = stage_lifecycle.evaluate_stage_transition(
            current,
            predecessor,
            stage_lifecycle.PRESENTATION_CHANGED_PATHS,
            stage_lifecycle.PRESENTATION_SURFACE_SHA256,
        )
        self.assertIn("presentation program delta is invalid", decision.errors)
        self.assertFalse(decision.valid)

    def test_closed_maintenance_shape_rejects_field_mutations(self):
        cases = (
            (
                "cycle-id",
                ("maintenanceCycle", "id"),
                "other-cycle",
                "maintenance cycle contract is invalid",
            ),
            (
                "snapshot-stage",
                ("maintenanceCycle", "closeoutSnapshot", "stage"),
                "other-stage",
                "snapshot identity is invalid",
            ),
            (
                "transition-shape",
                (
                    "maintenanceCycle", "closeoutSnapshot",
                    "acceptanceTransition", "unexpected",
                ),
                True,
                "acceptance transition shape is invalid",
            ),
            (
                "evaluation-digest",
                (
                    "maintenanceCycle", "closeoutSnapshot",
                    "evaluationContractSha256",
                ),
                "0" * 64,
                "evaluation contract digest is invalid",
            ),
            (
                "cycle-candidate-eligibility",
                ("maintenanceCycle", "candidateEligible"),
                True,
                "maintenance cycle contract is invalid",
            ),
            (
                "snapshot-candidate-eligibility",
                (
                    "maintenanceCycle", "closeoutSnapshot", "cycle",
                    "candidateEligible",
                ),
                True,
                "maintenance cycle is invalid",
            ),
            (
                "snapshot-extra-field",
                ("maintenanceCycle", "closeoutSnapshot", "unexpected"),
                True,
                "snapshot shape is invalid",
            ),
        )
        for label, path, value, expected_error in cases:
            with self.subTest(label=label):
                current, _ = _migration_documents()
                target = current[1]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                errors = stage_lifecycle.closed_maintenance_snapshot_errors(
                    current[1], current[2], current[4],
                )
                self.assertIn(expected_error, errors)
                self.assertFalse(
                    stage_lifecycle.is_structurally_valid_closed_maintenance_snapshot(
                        current[1], current[2], current[4],
                    )
                )

    def test_malformed_required_evidence_classes_fail_closed(self):
        for value in (None, 1, "representative-behavior"):
            with self.subTest(value=value):
                current, _ = _migration_documents()
                current[2]["criteria"][0]["requiredEvidenceClasses"] = value
                errors = stage_lifecycle.closed_maintenance_snapshot_errors(
                    current[1], current[2], current[4],
                )
                self.assertIn("evaluation contract digest is invalid", errors)
                self.assertFalse(
                    stage_lifecycle.is_structurally_valid_closed_maintenance_snapshot(
                        current[1], current[2], current[4],
                    )
                )

    def test_migration_complexity_assessment_is_exact(self):
        mutations = (
            ("assessment", "arbitrary unrelated claim"),
            ("limit", 959999),
            ("rule", "arbitrary unrelated calibration"),
        )
        for kind, value in mutations:
            with self.subTest(kind=kind):
                current, predecessor = _migration_documents()
                if kind == "assessment":
                    current[2]["criteria"][1][
                        "latestAssessmentBoundary"
                    ] = value
                elif kind == "limit":
                    current[1]["complexityBudget"]["targets"][
                        "maxProductCodeAndTestBytes"
                    ] = value
                else:
                    current[1]["complexityBudget"][
                        "targetCalibrationRule"
                    ] = value
                decision = stage_lifecycle.evaluate_stage_transition(
                    current,
                    predecessor,
                    stage_lifecycle.MIGRATION_CHANGED_PATHS,
                )
                self.assertIn(
                    "migration complexity calibration is invalid",
                    decision.errors,
                )
                self.assertFalse(decision.valid)


if __name__ == "__main__":
    unittest.main()
