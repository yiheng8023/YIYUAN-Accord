"""Source-obligation regressions; synthetic records are never product evidence."""

import copy
import unittest

import tests.product.test_admission as admission_fixtures
from yiyuan_accord import admission


class FunctionalObligationCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_type = admission_fixtures.CurrentDevelopmentEvidenceTests
        cls.fixture_type.setUpClass()
        cls.addClassCleanup(cls.fixture_type.doClassCleanups)

    def setUp(self):
        self.fixture = self.fixture_type()
        self.contract = copy.deepcopy(self.fixture.contract)
        policy = self.contract['acceptance']['admission']
        # Use the real observer, package/source guards and final recheck. Freeze
        # generic-only expected facts instead of copying improved declarations.
        claims = ['function', 'package-lifecycle', 'impact-assessment']
        common = {
            'host': 'codex', 'entry': 'cx-desktop', 'claims': claims,
            'duties': [row['id'] for row in self.contract['acceptance']['duties']],
            'qualityAxes': [row['id'] for row in self.contract['systemOptimization']['qualityAxes']],
            'scenarios': [],
            'conditions': {'effectiveHostConfigurationAndAuthority': 'same-synthetic-condition'},
        }
        scope = {**copy.deepcopy(common), 'id': 'fixture-continuity', 'rule': 'Synthetic source-bound outcomes only.'}
        self.case = {
            **copy.deepcopy(common), 'id': 'fixture-healthy-continuation', 'scope': scope['id'],
            'oracle': 'Independent source observation; labels alone are not complete functional branches.',
            'oracleFiles': ['docs/operations/ACCEPTANCE-v3.3.md', 'docs/operations/PLAN-v3.3.md'],
            'maxAgeSeconds': 3600,
            'expected': {
                'effect': {'businessOutcomeCorrect': True,
                           'requiredDutiesObserved': {key: True for key in common['duties']},
                           'healthyContinuationSelected': True, 'transferNeededThisTurn': False},
                'authority': {'singleWriterAndNecessaryAuthorityVerified': True},
                'poststate': {'requiredInheritanceAndContinuationVerified': True},
                'cleanup': {'ownedTemporaryResourcesReleasedOrJustifiablyRetained': True},
                'comparison': {'independentPoststateVerified': True},
            },
        }
        policy['requiredHosts'] = ['codex']
        policy['requiredCoverage'] = {claim: [scope['id']] for claim in claims}
        policy['requiredCoverage']['incremental-value'] = []
        policy['scopes'], policy['cases'] = [scope], [self.case]
        policy['acceptanceRequirements'] = [
            {'id': f'A{number:02}', 'requiredCoverage': {claim: [scope['id']] for claim in claims},
             'outcomeObligations': [self.obligation(f'A{number:02}', f'outcome-{number}',
                                                   '/effect/businessOutcomeCorrect')]}
            for number in range(1, 9)]
        self.requirement = policy['acceptanceRequirements'][4]
        self.requirement['outcomeObligations'] = [
            self.obligation('A05', 'necessary-migration', '/effect/necessaryMigrationObserved'),
            self.obligation('A05', 'independent-takeover', '/poststate/independentTakeoverVerified')]
        self.contract['cycle']['targetVersion'] = '3.3.2'
        self.history = self.fixture.history()
        self.history.__enter__()
        self.addCleanup(self.history.__exit__, None, None, None)

    @staticmethod
    def obligation(requirement, identity, pointer):
        return {'id': identity, 'source': {'path': 'docs/operations/ACCEPTANCE-v3.3.md',
                                         'anchor': requirement},
                'scope': 'fixture-continuity', 'claim': 'function', 'pointer': pointer, 'expected': True}

    def capability_case(self):
        case = copy.deepcopy(self.case)
        case['id'] = 'fixture-necessary-takeover'
        case['expected']['effect']['necessaryMigrationObserved'] = True
        case['expected']['poststate']['independentTakeoverVerified'] = True
        self.contract['acceptance']['admission']['cases'].append(case)
        return case

    def assess(self, *, missing_record=None, corrupt_fact=False, drift=False):
        self.fixture.commit(self.contract)
        def observer(request):
            result = self.fixture.observer(request)
            if request['phase'] == 'observe':
                result['records'] = [record for record in result['records'] if record['case'] != missing_record]
                if corrupt_fact:
                    result['records'][-1]['facts']['poststate']['value']['independentTakeoverVerified'] = False
            elif drift:
                result['conditions']['fixture-necessary-takeover']['effectiveHostConfigurationAndAuthority'] = 'drifted'
            return result
        return self.fixture.assess(self.contract, observer)

    def test_complete_labels_do_not_close_unobserved_functional_branches(self):
        report = self.assess()
        self.assertEqual(report['errors'], [])
        self.assertEqual(report['acceptedCases'], [self.case['id']])
        self.assertEqual(report['caseRejections'], {})
        row = report['acceptanceRequirements']['A05']
        self.assertFalse(row['complete'])
        self.assertEqual(row['missingObligations'], ['independent-takeover', 'necessary-migration'])
        self.assertEqual(set(row['missingObligationReasons'].values()), {'consequence-unobserved'})
        self.assertIn('A05', report['acceptanceRequirements']['A08']['blockedBy'])
        self.assertTrue(report['acceptanceRequirements']['A01']['complete'])
        self.assertFalse(report['functionalCompletion'])
        self.assertFalse(report['candidateEligible'])
        self.assertEqual(report['progress']['coverageVerified'], 2)

    def test_same_conditions_complete_capability_evidence_can_close_healthy_episode(self):
        self.capability_case()
        report = self.assess()
        self.assertEqual(report['errors'], [])
        self.assertTrue(report['functionalCompletion'])
        self.assertTrue(report['candidateEligible'])
        self.assertTrue(report['acceptanceRequirements']['A05']['complete'])
        self.assertTrue(report['acceptanceRequirements']['A08']['complete'])
        self.assertEqual(report['acceptanceRequirements']['A05']['missingObligations'], [])
        self.assertFalse(self.case['expected']['effect']['transferNeededThisTurn'])

    def test_unobserved_lifecycle_obligation_holds_completion_without_erasing_other_requirements(self):
        self.capability_case()
        row = self.contract['acceptance']['admission']['acceptanceRequirements'][5]['outcomeObligations'][0]
        row['claim'], row['pointer'] = 'package-lifecycle', '/poststate/lifecycleExitVerified'
        report = self.assess()
        self.assertEqual(report['errors'], [])
        self.assertTrue(report['acceptanceRequirements']['A05']['complete'])
        self.assertEqual(report['acceptanceRequirements']['A06']['missingObligations'], ['outcome-6'])
        self.assertEqual(report['acceptanceRequirements']['A08']['blockedBy'], ['A06'])
        self.assertFalse(report['functionalCompletion'])
        self.assertFalse(report['candidateEligible'])

    def test_missing_or_nonmatching_sources_do_not_discharge_obligations(self):
        capability = self.capability_case()
        for kind in ('missing-record', 'false-fact', 'condition-drift', 'different-scope',
                     'different-claim', 'oracle-source', 'anchor-source'):
            with self.subTest(kind=kind), self.fixture.history():
                saved = copy.deepcopy(self.contract)
                try:
                    if kind == 'different-scope':
                        other = copy.deepcopy(self.contract['acceptance']['admission']['scopes'][0])
                        other['id'] = capability['scope'] = 'other-scope'
                        self.contract['acceptance']['admission']['scopes'].append(other)
                    elif kind == 'different-claim':
                        capability['claims'] = ['package-lifecycle']
                    elif kind == 'oracle-source':
                        self.requirement['outcomeObligations'][0]['source']['path'] = 'GLOSSARY.md'
                    elif kind == 'anchor-source':
                        source = self.fixture.root / 'docs/operations/ACCEPTANCE-v3.3.md'
                        source.write_text('No criterion identifiers are present.', encoding='utf-8')
                    report = self.assess(missing_record=capability['id'] if kind == 'missing-record' else None,
                                         corrupt_fact=kind == 'false-fact', drift=kind == 'condition-drift')
                    self.assertFalse(report['acceptanceRequirements']['A05']['complete'])
                    self.assertIn('necessary-migration', report['acceptanceRequirements']['A05']['missingObligations'])
                    self.assertIn(self.case['id'], report['acceptedCases'])
                    self.assertFalse(report['functionalCompletion'])
                    self.assertFalse(report['candidateEligible'])
                    if kind in {'oracle-source', 'anchor-source'}:
                        reason = report['acceptanceRequirements']['A05']['missingObligationReasons']['necessary-migration']
                        self.assertEqual(reason, 'criterion-not-in-case-oracle' if kind == 'oracle-source'
                                         else 'criterion-anchor-unavailable')
                finally:
                    self.contract = saved
                    policy = self.contract['acceptance']['admission']
                    self.requirement = policy['acceptanceRequirements'][4]
                    capability = policy['cases'][1]

    def test_obligation_schema_rejects_invalid_declarations(self):
        self.capability_case()
        for kind in ('duplicate', 'scope', 'claim', 'pointer', 'nonleaf', 'false', 'null', 'numeric',
                     'source-path', 'source-anchor', 'partial', 'all-omitted', 'empty'):
            contract = copy.deepcopy(self.contract)
            policy = contract['acceptance']['admission']
            row = policy['acceptanceRequirements'][4]['outcomeObligations'][0]
            if kind == 'duplicate': row['id'] = policy['acceptanceRequirements'][0]['outcomeObligations'][0]['id']
            elif kind == 'scope': row['scope'] = 'missing'
            elif kind == 'claim': row['claim'] = 'incremental-value'
            elif kind == 'pointer': row['pointer'] = '/effect/bad~2escape'
            elif kind == 'nonleaf': row['pointer'] = '/effect/requiredDutiesObserved'
            elif kind in {'false', 'null', 'numeric'}:
                policy['cases'][1]['expected']['effect']['necessaryMigrationObserved'] = {
                    'false': False, 'null': None, 'numeric': 1}[kind]
            elif kind == 'source-path': row['source']['path'] = '../outside.md'
            elif kind == 'source-anchor': row['source']['anchor'] = 'an-invented-criterion'
            elif kind == 'partial': policy['acceptanceRequirements'][0].pop('outcomeObligations')
            elif kind == 'all-omitted':
                for requirement in policy['acceptanceRequirements']: requirement.pop('outcomeObligations')
            else: policy['acceptanceRequirements'][0]['outcomeObligations'] = []
            with self.subTest(kind=kind):
                self.assertTrue(admission.admission_contract_errors(contract))

    def test_legacy_declaration_keeps_original_shape_and_digest(self):
        self.contract['cycle']['targetVersion'] = '3.3.1'
        for requirement in self.contract['acceptance']['admission']['acceptanceRequirements']:
            requirement.pop('outcomeObligations')
        frozen = copy.deepcopy(self.contract)
        identity = admission._definition(self.contract, self.case)
        report = self.assess()
        self.assertEqual(report['errors'], [])
        self.assertTrue(report['acceptanceRequirements']['A05']['complete'])
        self.assertNotIn('missingObligations', report['acceptanceRequirements']['A05'])
        self.assertEqual(self.contract, frozen)
        self.assertEqual(admission._definition(self.contract, self.case), identity)

    def test_obligation_order_is_not_a_changed_meaning_but_membership_is(self):
        original = admission._reuse_definition(self.contract, self.case)
        self.requirement['outcomeObligations'].reverse()
        self.assertEqual(admission._reuse_definition(self.contract, self.case), original)
        self.requirement['outcomeObligations'].pop()
        self.assertNotEqual(admission._reuse_definition(self.contract, self.case), original)

    def test_required_mapping_uses_valid_semver_release_line(self):
        for version, expected in (('3.3.1', False), ('3.3.2-dev.1', True), ('3.3.2+codex.20261021010101', True),
                                  ('3.3.10', True), ('3.10.0', True), ('4.0.0', True), ('3.3.02', False)):
            with self.subTest(version=version):
                self.contract['cycle']['targetVersion'] = version
                self.assertEqual(admission._outcome_mapping_required(self.contract), expected)

    def test_json_pointer_selects_exact_true_leaf_with_rfc6901_escaping(self):
        expected = {'effect': {'path/with~escape': [True], 'parent': {'leaf': True}}}
        self.assertIs(admission._outcome_value(expected, '/effect/path~1with~0escape/0'), True)
        self.assertIs(admission._outcome_value(expected, '/effect/path~1with~0escape/00'), admission._MISSING_OUTCOME)
        self.assertIs(admission._outcome_value(expected, '/effect/absent'), admission._MISSING_OUTCOME)
        self.assertIsInstance(admission._outcome_value(expected, '/effect/parent'), dict)


if __name__ == '__main__':
    unittest.main()
