"""Fast source-contract regressions; none of these tests runs an Agent host."""

import copy
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from yiyuan_accord.development import (
    DEVELOPMENT_FILE, development_contract_errors, development_is_declared,
    verify_development,
)


ROOT = Path(__file__).resolve().parents[2]


class DevelopmentContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / DEVELOPMENT_FILE).read_text(encoding="utf-8"))
        self.tasks = [task["id"] for task in json.loads(
            (ROOT / "evals/golden-tasks.json").read_text(encoding="utf-8")
        )["tasks"]]

    def errors(self, contract):
        return development_contract_errors(contract, self.tasks)

    def test_current_mapping_is_valid_but_not_behavior_or_release(self):
        report = verify_development(ROOT)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["dutiesMapped"], 13)
        self.assertEqual(report["goldenTasksCovered"], len(self.tasks))
        self.assertFalse(report["functionalCompletion"])
        self.assertFalse(report["candidateEligible"])
        self.assertEqual(report["currentHostBehavior"], "unverified")
        self.assertEqual(report["releaseIntent"], "conditional-v3.2-release-after-acceptance")

    def test_conditional_release_requires_commit_push_and_remaining_evidence(self):
        altered = copy.deepcopy(self.contract)
        altered["authority"]["conditionalRelease"]["ready"] = True
        self.assertTrue(self.errors(altered))
        altered = copy.deepcopy(self.contract)
        altered["authority"]["conditionalRelease"]["conditions"] = ["some-check"]
        self.assertTrue(self.errors(altered))

    def test_plan_mapping_cannot_lose_a_function_or_an_acceptance_exit(self):
        for field, value in (("duties", ["unknown-function"]), ("procedure", ""),
                             ("exit", ""), ("state", "published")):
            altered = copy.deepcopy(self.contract)
            altered["systemOptimization"]["workSequence"][0][field] = value
            self.assertTrue(self.errors(altered))
        altered = copy.deepcopy(self.contract)
        for stage in altered["systemOptimization"]["workSequence"]:
            stage["duties"] = [item for item in stage["duties"] if item != "verification-and-value"]
        self.assertTrue(self.errors(altered))

    def test_isolation_is_not_a_clean_host_product_requirement(self):
        for field, value in (("cleanHostRequiredForProduct", True),
                             ("evaluationRule", ""), ("selfUseBoundary", ""),
                             ("arms", []), ("adaptationScenarios", [])):
            altered = copy.deepcopy(self.contract)
            altered["environmentControl"][field] = value
            self.assertTrue(self.errors(altered))

    def test_visible_plan_is_derived_and_stale_progress_is_rejected(self):
        from yiyuan_accord import development
        original = development._bounded_regular_bytes
        expected = development.render_development_plan(self.contract)
        self.assertEqual((ROOT / development.PLAN_FILE).read_text(encoding="utf-8"), expected)

        def stale(path):
            if path == ROOT / development.PLAN_FILE:
                return b"stale progress\n", None
            return original(path)

        with patch.object(development, "_bounded_regular_bytes", side_effect=stale):
            self.assertIn("visible plan is missing or out of sync with the development contract",
                          verify_development(ROOT)["errors"])

    def test_contextual_variation_and_order_are_not_frozen(self):
        altered = copy.deepcopy(self.contract)
        altered["source"]["variables"].append("future-host-surface")
        altered["implementation"]["modes"].reverse()
        altered["acceptance"]["duties"].reverse()
        altered["acceptance"]["duties"][0]["normalEntry"] = "A future supported host's suitable executor."
        self.assertEqual(self.errors(altered), [])

    def test_development_target_does_not_expand_hosts_or_claim_publication(self):
        for field, value in (("targetVersion", "latest"), ("targetVersion", True),
                             ("versionState", "published"),
                             ("existingHosts", ["codex"]),
                             ("existingHosts", ["codex", "claude-code", "new-host"]),
                             ("additionalHostAdaptation", "enabled")):
            with self.subTest(field=field, value=value):
                altered = copy.deepcopy(self.contract)
                altered["cycle"][field] = value
                self.assertTrue(self.errors(altered))

    def test_system_floors_cannot_be_deleted_averaged_or_promoted(self):
        for field, value in (("aggregation", "weighted-average"),
                             ("qualityAxes", self.contract["systemOptimization"]["qualityAxes"][:-1]),
                             ("rule", "")):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.contract)
                altered["systemOptimization"][field] = value
                self.assertTrue(self.errors(altered))
        for field, value in (("id", []), ("id", {}), ("floor", ""),
                             ("assessment", "verified")):
            with self.subTest(field=field, value=value):
                altered = copy.deepcopy(self.contract)
                altered["systemOptimization"]["qualityAxes"][0][field] = value
                self.assertTrue(self.errors(altered))

    def test_local_strategy_cannot_become_a_global_invariant(self):
        altered = copy.deepcopy(self.contract)
        altered["source"]["globalInvariants"].append({
            "id": "always-use-a-hook", "scope": "global", "meaning": "fixture",
        })
        self.assertIn("only the compliance boundary", " ".join(self.errors(altered)))

    def test_supporting_principles_require_their_safety_and_functional_floor(self):
        for field, value in (("class", "global"), ("precondition", ""),
                             ("subtraction", ""), ("restraint", ""),
                             ("fallback", ""), ("gapFilling", "")):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.contract)
                altered["supportingPrinciples"][field] = value
                self.assertTrue(self.errors(altered))

    def test_form_bias_and_cost_before_function_are_rejected(self):
        for field, value in (("runtimeEligible", False), ("formNeutral", False),
                             ("mandatoryMechanisms", ["pure-core"]),
                             ("mandatoryMechanisms", ["synchronous-hook"]),
                             ("selectionOrder", list(reversed(
                                 self.contract["implementation"]["selectionOrder"]))),
                             ("modes", ["accord-contained"])):
            with self.subTest(field=field, value=value):
                altered = copy.deepcopy(self.contract)
                altered["implementation"][field] = value
                self.assertTrue(self.errors(altered))

    def test_accounting_stop_function_outcome_and_value_stay_distinct(self):
        for state in self.contract["source"]["successStates"]:
            with self.subTest(state=state):
                altered = copy.deepcopy(self.contract)
                del altered["source"]["successStates"][state]
                self.assertIn("must remain distinct", " ".join(self.errors(altered)))

    def test_model_routing_binds_both_roles_and_observed_execution(self):
        for field, value in (("roles", ["main-agent"]), ("selection", ""),
                             ("authority", ""), ("nativeReplacement", ""),
                             ("verification", ""), ("failureOracle", "")):
            altered = copy.deepcopy(self.contract)
            altered["implementation"]["modelSelection"][field] = value
            self.assertTrue(self.errors(altered))

    def test_every_inherited_function_requires_a_disposition_even_if_tasks_overlap(self):
        for duty in self.contract["acceptance"]["duties"]:
            with self.subTest(duty=duty["id"]):
                altered = copy.deepcopy(self.contract)
                altered["acceptance"]["duties"] = [
                    item for item in altered["acceptance"]["duties"]
                    if item["id"] != duty["id"]
                ]
                self.assertIn("functional responsibility coverage", " ".join(self.errors(altered)))

    def test_a_function_can_retire_with_a_reason_and_reconciled_acceptance(self):
        altered = copy.deepcopy(self.contract)
        duty = next(item for item in altered["acceptance"]["duties"] if item["id"] == "native-replacement-and-retirement")
        altered["acceptance"]["duties"].remove(duty)
        altered["acceptance"]["retiredDuties"] = [{
            "id": duty["id"], "goldenTasks": duty["goldenTasks"],
            "reason": "Fixture: merge native replacement into context-dependent routing.",
            "acceptanceChange": "Fixture: routing now owns sufficient replacement, failure and cleanup.",
        }]
        for section, field in (("systemOptimization", "workSequence"), ("environmentControl", "adaptationScenarios")):
            for item in altered[section][field]:
                item["duties"] = list(dict.fromkeys(
                    "relations-routing-and-form" if key == duty["id"] else key for key in item["duties"]
                ))
        self.assertEqual(self.errors(altered), [])
        altered["acceptance"]["retiredDuties"][0]["acceptanceChange"] = ""
        self.assertTrue(self.errors(altered))

    def test_entry_effect_failure_and_dependency_are_required(self):
        for field, value in (("normalEntry", ""), ("requiredOutcome", ""),
                             ("failureOracle", ""), ("activationWhen", ""),
                             ("dependsOn", ["missing-duty"]),
                             ("dependsOn", ["goal-authority-correction"]),
                             ("goldenTasks", ["GT-unknown"])):
            with self.subTest(field=field, value=value):
                altered = copy.deepcopy(self.contract)
                altered["acceptance"]["duties"][0][field] = value
                self.assertTrue(self.errors(altered))

    def test_source_checks_cannot_promote_historical_passes_or_scope(self):
        mutations = [
            ("claimCeiling", "functionalCompletion", True),
            ("claimCeiling", "candidateEligible", True),
            ("claimCeiling", "releaseIntent", "publish"),
            ("claimCeiling", "currentHostBehavior", "verified"),
            ("claimCeiling", "incrementalValue", "verified"),
            ("authority", "scope", self.contract["authority"]["scope"] + ["install"]),
        ]
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                altered = copy.deepcopy(self.contract)
                altered[section][field] = value
                self.assertTrue(self.errors(altered))
        for field, value in (("assessment", "verified"), ("evidence", ["historical-PASS"])):
            altered = copy.deepcopy(self.contract)
            altered["acceptance"]["duties"][0][field] = value
            self.assertTrue(self.errors(altered))

    def test_malformed_shapes_fail_without_crashing(self):
        for altered in (None, [], {}, {**self.contract, "source": []},
                        {**self.contract, "predecessorSnapshot": 9}):
            with self.subTest(altered_type=type(altered).__name__):
                self.assertTrue(self.errors(altered))

    def test_missing_or_duplicate_source_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="accord-source-") as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text(f"Read {DEVELOPMENT_FILE}\n", encoding="utf-8")
            self.assertTrue(development_is_declared(root))
            self.assertFalse(verify_development(root)["valid"])
            (root / "product").mkdir()
            (root / DEVELOPMENT_FILE).write_text('{"schema":1,"schema":2}', encoding="utf-8")
            self.assertFalse(verify_development(root)["valid"])

    def test_historical_preimage_cannot_be_rewritten(self):
        from yiyuan_accord import development
        original = development._bounded_regular_bytes

        def changed(path):
            data, state = original(path)
            if path == ROOT / "product/acceptance.json":
                return data + b"\n", state
            return data, state

        with patch.object(development, "_bounded_regular_bytes", side_effect=changed):
            report = verify_development(ROOT)
        self.assertFalse(report["valid"])
        self.assertIn("historical baseline changed: product/acceptance.json", report["errors"])

    def test_unrelated_mutation_is_not_development_authority(self):
        from yiyuan_accord import development
        original = development._bounded_git_bytes

        def changed(root, arguments, *args, **kwargs):
            data = original(root, arguments, *args, **kwargs)
            if arguments[0] == "diff":
                return data + b"unrelated-project/file.json\0"
            return data

        with patch.object(development, "_bounded_git_bytes", side_effect=changed):
            report = verify_development(ROOT)
        self.assertFalse(report["valid"])
        self.assertIn("observed changes exceed the development implementation boundary", report["errors"])

    def test_historical_subject_is_not_promoted_to_current_subject(self):
        from yiyuan_accord.evidence import _behavior_subject_revision_errors
        revision = self.contract["predecessorSnapshot"].split(":", 1)[0]
        task = {"behaviorSubjectFiles": ["CONTEXT.md"]}
        observation = {"evaluatedRevision": revision}
        self.assertTrue(_behavior_subject_revision_errors(
            ROOT, "current", observation, task,
        ))

    def test_cli_exposes_the_narrow_claim_boundary(self):
        result = subprocess.run(
            [sys.executable, "-B", "-m", "yiyuan_accord", "verify-development", "--json"],
            cwd=ROOT, text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["scope"], "development-source-conformance-only")
        self.assertFalse(report["functionalCompletion"])



class DevelopmentDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="accord-delivery-tests-")
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name) / "repository"
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(cls.root)],
                       check=True, timeout=60)
        shutil.copytree(ROOT, cls.root, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
            ".git", ".tmp", ".remember", "__pycache__", "*.pyc"))
        cls.contract = json.loads((cls.root / DEVELOPMENT_FILE).read_text(encoding="utf-8"))

    @contextmanager
    def changed(self, locator, data):
        path = self.root / locator
        old = path.read_bytes() if path.exists() else None
        try:
            if data is None:
                path.unlink()
            else:
                path.write_bytes(data)
            yield
        finally:
            if old is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(old)

    def report(self):
        from yiyuan_accord.control import verify_product
        return verify_product(self.root)

    def test_current_delivery_never_inherits_predecessor_behavior_or_review(self):
        from yiyuan_accord import control
        with patch.object(control, "_validate_acceptance", side_effect=AssertionError("historical replay")):
            report = control.verify_product(self.root, {"decision": "accepted"})
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["release"], self.contract["delivery"]["version"])
        self.assertEqual(report["baselineContractRole"], "historical-predecessor-integrity-only")
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertFalse(report["functionalCompletion"])
        self.assertEqual(report["currentHostBehavior"], "unverified")
        self.assertNotIn("criteria", report)
        for host in report["hostChecks"].values():
            self.assertTrue(host["staticReady"])
            self.assertEqual(host["behaviorEvidenceState"], "unverified")

    def test_static_source_pass_cannot_hide_changed_or_missing_skill(self):
        for projection in self.contract["delivery"]["hostProjections"]:
            locator = projection["skill"]
            original = (self.root / locator).read_bytes()
            for data in (original + b"\nchanged behavior\n", None):
                with self.subTest(host=projection["id"], missing=data is None), self.changed(locator, data):
                    self.assertTrue(verify_development(self.root)["valid"])
                    report = self.report()
                    self.assertFalse(report["valid"])
                    self.assertTrue(any("package" in error for error in report["errors"]))

    def test_admission_consumes_checked_source_not_a_second_worktree_read(self):
        from yiyuan_accord import control
        original = control._read_json

        def read(root, locator, errors):
            if locator in (DEVELOPMENT_FILE, "product/constitution.json", "product/program.json"):
                raise AssertionError("reopened mutable authority after checking its preimage")
            return original(root, locator, errors)

        with patch.object(control, "_read_json", side_effect=read):
            report = self.report()
        self.assertTrue(report["valid"], report["errors"])

    def test_descriptor_cannot_hide_prerequisites_or_claim_effects(self):
        for projection in self.contract["delivery"]["hostProjections"]:
            locator = projection["contract"]
            original = json.loads((self.root / locator).read_text(encoding="utf-8"))
            for field, value in (("ordinaryPrerequisites", ["private-python-engine"]),
                                 ("behaviorEvidenceState", "verified")):
                altered = {**original, field: value}
                with self.subTest(host=projection["id"], field=field), self.changed(
                        locator, json.dumps(altered).encode()):
                    report = self.report()
                    self.assertFalse(report["valid"])
                    self.assertTrue(any("contract does not match" in error for error in report["errors"]))

    def test_manifest_version_and_marketplace_remain_bound(self):
        for locator in (self.contract["delivery"]["hostProjections"][0]["manifest"],
                        ".claude-plugin/marketplace.json"):
            changed = (self.root / locator).read_bytes().replace(
                self.contract["delivery"]["version"].encode(), b"3.1.0")
            with self.changed(locator, changed):
                self.assertFalse(self.report()["valid"])

    def test_current_package_namespace_and_license_guards_are_not_bypassed(self):
        for locator, data, fragment in (
            ("plugins/yiyuan-accord-codex/hidden-state.txt", b"undeclared", "undeclared"),
            ("plugins/yiyuan-accord-claude/LICENSE", b"changed license", "LICENSE"),
        ):
            declaration = copy.deepcopy(self.contract)
            declaration["changeBoundary"]["allowedPaths"].append(locator)
            with self.subTest(locator=locator), self.changed(
                    DEVELOPMENT_FILE, json.dumps(declaration, ensure_ascii=False).encode()), self.changed(locator, data):
                report = self.report()
                self.assertFalse(report["valid"])
                self.assertTrue(any(fragment in error for error in report["errors"]), report["errors"])

    def test_missing_or_malformed_successor_never_falls_back_to_old_passes(self):
        for data in (None, b"{}", b'{"delivery":null}', b'{"schema":1,"schema":2}'):
            with self.subTest(data=data), self.changed(DEVELOPMENT_FILE, data):
                report = self.report()
                self.assertFalse(report["valid"])
                self.assertEqual(report["hostChecks"], {})
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertEqual(report["programStatus"], "in-development")

    def test_invalid_delivery_shape_is_rejected_without_promotion(self):
        from yiyuan_accord.development import development_contract_errors
        tasks = [item["id"] for item in json.loads(
            (self.root / "evals/golden-tasks.json").read_text(encoding="utf-8"))["tasks"]]
        for value in (None, [], {}, {"version": "3.2.0", "hostProjections": []},
                      {**self.contract["delivery"], "hostProjections": [{"id": []}]}):
            changed = {**self.contract, "delivery": value}
            self.assertTrue(development_contract_errors(changed, tasks))

    def test_host_check_keeps_static_claim_and_rejects_unknown_host(self):
        from yiyuan_accord.control import host_check
        for host in ("codex", "claude-code"):
            report = host_check(self.root, host)
            self.assertTrue(report["valid"], report["errors"])
            self.assertEqual(report["claim"], "static host-admission conformance only")
            self.assertEqual(report["behaviorEvidenceState"], "unverified")
        self.assertFalse(host_check(self.root, "future-host")["valid"])


