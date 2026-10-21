import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'plugins/yiyuan-accord-codex/runtime/codex-capabilities.cjs'


@unittest.skipUnless(shutil.which('node'), 'Node required')
class CodexCapabilitiesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / 'managed' / 'sample' / 'SKILL.md'
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text('---\nname: sample\ndisable-model-invocation: true\n---\nReview current work.\n', encoding='utf-8')
        self.policy = self.skill.parent / 'agents' / 'openai.yaml'
        self.policy.parent.mkdir()
        self.policy.write_text('policy:\n  allow_implicit_invocation: false\n', encoding='utf-8')
        self.log = self.root / 'methods.jsonl'

    def fixture(self, *, enabled=True, duplicate=False, mode='normal'):
        rows = [{'name': 'sample', 'path': str(self.skill), 'enabled': enabled, 'scope': 'user',
                 'description': 'sensitive-unused-description'}]
        if duplicate:
            rows.append({**rows[0], 'path': str(self.root / 'other' / 'SKILL.md')})
        result = {'data': [{'cwd': str(self.root), 'skills': rows,
                           'errors': [{'path': str(self.root / 'broken' / 'SKILL.md'),
                                       'message': 'secret-native-error-must-not-escape'}]}]}
        fixture = self.root / 'native.cjs'
        fixture.write_text('''
const fs=require('node:fs');
const rl=require('node:readline').createInterface({input:process.stdin});
const rows=RESULT; const mode=MODE; const log=LOG;
if(mode==='hang'||mode==='tree')setInterval(()=>{},1000);
if(mode==='tree'||mode==='owner-exited'){
 const child=require('node:child_process').spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{
  stdio:mode==='owner-exited'?['ignore',process.stdout,process.stderr]:'ignore',windowsHide:true,detached:mode==='owner-exited'});
 fs.writeFileSync(log+'.child',String(child.pid));
}
rl.on('close',()=>{if(mode==='owner-exited')process.exit(0);});
rl.on('line',line=>{const m=JSON.parse(line);fs.appendFileSync(log,JSON.stringify(m.method)+'\\n');
 if(m.method==='initialize')process.stdout.write(JSON.stringify({id:m.id,result:{userAgent:'fixture'}})+'\\n');
 if(m.method==='skills/list'){
  if(mode==='hang'||mode==='tree')return;
  if(mode==='rpc-error'){process.stdout.write(JSON.stringify({id:m.id,error:{code:-32001,message:'secret-rpc-error'}})+'\\n');return;}
  if(mode==='invalid'){process.stdout.write('{invalid}\\n');return;}
  process.stdout.write(JSON.stringify({id:m.id,result:rows})+'\\n');
 }
});
'''.replace('RESULT', json.dumps(result)).replace('MODE', json.dumps(mode)).replace('LOG', json.dumps(str(self.log))), encoding='utf-8')
        return fixture

    def call(self, op, request=None, *, fixture=None, timeout_ms=1800):
        command = [shutil.which('node'), str(MODULE), op, '--cwd', str(self.root),
                   '--codex', str(fixture or self.fixture()), '--deadline-ms', str(timeout_ms), '--cleanup-ms', '600']
        result = subprocess.run(command, input='' if request is None else json.dumps(request),
                                capture_output=True, text=True, encoding='utf-8', timeout=12)
        self.assertNotIn('secret-', result.stdout)
        self.assertEqual(result.stderr, '')
        return result.returncode, json.loads(result.stdout)

    def request(self):
        return {'originalRequest': 'Fix the current coordination defect and review the change.',
                'delegation': {'sourceRef': 'current-user-input:3', 'scope': 'Read-only review of the current candidate.'},
                'selection': {'name': 'sample', 'path': str(self.skill)}}

    def test_inventory_is_native_cwd_scoped_projected_and_closed(self):
        code, result = self.call('inventory')
        self.assertEqual(code, 0)
        self.assertEqual(result['cwd'], str(self.root.resolve()))
        self.assertEqual(result['skills'], [{'name': 'sample', 'path': str(self.skill), 'enabled': True, 'scope': 'user'}])
        self.assertEqual(result['errors'][0]['path'], str(self.root / 'broken' / 'SKILL.md'))
        self.assertNotIn('sensitive-unused-description', json.dumps(result))
        self.assertEqual([json.loads(x) for x in self.log.read_text().splitlines()],
                         ['initialize', 'initialized', 'skills/list'])
        self.assertTrue(result['process']['stdinClosed'])
        self.assertTrue(result['process']['exitObserved'])
        self.assertFalse(result['process']['forced'])
        self.assertEqual(result['process']['exitCode'], 0)

    def test_prepare_retains_delegated_origin_and_exact_source_without_executing(self):
        request = self.request()
        code, result = self.call('prepare', request)
        self.assertEqual(code, 0)
        self.assertEqual(result['origin'], {'selection': 'coordinator-selected', **request['delegation'],
                                           'originalRequest': request['originalRequest']})
        self.assertEqual(result['source']['sha256'], hashlib.sha256(self.skill.read_bytes()).hexdigest())
        self.assertFalse(result['source']['policy']['allowImplicitInvocation'])
        self.assertTrue(result['source']['policy']['disableModelInvocation'])
        self.assertEqual(result['nativeInput'][1], {'type': 'skill', 'name': 'sample', 'path': str(self.skill)})
        self.assertIn('coordinator-selected', result['cli']['stdin'])
        self.assertTrue(result['cli']['requiresNativeLoadVerification'])
        self.assertEqual(len(self.log.read_text().splitlines()), 3)

    def test_disabled_selection_is_rejected(self):
        code, result = self.call('prepare', self.request(), fixture=self.fixture(enabled=False))
        self.assertEqual(code, 1)
        self.assertEqual(result['error']['code'], 'SKILL_DISABLED')
        self.assertTrue(result['process']['exitObserved'])

    def test_duplicate_name_preserves_native_path_but_withholds_cli_input(self):
        code, result = self.call('prepare', self.request(), fixture=self.fixture(duplicate=True))
        self.assertEqual(code, 0)
        self.assertEqual(result['nativeInput'][1]['path'], str(self.skill))
        self.assertFalse(result['cli']['available'])
        self.assertEqual(result['cli']['reason'], 'ambiguous-enabled-name')
        self.assertIsNone(result['cli']['stdin'])

    def test_previously_reviewed_source_and_policy_drift_are_rejected(self):
        for field, expected in [('expectedSha256', '0' * 64), ('expectedPolicySha256', '1' * 64)]:
            with self.subTest(field=field):
                request = self.request()
                request['selection']['expectedSha256'] = hashlib.sha256(self.skill.read_bytes()).hexdigest()
                request['selection'][field] = expected
                code, result = self.call('prepare', request)
                self.assertEqual(code, 1)
                self.assertEqual(result['error']['code'], 'SOURCE_CHANGED')

    def test_policy_review_requires_skill_hash_and_source_byte_limit_is_real(self):
        request = self.request()
        request['selection']['expectedPolicySha256'] = '0' * 64
        code, result = self.call('prepare', request)
        self.assertEqual((code, result['error']['code']), (1, 'INVALID_INPUT'))
        self.assertFalse(self.log.exists())
        self.skill.write_bytes(b'x' * 262145)
        code, result = self.call('prepare', self.request())
        self.assertEqual((code, result['error']['code']), (1, 'INVALID_SOURCE'))

    def test_same_source_alias_is_not_a_false_name_conflict(self):
        alias = self.root / 'alias'
        try:
            alias.symlink_to(self.skill.parent, target_is_directory=True)
        except OSError:
            self.skipTest('directory symlink unavailable')
        fixture = self.fixture(duplicate=True)
        text = fixture.read_text(encoding='utf-8').replace(json.dumps(str(self.root / 'other' / 'SKILL.md')),
                                                        json.dumps(str(alias / 'SKILL.md')))
        fixture.write_text(text, encoding='utf-8')
        code, result = self.call('prepare', self.request(), fixture=fixture)
        self.assertEqual(code, 0)
        self.assertTrue(result['cli']['available'])

    @unittest.skipUnless(os.name == 'nt', 'Windows path semantics')
    def test_windows_selected_path_case_does_not_change_native_identity(self):
        request = self.request()
        request['selection']['path'] = str(self.skill).upper()
        code, result = self.call('prepare', request)
        self.assertEqual(code, 0)
        self.assertEqual(result['nativeInput'][1]['path'], str(self.skill))

    def test_invalid_origin_or_oversized_input_starts_no_query(self):
        for request in [{'selection': self.request()['selection']},
                        {**self.request(), 'originalRequest': 'x' * 70000}]:
            with self.subTest(size=len(json.dumps(request))):
                code, result = self.call('prepare', request)
                self.assertEqual(code, 1)
                self.assertEqual(result['error']['code'], 'INVALID_INPUT')
                self.assertFalse(self.log.exists())

    def test_unfinished_piped_input_has_a_deadline_before_launch(self):
        fixture = self.fixture()
        process = subprocess.Popen([shutil.which('node'), str(MODULE), 'prepare', '--cwd', str(self.root),
                                    '--codex', str(fixture), '--deadline-ms', '100'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.stdin.write(b'{')
            process.stdin.flush()
            process.wait(timeout=3)
            result = json.loads(process.stdout.read())
            self.assertEqual(result['error']['code'], 'INVALID_INPUT')
            self.assertFalse(self.log.exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()

    def test_rpc_and_protocol_failures_close_the_owned_process(self):
        for mode in ['rpc-error', 'invalid']:
            with self.subTest(mode=mode):
                code, result = self.call('inventory', fixture=self.fixture(mode=mode))
                self.assertEqual(code, 1)
                self.assertEqual(result['error']['code'], 'NATIVE_QUERY_FAILED')
                self.assertTrue(result['process']['stdinClosed'])
                self.assertTrue(result['process']['exitObserved'])

    def test_deadline_escalates_only_owned_process_and_reports_exit(self):
        code, result = self.call('inventory', fixture=self.fixture(mode='hang'), timeout_ms=250)
        self.assertEqual(code, 1)
        self.assertEqual(result['error']['code'], 'NATIVE_QUERY_FAILED')
        self.assertTrue(result['process']['stdinClosed'])
        self.assertTrue(result['process']['forced'])
        self.assertTrue(result['process']['exitObserved'])

    @unittest.skipUnless(os.name == 'nt', 'Windows Node process-handle lifetime')
    def test_tree_stop_keeps_exact_original_handle_until_helper_returns(self):
        script = r'''
const cp=require('node:child_process'), originalSpawn=cp.spawn, originalSync=cp.spawnSync;
let owner, observation=null, asynchronousStop=false;
cp.spawn=(file,args,options)=>{const child=originalSpawn(file,args,options);
 if(file.toLowerCase().endsWith('taskkill.exe'))asynchronousStop=true;else owner=child;
 return child;};
cp.spawnSync=(file,args,options)=>{const handle=owner._handle;
 const before=handle!==null&&owner.exitCode===null&&owner.signalCode===null;
 const result=originalSync(file,args,options);
 observation={before,after:owner._handle===handle&&owner.exitCode===null&&owner.signalCode===null,
  pidMatched:args[args.indexOf('/PID')+1]===String(owner.pid)};return result;};
require(process.argv[1]).inventory({cwd:process.argv[2],codexPath:process.argv[3],deadlineMs:250,cleanupMs:600})
 .then(()=>{throw Error('fixture should time out')},error=>console.log(JSON.stringify({code:error.code,
  process:error.processState,observation,asynchronousStop})));
'''
        completed = subprocess.run([shutil.which('node'), '-e', script, str(MODULE),
            str(self.root), str(self.fixture(mode='hang'))], text=True, encoding='utf-8',
            capture_output=True, timeout=10)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(value['code'], 'NATIVE_QUERY_FAILED')
        self.assertFalse(value['asynchronousStop'])
        self.assertEqual(value['observation'], {'before': True, 'after': True, 'pidMatched': True})
        self.assertTrue(value['process']['exitObserved'])

    def test_exited_owner_with_open_descendant_pipe_is_held_without_stale_pid_stop(self):
        if os.name != 'nt' and not hasattr(os, 'pidfd_open'):
            self.skipTest('Exact Windows handle or Linux pidfd required for fixture cleanup')
        fixture = self.fixture(mode='owner-exited')
        child_file = Path(str(self.log)+'.child')
        process = subprocess.Popen([shutil.which('node'), str(MODULE), 'inventory', '--cwd',
            str(self.root), '--codex', str(fixture), '--deadline-ms', '1800', '--cleanup-ms', '300'],
            text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        handle = None
        try:
            end = time.monotonic()+5
            while not child_file.exists() and time.monotonic() < end:
                time.sleep(0.01)
            self.assertTrue(child_file.exists())
            pid = int(child_file.read_text())
            if os.name == 'nt':
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                handle = kernel.OpenProcess(0x00100001, False, pid)
                self.assertTrue(handle)
            else:
                import select
                import signal
                handle = os.pidfd_open(pid)
                poller = select.poll(); poller.register(handle, select.POLLIN)
            output, error = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 1, error)
            value = json.loads(output)
            self.assertEqual(value['error']['code'], 'CLEANUP_UNVERIFIED')
            self.assertTrue(value['process']['exitObserved'])
            self.assertFalse(value['process']['closeObserved'])
            self.assertIsNone(value['process']['terminationAttempt'])
            self.assertFalse(value['process']['forced'])
            self.assertEqual(value['process']['descendantVerification'], 'unknown-launcher-exited-with-open-pipes')
            if os.name == 'nt':
                self.assertEqual(kernel.WaitForSingleObject(handle, 0), 258)
            else:
                self.assertFalse(poller.poll(0))
        finally:
            if handle is not None:
                if os.name == 'nt':
                    try:
                        if kernel.WaitForSingleObject(handle, 0) != 0:
                            self.assertTrue(kernel.TerminateProcess(handle, 1))
                            self.assertEqual(kernel.WaitForSingleObject(handle, 1000), 0)
                    finally:
                        kernel.CloseHandle(handle)
                else:
                    try:
                        if not poller.poll(0):
                            signal.pidfd_send_signal(handle, signal.SIGTERM)
                            self.assertTrue(poller.poll(1000))
                    finally:
                        os.close(handle)
            if process.poll() is None:
                process.kill(); process.communicate(timeout=5)

    @unittest.skipUnless(os.name == 'nt', 'Windows owned-tree regression')
    def test_timeout_reclaims_an_actual_owned_descendant(self):
        import ctypes
        from ctypes import wintypes

        code, result = self.call('inventory', fixture=self.fixture(mode='tree'), timeout_ms=250)
        self.assertEqual(code, 1)
        self.assertTrue(result['process']['exitObserved'])
        pid = int(Path(str(self.log) + '.child').read_text())
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        handle = kernel.OpenProcess(0x00100001, False, pid)
        if handle:
            try:
                observed = kernel.WaitForSingleObject(handle, 1000)
                if observed != 0:  # Preserve the failed observation while releasing the fixture.
                    kernel.TerminateProcess(handle, 1)
                    kernel.WaitForSingleObject(handle, 1000)
                self.assertEqual(observed, 0, 'owned descendant still running')
            finally:
                kernel.CloseHandle(handle)
        else:
            self.assertEqual(ctypes.get_last_error(), 87, 'descendant exit could not be observed')


if __name__ == '__main__':
    unittest.main()
