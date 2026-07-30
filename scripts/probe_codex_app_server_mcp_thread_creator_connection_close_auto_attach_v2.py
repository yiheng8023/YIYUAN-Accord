#!/usr/bin/env python3
"""Offline-injectable v2 creator-close probe sequence.

This module contains no app-server launcher or network transport.  It accepts
already-constructed request/notification transports so deterministic tests can
prove the auto-attach RPC order before any separate live authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Protocol


PROBE_ID = "codex-app-server-mcp-thread-creator-connection-close-auto-attach-v2"
ARM_CONTROL = "connected-control"
ARM_CREATOR_CLOSE = "creator-connection-close"
ARM_NAMES = (ARM_CONTROL, ARM_CREATOR_CLOSE)


class InjectedTransport(Protocol):
    """Minimal non-owning transport interface used by the offline runner."""

    def request(
        self,
        request_id: int,
        method: str,
        params: Any,
        *,
        phase: str,
        thread_id: str | None = None,
    ) -> dict[str, Any]: ...

    def notify(
        self,
        method: str,
        params: Any,
        *,
        phase: str,
    ) -> None: ...

    def close(self) -> None: ...


class OfflineProbeFailure(RuntimeError):
    """Fail-closed error that retains the complete offline trace."""

    def __init__(self, message: str, trace: dict[str, Any]) -> None:
        super().__init__(message)
        self.trace = trace


def canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def observe_rollout_materialization(path: Path) -> dict[str, Any]:
    """Record rollout presence once; absence is not a setup gate."""
    resolved = path.resolve()
    observed = resolved.is_file() and resolved.stat().st_size > 0
    return {
        "path": resolved.as_posix(),
        "observed": observed,
        "bytes": resolved.stat().st_size if observed else None,
        "role": "diagnostic-only",
    }


def build_thread_start_params(workspace: Path) -> dict[str, Any]:
    return {
        "cwd": workspace.resolve().as_posix(),
        "ephemeral": False,
        "approvalPolicy": "never",
        "sandbox": "read-only",
        "name": PROBE_ID,
    }


def build_identity_tool_params(
    thread_id: str,
    owner: str,
    phase: str,
) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "server": "lifecycle_sentinel",
        "tool": "identity",
        "arguments": {
            "probe": PROBE_ID,
            "owner": owner,
            "phase": phase,
        },
    }


def _initialize(
    transport: InjectedTransport,
    *,
    owner: str,
    events: list[str],
) -> None:
    events.append(f"{owner}:initialize")
    response = transport.request(
        0,
        "initialize",
        {
            "clientInfo": {
                "name": PROBE_ID,
                "title": "MCP Thread Creator Close Auto-Attach V2",
                "version": "2.0.0",
            }
        },
        phase=f"{owner}-initialize",
    )
    if not isinstance(response.get("result"), dict):
        raise RuntimeError(f"{owner} initialize result is not an object")
    events.append(f"{owner}:initialized")
    transport.notify(
        "initialized",
        None,
        phase=f"{owner}-initialized",
    )


def _extract_thread(response: dict[str, Any]) -> tuple[str, Path]:
    result = response.get("result")
    thread = result.get("thread") if isinstance(result, dict) else None
    thread_id = thread.get("id") if isinstance(thread, dict) else None
    path = thread.get("path") if isinstance(thread, dict) else None
    if not isinstance(thread_id, str) or not thread_id:
        raise RuntimeError("thread/start omitted thread.id")
    if not isinstance(path, str) or not path:
        raise RuntimeError("thread/start omitted thread.path")
    return thread_id, Path(path)


def _summarize_identity(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    content = (
        result.get("structuredContent") if isinstance(result, dict) else None
    )
    if not isinstance(content, dict):
        raise RuntimeError("Sentinel response omitted structuredContent")
    summary = {
        "succeeded": result.get("isError") is False,
        "server": content.get("server"),
        "tool": content.get("tool"),
        "pid": content.get("pid"),
        "instanceId": content.get("instanceId"),
        "callId": content.get("callId"),
        "arguments": content.get("arguments"),
    }
    if (
        summary["succeeded"] is not True
        or summary["server"]
        != "agent-autonomy-harness-mcp-lifecycle-sentinel"
        or summary["tool"] != "identity"
        or not isinstance(summary["pid"], int)
        or not isinstance(summary["instanceId"], str)
    ):
        raise RuntimeError("Sentinel identity response is incomplete")
    return summary


def _require_same_exact_sentinel(
    creator_call: dict[str, Any],
    observer_call: dict[str, Any],
) -> None:
    if (
        creator_call.get("pid"),
        creator_call.get("instanceId"),
    ) != (
        observer_call.get("pid"),
        observer_call.get("instanceId"),
    ):
        raise RuntimeError("connections did not bind the same exact Sentinel")


def seal_evidence(value: dict[str, Any], events: list[str]) -> dict[str, Any]:
    sealed = {
        "sealed": True,
        "sha256": canonical_json_sha256(value),
        "snapshot": value,
    }
    events.append("evidence:seal")
    return sealed


def execute_offline_injected_arm(
    *,
    arm: str,
    creator_a: InjectedTransport,
    observer_b: InjectedTransport,
    workspace: Path,
    sample_window: Callable[[str, str], dict[str, Any]],
    bounded_cleanup: Callable[[], None],
) -> dict[str, Any]:
    """Execute the v2 sequence only against injected deterministic transports."""
    if arm not in ARM_NAMES:
        raise ValueError(f"unsupported arm: {arm}")
    events: list[str] = []
    trace: dict[str, Any] = {
        "probeId": PROBE_ID,
        "arm": arm,
        "formalLiveRun": False,
        "events": events,
        "cleanup": {
            "creatorClosed": False,
            "observerClosed": False,
            "boundedCleanupInvoked": False,
            "errors": [],
        },
    }
    primary_error: Exception | None = None
    try:
        _initialize(observer_b, owner="observer-b", events=events)
        events.append("observer-b:config/read")
        config_response = observer_b.request(
            1,
            "config/read",
            {},
            phase="observer-b-initialized-barrier",
        )
        if not isinstance(config_response.get("result"), dict):
            raise RuntimeError("observer config/read barrier failed")

        _initialize(creator_a, owner="creator-a", events=events)
        events.append("creator-a:thread/start")
        start_response = creator_a.request(
            1,
            "thread/start",
            build_thread_start_params(workspace),
            phase="creator-a-thread-start",
        )
        thread_id, rollout_path = _extract_thread(start_response)
        trace["thread"] = {
            "id": thread_id,
            "ephemeral": False,
            "sandbox": "read-only",
            "acquisitionPath": "thread-created-auto-attach",
            "rolloutMaterialization": observe_rollout_materialization(
                rollout_path
            ),
            "modelTurnRequests": 0,
            "turnStartedNotifications": 0,
        }

        events.append("creator-a:mcpServer/tool/call")
        creator_call = _summarize_identity(
            creator_a.request(
                2,
                "mcpServer/tool/call",
                build_identity_tool_params(
                    thread_id,
                    "creator-a",
                    "baseline",
                ),
                phase="creator-a-baseline",
                thread_id=thread_id,
            )
        )
        events.append("observer-b:mcpServer/tool/call:baseline")
        observer_call = _summarize_identity(
            observer_b.request(
                2,
                "mcpServer/tool/call",
                build_identity_tool_params(
                    thread_id,
                    "observer-b",
                    "baseline",
                ),
                phase="observer-b-baseline-direct",
                thread_id=thread_id,
            )
        )
        _require_same_exact_sentinel(creator_call, observer_call)
        trace["baseline"] = {
            "creatorCall": creator_call,
            "observerCall": observer_call,
            "sameThread": True,
            "sameExactSentinel": True,
        }

        events.append(f"window:{arm}")
        window = sample_window(arm, thread_id)
        if not isinstance(window, dict):
            raise RuntimeError("sample window result is not an object")
        trace["evidenceSeal"] = seal_evidence(
            {
                "arm": arm,
                "threadId": thread_id,
                "baseline": trace["baseline"],
                "window": window,
                "rolloutMaterialization": trace["thread"][
                    "rolloutMaterialization"
                ],
            },
            events,
        )

        events.append("observer-b:mcpServer/tool/call:post-window")
        post_window_call = _summarize_identity(
            observer_b.request(
                3,
                "mcpServer/tool/call",
                build_identity_tool_params(
                    thread_id,
                    "observer-b",
                    "post-window",
                ),
                phase="observer-b-post-window-direct",
                thread_id=thread_id,
            )
        )
        trace["postWindowCall"] = post_window_call
        trace["evidenceSealedBeforeObserverPostWindowCall"] = (
            events.index("evidence:seal")
            < events.index("observer-b:mcpServer/tool/call:post-window")
        )
    except Exception as error:
        primary_error = error
        trace["failure"] = {
            "type": type(error).__name__,
            "message": str(error),
        }
    finally:
        cleanup_actions = (
            ("creator-a", "creatorClosed", creator_a.close),
            ("observer-b", "observerClosed", observer_b.close),
            (
                "bounded-sentinel",
                "boundedCleanupInvoked",
                bounded_cleanup,
            ),
        )
        for label, success_key, action in cleanup_actions:
            events.append(f"cleanup:{label}")
            try:
                action()
                trace["cleanup"][success_key] = True
            except Exception as cleanup_error:
                trace["cleanup"]["errors"].append(
                    {
                        "target": label,
                        "type": type(cleanup_error).__name__,
                        "message": str(cleanup_error),
                    }
                )
    if primary_error is not None:
        raise OfflineProbeFailure(str(primary_error), trace) from primary_error
    if trace["cleanup"]["errors"]:
        raise OfflineProbeFailure("offline cleanup failed", trace)
    return trace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Offline-injectable v2 source only; live execution is not "
            "implemented or authorized."
        )
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="print the offline-only boundary",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.describe:
        print(
            json.dumps(
                {
                    "probeId": PROBE_ID,
                    "mode": "offline-injected-transport-only",
                    "formalLiveRunCount": 0,
                    "liveExecutionAuthorized": False,
                },
                sort_keys=True,
            )
        )
        return 0
    raise SystemExit(
        "Live execution is not implemented or authorized; use deterministic "
        "injected transports in tests."
    )


if __name__ == "__main__":
    raise SystemExit(main())
