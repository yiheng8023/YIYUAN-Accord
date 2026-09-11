"""Caller-owned deadlines for a serialized Codex App Server connection.

This does not start a process, authenticate ownership, retry an operation or
impose a host permission barrier. The caller supplies a bounded send/receive
transport, retains raw evidence and owns final process/resource cleanup.
"""
import math
import time
import uuid


class RpcDeadline(TimeoutError):
    """After a send attempt, effects remain unknown without reconciliation."""
    def __init__(self, phase, request_id=None, response=None):
        super().__init__(f"{phase} RPC deadline exceeded")
        self.phase = phase
        self.request_id = request_id
        self.may_have_executed = request_id is not None
        self.response = response


class RpcRemoteError(RuntimeError):
    def __init__(self, request_id, response):
        super().__init__("native RPC returned an error; inspect the bound response")
        self.request_id = request_id
        self.response = response


def _finite(value, *, positive=False):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or (positive and value <= 0)):
        raise ValueError("finite deadline and positive durations required")
    return value


class BoundedRpc:
    """One caller/connection; the caller explicitly handles interleaved events.

    receive(deadline) uses the same monotonic clock and must honor that absolute
    deadline. send must itself be bounded. on_event handles interleaved events;
    neither callback may manufacture authority or perform unbounded work.
    """
    def __init__(self, send, receive, *, work_deadline, request_timeout,
                 recovery_timeout, on_event, clock=time.monotonic):
        if not callable(on_event):
            raise ValueError("an interleaved-event handler is required")
        self._send, self._receive, self._clock = send, receive, clock
        self._work_deadline = _finite(work_deadline)
        self._request_timeout = _finite(request_timeout, positive=True)
        self._recovery_timeout = _finite(recovery_timeout, positive=True)
        self._on_event = on_event
        self._recovery_deadline = None
        self._recovery_thread = None
        self._prefix = uuid.uuid4().hex
        self._sequence = 0

    @property
    def recovery_deadline(self):
        return self._recovery_deadline

    def begin_recovery(self, owned_thread_id):
        """Caller must bind this target to its actual owned/native receipt.

        Recovery cannot restart or extend work, and repeated calls cannot renew
        its deadline or retarget it. Other owned cleanup needs its own bounds.
        """
        if not isinstance(owned_thread_id, str) or not owned_thread_id.strip():
            raise ValueError("an independently bound recovery target is required")
        if self._recovery_deadline is not None:
            if owned_thread_id != self._recovery_thread:
                raise ValueError("recovery target is already bound")
            return self._recovery_deadline
        self._recovery_thread = owned_thread_id
        self._recovery_deadline = _finite(self._clock() + self._recovery_timeout)
        return self._recovery_deadline

    def request(self, method, params):
        phase, limit = "work", self._work_deadline
        if self._recovery_deadline is not None:
            phase, limit = "recovery", self._recovery_deadline
            if (method not in {"turn/interrupt", "thread/read", "thread/unsubscribe"}
                    or not isinstance(params, dict)
                    or params.get("threadId") != self._recovery_thread):
                raise ValueError("recovery permits only bound-target stop/read/unsubscribe")
        now = self._clock()
        deadline = min(limit, now + self._request_timeout)
        if now >= deadline:
            raise RpcDeadline(phase)
        self._sequence += 1
        request_id = f"{self._prefix}:{self._sequence}"
        try:
            self._send({"id": request_id, "method": method, "params": params})
            while True:
                if self._clock() >= deadline:
                    raise RpcDeadline(phase, request_id)
                event = self._receive(deadline)
                matches = (isinstance(event, dict) and "method" not in event
                           and event.get("id") == request_id)
                if not matches:
                    self._on_event(event)
                if self._clock() >= deadline:
                    raise RpcDeadline(phase, request_id, event if matches else None)
                if not matches:
                    continue
                if ("result" in event) == ("error" in event):
                    raise ValueError("native RPC response must contain result or error")
                if "error" in event:
                    raise RpcRemoteError(request_id, event)
                return event["result"]
        except RpcDeadline:
            raise
        except TimeoutError as error:
            raise RpcDeadline(phase, request_id) from error
