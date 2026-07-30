import inspect
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.probe_codex_app_server_mcp_thread_unsubscribe_release_attribution import (
    ARM_CONTROL,
    ARM_UNSUBSCRIBE,
    PROBE_ID,
    build_minimal_child_environment,
    build_tool_request,
    classify_arm,
    classify_pair,
)


def process_identity(*, exists: bool = True) -> dict[str, object]:
    return {
        "exists": exists,
        "pid": 1234 if exists else None,
        "creationTime100ns": 5678 if exists else None,
        "imagePath": "C:/Python/python.exe" if exists else None,
        "parentPid": 2222 if exists else None,
        "workingSetBytes": 100 if exists else None,
        "privateUsageBytes": 80 if exists else None,
        "kernelTime100ns": 1 if exists else None,
        "userTime100ns": 2 if exists else None,
    }


def sample(identity: dict[str, object]) -> dict[str, object]:
    return {
        "sampleSkewMilliseconds": 1.0,
        "sentinel": identity,
        "appServer": {"exists": True},
    }


def retained_arm(arm: str) -> dict[str, object]:
    identity = process_identity()
    methods = ["thread/unsubscribe"] if arm == ARM_UNSUBSCRIBE else []
    return classify_arm(
        arm=arm,
        baseline_instance_id="instance-a",
        baseline_pid=1234,
        baseline_process=identity,
        process_samples=[sample(identity) for _ in range(3)],
        stop_events=[],
        post_window_call={
            "succeeded": True,
            "instanceId": "instance-a",
            "pid": 1234,
        },
        in_window_host_methods=methods,
        unsubscribe_status=(
            "unsubscribed" if arm == ARM_UNSUBSCRIBE else None
        ),
        action_skew_milliseconds=1.0,
        observation_seconds=1.0,
        sample_interval_seconds=0.5,
        model_turn_count=0,
    )


class ThreadUnsubscribeReleaseAttributionProbeTests(unittest.TestCase):
    def test_unsubscribe_retention_is_classified_bounded(self) -> None:
        result = retained_arm(ARM_UNSUBSCRIBE)
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "unsubscribe-runtime-retained-five-seconds",
        )
        self.assertTrue(result["runtimeRetained"])
        self.assertFalse(result["releaseObserved"])

    def test_subscribed_control_retention_is_classified(self) -> None:
        result = retained_arm(ARM_CONTROL)
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "subscribed-control-retained-five-seconds",
        )

    def test_release_requires_stop_event_and_exact_process_absence(self) -> None:
        baseline = process_identity()
        result = classify_arm(
            arm=ARM_UNSUBSCRIBE,
            baseline_instance_id="instance-a",
            baseline_pid=1234,
            baseline_process=baseline,
            process_samples=[
                sample(baseline),
                sample(process_identity(exists=False)),
                sample(process_identity(exists=False)),
            ],
            stop_events=[{"event": "instance-stop", "instanceId": "instance-a"}],
            post_window_call={
                "succeeded": True,
                "instanceId": "instance-b",
                "pid": 4567,
            },
            in_window_host_methods=["thread/unsubscribe"],
            unsubscribe_status="unsubscribed",
            action_skew_milliseconds=1.0,
            observation_seconds=1.0,
            sample_interval_seconds=0.5,
            model_turn_count=0,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "unsubscribe-release-observed-bounded",
        )
        self.assertTrue(result["releaseObserved"])

    def test_absence_without_stop_event_is_ambiguous(self) -> None:
        baseline = process_identity()
        result = classify_arm(
            arm=ARM_UNSUBSCRIBE,
            baseline_instance_id="instance-a",
            baseline_pid=1234,
            baseline_process=baseline,
            process_samples=[
                sample(baseline),
                sample(process_identity(exists=False)),
                sample(process_identity(exists=False)),
            ],
            stop_events=[],
            post_window_call={"succeeded": False},
            in_window_host_methods=["thread/unsubscribe"],
            unsubscribe_status="unsubscribed",
            action_skew_milliseconds=1.0,
            observation_seconds=1.0,
            sample_interval_seconds=0.5,
            model_turn_count=0,
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["classification"], "measurement-ambiguous")

    def test_forbidden_window_method_fails_closed(self) -> None:
        baseline = process_identity()
        result = classify_arm(
            arm=ARM_UNSUBSCRIBE,
            baseline_instance_id="instance-a",
            baseline_pid=1234,
            baseline_process=baseline,
            process_samples=[sample(baseline) for _ in range(3)],
            stop_events=[],
            post_window_call={
                "succeeded": True,
                "instanceId": "instance-a",
                "pid": 1234,
            },
            in_window_host_methods=[
                "thread/unsubscribe",
                "mcpServerStatus/list",
            ],
            unsubscribe_status="unsubscribed",
            action_skew_milliseconds=1.0,
            observation_seconds=1.0,
            sample_interval_seconds=0.5,
            model_turn_count=0,
        )
        self.assertFalse(result["valid"])
        self.assertIn(
            "forbidden-or-missing-in-window-host-method",
            result["invalidReasons"],
        )

    def test_pair_retention_falsifies_immediate_release_only(self) -> None:
        result = classify_pair(
            retained_arm(ARM_CONTROL),
            retained_arm(ARM_UNSUBSCRIBE),
        )
        self.assertTrue(result["valid"])
        self.assertTrue(result["unsubscribeImmediateReleaseFalsified"])
        self.assertFalse(result["unsubscribeReleaseAssociated"])

    def test_control_failure_makes_pair_inconclusive(self) -> None:
        control = retained_arm(ARM_CONTROL)
        control["valid"] = False
        result = classify_pair(control, retained_arm(ARM_UNSUBSCRIBE))
        self.assertFalse(result["valid"])
        self.assertEqual(result["classification"], "pair-inconclusive")

    def test_tool_request_self_binds_probe_arm_and_phase(self) -> None:
        request = build_tool_request(
            4, "thread-a", ARM_CONTROL, "post-window"
        )
        arguments = request["params"]["arguments"]
        self.assertEqual(arguments["probe"], PROBE_ID)
        self.assertEqual(arguments["arm"], ARM_CONTROL)
        self.assertEqual(arguments["phase"], "post-window")

    def test_minimal_environment_omits_account_and_proxy_keys(self) -> None:
        with patch.dict(
            os.environ,
            {
                "SYSTEMROOT": "C:/Windows",
                "PATH": "C:/Windows/System32",
                "OPENAI_API_KEY": "secret",
                "CHATGPT_AUTH_TOKEN": "secret",
                "HTTPS_PROXY": "http://proxy.invalid",
            },
            clear=True,
        ):
            environment, names = build_minimal_child_environment(
                Path("C:/tmp/isolated-codex-home")
            )
        self.assertIn("SYSTEMROOT", environment)
        self.assertIn("PATH", environment)
        self.assertIn("CODEX_HOME", environment)
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn("CHATGPT_AUTH_TOKEN", environment)
        self.assertNotIn("HTTPS_PROXY", environment)
        self.assertEqual(names, sorted(environment))

    def test_probe_source_never_starts_model_turn(self) -> None:
        import scripts.probe_codex_app_server_mcp_thread_unsubscribe_release_attribution as probe

        source = inspect.getsource(probe)
        self.assertNotIn('"method": "turn/start"', source)
        self.assertIn('"thread/unsubscribe"', source)
        self.assertNotIn("os.kill(", source)


if __name__ == "__main__":
    unittest.main()
