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


def _start_native_mcp_turn(app, thread_id, prompt):
    # thread/start may return while plugin MCP startup is still asynchronous.
    # Consume the existing native event stream within the original owner bounds.
    deadline = min(app.work_deadline, time.monotonic() + app.request_timeout)
    index, status = 0, None
    while True:
        while index < len(app.events):
            event = app.events[index]
            index += 1
            params = event.get('params', {})
            if (event.get('method') != 'mcpServer/startupStatus/updated'
                    or params.get('threadId') != thread_id or params.get('name') != 'accord-state'):
                continue
            status = params.get('status')
            if status not in {'starting', 'ready'}:
                raise RuntimeError('installed MCP startup failed or was cancelled before the turn')
        if time.monotonic() >= deadline:
            raise TimeoutError('installed MCP startup readiness deadline exceeded')
        if status == 'ready':
            return app.rpc('turn/start', {'threadId': thread_id,
                'input': [{'type': 'text', 'text': prompt}]})['turn']['id']
        try:
            app.events.append(app._receive(deadline))
        except TimeoutError as error:
            raise TimeoutError('installed MCP startup readiness deadline exceeded') from error


class NativeMcpEventTests(unittest.TestCase):
    @staticmethod
    def startup(status, *, thread='owned-thread', server='accord-state'):
        return {'method': 'mcpServer/startupStatus/updated', 'params': {
            'threadId': thread, 'name': server, 'status': status, 'error': None}}

    def app(self, events=()):
        app = mock.Mock(events=list(events), work_deadline=150, request_timeout=30)
        app.rpc.return_value = {'turn': {'id': 'owned-turn'}}
        return app

    def test_native_mcp_turn_waits_for_delayed_owned_ready(self):
        app = self.app([self.startup('starting')])
        pending = [self.startup('ready', thread='another-thread'),
                   self.startup('ready', server='another-server'), self.startup('ready')]
        def receive(deadline):
            app.rpc.assert_not_called()
            self.assertEqual(deadline, 130)
            return pending.pop(0)
        app._receive.side_effect = receive
        with mock.patch(__name__ + '.time.monotonic', return_value=100):
            self.assertEqual(_start_native_mcp_turn(app, 'owned-thread', 'inspect'), 'owned-turn')
        self.assertEqual(pending, [])
        app.rpc.assert_called_once_with('turn/start', {'threadId': 'owned-thread',
            'input': [{'type': 'text', 'text': 'inspect'}]})

    def test_native_mcp_turn_uses_already_received_ready(self):
        app = self.app([self.startup('starting'), self.startup('ready')])
        with mock.patch(__name__ + '.time.monotonic', return_value=100):
            self.assertEqual(_start_native_mcp_turn(app, 'owned-thread', 'inspect'), 'owned-turn')
        app._receive.assert_not_called()
        app.rpc.assert_called_once()

    def test_native_mcp_startup_failure_or_timeout_never_dispatches_turn(self):
        for status in ('failed', 'cancelled', 'unknown'):
            with self.subTest(status=status):
                app = self.app([self.startup('ready'), self.startup(status)])
                with mock.patch(__name__ + '.time.monotonic', return_value=100):
                    with self.assertRaisesRegex(RuntimeError, 'MCP startup failed'):
                        _start_native_mcp_turn(app, 'owned-thread', 'inspect')
                app.rpc.assert_not_called()
        app = self.app([self.startup('starting')])
        app._receive.side_effect = TimeoutError('native receive deadline')
        with mock.patch(__name__ + '.time.monotonic', return_value=100):
            with self.assertRaisesRegex(TimeoutError, 'startup readiness deadline exceeded'):
                _start_native_mcp_turn(app, 'owned-thread', 'inspect')
        app.rpc.assert_not_called()
        expired = self.app([self.startup('ready')])
        expired.work_deadline = 90
        with mock.patch(__name__ + '.time.monotonic', return_value=100):
            with self.assertRaisesRegex(TimeoutError, 'startup readiness deadline exceeded'):
                _start_native_mcp_turn(expired, 'owned-thread', 'inspect')
        expired.rpc.assert_not_called()
        expired._receive.assert_not_called()

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
        self.assertEqual(set(self.result()['remainingResponsibilities']),
                         {'finalSourceCheck', 'ownedDirectoryCleanup'})
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
            _finalize_native_integration({'status': 'passed'}, app, self.fixture,
                                         self.root, self.host, body_failed=False, scoped_hook=True)
        self.assertEqual(self.result()['remainingResponsibilities']['sessionEndRetirement'],
                         'not-executed; actual retirement unknown')

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


