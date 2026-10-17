"""Bounded MCP task-state entry; native host metadata delivery is checked separately."""
import json
import base64
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
BRIDGE = ROOT / 'plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs'
CHECKPOINT = BRIDGE.with_name('task-checkpoint.cjs')


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
        # Model the host's cleared environment plus the manifest's explicit forwarding.
        config = json.loads((ROOT / 'plugins/yiyuan-accord-codex/.mcp.json').read_text(encoding='utf-8'))
        allowed = {'PATH', 'SYSTEMROOT', 'WINDIR', *config['mcpServers']['accord-state'].get('env_vars', [])}
        env = {key: value for key, value in self.env.items() if key.upper() in allowed}
        env.update(HOME=str(self.root), USERPROFILE=str(self.root))
        p = subprocess.run([self.node, '-e', code, str(BRIDGE), operation], input=json.dumps(params or self.params),
            capture_output=True, text=True, encoding='utf-8', env=env, timeout=10)
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

    def test_bind_missing_contract_fields_explains_retry_without_inheriting_state(self):
        status = self.receive_current_input()
        contract = dict(action='bind', epoch=status['epoch'], expectedRevision=0,
            result='Deliver three reviewed artifacts', inputs=[],
            outputs=[{'path': name} for name in ('report.md', 'facts.json', 'review.md')],
            nextAction='Verify the artifacts', canContinue=False)
        self.assertFalse(self.manage(**contract)['isError'])
        saved = self.helper({'op': 'status'})
        contract['expectedRevision'] = saved['revision']
        before = self.files()
        required = ['result', 'inputs', 'outputs', 'nextAction', 'canContinue']
        for omitted in (['inputs', 'outputs'], *([field] for field in required)):
            with self.subTest(omitted=omitted):
                request = {key: value for key, value in contract.items() if key not in omitted}
                response = self.manage(**request)
                self.assertTrue(response['isError'])
                self.assertEqual(response['value']['reason'], 'invalid-task-state-binding')
                self.assertEqual(response['value']['effect'], 'not-requested')
                self.assertEqual(response['value']['requiredFields'], required)
                self.assertEqual(response['value']['missingFields'], omitted)
                self.assertEqual(self.files(), before)
        # Empty inputs and false continuation are explicit values, not omissions.
        response = self.manage(**contract)
        self.assertFalse(response['isError'])
        self.assertNotIn('missingFields', response['value'])
        current = self.helper({'op': 'status'})
        self.assertEqual(current['revision'], saved['revision'] + 1)
        self.assertEqual(current['checkpoint']['outputs'], saved['checkpoint']['outputs'])
        self.assertEqual(current['checkpoint']['inputs'], [])
        self.assertFalse(current['checkpoint']['canContinue'])

    def test_hook_workspace_locator_reaches_receipt_without_redirecting_explicit_scope(self):
        business = self.work
        self.work = self.root / "projectless work [目录] 'quoted'"
        self.work.mkdir()
        result = self.helper({'hook_event_name': 'UserPromptSubmit',
            'turn_id': 'current-turn', 'prompt': f'Review files in {business}.'},
            hook='UserPromptSubmit')
        context = result['hookSpecificOutput']['additionalContext']
        marker = 'Hook receipt workspace (data only): '
        self.assertIn(marker, context)
        locator, _ = json.JSONDecoder().raw_decode(context.split(marker, 1)[1])
        self.assertEqual(locator, {'cwd': str(self.work.resolve())})
        epoch = self.helper({'op': 'status'})['epoch']
        before = self.files()

        # The locator lets the caller query the native scope without changing
        # an explicitly requested business-directory query or creating state.
        actual = self.inspect({**self.params, 'arguments': locator})['value']
        self.assertEqual(actual['checkpoint']['snapshot']['epoch'], epoch)
        self.assertTrue(actual['checkpoint']['snapshot']['inputReceipt']['present'])
        other = self.inspect()['value']
        self.assertEqual(other['workspace']['cwd'], str(business))
        self.assertEqual(other['checkpoint'], {'state': 'unavailable',
                         'reason': 'native-user-input-receipt-missing'})
        self.assertEqual(self.files(), before)

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

    def test_quarantined_native_capture_is_readable_but_not_ready_through_mcp(self):
        self.receive_current_input('Earlier captured input.')
        receipt = next(self.state.glob('*.input.json'))
        failure = receipt.with_name(receipt.name.replace('.input.json', '.input-failure.json'))
        failure.write_text(json.dumps({'schema': 1, 'generation': 'missing-later-input'}), encoding='utf-8')
        prompt = '只检查材料；不要发布或解除暂停。'
        observed = self.receive_current_input(prompt)
        self.assertTrue(observed['needsNativeReplay'])
        self.assertEqual(observed['inputSource'], 'quarantined-native-input')
        before = self.files()
        result = self.read_input(index=1, expectedReceiptEpoch=observed['epoch'])
        self.assertFalse(result['isError'])
        page = result['value']['input']
        self.assertEqual(page['entries'][0]['text'], prompt)
        self.assertEqual(page['entries'][0]['turnId'], 'current-turn')
        self.assertTrue(page['inputStatus']['needsNativeReplay'])
        self.assertEqual(self.files(), before)
        inspected = self.inspect()['value']['checkpoint']['snapshot']
        self.assertFalse(inspected['currentInputReconciled'])
        rejected = self.manage(action='bind', epoch=observed['epoch'], expectedRevision=0,
            result='Review local material.', inputs=[], outputs=[{'path': 'result.txt'}],
            nextAction='Reconcile current input first.', canContinue=False)
        self.assertTrue(rejected['isError'])
        self.assertEqual(self.files(), before)
        self.assertEqual(self.helper({'hook_event_name': 'Stop'}, hook='Stop'), {})
        # The caller separately reconciles the actual current event before replay.
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt,
                     'turn_id': 'current-turn', 'recovery_epoch': observed['epoch']}, hook='UserPromptSubmit')
        restored = self.inspect()['value']['checkpoint']['snapshot']
        self.assertFalse(restored['needsNativeReplay'])
        replay = self.read_input(index=2, expectedReceiptEpoch=restored['epoch'])['value']['input']
        self.assertEqual(replay['entries'][0]['source'], 'retained-native-replay')
        self.assertEqual(replay['entries'][0]['recoveryEpoch'], observed['epoch'])
        self.assertTrue(failure.exists())

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

        # A successful write must remain inspectable through the same MCP entry.
        before = self.files()
        observed = self.inspect()
        self.assertFalse(observed['isError'], observed)
        self.assertEqual(self.files(), before)
        projected = observed['value']['checkpoint']['snapshot']
        self.assertEqual(projected['epoch'], saved['epoch'])
        self.assertEqual(projected['revision'], saved['revision'])
        self.assertEqual(projected['checkpoint']['epoch'], saved['checkpoint']['epoch'])
        self.assertEqual(projected['checkpoint']['details'], 'omitted-bounded-result')
        self.assertEqual(projected['inspection']['status'], 'incomplete')
        self.assertIn('Do not replace omitted details', observed['value']['detailRead'])
        locator = projected['checkpointSource']
        stored_bytes = Path(locator['path']).read_bytes()
        self.assertEqual(hashlib.sha256(stored_bytes).hexdigest(), locator['sha256'])
        stored = json.loads(stored_bytes)
        self.assertEqual(stored['outputs'], outputs)
        self.assertEqual(stored['unresolved'], unresolved)
        self.assertLess(len(json.dumps(observed['value'], ensure_ascii=False).encode()), 128 * 1024)

        paused = self.manage(action='pause', epoch=saved['epoch'], expectedRevision=saved['revision'],
                             reason='The user paused this unfinished task.')
        self.assertFalse(paused['isError'], paused)
        self.helper({'hook_event_name': 'SessionStart', 'source': 'resume'}, hook='SessionStart')
        resumed_basis = self.helper({'op': 'status'})
        before = self.files()
        self.params['arguments']['includeContext'] = True
        resumed = self.inspect()
        self.assertFalse(resumed['isError'], resumed)
        self.assertEqual(self.files(), before)
        projected = resumed['value']['checkpoint']['snapshot']
        for key in ('epoch', 'revision', 'mode', 'currentInputReconciled', 'needsNativeReplay',
                    'needsResumeReconciliation', 'inputReceipt', 'inputSource', 'checkpointSource'):
            self.assertEqual(projected[key], resumed_basis[key])
        self.assertEqual(projected['mode'], 'paused')
        self.assertTrue(projected['needsResumeReconciliation'])
        self.assertFalse(projected['currentInputReconciled'])
        self.assertFalse(resumed['value']['context']['sourceReleaseAllowed'])
        self.assertNotEqual(projected['checkpointSource']['sha256'], locator['sha256'])
        current_bytes = Path(projected['checkpointSource']['path']).read_bytes()
        self.assertEqual(hashlib.sha256(current_bytes).hexdigest(), projected['checkpointSource']['sha256'])
        self.assertEqual(json.loads(current_bytes)['reason'], 'The user paused this unfinished task.')

        # A locator is useful only for the validated source; corrupting that
        # same large file must not fall through to a successful summary.
        Path(projected['checkpointSource']['path']).write_bytes(current_bytes[:-1])
        before = self.files()
        rejected = self.inspect()
        self.assertEqual(rejected['value']['checkpoint']['state'], 'unavailable')
        self.assertEqual(rejected['value']['checkpoint']['reason'], 'state-inspection-unavailable')
        self.assertNotIn('detailRead', rejected['value'])
        self.assertEqual(self.files(), before)

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

    def automatic_capacity_retry(self, turn='retry-turn'):
        meta = self.params['_meta']['x-codex-turn-metadata']
        original = meta['turn_id']
        records = [
            {'type': 'event_msg', 'payload': {'type': 'task_complete',
                'turn_id': original, 'root_turn_id': original, 'error': {
                    'codex_error_info': 'server_overloaded',
                    'message': 'Selected model is at capacity. Please try a different model.'}}},
            {'type': 'event_msg', 'payload': {'type': 'task_started',
                'turn_id': turn, 'root_turn_id': turn, 'turn_attribution': {
                    'turn_id': turn, 'root_turn_id': turn,
                    'turn_trigger': 'capacity_retry_automatic',
                    'parent_turn_id': None, 'initiating_agent_path': None}}},
            {'type': 'turn_context', 'payload': {'turn_id': turn,
                'model': meta['model'], 'cwd': str(self.work)}},
        ]
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            for record in records:
                stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(),
                                         **record}) + '\n')
        meta['turn_id'] = turn
        return records

    def test_manage_capacity_retry_uses_bound_native_proof_without_replacing_input(self):
        self.native_context()
        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        status = self.helper({'op': 'status'}, session=session)
        contract = dict(result='Retain the bounded contract', inputs=[],
            outputs=[{'path': 'report.txt'}], nextAction='Create and verify report.txt',
            canContinue=True)
        self.assertFalse(self.manage(action='bind', epoch=status['epoch'], expectedRevision=0,
                                     **contract)['isError'])
        receipt = next(self.state.glob('*.input.json'))
        original_input = receipt.read_bytes()
        self.automatic_capacity_retry()
        self.append_context_usage(4500)
        before = self.files()
        self.assertFalse(self.inspect()['isError'])
        self.assertEqual(self.files(), before)
        response = self.manage(action='bind', epoch=status['epoch'], expectedRevision=1,
                               **contract)
        self.assertFalse(response['isError'], response)
        current = self.helper({'op': 'status'}, session=session)
        self.assertEqual((current['epoch'], current['revision'], current['mode']),
                         (status['epoch'], 2, 'active'))
        self.assertEqual(receipt.read_bytes(), original_input)
        before = self.files()
        self.params['arguments']['includeContext'] = True
        context = self.inspect()['value']['context']
        self.assertEqual(context['state'], 'observed', context)
        self.assertEqual(context['conditions']['turnId'], 'retry-turn')
        self.assertEqual(context['lastResponseTokens'], 4500)
        self.assertEqual(context['epoch'], status['epoch'])
        self.assertFalse(context['sourceReleaseAllowed'])
        self.assertEqual(self.files(), before)

    def test_capacity_retry_rejects_missing_changed_foreign_and_new_input_proof(self):
        def edit(rows, index, key, value):
            rows[index]['payload'][key] = value

        def attribution(rows, key, value):
            rows[-2]['payload']['turn_attribution'][key] = value

        cases = [
            ('missing-origin-context', lambda r, m: r.pop(1)),
            ('missing-origin-input', lambda r, m: r.pop(2)),
            ('changed-origin-input', lambda r, m: r[2]['payload']['content'][0].update(text='Changed input.')),
            ('foreign-session', lambda r, m: edit(r, 0, 'id', 'foreign-thread')),
            ('subagent-source', lambda r, m: edit(r, 0, 'source', {'subagent': 'actor'})),
            ('unproven-root-source', lambda r, m: r[0]['payload'].pop('source')),
            ('foreign-origin-cwd', lambda r, m: edit(r, 1, 'cwd', str(self.root))),
            ('foreign-current-cwd', lambda r, m: edit(r, -1, 'cwd', str(self.root))),
            ('missing-capacity-failure', lambda r, m: r.pop(-3)),
            ('foreign-completion', lambda r, m: edit(r, -3, 'root_turn_id', 'foreign-turn')),
            ('different-failure', lambda r, m: r[-3]['payload']['error'].update(codex_error_info='other')),
            ('generic-overload', lambda r, m: r[-3]['payload']['error'].update(message='Server overloaded.')),
            ('missing-current-context', lambda r, m: r.pop()),
            ('different-current-turn', lambda r, m: edit(r, -1, 'turn_id', 'foreign-turn')),
            ('ordinary-start', lambda r, m: attribution(r, 'turn_trigger', 'composer')),
            ('invented-parent', lambda r, m: attribution(r, 'parent_turn_id', 'current-turn')),
            ('subagent-start', lambda r, m: attribution(r, 'initiating_agent_path', '/child')),
            ('foreign-root-start', lambda r, m: attribution(r, 'root_turn_id', 'foreign-turn')),
            ('missing-attribution', lambda r, m: r[-2]['payload'].pop('turn_attribution')),
            ('reversed-time', lambda r, m: r[-2].update(timestamp='2020-01-01T00:00:00Z')),
            ('new-same-text-input', lambda r, m: r.insert(-2, r[2])),
            ('new-native-input', lambda r, m: r.append({'type': 'event_msg',
                'payload': {'type': 'user_message', 'message': 'Continue this work.'}})),
            ('aborted-current-turn', lambda r, m: r.append({'type': 'event_msg',
                'payload': {'type': 'turn_aborted', 'turn_id': 'retry-turn'}})),
            ('cancelled-current-turn', lambda r, m: r.append({'type': 'event_msg',
                'payload': {'type': 'task_cancelled', 'turn_id': 'retry-turn'}})),
            ('changed-native-model', lambda r, m: m.update(model='different-model')),
            ('missing-native-model', lambda r, m: m.pop('model')),
            ('missing-native-version', lambda r, m: m.pop('codex_version')),
        ]
        meta = self.params['_meta']['x-codex-turn-metadata']
        for label, change in cases:
            with self.subTest(label=label):
                meta.update(turn_id='current-turn', model='observed-model', codex_version='observed-version')
                self.native_context()
                status = self.helper({'op': 'status'}, session=meta['session_id'])
                self.automatic_capacity_retry()
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                change(rows, meta)
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                before = self.files()
                response = self.manage(action='bind', epoch=status['epoch'], expectedRevision=0,
                    result='Retain original task', inputs=[], outputs=[{'path': 'report.txt'}],
                    nextAction='Create report.txt', canContinue=True)
                self.assertEqual(response['value']['reason'], 'native-call-turn-conflict', response)
                self.assertEqual(self.files(), before)

    def test_capacity_retry_chain_extends_old_boundary_and_preserves_pause_after_compact(self):
        self.native_context()
        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        status = self.helper({'op': 'status'}, session=session)
        contract = dict(result='Retain original task', inputs=[], outputs=[{'path': 'report.txt'}],
                        nextAction='Create report.txt', canContinue=False,
                        unresolved=['Retain this unmet condition'])
        self.assertFalse(self.manage(action='bind', epoch=status['epoch'], expectedRevision=0,
                                     **contract)['isError'])
        self.assertFalse(self.manage(action='pause', epoch=status['epoch'], expectedRevision=1,
                                     reason='User pause remains effective')['isError'])
        receipt = next(self.state.glob('*.input.json'))
        original_input = receipt.read_bytes()
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': 'response_item', 'payload': {
                'type': 'message', 'role': 'assistant', 'content': 'x'*(2*1024*1024)}})+'\n')
        self.automatic_capacity_retry('retry-one')
        self.automatic_capacity_retry('retry-two')
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': 'compacted', 'payload': {'kind': 'fixture'}})+'\n')
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': 'turn_context', 'payload': {'turn_id': 'retry-two',
                    'cwd': str(self.work), 'model': 'observed-model'}})+'\n')
        self.append_context_usage(3000)
        response = self.manage(action='bind', epoch=status['epoch'], expectedRevision=2, **contract)
        self.assertFalse(response['isError'], response)
        current = self.helper({'op': 'status'}, session=session)
        self.assertEqual((current['mode'], current['revision']), ('paused', 3))
        self.assertEqual(current['checkpoint']['reason'], 'User pause remains effective')
        self.assertEqual(current['checkpoint']['unresolved'], contract['unresolved'])
        self.assertEqual(receipt.read_bytes(), original_input)
        before = self.files()
        blocked = self.manage(action='retire', epoch=status['epoch'], expectedRevision=3)
        self.assertEqual(blocked['value']['reason'], 'paused-task-cannot-retire')
        self.params['arguments']['includeContext'] = True
        context = self.inspect()['value']['context']
        self.assertEqual(context['state'], 'observed', context)
        self.assertEqual(context['turnAssociation']['retryCount'], 2)
        self.assertEqual(context['turnAssociation']['originalTurnId'], 'current-turn')
        self.assertEqual(self.files(), before)

    def test_capacity_retry_bounded_origin_and_recovery_flags_cannot_be_bypassed(self):
        meta = self.params['_meta']['x-codex-turn-metadata']
        for flag in ('needsNativeReplay', 'needsResumeReconciliation', 'interrupted', 'origin-over-budget'):
            with self.subTest(flag=flag):
                meta['turn_id'] = 'current-turn'
                self.native_context()
                status = self.helper({'op': 'status'}, session=meta['session_id'])
                receipt = next(self.state.glob('*.input.json'))
                original_input = receipt.read_bytes()
                if flag == 'origin-over-budget':
                    transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                    with transcript.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'type': 'response_item', 'payload': {
                            'role': 'assistant', 'content': 'x'*(16*1024*1024+1024)}})+'\n')
                else:
                    value = json.loads(receipt.read_bytes())
                    value[flag] = True
                    receipt.write_text(json.dumps(value), encoding='utf-8')
                self.automatic_capacity_retry()
                before = self.files()
                rejected = self.manage(action='bind', epoch=status['epoch'], expectedRevision=0,
                    result='Retain original task', inputs=[], outputs=[{'path': 'report.txt'}],
                    nextAction='Create report.txt', canContinue=True)
                self.assertEqual(rejected['value']['reason'], 'native-call-turn-conflict')
                self.assertEqual(self.files(), before)
                receipt.write_bytes(original_input)

    def test_capacity_retry_rechecks_receipt_failure_and_native_proof_before_write(self):
        meta = self.params['_meta']['x-codex-turn-metadata']
        source = self.work / 'source.txt'
        source.write_text('Protected source', encoding='utf-8')
        for change in ('new-input', 'same-epoch-receipt', 'failure-watermark', 'changing-transcript',
                       'final-proof-watermark', 'final-proof-receipt'):
            with self.subTest(change=change):
                for receipt in self.state.glob('*.input.json'):
                    receipt.unlink()
                meta['turn_id'] = 'current-turn'
                self.native_context()
                status = self.helper({'op': 'status'}, session=meta['session_id'])
                self.automatic_capacity_retry()
                receipt = next(self.state.glob('*.input.json'))
                original_input = receipt.read_bytes()
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                params = {**self.params, 'name': 'manage_task_state', 'arguments': dict(
                    cwd=str(self.work), action='bind', epoch=status['epoch'], expectedRevision=0,
                    result='Retain original task', inputs=['source.txt'],
                    outputs=[{'path': 'report.txt'}], nextAction='Create report.txt', canContinue=True)}
                script = r"""
const fs=require('node:fs'),path=require('node:path');
const x=JSON.parse(fs.readFileSync(0,'utf8'));let changed=false;
const inject=()=>{
  if(changed)return;changed=true;
  if(['same-epoch-receipt','final-proof-receipt'].includes(x.change)){
    const input=JSON.parse(fs.readFileSync(x.receipt,'utf8'));
    input.hostObservation.values.permissionMode='changed-during-inspection';
    fs.writeFileSync(x.receipt,JSON.stringify(input));
  }else if(['failure-watermark','final-proof-watermark'].includes(x.change)){
    fs.writeFileSync(x.receipt.replace('.input.json','.input-failure.json'),
      JSON.stringify({schema:1,generation:'later-input-failure'}));
  }else fs.appendFileSync(x.transcript,JSON.stringify({type:'response_item',
    payload:{type:'message',role:'user',content:[{type:'input_text',text:'New human input'}]}})+'\n');
};
if(x.change.startsWith('final-proof-')){
  const open=fs.openSync,close=fs.closeSync,read=fs.readSync,readFile=fs.readFileSync;
  const fds=new Set();let finalPhase=false;
  fs.readFileSync=(file,...args)=>{const value=readFile(file,...args);
    if(typeof file==='string'&&path.resolve(file)===x.source)finalPhase=true;return value;};
  fs.openSync=(file,...args)=>{const fd=open(file,...args);if(file===x.transcript)fds.add(fd);return fd;};
  fs.closeSync=(fd)=>{fds.delete(fd);return close(fd);};
  fs.readSync=(fd,...args)=>{const value=read(fd,...args);if(fds.has(fd)&&finalPhase)inject();return value;};
}else if(x.change==='changing-transcript'){
  const read=fs.readSync;fs.readSync=(...args)=>{const value=read(...args);inject();return value;};
}else{
  const read=fs.readFileSync;fs.readFileSync=(file,...args)=>{
    const value=read(file,...args);if(typeof file==='string'&&path.resolve(file)===x.source)inject();
    return value;
  };
}
const response=require(process.argv[1]).manageTaskState(x.params);
process.stdout.write(JSON.stringify({response,changed}));
"""
                request = dict(params=params, change=change, source=str(source),
                               receipt=str(receipt), transcript=str(transcript))
                p = subprocess.run([self.node, '-e', script, str(BRIDGE)], input=json.dumps(request),
                    text=True, encoding='utf-8', capture_output=True, env=self.env, timeout=10)
                self.assertEqual(p.returncode, 0, p.stderr)
                value = json.loads(p.stdout)
                self.assertTrue(value['changed'])
                response = value['response']
                self.assertTrue(response['isError'], response)
                self.assertIn(response['value']['reason'],
                              ('native-call-turn-conflict', 'latest-user-input-not-reconciled'))
                self.assertFalse(any(self.state.glob('*.state.json')))
                self.assertEqual(source.read_text(encoding='utf-8'), 'Protected source')
                if change in ('failure-watermark', 'final-proof-watermark'):
                    marker = receipt.with_name(receipt.name.replace('.input.json', '.input-failure.json'))
                    self.assertEqual(json.loads(marker.read_bytes())['generation'], 'later-input-failure')
                    self.assertTrue(self.helper({'op': 'status'}, session=meta['session_id'])['needsNativeReplay'])
                    marker.unlink()
                if change not in ('same-epoch-receipt', 'final-proof-receipt'):
                    self.assertEqual(receipt.read_bytes(), original_input)
                receipt.write_bytes(original_input)

    def test_capacity_retry_context_cannot_combine_proof_with_a_changed_second_snapshot(self):
        self.native_context()
        self.automatic_capacity_retry()
        self.append_context_usage(4500)
        self.params['arguments']['includeContext'] = True
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        receipt = next(self.state.glob('*.input.json'))
        original_input = receipt.read_bytes()
        script = r"""
const fs=require('node:fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));
const stat=fs.lstatSync;let observations=0,changed=false;
fs.lstatSync=(file,...args)=>{
  if(file===x.transcript&&++observations===3){
    changed=true;fs.appendFileSync(file,JSON.stringify({type:'response_item',
      payload:{type:'message',role:'user',content:[{type:'input_text',text:'New input'}]}})+'\n');
  }
  return stat(file,...args);
};
const result=require(process.argv[1]).inspectNativeState(x.params);
process.stdout.write(JSON.stringify({result,changed}));
"""
        p = subprocess.run([self.node, '-e', script, str(BRIDGE)],
            input=json.dumps(dict(params=self.params, transcript=str(transcript))),
            capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        value = json.loads(p.stdout)
        context = value['result']['value']['context']
        self.assertFalse(value['changed'] and context['state'] == 'observed', context)
        if not value['changed']:
            self.assertEqual(context['state'], 'observed', context)
            self.assertEqual(context['lastResponseTokens'], 4500)
        self.assertEqual(receipt.read_bytes(), original_input)
        self.assertFalse(any(self.state.glob('*.state.json')))

    def native_input_preview(self):
        params = {**self.params, 'arguments': {'cwd': str(self.work), 'includeNativeInputs': True}}
        result = self.inspect(params)
        self.assertFalse(result['isError'], result)
        return result['value']['checkpoint']['snapshot']

    def append_native_message(self, role='user', text='Native steering', **fields):
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        record = {'type': 'response_item', 'payload': {'type': 'message', 'role': role,
            'content': [{'type': 'input_text', 'text': text}], **fields}}
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(record)+'\n')
        return transcript

    def test_large_native_evidence_retains_state_and_readonly_helper_route(self):
        self.check_large_native_evidence()

    def test_large_native_evidence_preserves_large_paused_contract(self):
        self.check_large_native_evidence(paused=True)

    def check_large_native_evidence(self, paused=False):
        self.native_context()
        initial = self.native_input_preview()
        revision = 0
        if paused:
            self.assertFalse(self.manage(action='bind', epoch=initial['epoch'], expectedRevision=0,
                result='Preserve the authorized outcome', inputs=[], outputs=[{'path': 'out.json'}],
                nextAction='Wait for user resume', canContinue=False,
                unresolved=['unresolved-' + 'x' * 1900 + str(index) for index in range(32)])['isError'])
            self.assertFalse(self.manage(action='pause', epoch=initial['epoch'], expectedRevision=1,
                                        reason='Real pause')['isError'])
            revision = 2
        for index in range(300):
            self.append_native_message(text='Follow next authorized step', id=f'ordinary-{index}')
        before = self.files()
        params = {**self.params, 'arguments': {'cwd': str(self.work), 'includeNativeInputs': True}}
        result = self.inspect(params)
        self.assertFalse(result['isError'], result)
        self.assertLessEqual(len(json.dumps(result['value'], ensure_ascii=False).encode()), 128 * 1024)
        snapshot = result['value']['checkpoint']['snapshot']
        evidence = snapshot['nativeInputEvidence']
        self.assertEqual(evidence['details'], 'omitted-bounded-result')
        self.assertEqual(evidence['counts'], {'records': 301, 'pendingInputs': 300, 'enrichments': 0})
        for key in ('records', 'pendingInputs', 'enrichments', 'cursor'):
            self.assertNotIn(key, evidence)
        fallback = evidence['detailRead']
        self.assertEqual(fallback['request']['op'], 'status')
        self.assertTrue(fallback['request']['nativeInputEvidence'])
        self.assertEqual(fallback['expected']['storage'], snapshot['storage'])
        self.assertEqual(snapshot['mode'], 'paused' if paused else 'unbound')
        if paused:
            self.assertEqual(snapshot['checkpoint']['details'], 'omitted-bounded-result')
            self.assertFalse(snapshot['checkpoint']['canContinue'])
        full = subprocess.run([self.node, fallback['helperPath']], input=json.dumps(fallback['request']),
                              capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(full.returncode, 0, full.stderr)
        restored = json.loads(full.stdout)
        self.assertEqual(restored['epoch'], fallback['expected']['epoch'])
        self.assertEqual(restored['revision'], fallback['expected']['revision'])
        self.assertEqual(restored['storage'], fallback['expected']['storage'])
        full_evidence = restored['nativeInputEvidence']
        for key in ('state', 'reason', 'latestInputReconciled', 'latestNativeInputsComplete', 'contentCoverage'):
            self.assertEqual(evidence[key], full_evidence[key])
        self.assertFalse(evidence['latestInputReconciled'])
        self.assertEqual(len(full_evidence['pendingInputs']), 300)
        self.assertEqual(self.files(), before)
        self.assertTrue(self.manage(action='reconcile-input', epoch=snapshot['epoch'],
                                    expectedRevision=revision)['isError'])
        accepted = self.manage(action='reconcile-input', epoch=snapshot['epoch'], expectedRevision=revision,
                               evidenceCursor=full_evidence['cursor'])
        self.assertFalse(accepted['isError'], accepted)
        before = self.files()
        captured = self.native_input_preview()['nativeInputEvidence']
        self.assertEqual(captured['counts'], {'records': 301, 'pendingInputs': 0, 'enrichments': 0})
        self.assertTrue(captured['latestInputReconciled'])
        self.assertNotIn('cursor', captured)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.helper({'op': 'status'}, session=fallback['request']['session_id'])['mode'],
                         'paused' if paused else 'unbound')

    def test_native_input_reconciliation_accepts_benign_append_and_preserves_pause_basis(self):
        self.native_context()
        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        first = self.helper({'op': 'status'}, session=session)
        contract = dict(result='Original authorized contract', inputs=[], outputs=[{'path': 'report.txt'}],
                        nextAction='Create and verify report', canContinue=False)
        self.assertFalse(self.manage(action='bind', epoch=first['epoch'], expectedRevision=0, **contract)['isError'])
        self.assertFalse(self.manage(action='pause', epoch=first['epoch'], expectedRevision=1,
                                     reason='Preserve user pause')['isError'])
        receipt = next(self.state.glob('*.input.json'))
        original = json.loads(receipt.read_bytes())
        # Repeating the original text is still a distinct human input.
        self.append_native_message(text='Continue this work.', id='steering-item')
        preview = self.native_input_preview()
        evidence = preview['nativeInputEvidence']
        self.assertTrue(preview['storedInputEpochReconciled'])
        self.assertFalse(evidence['latestInputReconciled'])
        self.assertNotIn('prompt', evidence['pendingInputs'][0])
        before = self.files()
        for action in ('bind', 'pause', 'retire'):
            fields = contract if action == 'bind' else {'reason': 'Preserve pause'} if action == 'pause' else {}
            denied = self.manage(action=action, epoch=first['epoch'], expectedRevision=2, **fields)
            self.assertEqual(denied['value']['reason'], 'native-input-reconciliation-required')
            self.assertEqual(self.files(), before)
        self.append_native_message(role='assistant', text='Benign preview follow-up')
        with next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl')).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': 'response_item', 'payload': {
                'type': 'custom_tool_call_output', 'call_id': 'preview', 'output': 'Benign tool result'}})+'\n')
        reconciled = self.manage(action='reconcile-input', epoch=first['epoch'], expectedRevision=2,
                                  evidenceCursor=evidence['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        current = self.native_input_preview()
        self.assertNotEqual(current['epoch'], first['epoch'])
        self.assertEqual((current['revision'], current['mode']), (2, 'paused'))
        self.assertFalse(current['storedInputEpochReconciled'])
        self.assertTrue(current['nativeInputEvidence']['latestInputReconciled'])
        saved = json.loads(receipt.read_bytes())
        for key in ('hostObservation', 'nativeContextSource', 'failures'):
            self.assertEqual(saved.get(key), original.get(key))
        self.assertEqual(saved['nativeInputs'][:-1], original['nativeInputs'])
        self.assertEqual(saved['nativeInputBasis'], original['nativeInputBasis'])
        self.assertEqual(saved['nativeInputs'][-1]['nativeEvidence']['itemId'], 'steering-item')
        self.assertFalse(self.manage(action='bind', epoch=current['epoch'], expectedRevision=2,
            revisionReason='Reviewed the actual same-text steering', **contract)['isError'])
        self.automatic_capacity_retry('capacity-after-same-turn-reconcile')
        self.assertFalse(self.manage(action='bind', epoch=current['epoch'], expectedRevision=3,
            **contract)['isError'])
        self.assertEqual(self.helper({'op': 'status'}, session=session)['mode'], 'paused')

    def test_native_input_origin_host_context_and_mixed_retry_reuse_captured_prefix(self):
        self.native_context()
        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        status = self.helper({'op': 'status'}, session=session)
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
        rows.insert(2, {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer',
            'content': [{'type': 'input_text', 'text': 'Host timezone context'}]}})
        transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
        self.append_native_message(text='Reconcile the changed conditions', id='steer-before-retry')
        steering = self.native_input_preview()
        reconciled = self.manage(action='reconcile-input', epoch=status['epoch'], expectedRevision=0,
                                  evidenceCursor=steering['nativeInputEvidence']['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        status = self.helper({'op': 'status'}, session=session)
        self.automatic_capacity_retry('automatic-turn')
        self.automatic_capacity_retry('manual-turn')
        rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
        rows[-2]['payload']['turn_attribution']['turn_trigger'] = 'capacity_retry_manual'
        transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
        before = self.files()
        preview = self.native_input_preview()
        self.assertTrue(preview['nativeInputEvidence']['latestInputReconciled'])
        self.assertEqual(self.files(), before)
        result = self.manage(action='bind', epoch=status['epoch'], expectedRevision=0,
            result='Keep the authorized contract', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Create report', canContinue=True)
        self.assertFalse(result['isError'], result)

    def test_native_origin_skips_typed_ambient_before_first_hook_input(self):
        for text in ('Host page context', 'Continue this work.'):
            with self.subTest(text=text):
                if self.state.exists(): shutil.rmtree(self.state)
                self.native_context()
                meta = self.params['_meta']['x-codex-turn-metadata']
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                rows.insert(2, {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                    'id': 'initial-ambient', 'content': [{'type': 'input_text', 'text': text}],
                    'internal_chat_message_metadata_passthrough': {'turn_id': meta['turn_id'],
                        'content_item_kinds': ['additional_content.codex_apps_open_page']}}})
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                receipt = next(self.state.glob('*.input.json')); original = json.loads(receipt.read_bytes())
                preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
                self.assertEqual(evidence['state'], 'observed', evidence)
                self.assertEqual([item['itemId'] for item in evidence['pendingInputs']], ['initial-ambient'])
                reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                    evidenceCursor=evidence['cursor'])
                self.assertFalse(reconciled['isError'], reconciled)
                saved = json.loads(receipt.read_bytes())
                self.assertEqual(saved['nativeInputs'][:1], original['nativeInputs'])
                self.assertEqual(saved['promptSha256'], original['promptSha256'])
                self.assertEqual(saved['inputSource'], 'native-input-event')
                self.automatic_capacity_retry('retry-after-initial-ambient')
                bound = self.manage(action='bind', epoch=reconciled['value']['observation']['epoch'],
                    expectedRevision=0, result='Preserve actual first user input', inputs=[],
                    outputs=[{'path': 'report.txt'}], nextAction='Continue safely', canContinue=False)
                self.assertFalse(bound['isError'], bound)
                shutil.rmtree(self.state)

    def test_native_origin_skips_usage_without_hiding_input_or_control(self):
        for kind in ('count', 'usage', 'both', 'foreign-count', 'foreign-usage', 'human', 'interrupt'):
            with self.subTest(kind=kind):
                if self.state.exists(): shutil.rmtree(self.state)
                self.native_context()
                meta = self.params['_meta']['x-codex-turn-metadata']
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                count = {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': None}}
                usage = {'type': 'token_usage_record', 'payload': {'turn_id': meta['turn_id']}}
                inserts = [count] if kind == 'count' else [usage]
                if kind == 'both': inserts = [count, usage, count]
                if kind == 'foreign-count':
                    count['payload']['turn_id'] = 'foreign-turn'
                    inserts = [count]
                if kind == 'foreign-usage': usage['payload']['turn_id'] = 'foreign-turn'
                if kind == 'human':
                    inserts = [{'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                        'content': [{'type': 'input_text', 'text': 'An earlier uncaptured human input'}]}}]
                if kind == 'interrupt':
                    inserts = [{'type': 'event_msg', 'payload': {'type': 'task_interrupted'}}]
                rows[2:2] = inserts
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                before = self.files()
                preview = self.native_input_preview()
                evidence = preview['nativeInputEvidence']
                self.assertEqual(self.files(), before)
                if kind in ('count', 'usage', 'both'):
                    self.assertEqual(evidence['state'], 'observed', evidence)
                    self.assertTrue(evidence['latestNativeInputsComplete'])
                    self.automatic_capacity_retry('retry-after-usage')
                    bound = self.manage(action='bind', epoch=preview['epoch'], expectedRevision=0,
                        result='Preserve the actual input across usage records', inputs=[],
                        outputs=[{'path': 'report.txt'}], nextAction='Continue safely', canContinue=False)
                    self.assertFalse(bound['isError'], bound)
                else:
                    self.assertEqual(evidence['state'], 'unknown', evidence)
                    self.assertEqual(evidence['reason'], 'native-input-origin-unavailable')
                shutil.rmtree(self.state)

    def test_native_origin_accepts_only_bound_initial_thread_settings(self):
        for kind in ('matching', 'matching-turn', 'missing-thread', 'foreign-thread',
                     'foreign-turn', 'missing-settings', 'missing-model', 'foreign-model',
                     'foreign-cwd', 'unknown-event', 'human', 'interrupt'):
            with self.subTest(kind=kind):
                if self.state.exists(): shutil.rmtree(self.state)
                self.native_context()
                meta = self.params['_meta']['x-codex-turn-metadata']
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                # Observed CLI0.163 shape: a thread-scoped applied-settings event
                # between turn_context and the first real user input, no turn_id.
                payload = {'type': 'thread_settings_applied', 'thread_id': meta['thread_id'],
                           'thread_settings': {'model': meta['model'], 'cwd': str(self.work),
                                               'reasoning_effort': 'high'}}
                if kind == 'matching-turn': payload['turn_id'] = meta['turn_id']
                if kind == 'missing-thread': payload.pop('thread_id')
                if kind == 'foreign-thread': payload['thread_id'] = 'foreign-thread'
                if kind == 'foreign-turn': payload['turn_id'] = 'foreign-turn'
                if kind == 'missing-settings': payload.pop('thread_settings')
                if kind == 'missing-model': payload['thread_settings'].pop('model')
                if kind == 'foreign-model': payload['thread_settings']['model'] = 'foreign-model'
                if kind == 'foreign-cwd': payload['thread_settings']['cwd'] = str(self.work.parent / 'elsewhere')
                if kind == 'unknown-event': payload['type'] = 'thread_settings_unrecognized'
                inserts = [{'type': 'event_msg', 'payload': payload}]
                if kind == 'human':
                    inserts.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                        'content': [{'type': 'input_text', 'text': 'Earlier uncaptured instruction'}]}})
                if kind == 'interrupt':
                    inserts.append({'type': 'event_msg', 'payload': {'type': 'task_interrupted'}})
                rows[2:2] = inserts
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                before = self.files()
                preview = self.native_input_preview()
                evidence = preview['nativeInputEvidence']
                self.assertEqual(self.files(), before)
                if kind in ('matching', 'matching-turn'):
                    self.assertEqual(evidence['state'], 'observed', evidence)
                    self.assertTrue(evidence['latestNativeInputsComplete'])
                    payload['thread_settings']['reasoning_effort'] = 'medium'
                    transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                    changed = self.native_input_preview()['nativeInputEvidence']
                    self.assertNotEqual(changed['cursor']['signalsSha256'], evidence['cursor']['signalsSha256'])
                    rejected = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                          evidenceCursor=evidence['cursor'])
                    self.assertTrue(rejected['isError'])
                    self.assertEqual(rejected['value']['reason'], 'native-input-evidence-changed')
                    self.automatic_capacity_retry('retry-after-settings')
                    bound = self.manage(action='bind', epoch=preview['epoch'], expectedRevision=0,
                        result='Preserve input across attributable settings', inputs=[],
                        outputs=[{'path': 'report.txt'}], nextAction='Continue safely', canContinue=False)
                    self.assertFalse(bound['isError'], bound)
                else:
                    self.assertEqual((evidence['state'], evidence['reason']),
                                     ('unknown', 'native-input-origin-unavailable'))
                shutil.rmtree(self.state)

    def append_long_tail_and_repeated_context(self):
        meta = self.params['_meta']['x-codex-turn-metadata']
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        records = [
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
                'content': 'x' * (2 * 1024 * 1024)}},
            {'type': 'compacted', 'payload': {'kind': 'fixture'}},
            {'timestamp': datetime.now(timezone.utc).isoformat(),
             'type': 'turn_context', 'payload': {'turn_id': meta['turn_id'],
                'model': meta['model'], 'cwd': str(self.work)}},
        ]
        with transcript.open('a', encoding='utf-8') as stream:
            for record in records:
                stream.write(json.dumps(record) + '\n')
        self.append_context_usage(4500)
        return transcript

    def assert_latest_context(self, case):
        params = {**self.params, 'arguments': {'cwd': str(self.work),
            'includeContext': True, 'includeNativeInputs': True}}
        before = self.files()
        observed = self.inspect(params)['value']
        evidence = observed['checkpoint']['snapshot']['nativeInputEvidence']
        context = observed['context']
        self.assertEqual(self.files(), before)
        self.assertEqual(evidence['state'], 'observed', evidence)
        self.assertTrue(evidence['latestInputReconciled'])
        self.assertTrue(evidence['latestNativeInputsComplete'])
        self.assertEqual(context['state'], 'observed', context)
        return observed

    def test_same_turn_reconciliation_long_rollout_context(self):
        self.native_context()
        meta = self.params['_meta']['x-codex-turn-metadata']
        first = self.helper({'op': 'status'}, session=meta['session_id'])
        contract = dict(result='Preserve the same authorized task', inputs=[],
            outputs=[{'path': 'report.txt'}], nextAction='Continue after user resume',
            canContinue=False)
        self.assertFalse(self.manage(action='bind', epoch=first['epoch'],
            expectedRevision=0, **contract)['isError'])
        self.assertFalse(self.manage(action='pause', epoch=first['epoch'],
            expectedRevision=1, reason='User pause remains effective')['isError'])
        self.append_native_message(text='Inspect the current conditions.', id='same-turn-steer')
        pending = self.native_input_preview()
        reconciled = self.manage(action='reconcile-input', epoch=pending['epoch'],
            expectedRevision=2, evidenceCursor=pending['nativeInputEvidence']['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        self.assert_latest_context('same-turn-short-control')
        self.append_long_tail_and_repeated_context()
        saved = self.helper({'op': 'status'}, session=meta['session_id'])
        self.assertEqual(saved['mode'], 'paused')
        self.assertEqual(saved['checkpoint']['reason'], 'User pause remains effective')
        self.assert_latest_context('same-turn-long-rollout')

    def test_retained_recovery_long_rollout_context(self):
        self.native_context()
        meta = self.params['_meta']['x-codex-turn-metadata']
        session = meta['session_id']
        self.helper({'hook_event_name': 'SessionStart', 'source': 'resume'},
            session=session, hook='SessionStart')
        status = self.helper({'op': 'status'}, session=session)
        meta.update(turn_id='resume-turn', model='resumed-model')
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'timestamp': datetime.now(
                timezone.utc).isoformat(), 'type': 'turn_context',
                'payload': {'turn_id': meta['turn_id'], 'cwd': str(self.work),
                    'model': meta['model']}}) + '\n')
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Continue this work.',
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript),
            'recovery_epoch': status['epoch']}, session=session, hook='UserPromptSubmit')
        self.append_context_usage(4500)
        self.assert_latest_context('retained-recovery-short-control')
        self.append_long_tail_and_repeated_context()
        self.assert_latest_context('retained-recovery-long-rollout')

    def test_session_end_preserves_uncaptured_or_unknown_native_input(self):
        for kind in ('complete', 'pending', 'ambient', 'unsupported', 'unavailable'):
            with self.subTest(kind=kind):
                if self.state.exists(): shutil.rmtree(self.state)
                self.native_context()
                meta = self.params['_meta']['x-codex-turn-metadata']
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                if kind in ('pending', 'ambient'):
                    fields = {'id': 'uncaptured'}
                    if kind == 'ambient':
                        fields['internal_chat_message_metadata_passthrough'] = {
                            'turn_id': meta['turn_id'],
                            'content_item_kinds': ['additional_content.codex_apps_open_page']}
                    self.append_native_message(text='Actual pending source input', **fields)
                elif kind == 'unsupported':
                    self.append_native_message(content=[{'type': 'input_audio', 'data': 'unsupported'}])
                elif kind == 'unavailable':
                    transcript.unlink()
                receipt = next(self.state.glob('*.input.json'))
                before = receipt.read_bytes()
                self.assertEqual(self.helper({'hook_event_name': 'SessionEnd'},
                    session=meta['session_id'], hook='SessionEnd'), {})
                self.assertEqual(receipt.exists(), kind != 'complete')
                if receipt.exists(): self.assertEqual(receipt.read_bytes(), before)

    def test_native_origin_does_not_skip_untyped_or_foreign_first_user(self):
        for kind in ('label-only', 'wrong-turn', 'mixed-kinds', 'human'):
            with self.subTest(kind=kind):
                self.native_context()
                meta = self.params['_meta']['x-codex-turn-metadata']
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                payload = {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text',
                    'text': 'Earlier actual human' if kind == 'human' else '<external_codex_apps_open_page>{}</external_codex_apps_open_page>'}]}
                if kind in ('wrong-turn', 'mixed-kinds'):
                    payload['internal_chat_message_metadata_passthrough'] = {
                        'turn_id': 'foreign' if kind == 'wrong-turn' else meta['turn_id'],
                        'content_item_kinds': ['additional_content.codex_apps_open_page']+
                            (['unknown'] if kind == 'mixed-kinds' else [])}
                rows.insert(2, {'type': 'response_item', 'payload': payload})
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                before = self.files(); evidence = self.native_input_preview()['nativeInputEvidence']
                self.assertEqual((evidence['state'], evidence['reason']), ('unknown', 'native-input-origin-unavailable'))
                self.assertEqual(self.files(), before)
                shutil.rmtree(self.state)

    def test_native_input_reconciliation_cursor_rejects_new_input_control_and_changed_bytes(self):
        meta = self.params['_meta']['x-codex-turn-metadata']
        for change in ('human', 'old-bytes', 'control'):
            with self.subTest(change=change):
                for receipt in self.state.glob('*.input.json'):
                    receipt.unlink()
                meta['turn_id'] = 'current-turn'
                self.native_context()
                self.append_native_message(id='first-steering')
                preview = self.native_input_preview()
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                if change == 'human':
                    self.append_native_message(id='second-steering')
                elif change == 'old-bytes':
                    text = transcript.read_text(encoding='utf-8').replace('Native steering', 'Changed steering')
                    transcript.write_text(text, encoding='utf-8')
                else:
                    with transcript.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'type': 'event_msg', 'payload': {
                            'type': 'thread_settings_applied', 'thread_id': meta['thread_id']}})+'\n')
                before = self.files()
                denied = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                      evidenceCursor=preview['nativeInputEvidence']['cursor'])
                self.assertEqual(denied['value']['reason'], 'native-input-evidence-changed')
                self.assertEqual(self.files(), before)

    def test_native_input_reconciliation_holds_recovery_and_pending_attachments(self):
        meta = self.params['_meta']['x-codex-turn-metadata']
        for condition in ('needsNativeReplay', 'needsResumeReconciliation', 'interrupted', 'attachment'):
            with self.subTest(condition=condition):
                for receipt in self.state.glob('*.input.json'):
                    receipt.unlink()
                meta['turn_id'] = 'current-turn'
                self.native_context()
                transcript = self.append_native_message(id='steer')
                if condition == 'attachment':
                    rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                    rows[-1]['payload']['content'].append({'type': 'input_image', 'image_url': 'data:image/png;base64,fixture'})
                    transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                else:
                    receipt = next(self.state.glob('*.input.json'))
                    value = json.loads(receipt.read_bytes()); value[condition] = True
                    receipt.write_text(json.dumps(value), encoding='utf-8')
                preview = self.native_input_preview()
                before = self.files()
                denied = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                      evidenceCursor=preview['nativeInputEvidence']['cursor'])
                self.assertEqual(denied['value']['reason'], 'native-input-content-unsupported'
                                 if condition == 'attachment' else 'native-input-recovery-required')
                self.assertEqual(self.files(), before)
                if condition == 'attachment':
                    self.assertFalse(preview['nativeInputEvidence']['latestNativeInputsComplete'])

    def test_native_input_replay_uses_original_basis_without_new_turn_human_record(self):
        self.native_context()
        meta = self.params['_meta']['x-codex-turn-metadata']; session = meta['session_id']
        receipt = next(self.state.glob('*.input.json'))
        self.helper({'hook_event_name': 'SessionStart', 'source': 'resume'}, session=session, hook='SessionStart')
        status = self.helper({'op': 'status'}, session=session)
        # Emulate a pre-upgrade receipt: only real native input history survives.
        value = json.loads(receipt.read_bytes()); value.pop('nativeInputBasis')
        receipt.write_text(json.dumps(value), encoding='utf-8')
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        meta.update(turn_id='resume-turn', model='resumed-model')
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'type': 'turn_context',
                'payload': {'turn_id': meta['turn_id'], 'cwd': str(self.work), 'model': meta['model']}})+'\n')
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Continue this work.',
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript),
            'recovery_epoch': status['epoch']}, session=session, hook='UserPromptSubmit')
        before = self.files()
        preview = self.native_input_preview()
        self.assertFalse(preview['needsResumeReconciliation'])
        self.assertTrue(preview['nativeInputEvidence']['latestInputReconciled'], preview)
        self.assertEqual(self.files(), before)
        contract = dict(result='Retain the actual recovered contract', inputs=[], outputs=[{'path': 'report.txt'}],
                        nextAction='Create report', canContinue=True)
        bound = self.manage(action='bind', epoch=preview['epoch'], expectedRevision=0, **contract)
        self.assertFalse(bound['isError'], bound)
        self.automatic_capacity_retry('capacity-after-resume')
        self.append_context_usage(4500)
        bound = self.manage(action='bind', epoch=preview['epoch'], expectedRevision=1, **contract)
        self.assertFalse(bound['isError'], bound)
        params = {**self.params, 'arguments': {'cwd': str(self.work), 'includeContext': True}}
        observed = self.inspect(params)['value']
        self.assertEqual(observed['context']['state'], 'observed', observed)
        self.assertEqual(observed['context']['conditions']['turnId'], 'capacity-after-resume')
        params['arguments']['contextAssessment'] = self.context_assessment(observed)
        self.assertEqual(self.inspect(params)['value']['contextAssessment']['decision'], 'continue-bounded')
        self.append_native_message(text='Actual same-turn post-resume steering', id='resume-steer')
        pending = self.native_input_preview()
        self.assertFalse(pending['nativeInputEvidence']['latestInputReconciled'])
        reconciled = self.manage(action='reconcile-input', epoch=pending['epoch'], expectedRevision=2,
            evidenceCursor=pending['nativeInputEvidence']['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        saved = json.loads(receipt.read_bytes())
        self.assertEqual([item['source'] for item in saved['nativeInputs']],
                         ['native-input-event', 'retained-native-replay', 'reconciled-native-input'])
        self.automatic_capacity_retry('capacity-after-resumed-reconcile')
        self.append_context_usage(4600)
        bound = self.manage(action='bind', epoch=reconciled['value']['observation']['epoch'],
                            expectedRevision=2, **contract)
        self.assertFalse(bound['isError'], bound)
        params = {**self.params, 'arguments': {'cwd': str(self.work), 'includeContext': True}}
        observed = self.inspect(params)['value']
        self.assertEqual(observed['context']['state'], 'observed', observed)
        self.assertEqual(observed['context']['conditions']['turnId'], 'capacity-after-resumed-reconcile')
        params['arguments']['contextAssessment'] = self.context_assessment(observed)
        self.assertEqual(self.inspect(params)['value']['contextAssessment']['decision'], 'continue-bounded')
        meta['turn_id'] = 'unproved-composer-after-recovery'
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'type': 'event_msg',
                'payload': {'type': 'task_started', 'turn_id': meta['turn_id'], 'root_turn_id': meta['turn_id'],
                    'turn_attribution': {'turn_id': meta['turn_id'], 'root_turn_id': meta['turn_id'],
                        'turn_trigger': 'composer', 'parent_turn_id': None, 'initiating_agent_path': None}}})+'\n')
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'type': 'turn_context',
                'payload': {'turn_id': meta['turn_id'], 'cwd': str(self.work), 'model': meta['model']}})+'\n')
        self.append_native_message(text='Native input cannot prove this execution transition', id='unproved-steer')
        pending = self.native_input_preview(); before = self.files()
        for action in ('bind', 'reconcile-input'):
            fields = contract if action == 'bind' else {'evidenceCursor': pending['nativeInputEvidence']['cursor']}
            rejected = self.manage(action=action, epoch=pending['epoch'], expectedRevision=3, **fields)
            self.assertEqual(rejected['value']['reason'], 'native-call-turn-conflict', rejected)
            self.assertEqual(self.files(), before)

    def test_native_input_captured_attachment_is_text_only_and_cannot_authorize_mutation(self):
        self.native_context()
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
        rows[2]['payload']['content'].extend([
            {'type': 'input_text', 'text': '<image name=[Image #1] path="C:\\fixture\\image.png">'},
            {'type': 'input_image', 'image_url': 'data:image/png;base64,fixture'},
            {'type': 'input_text', 'text': '</image>'}])
        transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
        preview = self.native_input_preview()
        evidence = preview['nativeInputEvidence']
        self.assertEqual(evidence['state'], 'observed', evidence)
        self.assertTrue(evidence['latestInputReconciled'])
        self.assertFalse(evidence['latestNativeInputsComplete'])
        before = self.files()
        rejected = self.manage(action='bind', epoch=preview['epoch'], expectedRevision=0,
            result='Text-only anchor does not verify image', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Hold attachment-dependent mutation', canContinue=False)
        self.assertEqual(rejected['value']['reason'], 'native-input-content-coverage-unknown')
        self.assertEqual(self.files(), before)

    def test_native_input_reconciliation_cannot_attest_unproved_new_execution_turn(self):
        self.native_context()
        self.append_native_message(id='steer-on-original-turn')
        meta = self.params['_meta']['x-codex-turn-metadata']
        meta['turn_id'] = 'unproved-new-turn'
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'type': 'event_msg',
                'payload': {'type': 'task_started', 'turn_id': meta['turn_id'], 'root_turn_id': meta['turn_id'],
                    'turn_attribution': {'turn_id': meta['turn_id'], 'root_turn_id': meta['turn_id'],
                        'turn_trigger': 'composer', 'parent_turn_id': None, 'initiating_agent_path': None}}})+'\n')
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'type': 'turn_context',
                'payload': {'turn_id': meta['turn_id'], 'cwd': str(self.work), 'model': meta['model']}})+'\n')
        preview = self.native_input_preview()
        before = self.files()
        rejected = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                              evidenceCursor=preview['nativeInputEvidence']['cursor'])
        self.assertEqual(rejected['value']['reason'], 'native-call-turn-conflict')
        self.assertEqual(self.files(), before)

    def test_native_input_reconciliation_final_proof_rechecks_watermark_and_late_human(self):
        meta = self.params['_meta']['x-codex-turn-metadata']
        for change in ('watermark', 'human'):
            with self.subTest(change=change):
                for file in self.state.glob('*.input*.json'):
                    file.unlink()
                meta['turn_id'] = 'current-turn'
                self.native_context()
                self.append_native_message(id='pending-steer')
                preview = self.native_input_preview()
                receipt = next(self.state.glob('*.input.json')); original = receipt.read_bytes()
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                params = {**self.params, 'name': 'manage_task_state', 'arguments': {
                    'cwd': str(self.work), 'action': 'reconcile-input', 'epoch': preview['epoch'],
                    'expectedRevision': 0, 'evidenceCursor': preview['nativeInputEvidence']['cursor']}}
                script = r"""
const fs=require('node:fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));
const open=fs.openSync,close=fs.closeSync,read=fs.readSync;const fds=new Set();let reads=0,changed=false;
fs.openSync=(file,...args)=>{const fd=open(file,...args);if(file===x.transcript)fds.add(fd);return fd;};
fs.closeSync=(fd)=>{fds.delete(fd);return close(fd);};
fs.readSync=(fd,...args)=>{
  const value=read(fd,...args);
  if(fds.has(fd)&&++reads===3){changed=true;
    if(x.change==='watermark')fs.writeFileSync(x.receipt.replace('.input.json','.input-failure.json'),
      JSON.stringify({schema:1,generation:'late-input-failure'}));
    else fs.appendFileSync(x.transcript,JSON.stringify({type:'response_item',payload:{type:'message',
      role:'user',content:[{type:'input_text',text:'Late human input'}]}})+'\n');
  }
  return value;
};
const response=require(process.argv[1]).manageTaskState(x.params);
process.stdout.write(JSON.stringify({response,changed}));
"""
                result = subprocess.run([self.node, '-e', script, str(BRIDGE)],
                    input=json.dumps(dict(params=params, receipt=str(receipt), transcript=str(transcript), change=change)),
                    capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertTrue(value['changed'])
                self.assertTrue(value['response']['isError'], value)
                self.assertEqual(receipt.read_bytes(), original)
                self.assertFalse(any(self.state.glob('*.state.json')))
                if change == 'watermark':
                    marker = receipt.with_name(receipt.name.replace('.input.json', '.input-failure.json'))
                    self.assertEqual(json.loads(marker.read_bytes())['generation'], 'late-input-failure')

    def png_fixture(self, red=0):
        import struct
        import zlib
        def chunk(kind, content):
            return struct.pack('!I', len(content)) + kind + content + struct.pack('!I', zlib.crc32(kind+content))
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + \
            chunk(b'IDAT', zlib.compress(bytes([0, red, 0, 0]))) + chunk(b'IEND', b'')

    def wrapped_png(self, data, text='Continue this work.', item_id='image-input'):
        return {'type': 'message', 'role': 'user', 'id': item_id, 'content': [
            {'type': 'input_text', 'text': text},
            {'type': 'input_text', 'text': '<image name=[Image #1] path="C:\\not-authorized\\missing.png">'},
            {'type': 'input_image', 'image_url': 'data:image/png;base64,'+base64.b64encode(data).decode()},
            {'type': 'input_text', 'text': '</image>'}]}

    def replace_anchor_png(self, data):
        self.native_context()
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
        rows[2]['payload'] = self.wrapped_png(data)
        transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
        return transcript

    def test_native_png_initial_only_enrichment_retains_hook_count_and_source_read_is_readonly(self):
        png = self.png_fixture()
        self.replace_anchor_png(png)
        receipt = next(self.state.glob('*.input.json')); original = json.loads(receipt.read_bytes())
        preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
        self.assertFalse(evidence['latestNativeInputsComplete'])
        self.assertEqual(len(evidence['enrichments']), 1)
        record = evidence['records'][0]
        image = record['parts'][2]
        self.assertEqual((image['bytes'], image['sha256']), (len(png), hashlib.sha256(png).hexdigest()))
        selector = {'evidenceCursor': evidence['cursor'], 'recordOffset': record['recordOffset'],
                    'recordSha256': record['recordSha256'], 'partIndex': 2}
        before = self.files()
        read = self.read_input(sourcePart=selector, expectedReceiptEpoch=preview['epoch'])
        self.assertFalse(read['isError'], read)
        self.assertEqual(base64.b64decode(read['imageContent']['data']), png)
        self.assertEqual(read['imageContent']['mimeType'], 'image/png')
        self.assertEqual(self.files(), before)
        selector['partIndex'] = 1
        wrapper = self.read_input(sourcePart=selector, expectedReceiptEpoch=preview['epoch'])
        self.assertEqual(wrapper['value']['input']['text'], self.wrapped_png(png)['content'][1]['text'])
        reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                  evidenceCursor=evidence['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        self.assertEqual(reconciled['value']['observation']['capturedInputs'], 0)
        saved = json.loads(receipt.read_bytes())
        self.assertEqual(saved['nativeInputs'], original['nativeInputs'])
        self.assertEqual(saved['promptSha256'], original['promptSha256'])
        self.assertEqual(saved['inputSource'], 'native-input-event')
        self.assertNotIn(base64.b64encode(png).decode(), json.dumps(saved))
        current = self.native_input_preview()
        self.assertTrue(current['nativeInputEvidence']['latestNativeInputsComplete'])
        self.assertFalse(self.manage(action='bind', epoch=current['epoch'], expectedRevision=0,
            result='Source coverage is not image understanding', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Continue under actual task authority', canContinue=False)['isError'])

    def test_native_png_pending_ambient_and_repeated_media_are_ordered_without_read_gate(self):
        first, second = self.png_fixture(), self.png_fixture(255)
        transcript = self.replace_anchor_png(first)
        self.append_native_message(text='<external_codex_apps_open_page>{}</external_codex_apps_open_page>', id='ambient')
        with transcript.open('a', encoding='utf-8') as stream:
            for item_id in ('second-image', 'repeated-image'):
                stream.write(json.dumps({'type': 'response_item', 'payload': self.wrapped_png(second, item_id=item_id)})+'\n')
        preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
        self.assertEqual([item['itemId'] for item in evidence['pendingInputs']], ['ambient', 'second-image', 'repeated-image'])
        self.assertNotEqual(evidence['records'][0]['parts'][2]['sha256'], evidence['records'][2]['parts'][2]['sha256'])
        # No read call is required: structure coverage cannot stand for understanding.
        reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                  evidenceCursor=evidence['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        receipt = next(self.state.glob('*.input.json')); saved = json.loads(receipt.read_bytes())
        self.assertEqual(len(saved['nativeInputs']), 4)
        self.assertEqual([item.get('nativeEvidence', {}).get('itemId') for item in saved['nativeInputs'][1:]],
                         ['ambient', 'second-image', 'repeated-image'])
        self.assertEqual(saved['nativeInputs'][2]['promptSha256'], saved['nativeInputs'][3]['promptSha256'])
        self.assertNotIn('data:image/', json.dumps(saved))
        self.assertNotIn('understood', json.dumps(saved))
        self.assertTrue(self.native_input_preview()['nativeInputEvidence']['latestNativeInputsComplete'])

    def test_native_png_mcp_stdio_returns_single_image_content_over_old_text_result_bound(self):
        png = self.png_fixture() + b'\x00'*(156915-len(self.png_fixture()))
        self.replace_anchor_png(png)
        preview = self.native_input_preview(); record = preview['nativeInputEvidence']['records'][0]
        args = {'cwd': str(self.work), 'expectedReceiptEpoch': preview['epoch'], 'sourcePart': {
            'evidenceCursor': preview['nativeInputEvidence']['cursor'], 'recordOffset': record['recordOffset'],
            'recordSha256': record['recordSha256'], 'partIndex': 2}}
        request = {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {
            **self.params, 'name': 'read_task_input', 'arguments': args}}
        handshake = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'isolated-image', 'version': '1'}}}
        before = self.files()
        notification = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
        result = subprocess.run([self.node, str(BRIDGE)], input=json.dumps(handshake)+'\n'+json.dumps(notification)+'\n'+json.dumps(request)+'\n',
            capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout.splitlines()[-1])['result']
        self.assertFalse(response['isError'], response)
        images = [item for item in response['content'] if item['type'] == 'image']
        self.assertEqual(len(images), 1)
        self.assertEqual(base64.b64decode(images[0]['data']), png)
        self.assertNotIn('data:image/', json.dumps(response['structuredContent']))

    def test_native_multiple_png_wrappers_enrich_one_hook_without_reordering_parts(self):
        first, second = self.png_fixture(), self.png_fixture(255)
        transcript = self.replace_anchor_png(first)
        rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
        group = self.wrapped_png(second)['content'][1:]
        group[0]['text'] = group[0]['text'].replace('Image #1', 'Image #2')
        rows[2]['payload']['content'].extend(group)
        transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
        receipt = next(self.state.glob('*.input.json')); original = json.loads(receipt.read_bytes())
        preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
        self.assertEqual(evidence['state'], 'observed', evidence)
        record = evidence['records'][0]
        self.assertEqual([part['partIndex'] for part in record['parts']], list(range(7)))
        images = [part for part in record['parts'] if part['type'] == 'image']
        self.assertEqual([part['sha256'] for part in images],
                         [hashlib.sha256(data).hexdigest() for data in (first, second)])
        for part, data in zip(images, (first, second)):
            selected = {'evidenceCursor': evidence['cursor'], 'recordOffset': record['recordOffset'],
                        'recordSha256': record['recordSha256'], 'partIndex': part['partIndex']}
            before = self.files()
            read = self.read_input(sourcePart=selected, expectedReceiptEpoch=preview['epoch'])
            self.assertFalse(read['isError'], read)
            self.assertEqual(base64.b64decode(read['imageContent']['data']), data)
            self.assertEqual(self.files(), before)
        reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                  evidenceCursor=evidence['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        saved = json.loads(receipt.read_bytes())
        self.assertEqual(saved['nativeInputs'], original['nativeInputs'])
        self.assertEqual(saved['promptSha256'], original['promptSha256'])
        self.assertNotIn('data:image/', json.dumps(saved))
        self.assertTrue(self.native_input_preview()['nativeInputEvidence']['latestNativeInputsComplete'])

    def test_native_typed_ambient_gap_keeps_hook_ledger_and_latest_input(self):
        self.native_context()
        meta = self.params['_meta']['x-codex-turn-metadata']
        prompt = 'Current real user input'
        self.append_native_message(text=prompt, id='ambient',
            internal_chat_message_metadata_passthrough={'turn_id': meta['turn_id'],
                'content_item_kinds': ['additional_content.codex_apps_open_page']})
        transcript = self.append_native_message(text=prompt, id='current-human')
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt,
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript)},
            session=meta['session_id'], hook='UserPromptSubmit')
        receipt = next(self.state.glob('*.input.json')); original = json.loads(receipt.read_bytes())
        preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
        self.assertEqual(evidence['state'], 'observed', evidence)
        self.assertEqual([record['itemId'] for record in evidence['pendingInputs']], ['ambient'])
        self.assertTrue(self.manage(action='bind', epoch=preview['epoch'], expectedRevision=0,
            result='Cannot bind past missing input', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Reconcile source', canContinue=False)['isError'])
        reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                  evidenceCursor=evidence['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        saved = json.loads(receipt.read_bytes())
        self.assertEqual(saved['nativeInputs'][:2], original['nativeInputs'])
        for field in ('promptSha256', 'turnId', 'inputSource', 'nativeInputBasis'):
            self.assertEqual(saved[field], original[field])
        self.assertEqual(saved['nativeInputs'][-1]['nativeEvidence']['itemId'], 'ambient')
        current = self.native_input_preview()['nativeInputEvidence']
        self.assertTrue(current['latestNativeInputsComplete'], current)
        self.assertEqual([record['itemId'] for record in current['records']], [None, 'ambient', 'current-human'])
        self.automatic_capacity_retry('retry-after-ambient-gap')
        current = self.native_input_preview()
        bound = self.manage(action='bind', epoch=current['epoch'], expectedRevision=0,
            result='Keep source order for retry proof', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Continue safely', canContinue=False)
        self.assertFalse(bound['isError'], bound)

    def test_native_multiple_png_second_image_must_meet_shape_and_total_budget(self):
        for kind in ('invalid-second-wrapper', 'remote-second-image', 'total-budget'):
            with self.subTest(kind=kind):
                first, second = self.png_fixture(), self.png_fixture(255)
                if kind == 'total-budget':
                    first += b'\x00'*(4*1024*1024-len(first))
                    second += b'\x00'*(4*1024*1024+1-len(second))
                transcript = self.replace_anchor_png(first)
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                group = self.wrapped_png(second)['content'][1:]
                group[0]['text'] = group[0]['text'].replace('Image #1', 'Image #2')
                if kind == 'invalid-second-wrapper': group[2]['text'] = '<invalid-close>'
                elif kind == 'remote-second-image': group[1]['image_url'] = 'https://must-not-fetch.invalid/two.png'
                rows[2]['payload']['content'].extend(group)
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                before = self.files()
                preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
                self.assertFalse(evidence.get('latestNativeInputsComplete', False))
                if evidence['state'] == 'observed':
                    self.assertFalse(evidence['records'][0]['supported'])
                    self.assertTrue(self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                        evidenceCursor=evidence['cursor'])['isError'])
                self.assertEqual(self.files(), before)
                shutil.rmtree(self.state)

    def test_native_untyped_gap_before_a_later_hook_stays_unknown(self):
        for kind in ('label-only', 'wrong-turn', 'mixed-kinds', 'changed-old-human'):
            with self.subTest(kind=kind):
                self.native_context()
                meta = self.params['_meta']['x-codex-turn-metadata']
                fields = {}
                if kind in ('wrong-turn', 'mixed-kinds'):
                    fields['internal_chat_message_metadata_passthrough'] = {
                        'turn_id': 'foreign' if kind == 'wrong-turn' else meta['turn_id'],
                        'content_item_kinds': ['additional_content.codex_apps_open_page'] +
                            (['unknown'] if kind == 'mixed-kinds' else [])}
                self.append_native_message(text='<external_codex_apps_open_page>{}</external_codex_apps_open_page>'
                    if kind != 'changed-old-human' else 'Changed old human input', **fields)
                transcript = self.append_native_message(text='Later matching text')
                self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Later matching text',
                    'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript)},
                    session=meta['session_id'], hook='UserPromptSubmit')
                before = self.files()
                evidence = self.native_input_preview()['nativeInputEvidence']
                self.assertEqual(evidence['state'], 'unknown', evidence)
                self.assertEqual(evidence['reason'], 'native-captured-input-prefix-mismatch')
                self.assertEqual(self.files(), before)
                shutil.rmtree(self.state)

    def test_native_reconciled_human_before_a_later_hook_keeps_source_binding(self):
        self.native_context()
        transcript = self.append_native_message(text='Human C', id='human-c')
        preview = self.native_input_preview()
        reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
            evidenceCursor=preview['nativeInputEvidence']['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        original = json.loads(next(self.state.glob('*.input.json')).read_bytes())
        self.append_native_message(text='Human B', id='human-b')
        meta = self.params['_meta']['x-codex-turn-metadata']
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Human B',
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript)},
            session=meta['session_id'], hook='UserPromptSubmit')
        current = self.native_input_preview(); evidence = current['nativeInputEvidence']
        self.assertTrue(evidence['latestNativeInputsComplete'], evidence)
        self.assertEqual([record['itemId'] for record in evidence['records']], [None, 'human-c', 'human-b'])
        saved = json.loads(next(self.state.glob('*.input.json')).read_bytes())
        self.assertEqual(saved['nativeInputs'][:2], original['nativeInputs'])
        self.automatic_capacity_retry('retry-after-reconciled-human')
        bound = self.manage(action='bind', epoch=current['epoch'], expectedRevision=0,
            result='Preserve reconciled human source before later Hook', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Continue without replay', canContinue=False)
        self.assertFalse(bound['isError'], bound)

    def test_native_reconciliation_cursor_survives_same_turn_hook_and_holds_changed_media(self):
        first, second = self.png_fixture(), self.png_fixture(255)
        transcript = self.replace_anchor_png(first)
        preview = self.native_input_preview()
        reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
            evidenceCursor=preview['nativeInputEvidence']['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        old = json.loads(next(self.state.glob('*.input.json')).read_bytes())
        meta = self.params['_meta']['x-codex-turn-metadata']
        self.append_native_message(text='Later Hook input', id='later-hook')
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Later Hook input',
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript)},
            session=meta['session_id'], hook='UserPromptSubmit')
        saved = json.loads(next(self.state.glob('*.input.json')).read_bytes())
        self.assertEqual(saved['nativeInputReconciliation'], old['nativeInputReconciliation'])
        transcript.write_text(transcript.read_text(encoding='utf-8').replace(
            base64.b64encode(first).decode(), base64.b64encode(second).decode()), encoding='utf-8')
        before = self.files()
        evidence = self.native_input_preview()['nativeInputEvidence']
        self.assertEqual(evidence['state'], 'unknown', evidence)
        self.assertEqual(evidence['reason'], 'native-input-evidence-changed')
        self.assertEqual(self.files(), before)
        self.assertEqual(self.files(), before)

    def test_native_png_source_selector_and_malformed_media_never_fetch_paths_or_urls(self):
        for kind in ('remote', 'invalid-base64', 'wrong-signature', 'over-budget', 'extra-human-text'):
            with self.subTest(kind=kind):
                for receipt in self.state.glob('*.input.json'):
                    receipt.unlink()
                self.native_context()
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                payload = self.wrapped_png(self.png_fixture(), text='Pending screenshot')
                if kind == 'remote': payload['content'][2]['image_url'] = 'https://must-not-fetch.invalid/picture.png'
                elif kind == 'invalid-base64': payload['content'][2]['image_url'] = 'data:image/png;base64,!!!!'
                elif kind == 'wrong-signature': payload['content'][2]['image_url'] = 'data:image/png;base64,'+base64.b64encode(b'not a png').decode()
                elif kind == 'over-budget': payload['content'][2]['image_url'] = 'data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n'+b'\x00'*(8*1024*1024)).decode()
                else: payload['content'][1]['text'] = 'Actual additional user instructions'
                with transcript.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps({'type': 'response_item', 'payload': payload})+'\n')
                preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
                self.assertFalse(evidence['pendingInputs'][0]['supported'])
                record = evidence['pendingInputs'][0]; before = self.files()
                denied = self.read_input(expectedReceiptEpoch=preview['epoch'], sourcePart={
                    'evidenceCursor': evidence['cursor'], 'recordOffset': record['recordOffset'],
                    'recordSha256': record['recordSha256'], 'partIndex': 2})
                self.assertTrue(denied['isError'], denied)
                self.assertTrue(self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=0,
                                           evidenceCursor=evidence['cursor'])['isError'])
                self.assertEqual(self.files(), before)

    def test_native_png_source_read_rejects_epoch_selectors_and_source_changes(self):
        for change in ('epoch', 'index', 'hash', 'part', 'missing-cursor', 'cursor-key',
                       'old-bytes', 'new-user', 'control', 'watermark'):
            with self.subTest(change=change):
                for file in self.state.glob('*.input*.json'):
                    file.unlink()
                transcript = self.replace_anchor_png(self.png_fixture())
                preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']; record = evidence['records'][0]
                args = {'expectedReceiptEpoch': preview['epoch'], 'sourcePart': {'evidenceCursor': evidence['cursor'],
                    'recordOffset': record['recordOffset'], 'recordSha256': record['recordSha256'], 'partIndex': 2}}
                if change == 'epoch': args['expectedReceiptEpoch'] = 'different-epoch'
                elif change == 'index': args['index'] = 0
                elif change == 'hash': args['sourcePart']['recordSha256'] = '0'*64
                elif change == 'part': args['sourcePart']['partIndex'] = 8
                elif change == 'missing-cursor': del args['sourcePart']['evidenceCursor']
                elif change == 'cursor-key': args['sourcePart']['evidenceCursor']['unboundClaim'] = True
                elif change == 'old-bytes':
                    text = transcript.read_text(encoding='utf-8').replace(base64.b64encode(self.png_fixture()).decode(),
                        base64.b64encode(self.png_fixture(255)).decode())
                    transcript.write_text(text, encoding='utf-8')
                elif change == 'new-user': self.append_native_message(text='Later native input')
                elif change == 'control':
                    with transcript.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps({'type': 'event_msg', 'payload': {'type': 'thread_settings_applied'}})+'\n')
                else:
                    receipt = next(self.state.glob('*.input.json'))
                    receipt.with_name(receipt.name.replace('.input.json', '.input-failure.json')).write_text(
                        json.dumps({'schema': 1, 'generation': 'changed-watermark'}), encoding='utf-8')
                before = self.files(); rejected = self.read_input(**args)
                self.assertTrue(rejected['isError'], rejected)
                self.assertEqual(self.files(), before)
                if change in ('missing-cursor', 'cursor-key'):
                    meta = self.params['_meta']['x-codex-turn-metadata']
                    body = {'op': 'read-native-input', **args, 'nativeTurnId': meta['turn_id'],
                        'currentHost': {'threadId': meta['session_id'], 'turnId': meta['turn_id'],
                            'model': meta['model'], 'hostVersion': meta['codex_version'],
                            'sourceRef': 'codex-mcp-call:native-call-1'}, 'session_id': meta['session_id'], 'cwd': str(self.work)}
                    helper = subprocess.run([self.node, str(CHECKPOINT)], input=json.dumps(body),
                        capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
                    self.assertNotEqual(helper.returncode, 0, helper.stdout)
                    self.assertIn('invalid-native-source-selection', helper.stderr)
                    self.assertEqual(self.files(), before)

    def test_native_png_result_derivation_rechecks_same_source_before_bind_reconcile_or_read(self):
        for operation in ('bind', 'reconcile-input', 'source-read'):
            with self.subTest(operation=operation):
                for file in self.state.glob('*.json'):
                    file.unlink()
                transcript = self.replace_anchor_png(self.png_fixture())
                preview = self.native_input_preview()
                if operation == 'bind':
                    self.assertFalse(self.manage(action='reconcile-input', epoch=preview['epoch'],
                        expectedRevision=0, evidenceCursor=preview['nativeInputEvidence']['cursor'])['isError'])
                    preview = self.native_input_preview()
                record = preview['nativeInputEvidence']['records'][0]
                arguments = {'cwd': str(self.work)}
                if operation == 'source-read':
                    arguments.update(expectedReceiptEpoch=preview['epoch'], sourcePart={
                        'evidenceCursor': preview['nativeInputEvidence']['cursor'],
                        'recordOffset': record['recordOffset'], 'recordSha256': record['recordSha256'], 'partIndex': 2})
                else:
                    arguments.update(action=operation, epoch=preview['epoch'], expectedRevision=0)
                    if operation == 'reconcile-input':
                        arguments['evidenceCursor'] = preview['nativeInputEvidence']['cursor']
                    else:
                        arguments.update(result='Bind only the actual complete source snapshot', inputs=[],
                            outputs=[{'path': 'report.txt'}], nextAction='Hold a later input', canContinue=False)
                params = {**self.params, 'name': 'read_task_input' if operation == 'source-read' else 'manage_task_state',
                          'arguments': arguments}
                transcript_key = transcript.relative_to(self.root).as_posix()
                before = {key: value for key, value in self.files().items() if key != transcript_key}
                script = r"""
const fs=require('node:fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));
const from=Buffer.from;let decodes=0,changed=false;
Buffer.from=(value,encoding,...rest)=>{
  const bytes=from(value,encoding,...rest);
  if(encoding==='base64'&&++decodes===2){changed=true;
    fs.appendFileSync(x.transcript,JSON.stringify({type:'response_item',payload:{type:'message',role:'user',
      content:[{type:'input_text',text:'Late native input while deriving the final snapshot'}]}})+'\n');
  }
  return bytes;
};
const response=require(process.argv[1])[x.operation==='source-read'?'readTaskInput':'manageTaskState'](x.params);
process.stdout.write(JSON.stringify({response,changed}));
"""
                result = subprocess.run([self.node, '-e', script, str(BRIDGE)],
                    input=json.dumps(dict(params=params, transcript=str(transcript), operation=operation)),
                    capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                value = json.loads(result.stdout)
                self.assertTrue(value['changed'])
                self.assertTrue(value['response']['isError'], value)
                self.assertEqual({key: value for key, value in self.files().items() if key != transcript_key}, before)
                self.assertFalse(any(self.state.glob('*.state.json')))

    def test_native_png_enrichment_preserves_pause_and_complete_mixed_retry(self):
        self.native_context(); session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        status = self.helper({'op': 'status'}, session=session)
        contract = dict(result='Retain task and pause', inputs=[], outputs=[{'path': 'report.txt'}],
                        nextAction='Wait for actual authorized continuation', canContinue=False)
        self.assertFalse(self.manage(action='bind', epoch=status['epoch'], expectedRevision=0, **contract)['isError'])
        self.assertFalse(self.manage(action='pause', epoch=status['epoch'], expectedRevision=1, reason='User paused')['isError'])
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': 'response_item', 'payload': self.wrapped_png(self.png_fixture())})+'\n')
        preview = self.native_input_preview()
        self.automatic_capacity_retry('automatic-png')
        self.automatic_capacity_retry('manual-png')
        rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
        rows[-2]['payload']['turn_attribution']['turn_trigger'] = 'capacity_retry_manual'
        transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
        # New control invalidates the old preview; use a fresh source-bound cursor.
        preview = self.native_input_preview()
        reconciled = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=2,
                                  evidenceCursor=preview['nativeInputEvidence']['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        current = self.native_input_preview()
        self.assertEqual(current['mode'], 'paused')
        self.assertFalse(self.manage(action='bind', epoch=current['epoch'], expectedRevision=2, **contract)['isError'])
        self.assertEqual(self.helper({'op': 'status'}, session=session)['mode'], 'paused')

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
                           ('nativeTurnId', 'invented'), ('currentHost', {'turnId': 'invented'}),
                           ('transcriptPath', 'invented'), ('turn_trigger', 'capacity_retry_automatic'),
                           ('result', 'foreign-to-pause')]:
            with self.subTest(field=key):
                rejected = self.manage(**base, **{key: value})
                self.assertTrue(rejected['isError'])
                self.assertEqual(rejected['value']['reason'], 'invalid-task-state-operation')
                self.assertEqual(rejected['value']['unsupportedFields'], [key] if key == 'result' else [])
                self.assertEqual(rejected['value']['unknownFieldRanges'], [] if key == 'result' else [[5, 5]])
                self.assertEqual(rejected['value']['effect'], 'not-requested')
                self.assertEqual(self.files(), before)
        invalid_binding = self.manage(action='bind', epoch=status['epoch'], expectedRevision=status['revision'],
            result='Deliver report', inputs=[], outputs=[{'path': 'report.txt', 'op': 'write'}],
            nextAction='Create report.txt', canContinue=True)
        self.assertEqual(invalid_binding['value']['reason'], 'invalid-task-state-binding')
        self.assertEqual(self.files(), before)

    def test_manage_unsupported_fields_are_action_specific_names_without_values_or_writes(self):
        status = self.receive_current_input('PRIVATE_INPUT_DO_NOT_RETURN')
        before = self.files()
        cases = {
            'bind': {'reason': 'PRIVATE_REASON', 'disposition': 'PRIVATE_DISPOSITION'},
            'pause': {'canContinue': False, 'result': 'PRIVATE_RESULT'},
            'retire': {'inputs': ['PRIVATE_PATH'], 'resumeReason': 'PRIVATE_RESUME'},
            'reconcile-input': {'reason': 'PRIVATE_REASON', 'outputs': [{'path': 'PRIVATE_PATH'}]},
        }
        for action, fields in cases.items():
            with self.subTest(action=action):
                response = self.manage(action=action, epoch=status['epoch'],
                    expectedRevision=status['revision'], **fields,
                    session_id='PRIVATE_IDENTITY', unknown={'secret': 'PRIVATE_VALUE'})
                self.assertTrue(response['isError'])
                value = response['value']
                self.assertEqual(value['reason'], 'invalid-task-state-operation')
                self.assertEqual(value['effect'], 'not-requested')
                self.assertEqual(value['unsupportedFields'], sorted(fields))
                self.assertEqual(value['unknownFieldRanges'], [[4 + len(fields), 5 + len(fields)]])
                self.assertNotIn('PRIVATE_', json.dumps(response))
                self.assertEqual(self.files(), before)

    def test_private_field_names_and_complete_wire_response_are_bounded(self):
        args = {'cwd': str(self.work), 'action': 'pause', 'epoch': 'PRIVATE_EPOCH', 'expectedRevision': 0}
        args.update({('PRIVATE_PATH_\\secret\n\"' + str(i)): 'PRIVATE_VALUE' for i in range(1000)})
        args['reason'] = 'PRIVATE_REASON'
        args['PRIVATE_TOKEN'] = 'PRIVATE_VALUE'
        messages = [
            {'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {},
                'clientInfo': {'name': 'bounds', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {**self.params, 'name': 'manage_task_state', 'arguments': args}}]
        wire = ('\n'.join(map(json.dumps, messages)) + '\n').encode()
        self.assertLess(len(wire.splitlines()[-1]), 128 * 1024)
        for bridge in (BRIDGE, ROOT / 'runtime/native-state-mcp.cjs'):
            with self.subTest(bridge=bridge):
                process = subprocess.run([self.node, str(bridge)], input=wire,
                    capture_output=True, env=self.env, cwd=self.work, timeout=10)
                self.assertEqual(process.returncode, 0, process.stderr)
                response = process.stdout.splitlines()[-1]
                self.assertLessEqual(len(response) + 1, 128 * 1024)
                self.assertNotIn(b'PRIVATE_', response)
                result = json.loads(response)['result']
                value = result['structuredContent']
                self.assertTrue(result['isError'])
                self.assertEqual(value['unsupportedFields'], [])
                self.assertEqual(value['unknownFieldRanges'], [[4, 1003], [1005, 1005]])
                self.assertEqual(json.loads(result['content'][0]['text']), value)
                self.assertEqual(value['effect'], 'not-requested')
        self.assertFalse(self.state.exists())

    def test_repository_entry_preserves_version_paths_and_transport_failure(self):
        original = BRIDGE
        try:
            # Reuse the original full protocol, relative-env and bad-frame cases
            # through the repository entry as well as the packaged entry.
            globals()['BRIDGE'] = ROOT / 'runtime/native-state-mcp.cjs'
            self.test_invalid_utf8_oversize_and_truncated_input_have_no_state_effect()
            self.test_real_stdio_negotiation_zero_id_unknown_method_and_eof()
            self.test_relative_state_override_keeps_its_startup_directory_base()
        finally:
            globals()['BRIDGE'] = original

    def test_shared_entries_keep_distinct_version_sources_and_failed_start_exit(self):
        repo = self.root / 'repo'
        (repo / 'runtime').mkdir(parents=True)
        (repo / 'product').mkdir()
        shutil.copy(ROOT / 'runtime/native-state-mcp.cjs', repo / 'runtime/native-state-mcp.cjs')
        package = repo / 'plugins/yiyuan-accord-codex'
        shutil.copytree(BRIDGE.parent.parent, package)
        development = repo / 'product/development.json'
        development.write_text(json.dumps({'delivery': {'version': 'repository-fixture'}}), encoding='utf-8')
        manifest = package / '.codex-plugin/plugin.json'
        manifest.write_text(json.dumps({'version': 'package-fixture'}), encoding='utf-8')
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-06-18', 'capabilities': {},
            'clientInfo': {'name': 'version', 'version': '1'}}}
        script = "const m=require(process.argv[1]);const r=JSON.parse(process.argv[2]);process.stdout.write(JSON.stringify(m.createHandler()(r)));"
        for entry, expected in ((repo / 'runtime/native-state-mcp.cjs', 'repository-fixture'),
                                (package / 'runtime/native-state-mcp.cjs', 'package-fixture')):
            for arguments in ([str(entry)], ['-e', script, str(entry), json.dumps(request)]):
                process = subprocess.run([self.node, *arguments], input=json.dumps(request)+'\n',
                    text=True, encoding='utf-8', capture_output=True, env=self.env, timeout=10)
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(json.loads(process.stdout)['result']['serverInfo']['version'], expected)
        development.write_text('{}', encoding='utf-8')
        process = subprocess.run([self.node, str(repo / 'runtime/native-state-mcp.cjs')],
            input=b'', capture_output=True, env=self.env, timeout=10)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(process.stdout, b'')
        self.assertIn(b'Accord native-state transport stopped;', process.stderr)

    def test_manage_other_validation_and_identity_failures_keep_their_diagnostics(self):
        base = dict(action='pause', epoch='unobserved-epoch', expectedRevision=0, reason='Pause')
        for changes, reason in (
                ({'action': 'constructor'}, 'invalid-task-state-operation'),
                ({'action': None}, 'invalid-task-state-operation'),
                ({'cwd': '.'}, 'invalid-task-state-operation'),
                ({'epoch': ''}, 'invalid-task-state-operation'),
                ({'expectedRevision': -1}, 'invalid-task-state-operation'),
                ({'reason': ''}, 'invalid-task-state-pause')):
            with self.subTest(changes=changes):
                response = self.manage(**{**base, **changes})
                self.assertTrue(response['isError'])
                self.assertEqual(response['value']['reason'], reason)
                self.assertNotIn('unsupportedFields', response['value'])
                self.assertEqual(response['value']['effect'], 'not-requested')
        self.params.pop('_meta')
        response = self.manage(**base)
        self.assertEqual(response['value']['reason'], 'native-call-metadata-unavailable')
        self.assertNotIn('unsupportedFields', response['value'])
        self.assertFalse(self.state.exists())

    def test_manage_unsupported_field_diagnostic_is_bounded_even_for_oversize_names(self):
        response = self.manage(action='pause', epoch='unobserved', expectedRevision=0,
            **{'op': 'PRIVATE_OPERATION', '\u754c' * 44000: 'PRIVATE_VALUE'})
        self.assertTrue(response['isError'])
        self.assertEqual(response['value']['reason'], 'invalid-task-state-operation')
        self.assertEqual(response['value']['effect'], 'not-requested')
        self.assertEqual(response['value']['unsupportedFields'], [])
        self.assertEqual(response['value']['unknownFieldRanges'], [[4, 5]])
        self.assertNotIn('界', json.dumps(response, ensure_ascii=False))
        self.assertLessEqual(len(json.dumps(response, ensure_ascii=False).encode('utf-8')), 128 * 1024)
        self.assertNotIn('PRIVATE_', json.dumps(response))
        self.assertFalse(self.state.exists())

    def test_manage_unsupported_fields_are_returned_over_real_stdio_without_state_effect(self):
        messages = [
            {'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {
                'protocolVersion': '2025-06-18', 'capabilities': {},
                'clientInfo': {'name': 'diagnostic-test', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        ]
        for index, action in enumerate(('bind', 'pause', 'retire', 'reconcile-input'), 1):
            messages.append({'jsonrpc': '2.0', 'id': index, 'method': 'tools/call',
                'params': {**self.params, 'name': 'manage_task_state', 'arguments': {
                    'cwd': str(self.work), 'action': action, 'epoch': 'PRIVATE_EPOCH',
                    'expectedRevision': 0, 'session_id': 'PRIVATE_IDENTITY',
                    'op': {'secret': 'PRIVATE_VALUE'}}}})
        process = self.run_wire(('\n'.join(map(json.dumps, messages)) + '\n').encode())
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stderr, b'')
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(responses), 5)
        for response in responses[1:]:
            result = response['result']
            self.assertTrue(result['isError'])
            self.assertEqual(result['structuredContent']['unsupportedFields'], [])
            self.assertEqual(result['structuredContent']['unknownFieldRanges'], [[4, 5]])
            self.assertEqual(result['structuredContent']['effect'], 'not-requested')
            self.assertEqual(json.loads(result['content'][0]['text']), result['structuredContent'])
        self.assertNotIn(b'PRIVATE_', process.stdout)
        self.assertFalse(self.state.exists())

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
            {'type': 'session_meta', 'payload': {'id': session, 'cwd': str(self.work),
                'cli_version': 'recorded-old-version', 'source': 'cli'}},
            {'type': 'turn_context', 'payload': {'turn_id': meta['turn_id'], 'model': meta['model'], 'cwd': str(self.work)}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                'content': [{'type': 'input_text', 'text': 'Continue this work.'}]}},
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

    def test_runtime_observation_keeps_startup_version_and_loaded_functions_after_retirement(self):
        cached, retired = self.root / 'identity-package', self.root / 'retired-identity-package'
        shutil.copytree(ROOT / 'plugins/yiyuan-accord-codex', cached)
        script = '''
const fs=require('node:fs'), path=require('node:path');
const x=JSON.parse(fs.readFileSync(0,'utf8'));
const modulePath=path.join(x.cached,'runtime','native-state-mcp.cjs');
const manifest=path.join(x.cached,'.codex-plugin','plugin.json');
const originalVersion=JSON.parse(fs.readFileSync(manifest,'utf8')).version;
const m=require(modulePath), h=m.createHandler();
h({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-06-18',
  capabilities:{},clientInfo:{name:'identity-fixture',version:'1'}}});
h({jsonrpc:'2.0',method:'notifications/initialized'});
const call=()=>h({jsonrpc:'2.0',id:2,method:'tools/call',params:x.params}).result.structuredContent;
const before=call();
fs.writeFileSync(manifest,JSON.stringify({version:'later-disk-version'}));
fs.renameSync(x.cached,x.retired);
const after=call();
process.stdout.write(JSON.stringify({originalVersion,before,after}));
'''
        before_files = {p.name: p.read_bytes() for p in self.state.glob("*") if p.is_file()}
        p = subprocess.run([self.node, '-e', script], input=json.dumps({
            'cached': str(cached), 'retired': str(retired), 'params': self.params}),
            capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        first, after = result['before']['runtime'], result['after']['runtime']
        self.assertEqual(first, after)
        self.assertEqual(after['serverVersion'], result['originalVersion'])
        self.assertGreater(after['processId'], 0)
        self.assertEqual(after['modulePathAtLoad'], str(cached / 'runtime/native-state-mcp.cjs'))
        self.assertEqual(set(after['functionSha256']),
            {'handleHook', 'retireFiles', 'nativeContextReader', 'inspectNativeState'})
        self.assertTrue(all(len(value) == 64 for value in after['functionSha256'].values()))
        self.assertEqual({p.name: p.read_bytes() for p in self.state.glob("*") if p.is_file()}, before_files)

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

    def test_absent_environment_selectors_preserve_unknown_without_default_state_writes(self):
        for key in ('YIYUAN_ACCORD_TASK_STATE_DIR', 'CODEX_HOME'):
            self.env.pop(key, None)
        self.params['arguments']['includeContext'] = True
        value = self.inspect()['value']
        self.assertEqual(value['checkpoint']['reason'], 'native-user-input-receipt-missing')
        self.assertEqual(value['context']['reason'], 'native-user-input-receipt-missing')
        self.assertFalse((self.root / '.yiyuan-accord').exists())
        self.assertFalse((self.root / '.codex').exists())
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
                         ['bind', 'pause', 'retire', 'reconcile-input'])
        manage_tool = rows[2]['result']['tools'][2]
        self.assertIn('For bind, explicitly provide result, inputs, outputs, nextAction and canContinue',
                      manage_tool['description'])
        for field in ('result', 'inputs', 'outputs', 'nextAction', 'canContinue'):
            self.assertIn('Required for bind',
                          manage_tool['inputSchema']['properties'][field]['description'])
        feasibility = manage_tool['inputSchema']['properties']['canContinue']['description']
        self.assertIn('never requests a turn or drives automatic execution', feasibility)
        self.assertNotIn('additional automatic continuation', feasibility)
        self.assertIn('no protected inputs', manage_tool['inputSchema']['properties']['inputs']['description'])
        self.assertIn('not inherited', manage_tool['inputSchema']['properties']['outputs']['description'])
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
        config = json.loads((package / '.mcp.json').read_text(encoding='utf-8'))
        self.assertEqual(config, {'mcpServers': {'accord-state': {'command': 'node',
            'args': ['runtime/native-state-mcp.cjs'], 'cwd': '.',
            'env_vars': ['YIYUAN_ACCORD_TASK_STATE_DIR', 'CODEX_HOME'],
            'startup_timeout_sec': 10, 'tool_timeout_sec': 10}}})
        adapter = json.loads((package / 'adapter.json').read_text(encoding='utf-8'))
        self.assertTrue(adapter['persistentProcessAdded'])
        self.assertEqual(adapter['nativeTaskStateMcp']['storage'], 'existing-task-checkpoint-only')
        script = "const a=require(process.argv[1]),b=require(process.argv[2]);process.stdout.write(JSON.stringify(['inspectNativeState','readTaskInput','manageTaskState','main','runtimeVersion'].every(k=>a[k]===b[k])));"
        process = subprocess.run([self.node, '-e', script, str(ROOT / 'runtime/native-state-mcp.cjs'),
            str(BRIDGE)], capture_output=True, text=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout, 'true')

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


