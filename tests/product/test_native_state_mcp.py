"""Read-only MCP entry; native host metadata delivery is checked separately."""
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
import time

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / 'runtime/native-state-mcp.cjs'
CHECKPOINT = ROOT / 'runtime/task-checkpoint.cjs'


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

    def inspect(self, params=None):
        code = "const m=require(process.argv[1]);let s='';process.stdin.setEncoding('utf8');process.stdin.on('data',x=>s+=x);process.stdin.on('end',()=>process.stdout.write(JSON.stringify(m.inspectNativeState(JSON.parse(s)))));"
        p = subprocess.run([self.node, '-e', code, str(BRIDGE)], input=json.dumps(params or self.params),
            capture_output=True, text=True, encoding='utf-8', env=self.env, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

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
        ]
        p = self.run_wire(('\n'.join(map(json.dumps, messages))+'\n').encode())
        self.assertEqual(p.returncode, 0, p.stderr)
        rows = [json.loads(line) for line in p.stdout.splitlines()]
        self.assertEqual([row['id'] for row in rows], [0, 1, 2, 3, 4])
        self.assertEqual(rows[0]['error']['code'], -32002)
        self.assertEqual(rows[1]['result']['protocolVersion'], '2025-06-18')
        package_version = json.loads((ROOT/'plugins/yiyuan-accord-codex/.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
        self.assertEqual(rows[1]['result']['serverInfo']['version'], package_version)
        self.assertTrue(rows[2]['result']['tools'][0]['annotations']['readOnlyHint'])
        self.assertEqual(rows[3]['result']['structuredContent']['source']['threadId'], 'current-thread')
        self.assertEqual(rows[4]['error']['code'], -32601)
        self.assertFalse(self.state.exists())

    def test_invalid_utf8_oversize_and_truncated_input_have_no_state_effect(self):
        bad_utf8 = self.run_wire(b'\xff\n')
        self.assertEqual(json.loads(bad_utf8.stdout)['error']['code'], -32700)
        for raw in (b'x' * (128*1024+1), b'{"jsonrpc":"2.0"}'):
            p = self.run_wire(raw)
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(p.stdout)
        self.assertFalse(self.state.exists())

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


def native_integration(codex, evidence):
    """Native MCP metadata and read-only delivery; fixed local replies, no model."""
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
        'binarySha256': sha(codex), 'protectedSha256': sha(original),
        'ownedRoots': {name: str(root/name) for name in ('home','workspace','state','temp')},
        'limits': {'requestSeconds': 30, 'recoverySeconds': 15,
                   'providerRequestBytes': 2*1024*1024, 'providerRequests': 2},
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

    def response(body, ordinal):
        if ordinal != 1: return None
        tools = list(body.get('tools', []))
        for item in body.get('input', []):
            if isinstance(item, dict) and item.get('type') == 'additional_tools': tools += item.get('tools', [])
        matches = []
        def collect(items, namespace=None):
            for tool in items:
                if tool.get('type') == 'namespace': collect(tool.get('tools', []), tool.get('name'))
                elif tool.get('type') == 'function' and tool.get('name', '').endswith('inspect_task_state'):
                    matches.append((namespace, tool['name']))
        collect(tools)
        matches = list(dict.fromkeys(matches))
        if len(matches) != 1: raise ValueError('one directly exposed state tool required')
        namespace, name = matches[0]
        return {'type':'function_call', 'id':'state_tool_call', 'call_id':'native_state_call',
            'name':name, **({'namespace':namespace} if namespace else {}),
            'arguments':json.dumps({'cwd':str(root/'workspace'), 'includeContext':True})}

    fixture = host._Fixture(manifest, response)
    app = None
    result = {'realModelCalls': 0, 'status': 'pending'}
    try:
        argv = host._argv(manifest, fixture, ('-c','features.hooks=false','-c','features.code_mode_host=false'))
        app = host._App(manifest, 'mcp-state', argv, env, deadline)
        app.initialize()
        started = app.rpc('thread/start', {'cwd':str(root/'workspace'), 'model':'fixture-no-model',
            'ephemeral':True, 'sandbox':'read-only', 'approvalPolicy':'never'})
        thread = started['thread']['id']
        if started.get('sandbox', {}).get('type') != 'readOnly': raise RuntimeError('source is not read-only')
        turn = app.rpc('turn/start', {'threadId':thread,
            'input':[{'type':'text','text':'Inspect the saved state for this workspace.'}]})['turn']['id']
        terminal = app.wait_turn(thread, turn)
        calls = [e['params']['item'] for e in app.events if e.get('method') == 'item/completed'
            and e.get('params', {}).get('threadId') == thread
            and e.get('params', {}).get('turnId') == turn
            and e.get('params', {}).get('item', {}).get('type') == 'mcpToolCall']
        if terminal != 'completed' or len(calls) != 1: raise RuntimeError('one completed MCP call required')
        call = calls[0]
        reply = call.get('result') or {}
        value = reply.get('structuredContent')
        if value is None:
            content = [x.get('text') for x in reply.get('content', []) if x.get('type') == 'text']
            value = json.loads(content[0]) if len(content) == 1 else None
        if not value or reply.get('isError') is True or call.get('error'):
            raise RuntimeError('state tool result unavailable')
        source = value['source']
        if (source['threadId'] != thread or source['sessionTreeId'] != thread
                or source['turnId'] != turn or source['callId'] != call['id']):
            raise RuntimeError('metadata differs from native thread/turn/call receipts')
        if value['checkpoint'] != {'state':'unavailable','reason':'native-user-input-receipt-missing'}:
            raise RuntimeError('absent hook receipt was not preserved as unknown')
        if value.get('context', {}).get('reason') != 'native-user-input-receipt-missing':
            raise RuntimeError('optional context must preserve absent input as unknown')
        if sha(original) != manifest['protectedSha256'] or list((root/'state').iterdir()):
            raise RuntimeError('inspection changed protected files or task state')
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
                or 'inspect_task_state' not in after_servers[0]['tools']):
            raise RuntimeError('MCP connection or state tool lost after replacement')
        result['liveCacheUpgrade'] = {'beforeMcp': servers, 'result': upgrade,
            'beforeIdentity': [str(before_cache.st_dev), str(before_cache.st_ino)],
            'afterIdentity': [str(after_cache.st_dev), str(after_cache.st_ino)],
            'afterMcp': after_status}
        if sha(original) != manifest['protectedSha256'] or list((root/'state').iterdir()):
            raise RuntimeError('cache replacement changed original or task state')
        if len(fixture.requests) != 2 or fixture.auth_seen: raise RuntimeError('provider bounds differ')
        result.update(status='passed', threadId=thread, turnId=turn, nativeCall=call,
            providerRequests=len(fixture.requests), sourceSettings=started,
            claimLimit='Native plugin MCP registration, actual metadata and read-only unknown-state behavior; no real model judgment, GUI adoption or handoff dispatch.')
    except BaseException as error:
        result.update(status='failed', failure=type(error).__name__, reason=str(error))
        raise
    finally:
        if app is not None: result['resources'] = app.close()
        fixture.close()
        host.save(root/'result.json',result)
    if result['resources']['forced'] or not host._released(result['resources']['after']):
        raise RuntimeError('native process domain was not naturally released')
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
        arguments = parser.parse_args()
        native_integration(arguments.native_codex, arguments.evidence)
    else:
        unittest.main()