class NativeIntegrationFinishTests(unittest.TestCase):
    owned_names = ('home', 'workspace', 'state', 'temp', 'marketplace')

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='native-finish-regression-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.sources = self.root / 'executed-source'
        self.sources.mkdir()
        self.source = self.sources / 'source.py'
        self.source.write_bytes(b'fixed executed source\n')
        for name in (*self.owned_names, 'retained'):
            (self.root / name).mkdir()
        self.original = self.root / 'workspace/keep.txt'
        self.original.write_bytes(b'preserve exact original\r\n')
        self.original_bytes = self.original.read_bytes()
        self.manifest = {'sources': {'source.py': self.sha(self.source)},
                         'protectedSha256': self.sha(self.original)}
        self.saved_pass_observations = []
        self.result = {'status': 'body-completed', 'providerRequests': 3,
                       'resources': {'forced': False, 'exitCode': 0,
                                     'after': {'processGroupState': 'absent'}}}
        self.host = mock.Mock(save=self.save, _remove_owned_tree=self.remove)
        patch = mock.patch.dict(globals(), ROOT=self.sources)
        patch.start()
        self.addCleanup(patch.stop)

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def save(self, path, value):
        self.assertEqual(path.parent, self.root)
        if path.name == 'result.json' and value.get('status') == 'passed':
            # A published final pass must observe all actual tail consequences.
            self.assertTrue(all(not (self.root/name).exists() for name in self.owned_names))
            self.assertEqual(self.sha(self.root/'retained/keep.txt'), self.manifest['protectedSha256'])
            self.assertEqual(self.sha(self.source), self.manifest['sources']['source.py'])
            self.saved_pass_observations.append(True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def remove(self, path):
        self.assertEqual(path.resolve().parent, self.root)
        self.assertIn(path.name, self.owned_names)
        shutil.rmtree(path)

    def finish(self):
        return _finish_native_integration(self.result, self.root, self.host,
            self.manifest, self.original, scoped_hook=False)

    def saved(self):
        return json.loads((self.root/'result.json').read_text(encoding='utf-8'))

    def assert_failed(self, exception):
        saved = self.saved()
        self.assertEqual(saved['status'], 'failed')
        self.assertEqual(saved['failure'], type(exception).__name__)
        self.assertEqual(saved['reason'], str(exception))
        self.assertIn('ownedDirectoryCleanup', saved['remainingResponsibilities'])
        self.assertNotIn('sessionEndRetirement', saved['remainingResponsibilities'])
        self.assertEqual(self.saved_pass_observations, [])
        return saved

    def test_final_source_failure_preserves_original_and_all_cleanup_responsibilities(self):
        self.source.write_bytes(b'changed after body checks\n')
        with self.assertRaises(RuntimeError) as raised:
            self.finish()
        saved = self.assert_failed(raised.exception)
        progress = saved['finalizationProgress']
        self.assertFalse(progress['sourceVerified'])
        self.assertFalse(progress['originalRetained'])
        self.assertEqual(progress['completedRemovals'], [])
        self.assertIsNone(progress['attemptedRoot'])
        self.assertEqual(self.original.read_bytes(), self.original_bytes)
        self.assertTrue(all((self.root/name).is_dir() for name in self.owned_names))
        self.assertFalse((self.root/'cleanup.json').exists())

    def test_partial_directory_cleanup_keeps_original_error_and_actual_progress(self):
        partial = self.root/'state/partially-removed.txt'
        partial.write_bytes(b'owned partial cleanup fixture')
        original_remove = self.host._remove_owned_tree

        def remove_with_partial_failure(path):
            if path.name == 'state':
                partial.unlink()  # Effects can occur before the operation raises.
                raise OSError('fixed state cleanup failure after a partial effect')
            original_remove(path)

        self.host._remove_owned_tree = remove_with_partial_failure
        with self.assertRaisesRegex(OSError, 'fixed state cleanup failure') as raised:
            self.finish()
        saved = self.assert_failed(raised.exception)
        progress = saved['finalizationProgress']
        self.assertTrue(progress['sourceVerified'])
        self.assertTrue(progress['originalRetained'])
        self.assertEqual(progress['completedRemovals'], ['home', 'workspace'])
        self.assertEqual(progress['attemptedRoot'], 'state')
        self.assertFalse((self.root/'home').exists())
        self.assertFalse((self.root/'workspace').exists())
        self.assertFalse(partial.exists())
        self.assertTrue(all((self.root/name).is_dir() for name in ('state', 'temp', 'marketplace')))
        self.assertEqual((self.root/'retained/keep.txt').read_bytes(), self.original_bytes)
        self.assertFalse((self.root/'cleanup.json').exists())

    def test_complete_real_filesystem_tail_is_saved_passed_only_after_all_checks(self):
        self.finish()
        saved = self.saved()
        self.assertEqual(saved['status'], 'passed')
        self.assertEqual(saved['providerRequests'], 3)
        self.assertEqual(self.saved_pass_observations, [True])
        progress = saved['finalizationProgress']
        self.assertTrue(progress['sourceVerified'])
        self.assertTrue(progress['originalRetained'])
        self.assertEqual(progress['completedRemovals'], list(self.owned_names))
        self.assertTrue(all(not (self.root/name).exists() for name in self.owned_names))
        self.assertEqual((self.root/'retained/keep.txt').read_bytes(), self.original_bytes)
        cleanup = json.loads((self.root/'cleanup.json').read_text(encoding='utf-8'))
        self.assertEqual(cleanup['removed'], [str(self.root/name) for name in self.owned_names])
        self.assertTrue(cleanup['originalRetained'])
        self.assertFalse(cleanup['userHomeTouched'])

    def test_original_changed_after_body_is_not_copied_as_the_protected_original(self):
        self.original.write_bytes(b'changed during natural close')
        with self.assertRaises(RuntimeError) as raised:
            self.finish()
        saved = self.assert_failed(raised.exception)
        progress = saved['finalizationProgress']
        self.assertTrue(progress['sourceVerified'])
        self.assertFalse(progress['originalRetained'])
        self.assertEqual(progress['completedRemovals'], [])
        self.assertIsNone(progress['attemptedRoot'])
        self.assertTrue(all((self.root/name).is_dir() for name in self.owned_names))
        self.assertFalse((self.root/'cleanup.json').exists())


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

    def test_captured_multipart_input_requires_parts_and_pending_skill_reconciliation(self):
        self.native_context()
        before = self.native_input_preview()
        self.assertFalse(self.manage(action='bind', epoch=before['epoch'], expectedRevision=0,
            result='Keep pending report', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Hold', canContinue=False)['isError'])
        self.assertFalse(self.manage(action='pause', epoch=before['epoch'],
            expectedRevision=1, reason='User pause')['isError'])
        meta = self.params['_meta']['x-codex-turn-metadata']
        meta['turn_id'] = 'multipart-turn'
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
        rows[1]['payload']['turn_id'] = meta['turn_id']
        parts = ['provenance\n', 'scope\n', '业务🙂']
        payload = rows[2]['payload']
        payload['content'] = [{'type': 'input_text', 'text': value} for value in parts]
        payload['internal_chat_message_metadata_passthrough'] = {
            'turn_id': meta['turn_id'], 'content_item_kinds': ['user.text'] * len(parts)}
        skill = 'Selected Skill original guidance remains a separate source.'
        rows.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
            'id': 'selected-skill', 'content': [{'type': 'input_text', 'text': skill}]}})
        def write(data):
            transcript.write_text(''.join(json.dumps(row) + '\n' for row in data), encoding='utf-8')
        write(rows)
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': ''.join(parts),
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript)},
            session=meta['session_id'], hook='UserPromptSubmit')
        current = self.native_input_preview()
        evidence = current['nativeInputEvidence']
        self.assertEqual(evidence['state'], 'observed', evidence)
        self.assertFalse(evidence['latestNativeInputsComplete'])
        self.assertEqual(len(evidence['enrichments']), 1)
        self.assertEqual(evidence['pendingInputs'][0]['itemId'], 'selected-skill')
        def selected(record, index):
            return dict(evidenceCursor=evidence['cursor'], recordOffset=record['recordOffset'],
                        recordSha256=record['recordSha256'], partIndex=index)
        frozen = self.files()
        for index, value in enumerate(parts):
            reply = self.read_input(expectedReceiptEpoch=current['epoch'],
                sourcePart=selected(evidence['records'][0], index))
            self.assertEqual(reply['value']['input']['text'], value)
        reply = self.read_input(expectedReceiptEpoch=current['epoch'],
            sourcePart=selected(evidence['pendingInputs'][0], 0))
        self.assertEqual(reply['value']['input']['text'], skill)
        self.assertEqual(frozen, self.files())
        for metadata in [{'turn_id': 'foreign'}, {'content_item_kinds': ['user.text']}]:
            with self.subTest(metadata=metadata):
                changed = json.loads(json.dumps(rows))
                changed[2]['payload']['internal_chat_message_metadata_passthrough'].update(metadata)
                write(changed)
                changed_files = self.files()
                self.assertEqual(self.native_input_preview()['nativeInputEvidence']['state'], 'unknown')
                self.assertEqual(changed_files, self.files())
        write(rows)
        changed = json.loads(json.dumps(rows))
        changed[-1]['payload']['content'][0]['text'] = 'Replaced skill text'
        write(changed)
        changed_files = self.files()
        self.assertTrue(self.read_input(expectedReceiptEpoch=current['epoch'],
            sourcePart=selected(evidence['pendingInputs'][0], 0))['isError'])
        self.assertEqual(changed_files, self.files())
        write(rows)
        changed = json.loads(json.dumps(rows))
        changed[2]['payload']['content'][0]['text'] = 'provenance'
        changed[2]['payload']['content'][1]['text'] = '\nscope\n'
        write(changed)  # Same flat text, different part boundaries and source bytes.
        changed_files = self.files()
        self.assertTrue(self.read_input(expectedReceiptEpoch=current['epoch'],
            sourcePart=selected(evidence['records'][0], 0))['isError'])
        self.assertEqual(changed_files, self.files())
        write(rows)
        reply = self.manage(action='reconcile-input', epoch=current['epoch'],
            expectedRevision=current['revision'], evidenceCursor=evidence['cursor'])
        self.assertFalse(reply['isError'], reply)
        complete = self.native_input_preview()
        self.assertTrue(complete['nativeInputEvidence']['latestNativeInputsComplete'], complete)
        self.assertEqual(complete['mode'], 'paused')
        rows.append({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
            'content': [{'type': 'input_text', 'text': 'not'}, {'type': 'input_text', 'text': 'captured'}],
            'internal_chat_message_metadata_passthrough': {'turn_id': meta['turn_id'],
                'content_item_kinds': ['user.text', 'user.text']}}})
        write(rows)
        pending = self.native_input_preview()
        self.assertFalse(pending['nativeInputEvidence']['records'][-1]['supported'])
        frozen = self.files()
        reply = self.manage(action='reconcile-input', epoch=pending['epoch'],
            expectedRevision=pending['revision'], evidenceCursor=pending['nativeInputEvidence']['cursor'])
        self.assertTrue(reply['isError'])
        self.assertEqual(frozen, self.files())
        rows.pop()
        write(rows)
        self.automatic_capacity_retry('retry-one')
        retry_skill = 'Selected Skill after retry retains its actual source.'
        self.append_native_message(text=retry_skill, id='retry-skill')
        retry = self.native_input_preview()
        reply = self.manage(action='reconcile-input', epoch=retry['epoch'],
            expectedRevision=retry['revision'], evidenceCursor=retry['nativeInputEvidence']['cursor'])
        self.assertFalse(reply['isError'], reply)
        receipt = json.loads(next(self.state.glob('*.input.json')).read_bytes())
        self.assertEqual(receipt['nativeInputReconciliation']['turnId'], 'retry-one')
        self.assertEqual(receipt['nativeInputs'][-1]['prompt'], retry_skill)
        self.automatic_capacity_retry('retry-two')
        retry = self.native_input_preview()
        self.assertTrue(retry['nativeInputEvidence']['latestNativeInputsComplete'])
        reply = self.manage(action='bind', epoch=retry['epoch'], expectedRevision=retry['revision'],
            result='Keep pending report', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Hold', canContinue=False)
        self.assertFalse(reply['isError'], reply)
        self.assertEqual(reply['value']['observation']['mode'], 'paused')

    def test_manage_rejects_corrupt_saved_checkpoint_before_any_mutation(self):
        self.native_context()
        status = self.helper({'op': 'status'},
            session=self.params['_meta']['x-codex-turn-metadata']['session_id'])
        contract = dict(result='Deliver required report', inputs=[],
            outputs=[{'path': 'report.txt'}], nextAction='Write report', canContinue=True)
        self.assertFalse(self.manage(action='bind', epoch=status['epoch'],
            expectedRevision=0, **contract)['isError'])
        state = next(self.state.glob('*.state.json'))
        damaged = json.loads(state.read_bytes())
        damaged['outputs'] = []
        state.write_text(json.dumps(damaged), encoding='utf-8')
        before = {p.name: p.read_bytes() for p in self.state.glob('*.json')}
        self.assertEqual(self.inspect()['value']['checkpoint']['reason'],
                         'invalid-recovery-checkpoint')
        for args in [dict(action='retire'), dict(action='pause', reason='Hold'),
                     dict(action='bind', **contract)]:
            with self.subTest(action=args['action']):
                for name, content in before.items():
                    (self.state / name).write_bytes(content)
                result = self.manage(epoch=status['epoch'], expectedRevision=1, **args)
                self.assertTrue(result['isError'])
                self.assertEqual(result['value']['reason'], 'invalid-recovery-checkpoint')
                self.assertEqual(before, {p.name: p.read_bytes() for p in self.state.glob('*.json')})
        self.assertFalse((self.work / 'report.txt').exists())

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

    def append_app_message_edge(self, turn, *, capacity=False, alter=None):
        meta = self.params['_meta']['x-codex-turn-metadata']
        original = meta['turn_id']
        previous_root = getattr(self, '_app_message_root', original)
        root = turn if capacity else 'sender-root-' + turn
        error = {'codex_error_info': 'server_overloaded',
                 'message': 'Selected model is at capacity. Please try a different model.'} if capacity else None
        rows = [
            {'type': 'event_msg', 'payload': {'type': 'task_complete', 'turn_id': original,
                'root_turn_id': previous_root, 'error': error}},
            {'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': turn,
                'root_turn_id': root, 'turn_attribution': {'turn_id': turn, 'root_turn_id': root,
                    'turn_trigger': 'capacity_retry_automatic' if capacity else 'app_tool_send_message',
                    'parent_turn_id': None if capacity else 'sender-turn-' + turn,
                    'initiating_agent_path': None}}},
            {'type': 'turn_context', 'payload': {'turn_id': turn, 'model': meta['model'], 'cwd': str(self.work)}},
        ]
        if not capacity:
            rows.append({'type': 'response_item', 'payload': {'type': 'function_call_output',
                'id': 'inbound-' + turn, 'namespace': 'codex_app', 'name': 'send_message_to_thread',
                'output': '<codex_delegation>\n  <source_thread_id>aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee</source_thread_id>'
                          '\n  <input>Continue the existing authorized goal.</input>\n</codex_delegation>',
                'internal_chat_message_metadata_passthrough': {'turn_id': turn}}})
        if alter:
            alter(rows)
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stamp = datetime.now(timezone.utc).isoformat()
            for row in rows:
                stream.write(json.dumps({'timestamp': stamp, **row}) + '\n')
        meta['turn_id'] = turn
        self._app_message_root = root
        self.append_context_usage(4500)
        return rows

    def app_message_contract(self):
        self.native_context()
        (self.work / 'protected.txt').write_text('Keep the original source.', encoding='utf-8')
        session = self.params['_meta']['x-codex-turn-metadata']['session_id']
        status = self.helper({'op': 'status'}, session=session)
        contract = dict(result='Retain the original authorized outcome', inputs=['protected.txt'],
            outputs=[{'path': 'report.txt'}], nextAction='Continue bounded authorized work', canContinue=True)
        bound = self.manage(action='bind', epoch=status['epoch'], expectedRevision=0, **contract)
        self.assertFalse(bound['isError'], bound)
        return session, status, contract

    def test_app_message_continuation_binds_and_observes_without_human_input_replacement(self):
        session, status, contract = self.app_message_contract()
        receipt = next(self.state.glob('*.input.json'))
        original = receipt.read_bytes()
        self.append_app_message_edge('message-turn')
        self.params['arguments'].update(includeContext=True, includeNativeInputs=True)
        inspected = self.inspect()['value']
        evidence = inspected['checkpoint']['snapshot']['nativeInputEvidence']
        self.assertTrue(evidence['latestNativeInputsComplete'])
        self.assertEqual(evidence['pendingInputs'], [])
        self.assertEqual(len(evidence['records']), 1)  # A tool record is not a human input.
        context = inspected['context']
        self.assertEqual(context['state'], 'observed', context)
        self.assertEqual(context['conditions']['turnId'], 'message-turn')
        self.assertEqual(context['lastResponseTokens'], 4500)
        response = self.manage(action='bind', epoch=status['epoch'], expectedRevision=1, **contract)
        self.assertFalse(response['isError'], response)
        current = self.helper({'op': 'status'}, session=session)
        self.assertEqual(current['revision'], 2)
        self.assertEqual(current['checkpoint']['result'], contract['result'])
        self.assertEqual(current['checkpoint']['outputs'], contract['outputs'])
        self.assertTrue(all(item['unchanged'] for item in current['inspection']['inputs']))
        self.assertEqual(receipt.read_bytes(), original)

    def test_app_message_continuation_composes_multiple_and_capacity_edges(self):
        for edges in (('tool', 'tool'), ('capacity', 'tool'), ('tool', 'capacity'),
                      ('tool', 'capacity', 'tool')):
            with self.subTest(edges=edges):
                case = NativeStateMcpTests('test_context_is_opt_in_and_current_version_comes_from_native_call')
                case.setUp()
                try:
                    session, status, contract = case.app_message_contract()
                    receipt = next(case.state.glob('*.input.json')); original = receipt.read_bytes()
                    for index, kind in enumerate(edges):
                        case.append_app_message_edge('edge-' + str(index), capacity=kind == 'capacity')
                    case.params['arguments'].update(includeContext=True, includeNativeInputs=True)
                    context = case.inspect()['value']['context']
                    self.assertEqual(context['state'], 'observed', context)
                    self.assertEqual(context['conditions']['turnId'], 'edge-' + str(len(edges) - 1))
                    result = case.manage(action='bind', epoch=status['epoch'], expectedRevision=1, **contract)
                    self.assertFalse(result['isError'], result)
                    self.assertEqual(receipt.read_bytes(), original)
                    self.assertEqual(case.helper({'op': 'status'}, session=session)['revision'], 2)
                finally:
                    case.doCleanups()

    def test_app_message_continuation_rejects_forged_or_incomplete_transport(self):
        def quoted(rows):
            rows[3] = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant',
                'content': [{'type': 'output_text', 'text': rows[3]['payload']['output']}]}}
        def duplicate(rows):
            rows.append(json.loads(json.dumps(rows[3])))
        def swapped(rows):
            rows[2], rows[3] = rows[3], rows[2]
        variants = {
            'namespace': lambda rows: rows[3]['payload'].update(namespace='functions'),
            'tool-name': lambda rows: rows[3]['payload'].update(name='exec'),
            'passthrough-turn': lambda rows: rows[3]['payload']['internal_chat_message_metadata_passthrough'].update(turn_id='foreign'),
            'missing-passthrough': lambda rows: rows[3]['payload'].pop('internal_chat_message_metadata_passthrough'),
            'missing-record-id': lambda rows: rows[3]['payload'].pop('id'),
            'trigger-only': lambda rows: rows.pop(),
            'quoted-wrapper': quoted,
            'malformed-wrapper': lambda rows: rows[3]['payload'].update(output='ordinary stdout <input>continue</input>'),
            'root-attribution': lambda rows: rows[1]['payload']['turn_attribution'].update(root_turn_id='foreign'),
            'attribution-turn': lambda rows: rows[1]['payload']['turn_attribution'].update(turn_id='foreign'),
            'parent-missing': lambda rows: rows[1]['payload']['turn_attribution'].update(parent_turn_id=None),
            'subagent': lambda rows: rows[1]['payload']['turn_attribution'].update(initiating_agent_path='/root/child'),
            'unproved-composer': lambda rows: rows[1]['payload']['turn_attribution'].update(turn_trigger='composer'),
            'context-cwd': lambda rows: rows[2]['payload'].update(cwd=str(self.root)),
            'context-model': lambda rows: rows[2]['payload'].update(model='unobserved-model'),
            'completion-root': lambda rows: rows[0]['payload'].update(root_turn_id='foreign'),
            'completion-error': lambda rows: rows[0]['payload'].update(error={'codex_error_info': 'unknown'}),
            'duplicate-message': duplicate,
            'wrong-order': swapped,
        }
        for name, alter in variants.items():
            with self.subTest(variant=name):
                case = NativeStateMcpTests('test_context_is_opt_in_and_current_version_comes_from_native_call')
                case.setUp()
                try:
                    _, status, contract = case.app_message_contract()
                    case.append_app_message_edge('message-turn', alter=alter)
                    before = case.files()
                    rejected = case.manage(action='bind', epoch=status['epoch'], expectedRevision=1, **contract)
                    self.assertTrue(rejected['isError'], rejected)
                    self.assertEqual(rejected['value']['reason'], 'native-call-turn-conflict')
                    self.assertEqual(case.files(), before)
                finally:
                    case.doCleanups()

    def test_app_message_continuation_does_not_weaken_capacity_failure_proof(self):
        _, status, contract = self.app_message_contract()
        self.append_app_message_edge('message-turn')
        self.append_app_message_edge('retry-turn', capacity=True,
            alter=lambda rows: rows[0]['payload'].update(error=None))
        before = self.files()
        rejected = self.manage(action='bind', epoch=status['epoch'], expectedRevision=1, **contract)
        self.assertTrue(rejected['isError'], rejected)
        self.assertEqual(rejected['value']['reason'], 'native-call-turn-conflict')
        self.assertEqual(self.files(), before)

    def test_app_message_continuation_preserves_pause_and_recovery_rejection(self):
        session, status, contract = self.app_message_contract()
        paused = self.manage(action='pause', epoch=status['epoch'], expectedRevision=1,
            reason='Actual user pause retained by the fixture.')
        self.assertFalse(paused['isError'], paused)
        receipt = next(self.state.glob('*.input.json')); original = receipt.read_bytes()
        self.append_app_message_edge('message-turn')
        bound = self.manage(action='bind', epoch=status['epoch'], expectedRevision=2, **contract)
        self.assertFalse(bound['isError'], bound)
        current = self.helper({'op': 'status'}, session=session)
        self.assertEqual(current['mode'], 'paused')
        self.assertEqual(current['checkpoint']['reason'], 'Actual user pause retained by the fixture.')
        self.assertEqual(receipt.read_bytes(), original)
        self.helper({'hook_event_name': 'Interrupt'}, session=session, hook='Interrupt')
        interrupted = self.helper({'op': 'status'}, session=session)
        before = self.files()
        rejected = self.manage(action='bind', epoch=interrupted['epoch'], expectedRevision=3, **contract)
        self.assertTrue(rejected['isError'], rejected)
        self.assertEqual(self.files(), before)

    def test_app_message_mixed_chain_rejects_invalid_capacity_edges_and_unread_input(self):
        variants = {
            'error-code': lambda rows: rows[0]['payload']['error'].update(codex_error_info='unknown'),
            'error-message': lambda rows: rows[0]['payload']['error'].update(message='Model busy'),
            'root': lambda rows: (rows[1]['payload'].update(root_turn_id='foreign'),
                rows[1]['payload']['turn_attribution'].update(root_turn_id='foreign')),
            'parent': lambda rows: rows[1]['payload']['turn_attribution'].update(parent_turn_id='unexpected-parent'),
            'initiating-agent': lambda rows: rows[1]['payload']['turn_attribution'].update(initiating_agent_path='/root/child'),
            'attribution-turn': lambda rows: rows[1]['payload']['turn_attribution'].update(turn_id='foreign'),
            'trigger': lambda rows: rows[1]['payload']['turn_attribution'].update(turn_trigger='unknown_retry'),
            'time-order': lambda rows: rows[1].update(timestamp='2020-01-01T00:00:00+00:00'),
            'current-context': lambda rows: rows[2]['payload'].update(model='unobserved-model'),
            'human-input': lambda rows: rows.append({'type': 'response_item', 'payload': {'type': 'message',
                'role': 'user', 'content': [{'type': 'input_text', 'text': 'Actual unreviewed input'}]}}),
            'interruption': lambda rows: rows.append({'type': 'event_msg', 'payload': {'type': 'task_interrupted'}}),
            'duplicate-turn': lambda rows: None,
        }
        for name, alter in variants.items():
            with self.subTest(variant=name):
                case = NativeStateMcpTests('test_context_is_opt_in_and_current_version_comes_from_native_call')
                case.setUp()
                try:
                    _, status, contract = case.app_message_contract()
                    case.append_app_message_edge('message-turn')
                    case.append_app_message_edge('message-turn' if name == 'duplicate-turn' else 'retry-turn',
                        capacity=True, alter=alter)
                    if name == 'human-input':
                        case.params['arguments']['includeNativeInputs'] = True
                        pending = case.inspect()['value']['checkpoint']['snapshot']['nativeInputEvidence']
                        self.assertEqual(len(pending['pendingInputs']), 1)
                    before = case.files()
                    rejected = case.manage(action='bind', epoch=status['epoch'], expectedRevision=1, **contract)
                    self.assertTrue(rejected['isError'], rejected)
                    self.assertEqual(rejected['value']['reason'], 'native-call-turn-conflict')
                    if name not in ('current-context', 'human-input', 'interruption'):
                        self.assertEqual(rejected['value']['nativeInputDiagnostic']['readerReason'],
                            'native-tool-continuation-unproven')
                    self.assertEqual(case.files(), before)
                finally:
                    case.doCleanups()

    def test_app_message_continuation_keeps_the_existing_finite_chain_limit(self):
        for count in (64, 65):
            with self.subTest(count=count):
                case = NativeStateMcpTests('test_context_is_opt_in_and_current_version_comes_from_native_call')
                case.setUp()
                try:
                    _, status, contract = case.app_message_contract()
                    for index in range(count):
                        case.append_app_message_edge('message-' + str(index))
                    before = case.files()
                    response = case.manage(action='bind', epoch=status['epoch'], expectedRevision=1, **contract)
                    self.assertEqual(response['isError'], count == 65, response)
                    if count == 65:
                        self.assertEqual(response['value']['nativeInputDiagnostic']['readerReason'],
                            'native-tool-continuation-unproven')
                        self.assertEqual(case.files(), before)
                finally:
                    case.doCleanups()

    def test_app_message_ack_is_ordinary_output_and_cannot_supply_the_inbound_edge(self):
        def ack(payload, keep_envelope=False):
            payload['call_id'] = 'local-call-id'
            if not keep_envelope:
                payload['output'] = json.dumps({'threadId': 'other-thread'})
        for ack_only, keep_envelope in ((False, False), (True, False), (True, True)):
            with self.subTest(ack_only=ack_only, keep_envelope=keep_envelope):
                case = NativeStateMcpTests('test_context_is_opt_in_and_current_version_comes_from_native_call')
                case.setUp()
                try:
                    _, status, contract = case.app_message_contract()
                    def alter(rows):
                        if ack_only:
                            ack(rows[3]['payload'], keep_envelope)
                        else:
                            ordinary = json.loads(json.dumps(rows[3])); ordinary['payload']['id'] = 'ordinary-ack'
                            ack(ordinary['payload']); rows.append(ordinary)
                    case.append_app_message_edge('message-turn', alter=alter)
                    before = case.files()
                    result = case.manage(action='bind', epoch=status['epoch'], expectedRevision=1, **contract)
                    self.assertEqual(result['isError'], ack_only, result)
                    if ack_only:
                        self.assertEqual(result['value']['reason'], 'native-call-turn-conflict')
                        self.assertEqual(case.files(), before)
                finally:
                    case.doCleanups()

    def test_app_message_records_fence_late_control_without_becoming_user_inputs(self):
        _, status, _ = self.app_message_contract()
        self.append_app_message_edge('message-turn')
        self.params['arguments']['includeNativeInputs'] = True
        snapshot = self.inspect()['value']['checkpoint']['snapshot']
        evidence = snapshot['nativeInputEvidence']
        self.assertTrue(evidence['latestNativeInputsComplete'])
        self.assertEqual(len(evidence['records']), 1)
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        late = {'type': 'response_item', 'payload': {'type': 'function_call_output',
            'id': 'late-inbound', 'namespace': 'codex_app', 'name': 'send_message_to_thread',
            'output': '<codex_delegation><source_thread_id>aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee</source_thread_id>'
                      '<input>Changed scope must be reviewed.</input></codex_delegation>',
            'internal_chat_message_metadata_passthrough': {'turn_id': 'message-turn'}}}
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), **late}) + '\n')
        before = self.files()
        rejected = self.manage(action='reconcile-input', epoch=status['epoch'], expectedRevision=1,
            evidenceCursor=evidence['cursor'])
        self.assertTrue(rejected['isError'], rejected)
        self.assertEqual(rejected['value']['reason'], 'native-input-evidence-changed')
        self.assertEqual(self.files(), before)

    def test_app_tool_cold_start_does_not_manufacture_a_human_receipt(self):
        meta = self.params['_meta']['x-codex-turn-metadata']
        session = '11111111-2222-4333-8444-555555555555'
        meta.update(thread_id=session, session_id=session, turn_id='cold-tool-turn')
        self.env['CODEX_HOME'] = str(self.root / 'codex-home')
        transcript = Path(self.env['CODEX_HOME']) / 'sessions/2026/09/20' / (
            'rollout-2026-09-20T00-00-00-' + session + '.jsonl')
        transcript.parent.mkdir(parents=True)
        rows = [
            {'type': 'session_meta', 'payload': {'id': session, 'cwd': str(self.work),
                'source': 'vscode', 'cli_version': 'observed-version'}},
            {'type': 'event_msg', 'payload': {'type': 'task_started', 'turn_id': 'cold-tool-turn',
                'root_turn_id': 'source-turn', 'turn_attribution': {'turn_id': 'cold-tool-turn',
                    'root_turn_id': 'source-turn', 'parent_turn_id': 'source-turn',
                    'initiating_agent_path': None, 'turn_trigger': 'app_tool_create_thread'}}},
            {'type': 'turn_context', 'payload': {'turn_id': 'cold-tool-turn',
                'model': meta['model'], 'cwd': str(self.work)}},
            {'type': 'response_item', 'payload': {'type': 'function_call_output', 'id': 'cold-tool-input',
                'namespace': 'codex_app', 'name': 'create_thread',
                'output': '<codex_delegation><source_thread_id>aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee</source_thread_id>'
                          '<input>Authorized task data, without a human receipt.</input></codex_delegation>',
                'internal_chat_message_metadata_passthrough': {'turn_id': 'cold-tool-turn'}}},
        ]
        stamp = datetime.now(timezone.utc).isoformat()
        transcript.write_text(''.join(json.dumps({'timestamp': stamp, **row}) + '\n' for row in rows),
            encoding='utf-8')
        before = self.files()
        result = self.manage(action='bind', epoch='unbound-tool-event', expectedRevision=0,
            result='No invented human input', inputs=[], outputs=[{'path': 'report.txt'}],
            nextAction='Keep cold-start receipt gap explicit', canContinue=False)
        self.assertTrue(result['isError'], result)
        self.assertEqual(result['value']['reason'], 'native-user-input-receipt-missing')
        self.assertEqual(self.files(), before)


    def automatic_capacity_retry(self, turn='retry-turn', trigger='capacity_retry_automatic'):
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
                    'turn_trigger': trigger,
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
        for label, change in cases:
            with self.subTest(label=label):
                f = NativeStateMcpTests(); f.setUp(); self.addCleanup(f.doCleanups)
                meta = f.params['_meta']['x-codex-turn-metadata']
                f.native_context()
                status = f.helper({'op': 'status'}, session=meta['session_id'])
                f.automatic_capacity_retry()
                transcript = next(Path(f.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                change(rows, meta)
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                before = f.files()
                response = f.manage(action='bind', epoch=status['epoch'], expectedRevision=0,
                    result='Retain original task', inputs=[], outputs=[{'path': 'report.txt'}],
                    nextAction='Create report.txt', canContinue=True)
                self.assertEqual(response['value']['reason'], 'native-call-turn-conflict', response)
                if label == 'ordinary-start':
                    self.assertEqual(response['value'].get('nativeInputDiagnostic'),
                        {'stage':'initial-validation','readerReason':'capacity-retry-start-unproven'})
                self.assertEqual(f.files(), before)

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

    def test_native_origin_preserves_bound_compaction_and_rejects_other_prefix_effects(self):
        for kind in ('matching', 'foreign-thread', 'foreign-turn', 'missing-item-id',
                     'other-item', 'human', 'interrupt'):
            with self.subTest(kind=kind):
                if self.state.exists(): shutil.rmtree(self.state)
                self.native_context()
                meta = self.params['_meta']['x-codex-turn-metadata']
                original = self.helper({'op': 'status'}, session=meta['thread_id'])
                contract = dict(result='Preserve paused work', inputs=[],
                    outputs=[{'path': 'report.txt'}], nextAction='Wait for the user', canContinue=False)
                transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                rows = [json.loads(line) for line in transcript.read_text(encoding='utf-8').splitlines()]
                payload = {'type': 'item_completed', 'thread_id': meta['thread_id'],
                    'turn_id': meta['turn_id'], 'item': {'type': 'ContextCompaction', 'id': 'compact-1'}}
                if kind == 'foreign-thread': payload['thread_id'] = 'foreign-thread'
                if kind == 'foreign-turn': payload['turn_id'] = 'foreign-turn'
                if kind == 'missing-item-id': payload['item'].pop('id')
                if kind == 'other-item': payload['item']['type'] = 'CommandExecution'
                inserts = [{'type': 'event_msg', 'payload': payload}]
                if kind == 'human': inserts.append({'type': 'response_item', 'payload': {
                    'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Earlier input'}]}})
                if kind == 'interrupt': inserts.append({'type': 'event_msg', 'payload': {'type': 'task_interrupted'}})
                rows[2:2] = inserts
                transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                before = self.files()
                preview = self.native_input_preview(); evidence = preview['nativeInputEvidence']
                self.assertEqual(self.files(), before)
                if kind == 'matching':
                    self.assertEqual(evidence['state'], 'observed', evidence)
                    self.assertTrue(evidence['latestNativeInputsComplete'])
                    self.assertFalse(self.manage(action='bind', epoch=original['epoch'],
                        expectedRevision=0, **contract)['isError'])
                    self.assertFalse(self.manage(action='pause', epoch=original['epoch'],
                        expectedRevision=1, reason='Real user pause')['isError'])
                    before = self.files()
                    rows.append({'type': 'event_msg', 'payload': {**payload,
                        'item': {**payload['item'], 'id': 'compact-2'}}})
                    transcript.write_text(''.join(json.dumps(row)+'\n' for row in rows), encoding='utf-8')
                    before = self.files()
                    changed = self.native_input_preview()['nativeInputEvidence']
                    self.assertNotEqual(changed['cursor']['signalsSha256'], evidence['cursor']['signalsSha256'])
                    rejected = self.manage(action='reconcile-input', epoch=preview['epoch'], expectedRevision=2,
                        evidenceCursor=evidence['cursor'])
                    self.assertTrue(rejected['isError'])
                    self.assertEqual(rejected['value']['reason'], 'native-input-evidence-changed')
                    self.assertEqual(self.files(), before)
                    self.automatic_capacity_retry('retry-after-compaction')
                    rebound = self.manage(action='bind', epoch=preview['epoch'], expectedRevision=2, **contract)
                    self.assertFalse(rebound['isError'], rebound)
                    self.assertEqual(self.helper({'op': 'status'}, session=meta['thread_id'])['mode'], 'paused')
                else:
                    self.assertEqual((evidence['state'], evidence['reason']),
                        ('unknown', 'native-input-origin-unavailable'))
                    rejected = self.manage(action='bind', epoch=original['epoch'], expectedRevision=0, **contract)
                    self.assertTrue(rejected['isError'])
                    self.assertEqual(self.files(), before)

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

    def test_retained_cursor_recovers_input_origin_beyond_anonymous_tail_budget(self):
        self.native_context()
        self.append_native_message(text='Preserve the original source order.', id='saved-steering')
        pending = self.native_input_preview()
        reconciled = self.manage(action='reconcile-input', epoch=pending['epoch'],
            expectedRevision=0, evidenceCursor=pending['nativeInputEvidence']['cursor'])
        self.assertFalse(reconciled['isError'], reconciled)
        receipt = next(self.state.glob('*.input.json'))
        original = receipt.read_bytes()
        for _ in range(9):
            self.append_long_tail_and_repeated_context()
        observed = self.assert_latest_context('receipt-located-origin-over-16MiB')
        evidence = observed['checkpoint']['snapshot']['nativeInputEvidence']
        self.assertGreater(evidence['cursor']['endOffset'] - evidence['cursor']['anchorOffset'],
                           16 * 1024 * 1024)
        self.assertEqual(len(evidence['records']), 2)
        self.assertEqual(observed['context']['lastResponseTokens'], 4500)
        record = evidence['records'][1]
        read = self.read_input(expectedReceiptEpoch=observed['checkpoint']['snapshot']['epoch'],
            sourcePart={'evidenceCursor': evidence['cursor'], 'recordOffset': record['recordOffset'],
                        'recordSha256': record['recordSha256'], 'partIndex': 0})
        self.assertFalse(read['isError'], read)
        self.assertEqual(read['value']['input']['text'], 'Preserve the original source order.')
        bound = self.manage(action='bind', epoch=observed['checkpoint']['snapshot']['epoch'],
            expectedRevision=0, result='Preserve source-bound work', inputs=[],
            outputs=[{'path': 'report.txt'}], nextAction='Continue bounded work', canContinue=True)
        self.assertFalse(bound['isError'], bound)
        self.assertEqual(receipt.read_bytes(), original)
        for trigger, turn in (('capacity_retry_automatic', 'auto-long'), ('capacity_retry_manual', 'manual-long')):
            self.automatic_capacity_retry(turn, trigger)
            self.append_context_usage(4600)
            current = self.assert_latest_context(trigger)
            self.assertEqual(current['context']['conditions']['turnId'], turn)
            self.assertFalse(self.manage(action='bind', epoch=current['checkpoint']['snapshot']['epoch'],
                expectedRevision=1 if trigger == 'capacity_retry_automatic' else 2,
                result='Preserve source-bound work', inputs=[], outputs=[{'path': 'report.txt'}],
                nextAction='Continue bounded work', canContinue=True)['isError'])
            self.assertEqual(receipt.read_bytes(), original)

    def test_retained_cursor_recovery_rejects_untrusted_changed_or_out_of_budget_sources(self):
        self.native_context()
        self.append_native_message(id='saved-steering')
        pending = self.native_input_preview()
        self.assertFalse(self.manage(action='reconcile-input', epoch=pending['epoch'], expectedRevision=0,
            evidenceCursor=pending['nativeInputEvidence']['cursor'])['isError'])
        receipt = next(self.state.glob('*.input.json'))
        original = receipt.read_bytes()
        for _ in range(9):
            transcript = self.append_long_tail_and_repeated_context()
        valid = self.native_input_preview()
        evidence = valid['nativeInputEvidence']; record = evidence['records'][1]
        baseline = transcript.read_bytes()
        for change in ('no-retained', 'sourceId', 'headSha256', 'anchorOffset', 'prefixSha256',
                       'signalsSha256', 'prefix-bytes', 'truncated', 'range',
                       'record', 'unterminated', 'control', 'human', 'host', 'replacement'):
            with self.subTest(change=change):
                receipt.write_bytes(original); transcript.write_bytes(baseline)
                data = json.loads(original)
                cursor = data['nativeInputReconciliation']['cursor']
                if change == 'no-retained': del data['nativeInputReconciliation']
                elif change in ('sourceId', 'headSha256', 'prefixSha256', 'signalsSha256'):
                    cursor[change] = '0' * 64
                elif change == 'anchorOffset': cursor['anchorOffset'] += 1
                elif change == 'prefix-bytes': transcript.write_bytes(baseline.replace(b'Native steering', b'Changed steering', 1))
                elif change == 'truncated': transcript.write_bytes(baseline[:cursor['endOffset'] - 1])
                elif change == 'replacement':
                    replacement = transcript.with_suffix('.replacement')
                    replacement.write_bytes(baseline); replacement.replace(transcript)
                elif change in ('range', 'record'):
                    if change == 'record': transcript.write_bytes(baseline[:cursor['endOffset']])
                    with transcript.open('ab') as stream:
                        for _ in range(15 if change == 'range' else 1):
                            stream.write(json.dumps({'type': 'response_item', 'payload': {'role': 'assistant',
                                'content': 'x' * ((1024 * 1024) if change == 'range' else 16 * 1024 * 1024)}}).encode() + b'\n')
                elif change == 'unterminated':
                    with transcript.open('ab') as stream: stream.write(b'{"partial":')
                elif change == 'control':
                    with transcript.open('ab') as stream:
                        stream.write(b'{"type":"event_msg","payload":{"type":"turn_unknown_control"}}\n')
                elif change == 'human': self.append_native_message(text='New human input')
                elif change == 'host': self.params['_meta']['x-codex-turn-metadata']['model'] = 'changed-model'
                receipt.write_text(json.dumps(data), encoding='utf-8')
                before = self.files()
                current = self.native_input_preview()['nativeInputEvidence']
                if change == 'human':
                    self.assertEqual(current['state'], 'observed', current)
                    self.assertFalse(current['latestInputReconciled'])
                else: self.assertEqual(current['state'], 'unknown', current)
                reasons = {'no-retained': 'native-input-origin-unavailable',
                    'range': 'native-input-recovery-range-exceeded', 'record': 'native-input-recovery-record-too-large',
                    'unterminated': 'unterminated-tail-record', 'control': 'native-input-control-unrecognized',
                    'host': 'native-input-current-host-conflict'}
                if change in reasons: self.assertEqual(current['reason'], reasons[change])
                denied = self.manage(action='bind', epoch=valid['epoch'], expectedRevision=0,
                    result='Keep source-bound work', inputs=[], outputs=[{'path': 'report.txt'}],
                    nextAction='Hold changed evidence', canContinue=False)
                self.assertTrue(denied['isError'], denied)
                if change in ('range', 'record'):
                    self.assertEqual(denied['value']['nativeInputDiagnostic'],
                        {'stage': 'initial-validation', 'readerReason': reasons[change]})
                # An expected cursor supplied by the caller cannot enable located recovery.
                self.assertTrue(self.read_input(expectedReceiptEpoch=valid['epoch'], sourcePart={
                    'evidenceCursor': evidence['cursor'], 'recordOffset': record['recordOffset'],
                    'recordSha256': record['recordSha256'], 'partIndex': 0})['isError'])
                self.assertEqual(self.files(), before)
                self.params['_meta']['x-codex-turn-metadata']['model'] = 'observed-model'

    def test_retained_cursor_exact_32mib_budget_measures_reads_and_locked_recheck(self):
        self.native_context()
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        lines = transcript.read_bytes().splitlines(keepends=True)
        prefix = b'{"type":"response_item","payload":{"type":"message","role":"assistant","content":"'
        suffix = b'"}}\n'
        with transcript.open('wb') as stream:
            stream.write(lines[0])
            for _ in range(3): stream.write(prefix + b'x' * (1024 * 1024) + suffix)
            stream.write(b''.join(lines[1:]))
        self.append_native_message(id='source-before-long-tail')
        pending = self.native_input_preview()
        self.assertFalse(self.manage(action='reconcile-input', epoch=pending['epoch'], expectedRevision=0,
            evidenceCursor=pending['nativeInputEvidence']['cursor'])['isError'])
        receipt = next(self.state.glob('*.input.json')); original = receipt.read_bytes()
        anchor = json.loads(original)['nativeInputReconciliation']['cursor']['anchorOffset']
        self.append_context_usage(4700)
        short_source = transcript.read_bytes()
        remaining = anchor + 32 * 1024 * 1024 - transcript.stat().st_size
        full, rest = divmod(remaining, 1024 * 1024)
        if 0 < rest < len(prefix) + len(suffix): full -= 1; rest += 1024 * 1024
        with transcript.open('ab') as stream:
            for size in [1024 * 1024] * full + ([rest] if rest else []):
                stream.write(prefix + b'x' * (size - len(prefix) - len(suffix)) + suffix)
        self.assertEqual(transcript.stat().st_size - anchor, 32 * 1024 * 1024)
        params = {**self.params, 'arguments': {'cwd': str(self.work), 'includeContext': True,
                                             'includeNativeInputs': True}}
        script = r"""
const fs=require('node:fs'),{performance}=require('node:perf_hooks');
const x=JSON.parse(fs.readFileSync(0,'utf8')),open=fs.openSync,close=fs.closeSync,read=fs.readSync;
const sources=new Map(),locks=new Map(),scans=[],holds=[];let phase='inspect',changed=false;
fs.openSync=(file,...args)=>{const fd=open(file,...args);
  if(file===x.transcript){const scan={phase,bytes:0,maxRead:0,priorReads:0,inputLockedBytes:0};sources.set(fd,scan);scans.push(scan);}
  if(file===x.stateLock||file===x.receipt+'.lock')locks.set(fd,{kind:file===x.stateLock?'state':'input',at:performance.now()});
  return fd;
};
fs.readSync=(fd,buffer,offset,length,position)=>{const n=read(fd,buffer,offset,length,position),scan=sources.get(fd);
  if(scan){scan.bytes+=n;scan.maxRead=Math.max(scan.maxRead,length);
    if(position!==0&&position<x.anchor)scan.priorReads++;
    if([...locks.values()].some(lock=>lock.kind==='input'))scan.inputLockedBytes+=n;
  }return n;
};
fs.closeSync=fd=>{if(locks.has(fd)){const lock=locks.get(fd);holds.push({kind:lock.kind,ms:performance.now()-lock.at});locks.delete(fd);}
  const source=sources.delete(fd),result=close(fd);
  if(source&&x.reader&&!changed){changed=true;fs.appendFileSync(x.transcript,'{"type":"response_item","payload":{"type":"reasoning"}}\n');}return result;};
const bridge=require(process.argv[1]),start=performance.now(),meta=x.params._meta['x-codex-turn-metadata'];
const inspected=x.reader?require(x.reader).inspectNativeInputs({transcriptPath:x.transcript,sessionId:meta.session_id,
  turnId:meta.turn_id,cwd:x.params.arguments.cwd},{retainedCursor:JSON.parse(fs.readFileSync(x.receipt)).nativeInputReconciliation.cursor})
  :bridge.inspectNativeState(x.params);
const inspectMs=performance.now()-start;phase='bind';
const bound=x.reader?null:bridge.manageTaskState({...x.params,name:'manage_task_state',arguments:{cwd:x.params.arguments.cwd,
  action:'bind',epoch:x.epoch,expectedRevision:0,result:'Retain exact-budget source',inputs:[],outputs:[{path:'report.txt'}],
  nextAction:'Continue bounded work',canContinue:true}});
process.stdout.write(JSON.stringify({inspected,bound,scans,holds,inspectMs,bindMs:performance.now()-start-inspectMs,
  memory:process.memoryUsage(),maxRssKiB:process.resourceUsage().maxRSS,changed}));
"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE)], input=json.dumps({
            'params': params, 'transcript': str(transcript), 'receipt': str(receipt), 'anchor': anchor,
            'stateLock': str(receipt).replace('.input.json', '.lock'), 'epoch': json.loads(original)['epoch']}),
            capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertFalse(result['inspected']['isError'], result)
        self.assertFalse(result['bound']['isError'], result)
        self.assertEqual(result['inspected']['value']['context']['lastResponseTokens'], 4700)
        self.assertGreaterEqual(len(result['scans']), 4)
        for scan in result['scans']:
            self.assertEqual(scan['bytes'], 32 * 1024 * 1024 + 64 * 1024, scan)
            self.assertLessEqual(scan['maxRead'], 1024 * 1024)
            self.assertEqual(scan['priorReads'], 0)
        self.assertTrue(any(scan['inputLockedBytes'] > 0 for scan in result['scans']))
        self.assertEqual(receipt.read_bytes(), original)
        print('retained-32mib-measurement=' + json.dumps({key: result[key] for key in (
            'scans', 'holds', 'inspectMs', 'bindMs', 'memory', 'maxRssKiB')}, separators=(',', ':')))
        budget_source = transcript.read_bytes()
        size = anchor + 32 * 1024 * 1024 - 64 * 1024 - 8192 - len(short_source)
        transcript.write_bytes(short_source + prefix + b'x' * (size - len(prefix) - len(suffix)) + suffix)
        measured = subprocess.run([self.node, '-e', script, str(BRIDGE)], input=json.dumps({
            'params': params, 'transcript': str(transcript), 'receipt': str(receipt), 'anchor': anchor,
            'stateLock': str(receipt).replace('.input.json', '.lock'), 'epoch': json.loads(original)['epoch'],
            'reader': str(ROOT / 'runtime' / 'codex-context.cjs')}),
            capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(measured.returncode, 0, measured.stderr)
        limited = json.loads(measured.stdout)
        self.assertTrue(limited['changed'], limited)
        self.assertEqual(limited['inspected']['state'], 'unknown')
        self.assertLessEqual(sum(scan['bytes'] for scan in limited['scans']), 32 * 1024 * 1024)
        transcript.write_bytes(budget_source)
        with transcript.open('ab') as stream: stream.write(b'\n')
        self.assertEqual(self.native_input_preview()['nativeInputEvidence']['reason'],
                         'native-input-recovery-range-exceeded')

    def test_retained_cursor_recovery_rechecks_read_derivation_and_commit_sources(self):
        transcript = self.replace_anchor_png(self.png_fixture())
        pending = self.native_input_preview()
        self.assertFalse(self.manage(action='reconcile-input', epoch=pending['epoch'], expectedRevision=0,
            evidenceCursor=pending['nativeInputEvidence']['cursor'])['isError'])
        receipt = next(self.state.glob('*.input.json')); original = receipt.read_bytes()
        short_source = transcript.read_bytes()
        for _ in range(9): self.append_long_tail_and_repeated_context()
        current = self.assert_latest_context('complete-media-coverage-after-retained-recovery')
        evidence = current['checkpoint']['snapshot']['nativeInputEvidence']; record = evidence['records'][0]
        image = self.read_input(expectedReceiptEpoch=json.loads(original)['epoch'], sourcePart={
            'evidenceCursor': evidence['cursor'], 'recordOffset': record['recordOffset'],
            'recordSha256': record['recordSha256'], 'partIndex': 2})
        self.assertFalse(image['isError'], image)
        self.assertEqual(base64.b64decode(image['imageContent']['data']), self.png_fixture())
        baseline = transcript.read_bytes()
        for change in ('short-read', 'append-read', 'replace-read', 'append-derive', 'append-commit',
                       'benign-close', 'user-close', 'benign-close-commit', 'user-close-commit',
                       'developer-close', 'system-close', 'pause-close', 'compact-close', 'unknown-close',
                       'task-close', 'task-close-commit'):
            with self.subTest(change=change):
                # Isolate later variants even when an earlier red assertion leaves fixture state.
                for prior_state in self.state.glob('*.state.json'):
                    prior_state.unlink()
                transcript.write_bytes(short_source if 'close' in change else baseline)
                script = r"""
