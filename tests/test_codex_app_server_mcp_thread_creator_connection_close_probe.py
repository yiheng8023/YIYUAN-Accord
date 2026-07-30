from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
import tempfile
import unittest

from scripts.probe_codex_app_server_mcp_thread_creator_connection_close import (
    ARM_CONTROL,
    ARM_CREATOR_CLOSE,
    PROBE_ID,
    build_identity_tool_params,
    classify_arm,
    classify_pair,
    observe_rollout_materialization,
    write_artifacts,
)


def identity(pid: int, *, exists: bool = True) -> dict[str, object]:
    if not exists:
        return {
            "exists": False,
            "pid": None,
            "creationTime100ns": None,
            "imagePath": None,
            "parentPid": None,
        }
    return {
        "exists": True,
        "pid": pid,
        "creationTime100ns": pid * 100,
        "imagePath": f"C:/probe/process-{pid}.exe",
        "parentPid": max(1, pid - 1),
    }


def sample(
    *,
    sentinel: dict[str, object],
    creator: dict[str, object],
    observer: dict[str, object] | None = None,
    app_server: dict[str, object] | None = None,
    skew: float = 1.0,
) -> dict[str, object]:
    return {
        "sampleSkewMilliseconds": skew,
        "sentinel": sentinel,
        "creatorBridge": creator,
        "observerBridge": observer or identity(300),
        "appServer": app_server or identity(100),
    }


def arm_kwargs(
    arm: str,
    *,
    state: str = "retained",
) -> dict[str, object]:
    sentinel = identity(200)
    creator = identity(301)
    sentinel_samples = [sentinel for _ in range(3)]
    stop_events: list[dict[str, object]] = []
    post_window_call: dict[str, object] = {
        "succeeded": True,
        "pid": 200,
        "instanceId": "instance-a",
    }
    if state == "released":
        sentinel_samples = [
            sentinel,
            identity(200, exists=False),
            identity(200, exists=False),
        ]
        stop_events = [
            {
                "event": "instance-stop",
                "pid": 200,
                "instanceId": "instance-a",
            }
        ]
        post_window_call = {"succeeded": False}
    creator_samples = [creator for _ in range(3)]
    creator_close = None
    transport_actions: list[dict[str, object]] = []
    if arm == ARM_CREATOR_CLOSE:
        creator_samples = [
            creator,
            identity(301, exists=False),
            identity(301, exists=False),
        ]
        creator_close = {
            "returnCode": 0,
            "killSent": False,
            "stderrLines": ["BRIDGE_CLOSED code=1000 clean=true"],
            "processIdentity": creator,
        }
        transport_actions = [
            {
                "action": "creator-connection-close",
                "processIdentity": creator,
                "hostRpc": False,
            }
        ]
    return {
        "arm": arm,
        "app_server_process": identity(100),
        "creator_bridge_process": creator,
        "observer_bridge_process": identity(300),
        "thread_id_a": "thread-a",
        "thread_id_b": "thread-a",
        "creator_baseline_call": {
            "pid": 200,
            "instanceId": "instance-a",
        },
        "observer_baseline_call": {
            "pid": 200,
            "instanceId": "instance-a",
        },
        "sentinel_process": sentinel,
        "start_events": [
            {
                "event": "instance-start",
                "pid": 200,
                "instanceId": "instance-a",
            }
        ],
        "process_samples": [
            sample(
                sentinel=sentinel_sample,
                creator=creator_sample,
            )
            for sentinel_sample, creator_sample in zip(
                sentinel_samples, creator_samples, strict=True
            )
        ],
        "stop_events": stop_events,
        "post_window_call": post_window_call,
        "in_window_host_methods": [],
        "transport_actions": transport_actions,
        "creator_close": creator_close,
        "action_skew_milliseconds": 1.0,
        "observation_seconds": 1.0,
        "sample_interval_seconds": 0.5,
        "model_turn_count": 0,
        "turn_started_notification_count": 0,
        "configuration_unchanged": True,
        "auth_state_produced": False,
        "evidence_sealed_before_post_window_call": True,
    }


