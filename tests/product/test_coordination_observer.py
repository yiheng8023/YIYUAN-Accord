"""Offline counterexamples for the case's file observations, not Agent evidence."""
import csv
import json
import os
from pathlib import Path
import tempfile
import unittest

from scripts.inspect_coordination import FIXTURE, inspect_stage, snapshot


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


if __name__ == '__main__':
    unittest.main()
