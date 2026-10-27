"""Synthetic public admission tests; these are not native execution evidence."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from tests.product import test_admission as fixtures
from yiyuan_accord import admission as a


class ObligationEvidenceTests(unittest.TestCase):
    # Reuse the owned temporary Git fixture without inheriting its test suite.
    setUpClass = classmethod(fixtures.CurrentDevelopmentEvidenceTests.setUpClass.__func__)
    git = classmethod(fixtures.DevelopmentEvidenceTests.git.__func__)
    history = fixtures.DevelopmentEvidenceTests.history
    observer = fixtures.CurrentDevelopmentEvidenceTests.observer
    commit = fixtures.CurrentDevelopmentEvidenceTests.commit
    def assess(self, contract=None, observer=None):
        clock = a.datetime
        class FixtureClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.now(tz) + timedelta(seconds=2)
        # Leave room after fixture commits for a strictly ordered execution
        # before canonical whole-second review; retain outer expiry clocks.
        with patch.object(fixtures, 'datetime', FixtureClock), patch.object(a, 'datetime', FixtureClock):
            return fixtures.CurrentDevelopmentEvidenceTests.assess(self, contract, observer)
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
            # Derive the synthetic execution from its already-created review.
            # A second wall-clock sample can place cleanup after that review.
            stamp = min(datetime.fromisoformat(r['reviewedAt'].replace('Z', '+00:00'))
                        for r in result['reviewBundle']['reviews']) - timedelta(seconds=1)
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

    def test_fixture_timeline_survives_later_wall_clock_sample(self):
        wall_clock = datetime
        sampled = False
        class LaterFixture(wall_clock):
            @classmethod
            def now(cls, tz=None):
                nonlocal sampled
                sampled = True
                return wall_clock.now(tz) + timedelta(seconds=10)
        class LaterValidation(wall_clock):
            @classmethod
            def now(cls, tz=None):
                return wall_clock.now(tz) + timedelta(seconds=20 if sampled else 0)
        # The second fixture sample is delayed after the base observer created
        # its review. Only if that sample occurs does validation advance again,
        # isolating review ordering instead of rejecting future events.
        with patch(__name__ + '.datetime', LaterFixture), patch.object(a, 'datetime', LaterValidation):
            self.test_desktop_selects_cli_peer_and_adopts_with_actual_roles()
            self.test_late_cleanup_retains_failure_with_timely_adoption()

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

    def test_selected_cli_coordinator_can_reuse_desktop_base(self):
        with self.history():
            contract, case, base, state = self.role_fixture()
            def observer(request):
                result = base(request)
                if request['phase'] == 'observe':
                    w = result['obligationEvidence']['supplement-1']
                    w['execution']['roles']['coordinator']['entry'] = 'cx-cli'
                    w['chain'][0]['facts']['expectedRoles']['coordinator']['entry'] = 'cx-cli'
                    for node in w['chain']:
                        if node['role'] == 'coordinator':
                            node['facts']['entry'] = 'cx-cli'
                        w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
                    self.seal(w, state)
                return result
            report = self.assess(contract, observer)
            self.assertEqual(report.get('obligationEvidence', {}).get('supplement-1', {}).get('supportedObligations'),
                             self.IDS, report.get('obligationEvidenceRejections'))
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])

    def conflict_observer(self, base, state, *, renamed=False, invalid_bridge=False, operation_collision=False):
        checked = {}
        def observer(request):
            result = base(request)
            if request['phase'] == 'recheck':
                result['obligationEvidence'] = copy.deepcopy(checked)
                return result
            seed = result['obligationEvidence']['supplement-1']
            witnesses = {}
            layout = [('a', self.IDS[:1]), ('b', self.IDS), ('c', self.IDS[1:])]
            if renamed:
                layout = [('c', self.IDS[:1]), ('b', self.IDS), ('a', self.IDS[1:])]
            for name, obligations in layout:
                if operation_collision and name == 'b':
                    continue
                w = copy.deepcopy(seed)
                w['obligations'] = [row for row in w['obligations'] if row['id'] in obligations]
                identity = 'shared' if operation_collision else name
                w['execution']['episodeId'] = 'episode-' + identity
                w['execution']['operationId'] = 'operation-' + identity
                for node in w['chain']:
                    node['episodeId'] = w['execution']['episodeId']
                    node['operationId'] = w['execution']['operationId']
                if invalid_bridge and name == 'b':
                    w['chain'][3]['facts']['useful'] = False
                for node in w['chain']:
                    w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
                sealed = {}
                self.seal(w, sealed)
                checked[name] = sealed['recheck']
                witnesses[name] = w
            result['obligationEvidence'] = witnesses
            return result
        return observer

    def test_coherent_coordinator_identity_still_requires_selected_same_host_entry(self):
        with self.history():
            contract, case, base, state = self.role_fixture()
            for field, value in (('entry', 'cx-jetbrains'), ('host', 'claude-code')):
                with self.subTest(field=field):
                    def observer(request):
                        result = base(request)
                        if request['phase'] == 'observe':
                            w = result['obligationEvidence']['supplement-1']
                            w['execution']['roles']['coordinator'][field] = value
                            w['chain'][0]['facts']['expectedRoles']['coordinator'][field] = value
                            for node in w['chain']:
                                if node['role'] == 'coordinator':
                                    node['facts'][field] = value
                                w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
                            self.seal(w, state)
                        return result
                    report = self.assess(contract, observer)
                    self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))
                    self.assertIn(case['id'], report['acceptedCases'], report['errors'])

    def test_transitive_conflicts_reject_all_members_regardless_of_key_names(self):
        with self.history():
            contract, case, base, state = self.role_fixture()
            for renamed in (False, True):
                with self.subTest(renamed=renamed):
                    report = self.assess(contract, self.conflict_observer(base, state, renamed=renamed))
                    self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))
                    self.assertEqual(set(report.get('obligationEvidenceRejections', {})), {'a', 'b', 'c'})
                    self.assertIn(case['id'], report['acceptedCases'], report['errors'])

    def test_invalid_bridge_does_not_poison_valid_independent_witnesses(self):
        with self.history():
            contract, case, base, state = self.role_fixture()
            report = self.assess(contract, self.conflict_observer(base, state, invalid_bridge=True))
            self.assertEqual(set(report.get('obligationEvidence', {})), {'a', 'c'}, report.get('obligationEvidenceRejections'))
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])

    def test_operation_conflicts_reject_distinct_obligations_together(self):
        with self.history():
            contract, case, base, state = self.role_fixture()
            report = self.assess(contract, self.conflict_observer(base, state, operation_collision=True))
            self.assertFalse(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))
            self.assertEqual(set(report.get('obligationEvidenceRejections', {})), {'a', 'c'})
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])

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
            for variant in ('deferred-entry', 'other-host', 'coordinator-deferred-entry', 'coordinator-other-host',
                            'native-actor-drift', 'native-role-drift',
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
                            elif variant == 'coordinator-deferred-entry':
                                w['execution']['roles']['coordinator']['entry'] = 'cx-jetbrains'
                            elif variant == 'coordinator-other-host':
                                w['execution']['roles']['coordinator']['host'] = 'claude-code'
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
                            w['differences'][0]['sources'].append('actual')
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
                        self.assertEqual(report.get('obligationEvidenceRejectionCodes'),
                                         ['supplementary-base-case-not-admitted'])

    def test_reference_diagnostics_preserve_optional_failure_and_guard_order(self):
        for version in (1, 2):
            with self.subTest(version=version), self.history():
                def change(w):
                    section = w if version == 1 else w['sourceEpochs'][0]
                    row = section[field][0]
                    row['sources'].append('actual')
                    if variant == 'current':
                        row['sources'] = ['analysis']
                        row['currentConsequences'].append('analysis')
                    elif variant == 'hash': row['newSha256'] = '0' * 64
                    elif variant == 'shape': row['extra'] = True
                    elif variant == 'unknown': row['sources'].append('private-source-canary')
                    elif variant == 'duplicate': row['sources'].append('actual')
                    elif variant == 'unhashable': row['sources'].append({})
                if version == 1:
                    contract, case, base, state = self.fixture()
                    def observer(request):
                        result = base(request)
                        if request['phase'] == 'observe':
                            w = result['obligationEvidence']['supplement-1']
                            change(w)
                            self.seal(w, state)
                        return result
                else:
                    contract, observer = self.correction_fixture(change)
                for field in ('differences', 'normativeDifferences'):
                    for variant in ('analysis', 'current', 'hash', 'shape', 'unknown', 'duplicate', 'unhashable'):
                        with self.subTest(field=field, variant=variant):
                            report = self.assess(contract, observer)
                            code = {'analysis': 'source-analysis-reference-kind-mismatch',
                                    'current': 'current-observation-reference-kind-mismatch'}.get(variant)
                            self.assertEqual(report.get('obligationEvidenceRejectionCodes', []), [code] if code else [])
                            self.assertEqual(report['obligationEvidenceRejections']['supplement-1'],
                                             'supplementary-execution-unsupported')
                            self.assertFalse(report.get('obligationEvidence'))
                            self.assertEqual(report['errors'], [])
                            if version == 1:
                                self.assertIn(case['id'], report['acceptedCases'])
                                self.assertTrue(set(self.IDS) <= set(report['acceptanceRequirements']['A02']['missingObligations']))
                            else:
                                self.assertEqual(report['acceptedCases'], [])
                                self.assertIn('a04-actual-retroactive-correction',
                                              report['acceptanceRequirements']['A04']['missingObligations'])
                            self.assertFalse(report['candidateEligible'])
                            self.assertNotIn('private-source-canary', repr(report))

    def test_supplement_exception_text_and_foreign_codes_are_not_diagnostics(self):
        from yiyuan_accord import obligation_evidence
        with self.history():
            contract, case, observer, _ = self.fixture()
            for error in (ValueError('private-exception-canary'),
                          a._CaseRejection('private-exception-canary', ['unhashable'])):
                error.codes = getattr(error, 'codes', ('source-analysis-reference-kind-mismatch',))
                with self.subTest(type=type(error).__name__), patch.object(
                        obligation_evidence, 'evaluate', side_effect=error):
                    report = self.assess(contract, observer)
                    self.assertIn(case['id'], report['acceptedCases'])
                    self.assertEqual(report['errors'], [])
                    self.assertEqual(report['obligationEvidenceRejections']['supplement-1'],
                                     'supplementary-execution-unsupported')
                    self.assertNotIn('obligationEvidenceRejectionCodes', report)
                    self.assertNotIn('private-exception-canary', repr(report))

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


    def correction_fixture(self, change=lambda w: None):
        contract, case, base, state = self.flat_fixture()
        def observer(request):
            result = base(request)
            if request['phase'] != 'observe':
                return result
            w = result['obligationEvidence']['supplement-1']
            w.update(schema='yiyuan-accord-obligation-execution-evidence/v2',
                     type='independent-native-root-correction-poststate')
            w.pop('base'); w.pop('obligations')
            w['obligation'] = copy.deepcopy(next(o for r in contract['acceptance']['admission']['acceptanceRequirements']
                for o in r['outcomeObligations'] if o['id'] == 'a04-actual-retroactive-correction'))
            for key in ('managedSkill', 'sourcePolicy'): w['execution'].pop(key)
            w['sourceEpochs'] = [{'subject': w['execution'].pop('subject'),
                'projectionPackageSha256': w['execution'].pop('packageSha256'),
                'differences': w.pop('differences'), 'normativeDifferences': w.pop('normativeDifferences')}]
            revision = w['sourceEpochs'][0]['subject']['revision']
            w['execution']['loadedPackage'] = {'sha256': None, 'sources': ['native-load'],
                'limits': 'Point observation; full loaded bytes unknown.'}
            w['execution'].update(actor='root', entry='cx-desktop')
            stamp = min(datetime.fromisoformat(r['reviewedAt'].replace('Z', '+00:00')) for r in w['reviewBundle']['reviews'])
            w['current'].update(observedAt=stamp.isoformat(), maxAgeSeconds=300)
            affected = {'target': 'old-copy', 'disposition': 'corrected-and-verified',
                'before': ['pre-effect-binding'], 'after': ['useful-adoption'],
                'verification': ['useful-adoption'], 'basis': 'Dependent copy corrected; source preserved.'}
            facts = [('authority', {'origin': 'native-user-input', 'task': 'Correct the affected copy',
                'constraints': 'Keep source', 'permissions': {'write': 'copy'}, 'oneWriter': 'root'}),
                ('correction', {'callId': 'native-call-1', 'cause': ['pre-effect-binding'],
                    'targets': ['useful-adoption'], 'result': ['native-load'], 'success': True}),
                ('poststate', {'affected': [affected], 'preserved': ['pre-effect-binding'],
                    'retainedFailures': [], 'verification': ['native-load'], 'adoption': ['useful-adoption']}),
                ('cleanup', {'resourcesReleased': True, 'poststate': ['native-load']})]
            w['chain'] = []
            for i, (kind, fact) in enumerate(facts):
                node = {'type': kind, 'at': (stamp-timedelta(seconds=1, microseconds=-i)).isoformat(),
                        'actor': 'root', 'facts': fact, 'sourceEpochs': [] if kind == 'authority' else [revision]}
                w['sources'][kind] = {'sourceRef': 'fixture://' + kind, 'sha256': a._hash(node), 'kind': 'execution-observation'}
                w['chain'].append({**node, 'source': kind})
            change(w)
            # Reseal node identities too: rejection must exercise the changed
            # relationship, not an incidental stale node digest.
            for node in w['chain']:
                if isinstance(node, dict):
                    w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
            self.seal(w, state)
            # No base case can carry this independent consequence.
            result['records'] = []
            return result
        return contract, observer

    def test_independent_correction_does_not_admit_cases_or_complete_scope(self):
        with self.history():
            report = self.assess(*self.correction_fixture())
            self.assertEqual(report['acceptedCases'], [])
            leaf = report.get('obligationEvidence', {}).get('supplement-1', {})
            self.assertNotIn('baseCase', leaf)
            self.assertEqual(leaf.get('supportedObligations'), ['a04-actual-retroactive-correction'],
                             (report['errors'], report.get('obligationEvidenceRejections')))
            self.assertEqual(leaf.get('operationId'), 'operation-1')
            missing = report['acceptanceRequirements']['A04']['missingObligations']
            self.assertNotIn('a04-actual-retroactive-correction', missing)
            self.assertEqual(len(missing), 3)
            self.assertFalse(report['acceptanceRequirements']['A04']['complete'])
            self.assertFalse(report['candidateEligible'])

    def test_invalid_independent_correction_cannot_rescue_its_leaf(self):
        changes = [lambda w: w.update(base={'case': 'failed-cli'}),
            lambda w: w['obligation'].update(id='a08-same-business-complete-composition'),
            lambda w: w['execution'].update(entry='fixture-undeclared-entry'),
            lambda w: w['sourceEpochs'][0].update(projectionPackageSha256='0'*64),
            lambda w: w['chain'].__setitem__(1, None),
            lambda w: w['chain'][0].update(at=w['chain'][1]['at']),
            lambda w: w['chain'][2]['facts']['affected'][0].update(disposition='unresolved'),
            lambda w: w['chain'][3]['facts'].update(resourcesReleased=False),
            lambda w: w['chain'][1].update(sourceEpochs=['f'*40]),
            lambda w: w['quality'].pop(), lambda w: w['sourceEpochs'][0]['differences'].clear(),
            lambda w: w['sourceEpochs'][0]['normativeDifferences'].clear(),
            lambda w: w['current'].update(observedAt='2000-01-01T00:00:00Z'),
            lambda w: w['reviewBundle']['reviews'].pop()]
        for i, change in enumerate(changes):
            with self.subTest(i=i), self.history():
                report = self.assess(*self.correction_fixture(change))
                self.assertFalse(report.get('obligationEvidence'))
                self.assertIn('a04-actual-retroactive-correction', report['acceptanceRequirements']['A04']['missingObligations'])

    def test_multiple_source_epochs_and_different_loaded_bytes_remain_distinct(self):
        def change(w):
            current = w['current']
            w['execution']['loadedPackage']['sha256'] = 'a'*64
            w['sourceEpochs'].append({'subject': current['subject'], 'projectionPackageSha256': current['packageSha256'],
                                     'differences': [], 'normativeDifferences': []})
            w['chain'][-1]['sourceEpochs'] = [current['subject']['revision']]
        for bad in (None, 'package', 'delta'):
            def variation(w):
                change(w)
                if bad == 'package': w['sourceEpochs'][1]['projectionPackageSha256'] = '0'*64
                if bad == 'delta': w['sourceEpochs'][1]['differences'].append({'path': 'undeclared'})
            with self.subTest(bad=bad), self.history():
                report = self.assess(*self.correction_fixture(variation))
                self.assertEqual('supplement-1' in report.get('obligationEvidence', {}), bad is None,
                                 (report['errors'], report.get('obligationEvidenceRejections')))

    def test_undeclared_independent_route_stays_closed(self):
        with self.history():
            contract, observer = self.correction_fixture()
            contract['acceptance']['admission'].pop('independentObligationEvidence')
            self.commit(contract)
            report = self.assess(contract, observer)
            self.assertFalse(report.get('obligationEvidence'))
            self.assertIn('a04-actual-retroactive-correction', report['acceptanceRequirements']['A04']['missingObligations'])

    def test_current_entry_deferral_holds_independent_leaf(self):
        with self.history():
            contract, observer = self.correction_fixture()
            policy = contract['acceptance']['admission']
            for row in [*policy['scopes'], *policy['cases']]:
                conditions = row['conditions']
                parent = row.get('scope', row.get('id')) in {
                    'v33-admitted-entry-delivery', 'v33-admitted-entry-lifecycle'}
                if 'entryDispositions' in conditions:
                    conditions['entryDispositions']['cx-desktop'].update(
                        status='deferred', basis='Synthetic current deferral.')
                    if parent: row['subjectEntries'].remove('cx-desktop')
                if 'subjectEntries' in conditions:
                    conditions['subjectEntries'].remove('cx-desktop')
                    conditions.get('selectedModes', {}).pop('cx-desktop', None)
                if parent or 'subjectEntries' in conditions:
                    for matrix in row.get('expected', {}).get('effect', {}).values():
                        if isinstance(matrix, dict): matrix.pop('cx-desktop', None)
            self.assertEqual(a.admission_contract_errors(contract), [])
            self.commit(contract)
            report = self.assess(contract, observer)
            self.assertEqual(report['errors'], [])
            self.assertEqual(report.get('obligationEvidenceRejections', {}).get('supplement-1'),
                             'supplementary-execution-unsupported')
            self.assertFalse(report.get('obligationEvidence'))
            self.assertIn('a04-actual-retroactive-correction', report['acceptanceRequirements']['A04']['missingObligations'])

    def test_independent_current_observation_expires_only_at_final_check(self):
        shift = [timedelta(0)]
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) + shift[0]
        with self.history():
            contract, base = self.correction_fixture()
            def observer(request):
                result = base(request)
                if request['phase'] == 'recheck': shift[0] = timedelta(seconds=301)
                return result
            with patch.object(a, 'datetime', Clock):
                report = self.assess(contract, observer)
            self.assertEqual(report.get('obligationEvidenceRejections', {}).get('supplement-1'),
                             'supplementary-final-qualification-failed', report['errors'])
            self.assertFalse(report.get('obligationEvidence'))
            self.assertIn('a04-actual-retroactive-correction', report['acceptanceRequirements']['A04']['missingObligations'])


    def goal_fixture(self, change=lambda w: None, *, enabled=True):
        contract, _, base, state = self.role_fixture()
        case = next(c for c in contract['acceptance']['admission']['cases']
                    if c['id'] == a._SUPPLEMENTAL_GOAL_POLICY['baseCase'])
        if not enabled:
            contract['acceptance']['admission'].pop('supplementalGoalEvidence')
            self.commit(contract)
        def observer(request):
            result = base(request)
            if request['phase'] != 'observe':
                return result
            w = result['obligationEvidence']['supplement-1']
            record = next(r for r in result['records'] if r['case'] == case['id'])
            w.update(schema=a._SUPPLEMENTAL_GOAL_POLICY['schema'],
                     base={'case': case['id'], 'recordSha256': a._hash(record)})
            w['obligations'] = [{'id': a._SUPPLEMENTAL_GOAL_POLICY['obligation'],
                'criterion': copy.deepcopy(next(o for r in contract['acceptance']['admission']['acceptanceRequirements']
                    for o in r['outcomeObligations'] if o['id'] == a._SUPPLEMENTAL_GOAL_POLICY['obligation'])['source'])}]
            for k in ('managedSkill', 'sourcePolicy'):
                w['execution'].pop(k)
            w['execution']['inputMode'] = 'transparent-maintainer-evaluation'
            roles = w['execution']['roles']
            roles['requester'] = {**copy.deepcopy(roles['coordinator']), 'actor': 'maintainer-input-driver'}
            def source(key, value):
                w['sources'][key] = {'sourceRef': 'fixture://' + key, 'sha256': a._hash(value),
                                     'kind': 'execution-observation'}
                return key
            text = 'Organize these supplied records so tomorrow\'s colleague can use them.'
            incoming = source('ordinary-input', {'text': text, 'origin': 'transparent-maintainer-evaluation'})
            material = source('supplied-records', {'synthetic': True, 'rows': ['pending', 'confirmed']})
            def artifact(key, value):
                source(key, value)
                return {'id': key, 'source': key, 'sha256': w['sources'][key]['sha256']}
            requirements = artifact('requirements', {'use': 'contact pending registrants', 'retain': 'confirmed'})
            output = artifact('result-bundle', {'contact': ['pending'], 'sourcePreserved': True})
            use = source('consumer-use', {'used': 'pending contact identified from delivered artifact'})
            application = source('actual-application', {'requirements': requirements, 'output': output})
            poststate = source('owned-resource-poststate', {'worker': 0, 'originalsUnchanged': True})
            bound = {k: copy.deepcopy(v) for k, v in w['chain'][0]['facts'].items()
                     if k not in {'managedSkill', 'sourcePolicy', 'selectionDelegation'}}
            bound.update(naturalInput=text, inputMode=w['execution']['inputMode'], oneWriter='executor',
                         expectedRoles=copy.deepcopy(roles),
                         rolePermissions={name: {'readOnly': True} for name in roles})
            facts = [bound,
                {'origin': w['execution']['inputMode'], 'inputSource': incoming, 'naturalInput': text},
                {'inputSource': incoming, 'materialSources': [material], 'requirements': requirements,
                 'resolution': {'mode': 'source-grounded-interpretation',
                    'alternatives': ['on-site check-in list', 'pending-contact work list'],
                    'basis': 'The supplied handover note specifies contacting pending registrants.',
                    'clarificationSources': []}},
                {'requirements': copy.deepcopy(requirements), 'applicationSources': [application], 'output': output},
                {'requirements': copy.deepcopy(requirements), 'output': copy.deepcopy(output),
                 'useSources': [use], 'useful': True},
                {'resourcesReleased': True, 'poststate': [poststate]}]
            kinds = ('pre-effect-binding', 'ordinary-goal-input', 'goal-interpretation',
                     'requirements-applied', 'useful-adoption', 'cleanup')
            names = ('coordinator', 'requester', 'executor', 'executor', 'consumer', 'cleanup')
            stamp = datetime.fromisoformat(w['chain'][0]['at'].replace('Z', '+00:00'))
            w['chain'] = []
            for i, (kind, name, fact) in enumerate(zip(kinds, names, facts, strict=True)):
                node = {'type': kind, 'episodeId': w['execution']['episodeId'],
                    'operationId': w['execution']['operationId'], 'sequence': i,
                    'at': (stamp + timedelta(milliseconds=i)).isoformat(), 'role': name,
                    'facts': {**copy.deepcopy(roles[name]), 'permissions': {'readOnly': True}, **fact}}
                w['chain'].append({**node, 'source': source(kind, node)})
            package = Path(contract['delivery']['hostProjections'][0]['manifest']).parents[1].as_posix()
            changes = a._impact_differences(self.root, w['execution']['subject']['revision'], request['subject']['revision'],
                (package, package), case['oracleFiles'], {'calls': 0, 'files': 0, 'bytes': 0}, complete=True)
            w['differences'] = [{**row, 'basis': 'Synthetic complete source comparison',
                'sources': ['analysis'], 'currentConsequences': ['actual']} for row in changes]
            change(w)
            for node in w['chain']:
                w['sources'][node['source']]['sha256'] = a._hash({k: v for k, v in node.items() if k != 'source'})
            self.seal(w, state)
            return result
        return contract, case, observer, state

    def test_a01_v3_source_grounded_requirements_support_only_existing_leaf(self):
        with self.history():
            contract, case, observer, _ = self.goal_fixture()
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            leaf = report.get('obligationEvidence', {}).get('supplement-1', {})
            self.assertEqual(leaf.get('baseCase'), case['id'], report.get('obligationEvidenceRejections'))
            self.assertEqual(leaf.get('supportedObligations'), ['a01-ambiguous-goal-to-requirements'])
            self.assertNotIn('evidenceKind', leaf)
            self.assertNotIn('a01-ambiguous-goal-to-requirements',
                             report['acceptanceRequirements']['A01']['missingObligations'])
            self.assertFalse(report['candidateEligible'])

    def test_a01_v3_allows_sourced_clarification_without_mandatory_question(self):
        def clarify(w):
            w['sources']['necessary-answer'] = {'sourceRef': 'fixture://answer', 'sha256': 'c'*64,
                                               'kind': 'execution-observation'}
            w['chain'][2]['facts']['resolution'].update(mode='necessary-clarification',
                                                       clarificationSources=['necessary-answer'])
        with self.history():
            contract, case, observer, _ = self.goal_fixture(clarify)
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            self.assertTrue(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))

    def test_a01_v3_actual_input_can_arrive_before_effect_binding(self):
        def prior_input(w):
            bound, incoming = w['chain'][:2]
            incoming['at'] = (datetime.fromisoformat(bound['at']) - timedelta(milliseconds=1)).isoformat()
            incoming['sequence'], bound['sequence'] = 0, 1
            w['chain'][:2] = [incoming, bound]
        with self.history():
            contract, case, observer, _ = self.goal_fixture(prior_input)
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            self.assertTrue(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))

    def test_a01_v3_equivalent_artifact_source_aliases_keep_identity(self):
        def aliases(w):
            for name, i, field in [('requirements-alias', 3, 'requirements'), ('output-alias', 4, 'output')]:
                value = w['chain'][i]['facts'][field]
                w['sources'][name] = copy.deepcopy(w['sources'][value['source']])
                value['source'] = name
        with self.history():
            contract, case, observer, _ = self.goal_fixture(aliases)
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            self.assertTrue(report.get('obligationEvidence'), report.get('obligationEvidenceRejections'))

    def goal_deadline_failure(self, w):
        w['knownFailuresAndLimits'] = [{'kind': 'deadline-exceeded', 'sources': ['cleanup'],
            'impacts': [{'obligation': 'a01-ambiguous-goal-to-requirements',
                'qualityAxes': [q['axis'] for q in w['quality']], 'disposition': 'unaffected',
                'basis': 'Only mechanical cleanup was late.', 'sources': ['cleanup']}]}]

    def test_a01_v3_late_cleanup_can_be_accounted_but_not_late_adoption(self):
        for adoption_late in (False, True):
            with self.subTest(adoption_late=adoption_late), self.history():
                def change(w):
                    i = 3 if adoption_late else 4
                    at = datetime.fromisoformat(w['chain'][i]['at']) + timedelta(microseconds=500)
                    w['chain'][0]['facts']['deadlineAt'] = at.isoformat()
                    self.goal_deadline_failure(w)
                contract, case, observer, _ = self.goal_fixture(change)
                report = self.assess(contract, observer)
                self.assertIn(case['id'], report['acceptedCases'], report['errors'])
                self.assertEqual(bool(report.get('obligationEvidence')), not adoption_late,
                                 report.get('obligationEvidenceRejections'))

    def test_a01_v3_policy_omission_preserves_base_and_keeps_leaf_open(self):
        with self.history():
            contract, case, observer, _ = self.goal_fixture(enabled=False)
            report = self.assess(contract, observer)
            self.assertIn(case['id'], report['acceptedCases'], report['errors'])
            self.assertFalse(report.get('obligationEvidence'))
            self.assertIn('a01-ambiguous-goal-to-requirements',
                          report['acceptanceRequirements']['A01']['missingObligations'])

    def test_a01_v3_policy_rejects_other_schema_obligation_case_or_extra_field(self):
        for change in ({'schema': 'yiyuan-accord-obligation-execution-evidence/v1'},
                       {'obligation': 'a04-actual-retroactive-correction'},
                       {'baseCase': 'another-case'}, {'extra': True}):
            with self.subTest(change=change):
                contract = copy.deepcopy(self.contract)
                contract['acceptance']['admission']['supplementalGoalEvidence'].update(change)
                self.assertIn('supplemental goal evidence policy is invalid', a.admission_contract_errors(contract))

    def test_a01_v3_resealed_wrong_relationships_do_not_rescue_leaf(self):
        def wrong_entry(w):
            w['execution']['roles']['executor']['entry'] = 'cx-desktop'
            w['chain'][0]['facts']['expectedRoles']['executor']['entry'] = 'cx-desktop'
            for node in w['chain']:
                if node['role'] == 'executor': node['facts']['entry'] = 'cx-desktop'
        changes = {
            'foreign-obligation': lambda w: w['obligations'][0].update(id='a02-delegated-managed-selection'),
            'record-substitution': lambda w: w['base'].update(recordSha256='0'*64),
            'selected-but-wrong-entry': wrong_entry,
            'requester-role-confusion': lambda w: w['chain'][1].update(role='executor'),
            'input-without-origin': lambda w: w['chain'][1]['facts'].update(origin='file-exists'),
            'input-substitution': lambda w: w['chain'][1]['facts'].update(naturalInput='A different clear goal'),
            'missing-input-locator': lambda w: w['sources'].pop('ordinary-input'),
            'unrelated-input-link': lambda w: w['chain'][2]['facts'].update(inputSource='supplied-records'),
            'unsourced-clarification': lambda w: w['chain'][2]['facts']['resolution'].update(mode='necessary-clarification'),
            'missing-goal-alternatives': lambda w: w['chain'][2]['facts']['resolution'].update(alternatives=['formatting']),
            'requirements-id-switch': lambda w: w['chain'][3]['facts']['requirements'].update(id='another-requirement'),
            'requirements-hash-switch': lambda w: w['chain'][4]['facts']['requirements'].update(sha256='0'*64),
            'output-id-switch': lambda w: w['chain'][4]['facts']['output'].update(id='another-output'),
            'output-hash-switch': lambda w: w['chain'][4]['facts']['output'].update(sha256='0'*64),
            'unused-result': lambda w: w['chain'][4]['facts'].update(useful=False),
            'no-use-source': lambda w: w['chain'][4]['facts'].update(useSources=[]),
            'old-coordinator-writer': lambda w: w['chain'][0]['facts'].update(oneWriter='root-desktop'),
            'missing-resource-release': lambda w: w['chain'][5]['facts'].update(resourcesReleased=False),
            'missing-quality': lambda w: w['quality'].pop(),
            'historical-current-authority': lambda w: w['current']['context'].update(authority=['ordinary-input']),
        }
        for name, change in changes.items():
            with self.subTest(name=name), self.history():
                contract, case, observer, _ = self.goal_fixture(change)
                report = self.assess(contract, observer)
                self.assertIn(case['id'], report['acceptedCases'], report['errors'])
                self.assertFalse(report.get('obligationEvidence'), name)
                self.assertIn('a01-ambiguous-goal-to-requirements',
                              report['acceptanceRequirements']['A01']['missingObligations'])


if __name__ == '__main__':
    unittest.main()