class SnapshotReadOptimizationTests(unittest.TestCase):
    def test_related_documents_use_one_bounded_batch_and_fresh_parsed_objects(self):
        from yiyuan_accord import control
        revision = "2d09d6d089453d165f5bacb6c1f1492ddfc618aa"
        calls, original = [], control._bounded_git_bytes

        def capture(root, arguments, *args, **kwargs):
            calls.append(tuple(arguments))
            return original(root, arguments, *args, **kwargs)

        @control._snapshot_read_scope
        def read_twice():
            first = control._snapshot_documents(ROOT, revision)
            second = control._snapshot_documents(ROOT, revision)
            self.assertEqual(first, second)
            first[0]["purpose"] = "local test mutation"
            self.assertNotEqual(first[0]["purpose"], second[0]["purpose"])

        with patch.object(control, "_bounded_git_bytes", side_effect=capture):
            read_twice()
        self.assertEqual(sum(call[0] == "ls-tree" for call in calls), 1)
        self.assertEqual(sum(call[:2] == ("cat-file", "--batch") for call in calls), 1)
        self.assertIsNone(control._SNAPSHOT_READ_CACHE.get())

    def test_invocations_release_cache_even_after_failure(self):
        from yiyuan_accord import control
        scopes = []

        @control._snapshot_read_scope
        def attempt(fail=False):
            scopes.append(control._SNAPSHOT_READ_CACHE.get())
            if fail:
                raise ValueError("fixture failure")

        with self.assertRaises(ValueError):
            attempt(True)
        self.assertIsNone(control._SNAPSHOT_READ_CACHE.get())
        attempt()
        self.assertIsNot(scopes[0], scopes[1])
        self.assertIsNone(control._SNAPSHOT_READ_CACHE.get())

    def test_worktree_observations_are_not_cached_with_immutable_blobs(self):
        from yiyuan_accord import control

        @control._snapshot_read_scope
        def read_twice():
            return (control._snapshot_json(ROOT, "fixture.json"),
                    control._snapshot_json(ROOT, "fixture.json"))

        with patch.object(control, "_read_json", side_effect=[{"generation": 1}, {"generation": 2}]):
            first, second = read_twice()
        self.assertNotEqual(first, second)
