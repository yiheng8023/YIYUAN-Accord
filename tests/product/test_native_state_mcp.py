"""Bounded MCP task-state entry; native host metadata delivery is checked separately."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import queue
from datetime import datetime, timezone
import unittest
from unittest import mock
import time

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'runtime/native-state-mcp.cjs'
CHECKPOINT = ROOT / 'runtime/task-checkpoint.cjs'


def native_tool_result(call):
    reply = call.get('result') or {}
    value = reply.get('structuredContent')
    if value is None:
        content = [x.get('text') for x in reply.get('content', []) if x.get('type') == 'text']
        value = json.loads(content[0]) if len(content) == 1 else None
    return reply, value


def native_manage_disposition(call, *, preapproved):
    # App Server maps MCP isError to item.status and omits isError from result.
    # Tool rejection retains result; host/transport denial instead has error.
    if preapproved:
        _, value = native_tool_result(call)
        if (call.get('status') != 'failed' or call.get('error') is not None
                or not isinstance(value, dict)
                or value.get('schema') != 'yiyuan-accord-native-state-mutation/v1'
                or value.get('state') != 'unavailable'
                or value.get('reason') != 'native-user-input-receipt-missing'
                or value.get('effect') != 'unknown-check-post-state'):
            raise RuntimeError('manage tool did not preserve the expected adapter rejection')
        return 'expected-adapter-rejection-not-business-success'
    if (call.get('result') is not None or call.get('status') != 'failed'
            or (call.get('error') or {}).get('message')
            != 'MCP tool call requires approval, but approval policy is never'):
        raise RuntimeError('native approval boundary differs from the fixed case')
    return 'expected-host-denial-no-adapter-call'


class NativeMcpEventTests(unittest.TestCase):
    def test_host_denial_and_normalized_tool_rejection_are_distinct(self):
        denied = {'status': 'failed', 'result': None, 'error': {
            'message': 'MCP tool call requires approval, but approval policy is never'}}
        rejected = {'status': 'failed', 'error': None, 'result': {'structuredContent': {
            'schema': 'yiyuan-accord-native-state-mutation/v1', 'state': 'unavailable',
            'reason': 'native-user-input-receipt-missing', 'effect': 'unknown-check-post-state'}}}
        self.assertEqual(native_manage_disposition(denied, preapproved=False),
                         'expected-host-denial-no-adapter-call')
        self.assertEqual(native_manage_disposition(rejected, preapproved=True),
                         'expected-adapter-rejection-not-business-success')
        for call, preapproved in [(denied, True), (rejected, False),
                ({**rejected, 'status': 'completed'}, True),
                ({**rejected, 'error': {'message': 'transport failed'}}, True),
                ({**rejected, 'result': None}, True),
                ({**denied, 'error': {'message': 'different host failure'}}, False)]:
            with self.subTest(call=call, preapproved=preapproved), self.assertRaises(RuntimeError):
                native_manage_disposition(call, preapproved=preapproved)


class NativeIntegrationFinalizeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='accord-native-finalize-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.host = mock.Mock()
        self.host.save.side_effect = lambda path, value: path.write_text(
            json.dumps(value), encoding='utf-8')
        self.fixture = mock.Mock()

    def result(self):
        return json.loads((self.root/'result.json').read_text(encoding='utf-8'))

    def test_natural_close_preserves_the_successful_body_result(self):
        record = {'exitCode': 0, 'forced': False,
                  'after': {'processGroupState': 'absent'}}
        app = mock.Mock()
        app.close.return_value = record
        self.host._released.return_value = True
        _finalize_native_integration({'status': 'passed', 'providerRequests': 3},
                                     app, self.fixture, self.root, self.host,
                                     body_failed=False)
        self.fixture.close.assert_called_once_with()
        self.assertEqual(self.result(), {'status': 'passed', 'providerRequests': 3,
                                         'resources': record})

    def test_close_exception_still_closes_fixture_and_saves_resource_receipt(self):
        record = {'exitCode': 0, 'forced': True,
                  'after': {'processGroupState': 'unobservable'}}
        app = mock.Mock(_close_record=record)
        app.close.side_effect = RuntimeError('native app process release unobserved')
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
            _finalize_native_integration({'status': 'passed'}, app, self.fixture,
                                         self.root, self.host, body_failed=False)
        self.fixture.close.assert_called_once_with()
        saved = self.result()
        self.assertEqual(saved['status'], 'failed')
        self.assertEqual(saved['resources'], record)
        self.assertEqual([item['stage'] for item in saved['cleanupFailures']],
                         ['app.close', 'resource.release'])

    def test_forced_close_record_cannot_be_saved_as_passed(self):
        app = mock.Mock()
        app.close.return_value = {'exitCode': 0, 'forced': True, 'after': {'released': True}}
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
            _finalize_native_integration({'status': 'passed'}, app, self.fixture,
                                         self.root, self.host, body_failed=False)
        self.fixture.close.assert_called_once_with()
        self.assertEqual(self.result()['status'], 'failed')
        self.assertEqual(self.result()['cleanupFailures'][0]['stage'], 'resource.release')
        self.host._released.assert_not_called()

    def test_unobserved_release_cannot_be_saved_as_passed(self):
        app = mock.Mock()
        after = {'processGroupState': 'unobservable'}
        app.close.return_value = {'exitCode': 0, 'forced': False, 'after': after}
        self.host._released.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
            _finalize_native_integration({'status': 'passed'}, app, self.fixture,
                                         self.root, self.host, body_failed=False)
        self.host._released.assert_called_once_with(after)
        self.assertEqual(self.result()['status'], 'failed')
        self.assertEqual(self.result()['resources'], app.close.return_value)

    def test_body_failure_survives_both_close_failures(self):
        app = mock.Mock(_close_record={'exitCode': 0, 'forced': True,
                                      'after': {'processGroupState': 'unobservable'}})
        app.close.side_effect = RuntimeError('app close failed')
        self.fixture.close.side_effect = OSError('fixture close failed')
        result = {'status': 'pending'}
        with self.assertRaisesRegex(ValueError, 'body failed'):
            try:
                raise ValueError('body failed')
            except BaseException as error:
                result.update(status='failed', failure=type(error).__name__, reason=str(error))
                raise
            finally:
                _finalize_native_integration(result, app, self.fixture,
                                             self.root, self.host, body_failed=True)
        self.fixture.close.assert_called_once_with()
        saved = self.result()
        self.assertEqual((saved['failure'], saved['reason']), ('ValueError', 'body failed'))
        self.assertEqual([item['stage'] for item in saved['cleanupFailures']],
                         ['app.close', 'fixture.close', 'resource.release'])
        self.assertEqual(saved['resources'], app._close_record)


class NativeStateMcpTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='accord-native-state-mcp-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.work = self.root / 'work'
        self.work.mkdir()
        self.state = self.root / 'state'
        self.env = {**os.environ, 'YIYUAN_ACCORD_TASK_STATE_DIR': str(self.state)}
        self.node = shutil.which('node')
        self.assertIsNotNone(self.node)
        self.params = {'name': 'inspect_task_state', 'arguments': {'cwd': str(self.work)},
            '_meta': {'callId': 'native-call-1', 'x-codex-turn-metadata': {
                'thread_id': 'current-thread', 'session_id': 'current-thread', 'turn_id': 'current-turn',
                'model': 'observed-model', 'codex_version': 'observed-version'}}}

    def helper(self, operation, *, session='current-thread', hook=None):
        body = {'session_id': session, 'cwd': str(self.work), **operation}
        p = subprocess.run([self.node, str(CHECKPOINT), *(['--hook', hook] if hook else [])],
            input=json.dumps(body), capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def inspect(self, params=None, *, operation='inspectNativeState'):
        code = "const m=require(process.argv[1]);let s='';process.stdin.setEncoding('utf8');process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(m[process.argv[2]](JSON.parse(s)))));"
        p = subprocess.run([self.node, '-e', code, str(BRIDGE), operation], input=json.dumps(params or self.params),
            capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def read_input(self, **arguments):
        params = {**self.params, 'name': 'read_task_input',
                  'arguments': {**self.params['arguments'], **arguments}}
        return self.inspect(params, operation='readTaskInput')

    def manage(self, **arguments):
        params = {**self.params, 'name': 'manage_task_state',
                  'arguments': {'cwd': str(self.work), **arguments}}
        return self.inspect(params, operation='manageTaskState')

    def receive_current_input(self, prompt='Continue this task.'):
        turn = self.params['_meta']['x-codex-turn-metadata']['turn_id']
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt, 'turn_id': turn},
                    hook='UserPromptSubmit')
        return self.helper({'op': 'status'})

    def test_captured_input_pages_preserve_unicode_hashes_and_read_only_state(self):
        expected = ['甲🌱乙\n"quoted"', '', 'Preserve the pause.']
        for prompt in expected:
            self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt}, hook='UserPromptSubmit')
        before = self.files()
        cursor = {}
        restored = {i: '' for i in range(len(expected))}
        epoch = self.helper({'op': 'status'})['epoch']
        while cursor is not None:
            result = self.read_input(maxChars=2, **cursor)
            self.assertFalse(result['isError'], result)
            self.assertEqual(result['value']['source']['threadId'], 'current-thread')
            page = result['value']['input']
            self.assertEqual(page['receiptEpoch'], epoch)
            self.assertEqual(page['coverage'], 'captured-hook-inputs-only')
            for row in page['entries']:
                restored[row['index']] += row['text']
                self.assertEqual(row['promptSha256'], hashlib.sha256(expected[row['index']].encode()).hexdigest())
            if page['next']:
                self.assertEqual(page['next']['expectedReceiptEpoch'], epoch)
                self.assertNotEqual(page['next'], cursor)
            cursor = page['next']
        self.assertEqual(list(restored.values()), expected)
        self.assertEqual(self.files(), before)

    def test_captured_input_cursor_rejects_later_receipt_without_returning_text(self):
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Initial source.'}, hook='UserPromptSubmit')
        cursor = self.read_input(maxChars=2)['value']['input']['next']
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Later correction.'}, hook='UserPromptSubmit')
        before = self.files()
        for unbound in ({'offset': cursor['offset']}, {'index': 1}, {'index': 0, 'offset': 1}):
            missing_basis = self.read_input(**unbound)
            self.assertTrue(missing_basis['isError'])
            self.assertEqual(missing_basis['value']['reason'], 'captured-input-basis-required')
            self.assertNotIn('input', missing_basis['value'])
        rejected = self.read_input(**cursor)
        self.assertTrue(rejected['isError'])
        self.assertEqual(rejected['value']['reason'], 'captured-input-basis-changed')
        self.assertNotIn('input', rejected['value'])
        self.assertEqual(self.files(), before)

    def test_captured_input_rejects_identity_and_operation_overrides_or_bad_pages(self):
        for key, value in [('session_id', 'foreign'), ('op', 'retire'), ('recovery_epoch', 'invented'),
                           ('text', 'invented'), ('_meta', self.params['_meta']), ('index', -1),
                           ('index', 2**53), ('offset', True), ('offset', '0'), ('maxChars', 0),
                           ('maxChars', 16001), ('expectedReceiptEpoch', '')]:
            with self.subTest(argument=key, value=value):
                self.assertTrue(self.read_input(**{key: value})['isError'])
        self.assertTrue(self.read_input(cwd='.')['isError'])
        self.params.pop('_meta')
        self.assertEqual(self.read_input()['value']['reason'], 'native-call-metadata-unavailable')
        self.assertFalse(self.state.exists())

    def test_captured_input_never_reads_ancestor_or_invents_missing_text(self):
        missing = self.read_input()
        self.assertTrue(missing['isError'])
        self.assertFalse(self.state.exists())
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'ANCESTOR_PRIVATE'},
                    session='ancestor-root', hook='UserPromptSubmit')
        self.params['_meta']['x-codex-turn-metadata']['session_id'] = 'ancestor-root'
        before = self.files()
        result = self.read_input()
        self.assertEqual(result['value']['reason'], 'shared-session-scope-requires-reconciliation')
        self.assertNotIn('ANCESTOR_PRIVATE', json.dumps(result))
        self.assertEqual(self.files(), before)
        self.params['_meta']['x-codex-turn-metadata']['thread_id'] = 'ancestor-root'
        receipt = next(self.state.glob('*.input.json'))
        data = json.loads(receipt.read_text(encoding='utf-8'))
        del data['nativeInputs']
        receipt.write_text(json.dumps(data), encoding='utf-8')
        before = self.files()
        page = self.read_input()['value']['input']
        self.assertFalse(page['available'])
        self.assertEqual(page['entries'], [])
        self.assertEqual(self.files(), before)

    def test_captured_input_preserves_locks_quarantine_and_bounded_results(self):
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Captured before interruption.'}, hook='UserPromptSubmit')
        receipt = next(self.state.glob('*.input.json'))
        original = receipt.read_bytes()
        lock = receipt.with_name(receipt.name + '.lock')
        lock.write_text(json.dumps({'pid': os.getpid()}), encoding='utf-8')
        before = self.files()
        self.assertEqual(self.read_input()['value']['reason'], 'input-read-busy')
        self.assertEqual(self.files(), before)
        lock.unlink()
        failure = receipt.with_name(receipt.name.replace('.input.json', '.input-failure.json'))
        failure.write_text(json.dumps({'schema': 1, 'generation': 'uncaptured-input'}), encoding='utf-8')
        before = self.files()
        page = self.read_input()['value']['input']
        self.assertTrue(page['inputStatus']['needsNativeReplay'])
        self.assertEqual(page['entries'][0]['text'], 'Captured before interruption.')
        self.assertEqual(self.files(), before)
        # Even valid captured text cannot cause an unbounded response via corrupt metadata.
        data = json.loads(original)
        data['nativeInputs'][0]['epoch'] = 'x' * (128*1024)
        receipt.write_text(json.dumps(data), encoding='utf-8')
        before = self.files()
        self.assertEqual(self.read_input()['value']['reason'], 'bounded-input-result-exceeded')
        self.assertEqual(self.files(), before)

    def test_captured_input_rejects_concurrent_receipt_change(self):
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Protected recorded input.'}, hook='UserPromptSubmit')
        receipt = next(self.state.glob('*.input.json'))
        params = {**self.params, 'name': 'read_task_input'}
        script = ("const fs=require('node:fs'),m=require(process.argv[1]),read=fs.readFileSync;let n=0;"
                  "fs.readFileSync=(p,...a)=>{let b=read(p,...a);if(String(p)===process.argv[2]&&++n===2){"
                  "const v=JSON.parse(b);v.epoch='changed';b=Buffer.from(JSON.stringify(v));}return b;};"
                  "process.stdout.write(JSON.stringify(m.readTaskInput(JSON.parse(read(0,'utf8')))));" )
        before = self.files()
        p = subprocess.run([self.node, '-e', script, str(BRIDGE), str(receipt)], input=json.dumps(params),
                           capture_output=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['value']['reason'], 'input-changed-during-read')
        self.assertEqual(self.files(), before)

    def test_manage_bind_pause_inheritance_explicit_resume_and_verified_retirement(self):
        source = self.work / 'source.txt'
        output = self.work / 'report.txt'
        source.write_text('protected input', encoding='utf-8')
        status = self.receive_current_input('Create and verify the report.')
        contract = {'result': 'Deliver the verified report', 'inputs': ['source.txt'],
                    'outputs': [{'path': 'report.txt'}], 'nextAction': 'Create and verify report.txt',
                    'canContinue': True}
        bound = self.manage(action='bind', epoch=status['epoch'], expectedRevision=status['revision'],
                            **contract)
        self.assertFalse(bound['isError'], bound)
        self.assertEqual(bound['value']['observation']['mode'], 'active')
        self.assertEqual(bound['value']['observation']['inspection']['status'], 'incomplete')
        self.assertFalse(output.exists())

        current = self.receive_current_input('Pause this task and preserve its unfinished state.')
        paused = self.manage(action='pause', epoch=current['epoch'], expectedRevision=current['revision'],
                             reason='The user explicitly paused this task.')
        self.assertEqual(paused['value']['observation']['mode'], 'paused')
        current = self.helper({'op': 'status'})
        inherited = self.manage(action='bind', epoch=current['epoch'], expectedRevision=current['revision'],
                                **contract)
        self.assertFalse(inherited['isError'], inherited)
        self.assertEqual(inherited['value']['observation']['mode'], 'paused')
        snapshot = self.helper({'op': 'status'})
        self.assertEqual(snapshot['mode'], 'paused')
        self.assertEqual(snapshot['checkpoint']['reason'], 'The user explicitly paused this task.')
        blocked = self.manage(action='retire', epoch=snapshot['epoch'], expectedRevision=snapshot['revision'])
        self.assertTrue(blocked['isError'])
        self.assertEqual(blocked['value']['reason'], 'paused-task-cannot-retire')

        resume = self.receive_current_input('Resume this task and complete the report now.')
        resumed = self.manage(action='bind', epoch=resume['epoch'], expectedRevision=resume['revision'],
                              resumeReason='The latest user instruction explicitly resumes the paused work.',
                              **contract)
        self.assertFalse(resumed['isError'], resumed)
        self.assertEqual(resumed['value']['observation']['mode'], 'active')
        output.write_text('verified result', encoding='utf-8')
        current = self.helper({'op': 'status'})
        retired = self.manage(action='retire', epoch=current['epoch'], expectedRevision=current['revision'])
        self.assertFalse(retired['isError'], retired)
        self.assertEqual(retired['value']['observation']['scope'], 'task-checkpoint-files-only')
        self.assertEqual(source.read_text(encoding='utf-8'), 'protected input')
        self.assertEqual(output.read_text(encoding='utf-8'), 'verified result')
        self.assertFalse(any(p.name.endswith(('.state.json', '.input.json')) for p in self.state.iterdir()))

    def test_manage_unresolved_or_unmet_outputs_block_retirement_but_explicit_cancellation_is_bounded(self):
        (self.work / 'source.txt').write_text('protected input', encoding='utf-8')
        status = self.receive_current_input('Investigate the unresolved condition.')
        contract = {'result': 'Deliver report only after the external fact is resolved',
                    'inputs': ['source.txt'], 'outputs': [{'path': 'report.txt'}],
                    'unresolved': ['External acceptance is still unavailable.'],
                    'nextAction': 'Wait for the necessary external fact', 'canContinue': False}
        bound = self.manage(action='bind', epoch=status['epoch'], expectedRevision=status['revision'],
                            **contract)
        self.assertEqual(bound['value']['observation']['inspection']['status'], 'incomplete')
        current = self.helper({'op': 'status'})
        self.assertEqual(self.manage(action='retire', epoch=current['epoch'],
                                     expectedRevision=current['revision'])['value']['reason'],
                         'unmet-output-cannot-retire')
        (self.work / 'report.txt').write_text('local output exists', encoding='utf-8')
        current = self.helper({'op': 'status'})
        unresolved = self.manage(action='retire', epoch=current['epoch'], expectedRevision=current['revision'])
        self.assertTrue(unresolved['isError'])
        self.assertEqual(unresolved['value']['reason'], 'unmet-output-cannot-retire')
        current = self.helper({'op': 'status'})
        self.assertEqual(current['inspection']['status'], 'unresolved')
        cancellation = self.receive_current_input('Cancel this scoped task and retire only its owned state.')
        missing_reason = self.manage(action='retire', epoch=cancellation['epoch'],
                                     expectedRevision=cancellation['revision'], disposition='user-cancelled')
        self.assertTrue(missing_reason['isError'])
        self.assertEqual(missing_reason['value']['reason'], 'invalid-task-state-retirement')
        cancelled = self.manage(action='retire', epoch=cancellation['epoch'],
                                expectedRevision=cancellation['revision'],
                                disposition='user-cancelled',
                                reason='The latest user instruction explicitly cancels this scoped task.')
        self.assertFalse(cancelled['isError'], cancelled)
        self.assertEqual(cancelled['value']['observation']['inspection']['status'], 'unresolved')
        self.assertTrue((self.work / 'source.txt').exists())
        self.assertTrue((self.work / 'report.txt').exists())

    def test_manage_unbound_retirement_removes_only_the_current_receipt(self):
        protected = self.work / 'keep.txt'
        protected.write_text('preserve business data', encoding='utf-8')
        status = self.receive_current_input('No checkpoint is needed; retire only this input receipt.')
        self.assertEqual(status['mode'], 'unbound')
        retired = self.manage(action='retire', epoch=status['epoch'], expectedRevision=0,
                              reason='The current task has no bound checkpoint to preserve.')
        self.assertFalse(retired['isError'], retired)
        self.assertEqual(retired['value']['observation']['scope'], 'unbound-input-receipt-only')
        self.assertEqual(protected.read_text(encoding='utf-8'), 'preserve business data')
        self.assertFalse(any(p.name.endswith(('.state.json', '.input.json')) for p in self.state.iterdir()))

    def test_manage_compacts_oversize_success_without_hiding_the_written_binding(self):
        status = self.receive_current_input('Bind the large local inspection contract.')
        stem = '/'.join(('segment-' + str(i) + '-' + 'p' * 78) for i in range(7))
        outputs = [{'path': f'{stem}/result-{i:03d}.json'} for i in range(100)]
        unresolved = [f'condition-{i:02d}-' + 'u' * 1900 for i in range(32)]
        arguments = {'action': 'bind', 'epoch': status['epoch'],
                     'expectedRevision': status['revision'], 'result': 'Retain the bounded contract',
                     'inputs': [], 'outputs': outputs, 'unresolved': unresolved,
                     'nextAction': 'Resolve conditions and produce the declared outputs',
                     'canContinue': True}
        self.assertLess(len(json.dumps({'cwd': str(self.work), **arguments}).encode()), 128 * 1024)
        result = self.manage(**arguments)
        self.assertFalse(result['isError'], result)
        observation = result['value']['observation']
        self.assertEqual(observation['revision'], 1)
        self.assertEqual(observation['mode'], 'active')
        self.assertEqual(observation['inspection']['status'], 'incomplete')
        self.assertEqual(observation['details'], 'omitted-bounded-result')
        self.assertLess(len(json.dumps(result['value']).encode()), 128 * 1024)
        saved = self.helper({'op': 'status'})
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(saved['checkpoint']['result'], 'Retain the bounded contract')

    def test_manage_rejects_stale_epoch_revision_and_native_turn_without_rebinding(self):
        (self.work / 'source.txt').write_text('protected input', encoding='utf-8')
        first = self.receive_current_input('Create report version one.')
        contract = {'result': 'Deliver report version one', 'inputs': ['source.txt'],
                    'outputs': [{'path': 'report.txt'}], 'nextAction': 'Create report.txt',
                    'canContinue': True}
        bound = self.manage(action='bind', epoch=first['epoch'], expectedRevision=first['revision'],
                            **contract)
        self.assertFalse(bound['isError'], bound)
        current = self.helper({'op': 'status'})
        before = self.files()
        stale_revision = self.manage(action='pause', epoch=current['epoch'], expectedRevision=0,
                                     reason='Attempt using an old revision.')
        self.assertEqual(stale_revision['value']['reason'], 'task-revision-or-input-conflict')
        self.assertEqual(stale_revision['value']['effect'], 'unknown-check-post-state')
        self.assertEqual(self.files(), before)

        second = self.receive_current_input('Create report version two.')
        before = self.files()
        stale_epoch = self.manage(action='pause', epoch=current['epoch'], expectedRevision=current['revision'],
                                  reason='Attempt using an old epoch.')
        self.assertEqual(stale_epoch['value']['reason'], 'task-revision-or-input-conflict')
        self.assertEqual(self.files(), before)
        self.params['_meta']['x-codex-turn-metadata']['turn_id'] = 'different-current-turn'
        turn_conflict = self.manage(action='pause', epoch=second['epoch'], expectedRevision=second['revision'],
                                    reason='Attempt from a different native turn.')
        self.assertEqual(turn_conflict['value']['reason'], 'native-call-turn-conflict')
        self.assertEqual(self.files(), before)

    def test_manage_forwards_only_explicit_input_revision_evidence(self):
        source = self.work / 'source.txt'
        source.write_text('version one', encoding='utf-8')
        status = self.receive_current_input('Create the report from the current source.')
        contract = {'result': 'Deliver report from the current source', 'inputs': ['source.txt'],
                    'outputs': [{'path': 'report.txt'}], 'nextAction': 'Update and verify report.txt',
                    'canContinue': True}
        self.assertFalse(self.manage(action='bind', epoch=status['epoch'],
                                     expectedRevision=status['revision'], **contract)['isError'])
        source.write_text('version two', encoding='utf-8')
        current = self.receive_current_input('Use the inspected version two source and update the report.')
        observed = current['inspection']['inputs'][0]['current']
        before = self.files()
        missing = self.manage(action='bind', epoch=current['epoch'], expectedRevision=current['revision'],
                              revisionReason='The current source changed the affected result.', **contract)
        self.assertEqual(missing['value']['reason'], 'input-revision-required')
        self.assertEqual(self.files(), before)
        accepted = self.manage(action='bind', epoch=current['epoch'], expectedRevision=current['revision'],
            revisionReason='The latest user instruction adopts the inspected source revision.',
            inputRevisions=[{'path': 'source.txt', 'observed': observed,
                             'reason': 'The report must follow the inspected source revision.'}], **contract)
        self.assertFalse(accepted['isError'], accepted)
        saved = self.helper({'op': 'status'})['checkpoint']['inputRevisions'][0]
        self.assertEqual(saved['disposition'], 'refresh')
        self.assertEqual(saved['observed'], observed)

    def test_manage_rejects_descendants_identity_overrides_and_action_foreign_fields(self):
        status = self.receive_current_input('Keep state scoped to this root task.')
        base = {'action': 'pause', 'epoch': status['epoch'], 'expectedRevision': status['revision'],
                'reason': 'Scoped pause.'}
        before = self.files()
        self.params['_meta']['x-codex-turn-metadata']['session_id'] = 'ancestor-root'
        descendant = self.manage(**base)
        self.assertEqual(descendant['value']['reason'], 'shared-session-scope-requires-reconciliation')
        self.assertEqual(self.files(), before)
        self.params['_meta']['x-codex-turn-metadata']['session_id'] = 'current-thread'
        for key, value in [('op', 'recover-lock'), ('session_id', 'foreign'), ('storage', 'foreign'),
                           ('recovery_epoch', 'invented'), ('replay', True), ('turnId', 'invented'),
                           ('nativeTurnId', 'invented'), ('result', 'foreign-to-pause')]:
            with self.subTest(field=key):
                rejected = self.manage(**base, **{key: value})
                self.assertTrue(rejected['isError'])
                self.assertEqual(rejected['value']['reason'], 'invalid-task-state-operation')
                self.assertEqual(rejected['value']['effect'], 'not-requested')
                self.assertEqual(self.files(), before)
        invalid_binding = self.manage(action='bind', epoch=status['epoch'], expectedRevision=status['revision'],
            result='Deliver report', inputs=[], outputs=[{'path': 'report.txt', 'op': 'write'}],
            nextAction='Create report.txt', canContinue=True)
        self.assertEqual(invalid_binding['value']['reason'], 'invalid-task-state-binding')
        self.assertEqual(self.files(), before)

    def files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def native_context(self, age=0):
        session = '11111111-2222-4333-8444-555555555555'
        meta = self.params['_meta']['x-codex-turn-metadata']
        meta.update(thread_id=session, session_id=session)
        self.env['CODEX_HOME'] = str(self.root / 'codex-home')
        transcript = Path(self.env['CODEX_HOME']) / 'sessions/2026/09/20' / (
            'rollout-2026-09-20T00-00-00-' + session + '.jsonl')
        transcript.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromtimestamp(time.time()-age, timezone.utc).isoformat()
        records = [
            {'type': 'session_meta', 'payload': {'id': session, 'cwd': str(self.work), 'cli_version': 'recorded-old-version'}},
            {'type': 'turn_context', 'payload': {'turn_id': meta['turn_id'], 'model': meta['model'], 'cwd': str(self.work)}},
            {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
                'last_token_usage': {'total_tokens': 4000}, 'total_token_usage': {'total_tokens': 500000},
                'model_context_window': 12000}}},
        ]
        transcript.write_text(''.join(json.dumps({'timestamp': stamp, **row})+'\n' for row in records), encoding='utf-8')
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Continue this work.',
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript)},
            session=session, hook='UserPromptSubmit')

    def context_assessment(self, inspection, **changes):
        observation = inspection['context']
        now = int(time.time() * 1000)
        assessment = {
            'epoch': observation['epoch'],
            'expectedRevision': inspection['checkpoint']['snapshot']['revision'],
            'contextGeneration': observation['conditions']['contextGeneration'],
            'observedAtMs': now - 100,
            'validUntilMs': now + 30000,
            'sourceRef': 'inspected-inheritance-and-time-fixture',
            'integrity': 'verified',
            'estimates': {
                'sourceRef': 'bounded-work-and-reserve-fixture',
                'contextTailUpperBoundTokens': 500,
                'nextWorkTokens': 1000,
                'handoffTokens': 500,
                'recoveryTokens': 500,
                'safetyMarginTokens': 500,
            },
        }
        assessment.update(changes)
        return assessment

    def append_context_usage(self, total_tokens):
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        record = {'timestamp': datetime.now(timezone.utc).isoformat(), 'type': 'event_msg',
                  'payload': {'type': 'token_count', 'info': {
                      'last_token_usage': {'total_tokens': total_tokens},
                      'total_token_usage': {'total_tokens': 600000},
                      'model_context_window': 12000}}}
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record) + '\n')

    def test_first_context_read_survives_retirement_of_the_loaded_package_path(self):
        self.native_context()
        cached = self.root / 'cached-package'
        retired = self.root / 'retired-package'
        shutil.copytree(ROOT / 'plugins/yiyuan-accord-codex', cached)
        self.params['arguments']['includeContext'] = True
        state_before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        script = (
            "const fs=require('node:fs');const m=require(process.argv[1]);"
            "const request=JSON.parse(fs.readFileSync(0,'utf8'));"
            "fs.renameSync(process.argv[2],process.argv[3]);"
            "process.stdout.write(JSON.stringify(m.inspectNativeState(request)));"
        )
        p = subprocess.run([self.node, '-e', script, str(cached / 'runtime/native-state-mcp.cjs'),
            str(cached), str(retired)], input=json.dumps(self.params), text=True,
            encoding='utf-8', capture_output=True, env=self.env, cwd=self.work, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        context = json.loads(p.stdout)['value']['context']
        self.assertEqual(context['state'], 'observed', context)
        self.assertEqual(context['lastResponseTokens'], 4000)
        self.assertEqual(context['windowTokens'], 12000)
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, state_before)

    def test_missing_optional_reader_does_not_break_ordinary_status(self):
        self.native_context()
        cached = self.root / 'package-without-reader'
        shutil.copytree(ROOT / 'plugins/yiyuan-accord-codex', cached)
        (cached / 'runtime/codex-context.cjs').unlink()
        script = (
            "const fs=require('node:fs');const m=require(process.argv[1]);"
            "const request=JSON.parse(fs.readFileSync(0,'utf8'));"
            "const status=m.inspectNativeState(request);request.arguments.includeContext=true;"
            "process.stdout.write(JSON.stringify({status,context:m.inspectNativeState(request)}));"
        )
        p = subprocess.run([self.node, '-e', script, str(cached / 'runtime/native-state-mcp.cjs')],
            input=json.dumps(self.params), text=True, encoding='utf-8', capture_output=True,
            env=self.env, cwd=self.work, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['status']['value']['checkpoint']['state'], 'observed')
        self.assertNotIn('context', result['status']['value'])
        self.assertEqual(result['context']['value']['context']['reason'], 'MODULE_NOT_FOUND')

    def test_context_is_opt_in_and_current_version_comes_from_native_call(self):
        self.native_context()
        before = self.files()
        self.assertNotIn('context', self.inspect()['value'])
        self.params['arguments']['includeContext'] = True
        result = self.inspect()['value']
        context = result['context']
        self.assertEqual(context['state'], 'observed')
        self.assertEqual(context['conditions']['hostVersion'], 'observed-version')
        self.assertEqual(context['recordedHostVersion'], 'recorded-old-version')
        self.assertEqual(context['hostSourceRef'], 'codex-mcp-call:native-call-1')
        self.assertEqual(context['lastResponseTokens'], 4000)
        self.assertEqual(context['epoch'], result['checkpoint']['snapshot']['epoch'])
        self.assertFalse(context['sourceReleaseAllowed'])
        self.assertEqual(self.files(), before)

    def test_context_missing_stale_or_mismatched_remains_unknown(self):
        self.params['arguments']['includeContext'] = True
        self.assertEqual(self.inspect()['value']['context']['reason'], 'native-user-input-receipt-missing')
        self.native_context(age=120)
        expired = self.inspect()['value']['context']
        self.assertEqual(expired['reason'], 'token-count-expired')
        self.assertGreater(expired['sampleAgeMs'], 110000)
        self.assertIsNone(expired['lastResponseTokens'])
        self.params['arguments']['contextMaxAgeMs'] = 180000
        older = self.inspect()['value']['context']
        self.assertEqual(older['state'], 'observed')
        self.assertGreater(time.time()*1000-older['observedAtMs'], 110000)
        self.assertEqual(older['validUntilMs']-older['observedAtMs'], 180000)
        self.native_context()
        self.params['_meta']['x-codex-turn-metadata']['turn_id'] = 'other-turn'
        self.assertEqual(self.inspect()['value']['context']['reason'], 'current-host-turn-mismatch')

    def test_context_flag_and_current_identity_cannot_be_supplied_as_arguments(self):
        for value in (None, 1, 'true'):
            self.params['arguments']['includeContext'] = value
            self.assertTrue(self.inspect()['isError'])
        self.params['arguments']['includeContext'] = True
        for age in (0, -1, True, '30000'):
            self.params['arguments']['contextMaxAgeMs'] = age
            self.assertTrue(self.inspect()['isError'])
        self.params['arguments'].pop('contextMaxAgeMs')
        self.native_context()
        self.params['arguments']['includeContext'] = True
        self.params['_meta']['x-codex-turn-metadata'].pop('codex_version')
        self.assertEqual(self.inspect()['value']['context']['reason'], 'current-host-binding-missing')
        self.params['arguments']['currentHost'] = {'hostVersion': 'pretended'}
        self.assertTrue(self.inspect()['isError'])

    def test_context_input_change_during_state_read_is_not_combined(self):
        self.params['arguments']['includeContext'] = True
        script = "const h=require(process.argv[1]);h.operate=x=>x.op==='status'?{epoch:'one'}:{state:'observed',epoch:'two'};const m=require(process.argv[2]);let s='';process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(m.inspectNativeState(JSON.parse(s)))));"
        p = subprocess.run([self.node, '-e', script, str(CHECKPOINT), str(BRIDGE)],
            input=json.dumps(self.params), capture_output=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['value']['context']['reason'], 'input-changed-between-state-and-context')

    def test_context_assessment_uses_prior_basis_and_consumes_same_generation_growth(self):
        self.native_context()
        self.params['arguments']['includeContext'] = True
        inspection = self.inspect()['value']
        observation = inspection['context']
        assessment = self.context_assessment(inspection)
        self.params['arguments'] = {'cwd': str(self.work), 'contextAssessment': assessment,
                                    'contextMaxAgeMs': 30000}
        before = self.files()
        state_before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        first = self.inspect()['value']
        self.assertNotIn('context', first)
        self.assertEqual(first['contextAssessment']['decision'], 'continue-bounded')
        self.assertEqual(first['contextAssessment']['capacityFit'], 'fits')
        self.assertEqual(first['contextAssessment']['windowTokens'], 12000)
        self.assertFalse(first['contextAssessment']['sourceReleaseAllowed'])
        self.assertEqual(self.files(), before)

        # A later response boundary in the same generation is consumed by the
        # assessment itself; the caller does not need an observe/assess retry loop.
        self.append_context_usage(9000)
        grown = self.inspect()['value']['contextAssessment']
        self.assertEqual(grown['decision'], 'prepare-handoff')
        self.assertEqual(grown['capacityFit'], 'does-not-fit')
        self.assertNotEqual(grown['observationId'], observation['observationId'])
        self.assertFalse(grown['sourceReleaseAllowed'])
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, state_before)

    def test_context_assessment_preserves_stale_input_generation_pause_and_missing_identity(self):
        self.native_context()
        self.params['arguments']['includeContext'] = True
        inspection = self.inspect()['value']
        assessment = self.context_assessment(inspection)
        self.params['arguments'] = {'cwd': str(self.work), 'contextAssessment': assessment}
        before = self.files()

        stale_time = json.loads(json.dumps(self.params))
        stale_time['arguments']['contextAssessment']['validUntilMs'] = 0
        self.assertEqual(self.inspect(stale_time)['value']['contextAssessment']['decision'], 'reassess')

        changed_generation = json.loads(json.dumps(self.params))
        changed_generation['arguments']['contextAssessment']['contextGeneration'] = '0' * 64
        self.assertEqual(self.inspect(changed_generation)['value']['contextAssessment']['decision'], 'reassess')

        unknown_integrity = json.loads(json.dumps(self.params))
        unknown_integrity['arguments']['contextAssessment']['integrity'] = 'unknown'
        self.assertEqual(self.inspect(unknown_integrity)['value']['contextAssessment']['decision'], 'unknown')

        changed_model = json.loads(json.dumps(self.params))
        changed_model['_meta']['x-codex-turn-metadata']['model'] = 'rerouted-model'
        self.assertEqual(self.inspect(changed_model)['value']['contextAssessment']['decision'], 'reassess')

        missing_identity = json.loads(json.dumps(self.params))
        missing_identity['_meta']['x-codex-turn-metadata'].pop('codex_version')
        unknown = self.inspect(missing_identity)['value']['contextAssessment']
        self.assertEqual(unknown['decision'], 'unknown')
        self.assertIn('current-host-conditions-missing', unknown['reasons'])
        self.assertEqual(self.files(), before)

        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(),
                                     'type': 'compacted', 'payload': {'kind': 'fixture'}}) + '\n')
        self.append_context_usage(4000)
        compacted = self.inspect()['value']['contextAssessment']
        self.assertEqual(compacted['decision'], 'reassess')
        self.assertFalse(compacted['sourceReleaseAllowed'])

        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Changed task input.'},
                    session=session, hook='UserPromptSubmit')
        changed_input = self.inspect()['value']['contextAssessment']
        self.assertEqual(changed_input['decision'], 'reassess')
        self.assertFalse(changed_input['sourceReleaseAllowed'])

    def test_context_assessment_cannot_override_pause_or_supply_identity(self):
        self.native_context()
        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        (self.work / 'source.txt').write_text('protected', encoding='utf-8')
        status = self.helper({'op': 'status'}, session=session)
        self.helper({'op': 'bind', 'epoch': status['epoch'], 'expectedRevision': status['revision'],
            'result': 'Continue protected work', 'inputs': ['source.txt'],
            'outputs': [{'path': 'report.txt'}], 'nextAction': 'Complete one bounded span',
            'canContinue': True}, session=session)
        status = self.helper({'op': 'status'}, session=session)
        self.helper({'op': 'pause', 'epoch': status['epoch'], 'expectedRevision': status['revision'],
                     'reason': 'User paused.'}, session=session)
        self.params['arguments']['includeContext'] = True
        inspection = self.inspect()['value']
        assessment = self.context_assessment(inspection)
        self.params['arguments'] = {'cwd': str(self.work), 'contextAssessment': assessment}
        before = self.files()
        paused = self.inspect()['value']['contextAssessment']
        self.assertEqual((paused['decision'], paused['capacityFit']), ('paused', 'unknown'))
        self.assertFalse(paused['sourceReleaseAllowed'])
        self.assertEqual(self.files(), before)

        for key, value in [('conditions', {'threadId': 'other'}), ('op', 'bind'),
                           ('efficiencyCeilingTokens', 12000)]:
            with self.subTest(argument=key):
                body = json.loads(json.dumps(self.params))
                body['arguments']['contextAssessment'][key] = value
                self.assertTrue(self.inspect(body)['isError'])

    def test_context_assessment_rejects_checkpoint_revision_change_with_same_input_epoch(self):
        self.native_context()
        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        self.params['arguments']['includeContext'] = True
        inspection = self.inspect()['value']
        assessment = self.context_assessment(inspection)
        (self.work / 'source.txt').write_text('protected', encoding='utf-8')
        status = self.helper({'op': 'status'}, session=session)
        self.assertEqual(status['epoch'], assessment['epoch'])
        self.helper({'op': 'bind', 'epoch': status['epoch'], 'expectedRevision': status['revision'],
            'result': 'Bind changed work state', 'inputs': ['source.txt'],
            'outputs': [{'path': 'report.txt'}], 'nextAction': 'Continue carefully',
            'canContinue': True}, session=session)
        self.params['arguments'] = {'cwd': str(self.work), 'contextAssessment': assessment}
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        result = self.inspect()['value']['contextAssessment']
        self.assertEqual(result['decision'], 'reassess')
        self.assertIn('task-revision-or-input-conflict', result['reasons'])
        self.assertFalse(result['sourceReleaseAllowed'])
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)

    def test_missing_native_metadata_never_uses_argument_identity_or_creates_state(self):
        body = {'name': 'inspect_task_state', 'arguments': {'cwd': str(self.work)}}
        result = self.inspect(body)
        self.assertTrue(result['isError'])
        self.assertEqual(result['value']['reason'], 'native-call-metadata-unavailable')
        body['arguments']['_meta'] = self.params['_meta']
        self.assertTrue(self.inspect(body)['isError'])
        self.assertFalse(self.state.exists())

    def test_root_scope_reads_status_and_drops_unrelated_metadata(self):
        for session in ('current-thread', 'ancestor-root'):
            self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Inspect this task.'}, session=session, hook='UserPromptSubmit')
        expected = self.helper({'op': 'status'})
        ancestor = self.helper({'op': 'status'}, session='ancestor-root')
        self.assertNotEqual(expected['epoch'], ancestor['epoch'])
        self.params['_meta']['private'] = 'DO_NOT_RETURN_SENTINEL'
        self.params['_meta']['x-codex-turn-metadata']['unrelated'] = 'DO_NOT_RETURN_SENTINEL'
        before = self.files()
        observed = self.inspect()
        self.assertFalse(observed['isError'])
        value = observed['value']
        self.assertEqual(value['checkpoint']['snapshot'], expected)
        self.assertEqual(value['source']['threadId'], 'current-thread')
        self.assertEqual(value['source']['sessionTreeId'], 'current-thread')
        self.assertNotIn('DO_NOT_RETURN_SENTINEL', json.dumps(observed))
        self.assertEqual(self.files(), before)

    def test_descendant_does_not_silently_adopt_shared_root_state(self):
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Root responsibility.'},
            session='ancestor-root', hook='UserPromptSubmit')
        self.params['_meta']['x-codex-turn-metadata']['session_id'] = 'ancestor-root'
        self.params['arguments']['includeContext'] = True
        before = self.files()
        value = self.inspect()['value']
        self.assertEqual(value['source']['threadId'], 'current-thread')
        self.assertEqual(value['source']['sessionTreeId'], 'ancestor-root')
        self.assertEqual(value['checkpoint'], {'state': 'unavailable', 'reason': 'shared-session-scope-requires-reconciliation'})
        self.assertEqual(value['context']['reason'], 'shared-session-scope-requires-reconciliation')
        self.assertEqual(self.files(), before)

    def test_pause_and_resume_unknowns_survive_without_writes(self):
        (self.work / 'source.txt').write_text('protected', encoding='utf-8')
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Create report.'}, hook='UserPromptSubmit')
        status = self.helper({'op': 'status'})
        self.helper({'op': 'bind', 'epoch': status['epoch'], 'expectedRevision': 0,
            'result': 'Deliver report', 'inputs': ['source.txt'], 'outputs': [{'path': 'report.txt'}],
            'nextAction': 'Create and verify report', 'canContinue': True})
        status = self.helper({'op': 'status'})
        self.helper({'op': 'pause', 'epoch': status['epoch'], 'expectedRevision': status['revision'], 'reason': 'User paused.'})
        self.helper({'hook_event_name': 'SessionStart', 'source': 'resume'}, hook='SessionStart')
        before = self.files()
        snapshot = self.inspect()['value']['checkpoint']['snapshot']
        self.assertEqual(snapshot['mode'], 'paused')
        self.assertTrue(snapshot['needsResumeReconciliation'])
        self.assertFalse(snapshot['currentInputReconciled'])
        page = self.read_input()['value']['input']
        self.assertEqual(page['entries'][0]['text'], 'Create report.')
        self.assertTrue(page['inputStatus']['needsResumeReconciliation'])
        self.assertEqual(self.files(), before)

    def test_missing_receipt_remains_unknown_and_mutation_arguments_are_rejected(self):
        value = self.inspect()['value']
        self.assertEqual(value['state'], 'observed-call-context')
        self.assertEqual(value['checkpoint']['state'], 'unavailable')
        self.assertEqual(value['checkpoint']['reason'], 'native-user-input-receipt-missing')
        for key in ('op', 'session_id', 'epoch', 'storage', 'canContinue'):
            with self.subTest(argument=key):
                body = json.loads(json.dumps(self.params))
                body['arguments'][key] = 'unexpected'
                self.assertTrue(self.inspect(body)['isError'])
        self.assertFalse(self.state.exists())

    def test_relative_workspace_and_incomplete_call_identity_are_rejected(self):
        for field in ('callId', 'thread_id', 'session_id', 'turn_id'):
            with self.subTest(field=field):
                body = json.loads(json.dumps(self.params))
                target = body['_meta'] if field == 'callId' else body['_meta']['x-codex-turn-metadata']
                target[field] = ''
                self.assertTrue(self.inspect(body)['isError'])
        self.params['arguments']['cwd'] = '.'
        self.assertTrue(self.inspect()['isError'])
        self.assertFalse(self.state.exists())

    def run_wire(self, data):
        return subprocess.run([self.node, str(BRIDGE)], input=data, capture_output=True,
            env=self.env, cwd=self.work, timeout=10)

    def test_real_stdio_negotiation_zero_id_unknown_method_and_eof(self):
        messages = [
            {'jsonrpc': '2.0', 'id': 0, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': self.params},
            {'jsonrpc': '2.0', 'id': 4, 'method': 'retire'},
            {'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call',
             'params': {**self.params, 'name': 'read_task_input'}},
            {'jsonrpc': '2.0', 'id': 6, 'method': 'tools/call', 'params': {
                **self.params, 'name': 'manage_task_state', 'arguments': {'cwd': str(self.work),
                    'action': 'pause', 'epoch': 'unobserved-epoch', 'expectedRevision': 0,
                    'reason': 'No receipt exists for this request.'}}},
        ]
        p = self.run_wire(('\n'.join(map(json.dumps, messages))+'\n').encode())
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual([row['id'] for row in rows], [0, 1, 2, 3, 4, 5, 6])
        self.assertEqual(rows[0]['error']['code'], -32002)
        self.assertEqual(rows[1]['result']['protocolVersion'], '2025-06-18')
        package_version = json.loads((ROOT/'plugins/yiyuan-accord-codex/.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(rows[1]['result']['serverInfo']['version'], package_version)
        self.assertTrue(rows[2]['result']['tools'][0]['annotations']['readOnlyHint'])
        self.assertIn('contextAssessment', rows[2]['result']['tools'][0]['inputSchema']['properties'])
        self.assertEqual([tool['name'] for tool in rows[2]['result']['tools']],
                         ['inspect_task_state', 'read_task_input', 'manage_task_state'])
        self.assertTrue(rows[2]['result']['tools'][1]['annotations']['readOnlyHint'])
        self.assertFalse(rows[2]['result']['tools'][2]['annotations']['readOnlyHint'])
        self.assertTrue(rows[2]['result']['tools'][2]['annotations']['destructiveHint'])
        self.assertEqual(rows[2]['result']['tools'][2]['inputSchema']['properties']['action']['enum'],
                         ['bind', 'pause', 'retire'])
        self.assertEqual(rows[3]['result']['structuredContent']['source']['threadId'], 'current-thread')
        self.assertEqual(rows[4]['error']['code'], -32601)
        self.assertTrue(rows[5]['result']['isError'])
        self.assertEqual(rows[5]['result']['structuredContent']['reason'], 'native-user-input-receipt-missing')
        self.assertTrue(rows[6]['result']['isError'])
        self.assertEqual(rows[6]['result']['structuredContent']['reason'], 'native-user-input-receipt-missing')
        self.assertFalse(self.state.exists())

    def test_invalid_utf8_oversize_and_truncated_input_have_no_state_effect(self):
        bad_utf8 = self.run_wire(b'\xff\n')
        self.assertEqual(json.loads(bad_utf8.stdout)['error']['code'], -32700)
        for raw in (b'x' * (128*1024+1), b'{"jsonrpc":"2.0"}'):
            p = self.run_wire(raw)
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(p.stdout)
        self.assertFalse(self.state.exists())

    def test_transport_failure_after_valid_write_requires_poststate_check(self):
        status = self.receive_current_input('Bind this state before the transport closes.')
        manage = {**self.params, 'name': 'manage_task_state', 'arguments': {
            'cwd': str(self.work), 'action': 'bind', 'epoch': status['epoch'],
            'expectedRevision': status['revision'], 'result': 'Preserve the applied binding',
            'inputs': [], 'outputs': [{'path': 'report.txt'}],
            'nextAction': 'Create and verify report.txt', 'canContinue': True}}
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {},
                'clientInfo': {'name': 'poststate-test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': manage},
        ]
        raw = ('\n'.join(map(json.dumps, messages)) + '\n{').encode()
        process = self.run_wire(raw)
        self.assertNotEqual(process.returncode, 0)
        rows = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertFalse(rows[-1]['result']['isError'], rows[-1])
        self.assertNotIn(b'no state mutation was requested', process.stderr)
        self.assertIn(b'inspect task state for prior operation effects before retrying', process.stderr)
        saved = self.helper({'op': 'status'})
        self.assertEqual(saved['checkpoint']['result'], 'Preserve the applied binding')

    def test_incomplete_initialize_does_not_activate_tools(self):
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': self.params},
        ]
        p = self.run_wire(('\n'.join(map(json.dumps, messages))+'\n').encode())
        rows = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual([row['error']['code'] for row in rows], [-32602, -32002])
        self.assertFalse(self.state.exists())

    def test_package_registers_exact_source_without_an_account_or_network_endpoint(self):
        package = ROOT / 'plugins/yiyuan-accord-codex'
        self.assertEqual(BRIDGE.read_bytes(), (package / 'runtime/native-state-mcp.cjs').read_bytes())
        config = json.loads((package / '.mcp.json').read_text(encoding='utf-8'))
        self.assertEqual(config, {'mcpServers': {'accord-state': {'command': 'node',
            'args': ['runtime/native-state-mcp.cjs'], 'cwd': '.',
            'startup_timeout_sec': 10, 'tool_timeout_sec': 10}}})
        adapter = json.loads((package / 'adapter.json').read_text(encoding='utf-8'))
        self.assertTrue(adapter['persistentProcessAdded'])
        self.assertEqual(adapter['nativeTaskStateMcp']['storage'], 'existing-task-checkpoint-only')

    def test_running_stdio_server_does_not_pin_plugin_cache_directory(self):
        cache = self.root / 'cache'
        package = cache / 'version'
        shutil.copytree(ROOT / 'plugins/yiyuan-accord-codex', package)
        readers = []
        process = subprocess.Popen([self.node, 'runtime/native-state-mcp.cjs'], cwd=package,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env)
        def exchange(request):
            process.stdin.write((json.dumps(request) + '\n').encode())
            process.stdin.flush()
            output = queue.Queue()
            reader = threading.Thread(target=lambda: output.put(process.stdout.readline()), daemon=True)
            readers.append(reader)
            reader.start()
            return json.loads(output.get(timeout=5))
        try:
            initialized = exchange({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {},
                'clientInfo': {'name': 'cache-lifecycle-test', 'version': '1'}}})
            self.assertIn('serverInfo', initialized['result'])
            cache.rename(self.root / 'cache-backup')
            self.assertEqual(exchange({'jsonrpc': '2.0', 'id': 2, 'method': 'ping'})['result'], {})
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            for reader in readers:
                reader.join(timeout=5)
            process.stdout.close()
            process.stderr.close()
        self.assertEqual(process.returncode, 0)
        self.assertTrue(all(not reader.is_alive() for reader in readers))

    def test_relative_state_override_keeps_its_startup_directory_base(self):
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Current input.'}, hook='UserPromptSubmit')
        expected = self.helper({'op': 'status'})
        profile = self.root / 'native-home/profile'
        profile.mkdir(parents=True)
        self.env.update(HOME=str(profile), USERPROFILE=str(profile),
            YIYUAN_ACCORD_TASK_STATE_DIR=os.path.relpath(self.state, self.work))
        before = self.files()
        messages = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {},
                'clientInfo': {'name': 'relative-state-test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': self.params},
        ]
        p = self.run_wire(('\n'.join(map(json.dumps, messages))+'\n').encode())
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout.splitlines()[-1])['result']['structuredContent']
        self.assertEqual(result['checkpoint'], {'state': 'observed', 'snapshot': expected})
        self.assertEqual(self.files(), before)


def _finalize_native_integration(result, app, fixture, root, host, *, body_failed):
    """Retain the body outcome and every available native release receipt."""
    cleanup_failures = []

    def failed(stage, error):
        cleanup_failures.append({'stage': stage, 'failure': type(error).__name__,
                                 'reason': str(error)})

    if app is not None:
        try:
            result['resources'] = app.close()
        except BaseException as error:
            failed('app.close', error)
            if getattr(app, '_close_record', None) is not None:
                result['resources'] = app._close_record
    try:
        fixture.close()
    except BaseException as error:
        failed('fixture.close', error)

    if app is not None:
        record = result.get('resources')
        try:
            if (not isinstance(record, dict) or record.get('forced') is not False
                    or not isinstance(record.get('after'), dict)
                    or not host._released(record['after'])):
                raise RuntimeError('native process domain was not naturally released')
        except BaseException as error:
            failed('resource.release', error)
    if cleanup_failures:
        result['status'] = 'failed'
        result['cleanupFailures'] = cleanup_failures
    try:
        host.save(root/'result.json', result)
    except BaseException:
        if not body_failed:
            raise
    if cleanup_failures and not body_failed:
        raise RuntimeError('native integration cleanup failed: ' +
                           ', '.join(item['stage'] for item in cleanup_failures))


def native_integration(codex, evidence, *, preapprove_owned_manage_tool=False):
    """Native metadata and host denial or adapter rejection; fixed replies, no model."""
    sys.path.insert(0, str(ROOT))
    from scripts import observe_codex_lifecycle as host
    from scripts import observe_codex_entry, codex_rpc, inspect_native_resources
    root = Path(evidence).absolute()
    if root.exists() or root.parent.resolve() != root.parent or not root.parent.is_dir():
        raise ValueError('fresh parent-owned evidence directory required')
    root.mkdir()
    for name in ('home', 'workspace', 'state', 'temp', 'marketplace', 'commands', 'native', 'retained'):
        (root / name).mkdir()
    codex = Path(codex).resolve(strict=True)
    if os.name == 'nt' and codex.suffix.lower() != '.exe':
        raise ValueError('native executable required')
    node = Path(shutil.which('node')).resolve(strict=True)
    package = ROOT / 'plugins/yiyuan-accord-codex'
    prepared = root / 'marketplace/plugins/yiyuan-accord-codex'
    shutil.copytree(package, prepared)
    catalogue = root / 'marketplace/.agents/plugins'
    catalogue.mkdir(parents=True)
    shutil.copyfile(ROOT / '.agents/plugins/marketplace.json', catalogue / 'marketplace.json')
    original = root / 'workspace/keep.txt'
    original.write_bytes(b'Preserve this original.\n')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    manifest = {'evidence': str(root), 'codex': str(codex), 'node': str(node),
        'manageApproval': 'requested-process-scoped-fixture-preapproval' if preapprove_owned_manage_tool else 'native-default-with-never-policy',
        'binarySha256': sha(codex), 'protectedSha256': sha(original),
        'ownedRoots': {name: str(root/name) for name in ('home','workspace','state','temp')},
        'limits': {'requestSeconds': 30, 'recoverySeconds': 15,
                   'providerRequestBytes': 2*1024*1024, 'providerRequests': 3},
        'resourceController': 'windows-job-object' if os.name == 'nt' else 'posix-session-process-group'}
    source_files = [Path(__file__), Path(host.__file__), Path(observe_codex_entry.__file__),
        Path(codex_rpc.__file__), Path(inspect_native_resources.__file__)]
    source_files += [p for p in package.rglob('*') if p.is_file()]
    manifest['sources'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in source_files}
    for source in source_files:
        dest = root/'retained/executed-sources'/source.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        if sha(source) != sha(dest): raise ValueError('source changed while freezing')
    host.save(root/'manifest.json', manifest)
    env = host._owned_environment(manifest)
    deadline = time.monotonic()+150
    def command(label, arguments):
        record, value = host._run_cli(manifest, label, arguments, env, deadline)
        if (record['exitCode'] or record['forced'] or record['failure']
                or not host._released(record['after'])):
            raise RuntimeError('native plugin operation failed')
        return value
    command('marketplace-add', ['plugin','marketplace','add', str(root/'marketplace'),'--json'])
    command('plugin-add', ['plugin','add','yiyuan-accord-codex@yiyuan-accord','--json'])

    def exposed_tool(body, suffix):
        tools = list(body.get('tools', []))
        for item in body.get('input', []):
            if isinstance(item, dict) and item.get('type') == 'additional_tools': tools += item.get('tools', [])
        matches = []
        def collect(items, namespace=None):
            for tool in items:
                if tool.get('type') == 'namespace': collect(tool.get('tools', []), tool.get('name'))
                elif tool.get('type') == 'function' and tool.get('name', '').endswith(suffix):
                    matches.append((namespace, tool['name']))
        collect(tools)
        matches = list(dict.fromkeys(matches))
        if len(matches) != 1: raise ValueError('one directly exposed ' + suffix + ' tool required')
        return matches[0]

    def response(body, ordinal):
        if ordinal == 1:
            namespace, name = exposed_tool(body, 'inspect_task_state')
            arguments = {'cwd':str(root/'workspace'), 'includeContext':True}
            identity = ('state_tool_call', 'native_state_call')
        elif ordinal == 2:
            namespace, name = exposed_tool(body, 'manage_task_state')
            arguments = {'cwd':str(root/'workspace'), 'action':'pause',
                'epoch':'fixture-unobserved-receipt', 'expectedRevision':0,
                'reason':'Fixture checks missing-receipt rejection only; do not create task state.'}
            identity = ('manage_tool_call', 'native_manage_call')
        else:
            return None
        return {'type':'function_call', 'id':identity[0], 'call_id':identity[1],
            'name':name, **({'namespace':namespace} if namespace else {}),
            'arguments':json.dumps(arguments)}

    fixture = host._Fixture(manifest, response)
    app = None
    result = {'realModelCalls': 0, 'status': 'pending'}
    body_failed = False
    try:
        extra = ['-c','features.hooks=false','-c','features.code_mode_host=false']
        if preapprove_owned_manage_tool:
            # Official per-tool setting, only in this isolated test process. The
            # rejected pause has no receipt and cannot create checkpoint state.
            # 0.155.1 CLI override paths split on dots; quotes on the left are
            # literal key characters, unlike a TOML table header.
            extra += ['-c', 'plugins.yiyuan-accord-codex@yiyuan-accord.mcp_servers.accord-state.tools.manage_task_state.approval_mode="approve"']
        argv = host._argv(manifest, fixture, tuple(extra))
        app = host._App(manifest, 'mcp-state', argv, env, deadline)
        app.initialize()
        started = app.rpc('thread/start', {'cwd':str(root/'workspace'), 'model':'fixture-no-model',
            'ephemeral':True, 'sandbox':'read-only', 'approvalPolicy':'never'})
        thread = started['thread']['id']
        if started.get('sandbox', {}).get('type') != 'readOnly': raise RuntimeError('source is not read-only')
        turn = app.rpc('turn/start', {'threadId':thread,
            'input':[{'type':'text','text':'Inspect this workspace state and check that a state-management request with an unobserved receipt is rejected. Preserve files and do not create task state.'}]})['turn']['id']
        terminal = app.wait_turn(thread, turn)
        calls = [e['params']['item'] for e in app.events if e.get('method') == 'item/completed'
            and e.get('params', {}).get('threadId') == thread
            and e.get('params', {}).get('turnId') == turn
            and e.get('params', {}).get('item', {}).get('type') == 'mcpToolCall']
        if terminal != 'completed' or len(calls) != 2: raise RuntimeError('two completed MCP calls required')
        indexed = {call.get('id'): call for call in calls}
        if set(indexed) != {'native_state_call', 'native_manage_call'}:
            raise RuntimeError('native MCP call identities differ')
        call = indexed['native_state_call']
        reply, value = native_tool_result(call)
        if not value or call.get('status') != 'completed' or call.get('error'):
            raise RuntimeError('state tool result unavailable')
        source = value['source']
        if (source['threadId'] != thread or source['sessionTreeId'] != thread
                or source['turnId'] != turn or source['callId'] != call['id']):
            raise RuntimeError('metadata differs from native thread/turn/call receipts')
        if value['checkpoint'] != {'state':'unavailable','reason':'native-user-input-receipt-missing'}:
            raise RuntimeError('absent hook receipt was not preserved as unknown')
        if value.get('context', {}).get('reason') != 'native-user-input-receipt-missing':
            raise RuntimeError('optional context must preserve absent input as unknown')
        manage_call = indexed['native_manage_call']
        manage_disposition = native_manage_disposition(manage_call,
            preapproved=preapprove_owned_manage_tool)
        if sha(original) != manifest['protectedSha256'] or list((root/'state').iterdir()):
            raise RuntimeError('native state calls changed protected files or created task state')
        status_request = {'threadId': thread, 'detail': 'toolsAndAuthOnly'}
        live = app.rpc('mcpServerStatus/list', status_request)
        servers = [s for s in live['data'] if s.get('pluginId') == 'yiyuan-accord-codex@yiyuan-accord']
        if len(servers) != 1 or servers[0]['runtimeStatus'] != 'connected':
            raise RuntimeError('installed MCP must be connected before cache replacement')
        package_version = json.loads((package/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
        if servers[0]['serverInfo']['version'] != package_version:
            raise RuntimeError('MCP implementation identity differs from the installed package')
        cache = root/'home/plugins/cache/yiyuan-accord/yiyuan-accord-codex'
        before_cache = cache.stat()
        # Local fixture markets use native add/reinstall; marketplace upgrade is Git-only.
        upgrade = command('reinstall-live-mcp', ['plugin','add','yiyuan-accord-codex@yiyuan-accord','--json'])
        after_cache = cache.stat()
        if (upgrade.get('errors') or (before_cache.st_dev, before_cache.st_ino)
                == (after_cache.st_dev, after_cache.st_ino)):
            raise RuntimeError('native cache replacement was not established')
        after_status = app.rpc('mcpServerStatus/list', status_request)
        after_servers = [s for s in after_status['data'] if s.get('pluginId') == 'yiyuan-accord-codex@yiyuan-accord']
        if (len(after_servers) != 1 or after_servers[0]['runtimeStatus'] != 'connected'
                or not {'inspect_task_state','manage_task_state'}.issubset(after_servers[0]['tools'])):
            raise RuntimeError('MCP connection or state tool lost after replacement')
        result['liveCacheUpgrade'] = {'beforeMcp': servers, 'result': upgrade,
            'beforeIdentity': [str(before_cache.st_dev), str(before_cache.st_ino)],
            'afterIdentity': [str(after_cache.st_dev), str(after_cache.st_ino)],
            'afterMcp': after_status}
        if sha(original) != manifest['protectedSha256'] or list((root/'state').iterdir()):
            raise RuntimeError('cache replacement changed original or task state')
        if len(fixture.requests) != 3 or fixture.auth_seen: raise RuntimeError('provider bounds differ')
        result.update(status='passed', threadId=thread, turnId=turn, nativeCall=call,
            nativeManageCall=manage_call, manageDisposition=manage_disposition,
            providerRequests=len(fixture.requests), sourceSettings=started,
            claimLimit='Native plugin MCP registration and declared host-approval boundary. A denied/rejected write request is neither business success nor a completed state change; no real model judgment, GUI adoption or handoff dispatch. Process-scoped fixture preapproval, when selected, is not a user permission or product default.')
    except BaseException as error:
        body_failed = True
        result.update(status='failed', failure=type(error).__name__, reason=str(error))
        raise
    finally:
        _finalize_native_integration(result, app, fixture, root, host,
                                     body_failed=body_failed)
    if any(sha(ROOT/name) != digest for name,digest in manifest['sources'].items()):
        raise RuntimeError('execution sources changed during the episode')
    shutil.copy2(original, root/'retained/keep.txt')
    removed=[]
    for name in ('home','workspace','state','temp','marketplace'):
        target=root/name
        if target.resolve() != target or target.parent != root: raise ValueError('unsafe cleanup target')
        host._remove_owned_tree(target); removed.append(str(target))
    host.save(root/'cleanup.json',{'removed':removed,'originalRetained':True,'userHomeTouched':False})
    print(json.dumps({'status':result['status'],'providerRequests':len(fixture.requests),
                      'realModelCalls':0,'resources':result['resources']},ensure_ascii=False))


if __name__ == '__main__':
    if '--native-codex' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--native-codex', required=True)
        parser.add_argument('--evidence', required=True)
        parser.add_argument('--preapprove-owned-manage-tool', action='store_true',
            help='isolated fixture process only: prebind official approval of this one missing-receipt rejection probe')
        arguments = parser.parse_args()
        native_integration(arguments.native_codex, arguments.evidence,
            preapprove_owned_manage_tool=arguments.preapprove_owned_manage_tool)
    else:
        unittest.main()
