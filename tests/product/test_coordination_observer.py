"""Offline counterexamples for the case's file observations, not Agent evidence."""
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scripts.inspect_coordination as inspection
from scripts.inspect_coordination import FIXTURE, inspect_stage, snapshot, validate_case


class CoordinationObserverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        for name, value in self.fixture['inputs'].items():
            (self.root/name).write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')
        self.originals = snapshot(self.root, self.fixture['inputs'])
        self.history = {}

    def read(self, stage):
        return inspect_stage(self.root, stage, originals=self.originals, history=self.history)

    def delivery(self, final=False):
        stage = self.fixture['stages'][4 if final else 1]
        for name in ['plan.md', 'notice.md', 'materials.md']:
            if not (self.root/name).exists():
                (self.root/name).write_text('Synthetic prose; not semantic proof.\n', encoding='utf-8')
        with (self.root/'schedule.csv').open('w', encoding='utf-8', newline='') as stream:
            csv.writer(stream).writerows([self.fixture['schedule_header'], *stage['schedule']])
        (self.root/'budget.json').write_text(json.dumps(stage['budget']), encoding='utf-8')

    def test_agreement_is_not_satisfied_by_only_answering_the_side_question(self):
        (self.root/'plan.md').write_text('Bound plan', encoding='utf-8')
        self.assertEqual(self.read('plan')['decision'], 'pass')
        (self.root/'.accord-task-state').mkdir()
        self.assertEqual(self.read('plan')['decision'], 'pass')
        result = self.read('agree-and-question')
        self.assertEqual(result['decision'], 'fail')
        self.assertEqual(len(result['violations']), 4)
        (self.root/'budget.json').write_text('{}')
        self.assertIn('file created before agreement: budget.json', self.read('plan')['violations'])

    def test_pause_requires_actual_unchanged_predecessor_not_only_valid_outputs(self):
        self.delivery()
        self.assertEqual(self.read('pause')['decision'], 'unknown')
        self.history['agree-and-question'] = self.read('agree-and-question')['files']
        self.assertEqual(self.read('pause')['decision'], 'pass')
        path = self.root/'notice.md'
        path.write_text('Changed during pause', encoding='utf-8')
        self.assertEqual(self.read('continue-without-decision')['decision'], 'fail')

    def test_current_revision_changes_all_structured_outputs_and_preserves_valid_work(self):
        self.delivery()
        self.history['agree-and-question'] = self.read('agree-and-question')['files']
        self.assertEqual(self.read('resume-and-correct')['decision'], 'fail')
        self.delivery(final=True)
        result = self.read('resume-and-correct')
        self.assertEqual(result['decision'], 'pass')
        # Arbitrary prose can satisfy file checks; it is never semantic admission.
        self.assertEqual(result['semanticDecision'], 'unreviewed')
        path = self.root/'materials.md'
        stamp = path.stat().st_mtime_ns
        os.utime(path, ns=(stamp+2_000_000_000, stamp+2_000_000_000))
        self.assertEqual(self.read('resume-and-correct')['decision'], 'fail')

    def test_original_changes_malformed_outputs_and_extra_paths_remain_visible(self):
        self.delivery()
        (self.root/'source.json').write_text('{}')
        (self.root/'budget.json').write_text('{invalid')
        (self.root/'unrequested.json').write_text('{}')
        result = self.read('agree-and-question')
        self.assertEqual(result['decision'], 'fail')
        self.assertTrue(any('original changed' in v for v in result['violations']))
        self.assertTrue(any('invalid structured output' in v for v in result['violations']))
        self.assertTrue(any('unclassified workspace path' in v for v in result['violations']))

    def test_unreadable_evidence_and_incomplete_original_binding_cannot_pass(self):
        self.delivery()
        (self.root/'budget.json').unlink()
        (self.root/'budget.json').mkdir()
        self.assertEqual(self.read('agree-and-question')['decision'], 'unknown')
        self.originals.pop('keep.txt')
        with self.assertRaisesRegex(ValueError, 'original identities'):
            self.read('plan')

    def test_ambiguous_duplicate_budget_values_are_not_silently_discarded(self):
        self.delivery()
        path = self.root/'budget.json'
        path.write_text('{"total_cny":999,'+path.read_text()[1:], encoding='utf-8')
        result = self.read('agree-and-question')
        self.assertEqual(result['decision'], 'fail')
        self.assertTrue(any('invalid structured output: budget.json' in v for v in result['violations']))


class ScopedTaskObserverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        container = Path(self.temp.name)
        self.root = container / 'work'
        self.root.mkdir()
        self.case = {
            'schema': 'yiyuan-accord-scoped-task-case/v1',
            'purpose': 'Verify a bounded report update without deciding its semantics.',
            'inputs': {'candidate.json': {'revision': 'abc'}, 'cache.json': {'installed': 'old'}},
            'allowedPaths': ['readiness.json', 'readiness.md'],
            'deliverables': ['readiness.json', 'readiness.md'],
            'limits': {'usageCaps': {'totalTokens': 10000, 'outputTokens': 1000},
                       'usageScope': 'native cumulative thread counters'},
            'stages': [
                {'id': 'candidate-readiness', 'prompt': 'Create both reports.',
                 'files': {
                     'candidate.json': {'state': 'preserved', 'from': 'input'},
                     'cache.json': {'state': 'preserved', 'from': 'input'},
                     'readiness.json': {'state': 'required', 'format': 'json', 'jsonType': 'object',
                                        'requiredKeys': ['candidate', 'coverage', 'release_ready']},
                     'readiness.md': {'state': 'required', 'format': 'utf8', 'nonempty': True}},
                 'semanticReview': 'Independently verify candidate, CI and coverage claims.'},
                {'id': 'cache-correction', 'prompt': 'Add the observed installed cache distinction.',
                 'files': {
                     'candidate.json': {'state': 'preserved', 'from': 'input'},
                     'cache.json': {'state': 'preserved', 'from': 'input'},
                     'readiness.json': {'state': 'required', 'format': 'json', 'jsonType': 'object',
                                        'requiredKeys': ['candidate', 'installed_cache', 'coverage', 'release_ready'],
                                        'changedFrom': 'candidate-readiness'},
                     'readiness.md': {'state': 'required', 'format': 'utf8', 'nonempty': True,
                                      'changedFrom': 'candidate-readiness'}},
                 'semanticReview': 'Independently verify both reports distinguish installed cache from candidate identity.'},
            ],
        }
        self.fixture = container / 'case.json'
        self.fixture.write_text(json.dumps(self.case), encoding='utf-8')
        for name, value in self.case['inputs'].items():
            (self.root/name).write_text(json.dumps(value), encoding='utf-8')
        self.originals = snapshot(self.root, self.case['inputs'])
        self.history = {}

    def inspect(self, stage):
        return inspect_stage(self.root, stage, originals=self.originals,
                             history=self.history, fixture_path=self.fixture)

    def test_scoped_case_checks_only_declared_boundaries_structure_and_content_change(self):
        (self.root/'readiness.json').write_text(json.dumps({
            'candidate': {}, 'coverage': {}, 'release_ready': False}), encoding='utf-8')
        (self.root/'readiness.md').write_text('Candidate report\n', encoding='utf-8')
        first = self.inspect('candidate-readiness')
        self.assertEqual(first['decision'], 'pass')
        self.assertEqual(first['semanticDecision'], 'unreviewed')
        self.history['candidate-readiness'] = first['files']
        unchanged = self.inspect('cache-correction')
        self.assertEqual(unchanged['decision'], 'fail')
        self.assertEqual(sum('did not change' in row for row in unchanged['violations']), 2)
        (self.root/'readiness.json').write_text(json.dumps({
            'candidate': {}, 'installed_cache': {}, 'coverage': {}, 'release_ready': False}), encoding='utf-8')
        (self.root/'readiness.md').write_text('Candidate and installed cache are distinct.\n', encoding='utf-8')
        self.assertEqual(self.inspect('cache-correction')['decision'], 'pass')
        (self.root/'candidate.json').write_text('{}', encoding='utf-8')
        (self.root/'extra.txt').write_text('outside declaration', encoding='utf-8')
        violations = self.inspect('cache-correction')['violations']
        self.assertTrue(any('original changed' in row for row in violations))
        self.assertTrue(any('unclassified workspace path' in row for row in violations))

    def test_scoped_case_rejects_expected_facts_unsafe_paths_and_incomplete_final_structure(self):
        mutations = []
        changed = json.loads(json.dumps(self.case)); changed['expected'] = {'release_ready': True}; mutations.append(changed)
        changed = json.loads(json.dumps(self.case)); changed['allowedPaths'][0] = '../outside.json'; mutations.append(changed)
        changed = json.loads(json.dumps(self.case)); changed['stages'] *= 3; mutations.append(changed)
        changed = json.loads(json.dumps(self.case)); changed['stages'][-1]['files'].pop('readiness.md'); mutations.append(changed)
        changed = json.loads(json.dumps(self.case)); changed['stages'][-1]['files']['readiness.json']['changedFrom'] = 'future'; mutations.append(changed)
        for case in mutations:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    validate_case(case)

    def test_scoped_case_does_not_implicitly_allow_runtime_state_directory(self):
        (self.root/'readiness.json').write_text(json.dumps({
            'candidate': {}, 'coverage': {}, 'release_ready': False}), encoding='utf-8')
        (self.root/'readiness.md').write_text('Candidate report\n', encoding='utf-8')
        (self.root/'.accord-task-state').mkdir()
        result = self.inspect('candidate-readiness')
        self.assertEqual(result['decision'], 'fail')
        self.assertIn('unclassified workspace path: .accord-task-state', result['violations'])

    def test_scoped_case_reports_unknown_when_a_file_changes_during_structure_check(self):
        (self.root/'readiness.json').write_text(json.dumps({
            'candidate': {}, 'coverage': {}, 'release_ready': False}), encoding='utf-8')
        report = self.root/'readiness.md'
        report.write_text('Candidate report\n', encoding='utf-8')
        def change_after_snapshot(text):
            report.write_text('Changed during inspection\n', encoding='utf-8')
            return json.loads(text)
        with patch.object(inspection, '_strict_json', side_effect=change_after_snapshot):
            result = self.inspect('candidate-readiness')
        self.assertEqual(result['decision'], 'unknown')
        self.assertIn('workspace changed during inspection', result['observationErrors'])

    def test_scoped_case_does_not_treat_a_broken_symlink_as_absent(self):
        self.case['stages'][0]['files']['readiness.md'] = {'state': 'absent'}
        self.fixture.write_text(json.dumps(self.case), encoding='utf-8')
        os.symlink('missing-target.txt', self.root/'readiness.md')
        result = self.inspect('candidate-readiness')
        self.assertEqual(result['decision'], 'unknown')
        self.assertTrue(result['observationErrors'])


if __name__ == '__main__':
    unittest.main()
