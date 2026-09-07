"""Executable local task behavior; native Hook loading and model behavior are separate."""
import json
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
        result = subprocess.run([self.node, str(RUNTIME), *(["--hook"] if hook else [])],
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

    def test_unchanged_failure_does_not_loop_but_changed_observation_can_continue(self):
        self.bind()
        self.assertEqual(self.event("Stop", stop_hook_active=False)["decision"], "block")
        self.assertNotIn("decision", self.event("Stop", stop_hook_active=True))
        (self.work / "summary.json").write_text('{"total":60}', encoding="utf-8")
        self.assertEqual(self.event("Stop", stop_hook_active=True)["decision"], "block")
        self.assertNotIn("decision", self.event("Stop", stop_hook_active=True))

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

    def test_unbound_session_has_no_continuation_and_no_retained_input_after_end(self):
        self.assertEqual(self.event("Stop", stop_hook_active=False), {})
        self.assertEqual(self.event("SessionEnd"), {})
        self.assertEqual(list(self.state.iterdir()), [])

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


if __name__ == "__main__":
    unittest.main()
