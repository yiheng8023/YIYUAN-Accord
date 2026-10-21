from contextlib import contextmanager
import hashlib
import sys
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


@contextmanager
def owned_process(command, **options):
    """Contain fixed test peers before dispatch; never repair the tested result."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.observe_codex_entry import WindowsJob, PosixProcessGroup
    controller = WindowsJob() if os.name == 'nt' else PosixProcessGroup()
    process = None
    with tempfile.TemporaryDirectory() as directory:
        # Native launchers create their own POSIX group. Retain their actual
        # ChildProcess in the harness, since the outer group cannot contain it.
        preload = Path(directory) / 'owned-fixture-cleanup.cjs'
        preload.write_text(r"""
const cp=require('node:child_process'),spawn=cp.spawn,kill=process.kill.bind(process),owned=[];
cp.spawn=(file,args,options)=>{const child=spawn(file,args,options);
 const row={child,group:options?.detached===true,closed:false};owned.push(row);
 child.once('close',()=>{row.closed=true;});return child;};
let disposing;
function dispose(){return disposing||=(async()=>{
 for(const row of owned){const child=row.child;
  if(child.exitCode===null&&child.signalCode===null&&child._handle){
   if(row.group){try{kill(-child.pid,'SIGKILL');}catch(e){if(e.code!=='ESRCH')throw e;}}
   else child.kill('SIGKILL');
  }
 }
 const end=Date.now()+5000;
 while(owned.some(r=>!r.closed)&&Date.now()<end)await new Promise(r=>setTimeout(r,10));
 if(owned.some(r=>!r.closed))throw Error('fixture native closure unverified');
})();}
if(process.platform!=='win32'){
 process.once('beforeExit',()=>dispose().catch(e=>{console.error(e.message);process.exitCode=125;}));
 process.once('SIGTERM',()=>dispose().then(()=>process.exit(124),e=>{console.error(e.message);process.exit(125);}));
}
""", encoding='utf-8')
        command = [command[0], '--require', str(preload), *command[1:]]
        try:
            launch = {'creationflags': subprocess.CREATE_NO_WINDOW | 4} if os.name == 'nt' else {'start_new_session': True}
            process = subprocess.Popen(command, **options, **launch)
            controller.attach_and_resume(process)
            process.fixture_controller = controller
            yield process
        finally:
            try:
                if process is not None and process.poll() is None:
                    if os.name == 'nt':
                        controller.terminate()
                        if process.poll() is None:
                            process.kill()  # exact Popen handle, including attachment failure
                    else:
                        process.terminate()  # original Popen; native cleanup runs in the retained harness
                    process.communicate(timeout=7)
                if process is not None:
                    sample = controller.sample()
                    if os.name == 'nt' and sample['activeProcesses']:
                        controller.terminate()
                        end = time.monotonic() + 5
                        while controller.sample()['activeProcesses'] and time.monotonic() < end:
                            time.sleep(0.01)
                    sample = controller.sample()
                    assert (sample['activeProcesses'] == 0 if os.name == 'nt' else
                            sample['processGroupState'] == 'absent'), sample
            finally:
                controller.close()


def owned_run(command, *, input=None, timeout=25, **options):
    with owned_process(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, **options) as process:
        output, error = process.communicate(input, timeout=timeout)
        result = subprocess.CompletedProcess(command, process.returncode, output, error)
        result.fixture_resources = process.fixture_controller.sample()
        # An exited OS helper may still have a Job member completing shutdown.
        # Observe for the original descendant-test bound, without signalling it.
        end = time.monotonic() + 1
        while os.name == 'nt' and result.fixture_resources['activeProcesses'] and time.monotonic() < end:
            time.sleep(0.01)
            result.fixture_resources = process.fixture_controller.sample()
        return result


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
if(mode==='hang'||mode==='tree'||mode==='quiet-hang')setInterval(()=>{},1000);
if(mode==='tree'||mode==='owner-exited'){
 const child=require('node:child_process').spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{
  stdio:mode==='owner-exited'?['ignore',process.stdout,process.stderr]:'ignore',windowsHide:true,detached:mode==='owner-exited'});
 fs.writeFileSync(log+'.child',String(child.pid));
}
rl.on('close',()=>{if(mode==='owner-exited')process.exit(0);});
rl.on('line',line=>{const m=JSON.parse(line);fs.appendFileSync(log,JSON.stringify(m.method)+'\\n');
 if(mode==='quiet-hang')return; // Resident cleanup-negative peer, never writes a response.
 if(m.method==='initialize')process.stdout.write(JSON.stringify({id:m.id,result:{userAgent:'fixture'}})+'\\n');
 if(m.method==='skills/list'){
  if(mode==='hang'||mode==='tree')return;
  if(mode==='rpc-error'){process.stdout.write(JSON.stringify({id:m.id,error:{code:-32001,message:'secret-rpc-error'}})+'\\n');return;}
  if(mode==='invalid'){process.stdout.write('{invalid}\\n');return;}
  rows.data[0].cwd=m.params.cwds[0];
  process.stdout.write(JSON.stringify({id:m.id,result:rows})+'\\n');
 }
});
'''.replace('RESULT', json.dumps(result)).replace('MODE', json.dumps(mode)).replace('LOG', json.dumps(str(self.log))), encoding='utf-8')
        return fixture

    def call(self, op, request=None, *, fixture=None, timeout_ms=1800):
        command = [shutil.which('node'), str(MODULE), op, '--cwd', str(self.root),
                   '--codex', str(fixture or self.fixture()), '--deadline-ms', str(timeout_ms), '--cleanup-ms', '5000']
        result = owned_run(command, input='' if request is None else json.dumps(request),
                                text=True, encoding='utf-8', timeout=25)
        self.assertNotIn('secret-', result.stdout)
        self.assertEqual(result.stderr, '')
        self.last_fixture_resources = result.fixture_resources
        return result.returncode, json.loads(result.stdout)

    def request(self):
        return {'originalRequest': 'Fix the current coordination defect and review the change.',
                'delegation': {'sourceRef': 'current-user-input:3', 'scope': 'Read-only review of the current candidate.'},
                'selection': {'name': 'sample', 'path': str(self.skill)}}

    def test_inventory_is_native_cwd_scoped_projected_and_closed(self):
        code, result = self.call('inventory')
        self.assertEqual(code, 0)
        self.assertTrue(os.path.samefile(result['cwd'], self.root))
        self.assertEqual(result['skills'], [{'name': 'sample', 'path': str(self.skill), 'enabled': True, 'scope': 'user'}])
        self.assertEqual(result['errors'][0]['path'], str(self.root / 'broken' / 'SKILL.md'))
        self.assertNotIn('sensitive-unused-description', json.dumps(result))
        self.assertEqual([json.loads(x) for x in self.log.read_text().splitlines()],
                         ['initialize', 'initialized', 'skills/list'])
        self.assertTrue(result['process']['stdinClosed'])
        self.assertTrue(result['process']['exitObserved'])
        self.assertFalse(result['process']['forced'])
        self.assertEqual(result['process']['exitCode'], 0)

    def test_native_cwd_alias_uses_the_requested_canonical_inventory(self):
        alias = self.root / 'cwd-alias'
        if os.name == 'nt':
            executable = os.path.join(os.environ['SystemRoot'], 'System32', 'cmd.exe')
            command = ('"' + executable + '" /d /v:off /c mklink /J '
                       '"%ACCORD_JUNCTION_ALIAS%" "%ACCORD_JUNCTION_TARGET%"')
            subprocess.run(command, executable=executable,
                env={**os.environ, 'ACCORD_JUNCTION_ALIAS': str(alias),
                     'ACCORD_JUNCTION_TARGET': str(self.root.resolve())},
                check=True, timeout=30, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            alias.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(alias.rmdir if os.name == 'nt' else alias.unlink)
        self.root = alias
        code, result = self.call('inventory')
        self.assertEqual(code, 0, result)
        self.assertTrue(os.path.samefile(result['cwd'], alias))
        self.assertNotEqual(result['cwd'], str(alias))
        self.assertEqual(result['process']['queryPhase'], 'complete')

    def test_native_inventory_rejects_a_foreign_cwd(self):
        foreign = self.root / 'foreign'
        foreign.mkdir()
        peer = self.fixture()
        script = peer.read_text(encoding='utf-8')
        needle = '  process.stdout.write(JSON.stringify({id:m.id,result:rows})'
        self.assertEqual(script.count(needle), 1)
        peer.write_text(script.replace(needle,
            '  rows.data[0].cwd=' + json.dumps(str(foreign)) + ';\n' + needle), encoding='utf-8')
        code, result = self.call('inventory', fixture=peer)
        self.assertEqual((code, result['error']['code']), (1, 'NATIVE_QUERY_FAILED'))
        self.assertTrue(result['process']['exitObserved'])

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
            self.fail('directory symlink unavailable: native alias coverage prerequisite')
        fixture = self.fixture(duplicate=True)
        text = fixture.read_text(encoding='utf-8').replace(json.dumps(str(self.root / 'other' / 'SKILL.md')),
                                                        json.dumps(str(alias / 'SKILL.md')))
        fixture.write_text(text, encoding='utf-8')
        code, result = self.call('prepare', self.request(), fixture=fixture)
        self.assertEqual(code, 0)
        self.assertTrue(result['cli']['available'])

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
        self.assertEqual(result['error']['code'], 'NATIVE_QUERY_FAILED', result)
        self.assertTrue(result['process']['stdinClosed'], result)
        self.assertTrue(result['process']['forced'], result)
        self.assertTrue(result['process']['exitObserved'], result)
        self.assertTrue(result['process']['closeObserved'], result)
        # Attempted query stage is not a receipt; the fixed peer records intake.
        self.assertTrue(self.log.is_file(), result)
        self.assertIn('initialize', [json.loads(line) for line in self.log.read_text().splitlines()])
        self.assertIn(result['process']['queryPhase'], ['initialize', 'initialized', 'skills-list'])
        self.assertGreaterEqual(result['process']['terminationElapsedMs'], 0)
        self.assertIsNone(result['process']['terminationError'])

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
require(process.argv[1]).inventory({cwd:process.argv[2],codexPath:process.argv[3],deadlineMs:250,cleanupMs:5000})
 .then(()=>{throw Error('fixture should time out')},error=>console.log(JSON.stringify({code:error.code,
  process:error.processState,observation,asynchronousStop})));
'''
        completed = owned_run([shutil.which('node'), '-e', script, str(MODULE),
            str(self.root), str(self.fixture(mode='hang'))], text=True, encoding='utf-8',
            timeout=25)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(value['code'], 'NATIVE_QUERY_FAILED', value)
        self.assertFalse(value['asynchronousStop'])
        self.assertEqual(value['observation'], {'before': True, 'after': True, 'pidMatched': True})
        self.assertTrue(value['process']['exitObserved'])

    def test_uncompleted_stop_retains_unknown_and_safe_helper_diagnostics(self):
        # Deterministic failed OS-stop seam, never a timing-tolerance assertion.
        # The outer owned harness releases the actual fixed peer after capture.
        script = r"""
