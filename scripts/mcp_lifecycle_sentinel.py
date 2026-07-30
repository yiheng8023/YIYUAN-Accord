#!/usr/bin/env python3
"""Minimal local stdio MCP server for isolated lifecycle experiments.

The server has no network or account dependency. It exposes deterministic
identity and bounded hold tools, and writes only to an explicitly supplied
temporary JSONL event log. An abrupt-exit tool is available only when the
runner supplies a one-process token and the call presents the exact token.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
import uuid
from typing import Any


SERVER_NAME = "agent-autonomy-harness-mcp-lifecycle-sentinel"
SERVER_VERSION = "1.1.0"
CRASH_EXIT_CODE = 86


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Sentinel:
    def __init__(self, event_log: Path, crash_token: str | None = None) -> None:
        self.event_log = event_log
        self.crash_token = crash_token
        self.instance_id = str(uuid.uuid4())
        self.call_sequence = 0

    def record(self, event: str, **fields: Any) -> None:
        value = {
            "timestamp": utc_now(),
            "event": event,
            "pid": os.getpid(),
            "instanceId": self.instance_id,
            **fields,
        }
        with self.event_log.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False))
            stream.write("\n")

    def send(self, value: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(value, separators=(",", ":"), ensure_ascii=False))
        sys.stdout.write("\n")
        sys.stdout.flush()

    def tool_result(self, name: str, arguments: Any) -> dict[str, Any]:
        self.call_sequence += 1
        call_id = f"{self.instance_id}:{self.call_sequence}"
        if not isinstance(arguments, dict):
            arguments = {}
        if name == "crash" and self.crash_token is not None:
            supplied = arguments.get("token")
            if not isinstance(supplied, str) or not secrets.compare_digest(
                supplied, self.crash_token
            ):
                self.record(
                    "crash-rejected",
                    callId=call_id,
                    tool=name,
                    reason="token-mismatch",
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "crash token did not match",
                        }
                    ],
                    "isError": True,
                }
            self.record(
                "crash-requested",
                callId=call_id,
                tool=name,
                tokenMatched=True,
                exitCode=CRASH_EXIT_CODE,
            )
            os._exit(CRASH_EXIT_CODE)
        if name == "hold":
            requested = arguments.get("milliseconds", 0)
            milliseconds = (
                requested
                if isinstance(requested, int) and not isinstance(requested, bool)
                else 0
            )
            milliseconds = max(0, min(milliseconds, 5000))
            time.sleep(milliseconds / 1000)
        elif name != "identity":
            return {
                "content": [{"type": "text", "text": f"unknown tool: {name}"}],
                "isError": True,
            }

        payload = {
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "pid": os.getpid(),
            "instanceId": self.instance_id,
            "callId": call_id,
            "tool": name,
            "arguments": arguments,
        }
        self.record("tool-call", **payload)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
                }
            ],
            "structuredContent": payload,
            "isError": False,
        }

    def handle(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params")
        self.record("message", method=method, hasId="id" in message)

        if "id" not in message:
            return
        if method == "initialize":
            protocol_version = (
                params.get("protocolVersion")
                if isinstance(params, dict)
                else "2024-11-05"
            )
            self.send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": protocol_version,
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {
                            "name": SERVER_NAME,
                            "version": SERVER_VERSION,
                        },
                    },
                }
            )
            return
        if method == "ping":
            self.send({"jsonrpc": "2.0", "id": request_id, "result": {}})
            return
        if method == "tools/list":
            tools = [
                {
                    "name": "identity",
                    "description": (
                        "Return the sentinel PID, instance id, and call id."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
                {
                    "name": "hold",
                    "description": (
                        "Wait for at most five seconds, then return identity."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "milliseconds": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 5000,
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            ]
            if self.crash_token is not None:
                tools.append(
                    {
                        "name": "crash",
                        "description": (
                            "Test-only: exit abruptly before responding when the "
                            "one-process token matches."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "token": {"type": "string"},
                            },
                            "required": ["token"],
                            "additionalProperties": False,
                        },
                    }
                )
            self.send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools},
                }
            )
            return
        if method == "resources/list":
            self.send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": []},
                }
            )
            return
        if method == "resources/templates/list":
            self.send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resourceTemplates": []},
                }
            )
            return
        if method == "tools/call":
            name = params.get("name") if isinstance(params, dict) else None
            arguments = params.get("arguments", {}) if isinstance(params, dict) else {}
            self.send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": self.tool_result(str(name), arguments),
                }
            )
            return

        self.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"method not found: {method}"},
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-log", type=Path, required=True)
    parser.add_argument(
        "--allow-crash-token",
        help=(
            "Test-only one-process token. Without it the crash tool is not "
            "advertised and cannot exit the process."
        ),
    )
    parser.add_argument(
        "--cleanup-marker",
        type=Path,
        help=(
            "Test-only marker watched by the Sentinel. Observing it records "
            "harness cleanup and exits without implying natural lifecycle release."
        ),
    )
    arguments = parser.parse_args()
    event_log = arguments.event_log.resolve()
    event_log.parent.mkdir(parents=True, exist_ok=True)
    sentinel = Sentinel(event_log, crash_token=arguments.allow_crash_token)
    sentinel.record("instance-start")
    if arguments.cleanup_marker is not None:
        cleanup_marker = arguments.cleanup_marker.resolve()

        def watch_cleanup_marker() -> None:
            while not cleanup_marker.exists():
                time.sleep(0.05)
            sentinel.record(
                "harness-cleanup-marker-observed",
                marker=cleanup_marker.as_posix(),
            )
            os._exit(0)

        threading.Thread(target=watch_cleanup_marker, daemon=True).start()
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                sentinel.record("invalid-json", error=str(error))
                continue
            if isinstance(value, dict):
                sentinel.handle(value)
    finally:
        sentinel.record("instance-stop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
