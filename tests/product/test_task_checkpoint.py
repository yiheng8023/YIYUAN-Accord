"""Executable local task behavior; native Hook loading and model behavior are separate."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


RUNTIME = Path(__file__).resolve().parents[2] / "runtime/task-checkpoint.cjs"


class TaskCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="accord-checkpoint-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.work = self.root / "work"
        self.work.mkdir()
        self.state = self.root / "state"
        self.environment = {**os.environ, "YIYUAN_ACCORD_TASK_STATE_DIR": str(self.state)}
        self.node = shutil.which("node")
        self.assertIsNotNone(self.node)
        (self.work / "source.json").write_text('{"units":60}', encoding="utf-8")
        (self.work / "keep.txt").write_bytes(b"user-owned input\n")
        self.event("UserPromptSubmit", prompt="Deliver both files from the source and preserve the input.")

    def invoke(self, request, *, hook=False, success=True):
        request = {"session_id": "test-session", "cwd": str(self.work), **request}
        result = subprocess.run([self.node, str(RUNTIME), *(["--hook", request['hook_event_name']] if hook else [])],
                                input=json.dumps(request), text=True, encoding="utf-8",
                                capture_output=True, env=self.environment, cwd=self.work, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr

    def event(self, name, **fields):
        return self.invoke({"hook_event_name": name, **fields}, hook=True)

    def status(self):
        return self.invoke({"op": "status"})

    def bind(self, **fields):
        current = self.status()
        return self.invoke({"op": "bind", "epoch": current["epoch"], "expectedRevision": current["revision"],
            "result": "Correct CSV and JSON from the current source", "inputs": ["source.json", "keep.txt"],
            "outputs": [{"path": "summary.json", "json": {"/total": 60}}, {"path": "details.csv"}],
            "nextAction": "write and independently check both files", "canContinue": True, **fields})

    def write_outputs(self, total=60):
        (self.work / "summary.json").write_text(json.dumps({"total": total}), encoding="utf-8")
        (self.work / "details.csv").write_text(f"id,units\nA,{total}\n", encoding="utf-8")

    def test_missing_delivery_continues_then_real_files_allow_retirement(self):
        self.assertEqual(self.bind()["inspection"]["status"], "incomplete")
        stop = self.event("Stop", stop_hook_active=False)
        self.assertEqual(stop["decision"], "block")
        epoch = self.status()["epoch"]
        self.event("UserPromptSubmit", prompt=stop["reason"])
        self.assertEqual(self.status()["epoch"], epoch, "our callback cannot become new human authority")
        self.write_outputs()
        self.assertEqual(self.event("Stop", stop_hook_active=True), {})
        current = self.status()
        self.assertEqual(current["inspection"]["status"], "verified-local")
        retired = self.invoke({"op": "retire", "epoch": current["epoch"], "expectedRevision": current["revision"]})
        self.assertTrue(retired["retired"])
        self.assertEqual(list(self.state.iterdir()), [])
        self.assertEqual((self.work / "keep.txt").read_bytes(), b"user-owned input\n")
        self.assertEqual(json.loads((self.work / "source.json").read_text()), {"units": 60})
        self.assertEqual({p.name for p in self.work.iterdir()}, {"source.json", "keep.txt", "summary.json", "details.csv"})

    def test_source_refresh_invalidates_earlier_success_and_requires_new_result(self):
        self.bind()
        self.write_outputs()
        (self.work / "source.json").write_text('{"units":70}', encoding="utf-8")
        current = self.status()
        self.assertEqual(current["inspection"]["status"], "stale-inputs")
        self.assertIn("unmet-output", self.invoke({"op": "retire", "epoch": current["epoch"],
                      "expectedRevision": current["revision"]}, success=False))
        self.assertEqual(self.event("Stop", stop_hook_active=False)["decision"], "block")
        changed = [{"path": "summary.json", "json": {"/total": 70}}, {"path": "details.csv"}]
        self.bind(outputs=changed, revisionReason="The selected source changed; both outputs must use its current value.")
        self.assertEqual(self.status()["inspection"]["status"], "incomplete")
        self.write_outputs(70)
        self.assertEqual(self.status()["inspection"]["status"], "verified-local")

    def test_new_user_input_and_interrupt_cannot_inherit_a_continue_decision(self):
        self.bind()
        earlier = self.status()
        self.event("UserPromptSubmit", prompt="Pause; do not write anything else.")
        self.assertEqual(self.event("Stop", stop_hook_active=False), {})
        self.assertIn("latest-user-input", self.invoke({"op": "bind", "epoch": earlier["epoch"],
                      "expectedRevision": earlier["revision"]}, success=False))
        current = self.status()
        self.invoke({"op": "pause", "epoch": current["epoch"], "expectedRevision": current["revision"],
                     "reason": "The user explicitly paused this task."})
        self.assertEqual(self.event("Stop", stop_hook_active=False), {})
        self.event("UserPromptSubmit", prompt="Continue the same work.")
        self.bind()
        self.event("Interrupt")
        self.assertEqual(self.event("Stop", stop_hook_active=False), {})
        self.assertFalse((self.work / "summary.json").exists())

    def test_lost_native_input_stays_invalid_after_contended_lock_is_released(self):
        self.bind()
        earlier = self.status()
        lock = Path(str(next(self.state.glob('*.input.json'))) + '.lock')
        lock.write_text(json.dumps({'pid': os.getpid()}), encoding='utf-8')
        try:
            self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Stop; do not write.'},
                        hook=True, success=False)
        finally:
            lock.unlink()  # This test owns the still-live competing lock.
        current = self.status()
        self.assertTrue(current['needsNativeReplay'])
        self.assertFalse(current['currentInputReconciled'])
        self.assertNotEqual(current['epoch'], earlier['epoch'])
        self.assertEqual(self.event('Stop'), {})
        self.assertIn('replay', self.invoke({'op': 'bind', 'epoch': current['epoch'],
                      'expectedRevision': current['revision']}, success=False))
        # A later real input that cannot be captured must obsolete the earlier
        # recovery token; a rejected stale replay must not obsolete the new one.
        self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Still paused; new correction.'},
                    hook=True, success=False)
        later = self.status()
        self.assertNotEqual(later['epoch'], current['epoch'])
        self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Stop; do not write.',
                     'recovery_epoch': current['epoch']}, hook=True, success=False)
        self.assertEqual(self.status()['epoch'], later['epoch'])
        self.event('UserPromptSubmit', prompt='Still paused; new correction.', recovery_epoch=later['epoch'])
        self.assertFalse(self.status()['needsNativeReplay'])
        self.assertEqual(self.event('Stop'), {})

    def test_unidentified_oversize_input_requires_each_workspace_session_to_replay(self):
        self.bind()
        other_work = self.root / 'unrelated-work'
        other_work.mkdir()
        self.invoke({'hook_event_name': 'UserPromptSubmit', 'cwd': str(other_work),
                     'prompt': 'Unrelated workspace task.'}, hook=True)
        self.invoke({'hook_event_name': 'UserPromptSubmit', 'session_id': 'second-session',
                     'prompt': 'Separate task.'}, hook=True)
        self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Stop. ' + 'x' * 140000},
                    hook=True, success=False)
        first = self.status()
        second = self.invoke({'op': 'status', 'session_id': 'second-session'})
        self.assertTrue(first['needsNativeReplay'])
        self.assertTrue(second['needsNativeReplay'])
        self.assertFalse(self.invoke({'op': 'status', 'cwd': str(other_work)})['needsNativeReplay'])
        self.assertEqual(self.event('Stop'), {})
        self.event('UserPromptSubmit', prompt='Stop.', recovery_epoch=first['epoch'])
        self.assertFalse(self.status()['needsNativeReplay'])
        self.assertEqual(self.invoke({'op': 'status', 'session_id': 'second-session'})['epoch'], second['epoch'])
        self.assertTrue(self.invoke({'op': 'status', 'session_id': 'second-session'})['needsNativeReplay'])
        # Ending one session must not clear another session's workspace failure.
        current = self.status()
        self.invoke({'op': 'retire', 'epoch': current['epoch'], 'expectedRevision': current['revision'],
                     'disposition': 'user-cancelled', 'reason': 'The user explicitly stopped this task.'})
        self.assertTrue(self.invoke({'op': 'status', 'session_id': 'second-session'})['needsNativeReplay'])

    def test_missing_receipt_failure_has_a_recovery_token_and_new_interrupt_invalidates_it(self):
        input_path = next(self.state.glob('*.input.json'))
        input_path.unlink()  # The native receipt was never created in this scenario.
        self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Stop. ' + 'x' * 140000},
                    hook=True, success=False)
        before = self.status()
        self.assertTrue(before['needsNativeReplay'])
        self.assertFalse(input_path.exists())
        self.invoke({'hook_event_name': 'Interrupt'}, hook=True, success=False)
        after = self.status()
        self.assertNotEqual(after['epoch'], before['epoch'])
        self.assertFalse(input_path.exists(), 'failure status must not fabricate a native receipt')
        for token in (None, before['epoch']):
            self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Old event',
                         'recovery_epoch': token}, hook=True, success=False)
            self.assertEqual(self.status()['epoch'], after['epoch'])
        self.event('UserPromptSubmit', prompt='The actual current stop input.', recovery_epoch=after['epoch'])
        self.assertFalse(self.status()['needsNativeReplay'])
        self.assertTrue(input_path.exists())

    def test_input_failure_during_replay_publication_is_not_acknowledged_by_old_token(self):
        self.bind()
        lock = Path(str(next(self.state.glob('*.input.json'))) + '.lock')
        lock.write_text(json.dumps({'pid': os.getpid()}), encoding='utf-8')
        try:
            self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Earlier uncaptured input.'},
                        hook=True, success=False)
        finally:
            lock.unlink()
        before = self.status()
        request = {'session_id': 'test-session', 'cwd': str(self.work), 'hook_event_name': 'UserPromptSubmit',
                   'prompt': 'Earlier uncaptured input.', 'recovery_epoch': before['epoch']}
        script = r'''
const fs = require('node:fs'), child = require('node:child_process');
const helper = require(process.argv[1]), event = JSON.parse(process.argv[2]);
const rename = fs.renameSync;
let injected = false;
fs.renameSync = function(from, to) {
  if (!injected && String(to).endsWith('.input.json')) {
    injected = true;
    const lost = child.spawnSync(process.execPath, [process.argv[1], '--hook', 'UserPromptSubmit'], {
      cwd: event.cwd, encoding: 'utf8', input: JSON.stringify({...event, recovery_epoch: undefined,
        prompt: 'Newer native input: stop now.'}), timeout: 3000});
    if (lost.status === 0) throw new Error('fixture failed to contend on input publication');
  }
  return rename.call(this, from, to);
};
helper.hook(event);
process.stdout.write(JSON.stringify({injected}));
'''
        result = subprocess.run([self.node, '-e', script, str(RUNTIME), json.dumps(request)],
            env=self.environment, cwd=self.work, text=True, encoding='utf-8', capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['injected'])
        after = self.status()
        self.assertTrue(after['needsNativeReplay'])
        self.assertNotEqual(after['epoch'], before['epoch'])
        self.assertEqual(self.event('Stop'), {})

    def test_unbound_native_input_invalidates_the_known_caller_workspace(self):
        self.bind()
        for missing in ('session_id', 'cwd'):
            with self.subTest(missing=missing):
                event = {'session_id': 'test-session', 'cwd': str(self.work),
                         'hook_event_name': 'UserPromptSubmit', 'prompt': 'Stop.'}
                del event[missing]
                before = self.status()['epoch']
                result = subprocess.run([self.node, str(RUNTIME), '--hook', 'UserPromptSubmit'],
                    input=json.dumps(event), env=self.environment, cwd=self.work,
                    text=True, encoding='utf-8', capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('unbound-native-input', result.stderr)
                self.assertTrue(self.status()['needsNativeReplay'])
                self.assertNotEqual(self.status()['epoch'], before)
                self.assertEqual(self.event('Stop'), {})

    def test_input_failure_during_stop_publication_suppresses_old_continuation(self):
        self.bind()
        script = r'''
const fs = require('node:fs'), child = require('node:child_process');
const helper = require(process.argv[1]), cwd = process.argv[2], rename = fs.renameSync;
let injected = false;
fs.renameSync = function(from, to) {
  if (!injected && String(to).endsWith('.state.json')) {
    injected = true;
    const lost = child.spawnSync(process.execPath, [process.argv[1], '--hook', 'UserPromptSubmit'], {
      cwd, encoding: 'utf8', input: JSON.stringify({session_id: 'test-session', cwd,
        hook_event_name: 'UserPromptSubmit', prompt: 'Newer native input: stop now.'}), timeout: 3000});
    if (lost.status === 0) throw new Error('fixture failed to contend on Stop publication');
  }
  return rename.call(this, from, to);
};
const output = helper.hook({session_id: 'test-session', cwd, hook_event_name: 'Stop'});
process.stdout.write(JSON.stringify({injected, output}));
'''
        result = subprocess.run([self.node, '-e', script, str(RUNTIME), str(self.work)],
            env=self.environment, cwd=self.work, text=True, encoding='utf-8', capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'injected': True, 'output': {}})
        self.assertTrue(self.status()['needsNativeReplay'])
        self.assertFalse(self.status()['currentInputReconciled'])

    def test_unpersistable_input_failure_is_reported_unknown_not_durably_protected(self):
        self.bind()
        lock = Path(str(next(self.state.glob('*.input.json'))) + '.lock')
        lock.write_text(json.dumps({'pid': os.getpid()}), encoding='utf-8')
        fault = self.root / 'fail-watermark.cjs'
        fault.write_text('''
const fs = require('node:fs'), rename = fs.renameSync;
fs.renameSync = function(from, to) {
  if (String(to).endsWith('.input-failure.json')) throw Object.assign(new Error('denied'), {code:'EPERM'});
  return rename.call(this, from, to);
};
''', encoding='utf-8')
        try:
            result = subprocess.run([self.node, '-r', str(fault), str(RUNTIME), '--hook', 'UserPromptSubmit'],
                input=json.dumps({'session_id': 'test-session', 'cwd': str(self.work),
                                  'hook_event_name': 'UserPromptSubmit', 'prompt': 'Stop.'}),
                env=self.environment, cwd=self.work, text=True, encoding='utf-8', capture_output=True, timeout=10)
        finally:
            lock.unlink()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('freshness is unknown', result.stderr)
        self.assertFalse(list(self.state.glob('*.input-failure.json')))

    def test_unchanged_failure_does_not_loop_but_changed_observation_can_continue(self):
        self.bind()
        self.assertEqual(self.event("Stop", stop_hook_active=False)["decision"], "block")
        self.assertNotIn("decision", self.event("Stop", stop_hook_active=True))
        (self.work / "summary.json").write_text('{"total":60}', encoding="utf-8")
        self.assertEqual(self.event("Stop", stop_hook_active=True)["decision"], "block")
        self.assertNotIn("decision", self.event("Stop", stop_hook_active=True))

    def test_pause_does_not_reconcile_an_old_output_contract_with_new_requirements(self):
        self.bind()
        self.write_outputs()
        earlier = self.status()
        self.event('UserPromptSubmit', prompt='Pause; the deliverable now also needs an audit.json file.')
        current = self.status()
        self.invoke({'op': 'pause', 'epoch': current['epoch'], 'expectedRevision': current['revision'],
                     'reason': 'Pause now; the newly requested output has not been bound or produced.'})
        paused = self.status()
        self.assertFalse(paused['currentInputReconciled'])
        self.assertEqual(self.event('Stop'), {})
        self.assertIn('latest-user-input', self.invoke({'op': 'retire', 'epoch': paused['epoch'],
                      'expectedRevision': paused['revision']}, success=False))
        state = json.loads(next(self.state.glob('*.state.json')).read_text(encoding='utf-8'))
        self.assertEqual(state['epoch'], earlier['epoch'])
        self.assertFalse((self.work / 'audit.json').exists())

    def test_predicates_revision_and_reference_boundaries_are_real_checks(self):
        self.bind()
        current = self.status()
        self.assertIn("revision-conflict", self.invoke({"op": "bind", "epoch": current["epoch"],
                      "expectedRevision": 0}, success=False))
        self.assertIn("reason", self.invoke({"op": "bind", "epoch": current["epoch"],
            "expectedRevision": current["revision"], "result": "same", "inputs": [],
            "outputs": [{"path": "different.json"}], "nextAction": "write", "canContinue": True}, success=False))
        outside = self.invoke({"op": "bind", "epoch": current["epoch"], "expectedRevision": current["revision"],
            "result": "same", "inputs": ["../outside"], "outputs": [{"path": "summary.json"}],
            "nextAction": "write", "canContinue": True, "revisionReason": "probe"}, success=False)
        self.assertIn("workspace-relative", outside)
        self.bind(outputs=[{"path": "nested/summary.json", "json": {"/flag": False, "/zero": 0}}],
                  revisionReason="Exercise nested outputs and false-valued predicates.")
        (self.work / "nested").mkdir()
        (self.work / "nested/summary.json").write_text('{"flag":false,"zero":0}', encoding="utf-8")
        self.assertEqual(self.status()["inspection"]["status"], "verified-local")
        (self.work / "nested/summary.json").write_text('{"flag":false}', encoding="utf-8")
        self.assertEqual(self.status()["inspection"]["status"], "incomplete")

    def test_unbound_session_keeps_new_input_until_explicit_retirement_or_end(self):
        self.event("UserPromptSubmit", prompt="A new request arrived.", turn_id="newer")
        current = self.status()
        self.assertEqual(self.event("Stop", stop_hook_active=False, turn_id="older"), {})
        self.assertEqual(self.status()["epoch"], current["epoch"])
        self.assertEqual(self.event("SessionEnd"), {})
        self.assertEqual(list(self.state.iterdir()), [])

    def test_surviving_caller_can_retire_only_the_current_unbound_input_receipt(self):
        # A native prompt blocked by another Hook can exit without Stop/SessionEnd.
        # Cleanup has its own receipt and must not manufacture outcome acceptance.
        current = self.status()
        request = {"op": "retire", "epoch": current["epoch"], "expectedRevision": 0}
        self.assertIn("reason", self.invoke(request, success=False))
        request["reason"] = "Native process exited before the task was bound."
        self.event("UserPromptSubmit", prompt="A later request must survive old cleanup.")
        self.assertIn("current-receipt", self.invoke(request, success=False))
        self.assertTrue(list(self.state.glob("*.input.json")))
        current = self.status()
        retired = self.invoke({**request, "epoch": current["epoch"]})
        self.assertEqual(retired, {"retired": True, "scope": "unbound-input-receipt-only", "inspection": None})
        self.assertEqual(list(self.state.iterdir()), [])
        self.event("UserPromptSubmit", prompt="Deliver both files.")
        self.bind()
        current = self.status()
        self.assertIn("conflict", self.invoke({**request, "epoch": current["epoch"]}, success=False))
        self.assertEqual(self.status()["inspection"]["status"], "incomplete")
        self.assertEqual({p.name for p in self.work.iterdir()}, {"source.json", "keep.txt"})

    def test_recovery_keeps_live_locks_and_removes_only_dead_owned_lock(self):
        input_path = next(self.state.glob('*.input.json'))
        state_lock = input_path.with_name(input_path.name.replace('.input.json', '.lock'))
        state_lock.write_text(json.dumps({'pid': os.getpid()}), encoding='utf-8')
        self.assertIn('still-running', self.invoke({'op': 'recover-lock'}, success=False))
        self.assertTrue(state_lock.exists())
        dead = subprocess.check_output([self.node, '-e', 'process.stdout.write(String(process.pid))'],
                                       text=True, encoding='utf-8', timeout=10)
        state_lock.write_text(json.dumps({'pid': int(dead)}), encoding='utf-8')
        self.assertTrue(self.invoke({'op': 'recover-lock'})['recovered'])
        self.assertFalse(state_lock.exists())
        self.assertEqual(self.status()['mode'], 'unbound')
        input_lock = input_path.with_name(input_path.name + '.lock')
        input_lock.write_text(json.dumps({'pid': int(dead)}), encoding='utf-8')
        self.assertTrue(self.invoke({'op': 'recover-lock', 'lock': 'input'})['recovered'])
        self.assertTrue(input_path.exists())

    def test_cancellation_preserves_inputs_and_unfinished_state_survives_session_end(self):
        self.bind()
        self.event('SessionEnd')
        self.assertEqual(self.status()['inspection']['status'], 'incomplete')
        self.event('UserPromptSubmit', prompt='Cancel this task and keep my files.')
        current = self.status()
        request = {'op': 'retire', 'epoch': current['epoch'], 'expectedRevision': current['revision'],
                   'disposition': 'user-cancelled'}
        self.assertIn('reason', self.invoke(request, success=False))
        self.assertTrue(self.invoke({**request, 'reason': 'The user explicitly cancelled.'})['retired'])
        self.assertEqual(list(self.state.iterdir()), [])
        self.assertEqual({p.name for p in self.work.iterdir()}, {'source.json', 'keep.txt'})

    def test_input_arriving_during_retirement_cannot_be_deleted_by_old_result(self):
        self.bind()
        self.write_outputs()
        current = self.status()
        # Deliver a native input at the file-read boundary, after retirement has
        # read its old receipt but before publishing its deletion. No sleep race.
        script = '''
const fs = require('node:fs');
const runtime = require(process.argv[1]);
const request = JSON.parse(process.argv[2]);
const original = fs.readFileSync;
let delivered = false;
fs.readFileSync = function(file, ...args) {
  if (!delivered && String(file).endsWith('source.json')) {
    delivered = true;
    runtime.hook({session_id: request.session_id, cwd: request.cwd,
      hook_event_name: 'UserPromptSubmit', prompt: 'New requirement: keep working.'});
  }
  return original.call(this, file, ...args);
};
try { runtime.operate(request); process.exitCode = 2; }
catch (error) { process.stdout.write(error.message); }
'''
        request = {'op': 'retire', 'session_id': 'test-session', 'cwd': str(self.work),
                   'epoch': current['epoch'], 'expectedRevision': current['revision']}
        result = subprocess.run([self.node, '-e', script, str(RUNTIME), json.dumps(request)],
                                env=self.environment, capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('latest-user-input', result.stdout)
        self.assertNotEqual(self.status()['epoch'], current['epoch'])
        self.assertEqual(self.status()['revision'], current['revision'])
        self.assertEqual(self.event('Stop'), {})

    def check_retirement_deletion_failure(self, suffix, *, injected_input=True):
        current = self.status()
        before = {p.name: p.read_bytes() for p in self.state.iterdir() if p.name.endswith(('.state.json', '.input.json'))}
        script = '''
const fs = require('node:fs'), cp = require('node:child_process');
const runtime = require(process.argv[1]), request = JSON.parse(process.argv[2]);
const suffix = process.argv[3], inject = process.argv[4] === 'true';
const unlink = fs.unlinkSync; let delivered = false, child = null;
fs.unlinkSync = function(file, ...args) {
  if (!delivered && String(file).endsWith(suffix)) {
    delivered = true;
    if (!inject) throw Object.assign(new Error('test-delete-denied'), {code: 'EACCES'});
    child = cp.spawnSync(process.execPath, [process.argv[1], '--hook', 'UserPromptSubmit'], {
      env: process.env, cwd: request.cwd, encoding: 'utf8', timeout: 3000,
      input: JSON.stringify({session_id: request.session_id, cwd: request.cwd,
        hook_event_name: 'UserPromptSubmit', prompt: 'New input during checkpoint deletion.'})});
  }
  return unlink.call(this, file, ...args);
};
let result, error;
try { result = runtime.operate(request); } catch (e) { error = e.message; }
process.stdout.write(JSON.stringify({delivered, result, error,
  child: child && {status: child.status, stderr: child.stderr}}));
'''
        request = {'op': 'retire', 'session_id': 'test-session', 'cwd': str(self.work),
                   'epoch': current['epoch'], 'expectedRevision': current['revision'], 'reason': 'Owned test exit.'}
        result = subprocess.run([self.node, '-e', script, str(RUNTIME), json.dumps(request), suffix,
                                 str(injected_input).lower()], env=self.environment, capture_output=True,
                                text=True, encoding='utf8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['delivered'])
        self.assertNotIn('result', report)
        self.assertIn('latest-user-input' if injected_input else 'test-delete-denied', report['error'])
        if injected_input:
            self.assertEqual(report['child']['status'], 1)
            self.assertIn('EEXIST', report['child']['stderr'])
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()
                          if p.name.endswith(('.state.json', '.input.json'))}, before)
        after = self.status()
        self.assertEqual(after['revision'], current['revision'])
        self.assertEqual(after['needsNativeReplay'], injected_input)
        return after

    def test_failed_input_during_bound_deletion_preserves_recovery_context(self):
        self.bind()
        self.write_outputs()
        for suffix in ('.state.json', '.input.json'):
            with self.subTest(suffix=suffix):
                after = self.check_retirement_deletion_failure(suffix)
                self.assertIsNotNone(after['inspection'])
                self.event('UserPromptSubmit', prompt='New input during checkpoint deletion.',
                           recovery_epoch=after['epoch'])
                self.bind()
        current = self.status()
        self.assertTrue(self.invoke({'op': 'retire', 'epoch': current['epoch'],
                                    'expectedRevision': current['revision']})['retired'])

    def test_failed_input_during_unbound_deletion_preserves_receipt(self):
        after = self.check_retirement_deletion_failure('.input.json')
        self.assertEqual(after['mode'], 'unbound')

    def test_partial_checkpoint_deletion_restores_prior_files(self):
        self.bind()
        self.write_outputs()
        self.check_retirement_deletion_failure('.input.json', injected_input=False)

    def test_retirement_rejects_mixed_output_bytes_and_mid_inspection_source_change(self):
        # Deterministic file-read boundaries exercise actual predicate evaluation,
        # not timing sleeps. No single output satisfies the mixed predicates.
        script = '''
const fs = require('node:fs');
const path = require('node:path');
const runtime = require(process.argv[1]);
const request = JSON.parse(process.argv[2]);
const mode = process.argv[3], original = fs.readFileSync;
let changed = false;
fs.readFileSync = function(file, ...args) {
  const bytes = original.call(this, file, ...args);
  if (!changed && String(file).endsWith('summary.json')) {
    changed = true;
    fs.writeFileSync(path.join(request.cwd, mode === 'output' ? 'summary.json' : 'source.json'),
      mode === 'output' ? '{"total":70}' : '{"units":70}');
  }
  return bytes;
};
try { runtime.operate(request); process.exitCode = 2; }
catch (error) { process.stdout.write(error.message); }
'''
        for mode in ('output', 'input'):
            with self.subTest(mode=mode):
                self.event('UserPromptSubmit', prompt='Check this independent file-change case.')
                (self.work / 'source.json').write_bytes(b'{"units":60}')
                self.write_outputs()
                outputs = [{'path': 'summary.json', 'json': {'/total': 60}}]
                if mode == 'output':
                    outputs[0].update(sha256=hashlib.sha256((self.work / 'summary.json').read_bytes()).hexdigest(),
                                      json={'/total': 70})
                self.bind(outputs=outputs, revisionReason='Exercise the specified file-change boundary.')
                current = self.status()
                request = {'op': 'retire', 'session_id': 'test-session', 'cwd': str(self.work),
                           'epoch': current['epoch'], 'expectedRevision': current['revision']}
                result = subprocess.run([self.node, '-e', script, str(RUNTIME), json.dumps(request), mode],
                    env=self.environment, capture_output=True, text=True, encoding='utf-8', timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('unmet-output', result.stdout)
                self.assertTrue(list(self.state.glob('*.state.json')))
                self.assertTrue(list(self.state.glob('*.input.json')))

    def test_input_lock_recovery_requires_native_replay_before_old_task_can_continue(self):
        self.bind()
        before = self.status()
        input_path = next(self.state.glob('*.input.json'))
        dead = subprocess.check_output([self.node, '-e', 'process.stdout.write(String(process.pid))'],
                                       text=True, encoding='utf-8', timeout=10)
        Path(str(input_path) + '.lock').write_text(json.dumps({'pid': int(dead)}), encoding='utf-8')
        self.assertIn('EEXIST', self.invoke({'hook_event_name': 'UserPromptSubmit',
                      'prompt': 'Pause this task.'}, hook=True, success=False))
        self.assertTrue(self.invoke({'op': 'recover-lock', 'lock': 'input'})['recovered'])
        current = self.status()
        self.assertNotEqual(current['epoch'], before['epoch'])
        self.assertFalse(current['currentInputReconciled'])
        self.assertEqual(self.event('Stop'), {})
        self.assertIn('native-replay', self.invoke({'op': 'bind', 'epoch': current['epoch'],
                      'expectedRevision': current['revision']}, success=False))
        self.invoke({'op': 'pause', 'epoch': current['epoch'], 'expectedRevision': current['revision'],
                     'reason': 'Hold while the surviving caller reconciles the actual native event.'})
        current = self.status()
        self.assertFalse(current['currentInputReconciled'])
        self.assertIn('native-replay', self.invoke({'op': 'retire', 'epoch': current['epoch'],
                      'expectedRevision': current['revision']}, success=False))
        # The surviving caller replays the observed native event, without asking
        # the user to repeat it or treating the old checkpoint as fresh authority.
        self.event('UserPromptSubmit', prompt='Pause this task.', recovery_epoch=current['epoch'])
        current = self.status()
        self.invoke({'op': 'pause', 'epoch': current['epoch'], 'expectedRevision': current['revision'],
                     'reason': 'Reconciled the actual native pause input after receipt failure.'})
        self.assertEqual(self.event('Stop'), {})
        self.assertFalse((self.work / 'summary.json').exists())

    def test_initial_input_recovery_does_not_fabricate_or_overwrite_native_input(self):
        input_path = next(self.state.glob('*.input.json'))
        input_path.unlink()  # The first receipt was never published before its owner died.
        dead = subprocess.check_output([self.node, '-e', 'process.stdout.write(String(process.pid))'],
                                       text=True, encoding='utf-8', timeout=10)
        Path(str(input_path) + '.lock').write_text(json.dumps({'pid': int(dead)}), encoding='utf-8')
        self.assertTrue(self.invoke({'op': 'recover-lock', 'lock': 'input'})['needsNativeReplay'])
        self.assertFalse(input_path.exists())
        self.assertIn('receipt-missing', self.invoke({'op': 'status'}, success=False))
        self.assertEqual(self.event('Stop'), {})
        self.event('UserPromptSubmit', prompt='Replay the observed native input.', recovery_epoch=None)
        self.event('UserPromptSubmit', prompt='A newer actual native input.')
        current = self.status()
        for expected in (None, current['epoch']):
            self.assertIn('replay-conflict', self.invoke({'hook_event_name': 'UserPromptSubmit',
                          'prompt': 'Old replay must not replace the newer input.', 'recovery_epoch': expected},
                          hook=True, success=False))
        self.assertEqual(self.status()['epoch'], current['epoch'])

    def test_failed_native_receipt_publication_cannot_leave_an_old_task_usable(self):
        self.bind()
        fault = self.root / 'fail-publish.cjs'
        fault.write_text('''
const fs = require('node:fs'), rename = fs.renameSync;
fs.renameSync = function(from, to) {
  if (String(to).endsWith('.input.json')) throw Object.assign(new Error('publish denied'), {code: 'EPERM'});
  return rename.call(this, from, to);
};
''', encoding='utf-8')
        event = {'session_id': 'test-session', 'cwd': str(self.work),
                 'hook_event_name': 'UserPromptSubmit', 'prompt': 'Cancel the old task.'}
        result = subprocess.run([self.node, '-r', str(fault), str(RUNTIME), '--hook'],
            input=json.dumps(event), env=self.environment, capture_output=True, text=True,
            encoding='utf-8', timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('EPERM', result.stderr)
        self.assertTrue(list(self.state.glob('*.input.json.lock')))
        self.assertIn('EEXIST', self.invoke({'op': 'status'}, success=False))
        self.assertIn('EEXIST', self.invoke({'hook_event_name': 'Stop'}, hook=True, success=False))
        self.invoke({'op': 'recover-lock', 'lock': 'input'})
        current = self.status()
        self.assertTrue(current['needsNativeReplay'])
        self.assertFalse(current['currentInputReconciled'])
        self.assertEqual(self.event('Stop'), {})
        self.event('UserPromptSubmit', prompt=event['prompt'], recovery_epoch=current['epoch'])
        current = self.status()
        self.invoke({'op': 'retire', 'epoch': current['epoch'], 'expectedRevision': current['revision'],
                     'disposition': 'user-cancelled', 'reason': 'Replayed the actual native cancellation.'})
        self.assertEqual(list(self.state.iterdir()), list(self.state.glob('*.input-failure.json')))
        self.assertEqual(len(list(self.state.iterdir())), 1,
                         'keep the failure watermark until its owning state directory is safely retired')
        self.assertFalse((self.work / 'summary.json').exists())


if __name__ == "__main__":
    unittest.main()
