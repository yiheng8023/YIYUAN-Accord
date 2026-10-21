"""Offline deadline regressions; no filesystem fixtures, processes or models."""
import argparse
from contextlib import ExitStack, contextmanager
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from scripts import observe_codex_entry as entry
from scripts import observe_codex_lifecycle as lifecycle


class ObserverDeadlineTests(unittest.TestCase):
    @contextmanager
    def entry_run(self, *, preflight_time=None, inspection_time=None, dispatch_time=None,
                  work_seconds=1, turn_seconds=1):
        now, launches, saved = [0.0], [], {}
        control_calls = [0]
        manifest = {'evidence': 'C:/synthetic-evidence', 'workspace': 'C:/synthetic-work',
            'entryProtocol': 'exec-resume', 'hookMode': 'checkpoint-wrapper',
            'promptSha256s': ['sha'], 'initialCommand': ['synthetic-no-process'], 'inputs': {},
            'timeoutSeconds': work_seconds, 'turnTimeoutSeconds': turn_seconds, 'recoveryTimeoutSeconds': 1,
            'prompts': ['p'], 'case': 'C:/synthetic-case.json', 'episode': 'synthetic-episode',
            'limits': {'usageCaps': {}}}
        fixture = {'inputs': {}, 'stages': [{'id': 's'}]}
        observer = Mock()
        observer.snapshot.return_value = {}
        def inspect(*args, **kwargs):
            if inspection_time is not None:
                now[0] = inspection_time
            return {'files': {}, 'decision': 'pass', 'stage': 's'}
        observer.inspect_stage.side_effect = inspect
        process = Mock(pid=123, returncode=0)
        process.poll.return_value = 0
        def control(*args, **kwargs):
            control_calls[0] += 1
            if preflight_time is not None:
                now[0] = preflight_time
            if dispatch_time is not None and control_calls[0] == 2:
                now[0] = dispatch_time
        def launch(*args, **kwargs):
            launches.append(now[0])
            return process
        def save(path, value):
            saved[Path(path).name] = copy.deepcopy(value)
        native = {'valid': True, 'threadId': 'synthetic-thread', 'terminal': 'completed',
                  'usageObservation': {'decision': 'within-observed-limits'}}
        with ExitStack() as stack:
            for name, value in [('coordination_observer', observer), ('load_manifest', manifest),
                    ('digest', 'sha'), ('build_command', ['synthetic-no-process']),
                    ('_resource_controller', 'windows-job-object'),
                    ('shared_config_snapshot', {'state': 'observed', 'sha256': 'sha'}),
                    ('read_regular', json.dumps(fixture).encode()),
                    ('_close_processes', ({'activeProcesses': 0}, {'activeProcesses': 0}, False, None)),
                    ('persistent_cli_turn_receipt', native)]:
                stack.enter_context(patch.object(entry, name, return_value=value))
            stack.enter_context(patch.object(entry, '_verify_prepared_sources'))
            stack.enter_context(patch.object(entry, '_verify_control_stage', side_effect=control))
            stack.enter_context(patch.object(entry, '_new_controller'))
            stack.enter_context(patch.object(entry, 'save', side_effect=save))
            stack.enter_context(patch.object(entry.subprocess, 'Popen', side_effect=launch))
            stack.enter_context(patch.object(entry.time, 'monotonic', side_effect=lambda: now[0]))
            stack.enter_context(patch.object(Path, 'mkdir'))
            stack.enter_context(patch.object(Path, 'open', lambda path, mode='r', **kw:
                                            io.BytesIO(b'p') if 'b' in mode else io.StringIO()))
            yield argparse.Namespace(evidence=manifest['evidence'], observe_native_goal=False), launches, saved

    def test_public_persistent_preflight_cannot_dispatch_after_work_deadline(self):
        with self.entry_run(preflight_time=2) as (args, launches, saved):
            with self.assertRaises(TimeoutError):
                entry.run_persistent(args)
            self.assertEqual(launches, [])
            self.assertEqual(saved['result.json']['executionFailure']['phase'], 'preflight')
            self.assertFalse(saved['result.json']['caseComplete'])

    def test_stage_turn_deadline_and_last_pre_popen_window_are_both_guarded(self):
        for options in ({'preflight_time': 2, 'work_seconds': 10}, {'dispatch_time': 2}):
            with self.subTest(options=options), self.entry_run(**options) as (args, launches, saved):
                with self.assertRaises(TimeoutError):
                    entry.run_persistent(args)
                self.assertEqual(launches, [])
                self.assertEqual(saved['result.json']['executionFailure']['phase'], 'preflight')

    def test_public_persistent_observation_after_deadline_cannot_complete_case(self):
        with self.entry_run(inspection_time=2) as (args, launches, saved):
            result = entry.run_persistent(args)
            self.assertEqual(launches, [0])
            self.assertFalse(result['caseComplete'])
            self.assertEqual(result['stages'][0]['fileObservation']['decision'], 'pass')

    def test_public_persistent_legal_clock_preserves_success(self):
        with self.entry_run() as (args, launches, saved):
            result = entry.run_persistent(args)
            self.assertEqual(launches, [0])
            self.assertTrue(result['caseComplete'])

    @contextmanager
    def lifecycle_io(self, *, clock=2, identity_delay=False, hash_delay=False, launch_log_delay=False):
        now, launches = [clock], []
        manifest = {'evidence': 'C:/synthetic-evidence', 'codex': 'synthetic-codex', 'node': 'synthetic-node',
            'ownedRoots': {'workspace': 'C:/synthetic-work'}, 'resourceController': 'windows-job-object',
            'limits': {'requestSeconds': 5, 'recoverySeconds': 1},
            'binaryHashes': {'node': 'sha'}, 'packageHashes': {'runtime/task-checkpoint.cjs': 'sha'}}
        process = Mock(pid=123, returncode=0, stdin=io.BytesIO(), stdout=io.BytesIO())
        process.poll.return_value = 0
        job = Mock()
        job.sample.return_value = {'activeProcesses': 0}
        def identity(*args, **kwargs):
            if identity_delay:
                now[0] = 2
            return {'path': 'synthetic-no-process'}
        def digest(*args, **kwargs):
            if hash_delay:
                now[0] = 2
            return 'sha'
        def launch(*args, **kwargs):
            launches.append(now[0])
            return process
        def log_launch(*args, **kwargs):
            if launch_log_delay:
                now[0] = 2
        with ExitStack() as stack:
            for name, options in [('_codex_identity', {'side_effect': identity}),
                    ('_record_host_launch', {'side_effect': log_launch}), ('_replacement_binding', {'return_value': None}),
                    ('_new_controller', {'return_value': job}), ('save', {}),
                    ('digest', {'side_effect': digest}), ('read_regular', {'return_value': b'{}'}),
                    ('_wait_job', {'return_value': {'activeProcesses': 0}})]:
                stack.enter_context(patch.object(lifecycle, name, **options))
            stack.enter_context(patch.object(lifecycle.subprocess, 'Popen', side_effect=launch))
            stack.enter_context(patch.object(lifecycle.time, 'monotonic', side_effect=lambda: now[0]))
            stack.enter_context(patch.object(lifecycle.threading, 'Thread'))
            stack.enter_context(patch.object(Path, 'mkdir'))
            stack.enter_context(patch.object(Path, 'write_bytes'))
            stack.enter_context(patch.object(Path, 'iterdir', return_value=iter([])))
            stack.enter_context(patch.object(Path, 'exists', return_value=True))
            stack.enter_context(patch.object(Path, 'open', lambda path, mode='r', **kw:
                                            io.BytesIO() if 'b' in mode else io.StringIO()))
            yield manifest, launches, job

    def test_default_lifecycle_cli_rejects_expired_work_before_dispatch(self):
        for options in ({'clock': 2}, {'clock': 0, 'identity_delay': True}):
            with self.subTest(options=options), self.lifecycle_io(**options) as (manifest, launches, job):
                with self.assertRaises(TimeoutError):
                    lifecycle._run_cli(manifest, 'query', ['plugin', 'list'], {}, 1)
                self.assertEqual(launches, [])

    def test_app_server_rejects_expired_work_before_process_creation(self):
        for options in ({'clock': 2}, {'clock': 0, 'launch_log_delay': True}):
            with self.subTest(options=options), self.lifecycle_io(**options) as (manifest, launches, job):
                with self.assertRaises(TimeoutError):
                    lifecycle._App(manifest, 'query', ['synthetic-no-process'], {}, 1)
                self.assertEqual(launches, [])

    def test_inventory_query_inherits_the_remaining_owner_work_deadline(self):
        record = {'exitCode': 0, 'forced': False, 'failure': None}
        with patch.object(Path, 'mkdir'), patch.object(Path, 'exists', return_value=False), \
                patch.object(entry, 'shared_config_snapshot', return_value={'state': 'observed', 'sha256': 'sha'}), \
                patch.object(entry, 'save'), patch.object(lifecycle, '_run_cli', return_value=(record, {})) as command, \
                patch.object(entry.time, 'monotonic', return_value=0):
            entry._native_inventory('codex', 'market', 'work', 'evidence', 'before', work_deadline=1)
        self.assertEqual(command.call_args.args[4], 1)

    def test_turn_wait_does_not_accept_a_terminal_after_its_deadline(self):
        app = lifecycle._App.__new__(lifecycle._App)
        app.work_deadline, app.request_timeout, app.events = 1, 1, []
        now = [0]
        def late(deadline):
            now[0] = 2
            return {'method': 'turn/completed', 'params': {'threadId': 'thread',
                    'turn': {'id': 'turn', 'status': 'completed'}}}
        app._receive = late
        with patch.object(lifecycle.time, 'monotonic', side_effect=lambda: now[0]):
            with self.assertRaises(TimeoutError):
                app.wait_turn('thread', 'turn')
        self.assertEqual(len(app.events), 1)  # Preserve the late effect receipt.

    def test_helper_hashing_cannot_reopen_expired_work_before_popen(self):
        with self.lifecycle_io(clock=0, hash_delay=True) as (manifest, launches, job):
            with self.assertRaises(TimeoutError):
                lifecycle._helper(manifest, Path('C:/synthetic-installed'), {}, 1, 'thread', 'status')
            self.assertEqual(launches, [])

    def test_lifecycle_legal_clock_preserves_command_and_helper_success(self):
        with self.lifecycle_io(clock=0) as (manifest, launches, job):
            record, result = lifecycle._run_cli(manifest, 'query', ['plugin', 'list'], {}, 10)
            self.assertEqual(record['exitCode'], 0)
            self.assertEqual(result, {})
            self.assertEqual(launches, [0])
        with self.lifecycle_io(clock=0) as (manifest, launches, job):
            self.assertEqual(lifecycle._helper(manifest, Path('C:/synthetic-installed'), {}, 10, 'thread', 'status'), {})
            self.assertEqual(launches, [0])


if __name__ == '__main__':
    unittest.main()