const fs=require('node:fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));
const open=fs.openSync,close=fs.closeSync,read=fs.readSync,from=Buffer.from;
const sources=new Set(),inputLocks=new Set();let changed=false,decodes=0;
const inject=()=>{if(changed)return;changed=true;
  if(x.change==='replace-read'){fs.renameSync(x.transcript,x.transcript+'.old');fs.writeFileSync(x.transcript,x.baseline);}
  else if(x.change.includes('close'))fs.appendFileSync(x.transcript,x.append);
  else if(x.change!=='short-read')fs.appendFileSync(x.transcript,'\n');
};
fs.openSync=(file,...args)=>{const fd=open(file,...args);if(file===x.transcript)sources.add(fd);
  if(file===x.receipt+'.lock')inputLocks.add(fd);return fd;};
fs.closeSync=fd=>{const source=sources.delete(fd);inputLocks.delete(fd);const result=close(fd);
  if(source&&x.change.includes('close')&&(!x.change.includes('commit')||inputLocks.size))inject();return result;};
fs.readSync=(fd,...args)=>{const n=read(fd,...args);
  if(sources.has(fd)&&args[3]>=x.anchor&&!changed&&
      (['short-read','append-read','replace-read'].includes(x.change)||x.change==='append-commit'&&inputLocks.size)){
    inject();if(x.change==='short-read')return n-1;
  }return n;
};
Buffer.from=(value,encoding,...rest)=>{const bytes=from(value,encoding,...rest);
  if(x.change==='append-derive'&&encoding==='base64'&&++decodes===1)inject();return bytes;};
const response=require(process.argv[1]).manageTaskState(x.params);
if(x.change==='replace-read'){fs.unlinkSync(x.transcript);fs.renameSync(x.transcript+'.old',x.transcript);}
process.stdout.write(JSON.stringify({response,changed}));
"""
                params = {**self.params, 'name': 'manage_task_state', 'arguments': dict(cwd=str(self.work),
                    action='bind', epoch=json.loads(original)['epoch'], expectedRevision=0,
                    result='Bind only the unchanged snapshot', inputs=[], outputs=[{'path': 'report.txt'}],
                    nextAction='Hold source drift', canContinue=False)}
                request = dict(params=params, transcript=str(transcript), receipt=str(receipt), change=change,
                    anchor=evidence['cursor']['anchorOffset'], baseline='replacement fixture\n')
                kind = change.split('-')[0]
                payload = {'type': 'response_item', 'payload': {'type': 'message',
                    'role': 'assistant' if kind == 'benign' else kind,
                    'content': [{'type': 'input_text', 'text': 'Later input'}]}}
                if kind == 'task':
                    payload = {'type': 'response_item', 'payload': {'type': 'function_call_output',
                        'id': 'late-task', 'namespace': 'codex_app', 'name': 'send_message_to_thread',
                        'output': '<codex_delegation><source_thread_id>aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee</source_thread_id>'
                                  '<input>Actual late control data</input></codex_delegation>',
                        'internal_chat_message_metadata_passthrough': {
                            'turn_id': self.params['_meta']['x-codex-turn-metadata']['turn_id']}}}
                if kind in ('pause', 'compact', 'unknown'):
                    payload = {'type': {'pause': 'event_msg', 'compact': 'compacted', 'unknown': 'unknown'}[kind],
                               'payload': {'type': 'turn_aborted'}}
                request['append'] = json.dumps(payload) + '\n'
                run = subprocess.run([self.node, '-e', script, str(BRIDGE)], input=json.dumps(request),
                    capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)
                result = json.loads(run.stdout)
                self.assertTrue(result['changed'], result)
                if change.startswith('benign'):
                    self.assertFalse(result['response']['isError'], result)
                    self.assertEqual(json.loads(next(self.state.glob('*.state.json')).read_bytes())['revision'], 1)
                else:
                    self.assertTrue(result['response']['isError'], result)
                    diagnostic = result['response']['value']['nativeInputDiagnostic']
                    self.assertEqual(diagnostic['stage'], 'commit-recheck' if 'commit' in change else 'initial-validation')
                    self.assertEqual(diagnostic['readerReason'], 'transcript-read-failed' if change == 'short-read'
                        else 'transcript-path-changed-after-read' if change == 'append-derive' or 'close' in change
                        else 'transcript-changed-during-read')
                self.assertEqual(receipt.read_bytes(), original)
                if change.startswith('benign'):
                    for state in self.state.glob('*.state.json'): state.unlink()
                self.assertFalse(any(self.state.glob('*.state.json')))
                self.assertFalse(any(self.state.glob('*.lock')))

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

    def test_builtin_reader_failure_phase_survives_mcp_without_state_write(self):
        for action in ('bind', 'pause', 'retire', 'retire-unbound'):
            for phase, retry in [(p, r) for p in ('initial-validation', 'commit-recheck') for r in (False, True)]:
                with self.subTest(action=action, phase=phase, retry=retry):
                    f = NativeStateMcpTests(); f.setUp(); self.addCleanup(f.doCleanups)
                    f.native_context()
                    session = f.params['_meta']['x-codex-turn-metadata']['session_id']
                    status = f.helper({'op': 'status'}, session=session)
                    source = f.work/'source.txt'; source.write_text('Protected original', encoding='utf-8')
                    contract = dict(result='Keep the authorized task', inputs=['source.txt'],
                        outputs=[{'path':'report.txt'}], nextAction='Complete report', canContinue=True)
                    revision = 0
                    if action not in ('bind', 'retire-unbound'):
                        bound = f.manage(action='bind', epoch=status['epoch'], expectedRevision=0, **contract)
                        self.assertFalse(bound['isError'], bound); revision = 1
                    if retry: f.automatic_capacity_retry()
                    args = dict(cwd=str(f.work), action='retire' if action == 'retire-unbound' else action,
                                epoch=status['epoch'], expectedRevision=revision)
                    if action == 'bind': args.update(contract)
                    elif action == 'pause': args['reason'] = 'Explicit pause'
                    else: args.update(disposition='user-cancelled', reason='Explicit cancellation')
                    params = {**f.params, 'name':'manage_task_state', 'arguments':args}
                    transcript = next(Path(f.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
                    before = {p.name:p.read_bytes() for p in f.state.glob('*.json')}
                    if phase == 'initial-validation': transcript.unlink()
                    script = r"""
const fs=require('node:fs'),path=require('node:path');const x=JSON.parse(fs.readFileSync(0,'utf8'));
if(x.recheck&&x.unbound){const open=fs.openSync;let count=0;
 fs.openSync=(file,...args)=>{if(typeof file==='string'&&file.endsWith('.input.json.lock')&&++count===2)fs.unlinkSync(x.transcript);return open(file,...args);};
}else if(x.recheck){const read=fs.readFileSync;let changed=false;
 fs.readFileSync=(file,...args)=>{const value=read(file,...args);
  if(!changed&&typeof file==='string'&&path.resolve(file)===x.source){changed=true;fs.unlinkSync(x.transcript);}return value;};}
process.stdout.write(JSON.stringify(require(process.argv[1]).manageTaskState(x.params)));
"""
                    p = subprocess.run([f.node,'-e',script,str(BRIDGE)], input=json.dumps(dict(params=params,
                        source=str(source),transcript=str(transcript),recheck=phase=='commit-recheck',
                        unbound=action=='retire-unbound')),
                        capture_output=True,text=True,encoding='utf-8',env=f.env,timeout=10)
                    self.assertEqual(p.returncode,0,p.stderr)
                    response = json.loads(p.stdout)
                    self.assertTrue(response['isError'],response)
                    self.assertEqual(response['value']['reason'],
                        'native-call-turn-conflict' if retry else 'native-input-evidence-unavailable')
                    self.assertEqual(response['value'].get('nativeInputDiagnostic'),
                        {'stage':phase,'readerReason':'transcript-unavailable'})
                    self.assertEqual({p.name:p.read_bytes() for p in f.state.glob('*.json')},before)
                    self.assertEqual(source.read_text(encoding='utf-8'),'Protected original')

    def test_helper_retains_reason_and_safe_machine_diagnostic(self):
        self.native_context(); meta=self.params['_meta']['x-codex-turn-metadata']
        status=self.helper({'op':'status'},session=meta['session_id'])
        next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl')).unlink()
        body=dict(op='bind',session_id=meta['session_id'],cwd=str(self.work),epoch=status['epoch'],
            expectedRevision=0,nativeTurnId=meta['turn_id'],result='Retain objective',inputs=[],
            outputs=[{'path':'report.txt'}],nextAction='Continue safely',canContinue=True)
        p=subprocess.run([self.node,str(CHECKPOINT)],input=json.dumps(body),capture_output=True,
            text=True,encoding='utf-8',env=self.env,timeout=10)
        self.assertEqual(p.returncode,1)
        self.assertIn('native-input-evidence-unavailable',p.stderr)
        lines=[json.loads(line) for line in p.stderr.splitlines() if line.startswith('{')]
        self.assertEqual(lines,[{'nativeInputDiagnostic':{'stage':'initial-validation','readerReason':'transcript-unavailable'}}])

    def test_forged_error_diagnostic_is_not_projected(self):
        status=self.receive_current_input()
        params={**self.params,'name':'manage_task_state','arguments':dict(cwd=str(self.work),action='pause',
            epoch=status['epoch'],expectedRevision=0,reason='Pause')}
        script=r"""
const fs=require('node:fs');const x=JSON.parse(fs.readFileSync(0,'utf8'));
const checkpoint=require(process.argv[2]);checkpoint.operate=()=>{const e=new Error('native-input-evidence-unavailable');
 e.nativeInputDiagnostic=x.metadata;throw e;};
process.stdout.write(JSON.stringify(require(process.argv[1]).manageTaskState(x.params)));
"""
        for metadata in ({'stage':'initial-validation','readerReason':'transcript-unavailable'},
                         {'stage':'PRIVATE_PATH','readerReason':'PRIVATE_INPUT','extra':'PRIVATE_EXCEPTION'}):
            p=subprocess.run([self.node,'-e',script,str(BRIDGE),str(CHECKPOINT)],
                input=json.dumps(dict(params=params,metadata=metadata)),capture_output=True,text=True,
                encoding='utf-8',env=self.env,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            value=json.loads(p.stdout)['value']
            self.assertNotIn('nativeInputDiagnostic',value)
            self.assertNotIn('PRIVATE_',p.stdout)

    def test_unknown_reader_reason_is_fixed_not_injected_text(self):
        self.native_context(); meta=self.params['_meta']['x-codex-turn-metadata']
        status=self.helper({'op':'status'},session=meta['session_id'])
        params={**self.params,'name':'manage_task_state','arguments':dict(cwd=str(self.work),action='bind',
            epoch=status['epoch'],expectedRevision=0,result='Keep task',inputs=[],outputs=[{'path':'report.txt'}],
            nextAction='Continue',canContinue=True)}
        script=r"""
const fs=require('node:fs'),path=require('node:path');const x=JSON.parse(fs.readFileSync(0,'utf8'));
require(path.join(path.dirname(process.argv[1]),'codex-context.cjs')).inspectNativeInputs=()=>({state:'unknown',reason:x.reason});
process.stdout.write(JSON.stringify(require(process.argv[1]).manageTaskState(x.params)));
"""
        for reason in ('PRIVATE_PATH/PRIVATE_INPUT', {'exception':'PRIVATE_EXCEPTION'}, None):
            p=subprocess.run([self.node,'-e',script,str(BRIDGE)],input=json.dumps(dict(params=params,reason=reason)),
                capture_output=True,text=True,encoding='utf-8',env=self.env,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            value=json.loads(p.stdout)['value']
            self.assertEqual(value['nativeInputDiagnostic'],
                {'stage':'initial-validation','readerReason':'reader-reason-unavailable'})
            self.assertNotIn('PRIVATE_',p.stdout)

    def test_root_shim_preserves_safe_diagnostic_and_checkpoint_mirror(self):
        self.native_context(); meta=self.params['_meta']['x-codex-turn-metadata']
        status=self.helper({'op':'status'},session=meta['session_id'])
        next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl')).unlink()
        params={**self.params,'name':'manage_task_state','arguments':dict(cwd=str(self.work),action='bind',
            epoch=status['epoch'],expectedRevision=0,result='Keep task',inputs=[],outputs=[{'path':'report.txt'}],
            nextAction='Continue',canContinue=True)}
        root=BRIDGE.parents[3]
        self.assertEqual((root/'runtime/task-checkpoint.cjs').read_bytes(),CHECKPOINT.read_bytes())
        code="const fs=require('node:fs');process.stdout.write(JSON.stringify(require(process.argv[1]).manageTaskState(JSON.parse(fs.readFileSync(0,'utf8')))));"
        p=subprocess.run([self.node,'-e',code,str(root/'runtime/native-state-mcp.cjs')],input=json.dumps(params),
            capture_output=True,text=True,encoding='utf-8',env=self.env,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['value']['nativeInputDiagnostic'],
            {'stage':'initial-validation','readerReason':'transcript-unavailable'})

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
const digest=fn=>require('node:crypto').createHash('sha256').update(Function.prototype.toString.call(fn)).digest('hex');
const expectedDiagnosticFunctions={manageTaskState:digest(m.manageTaskState),
  nativeInputDiagnostic:digest(require(path.join(x.cached,'runtime','task-checkpoint.cjs')).nativeInputDiagnostic)};
h({jsonrpc:'2.0',id:1,method:'initialize',params:{protocolVersion:'2025-06-18',
  capabilities:{},clientInfo:{name:'identity-fixture',version:'1'}}});
h({jsonrpc:'2.0',method:'notifications/initialized'});
const call=()=>h({jsonrpc:'2.0',id:2,method:'tools/call',params:x.params}).result.structuredContent;
const before=call();
fs.writeFileSync(manifest,JSON.stringify({version:'later-disk-version'}));
fs.renameSync(x.cached,x.retired);
const after=call();
process.stdout.write(JSON.stringify({originalVersion,before,after,expectedDiagnosticFunctions}));
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
            {'handleHook', 'retireFiles', 'nativeContextReader', 'inspectNativeState',
             'manageTaskState', 'nativeInputDiagnostic'})
        for name, digest in result['expectedDiagnosticFunctions'].items():
            self.assertEqual(after['functionSha256'][name], digest)
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

    def start_execution_wire(self, capability_cli=None, direct=False, peer_mode=None, state_delay_ms=None):
        host = ROOT / 'tests/product/native_execution_mcp_host.cjs'
        command = [self.node, str(BRIDGE)] if direct else [self.node, str(host), str(self.root / 'native-wire.jsonl')]
        if capability_cli is not None and not direct:
            command.append(str(capability_cli))
        elif peer_mode is not None:
            command.extend(['', peer_mode])
        if state_delay_ms is not None:
            # Real checkpoint reader, with a one-shot delayed storage response.
            # No fake current-state fields and no model/native target factory.
            delayed = self.work/'delayed-state-host.cjs'
            delayed.write_text("const fs=require('node:fs');const bridge=require("+json.dumps(str(BRIDGE))+
                ");const {operate}=require("+json.dumps(str(CHECKPOINT))+
                ");let delayed=true;bridge.serve(process.stdin,process.stdout,'fixed-delayed-state',{readState(request){const result=operate(request);if(delayed){delayed=false;Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,"+
                str(state_delay_ms)+");}return result;}}).catch(()=>{process.exitCode=1;});", encoding='utf-8')
            command = [self.node, str(delayed)]
        process = subprocess.Popen(command,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding='utf-8', env=self.env, cwd=self.work)
        responses = queue.Queue()
        def receive():
            for line in process.stdout:
                responses.put(json.loads(line))
        reader = threading.Thread(target=receive, daemon=True)
        reader.start()
        def cleanup():
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
            reader.join(timeout=2)
            process.stdout.close(); process.stderr.close()
        self.addCleanup(cleanup)
        sequence = 0
        def send(method, params=None, notification=False):
            nonlocal sequence
            sequence += 1
            message = {'jsonrpc': '2.0', 'method': method}
            if not notification:
                message['id'] = sequence
            if params is not None:
                message['params'] = params
            process.stdin.write(json.dumps(message) + '\n'); process.stdin.flush()
            return sequence
        send('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                           'clientInfo': {'name': 'fixture', 'version': '1'}})
        self.assertEqual(responses.get(timeout=5)['id'], 1)
        send('notifications/initialized', notification=True)
        def call(action, **arguments):
            params = {**self.params, 'name': 'coordinate_task_execution',
                      'arguments': {'cwd': str(self.work), 'action': action, **arguments}}
            ident = send('tools/call', params)
            response = responses.get(timeout=8)
            self.assertEqual(response['id'], ident, response)
            return response['result']
        return process, responses, send, call

    def execution_contract(self):
        self.native_context()
        (self.work / 'drain.json').write_text(json.dumps({'fixture': True,
            'meaning': 'independently checked fixture has no concurrent business writer'}), encoding='utf-8')
        preview = self.native_input_preview()
        bound = self.manage(action='bind', epoch=preview['epoch'], expectedRevision=0,
            result='Review the authorized fixed candidate', inputs=['drain.json'],
            outputs=[{'path': 'review.json'}], nextAction='Perform the bounded review', canContinue=True)
        self.assertFalse(bound['isError'], bound)
        status = self.native_input_preview()
        return dict(epoch=status['epoch'], expectedRevision=status['revision'], scopeRef='fixed-review',
            model='fixture', intake='Inspect this fixed candidate.', continuation='Review one portion.',
            postRelease='Complete the remaining review.', deadlineMs=int(time.time()*1000)+20000,
            authoritySourceRef='native-user-input:fixture', quiescenceSourceRef='drain.json')

    def execution_failure_context(self, value):
        closed = value.get('nativeClosed')
        closed = closed if isinstance(closed, dict) else {}
        pending = value.get('pendingEffect')
        pending = pending if isinstance(pending, dict) else {}
        return json.dumps({'phase': value.get('phase'), 'failure': value.get('failure'),
            'busy': value.get('busy'), 'pendingKind': pending.get('kind'),
            'nativeClosed': {key: closed.get(key) for key in
                ('closed', 'forced', 'exitCode', 'exitObserved', 'closeObserved')}}, sort_keys=True)

    def execution_until(self, call, operation_id, predicate, *, timeout=8):
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            reply = call('inspect', operationId=operation_id)
            self.assertFalse(reply['isError'], reply)
            value = reply['structuredContent']
            if predicate(value):
                return value
            time.sleep(0.02)
        self.fail('fixed execution did not reach expected bounded phase: '+self.execution_failure_context(value))

    def test_execution_wire_responds_while_inventory_waits(self):
        _, responses, send, _ = self.start_execution_wire()
        inventory_id = send('tools/call', {**self.params, 'name': 'coordinate_task_execution',
            'arguments': {'cwd': str(self.work), 'action': 'inventory'}})
        ping_id = send('ping')
        self.assertEqual(responses.get(timeout=5)['id'], ping_id)
        inventory = responses.get(timeout=5)
        self.assertEqual(inventory['id'], inventory_id)
        self.assertTrue(inventory['result']['structuredContent']['fixture'])

    def delayed_capability_fixture(self):
        fixture = self.work / 'selected-cli.cjs'
        fixture.write_text("""
const fs=require('node:fs'),path=require('node:path');
if(process.argv.includes('--version')){console.log('codex-cli fixed-fixture');process.exit(0);}
const log=path.join(__dirname,'capability-close.jsonl');
const rl=require('node:readline').createInterface({input:process.stdin});
rl.on('line',line=>{const r=JSON.parse(line);
 if(r.method==='initialize')console.log(JSON.stringify({id:r.id,result:{userAgent:'fixed-fixture'}}));
 if(r.method==='skills/list')console.log(JSON.stringify({id:r.id,result:{data:[{cwd:r.params.cwds[0],skills:[],errors:[]}]}}));
});
rl.on('close',()=>{fs.appendFileSync(log,JSON.stringify({event:'eof',pid:process.pid})+'\\n');
 setTimeout(()=>{fs.appendFileSync(log,JSON.stringify({event:'natural-exit',pid:process.pid})+'\\n');},1300);});
""", encoding='utf-8')
        return fixture

    def test_mcp_capability_query_preserves_healthy_delayed_natural_close(self):
        fixture = self.delayed_capability_fixture()
        _, _, _, call = self.start_execution_wire(capability_cli=fixture)
        result = call('inventory')
        self.assertFalse(result['isError'], result)
        self.assertFalse(result['structuredContent']['process']['forced'])
        events = [json.loads(row)['event'] for row in (self.work/'capability-close.jsonl').read_text().splitlines()]
        self.assertEqual(events, ['eof', 'natural-exit'])

    def test_mcp_preserves_existing_relative_cli_selection_before_chdir(self):
        self.delayed_capability_fixture()
        self.env['CODEX_CLI_PATH'] = 'selected-cli.cjs'
        _, _, _, call = self.start_execution_wire(direct=True)
        result = call('inventory')
        self.assertFalse(result['isError'], result)
        self.assertEqual(result['structuredContent']['skills'], [])
        self.assertFalse(result['structuredContent']['process']['forced'])
        self.assertTrue((self.work/'capability-close.jsonl').exists())

    def test_execution_uses_selected_launcher_and_observed_target_cli_version(self):
        contract = self.execution_contract()
        launcher = self.work/'selected-execution.cjs'
        invocations = self.root/'launcher-invocations.jsonl'
        native_log = self.root/'selected-native.jsonl'
        launcher.write_text("""
const fs=require('node:fs');
const version=process.argv.includes('--version');
fs.appendFileSync(LOG,JSON.stringify(version?'version':'app-server')+'\\n');
if(version)console.log('codex-cli fixed-selected-version');
else {process.argv=[process.execPath,__filename,NATIVE_LOG,'normal'];require(HOST);}
""".replace('NATIVE_LOG', json.dumps(str(native_log)))
            .replace('LOG', json.dumps(str(invocations)))
            .replace('HOST', json.dumps(str(ROOT/'tests/product/external_handoff_host.cjs'))), encoding='utf-8')
        self.env['CODEX_CLI_PATH'] = launcher.name
        _, _, _, call = self.start_execution_wire(direct=True)
        operation_id = call('prepare', **contract)['structuredContent']['operationId']
        value = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        review = value['reviewRequest']
        self.assertFalse(call('review', operationId=operation_id, reviewId=review['reviewId'],
            observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-launch-plan')['isError'])
        value = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None
            and x['reviewRequest']['stage'] == 'target-created')
        evidence = call('read-evidence', operationId=operation_id,
            evidenceId=value['reviewRequest']['observationSha256'], maxChars=16000)['structuredContent']
        self.assertTrue(evidence['complete'])
        observed = json.loads(evidence['text'])
        self.assertEqual(observed['state']['connection']['hostVersion'], 'codex-cli fixed-selected-version')
        self.assertEqual([json.loads(row) for row in invocations.read_text().splitlines()], ['version', 'app-server'])
        cancelled = call('cancel', operationId=operation_id, reason='Fixed no-model probe complete')
        self.assertFalse(cancelled['isError'])
        self.assertTrue(cancelled['structuredContent']['nativeClosed']['closed'])

    def test_prepare_failure_releases_only_unregistered_owned_resources(self):
        # Real wrapper module; injected memory-only storage and dependency faults.
        script = r"""

const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),{createRequire}=require('node:module');
const file=process.argv[1],realRequire=createRequire(file),source=fs.readFileSync(file,'utf8');
(async()=>{const results=[];
for(const mode of ['open','scope','engine','close','scope-close','nonempty','remove','changed','invalid','collision']){
 let created=mode==='collision',opened=0,closed=0,removed=0,mkdir=0,changed=false,nonempty=false;
 const id='11111111-1111-4111-8111-111111111111',isOwned=p=>path.basename(p)===id;
 const boom=code=>Object.assign(Error(code),{code});
 const fakefs={existsSync:p=>isOwned(p)?created:true,realpathSync:p=>p,
  lstatSync:p=>({isDirectory:()=>true,isSymbolicLink:()=>false,dev:1n,ino:isOwned(p)&&changed?2n:1n}),
  mkdirSync:p=>{mkdir++;if(created)throw boom('EEXIST');created=true;},
  rmdirSync:(p,options)=>{if(!isOwned(p)||options!==undefined)throw boom('UNSAFE_REMOVAL');if(nonempty)throw boom('ENOTEMPTY');if(mode==='remove')throw boom('EACCES');removed++;created=false;}};
 const recorder={readScope(){throw boom(mode.startsWith('scope')?'SCOPE_BUSY':'SCOPE_NOT_FOUND');},close(){closed++;if(mode==='close'||mode==='scope-close')throw boom('CLOSE_FAILED');}};
 const sandbox={module:{exports:{}},process,Buffer,console,setTimeout,clearTimeout,
 require:name=>name==='node:fs'?fakefs:name==='node:crypto'?{...require(name),randomUUID:()=>id}:
 name==='./carrier-recorder.cjs'?{openCarrierRecorder(){opened++;if(mode==='open')throw boom('DB_OPEN_FAILED');return recorder;}}:
 name==='./external-handoff.cjs'?{createExternalHandoff(){nonempty=mode==='nonempty';changed=mode==='changed';throw boom('ENGINE_FAILED');}}:realRequire(name)};
 vm.runInNewContext(source,sandbox,{filename:file});
 const digest='a'.repeat(64),state={mode:mode==='invalid'?'paused':'active',epoch:'e',revision:1,checkpoint:{canContinue:true},
 hostObservationCurrent:true,currentInputReconciled:true,inputReceipt:{present:true},checkpointSource:{sha256:digest},
 nativeInputEvidence:{state:'observed',latestInputReconciled:true,latestNativeInputsComplete:true,pendingInputs:[]},
 inspection:{inputs:[{path:'drain.json',current:{present:true,sha256:digest},unchanged:true,stable:true}]}};
 const engine=sandbox.module.exports.createNativeTaskExecution({sourceOf:()=>({threadId:'fixture',sessionTreeId:'fixture',turnId:'t',callId:'c',model:'fixture',hostVersion:'fixture'}),readState:()=>state,storageRoot:path.resolve('fixture-only')});
 const result=await engine.call({arguments:{action:'prepare',cwd:process.cwd(),epoch:'e',expectedRevision:1,scopeRef:'s',model:'fixture',intake:'i',continuation:'c',postRelease:'p',authoritySourceRef:'a',quiescenceSourceRef:'drain.json',deadlineMs:Date.now()+10000}});
 results.push({mode,result,mkdir,opened,closed,removed,created,closeResults:await engine.close()});
}console.log(JSON.stringify(results));})();
"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE.with_name('native-task-execution.cjs'))],
                             capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = json.loads(run.stdout)
        expected = {
            'open': ('DB_OPEN_FAILED', 0, 1, 'not-returned'),
            'scope': ('SCOPE_BUSY', 1, 1, 'closed'),
            'engine': ('ENGINE_FAILED', 1, 1, 'closed'),
            'close': ('ENGINE_FAILED', 1, 0, 'close-unverified'),
            'scope-close': ('SCOPE_BUSY', 1, 0, 'close-unverified'),
            'nonempty': ('ENGINE_FAILED', 1, 0, 'closed'),
            'remove': ('ENGINE_FAILED', 1, 0, 'closed'),
            'changed': ('ENGINE_FAILED', 1, 0, 'closed'),
        }
        for row in rows:
            with self.subTest(mode=row['mode']):
                value = row['result']['value']
                self.assertTrue(row['result']['isError'], row)
                self.assertEqual(row['closeResults'], [], row)
                self.assertNotIn('operationId', value)
                if row['mode'] in expected:
                    reason, closed, removed, recorder = expected[row['mode']]
                    self.assertEqual((value['reason'], row['closed'], row['removed']),
                                     (reason, closed, removed), row)
                    self.assertEqual(value['preparationCleanup']['recorder'], recorder)
                    self.assertEqual(value['preparationCleanup']['directoryState'],
                                     'removed-empty' if removed else 'retained-unverified')
                    self.assertEqual(row['created'], not bool(removed))
                else:
                    self.assertEqual(row['opened'], 0, row)
                    self.assertEqual(row['removed'], 0, row)
                    self.assertNotIn('preparationCleanup', value)
                    self.assertEqual(value['reason'], 'EEXIST' if row['mode']=='collision' else 'current-source-not-executable')
                    if row['mode']=='invalid': self.assertEqual(row['mkdir'], 0)

    def test_recovery_initialization_retains_recorder_cleanup_owner(self):
        # Actual wrapper; synthetic state/handles and Map storage, no native work.
        script = r"""
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const file=process.argv[1],raw=fs.readFileSync(file,'utf8'),hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const boom=code=>Object.assign(Error(code),{code}),forbid=()=>{throw boom('NATIVE_FORBIDDEN');};
(async()=>{const rows=[];for(const mode of ['ok','io','quota','save','once','always']){
 const cwd=path.resolve('memory-work'),store=path.resolve('memory-store'),id='11111111-1111-4111-8111-111111111111';
 const source={threadId:'root',sessionTreeId:'root',turnId:'t',callId:'c',model:'m',hostVersion:'v'};
 const state={phase:'held',source,scopeRef:'s'},body=Buffer.from(JSON.stringify(state)),digest=hash(body);
 const lease={scopeRef:'s',transferId:id},record={revision:1,state,lease};
 const dir=path.join(store,'native-executions',hash(JSON.stringify({threadId:'root',cwd})),id),status=path.join(dir,'status.json');
 const original=JSON.stringify({operationId:id,source,phase:'held',stateEvidence:{evidenceId:digest,sha256:digest}});
 const mem=new Map([[status,Buffer.from(original)],[path.join(dir,digest+'.json'),body]]),handles=[];
 if(mode==='quota')for(let n=0;n<4;n++)mem.set(path.join(dir,String(n).repeat(64)+'.json'),Buffer.alloc(4194304-(n===3?512:0)));
 const disk={existsSync:p=>mem.has(p)||!/[.](json|sqlite|tmp)$/.test(p),realpathSync:p=>p,
 lstatSync:p=>({isDirectory:()=>!mem.has(p),isFile:()=>mem.has(p),isSymbolicLink:()=>false,nlink:1,size:mem.get(p)?.length||0}),
 readdirSync:()=>[...mem.keys()].map(p=>path.basename(p)),readFileSync:p=>mem.get(p),
 writeFileSync(p,b){if(['io','once','always'].includes(mode))throw boom('EIO');mem.set(p,Buffer.from(b));},
 openSync:p=>{if(mode==='save')throw boom('ENOSPC');return p;},fsyncSync(){},closeSync(){},
 renameSync(a,b){mem.set(b,mem.get(a));mem.delete(a);},unlinkSync:p=>mem.delete(p)};
 const open=()=>{const h={calls:0,closed:false},n=handles.push(h);return{inspectExternalStopped:()=>record,close(){h.calls++;if(n===2&&(mode==='always'||mode==='once'&&h.calls===1))throw boom('CLOSE_FAILED');h.closed=true;}};};
 const snapshot={mode:'active',epoch:'e',revision:1,checkpoint:{canContinue:true},checkpointSource:{sha256:digest},inputReceipt:{present:true},hostObservationCurrent:true,currentInputReconciled:true,
 nativeInputEvidence:{state:'observed',latestInputReconciled:true,latestNativeInputsComplete:true,pendingInputs:[]},inspection:{inputs:[]}};
 const maps=[],OwnedMap=class extends Map{constructor(){super();maps.push(this);}};
 const box={module:{exports:{}},process,Buffer,TextDecoder,Map:OwnedMap,setTimeout,clearTimeout,
 require:n=>n==='node:fs'?disk:n==='node:child_process'?{spawn:forbid,spawnSync:forbid}:n==='./carrier-recorder.cjs'?{openCarrierRecorder:open}:n.startsWith('./')?{}:require(n)};
 vm.runInNewContext(raw,box,{filename:file});const e=box.module.exports.createNativeTaskExecution({sourceOf:()=>source,readState:()=>snapshot,storageRoot:store,nativeFactory:forbid});
 const old={id,dir,cwd,source,stateEvidence:{evidenceId:digest,sha256:digest},recorderClosed:true,recorder:{close(){}},engine:{inspect:()=>state}};maps[0].set(id,old);
 const request={arguments:{action:'reconcile',cwd,operationId:id,epoch:'e',expectedRevision:1,recordRevision:1,recordSha256:digest,leaseSha256:hash(JSON.stringify(lease)),deadlineMs:Date.now()+10000}};
 let result,retry,handleCount,afterRetryHandles,unchanged,closed;try{result=await e.call(request);
 if(['once','always'].includes(mode)){handleCount=handles.length;retry=await e.call(request);afterRetryHandles=handles.length;}
 unchanged=maps[0].get(id)===old&&mem.get(status).toString()===original&&mem.get(path.join(dir,digest+'.json')).equals(body);
 }finally{closed=await e.close();}rows.push({mode,result,retry,handleCount,afterRetryHandles,unchanged,handles,closed});
 }console.log(JSON.stringify(rows));})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE.with_name('native-task-execution.cjs'))],
                             capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        for row in json.loads(run.stdout):
            with self.subTest(mode=row['mode']):
                mode, value = row['mode'], row['result']['value']
                self.assertEqual(row['result']['isError'], mode != 'ok', row)
                if mode != 'ok':
                    self.assertTrue(row['unchanged'], row)
                    self.assertEqual(value['reason'], {'quota': 'execution-evidence-limit', 'save': 'ENOSPC'}.get(mode, 'EIO'))
                if mode in ('once', 'always'):
                    self.assertEqual(value.get('recorderCleanup'), {'state': 'close-unverified', 'code': 'CLOSE_FAILED'})
                    self.assertTrue(row['retry']['isError'], row)
                    self.assertEqual(row['retry']['value']['reason'], 'recovery-resource-unverified', row)
                    self.assertEqual(row['afterRetryHandles'], row['handleCount'], row)
                    self.assertEqual(row['handles'][1]['calls'], 2, row)
                self.assertEqual(row['handles'][1]['closed'], mode != 'always', row)
                if mode == 'always':
                    self.assertTrue(any(x.get('state') == 'cleanup-unverified' for x in row['closed']), row)

    def test_execution_wire_requires_current_source_before_any_native_start(self):
        _, _, _, call = self.start_execution_wire()
        result = call('prepare', epoch='missing', expectedRevision=0, scopeRef='scope', model='fixture',
            intake='read', continuation='first', postRelease='last', deadlineMs=int(time.time()*1000)+1000,
            authoritySourceRef='not-proof', quiescenceSourceRef='not-proof')
        self.assertTrue(result['isError'])
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_wire_hash_bound_reviews_and_post_release_result(self):
        contract = self.execution_contract()
        process, _, _, call = self.start_execution_wire()
        prepared = call('prepare', **contract)
        self.assertFalse(prepared['isError'], prepared)
        operation_id = prepared['structuredContent']['operationId']
        stages = []
        while True:
            value = self.execution_until(call, operation_id, lambda x:
                x['reviewRequest'] is not None or x['phase'] in ('awaiting-intake-review', 'awaiting-release-review', 'completed', 'held', 'cancelled-held'))
            self.assertNotIn(value['phase'], ('held', 'cancelled-held'), value)
            if value['phase'] == 'completed':
                self.assertTrue(value['nativeClosed']['closed'])
                break
            request = value['reviewRequest']
            if request:
                stages.append(request['stage'])
                evidence = call('read-evidence', operationId=operation_id,
                    evidenceId=request['observationSha256'], maxChars=16000)
                self.assertFalse(evidence['isError'], evidence)
                self.assertEqual(evidence['structuredContent']['sha256'], request['observationSha256'])
                wrong = call('review', operationId=operation_id, reviewId=request['reviewId'],
                    observationSha256='0'*64, decision='allow', sourceRef='fixture-independent-review')
                self.assertTrue(wrong['isError'])
                accepted = call('review', operationId=operation_id, reviewId=request['reviewId'],
                    observationSha256=request['observationSha256'], decision='allow', sourceRef='fixture-independent-review')
                self.assertFalse(accepted['isError'], accepted)
            else:
                action = 'commit' if value['phase'] == 'awaiting-intake-review' else 'release'
                self.assertFalse(call(action, operationId=operation_id)['isError'])
        self.assertEqual(stages, ['prepare', 'target-created', 'commit', 'release', 'result', 'closed'])
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertEqual(sum(row['method']=='turn/start' for row in wire), 3)
        process.stdin.close(); process.wait(timeout=5)
        self.assertEqual(process.returncode, 0)

    def execution_accept(self, call, operation_id, stage, *, timeout=8):
        waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None, timeout=timeout)
        review = waiting['reviewRequest']
        self.assertEqual(review['stage'], stage)
        result = call('review', operationId=operation_id, reviewId=review['reviewId'],
            observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-independent-review')
        self.assertFalse(result['isError'], result)
        return waiting

    def test_execution_workspace_writes_only_after_reviewed_native_policy(self):
        contract = self.execution_write_contract()
        _, _, _, call = self.start_execution_wire(peer_mode='workspace-write')
        reply = call('prepare', **contract)
        self.assertFalse(reply['isError'], reply)
        operation_id = reply['structuredContent']['operationId']
        for stage in ('prepare', 'target-created'):
            self.execution_accept(call, operation_id, stage)
        self.execution_until(call, operation_id, lambda x: x['phase']=='awaiting-intake-review')
        self.assertFalse((self.work/'review.json').exists())
        call('commit', operationId=operation_id)
        self.execution_accept(call, operation_id, 'write-prepare')
        waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        self.assertEqual(waiting['reviewRequest']['stage'], 'commit')
        self.assertFalse((self.work/'review.json').exists())
        self.execution_accept(call, operation_id, 'commit')
        self.execution_until(call, operation_id, lambda x: x['phase']=='awaiting-release-review')
        self.assertEqual(json.loads((self.work/'review.json').read_text())['turn'], 2)
        call('release', operationId=operation_id)
        for stage in ('release', 'result', 'closed'):
            self.execution_accept(call, operation_id, stage)
        final = self.execution_until(call, operation_id, lambda x: x['phase']=='completed')
        self.assertTrue(final['nativeClosed']['closed'])
        self.assertEqual(json.loads((self.work/'review.json').read_text())['turn'], 3)
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        turns = [row['params'] for row in wire if row['method']=='turn/start']
        self.assertEqual([p['sandboxPolicy']['type'] for p in turns], ['readOnly', 'workspaceWrite', 'workspaceWrite'])
        self.assertTrue(all('review.json' in turn['input'][0]['text'] and
            'grants no additional authority' in turn['input'][0]['text'] for turn in turns))
        self.assertFalse(any(row['method']=='thread/inject_items' for row in wire))
        resume = next(row['params'] for row in wire if row['method']=='thread/resume')
        self.assertNotIn('cwd', resume)

    def execution_write_contract(self):
        contract = self.execution_contract()
        contract.update(sandbox='workspace-write', writeScope={'authoritySourceRef': 'drain.json',
            'outputs': [{'path': 'review.json', 'expectedSha256': None, 'expectedEffect': 'Two fixed fixture writes'}]})
        return contract

    def execution_intake(self, call, contract, *, timeout=8):
        reply = call('prepare', **contract)
        self.assertFalse(reply['isError'], reply)
        operation_id = reply['structuredContent']['operationId']
        for stage in ('prepare', 'target-created'):
            self.execution_accept(call, operation_id, stage, timeout=timeout)
        self.execution_until(call, operation_id, lambda x: x['phase']=='awaiting-intake-review', timeout=timeout)
        return operation_id

    def test_execution_workspace_actual_policy_denials_hold_without_writes(self):
        contract = self.execution_write_contract()
        contract['deadlineMs'] = int(time.time()*1000)+60000
        for mode in ('policy-readonly', 'policy-extra-root', 'policy-network', 'policy-missing', 'requirements-deny'):
            with self.subTest(mode=mode):
                _, _, _, call = self.start_execution_wire(peer_mode=mode)
                operation_id = self.execution_intake(call, {**contract, 'scopeRef': mode})
                call('commit', operationId=operation_id)
                self.execution_accept(call, operation_id, 'write-prepare')
                held = self.execution_until(call, operation_id, lambda x: x['phase']=='held')
                self.assertEqual(held['writer'], 'source')
                self.assertIn(held['failure'], ('NATIVE_WRITE_POLICY_UNVERIFIED', 'NATIVE_REQUIREMENTS_DENIED'))
                self.assertIsNone(held['reconciliationBasis'])
                self.assertIsNotNone(held['targetReconciliationBasis'])
                self.assertFalse((self.work/'review.json').exists())

    def test_execution_workspace_review_drift_holds_before_policy_transition(self):
        contract = self.execution_write_contract()
        _, _, _, call = self.start_execution_wire(peer_mode='workspace-write')
        operation_id = self.execution_intake(call, contract)
        call('commit', operationId=operation_id)
        waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        self.assertEqual(waiting['reviewRequest']['stage'], 'write-prepare')
        (self.work/'review.json').write_text('another writer changed the reviewed baseline', encoding='utf-8')
        held = self.execution_until(call, operation_id, lambda x: x['phase'] in ('held', 'cancelled-held'))
        self.assertEqual(held['writer'], 'source')
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertFalse(any(row['method']=='thread/resume' for row in wire))

    def test_execution_unknown_resume_retains_source_lease_without_replay(self):
        contract = self.execution_write_contract()
        _, _, _, call = self.start_execution_wire(peer_mode='resume-ack-loss')
        op = self.execution_intake(call, contract)
        call('commit', operationId=op)
        self.execution_accept(call, op, 'write-prepare')
        self.execution_until(call, op, lambda x: x['pendingEffect'] and
            x['pendingEffect'].get('method')=='thread/resume' and x['pendingEffect'].get('requestRef'))
        held = call('cancel', operationId=op, reason='Inspect unknown resume ACK')['structuredContent']
        self.assertEqual(held['writer'], 'source')
        self.assertIsNone(held['reconciliationBasis'])
        self.assertIsNone(held['targetReconciliationBasis'])
        self.assertFalse((self.work/'review.json').exists())
        call('commit', operationId=op)
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertEqual([row['method'] for row in wire].count('turn/start'), 1)
        self.assertEqual([row['method'] for row in wire].count('thread/resume'), 1)

    def test_execution_workspace_unknown_dispatch_never_replays_or_settles_zero_turn(self):
        contract = self.execution_write_contract()
        _, _, _, call = self.start_execution_wire(peer_mode='write-ack-loss')
        operation_id = self.execution_intake(call, contract)
        call('commit', operationId=operation_id)
        for stage in ('write-prepare', 'commit'):
            self.execution_accept(call, operation_id, stage)
        self.execution_until(call, operation_id, lambda x: x['writer']=='target' and x['pendingEffect']
            and x['pendingEffect']['method']=='turn/start' and x['pendingEffect']['requestRef'])
        held = call('cancel', operationId=operation_id, reason='unknown write dispatch')['structuredContent']
        self.assertEqual(held['phase'], 'cancelled-held')
        self.assertEqual(held['writer'], 'target')
        self.assertIsNone(held['reconciliationBasis'])
        self.assertEqual(json.loads((self.work/'review.json').read_text())['turn'], 2)
        call('commit', operationId=operation_id)
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertEqual(sum(row['method']=='turn/start' for row in wire), 2)

    def test_execution_workspace_interrupted_write_keeps_effects_and_writer(self):
        contract = self.execution_write_contract()
        _, _, _, call = self.start_execution_wire(peer_mode='write-interrupted')
        operation_id = self.execution_intake(call, contract)
        call('commit', operationId=operation_id)
        for stage in ('write-prepare', 'commit'):
            self.execution_accept(call, operation_id, stage)
        held = self.execution_until(call, operation_id, lambda x: x['phase']=='held')
        self.assertEqual(held['writer'], 'target')
        self.assertIsNone(held['reconciliationBasis'])
        self.assertEqual(json.loads((self.work/'review.json').read_text())['turn'], 2)
        evidence = call('read-evidence', operationId=operation_id,
            evidenceId=held['stateEvidence']['sha256'], maxChars=16000)['structuredContent']
        self.assertTrue(evidence['complete'])
        state = json.loads(evidence['text'])
        self.assertEqual(state['stoppedTurn']['terminal'], 'interrupted')
        self.assertTrue(state['pendingEffect']['effectsUnreviewed'])

    def test_execution_workspace_rejects_unbound_baseline_and_permission_expansion(self):
        contract = self.execution_write_contract()
        _, _, _, call = self.start_execution_wire()
        for changed in ({'sandbox': 'danger-full-access'}, {'sandbox': 'externalSandbox'},
                {'writeScope': {**contract['writeScope'], 'writableRoots': [str(self.root)]}},
                {'writeScope': {**contract['writeScope'], 'outputs': [{'path': '../escape', 'expectedSha256': None, 'expectedEffect': 'not admitted'}]}},
                {'writeScope': {**contract['writeScope'], 'outputs': [{'path': 'undeclared.json', 'expectedSha256': None, 'expectedEffect': 'not bound'}]}}):
            self.assertTrue(call('prepare', **{**contract, **changed})['isError'])
        (self.work/'review.json').write_text('original', encoding='utf-8')
        rejected = call('prepare', **contract)
        self.assertEqual(rejected['structuredContent']['reason'], 'write-baseline-mismatch')
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_workspace_original_bytes_are_retained_for_independent_diff(self):
        contract = self.execution_write_contract()
        original = b'original uncommitted artifact\r\n'
        (self.work/'review.json').write_bytes(original)
        contract['writeScope']['outputs'][0]['expectedSha256'] = hashlib.sha256(original).hexdigest()
        _, _, _, call = self.start_execution_wire(peer_mode='workspace-write')
        reply = call('prepare', **contract)
        operation_id = reply['structuredContent']['operationId']
        waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        packet = json.loads(call('read-evidence', operationId=operation_id,
            evidenceId=waiting['reviewRequest']['observationSha256'], maxChars=16000)['structuredContent']['text'])
        baseline = packet['writes']['baseline']
        source = json.loads(call('read-evidence', operationId=operation_id,
            evidenceId=baseline['evidence']['sha256'])['structuredContent']['text'])
        self.assertEqual(base64.b64decode(source['files'][0]['contentsBase64']), original)
        self.assertEqual(source['files'][0]['sha256'], hashlib.sha256(original).hexdigest())
        call('cancel', operationId=operation_id, reason='baseline verification complete')
        self.assertEqual((self.work/'review.json').read_bytes(), original)

    def test_execution_workspace_forced_old_peer_close_prevents_new_peer(self):
        contract = self.execution_write_contract()
        _, _, _, call = self.start_execution_wire(peer_mode='hang-on-eof')
        operation_id = self.execution_intake(call, contract)
        call('commit', operationId=operation_id)
        self.execution_accept(call, operation_id, 'write-prepare')
        held = self.execution_until(call, operation_id, lambda x: x['phase']=='held')
        self.assertEqual(held['writer'], 'source')
        self.assertFalse(held['nativeClosed']['closed'])
        self.assertTrue(held['nativeClosed']['forced'])
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertEqual(sum(row['method']=='initialize' for row in wire), 1)
        self.assertFalse(any(row['method']=='thread/resume' for row in wire))
        self.assertFalse((self.work/'review.json').exists())

    def execution_skill(self, enabled=True):
        from types import SimpleNamespace
        from tests.product.test_codex_capabilities import CodexCapabilitiesTests
        skill = self.work/'managed'/'sample'/'SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('---\nname: sample\ndisable-model-invocation: true\n---\nReview the candidate only.\n', encoding='utf-8')
        policy = skill.parent/'agents'/'openai.yaml'
        policy.parent.mkdir()
        policy.write_text('policy:\n  allow_implicit_invocation: false\n', encoding='utf-8')
        fixture = CodexCapabilitiesTests.fixture(SimpleNamespace(root=self.work, skill=skill,
            log=self.work/'skill-query.jsonl'), enabled=enabled, duplicate=True)
        request = {'originalRequest': 'Review the candidate',
            'delegation': {'sourceRef': 'current-bound-goal', 'scope': 'Review only'},
            'selection': {'name': 'sample', 'path': str(skill),
                'expectedSha256': hashlib.sha256(skill.read_bytes()).hexdigest(),
                'expectedPolicySha256': hashlib.sha256(policy.read_bytes()).hexdigest()}}
        return fixture, request

    def test_execution_skill_uses_exact_typed_path_after_intake(self):
        contract = self.execution_contract()
        fixture, request = self.execution_skill()
        _, _, _, call = self.start_execution_wire(capability_cli=fixture)
        prepared = call('prepare-skill', skillRequest=request)
        self.assertFalse(prepared['isError'], prepared)
        self.assertFalse(prepared['structuredContent']['cli']['available'])
        reply = call('prepare', **contract, skillRequest=request)
        self.assertFalse(reply['isError'], reply)
        operation_id = reply['structuredContent']['operationId']
        for stage in ('prepare', 'target-created'):
            self.execution_accept(call, operation_id, stage)
        self.execution_until(call, operation_id, lambda x: x['phase']=='awaiting-intake-review')
        call('commit', operationId=operation_id)
        self.execution_accept(call, operation_id, 'commit')
        self.execution_until(call, operation_id, lambda x: x['phase']=='awaiting-release-review')
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        turns = [row['params'] for row in wire if row['method']=='turn/start']
        self.assertEqual([item['type'] for item in turns[0]['input']], ['text'])
        self.assertIn({'type': 'skill', 'name': 'sample', 'path': request['selection']['path']}, turns[1]['input'])
        self.assertIn('coordinator-selected', turns[1]['input'][0]['text'])
        self.assertEqual(turns[1]['input'][-1]['text'], contract['continuation'])
        stopped = call('cancel', operationId=operation_id, reason='fixed test complete')['structuredContent']
        self.assertEqual(stopped['phase'], 'cancelled-held')
        self.assertIsNone(stopped['reconciliationBasis'])

    def test_execution_skill_disabled_does_not_start_target(self):
        contract = self.execution_contract()
        fixture, request = self.execution_skill(enabled=False)
        _, _, _, call = self.start_execution_wire(capability_cli=fixture)
        reply = call('prepare', **contract, skillRequest=request)
        self.assertFalse(reply['isError'], reply)
        held = self.execution_until(call, reply['structuredContent']['operationId'], lambda x: x['phase']=='held')
        self.assertEqual(held['failure'], 'SKILL_DISABLED')
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_skill_policy_is_observed_not_self_authorized(self):
        contract = self.execution_contract()
        fixture, request = self.execution_skill()
        _, _, _, call = self.start_execution_wire(capability_cli=fixture)
        reply = call('prepare', **contract, skillRequest=request)
        operation_id = reply['structuredContent']['operationId']
        waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        review = waiting['reviewRequest']
        evidence = call('read-evidence', operationId=operation_id, evidenceId=review['observationSha256'], maxChars=16000)
        packet = json.loads(evidence['structuredContent']['text'])
        skill = packet['state']['preparedSkill']
        self.assertTrue(skill['source']['policy']['disableModelInvocation'])
        self.assertFalse(skill['source']['policy']['allowImplicitInvocation'])
        self.assertEqual(skill['origin']['selection'], 'coordinator-selected')
        call('review', operationId=operation_id, reviewId=review['reviewId'],
            observationSha256=review['observationSha256'], decision='deny', sourceRef='source-body-restriction-reviewed')
        self.execution_until(call, operation_id, lambda x: x['phase']=='held')
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_skill_changed_after_review_holds_before_intake(self):
        contract = self.execution_contract()
        fixture, request = self.execution_skill()
        _, _, _, call = self.start_execution_wire(capability_cli=fixture)
        reply = call('prepare', **contract, skillRequest=request)
        operation_id = reply['structuredContent']['operationId']
        self.execution_accept(call, operation_id, 'prepare')
        self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        Path(request['selection']['path']).write_text('Changed source is not the reviewed Skill.', encoding='utf-8')
        held = self.execution_until(call, operation_id, lambda x: x['phase'] in ('held', 'cancelled-held'))
        self.assertEqual(held['writer'], 'source')
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertFalse(any(row['method']=='turn/start' for row in wire))

    def test_execution_skill_preparation_eof_waits_for_owned_metadata_peer(self):
        contract = self.execution_contract()
        fixture, request = self.execution_skill()
        ended = self.work/'skill-peer-ended.json'
        with fixture.open('a', encoding='utf-8') as stream:
            stream.write("\nrl.on('close',()=>setTimeout(()=>fs.writeFileSync("+json.dumps(str(ended))+",JSON.stringify({fixture:true,pid:process.pid})),1300));\n")
        process, _, _, call = self.start_execution_wire(capability_cli=fixture)
        reply = call('prepare', **contract, skillRequest=request)
        self.assertFalse(reply['isError'], reply)
        deadline = time.monotonic()+5
        while time.monotonic() < deadline:
            log = self.work/'skill-query.jsonl'
            if log.exists() and 'skills/list' in log.read_text():
                break
            time.sleep(0.02)
        self.assertTrue(log.exists())
        process.stdin.close(); process.wait(timeout=8)
        self.assertEqual(process.returncode, 0)
        self.assertTrue(ended.exists(), 'MCP exited while its metadata peer was still closing')
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_wire_source_change_invalidates_waiting_review(self):
        contract = self.execution_contract()
        _, _, _, call = self.start_execution_wire()
        operation_id = call('prepare', **contract)['structuredContent']['operationId']
        value = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        old = value['reviewRequest']
        self.append_native_message(text='Stop the previous scope and inspect the change.')
        rejected = call('review', operationId=operation_id, reviewId=old['reviewId'],
            observationSha256=old['observationSha256'], decision='allow', sourceRef='stale-review')
        self.assertTrue(rejected['isError'])
        held = self.execution_until(call, operation_id, lambda x: x['phase'] in ('held', 'cancelled-held'))
        self.assertIsNone(held['reviewRequest'])
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_reclaims_only_durable_no_effect_denials_after_sixteen(self):
        self.check_prestart_slot_reclamation('deny')

    def test_execution_reclaims_durable_prestart_cancellations_after_sixteen(self):
        # OE-P2-01: formerly the 17th zero-effect cancellation hit the cap.
        self.check_prestart_slot_reclamation('cancel')

    def check_prestart_slot_reclamation(self, disposition):
        contract = self.execution_contract()
        contract['deadlineMs'] = int(time.time()*1000)+60000
        _, _, _, call = self.start_execution_wire()
        first = None
        for number in range(18):
            reply = call('prepare', **contract)
            self.assertFalse(reply['isError'], (number, reply))
            operation_id = reply['structuredContent']['operationId']
            first = first or operation_id
            waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
            review = waiting['reviewRequest']
            self.assertEqual(review['stage'], 'prepare')
            if disposition == 'deny':
                call('review', operationId=operation_id, reviewId=review['reviewId'],
                    observationSha256=review['observationSha256'], decision='deny', sourceRef='fixture-denial')
            else:
                call('cancel', operationId=operation_id, reason='Fixture cancelled before any dispatch')
            phase = 'held' if disposition == 'deny' else 'cancelled-held'
            self.execution_until(call, operation_id, lambda x: x['phase']==phase and not x['busy'])
        retained = call('inspect', operationId=first)
        self.assertFalse(retained['isError'], retained)
        self.assertEqual(retained['structuredContent']['phase'], phase)
        self.assertEqual(retained['structuredContent']['controllerState'], 'not-owned-current-process')
        locator = retained['structuredContent']['stateEvidence']
        evidence = call('read-evidence', operationId=first, evidenceId=locator['sha256'])
        self.assertFalse(evidence['isError'], evidence)
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_invalid_effort_is_rejected_before_allocation_without_consuming_capacity(self):
        # OE-P2-02: whitespace previously allocated an INVALID_PLAN/new slot.
        contract = self.execution_contract()
        contract['deadlineMs'] = int(time.time()*1000)+60000
        _, _, _, call = self.start_execution_wire()
        for effort in [' ', '\t\r\n', '', None, 0, False, [], {}]*3:
            reply = call('prepare', **contract, effort=effort)
            self.assertTrue(reply['isError'], reply)
            self.assertEqual(reply['structuredContent']['reason'], 'invalid-execution-plan')
            self.assertFalse((self.state/'native-executions').exists(), 'invalid effort allocated execution resources')
        for number in range(16):
            reply = call('prepare', **{**contract, 'scopeRef': 'active-'+str(number)}, effort='low')
            self.assertFalse(reply['isError'], (number, reply))
            self.execution_until(call, reply['structuredContent']['operationId'], lambda x: x['reviewRequest'] is not None)
        capped = call('prepare', **{**contract, 'scopeRef': 'active-seventeenth'})
        self.assertEqual(capped['structuredContent']['reason'], 'execution-operation-limit')
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_deadline_expiry_after_validation_retains_prestart_failure_without_slot(self):
        contract = self.execution_contract()
        _, _, _, call = self.start_execution_wire(state_delay_ms=1000)
        contract['deadlineMs'] = int(time.time()*1000)+500
        reply = call('prepare', **contract)
        self.assertFalse(reply['isError'], reply)
        operation_id = reply['structuredContent']['operationId']
        stopped = self.execution_until(call, operation_id, lambda x: x['failure'] is not None)
        self.assertEqual(stopped['phase'], 'cancelled-held')
        self.assertEqual(stopped['controllerState'], 'not-owned-current-process')
        self.assertEqual(stopped['failure'], 'INVALID_PLAN')
        rejection = stopped['prestartRejection']
        original = json.loads(call('read-evidence', operationId=operation_id,
            evidenceId=rejection['evidence']['sha256'])['structuredContent']['text'])
        self.assertEqual(original['code'], 'INVALID_PLAN')
        self.assertEqual(original['deadlineMs'], contract['deadlineMs'])
        self.assertEqual(original['observation']['phase'], 'new')
        self.assertEqual(original['observation']['turnStarts'], 0)
        self.assertIsNone(original['observation']['revision'])
        contract['deadlineMs'] = int(time.time()*1000)+60000
        for number in range(16):
            valid = call('prepare', **{**contract, 'scopeRef': 'valid-'+str(number)})
            self.assertFalse(valid['isError'], valid)
            self.execution_until(call, valid['structuredContent']['operationId'], lambda x: x['reviewRequest'] is not None)
        self.assertEqual(call('prepare', **contract)['structuredContent']['reason'], 'execution-operation-limit')
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_does_not_evict_sixteen_unsettled_closed_peers(self):
        contract = self.execution_contract()
        contract['deadlineMs'] = int(time.time()*1000)+60000
        _, _, _, call = self.start_execution_wire()
        first = None
        for number in range(16):
            reply = call('prepare', **{**contract, 'scopeRef': 'unsettled-'+str(number)})
            self.assertFalse(reply['isError'], reply)
            operation_id = reply['structuredContent']['operationId']
            first = first or operation_id
            self.execution_accept(call, operation_id, 'prepare')
            self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
            stopped = call('cancel', operationId=operation_id, reason='stop before intake')['structuredContent']
            self.assertTrue(stopped['nativeClosed']['closed'])
        denied = call('prepare', **{**contract, 'scopeRef': 'new-unrelated'})
        self.assertEqual(denied['structuredContent']['reason'], 'execution-operation-limit')
        retained = call('inspect', operationId=first)['structuredContent']
        self.assertEqual(retained['controllerState'], 'owned-current-process')
        self.assertIsNotNone(retained['reconciliationBasis'])

    def test_execution_completed_slot_reclaims_memory_but_keeps_persistent_evidence(self):
        contract = self.execution_contract()
        contract['deadlineMs'] = int(time.time()*1000)+60000
        _, _, _, call = self.start_execution_wire()
        completed_id = self.execution_intake(call, contract)
        call('commit', operationId=completed_id)
        self.execution_accept(call, completed_id, 'commit')
        self.execution_until(call, completed_id, lambda x: x['phase']=='awaiting-release-review')
        call('release', operationId=completed_id)
        for stage in ('release', 'result', 'closed'):
            self.execution_accept(call, completed_id, stage)
        self.execution_until(call, completed_id, lambda x: x['phase']=='completed')
        for number in range(15):
            reply = call('prepare', **{**contract, 'scopeRef': 'denied-'+str(number)})
            operation_id = reply['structuredContent']['operationId']
            waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
            review = waiting['reviewRequest']
            call('review', operationId=operation_id, reviewId=review['reviewId'],
                observationSha256=review['observationSha256'], decision='deny', sourceRef='fixed-denial')
            self.execution_until(call, operation_id, lambda x: x['phase']=='held' and not x['busy'])
        following = call('prepare', **{**contract, 'scopeRef': 'following-task'})
        self.assertFalse(following['isError'], following)
        retained = call('inspect', operationId=completed_id)['structuredContent']
        self.assertEqual(retained['phase'], 'completed')
        self.assertEqual(retained['controllerState'], 'not-owned-current-process')
        self.assertFalse(call('read-evidence', operationId=completed_id,
            evidenceId=retained['stateEvidence']['sha256'])['isError'])
        call('cancel', operationId=following['structuredContent']['operationId'], reason='fixed test complete')

    def test_existing_pause_tool_remains_responsive_and_invalidates_execution(self):
        contract = self.execution_contract()
        _, responses, send, call = self.start_execution_wire()
        operation_id = call('prepare', **contract)['structuredContent']['operationId']
        self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        identifier = send('tools/call', {**self.params, 'name': 'manage_task_state',
            'arguments': {'cwd': str(self.work), 'action': 'pause', 'epoch': contract['epoch'],
                'expectedRevision': contract['expectedRevision'], 'reason': 'Fixture user paused the task.'}})
        paused = responses.get(timeout=5)
        self.assertEqual(paused['id'], identifier)
        self.assertFalse(paused['result']['isError'], paused)
        held = self.execution_until(call, operation_id, lambda x: x['phase'] in ('held', 'cancelled-held'))
        self.assertEqual(held['failure'], 'current-source-not-executable')
        self.assertIsNone(held['reviewRequest'])
        self.assertFalse((self.root/'native-wire.jsonl').exists())

    def test_execution_wire_notification_cancel_and_eof_retain_held_record(self):
        contract = self.execution_contract()
        process, responses, send, call = self.start_execution_wire()
        params = {**self.params, 'name': 'coordinate_task_execution',
                  'arguments': {'cwd': str(self.work), 'action': 'prepare', **contract}}
        request_id = send('tools/call', params)
        result = responses.get(timeout=5)['result']
        operation_id = result['structuredContent']['operationId']
        self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        send('notifications/cancelled', {'requestId': request_id}, notification=True)
        held = self.execution_until(call, operation_id, lambda x: x['phase'] in ('held', 'cancelled-held'))
        self.assertIsNone(held['reviewRequest'])
        process.stdin.close(); process.wait(timeout=5)
        saved = list(self.state.rglob('status.json'))
        self.assertEqual(len(saved), 1)
        state = json.loads(saved[0].read_text(encoding='utf-8'))
        self.assertIn(state['phase'], ('held', 'cancelled-held'))

    def test_execution_wire_eof_closes_started_target_without_approving_intake(self):
        contract = self.execution_contract()
        process, _, _, call = self.start_execution_wire()
        operation_id = call('prepare', **contract)['structuredContent']['operationId']
        value = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        review = value['reviewRequest']
        self.assertEqual(review['stage'], 'prepare')
        self.assertFalse(call('review', operationId=operation_id, reviewId=review['reviewId'],
            observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-plan-review')['isError'])
        self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None
                             and x['reviewRequest']['stage'] == 'target-created')
        process.stdin.close(); process.wait(timeout=5)
        self.assertEqual(process.returncode, 0)
        saved = json.loads(next(self.state.rglob('status.json')).read_text(encoding='utf-8'))
        self.assertIn(saved['phase'], ('held', 'cancelled-held'))
        self.assertTrue(saved['nativeClosed']['closed'])
        self.assertFalse(saved['nativeClosed']['forced'])
        wire = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertEqual(sum(row['method']=='thread/start' for row in wire), 1)
        self.assertFalse(any(row['method']=='turn/start' for row in wire))
        # A new MCP process can inspect retained evidence, but cannot take over
        # the old process or replay a still-bound scope by allocating another id.
        _, _, _, new_call = self.start_execution_wire()
        restored = new_call('inspect', operationId=operation_id)
        self.assertFalse(restored['isError'])
        self.assertEqual(restored['structuredContent']['controllerState'], 'not-owned-current-process')
        replay = new_call('prepare', **contract)
        self.assertTrue(replay['isError'])
        self.assertEqual(replay['structuredContent']['reason'], 'SCOPE_BUSY')
        wire_after = [json.loads(line) for line in (self.root/'native-wire.jsonl').read_text().splitlines()]
        self.assertEqual(wire_after, wire)

    def test_known_stopped_transfer_can_be_reviewed_and_settled_without_native_replay(self):
        self.check_stopped_reconciliation('success')

    def test_stopped_reconciliation_refuses_unknown_turn_dispatch(self):
        self.check_unsettleable_execution('lost-turn-receipt')

    def test_stopped_reconciliation_refuses_transferred_writer(self):
        self.check_unsettleable_execution('normal')

    def test_stopped_reconciliation_refuses_forced_peer_closure(self):
        self.check_unsettleable_execution('hang-on-eof')

    def check_unsettleable_execution(self, mode):
        contract = self.execution_contract()
        _, _, _, call = self.start_execution_wire(peer_mode=mode)
        operation_id = call('prepare', **contract)['structuredContent']['operationId']
        for stage in (['prepare'] if mode == 'hang-on-eof' else ['prepare', 'target-created']):
            waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
            review = waiting['reviewRequest']; self.assertEqual(review['stage'], stage)
            self.assertFalse(call('review', operationId=operation_id, reviewId=review['reviewId'],
                observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-independent-review')['isError'])
        if mode == 'hang-on-eof':
            self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None
                and x['reviewRequest']['stage']=='target-created')
        elif mode == 'normal':
            self.execution_until(call, operation_id, lambda x: x['phase']=='awaiting-intake-review')
            self.assertFalse(call('commit', operationId=operation_id)['isError'])
            waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
            review = waiting['reviewRequest']
            self.assertFalse(call('review', operationId=operation_id, reviewId=review['reviewId'],
                observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-writer-review')['isError'])
            self.execution_until(call, operation_id, lambda x: x['phase']=='awaiting-release-review')
        else:
            self.execution_until(call, operation_id, lambda x: x['pendingEffect'] is not None
                and x['pendingEffect']['method']=='turn/start' and x['pendingEffect']['requestRef'] is not None)
        stopped = call('cancel', operationId=operation_id, reason='Stop fixed peer and inspect uncertain effects')['structuredContent']
        self.assertIsNone(stopped['reconciliationBasis'])
        wire = (self.root/'native-wire.jsonl').read_bytes()
        result = call('reconcile', operationId=operation_id, epoch=contract['epoch'],
            expectedRevision=contract['expectedRevision'], recordRevision=0,
            recordSha256='a'*64, leaseSha256='b'*64, deadlineMs=int(time.time()*1000)+10000)
        self.assertTrue(result['isError'])
        self.assertEqual(result['structuredContent']['reason'], 'EXTERNAL_STOPPED_NOT_APPLICABLE')
        self.assertEqual((self.root/'native-wire.jsonl').read_bytes(), wire)

    def test_stopped_settlement_rechecks_record_and_lease_after_review_preparation(self):
        self.check_stopped_reconciliation('record-change')

    def test_stopped_settlement_rechecks_current_pause_after_review_preparation(self):
        self.check_stopped_reconciliation('source-paused')

    def test_known_stopped_expired_preparation_keeps_its_original_deadline(self):
        self.check_stopped_reconciliation('expired')

    def check_stopped_reconciliation(self, mode):
        contract = self.execution_contract()
        if mode == 'expired':
            contract['deadlineMs'] = int(time.time()*1000)+2000
        process, _, _, call = self.start_execution_wire()
        operation_id = call('prepare', **contract)['structuredContent']['operationId']
        waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None)
        review = waiting['reviewRequest']
        self.assertFalse(call('review', operationId=operation_id, reviewId=review['reviewId'],
            observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-plan-review')['isError'])
        self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None
                             and x['reviewRequest']['stage'] == 'target-created')
        if mode == 'expired':
            self.execution_until(call, operation_id, lambda x: x['phase']=='held')
        process.stdin.close(); process.wait(timeout=5)
        wire_before = (self.root/'native-wire.jsonl').read_bytes()
        # A genuinely new native input/turn is appended; the old source is not
        # resurrected and its plan/deadline are not rewritten for recovery.
        meta = self.params['_meta']['x-codex-turn-metadata']
        meta['turn_id'] = 'current-recovery-turn'
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': 'turn_context', 'payload': {
                'turn_id': meta['turn_id'], 'model': meta['model'], 'cwd': str(self.work)}})+'\n')
        self.append_native_message(text='Reconcile the stopped review and continue the same authorized scope.')
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Reconcile the stopped review and continue the same authorized scope.',
            'turn_id': meta['turn_id'], 'model': meta['model'], 'transcript_path': str(transcript)},
            session=meta['session_id'], hook='UserPromptSubmit')
        current = self.native_input_preview()
        self.assertFalse(self.manage(action='bind', epoch=current['epoch'], expectedRevision=current['revision'],
            result='Review the authorized fixed candidate', inputs=['drain.json'], outputs=[{'path': 'review.json'}],
            nextAction='Reconcile the stopped preparation', canContinue=True)['isError'])
        current = self.native_input_preview()
        original_deadline = contract['deadlineMs']
        contract.update(epoch=current['epoch'], expectedRevision=current['revision'])
        _, _, _, fresh = self.start_execution_wire()
        old = fresh('inspect', operationId=operation_id)['structuredContent']
        basis = old.get('reconciliationBasis')
        self.assertIsNotNone(basis, 'known-stopped external lease has no public reconciliation basis')
        self.assertFalse(fresh('reconcile', operationId=operation_id, epoch=contract['epoch'],
            expectedRevision=contract['expectedRevision'], deadlineMs=int(time.time()*1000)+10000, **basis)['isError'])
        waiting = self.execution_until(fresh, operation_id, lambda x: x['reviewRequest'] is not None)
        review = waiting['reviewRequest']
        self.assertEqual(review['stage'], 'external-known-stopped')
        if mode == 'record-change':
            body = fresh('read-evidence', operationId=operation_id,
                evidenceId=review['observationSha256'], maxChars=16000)['structuredContent']
            scope = json.loads(body['text'])['original']['state']['scopeRef']
            script = "const r=require(process.argv[1]).openCarrierRecorder({path:process.argv[2]});const s=r.read(process.argv[3],process.argv[4]);r.compareAndSet(process.argv[3],s.revision,s.state,s.lease);r.close();"
            changed = subprocess.run([self.node, '-e', script, str(BRIDGE.with_name('carrier-recorder.cjs')),
                str(next(self.state.rglob('carrier.sqlite'))), operation_id, scope], capture_output=True, timeout=5)
            self.assertEqual(changed.returncode, 0, changed.stderr)
        if mode == 'source-paused':
            self.assertFalse(self.manage(action='pause', epoch=contract['epoch'],
                expectedRevision=contract['expectedRevision'], reason='User paused before settlement.')['isError'])
        decision = fresh('review', operationId=operation_id, reviewId=review['reviewId'],
            observationSha256=review['observationSha256'], decision='allow',
            sourceRef='independent-old-actor-and-resource-effect-review')
        if mode in ('record-change', 'source-paused'):
            self.assertTrue(decision['isError'], decision)
            self.assertEqual(decision['structuredContent']['reason'],
                'stopped-record-basis-changed' if mode == 'record-change' else 'current-source-not-executable')
            self.assertEqual((self.root/'native-wire.jsonl').read_bytes(), wire_before)
            self.assertIsNotNone(fresh('inspect', operationId=operation_id)['structuredContent']['reconciliationBasis'])
            return
        self.assertFalse(decision['isError'], decision)
        stopped = fresh('inspect', operationId=operation_id)['structuredContent']
        self.assertEqual(stopped['phase'], 'external-source-retained')
        evidence = fresh('read-evidence', operationId=operation_id,
            evidenceId=stopped['stateEvidence']['evidenceId'], maxChars=16000)['structuredContent']
        record = json.loads(evidence['text'])
        self.assertEqual(record['plan']['deadlineMs'], original_deadline)
        self.assertEqual(record['failure'], record['reconciliation']['originalFailure'])
        self.assertEqual(record['reconciliation']['originalDeadlineMs'], original_deadline)
        self.assertEqual(record['reconciliation']['currentSource']['turnId'], 'current-recovery-turn')
        if mode == 'expired':
            self.assertLess(original_deadline, int(time.time()*1000))
            self.assertEqual(record['failure']['code'], 'DEADLINE_EXCEEDED')
            contract['deadlineMs'] = int(time.time()*1000)+20000
        self.assertEqual((self.root/'native-wire.jsonl').read_bytes(), wire_before)
        retried = fresh('prepare', **contract)
        self.assertFalse(retried['isError'], retried)
        retry_id = retried['structuredContent']['operationId']
        self.execution_until(fresh, retry_id, lambda x: x['reviewRequest'] is not None)
        self.assertEqual((self.root/'native-wire.jsonl').read_bytes(), wire_before)
        self.assertFalse(fresh('cancel', operationId=retry_id, reason='fixture completed without replay')['isError'])

    def test_target_effect_reconciliation_returns_same_scope_to_current_source(self):
        self.check_target_effect_reconciliation('source-current')

    def test_target_effect_reconciliation_retains_ack_loss_without_replaying(self):
        self.check_target_effect_reconciliation('ack-loss')

    def test_target_effect_reconciliation_retains_target_unless_source_explicitly_selected(self):
        self.check_target_effect_reconciliation('target-retained')

    def test_target_effect_reconciliation_rejects_stale_basis(self):
        self.check_target_effect_reconciliation('stale')

    def test_target_effect_reconciliation_rejects_unknown_material_effects(self):
        self.check_target_effect_reconciliation('unknown')

    def test_target_effect_reconciliation_holds_paused_source(self):
        self.check_target_effect_reconciliation('paused')

    def test_target_effect_reconciliation_holds_native_target_activity(self):
        self.check_target_effect_reconciliation('active-target')

    def test_target_effect_reconciliation_rechecks_outputs_before_settlement(self):
        self.check_target_effect_reconciliation('effect-drift')

    def test_target_effect_reconciliation_rechecks_lease_before_settlement(self):
        self.check_target_effect_reconciliation('lease-drift')

    def test_target_effect_reconciliation_cancel_closes_only_reader(self):
        self.check_target_effect_reconciliation('cancel')

    def test_target_effect_reconciliation_does_not_retry_uncertain_settlement(self):
        self.check_target_effect_reconciliation('settlement-unknown')

    def test_target_effect_reconciliation_keeps_original_input_invariants(self):
        self.check_target_effect_reconciliation('input-change')

    def test_target_effect_reconciliation_rechecks_native_facts(self):
        self.check_target_effect_reconciliation('native-drift')

    def test_target_effect_reconciled_slot_is_durably_reclaimable(self):
        self.check_target_effect_reconciliation('reclaim')

    def test_completed_intake_source_lease_uses_effect_reconciliation_without_replay(self):
        self.check_target_effect_reconciliation('source-intake')

    def test_completed_intake_reconciliation_cannot_grant_untransferred_writer(self):
        self.check_target_effect_reconciliation('source-intake-grant-target')

    def test_completed_intake_reconciliation_rechecks_native_turns(self):
        self.check_target_effect_reconciliation('source-intake-native-drift')

    def test_policy_denied_source_lease_uses_effect_reconciliation(self):
        self.check_target_effect_reconciliation('source-policy')

    def test_requirements_denied_source_lease_uses_effect_reconciliation(self):
        self.check_target_effect_reconciliation('source-requirements')

    def test_missing_policy_ack_preserves_effect_reconciliation(self):
        self.check_target_effect_reconciliation('source-policy-missing')

    def test_policy_prepared_commit_denial_keeps_source_recovery(self):
        self.check_target_effect_reconciliation('source-policy-commit-denied')

    def test_completed_intake_reconciliation_at_full_reference_capacity(self):
        self.check_target_effect_reconciliation('source-intake-capacity')

    def test_full_capacity_reconciliation_rechecks_effect_source_bytes(self):
        self.check_target_effect_reconciliation('source-intake-capacity-effect-source-drift')

    def test_full_capacity_reconciliation_preserves_original_input_invariants(self):
        self.check_target_effect_reconciliation('source-intake-capacity-input-change')

    def test_full_capacity_reconciliation_preserves_original_output_contract(self):
        self.check_target_effect_reconciliation('source-intake-capacity-output-change')

    def test_full_capacity_reconciliation_rejects_effect_source_escape(self):
        self.check_target_effect_reconciliation('source-intake-capacity-effect-escape')

    def test_full_capacity_reconciliation_rejects_effect_source_symlink(self):
        self.check_target_effect_reconciliation('source-intake-capacity-effect-symlink')

    def test_full_capacity_reconciliation_rejects_effect_source_hardlink(self):
        self.check_target_effect_reconciliation('source-intake-capacity-effect-hardlink')

    def test_reconciliation_accepts_independently_reviewed_new_reader_version(self):
        self.check_target_effect_reconciliation('source-intake-reader-new')

    def test_reconciliation_rejects_empty_reader_version(self):
        self.check_target_effect_reconciliation('source-intake-reader-empty')

    def test_reconciliation_rejects_original_reader_connection(self):
        self.check_target_effect_reconciliation('source-intake-reader-old-connection')

    def test_reconciliation_rejects_prior_reader_connection(self):
        self.check_target_effect_reconciliation('source-policy-reader-prior-connection')

    def test_reconciliation_rejects_reader_identity_drift(self):
        self.check_target_effect_reconciliation('source-intake-reader-drift')

    def test_reconciliation_rejects_unbound_reader_request_reference(self):
        self.check_target_effect_reconciliation('source-intake-reader-bad-ref')

    def test_reconciliation_rejects_missing_original_turn(self):
        self.check_target_effect_reconciliation('source-intake-reader-missing')

    def test_reconciliation_rejects_wrong_original_turn(self):
        self.check_target_effect_reconciliation('source-intake-reader-wrong')

    def test_reconciliation_rejects_duplicate_original_turn(self):
        self.check_target_effect_reconciliation('source-intake-reader-duplicate')

    def test_reconciliation_rejects_extra_original_turn(self):
        self.check_target_effect_reconciliation('source-intake-reader-extra')

    def test_reconciliation_rejects_nonterminal_original_turn(self):
        self.check_target_effect_reconciliation('source-intake-reader-nonterminal')

    def check_target_effect_reconciliation(self, mode):
        contract = self.execution_write_contract()
        capacity = mode.startswith('source-intake-capacity')
        # Full-capacity filesystem verification has a separate prospective fixture budget.
        phase_timeout = 30 if capacity else 8
        protected_inputs = ['drain.json']
        if capacity:
            for index in range(98):
                name = 'protected-%02d.txt' % index
                (self.work/name).write_text('Immutable fixture input %d' % index, encoding='utf-8')
                protected_inputs.append(name)
            current = self.native_input_preview()
            self.assertFalse(self.manage(action='bind', epoch=current['epoch'], expectedRevision=current['revision'],
                result='Review the authorized fixed candidate', inputs=protected_inputs,
                outputs=[{'path': 'review.json'}], nextAction='Read-only intake at full capacity', canContinue=True)['isError'])
            current = self.native_input_preview()
            self.assertEqual(len(current['checkpoint']['inputs']), 99)
            self.assertEqual(len(current['checkpoint']['outputs']), 1)
            contract.update(epoch=current['epoch'], expectedRevision=current['revision'],
                            deadlineMs=int(time.time()*1000)+60000)
        policy_mode = {'source-policy': 'policy-readonly', 'source-policy-missing': 'policy-missing', 'source-requirements': 'requirements-deny',
                       'source-policy-commit-denied': 'workspace-write',
                       'source-policy-reader-prior-connection': 'policy-readonly'}.get(mode)
        source_intake = mode.startswith('source-intake') or policy_mode is not None
        process, _, _, call = self.start_execution_wire(peer_mode=policy_mode or ('normal' if source_intake else 'write-ack-loss' if mode=='ack-loss' else 'write-interrupted'))
        operation_id = self.execution_intake(call, contract, timeout=phase_timeout)
        if policy_mode:
            call('commit', operationId=operation_id)
            self.execution_accept(call, operation_id, 'write-prepare', timeout=phase_timeout)
            if mode == 'source-policy-commit-denied':
                waiting = self.execution_until(call, operation_id, lambda x: x['reviewRequest'] is not None, timeout=phase_timeout)
                review = waiting['reviewRequest']
                self.assertEqual(review['stage'], 'commit')
                call('review', operationId=operation_id, reviewId=review['reviewId'],
                     observationSha256=review['observationSha256'], decision='deny', sourceRef='fixed-commit-denial')
            old = self.execution_until(call, operation_id, lambda x: x['phase']=='held', timeout=phase_timeout)
        elif not source_intake:
            call('commit', operationId=operation_id)
            for stage in ('write-prepare', 'commit'):
                self.execution_accept(call, operation_id, stage, timeout=phase_timeout)
        if source_intake and not policy_mode:
            old = call('cancel', operationId=operation_id, reason='Actual user pause after read-only intake')['structuredContent']
        elif mode == 'ack-loss':
            self.execution_until(call, operation_id, lambda x: x['writer']=='target' and x['pendingEffect']
                and x['pendingEffect']['method']=='turn/start' and x['pendingEffect']['requestRef'], timeout=phase_timeout)
            old = call('cancel', operationId=operation_id, reason='Inspect uncertain ACK and actual partial effects')['structuredContent']
        else:
            old = self.execution_until(call, operation_id, lambda x: x['phase']=='held', timeout=phase_timeout)
        process.stdin.close(); process.wait(timeout=5)
        original_writer = 'source' if source_intake else 'target'
        self.assertEqual(old['writer'], original_writer)
        if source_intake:
            self.assertFalse((self.work/'review.json').exists())
        old_bytes = None if source_intake else (self.work/'review.json').read_bytes()
        reader_mode = mode.split('reader-', 1)[1] if 'reader-' in mode else None
        old_state = None
        if reader_mode:
            old_state = json.loads(next(self.state.rglob(old['stateEvidence']['sha256']+'.json')).read_text(encoding='utf-8'))
            if reader_mode in ('old-connection', 'prior-connection'):
                connection = old_state['connection'] if reader_mode=='old-connection' else old_state['priorNative']['connection']
                self.env['ACCORD_TEST_READER_CONNECTION_ID'] = connection['connectionId']
            if reader_mode == 'new':
                history = self.root/'native-wire.jsonl.turns.json'
                turns = json.loads(history.read_text())
                turns[0]['items'] = [{'id': 'original-item', 'type': 'agentMessage', 'text': 'Persistent original item'}]
                history.write_text(json.dumps(turns), encoding='utf-8')
            if reader_mode in ('missing', 'wrong', 'duplicate', 'extra', 'nonterminal'):
                history = self.root/'native-wire.jsonl.turns.json'
                turns = json.loads(history.read_text())
                if reader_mode=='missing': turns = []
                elif reader_mode=='wrong': turns[0]['id'] = 'wrong-turn'
                elif reader_mode=='duplicate': turns += [dict(turns[0])]
                elif reader_mode=='extra': turns += [{'id': 'extra-turn', 'status': 'completed'}]
                else: turns[0]['status'] = 'inProgress'
                history.write_text(json.dumps(turns), encoding='utf-8')
        _, _, _, fresh = self.start_execution_wire(peer_mode='reader-'+reader_mode if reader_mode else
            'target-still-active' if mode=='active-target' else None)
        self.env.pop('ACCORD_TEST_READER_CONNECTION_ID', None)
        old = fresh('inspect', operationId=operation_id)['structuredContent']
        basis = old.get('targetReconciliationBasis')
        self.assertIsNotNone(basis, 'known-stopped target has no typed effect reconciliation basis: '+self.execution_failure_context(old))
        effect = self.work/'effects.json'
        effect_ref = 'effects.json'
        effect.write_text(json.dumps({'kind': 'external-target-effects/v1', 'operationId': operation_id,
            'recordSha256': basis['recordSha256'], 'actorSourceRef': 'fixed-old-peer-natural-close-and-exclusive-owner',
            'authoritySourceRef': 'new-current-fixture-input',
            'effects': [{'disposition': 'partial-effects-reviewed', 'sourceRef': 'independent-fixed-review.json-bytes'}],
            'unresolved': ['external-service-effect-still-unknown'] if mode=='unknown' else []}), encoding='utf-8')
        if mode == 'source-intake-capacity-effect-escape':
            (self.root/'effects.json').write_bytes(effect.read_bytes())
            effect_ref = '../effects.json'
        if mode in ('source-intake-capacity-effect-symlink', 'source-intake-capacity-effect-hardlink'):
            link = self.work/'effects-link.json'
            try:
                if mode.endswith('symlink'):
                    link.symlink_to(effect)
                else:
                    os.link(effect, link)
            except (OSError, NotImplementedError) as error:
                self.skipTest('Fixture link creation unavailable: '+str(error))
            effect_ref = link.name
        meta = self.params['_meta']['x-codex-turn-metadata']
        meta['turn_id'] = 'target-recovery-turn'
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        with transcript.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'type': 'turn_context', 'payload': {
                'turn_id': meta['turn_id'], 'model': meta['model'], 'cwd': str(self.work)}})+'\n')
        prompt = 'Review the stopped partial effects and take back the remaining current task.'
        self.append_native_message(text=prompt)
        self.helper({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt, 'turn_id': meta['turn_id'],
            'model': meta['model'], 'transcript_path': str(transcript)}, session=meta['session_id'], hook='UserPromptSubmit')
        current = self.native_input_preview()
        revised_inputs = {}
        if mode in ('input-change', 'source-intake-capacity-input-change'):
            (self.work/'drain.json').write_text('A different current source does not erase the original invariant.', encoding='utf-8')
            revised_inputs = {'revisionReason': 'Explicit fixture input change', 'inputRevisions': [{
                'path': 'drain.json', 'observed': {'present': True, 'sha256': hashlib.sha256((self.work/'drain.json').read_bytes()).hexdigest()},
                'reason': 'Explicit fixture source revision; original recovery still must reject this unsupported change.'}]}
        if mode == 'source-intake-capacity-output-change':
            revised_inputs['revisionReason'] = 'Explicit fixture output revision; recovery must still preserve the original output contract.'
        self.assertFalse(self.manage(action='bind', epoch=current['epoch'], expectedRevision=current['revision'],
            result='Review the authorized fixed candidate', inputs=protected_inputs if capacity else ['drain.json', 'effects.json'],
            outputs=[{'path': 'changed-review.json' if mode=='source-intake-capacity-output-change' else 'review.json'}],
            nextAction='Reconcile actual effects without replay', canContinue=True, **revised_inputs)['isError'])
        current = self.native_input_preview()
        args = dict(operationId=operation_id, epoch=current['epoch'], expectedRevision=current['revision'],
            deadlineMs=int(time.time()*1000)+(60000 if capacity else 20000), writerDisposition='target-retained' if mode in ('target-retained', 'source-intake-grant-target') else 'source-current', effectSourceRef=effect_ref, **basis)
        if mode == 'stale':
            args['recordRevision'] += 1
        if mode == 'paused':
            self.assertFalse(self.manage(action='pause', epoch=current['epoch'], expectedRevision=current['revision'],
                reason='Fixture user has not authorized resumption.')['isError'])
        before_turns = sum(json.loads(line)['method']=='turn/start' for line in (self.root/'native-wire.jsonl').read_text().splitlines())
        reply = fresh('reconcile-target', **args)
        if mode in ('stale', 'unknown', 'paused', 'input-change', 'source-intake-grant-target',
                    'source-intake-capacity-input-change', 'source-intake-capacity-output-change',
                    'source-intake-capacity-effect-escape', 'source-intake-capacity-effect-symlink',
                    'source-intake-capacity-effect-hardlink'):
            self.assertTrue(reply['isError'], reply)
            self.assertEqual(reply['structuredContent']['reason'], {'stale': 'stopped-record-basis-changed',
                'unknown': 'target-effects-unresolved', 'paused': 'current-source-not-executable',
                'input-change': 'original-input-invariants-changed',
                'source-intake-grant-target': 'source-writer-must-remain-current',
                'source-intake-capacity-input-change': 'original-input-invariants-changed',
                'source-intake-capacity-output-change': 'original-output-contract-changed',
                'source-intake-capacity-effect-escape': 'unsafe-effect-source',
                'source-intake-capacity-effect-symlink': 'unsafe-execution-evidence',
                'source-intake-capacity-effect-hardlink': 'unsafe-execution-evidence'}[mode])
            self.assertEqual(fresh('inspect', operationId=operation_id)['structuredContent']['writer'], original_writer)
            return
        self.assertFalse(reply['isError'], reply)
        waiting = self.execution_until(fresh, operation_id, lambda x: x['reviewRequest'] is not None or
            x['phase'] in ('held', 'cancelled-held') and not x['busy'], timeout=phase_timeout)
        if reader_mode in ('empty', 'old-connection', 'prior-connection', 'bad-ref', 'missing', 'wrong', 'duplicate', 'extra', 'nonterminal'):
            self.assertIn(waiting['failure'], ('target-reader-identity-changed', 'target-activity-unresolved', 'target-terminal-evidence-mismatch'))
            self.assertEqual(waiting['writer'], original_writer)
            self.assertEqual(waiting['targetRecoveryResource']['state'], 'closed')
            return
        if mode == 'active-target':
            self.assertEqual(waiting['failure'], 'target-activity-unresolved')
            self.assertEqual(waiting['writer'], 'target')
            self.assertEqual(waiting['targetRecoveryResource']['state'], 'closed')
            return
        self.assertIsNotNone(waiting['reviewRequest'], waiting)
        self.assertEqual(waiting['reviewRequest']['stage'], 'external-known-stopped-target')
        if reader_mode:
            packet = json.loads(fresh('read-evidence', operationId=operation_id,
                evidenceId=waiting['reviewRequest']['observationSha256'], maxChars=16000)['structuredContent']['text'])
            self.assertEqual(packet['nativeReader']['hostVersion'], 'fixed-native-fixture-next')
            self.assertEqual(packet['nativeReader']['originalHostVersion'], old_state['connection']['hostVersion'])
            self.assertTrue(packet['nativeReader']['versionChanged'])
            if reader_mode == 'new':
                facts = json.loads(fresh('read-evidence', operationId=operation_id,
                    evidenceId=packet['nativeFactsEvidence']['evidenceId'], maxChars=16000)['structuredContent']['text'])
                self.assertEqual(facts['turns'][0]['items'][0]['text'], 'Persistent original item')
        if reader_mode == 'drift':
            review = waiting['reviewRequest']
            rejected = fresh('review', operationId=operation_id, reviewId=review['reviewId'],
                observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-reader-review')
            self.assertTrue(rejected['isError'], rejected)
            stopped = fresh('inspect', operationId=operation_id)['structuredContent']
            self.assertEqual(stopped['writer'], original_writer)
            self.assertEqual(stopped['targetRecoveryResource']['state'], 'closed')
            return
        if mode == 'cancel':
            stopped = fresh('cancel', operationId=operation_id, reason='Stop administrative recovery')['structuredContent']
            self.assertEqual(stopped['writer'], 'target')
            self.assertEqual(stopped['targetRecoveryResource']['state'], 'closed')
            return
        if mode == 'settlement-unknown':
            import sqlite3
            from contextlib import closing
            database = next(self.state.rglob('carrier.sqlite'))
            with closing(sqlite3.connect(database)) as connection:
                connection.execute("CREATE TRIGGER fail_recovery_scope BEFORE UPDATE ON scopes BEGIN SELECT RAISE(ABORT,'fixture settlement uncertainty'); END")
            try:
                review = waiting['reviewRequest']
                failed = fresh('review', operationId=operation_id, reviewId=review['reviewId'],
                    observationSha256=review['observationSha256'], decision='allow', sourceRef='fixed-independent-effect-review')
                self.assertTrue(failed['isError'], failed)
            finally:
                with closing(sqlite3.connect(database)) as connection:
                    connection.execute('DROP TRIGGER fail_recovery_scope')
            held = fresh('inspect', operationId=operation_id)['structuredContent']
            self.assertEqual(held['writer'], 'target')
            self.assertEqual(held['targetSettlementAttempt']['state'], 'outcome-unknown')
            self.assertEqual(held['targetRecoveryResource']['state'], 'closed')
            wire = (self.root/'native-wire.jsonl').read_bytes()
            retried = fresh('reconcile-target', **args)
            self.assertEqual(retried['structuredContent']['reason'], 'target-settlement-unknown')
            self.assertEqual((self.root/'native-wire.jsonl').read_bytes(), wire)
            return
        if capacity:
            packet = json.loads(fresh('read-evidence', operationId=operation_id,
                evidenceId=waiting['reviewRequest']['observationSha256'], maxChars=16000)['structuredContent']['text'])
            evidence = packet['material']['effectSource']['evidence']
            source = json.loads(fresh('read-evidence', operationId=operation_id,
                evidenceId=evidence['evidenceId'], maxChars=16000)['structuredContent']['text'])
            self.assertEqual(base64.b64decode(source['contentsBase64']), effect.read_bytes())
            self.assertEqual(source['sha256'], hashlib.sha256(effect.read_bytes()).hexdigest())
        if mode == 'source-intake-capacity-effect-source-drift':
            effect.write_bytes(effect.read_bytes()+b'\n')  # Same parsed value, different exact source bytes.
        if mode == 'effect-drift':
            (self.work/'review.json').write_text('another effect after review snapshot', encoding='utf-8')
        if mode in ('native-drift', 'source-intake-native-drift'):
            history = self.root/'native-wire.jsonl.turns.json'
            history.write_text(json.dumps(json.loads(history.read_text())+[{'id': 'unowned-extra-turn', 'status': 'completed'}]), encoding='utf-8')
        if mode == 'lease-drift':
            state_page = fresh('read-evidence', operationId=operation_id,
                evidenceId=waiting['stateEvidence']['sha256'], maxChars=16000)['structuredContent']
            scope = json.loads(state_page['text'])['scopeRef']
            script = "const r=require(process.argv[1]).openCarrierRecorder({path:process.argv[2]});const x=r.read(process.argv[3],process.argv[4]);r.compareAndSet(process.argv[3],x.revision,x.state,x.lease);r.close();"
            mutation = subprocess.run([self.node, '-e', script, str(BRIDGE.with_name('carrier-recorder.cjs')),
                str(next(self.state.rglob('carrier.sqlite'))), operation_id, scope], capture_output=True, timeout=5)
            self.assertEqual(mutation.returncode, 0, mutation.stderr)
        if mode in ('effect-drift', 'lease-drift', 'native-drift', 'source-intake-native-drift',
                    'source-intake-capacity-effect-source-drift'):
            review = waiting['reviewRequest']
            rejected = fresh('review', operationId=operation_id, reviewId=review['reviewId'],
                observationSha256=review['observationSha256'], decision='allow', sourceRef='stale-independent-judgment')
            self.assertTrue(rejected['isError'], rejected)
            held = self.execution_until(fresh, operation_id, lambda x: x['phase'] in ('held', 'cancelled-held'), timeout=phase_timeout)
            self.assertEqual(held['writer'], original_writer)
            self.assertEqual(held['targetRecoveryResource']['state'], 'closed')
            return
        self.execution_accept(fresh, operation_id, 'external-known-stopped-target', timeout=phase_timeout)
        done = self.execution_until(fresh, operation_id, lambda x: x['phase']=='external-target-reconciled', timeout=phase_timeout)
        self.assertEqual(done['writer'], 'target' if mode=='target-retained' else 'source')
        self.assertEqual(done['scopeBinding']['requestedScope'], contract['scopeRef'])
        if source_intake:
            self.assertFalse((self.work/'review.json').exists())
        else:
            self.assertEqual((self.work/'review.json').read_bytes(), old_bytes)
        if capacity:
            after = self.native_input_preview()
            self.assertEqual([row['path'] for row in after['checkpoint']['inputs']], protected_inputs)
            self.assertEqual(after['checkpoint']['outputs'], [{'path': 'review.json'}])
        self.assertEqual(sum(json.loads(line)['method']=='turn/start' for line in (self.root/'native-wire.jsonl').read_text().splitlines()), before_turns)
        state = json.loads(fresh('read-evidence', operationId=operation_id,
            evidenceId=done['stateEvidence']['sha256'], maxChars=16000)['structuredContent']['text'])
        if reader_mode:
            self.assertEqual(state['reconciliation']['nativeReader'], packet['nativeReader'])
            self.assertEqual(state['reconciliation']['nativeReadRequest']['connectionId'], packet['nativeReader']['connectionId'])
            self.assertEqual(state['reconciliation']['nativeReadRequest']['hostVersion'], packet['nativeReader']['hostVersion'])
            self.assertNotEqual(state['reconciliation']['nativeReadRequest']['requestId'], packet['readRequest']['requestId'])
        self.assertEqual(state['failure'], state['reconciliation']['originalFailure'])
        self.assertEqual(state['plan']['deadlineMs'], contract['deadlineMs'])
        self.assertEqual(state['reconciliation']['originalDeadlineMs'], contract['deadlineMs'])
        self.assertNotIn('release', state)
        self.assertEqual(state['reconciliation']['currentSource']['turnId'], 'target-recovery-turn')
        if mode == 'ack-loss':
            self.assertEqual(state['reconciliation']['originalPendingEffect']['requestRef']['method'], 'turn/start')
        contract.update(epoch=current['epoch'], expectedRevision=current['revision'], deadlineMs=int(time.time()*1000)+(60000 if capacity else 20000))
        contract['writeScope']['outputs'][0]['expectedSha256'] = hashlib.sha256(old_bytes).hexdigest() if old_bytes is not None else None
        again = fresh('prepare', **contract)
        if mode == 'target-retained':
            self.assertEqual(again['structuredContent']['reason'], 'WRITER_CONFLICT')
            return
        self.assertFalse(again['isError'], again)
        fresh('cancel', operationId=again['structuredContent']['operationId'], reason='No business replay in fixture')
        if mode == 'reclaim':
            contract['deadlineMs'] = int(time.time()*1000)+60000
            for number in range(14):
                transient = fresh('prepare', **{**contract, 'scopeRef': 'denied-after-recovery-'+str(number)})['structuredContent']['operationId']
                request = self.execution_until(fresh, transient, lambda x: x['reviewRequest'] is not None, timeout=phase_timeout)['reviewRequest']
                fresh('review', operationId=transient, reviewId=request['reviewId'],
                    observationSha256=request['observationSha256'], decision='deny', sourceRef='fixed-denial')
                self.execution_until(fresh, transient, lambda x: x['phase']=='held' and not x['busy'], timeout=phase_timeout)
            following = fresh('prepare', **contract)
            self.assertFalse(following['isError'], following)
            self.assertEqual(fresh('inspect', operationId=operation_id)['structuredContent']['controllerState'], 'not-owned-current-process')
            fresh('cancel', operationId=following['structuredContent']['operationId'], reason='capacity check complete')

    def test_transport_backpressure_bounds_synchronous_and_invalid_responses(self):
        script = """
