"""Public verifier exercises with a synthetic observer, never product evidence."""

import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import subprocess
import unittest
from unittest.mock import patch

import tests.product.test_development as development_fixtures
from yiyuan_accord.control import verify_product
from yiyuan_accord.development import DEVELOPMENT_FILE, PLAN_FILE, render_development_plan
from yiyuan_accord.reviews import REVIEW_AXES, REVIEW_BUNDLE_SCHEMA


FACTS = {"effect": {"total": 130}, "authority": {"inputPreserved": True},
         "poststate": {"actualTotal": 130}, "cleanup": {"taskResidue": []},
         "comparison": {"nativeInterventions": 5, "composedInterventions": 2,
                        "matchedConditions": True}}


class DevelopmentEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        development_fixtures.DevelopmentDeliveryTests.setUpClass.__func__(cls)
        c = cls.contract
        # Isolate admission regressions from the separately tested production budget.
        c["changeBoundary"]["complexityBudget"]["maxProductCodeAndTestBytes"] += 50000
        c["acceptance"]["admission"] = {
            "schema": "yiyuan-accord-evidence-admission/v1",
            "rule": "Fixture-only independent source contract, not accepted product evidence.",
            "reviewMaxAgeSeconds": 3600, "scopes": [], "cases": [],
        }
        for projection in c["delivery"]["hostProjections"]:
            entry = next(row for row in c["capabilityMap"]["entrySurfaces"]["rows"]
                         if row["host"] == projection["id"])
            c["acceptance"]["admission"]["cases"].append({
                "id": projection["id"], "scope": projection["id"], "host": projection["id"], "entry": entry["id"],
                "duties": [d["id"] for d in c["acceptance"]["duties"]],
                "qualityAxes": [q["id"] for q in c["systemOptimization"]["qualityAxes"]],
                "scenarios": [s["id"] for s in c["environmentControl"]["adaptationScenarios"]],
                "claims": ["function", "incremental-value", "package-lifecycle"],
                "oracle": "Synthetic 130-total and independent post-state; no real host claim.",
                "oracleFiles": ["tests/product/test_admission.py"],
                "conditions": {"hostVersion": "fixture-1", "effectivePolicy": "fixture-bounded"},
                "maxAgeSeconds": 3600, "expected": copy.deepcopy(FACTS),
            })
            case = c["acceptance"]["admission"]["cases"][-1]
            c["acceptance"]["admission"]["scopes"].append({
                **{k: copy.deepcopy(case[k]) for k in ("id", "host", "entry", "duties", "qualityAxes", "scenarios", "claims", "conditions")},
                "rule": "Synthetic scope only; entry and environment may not borrow another scope's effects.",
            })
        cls.save_contract(c)
        cls.git("add", ".")
        cls.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "--quiet", "-m", "Bind synthetic acceptance subject")

    @classmethod
    def git(cls, *args):
        return subprocess.check_output(["git", "-C", str(cls.root), *args],
                                       stderr=subprocess.DEVNULL, timeout=30).decode().strip()

    @classmethod
    def save_contract(cls, contract):
        (cls.root / DEVELOPMENT_FILE).write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        (cls.root / PLAN_FILE).write_text(render_development_plan(contract), encoding="utf-8")

    @contextmanager
    def history(self):
        """Only the owned, committed fixture history changes; restore its carrier."""
        revision = self.git("rev-parse", "HEAD")
        try:
            yield
        finally:
            self.git("checkout", "--quiet", "--detach", revision)

    def commit_contract(self, contract):
        self.save_contract(contract)
        self.git("add", DEVELOPMENT_FILE, PLAN_FILE)
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--quiet", "-m", "Revise synthetic acceptance subject")

    def observer(self, request):
        stamp = datetime.now(timezone.utc).isoformat()
        if request["phase"] == "recheck":
            return {"subject": request["subject"], "conditions": copy.deepcopy(self.conditions),
                    "observationSha256": request["observationSha256"]}
        self.conditions = {key: copy.deepcopy(value["case"]["conditions"])
                           for key, value in request["cases"].items()}
        review = {"schema": REVIEW_BUNDLE_SCHEMA, "subject": request["subject"],
                  "decision": "pass", "reviews": []}
        for axis in REVIEW_AXES:
            review["reviews"].append({
                "axis": axis, "reviewerId": "fixture-" + axis,
                "context": {"isolation": "context-isolated", "history": "zero-inherited-history",
                            "environment": "isolated-no-accord", "accordExposure": "absent"},
                "subject": request["subject"], "reviewedAt": stamp[:19] + "Z",
                "findings": [], "disposition": "pass", "decision": "pass",
            })
        records = []
        for key, bound in request["cases"].items():
            records.append({
                "case": key, "evaluatedRevision": request["subject"]["revision"],
                "definitionSha256": bound["definitionSha256"],
                "packageSha256": bound["packageSha256"], "observedAt": stamp,
                "conditions": self.conditions[key], "observerId": "fixture-independent",
                "sourceRef": "fixture://episode/" + key, "episodeId": key,
                "facts": {name: {"episodeId": key, "value": copy.deepcopy(value)}
                          for name, value in FACTS.items()},
            })
        return {"records": records, "reviewBundle": review}

    def test_bound_observer_results_are_admitted_but_external_release_gates_remain(self):
        report = verify_product(self.root, evidence=self.observer)
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], ["claude-code", "codex"])
        self.assertTrue(report["repositoryCandidateReady"], report["errors"])
        self.assertTrue(report["functionalCompletion"])
        self.assertEqual(set(report["externalGates"].values()), {"not-evaluated-by-verifier"})
        self.assertIn("caller", report["evidenceAdmission"]["trustBoundary"])

    def test_evidence_that_expires_during_recheck_cannot_qualify(self):
        class Clock(datetime):
            offset = 0

            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) + timedelta(seconds=cls.offset)

        def observer(request):
            result = self.observer(request)
            if request["phase"] == "recheck":
                Clock.offset = 4000
            return result

        with patch("yiyuan_accord.admission.datetime", Clock):
            report = verify_product(self.root, evidence=observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], [])
        self.assertTrue(any("expired" in e for e in report["errors"]))

    def test_static_checks_cannot_be_combined_with_a_later_subject(self):
        original = subprocess.Popen
        switched = False

        def concurrent_commit(args, *pos, **kwargs):
            nonlocal switched
            if not switched and "status" in args and "--porcelain=v1" in args:
                switched = True
                contract = copy.deepcopy(self.contract)
                contract["delivery"]["rule"] += " Changed while static checks were running."
                self.commit_contract(contract)
            return original(args, *pos, **kwargs)

        with self.history(), patch("subprocess.Popen", side_effect=concurrent_commit):
            report = verify_product(self.root, evidence=self.observer)
        self.assertTrue(switched)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertTrue(any("subject" in e for e in report["errors"]), report["errors"])

    def capture_records(self):
        captured = []

        def observer(request):
            result = self.observer(request)
            if request["phase"] == "observe":
                captured.extend(copy.deepcopy(result["records"]))
            return result

        report = verify_product(self.root, evidence=observer)
        self.assertTrue(report["repositoryCandidateReady"], report["errors"])
        return captured

    def replay(self, records):
        def observer(request):
            result = self.observer(request)
            if request["phase"] == "observe":
                result["records"] = copy.deepcopy(records)
            return result
        return verify_product(self.root, evidence=observer)

    def test_shared_admission_rule_change_invalidates_earlier_records(self):
        with self.history():
            records = self.capture_records()
            contract = copy.deepcopy(self.contract)
            contract["acceptance"]["admission"]["rule"] += " Revised independent-source requirement."
            self.commit_contract(contract)
            report = self.replay(records)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], [])

    def test_independent_review_cannot_predate_its_final_subject(self):
        committed = int(self.git("show", "-s", "--format=%ct", "HEAD"))
        before = datetime.fromtimestamp(committed - 1, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        def observer(request):
            result = self.observer(request)
            if request["phase"] == "observe":
                for review in result["reviewBundle"]["reviews"]:
                    review["reviewedAt"] = before
            return result

        report = verify_product(self.root, evidence=observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertTrue(any("review" in e for e in report["errors"]))

    def test_function_evidence_is_not_incremental_value_or_lifecycle_qualification(self):
        contract = copy.deepcopy(self.contract)
        for case in contract["acceptance"]["admission"]["cases"]:
            case["claims"] = ["function"]
            del case["expected"]["comparison"]
        for scope in contract["acceptance"]["admission"]["scopes"]:
            scope["claims"] = ["function"]

        def observer(request):
            result = self.observer(request)
            if request["phase"] == "observe":
                for record in result["records"]:
                    del record["facts"]["comparison"]
            return result

        with self.history():
            self.commit_contract(contract)
            report = verify_product(self.root, evidence=observer)
        self.assertTrue(report["functionalCompletion"], report["errors"])
        self.assertEqual(report["incrementalValue"], "unverified")
        self.assertFalse(report["repositoryCandidateReady"])
        admission = report["evidenceAdmission"]
        self.assertFalse(any(admission["openCoverage"]["codex"]["claims"]["function"].values()))
        self.assertTrue(admission["unboundCoverage"]["codex"]["incremental-value"]["duties"])
        self.assertTrue(admission["unboundCoverage"]["codex"]["package-lifecycle"]["duties"])

    def test_invalid_prior_declaration_cannot_enter_the_revision_cache(self):
        with self.history():
            broken = copy.deepcopy(self.contract)
            del broken["acceptance"]["admission"]["cases"][0]["expected"]["comparison"]
            self.commit_contract(broken)
            old = self.git("rev-parse", "HEAD")
            self.commit_contract(self.contract)

            def observer(request):
                result = self.observer(request)
                if request["phase"] == "observe":
                    for record in result["records"]:
                        record["evaluatedRevision"] = old
                return result

            report = verify_product(self.root, evidence=observer)
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], [])

    def test_record_rejection_preserves_only_the_unaffected_case(self):
        stamp = datetime.now(timezone.utc)
        changes = {
            "wrong-package": lambda r: r.update(packageSha256="f" * 64),
            "wrong-definition": lambda r: r.update(definitionSha256="f" * 64),
            "unknown-revision": lambda r: r.update(evaluatedRevision="0" * 40),
            "future": lambda r: r.update(observedAt=(stamp + timedelta(days=1)).isoformat()),
            "expired": lambda r: r.update(observedAt=(stamp - timedelta(days=1)).isoformat()),
            "conditions": lambda r: r["conditions"].update(hostVersion="different"),
            "no-observer": lambda r: r.update(observerId=""),
            "no-source": lambda r: r.update(sourceRef=""),
            "cross-episode": lambda r: r["facts"]["poststate"].update(episodeId="another"),
            "missing-poststate": lambda r: r["facts"].pop("poststate"),
            "residue": lambda r: r["facts"]["cleanup"].update(value={"taskResidue": ["live-process"]}),
            "false-comparison": lambda r: r["facts"]["comparison"]["value"].update(matchedConditions=False),
        }
        for name, change in changes.items():
            with self.subTest(reason=name):
                def observer(request):
                    result = self.observer(request)
                    if request["phase"] == "observe":
                        change(next(r for r in result["records"] if r["case"] == "codex"))
                    return result
                report = verify_product(self.root, evidence=observer)
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertEqual(report["evidenceAdmission"]["acceptedCases"], ["claude-code"])

    def test_duplicate_and_missing_records_never_close_coverage(self):
        for duplicate in (True, False):
            with self.subTest(duplicate=duplicate):
                def observer(request):
                    result = self.observer(request)
                    if request["phase"] == "observe":
                        if duplicate:
                            result["records"].append(copy.deepcopy(result["records"][0]))
                        else:
                            result["records"].pop(0)
                    return result
                report = verify_product(self.root, evidence=observer)
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertEqual(report["evidenceAdmission"]["acceptedCases"], ["claude-code"])
                self.assertTrue(report["evidenceAdmission"]["openCoverage"]["codex"]["claims"]["function"]["duties"])

    def test_current_condition_drift_does_not_reuse_beginning_conditions(self):
        def observer(request):
            result = self.observer(request)
            if request["phase"] == "recheck":
                del result["conditions"]["codex"]
            return result
        report = verify_product(self.root, evidence=observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], ["claude-code"])

    def test_nonsemantic_progress_can_reuse_a_but_final_review_binds_b(self):
        with self.history():
            records = self.capture_records()
            contract = copy.deepcopy(self.contract)
            contract["systemOptimization"]["workSequence"][2]["state"] = "implemented-local-unreleased"
            self.commit_contract(contract)
            report = self.replay(records)
        self.assertTrue(report["repositoryCandidateReady"], report["errors"])

    def test_changed_case_definition_invalidates_only_its_dependents(self):
        with self.history():
            records = self.capture_records()
            contract = copy.deepcopy(self.contract)
            contract["acceptance"]["admission"]["cases"][0]["oracle"] += " Revised Codex-specific oracle."
            self.commit_contract(contract)
            report = self.replay(records)
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], ["claude-code"])
        self.assertFalse(report["repositoryCandidateReady"])

    def test_complementary_entries_cannot_be_combined_into_complete_coverage(self):
        self.assert_incomplete_scopes("cx-desktop", "fixture-1")

    def test_complementary_environments_cannot_be_combined_into_complete_coverage(self):
        self.assert_incomplete_scopes("cx-cli", "fixture-2")

    def assert_incomplete_scopes(self, entry, version):
        contract = copy.deepcopy(self.contract)
        cases = contract["acceptance"]["admission"]["cases"]
        other = copy.deepcopy(cases[0])
        other.update(id="codex-other", scope="codex-other", entry=entry)
        other["conditions"]["hostVersion"] = version
        scope = copy.deepcopy(contract["acceptance"]["admission"]["scopes"][0])
        scope.update(id=other["scope"], entry=other["entry"])
        scope["conditions"]["hostVersion"] = version
        contract["acceptance"]["admission"]["scopes"].append(scope)
        middle = len(other["duties"]) // 2
        cases[0]["duties"] = other["duties"][:middle]
        other["duties"] = other["duties"][middle:]
        cases.append(other)
        with self.history():
            self.commit_contract(contract)
            report = verify_product(self.root, evidence=self.observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertFalse(report["functionalCompletion"])
        self.assertTrue(report["evidenceAdmission"]["openCoverage"]["codex"]["claims"]["function"]["duties"])
        self.assertTrue(report["evidenceAdmission"]["openCoverage"]["codex-other"]["claims"]["function"]["duties"])

    def test_changed_oracle_file_prevents_reusing_old_observations(self):
        with self.history():
            records = self.capture_records()
            oracle = self.root / "tests/product/test_admission.py"
            oracle.write_bytes(oracle.read_bytes() + b"\n# Revised fixture oracle.\n")
            self.git("add", "tests/product/test_admission.py")
            self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                     "commit", "--quiet", "-m", "Change fixture oracle")
            report = self.replay(records)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], [])

    def test_oracle_paths_are_literal_even_when_they_contain_glob_characters(self):
        with self.history():
            path = "tests/product/fixture[1].py"
            oracle = self.root / path
            oracle.write_text("# Initial synthetic oracle.\n", encoding="utf-8")
            contract = copy.deepcopy(self.contract)
            contract["changeBoundary"]["allowedPaths"].append(path)
            # This fixture owns one extra file; the production ceiling is unchanged.
            contract["changeBoundary"]["complexityBudget"]["maxTrackedFiles"] += 1
            for case in contract["acceptance"]["admission"]["cases"]:
                case["oracleFiles"] = [path]
            self.git("add", path)
            self.commit_contract(contract)
            records = self.capture_records()
            oracle.write_text("# Changed synthetic oracle.\n", encoding="utf-8")
            self.git("add", path)
            self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                     "commit", "--quiet", "-m", "Change literal oracle")
            report = self.replay(records)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertEqual(report["evidenceAdmission"]["acceptedCases"], [])

    def test_unavailable_or_malformed_observer_is_redacted_and_fails_closed(self):
        secret_marker = "fixture-private-do-not-echo"

        def unavailable(request):
            raise RuntimeError(secret_marker)

        for observer in (unavailable, lambda request: {}, lambda request: {"secret": secret_marker},
                         lambda request: {"records": [], "reviewBundle": float("nan")}):
            with self.subTest(observer=observer):
                report = verify_product(self.root, evidence=observer)
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertNotIn(secret_marker, json.dumps(report))
                self.assertEqual(report["evidenceAdmission"]["acceptedCases"], [])

    def test_review_must_be_current_independent_and_observer_checked(self):
        for reason in ("missing", "subject", "stale", "not-independent", "recheck"):
            with self.subTest(reason=reason):
                def observer(request):
                    result = self.observer(request)
                    if request["phase"] == "observe":
                        review = result["reviewBundle"]
                        if reason == "missing":
                            review["reviews"].pop()
                        elif reason == "subject":
                            review["subject"] = {"revision": "0" * 40, "tree": "0" * 40}
                        elif reason == "stale":
                            review["reviews"][0]["reviewedAt"] = "2000-01-01T00:00:00Z"
                        elif reason == "not-independent":
                            review["reviews"][0]["context"]["accordExposure"] = "present"
                    elif reason == "recheck":
                        result["observationSha256"] = "0" * 64
                    return result
                report = verify_product(self.root, evidence=observer)
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertTrue(report["errors"])
        report = verify_product(self.root, review_bundle={"decision": "pass"}, evidence=self.observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertIn("review input differs from the observer-checked bundle", report["errors"])


if __name__ == "__main__":
    unittest.main()
