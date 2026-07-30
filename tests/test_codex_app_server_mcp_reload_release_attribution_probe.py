from pathlib import Path
import unittest

from scripts.probe_codex_app_server_mcp_reload_release_attribution import (
    PROBE_ID,
    build_thread_start_request,
    build_tool_request,
    classify_reload_window,
    read_executable_version,
    status_reports_callable_sentinel_tools,
    stop_events_in_window,
)


BASELINE = {
    "pid": 123,
    "exists": True,
    "imagePath": "C:/Python/python.exe",
    "creationTime100ns": 456,
    "parentPid": 100,
}


class CodexAppServerMcpReloadReleaseAttributionProbeTests(unittest.TestCase):
    def classify(self, **overrides):
        values = {
            "baseline_instance_id": "instance-a",
            "baseline_pid": 123,
            "baseline_process": dict(BASELINE),
            "process_samples": [dict(BASELINE), dict(BASELINE)],
            "stop_events": [],
            "post_window_call": {
                "succeeded": True,
                "instanceId": "instance-a",
                "pid": 123,
            },
            "app_server_alive_through_window": True,
            "attribution_actions": [
                "config-write-disabled",
                "config/mcpServer/reload",
                "mcpServerStatus/list",
                "read-only-process-and-event-sampling",
            ],
            "config_restored_exactly": True,
        }
        values.update(overrides)
        return classify_reload_window(**values)

    def test_retained_runtime_requires_same_exact_instance(self) -> None:
        result = self.classify()
        self.assertTrue(result["valid"])
        self.assertEqual(
            "loaded-runtime-retained-after-reload",
            result["classification"],
        )
        self.assertTrue(result["loadedRuntimeRetained"])

    def test_release_requires_stop_event_and_absent_final_process(self) -> None:
        result = self.classify(
            process_samples=[
                dict(BASELINE),
                {"pid": 123, "exists": False},
            ],
            stop_events=[{"event": "instance-stop"}],
            post_window_call={
                "succeeded": False,
                "error": {"message": "server unavailable"},
            },
        )
        self.assertTrue(result["valid"])
        self.assertEqual(
            "reload-release-observed-bounded",
            result["classification"],
        )
        self.assertTrue(result["reloadReleaseObserved"])

    def test_pid_absence_without_stop_event_is_invalid(self) -> None:
        result = self.classify(
            process_samples=[
                dict(BASELINE),
                {"pid": 123, "exists": False},
            ],
            post_window_call={"succeeded": False},
        )
        self.assertFalse(result["valid"])
        self.assertIn(
            "reload-window-outcome-ambiguous",
            result["invalidReasons"],
        )

    def test_teardown_or_unsubscribe_contaminates_window(self) -> None:
        actions = [
            "config-write-disabled",
            "config/mcpServer/reload",
            "thread/unsubscribe",
            "read-only-process-and-event-sampling",
        ]
        result = self.classify(attribution_actions=actions)
        self.assertEqual("measurement-invalid", result["classification"])
        self.assertIn(
            "forbidden-or-missing-attribution-window-action",
            result["invalidReasons"],
        )

    def test_config_restore_is_part_of_validity(self) -> None:
        result = self.classify(config_restored_exactly=False)
        self.assertEqual("measurement-invalid", result["classification"])
        self.assertIn("config-not-restored-exactly", result["invalidReasons"])

    def test_stop_event_window_uses_exact_instance_and_time(self) -> None:
        from datetime import datetime, timezone

        start = datetime(2026, 7, 27, 1, 0, tzinfo=timezone.utc)
        end = datetime(2026, 7, 27, 1, 1, tzinfo=timezone.utc)
        events = [
            {
                "event": "instance-stop",
                "instanceId": "instance-a",
                "timestamp": "2026-07-27T01:00:30+00:00",
            },
            {
                "event": "instance-stop",
                "instanceId": "instance-b",
                "timestamp": "2026-07-27T01:00:30+00:00",
            },
            {
                "event": "instance-stop",
                "instanceId": "instance-a",
                "timestamp": "2026-07-27T01:02:00+00:00",
            },
        ]
        self.assertEqual(
            [events[0]],
            stop_events_in_window(events, "instance-a", start, end),
        )

    def test_requests_bind_the_new_probe_identity_and_start_no_turn(self) -> None:
        start = build_thread_start_request(1, Path("."), "fixture")
        call = build_tool_request(2, "thread-a", "phase-a")
        self.assertEqual("thread/start", start["method"])
        self.assertIn(PROBE_ID, start["params"]["name"])
        self.assertEqual("mcpServer/tool/call", call["method"])
        self.assertEqual(PROBE_ID, call["params"]["arguments"]["probe"])

    def test_status_with_empty_tools_is_not_callable_surface(self) -> None:
        status = {
            "data": [
                {
                    "name": "lifecycle_sentinel",
                    "tools": {},
                }
            ]
        }
        self.assertFalse(status_reports_callable_sentinel_tools(status))
        status["data"][0]["tools"] = {"identity": {}}
        self.assertTrue(status_reports_callable_sentinel_tools(status))

    def test_version_reader_binds_an_explicit_executable(self) -> None:
        import sys

        version = read_executable_version(sys.executable)
        self.assertIn("Python", version)

    def test_source_contains_no_model_turn_or_pid_signal_cleanup(self) -> None:
        source = (
            Path(__file__).resolve().parent.parent
            / "scripts"
            / "probe_codex_app_server_mcp_reload_release_attribution.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"turn/start"', source)
        self.assertNotIn("os.kill(", source)
        self.assertNotIn("signal.SIG", source)
        self.assertIn("cleanupMarkerExitIsNaturalReleaseEvidence", source)


if __name__ == "__main__":
    unittest.main()
