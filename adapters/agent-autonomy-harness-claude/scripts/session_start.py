"""Root-bounded launcher for the Claude Code SessionStart projection.

Claude Code adds plain stdout from SessionStart command hooks to model context.
The launcher therefore prints only the bounded common projection, and remains
silent for malformed, unsupported, out-of-root, or runtime-drift inputs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any


AUTHORITY_PATHS = (
    "product/constitution.json",
    "product/program.json",
    "product/acceptance.json",
)
PINNED_RUNTIME_SHA256 = {
    "harness/control.py": "643e699398c303928b3612745d5f37f8dacfcad560696a61931fb6c3e5317307",
    "harness/continuation.py": "0e06d261b2ebf4e720c7d75db5d2a595ec9b7ed97aee392a0940fa7f7db27fc8",
    "harness/claude_reference.py": "9d70662c5bc33fe0f16a28b7da95123f4277d62933cedfb0caccd5ac147cab2a",
}
FORWARDED_FIELDS = ("hook_event_name", "source", "cwd")
MAX_INPUT_CHARACTERS = 65_536
MAX_RUNTIME_BYTES = 1_048_576


def find_harness_root(cwd: Any) -> Path | None:
    if not isinstance(cwd, str) or not cwd.strip():
        return None
    try:
        current = Path(cwd).resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not current.is_dir():
        return None
    for candidate in (current, *current.parents):
        required = (*AUTHORITY_PATHS, *PINNED_RUNTIME_SHA256)
        if all((candidate / relative).is_file() for relative in required):
            return candidate
    return None


def _read_reviewed_runtime(root: Path) -> dict[str, bytes] | None:
    sources: dict[str, bytes] = {}
    try:
        for relative in PINNED_RUNTIME_SHA256:
            with (root / relative).open("rb") as stream:
                source = stream.read(MAX_RUNTIME_BYTES + 1)
            if len(source) > MAX_RUNTIME_BYTES:
                return None
            sources[relative] = source
    except OSError:
        return None
    if not all(
        hashlib.sha256(sources[relative]).hexdigest() == expected
        for relative, expected in PINNED_RUNTIME_SHA256.items()
    ):
        return None
    return sources


def _load_module(name: str, path: Path, source: bytes) -> ModuleType:
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = name.rpartition(".")[0]
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def _load_reference_module(root: Path, sources: dict[str, bytes]) -> ModuleType:
    package_name = "_agent_autonomy_harness_claude_plugin_runtime"
    package = ModuleType(package_name)
    package.__path__ = [str(root / "harness")]  # type: ignore[attr-defined]
    package.__package__ = package_name
    sys.modules[package_name] = package
    for module in ("control", "continuation"):
        _load_module(
            f"{package_name}.{module}",
            root / f"harness/{module}.py",
            sources[f"harness/{module}.py"],
        )
    return _load_module(
        f"{package_name}.claude_reference",
        root / "harness/claude_reference.py",
        sources["harness/claude_reference.py"],
    )


def run_projection(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    root = find_harness_root(payload.get("cwd"))
    if root is None:
        return None
    sources = _read_reviewed_runtime(root)
    if sources is None:
        return None
    forwarded = {field: payload.get(field) for field in FORWARDED_FIELDS}
    try:
        reference = _load_reference_module(root, sources)
        output = reference.render_session_start_context(root, forwarded)
    except Exception:
        return None
    return output if isinstance(output, str) and output else None


def main() -> int:
    try:
        raw = sys.stdin.read(MAX_INPUT_CHARACTERS + 1)
        payload = json.loads(raw) if len(raw) <= MAX_INPUT_CHARACTERS else None
    except (json.JSONDecodeError, OSError, RecursionError, UnicodeError):
        payload = None
    output = run_projection(payload)
    if output is not None:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
