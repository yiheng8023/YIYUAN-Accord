"""Public verifier exercises with a synthetic observer, never product evidence."""

import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch

import tests.product.test_development as development_fixtures
from yiyuan_accord.control import verify_product
from yiyuan_accord.development import DEVELOPMENT_FILE, PLAN_FILE, render_development_plan
from yiyuan_accord.reviews import REVIEW_AXES


FACTS = {"effect": {"total": 130}, "authority": {"inputPreserved": True},
         "poststate": {"actualTotal": 130}, "cleanup": {"taskResidue": []},
         "comparison": {"nativeInterventions": 5, "composedInterventions": 2,
                        "matchedConditions": True}}


class DevelopmentEvidenceTests(unittest.TestCase):
    def test_successor_cannot_promote_retained_cases_even_with_an_observer(self):
        from pathlib import Path
        from yiyuan_accord.admission import assess_development_evidence
        root = Path(__file__).resolve().parents[2]
        current = json.loads((root / DEVELOPMENT_FILE).read_text(encoding='utf-8'))
        # Reproduce the earlier successor snapshot with retained predecessor
        # policy; current v5 declarations now have their own admission path.
        current['acceptance']['admission'] = development_fixtures.historical_development()['acceptance']['admission']
        current['acceptance']['currentQualification'] = 'not-bound-for-v3.3'
        called = []
        result = assess_development_evidence(root, current, lambda request: called.append(request))
        self.assertEqual(result['scope'], 'current-v3.3-admission-not-yet-bound')
        self.assertFalse(result['candidateEligible'])
        self.assertFalse(result['functionalCompletion'])
        self.assertEqual(called, [])

    @classmethod
    def setUpClass(cls):
        # These cases exercise the v4 observer/admission API, not successor
        # acceptance. Retain the exact released files as well as the definition.
        temporary = tempfile.TemporaryDirectory(prefix='accord-v4-admission-')
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name) / 'repository'
        subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(development_fixtures.ROOT), str(cls.root)],
                       check=True, timeout=60)
        subprocess.run(['git', '-C', str(cls.root), 'checkout', '--quiet', '--detach',
                        'cf13486db9e5d0e9a6eef2d9df187d5e0405ee88'], check=True, timeout=60)
        cls.contract = json.loads((cls.root / DEVELOPMENT_FILE).read_text(encoding='utf-8'))
        c = cls.contract
        # Isolate admission regressions from the separately tested production budget.
        c["changeBoundary"]["complexityBudget"]["maxProductCodeAndTestBytes"] += 50000
        c["acceptance"]["admission"] = {
            "schema": "yiyuan-accord-evidence-admission/v3",
            "rule": "Fixture-only independent source contract, not accepted product evidence.",
            "reviewMaxAgeSeconds": 3600, "scopes": [], "cases": [],
            "requiredCoverage": {claim: ["codex", "claude-code"] for claim in (
                "function", "incremental-value", "package-lifecycle")},
            "reviewPolicy": {
                "requiredAxes": list(REVIEW_AXES), "minimumReviewers": 2,
                "independentAxes": [["specification", "implementation"]],
                "contexts": {"isolation": ["context-isolated"],
                             "history": ["zero-inherited-history", "inherited-history-disclosed"],
                             "environment": ["isolated-no-accord", "shared-environment-disclosed"],
                             "accordExposure": ["absent", "present-disclosed"]},
                "rule": "Fixture policy only; independent provenance is a caller responsibility.",
            },
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
        review = {"schema": "yiyuan-accord-development-review-bundle/v1", "subject": request["subject"],
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

    def test_declared_review_duties_can_share_reviewers_with_disclosed_context(self):
        def observer(request):
            result = self.observer(request)
            if request["phase"] == "observe":
                for index, review in enumerate(result["reviewBundle"]["reviews"]):
                    review["reviewerId"] = "fixture-reviewer-" + str(index // 2)
                    if index % 2:
                        review["context"].update(history="inherited-history-disclosed",
                                                environment="shared-environment-disclosed",
                                                accordExposure="present-disclosed")
            return result

        report = verify_product(self.root, evidence=observer)
        self.assertTrue(report["repositoryCandidateReady"], report["errors"])

    def impact_contract(self):
        contract = copy.deepcopy(self.contract)
        policy = contract['acceptance']['admission']
        policy['schema'] = 'yiyuan-accord-evidence-admission/v4'
        policy['requiredCoverage']['incremental-value'] = []
        policy['requiredCoverage']['impact-assessment'] = []
        for rows in (policy['scopes'], policy['cases']):
            for row in rows:
                row['claims'].remove('incremental-value')
        for original in list(policy['cases']):
            case = copy.deepcopy(original)
            case.update(id=original['host'] + '-impact', scope=original['host'] + '-impact',
                        claims=['impact-assessment'])
            case['expected']['comparison'] = {'assessmentCompleted': True, 'observedResult': 'neutral',
                                              'unresolvedMaterialRegression': False}
            policy['cases'].append(case)
            policy['scopes'].append({**{k: copy.deepcopy(case[k]) for k in
                ('id', 'host', 'entry', 'duties', 'qualityAxes', 'scenarios', 'claims', 'conditions')},
                'rule': 'Synthetic bounded impact assessment, not an incremental-benefit witness.'})
            policy['requiredCoverage']['impact-assessment'].append(case['scope'])
        return contract

    def impact_observer(self, request):
        result = self.observer(request)
        if request['phase'] == 'observe':
            for record in result['records']:
                if record['case'].endswith('-impact'):
                    record['facts']['comparison']['value'] = {
                        'assessmentCompleted': True, 'observedResult': 'neutral',
                        'unresolvedMaterialRegression': False}
        return result

    def test_neutral_impact_qualification_cannot_claim_incremental_support(self):
        with self.history():
            self.commit_contract(self.impact_contract())
            report = verify_product(self.root, evidence=self.impact_observer)
        self.assertTrue(report['repositoryCandidateReady'], report['errors'])
        self.assertEqual(report['impactAssessment'], 'complete-for-bound-scopes')
        self.assertEqual(report['incrementalValue'], 'unverified')

    def test_impact_evidence_and_material_regressions_cannot_be_skipped(self):
        for missing in (True, False):
            with self.subTest(missing=missing), self.history():
                self.commit_contract(self.impact_contract())
                def observer(request):
                    result = self.impact_observer(request)
                    if request['phase'] == 'observe':
                        if missing:
                            result['records'] = [r for r in result['records'] if r['case'] != 'codex-impact']
                        else:
                            next(r for r in result['records'] if r['case'] == 'codex-impact')['facts']['comparison']['value']['unresolvedMaterialRegression'] = True
                    return result
                report = verify_product(self.root, evidence=observer)
                self.assertTrue(report['functionalCompletion'], report['errors'])
                self.assertFalse(report['repositoryCandidateReady'])
                self.assertEqual(report['impactAssessment'], 'unverified')

    def test_v4_cannot_drop_required_floors_or_hide_an_active_gain_claim(self):
        from yiyuan_accord.admission import admission_contract_errors
        for claim in ('function', 'package-lifecycle', 'impact-assessment'):
            contract = self.impact_contract()
            contract['acceptance']['admission']['requiredCoverage'][claim] = []
            self.assertTrue(admission_contract_errors(contract), claim)
        contract = self.impact_contract()
        for rows in ('cases', 'scopes'):
            contract['acceptance']['admission'][rows][0]['claims'].append('incremental-value')
        self.assertTrue(admission_contract_errors(contract))
        contract['acceptance']['admission']['requiredCoverage']['incremental-value'] = ['codex']
        self.assertEqual(admission_contract_errors(contract), [])

    def test_declared_gain_still_requires_its_positive_evidence_under_v4(self):
        contract = self.impact_contract()
        policy = contract['acceptance']['admission']
        for rows in ('cases', 'scopes'):
            policy[rows][0]['claims'].append('incremental-value')
        policy['requiredCoverage']['incremental-value'] = ['codex']
        policy['cases'][0]['expected']['comparison']['positiveWitness'] = True
        with self.history():
            self.commit_contract(contract)
            report = verify_product(self.root, evidence=self.impact_observer)
        self.assertFalse(report['repositoryCandidateReady'])
        self.assertEqual(report['incrementalValue'], 'unverified')
        self.assertEqual(report['impactAssessment'], 'complete-for-bound-scopes')

    def test_review_context_cannot_be_both_no_accord_and_accord_exposed(self):
        def observer(request):
            result = self.observer(request)
            if request["phase"] == "observe":
                result["reviewBundle"]["reviews"][0]["context"]["accordExposure"] = "present-disclosed"
            return result

        self.assertFalse(verify_product(self.root, evidence=observer)["repositoryCandidateReady"])

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
        for field in ("rule", "requiredCoverage"):
            with self.subTest(field=field), self.history():
                records = self.capture_records()
                contract = copy.deepcopy(self.contract)
                policy = contract["acceptance"]["admission"]
                if field == "rule":
                    policy[field] += " Revised independent-source requirement."
                else:
                    policy[field]["incremental-value"].append("future-comparison")
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
        self.assertEqual(admission["unboundCoverage"]["incremental-value"], ["claude-code", "codex"])
        self.assertEqual(admission["unboundCoverage"]["package-lifecycle"], ["claude-code", "codex"])

    def scoped_contract(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        policy.update(schema="yiyuan-accord-evidence-admission/v3", requiredCoverage={
            "function": ["codex", "claude-code"],
            "package-lifecycle": ["codex-lifecycle", "claude-code-lifecycle"],
            "incremental-value": ["codex-value"],
        })
        for case, scope in zip(policy["cases"][:], policy["scopes"][:]):
            case["claims"] = scope["claims"] = ["function"]
            for claim, suffix, duty, axis in (
                    ("package-lifecycle", "lifecycle", "package-lifecycle", "recovery-and-lifecycle"),
                    ("incremental-value", "value", "verification-and-value", "user-burden-and-interference")):
                if claim == "incremental-value" and case["host"] != "codex":
                    continue
                scoped = {**copy.deepcopy(scope), "id": case["id"] + "-" + suffix,
                          "claims": [claim], "duties": [duty], "qualityAxes": [axis], "scenarios": []}
                policy["scopes"].append(scoped)
                policy["cases"].append({**copy.deepcopy(case), **{
                    k: copy.deepcopy(scoped[k]) for k in ("id", "duties", "qualityAxes", "scenarios", "claims")},
                    "scope": scoped["id"]})
        return contract

    def test_required_claims_use_bound_scopes_not_a_full_cross_product(self):
        with self.history():
            self.commit_contract(self.scoped_contract())
            report = verify_product(self.root, evidence=self.observer)
        self.assertTrue(report["functionalCompletion"], report["errors"])
        self.assertTrue(report["repositoryCandidateReady"], report["errors"])

    def test_case_failures_do_not_erase_independent_claims(self):
        class Clock(datetime):
            offset = 0

            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) + timedelta(seconds=cls.offset)

        for reason, key in [(r, "claude-code-lifecycle") for r in (
                "effect", "conditions", "recheck", "expired")] + [("effect", "codex"), ("effect", "codex-value")]:
            with self.subTest(reason=reason, case=key), self.history():
                contract = self.scoped_contract()
                if reason == "expired":
                    next(c for c in contract["acceptance"]["admission"]["cases"] if c["id"] == key)["maxAgeSeconds"] = 1
                self.commit_contract(contract)
                Clock.offset = 0

                def observer(request):
                    result = self.observer(request)
                    if request["phase"] == "observe":
                        record = next(r for r in result["records"] if r["case"] == key)
                        if reason == "effect":
                            record["facts"]["effect"]["value"]["total"] = 999
                        elif reason == "conditions":
                            record["conditions"] = {"hostVersion": "changed"}
                    elif reason == "recheck":
                        del result["conditions"][key]
                    elif reason == "expired":
                        Clock.offset = 2
                    return result

                with patch("yiyuan_accord.admission.datetime", Clock):
                    report = verify_product(self.root, evidence=observer)
                self.assertFalse(report["valid"])
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertTrue(report["errors"])
                self.assertEqual(report["functionalCompletion"], key != "codex")
                self.assertEqual(report["currentHostBehavior"], "unverified" if key == "codex" else "verified-for-bound-cases")
                self.assertEqual(report["incrementalValue"], "unverified" if key == "codex-value" else "supported-for-bound-cases")
                self.assertEqual(set(report["evidenceAdmission"]["acceptedCases"]),
                                 {c["id"] for c in contract["acceptance"]["admission"]["cases"]} - {key})

    def test_untrusted_evidence_still_blocks_all_independent_claims(self):
        with self.history():
            self.commit_contract(self.scoped_contract())
            for reason in ("source", "identity", "episode", "review", "recheck"):
                with self.subTest(reason=reason):
                    def observer(request):
                        result = self.observer(request)
                        if request["phase"] == "observe":
                            record = next(r for r in result["records"] if r["case"] == "claude-code-lifecycle")
                            record["facts"]["effect"]["value"]["total"] = 999
                            if reason == "source":
                                record["sourceRef"] = ""
                            elif reason == "identity":
                                record["packageSha256"] = "f" * 64
                            elif reason == "episode":
                                record["facts"]["cleanup"]["episodeId"] = "another"
                            elif reason == "review":
                                result["reviewBundle"]["reviews"] = []
                        elif reason == "recheck":
                            result["observationSha256"] = "f" * 64
                        return result

                    report = verify_product(self.root, evidence=observer)
                    self.assertFalse(report["valid"])
                    self.assertFalse(report["repositoryCandidateReady"])
                    self.assertFalse(report["functionalCompletion"])
                    self.assertEqual(report["incrementalValue"], "unverified")

    def test_removing_scopes_and_cases_leaves_the_required_claims_unbound(self):
        contract = copy.deepcopy(self.contract)
        for field in ("scopes", "cases"):
            contract["acceptance"]["admission"][field].pop(0)
        with self.history():
            self.commit_contract(contract)
            report = verify_product(self.root, evidence=self.observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertFalse(report["functionalCompletion"])
        self.assertEqual(report["evidenceAdmission"]["unboundCoverage"]["function"], ["codex"])

    def test_complementary_hosts_cannot_erase_product_inventory_gaps(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        for field in ("duties", "qualityAxes", "scenarios"):
            values = policy["scopes"][0][field]
            middle = len(values) // 2
            for index, part in enumerate((values[:middle], values[middle:])):
                policy["scopes"][index][field] = policy["cases"][index][field] = part
        with self.history():
            self.commit_contract(contract)
            report = verify_product(self.root, evidence=self.observer)
        self.assertTrue(report["functionalCompletion"], report["errors"])
        self.assertFalse(report["repositoryCandidateReady"])
        for host in ("codex", "claude-code"):
            for field in ("duties", "qualityAxes"):
                self.assertTrue(report["evidenceAdmission"]["productCoverage"][host][field])
            self.assertEqual(report["evidenceAdmission"]["productCoverage"][host]["scenarios"], [])

    def test_unselected_scenario_inventory_does_not_require_a_host_experiment(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        scenario = contract["environmentControl"]["adaptationScenarios"][0]["id"]
        for row in policy["scopes"] + policy["cases"]:
            row["scenarios"].remove(scenario)
        with self.history():
            self.commit_contract(contract)
            report = verify_product(self.root, evidence=self.observer)
        self.assertTrue(report["repositoryCandidateReady"], report["errors"])

    def test_selected_scenario_without_case_evidence_still_blocks_completion(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        scenario = policy["scopes"][0]["scenarios"][0]
        policy["cases"][0]["scenarios"].remove(scenario)
        with self.history():
            self.commit_contract(contract)
            report = verify_product(self.root, evidence=self.observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertFalse(report["functionalCompletion"])
        self.assertEqual(report["evidenceAdmission"]["openCoverage"]["codex"]
                         ["claims"]["function"]["scenarios"], [scenario])

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
            stage = contract["systemOptimization"]["workSequence"][2]
            stage["state"] = "active" if stage["state"] != "active" else "implemented-local-unreleased"
            self.commit_contract(contract)
            report = self.replay(records)
        self.assertTrue(report["repositoryCandidateReady"], report["errors"])

    def test_skill_budget_reuse_preserves_original_record_digests(self):
        for relabel in (False, True):
            with self.subTest(relabel=relabel), self.history():
                records = self.capture_records()
                original = copy.deepcopy(records)
                contract = copy.deepcopy(self.contract)
                for projection in contract["delivery"]["hostProjections"]:
                    projection["maxSkillBytes"] += 1
                self.commit_contract(contract)

                def observer(request):
                    result = self.observer(request)
                    if request["phase"] == "observe":
                        result["records"] = copy.deepcopy(records)
                        for record in result["records"]:
                            current = request["cases"][record["case"]]["definitionSha256"]
                            self.assertNotEqual(record["definitionSha256"], current)
                            if relabel:
                                record["definitionSha256"] = current
                    return result

                report = verify_product(self.root, evidence=observer)
                self.assertEqual(records, original)
                self.assertEqual(report["repositoryCandidateReady"], not relabel, report["errors"])
                self.assertEqual(report["evidenceAdmission"]["acceptedCases"],
                                 [] if relabel else ["claude-code", "codex"])

    def test_invalid_current_skill_budgets_and_insufficient_caps_fail_static_admission(self):
        for value in (None, "13600", True, 0, -1, 1.5, 1, "missing"):
            with self.subTest(cap=value), self.history():
                contract = copy.deepcopy(self.contract)
                contract["delivery"]["hostProjections"][0]["maxSkillBytes"] = value
                if value == "missing":
                    del contract["delivery"]["hostProjections"][0]["maxSkillBytes"]
                self.commit_contract(contract)
                report = verify_product(self.root, evidence=self.observer)
                self.assertFalse(report["contractValid"], report["errors"])
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertTrue(any("Skill" in error and "budget" in error for error in report["errors"]))

    def test_invalid_historical_skill_budget_cannot_be_laundered_by_a_valid_current_cap(self):
        from yiyuan_accord.admission import _definition

        for value in (None, "13600", True, 0, -1, 1.5, "missing"):
            with self.subTest(prior_cap=value), self.history():
                prior = copy.deepcopy(self.contract)
                prior["delivery"]["hostProjections"][0]["maxSkillBytes"] = value
                if value == "missing":
                    del prior["delivery"]["hostProjections"][0]["maxSkillBytes"]
                self.commit_contract(prior)
                revision = self.git("rev-parse", "HEAD")
                self.commit_contract(self.contract)

                def observer(request):
                    result = self.observer(request)
                    if request["phase"] == "observe":
                        record = next(r for r in result["records"] if r["case"] == "codex")
                        case = next(c for c in prior["acceptance"]["admission"]["cases"] if c["id"] == "codex")
                        record.update(evaluatedRevision=revision, definitionSha256=_definition(prior, case))
                    return result

                report = verify_product(self.root, evidence=observer)
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertEqual(report["evidenceAdmission"]["acceptedCases"], ["claude-code"])

    def test_changed_case_definition_invalidates_only_its_dependents(self):
        records = self.capture_records()
        for change in ("oracle", "permission", "outcome", "marker"):
            with self.subTest(change=change), self.history():
                contract = copy.deepcopy(self.contract)
                projection = contract["delivery"]["hostProjections"][0]
                projection["maxSkillBytes"] += 1
                policy = contract["acceptance"]["admission"]
                case = policy["cases"][0]
                if change == "oracle":
                    case["oracle"] += " Revised Codex-specific oracle."
                elif change == "permission":
                    case["conditions"]["effectivePolicy"] = "changed-permission"
                    policy["scopes"][0]["conditions"]["effectivePolicy"] = "changed-permission"
                elif change == "outcome":
                    case["expected"]["effect"]["total"] = 999
                else:
                    projection["requiredSkillMarkers"].append("name: deliver-demand-driven-outcome")
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
        for reason in ("missing", "subject", "stale", "not-independent", "recheck",
                       "one-reviewer", "dependent-axes", "legacy-schema"):
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
                        elif reason == "one-reviewer":
                            for row in review["reviews"]:
                                row["reviewerId"] = "same-native-identity"
                        elif reason == "dependent-axes":
                            review["reviews"][2]["reviewerId"] = review["reviews"][1]["reviewerId"]
                        elif reason == "legacy-schema":
                            review["schema"] = "yiyuan-accord-external-review-bundle/v1"
                    elif reason == "recheck":
                        result["observationSha256"] = "0" * 64
                    return result
                report = verify_product(self.root, evidence=observer)
                self.assertFalse(report["repositoryCandidateReady"])
                self.assertTrue(report["errors"])
        report = verify_product(self.root, review_bundle={"decision": "pass"}, evidence=self.observer)
        self.assertFalse(report["repositoryCandidateReady"])
        self.assertIn("review input differs from the observer-checked bundle", report["errors"])


class CurrentDevelopmentEvidenceTests(unittest.TestCase):
    """Committed synthetic current subjects, never real host or review evidence."""
    git = DevelopmentEvidenceTests.__dict__["git"]
    history = DevelopmentEvidenceTests.history

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="accord-v33-admission-")
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name) / "repository"
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(development_fixtures.ROOT), str(cls.root)],
                       check=True, timeout=60)
        shutil.copytree(development_fixtures.ROOT, cls.root, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", ".tmp", ".remember", "__pycache__", "*.pyc"))
        for locator in ("plugins/yiyuan-accord-claude", ".claude-plugin"):
            if not (development_fixtures.ROOT / locator).exists():
                target = (cls.root / locator).resolve()
                if not target.is_relative_to(cls.root.resolve()):
                    raise ValueError("fixture cleanup escaped the owned repository")
                if target.exists():
                    shutil.rmtree(target)
        cls.contract = json.loads((cls.root / DEVELOPMENT_FILE).read_text(encoding="utf-8"))
        cls.git("add", ".")
        cls.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "--quiet", "--allow-empty", "-m", "Bind synthetic v3.3 admission subject")

    def assess(self, contract=None, observer=None):
        from yiyuan_accord.admission import assess_development_evidence, evidence_subject
        return assess_development_evidence(self.root, contract or self.contract, observer,
                                            subject=evidence_subject(self.root))

    def observer(self, request):
        result = DevelopmentEvidenceTests.observer(self, request)
        if request["phase"] == "observe":
            for record in result["records"]:
                record["facts"] = {name: {"episodeId": record["episodeId"], "value": copy.deepcopy(value)}
                                   for name, value in request["cases"][record["case"]]["case"]["expected"].items()}
        return result

    def commit(self, contract):
        (self.root / DEVELOPMENT_FILE).write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--quiet", "-m", "Revise synthetic current subject")

    def test_current_case_can_be_admitted_without_closing_missing_requirements(self):
        report = self.assess(observer=self.observer)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["acceptedCases"], sorted(case["id"] for case in self.contract["acceptance"]["admission"]["cases"]))
        self.assertFalse(report["functionalCompletion"])
        self.assertFalse(report["candidateEligible"])
        self.assertEqual(set(report["acceptanceRequirements"]), {f"A{i:02}" for i in range(1, 9)})
        self.assertFalse(any(r["complete"] for r in report["acceptanceRequirements"].values()))
        self.assertIn("v33-chatgpt-entry-coverage", report["unboundCoverage"]["function"])
        self.assertNotIn("claude-code", report["productCoverage"])
        self.assertEqual(report["progress"]["coverageVerified"], 3)
        self.assertEqual(report["progress"]["requirementsComplete"], 0)
        # SDK sub-scopes cannot discharge other entries or autonomous adaptation.
        missing = report["acceptanceRequirements"]["A06"]["missingScopes"]
        self.assertIn("v33-codex-lifecycle", missing["package-lifecycle"])
        self.assertIn("v33-environment-adaptation", missing["function"])
        self.assertNotIn("v33-codex-sdk-lifecycle", missing["package-lifecycle"])
        self.assertNotIn("v33-codex-sdk-scoped-exposure", missing["function"])

    def test_current_declaration_without_observer_reports_actual_missing_coverage(self):
        report = self.assess()
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["acceptedCases"], [])
        self.assertFalse(report["candidateEligible"])
        self.assertIn("v33-codex-cli-ordinary-delivery", report["acceptanceRequirements"]["A03"]["missingScopes"]["function"])
        self.assertEqual(report["progress"], {
            "scope": "acceptance-evidence-coverage-not-effort-or-implementation-completion",
            "requirementsTotal": 8, "requirementsComplete": 0,
            "coverageTotal": 17, "coverageDefined": 3, "coverageVerified": 0,
            "coverageScorePercent": 0.0,
            "coverageUnbound": 14, "coverageDefinedButUnverified": 3,
            "casesDefined": 3, "casesAccepted": 0,
        })

    def test_incomplete_mapping_or_old_policy_cannot_dispatch_current_observer(self):
        from yiyuan_accord.admission import admission_contract_errors
        variants = []
        for change in (lambda p: p["acceptanceRequirements"].pop(),
                       lambda p: p["requiredCoverage"]["function"].append("unmapped-scope"),
                       lambda p: p["cases"][0]["oracleFiles"].remove("docs/operations/ACCEPTANCE-v3.3.md"),
                       lambda p: p["cases"][0]["oracleFiles"].remove("docs/operations/PLAN-v3.3.md"),
                       lambda p: p.update(requiredHosts=[])):
            contract = copy.deepcopy(self.contract)
            change(contract["acceptance"]["admission"])
            variants.append(contract)
        for contract in variants:
            self.assertTrue(admission_contract_errors(contract))
            calls = []
            self.assertTrue(self.assess(contract, lambda request: calls.append(request))["errors"])
            self.assertEqual(calls, [])

    def test_old_case_wrong_package_and_changed_conditions_cannot_supply_current_evidence(self):
        for kind in ("old-case", "package", "conditions", "recheck"):
            def observer(request):
                result = self.observer(request)
                if request["phase"] == "observe":
                    record = result["records"][0]
                    if kind == "old-case": record["case"] = "codex-cli-ordinary-entry-dev3-retained-reassessment"
                    if kind == "package": record["packageSha256"] = "0" * 64
                    if kind == "conditions": record["conditions"]["model"] = "unverified-replacement"
                elif kind == "recheck": result["conditions"] = {}
                return result
            with self.subTest(kind=kind):
                report = self.assess(observer=observer)
                self.assertNotIn(self.contract["acceptance"]["admission"]["cases"][0]["id"], report["acceptedCases"])
                self.assertFalse(report["candidateEligible"])
                self.assertTrue(report["errors"])

    def test_changed_acceptance_document_invalidates_retained_current_case(self):
        retained = None
        def capture(request):
            nonlocal retained
            result = self.observer(request)
            if request["phase"] == "observe": retained = copy.deepcopy(result["records"])
            return result
        self.assertTrue(self.assess(observer=capture)["acceptedCases"])
        with self.history():
            path = self.root / "docs/operations/ACCEPTANCE-v3.3.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nChanged synthetic acceptance dependency.\n", encoding="utf-8")
            self.commit(self.contract)
            def replay(request):
                result = self.observer(request)
                if request["phase"] == "observe": result["records"] = retained
                return result
            self.assertEqual(self.assess(observer=replay)["acceptedCases"], [])

    def test_complete_synthetic_coverage_uses_existing_review_and_recheck_chain(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        template = policy["cases"][0]
        policy["cases"], policy["scopes"] = [], []
        for claim, scope_ids in policy["requiredCoverage"].items():
            for scope_id in scope_ids:
                case = copy.deepcopy(template)
                case.update(id="fixture-" + scope_id, scope=scope_id, claims=[claim],
                            duties=[r["id"] for r in contract["acceptance"]["duties"]],
                            qualityAxes=[r["id"] for r in contract["systemOptimization"]["qualityAxes"]])
                if claim == "impact-assessment": case["expected"]["comparison"] = {"fixtureAssessment": True}
                policy["cases"].append(case)
                policy["scopes"].append({**{k: copy.deepcopy(case[k]) for k in
                    ("host", "entry", "duties", "qualityAxes", "scenarios", "claims", "conditions")},
                    "id": scope_id, "rule": "Synthetic scope for algorithm exercise, not actual coverage."})
        with self.history():
            self.commit(contract)
            phases = []
            def observer(request):
                phases.append(request["phase"])
                return self.observer(request)
            report = self.assess(contract, observer)
            self.assertEqual(report["errors"], [])
            self.assertEqual(phases, ["observe", "recheck"])
            self.assertTrue(report["candidateEligible"])
            self.assertTrue(all(r["complete"] for r in report["acceptanceRequirements"].values()))
            self.assertEqual(report["incrementalValue"], "unverified")
            self.assertEqual(report["progress"]["requirementsComplete"], 8)
            self.assertEqual(report["progress"]["coverageVerified"], 17)
            def missing_continuity(request):
                result = self.observer(request)
                if request["phase"] == "observe":
                    result["records"] = [r for r in result["records"]
                                         if r["case"] != "fixture-v33-autonomous-continuity"]
                return result
            report = self.assess(contract, missing_continuity)
            self.assertFalse(report["acceptanceRequirements"]["A05"]["complete"])
            self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])
            self.assertEqual(report["acceptanceRequirements"]["A08"]["blockedBy"], ["A05"])
            self.assertTrue(report["acceptanceRequirements"]["A01"]["complete"])
            self.assertEqual(report["progress"]["requirementsComplete"], 6)
            self.assertEqual(report["progress"]["coverageVerified"], 16)
            def missing(request):
                result = self.observer(request)
                if request["phase"] == "observe": result["records"] = result["records"][:-1]
                return result
            report = self.assess(contract, missing)
            self.assertFalse(report["candidateEligible"])
            self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])
            self.assertTrue(report["acceptanceRequirements"]["A01"]["complete"])

        # Individually valid episodes cannot be unioned into an integrated run.
        integration = next(c for c in policy["cases"] if c["scope"] == "v33-system-integration")
        second = copy.deepcopy(integration)
        second["id"] += "-separate-episode"
        duties = integration["duties"]
        integration["duties"], second["duties"] = duties[:1], duties[1:]
        policy["cases"].append(second)
        with self.history():
            self.commit(contract)
            report = self.assess(contract, self.observer)
            self.assertEqual(report["errors"], [])
            self.assertEqual(len(report["acceptedCases"]), len(policy["cases"]))
            self.assertFalse(report["candidateEligible"])
            self.assertFalse(report["functionalCompletion"])
            self.assertIn("v33-system-integration", report["unjoinedCoverage"]["function"])
            self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])
            def failed_impact(request):
                result = self.observer(request)
                if request["phase"] == "observe":
                    record = next(r for r in result["records"]
                                  if r["case"] == "fixture-v33-system-impact-assessment")
                    record["facts"]["comparison"]["value"]["fixtureAssessment"] = False
                return result
            report = self.assess(contract, failed_impact)
            self.assertFalse(report["candidateEligible"])
            self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])
            self.assertTrue(report["acceptanceRequirements"]["A01"]["complete"])


if __name__ == "__main__":
    unittest.main()
