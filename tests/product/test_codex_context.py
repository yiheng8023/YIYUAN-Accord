import datetime as dt
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "runtime" / "codex-context.cjs"
SESSION = "01a09f6e-a885-7201-9dce-0b1a6cf07833"
TURN = "01a09f74-bde2-7773-a981-fdf79825cc9e"
NOW = int(dt.datetime(2026, 9, 14, 12, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)


class CodexContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        if not cls.node:
            raise unittest.SkipTest("node is required")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.sessions = self.root / "sessions"
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        folder = self.sessions / "2026" / "09" / "14"
        folder.mkdir(parents=True)
        self.rollout = folder / f"rollout-2026-09-14T11-59-00-{SESSION}.jsonl"
        self.binding = dict(transcriptPath=str(self.rollout), sessionId=SESSION, turnId=TURN,
                            cwd=str(self.workspace), model="gpt-5.6-sol")

    def tearDown(self):
        self.temp.cleanup()

    def line(self, record, timestamp="2026-09-14T11:59:50Z"):
        return json.dumps({"timestamp": timestamp, **record}, separators=(",", ":"))

    def meta(self, **changes):
        payload = {"id": SESSION, "cwd": str(self.workspace), "cli_version": "0.154.0"}
        payload.update(changes)
        return self.line({"type": "session_meta", "payload": payload}, "2026-09-14T11:59:00Z")

    def context(self, turn=TURN, model="gpt-5.6-sol", cwd=None):
        return self.line({"type": "turn_context", "payload": {
            "turn_id": turn, "cwd": str(cwd or self.workspace), "model": model}})

    def usage(self, last=4000, cumulative=50000, window=10000, timestamp="2026-09-14T11:59:50Z"):
        return self.line({"type": "event_msg", "payload": {"type": "token_count", "info": {
            "last_token_usage": {"total_tokens": last},
            "total_token_usage": {"total_tokens": cumulative},
            "model_context_window": window}}}, timestamp)

    def write(self, *lines, trailing_newline=True):
        content = "\n".join(lines) + ("\n" if trailing_newline else "")
        self.rollout.write_text(content, encoding="utf-8")

    def observe(self, binding=None, now=NOW, max_age=30000, sessions=None):
        script = (
            "const fs=require('node:fs');"
            "const {observeNativeTranscript}=require(process.argv[1]);"
            "const x=JSON.parse(fs.readFileSync(0,'utf8'));"
            "process.stdout.write(JSON.stringify(observeNativeTranscript(x.binding,x.options)));"
        )
        request = {"binding": binding or self.binding, "options": {
            "now": now, "maxAgeMs": max_age, "sessionsRoot": str(sessions or self.sessions)}}
        result = subprocess.run([self.node, "-e", script, str(RUNTIME)], input=json.dumps(request),
                                text=True, encoding="utf-8", capture_output=True, timeout=10,
                                cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_observes_current_native_response_boundary_without_using_cumulative_as_occupancy(self):
        self.write(self.meta(), self.context(), self.usage())
        result = self.observe()
        self.assertEqual(result["state"], "observed")
        self.assertEqual(result["conditions"], {
            "threadId": SESSION, "turnId": TURN, "hostVersion": "0.154.0",
            "model": "gpt-5.6-sol", "contextGeneration": result["conditions"]["contextGeneration"]})
        self.assertEqual(result["lastResponseTokens"], 4000)
        self.assertEqual(result["lastResponseScope"], "last-native-response-boundary")
        self.assertEqual(result["cumulativeTokens"], 50000)
        self.assertEqual(result["cumulativeScope"], "session-cumulative-not-occupancy")
        self.assertEqual(result["windowTokens"], 10000)
        self.assertEqual(result["observedAtMs"], NOW - 10000)
        self.assertEqual(result["validUntilMs"], NOW + 20000)
        self.assertTrue(result["observationId"])
        self.assertIn("#byte=", result["sourceRef"])
        self.assertNotIn(str(self.root), result["sourceRef"])

    def test_rejects_noncanonical_path_and_session_or_workspace_identity_drift(self):
        self.write(self.meta(), self.context(), self.usage())
        outside = self.root / "outside.jsonl"
        outside.write_text(self.meta() + "\n", encoding="utf-8")
        binding = {**self.binding, "transcriptPath": str(outside)}
        self.assertEqual(self.observe(binding)["reason"], "transcript-outside-sessions-root")

        self.write(self.meta(id="01a09f6e-a885-7201-9dce-0b1a6cf07834"), self.context(), self.usage())
        self.assertEqual(self.observe()["reason"], "session-meta-mismatch")

        other = self.root / "other-workspace"
        other.mkdir()
        self.write(self.meta(), self.context(cwd=other), self.usage())
        self.assertEqual(self.observe()["reason"], "turn-cwd-mismatch")

    def test_requires_the_bound_turn_to_be_latest_and_associates_token_count_by_turn_context(self):
        later = "01a09f75-297a-7bf3-aee6-d12add1e3bbd"
        self.write(self.meta(), self.context(), self.usage(), self.context(later),
                   self.usage(last=5000, cumulative=55000))
        self.assertEqual(self.observe()["reason"], "current-turn-not-latest")

        latest = {**self.binding, "turnId": later}
        result = self.observe(latest)
        self.assertEqual(result["state"], "observed")
        self.assertEqual(result["lastResponseTokens"], 5000)

        self.write(self.meta(), self.usage())
        self.assertEqual(self.observe()["reason"], "current-turn-context-not-in-bounded-tail")

    def test_compaction_reroute_and_unknown_usage_need_fresh_matching_evidence(self):
        compact = self.line({"type": "event_msg", "payload": {"type": "context_compacted"}})
        reroute = self.line({"type": "event_msg", "payload": {
            "type": "model_rerouted", "to_model": "gpt-5.6-terra"}})

        self.write(self.meta(), self.context(), self.usage())
        before = self.observe()
        self.write(self.meta(), self.context(), self.usage(), compact)
        self.assertEqual(self.observe()["reason"], "compaction")
        self.write(self.meta(), self.context(), self.usage(), compact,
                   self.usage(last=1000, cumulative=51000))
        after = self.observe()
        self.assertEqual(after["state"], "observed")
        self.assertNotEqual(before["conditions"]["contextGeneration"],
                            after["conditions"]["contextGeneration"])

        self.write(self.meta(), self.context(), self.usage(), reroute,
                   self.usage(last=1000, cumulative=51000))
        self.assertEqual(self.observe()["reason"], "turn-model-mismatch")

        unknown = self.line({"type": "event_msg", "payload": {"type": "token_count", "info": None}})
        self.write(self.meta(), self.context(), self.usage(), unknown)
        self.assertEqual(self.observe()["reason"], "unknown-token-count")

    def test_rejects_expired_future_contradictory_or_unterminated_token_evidence(self):
        self.write(self.meta(), self.context(), self.usage(timestamp="2026-09-14T11:00:00Z"))
        self.assertEqual(self.observe()["reason"], "token-count-expired")
        self.write(self.meta(), self.context(), self.usage(timestamp="2026-09-14T12:00:01Z"))
        self.assertEqual(self.observe()["reason"], "token-count-from-future")
        self.write(self.meta(), self.context(), self.usage(last=6000, cumulative=5000))
        self.assertEqual(self.observe()["reason"], "invalid-token-count")

        self.write(self.meta(), self.context(), self.usage(), '{"unfinished":', trailing_newline=False)
        self.assertEqual(self.observe()["reason"], "unterminated-tail-record")

    def test_generation_is_stable_for_usage_growth_and_changes_with_window_or_file_identity(self):
        self.write(self.meta(), self.context(), self.usage())
        first = self.observe()
        with self.rollout.open("a", encoding="utf-8") as stream:
            stream.write(self.usage(last=4500, cumulative=54500,
                                    timestamp="2026-09-14T11:59:55Z") + "\n")
        grown = self.observe()
        self.assertEqual(first["conditions"]["contextGeneration"],
                         grown["conditions"]["contextGeneration"])
        self.assertNotEqual(first["observationId"], grown["observationId"])

        with self.rollout.open("a", encoding="utf-8") as stream:
            stream.write(self.usage(last=4600, cumulative=59100, window=12000,
                                    timestamp="2026-09-14T11:59:56Z") + "\n")
        resized = self.observe()
        self.assertNotEqual(grown["conditions"]["contextGeneration"],
                            resized["conditions"]["contextGeneration"])

        content = self.rollout.read_bytes()
        replacement = self.rollout.with_suffix(".replacement")
        replacement.write_bytes(content)
        replacement.replace(self.rollout)
        replaced = self.observe()
        self.assertEqual(replaced["state"], "observed")
        self.assertNotEqual(resized["conditions"]["contextGeneration"],
                            replaced["conditions"]["contextGeneration"])

    def test_rejects_path_replacement_after_bounded_read(self):
        self.write(self.meta(), self.context(), self.usage())
        replacement = self.rollout.with_suffix(".replacement")
        replacement.write_bytes(self.rollout.read_bytes())
        old = self.rollout.with_suffix(".old")
        script = (
            "const fs=require('node:fs');"
            "const {observeNativeTranscript}=require(process.argv[1]);"
            "const x=JSON.parse(fs.readFileSync(0,'utf8'));"
            "const close=fs.closeSync;let swapped=false;"
            "fs.closeSync=(fd)=>{close(fd);if(!swapped){swapped=true;"
            "fs.renameSync(x.binding.transcriptPath,x.old);"
            "fs.renameSync(x.replacement,x.binding.transcriptPath);}};"
            "process.stdout.write(JSON.stringify(observeNativeTranscript(x.binding,x.options)));"
        )
        request = {"binding": self.binding, "replacement": str(replacement), "old": str(old),
                   "options": {"now": NOW, "maxAgeMs": 30000,
                               "sessionsRoot": str(self.sessions)}}
        result = subprocess.run([self.node, "-e", script, str(RUNTIME)], input=json.dumps(request),
                                text=True, encoding="utf-8", capture_output=True, timeout=10,
                                cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["reason"], "transcript-path-changed-after-read")

    def test_bounded_tail_does_not_search_older_history_for_a_missing_turn_context(self):
        huge = self.line({"type": "response_item", "payload": {
            "type": "message", "role": "assistant", "content": "x" * (1024 * 1024 + 64)}})
        self.write(self.meta(), self.context(), huge, self.usage())
        result = self.observe()
        self.assertEqual(result["state"], "unknown")
        self.assertEqual(result["reason"], "current-turn-context-not-in-bounded-tail")


if __name__ == "__main__":
    unittest.main()
