from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import harness.control as product_control
from harness.control import validate_continuation_receipt


ROOT = Path(__file__).resolve().parents[2]


class ProductControlCliTests(unittest.TestCase):
    def run_verify(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "harness",
                "verify",
                "--root",
                str(root),
                "--json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def copy_checkout_with_history(self, target: Path) -> None:
        shutil.copytree(
            ROOT,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".tmp",
                "legacy",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
            ),
        )
        subprocess.run(
            ["git", "init", "--quiet"],
            cwd=target,
            text=True,
            capture_output=True,
            check=True,
        )
        common_dir = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        alternates = target / ".git" / "objects" / "info" / "alternates"
        alternates.parent.mkdir(parents=True, exist_ok=True)
        alternates.write_bytes(
            (
                str((Path(common_dir) / "objects").resolve()).replace("\\", "/")
                + "\n"
            ).encode("utf-8")
        )

    def test_current_repository_exposes_one_product_progress_report(self) -> None:
        result = self.run_verify(ROOT)

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["productId"], "agent-autonomy-harness")
        self.assertEqual(report["release"], "v0.1")
        self.assertEqual(
            report["activeIncrement"],
            "increment.current-official-route-evaluation-slice",
        )
        self.assertTrue(report["criterionStates"]["O4"])
        self.assertEqual(report["outcomes"], {"total": 5, "verified": 4})
        self.assertEqual(report["guardrails"], {"total": 4, "passed": 4})
        self.assertEqual(report["completionState"], "in-progress")

    def test_unmapped_work_is_rejected_at_the_product_seam(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["increments"][0]["workItems"].append(
                {
                    "id": "work.unmapped",
                    "state": "planned",
                    "acceptanceIds": [],
                    "deliverables": ["nowhere"],
                }
            )
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "work item work.unmapped must map to at least one acceptance criterion",
            report["errors"],
        )

    def test_active_work_must_belong_to_the_active_increment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            non_active_increment = next(
                item
                for item in program["increments"]
                if item["id"] == "increment.context-continuity-product-slice"
            )
            non_active_increment["workItems"][0]["state"] = "active"
            current_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            current_increment["workItems"][0]["state"] = "planned"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "active work work.run-real-continuity-slice must belong to the active increment",
            report["errors"],
        )

    def test_completed_increment_cannot_retain_open_work(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            completed_increment = next(
                item for item in program["increments"] if item["state"] == "completed"
            )
            completed_increment["workItems"][0]["state"] = "planned"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "completed increment increment.product-control-reset cannot retain open work work.bind-product-constitution",
            report["errors"],
        )

    def test_completed_increment_requires_its_outcomes_to_be_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            o4 = next(
                item for item in acceptance["criteria"] if item["id"] == "O4"
            )
            o4["assessment"] = "planned"
            o4.pop("evidence")
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "completed increment increment.context-continuity-product-slice requires verified outcome O4",
            report["errors"],
        )

    def test_falsified_increment_can_stop_without_promoting_its_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_checkout_with_history(target)

            result = self.run_verify(target)

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertFalse(report["criterionStates"]["O3"])

    def test_falsified_increment_cannot_stop_while_review_root_remains(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_checkout_with_history(target)
            (
                target / ".tmp" / "o3-capability-review-2026-08-11"
            ).mkdir(parents=True)

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "stopped increment increment.capability-lifecycle-product-slice must bind valid falsifier and cleanup evidence",
            report["errors"],
        )

    def test_falsified_increment_requires_observed_zero_coverage_stop_rule(self) -> None:
        mutations = {
            "stop rule did not fire": lambda evidence: evidence[
                "stopRuleObservation"
            ].__setitem__("stopTriggered", False),
            "stop sequence drifted": lambda evidence: evidence[
                "stopRuleObservation"
            ].__setitem__("stopSequence", ["some-other-candidate"]),
            "candidate added unique coverage": lambda evidence: evidence[
                "candidateReviews"
            ][0].__setitem__("uniqueDemandIds", ["SE-DISCOVERY-REQ-01"]),
            "zero coverage metric drifted": lambda evidence: evidence[
                "decisionMetrics"
            ]["primary"][1].__setitem__("value", 1),
            "program falsifier did not match": lambda evidence: evidence[
                "incrementFalsifierObservation"
            ].__setitem__("matchedFalsifier", "some unrelated failure"),
            "contract revision drifted": lambda evidence: evidence[
                "taskBinding"
            ].__setitem__("contractRevision", "0" * 40),
            "candidate source revision drifted": lambda evidence: evidence[
                "sourceSnapshots"
            ][0].__setitem__("revision", "0" * 40),
            "candidate source id is unhashable": lambda evidence: evidence[
                "sourceSnapshots"
            ][0].__setitem__("id", []),
            "cleanup target drifted": lambda evidence: evidence[
                "cleanupObservation"
            ].__setitem__("root", "C:/tmp/some-other-review-root"),
            "cleanup parent is not text": lambda evidence: evidence[
                "cleanupObservation"
            ].__setitem__("resolvedParent", []),
            "post-stop acquired inventory drifted": lambda evidence: evidence[
                "stopRuleObservation"
            ].__setitem__("alreadyAcquiredBeforeStopConclusion", []),
            "claim ceiling collapsed": lambda evidence: evidence.__setitem__(
                "claimLimits", ["looks good"]
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                self.copy_checkout_with_history(target)
                evidence_path = (
                    target
                    / "product"
                    / "evidence"
                    / "o3-portfolio-cohort-review-2026-08-11.json"
                )
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                mutate(evidence)
                evidence_path.write_text(
                    json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(
                    "stopped increment increment.capability-lifecycle-product-slice must bind valid falsifier and cleanup evidence",
                    report["errors"],
                )

    def test_official_kpi_event_requires_its_exact_machine_bound_contract(self) -> None:
        mutations = {
            "plugin version drifted": lambda contract: contract[
                "capabilityIdentity"
            ].__setitem__("pluginVersion", "some-other-version"),
            "skill hash drifted": lambda contract: contract[
                "capabilityIdentity"
            ]["skillChain"][0].__setitem__("sha256", "0" * 64),
            "unpaired surrogate": lambda contract: contract[
                "capabilityIdentity"
            ].__setitem__("pluginName", "\ud800"),
            "unpaired surrogate in prompt": lambda contract: contract[
                "eventContract"
            ].__setitem__("prompt", "\ud800"),
            "prompt changed without rebind": lambda contract: contract[
                "eventContract"
            ].__setitem__("prompt", contract["eventContract"]["prompt"] + " changed"),
            "fresh context disabled": lambda contract: contract[
                "eventContract"
            ].__setitem__("forkTurns", "all"),
            "private source added": lambda contract: contract[
                "dataBoundary"
            ]["allowed"].append("private account data"),
            "receiver write added": lambda contract: contract[
                "authorityBoundary"
            ]["allowed"].append("write repository files"),
            "scorecard count drifted": lambda contract: contract[
                "scorecardContract"
            ].__setitem__("harnessScenarios", 12),
            "KPI target drifted": lambda contract: contract[
                "measurementFramework"
            ]["primary"][1].__setitem__("target", 999),
            "verification removed": lambda contract: contract.__setitem__(
                "verification", []
            ),
            "receiver mutation allowed": lambda contract: contract[
                "cleanup"
            ].__setitem__("persistentStateAllowed", True),
            "dirty post-event state allowed": lambda contract: contract[
                "cleanup"
            ].__setitem__("requiredPostEventState", "dirty Git status is allowed"),
            "claim ceiling collapsed": lambda contract: contract.__setitem__(
                "claimLimits", ["looks good"]
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                self.copy_checkout_with_history(target)
                contract_path = (
                    target
                    / "product"
                    / "evidence"
                    / "o3-official-kpi-event-contract-2026-08-11.json"
                )
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                mutate(contract)
                contract_path.write_text(
                    json.dumps(contract, ensure_ascii=True, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(
                    "work item work.run-fresh-official-kpi-capability-event must bind the exact official KPI event contract",
                    report["errors"],
                )

    def test_official_kpi_event_work_context_cannot_expand_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_checkout_with_history(target)
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            increment = next(
                item
                for item in program["increments"]
                if item["id"]
                == "increment.current-official-route-evaluation-slice"
            )
            work_item = next(
                item
                for item in increment["workItems"]
                if item["id"] == "work.run-fresh-official-kpi-capability-event"
            )
            work_item["capabilityContext"]["authorityBoundary"] = (
                "allow repository writes, installs, accounts, and publication"
            )
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "work item work.run-fresh-official-kpi-capability-event must bind the exact official KPI event contract",
            report["errors"],
        )

    def test_active_scorecard_work_requires_its_exact_capability_context(
        self,
    ) -> None:
        mutations = {
            "task revision drifted": lambda context: context.__setitem__(
                "taskBinding", "agent-autonomy-harness-v0.1-closeout@" + "0" * 40
            ),
            "authority became arbitrary text": lambda context: context.__setitem__(
                "authorityBoundary", "anything goes"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                self.copy_checkout_with_history(target)
                program_path = target / "product" / "program.json"
                program = json.loads(program_path.read_text(encoding="utf-8"))
                increment = next(
                    item
                    for item in program["increments"]
                    if item["id"]
                    == "increment.current-official-route-evaluation-slice"
                )
                scorecard_work = next(
                    item
                    for item in increment["workItems"]
                    if item["id"]
                    == "work.build-sparse-scorecard-and-close-lifecycle"
                )
                mutate(scorecard_work["capabilityContext"])
                program_path.write_text(
                    json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(
                    "work item work.build-sparse-scorecard-and-close-lifecycle must bind the exact scorecard capabilityContext",
                    report["errors"],
                )

    def test_scorecard_work_requires_the_evidence_incomplete_predecessor(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_checkout_with_history(target)
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            increment = next(
                item
                for item in program["increments"]
                if item["id"]
                == "increment.current-official-route-evaluation-slice"
            )
            event_work = next(
                item
                for item in increment["workItems"]
                if item["id"]
                == "work.run-fresh-official-kpi-capability-event"
            )
            event_work["state"] = "planned"
            event_work.pop("resultEvidence")
            event_work.pop("result")
            event_work.pop("cancellationRationale")
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (
                target
                / "product"
                / "evidence"
                / "o3-official-kpi-event-receipt-2026-08-11.json"
            ).unlink()

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "work item work.build-sparse-scorecard-and-close-lifecycle requires a cancelled evidence-incomplete predecessor with a valid normalized event receipt",
            report["errors"],
        )

    def test_active_scorecard_work_rejects_self_declared_progress_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_checkout_with_history(target)
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            increment = next(
                item
                for item in program["increments"]
                if item["id"]
                == "increment.current-official-route-evaluation-slice"
            )
            scorecard_work = next(
                item
                for item in increment["workItems"]
                if item["id"]
                == "work.build-sparse-scorecard-and-close-lifecycle"
            )
            scorecard_work["progressEvidence"] = (
                "product/evidence/o3-sparse-scorecard-2026-08-11.json"
            )
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            (
                target
                / "product"
                / "evidence"
                / "o3-sparse-scorecard-2026-08-11.json"
            ).write_text(
                json.dumps({"id": "self-declared-scorecard"}, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "active work item work.build-sparse-scorecard-and-close-lifecycle must bind valid source-reconciled scorecard progress evidence",
            report["errors"],
        )

    def test_scorecard_work_cannot_complete_with_pending_or_missing_evidence(
        self,
    ) -> None:
        mutations = {
            "lifecycle remains pending": (
                lambda work, target: None,
                "completed work item work.build-sparse-scorecard-and-close-lifecycle cannot use lifecycle-pending scorecard evidence",
            ),
            "progress evidence removed": (
                lambda work, target: (
                    work.pop("progressEvidence"),
                    (
                        target
                        / "product"
                        / "evidence"
                        / "o3-sparse-scorecard-2026-08-11.json"
                    ).unlink(),
                ),
                "completed work item work.build-sparse-scorecard-and-close-lifecycle must bind valid source-reconciled scorecard progress evidence",
            ),
        }
        for label, (mutate, expected_error) in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                self.copy_checkout_with_history(target)
                program_path = target / "product" / "program.json"
                program = json.loads(program_path.read_text(encoding="utf-8"))
                increment = next(
                    item
                    for item in program["increments"]
                    if item["id"]
                    == "increment.current-official-route-evaluation-slice"
                )
                scorecard_work = next(
                    item
                    for item in increment["workItems"]
                    if item["id"]
                    == "work.build-sparse-scorecard-and-close-lifecycle"
                )
                scorecard_work["state"] = "completed"
                mutate(scorecard_work, target)
                program_path.write_text(
                    json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(expected_error, report["errors"])

    def test_active_scorecard_work_requires_the_bound_lifecycle_contract(
        self,
    ) -> None:
        mutations = {
            "contract locator removed": lambda work, contract, path: (
                work.pop("lifecycleContractEvidence"),
                path.unlink(),
            ),
            "prior attempt evidence removed": lambda work, contract, path: work.pop(
                "lifecycleAttemptEvidence"
            ),
            "contract phase semantics drifted": lambda work, contract, path: contract[
                "phaseSemantics"
            ].__setitem__("boundedActivation", "ordinary Skill use"),
            "durable checkpoint protocol removed": lambda work, contract, path: contract[
                "eventContract"
            ].pop("checkpointProtocol"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                self.copy_checkout_with_history(target)
                program_path = target / "product" / "program.json"
                program = json.loads(program_path.read_text(encoding="utf-8"))
                increment = next(
                    item
                    for item in program["increments"]
                    if item["id"]
                    == "increment.current-official-route-evaluation-slice"
                )
                scorecard_work = next(
                    item
                    for item in increment["workItems"]
                    if item["id"]
                    == "work.build-sparse-scorecard-and-close-lifecycle"
                )
                contract_path = (
                    target
                    / "product"
                    / "evidence"
                    / "o3-official-lifecycle-transaction-contract-2026-08-11.json"
                )
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                mutate(scorecard_work, contract, contract_path)
                program_path.write_text(
                    json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                if contract_path.exists():
                    contract_path.write_text(
                        json.dumps(contract, ensure_ascii=True, indent=2) + "\n",
                        encoding="utf-8",
                    )

                result = self.run_verify(target)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(
                    "active work item work.build-sparse-scorecard-and-close-lifecycle must bind the exact bound lifecycle transaction contract",
                    report["errors"],
                )

    def test_sparse_scorecard_is_fail_closed_at_source_and_claim_boundaries(
        self,
    ) -> None:
        mutations = {
            "criterion source hash drifted": lambda scorecard: scorecard[
                "entries"
            ]["partialCriteria"][0]["evidence"].__setitem__(
                "historicalRecordCanonicalSha256", "0" * 64
            ),
            "derived membership drifted": lambda scorecard: scorecard[
                "entries"
            ]["lifecycleSlices"][0]["memberCriterionIds"].pop(),
            "required disposition removed": lambda scorecard: scorecard[
                "entries"
            ]["evaluationDimensions"][0].pop("disposition"),
            "cartesian aggregate retained": lambda scorecard: scorecard[
                "aggregateDecisions"
            ][0].__setitem__("disposition", "retain"),
            "capability addition invented": lambda scorecard: scorecard[
                "routeDecision"
            ].__setitem__("additionProposed", True),
            "lifecycle phase promoted": lambda scorecard: scorecard[
                "lifecycleTransaction"
            ]["phases"].__setitem__("boundedActivation", "observed"),
            "claim ceiling collapsed": lambda scorecard: scorecard.__setitem__(
                "claimLimits", ["looks good"]
            ),
            "entry container malformed": lambda scorecard: scorecard[
                "entries"
            ].__setitem__("harnessScenarios", []),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                self.copy_checkout_with_history(target)
                scorecard_path = (
                    target
                    / "product"
                    / "evidence"
                    / "o3-sparse-scorecard-2026-08-11.json"
                )
                scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
                mutate(scorecard)
                scorecard_path.write_text(
                    json.dumps(scorecard, ensure_ascii=True, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(
                    "active work item work.build-sparse-scorecard-and-close-lifecycle must bind valid source-reconciled scorecard progress evidence",
                    report["errors"],
                )

    def test_sparse_scorecard_semantics_are_derived_from_the_historical_source(
        self,
    ) -> None:
        source = json.loads(
            subprocess.run(
                [
                    "git",
                    "show",
                    "c53866726834d79a68c61a5b87b4f7ce90698a2c:registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            ).stdout
        )
        scorecard = json.loads(
            (
                ROOT
                / "product"
                / "evidence"
                / "o3-sparse-scorecard-2026-08-11.json"
            ).read_text(encoding="utf-8")
        )
        partial_entries = scorecard["entries"]["partialCriteria"]
        aggregate_decision = scorecard["aggregateDecisions"][0]

        self.assertTrue(
            product_control._valid_o3_sparse_scorecard_source_derivation(
                source,
                partial_entries,
                aggregate_decision,
            )
        )

        mutations = {
            "human-judgment omission set drifted": lambda src, entries, decision: src[
                "criterionReconciliations"
            ][0]["dispositions"].remove("needs-human-judgment"),
            "correction disposition removed": lambda src, entries, decision: entries[
                3
            ].__setitem__("disposition", "retain-with-claim-narrowing"),
            "mapped count drifted": lambda src, entries, decision: src[
                "candidateCoverageSummary"
            ].__setitem__("mappedRouteCellCount", 49),
            "cartesian total drifted": lambda src, entries, decision: src[
                "candidateCoverageSummary"
            ].__setitem__("routeCellCount", 77),
            "explicit route cell appeared": lambda src, entries, decision: src.__setitem__(
                "routeCellRecords",
                [{"scenarioId": "GEN-CREATIVE-01", "routeClassId": "N"}],
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                mutated_source = deepcopy(source)
                mutated_entries = deepcopy(partial_entries)
                mutated_decision = deepcopy(aggregate_decision)
                mutate(mutated_source, mutated_entries, mutated_decision)
                self.assertFalse(
                    product_control._valid_o3_sparse_scorecard_source_derivation(
                        mutated_source,
                        mutated_entries,
                        mutated_decision,
                    )
                )

    def test_completed_official_kpi_event_rejects_a_self_declared_receipt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_checkout_with_history(target)
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            increment = next(
                item
                for item in program["increments"]
                if item["id"]
                == "increment.current-official-route-evaluation-slice"
            )
            event_work = next(
                item
                for item in increment["workItems"]
                if item["id"]
                == "work.run-fresh-official-kpi-capability-event"
            )
            scorecard_work = next(
                item
                for item in increment["workItems"]
                if item["id"] == "work.build-sparse-scorecard-and-close-lifecycle"
            )
            event_work["state"] = "completed"
            event_work["resultEvidence"] = (
                "product/evidence/o3-official-kpi-event-receipt-2026-08-11.json"
            )
            scorecard_work["state"] = "active"
            scorecard_work["capabilityContext"] = deepcopy(
                event_work["capabilityContext"]
            )
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            receipt_path = (
                target
                / "product"
                / "evidence"
                / "o3-official-kpi-event-receipt-2026-08-11.json"
            )
            receipt_path.write_text(
                json.dumps(
                    {"id": "self-declared-receipt", "eventOccurred": True},
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "closed work item work.run-fresh-official-kpi-capability-event must bind a valid normalized event receipt",
            report["errors"],
        )

    def test_missing_raw_payload_hash_prevents_event_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.copy_checkout_with_history(target)
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            increment = next(
                item
                for item in program["increments"]
                if item["id"]
                == "increment.current-official-route-evaluation-slice"
            )
            event_work = next(
                item
                for item in increment["workItems"]
                if item["id"]
                == "work.run-fresh-official-kpi-capability-event"
            )
            event_work["state"] = "completed"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "work item work.run-fresh-official-kpi-capability-event cannot be completed while the contract-required raw payload hash is absent",
            report["errors"],
        )

    def test_official_kpi_event_receipt_is_fail_closed_at_claim_boundaries(
        self,
    ) -> None:
        mutations = {
            "receiver revision drifted": lambda receipt: receipt[
                "eventIdentity"
            ].__setitem__("observedRevision", "0" * 40),
            "normalized decision drifted": lambda receipt: receipt[
                "normalizedProjection"
            ]["routeDecision"].__setitem__("additionProposed", True),
            "grain assessment is not an object": lambda receipt: receipt[
                "normalizedProjection"
            ].__setitem__("grainAssessment", []),
            "raw output hash was guessed": lambda receipt: receipt[
                "normalizedProjection"
            ]["rawPayload"].__setitem__("sha256", "0" * 64),
            "absent lifecycle phase was promoted": lambda receipt: receipt[
                "lifecyclePhaseReconciliation"
            ]["phases"].__setitem__("boundedActivation", "observed"),
            "lifecycle owner was invented": lambda receipt: receipt[
                "lifecyclePhaseReconciliation"
            ].__setitem__("lifecycleOwner", "parent Agent"),
            "post-event repository was dirty": lambda receipt: receipt[
                "postEvent"
            ].__setitem__("clean", False),
            "skill identity drifted": lambda receipt: receipt[
                "sourceSkillIdentities"
            ][0].__setitem__("sha256", "0" * 64),
            "claim ceiling collapsed": lambda receipt: receipt.__setitem__(
                "claimLimits", ["looks good"]
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                self.copy_checkout_with_history(target)
                receipt_path = (
                    target
                    / "product"
                    / "evidence"
                    / "o3-official-kpi-event-receipt-2026-08-11.json"
                )
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                mutate(receipt)
                receipt_path.write_text(
                    json.dumps(receipt, ensure_ascii=True, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(
                    "closed work item work.run-fresh-official-kpi-capability-event must bind a valid normalized event receipt",
                    report["errors"],
                )

    def test_predecessor_identity_is_rejected_from_active_product_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            predecessor_identity = "agent" + "-skills" + "-curated"
            program["purpose"] = f"{predecessor_identity} compatibility mode"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "active product authority contains a forbidden predecessor identity",
            report["errors"],
        )

    def test_top_level_contract_drift_cannot_leave_o1_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["completionExpression"] = "O1"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])

    def test_constitution_cannot_disable_the_predecessor_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["predecessorIdentityPattern"] = "(?!)"
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            predecessor_identity = "agent" + "-skills" + "-curated"
            program["purpose"] = f"{predecessor_identity} compatibility mode"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "active product authority contains a forbidden predecessor identity",
            report["errors"],
        )

    def test_constitution_cannot_remove_a_bootstrap_authority_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["requiredAuthorityFiles"] = [
                "product/constitution.json",
                "product/program.json",
                "product/acceptance.json",
                "product/evidence/project-reset-real-task-route-2026-08-11.json",
                "product/evidence/project-reset-cleanup-observation-2026-08-11.json",
            ]
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            predecessor_identity = "agent" + "-skills" + "-curated"
            (target / "README.md").write_text(
                f"# {predecessor_identity}\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "active product authority contains a forbidden predecessor identity",
            report["errors"],
        )

    def test_reintroduced_predecessor_authority_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            registry = target / "registry"
            registry.mkdir()
            predecessor_plan = registry / ("curation" + "-program" + "-plan.json")
            predecessor_plan.write_text("{}\n", encoding="utf-8")

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G3"])
        self.assertIn(
            "current checkout contains a forbidden predecessor authority path",
            report["errors"],
        )

    def test_malformed_program_items_are_structurally_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["increments"] = ["not-an-object"]
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("program increment 0 must be an object", report["errors"])
        self.assertFalse(report["criterionStates"]["O1"])

    def test_unhashable_structure_fields_are_rejected_without_traceback(self) -> None:
        cases = (
            "criterion-id",
            "work-state",
            "capability-context-mode",
            "portfolio-root",
            "task-time-root",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                shutil.copytree(ROOT / "product", target / "product")
                if case == "criterion-id":
                    path = target / "product" / "acceptance.json"
                    document = json.loads(path.read_text(encoding="utf-8"))
                    document["criteria"][1]["id"] = []
                else:
                    path = target / "product" / "program.json"
                    document = json.loads(path.read_text(encoding="utf-8"))
                    active_increment = next(
                        item for item in document["increments"] if item["state"] == "active"
                    )
                    active_work = next(
                        item
                        for item in active_increment["workItems"]
                        if item["state"] == "active"
                    )
                    if case == "work-state":
                        active_work["state"] = []
                    elif case == "capability-context-mode":
                        active_work["operationIds"] = [
                            "installed-authorized-capability-use"
                        ]
                        active_work["capabilityContext"] = {"mode": []}
                    elif case == "portfolio-root":
                        active_work["operationIds"] = ["inactive-exact-acquisition"]
                        active_work["capabilityContext"] = {
                            "mode": "portfolio-curation",
                            "inactiveAcquisitionRoot": [],
                        }
                    else:
                        active_work["operationIds"] = ["inactive-exact-acquisition"]
                        active_work["capabilityContext"] = {
                            "mode": "task-time",
                            "inactiveAcquisitionRoot": [],
                        }
                path.write_text(
                    json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse(report["valid"])
            self.assertFalse(report["criterionStates"]["O1"])

    def test_outcome_evidence_is_not_interchangeable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            route_evidence = "product/evidence/project-reset-real-task-route-2026-08-11.json"
            for criterion in acceptance["criteria"]:
                if criterion["id"] in {"O3", "O4"}:
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = [route_evidence]
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O3"])
        self.assertFalse(report["criterionStates"]["O4"])
        self.assertIn(
            "criterion O3 verification remains fail-closed until the real-task evaluation and host lifecycle evidence validator is implemented",
            report["errors"],
        )
        self.assertIn(
            f"evidence {route_evidence} is not a real continuation receipt",
            report["errors"],
        )

    def test_o4_rejects_an_unbound_self_declared_continuation_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            evidence_relative = "product/evidence/unbound-continuation.json"
            evidence_path = target / evidence_relative
            evidence_path.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "id": "unbound-continuation",
                        "continuation": {
                            "realEvent": True,
                            "receiverDelta": {"materialRestatementItems": 0},
                            "receiverClaimBoundary": "claims one continuation only",
                        },
                        "claimLimits": ["claims one continuation only"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            for criterion in acceptance["criteria"]:
                if criterion["id"] == "O4":
                    criterion["assessment"] = "verified"
                    criterion["evidence"] = [evidence_relative]
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O4"])
        self.assertIn(
            f"evidence {evidence_relative} is not a real continuation receipt",
            report["errors"],
        )

    def test_o4_receipt_is_bound_to_the_observed_source_and_invocation(self) -> None:
        evidence_path = (
            ROOT
            / "product"
            / "evidence"
            / "context-continuity-fresh-receiver-2026-08-11.json"
        )
        receipt = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertTrue(validate_continuation_receipt(ROOT, receipt))

        def forge_revision(candidate: dict[str, object]) -> None:
            zero_revision = "0" * 40
            candidate["sourcePacket"]["revision"] = zero_revision
            candidate["sourcePacket"]["remoteMain"] = zero_revision
            candidate["receiver"]["liveGitFacts"]["head"] = zero_revision
            candidate["receiver"]["liveGitFacts"]["originMain"] = zero_revision

        def forge_prompt(candidate: dict[str, object]) -> None:
            prompt = "the material contract was provided out of band"
            candidate["invocation"]["prompt"] = prompt
            candidate["invocation"]["promptSha256"] = hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest()

        def forge_receiver(candidate: dict[str, object]) -> None:
            candidate["receiver"]["receiverId"] = "/root/forged_receiver"

        def forge_recovered_goal(candidate: dict[str, object]) -> None:
            candidate["continuation"]["receiverDelta"]["recoveredContract"][
                "productGoal"
            ] = "a materially different goal"

        def broaden_claim(candidate: dict[str, object]) -> None:
            candidate["continuation"]["receiverClaimBoundary"].append(
                "proves cross-host production readiness"
            )

        def remove_cleanup(candidate: dict[str, object]) -> None:
            candidate.pop("cleanupReceipt")

        mutations = {
            "revision": forge_revision,
            "prompt": forge_prompt,
            "receiver": forge_receiver,
            "recovered goal": forge_recovered_goal,
            "claim boundary": broaden_claim,
            "cleanup receipt": remove_cleanup,
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = deepcopy(receipt)
                mutate(candidate)
                self.assertFalse(validate_continuation_receipt(ROOT, candidate))

    def test_cleanup_evidence_requires_resolved_absolute_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            evidence_path = target / "product" / "evidence" / "project-reset-cleanup-observation-2026-08-11.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["roots"] = ["%TEMP%"]
            evidence_path.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O5"])
        self.assertFalse(report["criterionStates"]["G4"])
        self.assertIn(
            "cleanup evidence product/evidence/project-reset-cleanup-observation-2026-08-11.json must declare resolved absolute roots",
            report["errors"],
        )

    def test_cleanup_evidence_rejects_unsafe_regex_without_traceback(self) -> None:
        cases = (
            (
                ".*",
                "targetPattern must be start-anchored relative literal alternatives",
            ),
            (
                "^(../escape)",
                "targetPattern must be start-anchored relative literal alternatives",
            ),
            (
                "a{999999999999999999999999999999999999}",
                "targetPattern must compile",
            ),
        )
        for pattern, expected_error in cases:
            with self.subTest(pattern=pattern), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                shutil.copytree(ROOT / "product", target / "product")
                relative = (
                    "product/evidence/project-reset-cleanup-observation-2026-08-11.json"
                )
                evidence_path = target / relative
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                evidence["targetPattern"] = pattern
                evidence_path.write_text(
                    json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(
                any(expected_error in error for error in report["errors"]),
                report["errors"],
            )

    def test_release_identity_cannot_drift_between_plan_and_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            acceptance["release"] = "v-next"
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn("program and acceptance releases must match", report["errors"])

    def test_arbitrary_authority_text_cannot_satisfy_the_human_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            program["authorityBoundary"]["userOwns"] = ["none"]
            program["authorityBoundary"]["agentOwnsWithinBoundedAuthority"] = [
                "release",
                "delete",
            ]
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("program authority boundary is incomplete or conflicting", report["errors"])

    def test_active_work_cannot_claim_an_unauthorized_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = ["release"]
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("active work requests unauthorized operations: release", report["errors"])

    def test_active_work_must_bind_at_least_one_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = []
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn("active or completed work must bind at least one operation", report["errors"])

    def test_constitution_cannot_reactivate_the_local_legacy_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["activeAuthorityGlobs"].append("Legacy/**/*.json")
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "constitution cannot activate excluded authority locator: Legacy/**/*.json",
            report["errors"],
        )

    def test_unreferenced_legacy_directory_is_not_active_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            legacy = target / "legacy"
            legacy.mkdir()
            (legacy / "ordinary.txt").write_text("unrelated archive\n", encoding="utf-8")

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertTrue(report["criterionStates"]["G3"])
        self.assertNotIn(
            "current checkout must not contain a repository-local legacy quarantine",
            report["errors"],
        )

    def test_inactive_temporary_review_pool_is_not_active_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            review_pool = target / ".tmp" / "capability-review"
            review_pool.mkdir(parents=True)
            (review_pool / "candidate.md").write_text(
                "agent-" + "skills-" + "curated historical candidate metadata\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertTrue(report["criterionStates"]["G3"])
        self.assertNotIn(
            "active product authority contains a forbidden predecessor identity",
            report["errors"],
        )

    def test_absolute_authority_glob_is_structurally_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["activeAuthorityGlobs"].append("C:/**/*.json")
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "constitution authority glob must be relative: C:/**/*.json",
            report["errors"],
        )

    def test_broad_authority_glob_cannot_reactivate_inactive_pool(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            review_pool = target / ".tmp" / "capability-review"
            review_pool.mkdir(parents=True)
            (review_pool / "candidate.md").write_text(
                "inactive candidate metadata\n", encoding="utf-8"
            )
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["activeAuthorityGlobs"].append("**/*")
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "constitution authority glob must begin with a literal root: **/*",
            report["errors"],
        )

    def test_active_authority_glob_rejects_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            target = temporary_root / "checkout"
            shutil.copytree(ROOT / "product", target / "product")
            outside = temporary_root / "outside.json"
            outside.write_text('{"outside": true}\n', encoding="utf-8")
            link = target / "product" / "evidence" / "escape.json"
            try:
                link.symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "active authority glob cannot include a symlink: product/evidence/escape.json",
            report["errors"],
        )

    def test_required_authority_file_rejects_symlink_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            replacement = target / "real-readme.md"
            replacement.write_text("replacement\n", encoding="utf-8")
            link = target / "README.md"
            try:
                link.symlink_to(replacement)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)
        report = json.loads(result.stdout)
        self.assertIn(
            "authority path cannot be a symlink: README.md",
            report["errors"],
        )

    def test_posix_absolute_cleanup_root_is_portable_evidence_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            evidence_path = target / "product" / "evidence" / "project-reset-cleanup-observation-2026-08-11.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["roots"] = ["/tmp"]
            evidence_path.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertTrue(report["criterionStates"]["O5"])
        self.assertTrue(report["criterionStates"]["G4"])
        self.assertNotIn(
            "cleanup evidence product/evidence/project-reset-cleanup-observation-2026-08-11.json must declare resolved absolute roots",
            report["errors"],
        )

    def test_top_level_authority_id_cannot_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            acceptance["id"] = "renamed-authority"
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "product/acceptance.json must retain authority id harness-product-acceptance-v0.1",
            report["errors"],
        )

    def test_agent_cannot_drop_its_omission_detection_obligation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["collaborationModel"] = {
                "userContributions": [
                    "goals-and-direction",
                    "domain-context",
                    "corrections",
                    "accountable-final-judgment",
                ],
                "agentObligations": [
                    "assumption-disclosure",
                    "counterexample-search",
                    "evidence-reconciliation",
                    "coverage-supplementation",
                    "bounded-autonomous-execution",
                ],
            }
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "constitution collaborationModel must preserve user roles and agent obligations",
            report["errors"],
        )

    def test_collaboration_model_can_add_further_responsibilities(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            constitution_path = target / "product" / "constitution.json"
            constitution = json.loads(constitution_path.read_text(encoding="utf-8"))
            constitution["collaborationModel"]["userContributions"].append(
                "additional-domain-judgment"
            )
            constitution["collaborationModel"]["agentObligations"].append(
                "alternative-generation"
            )
            constitution_path.write_text(
                json.dumps(constitution, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertNotIn(
            "constitution collaborationModel must preserve user roles and agent obligations",
            report["errors"],
        )

    def test_planned_unauthorized_work_requires_an_explicit_authority_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            official_route_increment = next(
                item
                for item in program["increments"]
                if item["id"]
                == "increment.current-official-route-evaluation-slice"
            )
            live_work = next(
                item
                for item in official_route_increment["workItems"]
                if item["id"] == "work.build-sparse-scorecard-and-close-lifecycle"
            )
            live_work["state"] = "planned"
            live_work["operationIds"] = [
                "external-capability-preview",
                "external-capability-mutation",
                "consumer-projection",
                "rollback",
            ]
            live_work.pop("authorityGate")
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "planned work work.build-sparse-scorecard-and-close-lifecycle requests unauthorized operations without an authorityGate",
            report["errors"],
        )

    def test_unknown_authority_gate_cannot_cover_planned_operations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            official_route_increment = next(
                item
                for item in program["increments"]
                if item["id"]
                == "increment.current-official-route-evaluation-slice"
            )
            live_work = next(
                item
                for item in official_route_increment["workItems"]
                if item["id"] == "work.build-sparse-scorecard-and-close-lifecycle"
            )
            live_work["state"] = "planned"
            live_work["operationIds"] = [
                "external-capability-preview",
                "external-capability-mutation",
                "consumer-projection",
                "rollback",
            ]
            live_work["authorityGate"] = "some-non-empty-text"
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O1"])
        self.assertIn(
            "planned work work.build-sparse-scorecard-and-close-lifecycle authorityGate some-non-empty-text does not cover operations: consumer-projection, external-capability-mutation, external-capability-preview, rollback",
            report["errors"],
        )

    def test_capability_discovery_requires_an_eligible_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = [
                "targeted-capability-discovery",
                "capability-static-review",
                "inactive-exact-acquisition",
            ]
            active_work["authorityGate"] = (
                "complete-portfolio-curation-contract-required"
            )
            active_work.pop("capabilityContext", None)
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            f"active or completed work {active_work['id']} has capability operations without an eligible capabilityContext",
            report["errors"],
        )

    def test_bound_task_context_allows_low_risk_capability_use(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = [
                "installed-authorized-capability-use",
                "coverage-analysis",
            ]
            active_work["capabilityContext"] = {
                "mode": "task-time",
                "taskBinding": "the active source-bound continuation task",
                "gapOrMaterialBenefit": "reduce manual coverage reconciliation",
                "dataBoundary": "repository-local public project data only",
                "authorityBoundary": "no setup or account mutation",
                "verificationSurface": "product verifier and task evidence",
            }
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertTrue(report["criterionStates"]["G1"])
        self.assertNotIn(
            f"active or completed work {active_work['id']} has capability operations without an eligible capabilityContext",
            report["errors"],
        )

    def test_bound_task_gap_allows_targeted_inactive_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = [
                "coverage-analysis",
                "targeted-capability-discovery",
                "capability-static-review",
                "inactive-exact-acquisition",
            ]
            active_work["capabilityContext"] = {
                "mode": "task-time",
                "taskBinding": "the active source-bound task",
                "gapOrMaterialBenefit": "current routes lack the required parser",
                "capabilityGap": "parse the bound format without manual conversion",
                "dataBoundary": "repository-local public fixture only",
                "authorityBoundary": "no install enablement execution or projection",
                "verificationSurface": "fixture parse and cleanup receipt",
                "candidateSourceBoundary": "pinned reviewed upstream sources",
                "inactiveAcquisitionRoot": ".tmp/task-gap-review",
                "reviewCriteria": ["provenance", "license", "security"],
                "cohortStopRule": "stop after five candidates or one adequate route",
            }
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertTrue(report["criterionStates"]["G1"])
        self.assertNotIn(
            f"active or completed work {active_work['id']} has capability operations without an eligible capabilityContext",
            report["errors"],
        )

    def test_planned_live_gate_does_not_authorize_active_operations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            active_increment = next(
                item for item in program["increments"] if item["state"] == "active"
            )
            active_work = next(
                item for item in active_increment["workItems"] if item["state"] == "active"
            )
            active_work["operationIds"] = [
                "external-capability-preview",
                "external-capability-mutation",
                "rollback",
            ]
            active_work["authorityGate"] = (
                "separate-live-capability-lifecycle-authorization-required"
            )
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            "active work requests unauthorized operations: external-capability-mutation, external-capability-preview, rollback",
            report["errors"],
        )

    def test_complete_portfolio_context_allows_inactive_curation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            portfolio_increment = next(
                item
                for item in program["increments"]
                if item["id"] == "increment.capability-lifecycle-product-slice"
            )
            active_work = next(
                item
                for item in portfolio_increment["workItems"]
                if item["id"] == "work.acquire-inactive-portfolio-cohort"
            )
            active_work["operationIds"] = [
                "coverage-analysis",
                "targeted-capability-discovery",
                "capability-static-review",
                "inactive-exact-acquisition",
            ]
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertTrue(report["criterionStates"]["G1"])
        self.assertNotIn(
            f"active or completed work {active_work['id']} has capability operations without an eligible capabilityContext",
            report["errors"],
        )

    def test_portfolio_context_rejects_an_active_authority_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            program_path = target / "product" / "program.json"
            program = json.loads(program_path.read_text(encoding="utf-8"))
            portfolio_increment = next(
                item
                for item in program["increments"]
                if item["id"] == "increment.capability-lifecycle-product-slice"
            )
            active_work = next(
                item
                for item in portfolio_increment["workItems"]
                if item["id"] == "work.acquire-inactive-portfolio-cohort"
            )
            active_work["operationIds"] = ["inactive-exact-acquisition"]
            active_work["capabilityContext"]["allowedOperations"] = [
                "inactive-exact-acquisition"
            ]
            active_work["capabilityContext"]["inactiveAcquisitionRoot"] = (
                "product/evidence/candidates"
            )
            program_path.write_text(
                json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["G1"])
        self.assertIn(
            f"active or completed work {active_work['id']} has capability operations without an eligible capabilityContext",
            report["errors"],
        )

    def test_portfolio_context_rejects_semantic_boundary_conflicts(self) -> None:
        mutations = {
            "wrong task": lambda context: context.__setitem__(
                "taskBinding", "some-other-task"
            ),
            "wrong objective": lambda context: context.__setitem__(
                "coverageObjectiveId", "grow-the-capability-count"
            ),
            "private data": lambda context: context["accountDataPolicy"].__setitem__(
                "privateDataAllowed", True
            ),
            "missing denied operation": lambda context: context.__setitem__(
                "deniedOperations", ["publication"]
            ),
            "unbounded cohort": lambda context: context["cohortPolicy"].__setitem__(
                "maxCandidates", 999
            ),
            "no cleanup": lambda context: context["cohortPolicy"].__setitem__(
                "cleanupRequired", False
            ),
            "shared temporary root": lambda context: context.__setitem__(
                "inactiveAcquisitionRoot", ".tmp/"
            ),
            "missing review criterion": lambda context: context.__setitem__(
                "reviewCriteria", ["license-and-redistribution"]
            ),
            "missing verification requirement": lambda context: context.__setitem__(
                "verificationRequirements", ["static-review-receipt"]
            ),
            "conflicting free prose": lambda context: context.__setitem__(
                "authorityBoundary", "allow all private account execution"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary)
                shutil.copytree(ROOT / "product", target / "product")
                program_path = target / "product" / "program.json"
                program = json.loads(program_path.read_text(encoding="utf-8"))
                portfolio_increment = next(
                    item
                    for item in program["increments"]
                    if item["id"]
                    == "increment.capability-lifecycle-product-slice"
                )
                active_work = next(
                    item
                    for item in portfolio_increment["workItems"]
                    if item["id"] == "work.acquire-inactive-portfolio-cohort"
                )
                mutate(active_work["capabilityContext"])
                program_path.write_text(
                    json.dumps(program, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                result = self.run_verify(target)

                report = json.loads(result.stdout)
                self.assertFalse(report["criterionStates"]["G1"])
                self.assertIn(
                    f"active or completed work {active_work['id']} has capability operations without an eligible capabilityContext",
                    report["errors"],
                )

    def test_o3_verification_remains_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            acceptance_path = target / "product" / "acceptance.json"
            acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
            criterion = next(
                item for item in acceptance["criteria"] if item["id"] == "O3"
            )
            criterion["assessment"] = "verified"
            criterion["evidence"] = [
                "product/evidence/project-reset-real-task-route-2026-08-11.json"
            ]
            acceptance_path.write_text(
                json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O3"])
        self.assertIn(
            "criterion O3 verification remains fail-closed until the real-task evaluation and host lifecycle evidence validator is implemented",
            report["errors"],
        )

    def test_verified_criterion_cannot_use_test_fixture_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            shutil.copytree(ROOT / "product", target / "product")
            evidence_relative = (
                "product/evidence/project-reset-real-task-route-2026-08-11.json"
            )
            evidence_path = target / evidence_relative
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["testFixture"] = True
            evidence_path.write_text(
                json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = self.run_verify(target)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["criterionStates"]["O2"])
        self.assertIn(
            f"verified criterion O2 cannot use test fixture evidence {evidence_relative}",
            report["errors"],
        )


if __name__ == "__main__":
    unittest.main()
