"""Protocol evidence only: real native envelope shapes plus missing/foreign cases."""
import copy
from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import patch

from scripts.codex_events import NativeTurnWatch


def item(method, kind="contextCompaction", item_id="compact", turn="turn", thread="thread", **values):
    return {"method": method, "params": {"threadId": thread, "turnId": turn,
            "item": {"type": kind, "id": item_id, **values}}}


def terminal(status="completed", turn="turn", thread="thread"):
    # Actual App Server turn terminals have no params.turnId.
    return {"method": "turn/completed", "params": {"threadId": thread,
            "turn": {"id": turn, "status": status}}}


class NativeTurnWatchTests(unittest.TestCase):
    def test_manual_compaction_requires_exact_new_chain(self):
        watch = NativeTurnWatch.for_compaction("thread")
        for event in [terminal(turn="old"), item("item/completed", item_id="old", turn="old"),
                      item("item/started", thread="foreign")]:
            self.assertIsNone(watch.observe(event).turn_id)
        self.assertFalse(watch.observe(item("item/started")).protocol_complete)
        self.assertEqual(watch.view.turn_id, "turn")
        for event in [item("item/completed", item_id="wrong"), item("item/completed", turn="old"),
                      terminal(turn="old"), terminal(thread="foreign")]:
            self.assertFalse(watch.observe(event).protocol_complete)
        self.assertFalse(watch.observe(item("item/completed")).finished)
        result = watch.observe(terminal())
        self.assertTrue(result.finished)
        self.assertTrue(result.protocol_complete)

    def test_missing_compaction_events_never_pass(self):
        events = [item("item/started"), item("item/completed"), terminal()]
        for omitted in range(len(events)):
            with self.subTest(omitted=omitted):
                watch = NativeTurnWatch.for_compaction("thread")
                for i, event in enumerate(events):
                    if i != omitted:
                        watch.observe(event)
                self.assertFalse(watch.view.protocol_complete)
        watch = NativeTurnWatch.for_compaction("thread")
        for event in [item("item/completed"), item("item/started"), terminal()]:
            watch.observe(event)
        self.assertFalse(watch.view.finished)

    def test_failure_terminal_does_not_wait_for_missing_completion(self):
        for status in ["failed", "interrupted", "future-terminal-status"]:
            watch = NativeTurnWatch.for_compaction("thread")
            watch.observe(item("item/started"))
            result = watch.observe(terminal(status))
            self.assertTrue(result.finished)
            self.assertFalse(result.protocol_complete)

    def test_failure_before_compaction_identity_remains_unknown(self):
        watch = NativeTurnWatch.for_compaction("thread")
        watch.observe({"method": "turn/started", "params": {
            "threadId": "thread", "turn": {"id": "attempt", "status": "inProgress"}}})
        result = watch.observe(terminal("failed", turn="attempt"))
        self.assertIsNone(result.turn_id)
        self.assertIsNone(result.terminal_status)
        self.assertFalse(result.finished)
        self.assertFalse(result.protocol_complete)

    def test_user_turn_needs_its_own_nonempty_final_answer(self):
        watch = NativeTurnWatch.for_turn("thread", "turn")
        for text, phase, turn, thread in [("", "final_answer", "turn", "thread"),
                (" \n", "final_answer", "turn", "thread"), ("still working", "commentary", "turn", "thread"),
                ("earlier", "final_answer", "old", "thread"), ("other", "final_answer", "turn", "foreign")]:
            watch.observe(item("item/completed", "agentMessage", "answer", turn, thread, phase=phase, text=text))
        self.assertIsNone(watch.view.final_answer_id)
        result = watch.observe(terminal())
        self.assertTrue(result.finished)
        self.assertFalse(result.protocol_complete)
        watch.observe(item("item/completed", "agentMessage", "answer", phase="final_answer", text="actual answer"))
        self.assertTrue(watch.view.protocol_complete)

    def test_answer_alone_or_failed_turn_is_not_protocol_success(self):
        watch = NativeTurnWatch.for_turn("thread", "turn")
        watch.observe(item("item/completed", "agentMessage", "answer", phase="final_answer", text="done"))
        self.assertFalse(watch.view.finished)
        self.assertFalse(watch.view.protocol_complete)
        self.assertFalse(watch.observe(terminal("failed")).protocol_complete)

    def test_terminal_can_carry_the_authoritative_final_item(self):
        watch = NativeTurnWatch.for_turn("thread", "turn")
        event = terminal()
        event["params"]["turn"]["items"] = [{"type": "agentMessage", "id": "answer",
            "phase": "final_answer", "text": "actual final"}]
        result = watch.observe(event)
        self.assertTrue(result.protocol_complete)
        self.assertEqual(result.final_answer_id, "answer")
        for items in [[], [{"type": "agentMessage", "id": "comment", "phase": "commentary", "text": "working"}]]:
            event["params"]["turn"]["items"] = items
            self.assertFalse(NativeTurnWatch.for_turn("thread", "turn").observe(event).protocol_complete)

    def test_malformed_terminal_answer_cannot_hide_behind_completion(self):
        for items in [None, [None], [{"type": "agentMessage", "id": "answer", "phase": "final_answer", "text": None}]]:
            event = terminal()
            event["params"]["turn"]["items"] = items
            watch = NativeTurnWatch.for_turn("thread", "turn")
            with self.assertRaises(ValueError):
                watch.observe(event)
            self.assertFalse(watch.view.protocol_complete)

    def test_user_turn_can_contain_multiple_compactions(self):
        watch = NativeTurnWatch.for_turn("thread", "turn")
        for name in ["first", "second"]:
            watch.observe(item("item/started", item_id=name))
            watch.observe(item("item/completed", item_id=name))
        watch.observe(item("item/completed", "agentMessage", "answer", phase="final_answer", text="done"))
        self.assertTrue(watch.observe(terminal()).protocol_complete)

    def test_duplicate_compaction_start_does_not_erase_observed_completion(self):
        watch = NativeTurnWatch.for_compaction("thread")
        watch.observe(item("item/started"))
        watch.observe(item("item/completed"))
        watch.observe(item("item/started"))
        self.assertTrue(watch.observe(terminal()).protocol_complete)

    def test_ambiguity_invalidates_watch_instead_of_reusing_success(self):
        watch = NativeTurnWatch.for_compaction("thread")
        for event in [item("item/started"), item("item/completed"), terminal()]:
            watch.observe(event)
        with self.assertRaises(ValueError):
            watch.observe(item("item/started", item_id="another"))
        self.assertTrue(watch.view.finished)
        self.assertFalse(watch.view.protocol_complete)
        self.assertIsNotNone(watch.view.invalid_reason)
        with self.assertRaises(ValueError):
            watch.observe(terminal())

    def test_conflicting_terminal_is_not_silently_overwritten(self):
        watch = NativeTurnWatch.for_turn("thread", "turn")
        watch.observe(terminal("completed"))
        with self.assertRaises(ValueError):
            watch.observe(terminal("failed"))
        self.assertFalse(watch.view.protocol_complete)

    def test_malformed_target_notifications_and_server_requests_fail_closed(self):
        cases = [None, {"method": "turn/completed", "params": None},
                 {"method": "turn/completed", "params": {"threadId": "thread", "turnId": "turn"}},
                 terminal(status=""), item("item/started", item_id=""),
                 {"method": "item/started", "params": {"threadId": "thread", "item": []}},
                 {"id": "request", "method": "item/tool/requestUserInput", "params": {}}]
        for event in cases:
            with self.subTest(event=event):
                watch = NativeTurnWatch.for_compaction("thread")
                watch.observe(item("item/started"))
                with self.assertRaises(ValueError):
                    watch.observe(event)
                self.assertIsNotNone(watch.view.invalid_reason)
                self.assertFalse(watch.view.protocol_complete)

    def test_views_are_immutable_and_do_not_alias_input_or_access_files(self):
        watch = NativeTurnWatch.for_compaction("thread")
        event = item("item/started")
        original = copy.deepcopy(event)
        with patch("builtins.open", side_effect=AssertionError("no file access")):
            before = watch.observe(event)
            watch.observe(item("item/completed"))
            after = watch.observe(terminal())
        self.assertEqual(event, original)
        event["params"]["turnId"] = "mutated"
        self.assertEqual(after.turn_id, "turn")
        self.assertFalse(before.compaction_completed)
        self.assertTrue(after.compaction_completed)
        with self.assertRaises(FrozenInstanceError):
            after.turn_id = "different"
        self.assertNotIn("text", after.__dict__)

    def test_instances_and_ignored_notifications_do_not_share_state(self):
        first = NativeTurnWatch.for_compaction("thread")
        second = NativeTurnWatch.for_compaction("thread")
        for event in [item("item/started"), item("item/completed"), terminal()]:
            first.observe(event)
        initial = second.view
        for event in [{"id": "earlier", "result": {}}, {"method": "account/updated", "params": {}},
                      item("item/completed", "commandExecution")]:
            self.assertEqual(second.observe(event), initial)
        self.assertIsNone(second.view.turn_id)

    def test_unbound_constructor_cannot_guess_an_identity(self):
        for value in [None, "", "  ", 1, True]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                NativeTurnWatch.for_compaction(value)
            with self.assertRaises(ValueError):
                NativeTurnWatch.for_turn("thread", value)
        with self.assertRaises(ValueError):
            NativeTurnWatch("thread", "turn", compaction=True)
        with self.assertRaises(ValueError):
            NativeTurnWatch("thread", compaction="false")


if __name__ == "__main__":
    unittest.main()
