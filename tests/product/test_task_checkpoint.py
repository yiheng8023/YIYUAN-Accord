"""Executable local task behavior; native Hook loading and model behavior are separate."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import copy
import time


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
        preload = ['--require', str(self.preload)] if hasattr(self, 'preload') else []
        result = subprocess.run([self.node, *preload, str(RUNTIME), *(["--hook", request['hook_event_name']] if hook else [])],
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

    def pause(self, reason='User paused.'):
        current = self.status()
        return self.invoke(dict(op='pause', epoch=current['epoch'], expectedRevision=current['revision'], reason=reason))

    def bind(self, **fields):
        current = self.status()
        return self.invoke({"op": "bind", "epoch": current["epoch"], "expectedRevision": current["revision"],
            "result": "Correct CSV and JSON from the current source", "inputs": ["source.json", "keep.txt"],
            "outputs": [{"path": "summary.json", "json": {"/total": 60}}, {"path": "details.csv"}],
            "nextAction": "write and independently check both files", "canContinue": True, **fields})

    def write_outputs(self, total=60):
        (self.work / "summary.json").write_text(json.dumps({"total": total}), encoding="utf-8")
        (self.work / "details.csv").write_text(f"id,units\nA,{total}\n", encoding="utf-8")

    def test_interactive_stdin_fails_promptly_without_waiting_or_mutating_task_state(self):
        preload = self.root / 'interactive-stdin.cjs'
        preload.write_text("Object.defineProperty(process.stdin,'isTTY',{value:true});", encoding='utf-8')
        before = {p.name:p.read_bytes() for p in self.state.iterdir()}
        process = subprocess.Popen([self.node, '--require', str(preload), str(RUNTIME)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=self.work, env=self.environment)
        try:
            self.assertEqual(process.wait(timeout=3), 1)
            stdout, stderr = process.communicate()
            self.assertEqual(stdout, b'')
            self.assertIn(b'pipe one JSON object or use --help', stderr)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        self.assertEqual({p.name:p.read_bytes() for p in self.state.iterdir()}, before)
        help_result = subprocess.run([self.node, '--require', str(preload), str(RUNTIME), '--help'],
            capture_output=True, text=True, encoding='utf-8', timeout=3, cwd=self.work, env=self.environment)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn('status', json.loads(help_result.stdout))
        self.assertEqual(self.status()['mode'], 'unbound')

    def test_native_text_survives_side_question_compact_and_pause_without_new_authority(self):
        goal = '交付 review.json 和 review.md；不得读取上级目录。原样保留 🌱 与 "引文"。'
        correction = '同意，补充检查引用；保持暂停，先不要交付。'
        self.event('UserPromptSubmit', prompt=goal)
        self.bind(unresolved=['Await the requested review.'])
        self.pause('User decision remains pending.')
        self.event('UserPromptSubmit', prompt=correction)
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        self.event('SessionStart', source='compact')
        page = self.invoke({'op': 'read-native-input'})
        self.assertEqual([row['text'] for row in page['entries']][1:], [goal, correction])
        self.assertIsNone(page['next'])
        status = self.status()
        self.assertEqual(status['mode'], 'paused')
        self.assertFalse(status['currentInputReconciled'])
        self.assertEqual(status['checkpoint']['unresolved'], ['Await the requested review.'])
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)

    def test_native_text_read_needs_no_filesystem_writes(self):
        self.bind(unresolved=['Decision pending.'])
        self.pause()
        self.event('SessionStart', source='compact')
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        self.preload = self.root / 'deny-writes.cjs'
        self.preload.write_text("const fs=require('node:fs'),open=fs.openSync;"
            "const deny=()=>{throw Object.assign(new Error('read-only filesystem'),{code:'EROFS'});};"
            "fs.openSync=(p,f,...a)=>f==='r'?open(p,f,...a):deny();"
            "for(const k of ['writeSync','writeFileSync','mkdirSync','renameSync','unlinkSync'])fs[k]=deny;",
            encoding='utf-8')
        page = self.invoke({'op': 'read-native-input'})
        self.assertTrue(page['available'])
        self.assertEqual(page['entries'][0]['text'],
                         'Deliver both files from the source and preserve the input.')
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)

    def test_native_text_read_preserves_existing_publication_locks(self):
        receipt = next(self.state.glob('*.input.json'))
        for lock in [receipt.with_name(receipt.name + '.lock'),
                     receipt.with_name(receipt.name.replace('.input.json', '.lock'))]:
            with self.subTest(lock=lock.name):
                lock.write_text(json.dumps({'pid': os.getpid()}), encoding='utf-8')
                before = {p.name: p.read_bytes() for p in self.state.iterdir()}
                self.assertIn('input-read-busy', self.invoke({'op': 'read-native-input'}, success=False))
                self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)
                lock.unlink()

    def test_native_text_read_rejects_changed_receipt_or_failure_evidence(self):
        receipt = next(self.state.glob('*.input.json'))
        failure = receipt.with_name(receipt.name.replace('.input.json', '.input-failure.json'))
        for change in ['receipt', 'failure']:
            with self.subTest(change=change):
                self.preload = self.root / 'concurrent-input.cjs'
                self.preload.write_text("const fs=require('node:fs'),read=fs.readFileSync;let n=0;"
                    f"const target={json.dumps(str(receipt))},failure={json.dumps(str(failure))};"
                    "fs.readFileSync=(p,...a)=>{let b=read(p,...a);if(String(p)===target&&++n===2){"
                    + ("let v=JSON.parse(b);v.epoch='concurrent-input';b=Buffer.from(JSON.stringify(v));"
                       if change == 'receipt' else
                       "fs.writeFileSync(failure,JSON.stringify({schema:1,generation:'concurrent-failure'}));")
                    + "}return b;};", encoding='utf-8')
                self.assertIn('input-changed-during-read',
                              self.invoke({'op': 'read-native-input'}, success=False))
        del self.preload
        self.assertTrue(self.status()['needsNativeReplay'])
        self.assertEqual(json.loads(failure.read_text())['generation'], 'concurrent-failure')

    def test_native_text_read_rejects_publication_started_during_read(self):
        receipt = next(self.state.glob('*.input.json'))
        lock = receipt.with_name(receipt.name + '.lock')
        self.preload = self.root / 'publication-start.cjs'
        self.preload.write_text("const fs=require('node:fs'),read=fs.readFileSync;"
            f"const target={json.dumps(str(receipt))},lock={json.dumps(str(lock))};"
            "fs.readFileSync=(p,...a)=>{const b=read(p,...a);if(String(p)===target)"
            "fs.writeFileSync(lock,JSON.stringify({pid:process.pid}));return b;};", encoding='utf-8')
        self.assertIn('input-read-busy', self.invoke({'op': 'read-native-input'}, success=False))
        self.assertTrue(lock.exists())

    def test_native_text_paging_preserves_unicode_and_captured_order(self):
        expected = ['甲🌱乙\n"丙"', '', '同意。']
        for prompt in expected:
            self.event('UserPromptSubmit', prompt=prompt)
        cursor = {'index': 1, 'offset': 0}
        restored = {index: '' for index in range(1, 4)}
        before = self.status()
        while cursor is not None:
            page = self.invoke({'op': 'read-native-input', 'maxChars': 2, **cursor})
            self.assertLessEqual(sum(len(row['text']) for row in page['entries']), 2)
            for row in page['entries']:
                restored[row['index']] += row['text']
                self.assertEqual(row['promptSha256'], hashlib.sha256(expected[row['index'] - 1].encode()).hexdigest())
            self.assertNotEqual(page['next'], cursor)
            cursor = page['next']
        self.assertEqual(list(restored.values()), expected)
        self.assertEqual(self.status(), before)
        for fields in ({'index': -1}, {'offset': -1}, {'offset': 9999}, {'maxChars': 0}, {'maxChars': 16001}):
            self.assertIn('invalid-input-page', self.invoke({'op': 'read-native-input', **fields}, success=False))

    def test_legacy_receipt_does_not_invent_missing_native_text(self):
        path = next(self.state.glob('*.input.json'))
        legacy = json.loads(path.read_text(encoding='utf-8'))
        del legacy['nativeInputs']
        path.write_text(json.dumps(legacy), encoding='utf-8')
        before = path.read_bytes()
        page = self.invoke({'op': 'read-native-input'})
        self.assertFalse(page['available'])
        self.assertEqual(page['entries'], [])
        self.assertEqual(path.read_bytes(), before)
        self.event('UserPromptSubmit', prompt='A newly captured side question.')
        page = self.invoke({'op': 'read-native-input'})
        self.assertEqual(page['coverage'], 'captured-hook-inputs-only')
        self.assertEqual([row['text'] for row in page['entries']], ['A newly captured side question.'])

    def test_host_continuation_is_not_retained_as_a_new_user_request(self):
        self.bind()
        continuation = self.event('Stop')['reason']
        original = self.invoke({'op': 'read-native-input'})['entries']
        self.event('UserPromptSubmit', prompt=continuation)
        self.assertEqual(self.invoke({'op': 'read-native-input'})['entries'], original)
        self.event('SessionStart', source='resume')
        recovery_epoch = self.status()['epoch']
        self.event('UserPromptSubmit', prompt='Actual retained native input.', recovery_epoch=recovery_epoch)
        page = self.invoke({'op': 'read-native-input'})
        self.assertEqual(page['entries'][-1]['source'], 'retained-native-replay')
        self.assertEqual(page['entries'][-1]['text'], 'Actual retained native input.')
        self.assertEqual(page['entries'][-1]['recoveryEpoch'], recovery_epoch)
        self.assertNotEqual(page['entries'][-1]['epoch'], recovery_epoch)

    def test_large_retained_inputs_survive_failed_publication_recovery_and_retirement(self):
        for prompt in ('a' * 80000, 'b' * 80000):
            self.event('UserPromptSubmit', prompt=prompt)
        self.bind()
        path = next(self.state.glob('*.input.json'))
        self.assertGreater(path.stat().st_size, 128 * 1024)
        before = path.read_bytes()
        self.preload = self.root / 'fail-input-write.cjs'
        self.preload.write_text("const fs=require('node:fs');const rename=fs.renameSync;"
            "fs.renameSync=(a,b)=>{if(String(b).endsWith('.input.json'))throw Error('receipt-write-failed');return rename(a,b)};", encoding='utf-8')
        self.assertIn('receipt-write-failed', self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': 'Still paused.'}, hook=True, success=False))
        del self.preload
        self.assertEqual(path.read_bytes(), before)
        self.assertIn('EEXIST', self.invoke({'op': 'status'}, success=False))
        self.invoke({'op': 'recover-lock', 'lock': 'input'})
        page = self.invoke({'op': 'read-native-input', 'index': 2, 'maxChars': 1})
        self.assertEqual(page['entries'][0]['text'], 'b')
        self.assertTrue(self.status()['needsNativeReplay'])
        self.event('UserPromptSubmit', prompt='Finish the approved delivery.', recovery_epoch=self.status()['epoch'])
        self.bind()
        self.event('SessionEnd')
        self.assertEqual(self.status()['recoveryInputs']['count'], 4)
        self.write_outputs()
        current = self.status()
        self.invoke({'op': 'retire', 'epoch': current['epoch'], 'expectedRevision': current['revision']})
        self.assertFalse(list(self.state.glob('*.input.json')))

    def test_corrupt_retained_text_is_not_returned_or_repaired_by_readback(self):
        path = next(self.state.glob('*.input.json'))
        value = json.loads(path.read_text(encoding='utf-8'))
        value['nativeInputs'][0]['prompt'] = 'Corrupted goal and authority.'
        path.write_text(json.dumps(value), encoding='utf-8')
        before = path.read_bytes()
        self.assertIn('invalid-retained-input', self.invoke({'op': 'read-native-input'}, success=False))
        self.assertEqual(path.read_bytes(), before)
        value['nativeInputs'][0]['promptSha256'] = hashlib.sha256(value['nativeInputs'][0]['prompt'].encode()).hexdigest()
        value['nativeInputs'][0]['recoveryEpoch'] = 'contradictory-replay-identity'
        path.write_text(json.dumps(value), encoding='utf-8')
        before = path.read_bytes()
        self.assertIn('invalid-retained-input', self.invoke({'op': 'read-native-input'}, success=False))
        self.assertEqual(path.read_bytes(), before)

    def test_full_input_receipt_rejects_capture_without_silently_dropping_history(self):
        path = next(self.state.glob('*.input.json'))
        value = json.loads(path.read_text(encoding='utf-8'))
        prompt = 'x' * 120000
        value['nativeInputs'] = [dict(epoch=f'fixture-{index}', turnId=None, source='native-input-event',
            prompt=prompt, promptSha256=hashlib.sha256(prompt.encode()).hexdigest()) for index in range(69)]
        path.write_text(json.dumps(value), encoding='utf-8')
        self.assertLess(path.stat().st_size, 8 * 1024 * 1024)
        before = path.read_bytes()
        self.assertIn('oversize-state-object', self.invoke({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt}, hook=True, success=False))
        self.assertEqual(path.read_bytes(), before)
        self.assertIn('EEXIST', self.invoke({'op': 'status'}, success=False))
        self.invoke({'op': 'recover-lock', 'lock': 'input'})
        self.assertTrue(self.status()['needsNativeReplay'])
        self.assertEqual(self.status()['recoveryInputs']['count'], 69)

    def test_unbound_input_retirement_removes_text_without_touching_other_sessions(self):
        self.event('UserPromptSubmit', session_id='other-session', prompt='Other task data.')
        self.event('SessionEnd')
        self.assertIn('native-user-input-receipt-missing', self.invoke({'op': 'read-native-input'}, success=False))
        other = self.invoke({'op': 'read-native-input', 'session_id': 'other-session'})
        self.assertEqual([row['text'] for row in other['entries']], ['Other task data.'])

    def test_compact_reentry_preserves_pause_identity_and_pending_contract(self):
        self.bind(unresolved=['The customer scope remains undecided.'])
        self.pause('Wait for the customer decision.')
        original = self.status()
        files = {p.name: p.read_bytes() for p in self.state.iterdir()}
        output = self.event('SessionStart', source='compact', model='changed-host-model')
        context = output['hookSpecificOutput']['additionalContext']
        self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'SessionStart')
        self.assertIn('Accord context recovery', context)
        self.assertIn('Accord task entry', context)
        self.assertNotIn('Native host observations', context)
        restored = self.status()
        self.assertEqual(restored['epoch'], original['epoch'])
        self.assertEqual(restored['checkpoint'], original['checkpoint'])
        self.assertEqual(restored['mode'], 'paused')
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, files)
        self.assertEqual(self.event('Stop'), {})

    def test_compact_without_input_receipt_does_not_manufacture_state(self):
        files = {p.name: p.read_bytes() for p in self.state.iterdir()}
        output = self.event('SessionStart', source='compact', session_id='new-unbound-session')
        context = output['hookSpecificOutput']['additionalContext']
        self.assertIn('Accord context recovery', context)
        self.assertIn('unknown', context)
        self.assertNotIn('Native input receipt:', context)
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, files)

    def test_compact_reentry_does_not_clear_an_interruption(self):
        self.bind()
        self.event('Interrupt')
        files = {p.name: p.read_bytes() for p in self.state.iterdir()}
        original = self.status()
        self.event('SessionStart', source='compact')
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, files)
        self.assertEqual(self.status(), original)
        self.assertEqual(self.event('Stop'), {})

    def test_compact_read_failure_does_not_fabricate_native_input_loss(self):
        self.bind()
        self.pause()
        files = {p.name: p.read_bytes() for p in self.state.iterdir()}
        lock = Path(str(next(self.state.glob('*.input.json'))) + '.lock')
        lock.write_text(json.dumps({'pid':os.getpid()}), encoding='utf-8')
        try:
            output = self.event('SessionStart', source='compact')
            self.assertIn('unknown', output['hookSpecificOutput']['additionalContext'])
        finally:
            lock.unlink()
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, files)
        self.assertFalse(self.status()['needsNativeReplay'])

    def test_compact_reentry_preserves_existing_input_loss_quarantine(self):
        self.bind()
        lock = Path(str(next(self.state.glob('*.input.json'))) + '.lock')
        lock.write_text(json.dumps({'pid':os.getpid()}), encoding='utf-8')
        try:
            self.invoke({'hook_event_name':'UserPromptSubmit','prompt':'Changed scope.'}, hook=True, success=False)
        finally:
            lock.unlink()
        original = self.status()
        self.assertTrue(original['needsNativeReplay'])
        files = {p.name: p.read_bytes() for p in self.state.iterdir()}
        context = self.event('SessionStart', source='compact')['hookSpecificOutput']['additionalContext']
        self.assertIn('unknown', context)
        self.assertNotIn('Native input receipt:', context)
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, files)
        self.assertEqual(self.status(), original)

    def test_rebinding_after_side_question_preserves_pause_and_unfinished_contract(self):
        self.bind(unresolved=['Operating facts still need confirmation.'])
        self.pause('User paused execution pending review.')
        self.event('SessionStart', source='resume')
        self.event('UserPromptSubmit', prompt='Explain progress and adjust the plan to 70; execution remains paused.')
        outputs = [{'path': 'summary.json', 'json': {'/total': 70}}, {'path': 'details.csv'}]
        rebound = self.bind(outputs=outputs, revisionReason='The user corrected the planned total; the pause remains in force.')
        self.assertEqual(rebound['mode'], 'paused')
        checked = self.status()
        self.assertEqual(checked['mode'], 'paused')
        self.assertEqual(checked['checkpoint']['reason'], 'User paused execution pending review.')
        self.assertEqual(checked['checkpoint']['outputs'], outputs)
        self.assertEqual(checked['checkpoint']['unresolved'], ['Operating facts still need confirmation.'])
        self.assertTrue(checked['currentInputReconciled'])
        self.assertEqual(self.event('Stop'), {})
        self.event('SessionEnd')
        self.assertEqual(self.status()['checkpoint'], checked['checkpoint'])
        self.assertFalse((self.work / 'summary.json').exists())

    def test_pause_requires_explicit_resume_disposition_before_successful_retirement(self):
        self.bind()
        self.write_outputs()
        self.pause()
        paused = self.status()
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        self.assertIn('paused-task', self.invoke(dict(op='retire', epoch=paused['epoch'],
                      expectedRevision=paused['revision']), success=False))
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)
        self.event('UserPromptSubmit', prompt='Resume the approved work and finish the verified local delivery.')
        reason = 'The current user input explicitly resumes this paused local delivery.'
        self.assertEqual(self.bind(resumeReason=reason)['mode'], 'active')
        resumed = self.status()
        self.assertEqual(resumed['mode'], 'active')
        self.assertEqual(resumed['checkpoint']['resumeReason'], reason)
        self.assertIsNone(resumed['checkpoint']['reason'])
        self.assertTrue(self.invoke(dict(op='retire', epoch=resumed['epoch'], expectedRevision=resumed['revision']))['retired'])
        self.assertEqual(list(self.state.iterdir()), [])

    def test_invalid_resume_disposition_preserves_existing_state(self):
        self.bind()
        active = self.status()
        request = dict(op='bind', epoch=active['epoch'], expectedRevision=active['revision'],
                       result='Preserve current work', inputs=['source.json', 'keep.txt'],
                       outputs=active['checkpoint']['outputs'], nextAction='Continue if allowed', canContinue=True)
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        self.assertIn('resume', self.invoke({**request, 'resumeReason': 'No pause exists.'}, success=False))
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)
        self.pause()
        paused = self.status()
        request['expectedRevision'] = paused['revision']
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        for reason in ('', ' ', None, False, 'x' * 2049):
            with self.subTest(reason=repr(reason)[:20]):
                self.assertIn('resume', self.invoke({**request, 'resumeReason': reason}, success=False))
                self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)

    def test_recorded_unresolved_work_survives_green_files_and_prevents_retirement(self):
        question = 'Verify the operating instructions against the actual tool.'
        self.bind(unresolved=[question])
        self.write_outputs()
        current = self.status()
        self.assertEqual(current['checkpoint']['unresolved'], [question])
        self.assertEqual(current['inspection']['status'], 'unresolved')
        self.assertTrue(all(row['matched'] for row in current['inspection']['outputs']))
        self.assertIn('unmet-output-cannot-retire', self.invoke(dict(op='retire', epoch=current['epoch'],
                       expectedRevision=current['revision']), success=False))
        first = self.event('Stop')
        self.assertEqual(first['decision'], 'block')
        self.assertNotIn('decision', self.event('Stop'), 'unchanged unknowns must not cause endless retries')
        self.assertEqual(self.status()['checkpoint']['unresolved'], [question])

    def test_rebinding_inherits_unknowns_and_removal_requires_explicit_disposition(self):
        question = 'Actual save behavior is not yet evidenced.'
        self.bind(unresolved=[question], canContinue=False)
        self.write_outputs()
        self.event('SessionStart', source='resume')
        self.event('UserPromptSubmit', prompt='Continue the same delivery with the newly supplied manual.')
        self.bind()  # A caller using the prior file-only interface must not erase it.
        current = self.status()
        self.assertEqual(current['checkpoint']['unresolved'], [question])
        self.assertEqual(current['inspection']['status'], 'unresolved')
        request = dict(op='bind', epoch=current['epoch'], expectedRevision=current['revision'],
                       result='Complete the same delivery', inputs=['source.json', 'keep.txt'],
                       outputs=current['checkpoint']['outputs'], nextAction='verify source', canContinue=True,
                       unresolved=[])
        self.assertIn('changed-unresolved-conditions-need-reason', self.invoke(request, success=False))
        self.assertEqual(self.status()['checkpoint'], current['checkpoint'])
        (self.work / 'manual.txt').write_text('Inspected tool instructions supplied for this fixture.', encoding='utf-8')
        request.update(inputs=['source.json', 'keep.txt', 'manual.txt'],
                       revisionReason='Inspected the supplied manual and corrected the affected instructions.')
        self.invoke(request)
        checked = self.status()
        self.assertEqual(checked['checkpoint']['unresolved'], [])
        self.assertEqual(checked['inspection']['status'], 'verified-local')
        self.assertEqual(checked['checkpoint']['revisionReason'], request['revisionReason'])
        self.assertTrue(self.invoke(dict(op='retire', epoch=checked['epoch'], expectedRevision=checked['revision']))['retired'])

    def test_waiting_unknowns_preserve_pause_end_and_explicit_cancellation(self):
        self.bind(unresolved=['Missing source requires the user.'], canContinue=False)
        self.write_outputs()
        current = self.status()
        self.assertEqual(self.event('Stop'), {})
        self.event('SessionEnd')
        self.assertEqual(self.status()['checkpoint'], current['checkpoint'])
        self.invoke(dict(op='pause', epoch=current['epoch'], expectedRevision=current['revision'], reason='User paused.'))
        self.event('UserPromptSubmit', prompt='Explain the current result only.')
        self.assertEqual(self.status()['mode'], 'paused')
        self.assertEqual(self.status()['checkpoint']['unresolved'], ['Missing source requires the user.'])
        self.assertEqual(self.event('Stop'), {})
        self.event('UserPromptSubmit', prompt='Cancel this task and release its checkpoint.')
        current = self.status()
        retired = self.invoke(dict(op='retire', epoch=current['epoch'], expectedRevision=current['revision'],
                              disposition='user-cancelled', reason='The latest user input cancels this task.'))
        self.assertTrue(retired['retired'])
        self.assertEqual(retired['inspection']['status'], 'unresolved')
        self.assertEqual(list(self.state.iterdir()), [])

    def test_invalid_unresolved_conditions_cannot_replace_a_healthy_binding(self):
        self.bind(unresolved=['Keep this unresolved responsibility.'])
        original = self.status()['checkpoint']
        for invalid in (None, 'not a list', [''], ['  '], ['same', 'same'], [{}], ['x' * 2049], ['x'] * 33):
            with self.subTest(invalid=invalid):
                current = self.status()
                error = self.invoke(dict(op='bind', epoch=current['epoch'], expectedRevision=current['revision'],
                    result='Same result', inputs=['source.json'], outputs=original['outputs'],
                    nextAction='Continue', canContinue=True, unresolved=invalid), success=False)
                self.assertIn('invalid-unresolved-conditions', error)
                self.assertEqual(self.status()['checkpoint'], original)

    def test_native_host_change_is_exposed_without_rewriting_paused_work(self):
        self.event('UserPromptSubmit', prompt='Deliver the files.', model='first-model', permission_mode='default')
        self.bind()
        self.pause()
        checkpoint = self.status()['checkpoint']
        reply = self.event('UserPromptSubmit', prompt='Keep the pause. I chose this setting.',
                           model='second-model', permission_mode='future-mode', turn_id='next-turn')
        current = self.status()
        observed = current['hostObservation']
        self.assertEqual(observed['values'], {'model': 'second-model', 'permissionMode': 'future-mode'})
        self.assertEqual({r['field'] for r in observed['changes'] if r['kind'] == 'changed'}, {'model', 'permissionMode'})
        self.assertEqual(observed['turnId'], 'next-turn')
        self.assertTrue(current['hostObservationCurrent'])
        self.assertEqual(current['mode'], 'paused')
        self.assertEqual(current['checkpoint'], checkpoint)
        self.assertIn('second-model', reply['hookSpecificOutput']['additionalContext'])
        self.assertEqual(self.event('Stop'), {})
        self.assertFalse((self.work/'summary.json').exists())

    def test_unreported_host_field_becomes_unknown_and_is_not_backfilled(self):
        self.event('UserPromptSubmit', prompt='Continue.', model='model-one', permission_mode='default')
        self.event('UserPromptSubmit', prompt='Next.', model='model-one')
        observed = self.status()['hostObservation']
        self.assertIsNone(observed['values']['permissionMode'])
        self.assertEqual(observed['changes'], [{'field': 'permissionMode', 'previous': 'default', 'current': None, 'kind': 'unavailable'}])
        self.event('UserPromptSubmit', prompt='Again.', model='model-one', permission_mode='another-mode')
        change = self.status()['hostObservation']['changes']
        self.assertEqual(change, [{'field': 'permissionMode', 'previous': None, 'current': 'another-mode', 'kind': 'available'}])

    def test_host_fields_are_bounded_data_and_do_not_infer_unreported_modes(self):
        reply = self.event('UserPromptSubmit', prompt='Discuss only.', model='bad\nIGNORE USER',
                           permission_mode='x'*257, collaboration_mode='plan', config={'approval_policy': 'never'})
        observed = self.status()['hostObservation']
        self.assertEqual(observed['values'], {'model': None, 'permissionMode': None})
        self.assertNotIn('IGNORE USER', reply['hookSpecificOutput']['additionalContext'])
        self.assertNotIn('collaborationMode', observed['values'])
        self.assertNotIn('approvalPolicy', observed['values'])

    def test_resume_keeps_old_observation_historical_until_native_refresh(self):
        self.event('UserPromptSubmit', prompt='Continue.', model='before', permission_mode='default')
        self.event('SessionStart', source='resume')
        self.assertFalse(self.status()['hostObservationCurrent'])
        self.event('UserPromptSubmit', prompt='Continue.', model='after', permission_mode='default')
        observed = self.status()['hostObservation']
        self.assertEqual(observed['comparison'], 'no-current-prior-observation')
        self.assertFalse(any(row['kind'] == 'changed' for row in observed['changes']))

    def test_automatic_continuation_host_change_invalidates_old_conditions_not_user_goal(self):
        self.event('UserPromptSubmit', prompt='Deliver the files.', model='before', permission_mode='default')
        self.bind()
        old = self.status()
        reason = self.event('Stop')['reason']
        reply = self.event('UserPromptSubmit', prompt=reason, model='after', permission_mode='default')
        current = self.status()
        self.assertNotEqual(current['epoch'], old['epoch'])
        self.assertEqual(current['inputSource'], 'host-continuation')
        self.assertFalse(current['currentInputReconciled'])
        self.assertEqual(current['checkpoint'], old['checkpoint'])
        self.assertIn('not a new user decision', reply['hookSpecificOutput']['additionalContext'])
        self.assertEqual(self.event('Stop'), {})

    def context_request(self):
        current = self.status()
        scope = dict(threadId="native-thread", turnId="native-turn", hostVersion="observed-host",
                     model="discovered-model", contextGeneration="after-reconciliation")
        now = int(time.time() * 1000)
        return dict(op="assess-context", epoch=current["epoch"], expectedRevision=current["revision"],
                    conditions=scope, assessment=dict(conditions=copy.deepcopy(scope), epoch=current["epoch"],
                    observedAtMs=now - 100, validUntilMs=now + 30000, sourceRef="offline-bound-fixture",
                    integrity="verified", usageEvent={"method": "thread/tokenUsage/updated", "params": {
                        "threadId": scope["threadId"], "turnId": scope["turnId"], "tokenUsage": {
                            "modelContextWindow": 10000, "total": {"totalTokens": 9999999},
                            "last": {"inputTokens": 4000, "outputTokens": 100, "totalTokens": 4100}}}},
                    estimates=dict(sourceRef="offline-estimate-not-native-measurement", contextUpperBoundTokens=5000,
                                   nextWorkTokens=1000, handoffTokens=500, recoveryTokens=500, safetyMarginTokens=500,
                                   efficiencyCeilingTokens=8000, efficiencySourceRef="offline-range-fixture")))

    def test_context_budget_reserves_takeover_and_recovery_before_more_work(self):
        self.bind()
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        for work, context, expected in ((1000, 5000, "continue-bounded"),
                                        (1500, 5000, "prepare-handoff"),
                                        (0, 6500, "preserve-recovery")):
            request = self.context_request()
            request["assessment"]["estimates"].update(nextWorkTokens=work, contextUpperBoundTokens=context)
            answer = self.invoke(request)
            self.assertEqual(answer["decision"], expected)
            self.assertFalse(answer["sourceReleaseAllowed"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.state.iterdir()})

    def test_context_budget_does_not_invent_occupancy_efficiency_or_loss(self):
        for field, value, expected in (("contextUpperBoundTokens", None, "unknown"),
                                       ("efficiencyCeilingTokens", None, "unknown"),
                                       ("recoveryTokens", 0, "unknown"),
                                       ("safetyMarginTokens", -1, "unknown"),
                                       ("handoffTokens", True, "unknown"),
                                       ("sourceRef", "", "unknown")):
            with self.subTest(field=field):
                request = self.context_request()
                request["assessment"]["estimates"][field] = value
                self.assertEqual(self.invoke(request)["decision"], expected)
        for integrity, expected in (("unknown", "unknown"), ("degraded", "reassess")):
            request = self.context_request()
            request["assessment"].update(integrity=integrity, compactionCount=15)
            self.assertEqual(self.invoke(request)["decision"], expected)
        request = self.context_request()
        request["assessment"]["estimates"].update(efficiencyCeilingTokens=None, nextWorkTokens=5000)
        self.assertEqual(self.invoke(request)["decision"], "prepare-handoff")

    def test_context_budget_invalidates_changed_carrier_input_and_expired_evidence(self):
        for field in ("model", "hostVersion", "contextGeneration", "threadId", "turnId"):
            request = self.context_request()
            request["conditions"][field] = "changed"
            self.assertEqual(self.invoke(request)["decision"], "reassess")
        request = self.context_request()
        request["assessment"]["validUntilMs"] = 0
        self.assertEqual(self.invoke(request)["decision"], "reassess")
        request = self.context_request()
        self.event("UserPromptSubmit", prompt="A new authoritative correction")
        self.assertEqual(self.invoke(request)["decision"], "reassess")

    def test_context_budget_native_capacity_must_match_specific_thread_and_turn(self):
        for field in ("threadId", "turnId"):
            request = self.context_request()
            request["assessment"]["usageEvent"]["params"][field] = "another"
            self.assertEqual(self.invoke(request)["decision"], "unknown")
        request = self.context_request()
        request["assessment"]["usageEvent"]["params"]["tokenUsage"]["modelContextWindow"] = None
        self.assertEqual(self.invoke(request)["decision"], "unknown")
        request = self.context_request()
        request["assessment"]["usageEvent"]["params"]["tokenUsage"]["modelContextWindow"] = 6000
        self.assertEqual(self.invoke(request)["decision"], "preserve-recovery")

    def test_context_budget_cannot_clear_pause_or_input_loss(self):
        self.bind()
        self.pause('user stopped')
        self.assertEqual(self.invoke(self.context_request())["decision"], "paused")
        self.assertEqual(self.status()["mode"], "paused")
        self.event("SessionStart", source="resume")
        self.assertEqual(self.invoke(self.context_request())["decision"], "paused")
        self.assertTrue(self.status()["needsResumeReconciliation"])

    def signal_request(self):
        now = int(time.time() * 1000)
        return dict(binding=dict(connectionId="owned-connection", threadId="thread", hostVersion="host", model="model"),
                    turnId="turn", connected=True, maxAgeMs=30000, events=[
                        dict(receivedAtMs=now - 10, event={"method": "turn/started", "params": {
                            "threadId": "thread", "turn": {"id": "turn"}}}),
                        dict(receivedAtMs=now, event={"method": "thread/tokenUsage/updated", "params": {
                            "threadId": "thread", "turnId": "turn", "tokenUsage": {
                                "modelContextWindow": 10000, "total": {"totalTokens": 1000000}}}})])

    def signals(self, request):
        result = subprocess.run([self.node, str(RUNTIME), "--context-signals"], input=json.dumps(request),
                                text=True, encoding="utf-8", capture_output=True, timeout=10,
                                env=self.environment, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_native_signals_keep_capacity_separate_from_occupancy_and_connection(self):
        request = self.signal_request()
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        result = self.signals(request)
        self.assertEqual(result["windowTokens"], 10000)
        self.assertIsNone(result["occupancy"])
        self.assertIsNone(result["efficiency"])
        self.assertEqual(result["integrity"], "unknown")
        changed = copy.deepcopy(request)
        changed["binding"]["connectionId"] = "reconnected"
        self.assertNotEqual(result["conditions"]["contextGeneration"],
                            self.signals(changed)["conditions"]["contextGeneration"])
        request["connected"] = False
        self.assertEqual(self.signals(request)["state"], "unknown")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.state.iterdir()})

    def test_native_signals_require_new_usage_after_reroute_and_compaction(self):
        for event in (
            {"method": "model/rerouted", "params": {"threadId": "thread", "turnId": "turn", "toModel": "new-model"}},
            {"method": "item/completed", "params": {"threadId": "thread", "turnId": "turn", "item": {
                "type": "contextCompaction", "id": "compact"}}},
        ):
            request = self.signal_request()
            old = self.signals(request)
            at = request["events"][-1]["receivedAtMs"]
            request["events"].append(dict(receivedAtMs=at, event=event))
            self.assertEqual(self.signals(request)["state"], "unknown")
            request["events"].append(copy.deepcopy(request["events"][1]))
            new = self.signals(request)
            self.assertEqual(new["state"], "window-observed")
            self.assertNotEqual(old["observationId"], new["observationId"])
            self.assertNotEqual(old["conditions"]["contextGeneration"], new["conditions"]["contextGeneration"])
        request = self.signal_request()
        request["events"].append(dict(receivedAtMs=request["events"][-1]["receivedAtMs"], event={
            "method": "item/started", "params": {"threadId": "thread", "turnId": "turn", "item": {
                "type": "contextCompaction", "id": "still-running"}}}))
        request["events"].append(copy.deepcopy(request["events"][1]))
        self.assertEqual(self.signals(request)["state"], "unknown")

    def test_native_signals_reject_old_turn_future_expired_and_reordered_records(self):
        request = self.signal_request()
        request["turnId"] = "other-turn"
        self.assertEqual(self.signals(request)["state"], "unknown")

        for offset in (-100000, 100000):
            request = self.signal_request()
            for item in request["events"]: item["receivedAtMs"] += offset
            self.assertEqual(self.signals(request)["state"], "unknown")
        request = self.signal_request()
        request["events"].reverse()
        self.assertEqual(self.signals(request)["state"], "unknown")
        request = self.signal_request()
        request["events"][-1]["event"]["params"]["tokenUsage"]["modelContextWindow"] = None
        self.assertEqual(self.signals(request)["state"], "unknown")
        request = self.signal_request()
        request["events"].append(dict(receivedAtMs=request["events"][-1]["receivedAtMs"], event={
            "method": "turn/completed", "params": {"threadId": "thread", "turn": {"id": "turn"}}}))
        self.assertEqual(self.signals(request)["state"], "unknown")

    def test_budget_with_native_signals_rejects_a_superseded_observation(self):
        request = self.context_request()
        request["signals"] = signals = self.signal_request()
        observed = self.signals(signals)
        request["conditions"] = observed["conditions"]
        request["assessment"].update(conditions=observed["conditions"], observationId=observed["observationId"],
                                     usageEvent=observed["usageEvent"])
        self.assertEqual(self.invoke(request)["decision"], "continue-bounded")
        signals["events"][-1]["event"]["params"]["tokenUsage"]["modelContextWindow"] = 6000
        self.assertEqual(self.invoke(request)["decision"], "reassess")
        signals["connected"] = False
        self.assertEqual(self.invoke(request)["decision"], "reassess")

    def default_storage_fixture(self):
        self.preload = self.root / 'isolated-os.cjs'
        self.preload.write_text("const os=require('node:os'); os.homedir=()=>process.env.ACCORD_TEST_HOME; "
                                "os.tmpdir=()=>process.env.ACCORD_TEST_TEMP;", encoding='utf-8')
        self.environment.pop('YIYUAN_ACCORD_TASK_STATE_DIR', None)
        self.environment.update(ACCORD_TEST_HOME=str(self.root / 'home'), ACCORD_TEST_TEMP=str(self.root / 'temp-a'))
        return self.root / 'home/.yiyuan-accord/task-state'

    def test_cold_process_recovers_partial_work_after_temp_directory_changes(self):
        stable = self.default_storage_fixture()
        self.event('UserPromptSubmit', prompt='Deliver both files from the source and preserve the input.')
        current = self.status()
        request = {'op':'bind', 'session_id':'test-session', 'cwd':str(self.work),
                   'epoch':current['epoch'], 'expectedRevision':0, 'result':'Deliver both files',
                   'inputs':['source.json', 'keep.txt'],
                   'outputs':[{'path':'summary.json','json':{'/total':60}}, {'path':'details.csv'}],
                   'nextAction':'Finish missing details, inspect both outputs, then retire', 'canContinue':True}
        script = """
