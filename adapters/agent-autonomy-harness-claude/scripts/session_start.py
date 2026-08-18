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
    "harness/task_validator_o1_lifecycle_suite.py": "a9e0d8e74705fd4c7b606c9ace0d3dd0caddce8a44525d86ffb6908ffa96f25a",
    "harness/task_capture_o2_codex_reference.py": "3ff9248b637e01f055919ad8d6ca1def0517fc8376c50f3aa76957399271d2bc",
    "harness/task_validator_o2_codex_reference.py": "a75b96e16f20ba87e3f76830f052cde5e65e06763ea68124a4dd8917e40d726e",
    "harness/task_validator_o2_codex_reference_permission_profile.py": "f5825805521aa9279882d1505e09bc61ba3e0cc2caa50d3b856b34e2ee1a809f",
    "harness/task_validator_o4_continuous_self_correction.py": "7d2264c29b561a402493e3c509d8e4e2a66dcbb10a5ebbc70f1d158feb87ec2d",
    "harness/control.py": "2ca5b676f4e79719ee0ff41864a578cef8c6db4586ae246055a25e0b0dbc0580",
    "harness/continuation.py": "6e780c3d5a12397e4ba9f82aac66f79386b6dadf06d46320add3ecfd07b73f66",
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
    for module in (
        "task_validator_o1_lifecycle_suite",
        "task_capture_o2_codex_reference",
        "task_validator_o2_codex_reference",
        "task_validator_o2_codex_reference_permission_profile",
        "task_validator_o4_continuous_self_correction",
        "control",
        "continuation",
    ):
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