const {Readable,Writable}=require('node:stream');
const bridge=require(process.argv[1]);
(async()=>{
  const results=[];
  for(const invalid of [false,true]){
    let pulls=0,writes=0,release;
    const input=Readable.from((async function*(){
      for(let id=0;id<200;id++){
        pulls++;yield Buffer.from(invalid?'null!\\n':JSON.stringify({jsonrpc:'2.0',id,method:'ping'})+'\\n');
      }
    })());
    const output=new Writable({highWaterMark:1,write(chunk,encoding,done){
      writes++;if(writes===1)release=done;else done();
    }});
    const running=bridge.serve(input,output,'fixed-backpressure');
    await new Promise(resolve=>setTimeout(resolve,30));
    const blocked=pulls;release();await running;
    results.push({blocked,writes});
  }
  console.log(JSON.stringify(results));
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE)], capture_output=True,
                             env=self.env, cwd=self.work, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        for result in json.loads(run.stdout):
            self.assertLessEqual(result['blocked'], 2)
            self.assertEqual(result['writes'], 200)

    def test_execution_handler_preserves_numeric_and_string_request_ids_for_cancellation(self):
        script = r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const [mcpFile,executionFile]=process.argv.slice(-2);
if(path.basename(mcpFile)!=='native-state-mcp.cjs'||path.basename(executionFile)!=='native-task-execution.cjs')throw Error('Explicit actual module paths required');
const memory=new Map(),cancelled=[];
const stat=(f=false)=>({isDirectory:()=>!f,isFile:()=>f,isSymbolicLink:()=>false,nlink:1,size:0,ino:1n,dev:1n});
const memfs={existsSync:p=>memory.has(p)||!(/\.(json|sqlite|tmp)$/.test(p)),realpathSync:p=>path.resolve(p),lstatSync:p=>({...stat(memory.has(p)),size:memory.get(p)?.length||0}),mkdirSync(){},writeFileSync(p,v){memory.set(p,Buffer.from(v));},readFileSync:p=>memory.get(p),openSync:p=>p,fsyncSync(){},closeSync(){},renameSync(a,b){memory.set(b,memory.get(a));memory.delete(a);},unlinkSync:p=>memory.delete(p),rmdirSync(){}};
let nativeExports;
const fakeEngine=()=>{let s={phase:'new',busy:false,writer:'source',sourceRecovery:'retained',turnStarts:0},done,id;return{inspect:()=>s,prepare(p){id=p.transferId;s={...s,phase:'awaiting-review',busy:true};return new Promise(r=>done=r);},async cancel(){cancelled.push(id);s={...s,phase:'cancelled-held',busy:false};done?.();}}};
const forbid=()=>{throw Error('REAL_PROCESS_OR_NATIVE_FORBIDDEN');};
const fakeRequire=n=>n==='node:fs'?memfs:n==='node:child_process'?{spawn:forbid,spawnSync:forbid}:n==='./task-checkpoint.cjs'?{}:n==='./codex-capabilities.cjs'?{}:n==='./external-handoff.cjs'?{createExternalHandoff:fakeEngine}:n==='./native-task-execution.cjs'?nativeExports:n==='./carrier-recorder.cjs'?{openCarrierRecorder:()=>({readScope(){throw Object.assign(Error('SCOPE_NOT_FOUND'),{code:'SCOPE_NOT_FOUND'});},read:forbid,close(){}})}:require(n);
function load(file){const raw=fs.readFileSync(file,'utf8'),box={module:{exports:{}},exports:{},require:fakeRequire,process:{platform:process.platform,env:{},pid:999},Buffer,TextDecoder,Date,Map,Set,setTimeout,clearTimeout,__filename:file,__dirname:path.dirname(file)};vm.runInNewContext(raw,box,{filename:file});return {exports:box.module.exports,sha256:crypto.createHash('sha256').update(raw).digest('hex')};}
const native=load(executionFile);nativeExports=native.exports;const bridge=load(mcpFile);
const cwd=path.resolve('mock-request-id-work'),snapshot={epoch:'epoch',revision:1,mode:'active',checkpoint:{canContinue:true},inputReceipt:{present:true},hostObservationCurrent:true,currentInputReconciled:true,nativeInputEvidence:{state:'observed',latestInputReconciled:true,latestNativeInputsComplete:true,pendingInputs:[]},checkpointSource:{sha256:'a'.repeat(64)},inspection:{inputs:[{path:'q.json',current:{present:true,sha256:'a'.repeat(64)},unchanged:true,stable:true}]}};
const h=bridge.exports.createHandler('controlled-in-memory',{readState:()=>snapshot,storageRoot:path.resolve('mock-request-id-store'),nativeFactory:forbid});
h({jsonrpc:'2.0',id:0,method:'initialize',params:{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'memory-proof',version:'1'}}});h({jsonrpc:'2.0',method:'notifications/initialized'});
const params=(scope,callId)=>({name:'coordinate_task_execution',_meta:{callId,'x-codex-turn-metadata':{thread_id:'root',session_id:'root',turn_id:'turn',model:'model',codex_version:'host'}},arguments:{action:'prepare',cwd,epoch:'epoch',expectedRevision:1,scopeRef:scope,model:'model',intake:'read',continuation:'continue',postRelease:'finish',deadlineMs:Date.now()+10000,authoritySourceRef:'authority',quiescenceSourceRef:'q.json'}});
const cancel=async id=>{h({jsonrpc:'2.0',method:'notifications/cancelled',params:{requestId:id}});await new Promise(setImmediate);};
(async()=>{let result;try{const a=await h({jsonrpc:'2.0',id:1,method:'tools/call',params:params('scopeA','callA')}),b=await h({jsonrpc:'2.0',id:'1',method:'tools/call',params:params('scopeB','callB')});if(a.result.isError||b.result.isError)throw Error(JSON.stringify({a,b}));const A=a.result.structuredContent.operationId,B=b.result.structuredContent.operationId;await cancel(1);const afterNumeric=cancelled.slice();await cancel('1');const afterString=cancelled.slice();await cancel(1);await cancel('1');result={kind:'actual-MCP-handler-and-task-execution-in-memory',mcpSourceSha256:bridge.sha256,executionSourceSha256:native.sha256,responseIds:[a.id,b.id],responseIdTypes:[typeof a.id,typeof b.id],numericOperation:A,stringOperation:B,afterNumeric,afterString,afterRepeated:cancelled.slice(),numericCancellationCorrect:afterNumeric.length===1&&afterNumeric[0]===A,stringCancellationCorrect:afterString.length===2&&afterString[0]===A&&afterString[1]===B,cleanupRemovedRequestAssociations:cancelled.length===2,noNativeOrModel:true,noRealFsWrites:true};}finally{await h.close();}console.log(JSON.stringify(result));})().catch(e=>{console.error(e.stack);process.exitCode=1;});