const fs=require('node:fs'), runtime=require(process.argv[1]), request=JSON.parse(process.argv[2]);
const bound=runtime.operate(request);
fs.writeFileSync('summary.json', JSON.stringify({total:60}));
fs.writeFileSync(process.argv[3], JSON.stringify(bound));
process.kill(process.pid, 'SIGKILL');
"""
        ack = self.root / 'before-process-death.json'
        killed = subprocess.run([self.node,'--require',str(self.preload),'-e',script,str(RUNTIME),json.dumps(request),str(ack)],
                                cwd=self.work, env=self.environment, capture_output=True, timeout=10)
        self.assertNotEqual(killed.returncode, 0)
        self.assertEqual(json.loads(ack.read_text())['revision'], 1)
        self.assertTrue(list(stable.glob('*.state.json')))
        self.environment['ACCORD_TEST_TEMP'] = str(self.root / 'temp-b')
        restored = self.status()
        self.assertEqual(restored['checkpoint']['result'], 'Deliver both files')
        self.assertEqual(restored['inspection']['status'], 'incomplete')
        self.assertEqual(restored['storage']['kind'], 'durable-user-data')
        self.assertEqual(self.event('Stop')['decision'], 'block')
        self.assertIn('native-user-input-receipt-missing', self.invoke({'op':'status','session_id':'foreign'}, success=False))
        self.write_outputs()
        latest = self.status()
        self.invoke({'op':'retire','epoch':latest['epoch'],'expectedRevision':latest['revision']})
        self.assertFalse(list(stable.iterdir()))
        self.assertEqual((self.work / 'source.json').read_text(), '{"units":60}')

    def test_cold_readback_preserves_pause_and_new_input_requires_reconciliation(self):
        self.default_storage_fixture()
        self.event('UserPromptSubmit', prompt='Prepare the files.')
        self.bind()
        self.pause()
        self.environment['ACCORD_TEST_TEMP'] = str(self.root / 'temp-b')
        self.event('UserPromptSubmit', prompt='Explain progress; work remains paused.')
        restored = self.status()
        self.assertEqual(restored['mode'], 'paused')
        self.assertFalse(restored['currentInputReconciled'])
        self.assertEqual(self.event('Stop'), {})
        self.assertEqual(restored['checkpoint']['reason'], 'User paused.')

    def test_resume_holds_old_continuation_until_native_reconciliation(self):
        self.bind()
        old = self.status()
        self.event('SessionStart', source='resume')
        restored = self.status()
        self.assertFalse(restored['needsNativeReplay'])
        self.assertTrue(restored['needsResumeReconciliation'])
        self.assertFalse(restored['currentInputReconciled'])
        self.assertNotEqual(old['epoch'], restored['epoch'])
        self.assertEqual(restored['checkpoint'], old['checkpoint'])
        self.assertEqual(self.event('Stop'), {})
        self.assertIn('resumed-task-needs-native-input-reconciliation', self.invoke({
            'op':'bind', 'epoch':restored['epoch'], 'expectedRevision':restored['revision']}, success=False))
        # The native caller supplies retained input, not fabricated authority.
        self.event('UserPromptSubmit', prompt='Deliver both files from the source and preserve the input.',
                   recovery_epoch=restored['epoch'])
        self.assertEqual(self.event('Stop'), {})
        self.bind()
        self.assertEqual(self.event('Stop')['decision'], 'block')
        self.write_outputs()
        current = self.status()
        self.invoke({'op':'retire','epoch':current['epoch'],'expectedRevision':current['revision']})
        self.assertFalse(list(self.state.iterdir()))

    def test_resumed_native_input_enters_without_controller_replay(self):
        self.bind()
        self.event('SessionStart', source='resume')
        resume_epoch = self.status()['epoch']
        # Ordinary native delivery has no Accord recovery_epoch parameter.
        self.event('UserPromptSubmit', prompt='Continue, but deliver only A with 55 units. Preserve the originals.')
        current = self.status()
        self.assertFalse(current['needsNativeReplay'])
        self.assertFalse(current['needsResumeReconciliation'])
        self.assertFalse(current['currentInputReconciled'])
        self.assertIn('native-replay-conflict', self.invoke({'hook_event_name':'UserPromptSubmit',
            'prompt':'An obsolete retained input', 'recovery_epoch':resume_epoch}, hook=True, success=False))
        self.assertEqual(self.status()['epoch'], current['epoch'])
        self.assertEqual(self.event('Stop'), {})
        self.bind(outputs=[{'path':'summary.json','json':{'/total':55}},{'path':'details.csv'}],
                  revisionReason='Latest native user input changed the total to 55.')
        self.write_outputs(55)
        current = self.status()
        self.invoke({'op':'retire','epoch':current['epoch'],'expectedRevision':current['revision']})
        self.assertFalse(list(self.state.iterdir()))
        self.assertEqual((self.work/'source.json').read_text(), '{"units":60}')

    def test_resume_does_not_relax_actual_input_loss_quarantine(self):
        self.bind()
        self.invoke({'hook_event_name':'UserPromptSubmit'}, hook=True, success=False)
        self.assertTrue(self.status()['needsNativeReplay'])
        self.event('SessionStart', source='resume')
        self.assertTrue(self.status()['needsNativeReplay'])
        self.assertIn('input-receipt-needs-native-replay', self.invoke({
            'hook_event_name':'UserPromptSubmit','prompt':'A new input cannot silently clear lost input.'},
            hook=True, success=False))
        self.assertEqual(self.event('Stop'), {})

    def test_resume_preserves_pause_and_other_sessions(self):
        self.bind()
        self.pause()
        before = {p.name:p.read_bytes() for p in self.state.iterdir()}
        self.event('SessionStart', source='resume', session_id='unrelated')
        self.event('SessionStart', source='compact')
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.state.iterdir()})
        self.event('SessionStart', source='resume')
        restored = self.status()
        self.event('UserPromptSubmit', prompt='Explain progress; work remains paused.')
        self.assertFalse(self.status()['needsResumeReconciliation'])
        self.assertEqual(self.status()['mode'], 'paused')
        self.assertEqual(self.status()['checkpoint']['reason'], 'User paused.')
        self.assertEqual(self.event('Stop'), {})

    def test_repeated_resume_rejects_stale_recovery_receipt(self):
        self.bind()
        self.event('SessionStart', source='resume')
        first = self.status()
        self.event('SessionStart', source='resume')
        second = self.status()
        self.assertNotEqual(first['epoch'], second['epoch'])
        self.assertIn('native-replay-conflict', self.invoke({'hook_event_name':'UserPromptSubmit',
            'prompt':'Deliver both files.', 'recovery_epoch':first['epoch']}, hook=True, success=False))
        self.assertEqual(self.status()['epoch'], second['epoch'])
        self.assertEqual(self.event('Stop'), {})

    def test_failed_resume_publication_cannot_leave_old_input_usable(self):
        self.bind()
        before = self.status()['checkpoint']
        self.preload = self.root / 'fail-resume.cjs'
        self.preload.write_text("const fs=require('node:fs'), rename=fs.renameSync; "
            "fs.renameSync=(a,b)=>{if(b.endsWith('.input.json'))throw Error('resume-write-failed');return rename(a,b)};",
            encoding='utf-8')
        self.assertIn('resume-write-failed', self.invoke({'hook_event_name':'SessionStart','source':'resume'},
                                                       hook=True, success=False))
        del self.preload
        self.invoke({'op':'recover-lock','lock':'input'})
        recovered = self.status()
        self.assertTrue(recovered['needsNativeReplay'])
        self.assertEqual(recovered['checkpoint'], before)
        self.assertEqual(self.event('Stop'), {})

    def test_legacy_state_is_visible_and_competing_locations_are_not_merged(self):
        self.bind()
        stable = self.default_storage_fixture()
        legacy = Path(self.environment['ACCORD_TEST_TEMP']) / 'yiyuan-accord-tasks'
        shutil.copytree(self.state, legacy)
        restored = self.status()
        self.assertEqual(restored['storage']['kind'], 'legacy-temporary')
        self.assertEqual(restored['checkpoint']['result'], 'Correct CSV and JSON from the current source')
        self.assertFalse(stable.exists())
        shutil.copytree(legacy, stable)
        before = {str(p):p.read_bytes() for folder in (legacy,stable) for p in folder.iterdir()}
        self.assertIn('conflicting-state-locations', self.invoke({'op':'status'}, success=False))
        self.assertEqual(before, {str(p):p.read_bytes() for folder in (legacy,stable) for p in folder.iterdir()})

    def test_flush_failure_does_not_publish_a_new_checkpoint(self):
        self.bind()
        current = self.status()
        before = {p.name:p.read_bytes() for p in self.state.iterdir()}
        script = """
