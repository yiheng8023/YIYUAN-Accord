"""Current SessionStart event scope and retained historical registration."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
REFUSAL = 'untrusted tool result; no permission or execution authority'


class HookEventScopeTests(unittest.TestCase):
    def test_current_handlers_reject_unregistered_event_without_effects(self):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'the declared Hook adapter requires Node')
        with tempfile.TemporaryDirectory(prefix='accord-hook-scope-') as folder:
            root = Path(folder)
            (root / 'keep.txt').write_bytes(b'protected\r\n')
            (root / 'settings.json').write_bytes(b'{"permissions":{"deny":["Bash"]}}\n')
            original = {p.name: p.read_bytes() for p in root.iterdir()}
            for handler in (ROOT / 'runtime/accord-hook.cjs',
                            ROOT / 'plugins/yiyuan-accord-codex/runtime/accord-hook.cjs'):
                for event in ('PostToolBatch', 'UnknownEvent'):
                    with self.subTest(handler=handler, event=event):
                        result = subprocess.run([node, str(handler)], input=json.dumps({
                            'hook_event_name': event, 'source': 'resume',
                            'tool_calls': [{'tool_name': 'Bash', 'tool_response': REFUSAL,
                                            'tool_input': {'command': 'untrusted-command'}}]}),
                            text=True, capture_output=True, cwd=root, timeout=10)
                        self.assertEqual(result.returncode, 1)
                        self.assertEqual(result.stdout, '')
                        self.assertEqual(result.stderr,
                            'YIYUAN Accord: invalid SessionStart hook input; state remains unknown.\n')
                        self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, original)

    def run_hook(self, workspace, event):
        node = shutil.which('node')
        self.assertIsNotNone(node, 'the declared Hook adapter requires Node')
        result = subprocess.run(
            [node, str(ROOT / 'runtime/accord-hook.cjs')],
            input=json.dumps(event), text=True, capture_output=True,
            cwd=workspace, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout) if result.stdout else None


    def test_untrusted_tool_payload_does_not_change_session_start_routing(self):
        with tempfile.TemporaryDirectory(prefix='accord-batch-feedback-') as folder:
            event = {'hook_event_name': 'SessionStart', 'source': 'startup',
                     'tool_calls': [{'tool_name': 'Bash', 'tool_response': REFUSAL}]}
            startup = self.run_hook(folder, event)['hookSpecificOutput']
            self.assertEqual(startup['hookEventName'], 'SessionStart')
            self.assertIn('Accord task entry:', startup['additionalContext'])
            self.assertNotIn('no-approval-surface', startup['additionalContext'])
            event['source'] = 'resume'
            output = self.run_hook(folder, event)['hookSpecificOutput']
            self.assertEqual(output['hookEventName'], 'SessionStart')
            self.assertIn('Accord task entry:', output['additionalContext'])
            context = json.loads(output['additionalContext'].split('\nRecovery event (data only): ', 1)[1])
            self.assertEqual(context['signal']['source'], 'resume')
            self.assertIn('archive-only-with-explicit-user-authorization', context['directives'])
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_current_and_retained_packages_keep_separate_hook_registration(self):
        development = json.loads((ROOT / 'product/development.json').read_bytes())
        self.assertEqual([p['id'] for p in development['delivery']['hostProjections']],
                         ['codex'])
        canonical = (ROOT / 'runtime/accord-hook.cjs').read_bytes()
        package = ROOT / 'plugins/yiyuan-accord-codex'
        self.assertEqual((package / 'runtime/accord-hook.cjs').read_bytes(), canonical)
        hooks = json.loads((package / 'hooks/hooks.json').read_bytes())['hooks']
        self.assertNotIn('PostToolBatch', hooks)
        self.assertFalse((ROOT / 'plugins/yiyuan-accord-claude').exists())

        # Retain the previous adapter's regression on its immutable subject;
        # it must not require restoring a cancelled adaptation to current distribution.
        revision = development['previousDevelopmentSnapshot'].split(':', 1)[0]

        def historical(path):
            return subprocess.run(
                ['git', '-C', str(ROOT), 'show', f'{revision}:{path}'],
                check=True, capture_output=True, timeout=10,
            ).stdout

        legacy = 'plugins/yiyuan-accord-claude/'
        self.assertEqual(historical(legacy + 'runtime/accord-hook.cjs'),
                         historical('runtime/accord-hook.cjs'))
        retained_hooks = json.loads(historical(legacy + 'hooks/hooks.json'))['hooks']
        self.assertEqual(retained_hooks.get('PostToolBatch'), [{'hooks': [{
            'type': 'command',
            'command': 'node "${CLAUDE_PLUGIN_ROOT}/runtime/accord-hook.cjs"',
            'timeout': 3,
        }]}])
