"""Deadline boundaries must preserve recovery without silently dispatching work."""
import unittest
from scripts.codex_rpc import BoundedRpc, RpcDeadline, RpcRemoteError


class CodexRpcTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.sent, self.events, self.notifications = [], [], []
        self.reply_at = None
        self.rpc = BoundedRpc(self.send, self.receive, work_deadline=20,
            request_timeout=4, recovery_timeout=6, clock=lambda: self.now,
            on_event=self.notifications.append)

    def send(self, request):
        self.sent.append(request)

    def receive(self, deadline):
        if self.events:
            return self.events.pop(0)
        if self.reply_at is not None:
            self.now = self.reply_at
        return {"id": self.sent[-1]["id"], "result": {"received": True}}

    def test_expired_work_never_dispatches_and_recovery_can_read_acknowledgement(self):
        self.now = 20
        with self.assertRaises(RpcDeadline) as caught:
            self.rpc.request("turn/start", {"threadId": "owned"})
        self.assertFalse(caught.exception.may_have_executed)
        self.assertEqual(self.sent, [])
        self.assertEqual(self.rpc.begin_recovery("owned"), 26)
        self.assertEqual(self.rpc.request("turn/interrupt", {"threadId": "owned", "turnId": "turn"}), {"received": True})
        self.assertEqual(len(self.sent), 1)

    def test_recovery_neither_extends_its_window_nor_reopens_work(self):
        self.assertEqual(self.rpc.begin_recovery("owned"), 16)
        self.now = 14
        self.assertEqual(self.rpc.begin_recovery("owned"), 16)
        for method, params in [("turn/start", {"threadId": "owned"}),
                               ("thread/start", {}),
                               ("thread/read", {"threadId": "other"})]:
            with self.subTest(method=method, params=params), self.assertRaises(ValueError):
                self.rpc.request(method, params)
        with self.assertRaises(ValueError):
            self.rpc.begin_recovery("other")
        self.now = 16
        with self.assertRaises(RpcDeadline) as caught:
            self.rpc.request("thread/unsubscribe", {"threadId": "owned"})
        self.assertFalse(caught.exception.may_have_executed)
        self.assertEqual(self.sent, [])

    def test_deadline_after_send_reports_unknown_effect_and_never_retries(self):
        self.reply_at = 14
        with self.assertRaises(RpcDeadline) as caught:
            self.rpc.request("turn/start", {"threadId": "owned"})
        error = caught.exception
        self.assertTrue(error.may_have_executed)
        self.assertEqual(error.request_id, self.sent[0]["id"])
        self.assertEqual(error.response["result"], {"received": True})
        self.assertEqual(len(self.sent), 1)

    def test_send_timeout_is_not_mistaken_for_no_dispatch(self):
        def send(request):
            self.sent.append(request)
            raise TimeoutError("partial transport write")
        rpc = BoundedRpc(send, self.receive, work_deadline=20,
            request_timeout=4, recovery_timeout=6, clock=lambda: self.now,
            on_event=self.notifications.append)
        with self.assertRaises(RpcDeadline) as caught:
            rpc.request("turn/start", {"threadId": "owned"})
        self.assertTrue(caught.exception.may_have_executed)
        self.assertEqual(len(self.sent), 1)

    def test_interleaved_events_and_prior_replies_reach_the_caller(self):
        notification = {"method": "turn/completed", "params": {"threadId": "owned"}}
        earlier = {"id": "earlier", "result": {"alreadyExecuted": True}}
        self.events = [notification, earlier]
        self.assertEqual(self.rpc.request("thread/read", {"threadId": "owned"}), {"received": True})
        self.assertEqual(self.notifications, [notification, earlier])

    def test_remote_error_is_distinct_and_does_not_echo_private_response(self):
        def receive(deadline):
            return {"id": self.sent[-1]["id"], "error": {"message": "private detail"}}
        self.rpc._receive = receive
        with self.assertRaises(RpcRemoteError) as caught:
            self.rpc.request("thread/read", {"threadId": "owned"})
        self.assertNotIn("private detail", str(caught.exception))
        self.assertEqual(caught.exception.response["error"]["message"], "private detail")

    def test_interleaved_event_received_at_deadline_still_reaches_caller(self):
        event = {"method": "turn/completed", "params": {"threadId": "owned"}}
        def receive(deadline):
            self.now = deadline
            return event
        self.rpc._receive = receive
        with self.assertRaises(RpcDeadline) as caught:
            self.rpc.request("thread/read", {"threadId": "owned"})
        self.assertTrue(caught.exception.may_have_executed)
        self.assertEqual(self.notifications, [event])

    def test_recovery_operations_share_the_fixed_recovery_deadline(self):
        self.now = 30
        self.rpc.begin_recovery("owned")
        self.reply_at = 33
        self.rpc.request("turn/interrupt", {"threadId": "owned", "turnId": "turn"})
        self.reply_at = 35
        self.rpc.request("thread/read", {"threadId": "owned"})
        self.reply_at = 36
        with self.assertRaises(RpcDeadline) as caught:
            self.rpc.request("thread/unsubscribe", {"threadId": "owned"})
        self.assertEqual(caught.exception.phase, "recovery")
        self.assertTrue(caught.exception.may_have_executed)
        self.assertEqual(self.rpc.recovery_deadline, 36)

    def test_invalid_limits_cannot_disable_the_bounds(self):
        for field in ["work_deadline", "request_timeout", "recovery_timeout"]:
            for value in [float("inf"), float("nan"), True, "30", None]:
                args = dict(work_deadline=20, request_timeout=4, recovery_timeout=6)
                args[field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    BoundedRpc(self.send, self.receive, on_event=self.notifications.append, **args)
        for field in ["request_timeout", "recovery_timeout"]:
            for value in [0, -1]:
                args = dict(work_deadline=20, request_timeout=4, recovery_timeout=6)
                args[field] = value
                with self.assertRaises(ValueError):
                    BoundedRpc(self.send, self.receive, on_event=self.notifications.append, **args)

    def test_event_handling_cannot_be_silently_omitted(self):
        args = dict(work_deadline=20, request_timeout=4, recovery_timeout=6)
        with self.assertRaises(TypeError):
            BoundedRpc(self.send, self.receive, **args)
        with self.assertRaises(ValueError):
            BoundedRpc(self.send, self.receive, on_event=None, **args)
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