const cp=require('node:child_process');
cp.spawnSync=()=>({status:null,signal:'SIGTERM',error:{code:'ETIMEDOUT',message:'secret-helper-detail'}});
const originalKill=process.kill;
process.kill=(pid,signal)=>{if(pid<0)throw Object.assign(Error('secret-group-detail'),{code:'ESRCH'});
 return originalKill(pid,signal);};
require(process.argv[1]).inventory({cwd:process.argv[2],codexPath:process.argv[3],deadlineMs:250,cleanupMs:50})
 .then(()=>{throw Error('expected unknown cleanup');},e=>{console.log(JSON.stringify({code:e.code,process:e.processState}));
  setInterval(()=>{},1000);});
setTimeout(()=>process.exit(2),5000).unref();
"""
        with owned_process([shutil.which('node'), '-e', script, str(MODULE),
                            str(self.root), str(self.fixture(mode='quiet-hang'))],
                           text=True, encoding='utf-8', stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) as process:
            # Keep the owner alive until the raw result and peer state have been
            # checked. Parent exit itself may otherwise change child lifetime.
            output = process.stdout.readline()
            self.assertTrue(output)
            self.assertNotIn('secret-', output)
            value = json.loads(output)
            self.assertTrue(self.log.is_file(), value)
            self.assertIn('initialize', [json.loads(line) for line in self.log.read_text().splitlines()])
            self.assertEqual(value['code'], 'CLEANUP_UNVERIFIED', value)
            self.assertFalse(value['process']['exitObserved'], value)
            self.assertFalse(value['process']['closeObserved'], value)
            self.assertTrue(value['process']['forced'], value)
            self.assertGreaterEqual(value['process']['terminationElapsedMs'], 0)
            self.assertIsNone(value['process']['terminationExitCode'])
            self.assertEqual(value['process']['terminationError'], 'ETIMEDOUT' if os.name == 'nt' else 'ESRCH')
            self.assertEqual(value['process']['terminationSignal'], 'SIGTERM' if os.name == 'nt' else None)
            if os.name == 'nt':
                self.assertGreater(process.fixture_controller.sample()['activeProcesses'], 1,
                                   ('raw unknown captured before Job finally released the fixture', value))

    def test_exited_owner_with_open_descendant_pipe_is_held_without_stale_pid_stop(self):
        fixture = self.fixture(mode='owner-exited')
        child_file = Path(str(self.log)+'.child')
        owner = owned_process([shutil.which('node'), str(MODULE), 'inventory', '--cwd',
            str(self.root), '--codex', str(fixture), '--deadline-ms', '1800', '--cleanup-ms', '300'],
            text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        with owner as process:
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

    def test_timeout_reclaims_an_actual_owned_descendant(self):
        code, result = self.call('inventory', fixture=self.fixture(mode='tree'), timeout_ms=250)
        self.assertEqual(code, 1)
        self.assertTrue(Path(str(self.log) + '.child').is_file(), result)
        self.assertTrue(result['process']['exitObserved'], result)
        self.assertTrue(result['process']['closeObserved'], result)
        self.assertEqual(self.last_fixture_resources['activeProcesses'], 0,
                         (result, self.last_fixture_resources))



# Applicability, not skips: these cases exercise Windows handles/path identity,
# or a retained native process identity only available on Windows/Linux pidfd.
if os.name != 'nt':
    for name in ('test_windows_selected_path_case_does_not_change_native_identity',
                 'test_tree_stop_keeps_exact_original_handle_until_helper_returns',
                 'test_timeout_reclaims_an_actual_owned_descendant'):
        delattr(CodexCapabilitiesTests, name)
if os.name != 'nt' and not hasattr(os, 'pidfd_open'):
    delattr(CodexCapabilitiesTests, 'test_exited_owner_with_open_descendant_pipe_is_held_without_stale_pid_stop')

if __name__ == '__main__':
    unittest.main()