"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE),
                              str(BRIDGE.with_name('native-task-execution.cjs'))],
                             capture_output=True, text=True, encoding='utf-8',
                             env=self.env, cwd=self.work, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['responseIds'], [1, '1'])
        self.assertEqual(result['responseIdTypes'], ['number', 'string'])
        self.assertNotEqual(result['numericOperation'], result['stringOperation'])
        self.assertEqual(result['afterNumeric'], [result['numericOperation']])
        self.assertEqual(result['afterString'], [result['numericOperation'], result['stringOperation']])
        self.assertEqual(result['afterRepeated'], result['afterString'])
        self.assertTrue(result['noNativeOrModel'])
        self.assertTrue(result['noRealFsWrites'])

    def test_transport_limit_keeps_cancel_ping_and_invalid_input_responsive(self):
        script = """
const {Readable,Writable}=require('node:stream');
const execution=require(process.argv[2]);
let cancelled=0,closed=0,pending=[];
execution.createNativeTaskExecution=()=>({observe(){},
  call(){return new Promise(resolve=>pending.push(resolve));},
  async cancelRequest(){cancelled++;},
  async close(){closed++;pending.forEach(resolve=>resolve({isError:false,value:{fixture:true}}));}
});
const bridge=require(process.argv[1]);
const frames=[{jsonrpc:'2.0',id:0,method:'initialize',params:{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'fixture',version:'1'}}},
  {jsonrpc:'2.0',method:'notifications/initialized'}];
for(let id=1;id<=64;id++)frames.push({jsonrpc:'2.0',id,method:'tools/call',params:{name:'coordinate_task_execution'}});
frames.push({jsonrpc:'2.0',method:'notifications/cancelled',params:{requestId:1}},
  {jsonrpc:'2.0',id:100,method:'ping'},null,
  {jsonrpc:'2.0',id:101,method:'tools/call',params:{name:'coordinate_task_execution'}});
const rows=[];
const output=new Writable({write(chunk,encoding,done){rows.push(JSON.parse(chunk));done();}});
bridge.serve(Readable.from([Buffer.from(frames.map(x=>JSON.stringify(x)).join('\\n')+'\\n')]),output,'fixed-overload')
  .then(()=>console.log(JSON.stringify({cancelled,closed,rows})))
  .catch(error=>{console.error(error);process.exitCode=1;});
"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE),
                              str(BRIDGE.with_name('native-task-execution.cjs'))],
                             capture_output=True, env=self.env, cwd=self.work, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual((result['cancelled'], result['closed']), (1, 1))
        rows = {row['id']: row for row in result['rows']}
        self.assertEqual(len(rows), 68)
        self.assertEqual(rows[100]['result'], {})
        self.assertEqual(rows[101]['error']['code'], -32001)
        self.assertEqual(rows[None]['error']['code'], -32600)
        self.assertTrue(all(rows[i]['result']['structuredContent']['fixture'] for i in range(1, 65)))

    def test_closed_transport_releases_owned_work_during_backpressure_or_idle_read(self):
        script = """
