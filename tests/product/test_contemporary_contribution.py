"""Real temporary Git subjects and synthetic observers; never product evidence."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from tests.product import test_admission as fixtures
from tests.product.git_fixture import owned_git_environment
from yiyuan_accord import admission


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def normative_changes(old, current, pointer=''):
    """Fixture source oracle: dictionaries expand; ordered arrays stay whole."""
    if isinstance(old, dict) and isinstance(current, dict):
        rows = []
        for key in sorted(old.keys() | current.keys()):
            path = pointer + '/' + key.replace('~', '~0').replace('/', '~1')
            if key not in old or key not in current:
                rows.append({'pointer': path, 'oldSha256': digest(old[key]) if key in old else None,
                             'newSha256': digest(current[key]) if key in current else None})
            else:
                rows.extend(normative_changes(old[key], current[key], path))
        return rows
    return [] if digest(old) == digest(current) else [
        {'pointer': pointer, 'oldSha256': digest(old), 'newSha256': digest(current)}]


class ContemporaryContributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A local helper class keeps all inherited regression methods out of
        # discovery while retaining the existing isolated Git fixture lifecycle.
        class OwnedFixture(fixtures.CurrentDevelopmentEvidenceTests):
            pass
        OwnedFixture.setUpClass()
        cls.addClassCleanup(OwnedFixture.doClassCleanups)
        cls.fixture = OwnedFixture()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.fixture.root), *args],
                                      env=owned_git_environment(), timeout=30)

    def source_changes(self, old_revision, current_revision):
        raw = self.git('diff', '--raw', '--no-abbrev', '-z', '--no-renames',
                       '--no-ext-diff', '--no-textconv', old_revision, current_revision, '--')
        pieces = raw.split(b'\0')[:-1]
        rows = []
        for index in range(0, len(pieces), 2):
            mode1, mode2, blob1, blob2, _ = pieces[index].decode().split()
            row = {'path': pieces[index + 1].decode(), 'oldMode': mode1[1:], 'newMode': mode2}
            for side, blob in [('old', blob1), ('new', blob2)]:
                row[side + 'Sha256'] = (None if blob == '0' * 40 else
                    hashlib.sha256(self.git('cat-file', 'blob', blob)).hexdigest())
            rows.append(row)
        return rows

    def contemporary_fixture(self, parent=None, *, function_case=None):
        helper = self.fixture
        saved = helper.contract
        original = copy.deepcopy(saved)
        original['changeBoundary']['contemporaryFixture'] = {
            'ordered': ['first', 'second'], 'removed': None, 'retyped': {'value': 1}}
        original['cycle']['targetVersion'] = original['authority']['conditionalRelease']['target'] = '3.3.1'
        host = original['delivery']['hostProjections'][0]
        original['delivery']['version'] = host['packageVersion'] = '3.3.1'
        manifest = helper.root / host['manifest']
        value = json.loads(manifest.read_bytes())
        value['version'] = '3.3.1'
        manifest.write_bytes(json.dumps(value).encode())
        helper.update_package_identity(original)
        helper.contract = original
        try:
            current, case, record, base = (helper.impact_fixture(function_case) if parent is None else
                                          helper.parent_fixture(parent))
        finally:
            helper.contract = saved
        old = json.loads(self.git('show', record['evaluatedRevision'] + ':product/development.json'))
        current['cycle']['targetVersion'] = current['authority']['conditionalRelease']['target'] = '3.3.2'
        changes = current['changeBoundary']['contemporaryFixture']
        changes['ordered'].reverse()
        changes.pop('removed')
        changes.update(retyped='a different type', added=None)
        host = current['delivery']['hostProjections'][0]
        current['delivery']['version'] = host['packageVersion'] = '3.3.2-dev.1'
        value = json.loads(manifest.read_bytes())
        value['version'] = '3.3.2-dev.1'
        manifest.write_bytes(json.dumps(value).encode())
        outside = helper.root / 'scripts/contemporary-outside-oracle.py'
        outside.write_bytes(b'# New candidate source outside the original declared closure.\n')
        policy = current['acceptance']['admission']
        requirement = next(row for row in policy['acceptanceRequirements'] if row['id'] == 'A01')
        if parent is None and function_case is None:
            requirement['outcomeObligations'].append({
                'id': 'a01-contemporary-still-missing', 'source': {
                    'path': 'docs/operations/ACCEPTANCE-v3.3.md', 'anchor': 'A01'},
                'scope': case['scope'], 'claim': 'function',
                'pointer': '/effect/unobservedPreciseResult', 'expected': True})
        helper.update_package_identity(current)
        helper.commit(current)
        state = {}
        group = 'parentApplicability' if parent else 'currentApplicability'

        def observe(request):
            result = base(request)
            if request['phase'] == 'recheck':
                # Existing final recheck also binds the complete new section.
                material = state['material']
                result[group][case['id']]['evidenceSha256'] = digest({
                    key: value for key, value in material.items() if key != 'reviewBundle'})
                result[group][case['id']]['contemporary'] = copy.deepcopy(material['contemporary'])
                return result
            material = result[group][case['id']]
            if function_case is not None:
                material['original']['qualification']['claim'] = case['claims'][0]
            material['schema'] = material['schema'].replace('/v1', '/v2')
            delta = self.source_changes(record['evaluatedRevision'], request['subject']['revision'])
            material['sources']['complete-source-delta'] = {
                'sourceRef': 'fixture://shared-exact-candidate-delta', 'sha256': digest(delta),
                'kind': 'source-analysis'}
            leaves = admission._condition_leaves(case['expected'])
            material['differences'] = [{**row, 'role': 'synthetic complete candidate change',
                'impact': 'current-consequence-supported', 'basis': 'Actual fixture source effect adjudication.',
                'sources': ['analysis'], 'currentConsequences': ['actual']} for row in delta]
            material['contemporary'] = {
                'normativeDifferences': [{**row, 'affectedPointers': sorted(leaves),
                    'impact': 'current-consequence-supported', 'basis': 'Synthetic normative change reviewed.',
                    'sources': ['analysis'], 'currentConsequences': ['actual']}
                    for row in normative_changes(old, current)],
                'sourceDelta': {'sha256': digest(delta), 'source': 'complete-source-delta'},
                'contributions': [{'pointer': pointer, 'disposition': 'current-applicable',
                    'originalSources': ['final'], 'currentSources': ['actual'],
                    'basis': 'This exact original effect remains applicable, not newly executed.'}
                    for pointer in sorted(leaves)]}
            self.fixture.sign_parent_material(material)
            state['material'] = material
            return result

        return current, case, record, base, observe

    def mutate(self, observe, change, *, parent=False, recheck=None):
        def wrapper(request):
            result = observe(request)
            group = 'parentApplicability' if parent else 'currentApplicability'
            if request['phase'] == 'observe':
                for material in result[group].values():
                    change(material)
                    self.fixture.sign_parent_material(material)
            elif recheck:
                recheck(result[group])
            return result
        return wrapper

    def derived_fixture(self, parent=None):
        current, case, record, _, observe = self.contemporary_fixture(parent,
            function_case='v33-goal-authority-correction-steering-01' if parent is None else None)
        obligation = next(row for requirement in current['acceptance']['admission']['acceptanceRequirements']
            for row in requirement['outcomeObligations'] if (row['id'] == 'a01-side-inputs-preserve-goal' if parent is None else
                row['scope'] == case['scope'] and row['claim'] in case['claims']))
        group = 'parentApplicability' if parent else 'currentApplicability'
        state = {}
        def observer(request):
            result = observe(request)
            if request['phase'] == 'recheck':
                material = state['material']
                result[group][case['id']]['evidenceSha256'] = digest({
                    key: value for key, value in material.items() if key != 'reviewBundle'})
                result[group][case['id']]['contemporary'] = copy.deepcopy(material['contemporary'])
                return result
            material = result[group][case['id']]
            material['schema'] = material['schema'].replace('/v2', '/v3')
            facts = [
                {'goal': 'Deliver authorized A/B', 'question': 'Why is C pending?', 'C': 'not authorized'},
                {'answer': 'Complete source facts do not authorize C', 'goal': 'Deliver authorized A/B'},
                {'selected': ['A', 'B'], 'used': 5, 'pending': ['C'], 'files': ['selection', 'note']}]
            if parent:
                facts = [{'business': 'one original combined delivery', 'scope': 'one episode'},
                         {'result': 'original required relationships and complete delivery retained'}]
            chain = []
            for sequence, fact in enumerate(facts):
                source = 'ordered-original-' + str(sequence)
                material['sources'][source] = {'sourceRef': 'fixture://original-episode/' + str(sequence),
                    'sha256': digest(fact), 'kind': 'original-final-outcome'}
                chain.append({'source': source, 'episodeId': record['episodeId'],
                              'sequence': sequence, 'facts': fact})
            material['contemporary']['derivedOutcomes'] = [{
                'obligation': obligation['id'], 'case': case['id'], 'recordSha256': digest(record),
                'packageSha256': record['packageSha256'], 'episodeId': record['episodeId'],
                'criterion': copy.deepcopy(obligation['source']), 'chain': chain,
                'currentSources': ['actual'],
                'basis': 'Synthetic independent source adjudication: question answered and authorized work delivered; C remains pending.'}]
            self.fixture.sign_parent_material(material)
            state['material'] = material
            return result
        return current, case, record, observer

    def test_reviewed_derived_outcome_preserves_original_case_and_other_missing_results(self):
        with self.fixture.history():
            current, case, record, observe = self.derived_fixture()
            frozen = copy.deepcopy((case, record))
            report = self.fixture.assess(current, observe)
            self.assertEqual(report['acceptedCases'], [case['id']], report['caseRejections'])
            self.assertEqual(report['errors'], [])
            self.assertEqual((case, record), frozen)
            a01 = report['acceptanceRequirements']['A01']
            self.assertNotIn('a01-side-inputs-preserve-goal', a01['missingObligations'])
            self.assertIn('a01-ambiguous-goal-to-requirements', a01['missingObligations'])
            self.assertFalse(report['functionalCompletion'])
            self.assertFalse(report['candidateEligible'])

    def test_derived_outcomes_reject_naked_values_wrong_identity_and_unbound_source_facts(self):
        with self.fixture.history():
            current, case, _, observe = self.derived_fixture()
            def damage(material, kind):
                section = material['contemporary']
                row = section['derivedOutcomes'][0]
                if kind == 'bare-true':
                    section['derivedOutcomes'] = [True]
                elif kind == 'direct-value':
                    row['value'] = True
                elif kind in ('case', 'recordSha256', 'packageSha256', 'episodeId', 'obligation'):
                    row[kind] = 'unrelated-original'
                elif kind == 'criterion':
                    row['criterion']['anchor'] = 'A08'
                elif kind == 'duplicate':
                    section['derivedOutcomes'].append(copy.deepcopy(row))
                elif kind == 'empty-chain':
                    row['chain'] = []
                elif kind == 'cross-episode':
                    row['chain'][-1]['episodeId'] = 'another-business'
                elif kind == 'order':
                    row['chain'].reverse()
                elif kind == 'boolean-sequence':
                    row['chain'][0]['sequence'] = False
                elif kind == 'boolean-fact':
                    row['chain'][0]['facts'] = True
                elif kind == 'source-bytes':
                    row['chain'][-1]['facts']['used'] = 4
                elif kind == 'source-digest':
                    material['sources'][row['chain'][0]['source']]['sha256'] = '0' * 64
                elif kind == 'source-kind':
                    material['sources'][row['chain'][0]['source']]['kind'] = 'current-observation'
                elif kind == 'no-current':
                    row['currentSources'] = []
            kinds = ('bare-true', 'direct-value', 'case', 'recordSha256', 'packageSha256',
                     'episodeId', 'obligation', 'criterion', 'duplicate', 'empty-chain',
                     'cross-episode', 'order', 'boolean-sequence', 'boolean-fact',
                     'source-bytes', 'source-digest', 'source-kind', 'no-current')
            for kind in kinds:
                with self.subTest(kind=kind):
                    report = self.fixture.assess(current, self.mutate(
                        observe, lambda material: damage(material, kind)))
                    self.assertEqual(report['acceptedCases'], [])
                    self.assertFalse(report['candidateEligible'])

    def test_derived_outcomes_do_not_replace_original_case_conditions_or_independent_review(self):
        with self.fixture.history():
            current, case, _, observe = self.derived_fixture()
            def damage(material, kind):
                if kind == 'original-leaf':
                    material['contemporary']['contributions'].pop()
                elif kind == 'unresolved-leaf':
                    material['contemporary']['contributions'][0].update(
                        disposition='unresolved', currentSources=[])
                elif kind == 'condition':
                    material['conditionBindings'].pop()
                elif kind == 'reviewer':
                    for review in material['reviewBundle']['reviews']:
                        review['reviewerId'] = 'one-self-reviewer'
                elif kind == 'review-axis':
                    material['reviewBundle']['reviews'].pop()
                elif kind == 'review-subject':
                    material['reviewBundle']['subject']['revision'] = '0' * 40
                elif kind == 'missing-effect-reviewed':
                    material['contemporary']['derivedOutcomes'][0]['chain'].pop()
                    # Supplied independent review rejects this known answer-only
                    # source. The validator does not invent a semantic NLP gate.
                    review = material['reviewBundle']['reviews'][0]
                    review['decision'] = 'fail'
                    review['findings'] = [{'severity': 'P1', 'disposition': 'fail'}]
            for kind in ('original-leaf', 'unresolved-leaf', 'condition', 'reviewer',
                         'review-axis', 'review-subject', 'missing-effect-reviewed'):
                with self.subTest(kind=kind):
                    report = self.fixture.assess(current, self.mutate(
                        observe, lambda material: damage(material, kind)))
                    self.assertEqual(report['acceptedCases'], [])
                    self.assertIn('a01-side-inputs-preserve-goal',
                        report['acceptanceRequirements']['A01']['missingObligations'])

    def test_derived_outcomes_require_exact_recheck_and_explicit_new_material_version(self):
        with self.fixture.history():
            current, case, _, observe = self.derived_fixture()
            for version in ('v1', 'v2'):
                with self.subTest(version=version):
                    report = self.fixture.assess(current, self.mutate(observe,
                        lambda material: material.update(schema=material['schema'].replace('v3', version))))
                    self.assertEqual(report['acceptedCases'], [])
            for kind in ('chain', 'digest', 'current-condition'):
                def drift(rows):
                    item = rows[case['id']]
                    if kind == 'chain':
                        item['contemporary']['derivedOutcomes'][0]['chain'][0]['facts']['goal'] = 'a changed goal'
                    elif kind == 'digest':
                        item['evidenceSha256'] = '0' * 64
                    else:
                        item['current']['context']['authority'] = []
                with self.subTest(recheck=kind):
                    report = self.fixture.assess(current, self.mutate(observe, lambda material: None, recheck=drift))
                    self.assertIn('current-applicability-changed', report['caseRejections'][case['id']])
                    self.assertEqual(report['acceptedCases'], [])

    def test_v3_parent_derived_outcome_keeps_same_episode_joint_gate_and_a08_prerequisites(self):
        with self.fixture.history():
            current, case, record, observe = self.derived_fixture('v33-system-integration-live-development-01')
            frozen = copy.deepcopy(record)
            report = self.fixture.assess(current, observe)
            self.assertEqual(report['acceptedCases'], [case['id']], report['caseRejections'])
            self.assertEqual(record, frozen)
            a08 = report['acceptanceRequirements']['A08']
            self.assertNotIn('a08-same-business-complete-composition', a08['missingObligations'])
            self.assertFalse(a08['complete'])
            self.assertTrue(a08['blockedBy'])
            for kind in ('role', 'relationship', 'episode'):
                def missing(material):
                    if kind == 'role':
                        material['roles'].pop()
                    elif kind == 'relationship':
                        material['relationships'].pop()
                    else:
                        material['relationships'][0]['episodeId'] = 'unrelated-business'
                with self.subTest(kind=kind):
                    rejected = self.fixture.assess(current, self.mutate(observe, missing, parent=True))
                    self.assertEqual(rejected['acceptedCases'], [])
                    self.assertFalse(rejected['acceptanceRequirements']['A08']['complete'])

    def sdk_lifecycle_fixture(self, version=2):
        case_id = 'v33-codex-sdk-lifecycle-01'
        current, case, record, legacy, observe = self.contemporary_fixture(case_id)
        def observed(request):
            result = observe(request)
            if request['phase'] == 'observe':
                material = result['parentApplicability'][case_id]
                material['schema'] = 'yiyuan-accord-parent-applicability/v' + str(version)
                if version == 3:
                    material['contemporary']['derivedOutcomes'] = []
                material['roles'][0].update(responsibility='historical-execution',
                    currentActor=None, currentSources=[])
                for row in material['conditionBindings']:
                    row['responsibility'] = 'historical-execution'
                for row in material['predicateBindings']:
                    row['responsibility'] = 'actual-current-reassessment'
                material['relationships'] = []
                self.fixture.sign_parent_material(material)
            return result
        return current, case, record, legacy, observed

    def test_sdk_lifecycle_complete_contemporary_bridge_preserves_original_identity(self):
        for version in (2, 3):
            with self.subTest(version=version), self.fixture.history():
                current, case, record, _, observe = self.sdk_lifecycle_fixture(version)
                original, original_case, phases = copy.deepcopy(record), copy.deepcopy(case), []
                def checked(request):
                    phases.append(request['phase'])
                    result = observe(request)
                    if request['phase'] == 'observe':
                        material = result['parentApplicability'][case['id']]
                        self.assertEqual(len(material['predicateBindings']), 21)
                        self.assertEqual([(r['entry'], r['mode']) for r in material['roles']], [('cx-sdk', None)])
                        self.assertEqual(material['original']['qualification']['claim'], 'package-lifecycle')
                        self.assertTrue(material['original']['qualification']['knownFailuresAndLimits'])
                    return result
                report = self.fixture.assess(current, checked)
                self.assertEqual(report['acceptedCases'], [case['id']], report['caseRejections'])
                self.assertEqual(report['errors'], [])
                self.assertEqual(phases, ['observe', 'recheck'])
                self.assertEqual(record, original)
                self.assertEqual(case, original_case)
                self.assertEqual(case['conditions']['execution']['resourceController'], 'windows-job-object')
                supported = report['currentParentApplicability'][case['id']]
                self.assertIn('complete-package-changed', supported['reconciledReasons'])
                self.assertFalse(report['functionalCompletion'])
                self.assertFalse(report['candidateEligible'])
                self.assertFalse(report['acceptanceRequirements']['A06']['complete'])

    def test_sdk_lifecycle_bridge_rejects_incomplete_or_misbound_sources(self):
        with self.fixture.history():
            current, case, record, legacy, observe = self.sdk_lifecycle_fixture(3)
            for route in (legacy, self.fixture.replay([record])):
                self.assertEqual(self.fixture.assess(current, route)['acceptedCases'], [])
            mutations = {
                'predicate': lambda material: material['predicateBindings'].pop(),
                'condition': lambda material: material['conditionBindings'].pop(),
                'role': lambda material: material['roles'].clear(),
                'wrong-role': lambda material: material['roles'][0].update(entry='cx-cli'),
                'duplicate-role': lambda material: material['roles'].append(copy.deepcopy(material['roles'][0])),
                'current-consequence': lambda material: material['differences'][0].update(currentConsequences=[]),
                'source-delta': lambda material: material['differences'].pop(),
                'normative-delta': lambda material: material['contemporary']['normativeDifferences'].pop(),
                'missing-contribution': lambda material: material['contemporary']['contributions'].pop(),
                'f990-insufficient-bridge': lambda material: material['contemporary']['contributions'][0].update(
                    disposition='unresolved', currentSources=[]),
                'qualification': lambda material: material['original']['qualification'].update(decision='not-run'),
                'original-final-source': lambda material: material['original']['qualification'].update(finalOutcomeSources=[]),
                'negative-disposition': lambda material: material['original']['qualification']['knownFailuresAndLimits'][0].update(
                    disposition='silently-ignored'),
                'old-package': lambda material: material['original'].update(packageSha256='0' * 64),
                'current-package': lambda material: material['current'].update(packageSha256='0' * 64),
                'expired-review': lambda material: material['reviewBundle']['reviews'][0].update(reviewedAt='2000-01-01T00:00:00Z'),
                'review-axis': lambda material: material['reviewBundle']['reviews'].pop(),
                'posix-count-is-not-zero': lambda material: next(r for r in material['predicateBindings']
                    if r['pointer'] == '/cleanup/ownedProcesses').update(currentValue=None),
                'wrong-controller': lambda material: next(r for r in material['conditionBindings']
                    if r['pointer'] == '/execution/resourceController').update(currentValue='posix-session-process-group'),
                'unsourced-derived-outcome': lambda material: material['contemporary']['derivedOutcomes'].append({}),
            }
            for kind, change in mutations.items():
                with self.subTest(rejection=kind):
                    report = self.fixture.assess(current, self.mutate(observe, change, parent=True))
                    self.assertEqual(report['acceptedCases'], [], kind)
                    self.assertIn(case['id'], report['caseRejections'])
            def drift(rows):
                rows[case['id']]['contemporary']['sourceDelta']['sha256'] = '0' * 64
            report = self.fixture.assess(current, self.mutate(observe, lambda material: None, parent=True, recheck=drift))
            self.assertIn('current-applicability-changed', report['caseRejections'][case['id']])
            # Structural rejection does not authenticate arbitrary source claims.
            def hot_record(request):
                result = observe(request)
                if request['phase'] == 'observe':
                    result['records'][0]['conditions']['execution'].update(
                        resourceController='posix-session-process-group', caseVariant='hot-reload')
                    result['records'][0]['facts']['cleanup']['value']['ownedProcesses'] = None
                return result
            self.assertEqual(self.fixture.assess(current, hot_record)['acceptedCases'], [])
            def ordinary_channel(request):
                result = observe(request)
                result['currentApplicability'] = result.pop('parentApplicability')
                return result
            self.assertEqual(self.fixture.assess(current, ordinary_channel)['acceptedCases'], [])
            protected = self.fixture.root / 'README.md'
            before = protected.read_bytes()
            def changed_after_recheck(request):
                result = observe(request)
                if request['phase'] == 'recheck': protected.write_bytes(before + b'\nchanged after observation\n')
                return result
            try:
                self.assertEqual(self.fixture.assess(current, changed_after_recheck)['acceptedCases'], [])
            finally:
                protected.write_bytes(before)
            original_case = copy.deepcopy(case)
            case['conditions']['execution']['limits']['providerRequests'] = 6
            self.fixture.commit(current)
            self.assertEqual(self.fixture.assess(current, observe)['acceptedCases'], [])
            self.assertEqual(record['conditions'], original_case['conditions'])

    def test_sdk_route_does_not_open_other_complete_case_claims(self):
        for case_id in ('v33-codex-sdk-scoped-exposure-01', 'v33-cli-readme-semantic-review-20261020-01',
                        'synthetic-other-lifecycle'):
            with self.subTest(case=case_id), self.fixture.history():
                saved = self.fixture.contract
                if case_id == 'synthetic-other-lifecycle':
                    changed = copy.deepcopy(saved)
                    policy = changed['acceptance']['admission']
                    extra = copy.deepcopy(next(c for c in policy['cases'] if c['id'] == 'v33-codex-sdk-lifecycle-01'))
                    scope = copy.deepcopy(next(c for c in policy['scopes'] if c['id'] == extra['scope']))
                    extra.update(id=case_id, scope=case_id)
                    scope['id'] = case_id
                    policy['cases'].append(extra)
                    policy['scopes'].append(scope)
                    self.fixture.contract = changed
                try:
                    current, case, _, _, observe = self.contemporary_fixture(case_id)
                finally:
                    self.fixture.contract = saved
                for version in (2, 3):
                    def schema(material):
                        material['schema'] = 'yiyuan-accord-parent-applicability/v' + str(version)
                        if version == 3: material['contemporary']['derivedOutcomes'] = []
                    report = self.fixture.assess(current, self.mutate(observe, schema, parent=True))
                    self.assertEqual(report['acceptedCases'], [])
                    self.assertIn('current-applicability-unsupported', report['caseRejections'][case_id])

    def test_explicit_current_review_retains_original_effect_without_new_outcome(self):
        with self.fixture.history():
            current, case, record, legacy, observe = self.contemporary_fixture()
            frozen = copy.deepcopy(record)
            old = self.fixture.assess(current, legacy)
            self.assertEqual(old['acceptedCases'], [])
            self.assertIn('current-applicability-unsupported', old['caseRejections'][case['id']])
            report = self.fixture.assess(current, observe)
            self.assertEqual(report['acceptedCases'], [case['id']], report['caseRejections'])
            self.assertEqual(report['errors'], [])
            self.assertEqual(record, frozen)
            self.assertIn('a01-contemporary-still-missing',
                          report['acceptanceRequirements']['A01']['missingObligations'])
            self.assertFalse(report['functionalCompletion'])
            self.assertFalse(report['candidateEligible'])

    def test_reviewed_partial_original_effects_do_not_admit_a_whole_case(self):
        with self.fixture.history():
            current, case, _, _, observe = self.contemporary_fixture()
            for change in ('missing', 'unresolved', 'contradicted'):
                def partial(material):
                    rows = material['contemporary']['contributions']
                    if change == 'missing':
                        rows.pop()
                    else:
                        rows[-1].update(disposition=change, currentSources=[])
                with self.subTest(change=change):
                    report = self.fixture.assess(current, self.mutate(observe, partial))
                    self.assertEqual(report['acceptedCases'], [])
                    self.assertIn('current-contribution-incomplete', report['caseRejections'][case['id']])
                    self.assertFalse(report['functionalCompletion'])

    def test_complete_normative_source_and_current_evidence_cannot_be_omitted(self):
        with self.fixture.history():
            current, case, _, _, observe = self.contemporary_fixture()
            def wrong(material, kind):
                section = material['contemporary']
                if kind == 'outside-source':
                    material['differences'] = [row for row in material['differences']
                        if row['path'] != 'scripts/contemporary-outside-oracle.py']
                elif kind == 'source-hash':
                    material['sources']['complete-source-delta']['sha256'] = '0' * 64
                elif kind == 'normative':
                    section['normativeDifferences'].pop()
                elif kind == 'ordered-array':
                    row = next(row for row in section['normativeDifferences']
                               if row['pointer'].endswith('/ordered'))
                    row['newSha256'] = row['oldSha256']
                elif kind == 'duplicate':
                    section['contributions'].append(copy.deepcopy(section['contributions'][0]))
                elif kind == 'no-current-source':
                    section['contributions'][0]['currentSources'] = ['final']
                elif kind == 'malformed':
                    section['normativeDifferences'][0]['impact'] = []
                elif kind == 'review':
                    material['reviewBundle']['reviews'].pop()
            for kind in ('outside-source', 'source-hash', 'normative', 'ordered-array',
                         'duplicate', 'no-current-source', 'malformed', 'review'):
                with self.subTest(kind=kind):
                    report = self.fixture.assess(current, self.mutate(
                        observe, lambda material: wrong(material, kind)))
                    self.assertEqual(report['acceptedCases'], [])
            def changed(rows):
                rows[case['id']]['contemporary']['sourceDelta']['sha256'] = '0' * 64
            report = self.fixture.assess(current, self.mutate(observe, lambda material: None, recheck=changed))
            self.assertIn('current-applicability-changed', report['caseRejections'][case['id']])

    def test_normative_reference_diagnostics_preserve_rejection_precedence(self):
        for parent in (None, 'v33-system-integration-live-development-01'):
            with self.subTest(parent=parent), self.fixture.history():
                current, case, record, _, observe = self.contemporary_fixture(parent)
                frozen = copy.deepcopy(record)
                self.assertEqual(self.fixture.assess(current, observe)['acceptedCases'], [case['id']])
                for variant in ('analysis', 'current', 'hash', 'impact', 'unknown', 'duplicate', 'unhashable'):
                    def wrong(material):
                        row = material['contemporary']['normativeDifferences'][0]
                        row['sources'].append('actual')
                        if variant == 'current':
                            row['sources'] = ['analysis']
                            row['currentConsequences'].append('analysis')
                        elif variant == 'hash': row['newSha256'] = '0' * 64
                        elif variant == 'impact': row['impact'] = []
                        elif variant == 'unknown': row['sources'].append('private-source-canary')
                        elif variant == 'duplicate': row['sources'].append('actual')
                        elif variant == 'unhashable': row['sources'].append({})
                    with self.subTest(variant=variant):
                        report = self.fixture.assess(current, self.mutate(observe, wrong, parent=bool(parent)))
                        code = {'analysis': 'source-analysis-reference-kind-mismatch',
                                'current': 'current-observation-reference-kind-mismatch'}.get(variant)
                        self.assertEqual(report['caseRejections'][case['id']],
                            sorted(['current-applicability-unsupported'] + ([code] if code else [])))
                        self.assertEqual(report['acceptedCases'], [])
                        self.assertFalse(report['candidateEligible'])
                        self.assertNotIn('private-source-canary', repr(report))
                        self.assertEqual(record, frozen)

    def test_parent_retains_complete_roles_predicates_and_same_episode_chain(self):
        parent = 'v33-system-integration-live-development-01'
        with self.fixture.history():
            current, case, record, _, observe = self.contemporary_fixture(parent)
            report = self.fixture.assess(current, observe)
            self.assertEqual(report['acceptedCases'], [parent], report['caseRejections'])
            self.assertEqual(report['currentParentApplicability'][parent]['original']['episodeId'], record['episodeId'])
            self.assertFalse(report['acceptanceRequirements']['A08']['complete'])
            for kind in ('role', 'predicate', 'episode'):
                def incomplete(material):
                    if kind == 'role':
                        material['roles'].pop()
                    elif kind == 'predicate':
                        material['predicateBindings'].pop()
                    else:
                        material['relationships'][0]['episodeId'] = 'a-different-business'
                with self.subTest(kind=kind):
                    report = self.fixture.assess(current, self.mutate(observe, incomplete, parent=True))
                    self.assertEqual(report['acceptedCases'], [])

    def test_current_review_cannot_change_the_original_case_or_grant_authority(self):
        with self.fixture.history():
            current, case, _, _, observe = self.contemporary_fixture()
            original_case = copy.deepcopy(case)
            original_authority = copy.deepcopy(current['authority'])
            for kind in ('condition', 'expected', 'oracle', 'authority'):
                case.clear()
                case.update(copy.deepcopy(original_case))
                current['authority'] = copy.deepcopy(original_authority)
                if kind == 'condition':
                    case['conditions']['newExecutionPremise'] = 'changed'
                elif kind == 'expected':
                    case['expected']['effect']['newClaim'] = True
                elif kind == 'oracle':
                    case['oracleFiles'].append('README.md')
                else:
                    current['authority']['conditionalRelease']['decision'] = 'not-authorized'
                self.fixture.commit(current)
                with self.subTest(kind=kind):
                    report = self.fixture.assess(current, observe)
                    self.assertEqual(report['acceptedCases'], [])

    def test_special_source_and_lifecycle_cases_do_not_enter_the_function_bridge(self):
        for case_id in ('v33-codex-sdk-lifecycle-01', 'v33-openai-entry-applicability-01',
                        'v33-codex-entry-coverage-01'):
            with self.subTest(case=case_id), self.fixture.history():
                current, case, _, _, observer = self.contemporary_fixture(function_case=case_id)
                report = self.fixture.assess(current, observer)
                self.assertEqual(report['acceptedCases'], [])
                self.assertIn('current-applicability-unsupported', report['caseRejections'][case['id']])

    def second_record_observer(self, current, record, observe):
        """Capture another genuine synthetic old record through the public seam."""
        helper = self.fixture
        current_revision = self.git('rev-parse', 'HEAD').decode().strip()
        old = json.loads(self.git('show', record['evaluatedRevision'] + ':product/development.json'))
        helper.git('checkout', '--quiet', '--detach', record['evaluatedRevision'])
        try:
            capture, records = helper.capture()
            result = helper.assess(old, capture)
            second = next(row for row in records() if row['case'] ==
                          'v33-goal-authority-correction-steering-01')
            self.assertIn(second['case'], result['acceptedCases'])
        finally:
            helper.git('checkout', '--quiet', '--detach', current_revision)
        case = next(row for row in current['acceptance']['admission']['cases'] if row['id'] == second['case'])
        state = {}
        def wrapper(request):
            result = observe(request)
            if request['phase'] == 'recheck':
                material = state['material']
                result['currentApplicability'][second['case']] = {
                    'evidenceSha256': digest({key: value for key, value in material.items() if key != 'reviewBundle'}),
                    **{key: copy.deepcopy(material[key]) for key in ['current', 'conditionBindings', 'contemporary']}}
                return result
            result['records'].append(copy.deepcopy(second))
            material = copy.deepcopy(next(iter(result['currentApplicability'].values())))
            original = material['original']
            original.update(recordSha256=digest(second), **{key: second[key] for key in
                ['definitionSha256', 'packageSha256', 'episodeId']})
            original['qualification'].update(case=case['id'], scope=case['scope'],
                recordSha256=digest(second), episodeId=second['episodeId'])
            material['sources']['final']['sha256'] = digest({'syntheticFinalCaseAccepted': case['id']})
            material['current']['definitionSha256'] = request['cases'][case['id']]['definitionSha256']
            material['conditionBindings'] = [{'pointer': pointer, 'originalValue': value,
                'responsibility': 'continuing-applicability', 'currentValue': copy.deepcopy(value),
                'basis': 'Actual synthetic continuing condition.', 'sources': ['actual']}
                for pointer, value in admission._condition_leaves(case['conditions']).items()]
            leaves = admission._condition_leaves(case['expected'])
            for row in material['contemporary']['normativeDifferences']:
                row['affectedPointers'] = sorted(leaves)
            material['contemporary']['contributions'] = [{'pointer': pointer,
                'disposition': 'current-applicable', 'originalSources': ['final'], 'currentSources': ['actual'],
                'basis': 'This original synthetic leaf remains applicable.'} for pointer in sorted(leaves)]
            helper.sign_parent_material(material)
            state['material'] = material
            result['currentApplicability'][case['id']] = material
            return result
        return wrapper, second['case']

    def test_all_read_limits_failed_attempts_and_success_only_assessment_cache(self):
        with self.fixture.history():
            current, case, record, _, observe = self.contemporary_fixture()
            # Five distinct legal blobs exceed 4MiB independently of repository
            # source size; each remains below 1MiB. These are owned source
            # fixtures, not a replay or an executable workload.
            for index in range(5):
                (self.fixture.root / f'docs/contemporary-{index}.txt').write_bytes(bytes([65 + index]) * 900000)
            self.fixture.commit(current)
            observer, second = self.second_record_observer(current, record, observe)
            changes = self.git('diff', '--raw', '--no-abbrev', '-z', '--no-renames',
                               record['evaluatedRevision'], 'HEAD', '--').split(b'\0')[:-1]
            blobs = set()
            for row in changes[::2]:
                blobs.update(value for value in row.decode().split()[2:4] if value != '0' * 40)
            sizes = {blob: int(self.git('cat-file', '-s', blob)) for blob in blobs}
            self.assertGreater(sum(sizes.values()), 4194304)
            package = 'plugins/yiyuan-accord-codex'
            package_files = package_bytes = 0
            for revision in [record['evaluatedRevision'], 'HEAD']:
                rows = self.git('ls-tree', '-r', '-l', revision, '--', package).decode().splitlines()
                package_files += len(rows)
                package_bytes += sum(int(row.split('\t')[0].split()[3]) for row in rows)
            actual = admission._bounded_git_bytes
            batches = []
            seen_sizes = [False]
            def boundary(root, args, limit, stdin=None):
                if '--batch-check' in args:
                    seen_sizes[0] = True
                if seen_sizes[0] and '--batch' in args:
                    batch = stdin.decode().splitlines()
                    batches.append(batch)
                return actual(root, args, limit, stdin)
            with patch.object(admission, '_bounded_git_bytes', side_effect=boundary):
                report = self.fixture.assess(current, observer)
            self.assertEqual(report['acceptedCases'], sorted([case['id'], second]), report['caseRejections'])
            self.assertGreater(len(batches), 1)
            self.assertEqual(sum(map(len, batches)), len(sizes))
            self.assertTrue(all(len(batch) <= 256 and sum(sizes[blob] for blob in batch) <= 4194304
                                for batch in batches))
            # A new assessment must re-read its immutable evidence; no cache
            # survives a new caller observation/recheck window.
            batches.clear()
            seen_sizes[0] = False
            with patch.object(admission, '_bounded_git_bytes', side_effect=boundary):
                again = self.fixture.assess(current, observer)
            self.assertEqual(again['acceptedCases'], report['acceptedCases'])
            self.assertEqual(sum(map(len, batches)), len(sizes))
            for name, maximum in [('_PACKAGE_ASSESSMENT_CALLS', 10),
                ('_PACKAGE_ASSESSMENT_FILES', package_files + len(sizes)),
                ('_PACKAGE_ASSESSMENT_BYTES', package_bytes + sum(sizes.values()))]:
                fail = [True]
                seen_sizes[0] = False
                def unavailable(root, args, limit, stdin=None):
                    if '--batch-check' in args:
                        seen_sizes[0] = True
                    if seen_sizes[0] and '--batch' in args and fail[0]:
                        fail[0] = False
                        raise OSError('Synthetic failure at the external Git read boundary')
                    return actual(root, args, limit, stdin)
                with self.subTest(bound=name), patch.object(admission, name, maximum), \
                        patch.object(admission, '_bounded_git_bytes', side_effect=unavailable):
                    failed = self.fixture.assess(current, observer)
                    self.assertFalse(fail[0], failed['errors'])
                    self.assertEqual(failed['acceptedCases'], [])
            # An oversized source outside the old oracle/package/core closure
            # is rejected before any batch can overrun the per-blob bound.
            (self.fixture.root / 'docs/contemporary-too-large.txt').write_bytes(b'x' * 1048577)
            self.fixture.commit(current)
            oversized = self.fixture.assess(current, observe)
            self.assertEqual(oversized['acceptedCases'], [])


if __name__ == '__main__':
    unittest.main()
