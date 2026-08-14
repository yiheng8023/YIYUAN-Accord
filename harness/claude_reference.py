"""Thin, stateless Claude Code reference-host projection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .continuation import render_continuation_context


ADAPTER_ID = "harness-claude-session-start-v0.2-candidate.2"
CLAUDE_ENTRY_SUBSTRATE = {
    "source": "https://github.com/anthropics/claude-code/tree/1f6015b5d578adf79c8527443328a216d6b6a3f1",
    "package": "@anthropic-ai/claude-code",
    "version": "2.1.232",
    "licenseOrTerms": (
        "Anthropic Commercial Terms and Privacy Policy referenced by the "
        "@anthropic-ai/claude-code 2.1.232 package README.md"
    ),
    "maturity": "released distinct-host runtime with native SessionStart hooks",
    "reuseBoundary": (
        "SessionStart input and plain-stdout context output through session-scoped "
        "--plugin-dir only; no prompt or transcript content access, session store, "
        "lifecycle receipt, result validation, persistent installation, or Hook activation"
    ),
}


def render_session_start_context(root: Path, payload: Any) -> str | None:
    """Translate a native Claude Code SessionStart envelope to common context."""

    return render_continuation_context(
        root,
        payload,
        adapter_id=ADAPTER_ID,
        host_substrate=CLAUDE_ENTRY_SUBSTRATE,
    )