const {PassThrough,Writable}=require('node:stream');
const execution=require(process.argv[2]);
let closed=0,resolve;
execution.createNativeTaskExecution=()=>({observe(){},
  call(){return new Promise(done=>{resolve=done;});},async cancelRequest(){},
  async close(){closed++;resolve?.({isError:false,value:{fixture:true}});}
});
const bridge=require(process.argv[1]);
(async()=>{
  const reports=[];
  for(const mode of ['blocked-output','idle-output','blocked-input']){
    const input=new PassThrough();let writes=0;
    const output=new Writable({highWaterMark:mode==='idle-output'?16384:1,
      write(chunk,encoding,done){writes++;if(writes===1||mode==='idle-output')done();}
    });
    const done=bridge.serve(input,output,'fixed-close').then(()=>false,()=>true);
    const frames=[{jsonrpc:'2.0',id:0,method:'initialize',params:{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'fixture',version:'1'}}},
      {jsonrpc:'2.0',method:'notifications/initialized'},
      {jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'coordinate_task_execution'}},
      {jsonrpc:'2.0',id:2,method:'ping'}];
    input.write(frames.map(x=>JSON.stringify(x)).join('\\n')+'\\n');
    await new Promise(done=>setTimeout(done,30));
    if(mode==='blocked-input')input.destroy();else output.destroy();
    reports.push({failed:await done,closed,writes});
    input.destroy();output.destroy();
  }
  console.log(JSON.stringify(reports));
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE),
                              str(BRIDGE.with_name('native-task-execution.cjs'))],
                             capture_output=True, env=self.env, cwd=self.work, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual([row['closed'] for row in result], [1, 2, 3])
        self.assertTrue(all(row['failed'] for row in result))
        self.assertTrue(all(row['writes'] <= 2 for row in result))

    def test_failed_response_is_handled_while_owned_cleanup_is_pending(self):
        script = """
const {PassThrough,Writable}=require('node:stream');
const execution=require(process.argv[2]);
let closeStarted=0,finishClose,writes=0;
execution.createNativeTaskExecution=()=>({observe(){},
  async call(){return {isError:false,value:{fixture:true}};},async cancelRequest(){},
  async close(){closeStarted++;await new Promise(done=>{finishClose=done;});}
});
const bridge=require(process.argv[1]),input=new PassThrough(),unhandled=[];
const onRejection=error=>unhandled.push(error.message);
process.on('unhandledRejection',onRejection);
const output=new Writable({write(chunk,encoding,done){writes++;done(writes===2?new Error('fixed-output-failure'):undefined);}});
const running=bridge.serve(input,output,'fixed-slow-cleanup').then(()=>false,()=>true);
const frames=[{jsonrpc:'2.0',id:0,method:'initialize',params:{protocolVersion:'2025-06-18',capabilities:{},clientInfo:{name:'fixture',version:'1'}}},
  {jsonrpc:'2.0',method:'notifications/initialized'},
  {jsonrpc:'2.0',id:1,method:'tools/call',params:{name:'coordinate_task_execution'}}];
(async()=>{
  input.write(frames.map(x=>JSON.stringify(x)).join('\\n')+'\\n');
  await new Promise(done=>setTimeout(done,40));
  if(!finishClose)throw new Error('cleanup did not start');
  finishClose();const failed=await running;
  await new Promise(done=>setImmediate(done));
  process.removeListener('unhandledRejection',onRejection);
  console.log(JSON.stringify({closeStarted,failed,unhandled}));
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
        run = subprocess.run([self.node, '-e', script, str(BRIDGE),
                              str(BRIDGE.with_name('native-task-execution.cjs'))],
                             capture_output=True, env=self.env, cwd=self.work, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout), {'closeStarted': 1, 'failed': True, 'unhandled': []})

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
        self.assertFalse(rows[2]['result']['tools'][0]['annotations']['readOnlyHint'])
        self.assertTrue(rows[2]['result']['tools'][0]['annotations']['destructiveHint'])
        self.assertIn('contextAssessment', rows[2]['result']['tools'][0]['inputSchema']['properties'])
        self.assertEqual([tool['name'] for tool in rows[2]['result']['tools'][:3]],
                         ['inspect_task_state', 'read_task_input', 'manage_task_state'])
        self.assertEqual(rows[2]['result']['tools'][3]['name'], 'coordinate_task_execution')
        self.assertFalse(rows[2]['result']['tools'][1]['annotations']['readOnlyHint'])
        self.assertTrue(rows[2]['result']['tools'][1]['annotations']['destructiveHint'])
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
            'env_vars': ['YIYUAN_ACCORD_TASK_STATE_DIR', 'CODEX_HOME', 'CODEX_CLI_PATH'],
            'startup_timeout_sec': 10, 'tool_timeout_sec': 30}}})
        adapter = json.loads((package / 'adapter.json').read_text(encoding='utf-8'))
        self.assertTrue(adapter['persistentProcessAdded'])
        self.assertEqual(adapter['nativeTaskStateMcp']['storage'],
                         'existing-task-checkpoint-plus-task-owned-operation-evidence-and-sqlite')
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


    def execution_snapshot_race(self, mode):
        contract = self.execution_contract()
        transcript = next(Path(self.env['CODEX_HOME']).rglob('rollout-*.jsonl'))
        script = r"""
