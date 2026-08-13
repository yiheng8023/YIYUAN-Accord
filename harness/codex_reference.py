"""Thin, stateless Codex reference-host projection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .continuation import render_continuation_context


ADAPTER_ID = "harness-codex-session-start-v0.2-candidate.1"
CODEX_ENTRY_SUBSTRATE = {
    "source": "https://github.com/openai/codex/tree/be6e8eac029b183056b7e4402879f15d2c85f61b",
    "package": "@openai/codex",
    "version": "0.147.0",
    "license": "Apache-2.0",
    "maturity": "non-prerelease reference-host package with native SessionStart hooks",
    "reuseBoundary": (
        "SessionStart input and additionalContext output only; no prompt or transcript "
        "content access, session store, lifecycle receipt, result validation, or Hook activation"
    ),
}


def render_session_start_context(root: Path, payload: Any) -> str | None:
    """Translate a native Codex SessionStart envelope to common context."""

    return render_continuation_context(
        root,
        payload,
        adapter_id=ADAPTER_ID,
        host_substrate=CODEX_ENTRY_SUBSTRATE,
    )


def session_start_hook_output(root: Path, payload: Any) -> dict[str, Any]:
    """Return a schema-compatible, non-blocking Codex Hook output."""

    context = render_session_start_context(root, payload)
    output: dict[str, Any] = {"continue": True, "suppressOutput": True}
    if context is not None:
        output["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    return output