def native_integration(codex, evidence, *, preapprove_owned_manage_tool=False, scoped_hook=False):
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
    # Even a lost selector must stay inside the fixture's owned default profile.
    profile = root / 'home/profile'
    profile.mkdir()
    env.update(HOME=str(profile), USERPROFILE=str(profile))
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
            namespace, name = exposed_tool(body, 'read_task_input' if scoped_hook else 'inspect_task_state')
            arguments = {'cwd':str(root/'workspace'), **({} if scoped_hook else {'includeContext':True})}
            identity = ('input_tool_call', 'native_input_call') if scoped_hook else ('state_tool_call', 'native_state_call')
        elif ordinal == 2:
            # Inspect after one completed provider reply, when native token counts exist.
            namespace, name = exposed_tool(body, 'inspect_task_state' if scoped_hook else 'manage_task_state')
            arguments = {'cwd':str(root/'workspace'), 'includeContext':True} if scoped_hook else {
                'cwd':str(root/'workspace'), 'action':'pause', 'epoch':'fixture-unobserved-receipt',
                'expectedRevision':0, 'reason':'Fixture checks missing-receipt rejection only; do not create task state.'}
            identity = ('state_tool_call', 'native_state_call') if scoped_hook else ('manage_tool_call', 'native_manage_call')
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
        extra = ['-c','features.code_mode_host=false']
        if scoped_hook:
            app = host._App(manifest, 'hook-discovery', host._argv(manifest, fixture, extra), env, deadline)
            app.initialize()
            hooks = app.rpc('hooks/list', {'cwds':[str(root/'workspace')]})
            owned = [h for h in host._hook_rows(hooks)
                if h.get('key', '').startswith('yiyuan-accord-codex@yiyuan-accord:')]
            if len(owned) != host._declared_hook_count(package):
                raise RuntimeError('owned Hook registrations differ')
            trust = {h['key']:{'enabled':True, 'trusted_hash':h['currentHash']} for h in owned}
            result['hookDiscoveryResources'] = app.close(manifest)
            if (result['hookDiscoveryResources'].get('forced')
                    or not host._released(result['hookDiscoveryResources']['after'])):
                raise RuntimeError('Hook discovery resources not naturally released')
            app = None
            extra += ['-c', 'hooks.state=' + host._toml(trust)]
            result['hookTrust'] = trust
        else:
            extra += ['-c','features.hooks=false']
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
            'ephemeral':not scoped_hook, 'sandbox':'read-only', 'approvalPolicy':'never'})
        thread = started['thread']['id']
        if started.get('sandbox', {}).get('type') != 'readOnly': raise RuntimeError('source is not read-only')
        prompt = ('Inspect this workspace state and read this current captured input. Preserve files and do not bind task state.'
            if scoped_hook else 'Inspect this workspace state and check that a state-management request with an unobserved receipt is rejected. Preserve files and do not create task state.')
        turn = app.rpc('turn/start', {'threadId':thread,
            'input':[{'type':'text','text':prompt}]})['turn']['id']
        terminal = app.wait_turn(thread, turn)
        calls = [e['params']['item'] for e in app.events if e.get('method') == 'item/completed'
            and e.get('params', {}).get('threadId') == thread
            and e.get('params', {}).get('turnId') == turn
            and e.get('params', {}).get('item', {}).get('type') == 'mcpToolCall']
        if terminal != 'completed' or len(calls) != 2: raise RuntimeError('two completed MCP calls required')
        indexed = {call.get('id'): call for call in calls}
        second_id = 'native_input_call' if scoped_hook else 'native_manage_call'
        if set(indexed) != {'native_state_call', second_id}:
            raise RuntimeError('native MCP call identities differ')
        call = indexed['native_state_call']
        reply, value = native_tool_result(call)
        if not value or call.get('status') != 'completed' or call.get('error'):
            raise RuntimeError('state tool result unavailable')
        source = value['source']
        if (source['threadId'] != thread or source['sessionTreeId'] != thread
                or source['turnId'] != turn or source['callId'] != call['id']):
            raise RuntimeError('metadata differs from native thread/turn/call receipts')
        manage_call = indexed[second_id]
        if scoped_hook:
            receipts = list((root/'state').glob('*.input.json'))
            if len(receipts) != 1: raise RuntimeError('one real scoped Hook receipt required')
            receipt = json.loads(receipts[0].read_text(encoding='utf-8'))
            snapshot = value['checkpoint'].get('snapshot', {})
            _, captured = native_tool_result(manage_call)
            transcript = Path(receipt['nativeContextSource']['transcriptPath'])
            if (value['checkpoint']['state'] != 'observed' or snapshot.get('epoch') != receipt['epoch']
                    or snapshot.get('inputReceipt', {}).get('present') is not True
                    or receipt['turnId'] != turn or receipt['promptSha256'] != hashlib.sha256(prompt.encode()).hexdigest()
                    or not captured or captured['input']['receiptEpoch'] != receipt['epoch']
                    or captured['input']['entries'][0]['text'] != prompt
                    or captured['source']['threadId'] != thread or captured['source']['turnId'] != turn
                    or not transcript.is_relative_to(root/'home/sessions') or not transcript.is_file()
                    or value.get('context', {}).get('state') != 'observed'
                    or value['context']['epoch'] != receipt['epoch']):
                raise RuntimeError('MCP did not reconcile the scoped Hook input and native context')
            host.save(root/'retained/hook-input.json', receipt)
            result['scopedHookInput'] = {'receipt':receipt, 'captured':captured, 'context':value['context']}
            manage_disposition = 'read-only-captured-input'
        else:
            if value['checkpoint'] != {'state':'unavailable','reason':'native-user-input-receipt-missing'}:
                raise RuntimeError('absent hook receipt was not preserved as unknown')
            if value.get('context', {}).get('reason') != 'native-user-input-receipt-missing':
                raise RuntimeError('optional context must preserve absent input as unknown')
            manage_disposition = native_manage_disposition(manage_call,
                preapproved=preapprove_owned_manage_tool)
        state_before = {p.name:sha(p) for p in (root/'state').iterdir()}
        if (sha(original) != manifest['protectedSha256'] or not scoped_hook and state_before
                or (profile/'.yiyuan-accord').exists() or (root/'home/.yiyuan-accord').exists()):
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
        if (sha(original) != manifest['protectedSha256']
                or {p.name:sha(p) for p in (root/'state').iterdir()} != state_before):
            raise RuntimeError('cache replacement changed original or task state')
        if len(fixture.requests) != 3 or fixture.auth_seen: raise RuntimeError('provider bounds differ')
        result.update(status='passed', threadId=thread, turnId=turn, nativeCall=call,
            nativeManageCall=manage_call, manageDisposition=manage_disposition,
            providerRequests=len(fixture.requests), sourceSettings=started,
            claimLimit='Native plugin MCP registration and declared host-approval boundary. A denied/rejected write request is neither business success nor a completed state change; no real model judgment, GUI adoption or handoff dispatch. Process-scoped fixture preapproval, when selected, is not a user permission or product default.')
        if scoped_hook:
            result['nativeInputCall'] = result.pop('nativeManageCall')
            result['claimLimit'] = 'Native Hook input and context read through the installed MCP environment whitelist; isolated profile, three fixed local provider replies, zero real model calls. No business delivery, GUI adoption or full acceptance claim.'
    except BaseException as error:
        body_failed = True
        result.update(status='failed', failure=type(error).__name__, reason=str(error))
        raise
    finally:
        _finalize_native_integration(result, app, fixture, root, host,
                                     body_failed=body_failed)
    if scoped_hook:
        if list((root/'state').iterdir()):
            result.update(status='failed', reason='native SessionEnd did not retire the scoped receipt')
            host.save(root/'result.json', result)
            raise RuntimeError(result['reason'])
        result['scopedReceiptRetired'] = True
        host.save(root/'result.json', result)
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
        parser.add_argument('--scoped-hook', action='store_true', help='verify native Hook to MCP scoped environment forwarding')
        arguments = parser.parse_args()
        native_integration(arguments.native_codex, arguments.evidence,
            preapprove_owned_manage_tool=arguments.preapprove_owned_manage_tool, scoped_hook=arguments.scoped_hook)
    else:
        unittest.main()
