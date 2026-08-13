"""Agent Autonomy Harness contract verifier and thin reference adapters."""

from .claude_reference import (
    render_session_start_context as render_claude_session_start_context,
)
from .codex_reference import (
    render_session_start_context as render_codex_session_start_context,
    session_start_hook_output as codex_session_start_hook_output,
)
from .control import verify_product

# Backward-compatible Codex aliases retained for the first reference host.
render_session_start_context = render_codex_session_start_context
session_start_hook_output = codex_session_start_hook_output

__all__ = [
    "codex_session_start_hook_output",
    "render_claude_session_start_context",
    "render_codex_session_start_context",
    "render_session_start_context",
    "session_start_hook_output",
    "verify_product",
]
