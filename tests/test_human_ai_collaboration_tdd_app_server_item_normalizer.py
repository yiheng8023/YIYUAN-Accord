from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_human_ai_collaboration_tdd_trial import (
    evaluate_tdd_timeline,
)
from scripts.normalize_human_ai_collaboration_tdd_app_server_items import (
    NORMALIZER_CONTRACT_VERSION,
    classify_unittest_invocation,
    command_may_write_files,
    normalize_tdd_app_server_event_stream,
    validate_raw_fixture_document,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "human-ai-collaboration-tdd-raw-app-server-item-fixtures-2026-07-26.json"
)
THREAD_ID = "thread-fixture"
TURN_ID = "turn-fixture"
FOCUSED = "test_feature.CappedBackoffTests.test_first_attempt"
OTHER_FOCUSED = "test_feature.CappedBackoffTests.test_cap"


def message(method: str, params: dict) -> dict:
    return {"jsonrpc": "2.0", "method": method, "params": params}


def target_params(**values) -> dict:
    return {"threadId": THREAD_ID, "turnId": TURN_ID, **values}


def file_item(item_id: str, root: Path, paths: list[str]) -> dict:
    changes = [
        {
            "path": str(root / path),
            "kind": {"type": "update"},
            "diff": f"diff for {path}",
        }
        for path in paths
    ]
    return {
        "id": item_id,
        "type": "fileChange",
        "status": "completed",
        "changes": changes,
    }


def command_item(
    item_id: str,
    command: str,
    output: str | None,
    exit_code: int | None,
    root: Path,
    *,
    status: str,
) -> dict:
    return {
        "id": item_id,
        "type": "commandExecution",
        "status": status,
        "command": command,
        "commandActions": [],
        "cwd": str(root),
        "aggregatedOutput": output,
        "exitCode": exit_code,
    }


def append_file_pair(
    messages: list[dict],
    *,
    item_id: str,
    root: Path,
    paths: list[str],
    include_start: bool = True,
) -> None:
    completed = file_item(item_id, root, paths)
    started = {**completed, "status": "inProgress", "changes": []}
    if include_start:
        messages.append(
            message(
                "item/started",
                target_params(item=started, startedAtMs=1),
            )
        )
    messages.append(
        message(
            "item/completed",
            target_params(item=completed, completedAtMs=2),
        )
    )


def append_command_pair(
    messages: list[dict],
    *,
    item_id: str,
    command: str,
    output: str,
    exit_code: int,
    root: Path,
    aggregated_override: str | None = None,
) -> None:
    messages.append(
        message(
            "item/started",
            target_params(
                item=command_item(
                    item_id,
                    command,
                    None,
                    None,
                    root,
                    status="inProgress",
                ),
                startedAtMs=3,
            ),
        )
    )
    messages.append(
        message(
            "item/commandExecution/outputDelta",
            target_params(itemId=item_id, delta=output),
        )
    )
    messages.append(
        message(
            "item/completed",
            target_params(
                item=command_item(
                    item_id,
                    command,
                    (
                        aggregated_override
                        if aggregated_override is not None
                        else output
                    ),
                    exit_code,
                    root,
                    status="completed",
                ),
                completedAtMs=4,
            ),
        )
    )