// execution-snapshot-race: real checkpoint reader, synthetic sources, no model.
const fs=require('node:fs'),path=require('node:path');
const x=JSON.parse(fs.readFileSync(0,'utf8'));
const modulePath=path.join(x.runtime,'native-task-execution.cjs');
const {createNativeTaskExecution}=require(modulePath),{operate,hook}=require(path.join(x.runtime,'task-checkpoint.cjs'));
const original={open:fs.openSync,close:fs.closeSync,read:fs.readSync,write:fs.writeFileSync,now:Date.now};
const fds=new Set(),observations=[];let reads=0,injections=0,armed=false,injected=false,nativeStarts=0,expired=false;
const secret='PRIVATE-SYNTHETIC-INPUT-MUST-NOT-LEAK';
const source={kind:'codex-mcp-request-metadata',threadId:x.meta.thread_id,sessionTreeId:x.meta.session_id,
 turnId:x.meta.turn_id,model:x.meta.model,hostVersion:x.meta.codex_version,callId:'fixture-race'};
const message=role=>({type:'response_item',payload:{type:'message',role,
 content:[{type:role==='assistant'?'output_text':'input_text',text:secret}]}});
function append(){if(!armed||injected)return;injected=true;injections++;
 const row=x.mode==='control'?{type:'event_msg',payload:{type:'turn_aborted',turn_id:source.turnId}}:
 message(['user','diagnostic-write-failure'].includes(x.mode)?'user':'assistant');
 fs.appendFileSync(x.transcript,JSON.stringify(row)+'\n');}
