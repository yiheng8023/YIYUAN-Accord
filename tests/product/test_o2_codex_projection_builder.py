from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from harness.task_capture_o2_codex_reference import (
    BUILDER_KIND,
    BUILDER_LOCATOR,
    SOURCE_CONTRACT_REVISION,
    build_filesystem_projection,
    build_plugin_list_projection,
    build_exec_projection,
)


BUILDER_SHA256 = "a" * 64
BUILDER_REVISION = "b" * 40


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()


class O2CodexProjectionBuilderTests(unittest.TestCase):
    def test_plugin_list_projection_strips_native_paths(self) -> None:
        native = {
            "installed": [
                {
                    "pluginId": "agent-autonomy-harness-codex@agent-autonomy-harness",
                    "name": "agent-autonomy-harness-codex",
                    "marketplaceName": "agent-autonomy-harness",
                    "version": "1.2.0-conformance-candidate.1+codex.payload-707d3bb49a1d",
                    "installed": True,
                    "enabled": True,
                    "source": {
                        "source": "local",
                        "path": "C:\\Users\\private\\plugin",
                    },
                    "marketplaceSource": {
                        "sourceType": "local",
                        "source": "\\\\?\\C:\\Users\\private\\marketplace",
                    },
                    "installPolicy": "AVAILABLE",
                    "authPolicy": "ON_INSTALL",
                }
            ],
            "available": [],
        }

        projection = build_plugin_list_projection(
            json_bytes(native),
            environment_identity="codex-env.clean-isolated-v1",
            codex_version="0.147.0",
            builder_revision=BUILDER_REVISION,
            builder_sha256=BUILDER_SHA256,
        )

        self.assertEqual(
            projection["projectionBuilder"],
            {
                "kind": BUILDER_KIND,
                "locator": BUILDER_LOCATOR,
                "revision": BUILDER_REVISION,
                "sha256": BUILDER_SHA256,
                "sourceContractRevision": SOURCE_CONTRACT_REVISION,
            },
        )
        self.assertEqual(
            projection["plugins"],
            [
                {
                    "pluginId": "agent-autonomy-harness-codex@agent-autonomy-harness",
                    "version": "1.2.0-conformance-candidate.1+codex.payload-707d3bb49a1d",
                    "installed": True,
                    "enabled": True,
                    "sourceType": "local-marketplace",
                }
            ],
        )
        self.assertNotIn("Users", json.dumps(projection))

    def test_exec_projection_uses_only_terminal_public_events(self) -> None:
        message = "READY"
        native_events = [
            {"type": "thread.started", "thread_id": "019f2b90-0c34-77a1-ad02-b38355965b93"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {"id": "item_0", "type": "reasoning", "text": "private"},
            },
            {
                "type": "item.started",
                "item": {
                    "id": "item_1",
                    "type": "command_execution",
                    "command": "powershell -File C:\\Users\\private\\task.ps1",
                    "aggregated_output": "",
                    "status": "in_progress",
                },
            },
            {
                "type": "item.completed",
                "item": {
                    "id": "item_1",
                    "type": "command_execution",
                    "command": "powershell -File C:\\Users\\private\\task.ps1",
                    "aggregated_output": "private output",
                    "exit_code": 0,
                    "status": "completed",
                },
            },
            {
                "type": "item.completed",
                "item": {"id": "item_2", "type": "agent_message", "text": message},
            },
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 10,
                    "cached_input_tokens": 0,
                    "cache_write_input_tokens": 0,
                    "output_tokens": 2,
                    "reasoning_output_tokens": 0,
                },
            },
        ]
        raw = b"".join(json_bytes(event) for event in native_events)

        projection = build_exec_projection(
            raw,
            scenario_identity="o2-codex-reference.simple-native-no-op",
            phase="single",
            codex_version="0.147.0",
            goal_sha256="b" * 64,
            builder_revision=BUILDER_REVISION,
            builder_sha256=BUILDER_SHA256,
        )

        self.assertEqual(
            projection["events"],
            [
                {"type": "thread.started"},
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "itemType": "action_completion",
                    "exitCode": 0,
                },
                {
                    "type": "item.completed",
                    "itemType": "agent_message",
                    "messageSha256": hashlib.sha256(message.encode()).hexdigest(),
                },
                {"type": "turn.completed"},
            ],
        )
        serialized = json.dumps(projection)
        self.assertNotIn("019f2b90", serialized)
        self.assertNotIn("Users", serialized)
        self.assertNotIn("private output", serialized)

    def test_exec_projection_rejects_failure_and_unknown_item(self) -> None:
        envelopes = (
            [
                {"type": "thread.started", "thread_id": "thread-private"},
                {"type": "turn.started"},
                {"type": "turn.failed", "error": {"message": "failed"}},
            ],
            [
                {"type": "thread.started", "thread_id": "thread-private"},
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "item": {"id": "item_0", "type": "web_search", "query": "x"},
                },
                {"type": "turn.completed", "usage": {}},
            ],
        )
        for events in envelopes:
            with self.subTest(events=events):
                with self.assertRaises(ValueError):
                    build_exec_projection(
                        b"".join(json_bytes(event) for event in events),
                        scenario_identity="o2-codex-reference.simple-native-no-op",
                        phase="single",
                        codex_version="0.147.0",
                        goal_sha256="b" * 64,
                        builder_revision=BUILDER_REVISION,
                        builder_sha256=BUILDER_SHA256,
                    )

    def test_filesystem_projection_is_bounded_and_rejects_links(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "result.json").write_bytes(b'{"status":"ok"}\n')
            projection = build_filesystem_projection(
                root,
                scenario_identity="o2-codex-reference.nontrivial-goal-intake",
                phase="after",
                builder_revision=BUILDER_REVISION,
                builder_sha256=BUILDER_SHA256,
            )
            self.assertEqual(projection["files"][0]["path"], "result.json")
            self.assertEqual(
                projection["files"][0]["sha256"],
                hashlib.sha256(b'{"status":"ok"}\n').hexdigest(),
            )
            with patch.object(Path, "is_symlink", return_value=True):
                with self.assertRaises(ValueError):
                    build_filesystem_projection(
                        root,
                        scenario_identity="o2-codex-reference.nontrivial-goal-intake",
                        phase="after",
                        builder_revision=BUILDER_REVISION,
                        builder_sha256=BUILDER_SHA256,
                    )

    def test_duplicate_and_oversized_native_input_fail_closed(self) -> None:
        duplicate = b'{"installed":[],"installed":[],"available":[]}\n'
        with self.assertRaises(ValueError):
            build_plugin_list_projection(
                duplicate,
                environment_identity="codex-env.clean-isolated-v1",
                codex_version="0.147.0",
                builder_revision=BUILDER_REVISION,
                builder_sha256=BUILDER_SHA256,
            )
        with self.assertRaises(ValueError):
            build_plugin_list_projection(
                b" " * (1_048_576 + 1),
                environment_identity="codex-env.clean-isolated-v1",
                codex_version="0.147.0",
                builder_revision=BUILDER_REVISION,
                builder_sha256=BUILDER_SHA256,
            )


if __name__ == "__main__":
    unittest.main()