class ThreadCreatorConnectionCloseProbeTests(unittest.TestCase):
    def test_zero_turn_rollout_absence_is_recorded_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-materialized.jsonl"
            observation = observe_rollout_materialization(path)
        self.assertEqual(
            observation,
            {
                "path": path.resolve().as_posix(),
                "observed": False,
                "bytes": None,
            },
        )

    def classify(
        self,
        arm: str,
        *,
        state: str = "retained",
        **updates: object,
    ) -> dict[str, object]:
        values = arm_kwargs(arm, state=state)
        values.update(updates)
        return classify_arm(**values)

    def test_control_retention_is_measurement_valid(self) -> None:
        result = self.classify(ARM_CONTROL)
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "connected-control-runtime-retained-five-seconds",
        )

    def test_treatment_release_requires_bound_clean_close(self) -> None:
        result = self.classify(
            ARM_CREATOR_CLOSE,
            state="released",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["classification"],
            "creator-connection-close-release-observed-bounded",
        )
        self.assertTrue(result["releaseObserved"])
        self.assertFalse(result["creatorConnectionCloseIsTaskEnd"])
        self.assertFalse(result["publicLeaseOrReferenceCountObserved"])

    def test_treatment_retention_falsifies_only_immediate_release(self) -> None:
        control = self.classify(ARM_CONTROL)
        treatment = self.classify(ARM_CREATOR_CLOSE)
        pair = classify_pair(control, treatment)
        self.assertTrue(pair["valid"])
        self.assertTrue(pair["conclusive"])
        self.assertEqual(
            pair["classification"],
            "creator-connection-close-immediate-release-falsified-bounded",
        )
        self.assertTrue(
            pair["creatorConnectionCloseImmediateReleaseFalsified"]
        )
        self.assertFalse(
            pair["creatorConnectionCloseReleaseAssociated"]
        )

    def test_release_association_requires_retained_control(self) -> None:
        control = self.classify(ARM_CONTROL)
        treatment = self.classify(
            ARM_CREATOR_CLOSE,
            state="released",
        )
        pair = classify_pair(control, treatment)
        self.assertTrue(pair["valid"])
        self.assertTrue(pair["conclusive"])
        self.assertEqual(
            pair["classification"],
            "creator-connection-close-release-associated-bounded",
        )

    def test_both_arms_stopping_is_valid_but_inconclusive(self) -> None:
        control = self.classify(ARM_CONTROL, state="released")
        treatment = self.classify(
            ARM_CREATOR_CLOSE,
            state="released",
        )
        pair = classify_pair(control, treatment)
        self.assertTrue(pair["valid"])
        self.assertFalse(pair["conclusive"])
        self.assertEqual(
            pair["classification"], "inconclusive-valid-bounded"
        )

    def test_forbidden_window_rpc_fails_closed(self) -> None:
        result = self.classify(
            ARM_CREATOR_CLOSE,
            in_window_host_methods=["mcpServer/tool/call"],
        )
        self.assertFalse(result["valid"])
        self.assertIn(
            "in-window-host-rpc-observed", result["invalidReasons"]
        )

    def test_unbound_close_fails_closed(self) -> None:
        values = arm_kwargs(ARM_CREATOR_CLOSE)
        values["creator_close"] = {
            "returnCode": 0,
            "killSent": False,
            "stderrLines": [],
            "processIdentity": values["creator_bridge_process"],
        }
        result = classify_arm(**values)
        self.assertFalse(result["valid"])
        self.assertIn(
            "creator-close-not-exactly-bound", result["invalidReasons"]
        )

    def test_unclean_close_fails_closed(self) -> None:
        values = arm_kwargs(ARM_CREATOR_CLOSE)
        values["creator_close"]["stderrLines"] = [
            "BRIDGE_CLOSED code=1000 clean=false"
        ]
        result = classify_arm(**values)
        self.assertFalse(result["valid"])
        self.assertIn(
            "creator-close-not-exactly-bound", result["invalidReasons"]
        )

    def test_observer_must_remain_alive(self) -> None:
        values = arm_kwargs(ARM_CREATOR_CLOSE)
        values["process_samples"][-1]["observerBridge"] = identity(
            300, exists=False
        )
        result = classify_arm(**values)
        self.assertFalse(result["valid"])
        self.assertIn(
            "observer-bridge-not-alive-through-window",
            result["invalidReasons"],
        )

    def test_evidence_must_be_sealed_before_post_window_call(self) -> None:
        result = self.classify(
            ARM_CREATOR_CLOSE,
            evidence_sealed_before_post_window_call=False,
        )
        self.assertFalse(result["valid"])
        self.assertIn(
            "post-window-call-precedes-evidence-seal",
            result["invalidReasons"],
        )

    def test_fixture_pre_registers_pair_classification(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "mcp-thread-creator-connection-close-attribution-2026-07-27.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        for case in fixture["cases"]:
            arms = {}
            for label in ("control", "treatment"):
                state = case[label]
                arm = (
                    ARM_CONTROL
                    if label == "control"
                    else ARM_CREATOR_CLOSE
                )
                if state == "invalid":
                    arms[label] = {
                        "classification": "invalid",
                        "valid": False,
                    }
                else:
                    arms[label] = self.classify(arm, state=state)
            actual = classify_pair(arms["control"], arms["treatment"])
            for key, expected in case["expected"].items():
                self.assertEqual(
                    actual[key],
                    expected,
                    msg=f"{case['id']} {key}",
                )

    def test_tool_request_self_binds_probe_owner_and_phase(self) -> None:
        params = build_identity_tool_params(
            "thread-a", "observer-b", "post-window"
        )
        self.assertEqual(params["threadId"], "thread-a")
        self.assertEqual(params["arguments"]["probe"], PROBE_ID)
        self.assertEqual(params["arguments"]["owner"], "observer-b")
        self.assertEqual(params["arguments"]["phase"], "post-window")

    def test_protocol_keeps_live_execution_out_of_scope(self) -> None:
        protocol_path = (
            Path(__file__).resolve().parents[1]
            / "registry"
            / "mcp-thread-creator-connection-close-attribution-protocol-2026-07-27.json"
        )
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        self.assertEqual(
            protocol["id"],
            "MCP-THREAD-CREATOR-CONNECTION-CLOSE-ATTRIBUTION-01",
        )
        boundary = protocol["executionBoundary"]
        self.assertFalse(boundary["formalLivePairedRunsExecuted"])
        self.assertFalse(boundary["modelOrAccountUseAuthorized"])
        self.assertFalse(boundary["externalNetworkUseAuthorized"])
        self.assertFalse(boundary["loopbackTransportExecutionAuthorized"])
        self.assertFalse(boundary["globalConfigurationMutationAuthorized"])
        self.assertFalse(boundary["installationAuthorized"])

    def test_probe_has_no_model_turn_request_call(self) -> None:
        import scripts.probe_codex_app_server_mcp_thread_creator_connection_close as probe

        tree = ast.parse(inspect.getsource(probe))
        requested_methods: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"request", "send_request"}:
                continue
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                if isinstance(node.args[1].value, str):
                    requested_methods.append(node.args[1].value)
        self.assertNotIn("turn/start", requested_methods)
        self.assertNotIn("thread/unsubscribe", requested_methods)
        self.assertIn("thread/start", requested_methods)
        self.assertIn("mcpServer/tool/call", requested_methods)

    def test_artifact_writer_emits_declared_files(self) -> None:
        arm_report = {
            "processSamples": [{"index": 0}],
            "eventsAtWindowEnd": [{"event": "instance-start"}],
            "transportActions": [],
            "rpcLedgerAtSeal": {
                "creator-a": [],
                "observer-b": [],
            },
            "configuration": {"sha256": "ABC"},
            "appServerStderr": [],
            "connections": {
                "creator-a": {
                    "rpcLedger": [],
                    "stderrLines": [
                        "BRIDGE_READY pid=1",
                        "BRIDGE_CLOSED code=1000 clean=true",
                    ],
                },
                "observer-b": {
                    "rpcLedger": [],
                    "stderrLines": ["BRIDGE_READY pid=2"],
                },
            },
        }
        report = {
            "probeId": PROBE_ID,
            "arms": {
                ARM_CONTROL: arm_report,
                ARM_CREATOR_CLOSE: arm_report,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_artifacts(root, report)
            self.assertTrue((root / "pair-report.json").is_file())
            for arm in (ARM_CONTROL, ARM_CREATOR_CLOSE):
                arm_dir = root / arm
                for name in (
                    "report.json",
                    "process-samples.jsonl",
                    "sentinel-events.jsonl",
                    "rpc-ledger.json",
                    "transport-actions.json",
                    "bridge-events.jsonl",
                    "stderr.log",
                    "config-manifest.json",
                ):
                    self.assertTrue(
                        (arm_dir / name).is_file(),
                        msg=f"{arm}/{name}",
                    )


if __name__ == "__main__":
    unittest.main()