fs.openSync=(file,...args)=>{const transcript=path.resolve(String(file))===x.transcript;
 if(transcript&&x.mode==='assistant-before')append();
 const fd=original.open(file,...args);if(transcript)fds.add(fd);return fd;};
fs.closeSync=fd=>{if(fds.has(fd)&&x.mode==='assistant-after')append();fds.delete(fd);return original.close(fd);};
fs.readSync=(fd,...args)=>{const n=original.read(fd,...args);if(fds.has(fd)&&x.mode!=='assistant-after')append();return n;};
fs.writeFileSync=(file,data,...args)=>{
 if(x.mode==='diagnostic-write-failure'&&String(data).startsWith('{')){
  let value;try{value=JSON.parse(String(data));}catch(_){}
  if(value?.kind==='source-gate-failure')throw Object.assign(new Error('fixture diagnostic write denied'),{code:'EACCES'});
 }return original.write(file,data,...args);};
Date.now=()=>expired?x.contract.deadlineMs:original.now();
const readState=request=>{
 reads++;
 if(reads===2){
  if(x.mode==='pause')operate({op:'pause',session_id:source.sessionTreeId,cwd:x.cwd,
   epoch:x.contract.epoch,expectedRevision:x.contract.expectedRevision,reason:'Fixture pause'});
  if(x.mode==='epoch'){
   fs.appendFileSync(x.transcript,JSON.stringify({type:'response_item',payload:{type:'message',role:'user',
    content:[{type:'input_text',text:'Continue this work.'}]}})+'\n');
   hook({hook_event_name:'UserPromptSubmit',prompt:'Continue this work.',session_id:source.sessionTreeId,
    cwd:x.cwd,turn_id:source.turnId,model:source.model,transcript_path:x.transcript});
   const latest=operate(request);
   operate({op:'bind',session_id:source.sessionTreeId,cwd:x.cwd,epoch:latest.epoch,expectedRevision:latest.revision,
    result:'Review the authorized fixed candidate',inputs:['drain.json'],outputs:[{path:'review.json'}],
    nextAction:'Perform the bounded review',canContinue:true});
  }
  if(x.mode==='protected')fs.appendFileSync(path.join(x.cwd,'drain.json'),' ');
 }
 armed=reads===2&&!['pause','observe'].includes(x.mode)||x.mode==='continuous'&&reads===3;
 injected=false;const snapshot=operate(request);armed=false;
 if(x.mode==='deadline'&&reads===2)expired=true;
 observations.push({read:reads,reason:snapshot.nativeInputEvidence?.reason,mode:snapshot.mode,
  epochMatches:snapshot.epoch===x.contract.epoch,revision:snapshot.revision,
  inputReconciled:snapshot.nativeInputEvidence?.latestInputReconciled,
  inputsComplete:snapshot.nativeInputEvidence?.latestNativeInputsComplete,
  pending:snapshot.nativeInputEvidence?.pendingInputs?.length,
  protectedUnchanged:snapshot.inspection?.inputs?.every(row=>row.unchanged&&row.stable)});
 return snapshot;
};
const execution=createNativeTaskExecution({sourceOf:()=>source,readState,storageRoot:x.storage,
 nativeFactory:async()=>{nativeStarts++;throw Error('fixture must not create native target');}});
const params=(action,args={})=>({arguments:{action,cwd:x.cwd,...args}});
const call=(action,args={})=>execution.call(params(action,args));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 let output;
 try{
  const initial=await call('prepare',x.contract);
  if(initial.isError)throw Error(JSON.stringify(initial));
  const id=initial.value.operationId;
  // A bounded microtask/event-loop drain, not a race against a fixed sleep.
  let observed;
  for(let i=0;i<40;i++){await tick();observed=(await call('inspect',{operationId:id})).value;
   if(observed.failure||observed.reviewRequest)break;}
  if(x.mode==='observe'){
   if(!observed.reviewRequest)throw Error('fixture did not reach review');
   fs.appendFileSync(x.transcript,JSON.stringify(message('user'))+'\n');
   execution.observe(params('inspect',{operationId:id}));
   for(let i=0;i<40;i++){await tick();observed=(await call('inspect',{operationId:id})).value;
    if(observed.failure&&!observed.busy)break;}
  }
  const readEvidence=async locator=>locator?JSON.parse((await call('read-evidence',{
   operationId:id,evidenceId:locator.evidenceId})).value.text):null;
  const state=await readEvidence(observed.stateEvidence),diagnostic=await readEvidence(observed.sourceFailureEvidence);
  output={observed,state,diagnostic,observations,nativeStarts,injections};
 }finally{await execution.close();Date.now=original.now;}
 process.stdout.write(JSON.stringify(output));
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
"""
        result = subprocess.run([self.node, '-e', script], input=json.dumps({
            'runtime': str(BRIDGE.parent), 'storage': str(self.state), 'cwd': str(self.work),
            'transcript': str(transcript), 'meta': self.params['_meta']['x-codex-turn-metadata'],
            'contract': contract, 'mode': mode}), capture_output=True, text=True,
            encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['nativeStarts'], 0)
        self.assertEqual(value['state']['turnStarts'], 0)
        self.assertIsNone(value['state'].get('target'))
        self.assertIsNone(value['state']['pendingEffect'])
        self.assertIsNone(value['state']['revision'])
        return value

    def test_execution_snapshot_reobservation_preserves_input_control_and_independent_gates(self):
        for mode in ('assistant', 'assistant-before', 'assistant-after', 'user', 'control', 'pause',
                     'continuous', 'deadline', 'epoch', 'protected'):
            with self.subTest(mode=mode):
                case = NativeStateMcpTests()
                case.setUp()
                try:
                    value = case.execution_snapshot_race(mode)
                finally:
                    case.doCleanups()
                observed, rows = value['observed'], value['observations']
                if mode.startswith('assistant'):
                    self.assertIsNone(observed['failure'], value)
                    self.assertEqual(observed['reviewRequest']['stage'], 'prepare')
                    if mode == 'assistant-after':
                        self.assertEqual(rows[1]['reason'], 'bound-native-input-prefix')
                    else:
                        self.assertIn(rows[1]['reason'], ('transcript-changed-before-read', 'transcript-changed-during-read',
                                                         'transcript-path-changed-after-read'))
                    self.assertEqual(rows[2]['reason'], 'bound-native-input-prefix')
                    continue
                self.assertEqual(observed['failure'], 'current-source-not-executable', value)
                self.assertEqual(observed['phase'], 'held')
                diagnostic = value['diagnostic']
                self.assertIsNotNone(diagnostic, 'failed source gate must retain safe diagnostic evidence')
                self.assertEqual(set(diagnostic), {'kind', 'stage', 'observations'})
                self.assertEqual(diagnostic['kind'], 'source-gate-failure')
                self.assertEqual(diagnostic['stage'], 'prepare')
                attempts = diagnostic['observations']
                self.assertEqual(len(attempts), 1 if mode in ('pause', 'deadline', 'epoch', 'protected') else 2)
                for attempt in attempts:
                    self.assertEqual(set(attempt), {'attempt', 'gates', 'sameBasis', 'protectedSource', 'nativeInputs'})
                    self.assertEqual(set(attempt['gates']), {'active', 'checkpoint', 'canContinue', 'noReplay',
                        'noResumeReconciliation', 'hostCurrent', 'inputReconciled', 'receiptPresent',
                        'evidenceObserved', 'latestInputReconciled', 'latestInputsComplete', 'noPendingInputs'})
                    self.assertTrue(all(type(flag) is bool for flag in attempt['gates'].values()))
                    self.assertEqual(set(attempt['nativeInputs']), {'state', 'reason', 'pendingCount'})
                text = json.dumps(diagnostic)
                self.assertNotIn('PRIVATE-SYNTHETIC-INPUT-MUST-NOT-LEAK', text)
                self.assertNotIn(str(case.work), text)
                if mode == 'user':
                    self.assertEqual(rows[-1]['pending'], 1)
                    self.assertFalse(rows[-1]['inputsComplete'])
                elif mode == 'control':
                    self.assertEqual(rows[-1]['reason'], 'native-input-control-needs-reconciliation')
                elif mode == 'pause':
                    self.assertEqual(rows[-1]['mode'], 'paused')
                elif mode == 'epoch':
                    self.assertFalse(attempts[-1]['sameBasis'])
                    self.assertEqual(rows[-1]['reason'], 'transcript-changed-during-read')
                    self.assertTrue(attempts[-1]['gates']['inputReconciled'])
                elif mode == 'protected':
                    self.assertFalse(attempts[-1]['protectedSource'])
                elif mode == 'continuous':
                    self.assertEqual(value['injections'], 2)
                    self.assertEqual(rows[-1]['reason'], 'transcript-changed-during-read')

    def test_execution_snapshot_diagnostic_failure_and_observe_cancel_preserve_primary_failure(self):
        for mode in ('diagnostic-write-failure', 'observe'):
            with self.subTest(mode=mode):
                case = NativeStateMcpTests()
                case.setUp()
                try:
                    value = case.execution_snapshot_race(mode)
                finally:
                    case.doCleanups()
                observed = value['observed']
                self.assertEqual(observed['failure'], 'current-source-not-executable', value)
                self.assertIn(observed['phase'], ('held', 'cancelled-held'))
                self.assertFalse(observed['busy'])
                self.assertIsNone(observed['reviewRequest'])
                if mode == 'diagnostic-write-failure':
                    self.assertEqual(observed.get('sourceFailureDiagnosticError'), 'EACCES')
                    self.assertIsNone(observed['sourceFailureEvidence'])
                else:
                    self.assertIsNone(observed.get('sourceFailureDiagnosticError'))
                    self.assertIsNotNone(value['diagnostic'], 'observe cancellation must retain source gate diagnosis')
                    self.assertEqual(value['diagnostic']['stage'], 'source-check')
                    self.assertFalse(value['diagnostic']['observations'][-1]['gates']['noPendingInputs'])


def _finalize_native_integration(result, app, fixture, root, host, *, body_failed, scoped_hook=False):
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
    if body_failed or cleanup_failures:
        result['remainingResponsibilities'] = {
            'finalSourceCheck': 'not-executed',
            'ownedDirectoryCleanup': 'not-executed; home/workspace/state/temp/marketplace retained'}
        if scoped_hook:
            result['remainingResponsibilities']['sessionEndRetirement'] = 'not-executed; actual retirement unknown'
    try:
        host.save(root/'result.json', result)
    except BaseException:
        if not body_failed:
            raise
    if cleanup_failures and not body_failed:
        raise RuntimeError('native integration cleanup failed: ' +
                           ', '.join(item['stage'] for item in cleanup_failures))


def _finish_native_integration(result, root, host, manifest, original, *, scoped_hook=False):
    """Save a terminal verdict only after the existing postchecks and owned cleanup."""
    names = ('home', 'workspace', 'state', 'temp', 'marketplace')
    progress = {'stage': 'scoped-receipt-check', 'sourceVerified': False,
                'originalRetained': False, 'completedRemovals': [], 'attemptedRoot': None}
    result.update(status='finalizing', finalizationProgress=progress)
    sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        if scoped_hook:
            if list((root/'state').iterdir()):
                raise RuntimeError('native SessionEnd did not retire the scoped receipt')
            result['scopedReceiptRetired'] = True
        progress['stage'] = 'final-source-check'
        if any(sha(ROOT/name) != digest for name, digest in manifest['sources'].items()):
            raise RuntimeError('execution sources changed during the episode')
        progress['sourceVerified'] = True
        progress['stage'] = 'original-retention'
        if sha(original) != manifest['protectedSha256']:
            raise RuntimeError('protected original changed before retention')
        retained = root/'retained/keep.txt'
        shutil.copy2(original, retained)
        if sha(retained) != manifest['protectedSha256'] or sha(original) != manifest['protectedSha256']:
            raise RuntimeError('protected original retention mismatch')
        progress['originalRetained'] = True
        progress['stage'] = 'owned-directory-cleanup'
        for name in names:
            target = root/name
            if target.resolve() != target or target.parent != root:
                raise ValueError('unsafe cleanup target')
            progress['attemptedRoot'] = name
            host._remove_owned_tree(target)
            progress['completedRemovals'].append(name)
            progress['attemptedRoot'] = None
        progress['stage'] = 'cleanup-receipt'
        host.save(root/'cleanup.json', {'removed': [str(root/name) for name in names],
                                      'originalRetained': True, 'userHomeTouched': False})
        progress['stage'] = 'final-result'
        result.update(status='passed')
        result.pop('remainingResponsibilities', None)
        host.save(root/'result.json', result)
    except BaseException as error:
        result.update(status='failed', failure=type(error).__name__, reason=str(error))
        remaining = {'finalizationEvidence': 'not-completed; see finalizationProgress and original error'}
        if not progress['sourceVerified']:
            remaining['finalSourceCheck'] = 'not-completed'
        if scoped_hook and not result.get('scopedReceiptRetired'):
            remaining['sessionEndRetirement'] = 'not-completed; actual retirement unknown'
        if len(progress['completedRemovals']) < len(names):
            remaining['ownedDirectoryCleanup'] = {
                'remainingOrUnknown': [name for name in names if name not in progress['completedRemovals']],
                'attemptedRootEffect': 'unknown' if progress['attemptedRoot'] else 'not-dispatched'}
        result['remainingResponsibilities'] = remaining
        try:
            host.save(root/'result.json', result)
        except BaseException as save_error:
            raise error from save_error
        raise


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
        # The shared handler can protectively stop owned execution, so reads no
        # longer claim read-only approval. Only these isolated fixed-response
        # probes preapprove the two named reads; user/default policy is untouched.
        for tool in ('inspect_task_state', 'read_task_input'):
            extra += ['-c', f'plugins.yiyuan-accord-codex@yiyuan-accord.mcp_servers.accord-state.tools.{tool}.approval_mode="approve"']
        result['readApproval'] = 'isolated-process-preapproval-of-two-named-state-reads'
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
        turn = _start_native_mcp_turn(app, thread, prompt)
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
        result.update(status='body-completed', threadId=thread, turnId=turn, nativeCall=call,
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
                                     body_failed=body_failed, scoped_hook=scoped_hook)
    _finish_native_integration(result, root, host, manifest, original, scoped_hook=scoped_hook)
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