def build_raw_case(root: Path, mutation: str) -> list[dict]:
    messages = [
        message(
            "turn/started",
            {
                "threadId": THREAD_ID,
                "turn": {"id": TURN_ID},
            },
        )
    ]
    red_output = (
        "Ran 1 test\n\nFAILED (failures=1)\n"
        "FAIL: test_first_attempt\nAssertionError: None != 3\n"
    )
    red_exit = 1
    if mutation == "syntax-red":
        red_output = (
            "Ran 1 test\n\nFAILED (errors=1)\n"
            "ERROR: test_first_attempt\nSyntaxError: invalid syntax\n"
        )
    green_output = "Ran 1 test in 0.001s\n\nOK\n"
    green_identity = OTHER_FOCUSED if mutation == "identity-mismatch" else FOCUSED

    def add_test_mutation() -> None:
        append_file_pair(
            messages,
            item_id="file-test",
            root=root,
            paths=["test_feature.py"],
            include_start=mutation != "missing-start",
        )

    def add_red() -> None:
        append_command_pair(
            messages,
            item_id="cmd-red",
            command=f"python -B -m unittest -v {FOCUSED}",
            output=red_output,
            exit_code=red_exit,
            root=root,
            aggregated_override=(
                "different output"
                if mutation == "output-conflict"
                else None
            ),
        )

    def add_production() -> None:
        paths = ["feature.py"]
        if mutation == "mixed-mutation":
            paths = ["feature.py", "test_feature.py"]
        elif mutation == "out-of-scope":
            paths = ["feature.py", "unexpected.py"]
        append_file_pair(
            messages,
            item_id="file-production",
            root=root,
            paths=paths,
        )

    if mutation == "noncausal-empty-output":
        append_command_pair(
            messages,
            item_id="cmd-noncausal-empty",
            command="Get-ChildItem missing.py",
            output="",
            exit_code=1,
            root=root,
        )
    add_test_mutation()
    if mutation == "production-before-red":
        add_production()
        add_red()
    else:
        add_red()
        add_production()
    if mutation == "process-evidence":
        append_file_pair(
            messages,
            item_id="file-evidence",
            root=root,
            paths=["PROCESS_EVIDENCE.json"],
        )
    append_command_pair(
        messages,
        item_id="cmd-green",
        command=f"python -B -m unittest -v {green_identity}",
        output=(
            "Ran 0 tests in 0.000s\n\nOK\n"
            if mutation == "zero-tests-green"
            else green_output
        ),
        exit_code=0,
        root=root,
    )
    append_command_pair(
        messages,
        item_id="cmd-full",
        command=(
            "python -B -m unittest -v test_feature.py > opaque-output.txt"
            if mutation == "opaque-write-command"
            else "python -B -m unittest -v test_feature.py"
        ),
        output="Ran 4 tests in 0.002s\n\nOK\n",
        exit_code=0,
        root=root,
    )
    if mutation == "unknown-method":
        messages.append(
            message(
                "item/futureCausal/delta",
                target_params(itemId="future", delta="state"),
            )
        )
    if mutation == "known-noncausal":
        reasoning = {
            "id": "reasoning-1",
            "type": "reasoning",
            "summary": [],
            "content": [],
        }
        messages.extend(
            [
                message(
                    "item/started",
                    target_params(item=reasoning, startedAtMs=5),
                ),
                message(
                    "item/completed",
                    target_params(item=reasoning, completedAtMs=6),
                ),
                message(
                    "turn/plan/updated",
                    target_params(
                        explanation="fixture plan update",
                        plan=[
                            {
                                "step": "inspect",
                                "status": "completed",
                            }
                        ],
                    ),
                ),
            ]
        )
    if mutation == "future-plan-shape":
        messages.append(
            message(
                "turn/plan/updated",
                target_params(
                    explanation="future shape with an unreviewed field",
                    plan=[
                        {
                            "step": "write",
                            "status": "inProgress",
                        }
                    ],
                    stateMutationCandidate=True,
                ),
            )
        )
    messages.append(
        message(
            "turn/completed",
            {
                "threadId": THREAD_ID,
                "turn": {"id": TURN_ID},
            },
        )
    )
    return messages


class HumanAiCollaborationTddAppServerItemNormalizerTests(
    unittest.TestCase
):
    def test_all_raw_fixture_cases_match(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            NORMALIZER_CONTRACT_VERSION,
            fixture["normalizerContractVersion"],
        )
        validate_raw_fixture_document(fixture)
        self.assertEqual(15, len(fixture["cases"]))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for case in fixture["cases"]:
                with self.subTest(case=case["id"]):
                    result = normalize_tdd_app_server_event_stream(
                        build_raw_case(root, case["mutation"]),
                        thread_id=THREAD_ID,
                        turn_id=TURN_ID,
                        trial_root=root,
                    )
                    offline = evaluate_tdd_timeline(result["events"])
                    self.assertEqual(
                        case["expectedNormalizerStatus"],
                        result["status"],
                    )
                    self.assertEqual(
                        case["expectedOfflineStatus"],
                        offline["status"],
                    )

    def test_valid_case_preserves_receive_order_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = normalize_tdd_app_server_event_stream(
                build_raw_case(root, "none"),
                thread_id=THREAD_ID,
                turn_id=TURN_ID,
                trial_root=root,
            )
        ordinals = [
            row["receiveOrdinal"] for row in result["rawEnvelopes"]
        ]
        self.assertEqual(sorted(ordinals), ordinals)
        self.assertTrue(result["redGreenIdentityMatched"])
        self.assertTrue(result["focusedGreenObserved"])
        self.assertTrue(result["fullVisibleSuiteGreenObserved"])
        self.assertFalse(result["provesNoUnobservedTransientWrite"])
        self.assertFalse(result["provesCrossHostSchemaStability"])

    def test_other_turn_messages_are_filtered(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            messages = build_raw_case(root, "none")
            messages.insert(
                1,
                message(
                    "item/futureCausal/delta",
                    {
                        "threadId": "other",
                        "turnId": "other",
                        "itemId": "ignored",
                    },
                ),
            )
            result = normalize_tdd_app_server_event_stream(
                messages,
                thread_id=THREAD_ID,
                turn_id=TURN_ID,
                trial_root=root,
            )
        self.assertEqual("normalized-observable", result["status"])
        self.assertEqual([], result["unknownMethods"])

    def test_nested_powershell_unittest_command_is_classified(self) -> None:
        command = (
            '"C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command '
            "'python -B -m unittest -v test_feature.py'"
        )
        self.assertEqual(
            {
                "testScope": "full-visible-suite",
                "testIdentity": None,
            },
            classify_unittest_invocation(command),
        )

    def test_null_redirection_is_not_treated_as_a_file_write(self) -> None:
        self.assertFalse(
            command_may_write_files(
                "git rev-parse HEAD 2>$null"
            )
        )
        self.assertTrue(
            command_may_write_files(
                "python -B -m unittest test_feature.py > result.txt"
            )
        )
        self.assertTrue(
            command_may_write_files(
                "Set-Content -LiteralPath feature.py -Value $source"
            )
        )


if __name__ == "__main__":
    unittest.main()
