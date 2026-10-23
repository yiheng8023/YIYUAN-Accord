"""Public verifier exercises with a synthetic observer, never product evidence."""

import copy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest
from unittest.mock import patch

import tests.product.test_development as development_fixtures
from yiyuan_accord.control import verify_product
from yiyuan_accord.development import (
    DEVELOPMENT_FILE, PLAN_FILE, development_observations, render_development_plan,
)
from yiyuan_accord.reviews import REVIEW_AXES


FACTS = {"effect": {"total": 130}, "authority": {"inputPreserved": True},
         "poststate": {"actualTotal": 130}, "cleanup": {"taskResidue": []},
         "comparison": {"nativeInterventions": 5, "composedInterventions": 2,
                        "matchedConditions": True}}


class OwnedGitFixtureRoutingTests(unittest.TestCase):
    def test_fixture_mutations_and_history_restore_ignore_other_owned_repository(self):
        import os
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            protected, target = root / 'protected', root / 'target'
            helper = development_fixtures.WorkingTreeOverlayTests()
            clean = helper.protected_repository(protected)
            target.mkdir()
            subprocess.run(['git', 'init', '--quiet', str(target)], env=clean, check=True, timeout=30)
            def snapshot():
                paths = [protected / name for name in ('.git/config', '.git/index', '.git/HEAD', 'keep.txt', 'retired.txt')]
                paths.extend(path for path in (protected / '.git/refs').rglob('*') if path.is_file())
                return {path.relative_to(protected).as_posix(): path.read_bytes() for path in paths}
            before = snapshot()
            historical = development_fixtures.historical_development()
            class OwnedFixture(DevelopmentEvidenceTests):
                pass
            OwnedFixture.root = target
            (target / 'payload.txt').write_text('first')
            with patch.dict(os.environ, {**clean, 'GIT_DIR': str(protected / '.git'), 'GIT_WORK_TREE': str(protected),
                                        'GIT_INDEX_FILE': str(protected / '.git/index')}, clear=True):
                self.assertEqual(development_fixtures.historical_development(), historical)
                OwnedFixture.git('add', '.')
                OwnedFixture.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                 'commit', '--quiet', '-m', 'Own first revision')
                self.assertEqual(snapshot(), before)
                first = OwnedFixture.git('rev-parse', 'HEAD')
                (target / 'payload.txt').write_text('second')
                OwnedFixture.git('add', '.')
                OwnedFixture.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                                 'commit', '--quiet', '-m', 'Own second revision')
                second = OwnedFixture.git('rev-parse', 'HEAD')
                with OwnedFixture().history():
                    OwnedFixture.git('checkout', '--quiet', '--detach', first)
                    self.assertEqual((target / 'payload.txt').read_text(), 'first')
                self.assertEqual(OwnedFixture.git('rev-parse', 'HEAD'), second)
                self.assertEqual((target / 'payload.txt').read_text(), 'second')
                manifest = target / 'package/.codex-plugin/plugin.json'
                manifest.parent.mkdir(parents=True)
                manifest.write_bytes(b'{}\n')
                contract = {'delivery': {'hostProjections': [{'manifest': 'package/.codex-plugin/plugin.json'}]}}
                CurrentDevelopmentEvidenceTests.update_package_identity(OwnedFixture(), contract)
                self.assertEqual(contract['delivery']['hostProjections'][0]['packageSha256'],
                                 'ea6b7a8fe16ae7fdae84480c37180ebd111fb9a62e07f3090003efbf4c1904bd')
            self.assertEqual(snapshot(), before)


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
                       env=development_fixtures.owned_git_environment(), check=True, timeout=60)
        subprocess.run(['git', '-C', str(cls.root), 'checkout', '--quiet', '--detach',
                        'cf13486db9e5d0e9a6eef2d9df187d5e0405ee88'],
                       env=development_fixtures.owned_git_environment(), check=True, timeout=60)
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
                                       env=development_fixtures.owned_git_environment(),
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
        self.assertEqual(report["evidenceAdmission"]["caseRejections"], {})
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
        self.assertEqual(report["evidenceAdmission"]["caseRejections"]["codex"], ["observation-expired"])

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
            "conditions": lambda r: r["conditions"].update(hostVersion="fixture-private-condition"),
            "no-observer": lambda r: r.update(observerId=""),
            "no-source": lambda r: r.update(sourceRef=""),
            "cross-episode": lambda r: r["facts"]["poststate"].update(episodeId="another"),
            "missing-poststate": lambda r: r["facts"].pop("poststate"),
            "residue": lambda r: r["facts"]["cleanup"].update(value={"taskResidue": ["live-process"]}),
            "false-comparison": lambda r: r["facts"]["comparison"]["value"].update(matchedConditions=False),
        }
        reasons = {
            "wrong-package": "record-declared-package-mismatch",
            "wrong-definition": "record-definition-mismatch",
            "unknown-revision": "source-evidence-unavailable",
            "future": "observation-time-invalid",
            "expired": "observation-predates-candidate",
            "conditions": "execution-conditions-mismatch",
            "no-observer": "provenance-missing", "no-source": "provenance-missing",
            "cross-episode": "facet-episode-mismatch", "missing-poststate": "facet-shape-invalid",
            "residue": "consequence-mismatch", "false-comparison": "consequence-mismatch",
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
                self.assertIn(reasons[name], report["evidenceAdmission"]["caseRejections"]["codex"])
                self.assertNotIn("claude-code", report["evidenceAdmission"]["caseRejections"])
                self.assertNotIn("fixture-private-condition", json.dumps(report))

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
        self.assertEqual(report["evidenceAdmission"]["caseRejections"]["codex"], ["current-conditions-changed"])

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
        self.assertEqual(report["evidenceAdmission"]["caseRejections"]["codex"], ["execution-dependency-changed"])

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

    def test_legacy_observation_envelopes_retain_one_megabyte_limit(self):
        from yiyuan_accord.admission import assess_development_evidence, evidence_subject
        for schema in ('v3', 'v4'):
            with self.subTest(schema=schema), self.history():
                contract = copy.deepcopy(self.contract) if schema == 'v3' else self.impact_contract()
                if schema == 'v4':
                    self.commit_contract(contract)
                phases = []
                sizes = {}
                def observer(request):
                    phases.append(request['phase'])
                    result = self.observer(request) if schema == 'v3' else self.impact_observer(request)
                    if request['phase'] == 'observe':
                        finding = {'severity': 'P3', 'disposition': 'pass'}
                        encoded = lambda value: json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                           ensure_ascii=False).encode('utf-8')
                        count = (1_000_001 - len(encoded(result))) // (len(encoded(finding)) + 1) + 1
                        result['reviewBundle']['reviews'][0]['findings'] = [finding] * count
                        sizes.update(total=len(encoded(result)), review=len(encoded(result['reviewBundle'])))
                    return result
                report = assess_development_evidence(self.root, contract, observer,
                                                      subject=evidence_subject(self.root))
                self.assertGreater(sizes['total'], 1_000_000)
                self.assertLess(sizes['review'], 1_000_000)
                self.assertEqual(phases, ['observe'])
                self.assertEqual(report['acceptedCases'], [])
                self.assertTrue(report['errors'])

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

    @classmethod
    def historical_contract(cls):
        return json.loads(subprocess.check_output(['git', '-C', str(cls.root), 'show',
            '062157711d6aa2cdab274757d54f0a73423d9201:product/development.json'],
            env=development_fixtures.owned_git_environment(), timeout=30))

    def historical_fixture_case(self, case_id):
        # Only the isolated synthetic subject uses an ended sample. It never
        # returns to the repository's active acceptance gates.
        contract = copy.deepcopy(self.contract)
        case = copy.deepcopy(next(c for c in self.historical_contract()['acceptance']['admission']['cases']
                                  if c['id'] == case_id))
        scope = next(s for s in contract['acceptance']['admission']['scopes'] if s['id'] == case['scope'])
        # Current required semantics win only in this synthetic subject;
        # the exact historical case remains unchanged in its Git snapshot.
        case['conditions'] = {**case['conditions'], **copy.deepcopy(scope['conditions'])}
        contract['acceptance']['admission']['cases'].append(case)
        return contract, case

    def historical_mapping_fixture(self):
        contract = copy.deepcopy(self.contract)
        policy = contract['acceptance']['admission']
        policy['cases'] = copy.deepcopy(self.historical_contract()['acceptance']['admission']['cases'])
        for case in policy['cases']:
            scope = next(s for s in policy['scopes'] if s['id'] == case['scope'])
            case['conditions'] = {**case['conditions'], **copy.deepcopy(scope['conditions'])}
        return contract

    def assert_preserved_requirements_with_current_outcomes(self, prior):
        from yiyuan_accord.admission import admission_contract_errors
        policy = self.contract['acceptance']['admission']
        self.assertEqual(policy['requiredCoverage'], prior['requiredCoverage'])
        self.assertEqual([{key: row[key] for key in ('id', 'requiredCoverage')}
                          for row in policy['acceptanceRequirements']], prior['acceptanceRequirements'])
        self.assertEqual([(row['id'], len(row['outcomeObligations']))
                          for row in policy['acceptanceRequirements']],
                         [('A01', 6), ('A02', 17), ('A03', 4), ('A04', 4),
                          ('A05', 6), ('A06', 5), ('A07', 6), ('A08', 4)])
        self.assertEqual(admission_contract_errors(self.contract), [])
        for index in range(8):
            missing = copy.deepcopy(self.contract)
            del missing['acceptance']['admission']['acceptanceRequirements'][index]['outcomeObligations']
            self.assertIn('current acceptance must bind nonempty source outcome obligations for every requirement',
                          admission_contract_errors(missing))

    def test_ended_current_instances_leave_gates_with_exact_history_and_scope_floors(self):
        from yiyuan_accord.admission import _definition
        old = self.historical_contract()
        record = development_observations(self.root, self.contract)[0]
        policy = self.contract['acceptance']['admission']
        self.assertEqual(record['historicalSource']['observationCount'], len(old['developmentObservations']))
        self.assertEqual(record['historicalSource']['observationsSha256'], hashlib.sha256(json.dumps(
            old['developmentObservations'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest())
        for declaration in record['declarations']:
            case = next(c for c in old['acceptance']['admission']['cases'] if c['id'] == declaration['caseId'])
            self.assertNotIn(case['id'], {c['id'] for c in policy['cases']})
            self.assertEqual(declaration['caseObjectSha256'], hashlib.sha256(json.dumps(
                case, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest())
            self.assertEqual(declaration['definitionSha256'], _definition(old, case))
        self.assert_preserved_requirements_with_current_outcomes(old['acceptance']['admission'])
        for scope, prior in zip(policy['scopes'], old['acceptance']['admission']['scopes']):
            for key in ('id', 'host', 'entry', 'duties', 'qualityAxes', 'scenarios', 'claims'):
                self.assertEqual(scope[key], prior[key])
        self.assertFalse(self.assess()['candidateEligible'])

    def test_new_coordination_conditions_do_not_force_old_sample_but_keep_control(self):
        from yiyuan_accord.admission import _conditions_match
        for sid in ('v33-goal-authority-correction', 'v33-paused-work-recovery'):
            required = next(s['conditions'] for s in self.contract['acceptance']['admission']['scopes'] if s['id'] == sid)
            actual = {**required, 'codexVersion': 'new-supported-host', 'model': 'current-model',
                      'reasoning': 'current-option', 'userConfigBaselineSha256': 'a' * 64,
                      'input': 'different ordinary input', 'turnCount': 2}
            self.assertTrue(_conditions_match(actual, required))
            self.assertFalse(_conditions_match({**actual, 'goalModeActive': True}, required))
            actual.pop('userControl')
            self.assertFalse(_conditions_match(actual, required))

    def test_current_mode_catalog_rejects_missing_duplicate_and_invalid_declarations(self):
        from yiyuan_accord.admission import _entry_modes
        surfaces = self.contract["capabilityMap"]["entrySurfaces"]
        catalog = surfaces["modeCatalog"]
        dispositions = next(row for row in self.contract["acceptance"]["admission"]["scopes"]
                            if row["id"] == "v33-openai-entry-applicability")["conditions"]["entryDispositions"]
        self.assertEqual(set(_entry_modes(dispositions, catalog)), set(catalog))
        for change in (lambda x:x.pop("chatgpt-web"),
                       lambda x:x.update({"chatgpt-web": []}),
                       lambda x:x.update({"chatgpt-web": ["chat", "chat"]}),
                       lambda x:x.update({"chatgpt-web": [False]})):
            altered = copy.deepcopy(catalog); change(altered)
            with self.assertRaises(ValueError):
                _entry_modes(dispositions, altered)

    def test_historical_mode_catalog_keeps_its_original_reading(self):
        from yiyuan_accord.admission import _entry_modes
        historical = json.loads(subprocess.check_output(
            ["git", "show", "dce00cc9dc7a1224c027a85f7f2b88c824139e35:product/development.json"],
            cwd=Path(__file__).resolve().parents[2],
            env=development_fixtures.owned_git_environment(), timeout=30))
        dispositions = next(row for row in historical["acceptance"]["admission"]["scopes"]
                            if row["id"] == "v33-openai-entry-applicability")["conditions"]["entryDispositions"]
        modes = _entry_modes(dispositions)
        self.assertEqual(set(modes["chatgpt-desktop"]), {"chat", "work-local", "work-cloud", "remote"})
        self.assertEqual(modes["chatgpt-desktop"]["work-cloud"]["status"], "deferred")

    def test_mode_presentation_order_reuses_meaning_without_rewriting_identity(self):
        from yiyuan_accord.admission import _definition, _reuse_definition, admission_contract_errors
        reordered = copy.deepcopy(self.contract)
        reordered["capabilityMap"]["entrySurfaces"]["modeCatalog"]["chatgpt-desktop"].reverse()
        self.assertEqual(admission_contract_errors(reordered), [])
        for case in self.contract["acceptance"]["admission"]["cases"]:
            if "subjectEntries" not in case:
                continue
            original = _definition(self.contract, case)
            self.assertNotEqual(original, _definition(reordered, case))
            self.assertEqual(_reuse_definition(self.contract, case), _reuse_definition(reordered, case))
            self.assertEqual(original, _definition(self.contract, case))

    def test_substantive_mode_membership_change_never_reuses_old_meaning(self):
        from yiyuan_accord.admission import _reuse_definition
        for operation in (lambda values: values.remove("remote"), lambda values: values.append("new-mode")):
            changed = copy.deepcopy(self.contract)
            operation(changed["capabilityMap"]["entrySurfaces"]["modeCatalog"]["chatgpt-desktop"])
            for case in self.contract["acceptance"]["admission"]["cases"]:
                if "subjectEntries" in case:
                    self.assertNotEqual(_reuse_definition(self.contract, case), _reuse_definition(changed, case))

    def test_reference_set_order_reuses_without_mutating_original_declarations(self):
        from yiyuan_accord.admission import _definition, _reuse_definition, admission_contract_errors
        original = copy.deepcopy(self.contract)
        for key in ("duties", "qualityAxes", "scenarios", "claims", "subjectEntries"):
            reordered = copy.deepcopy(self.contract)
            for group in ("scopes", "cases"):
                for row in reordered["acceptance"]["admission"][group]:
                    if key in row:
                        row[key].reverse()
            self.assertEqual(admission_contract_errors(reordered), [])
            for old, new in zip(self.contract["acceptance"]["admission"]["cases"],
                                reordered["acceptance"]["admission"]["cases"]):
                with self.subTest(field=key, case=old["id"]):
                    stored = _definition(self.contract, old)
                    self.assertEqual(_reuse_definition(self.contract, old), _reuse_definition(reordered, new))
                    self.assertEqual(stored, _definition(self.contract, old))
        self.assertEqual(self.contract, original)

    def test_reference_membership_and_execution_order_still_change_reuse(self):
        from yiyuan_accord.admission import _reuse_definition, admission_contract_errors
        for key in ("duties", "qualityAxes", "scenarios"):
            changed = copy.deepcopy(self.contract)
            scope = changed["acceptance"]["admission"]["scopes"][0]
            removed = scope[key].pop()
            for row in changed["acceptance"]["admission"]["cases"]:
                if row["scope"] == scope["id"]:
                    row[key] = [value for value in row[key] if value != removed]
            self.assertEqual(admission_contract_errors(changed), [])
            for old, new in zip(self.contract["acceptance"]["admission"]["cases"],
                                changed["acceptance"]["admission"]["cases"]):
                if old["scope"] == scope["id"]:
                    with self.subTest(field=key, case=old["id"]):
                        self.assertNotEqual(_reuse_definition(self.contract, old), _reuse_definition(changed, new))
        first = copy.deepcopy(self.contract["acceptance"]["admission"]["cases"][0])
        first["expected"]["effect"]["orderedActions"] = ["read", "write"]
        reversed_actions = copy.deepcopy(first)
        reversed_actions["expected"]["effect"]["orderedActions"].reverse()
        self.assertNotEqual(_reuse_definition(self.contract, first), _reuse_definition(self.contract, reversed_actions))

    def test_coverage_set_and_requirement_row_order_preserve_reuse(self):
        from yiyuan_accord.admission import _definition, _reuse_definition, admission_contract_errors
        original = copy.deepcopy(self.contract)
        for kind in ("coverage", "requirement-rows", "requirement-coverage"):
            reordered = copy.deepcopy(self.contract)
            policy = reordered["acceptance"]["admission"]
            if kind == "coverage":
                for ids in policy["requiredCoverage"].values():
                    ids.reverse()
            elif kind == "requirement-rows":
                policy["acceptanceRequirements"].reverse()
            else:
                for row in policy["acceptanceRequirements"]:
                    for ids in row["requiredCoverage"].values():
                        ids.reverse()
            self.assertEqual(admission_contract_errors(reordered), [])
            for case in self.contract["acceptance"]["admission"]["cases"]:
                with self.subTest(kind=kind, case=case["id"]):
                    stored = _definition(self.contract, case)
                    self.assertEqual(_reuse_definition(self.contract, case), _reuse_definition(reordered, case))
                    self.assertEqual(stored, _definition(self.contract, case))
        self.assertEqual(self.contract, original)

    def test_requirement_to_scope_mapping_change_remains_material(self):
        from yiyuan_accord.admission import _reuse_definition, admission_contract_errors
        changed = copy.deepcopy(self.contract)
        requirements = changed["acceptance"]["admission"]["acceptanceRequirements"]
        # Move one actual scope between requirements while preserving global
        # membership. A mapping change must not be mistaken for presentation.
        source, target, claim, scope = next(
            (a, b, claim, scope)
            for a in requirements for b in requirements if a is not b
            for claim, ids in a["requiredCoverage"].items() if len(ids) > 1
            for scope in ids if claim in b["requiredCoverage"] and scope not in b["requiredCoverage"][claim])
        source["requiredCoverage"][claim].remove(scope)
        target["requiredCoverage"][claim].append(scope)
        self.assertIn('outcome obligations must bind unique IDs, source criteria, declared scope claims and true consequence leaves',
                      admission_contract_errors(changed))
        # A consistent synthetic criterion relocation moves its exact obligations
        # too. It changes meaning, without granting any real case admission.
        moved = [row for row in source['outcomeObligations']
                 if row['scope'] == scope and row['claim'] == claim]
        self.assertTrue(moved)
        source['outcomeObligations'] = [row for row in source['outcomeObligations'] if row not in moved]
        for row in moved:
            row['source']['anchor'] = target['id']
        target['outcomeObligations'].extend(moved)
        self.assertEqual(admission_contract_errors(changed), [])
        for case in self.contract["acceptance"]["admission"]["cases"]:
            self.assertNotEqual(_reuse_definition(self.contract, case), _reuse_definition(changed, case))

    git = DevelopmentEvidenceTests.__dict__["git"]
    history = DevelopmentEvidenceTests.history

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory(prefix="accord-v33-admission-")
        cls.addClassCleanup(temporary.cleanup)
        cls.root = Path(temporary.name) / "repository"
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", str(development_fixtures.ROOT), str(cls.root)],
                       env=development_fixtures.owned_git_environment(), check=True, timeout=60)
        development_fixtures.overlay_current_tree(cls.root)
        cls.contract = json.loads((cls.root / DEVELOPMENT_FILE).read_text(encoding="utf-8"))
        # Synthetic development sources stay explicit after the real candidate freezes.
        # Individual final-promotion tests perform their own directional transition.
        if cls.contract['status'] == 'candidate-frozen':
            from yiyuan_accord.guardrails import package_sha256
            cls.contract['status'] = 'in-development'
            cls.contract['cycle']['versionState'] = 'development-target-not-published'
            version = cls.contract['cycle']['targetVersion'] + '-dev.1'
            cls.contract['delivery']['version'] = version
            for projection in cls.contract['delivery']['hostProjections']:
                manifest = cls.root / projection['manifest']
                value = json.loads(manifest.read_text(encoding='utf-8'))
                value['version'] = projection['packageVersion'] = version
                manifest.write_text(json.dumps(value), encoding='utf-8')
                # Include newly declared package files before hashing this synthetic subject.
                cls.git('add', '--', manifest.parent.parent.relative_to(cls.root).as_posix())
                projection['packageSha256'] = package_sha256(cls.root, cls.git(
                    'ls-files', '--', manifest.parent.parent.relative_to(cls.root).as_posix()).splitlines())
            (cls.root / DEVELOPMENT_FILE).write_text(json.dumps(cls.contract), encoding='utf-8')
        cls.git("add", ".")
        cls.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "--quiet", "--allow-empty", "-m", "Bind synthetic v3.3 admission subject")

    def assess(self, contract=None, observer=None):
        from yiyuan_accord.admission import assess_development_evidence, evidence_subject
        return assess_development_evidence(self.root, contract or self.contract, observer,
                                            subject=evidence_subject(self.root))

    def execution_fixture(self):
        contract, case = self.historical_fixture_case("v33-paused-work-recovery-01")
        execution = {key: case["conditions"][key] for key in (
            "entryProtocol", "model", "reasoning", "windowsSandbox", "codexVersion")}
        execution.update(host=case["host"], entry=case["entry"],
                         runner="scripts/observe_codex_entry.py",
                         caseFile="product/cases/coordination-v3.3.json",
                         hookMode="native-package-hooks", timeoutSeconds=600,
                         turnTimeoutSeconds=180, recoveryTimeoutSeconds=20,
                         usageCaps={"outputTokens": 14000}, usageScope="synthetic test only")
        fixture = subprocess.check_output(["git", "-C", str(self.root), "show",
                                            "HEAD:" + execution["caseFile"]],
                                            env=development_fixtures.owned_git_environment(), timeout=30)
        execution["caseSha256"] = hashlib.sha256(fixture).hexdigest()
        case["conditions"]["execution"] = copy.deepcopy(execution)
        from yiyuan_accord.admission import _revision_package_snapshot
        snapshot = _revision_package_snapshot(self.root, self.git("rev-parse", "HEAD"),
            "plugins/yiyuan-accord-codex", {"calls": 0, "files": 0, "bytes": 0})
        files = {path.removeprefix("plugins/yiyuan-accord-codex/"): hashlib.sha256(raw).hexdigest()
                 for path, raw in snapshot["files"].items()}
        return contract, case, execution, files

    def test_execution_prebinding_uses_committed_identity_without_admitting_facts(self):
        from yiyuan_accord.admission import bind_evidence_execution, _definition
        with self.history():
            contract, case, execution, files = self.execution_fixture()
            with self.assertRaisesRegex(ValueError, "execution case was not prebound"):
                bind_evidence_execution(self.root, case["id"], execution, files)
            incomplete = copy.deepcopy(contract)
            next(c for c in incomplete['acceptance']['admission']['cases']
                 if c['id'] == case['id'])['conditions'].pop('execution')
            self.commit(incomplete)
            with self.assertRaisesRegex(ValueError, "prebound case conditions"):
                bind_evidence_execution(self.root, case["id"], execution, files)
            self.commit(contract)
            bound = bind_evidence_execution(self.root, case["id"], execution, files)
            self.assertEqual(bound["subject"]["revision"], self.git("rev-parse", "HEAD"))
            self.assertEqual(bound["definitionSha256"], _definition(contract, case))
            self.assertEqual(bound["execution"], execution)
            self.assertIn("goalModeActive", bound["remainingConditions"])
            self.assertFalse({"observedAt", "facts", "reviewBundle", "acceptedCases"} & bound.keys())

    def test_execution_prebinding_rejects_drift_and_uncommitted_declarations(self):
        from yiyuan_accord.admission import bind_evidence_execution
        with self.history():
            contract, case, execution, files = self.execution_fixture()
            self.commit(contract)
            for key, value in (("model", "other"), ("hookMode", "installed-plugin"),
                               ("timeoutSeconds", 900), ("usageCaps", {"outputTokens": 99999})):
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, "prebound case conditions"):
                    bind_evidence_execution(self.root, case["id"], {**execution, key: value}, files)
            with self.assertRaisesRegex(ValueError, "package differs"):
                bind_evidence_execution(self.root, case["id"], execution, {**files, "extra.txt": "0" * 64})
            dirty = self.root / "uncommitted-execution.txt"
            dirty.write_text("no dispatch")
            try:
                with self.assertRaisesRegex(ValueError, "clean committed"):
                    bind_evidence_execution(self.root, case["id"], execution, files)
            finally:
                dirty.unlink()

    def test_composed_execution_keeps_observer_and_worker_separate_and_rejects_drift(self):
        from yiyuan_accord.admission import bind_evidence_execution
        with self.history():
            contract, child, worker, files = self.execution_fixture()
            scope = next(row for row in contract["acceptance"]["admission"]["scopes"]
                         if row["id"] == "v33-dynamic-model-routing")
            parent = copy.deepcopy(child)
            parent.update({key: copy.deepcopy(scope[key]) for key in
                           ("host", "entry", "duties", "qualityAxes", "scenarios", "claims")})
            parent.update(id="synthetic-composition", scope=scope["id"])
            execution = {"host": scope["host"], "entry": scope["entry"],
                         "coordinator": {"role": "observer", "sourceRef": "synthetic-only"},
                         "worker": worker, **{key: worker[key] for key in ("runner", "caseFile", "caseSha256")}}
            parent["conditions"] = {**copy.deepcopy(scope["conditions"]), "execution": copy.deepcopy(execution)}
            contract["acceptance"]["admission"]["cases"].append(parent)
            self.commit(contract)
            bound = bind_evidence_execution(self.root, parent["id"], execution, files)
            self.assertEqual(bound["execution"]["entry"], "cx-desktop")
            self.assertEqual(bound["execution"]["worker"]["entry"], "cx-cli")
            self.assertFalse({"facts", "acceptedCases", "observedAt"} & bound.keys())
            for key, value in (("entry", "cx-desktop"), ("model", "other-model"),
                               ("windowsSandbox", "unelevated"), ("caseSha256", "f" * 64),
                               ("recoveryTimeoutSeconds", 99), ("usageCaps", {"outputTokens": 99999})):
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, "prebound case conditions"):
                    changed = copy.deepcopy(execution)
                    changed["worker"][key] = value
                    bind_evidence_execution(self.root, parent["id"], changed, files)
            with self.assertRaisesRegex(ValueError, "package differs"):
                bind_evidence_execution(self.root, parent["id"], execution, {**files, "foreign.txt": "0" * 64})
            dirty = self.root / "uncommitted-execution.txt"
            dirty.write_text("no dispatch")
            try:
                with self.assertRaisesRegex(ValueError, "clean committed"):
                    bind_evidence_execution(self.root, parent["id"], execution, files)
            finally:
                dirty.unlink()

    def test_execution_prebinding_rejects_conflicting_or_uncommitted_fixture_identity(self):
        from yiyuan_accord.admission import bind_evidence_execution
        with self.history():
            for key, value, reason in (("model", "other", "contradicts"),
                                       ("entry", "cx-sdk", "host entry"),
                                       ("caseSha256", "0" * 64, "fixture differs"),
                                       ("caseFile", "README.md", "oracle dependencies")):
                contract, case, execution, files = self.execution_fixture()
                execution[key] = value
                case["conditions"]["execution"] = copy.deepcopy(execution)
                self.commit(contract)
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, reason):
                    bind_evidence_execution(self.root, case["id"], execution, files)

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

    def sparse_contract(self):
        contract, case = self.historical_fixture_case("v33-goal-authority-correction-01")
        projection = contract["delivery"]["hostProjections"][0]
        case["packageFiles"] = [
            projection["manifest"],
            projection["contract"],
            projection["skill"],
            "plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs",
            "plugins/yiyuan-accord-codex/skills/maintain-task-continuity/SKILL.md",
        ]
        return contract, case

    def update_package_identity(self, contract):
        projection = contract["delivery"]["hostProjections"][0]
        package = Path(projection["manifest"]).parents[1].as_posix()
        self.git("add", package)
        listing = subprocess.check_output(
            ["git", "-C", str(self.root), "ls-files", "-s", "-z", "--", package],
            env=development_fixtures.owned_git_environment(), timeout=30)
        digest = hashlib.sha256()
        for row in (item for item in listing.split(b"\0") if item):
            metadata, locator = row.split(b"\t", 1)
            blob = metadata.split()[1].decode("ascii")
            digest.update(locator)
            digest.update(b"\0")
            digest.update(hashlib.sha256(subprocess.check_output(
                ["git", "-C", str(self.root), "cat-file", "blob", blob],
                env=development_fixtures.owned_git_environment(), timeout=30)).digest())
        projection["packageSha256"] = digest.hexdigest()

    def capture(self):
        records = None
        def observer(request):
            nonlocal records
            result = self.observer(request)
            if request["phase"] == "observe":
                records = copy.deepcopy(result["records"])
            return result
        return observer, lambda: records

    def replay(self, records, mutate=None):
        def observer(request):
            result = self.observer(request)
            if request["phase"] == "observe":
                result["records"] = copy.deepcopy(records)
                if mutate is not None:
                    mutate(result["records"], request)
            return result
        return observer

    def test_current_historical_facts_keep_time_with_fresh_applicability_review(self):
        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) + timedelta(days=2)

        retained = []
        def observer(request):
            result = self.observer(request)
            if request['phase'] == 'observe':
                retained.extend(copy.deepcopy(result['records']))
                for review in result['reviewBundle']['reviews']:
                    review['reviewedAt'] = Later.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            return result

        with patch('yiyuan_accord.admission.datetime', Later):
            report = self.assess(observer=observer)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['acceptedCases'], sorted(row['case'] for row in retained))
        self.assertTrue(all(datetime.fromisoformat(row['observedAt']) < Later.now(timezone.utc)
                            - timedelta(days=1) for row in retained))

    def impact_fixture(self, parent_case=None, *, final=False):
        """Synthetic original qualification and changed full dependency closure."""
        from yiyuan_accord import admission as a
        if parent_case is None:
            contract, case = self.historical_fixture_case("v33-goal-authority-correction-01")
        else:
            contract = copy.deepcopy(self.contract)
            case = next(row for row in contract["acceptance"]["admission"]["cases"] if row["id"] == parent_case)
        if final:
            # Exercise the retained 3.3.0 transition, not a new patch promotion.
            contract['cycle']['targetVersion'] = contract['authority']['conditionalRelease']['target'] = '3.3.0'
            contract['delivery']['version'] = contract['delivery']['hostProjections'][0]['packageVersion'] = '3.3.0-dev.1'
            manifest = self.root / contract['delivery']['hostProjections'][0]['manifest']
            contents = json.loads(manifest.read_text(encoding='utf-8'))
            contents['version'] = contract['delivery']['version']
            manifest.write_text(json.dumps(contents), encoding='utf-8')
            self.update_package_identity(contract)
        self.commit(contract)
        capture, records = self.capture()
        original_report = self.assess(contract, capture)
        self.assertIn(case["id"], original_report["acceptedCases"], original_report)
        record = next(row for row in records() if row["case"] == case["id"])
        original_subject = a.evidence_subject(self.root)
        host = contract["delivery"]["hostProjections"][0]
        package = Path(host["manifest"]).parents[1].as_posix()
        helper = self.root / package / "runtime/task-checkpoint.cjs"
        helper.write_bytes(helper.read_bytes() + b"\n// synthetic current impact\n")
        (self.root / "yiyuan_accord/impact_fixture.py").write_text("# never imported\n")
        adjudicator = self.root / "yiyuan_accord/admission.py"
        adjudicator.write_bytes(adjudicator.read_bytes() + b"\n# synthetic adjudicator change\n")
        old_version = contract['delivery']['version']
        version = "3.3.0" if final else a._normalized_cache_version(old_version) + "+codex.20990101000000"
        contract["delivery"]["version"] = host["packageVersion"] = version
        manifest = self.root / host["manifest"]
        if final:
            contract['status'] = 'candidate-frozen'
            contract['cycle']['versionState'] = 'final-candidate-not-publication-proof'
            manifest.write_bytes(manifest.read_bytes().replace(json.dumps(old_version).encode(),
                                                               json.dumps(version).encode(), 1))
        else:
            contents = json.loads(manifest.read_text(encoding="utf-8"))
            contents["version"] = version
            manifest.write_text(json.dumps(contents), encoding="utf-8")
        if 'packageFiles' in case:
            contents = json.loads(manifest.read_text(encoding='utf-8'))
            contents['description'] += ' Synthetic current applicability UI.'
            manifest.write_text(json.dumps(contents), encoding='utf-8')
            helper.chmod(helper.stat().st_mode | 0o111)
        self.update_package_identity(contract)
        if 'packageFiles' in case:
            self.git('update-index', '--chmod=+x', '--', helper.relative_to(self.root).as_posix())
        self.commit(contract)
        state = {}

        def observer(request):
            result = self.observer(request)
            if request["phase"] == "recheck":
                material = state["material"]
                result["currentApplicability"] = {case["id"]: {
                    "evidenceSha256": a._hash({k: v for k, v in material.items() if k != "reviewBundle"}),
                    "current": copy.deepcopy(material["current"]),
                    "conditionBindings": copy.deepcopy(material["conditionBindings"])}}
                return result
            result["records"] = [copy.deepcopy(record)]
            material = {"schema": "yiyuan-accord-current-applicability/v1",
                "original": {"subject": original_subject, "recordSha256": a._hash(record),
                    **{k: record[k] for k in ("definitionSha256", "packageSha256", "episodeId")},
                    "qualification": {"case": case["id"], "scope": case["scope"], "claim": "function",
                        "episodeId": record["episodeId"], "recordSha256": a._hash(record),
                        "subject": original_subject, "decision": "accepted", "stage": "final-case-qualification",
                        "qualifiedAt": datetime.now(timezone.utc).isoformat(), "sources": ["qualification"],
                        "finalOutcomeSources": ["final"], "knownFailuresAndLimits": [{"sources": ["final"],
                            "disposition": "outside-case-claim", "basis": "Synthetic unrelated closeout limit retained.",
                            "resolutionSources": []}]}},
                "current": {"subject": request["subject"], "definitionSha256": a._definition(contract, case),
                    "packageSha256": host["packageSha256"], "context": {key: ["actual"] for key in
                        ("configuration", "authority", "helpers", "continuingState")}},
                "sources": {key: {"sourceRef": "fixture://" + key, "sha256": digest, "kind": kind}
                    for key, digest, kind in (("qualification", a._hash(original_report), "original-qualification"),
                        ("final", a._hash({"syntheticFinalCaseAccepted": case["id"], "otherCloseoutHeld": True}), "original-final-outcome"),
                        ("actual", a._hash({"syntheticCurrentPoststate": True}), "current-observation"),
                        ("analysis", a._hash({"syntheticAnalysis": True}), "source-analysis"))},
                "differences": [{**row, "role": "synthetic execution/adjudicator",
                    "impact": "current-consequence-supported", "basis": "Synthetic current effect reviewed.",
                    "sources": ["analysis"], "currentConsequences": ["actual"]}
                    for row in a._impact_differences(self.root, record["evaluatedRevision"],
                        request["subject"]["revision"], (package, package), case["oracleFiles"],
                        {"calls": 0, "files": 0, "bytes": 0})],
                "conditionBindings": [{"pointer": pointer, "originalValue": value,
                    "responsibility": "continuing-applicability", "currentValue": copy.deepcopy(value),
                    "basis": "Synthetic still-required condition independently observed.", "sources": ["actual"]}
                    for pointer, value in a._condition_leaves(case["conditions"]).items()]}
            for key in ("host", "entry"):
                material["current"]["context"][key] = {"value": case[key], "sources": ["actual"]}
            review = copy.deepcopy(result["reviewBundle"])
            review["schema"] = "yiyuan-accord-development-impact-review-bundle/v1"
            digest = a._hash(material)
            review["evidenceSha256"] = digest
            for row in review["reviews"]:
                row["evidenceSha256"] = digest
            material["reviewBundle"] = review
            state["material"] = material
            result["currentApplicability"] = {case["id"]: material}
            return result
        return contract, case, record, observer

    def parent_fixture(self, case_id, *, final=False):
        from yiyuan_accord import admission as a
        contract, case, record, base = self.impact_fixture(case_id, final=final)
        state = {}
        def observer(request):
            result = base(request)
            if request["phase"] == "recheck":
                result.pop("currentApplicability")
                material = state["material"]
                result["parentApplicability"] = {case_id: {
                    "evidenceSha256": a._hash({k: v for k, v in material.items() if k != "reviewBundle"}),
                    **{k: copy.deepcopy(material[k]) for k in
                       ("current", "conditionBindings", "predicateBindings", "roles", "relationships")}}}
                return result
            material = result.pop("currentApplicability")[case_id]
            material["schema"] = "yiyuan-accord-parent-applicability/v1"
            material["original"]["qualification"]["claim"] = case["claims"][0]
            entries = case.get("subjectEntries", case["conditions"].get("subjectEntries", [case["entry"]]))
            modes = case["conditions"].get("selectedModes", {key: [name for name, value in
                row.get("modes", {}).items() if value["status"] == "selected"] for key, row in
                case["conditions"].get("entryDispositions", {}).items()})
            identities = [(entry, mode) for entry in entries for mode in [None, *modes.get(entry, [])]]
            material["roles"] = [{"id": str(index), "entry": entry, "mode": mode,
                "originalActor": "synthetic-old-" + entry, "currentActor": "synthetic-current-" + entry,
                "responsibility": "continuing-applicability", "originalSources": ["final"],
                "currentSources": ["actual"], "basis": "Synthetic observed actor relationship."}
                for index, (entry, mode) in enumerate(identities)]
            bindings = []
            for pointer, value in a._condition_leaves(case["expected"]).items():
                parts = pointer.split("/")
                entry = next((entry for entry in entries if entry in parts), entries[0])
                mode = parts[parts.index("modes") + 1] if "modes" in parts else None
                bindings.append({"pointer": pointer, "role": str(identities.index((entry, mode))),
                    "responsibility": "continuing-applicability", "originalValue": value, "currentValue": copy.deepcopy(value),
                    "originalSources": ["final"], "currentSources": ["actual"],
                    "basis": "Synthetic full original predicate applies."})
            material["predicateBindings"] = bindings
            for row in material["conditionBindings"]:
                row.update(role="0", originalSources=["final"])
            material["relationships"] = [{"kind": kind, "episodeId": record["episodeId"],
                "fromRole": "0", "toRole": "0", "fromEvent": "event/" + str(index),
                "toEvent": "event/" + str(index + 1), "sources": ["final"],
                "basis": "Synthetic actual parent event relation, not a union of child PASSes."}
                for index, kind in enumerate(("authority", "single-writer", "action", "feedback", "adoption", "poststate"))]
            self.sign_parent_material(material)
            state["material"] = material
            result["parentApplicability"] = {case_id: material}
            return result
        return contract, case, record, observer

    @staticmethod
    def sign_parent_material(material):
        from yiyuan_accord.admission import _hash
        digest = _hash({k: v for k, v in material.items() if k != "reviewBundle"})
        material["reviewBundle"]["evidenceSha256"] = digest
        for row in material["reviewBundle"]["reviews"]:
            row["evidenceSha256"] = digest

    @staticmethod
    def canonical_bytes(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=False, allow_nan=False).encode('utf-8')

    def test_final_promotion_comparison_is_directional_and_preserves_all_case_meaning(self):
        from yiyuan_accord import admission as a
        original = copy.deepcopy(self.contract)
        # This historical branch remains specifically 3.3.0 development -> final.
        original['cycle']['targetVersion'] = original['authority']['conditionalRelease']['target'] = '3.3.0'
        original['delivery']['version'] = original['delivery']['hostProjections'][0]['packageVersion'] = '3.3.0-dev.1'
        final = copy.deepcopy(original)
        final['status'] = 'candidate-frozen'
        final['cycle']['versionState'] = 'final-candidate-not-publication-proof'
        final['delivery']['version'] = '3.3.0'
        final['delivery']['hostProjections'][0]['packageVersion'] = '3.3.0'
        before = self.canonical_bytes(original)
        cases = original['acceptance']['admission']['cases']
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertEqual(a._impact_comparison(original, case, final, case),
                                 'authorized-v33-final-candidate')
                self.assertNotEqual(a._impact_definition(original, case), a._impact_definition(final, case))
                self.assertIsNone(a._impact_comparison(final, case, original, case))
        # This committed 3930000-byte source allocation predates the current
        # 3973000 allocation. Source maintenance must not rewrite case clocks
        # or add an equality gate absent from the stored definition.
        retained = copy.deepcopy(original)
        retained['changeBoundary']['complexityBudget'] = json.loads(self.git('show',
            'e3d67d20238a105341a763a4f30ef443c80269dd:product/development.json'))['changeBoundary']['complexityBudget']
        self.assertEqual(retained['changeBoundary']['complexityBudget']['maxProductCodeAndTestBytes'], 3930000)
        self.assertNotEqual(retained['changeBoundary']['complexityBudget'], final['changeBoundary']['complexityBudget'])
        for case in cases:
            with self.subTest(source_budget_evolution=case['id']):
                self.assertEqual(a._definition(retained, case), a._definition(original, case))
                self.assertEqual(a._impact_comparison(retained, case, final, case),
                                 'authorized-v33-final-candidate')
        bounded = next(case for case in cases if case['id'] == 'v33-resource-pressure-current-capacity-01')
        changed_case = copy.deepcopy(bounded)
        changed_case['conditions']['execution']['limits']['wholeWorkSeconds'] += 1
        self.assertIsNone(a._impact_comparison(retained, bounded, final, changed_case))
        case = cases[0]
        for version in ('3.3.0-dev.1', '3.3.0-dev.17+codex.20261021000000'):
            changed = copy.deepcopy(original)
            changed['delivery']['version'] = changed['delivery']['hostProjections'][0]['packageVersion'] = version
            with self.subTest(legal_development=version):
                self.assertEqual(a._impact_comparison(changed, case, final, case),
                                 'authorized-v33-final-candidate')
        for field in ('authority', 'claimCeiling'):
            changed = copy.deepcopy(original)
            candidate = copy.deepcopy(final)
            changed[field] = candidate[field] = None
            with self.subTest(malformed=field):
                self.assertIsNone(a._impact_comparison(changed, case, candidate, case))
        for field, value in (('productId', 'other-product'), ('claimCeiling', {
                **original['claimCeiling'], 'currentHostBehavior': 'verified'})):
            changed = copy.deepcopy(original)
            candidate = copy.deepcopy(final)
            changed[field] = candidate[field] = value
            with self.subTest(invalid_both=field):
                self.assertIsNone(a._impact_comparison(changed, case, candidate, case))
        for kind in ('target', 'cycle', 'cycle-field', 'authority', 'ready', 'state', 'status',
                     'final-build', 'projection', 'claims', 'ceiling', 'quality', 'source',
                     'condition', 'expected', 'oracle', 'entry', 'scope'):
            changed, target = copy.deepcopy(final), copy.deepcopy(case)
            if kind == 'target': changed['cycle']['targetVersion'] = '3.4.0'
            elif kind == 'cycle': changed['cycle']['id'] = 'other-cycle'
            elif kind == 'cycle-field': changed['cycle']['sourceDecision'] += ' Changed.'
            elif kind == 'authority': changed['authority']['conditionalRelease']['decision'] = 'not-authorized'
            elif kind == 'ready': changed['authority']['conditionalRelease']['ready'] = True
            elif kind == 'state': changed['cycle']['versionState'] = 'development-target-not-published'
            elif kind == 'status': changed['status'] = 'in-development'
            elif kind == 'final-build': changed['delivery']['version'] = '3.3.0+codex.20261021000000'
            elif kind == 'projection': changed['delivery']['hostProjections'][0]['packageVersion'] = '3.4.0'
            elif kind == 'claims': target['claims'].append('incremental-value')
            elif kind == 'ceiling': changed['claimCeiling']['candidateEligible'] = True
            elif kind == 'quality': changed['systemOptimization']['qualityAxes'][0]['rule'] = 'Changed quality rule.'
            elif kind == 'source': changed['source']['rule'] = 'Changed source.'
            elif kind == 'condition': target['conditions']['other'] = True
            elif kind == 'expected': target['expected']['other'] = True
            elif kind == 'oracle': target['oracleFiles'].append('other.py')
            elif kind == 'entry': target['entry'] = 'other-entry'
            else: target['scope'] = 'other-scope'
            with self.subTest(kind=kind):
                self.assertIsNone(a._impact_comparison(original, case, changed, target))
        for version in ('3.3.0-rc.1', '3.3.0-beta.1', '3.3.0-dev.0', '3.3.0-dev.1+other.1',
                        '3.3.0-dev.1+codex.123', '3.4.0-dev.1'):
            changed = copy.deepcopy(original)
            changed['delivery']['version'] = version
            changed['delivery']['hostProjections'][0]['packageVersion'] = version
            with self.subTest(original_version=version):
                self.assertIsNone(a._impact_comparison(changed, case, final, case))
        self.assertEqual(self.canonical_bytes(original), before)

    def test_final_promotion_current_and_whole_host_parent_require_complete_material(self):
        for parent in (False, True):
            with self.subTest(parent=parent), self.history():
                if parent:
                    contract, case, record, base = self.parent_fixture(
                        'v33-whole-host-lifecycle-current-development-02', final=True)
                else:
                    contract, case, record, base = self.impact_fixture(final=True)
                frozen = self.canonical_bytes(record)
                report = self.assess(contract, base)
                self.assertEqual(report['errors'], [], report['caseRejections'])
                self.assertEqual(report['acceptedCases'], [case['id']])
                mapping = 'currentParentApplicability' if parent else 'currentApplicability'
                material_map = 'parentApplicability' if parent else 'currentApplicability'
                comparison = report[mapping][case['id']]['definitionComparison']
                self.assertEqual(comparison['kind'], 'authorized-v33-final-candidate')
                self.assertEqual(comparison['currentVersion'], '3.3.0')
                self.assertEqual(self.canonical_bytes(record), frozen)
                self.assertNotIn(case['id'], self.assess(contract, self.replay([record]))['acceptedCases'])
                for kind in ('original-record', 'provenance', 'material-hash', 'old-package', 'stale-review',
                             'missing-condition', 'missing-delta', 'recheck'):
                    def observer(request):
                        result = base(request)
                        if request['phase'] == 'observe':
                            material = result[material_map][case['id']]
                            if kind == 'original-record': result['records'][0]['definitionSha256'] = '0' * 64
                            elif kind == 'provenance': result['records'][0]['sourceRef'] = ''
                            elif kind == 'material-hash': material['reviewBundle']['evidenceSha256'] = '0' * 64
                            elif kind == 'old-package': material['original']['packageSha256'] = '0' * 64
                            elif kind == 'stale-review':
                                for row in material['reviewBundle']['reviews']:
                                    row['reviewedAt'] = '2000-01-01T00:00:00Z'
                            elif kind == 'missing-condition': material['conditionBindings'].pop()
                            elif kind == 'missing-delta': material['differences'].pop()
                            if kind != 'material-hash': self.sign_parent_material(material)
                        elif kind == 'recheck':
                            result[material_map][case['id']]['current']['packageSha256'] = '0' * 64
                        return result
                    with self.subTest(rejection=kind):
                        rejected = self.assess(contract, observer)
                        self.assertEqual(rejected['acceptedCases'], [])
                        self.assertIn(case['id'], rejected['caseRejections'])
                self.assertEqual(self.canonical_bytes(record), frozen)

    def test_sparse_material_reassesses_selected_runtime_metadata_and_modes(self):
        from yiyuan_accord import admission as a
        for case_id in ('v33-resource-pressure-current-capacity-01',
                        'v33-environment-adaptation-current-capacity-01'):
            for final in (False, True):
                with self.subTest(case=case_id, final=final), self.history():
                    contract, case, record, base = self.impact_fixture(case_id, final=final)
                    frozen = self.canonical_bytes(record)
                    selected = 'plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs'
                    observed = {}
                    def observer(request):
                        result = base(request)
                        if request['phase'] == 'observe': observed.update(copy.deepcopy(result))
                        return result
                    report = self.assess(contract, observer)
                    self.assertEqual(report['errors'], [], report['caseRejections'])
                    self.assertEqual(report['acceptedCases'], [case_id])
                    self.assertNotIn(case_id, report['packageReuse'])
                    supported = report['currentApplicability'][case_id]
                    self.assertIn('selected-package-dependency-changed', supported['reconciledReasons'])
                    rows = observed['currentApplicability'][case_id]['differences']
                    runtime = next(row for row in rows if row['path'] == selected)
                    self.assertNotEqual(runtime['oldSha256'], runtime['newSha256'])
                    self.assertNotEqual(runtime['oldMode'], runtime['newMode'])
                    self.assertTrue(any(row['path'].endswith('/plugin.json') for row in rows))
                    self.assertEqual(self.canonical_bytes(record), frozen)
                    self.assertNotIn(case_id, self.assess(contract, self.replay([record]))['acceptedCases'])
                    if not final:
                        continue
                    for kind in ('selected-delta', 'selected-sha', 'condition', 'review-digest', 'candidate-review', 'recheck'):
                        def invalid(request):
                            result = base(request)
                            if request['phase'] == 'observe':
                                material = result['currentApplicability'][case_id]
                                if kind == 'selected-delta':
                                    material['differences'] = [row for row in material['differences'] if row['path'] != selected]
                                elif kind == 'selected-sha':
                                    next(row for row in material['differences'] if row['path'] == selected)['newSha256'] = '0' * 64
                                elif kind == 'condition': material['conditionBindings'][0]['currentValue'] = 'drift'
                                elif kind == 'review-digest': material['reviewBundle']['evidenceSha256'] = '0' * 64
                                elif kind == 'candidate-review': result['reviewBundle']['decision'] = 'fail'
                                if kind != 'review-digest': self.sign_parent_material(material)
                            elif kind == 'recheck':
                                result['currentApplicability'][case_id]['current']['packageSha256'] = '0' * 64
                            return result
                        with self.subTest(rejection=kind):
                            self.assertEqual(self.assess(contract, invalid)['acceptedCases'], [])
                    read_snapshot = a._revision_package_snapshot
                    current_revision = supported['current']['subject']['revision']
                    for kind in ('missing-file', 'invalid-mode', 'malformed-manifest'):
                        def broken_snapshot(*args):
                            snapshot = read_snapshot(*args)
                            if args[1] == current_revision:
                                if kind == 'missing-file': snapshot['files'].pop(selected)
                                elif kind == 'invalid-mode': snapshot['modes'][selected] = '120000'
                                else: snapshot['files'][contract['delivery']['hostProjections'][0]['manifest']] = b'{bad'
                            return snapshot
                        with self.subTest(structure=kind), patch.object(a, '_revision_package_snapshot', side_effect=broken_snapshot):
                            with patch.object(a, '_current_impact', wraps=a._current_impact) as impact:
                                self.assertEqual(self.assess(contract, base)['acceptedCases'], [])
                                impact.assert_not_called()
                    self.assertEqual(self.canonical_bytes(record), frozen)

    def aggregate_fixture(self):
        # Repeated condition values and their applicability bindings compose a
        # large envelope; every original case, record and material stays bounded.
        contract = copy.deepcopy(self.contract)
        case_id = 'v33-system-integration-live-development-01'
        case = next(row for row in contract['acceptance']['admission']['cases'] if row['id'] == case_id)
        case['conditions']['syntheticCapacity'] = {str(i): '界' * 800 for i in range(100)}
        with patch.object(self, 'contract', contract):
            contract, case, record, base = self.parent_fixture(case_id)
        envelopes = {}

        def observer(request):
            result = base(request)
            if request['phase'] == 'observe':
                material = result['parentApplicability'][case_id]
                for row in material['conditionBindings']:
                    if row['pointer'].startswith('/syntheticCapacity/'):
                        row['basis'] = '界' * 1200
                self.sign_parent_material(material)
            envelopes[request['phase']] = copy.deepcopy(result)
            return result
        return contract, case, observer, envelopes

    def test_current_aggregate_observe_and_recheck_keep_individual_limits(self):
        with self.history():
            contract, case, observer, envelopes = self.aggregate_fixture()
            returned = []
            def detached(request):
                result = observer(request)
                if request['phase'] == 'observe':
                    returned.append(result)
                else:
                    digest = hashlib.sha256(self.canonical_bytes(returned[0])).hexdigest()
                    self.assertEqual(request['observationSha256'], digest)
                    returned[0]['records'][0]['observerId'] = 'late-foreign-mutation'
                    self.assertNotEqual(request['observationSha256'],
                                        hashlib.sha256(self.canonical_bytes(returned[0])).hexdigest())
                return result
            report = self.assess(contract, detached)
            self.assertEqual(report['errors'], [])
            self.assertIn(case['id'], report['acceptedCases'])
            self.assertEqual(set(envelopes), {'observe', 'recheck'})
            for envelope in envelopes.values():
                size = len(self.canonical_bytes(envelope))
                self.assertGreater(size, 1_000_000)
                self.assertLess(size, 2_000_000)
            observed = envelopes['observe']
            for item in [*observed['records'], observed['reviewBundle'],
                         *observed['parentApplicability'].values()]:
                self.assertLess(len(self.canonical_bytes(item)), 1_000_000)
            rechecked = envelopes['recheck']
            for item in [*rechecked['conditions'].values(), *rechecked['parentApplicability'].values()]:
                self.assertLess(len(self.canonical_bytes(item)), 1_000_000)

    def test_current_aggregate_caps_and_untrusted_values_fail_closed(self):
        with self.history():
            contract, case, observer, envelopes = self.aggregate_fixture()
            self.assertIn(case['id'], self.assess(contract, observer)['acceptedCases'])
            for kind in ('observe-total', 'recheck-total', 'record', 'review', 'current-material',
                         'parent-material', 'recheck-conditions', 'recheck-material',
                         'observe-nonfinite', 'recheck-nonfinite', 'payload-limit', 'hash', 'identity'):
                phases = []
                sizes = {}
                def invalid(request):
                    phase = request['phase']
                    phases.append(phase)
                    result = copy.deepcopy(envelopes[phase])
                    if kind == 'review' and phase == 'observe':
                        result = self.observer(request)
                    if phase == 'recheck':
                        result['observationSha256'] = request['observationSha256']
                    if kind == 'observe-total' and phase == 'observe':
                        finding = {'severity': 'P3', 'disposition': 'pass'}
                        count = ((2_000_001 - len(self.canonical_bytes(result)))
                                 // (len(self.canonical_bytes(finding)) + 1) + 1)
                        result['reviewBundle']['reviews'][0]['findings'] = [finding] * count
                        sizes.update(review=len(self.canonical_bytes(result['reviewBundle'])),
                                     total=len(self.canonical_bytes(result)))
                    elif kind == 'recheck-total' and phase == 'recheck':
                        # Every condition item stays small; only their composition overflows.
                        result['conditions']['synthetic-extra-1'] = '界' * 160_000
                        result['conditions']['synthetic-extra-2'] = '界' * 160_000
                        sizes['total'] = len(self.canonical_bytes(result))
                    elif kind in ('record', 'review', 'current-material', 'parent-material') and phase == 'observe':
                        if kind == 'record': item = result['records'][0]
                        elif kind == 'review': item = result['reviewBundle']
                        else:
                            item = result['parentApplicability'][case['id']]
                            if kind == 'current-material':
                                result['currentApplicability'] = result.pop('parentApplicability')
                        # The whole envelope fits 2 MB but this one item exceeds 1 MB.
                        item['syntheticPadding'] = 'x' * (1_000_001 - len(self.canonical_bytes(item)))
                        sizes.update(item=len(self.canonical_bytes(item)), total=len(self.canonical_bytes(result)))
                    elif kind in ('recheck-conditions', 'recheck-material') and phase == 'recheck':
                        mapping = result['conditions' if kind == 'recheck-conditions' else 'parentApplicability']
                        mapping[case['id']] = '界' * 333_334
                        sizes.update(item=len(self.canonical_bytes(mapping[case['id']])),
                                     total=len(self.canonical_bytes(result)))
                    elif kind == phase + '-nonfinite':
                        result['syntheticPadding'] = float('nan')
                    elif kind == 'payload-limit' and phase == 'observe':
                        result['envelopeLimit'] = 10_000_000
                    elif kind == 'hash' and phase == 'recheck':
                        result['observationSha256'] = '0' * 64
                    elif kind == 'identity' and phase == 'recheck':
                        result['subject']['revision'] = '0' * 40
                    return result
                with self.subTest(kind=kind):
                    report = self.assess(contract, invalid)
                    if kind in ('observe-total', 'recheck-total'):
                        self.assertGreater(sizes['total'], 2_000_000)
                    if 'review' in sizes:
                        self.assertLess(sizes['review'], 1_000_000)
                    if 'item' in sizes:
                        self.assertGreater(sizes['item'], 1_000_000)
                        self.assertLess(sizes['total'], 2_000_000)
                    self.assertEqual(report['acceptedCases'], [])
                    self.assertTrue(report['errors'])
                    self.assertEqual(phases, ['observe'] if kind in (
                        'observe-total', 'record', 'review', 'current-material', 'parent-material',
                        'observe-nonfinite', 'payload-limit') else ['observe', 'recheck'])

    def test_parent_applicability_complete_each_class_preserves_original_and_a08(self):
        for case_id in ("v33-admitted-entry-delivery-01", "v33-admitted-entry-lifecycle-01",
                        "v33-system-integration-live-development-01",
                        "v33-system-impact-assessment-live-development-01"):
            with self.subTest(case=case_id), self.history():
                contract, case, record, base = self.parent_fixture(case_id)
                frozen = copy.deepcopy(record)
                def observer(request):
                    result = base(request)
                    if request["phase"] == "observe" and case["scope"] != "v33-system-integration":
                        material = result["parentApplicability"][case_id]
                        material["relationships"] = []
                        self.sign_parent_material(material)
                    return result
                report = self.assess(contract, observer)
                self.assertEqual(report["errors"], [], report)
                self.assertEqual(report["acceptedCases"], [case_id])
                self.assertEqual(record, frozen)
                self.assertIn(case_id, report["currentParentApplicability"])
                self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])
                self.assertFalse(report["candidateEligible"])
                self.assertNotIn(case_id, self.assess(contract, self.replay([record]))["acceptedCases"])

    def test_parent_applicability_rejects_incomplete_predicates_roles_chain_and_recheck(self):
        case_id = "v33-system-impact-assessment-live-development-01"
        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            for kind in ("comparison", "non-effect", "scenario", "condition", "source", "final",
                         "identity", "delta", "delta-mode", "child-episode", "relationship-source", "digest",
                         "recheck", "current-review", "unknown"):
                def observer(request):
                    result = base(request)
                    if request["phase"] == "recheck":
                        if kind == "recheck": result["parentApplicability"][case_id]["roles"][0]["currentSources"] = []
                        return result
                    material = result["parentApplicability"][case_id]
                    if kind in {"comparison", "non-effect", "scenario"}:
                        text = {"comparison": "/comparison/", "non-effect": "/authority/",
                                "scenario": "/native-sufficient"}[kind]
                        material["predicateBindings"] = [row for row in material["predicateBindings"] if text not in row["pointer"]]
                    elif kind == "condition": material["conditionBindings"].pop()
                    elif kind == "source": material["roles"][0]["currentSources"] = []
                    elif kind == "final": material["original"]["qualification"]["decision"] = "failed"
                    elif kind == "identity": result["records"][0]["observerId"] = "relabelled"
                    elif kind == "delta": material["differences"].pop()
                    elif kind == "delta-mode": material["differences"][0]["newMode"] = "100755"
                    elif kind == "child-episode": material["relationships"][0]["episodeId"] = "separate-child"
                    elif kind == "relationship-source": material["relationships"][0]["sources"] = ["analysis"]
                    elif kind == "digest": material["reviewBundle"]["reviews"][0]["evidenceSha256"] = "0" * 64
                    elif kind == "current-review": result["reviewBundle"]["decision"] = "fail"
                    elif kind == "unknown": material["predicateBindings"][0]["currentValue"] = "unknown"
                    if kind != "digest": self.sign_parent_material(material)
                    return result
                with self.subTest(kind=kind):
                    report = self.assess(contract, observer)
                    self.assertNotIn(case_id, report["acceptedCases"])
                    if kind == "recheck":
                        self.assertIn("current-applicability-changed", report["caseRejections"][case_id])

    def test_whole_host_parent_reuses_complete_original_with_fresh_current_review(self):
        case_id = "v33-whole-host-lifecycle-current-development-02"
        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) + timedelta(days=2)

        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            frozen = self.canonical_bytes(record)
            original_case = copy.deepcopy(case)
            original_conditions = {}
            pending = [("", original_case["conditions"])]
            while pending:
                pointer, value = pending.pop()
                if isinstance(value, (dict, list)) and value:
                    items = value.items() if isinstance(value, dict) else enumerate(value)
                    pending.extend((pointer + "/" + str(key).replace("~", "~0").replace("/", "~1"), child)
                                   for key, child in items)
                else:
                    original_conditions[pointer] = value
            original_stage_seconds = original_case["conditions"]["currentDecisionBinding"]["limits"][
                "sameWholeStageWallSeconds"]
            def observer(request):
                result = base(request)
                if request["phase"] == "observe":
                    material = result["parentApplicability"][case_id]
                    self.assertEqual(len(material["predicateBindings"]), 35)
                    self.assertEqual(len(material["conditionBindings"]), len(original_conditions))
                    self.assertEqual({row["pointer"]: row["originalValue"]
                                      for row in material["conditionBindings"]}, original_conditions)
                    self.assertEqual(len(material["roles"]), 9)
                    self.assertNotEqual(record["packageSha256"], material["current"]["packageSha256"])
                    material["relationships"] = []
                    ended = next(row for row in material["roles"] if row["entry"] == "cx-vscode")
                    ended.update(responsibility="historical-execution", currentActor=None, currentSources=[])
                    root = next(row for row in material["roles"] if row["entry"] == "cx-desktop")
                    root["responsibility"] = "actual-current-reassessment"
                    # Retain execution identities and clocks; continuing source,
                    # permission and recovery dependencies still need current evidence.
                    historical = [row for row in material["conditionBindings"] if row["pointer"].startswith((
                        "/currentDecisionBinding/episodeId", "/currentDecisionBinding/observerCarrier/",
                        "/currentDecisionBinding/currentPackage/", "/currentDecisionBinding/limits/"))]
                    for row in historical:
                        row.update(role=root["id"], responsibility="historical-execution")
                    stage = next(row for row in historical if row["pointer"].endswith("/sameWholeStageWallSeconds"))
                    self.assertEqual(stage["originalValue"], original_stage_seconds)
                    self.assertEqual(stage["currentValue"], original_stage_seconds)
                    for bundle in (result["reviewBundle"], material["reviewBundle"]):
                        for review in bundle["reviews"]:
                            review["reviewedAt"] = Later.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    self.sign_parent_material(material)
                return result
            with patch("yiyuan_accord.admission.datetime", Later):
                report = self.assess(contract, observer)
            self.assertEqual(report["errors"], [], report["caseRejections"])
            self.assertEqual(report["acceptedCases"], [case_id])
            self.assertEqual(self.canonical_bytes(record), frozen)
            self.assertEqual(case, original_case)
            self.assertLess(datetime.fromisoformat(record["observedAt"]),
                            Later.now(timezone.utc) - timedelta(seconds=case["maxAgeSeconds"]))
            self.assertIn("complete-package-changed", report["currentParentApplicability"][case_id]["reconciledReasons"])
            self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])
            self.assertFalse(report["candidateEligible"])
            legacy = self.assess(contract, self.replay([record]))
            self.assertNotIn(case_id, legacy["acceptedCases"])
            self.assertIn("reuse-definition-mismatch", legacy["caseRejections"][case_id])

    def test_whole_host_parent_rejects_unbound_original_current_and_recheck(self):
        case_id = "v33-whole-host-lifecycle-current-development-02"
        variants = ("function-channel", "claim", "role", "fake-current-actor", "predicate", "authority", "cleanup", "condition",
                        "observer", "time", "episode", "old-package", "old-stage", "current-stage", "delta", "current-package",
                    "context", "source-kind", "digest", "review-subject", "expired-review", "current-review",
                    "recheck-package", "recheck-context", "recheck-roles", "recheck-predicates", "recheck-conditions", "recheck-digest")
        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            frozen = self.canonical_bytes(record)
            for kind in variants:
                def observer(request):
                    result = base(request)
                    if request["phase"] == "recheck":
                        material = result["parentApplicability"][case_id]
                        if kind == "function-channel":
                            result["currentApplicability"] = result.pop("parentApplicability")
                        elif kind == "recheck-package": material["current"]["packageSha256"] = "0" * 64
                        elif kind == "recheck-context": material["current"]["context"]["authority"] = []
                        elif kind == "recheck-roles": material["roles"].pop()
                        elif kind == "recheck-predicates": material["predicateBindings"].pop()
                        elif kind == "recheck-conditions": material["conditionBindings"].pop()
                        elif kind == "recheck-digest": material["evidenceSha256"] = "0" * 64
                        return result
                    material = result["parentApplicability"][case_id]
                    if kind == "function-channel":
                        material["schema"] = "yiyuan-accord-current-applicability/v1"
                        material["original"]["qualification"]["claim"] = "function"
                        for key in ("predicateBindings", "roles", "relationships"): material.pop(key)
                        for row in material["conditionBindings"]:
                            row.pop("role"); row.pop("originalSources")
                        result["currentApplicability"] = result.pop("parentApplicability")
                    elif kind == "claim": material["original"]["qualification"]["claim"] = "function"
                    elif kind == "role": material["roles"].pop()
                    elif kind == "fake-current-actor": material["roles"][0]["responsibility"] = "historical-execution"
                    elif kind == "predicate": material["predicateBindings"].pop(0)
                    elif kind in ("authority", "cleanup"):
                        material["predicateBindings"] = [row for row in material["predicateBindings"]
                            if not row["pointer"].startswith("/" + kind + "/")]
                    elif kind == "condition": material["conditionBindings"].pop()
                    elif kind == "observer": result["records"][0]["observerId"] = "relabelled-current-Root"
                    elif kind == "time":
                        result["records"][0]["observedAt"] = datetime.fromisoformat(record["observedAt"]).strftime("%Y-%m-%dT%H:%M:%SZ")
                    elif kind == "episode": result["records"][0]["episodeId"] = "new-execution"
                    elif kind == "old-package": result["records"][0]["packageSha256"] = material["current"]["packageSha256"]
                    elif kind in ("old-stage", "current-stage"):
                        next(row for row in material["conditionBindings"] if row["pointer"].endswith(
                            "/sameWholeStageWallSeconds"))[
                                "originalValue" if kind == "old-stage" else "currentValue"] = 7200
                    elif kind == "delta": material["differences"].pop()
                    elif kind == "current-package": material["current"]["packageSha256"] = record["packageSha256"]
                    elif kind == "context": material["current"]["context"]["entry"]["value"] = "cx-cli"
                    elif kind == "source-kind": material["sources"]["actual"]["kind"] = "source-analysis"
                    elif kind == "digest": material["reviewBundle"]["reviews"][0]["evidenceSha256"] = "0" * 64
                    elif kind == "review-subject": material["reviewBundle"]["subject"] = material["original"]["subject"]
                    elif kind == "expired-review": material["reviewBundle"]["reviews"][0]["reviewedAt"] = "2000-01-01T00:00:00Z"
                    elif kind == "current-review": result["reviewBundle"]["decision"] = "fail"
                    if kind != "digest": self.sign_parent_material(material)
                    return result
                with self.subTest(kind=kind):
                    report = self.assess(contract, observer)
                    self.assertNotIn(case_id, report["acceptedCases"])
                    self.assertIn(case_id, report["caseRejections"])
                    if kind.startswith("recheck-"):
                        self.assertIn("current-applicability-changed", report["caseRejections"][case_id])
                    self.assertEqual(self.canonical_bytes(record), frozen)

    def test_parent_scope_extension_does_not_admit_sdk_or_ordinary_function(self):
        for case_id in ("v33-codex-sdk-lifecycle-01", "v33-codex-sdk-scoped-exposure-01",
                        "v33-cli-readme-semantic-review-20261020-01"):
            with self.subTest(case=case_id), self.history():
                contract, case, record, observer = self.parent_fixture(case_id)
                report = self.assess(contract, observer)
                self.assertNotIn(case_id, report["acceptedCases"])
                self.assertIn("current-applicability-unsupported", report["caseRejections"][case_id])

    def test_parent_applicability_integration_requires_original_connected_chain(self):
        case_id = "v33-system-integration-live-development-01"
        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            for kind in ("empty", "missing-kind", "disjoint-events", "disjoint-roles", "child-episode"):
                def observer(request):
                    result = base(request)
                    if request["phase"] == "observe":
                        material = result["parentApplicability"][case_id]
                        edges = material["relationships"]
                        if kind == "empty": material["relationships"] = []
                        elif kind == "missing-kind": edges.pop()
                        elif kind == "disjoint-events": edges[1]["fromEvent"] = "independent-child-event"
                        elif kind == "disjoint-roles": edges[1]["fromRole"] = "1"
                        else: edges[1]["episodeId"] = "independent-child-episode"
                        self.sign_parent_material(material)
                    return result
                with self.subTest(kind=kind):
                    report = self.assess(contract, observer)
                    self.assertNotIn(case_id, report["acceptedCases"])
                    self.assertIn("current-applicability-unsupported", report["caseRejections"][case_id])

    def test_parent_applicability_changed_definition_and_conditions_still_reject(self):
        case_id = "v33-system-integration-live-development-01"
        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            for kind in ("authority", "quality", "scope", "condition", "expected", "scenario"):
                with self.subTest(kind=kind), self.history():
                    before = copy.deepcopy(contract)
                    if kind == "authority": contract["authority"]["basis"] += " Changed authority."
                    elif kind == "quality": contract["systemOptimization"]["qualityAxes"][0]["floor"] += " Changed floor."
                    elif kind == "scope":
                        next(row for row in contract["acceptance"]["admission"]["scopes"]
                             if row["id"] == case["scope"])["rule"] += " Changed rule."
                    elif kind == "condition": case["conditions"]["newCondition"] = True
                    elif kind == "expected": case["expected"]["effect"]["newPredicate"] = True
                    else: case["scenarios"] = case["scenarios"][:-1]
                    self.commit(contract)
                    self.assertNotIn(case_id, self.assess(contract, base)["acceptedCases"])
                    contract.clear(); contract.update(before)
                    case = next(row for row in contract["acceptance"]["admission"]["cases"] if row["id"] == case_id)

    def test_parent_applicability_mixed_binding_responsibilities_preserve_actor_identity(self):
        case_id = "v33-system-integration-live-development-01"
        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            def mixed_root(request):
                result = base(request)
                if request["phase"] == "observe":
                    material = result["parentApplicability"][case_id]
                    role = next(row for row in material["roles"] if row["entry"] == "cx-desktop" and row["mode"] is None)
                    historical = {"/liveDevelopmentBinding/actor/model": "gpt-6.1-sol",
                                  "/liveDevelopmentBinding/firstSpanLimits/wallSeconds": 900}
                    for row in material["conditionBindings"]:
                        row["role"] = role["id"]
                        if row["pointer"] in historical:
                            self.assertEqual(row["originalValue"], historical[row["pointer"]])
                            row["responsibility"] = "historical-execution"
                    composition = next(row for row in material["conditionBindings"] if row["pointer"] == "/composition")
                    self.assertEqual(composition["responsibility"], "continuing-applicability")
                    historical_fact = material["predicateBindings"][0]
                    historical_fact.update(role=role["id"], responsibility="historical-execution", currentSources=[])
                    self.sign_parent_material(material)
                return result
            report = self.assess(contract, mixed_root)
            self.assertEqual(report["errors"], [], report)
            self.assertEqual(report["acceptedCases"], [case_id])

        case_id = "v33-admitted-entry-delivery-01"
        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            for kind in ("valid", "current-no-source", "reassessment-no-source", "historical-continuing",
                         "fake-current-actor", "pretended-live-actor", "historical-source-kind",
                         "condition-reassessment-no-source", "condition-continuing-historical", "unknown-responsibility"):
                def ended_ide(request):
                    result = base(request)
                    if request["phase"] == "observe":
                        material = result["parentApplicability"][case_id]
                        material["relationships"] = []
                        role = next(row for row in material["roles"] if row["entry"] == "cx-vscode" and row["mode"] is None)
                        role.update(responsibility="historical-execution", currentActor=None, currentSources=[])
                        ide = [row for row in material["predicateBindings"] if "/entryDelivery/cx-vscode/" in row["pointer"]]
                        for row in ide:
                            row.update(responsibility="historical-execution", currentSources=[])
                        reassessment = next(row for row in ide if row["pointer"].endswith("/reusedEvidenceApplicable"))
                        reassessment.update(responsibility="actual-current-reassessment", currentSources=["actual"])
                        historical_recheck = next(row for row in ide if row["pointer"].endswith("/unfinishedResponsibilitiesAccounted"))
                        historical_recheck["currentSources"] = ["actual"]
                        condition = next(row for row in material["conditionBindings"] if row["pointer"] == "/sourceBasis")
                        condition.update(role=role["id"], responsibility="actual-current-reassessment")
                        if kind == "current-no-source":
                            next(row for row in material["predicateBindings"] if row not in ide)["currentSources"] = []
                        elif kind == "reassessment-no-source": reassessment["currentSources"] = []
                        elif kind == "historical-continuing": reassessment["responsibility"] = "continuing-applicability"
                        elif kind == "fake-current-actor": role["currentActor"] = {"observer": "Root"}
                        elif kind == "pretended-live-actor": role["currentActor"] = "pretended-live-IDE"
                        elif kind == "historical-source-kind": historical_recheck["currentSources"] = ["analysis"]
                        elif kind == "condition-reassessment-no-source": condition["sources"] = []
                        elif kind == "condition-continuing-historical": condition["responsibility"] = "continuing-applicability"
                        elif kind == "unknown-responsibility": reassessment["responsibility"] = "unknown"
                        self.sign_parent_material(material)
                    return result
                with self.subTest(kind=kind):
                    report = self.assess(contract, ended_ide)
                    if kind == "valid":
                        self.assertEqual(report["errors"], [], report)
                        self.assertEqual(report["acceptedCases"], [case_id])
                        self.assertEqual(report["currentParentApplicability"][case_id]["current"]["context"]["entry"]["value"], "cx-desktop")
                    else:
                        self.assertNotIn(case_id, report["acceptedCases"])
                        self.assertIn("current-applicability-unsupported", report["caseRejections"][case_id])

    def test_parent_applicability_entry_aggregate_and_mode_roles_are_exact(self):
        for case_id, facet in (("v33-admitted-entry-delivery-01", "entryDelivery"),
                               ("v33-admitted-entry-lifecycle-01", "entryLifecycle")):
            with self.subTest(case=case_id), self.history():
                contract, case, record, base = self.parent_fixture(case_id)
                for kind in ("valid", "aggregate-as-remote", "work-local-as-remote"):
                    def observer(request):
                        result = base(request)
                        if request["phase"] == "observe":
                            material = result["parentApplicability"][case_id]
                            material["relationships"] = []
                            if kind != "valid":
                                prefix = "/effect/" + facet + "/chatgpt-desktop/"
                                binding = next(row for row in material["predicateBindings"]
                                    if row["pointer"].startswith(prefix) and
                                    (("/modes/" not in row["pointer"]) if kind == "aggregate-as-remote"
                                     else "/modes/work-local/" in row["pointer"]))
                                binding["role"] = next(row["id"] for row in material["roles"]
                                    if row["entry"] == "chatgpt-desktop" and row["mode"] == "remote")
                            self.sign_parent_material(material)
                        return result
                    with self.subTest(binding=kind):
                        report = self.assess(contract, observer)
                        if kind == "valid":
                            self.assertEqual(report["errors"], [], report)
                            self.assertEqual(report["acceptedCases"], [case_id])
                        else:
                            self.assertNotIn(case_id, report["acceptedCases"])
                            self.assertIn("current-applicability-unsupported", report["caseRejections"][case_id])

    def test_parent_applicability_mode_mapping_and_v1_exclusion(self):
        case_id = "v33-admitted-entry-delivery-01"
        with self.history():
            contract, case, record, base = self.parent_fixture(case_id)
            for kind in ("mode", "wrong-mode", "v1", "overlap"):
                def observer(request):
                    result = base(request)
                    if request["phase"] == "observe":
                        material = result["parentApplicability"][case_id]
                        if kind == "mode": material["roles"].pop()
                        elif kind == "wrong-mode":
                            next(row for row in material["roles"] if row["mode"] == "remote")["mode"] = "chat"
                        elif kind == "v1":
                            material["schema"] = "yiyuan-accord-current-applicability/v1"
                            for key in ("roles", "relationships", "predicateBindings"): material.pop(key)
                            for row in material["conditionBindings"]:
                                row.pop("role"); row.pop("originalSources")
                            result["currentApplicability"] = result.pop("parentApplicability")
                        else: result["currentApplicability"] = copy.deepcopy(result["parentApplicability"])
                        self.sign_parent_material(material)
                    return result
                with self.subTest(kind=kind):
                    self.assertNotIn(case_id, self.assess(contract, observer)["acceptedCases"])

    def test_current_impact_default_and_explicit_scoped_success(self):
        with self.history():
            contract, case, record, observer = self.impact_fixture()
            frozen = copy.deepcopy(record)
            legacy = self.assess(contract, self.replay([record]))
            self.assertEqual(legacy["acceptedCases"], [])
            self.assertIn("reuse-definition-mismatch", legacy["caseRejections"][case["id"]])
            def empty(request):
                result = self.replay([record])(request)
                if request["phase"] == "observe": result["currentApplicability"] = {}
                return result
            self.assertEqual(self.assess(contract, empty), legacy)
            report = self.assess(contract, observer)
            self.assertEqual(report["errors"], [])
            self.assertEqual(report["acceptedCases"], [case["id"]])
            self.assertEqual(record, frozen)
            supported = report["currentApplicability"][case["id"]]
            self.assertIn("complete-package-changed", supported["reconciledReasons"])
            self.assertIn("not-new-execution-or-parent-coverage", supported["claimLimit"])
            self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])
            clock = [0]
            def expires(request):
                result = observer(request)
                if request["phase"] == "recheck": clock[0] = case["maxAgeSeconds"]
                return result
            with patch("yiyuan_accord.admission.monotonic", side_effect=lambda: clock[0]):
                expired = self.assess(contract, expires)
            self.assertEqual(expired["acceptedCases"], [])
            self.assertIn("current-applicability-expired", expired["caseRejections"][case["id"]])

    def test_current_impact_rejects_missing_malformed_stale_and_unbound_evidence(self):
        from yiyuan_accord import admission as a
        def resign(material):
            digest = a._hash({k: v for k, v in material.items() if k != "reviewBundle"})
            material["reviewBundle"]["evidenceSha256"] = digest
            for row in material["reviewBundle"]["reviews"]: row["evidenceSha256"] = digest
        with self.history():
            contract, case, _, base = self.impact_fixture()
            def mutate(kind, result):
                material = result["currentApplicability"][case["id"]]
                if kind == "missing-delta": material["differences"].pop()
                elif kind == "wrong-mode": material["differences"][0]["oldMode"] = "100755"
                elif kind == "wrong-sha": material["differences"][0]["newSha256"] = "0" * 64
                elif kind == "duplicate-delta": material["differences"].append(copy.deepcopy(material["differences"][0]))
                elif kind == "missing-source": material["sources"].pop("actual")
                elif kind == "ast-only": material["differences"][0]["currentConsequences"] = ["analysis"]
                elif kind == "partial": material["original"]["qualification"]["stage"] = "early-core"
                elif kind == "final-failed": material["original"]["qualification"]["decision"] = "held"
                elif kind == "early-only": material["original"]["qualification"]["finalOutcomeSources"] = ["qualification"]
                elif kind == "negative-unresolved": material["original"]["qualification"]["knownFailuresAndLimits"][0]["disposition"] = "unresolved-within-case"
                elif kind == "negative-missing-source": material["original"]["qualification"]["knownFailuresAndLimits"][0]["sources"] = []
                elif kind == "wrong-record": material["original"]["recordSha256"] = "0" * 64
                elif kind == "missing-condition": material["conditionBindings"].pop()
                elif kind == "continuing-drift": material["conditionBindings"][0]["currentValue"] = "wrong"
                elif kind == "unknown-responsibility": material["conditionBindings"][0]["responsibility"] = "optional"
                elif kind == "wrong-subject": material["current"]["subject"]["tree"] = "0" * 40
                elif kind == "wrong-host": material["current"]["context"]["host"]["value"] = "other-host"
                elif kind == "wrong-entry": material["current"]["context"]["entry"]["value"] = "other-entry"
                elif kind == "unbound-review": material["reviewBundle"]["reviews"][0].pop("evidenceSha256")
                elif kind == "ordinary-review": material["reviewBundle"]["schema"] = "yiyuan-accord-development-review-bundle/v1"
                elif kind == "stale-review":
                    for row in material["reviewBundle"]["reviews"]: row["reviewedAt"] = "2000-01-01T00:00:00Z"
                elif kind == "same-reviewer":
                    for row in material["reviewBundle"]["reviews"]: row["reviewerId"] = "same"
                elif kind == "unknown-material": material["extra"] = True
                elif kind == "current-review-failed": result["reviewBundle"]["decision"] = "fail"
                elif kind == "original-fact-failed": result["records"][0]["facts"][next(iter(case["expected"]))]["value"] = False
                else: material["differences"] = None
                if kind not in {"unbound-review"}: resign(material)
            kinds = ("missing-delta", "wrong-mode", "wrong-sha", "duplicate-delta", "missing-source",
                "ast-only", "partial", "final-failed", "early-only", "negative-unresolved", "negative-missing-source",
                "wrong-record", "missing-condition", "continuing-drift",
                "unknown-responsibility", "wrong-subject", "wrong-host", "wrong-entry", "unbound-review", "ordinary-review", "stale-review",
                "same-reviewer", "unknown-material", "current-review-failed", "original-fact-failed", "malformed")
            for kind in kinds:
                def observer(request):
                    result = base(request)
                    if request["phase"] == "observe": mutate(kind, result)
                    return result
                with self.subTest(kind=kind):
                    report = self.assess(contract, observer)
                    self.assertEqual(report["acceptedCases"], [])
                    self.assertIn(case["id"], report["caseRejections"])
            for kind in ("digest", "current", "condition", "missing-map"):
                def observer(request):
                    result = base(request)
                    if request["phase"] == "recheck":
                        if kind == "missing-map": result.pop("currentApplicability")
                        elif kind == "digest": result["currentApplicability"][case["id"]]["evidenceSha256"] = "0" * 64
                        elif kind == "current": result["currentApplicability"][case["id"]]["current"]["context"]["authority"] = []
                        else: result["conditions"][case["id"]] = {}
                    return result
                with self.subTest(recheck=kind):
                    self.assertEqual(self.assess(contract, observer)["acceptedCases"], [])

    def test_current_impact_semantics_and_scope_are_not_artifact_identity(self):
        from yiyuan_accord import admission as a
        contract, case = self.historical_fixture_case("v33-goal-authority-correction-01")
        self.assertTrue(a._impact_eligible(contract, case))
        digest = a._impact_definition(contract, case)
        for kind in ("base", "expected", "condition", "authority", "quality", "scope", "packageFiles"):
            changed, target = copy.deepcopy(contract), copy.deepcopy(case)
            if kind == "base": changed["delivery"]["version"] = "9.0.0"
            elif kind == "expected": target["expected"]["effect"] = {"other": True}
            elif kind == "condition": target["conditions"]["other"] = True
            elif kind == "authority": changed["authority"] = {"other": True}
            elif kind == "quality": changed["systemOptimization"]["qualityAxes"][0]["rule"] = "changed"
            elif kind == "scope": next(row for row in changed["acceptance"]["admission"]["scopes"]
                                        if row["id"] == case["scope"])["rule"] = "changed"
            else: target["packageFiles"] = []
            with self.subTest(kind=kind):
                try: actual = a._impact_definition(changed, target)
                except ValueError: continue
                self.assertNotEqual(digest, actual)
        for kind in ("claims", "nested", "a08", "parent", "lifecycle"):
            changed, target = copy.deepcopy(contract), copy.deepcopy(case)
            if kind == "claims": target["claims"].append("incremental-value")
            elif kind == "nested": target["conditions"]["nested"] = {"selectedModes": []}
            elif kind == "a08":
                next(row for row in changed["acceptance"]["admission"]["acceptanceRequirements"]
                     if row["id"] == "A08")["requiredCoverage"]["function"].append(target["scope"])
            else:
                target["scope"] = "v33-admitted-entry-delivery" if kind == "parent" else "v33-codex-lifecycle"
            with self.subTest(excluded=kind):
                self.assertFalse(a._impact_eligible(changed, target))

    def test_current_impact_git_delta_retains_modes_additions_deletions_and_adjudicator(self):
        from yiyuan_accord import admission as a
        original_revision = self.git("rev-parse", "HEAD")
        with self.history():
            contract, case, record, _ = self.impact_fixture()
            old = self.git("rev-parse", "HEAD")
            package = "plugins/yiyuan-accord-codex"
            source = self.root / "yiyuan_accord/impact_fixture.py"
            source.unlink()
            (self.root / "yiyuan_accord/renamed_fixture.py").write_text("# never imported\n")
            self.git("add", ".")
            path = package + "/runtime/task-checkpoint.cjs"
            # Keep the POSIX worktree consistent with the staged executable bit;
            # otherwise history restoration sees a local mode change and fails.
            (self.root / path).chmod(0o755)
            self.git("update-index", "--chmod=+x", path)
            self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "-m", "Synthetic mode and path delta")
            rows = a._impact_differences(self.root, old, self.git("rev-parse", "HEAD"),
                (package, package), case["oracleFiles"], {"calls": 0, "files": 0, "bytes": 0})
            by_path = {row["path"]: row for row in rows}
            self.assertEqual(by_path[path]["oldSha256"], by_path[path]["newSha256"])
            self.assertNotEqual(by_path[path]["oldMode"], by_path[path]["newMode"])
            self.assertEqual(by_path["yiyuan_accord/impact_fixture.py"]["newMode"], "000000")
            self.assertIsNone(by_path["yiyuan_accord/impact_fixture.py"]["newSha256"])
            self.assertEqual(by_path["yiyuan_accord/renamed_fixture.py"]["oldMode"], "000000")
        self.assertEqual(self.git("rev-parse", "HEAD"), original_revision)
        self.assertEqual(self.git("status", "--porcelain=v1"), "")

    def test_current_impact_rejects_truncated_duplicate_and_unsupported_git_delta(self):
        from yiyuan_accord import admission as a
        row = b":100644 100755 " + b"a" * 40 + b" " + b"a" * 40 + b" M\0yiyuan_accord/source.py\0"
        for raw in (row[:-1], row + b":100644\0", row + row,
                    row.replace(b"100755", b"120000"), row.replace(b"source.py", b"../source.py"),
                    row.replace(b"100644", b"000000"), row.replace(b" M\0", b" A\0")):
            with self.subTest(raw=raw[:32]), patch.object(a, "_git", return_value=raw), self.assertRaises(ValueError):
                a._impact_differences(self.root, "a" * 40, "b" * 40, (), [], {"calls": 0, "files": 0, "bytes": 0})
        with patch.object(a, "_git", return_value=b""):
            self.assertEqual(a._impact_differences(self.root, "a" * 40, "b" * 40, (), [],
                                                  {"calls": 0, "files": 0, "bytes": 0}), [])

    def test_current_impact_review_requires_every_review_digest_and_preserves_legacy_schema(self):
        from yiyuan_accord.reviews import evaluate_review_bundle
        subject = {"revision": "a" * 40, "tree": "b" * 40}
        bundle = self.observer({"phase": "observe", "subject": subject, "cases": {}})["reviewBundle"]
        policy = self.contract["acceptance"]["admission"]["reviewPolicy"]
        self.assertEqual(evaluate_review_bundle(bundle, **{"subject_revision": subject["revision"],
            "subject_tree": subject["tree"]}, policy=policy)["decision"], "pass")
        impact = copy.deepcopy(bundle)
        impact.update(schema="yiyuan-accord-development-impact-review-bundle/v1", evidenceSha256="c" * 64)
        for row in impact["reviews"]: row["evidenceSha256"] = "c" * 64
        check = lambda value, digest="c" * 64: evaluate_review_bundle(value, subject["revision"], subject["tree"],
            policy=policy, expected_evidence_sha256=digest)["decision"]
        self.assertEqual(check(impact), "pass")
        self.assertEqual(check(bundle), "fail")
        self.assertEqual(evaluate_review_bundle(impact, subject["revision"], subject["tree"], policy=policy)["decision"], "fail")
        for digest in (True, 1, "", "wrong", "d" * 64):
            self.assertEqual(check(impact, digest), "fail")
        for index in range(4):
            for kind in ("missing", "different"):
                wrong = copy.deepcopy(impact)
                if kind == "missing": wrong["reviews"][index].pop("evidenceSha256")
                else: wrong["reviews"][index]["evidenceSha256"] = "d" * 64
                self.assertEqual(check(wrong), "fail")

    def test_current_applicability_window_covers_observe_recheck_and_final_checks(self):
        from yiyuan_accord import admission
        limit = min(case['maxAgeSeconds'] for case in self.contract['acceptance']['admission']['cases'])
        for stage in ('observe', 'recheck', 'final', 'criterion-source'):
            clock = [0]
            rechecked = [False]
            original_subject = admission.evidence_subject
            original_git = admission._git

            def observer(request):
                result = self.observer(request)
                if request['phase'] == stage:
                    clock[0] = limit
                if request['phase'] == 'recheck':
                    rechecked[0] = True
                return result

            def subject(root):
                if stage == 'final' and rechecked[0]:
                    clock[0] = limit
                return original_subject(root)

            def git(root, *args):
                result = original_git(root, *args)
                if (stage == 'criterion-source' and args[0] == 'show'
                        and args[-1].endswith(':docs/operations/ACCEPTANCE-v3.3.md')):
                    clock[0] = limit
                return result

            with self.subTest(stage=stage), patch('yiyuan_accord.admission.monotonic',
                    side_effect=lambda: clock[0], create=True), patch(
                    'yiyuan_accord.admission.evidence_subject', side_effect=subject), patch(
                    'yiyuan_accord.admission._git', side_effect=git):
                report = self.assess(observer=observer)
                self.assertEqual(report['acceptedCases'], [])
                self.assertTrue(all('current-applicability-expired' in reasons
                                    for reasons in report['caseRejections'].values()))

    def test_current_subject_and_checkout_checked_after_criterion_sources(self):
        from yiyuan_accord import admission
        for change in ('subject', 'dirty'):
            changed = [False]
            original_git = admission._git
            original_subject = admission.evidence_subject
            original_clean = admission.clean_git_checkout

            def git(root, *args):
                result = original_git(root, *args)
                if (args[0] == 'show'
                        and args[-1].endswith(':docs/operations/ACCEPTANCE-v3.3.md')):
                    changed[0] = True
                return result

            def subject(root):
                value = original_subject(root)
                return {**value, 'tree': '0' * 40} if change == 'subject' and changed[0] else value

            def clean(root):
                return not (change == 'dirty' and changed[0]) and original_clean(root)

            with self.subTest(change=change), patch('yiyuan_accord.admission._git', side_effect=git), patch(
                    'yiyuan_accord.admission.evidence_subject', side_effect=subject), patch(
                    'yiyuan_accord.admission.clean_git_checkout', side_effect=clean):
                report = self.assess(observer=self.observer)
                self.assertTrue(changed[0])
                self.assertEqual(report['acceptedCases'], [])
                self.assertFalse(report['functionalCompletion'])
                self.assertFalse(report['candidateEligible'])
                self.assertIn('evidence observer unavailable, invalid or subject changed', report['errors'])
                if change == 'dirty':
                    self.assertFalse(report['checkoutClean'])

    def test_current_applicability_expiry_is_case_scoped_and_rejects_clock_rollback(self):
        contract = copy.deepcopy(self.contract)
        cases = contract['acceptance']['admission']['cases']
        cases[0]['maxAgeSeconds'] = 1
        all_ids = {case['id'] for case in cases}
        with self.history():
            self.commit(contract)
            for elapsed, rejected in ((0.999, set()), (1, {cases[0]['id']}), (-1, all_ids)):
                with self.subTest(elapsed=elapsed), patch('yiyuan_accord.admission.monotonic',
                                                        side_effect=[100, 100 + elapsed]):
                    report = self.assess(contract, self.observer)
                    self.assertEqual(set(report['acceptedCases']), all_ids - rejected)
                    self.assertEqual(set(report['caseRejections']), rejected)

    def test_historical_generic_cases_can_be_admitted_without_closing_current_requirements(self):
        # This counterexample deliberately has no resource/environment cases;
        # future declarations must not change what its observer can discharge.
        contract = self.without_resource_and_environment_cases()
        with self.history():
            if contract != self.contract:
                self.commit(contract)
            report = self.assess(contract, self.observer)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["acceptedCases"], sorted(
            case["id"] for case in contract["acceptance"]["admission"]["cases"]))
        self.assertEqual(report["entrySelection"], {
            "final": True,
            "selected": ["chatgpt-desktop", "chatgpt-mobile", "cx-cli", "cx-desktop", "cx-sdk", "cx-vscode"],
            "selectedModes": {"chatgpt-desktop": ["remote", "work-local"],
                              "chatgpt-mobile": ["remote"], "chatgpt-web": []},
            "pendingModes": {"chatgpt-desktop": [], "chatgpt-mobile": [],
                             "chatgpt-web": []}})
        applicability = report["openCoverage"]["v33-openai-entry-applicability"]
        self.assertEqual(applicability["claims"]["function"],
                         {"duties": [], "qualityAxes": [], "scenarios": []})
        self.assertEqual(applicability["entry"], "cx-desktop")
        self.assertEqual(set(applicability["subjectEntries"]), {
            row["id"] for row in self.contract["capabilityMap"]["entrySurfaces"]["rows"]
            if row["host"] == "codex"})
        self.assertFalse(report["functionalCompletion"])
        self.assertFalse(report["candidateEligible"])
        self.assertEqual(set(report["acceptanceRequirements"]), {f"A{i:02}" for i in range(1, 9)})
        # Scope membership can be complete while precise source outcome leaves
        # remain absent. The observer cannot manufacture those new obligations.
        self.assertEqual({key for key, row in report["acceptanceRequirements"].items() if row["complete"]},
                         set())
        missing = {
            'A01': {'a01-ambiguous-goal-to-requirements', 'a01-side-inputs-preserve-goal',
                    'a01-authority-and-resume', 'a01-affected-results-correct',
                    'a01-usable-delivery', 'a01-input-content-not-user-authorization'},
            'A03': {'a03-ordinary-unprompted-progress', 'a03-actual-feedback-and-recovery',
                    'a03-genuine-pause-and-resume', 'a03-current-goal-resumed'},
        }
        for requirement, obligations in missing.items():
            self.assertEqual(set(report['acceptanceRequirements'][requirement]['missingObligations']), obligations)
        for scope in ('v33-codex-cli-ordinary-delivery', 'v33-goal-authority-correction'):
            coverage = report['openCoverage'][scope]['claims']['function']
            self.assertEqual({key: value for key, value in coverage.items() if key != 'outcomeObligations'},
                             {'duties': [], 'qualityAxes': [], 'scenarios': []})
        self.assertEqual(report["acceptanceRequirements"]["A05"]["missingScopes"],
                         {"function": ["v33-autonomous-continuity"]})
        continuity = report["openCoverage"]["v33-autonomous-continuity"]["claims"]["function"]
        self.assertEqual({key: value for key, value in continuity.items() if key != 'outcomeObligations'},
                         {"duties": ["recovery-and-rollback"], "qualityAxes": [],
                          "scenarios": ["capability-loss"]})
        requirement = next(row for row in contract['acceptance']['admission']['acceptanceRequirements']
                           if row['id'] == 'A05')
        self.assertEqual(set(continuity['outcomeObligations']),
                         {row['id'] for row in requirement['outcomeObligations']})
        # Historical executions do not supply replacement correction or
        # installed-environment evidence, even when a component worked.
        self.assertNotIn("v33-systemic-correction-02", report["acceptedCases"])
        self.assertNotIn("v33-codex-cli-review-delivery-01", report["acceptedCases"])
        self.assertNotIn("v33-codex-cli-ordinary-retro-01", report["acceptedCases"])
        self.assertEqual(set(report["acceptanceRequirements"]["A04"]["missingScopes"]["function"]),
                         {"v33-systemic-correction", "v33-system-integration"})
        self.assertEqual(report["openCoverage"]["v33-codex-cli-ordinary-delivery"]
                         ["claims"]["function"]["scenarios"], [])
        self.assertNotIn("v33-openai-entry-applicability", report["unboundCoverage"]["function"])
        self.assertEqual(report["acceptanceRequirements"]["A02"]["missingScopes"]["function"],
                         ["v33-dynamic-model-routing"])
        self.assertNotIn("claude-code", report["productCoverage"])
        # Four unchanged entry/lifecycle pairs and the source-bound capability
        # role coverage remain verified; none completes a whole current A item.
        self.assertEqual(report["progress"]["coverageVerified"], 5)
        self.assertEqual(report["progress"]["requirementsComplete"], 0)
        # The explicit absent resource/adaptation cases and lifecycle parents
        # cannot be discharged by SDK sub-scopes.
        missing = report["acceptanceRequirements"]["A06"]["missingScopes"]
        self.assertIn("v33-codex-lifecycle", missing["package-lifecycle"])
        self.assertIn("v33-environment-adaptation", missing["function"])
        self.assertNotIn("v33-codex-sdk-lifecycle", missing["package-lifecycle"])

        # Its exact component case can remain admitted while the finer current
        # installation/reuse obligations still lack a source-bound consequence.
        self.assertIn("v33-codex-sdk-scoped-exposure-01", report["acceptedCases"])
        self.assertIn("v33-codex-sdk-scoped-exposure", missing["function"])

    def source_case_binding_gaps(self, contract):
        """Independent declaration oracle; never read verifier output as truth."""
        policy = contract['acceptance']['admission']
        dimensions = ('duties', 'qualityAxes', 'scenarios')
        joint_scopes = next(row for row in policy['acceptanceRequirements'] if row['id'] == 'A08')
        joint_scopes = joint_scopes['requiredCoverage']['function']
        gaps, without_cases = {}, 0
        for scope in policy['scopes']:
            for claim in scope['claims']:
                if scope['id'] not in policy['requiredCoverage'].get(claim, []):
                    continue
                allocated = [case for case in policy['cases']
                             if case['scope'] == scope['id'] and claim in case['claims']]
                missing = {field: sorted(value for value in scope[field]
                                        if all(value not in case[field] for case in allocated))
                           for field in dimensions}
                joint_missing = claim == 'function' and scope['id'] in joint_scopes and not any(
                    all(value in case[field] for field in dimensions for value in scope[field])
                    for case in allocated)
                without_cases += not allocated
                if not allocated or any(missing.values()) or joint_missing:
                    gaps.setdefault(scope['id'], {})[claim] = {
                        'caseIds': sorted(case['id'] for case in allocated),
                        'missingDimensions': missing, 'jointCaseMissing': joint_missing}
        return gaps, without_cases

    def test_current_declaration_without_observer_reports_actual_missing_coverage(self):
        self.assert_current_declaration_reports_missing_coverage(self.contract)

    def assert_current_declaration_reports_missing_coverage(self, contract):
        report = self.assess(contract)
        policy = contract['acceptance']['admission']
        expected_gaps, without_cases = self.source_case_binding_gaps(contract)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["acceptedCases"], [])
        self.assertFalse(report["functionalCompletion"])
        self.assertFalse(report["candidateEligible"])
        self.assertIn("v33-codex-cli-ordinary-delivery", report["acceptanceRequirements"]["A03"]["missingScopes"]["function"])
        self.assertEqual(report["progress"], {
            "scope": "acceptance-evidence-coverage-not-effort-or-implementation-completion",
            "requirementsTotal": 8, "requirementsComplete": 0,
            "coverageTotal": 17, "coverageDefined": 17, "coverageVerified": 0,
            "coverageScorePercent": 0.0,
            "coverageUnbound": 0, "coverageDefinedButUnverified": 17,
            "coverageWithoutCases": without_cases,
            "coverageWithCaseBindingGaps": sum(len(claims) for claims in expected_gaps.values()),
            "casesDefined": len(policy["cases"]), "casesAccepted": 0,
        })
        # Compare every scope/claim, case ID, dimension and joint obligation,
        # including newly allocated scopes, against the source declarations.
        self.assertEqual(report['caseBindingGaps'], expected_gaps)
        integration = report['openCoverage']['v33-system-integration']['claims']['function']
        self.assertTrue({'recovery-and-rollback', 'context-and-task-continuity'}
                        <= set(integration['duties']))
        self.assertTrue({'mid-task-user-steering', 'capability-loss'}
                        <= set(integration['scenarios']))
        continuity = report['openCoverage']['v33-autonomous-continuity']['claims']['function']
        scope = next(s for s in policy['scopes'] if s['id'] == 'v33-autonomous-continuity')
        for key in ('duties', 'qualityAxes', 'scenarios'):
            self.assertEqual(set(continuity[key]), set(scope[key]))
        self.assertEqual(report['acceptanceRequirements']['A08']['blockedBy'],
                         ['A01', 'A02', 'A03', 'A04', 'A05', 'A06', 'A07'])
        self.assertIn('v33-codex-lifecycle',
                      report['acceptanceRequirements']['A06']['missingScopes']['package-lifecycle'])
        self.assertIn('v33-system-impact-assessment',
                      report['acceptanceRequirements']['A08']['missingScopes']['impact-assessment'])
        self.assertIn('v33-autonomous-continuity',
                      report['acceptanceRequirements']['A05']['missingScopes']['function'])
        self.assertIn('v33-dynamic-model-routing',
                      report['acceptanceRequirements']['A02']['missingScopes']['function'])
        return report

    def test_resource_and_environment_declarations_do_not_promote_evidence(self):
        baseline = copy.deepcopy(self.contract)
        policy = baseline['acceptance']['admission']
        scope_ids = {'v33-resource-pressure-and-exit', 'v33-environment-adaptation'}
        policy['cases'] = [case for case in policy['cases'] if case['scope'] not in scope_ids]
        expanded = copy.deepcopy(baseline)
        expanded_policy = expanded['acceptance']['admission']
        # Exercise both declaration layouts without executing the real cases
        # or supplying an observer. These clones cover declarations only.
        for scope in policy['scopes']:
            if scope['id'] not in scope_ids:
                continue
            case = copy.deepcopy(policy['cases'][0])
            case.pop('packageFiles', None)
            case.update({key: copy.deepcopy(scope[key]) for key in
                         ('host', 'entry', 'duties', 'qualityAxes', 'scenarios', 'claims', 'conditions')})
            case.update(id='fixture-declaration-' + scope['id'], scope=scope['id'])
            expanded_policy['cases'].append(case)
        reports = []
        for contract in (baseline, expanded):
            with self.subTest(cases=len(contract['acceptance']['admission']['cases'])):
                for key in ('scopes', 'requiredCoverage', 'acceptanceRequirements'):
                    self.assertEqual(contract['acceptance']['admission'][key],
                                     self.contract['acceptance']['admission'][key])
                # Reuse the full comparison, including all zero-evidence and
                # false-qualification assertions, without reassessing twice.
                reports.append(self.assert_current_declaration_reports_missing_coverage(contract))
        before, after = reports
        self.assertTrue(scope_ids <= set(before['caseBindingGaps']))
        self.assertFalse(scope_ids & set(after['caseBindingGaps']))
        for metric in ('coverageWithoutCases', 'coverageWithCaseBindingGaps'):
            self.assertEqual(after['progress'][metric], before['progress'][metric] - 2)
        self.assertEqual(after['progress']['casesDefined'], before['progress']['casesDefined'] + 2)

    def without_resource_and_environment_cases(self):
        """An explicit no-case counterexample, with all scope floors intact."""
        contract = self.historical_mapping_fixture()
        policy = contract['acceptance']['admission']
        policy['cases'] = [case for case in policy['cases'] if case['scope'] not in
                           {'v33-resource-pressure-and-exit', 'v33-environment-adaptation'}]
        return contract

    def without_correction_and_user_environment_cases(self):
        contract = self.without_resource_and_environment_cases()
        policy = contract['acceptance']['admission']
        policy['cases'] = [c for c in policy['cases'] if c['scope'] != 'v33-systemic-correction'
                           and not (c['scope'] == 'v33-codex-cli-ordinary-delivery'
                                    and 'effective-user-environment' in c['scenarios'])]
        return contract

    def test_ended_resource_cases_keep_their_exact_history_and_scope_floors(self):
        historical = json.loads(subprocess.check_output([
            'git', '-C', str(self.root), 'show',
            '916ff322680ea5f0df6ee45b1fe326ec286a1603:product/development.json'],
            env=development_fixtures.owned_git_environment(), timeout=30))
        record = next(r for r in self.historical_contract()['developmentObservations']
                      if r['id'] == 'resource-environment-ended-instance-disposition-20260930')
        policy = self.contract['acceptance']['admission']
        self.assertEqual(record['outcome'], 'not-admitted')
        self.assertEqual(record['originalLimits']['wholeWorkSeconds'], 600)
        self.assertEqual(record['originalLimits']['workerMemoryMiB'], [160, 96])
        for declaration in record['declarations']:
            with self.subTest(case=declaration['caseId']):
                self.assertNotIn(declaration['caseId'], {r['id'] for r in policy['cases']})
                old = next(r for r in historical['acceptance']['admission']['cases']
                           if r['id'] == declaration['caseId'])
                digest = hashlib.sha256(json.dumps(old, sort_keys=True, separators=(',', ':'),
                                                   ensure_ascii=False).encode()).hexdigest()
                self.assertEqual(digest, declaration['caseObjectSha256'])
                scope = next(r for r in policy['scopes'] if r['id'] == old['scope'])
                prior = next(r for r in historical['acceptance']['admission']['scopes'] if r['id'] == old['scope'])
                # Preserve outcome floors and exact historical definitions,
                # not the old sample's SDK/Windows implementation choices.
                floor_keys = ('id', 'host', 'duties', 'qualityAxes', 'scenarios', 'claims')
                self.assertEqual({k:scope[k] for k in floor_keys},
                                 {k:prior[k] for k in floor_keys})
                self.assertEqual(scope['entry'], 'cx-desktop')
                self.assertNotIn('limitSemantics', scope['conditions'])
                self.assertEqual(scope['conditions']['collaborationMode'], 'default')
                self.assertIs(scope['conditions']['goalModeActive'], False)
                self.assertNotIn('limits', scope['conditions'])

    def test_resource_scope_allows_fresh_prebinding_without_replaying_ended_case(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract = copy.deepcopy(self.contract)
        policy = contract['acceptance']['admission']
        scope = next(r for r in policy['scopes'] if r['id'] == 'v33-environment-adaptation')
        case = {k: copy.deepcopy(scope[k]) for k in
                ('host', 'entry', 'duties', 'qualityAxes', 'scenarios', 'claims', 'conditions')}
        case.update(id='new-resource-route-fixture', scope=scope['id'], oracle='Synthetic declaration only.',
                    oracleFiles=['docs/operations/ACCEPTANCE-v3.3.md', 'docs/operations/PLAN-v3.3.md'], maxAgeSeconds=86400,
                    expected=copy.deepcopy(policy['cases'][0]['expected']))
        case['conditions'].update(codexVersion='0.158.0', model='gpt-6-sol', reasoning='high',
                                  input='Distinct prospective input, no execution.', ordinaryUserInputs=2,
                                  limits={'wholeWorkSeconds': 3600, 'recoverySeconds': 120,
                                          'workerInvocationSeconds': 300, 'workerRecoverySeconds': 30,
                                          'usageCaps': {'totalTokens': 3000000,
                                                        'uncachedInputTokens': 300000, 'outputTokens': 20000}})
        policy['cases'].append(case)
        self.assertEqual(admission_contract_errors(contract), [])
        report = self.assess(contract)
        self.assertEqual(report['acceptedCases'], [])
        self.assertFalse(report['functionalCompletion'])
        case['conditions']['goalModeActive'] = True
        self.assertTrue(admission_contract_errors(contract))

    def bounded_resource_declaration(self, scope_id='v33-environment-adaptation'):
        contract = copy.deepcopy(self.contract)
        policy = contract['acceptance']['admission']
        # This variant changes its scope policy; current real cases keep their
        # original conditions and must not be silently migrated into the fixture.
        policy['cases'] = [case for case in policy['cases'] if case['scope'] != scope_id]
        scope = next(row for row in policy['scopes'] if row['id'] == scope_id)
        # A typed ceiling is a prospective policy fixture, never host evidence.
        scope['conditions']['limitSemantics'] = 'maximum'
        scope['conditions']['limits'] = {
            'wholeWorkSeconds': 600, 'recoverySeconds': 20,
            'workerInvocationSeconds': 45, 'workerRecoverySeconds': 10,
            'usageCaps': {'totalTokens': 2500000, 'uncachedInputTokens': 200000, 'outputTokens': 14000}}
        case = {key: copy.deepcopy(scope[key]) for key in
                ('host', 'entry', 'duties', 'qualityAxes', 'scenarios', 'claims', 'conditions')}
        case.update(id='bounded-resource-policy-fixture', scope=scope_id,
                    oracle='Synthetic declaration; no execution or acceptance.',
                    oracleFiles=['docs/operations/ACCEPTANCE-v3.3.md', 'docs/operations/PLAN-v3.3.md'],
                    maxAgeSeconds=3600, expected=copy.deepcopy(policy['cases'][0]['expected']))
        policy['cases'].append(case)
        return contract, scope, case

    def test_explicit_resource_ceilings_accept_stricter_prospective_budgets(self):
        from yiyuan_accord.admission import admission_contract_errors
        for scope_id in ('v33-resource-pressure-and-exit', 'v33-environment-adaptation'):
            contract, scope, case = self.bounded_resource_declaration(scope_id)
            case['conditions']['limits'] = {
                'wholeWorkSeconds': 240, 'recoverySeconds': 10,
                'workerInvocationSeconds': 30, 'workerRecoverySeconds': 5,
                'usageCaps': {'totalTokens': 1000000, 'uncachedInputTokens': 100000, 'outputTokens': 8000}}
            with self.subTest(scope=scope_id):
                self.assertEqual(admission_contract_errors(contract), [])
                self.assertEqual(scope['conditions']['limits']['wholeWorkSeconds'], 600)

    def test_resource_ceilings_reject_overflow_missing_unknown_and_noninteger_limits(self):
        from yiyuan_accord.admission import admission_contract_errors
        alterations = (
            lambda limits: limits.update(wholeWorkSeconds=601),
            lambda limits: limits['usageCaps'].update(outputTokens=14001),
            lambda limits: limits.pop('recoverySeconds'),
            lambda limits: limits.update(unknownBudget=1),
            lambda limits: limits['usageCaps'].pop('uncachedInputTokens'),
            *(lambda limits, value=value: limits.update(wholeWorkSeconds=value)
              for value in (0, -1, True, '240', 240.0, None)),
        )
        for index, alter in enumerate(alterations):
            contract, _, case = self.bounded_resource_declaration()
            alter(case['conditions']['limits'])
            with self.subTest(alteration=index):
                self.assertTrue(admission_contract_errors(contract))

    def test_limit_ceiling_does_not_relax_other_conditions_or_legacy_exact_binding(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract, scope, case = self.bounded_resource_declaration()
        case['conditions']['collaborationMode'] = 'plan'
        self.assertTrue(admission_contract_errors(contract))
        contract, scope, case = self.bounded_resource_declaration()
        scope['conditions'].pop('limitSemantics')
        case['conditions'].pop('limitSemantics')
        case['conditions']['limits']['wholeWorkSeconds'] = 240
        self.assertTrue(admission_contract_errors(contract))

    def test_invalid_limit_policy_cannot_silently_fall_back_to_exact_binding(self):
        from yiyuan_accord.admission import admission_contract_errors
        for invalid in ('minimum', 'unknown', True):
            contract, scope, case = self.bounded_resource_declaration()
            scope['conditions']['limitSemantics'] = case['conditions']['limitSemantics'] = invalid
            with self.subTest(policy=invalid):
                self.assertTrue(admission_contract_errors(contract))
        contract, scope, case = self.bounded_resource_declaration()
        scope['conditions']['limits'] = case['conditions']['limits'] = {}
        self.assertTrue(admission_contract_errors(contract))

    def test_resource_subject_method_is_bound_per_case_without_relabelling_observer(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract, scope, case = self.bounded_resource_declaration()
        self.assertEqual(scope['entry'], 'cx-desktop')
        self.assertFalse({'entryProtocol', 'operatingSystem', 'windowsSandbox'} & scope['conditions'].keys())
        case['conditions'].update(subjectEntry='cx-cli', operatingSystem='Linux',
                                  entryProtocol='ordinary-native', permissionPolicy='read-only')
        self.assertEqual(admission_contract_errors(contract), [])
        case['conditions']['businessNetwork'] = True
        self.assertTrue(admission_contract_errors(contract))
        case['conditions']['businessNetwork'] = False
        case['entry'] = 'cx-sdk'
        self.assertTrue(admission_contract_errors(contract))

    def test_resource_observation_must_match_case_budget_not_just_parent_ceiling(self):
        contract, _, case = self.bounded_resource_declaration()
        case['conditions']['limits']['wholeWorkSeconds'] = 240
        for changed_phase in ('observe', 'recheck'):
            def observer(request):
                response = self.observer(request)
                if request['phase'] == changed_phase:
                    if changed_phase == 'observe':
                        conditions = next(row['conditions'] for row in response['records']
                                          if row['case'] == case['id'])
                    else:
                        conditions = response['conditions'][case['id']]
                    # Still within the parent 600 ceiling, but not the actual
                    # prospectively bound 240-second case. Never borrow it.
                    conditions['limits']['wholeWorkSeconds'] = 241
                return response
            with self.subTest(phase=changed_phase):
                with self.history():
                    # The observer must see a committed synthetic subject;
                    # otherwise declaration drift stops it before this gate.
                    self.commit(contract)
                    report = self.assess(contract, observer)
                    self.assertNotIn(case['id'], report['acceptedCases'])
                    self.assertTrue(report['caseRejections'][case['id']])
                    self.assertFalse(report['candidateEligible'])

    def test_ended_fixed_sdk_cases_preserve_original_definitions_and_scope_floors(self):
        from yiyuan_accord.admission import _definition
        record = next(row for row in self.historical_contract()['developmentObservations']
                      if row['id'] == 'ended-fixed-sdk-case-disposition-20261005')
        historical = json.loads(subprocess.check_output([
            'git', '-C', str(self.root), 'show', record['declarations'][0]['declarationSnapshot']],
            env=development_fixtures.owned_git_environment(), timeout=30))
        policy = self.contract['acceptance']['admission']
        self.assertEqual(record['outcome'], 'not-admitted')
        self.assert_preserved_requirements_with_current_outcomes(historical['acceptance']['admission'])
        for declaration in record['declarations']:
            with self.subTest(case=declaration['caseId']):
                old = next(row for row in historical['acceptance']['admission']['cases']
                           if row['id'] == declaration['caseId'])
                digest = hashlib.sha256(json.dumps(old, sort_keys=True, separators=(',', ':'),
                                                   ensure_ascii=False).encode()).hexdigest()
                self.assertEqual(digest, declaration['caseObjectSha256'])
                self.assertEqual(_definition(historical, old), declaration['definitionSha256'])
                self.assertNotIn(old['id'], {row['id'] for row in policy['cases']})
                self.assertEqual(declaration['attempts'], 1)
                self.assertEqual(declaration['limits']['timeoutSeconds'], 600)
                self.assertEqual(declaration['limits']['turnTimeoutSeconds'], 240)
                self.assertEqual(declaration['limits']['recoveryTimeoutSeconds'], 20)
                scope = next(row for row in policy['scopes'] if row['id'] == old['scope'])
                prior = next(row for row in historical['acceptance']['admission']['scopes']
                             if row['id'] == old['scope'])
                # Routing prose may evolve.
                scope, prior = copy.deepcopy((scope, prior))
                if 'entryScope' in prior['conditions']:
                    route = scope['conditions'].pop('entryScope')
                    prior['conditions'].pop('entryScope')
                    self.assertIsInstance(route, str)
                    self.assertIn('v33-openai-entry-applicability', route)
                self.assertEqual(scope, prior)
                prior_fixture = subprocess.check_output(['git', '-C', str(self.root), 'show',
                                                        record['declarations'][0]['declarationSnapshot'].split(':')[0]
                                                        + ':' + declaration['caseFile']],
                                                        env=development_fixtures.owned_git_environment(), timeout=30)
                self.assertEqual((self.root / declaration['caseFile']).read_bytes(), prior_fixture)
        report = self.assess()
        self.assertFalse(report['functionalCompletion'])
        self.assertFalse(report['candidateEligible'])
        self.assertIn('v33-system-integration', report['acceptanceRequirements']['A08']['missingScopes']['function'])
        self.assertEqual(report['caseBindingGaps'], self.source_case_binding_gaps(self.contract)[0])
        self.assertIn('v33-dynamic-model-routing',
                      report['acceptanceRequirements']['A02']['missingScopes']['function'])

    def test_execution_fixtures_match_their_bound_source_revisions(self):
        from yiyuan_accord.admission import _definition
        # These two immutable executions were observed at this exact subject.
        # New deadline/resource handling in HEAD does not re-execute old work.
        revision = 'd855cd0936733960cd107168a3369963a65d874a'
        definitions = {
            'v33-codex-sdk-lifecycle-01': 'd82650fd8449a9501e9eb0c8c4bb5f766233cd220390418bcd9cdd4da1708793',
            'v33-codex-sdk-scoped-exposure-01': '4523db05acee328aa1510214744c84df90913673c3952f5572025d66952b466d',
        }
        original = json.loads(subprocess.check_output(
            ['git', '-C', str(self.root), 'show', revision + ':' + DEVELOPMENT_FILE],
            env=development_fixtures.owned_git_environment(), timeout=30))
        checked = set()
        for case in self.contract['acceptance']['admission']['cases']:
            source_revision = 'HEAD'
            if case['id'] in definitions:
                source_revision = revision
                bound = next(row for row in original['acceptance']['admission']['cases'] if row['id'] == case['id'])
                self.assertEqual(case, bound)
                self.assertEqual(_definition(original, bound), definitions[case['id']])
            pending = [case['conditions'].get('execution')]
            while pending:
                value = pending.pop()
                if isinstance(value, list):
                    pending.extend(value)
                    continue
                if not isinstance(value, dict):
                    continue
                pending.extend(item for item in value.values() if isinstance(item, (dict, list)))
                if not {'runner', 'caseFile', 'caseSha256'} <= set(value):
                    continue
                with self.subTest(case=case['id'], fixture=value['caseFile']):
                    self.assertIn(value['caseFile'], case['oracleFiles'])
                    raw = subprocess.check_output(
                        ['git', '-C', str(self.root), 'show', source_revision + ':' + value['caseFile']],
                        env=development_fixtures.owned_git_environment(), timeout=30)
                    self.assertEqual(value['caseSha256'], hashlib.sha256(raw).hexdigest())
                    if source_revision != 'HEAD':
                        current = subprocess.check_output(
                            ['git', '-C', str(self.root), 'show', 'HEAD:' + value['caseFile']],
                            env=development_fixtures.owned_git_environment(), timeout=30)
                        self.assertNotEqual(hashlib.sha256(current).hexdigest(), value['caseSha256'])
                checked.add(case['id'])
        self.assertTrue({'v33-codex-sdk-lifecycle-01', 'v33-codex-sdk-scoped-exposure-01'} <= checked)

    def test_ended_release_case_preserves_failure_identity_and_continuity_floor(self):
        from yiyuan_accord.admission import _definition
        record = next(row for row in self.historical_contract()['developmentObservations']
                      if row['id'] == 'ended-release-ack-case-disposition-20261006')
        declaration = record['declarations'][0]
        historical = json.loads(subprocess.check_output([
            'git', '-C', str(self.root), 'show', declaration['declarationSnapshot']],
            env=development_fixtures.owned_git_environment(), timeout=30))
        policy = self.contract['acceptance']['admission']
        old = next(row for row in historical['acceptance']['admission']['cases']
                   if row['id'] == declaration['caseId'])
        self.assertNotIn(old['id'], {row['id'] for row in policy['cases']})
        self.assertEqual(record['executionVerdict'], 'failed')
        self.assertEqual(record['outcome'], 'not-admitted')
        self.assertTrue(record['originalAuthority']['consumed'])
        self.assertFalse(record['originalAuthority']['replayAllowed'])
        self.assertEqual(declaration['attempts'], 1)
        self.assertEqual(declaration['caseObjectSha256'], hashlib.sha256(json.dumps(
            old, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest())
        self.assertEqual(declaration['definitionSha256'], _definition(historical, old))
        for key, value in declaration['limits'].items():
            self.assertEqual(value, old['conditions']['execution'][key])
        original_file = subprocess.check_output(['git', '-C', str(self.root), 'show',
            declaration['declarationSnapshot'].split(':')[0] + ':' + declaration['caseFile']],
            env=development_fixtures.owned_git_environment(), timeout=30)
        self.assertEqual((self.root / declaration['caseFile']).read_bytes(), original_file)
        self.assertEqual(hashlib.sha256(original_file).hexdigest(), declaration['caseFileSha256'])
        self.assert_preserved_requirements_with_current_outcomes(historical['acceptance']['admission'])
        prior_scopes = {row['id']: row for row in historical['acceptance']['admission']['scopes']}
        self.assertEqual({row['id'] for row in policy['scopes']}, set(prior_scopes))
        for scope in policy['scopes']:
            prior = prior_scopes[scope['id']]
            # This ended instance freezes its own identity, definition, limits
            # and failure (above), not every later parent's implementation or
            # user-selected subjects. Current outcome/quality floors remain.
            floor_keys = ('id', 'host', 'duties', 'qualityAxes', 'scenarios', 'claims')
            self.assertEqual({key: scope[key] for key in floor_keys},
                             {key: prior[key] for key in floor_keys})
        report = self.assess()
        self.assertEqual(report['acceptedCases'], [])
        self.assertFalse(report['functionalCompletion'])
        self.assertFalse(report['candidateEligible'])
        gap = report['openCoverage']['v33-autonomous-continuity']['claims']['function']
        scope = next(s for s in policy['scopes'] if s['id'] == 'v33-autonomous-continuity')
        self.assertEqual(set(gap['duties']), set(scope['duties']))
        self.assertEqual(set(gap['scenarios']), set(scope['scenarios']))
        self.assertFalse(report['acceptanceRequirements']['A05']['complete'])
        self.assertIn('A05', report['acceptanceRequirements']['A08']['blockedBy'])

    def test_ended_ordinary_instances_keep_history_without_erasing_live_scope(self):
        from yiyuan_accord.admission import _definition
        record = next(row for row in development_observations(self.root, self.contract)
                      if row['id'] == 'ended-ordinary-cli-case-disposition-20261017')
        policy = self.contract['acceptance']['admission']
        historical = json.loads(subprocess.check_output(['git', '-C', str(self.root), 'show',
            record['declarations'][0]['declarationSnapshot']],
            env=development_fixtures.owned_git_environment(), timeout=30))
        prior = historical['acceptance']['admission']
        ended = {row['caseId'] for row in record['declarations']}
        self.assertEqual(ended, {'v33-cli-action-diagnostics-01', 'v33-cli-tool-recovery-01'})
        self.assertEqual(record['outcome'], 'not-admitted')
        self.assertFalse(ended & {c['id'] for c in policy['cases']})
        for row in record['declarations']:
            old = next(c for c in prior['cases'] if c['id'] == row['caseId'])
            self.assertEqual(row['outcome'], 'not-admitted')
            self.assertFalse(row['replayAllowed'])
            self.assertEqual(row['definitionSha256'], _definition(historical, old))
            self.assertEqual(row['caseObjectSha256'], hashlib.sha256(json.dumps(
                old, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest())
            if 'caseFile' in row:
                original = subprocess.check_output(['git', '-C', str(self.root), 'show',
                    row['declarationSnapshot'].split(':')[0] + ':' + row['caseFile']],
                    env=development_fixtures.owned_git_environment(), timeout=30)
                self.assertEqual((self.root / row['caseFile']).read_bytes(), original)
                self.assertEqual(hashlib.sha256(original).hexdigest(), row['caseFileSha256'])
                self.assertEqual(row['execution'], old['conditions']['execution'])
        self.assert_preserved_requirements_with_current_outcomes(prior)
        # Freeze ended evidence, not future cases, host methods or routing prose.
        sid = 'v33-codex-cli-ordinary-delivery'
        scope = next(s for s in policy['scopes'] if s['id'] == sid)
        old_scope = next(s for s in prior['scopes'] if s['id'] == sid)
        for key in ('duties', 'qualityAxes', 'scenarios', 'claims'):
            self.assertEqual(scope[key], old_scope[key])
        self.assert_current_declaration_reports_missing_coverage(self.contract)

    def test_partial_allocation_case_keeps_uncovered_duties_and_scenarios_open(self):
        contract = self.without_resource_and_environment_cases()
        policy = contract['acceptance']['admission']
        scope = next(row for row in policy['scopes'] if row['id'] == 'v33-dynamic-model-routing')
        case = copy.deepcopy(policy['cases'][0])
        # Test an explicit unallocated baseline, independent of current real
        # episodes. Adding another case must not silently widen this fixture.
        policy['cases'] = [row for row in policy['cases'] if row['scope'] != scope['id']]
        case.pop('packageFiles', None)
        case.update(id='partial-allocation-fixture', scope=scope['id'], host=scope['host'], entry=scope['entry'],
                    claims=['function'], conditions=copy.deepcopy(scope['conditions']),
                    duties=[scope['duties'][0]], qualityAxes=[scope['qualityAxes'][0]],
                    scenarios=['native-sufficient'])
        policy['cases'].append(case)
        report = self.assess(contract)
        self.assertEqual(report['errors'], [])
        gap = report['caseBindingGaps'][scope['id']]['function']
        self.assertEqual(set(gap['caseIds']), {case['id']})
        self.assertTrue(gap['missingDimensions']['duties'])
        self.assertIn('capability-loss', gap['missingDimensions']['scenarios'])
        self.assertIn('default-host-without-extra-extensions', gap['missingDimensions']['scenarios'])
        self.assertEqual(report['progress']['coverageWithoutCases'], 5)
        self.assertEqual(report['progress']['coverageWithCaseBindingGaps'], 7)
        self.assertEqual(report['acceptedCases'], [])
        self.assertFalse(report['functionalCompletion'])

    def test_diagnostic_retains_unplanned_scope_and_scenario_gaps(self):
        contract = self.without_correction_and_user_environment_cases()
        # This negative explicitly asks for an unplanned allocation scope.
        contract['acceptance']['admission']['cases'] = [case for case in
            contract['acceptance']['admission']['cases'] if case['scope'] != 'v33-dynamic-model-routing']
        report = self.assess(contract)
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['progress']['coverageWithoutCases'], 7)
        self.assertEqual(report['progress']['coverageWithCaseBindingGaps'], 9)
        gaps = report['caseBindingGaps']
        self.assertEqual(set(gaps), {'v33-systemic-correction', 'v33-codex-cli-ordinary-delivery',
                                    'v33-dynamic-model-routing', 'v33-autonomous-continuity',
                                    'v33-system-integration',
                                    'v33-codex-lifecycle', 'v33-system-impact-assessment',
                                    'v33-resource-pressure-and-exit', 'v33-environment-adaptation'})
        correction = gaps['v33-systemic-correction']['function']
        self.assertEqual(correction['caseIds'], [])
        self.assertTrue(correction['missingDimensions']['duties'])
        delivery = gaps['v33-codex-cli-ordinary-delivery']['function']
        self.assertEqual(delivery['caseIds'], ['v33-codex-cli-ordinary-delivery-01'])
        self.assertEqual(delivery['missingDimensions']['scenarios'], ['effective-user-environment'])
        self.assertFalse(delivery['jointCaseMissing'])

    def test_case_bindings_do_not_count_as_accepted_evidence(self):
        contract = self.without_correction_and_user_environment_cases()
        case = next(c for c in contract['acceptance']['admission']['cases']
                    if c['scope'] == 'v33-codex-cli-ordinary-delivery')
        case['scenarios'].append('effective-user-environment')
        report = self.assess(contract)
        self.assertEqual(report['errors'], [])
        self.assertNotIn('v33-codex-cli-ordinary-delivery', report['caseBindingGaps'])
        self.assertEqual(report['progress']['coverageWithCaseBindingGaps'], 8)
        continuity = report['caseBindingGaps']['v33-autonomous-continuity']['function']
        self.assertEqual(continuity['caseIds'], ['v33-continuity-catalog-01'])
        self.assertEqual(continuity['missingDimensions'],
                         {'duties': ['recovery-and-rollback'], 'qualityAxes': [],
                          'scenarios': ['capability-loss']})
        for scope in ('v33-resource-pressure-and-exit', 'v33-environment-adaptation'):
            self.assertEqual(report['caseBindingGaps'][scope]['function']['caseIds'], [])
        self.assertEqual(report['progress']['coverageVerified'], 0)
        self.assertEqual(report['acceptedCases'], [])
        self.assertFalse(report['candidateEligible'])

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

    def test_entry_parent_contract_rejects_omissions_and_cross_scope_drift(self):
        from yiyuan_accord.admission import admission_contract_errors
        parent_ids = {"v33-openai-entry-applicability", "v33-admitted-entry-delivery",
                      "v33-admitted-entry-lifecycle"}
        def parts(contract, scope_id):
            policy = contract["acceptance"]["admission"]
            return (next(row for row in policy["scopes"] if row["id"] == scope_id),
                    next(row for row in policy["cases"] if row["scope"] == scope_id))
        variants = []
        missing_candidate = copy.deepcopy(self.contract)
        for scope_id in parent_ids:
            scope, case = parts(missing_candidate, scope_id)
            scope["conditions"]["entryDispositions"].pop("cx-xcode")
            case["conditions"]["entryDispositions"].pop("cx-xcode")
        scope, case = parts(missing_candidate, "v33-openai-entry-applicability")
        scope["subjectEntries"].remove("cx-xcode")
        case["subjectEntries"].remove("cx-xcode")
        case["expected"]["effect"]["entryApplicability"].pop("cx-xcode")
        variants.append(missing_candidate)
        missing_selected = copy.deepcopy(self.contract)
        scope, case = parts(missing_selected, "v33-admitted-entry-delivery")
        scope["subjectEntries"].remove("cx-vscode")
        case["subjectEntries"].remove("cx-vscode")
        case["expected"]["effect"]["entryDelivery"].pop("cx-vscode")
        variants.append(missing_selected)
        missing_expected = copy.deepcopy(self.contract)
        parts(missing_expected, "v33-admitted-entry-lifecycle")[1]["expected"]["effect"]["entryLifecycle"].pop("cx-sdk")
        variants.append(missing_expected)
        empty_expected = copy.deepcopy(self.contract)
        parts(empty_expected, "v33-admitted-entry-delivery")[1]["expected"]["effect"]["entryDelivery"]["cx-cli"] = {}
        variants.append(empty_expected)
        changed_conditions = copy.deepcopy(self.contract)
        scope, case = parts(changed_conditions, "v33-admitted-entry-delivery")
        scope["conditions"]["entryDispositions"]["cx-cli"]["basis"] += " Changed."
        case["conditions"] = copy.deepcopy(scope["conditions"])
        variants.append(changed_conditions)
        for contract in variants:
            with self.subTest(error=admission_contract_errors(contract)):
                self.assertTrue(admission_contract_errors(contract))

    def test_entry_parent_cases_stay_unaccepted_until_selection_is_final(self):
        parent_ids = {"v33-openai-entry-applicability", "v33-admitted-entry-delivery",
                      "v33-admitted-entry-lifecycle"}
        for selection_final, clear_pending in ((False, False), (True, False), (False, True)):
            contract = copy.deepcopy(self.contract)
            policy = contract["acceptance"]["admission"]
            for row in [*policy["scopes"], *policy["cases"]]:
                if row.get("scope", row.get("id")) not in parent_ids:
                    continue
                row["conditions"]["selectionFinal"] = selection_final
                # Construct the unresolved row explicitly; the current baseline is final.
                row["conditions"]["entryDispositions"]["cx-jetbrains"]["status"] = "pending"
                if clear_pending:
                    for disposition in row["conditions"]["entryDispositions"].values():
                        if disposition["status"] == "pending":
                            disposition["status"] = "deferred"
                        for mode in disposition.get("modes", {}).values():
                            if mode["status"] == "pending":
                                mode["status"] = "deferred"
            with self.subTest(selectionFinal=selection_final, clearPending=clear_pending), self.history():
                self.commit(contract)
                report = self.assess(contract, self.observer)
            parent_cases = {case["id"] for case in policy["cases"] if case["scope"] in parent_ids}
            self.assertFalse(parent_cases & set(report["acceptedCases"]))
            self.assertFalse(report["entrySelection"]["final"])
            self.assertFalse(report["acceptanceRequirements"]["A02"]["complete"])

    def test_final_entry_selection_can_admit_all_three_parent_cases(self):
        contract = copy.deepcopy(self.contract)
        parent_ids = {"v33-openai-entry-applicability", "v33-admitted-entry-delivery",
                      "v33-admitted-entry-lifecycle"}
        policy = contract["acceptance"]["admission"]
        for row in [*policy["scopes"], *policy["cases"]]:
            scope_id = row.get("scope", row.get("id"))
            if scope_id not in parent_ids:
                continue
            row["conditions"]["selectionFinal"] = True
            for disposition in row["conditions"]["entryDispositions"].values():
                if disposition["status"] == "pending":
                    disposition["status"] = "deferred"
                for mode in disposition.get("modes", {}).values():
                    if mode["status"] == "pending":
                        mode["status"] = "deferred"
        with self.history():
            self.commit(contract)
            report = self.assess(contract, self.observer)
        parent_cases = {case["id"] for case in policy["cases"] if case["scope"] in parent_ids}
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["entrySelection"]["final"])
        self.assertTrue(parent_cases <= set(report["acceptedCases"]))
        self.assertIn("v33-codex-entry-coverage-01", report["acceptedCases"])

    def test_selected_entry_pending_mode_still_blocks_all_parent_admission(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        for row in [*policy["scopes"], *policy["cases"]]:
            if "entryDispositions" not in row["conditions"]:
                continue
            row["conditions"]["selectionFinal"] = True
            for key, disposition in row["conditions"]["entryDispositions"].items():
                if disposition["status"] == "pending":
                    disposition["status"] = "deferred"
                for mode, value in disposition.get("modes", {}).items():
                    if (key, mode) == ("chatgpt-desktop", "work-local"):
                        value["status"] = "pending"
                    elif value["status"] == "pending":
                        value["status"] = "deferred"
            if row.get("scope") in {"v33-admitted-entry-delivery", "v33-admitted-entry-lifecycle"}:
                for mapping in row["expected"]["effect"].values():
                    mapping["chatgpt-desktop"]["modes"].pop("work-local")
        for case in policy["cases"]:
            if case["scope"] == "v33-codex-entry-coverage":
                case["conditions"]["selectedModes"]["chatgpt-desktop"].remove("work-local")
                case["expected"]["effect"]["entryCapabilityCoverage"]["chatgpt-desktop"]["modes"].pop("work-local")
        self.sync_selected_cases(policy)
        with self.history():
            self.commit(contract)
            report = self.assess(contract, self.observer)
        self.assertEqual(report["errors"], [])
        self.assertFalse(report["entrySelection"]["final"])
        self.assertEqual(report["entrySelection"]["pendingModes"]["chatgpt-desktop"], ["work-local"])
        self.assertEqual(report["entrySelection"]["selectedModes"]["chatgpt-desktop"], ["remote"])
        self.assertFalse({"v33-openai-entry-applicability-01", "v33-admitted-entry-delivery-01",
                          "v33-admitted-entry-lifecycle-01", "v33-codex-entry-coverage-01"}
                         & set(report["acceptedCases"]))

    def test_task_relative_chat_candidate_does_not_count_as_selected_delivery(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        for row in [*policy["scopes"], *policy["cases"]]:
            if "entryDispositions" not in row["conditions"]:
                continue
            row["conditions"]["selectionFinal"] = True
            for key, disposition in row["conditions"]["entryDispositions"].items():
                if key == "chatgpt-web":
                    disposition["status"] = "pending"
                elif disposition["status"] == "pending":
                    disposition["status"] = "deferred"
                for mode, value in disposition.get("modes", {}).items():
                    if mode == "chat":
                        value["status"] = "pending"
                    elif value["status"] == "pending":
                        value["status"] = "deferred"
        with self.history():
            self.commit(contract)
            report = self.assess(contract, self.observer)
        self.assertEqual(report["errors"], [])
        selection = report["entrySelection"]
        self.assertFalse(selection["final"])
        self.assertEqual(len(selection["selected"]), 6)
        self.assertNotIn("chatgpt-web", selection["selected"])
        for key in ("chatgpt-desktop", "chatgpt-mobile", "chatgpt-web"):
            self.assertEqual(selection["pendingModes"][key], ["chat"])
            self.assertNotIn("chat", selection["selectedModes"][key])
        self.assertFalse({"v33-openai-entry-applicability-01", "v33-admitted-entry-delivery-01",
                          "v33-admitted-entry-lifecycle-01"} & set(report["acceptedCases"]))
        self.assertFalse(report["acceptanceRequirements"]["A02"]["complete"])

    def entry_coverage_contract(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        if any(case["scope"] == "v33-codex-entry-coverage" for case in policy["cases"]):
            return contract
        scope = next(row for row in policy["scopes"] if row["id"] == "v33-codex-entry-coverage")
        parent = next(row for row in policy["cases"] if row["scope"] == "v33-admitted-entry-delivery")
        facets = ("discoveryDenominatorBound", "officialAndActualSourcesReconciled",
                  "zeroUnexplainedOmissions", "capabilityDispositionsSupported",
                  "necessaryCapabilityUseVerified", "authorityAndExitPathsAccounted",
                  "unavailableAndSufficientNativeCounterexamplesPreserved", "changedUserOrHostStateReconciled")
        subjects = list(parent["subjectEntries"])
        modes = {key: [mode for mode, row in parent["conditions"]["entryDispositions"][key].get("modes", {}).items()
                       if row["status"] == "selected"] for key in subjects}
        matrix = {key: {facet: True for facet in facets} for key in subjects}
        for key, values in modes.items():
            if values:
                matrix[key]["modes"] = {mode: {facet: True for facet in facets} for mode in values}
        policy["cases"].append({
            "id": "v33-codex-entry-coverage-01", "scope": scope["id"],
            **{key: scope[key] for key in ("host", "entry", "duties", "qualityAxes", "scenarios", "claims")},
            "conditions": {**scope["conditions"], "subjectEntries": subjects, "selectedModes": modes},
            "oracle": "Independently reconcile bound sources, actual subjects and necessary capability use.",
            "oracleFiles": ["docs/operations/PLAN-v3.3.md", "docs/operations/ACCEPTANCE-v3.3.md"],
            "maxAgeSeconds": 86400,
            "expected": {"effect": {"entryCapabilityCoverage": matrix},
                         "authority": {"currentSelectionRespected": True},
                         "poststate": {"selectionFinal": True},
                         "cleanup": {"unrelatedStateUnchanged": True}},
        })
        return contract

    def sync_selected_cases(self, policy):
        conditions = next(c['conditions'] for c in policy['cases'] if c['scope'] == 'v33-codex-entry-coverage')
        for case in policy['cases']:
            for key in ('subjectEntries', 'selectedModes'):
                if key in case['conditions']:
                    case['conditions'][key] = copy.deepcopy(conditions[key])

    def test_entry_coverage_rejects_missing_stale_and_weakened_matrices(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract = self.entry_coverage_contract()
        self.assertEqual(admission_contract_errors(contract), [])
        for variant in ("missing-effect", "shrunk-both", "missing-mode", "pending-chat",
                        "pending-web", "weakened-facet", "stale-source"):
            changed = copy.deepcopy(contract)
            policy = changed["acceptance"]["admission"]
            case = next(row for row in policy["cases"] if row["scope"] == "v33-codex-entry-coverage")
            rows = case["expected"]["effect"]["entryCapabilityCoverage"]
            if variant in ("missing-effect", "shrunk-both"):
                rows.pop("cx-sdk")
                if variant == "shrunk-both":
                    case["conditions"]["subjectEntries"].remove("cx-sdk")
                    case["conditions"]["selectedModes"].pop("cx-sdk")
            elif variant == "missing-mode":
                rows["chatgpt-desktop"]["modes"].pop("remote")
            elif variant == "pending-chat":
                case["conditions"]["selectedModes"]["chatgpt-desktop"].append("chat")
                rows["chatgpt-desktop"]["modes"]["chat"] = {"discoveryDenominatorBound": True}
            elif variant == "pending-web":
                case["conditions"]["subjectEntries"].append("chatgpt-web")
                case["conditions"]["selectedModes"]["chatgpt-web"] = []
                rows["chatgpt-web"] = copy.deepcopy(rows["cx-cli"])
            elif variant == "weakened-facet":
                for row in rows.values():
                    row.pop("necessaryCapabilityUseVerified")
                    for value in row.get("modes", {}).values():
                        value.pop("necessaryCapabilityUseVerified")
            else:
                for row in [*policy["scopes"], *policy["cases"]]:
                    if "entryDispositions" not in row["conditions"]:
                        continue
                    row["conditions"]["entryDispositions"]["cx-sdk"]["status"] = "deferred"
                    if row.get("scope", row.get("id")) != "v33-openai-entry-applicability":
                        row["subjectEntries"].remove("cx-sdk")
                    if row.get("scope") in ("v33-admitted-entry-delivery", "v33-admitted-entry-lifecycle"):
                        next(iter(row["expected"]["effect"].values())).pop("cx-sdk")
            with self.subTest(variant=variant):
                self.assertTrue(admission_contract_errors(changed))

    def test_entry_coverage_waits_for_selection_and_binds_its_source(self):
        from yiyuan_accord.admission import _definition
        contract = self.entry_coverage_contract()
        for row in [*contract['acceptance']['admission']['scopes'],
                    *contract['acceptance']['admission']['cases']]:
            if 'entryDispositions' in row['conditions']:
                row['conditions']['selectionFinal'] = False
        case = next(row for row in contract["acceptance"]["admission"]["cases"]
                    if row["scope"] == "v33-codex-entry-coverage")
        before = _definition(contract, case)
        changed = copy.deepcopy(contract)
        for row in [*changed["acceptance"]["admission"]["scopes"], *changed["acceptance"]["admission"]["cases"]]:
            if "entryDispositions" in row["conditions"]:
                row["conditions"]["entryDispositions"]["cx-cli"]["basis"] += " Updated supported source."
        self.assertNotEqual(before, _definition(changed, case))
        with self.history():
            self.commit(contract)
            report = self.assess(contract, self.observer)
        self.assertEqual(report["errors"], [])
        self.assertNotIn(case["id"], report["acceptedCases"])

    def test_entry_coverage_accepts_reordered_and_rebound_selection(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract = self.entry_coverage_contract()
        policy = contract["acceptance"]["admission"]
        case = next(row for row in policy["cases"] if row["scope"] == "v33-codex-entry-coverage")
        case["conditions"]["subjectEntries"].reverse()
        for values in case["conditions"]["selectedModes"].values():
            values.reverse()
        self.assertEqual(admission_contract_errors(contract), [])
        for row in [*policy["scopes"], *policy["cases"]]:
            if "entryDispositions" not in row["conditions"]:
                continue
            row["conditions"]["entryDispositions"]["cx-sdk"]["status"] = "deferred"
            if row.get("scope", row.get("id")) != "v33-openai-entry-applicability":
                row["subjectEntries"].remove("cx-sdk")
            if row.get("scope") in ("v33-admitted-entry-delivery", "v33-admitted-entry-lifecycle"):
                next(iter(row["expected"]["effect"].values())).pop("cx-sdk")
        self.assertTrue(admission_contract_errors(contract))
        case["conditions"]["subjectEntries"].remove("cx-sdk")
        case["conditions"]["selectedModes"].pop("cx-sdk")
        case["expected"]["effect"]["entryCapabilityCoverage"].pop("cx-sdk")
        self.sync_selected_cases(policy)
        self.assertEqual(admission_contract_errors(contract), [])
        case["duties"] = case["duties"][:1]
        case["qualityAxes"] = case["qualityAxes"][:1]
        self.assertEqual(admission_contract_errors(contract), [])

    def lifecycle_binding_contract(self, scope_id='v33-codex-lifecycle'):
        contract = copy.deepcopy(self.contract)
        policy = contract['acceptance']['admission']
        scope = next(row for row in policy['scopes'] if row['id'] == scope_id)
        parent = next(row for row in policy['cases'] if row['scope'] == 'v33-admitted-entry-lifecycle')
        case = copy.deepcopy(parent)
        subjects = case.pop('subjectEntries')
        modes = {key: [mode for mode, row in parent['conditions']['entryDispositions'][key].get('modes', {}).items()
                       if row['status'] == 'selected'] for key in subjects}
        case.update(id='fixture-host-lifecycle', scope=scope['id'],
                    **{key: copy.deepcopy(scope[key]) for key in
                       ('host', 'entry', 'duties', 'qualityAxes', 'scenarios', 'claims')},
                    conditions={**copy.deepcopy(scope['conditions']), 'subjectEntries': subjects, 'selectedModes': modes},
                    oracle='Synthetic source/selection binding only; not whole-host lifecycle adequacy or observations.')
        policy['cases'].append(case)
        return contract

    def test_integration_rejects_incomplete_or_stale_selection(self):
        from yiyuan_accord.admission import _entry_selection, admission_contract_errors
        contract = self.lifecycle_binding_contract('v33-system-integration')
        self.assertEqual(admission_contract_errors(contract), [])
        for variant in ('missing-subject', 'missing-modes', 'missing-mode', 'unknown-mode', 'pending-mode',
                        'missing-applicability'):
            changed = copy.deepcopy(contract)
            policy = changed['acceptance']['admission']
            conditions = policy['cases'][-1]['conditions']
            if variant == 'missing-subject':
                conditions['subjectEntries'].remove('cx-sdk')
                conditions['selectedModes'].pop('cx-sdk')
            elif variant == 'missing-modes':
                conditions.pop('selectedModes')
            elif variant == 'missing-mode':
                conditions['selectedModes']['chatgpt-desktop'].remove('remote')
            elif variant == 'missing-applicability':
                policy['scopes'] = []
                policy['cases'] = [policy['cases'][-1]]
                with self.assertRaisesRegex(ValueError, 'requires the applicability selection'):
                    _entry_selection(policy, {})
                continue
            else:
                conditions['selectedModes']['chatgpt-desktop'].append(
                    'chat' if variant == 'pending-mode' else 'invented')
            with self.subTest(variant=variant):
                self.assertTrue(admission_contract_errors(changed))

    def test_integration_definition_binds_selection_sources(self):
        from yiyuan_accord.admission import _definition, _reuse_definition, admission_contract_errors
        contract = self.lifecycle_binding_contract('v33-system-integration')
        case = contract['acceptance']['admission']['cases'][-1]
        original = _definition(contract, case)
        for source in ('basis', 'subject', 'mode-catalog'):
            changed = copy.deepcopy(contract)
            surfaces = changed['capabilityMap']['entrySurfaces']
            if source == 'basis':
                policy = changed['acceptance']['admission']
                for row in [*policy['scopes'], *policy['cases']]:
                    if 'entryDispositions' in row['conditions']:
                        row['conditions']['entryDispositions']['cx-cli']['basis'] += ' Revised source.'
            elif source == 'subject':
                next(row for row in surfaces['rows'] if row['id'] == 'chatgpt-desktop')['execution'] += ' Revised source.'
            else:
                surfaces['modeCatalog']['chatgpt-desktop'].reverse()
            with self.subTest(source=source):
                self.assertEqual(admission_contract_errors(changed), [])
                self.assertNotEqual(original, _definition(changed, case))
                if source == 'mode-catalog':
                    self.assertEqual(_reuse_definition(contract, case), _reuse_definition(changed, case))

    def test_integration_complete_evidence_waits_for_final_selection(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract = self.lifecycle_binding_contract('v33-system-integration')
        policy = contract['acceptance']['admission']
        case = policy['cases'][-1]
        case['conditions']['subjectEntries'].reverse()
        for modes in case['conditions']['selectedModes'].values(): modes.reverse()
        for final, pending in ((False, False), (True, True), (True, False)):
            for row in [*policy['scopes'], *policy['cases']]:
                if 'entryDispositions' not in row['conditions']: continue
                row['conditions']['selectionFinal'] = final
                for disposition in row['conditions']['entryDispositions'].values():
                    if disposition['status'] == 'pending': disposition['status'] = 'deferred'
                    for mode in disposition.get('modes', {}).values():
                        if mode['status'] == 'pending': mode['status'] = 'deferred'
                row['conditions']['entryDispositions']['chatgpt-desktop']['modes']['chat']['status'] = (
                    'pending' if pending else 'deferred')
            with self.subTest(final=final, pending=pending), self.history():
                self.assertEqual(admission_contract_errors(contract), [])
                self.commit(contract)
                report = self.assess(contract, self.observer)
                self.assertEqual(report['errors'], [])
                self.assertEqual(case['id'] in report['acceptedCases'], final and not pending)
                self.assertEqual(report['entrySelection']['final'], final and not pending)
                self.assertEqual(report['caseRejections'].get(case['id'], []),
                                 [] if final and not pending else ['entry-selection-pending'])

    def test_integration_reuse_preserves_set_meaning_and_business_order(self):
        from yiyuan_accord.admission import _definition, _reuse_definition, admission_contract_errors
        contract = self.lifecycle_binding_contract('v33-system-integration')
        case = contract['acceptance']['admission']['cases'][-1]
        case['conditions']['actions'] = ['inspect', 'deliver']
        original = copy.deepcopy(contract)
        stored, reusable = _definition(contract, case), _reuse_definition(contract, case)
        for variant in ('subjects-reordered', 'modes-reordered', 'subject-removed', 'mode-removed', 'actions-reordered'):
            changed = copy.deepcopy(contract)
            target = changed['acceptance']['admission']['cases'][-1]
            conditions = target['conditions']
            if variant == 'subjects-reordered': conditions['subjectEntries'].reverse()
            elif variant == 'modes-reordered': conditions['selectedModes']['chatgpt-desktop'].reverse()
            elif variant == 'subject-removed':
                conditions['subjectEntries'].remove('cx-sdk')
                conditions['selectedModes'].pop('cx-sdk')
            elif variant == 'mode-removed': conditions['selectedModes']['chatgpt-desktop'].remove('remote')
            else: conditions['actions'].reverse()
            with self.subTest(variant=variant):
                self.assertNotEqual(stored, _definition(changed, target))
                self.assertEqual(bool(admission_contract_errors(changed)), variant.endswith('-removed'))
                self.assertEqual(reusable == _reuse_definition(changed, target),
                                 variant in ('subjects-reordered', 'modes-reordered'))
        self.assertEqual(contract, original)
        self.assertEqual(_definition(contract, case), stored)

    def test_host_lifecycle_cannot_close_while_entry_selection_is_pending(self):
        contract = self.lifecycle_binding_contract()
        policy = contract['acceptance']['admission']
        for row in [*policy['scopes'], *policy['cases']]:
            if 'entryDispositions' in row['conditions']:
                row['conditions']['entryDispositions']['cx-jetbrains']['status'] = 'pending'
        with self.history():
            self.commit(contract)
            report = self.assess(contract, self.observer)
        self.assertEqual(report['errors'], [])
        self.assertNotIn('fixture-host-lifecycle', report['acceptedCases'])
        self.assertIn('v33-codex-lifecycle', report['acceptanceRequirements']['A06']['missingScopes']['package-lifecycle'])

    def test_host_lifecycle_rejects_stale_subject_and_mode_bindings(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract = self.lifecycle_binding_contract()
        self.assertEqual(admission_contract_errors(contract), [])
        for variant in ('missing-subject', 'missing-mode', 'pending-mode', 'unknown-mode'):
            changed = copy.deepcopy(contract)
            case = changed['acceptance']['admission']['cases'][-1]
            if variant == 'missing-subject':
                case['conditions']['subjectEntries'].remove('cx-sdk')
                case['conditions']['selectedModes'].pop('cx-sdk')
            elif variant == 'missing-mode':
                case['conditions']['selectedModes']['chatgpt-desktop'].remove('remote')
            else:
                case['conditions']['selectedModes']['chatgpt-desktop'].append('chat' if variant == 'pending-mode' else 'invented')
            with self.subTest(variant=variant):
                self.assertTrue(admission_contract_errors(changed))

    def test_host_lifecycle_definition_depends_on_applicability_source(self):
        from yiyuan_accord.admission import _definition
        contract = self.lifecycle_binding_contract()
        case = contract['acceptance']['admission']['cases'][-1]
        old = _definition(contract, case)
        changed = copy.deepcopy(contract)
        for row in [*changed['acceptance']['admission']['scopes'], *changed['acceptance']['admission']['cases']]:
            if 'entryDispositions' in row['conditions']:
                row['conditions']['entryDispositions']['cx-cli']['basis'] += ' Changed supported source.'
        self.assertNotEqual(_definition(changed, case), old)

    def test_host_lifecycle_accepts_final_reordered_binding(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract = self.lifecycle_binding_contract()
        policy = contract['acceptance']['admission']
        for row in [*policy['scopes'], *policy['cases']]:
            if 'entryDispositions' not in row['conditions']:
                continue
            row['conditions']['selectionFinal'] = True
            for disposition in row['conditions']['entryDispositions'].values():
                if disposition['status'] == 'pending': disposition['status'] = 'deferred'
                for mode in disposition.get('modes', {}).values():
                    if mode['status'] == 'pending': mode['status'] = 'deferred'
        case = policy['cases'][-1]
        case['conditions']['subjectEntries'].reverse()
        for modes in case['conditions']['selectedModes'].values(): modes.reverse()
        self.assertEqual(admission_contract_errors(contract), [])
        with self.history():
            self.commit(contract)
            report = self.assess(contract, self.observer)
        self.assertEqual(report['errors'], [])
        self.assertIn(case['id'], report['acceptedCases'])

    def test_mode_declarations_reject_omission_drift_and_weakened_effects(self):
        from yiyuan_accord.admission import admission_contract_errors
        for kind in ("missing-mode", "unknown-mode", "no-modes", "foreign-modes", "empty-basis",
                     "row-selected-without-mode", "mode-selected-without-row", "parent-drift",
                     "missing-effect", "extra-effect", "weakened-effect"):
            contract = copy.deepcopy(self.contract)
            policy = contract["acceptance"]["admission"]
            for row in [*policy["scopes"], *policy["cases"]]:
                if "entryDispositions" not in row["conditions"]:
                    continue
                dispositions = row["conditions"]["entryDispositions"]
                desktop = dispositions["chatgpt-desktop"]
                if kind == "missing-mode": desktop["modes"].pop("remote")
                if kind == "unknown-mode": desktop["modes"]["invented"] = copy.deepcopy(desktop["modes"]["chat"])
                if kind == "no-modes":
                    for value in dispositions.values(): value.pop("modes", None)
                if kind == "foreign-modes": dispositions["cx-cli"]["modes"] = copy.deepcopy(desktop["modes"])
                if kind == "empty-basis": desktop["modes"]["work-local"]["basis"] = " "
                if kind == "row-selected-without-mode": desktop["modes"]["work-local"]["status"] = "deferred"
                if kind == "mode-selected-without-row": desktop["status"] = "pending"
            scope = next(row for row in policy["scopes"] if row["id"] == "v33-admitted-entry-delivery")
            case = next(row for row in policy["cases"] if row["scope"] == scope["id"])
            modes = case["expected"]["effect"]["entryDelivery"]["chatgpt-desktop"]["modes"]
            if kind == "parent-drift": scope["conditions"]["entryDispositions"]["chatgpt-desktop"]["modes"]["remote"]["basis"] += " Changed."
            if kind == "missing-effect": modes.clear()
            if kind == "extra-effect": modes["outside-scope"] = copy.deepcopy(modes["work-local"])
            if kind == "weakened-effect": modes["work-local"] = {"boundedModeVerified": True}
            with self.subTest(kind=kind):
                self.assertTrue(admission_contract_errors(contract))

    def test_legacy_pending_modes_remain_readable_but_cannot_finalize_by_deletion(self):
        from yiyuan_accord.admission import admission_contract_errors, _entry_selection
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        for row in [*policy["scopes"], *policy["cases"]]:
            if "entryDispositions" not in row["conditions"]:
                continue
            for value in row["conditions"]["entryDispositions"].values():
                if value.pop("modes", None) is not None:
                    value["status"] = "pending"
            if "applicability" not in row.get("scope", row["id"]):
                row["subjectEntries"] = [key for key in row["subjectEntries"] if not key.startswith("chatgpt-")]
            if "expected" in row:
                for effects in row["expected"]["effect"].values():
                    for key in list(effects):
                        effects[key].pop("modes", None)
                        if key not in row["subjectEntries"]: effects.pop(key)
        for case in policy["cases"]:
            if case["scope"] == "v33-codex-entry-coverage":
                subjects = [key for key in case["conditions"]["subjectEntries"] if not key.startswith("chatgpt-")]
                case["conditions"]["subjectEntries"] = subjects
                case["conditions"]["selectedModes"] = {key: [] for key in subjects}
                matrix = case["expected"]["effect"]["entryCapabilityCoverage"]
                for key in set(matrix) - set(subjects):
                    matrix.pop(key)
        self.sync_selected_cases(policy)
        entries = {row["id"]: row["host"] for row in contract["capabilityMap"]["entrySurfaces"]["rows"]}
        self.assertEqual(admission_contract_errors(contract), [])
        self.assertFalse(_entry_selection(policy, entries)["final"])
        for row in [*policy["scopes"], *policy["cases"]]:
            if "entryDispositions" in row["conditions"]:
                row["conditions"]["selectionFinal"] = True
                for value in row["conditions"]["entryDispositions"].values():
                    if value["status"] == "pending": value["status"] = "deferred"
        self.assertTrue(admission_contract_errors(contract))

    def test_subject_entry_semantics_are_bound_without_changing_old_case_identity(self):
        from yiyuan_accord.admission import _definition, _reuse_definition
        policy = self.contract["acceptance"]["admission"]
        old_case = next(case for case in policy["cases"] if "subjectEntries" not in case)
        without_parents = copy.deepcopy(self.contract)
        without_parents["acceptance"]["admission"]["scopes"] = [
            row for row in without_parents["acceptance"]["admission"]["scopes"] if "subjectEntries" not in row]
        without_parents["acceptance"]["admission"]["cases"] = [
            row for row in without_parents["acceptance"]["admission"]["cases"] if "subjectEntries" not in row]
        self.assertEqual(_definition(self.contract, old_case), _definition(without_parents, old_case))
        parent = next(case for case in policy["cases"] if case["scope"] == "v33-admitted-entry-delivery")
        before = _reuse_definition(self.contract, parent)
        changed = copy.deepcopy(self.contract)
        entry = next(row for row in changed["capabilityMap"]["entrySurfaces"]["rows"]
                     if row["id"] == "cx-vscode")
        entry["environment"] += " Changed subject-entry semantics."
        self.assertNotEqual(before, _reuse_definition(changed, parent))

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

    def test_sparse_package_contract_rejects_invalid_or_broad_dependency_sets(self):
        from yiyuan_accord.admission import admission_contract_errors
        contract, case = self.sparse_contract()
        projection = contract["delivery"]["hostProjections"][0]
        valid = list(case["packageFiles"])
        variants = (
            [],
            [projection["manifest"], projection["manifest"]],
            ["README.md", projection["manifest"]],
            [projection["manifest"], "plugins/yiyuan-accord-codex/not-declared.txt"],
            [value for value in valid if value != projection["manifest"]],
            [value for value in valid if value != projection["contract"]],
            [value for value in valid if value != projection["skill"]],
        )
        for package_files in variants:
            changed = copy.deepcopy(contract)
            target = next(row for row in changed["acceptance"]["admission"]["cases"]
                          if row["id"] == case["id"])
            target["packageFiles"] = package_files
            with self.subTest(packageFiles=package_files):
                self.assertTrue(admission_contract_errors(changed))
        for claim in ("package-lifecycle", "impact-assessment"):
            changed = copy.deepcopy(contract)
            target = next(row for row in changed["acceptance"]["admission"]["cases"]
                          if row["id"] == case["id"])
            target["claims"] = [claim]
            with self.subTest(claim=claim):
                self.assertTrue(admission_contract_errors(changed))
        a08 = copy.deepcopy(contract)
        a08_requirement = next(row for row in a08["acceptance"]["admission"]["acceptanceRequirements"]
                               if row["id"] == "A08")
        a08_requirement["requiredCoverage"]["function"].append(case["scope"])
        self.assertTrue(admission_contract_errors(a08))
        aggregate = copy.deepcopy(self.contract)
        parent = next(row for row in aggregate["acceptance"]["admission"]["cases"]
                      if row["scope"] == "v33-admitted-entry-delivery")
        parent["packageFiles"] = valid
        self.assertTrue(admission_contract_errors(aggregate))

    def test_sparse_package_dependencies_are_definition_bound(self):
        from yiyuan_accord.admission import _reuse_definition
        contract, case = self.sparse_contract()
        original = _reuse_definition(contract, case)
        for action in ("add", "remove"):
            changed = copy.deepcopy(contract)
            target = next(row for row in changed["acceptance"]["admission"]["cases"]
                          if row["id"] == case["id"])
            if action == "add":
                target["packageFiles"].append(
                    "plugins/yiyuan-accord-codex/skills/coordinate-capabilities/SKILL.md")
            else:
                target["packageFiles"].remove(
                    "plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs")
            with self.subTest(action=action):
                self.assertNotEqual(original, _reuse_definition(changed, target))

    def test_oracle_read_failure_recovers_without_leaking_between_assessments(self):
        from yiyuan_accord import admission
        first, later = self.contract["acceptance"]["admission"]["cases"][:2]
        path = sorted(set(first["oracleFiles"]) & set(later["oracleFiles"]))[0]
        locator = f"{self.git('rev-parse', 'HEAD')}:{path}"
        original_git = admission._git
        failed = False

        def observer(request):
            response = self.observer(request)
            if request["phase"] == "observe":
                response["records"] = [record for record in response["records"]
                                       if record["case"] in {first["id"], later["id"]}]
            return response

        def transient_read(root, *args):
            nonlocal failed
            if args == ("cat-file", "blob", locator) and not failed:
                failed = True
                raise subprocess.SubprocessError("synthetic first oracle read failure")
            return original_git(root, *args)

        with patch.object(admission, "_git", side_effect=transient_read):
            recovered = self.assess(observer=observer)
        self.assertNotIn(first["id"], recovered["acceptedCases"])
        self.assertIn("source-evidence-unavailable", recovered["caseRejections"][first["id"]])
        self.assertIn(later["id"], recovered["acceptedCases"], recovered["errors"])

        def unavailable_read(root, *args):
            if args == ("cat-file", "blob", locator):
                raise subprocess.SubprocessError("synthetic persistent oracle read failure")
            return original_git(root, *args)

        with patch.object(admission, "_git", side_effect=unavailable_read):
            unavailable = self.assess(observer=observer)
        for case in (first, later):
            self.assertNotIn(case["id"], unavailable["acceptedCases"])
            self.assertIn("source-evidence-unavailable", unavailable["caseRejections"][case["id"]])

    def test_revision_package_snapshot_rejects_shared_assessment_budget_exhaustion(self):
        from yiyuan_accord import admission
        revision = self.git("rev-parse", "HEAD")
        projection = self.contract["delivery"]["hostProjections"][0]
        package = Path(projection["manifest"]).parents[1].as_posix()
        budgets = (
            {"calls": admission._PACKAGE_ASSESSMENT_CALLS, "files": 0, "bytes": 0},
            {"calls": 0, "files": admission._PACKAGE_ASSESSMENT_FILES, "bytes": 0},
            {"calls": 0, "files": 0, "bytes": admission._PACKAGE_ASSESSMENT_BYTES},
        )
        for budget in budgets:
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                admission._revision_package_snapshot(self.root, revision, package, budget)

    def test_failed_package_reads_consume_the_shared_assessment_budget(self):
        from yiyuan_accord import admission
        revision = self.git("rev-parse", "HEAD")
        projection = self.contract["delivery"]["hostProjections"][0]
        package = Path(projection["manifest"]).parents[1].as_posix()
        missing_budget = {"calls": 0, "files": 0, "bytes": 0}
        for _ in range(2):
            with self.assertRaises(ValueError):
                admission._revision_package_snapshot(
                    self.root, revision, package + "-missing", missing_budget)
        self.assertEqual(missing_budget, {"calls": 2, "files": 0, "bytes": 0})
        batch_budget = {"calls": 0, "files": 0, "bytes": 0}
        with patch.object(admission, "_batch_blobs", side_effect=ValueError("fixture batch failure")):
            for _ in range(2):
                with self.assertRaises(ValueError):
                    admission._revision_package_snapshot(
                        self.root, revision, package, batch_budget)
        self.assertEqual(batch_budget["calls"], 4)
        self.assertGreater(batch_budget["files"], 0)
        self.assertEqual(batch_budget["bytes"], 2 * admission._PACKAGE_TREE_BYTES)

    def test_sparse_package_reuses_unselected_skill_and_manifest_version_only(self):
        for change in ("unselected-skill", "manifest-version"):
            with self.subTest(change=change), self.history():
                contract, case = self.sparse_contract()
                self.commit(contract)
                capture, records = self.capture()
                self.assertIn(case["id"], self.assess(contract, capture)["acceptedCases"])
                original_records = records()
                old_package = next(row for row in original_records if row["case"] == case["id"])["packageSha256"]
                if change == "unselected-skill":
                    path = self.root / "plugins/yiyuan-accord-codex/skills/coordinate-capabilities/SKILL.md"
                    path.write_text(path.read_text(encoding="utf-8") + "\nUnselected fixture change.\n", encoding="utf-8")
                else:
                    projection = contract["delivery"]["hostProjections"][0]
                    manifest_path = self.root / projection["manifest"]
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    version = manifest['version'].split('+', 1)[0] + "+codex.20260921123456"
                    manifest["version"] = version
                    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    contract["delivery"]["version"] = version
                    projection["packageVersion"] = version
                self.update_package_identity(contract)
                self.commit(contract)
                report = self.assess(contract, self.replay(original_records))
                self.assertIn(case["id"], report["acceptedCases"], report["errors"])
                reuse = report["packageReuse"][case["id"]]
                self.assertEqual(reuse["evaluatedPackageSha256"], old_package)
                self.assertEqual(reuse["currentPackageSha256"],
                                 contract["delivery"]["hostProjections"][0]["packageSha256"])
                self.assertNotEqual(reuse["evaluatedPackageSha256"], reuse["currentPackageSha256"])
                self.assertEqual(reuse["packageFiles"], sorted(case["packageFiles"]))
                self.assertEqual(reuse["claimLimit"],
                                 "selected-files-unchanged-not-dependency-completeness")

    def test_sparse_package_rejects_selected_bytes_and_relabelled_record(self):
        changes = {
            "skill": "plugins/yiyuan-accord-codex/skills/maintain-task-continuity/SKILL.md",
            "runtime": "plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs",
            "manifest-description": "plugins/yiyuan-accord-codex/.codex-plugin/plugin.json",
            "manifest-base-version": "plugins/yiyuan-accord-codex/.codex-plugin/plugin.json",
            "manifest-custom-cache": "plugins/yiyuan-accord-codex/.codex-plugin/plugin.json",
        }
        for change, locator in changes.items():
            with self.subTest(change=change), self.history():
                contract, case = self.sparse_contract()
                self.commit(contract)
                capture, records = self.capture()
                self.assertIn(case["id"], self.assess(contract, capture)["acceptedCases"])
                original_records = records()
                path = self.root / locator
                if change in {"manifest-description", "manifest-base-version", "manifest-custom-cache"}:
                    value = json.loads(path.read_text(encoding="utf-8"))
                    if change == "manifest-description":
                        value["description"] += " Changed."
                    else:
                        value["version"] = ("4.0.0-dev.1+codex.20260921123456"
                                            if change == "manifest-base-version"
                                            else value['version'].split('+', 1)[0] + "+codex.fixture")
                        contract["delivery"]["version"] = value["version"]
                        contract["delivery"]["hostProjections"][0]["packageVersion"] = value["version"]
                    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                else:
                    path.write_text(path.read_text(encoding="utf-8") + "\nSelected fixture change.\n", encoding="utf-8")
                self.update_package_identity(contract)
                self.commit(contract)
                report = self.assess(contract, self.replay(original_records))
                self.assertNotIn(case["id"], report["acceptedCases"])
                self.assertTrue(report["errors"])
                reason = ("reuse-definition-mismatch"
                          if change in {"manifest-base-version", "manifest-custom-cache"}
                          else "selected-package-dependency-changed")
                self.assertIn(reason, report["caseRejections"][case["id"]])
        with self.history():
            contract, case = self.sparse_contract()
            self.commit(contract)
            capture, records = self.capture()
            self.assess(contract, capture)
            original_records = records()
            path = self.root / "plugins/yiyuan-accord-codex/skills/coordinate-capabilities/SKILL.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nUnselected fixture change.\n", encoding="utf-8")
            self.update_package_identity(contract)
            self.commit(contract)
            current_hash = contract["delivery"]["hostProjections"][0]["packageSha256"]
            def relabel(rows, _request):
                next(row for row in rows if row["case"] == case["id"])["packageSha256"] = current_hash
            report = self.assess(contract, self.replay(original_records, relabel))
            self.assertNotIn(case["id"], report["acceptedCases"])
            self.assertTrue(report["errors"])

    def test_default_and_lifecycle_cases_keep_complete_package_binding(self):
        with self.history():
            capture, records = self.capture()
            self.assess(self.contract, capture)
            original_records = records()
            changed = copy.deepcopy(self.contract)
            path = self.root / "plugins/yiyuan-accord-codex/skills/coordinate-capabilities/SKILL.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nWhole-package fixture change.\n", encoding="utf-8")
            self.update_package_identity(changed)
            self.commit(changed)
            report = self.assess(changed, self.replay(original_records))
            current_cases = {case["id"] for case in self.contract["acceptance"]["admission"]["cases"]}
            self.assertFalse(current_cases & set(report["acceptedCases"]))
            self.assertTrue(report["errors"])

    def test_changed_executable_oracle_invalidates_only_dependent_current_cases(self):
        retained = None
        def capture(request):
            nonlocal retained
            result = self.observer(request)
            if request["phase"] == "observe": retained = copy.deepcopy(result["records"])
            return result
        self.assertTrue(self.assess(observer=capture)["acceptedCases"])
        with self.history():
            locator = "scripts/observe_codex_entry.py"
            path = self.root / locator
            path.write_text(path.read_text(encoding="utf-8") + "\nChanged synthetic acceptance dependency.\n", encoding="utf-8")
            self.commit(self.contract)
            def replay(request):
                result = self.observer(request)
                if request["phase"] == "observe": result["records"] = retained
                return result
            expected = sorted(case["id"] for case in self.contract["acceptance"]["admission"]["cases"]
                              if locator not in case["oracleFiles"])
            self.assertEqual(self.assess(observer=replay)["acceptedCases"], expected)

    def test_navigation_updates_preserve_evidence_but_changed_case_criteria_do_not(self):
        retained = None
        def capture(request):
            nonlocal retained
            result = self.observer(request)
            if request["phase"] == "observe": retained = copy.deepcopy(result["records"])
            return result
        expected = sorted(case["id"] for case in self.contract["acceptance"]["admission"]["cases"])
        before = self.assess(observer=capture)
        self.assertEqual(before["acceptedCases"], expected)
        def replay(request):
            result = self.observer(request)  # Reviews still bind the current candidate.
            if request["phase"] == "observe": result["records"] = copy.deepcopy(retained)
            return result
        with self.history():
            for name in ("PROCEDURE-v3.3.md", "CONTINUATION.md", "PLAN-v3.3.md", "ACCEPTANCE-v3.3.md"):
                path = self.root / "docs/operations" / name
                path.write_text(path.read_text(encoding="utf-8") + "\nSynthetic historical observation only.\n", encoding="utf-8")
            self.commit(self.contract)
            report = self.assess(observer=replay)
            self.assertEqual(report["errors"], [])
            self.assertEqual(report["acceptedCases"], expected)
            self.assertEqual(report["candidateEligible"], before["candidateEligible"])
            changed = copy.deepcopy(self.contract)
            case = changed["acceptance"]["admission"]["cases"][0]
            case["oracle"] += " Changed synthetic normative decision."
            self.commit(changed)
            self.assertEqual(self.assess(changed, observer=replay)["acceptedCases"],
                             [key for key in expected if key != case["id"]])

    def test_progress_descriptions_do_not_change_reuse_but_quality_floors_do(self):
        from yiyuan_accord.admission import _definition, _reuse_definition
        case = self.contract["acceptance"]["admission"]["cases"][0]
        old = _definition(self.contract, case)
        reusable = _reuse_definition(self.contract, case)
        changed = copy.deepcopy(self.contract)
        entry = next(row for row in changed["capabilityMap"]["entrySurfaces"]["rows"] if row["id"] == case["entry"])
        entry["observation"] = "Updated progress; no execution condition changed."
        entry["currentEffect"] = "described-in-current-progress"
        duty = next(row for row in changed["acceptance"]["duties"] if row["id"] in case["duties"])
        duty["assessment"] = "progress-update"
        duty["evidence"] = ["new-observation-pointer"]
        floor = next(row for row in changed["systemOptimization"]["qualityAxes"] if row["id"] in case["qualityAxes"])
        floor["assessment"] = "progress-update"
        self.assertNotEqual(_definition(changed, case), old)
        self.assertEqual(_reuse_definition(changed, case), reusable)
        duty["requiredOutcome"] += " A new necessary outcome."
        self.assertNotEqual(_reuse_definition(changed, case), reusable)
        duty["requiredOutcome"] = next(row for row in self.contract["acceptance"]["duties"] if row["id"] == duty["id"])["requiredOutcome"]
        floor["floor"] += " A new necessary condition."
        self.assertNotEqual(_reuse_definition(changed, case), reusable)

    def test_complete_synthetic_coverage_uses_existing_review_and_recheck_chain(self):
        contract = copy.deepcopy(self.contract)
        policy = contract["acceptance"]["admission"]
        template = policy["cases"][0]
        coverage_template = next(case for case in policy["cases"] if case["scope"] == "v33-codex-entry-coverage")
        lifecycle_template = self.lifecycle_binding_contract()['acceptance']['admission']['cases'][-1]
        parent_ids = {"v33-openai-entry-applicability", "v33-admitted-entry-delivery",
                      "v33-admitted-entry-lifecycle"}
        parent_cases = {scope_id: copy.deepcopy(next(case for case in policy["cases"] if case["scope"] == scope_id))
                        for scope_id in parent_ids}
        parent_scopes = {scope_id: copy.deepcopy(next(scope for scope in policy["scopes"] if scope["id"] == scope_id))
                         for scope_id in parent_ids}
        for row in [*parent_cases.values(), *parent_scopes.values()]:
            row["conditions"]["selectionFinal"] = True
            for disposition in row["conditions"]["entryDispositions"].values():
                if disposition["status"] == "pending":
                    disposition["status"] = "deferred"
                for mode in disposition.get("modes", {}).values():
                    if mode["status"] == "pending":
                        mode["status"] = "deferred"
        policy["cases"], policy["scopes"] = [], []
        for claim, scope_ids in policy["requiredCoverage"].items():
            for scope_id in scope_ids:
                if scope_id in parent_ids:
                    policy["cases"].append(parent_cases[scope_id])
                    policy["scopes"].append(parent_scopes[scope_id])
                    continue
                case = copy.deepcopy(coverage_template if scope_id == "v33-codex-entry-coverage"
                                     else lifecycle_template if scope_id == 'v33-codex-lifecycle' else template)
                case.update(id="fixture-" + scope_id, scope=scope_id, claims=[claim],
                            duties=[r["id"] for r in contract["acceptance"]["duties"]],
                            qualityAxes=[r["id"] for r in contract["systemOptimization"]["qualityAxes"]])
                if scope_id == 'v33-system-integration':
                    for key in ('subjectEntries', 'selectedModes'):
                        case['conditions'][key] = copy.deepcopy(lifecycle_template['conditions'][key])
                if claim == "impact-assessment": case["expected"]["comparison"] = {"fixtureAssessment": True}
                policy["cases"].append(case)
                policy["scopes"].append({**{k: copy.deepcopy(case[k]) for k in
                    ("host", "entry", "duties", "qualityAxes", "scenarios", "claims", "conditions")},
                    "id": scope_id, "rule": "Synthetic scope for algorithm exercise, not actual coverage."})
        # Generic successes remain insufficient under the current precise contract.
        # This observer is explicitly synthetic; no real outcome is authored here.
        with self.history():
            self.commit(contract)
            generic = self.assess(contract, self.observer)
            self.assertEqual(generic['errors'], [])
            self.assertEqual(len(generic['acceptedCases']), len(policy['cases']))
            self.assertFalse(generic['candidateEligible'])
            self.assertFalse(generic['functionalCompletion'])
            self.assertTrue(any(r['missingObligations'] for r in generic['acceptanceRequirements'].values()))
        # Supply complete, scope/claim-bound mock consequences for the positive
        # algorithm path. Preserve the original coverage and all negative checks.
        for requirement in policy['acceptanceRequirements']:
            for obligation in requirement['outcomeObligations']:
                for case in policy['cases']:
                    if case['scope'] != obligation['scope'] or obligation['claim'] not in case['claims']:
                        continue
                    source = obligation['source']['path']
                    if source not in case['oracleFiles']:
                        case['oracleFiles'].append(source)
                    parts = [p.replace('~1', '/').replace('~0', '~')
                             for p in obligation['pointer'].split('/')[1:]]
                    node = case['expected']
                    for part in parts[:-1]:
                        node = node.setdefault(part, {})
                    node[parts[-1]] = True
        split = copy.deepcopy(contract)
        split_cases = split['acceptance']['admission']['cases']
        first = next(c for c in split_cases if c['scope'] == 'v33-system-integration')
        second = copy.deepcopy(first)
        second['id'] += '-remaining-duties'
        first['duties'], second['duties'] = first['duties'][:1], second['duties'][1:]
        split_cases.append(second)
        planned = self.assess(split)
        self.assertEqual(planned['errors'], [])
        gap = planned['caseBindingGaps']['v33-system-integration']['function']
        self.assertFalse(any(gap['missingDimensions'].values()))
        self.assertTrue(gap['jointCaseMissing'])
        self.assertEqual(planned['progress']['coverageWithoutCases'], 0)
        self.assertFalse(planned['candidateEligible'])
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
            self.assertEqual(report['caseBindingGaps'], {})
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

        # Even if every remaining case is admitted, removing an execution
        # instance cannot vacuously discharge its still-required scope.
        for empty_scope, requirement in (("v33-systemic-correction", "A04"),
                                         ("v33-codex-cli-ordinary-delivery", "A07")):
            missing_case = copy.deepcopy(contract)
            remaining = missing_case["acceptance"]["admission"]["cases"]
            remaining[:] = [case for case in remaining if case["scope"] != empty_scope]
            with self.subTest(empty_scope=empty_scope), self.history():
                self.commit(missing_case)
                report = self.assess(missing_case, self.observer)
                self.assertEqual(report["errors"], [])
                self.assertEqual(len(report["acceptedCases"]), len(remaining))
                self.assertFalse(report["candidateEligible"])
                self.assertFalse(report["functionalCompletion"])
                self.assertIn(empty_scope, report["acceptanceRequirements"]
                              [requirement]["missingScopes"]["function"])
                self.assertFalse(report["acceptanceRequirements"]["A08"]["complete"])

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
