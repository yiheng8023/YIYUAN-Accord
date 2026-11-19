"""Check the standalone Claude candidate's sources and native event contract."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import build_claude_plugin as builder


class ClaudeCodeAdapterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="accord-claude-")
        self.addCleanup(temporary.cleanup)
        self.market = Path(temporary.name) / "local market"
        self.package = builder.build(self.market)
        self.current = builder.ROOT / builder.CURRENT
        self.hook = self.package / "runtime/accord-hook.cjs"

    def test_build_preserves_portable_guidance_and_records_versions_and_hashes(self):
        source_manifest = json.loads((self.current / ".codex-plugin/plugin.json").read_bytes())
        manifest = json.loads((self.package / ".claude-plugin/plugin.json").read_bytes())
        record = json.loads((self.market / "build.json").read_bytes())
        self.assertEqual(source_manifest["version"], record["accordSourceVersion"])
        self.assertEqual(manifest["version"], record["candidateVersion"])
        self.assertTrue(manifest["version"].startswith(record["accordSourceVersion"] + "-"))
        self.assertEqual(record["sources"]["scripts/build_claude_plugin.py"],
                         sha256(Path(builder.__file__).read_bytes()).hexdigest())
        common = (builder.ROOT / builder.LIFECYCLE_SOURCE).read_bytes()
        self.assertEqual(record["sources"][builder.LIFECYCLE_SOURCE], sha256(common).hexdigest())
        self.assertNotIn(builder.CODEX_LIFECYCLE_SOURCE, record["sources"])
        self.assertNotIn(f"{builder.CURRENT}/{builder.LIFECYCLE_SKILL}", record["sources"])
        self.assertEqual(record["marketplaceSha256"],
                         sha256((self.market / ".claude-plugin/marketplace.json").read_bytes()).hexdigest())
        self.assertEqual(
            record["packageFiles"],
            {path.relative_to(self.package).as_posix(): sha256(path.read_bytes()).hexdigest()
             for path in self.package.rglob("*") if path.is_file()},
        )
        for name in builder.FOUNDATION + tuple(
                f"skills/{skill}/SKILL.md" for skill in
                ("coordinate-capabilities", "verify-and-close-outcome")):
            with self.subTest(name=name):
                self.assertEqual((self.current / name).read_bytes(), (self.package / name).read_bytes())
                source = f"{builder.CURRENT}/{name}"
                self.assertEqual(sha256((self.current / name).read_bytes()).hexdigest(), record["sources"][source])
        translation, original = (self.package / name for name in builder.FOUNDATION)
        self.assertIn(f"[Chinese source]({original.name})", translation.read_text(encoding="utf-8"))
        self.assertEqual(translation.parent, original.parent)
        continuity = (self.package / "skills/maintain-task-continuity/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Claude Code’s native history", continuity)
        self.assertIn("A lost connection does not establish whether an operation stopped or succeeded.", continuity)
        self.assertNotIn("read_task_input", continuity)
        self.assertTrue((self.package / "skills/coordinate-capabilities/references/native-capabilities.md").is_file())

    def test_coordination_skill_reads_the_foundation_only_when_missing(self):
        name = f"skills/{builder.ENTRY}/SKILL.md"
        codex = (self.current / name).read_text(encoding="utf-8")
        claude = (self.package / name).read_text(encoding="utf-8")
        first_duty = "\n\nInterpret each input"
        self.assertIn(first_duty, codex)
        self.assertIn(first_duty, claude)
        self.assertEqual(codex.split(first_duty, 1)[1], claude.split(first_duty, 1)[1])
        self.assertIn("meta-guidance already present in this task. When it is missing, read the bundled\n"
                      "[English translation](references/meta-guidance.md) before applying these duties.", claude)
        self.assertNotIn("The native entry supplies the English text", claude)

    def test_codex_lifecycle_source_matches_the_packaged_skill(self):
        output = self.market.parent / "codex lifecycle.md"
        done = subprocess.run(
            [sys.executable, "-B", str(Path(builder.__file__)), "--codex-lifecycle-output", str(output)],
            capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual((self.current / builder.LIFECYCLE_SKILL).read_bytes(), output.read_bytes())

    def test_codex_lifecycle_edit_leaves_claude_package_unchanged(self):
        source_root = self.market.parent / "source copy"
        record = (self.market / "build.json").read_bytes()
        codex_skill = f"{builder.CURRENT}/{builder.LIFECYCLE_SKILL}"
        codex_paths = (builder.CODEX_LIFECYCLE_SOURCE, codex_skill)
        for name in (*json.loads(record)["sources"], *codex_paths):
            data = (builder.ROOT / name).read_bytes()
            if name in codex_paths:
                data += b"\nTemporary Codex lifecycle note.\n"
            copy = source_root / name
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(data)
        with patch.object(builder, "ROOT", source_root):
            codex = builder.build_codex_lifecycle(self.market.parent / "revised codex.md")
            rebuilt = builder.build(self.market.parent / "rebuilt market")
        self.assertEqual((source_root / codex_skill).read_bytes(), codex.read_bytes())
        self.assertEqual(record, (rebuilt.parents[1] / "build.json").read_bytes())
        for name in json.loads(record)["packageFiles"]:
            self.assertEqual((self.package / name).read_bytes(), (rebuilt / name).read_bytes(), name)

    def test_build_rejects_existing_market_without_editing_it(self):
        record = (self.market / "build.json").read_bytes()
        with self.assertRaises(FileExistsError):
            builder.build(self.market)
        self.assertEqual(record, (self.market / "build.json").read_bytes())

    def test_failed_member_write_publishes_neither_manifest_and_allows_retry(self):
        output = self.market.parent / "failed market"
        write_bytes = Path.write_bytes

        def fail_member(path, data):
            if path.name == "NOTICE":
                self.assertFalse((output / ".claude-plugin/marketplace.json").exists())
                self.assertFalse((output / "plugins" / builder.PACKAGE / ".claude-plugin/plugin.json").exists())
                raise OSError("simulated member write failure")
            return write_bytes(path, data)

        with patch.object(Path, "write_bytes", fail_member):
            with self.assertRaisesRegex(OSError, "simulated member write failure"):
                builder.build(output)
        self.assertFalse(output.exists())
        package = builder.build(output)
        self.assertTrue((package / ".claude-plugin/plugin.json").is_file())
        self.assertTrue((output / ".claude-plugin/marketplace.json").is_file())

    def invoke_hook(self, data):
        return subprocess.run(
            ["node", str(self.hook)], input=data, capture_output=True,
            cwd=self.market, timeout=5, check=False,
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for native Hook tests")
    def test_native_entry_events_carry_current_guidance_without_task_data(self):
        hooks = json.loads((self.package / "hooks/hooks.json").read_bytes())["hooks"]
        self.assertEqual({"SessionStart", "SubagentStart"}, set(hooks))
        self.assertEqual("node", hooks["SessionStart"][0]["hooks"][0]["command"].split()[0])
        skill = (self.current / f"skills/{builder.ENTRY}/SKILL.md").read_bytes().decode("utf-8")
        body = skill.split("---", 2)[-1].strip()
        foundation = (self.current / builder.FOUNDATION[0]).read_bytes().decode("utf-8").strip()
        expected_duties = [paragraph for paragraph in body.replace("\r\n", "\n").split("\n\n")
                           if paragraph.startswith(("Interpret each input", "For an authorized outcome",
                                                    "Verify the claimed consequence"))]
        self.assertEqual(len(expected_duties), 3)
        sources = hooks["SessionStart"][0]["matcher"].split("|")
        events = [{"hook_event_name": "SessionStart", "source": source} for source in sources]
        events.append({"hook_event_name": "SubagentStart", "agent_id": "synthetic-id", "agent_type": "Explore"})
        for event in events:
            with self.subTest(event=event):
                data = json.dumps({**event, "prompt": "never-forward-this"}).encode()
                done = self.invoke_hook(data)
                self.assertEqual(0, done.returncode, done.stderr)
                result = json.loads(done.stdout)
                self.assertEqual({"hookSpecificOutput"}, set(result))
                output = result["hookSpecificOutput"]
                self.assertEqual(event["hook_event_name"], output["hookEventName"])
                context = output["additionalContext"]
                self.assertLessEqual(len(context.encode("utf-8")), 1800)
                for paragraph in expected_duties:
                    self.assertIn(paragraph, context)
                self.assertIn(f"{builder.PACKAGE}:{builder.ENTRY}", context)
                self.assertNotIn(foundation, context)
                self.assertNotIn("never-forward-this", context)
                self.assertNotIn("synthetic-id", context)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for native Hook tests")
    def test_unsupported_or_damaged_events_do_not_emit_guidance(self):
        for data in (
            b'{"hook_event_name":"Stop"}',
            b'{"hook_event_name":"SessionStart","source":"unknown"}',
            b'{"hook_event_name":"SubagentStart","agent_type":"Explore"}',
            b'"\xff"',
            b" " * 65537,
        ):
            with self.subTest(data=data[:60]):
                done = self.invoke_hook(data)
                self.assertNotEqual(0, done.returncode)
                self.assertEqual(b"", done.stdout)
