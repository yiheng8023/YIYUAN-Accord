"""Passive lifecycle observations for caller-owned Codex App Server operations.

Create a fresh watch per request. Feed only new, ordered notifications from the
bound connection, including events interleaved with its RPC acknowledgement.
For manual compaction, first quiesce unrelated work on that thread: the RPC has
no operation ID, so the next compaction start supplies the identity. This cannot
authenticate transport ownership or infer missing events.

There is no dispatch, callback, file access, path, model or budget selection.
Keep paths and limits explicitly on the caller's own run instance. Retain raw
evidence separately; protocol completion is not semantic acceptance, authority,
restoration or permission to release a source.
"""
from dataclasses import dataclass
from typing import Optional


def _identity(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("nonempty native identity required")
    return value


@dataclass(frozen=True)
class TurnObservation:
    thread_id: str
    turn_id: Optional[str]
    compaction_item_id: Optional[str]
    compaction_completed: bool
    terminal_status: Optional[str]
    final_answer_id: Optional[str]
    invalid_reason: Optional[str]
    finished: bool
    protocol_complete: bool


class NativeTurnWatch:
    """Bounded metadata for one user turn or one idle-thread manual compaction.

    Views are immutable and contain no transcript text. User turns need an
    observed nonempty final answer as well as a successful terminal; compaction
    needs its own start/item-completion/terminal chain. After identity is bound,
    a terminal failure ends the watch without success. Failure before any
    compaction item starts remains unbound; use the caller's RPC error/deadline
    and scoped recovery, never guess an interrupt target. Missing events never
    imply success. Raw messages still require independent semantic review.
    """
    def __init__(self, thread_id, turn_id=None, *, compaction=False):
        if type(compaction) is not bool:
            raise ValueError("explicit compaction mode required")
        self._thread = _identity(thread_id)
        if compaction and turn_id is not None:
            raise ValueError("manual compaction must discover its own turn")
        self._turn = None if compaction else _identity(turn_id)
        self._compaction = compaction
        self._item = self._status = self._answer = self._invalid = None
        self._item_completed = False

    @classmethod
    def for_turn(cls, thread_id, turn_id):
        return cls(thread_id, turn_id)

    @classmethod
    def for_compaction(cls, thread_id):
        return cls(thread_id, compaction=True)

    @property
    def view(self):
        success = (self._status == "completed" and
                   (self._item_completed if self._compaction else self._answer is not None))
        finished = (self._invalid is not None or self._status is not None and
                    (not self._compaction or self._status != "completed" or self._item_completed))
        return TurnObservation(self._thread, self._turn, self._item, self._item_completed,
                               self._status, self._answer, self._invalid, bool(finished),
                               bool(success and self._invalid is None))

    def observe(self, event):
        if self._invalid is not None:
            raise ValueError("invalid observer; bind a fresh watch after reconciliation")
        try:
            self._observe(event)
        except ValueError as error:
            self._invalid = str(error)
            raise
        return self.view

    def _observe(self, event):
        if not isinstance(event, dict):
            raise ValueError("native notification object required")
        method = event.get("method")
        if method is not None and "id" in event:
            raise ValueError("server requests require explicit caller handling")
        if method not in ("turn/completed", "item/started", "item/completed"):
            return
        params = event.get("params")
        if not isinstance(params, dict):
            raise ValueError("native notification params required")
        if _identity(params.get("threadId")) != self._thread:
            return
        if method == "turn/completed":
            turn = params.get("turn")
            if not isinstance(turn, dict):
                raise ValueError("native terminal turn object required")
            turn_id = _identity(turn.get("id"))
            if turn_id != self._turn:
                return
            status = _identity(turn.get("status"))
            if self._status is not None and status != self._status:
                raise ValueError("conflicting native terminal status")
            if not self._compaction:
                items = turn.get("items", [])
                if not isinstance(items, list):
                    raise ValueError("native terminal items must be a list")
                for item in items:
                    if not isinstance(item, dict):
                        raise ValueError("native terminal item object required")
                    self._observe_answer(item)
            self._status = status
            return
        item = params.get("item")
        if not isinstance(item, dict):
            raise ValueError("native item object required")
        if self._compaction and item.get("type") == "contextCompaction":
            turn_id, item_id = _identity(params.get("turnId")), _identity(item.get("id"))
            if method == "item/started":
                if self._item is not None and (turn_id, item_id) != (self._turn, self._item):
                    raise ValueError("ambiguous native compaction start")
                self._turn, self._item = turn_id, item_id
            elif (turn_id, item_id) == (self._turn, self._item):
                self._item_completed = True
        elif (not self._compaction and method == "item/completed" and
              item.get("type") == "agentMessage" and item.get("phase") == "final_answer"):
            if _identity(params.get("turnId")) != self._turn:
                return
            self._observe_answer(item)

    def _observe_answer(self, item):
        if item.get("type") == "agentMessage" and item.get("phase") == "final_answer":
            text = item.get("text")
            if not isinstance(text, str):
                raise ValueError("native final answer text required")
            if text.strip():
                self._answer = _identity(item.get("id"))