const fs=require('node:fs'), runtime=require(process.argv[1]);
fs.fsyncSync=()=>{throw new Error('test-flush-failed')};
try {runtime.operate(JSON.parse(process.argv[2]));process.exitCode=2;}
catch(e){process.stdout.write(e.message);}
"""
        request = {'op':'pause','session_id':'test-session','cwd':str(self.work),
                   'epoch':current['epoch'],'expectedRevision':current['revision'],'reason':'User paused.'}
        failed = subprocess.run([self.node,'-e',script,str(RUNTIME),json.dumps(request)],
                                cwd=self.work, env=self.environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(failed.returncode,0,failed.stderr)
        self.assertIn('test-flush-failed',failed.stdout)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.state.iterdir()})

    def test_default_storage_does_not_create_through_redirected_parent(self):
        stable = self.default_storage_fixture()
        stable.parent.parent.mkdir()
        outside = self.root / 'redirect-target'
        outside.mkdir()
        made = subprocess.run([self.node,'-e',
            "require('node:fs').symlinkSync(process.argv[1],process.argv[2],process.platform==='win32'?'junction':'dir')",
            str(outside),str(stable.parent)],capture_output=True,text=True,timeout=10)
        self.assertEqual(made.returncode,0,made.stderr)
        self.assertIn('unsafe-state-directory',self.invoke({'hook_event_name':'UserPromptSubmit','prompt':'Create no redirected state.'},hook=True,success=False))
        self.assertEqual(list(outside.iterdir()),[])

    def test_native_entry_lifecycle_survives_missing_detailed_skill(self):
        # Mechanism ablation checks entry delivery and state effects, not prose
        # fragments as a substitute for actual semantic behavior.
        isolated = self.root / 'package/runtime/task-checkpoint.cjs'
        isolated.parent.mkdir(parents=True)
        isolated.write_bytes(RUNTIME.read_bytes())
        request = {'hook_event_name': 'UserPromptSubmit', 'session_id': 'no-skill',
                   'cwd': str(self.work), 'prompt': 'What can I do with these orders?'}
        run = subprocess.run([self.node, str(isolated), '--hook', 'UserPromptSubmit'],
            input=json.dumps(request), text=True, encoding='utf-8', capture_output=True,
            env=self.environment, cwd=self.work, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        output = json.loads(run.stdout)
        self.assertEqual(set(output), {'hookSpecificOutput'})
        context = output['hookSpecificOutput']['additionalContext']
        self.assertTrue(isinstance(context, str) and context.strip())
        self.assertEqual(output['hookSpecificOutput']['hookEventName'], 'UserPromptSubmit')
        status = subprocess.run([self.node, str(isolated)],
            input=json.dumps({'op': 'status', 'session_id': 'no-skill', 'cwd': str(self.work)}),
            text=True, encoding='utf-8', capture_output=True, env=self.environment, cwd=self.work, timeout=10)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)['mode'], 'unbound')
        self.assertIsNone(json.loads(status.stdout)['checkpoint'])
        self.assertFalse(list(self.state.glob('*.state.json')))
        self.assertEqual(self.invoke({'session_id': 'no-skill', 'hook_event_name': 'Stop'}, hook=True), {})
        self.invoke({'session_id': 'no-skill', 'hook_event_name': 'SessionEnd'}, hook=True)
        self.assertEqual(len(list(self.state.glob('*.input.json'))), 1)  # setUp session survives

    def test_new_input_exposes_pending_work_without_carrying_old_authority(self):
        self.bind()
        previous = self.status()
        response = self.event('UserPromptSubmit', prompt='Also, why are some orders missing?')
        self.assertIn('unfinished checkpoint remains', response['hookSpecificOutput']['additionalContext'])
        self.assertIn('reconcile this input', response['hookSpecificOutput']['additionalContext'])
        current = self.status()
        self.assertEqual(current['revision'], previous['revision'])
        self.assertFalse(current['currentInputReconciled'])
        self.assertEqual(self.event('Stop'), {})
        self.invoke({'op': 'pause', 'epoch': current['epoch'], 'expectedRevision': current['revision'],
                     'reason': 'The actual user has paused dependent changes.'})
        response = self.event('UserPromptSubmit', prompt='Explain the last result.')
        self.assertIn('paused checkpoint remains', response['hookSpecificOutput']['additionalContext'])
        self.assertEqual(self.event('Stop'), {})

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

    def test_status_contract_supports_recovery_and_revision_without_private_state_access(self):
        self.assertIsNone(self.status()['checkpoint'])
        self.bind()
        earlier = self.status()
        self.event('UserPromptSubmit', prompt='Change the total to 55 and update both files.')
        current = self.status()
        contract = current['checkpoint']
        self.assertEqual(contract['epoch'], earlier['epoch'])
        self.assertNotEqual(contract['epoch'], current['epoch'])
        self.assertFalse(current['currentInputReconciled'])
        self.assertEqual(contract['outputs'][0]['json'], {'/total': 60})
        self.assertEqual(contract['inputs'][0]['observed']['sha256'],
                         hashlib.sha256((self.work / 'source.json').read_bytes()).hexdigest())
        request = {key: contract[key] for key in ('result', 'outputs', 'nextAction', 'canContinue')}
        request.update(op='bind', epoch=current['epoch'], expectedRevision=current['revision'],
                       inputs=[item['path'] for item in contract['inputs']])
        request['outputs'][0]['json']['/total'] = 55
        request['result'] = 'Both files reflect the user correction to 55.'
        self.assertIn('changed-output-contract-needs-reason', self.invoke(request, success=False))
        request['revisionReason'] = 'The latest user input changed the approved total.'
        self.assertEqual(self.invoke(request)['revision'], 2)
        self.write_outputs(55)
        revised = self.status()
        self.assertTrue(revised['currentInputReconciled'])
        self.assertEqual(revised['checkpoint']['revisionReason'], request['revisionReason'])
        self.assertEqual(revised['inspection']['status'], 'verified-local')
        self.assertTrue(self.invoke({'op':'retire', 'epoch':revised['epoch'],
                                    'expectedRevision':revised['revision']})['retired'])

    def test_contract_readback_does_not_resume_pause_or_acknowledge_lost_input(self):
        self.bind()
        self.pause('The user has paused work.')
        paused = self.status()
        self.assertEqual(paused['mode'], 'paused')
        self.assertEqual(paused['checkpoint']['reason'], 'The user has paused work.')
        self.assertEqual(self.event('Stop'), {})
        lock = Path(str(next(self.state.glob('*.input.json'))) + '.lock')
        lock.write_text(json.dumps({'pid':os.getpid()}), encoding='utf-8')
        try:
            self.invoke({'hook_event_name':'UserPromptSubmit', 'prompt':'Cancel this work.'},
                        hook=True, success=False)
        finally:
            lock.unlink()
        current = self.status()
        self.assertEqual(current['checkpoint'], paused['checkpoint'])
        self.assertTrue(current['needsNativeReplay'])
        self.assertFalse(current['currentInputReconciled'])
        self.assertEqual(current['mode'], 'paused')
        self.assertEqual(self.event('Stop'), {})
        self.assertIn('replay', self.invoke({'op':'bind', 'epoch':current['epoch'],
                                           'expectedRevision':current['revision']}, success=False))
        self.assertTrue(self.status()['needsNativeReplay'])

    def test_contract_remains_readable_when_files_are_uninspectable_without_state_writes(self):
        self.bind()
        contract = self.status()['checkpoint']
        self.event('Stop')  # Exercise internal continuation fields excluded from readback.
        (self.work / 'summary.json').mkdir()
        before = {p.name:p.read_bytes() for p in self.state.iterdir()}
        for _ in range(2):
            current = self.status()
            self.assertEqual(current['inspection']['status'], 'inspection-unavailable')
            self.assertEqual(current['checkpoint'], contract)
            self.assertNotIn('continuation', current['checkpoint'])
            self.assertNotIn('lastBlock', current['checkpoint'])
        self.assertEqual({p.name:p.read_bytes() for p in self.state.iterdir()}, before)

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
        self.bind(resumeReason="The latest user input explicitly continues the paused work.")
        self.assertEqual(self.status()['mode'], 'active')
        self.event("Interrupt")
        self.assertEqual(self.event("Stop", stop_hook_active=False), {})
        self.assertFalse((self.work / "summary.json").exists())

    def test_uninspectable_files_do_not_block_status_pause_or_explicit_cancellation(self):
        for name in ('summary.json', 'source.json'):
            with self.subTest(path=name):
                self.event('UserPromptSubmit', prompt='Produce the approved files.')
                self.bind()
                current = self.status()
                path = self.work / name
                original = path.read_bytes() if path.exists() else None
                if path.exists():
                    path.unlink()
                path.mkdir()
                try:
                    request = {'epoch': current['epoch'], 'expectedRevision': current['revision']}
                    self.assertIn('reference-is-not-a-file', self.invoke(
                        {'op': 'retire', **request}, success=False))
                    status = self.status()
                    self.assertEqual(status['inspection']['status'], 'inspection-unavailable')
                    self.assertIn('reference-is-not-a-file', status['inspection']['error'])
                    paused = self.invoke({'op': 'pause', **request, 'reason': 'User paused.'})
                    self.assertEqual(paused['mode'], 'paused')
                    self.assertEqual(paused['pending']['status'], 'inspection-unavailable')
                    self.assertEqual(self.event('Stop'), {})
                    self.assertIn('task-revision-or-input-conflict', self.invoke(
                        {'op': 'retire', **request, 'disposition': 'user-cancelled',
                         'reason': 'User cancelled.'}, success=False))
                    retired = self.invoke({'op': 'retire', 'epoch': current['epoch'],
                        'expectedRevision': paused['revision'], 'disposition': 'user-cancelled',
                        'reason': 'User cancelled; preserve all workspace contents.'})
                    self.assertTrue(retired['retired'])
                    self.assertEqual(retired['inspection']['status'], 'inspection-unavailable')
                    self.assertTrue(path.is_dir())
                    self.assertEqual((self.work / 'keep.txt').read_bytes(), b'user-owned input\n')
                    self.assertFalse(list(self.state.glob('*.state.json')))
                    self.assertFalse(list(self.state.glob('*.input.json')))
                finally:
                    path.rmdir()
                    if original is not None:
                        path.write_bytes(original)

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

    def test_session_end_preserves_interrupted_unbound_input_until_explicit_retirement(self):
        original = self.invoke({'op': 'read-native-input'})['entries']
        self.event('Interrupt')
        interrupted = self.status()
        before = {p.name: p.read_bytes() for p in self.state.iterdir()}
        self.event('SessionEnd')
        self.assertEqual({p.name: p.read_bytes() for p in self.state.iterdir()}, before)
        self.assertEqual(self.invoke({'op': 'read-native-input'})['entries'], original)
        self.assertFalse(self.status()['hostObservationCurrent'])
        self.assertEqual(self.status()['mode'], 'unbound')
        self.event('SessionStart', source='resume')
        self.assertTrue(self.status()['needsResumeReconciliation'])
        self.event('SessionEnd')
        self.assertEqual(self.invoke({'op': 'read-native-input'})['entries'], original)
        self.event('UserPromptSubmit', prompt='The task is cancelled; retain the original files.')
        current = self.status()
        self.assertIn('current-receipt', self.invoke({'op': 'retire', 'epoch': interrupted['epoch'],
            'expectedRevision': 0, 'reason': 'Old cleanup must not discard new input.'}, success=False))
        self.assertTrue(self.invoke({'op': 'retire', 'epoch': current['epoch'], 'expectedRevision': 0,
            'reason': 'Current explicit cancellation; no unfinished fixture effects remain.'})['retired'])
        self.assertEqual(list(self.state.iterdir()), [])
        self.assertEqual({p.name for p in self.work.iterdir()}, {'source.json', 'keep.txt'})

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
