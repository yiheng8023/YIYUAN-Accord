"""Synthetic public admission tests; these are not native execution evidence."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from tests.product import test_admission as fixtures
from yiyuan_accord import admission as a


class ObligationEvidenceTests(unittest.TestCase):
    # Reuse the owned temporary Git fixture without inheriting its test suite.
    setUpClass = classmethod(fixtures.CurrentDevelopmentEvidenceTests.setUpClass.__func__)
    git = classmethod(fixtures.DevelopmentEvidenceTests.git.__func__)
    history = fixtures.DevelopmentEvidenceTests.history
    observer = fixtures.CurrentDevelopmentEvidenceTests.observer
    commit = fixtures.CurrentDevelopmentEvidenceTests.commit
    assess = fixtures.CurrentDevelopmentEvidenceTests.assess
    IDS = ["a02-delegated-managed-selection", "a02-explicit-policy-native-adoption"]

    def flat_fixture(self):
        contract = copy.deepcopy(self.contract)
        case = next(c for c in contract['acceptance']['admission']['cases']
                    if c['scope'] == 'v33-dynamic-model-routing' and c['claims'] == ['function'])
        old_subject = a.evidence_subject(self.root)
        old_contract = copy.deepcopy(contract)
        contract['authority']['rule'] += ' Synthetic current dependency review.'
        self.commit(contract)
        state = {}

        def observer(request):
            result = self.observer(request)
            if request['phase'] == 'recheck':
                result['obligationEvidence'] = {'supplement-1': copy.deepcopy(state['recheck'])}
                return result
            record = next(r for r in result['records'] if r['case'] == case['id'])
            stamp = datetime.now(timezone.utc) - timedelta(seconds=1)
            execution = {'subject': old_subject, 'packageSha256': old_contract['delivery']['hostProjections'][0]['packageSha256'],
                'episodeId': 'separate-native-episode', 'operationId': 'operation-1',
                'actor': 'worker-1', 'host': case['host'], 'entry': case['entry'],
                'profile': {'model': 'fixture-model', 'configuration': 'fixture-profile'},
                'managedSkill': {'id': 'fixture-skill', 'sha256': 'a'*64},
                'sourcePolicy': {'mode': 'explicit-only', 'sha256': 'b'*64}}
            sources = {}
            def source(key, facts, kind='execution-observation'):
                sources[key] = {'sourceRef': 'fixture://' + key, 'sha256': a._hash(facts), 'kind': kind}
                return key
            identity = {k: copy.deepcopy(execution[k]) for k in ('actor', 'host', 'entry', 'profile', 'managedSkill', 'sourcePolicy')}
            bound = {**identity, 'subject': old_subject, 'packageSha256': execution['packageSha256'],
                'naturalInput': 'Review this supplied source and use the result.',
                'selectionDelegation': 'coordinator', 'permissions': {'readOnly': True},
                'oneWriter': 'root', 'resourceLimits': {'seconds': 60},
                'deadlineAt': (stamp + timedelta(seconds=50)).isoformat()}
            facts = [bound,
                {**identity, 'selectionAuthority': 'coordinator-delegated'},
                {**identity, 'origin': 'native-skill-loader', 'fullBodyLoaded': True, 'dependenciesLoaded': True},
                {**identity, 'useful': True, 'actualEffect': 'Source-linked review adopted by root'},
                {**identity, 'resourcesReleased': True, 'poststate': 'No task-owned processes remain'}]
            chain = []
            for i, (kind, fact) in enumerate(zip(('pre-effect-binding', 'select', 'native-load', 'useful-adoption', 'cleanup'), facts)):
                node = {'type': kind, 'episodeId': execution['episodeId'],
                    'operationId': execution['operationId'], 'sequence': i, 'at': (stamp + timedelta(milliseconds=i)).isoformat(), 'facts': fact}
                chain.append({**node, 'source': source(kind, node)})
            source('actual', {'currentAuthorityAndDependencies': 'observed'}, 'current-observation')
            source('analysis', {'analysis': 'independently reviewed'}, 'source-analysis')
            package = Path(contract['delivery']['hostProjections'][0]['manifest']).parents[1].as_posix()
            changes = a._impact_differences(self.root, old_subject['revision'], request['subject']['revision'],
                (package, package), case['oracleFiles'], {'calls': 0, 'files': 0, 'bytes': 0}, complete=True)
            def delta(row):
                return {**row, 'basis': 'Synthetic current consequences independently reviewed',
                    'sources': ['analysis'], 'currentConsequences': ['actual']}
            witness = {'schema': 'yiyuan-accord-obligation-execution-evidence/v1',
                'base': {'case': case['id'], 'recordSha256': a._hash(record)},
                'obligations': [{'id': key, 'criterion': copy.deepcopy(next(o for r in contract['acceptance']['admission']['acceptanceRequirements']
                    for o in r['outcomeObligations'] if o['id'] == key)['source'])} for key in self.IDS],
                'execution': execution, 'chain': chain, 'sources': sources,
                'quality': [{'axis': q['id'], 'disposition': 'supported', 'basis': 'Full execution quality reviewed', 'sources': ['cleanup']}
                    for q in contract['systemOptimization']['qualityAxes']],
                'knownFailuresAndLimits': [],
                'current': {'subject': request['subject'], 'packageSha256': contract['delivery']['hostProjections'][0]['packageSha256'],
                    'context': {k: ['actual'] for k in ('configuration', 'authority', 'helpers', 'continuingState')}},
                'differences': [delta(row) for row in changes],
                'normativeDifferences': [delta(row) for row in a._normative_differences(old_contract, contract)]}
            digest = a._hash(witness)
            review = copy.deepcopy(result['reviewBundle'])
            review.update(schema='yiyuan-accord-development-impact-review-bundle/v1', evidenceSha256=digest)
            for row in review['reviews']:
                row['evidenceSha256'] = digest
            witness['reviewBundle'] = review
            state['witness'] = witness
            state['recheck'] = {'evidenceSha256': digest, 'current': copy.deepcopy(witness['current'])}
            result['obligationEvidence'] = {'supplement-1': witness}
            return result
        return contract, case, observer, state

    def test_separate_execution_supports_only_exact_obligations(self):
        with self.history():
            contract, case, observer, _ = self.fixture()
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            self.assertEqual(report['obligationEvidence']['supplement-1']['supportedObligations'], self.IDS)
            self.assertFalse(set(self.IDS) & set(report['acceptanceRequirements']['A02']['missingObligations']))
            self.assertFalse(report['acceptanceRequirements']['A08']['complete'])
            self.assertFalse(report['candidateEligible'])

    def fixture(self):
        return self.role_fixture(split_roles=False)

    def role_fixture(self, *, split_roles=True):
        contract, case, base, state = self.flat_fixture()
        def observer(request):
            result = base(request)
            if request['phase'] == 'recheck':
                return result
            w = result['obligationEvidence']['supplement-1']
            old = {k: w['execution'].pop(k) for k in ('actor', 'host', 'entry', 'profile')}
            coordinator = {**old, 'actor': 'root-desktop', 'entry': case['entry']}
            executor = {**copy.deepcopy(old), 'actor': 'cli-peer', 'entry': 'cx-cli',
                'profile': {'model': 'gpt-6.1-sol', 'effort': 'high', 'sandbox': 'read-only', 'approval': 'never'}}
            cleanup = {**copy.deepcopy(coordinator), 'actor': 'root-reader'}
            roles = {'coordinator': coordinator, 'executor': executor,
                     'consumer': copy.deepcopy(coordinator), 'cleanup': cleanup}
            if not split_roles:
                roles = {name: copy.deepcopy(coordinator) for name in roles}
            w['execution']['roles'] = copy.deepcopy(roles)
            by_type = {'pre-effect-binding': 'coordinator', 'select': 'coordinator',
                'native-load': 'executor', 'useful-adoption': 'consumer', 'cleanup': 'cleanup'}
            for node in w['chain']:
                role = by_type[node['type']]
                node['role'] = role
                node['facts'].update(copy.deepcopy(roles[role]))
                node['facts']['permissions'] = {'readOnly': True}
            bound = w['chain'][0]['facts']
            bound['expectedRoles'] = copy.deepcopy(roles)
            # The actual peer/reader identity does not exist at preparation.
            for role in ('executor', 'cleanup'):
                bound['expectedRoles'][role].pop('actor')
            bound['rolePermissions'] = {role: {'readOnly': True} for role in roles}
            bound['oneWriter'] = roles['coordinator']['actor']
            w['chain'][1]['facts']['confirmedExecutor'] = copy.deepcopy(roles['executor'])
            w['chain'][1]['facts']['confirmedPermissions'] = {'readOnly': True}
            for node in w['chain']:
                w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
            self.seal(w, state)
            return result
        return contract, case, observer, state

    def test_desktop_selects_cli_peer_and_adopts_with_actual_roles(self):
        with self.history():
            contract, case, observer, _ = self.role_fixture()
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            self.assertEqual(report.get('obligationEvidence', {}).get('supplement-1', {}).get('supportedObligations'),
                             self.IDS, report.get('obligationEvidenceRejections'))

    def window_observer(self, contract, base, state, variant):
        def observer(request):
            result = base(request)
            if request['phase'] == 'observe':
                w = result['obligationEvidence']['supplement-1']
                index = {'late-load': 1, 'late-adoption': 2, 'late-cleanup': 3}.get(variant)
                if index is not None:
                    w['chain'][0]['facts']['deadlineAt'] = (
                        datetime.fromisoformat(w['chain'][index]['at']) + timedelta(microseconds=500)).isoformat()
                if variant == 'resource-window-mismatch':
                    w['chain'][0]['facts']['resourceLimits']['seconds'] = 1
                w['knownFailuresAndLimits'] = [{'kind': 'deadline-exceeded', 'sources': ['cleanup'],
                    'impacts': [{'obligation': key, 'qualityAxes': [q['axis'] for q in w['quality']],
                        'disposition': 'unaffected', 'basis': 'Synthetic independent scoped effect review',
                        'sources': ['cleanup']} for key in self.IDS]}]
                for node in w['chain']:
                    w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
                self.seal(w, state)
            return result
        return observer

    def test_late_load_or_adoption_cannot_be_excused_by_negative_attribution(self):
        with self.history():
            contract, _, base, state = self.role_fixture()
            for variant in ('late-load', 'late-adoption'):
                with self.subTest(variant=variant):
                    report = self.assess(contract, self.window_observer(contract, base, state, variant))
                    self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))

    def test_resource_seconds_bound_the_sourced_execution_window(self):
        with self.history():
            contract, _, base, state = self.role_fixture()
            report = self.assess(contract, self.window_observer(contract, base, state, 'resource-window-mismatch'))
            self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))

    def test_late_cleanup_retains_failure_with_timely_adoption(self):
        with self.history():
            contract, _, base, state = self.role_fixture()
            report = self.assess(contract, self.window_observer(contract, base, state, 'late-cleanup'))
            self.assertEqual(report.get('obligationEvidence', {}).get('supplement-1', {}).get('supportedObligations'),
                             self.IDS, report.get('obligationEvidenceRejections'))

    def test_roles_reject_unselected_entries_identity_and_permission_drift(self):
        with self.history():
            contract, case, base, state = self.role_fixture()
            for variant in ('deferred-entry', 'other-host', 'native-actor-drift', 'native-role-drift',
                            'unconfirmed-target', 'permission-drift', 'retrospective-executor-profile'):
                with self.subTest(variant=variant):
                    def observer(request):
                        result = base(request)
                        if request['phase'] == 'observe':
                            w = result['obligationEvidence']['supplement-1']
                            if variant == 'deferred-entry':
                                w['execution']['roles']['executor']['entry'] = 'cx-jetbrains'
                            elif variant == 'other-host':
                                w['execution']['roles']['executor']['host'] = 'claude-code'
                            elif variant == 'native-actor-drift':
                                w['chain'][2]['facts']['actor'] = 'another-peer'
                            elif variant == 'native-role-drift':
                                w['chain'][2]['role'] = 'coordinator'
                            elif variant == 'unconfirmed-target':
                                w['chain'][1]['facts']['confirmedExecutor'] = {}
                            elif variant == 'permission-drift':
                                w['chain'][2]['facts']['permissions'] = {'write': True}
                            else:
                                w['chain'][0]['facts']['expectedRoles']['executor']['profile']['effort'] = 'low'
                            for node in w['chain']:
                                w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
                            self.seal(w, state)
                        return result
                    report = self.assess(contract, observer)
                    self.assertIn(case['id'], report['acceptedCases'], report['errors'])
                    self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))

    @staticmethod
    def seal(witness, state):
        digest = a._hash({k: v for k, v in witness.items() if k != 'reviewBundle'})
        witness['reviewBundle']['evidenceSha256'] = digest
        for row in witness['reviewBundle']['reviews']:
            row['evidenceSha256'] = digest
        state['recheck'] = {'evidenceSha256': digest, 'current': copy.deepcopy(witness['current'])}

    def test_bad_supplements_preserve_base_and_exact_gaps(self):
        with self.history():
            contract, case, base, state = self.fixture()
            changes = {
                'parent-obligation': lambda w: w['obligations'][0].update(id='a08-same-business-complete-composition'),
                'cross-scope': lambda w: w['base'].update(case=next(c['id'] for c in contract['acceptance']['admission']['cases'] if c['scope'] != case['scope'])),
                'duplicate-obligation': lambda w: w['obligations'].append(copy.deepcopy(w['obligations'][0])),
                'same-original-episode': lambda w: w['execution'].update(episodeId=case['id']),
                'foreign-native-episode': lambda w: w['chain'][2].update(episodeId='foreign'),
                'wrong-native-origin': lambda w: w['chain'][2]['facts'].update(origin='arbitrary-file-read'),
                'load-without-use': lambda w: w['chain'][3]['facts'].update(useful=False),
                'retrospective-binding': lambda w: w['chain'][0].update(at=w['chain'][2]['at']),
                'missing-permission': lambda w: w['chain'][0]['facts'].update(permissions={}),
                'policy-drift': lambda w: w['chain'][2]['facts']['sourcePolicy'].update(mode='auto'),
                'missing-quality-axis': lambda w: w['quality'].pop(),
                'quality-negative': lambda w: w['quality'][0].update(disposition='unresolved'),
                'source-hash-change': lambda w: w['sources']['native-load'].update(sha256='0'*64),
                'execution-package-substitution': lambda w: w['execution'].update(packageSha256='0'*64),
                'missing-own-source-delta': lambda w: w['differences'].clear(),
                'missing-own-normative-delta': lambda w: w['normativeDifferences'].clear(),
                'stale-current-authority': lambda w: w['current']['context'].update(authority=['pre-effect-binding']),
                'missing-independent-review': lambda w: w['reviewBundle']['reviews'].pop(),
            }
            for name, change in changes.items():
                with self.subTest(name=name):
                    def observer(request):
                        result = base(request)
                        if request['phase'] == 'observe':
                            w = result['obligationEvidence']['supplement-1']
                            change(w)
                            # A new exact material review cannot rescue false
                            # causal facts, incomplete deltas or missing quality.
                            self.seal(w, state)
                        return result
                    report = self.assess(contract, observer)
                    self.assertIn(case['id'], report['acceptedCases'], report['errors'])
                    self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))
                    self.assertIn('supplement-1', report['obligationEvidenceRejections'])
                    self.assertTrue(set(self.IDS) <= set(report['acceptanceRequirements']['A02']['missingObligations']))

    def test_recheck_conflicts_and_failed_base_cannot_support(self):
        with self.history():
            contract, case, base, state = self.fixture()
            for variant in ('changed', 'missing', 'duplicate', 'base-failed', 'deadline-undisclosed', 'negative-unresolved'):
                with self.subTest(variant=variant):
                    def observer(request):
                        result = base(request)
                        if request['phase'] == 'recheck':
                            if variant == 'changed':
                                result['obligationEvidence']['supplement-1']['evidenceSha256'] = '0'*64
                            if variant == 'missing':
                                result.pop('obligationEvidence')
                            if variant == 'duplicate':
                                result['obligationEvidence']['duplicate'] = copy.deepcopy(result['obligationEvidence']['supplement-1'])
                            return result
                        w = result['obligationEvidence']['supplement-1']
                        if variant == 'duplicate':
                            result['obligationEvidence']['duplicate'] = copy.deepcopy(w)
                        if variant == 'base-failed':
                            r = next(r for r in result['records'] if r['case'] == case['id'])
                            r['facts']['effect']['value'] = {}
                        if variant == 'deadline-undisclosed':
                            w['chain'][0]['facts']['deadlineAt'] = w['chain'][1]['at']
                            w['sources']['pre-effect-binding']['sha256'] = a._hash({k: v for k, v in w['chain'][0].items() if k != 'source'})
                        if variant == 'negative-unresolved':
                            w['knownFailuresAndLimits'] = [{'kind': 'deadline-exceeded', 'sources': ['cleanup'],
                                'impacts': [{'obligation': key, 'qualityAxes': [q['axis'] for q in w['quality']],
                                    'disposition': 'unresolved', 'basis': 'Original failure retained', 'sources': ['cleanup']} for key in self.IDS]}]
                        self.seal(w, state)
                        return result
                    report = self.assess(contract, observer)
                    self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))
                    self.assertTrue(set(self.IDS) <= set(report['acceptanceRequirements']['A02']['missingObligations']))
                    if variant != 'base-failed':
                        self.assertIn(case['id'], report['acceptedCases'], report['errors'])
                    else:
                        self.assertNotIn(case['id'], report['acceptedCases'])

    def test_omission_preserves_legacy_envelope_result(self):
        # No optional field means the existing input and verdict stay identical.
        one = self.assess(observer=self.observer)
        two = self.assess(observer=lambda request: self.observer(request))
        self.assertEqual(one, two)

    def test_malformed_optional_mapping_preserves_base(self):
        with self.history():
            contract, case, base, _ = self.fixture()
            def observer(request):
                result = base(request)
                if request['phase'] == 'observe':
                    result['obligationEvidence'] = []
                return result
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))


if __name__ == '__main__':
    unittest.main()
