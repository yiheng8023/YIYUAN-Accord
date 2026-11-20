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
        source = (builder.ROOT / builder.ENTRY_SOURCE).read_text(encoding="utf-8")
        intro = source.split("<!-- accord:host-entry -->\n", 1)[1].split("\n<!-- /accord -->", 1)[0]
        self.assertEqual(1, codex.count(intro))
        self.assertEqual(codex.replace(intro, builder.CLAUDE_ENTRY), claude)
        self.assertNotIn("<!-- accord:", claude)
        self.assertIn("meta-guidance already present in this task. When it is missing, read the bundled\n"
                      "[English translation](references/meta-guidance.md) before applying these duties.", claude)

    def test_codex_coordination_projection_matches_the_packaged_skill(self):
        output = self.market.parent / "codex coordination.md"
        done = subprocess.run(
            [sys.executable, "-B", str(Path(builder.__file__)), "--codex-entry-output", str(output)],
            capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual((self.current / f"skills/{builder.ENTRY}/SKILL.md").read_bytes(), output.read_bytes())

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for native Hook tests")
    def test_reordered_source_metadata_still_loads_in_the_codex_entry_hook(self):
        package = shutil.copytree(self.current, self.market.parent / "codex entry")
        source = (builder.ROOT / builder.ENTRY_SOURCE).read_bytes().splitlines(keepends=True)
        source[1], source[2] = source[2], source[1]
        marker = b"<!-- accord:scope -->\n"
        edited = b"".join(source).replace(marker, marker + b"Revised scope. ", 1)
        skill, _ = builder.compose_entry(edited)
        (package / f"skills/{builder.ENTRY}/SKILL.md").write_bytes(skill)
        done = self.invoke_hook(b'{"hook_event_name":"SessionStart","source":"startup"}', package)
        self.assertEqual(0, done.returncode, done.stderr)
        context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Revised scope. ", context)
        self.assertNotIn("<!-- accord:", context)

    def test_codex_lifecycle_source_matches_the_packaged_skill(self):
        output = self.market.parent / "codex lifecycle.md"
        done = subprocess.run(
            [sys.executable, "-B", str(Path(builder.__file__)), "--codex-lifecycle-output", str(output)],
            capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual((self.current / builder.LIFECYCLE_SKILL).read_bytes(), output.read_bytes())

    def test_codex_lifecycle_edit_leaves_claude_package_unchanged(self):
        source_root = self.copy_build_sources()
        record = (self.market / "build.json").read_bytes()
        codex_skill = f"{builder.CURRENT}/{builder.LIFECYCLE_SKILL}"
        codex_paths = (builder.CODEX_LIFECYCLE_SOURCE, codex_skill)
        for name in codex_paths:
            data = (builder.ROOT / name).read_bytes() + b"\nTemporary Codex lifecycle note.\n"
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

    def test_failed_publication_removes_partial_output_and_allows_retry(self):
        rename = Path.rename
        for final_name in ("build.json", "plugins", ".claude-plugin"):
            with self.subTest(final_name=final_name):
                output = self.market.parent / f"interrupted publication {final_name}"

                def fail_move(source, target):
                    if Path(target) == output / final_name:
                        raise OSError("simulated publication failure")
                    return rename(source, target)

                with patch.object(Path, "rename", fail_move):
                    with self.assertRaisesRegex(OSError, "simulated publication failure"):
                        builder.build(output)
                self.assertFalse(output.exists())
                package = builder.build(output)
                self.assertTrue((package / ".claude-plugin/plugin.json").is_file())
                self.assertTrue((output / ".claude-plugin/marketplace.json").is_file())

    def test_failed_publication_preserves_a_changed_output_entry(self):
        output = self.market.parent / "publication with an external addition"
        unrelated = output / "plugins" / "other-project.txt"
        rename = Path.rename

        def fail_move(source, target):
            if Path(target) == output / ".claude-plugin":
                unrelated.write_bytes(b"independent contents")
                raise OSError("simulated publication failure")
            return rename(source, target)

        with patch.object(Path, "rename", fail_move):
            with self.assertRaisesRegex(OSError, "output remaining"):
                builder.build(output)
        self.assertEqual(unrelated.read_bytes(), b"independent contents")
        self.assertFalse((output / ".claude-plugin/marketplace.json").exists())

    def invoke_hook(self, data, package=None):
        return subprocess.run(
            ["node", str((package or self.package) / "runtime/accord-hook.cjs")], input=data, capture_output=True,
            cwd=self.market, timeout=5, check=False,
        )

    def copy_build_sources(self):
        root = self.market.parent / "source copy"
        for name in json.loads((self.market / "build.json").read_bytes())["sources"]:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(builder.ROOT / name, target)
        return root

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for native Hook tests")
    def test_edits_follow_named_duties_through_build_and_hook(self):
        root = self.copy_build_sources()
        source = root / builder.ENTRY_SOURCE
        text = source.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        lines[1], lines[2] = lines[2], lines[1]
        text = "".join(lines)
        revised = {"scope": "Apply the current scope.", "action": "Use the authorized means.",
                   "verification": "Check\nthe result.\n\n复核原件。"}
        for role, value in revised.items():
            marker = f"<!-- accord:{role} -->\n"
            original = text.split(marker, 1)[1].split("\n<!-- /accord -->", 1)[0]
            text = text.replace(marker + original, marker + value, 1)
        outside = "Verify the claimed consequence in an unrelated example."
        source.write_text(text + "\n" + outside + "\n", encoding="utf-8")
        with patch.object(builder, "ROOT", root):
            package = builder.build(self.market.parent / "reworded")
        skill = (package / f"skills/{builder.ENTRY}/SKILL.md").read_text(encoding="utf-8")
        self.assertIn(outside, skill)
        done = self.invoke_hook(b'{"hook_event_name":"SessionStart","source":"startup"}', package)
        self.assertEqual(0, done.returncode, done.stderr)
        context = json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
        for value in revised.values():
            self.assertIn(value, context)
            self.assertIn(value, skill)
        self.assertNotIn(outside, context)
        self.assertNotIn("<!-- accord:", context)

    def test_invalid_source_or_oversized_event_fails_before_publication(self):
        root = self.copy_build_sources()
        source = root / builder.ENTRY_SOURCE
        original = source.read_text(encoding="utf-8")
        marker = "<!-- accord:scope -->\n"
        scope = original.split(marker, 1)[1].split("\n<!-- /accord -->", 1)[0]
        changes = {
            "missing": original.replace(marker, ""),
            "duplicate": original.replace("<!-- accord:action -->", "<!-- accord:scope -->"),
            "empty": original.replace(marker + scope, marker),
            "unknown": original.replace(marker, "<!-- accord:unspecified -->\n"),
            "over budget": original.replace(marker, marker + "界" * 601),
            "oversized full Skill": original + "x" * 10001,
            "incorrect identity": original.replace("name: " + builder.ENTRY, "name: different-skill", 1),
            "extra field": original.replace("name: ", "unhandled-setting: enabled\nname: ", 1),
        }
        output = self.market.parent / "retryable build"
        with patch.object(builder, "ROOT", root):
            for case, changed in changes.items():
                with self.subTest(case=case):
                    source.write_text(changed, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        builder.build(output)
                    self.assertFalse(output.exists())
            source.write_text(original, encoding="utf-8")
            self.assertTrue(builder.build(output).is_dir())

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for native Hook tests")
    def test_a_longer_event_can_exceed_the_budget_while_startup_still_fits(self):
        startup = self.invoke_hook(b'{"hook_event_name":"SessionStart","source":"startup"}')
        self.assertEqual(0, startup.returncode, startup.stderr)
        context = json.loads(startup.stdout)["hookSpecificOutput"]["additionalContext"]
        padding = "x" * (1800 - len(context.encode("utf-8")))
        source = (builder.ROOT / builder.ENTRY_SOURCE).read_bytes()
        marker = b"<!-- accord:action -->\n"
        revised = source.replace(marker, marker + padding.encode("ascii"), 1)
        skill, sections = builder.compose_entry(revised, builder.CLAUDE_ENTRY)
        with self.assertRaisesRegex(ValueError, "1800-byte context budget"):
            builder.compile_entry_hook((builder.ROOT / builder.HOOK_SOURCE).read_bytes(), skill, sections)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for native Hook tests")
    def test_hook_recognizes_line_endings_and_rejects_a_damaged_or_missing_skill(self):
        skill = self.package / f"skills/{builder.ENTRY}/SKILL.md"
        original = skill.read_bytes()
        event = b'{"hook_event_name":"SessionStart","source":"startup"}'
        expected = self.invoke_hook(event)
        self.assertEqual(0, expected.returncode, expected.stderr)
        skill.write_bytes(original.replace(b"\n", b"\r\n"))
        converted = self.invoke_hook(event)
        self.assertEqual(0, converted.returncode, converted.stderr)
        self.assertEqual(expected.stdout, converted.stdout)
        for data in (original.replace(b"Claude Code", b"Other Code", 1), b"\xff", None):
            with self.subTest(damage="missing" if data is None else len(data)):
                if data is None:
                    skill.unlink()
                else:
                    skill.write_bytes(data)
                done = self.invoke_hook(event)
                self.assertNotEqual(0, done.returncode)
                self.assertEqual(b"", done.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required for native Hook tests")
    def test_native_entry_events_carry_current_guidance_without_task_data(self):
        hooks = json.loads((self.package / "hooks/hooks.json").read_bytes())["hooks"]
        self.assertEqual({"SessionStart", "SubagentStart"}, set(hooks))
        self.assertEqual("node", hooks["SessionStart"][0]["hooks"][0]["command"].split()[0])
        source = (builder.ROOT / builder.ENTRY_SOURCE).read_text(encoding="utf-8")
        foundation = (self.current / builder.FOUNDATION[0]).read_bytes().decode("utf-8").strip()
        expected_duties = [source.split(f"<!-- accord:{role} -->\n", 1)[1].split("\n<!-- /accord -->", 1)[0]
                           for role in ("scope", "action", "verification")]
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
            b'{"hook_event_name":"SessionStart","source":"__proto__"}',
            b'{"hook_event_name":"SessionStart","source":["startup"]}',
            b'{"hook_event_name":"SubagentStart","agent_type":"Explore"}',
            b'"\xff"',
            b" " * 65537,
        ):
            with self.subTest(data=data[:60]):
                done = self.invoke_hook(data)
                self.assertNotEqual(0, done.returncode)
                self.assertEqual(b"", done.stdout)
