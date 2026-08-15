"""Root-bounded launcher for the Codex SessionStart reference projection.

The plugin owns only host packaging. The repository-owned adapter and verifier
remain the implementation and product authority. This isolated launcher reads
the Hook envelope, discovers a containing Harness authority root, loads only
the exact reviewed module bytes, forwards only the three fields used by the
adapter, and otherwise returns a non-blocking no-op.
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
    "harness/control.py": "bb45c1f37ce718ec0362a9f12b64f2d556135aabaea5acf7dc164656155189da",
    "harness/continuation.py": "7151a0fdfab1703374fdc42871d4dc7b68f68e1dc175238a577240fa2ae80bb7",
    "harness/codex_reference.py": "15d10628f2e8989d376e5c61adc9bf75cd086e88f8fd6ac25a76bfebc069186b",
}
FORWARDED_FIELDS = ("hook_event_name", "source", "cwd")
NOOP = {"continue": True, "suppressOutput": True}


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
    try:
        sources = {
            relative: (root / relative).read_bytes()
            for relative in PINNED_RUNTIME_SHA256
        }
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
    package_name = "_agent_autonomy_harness_plugin_runtime"
    package = ModuleType(package_name)
    package.__path__ = [str(root / "harness")]  # type: ignore[attr-defined]
    package.__package__ = package_name
    sys.modules[package_name] = package
    _load_module(
        f"{package_name}.control",
        root / "harness/control.py",
        sources["harness/control.py"],
    )
    _load_module(
        f"{package_name}.continuation",
        root / "harness/continuation.py",
        sources["harness/continuation.py"],
    )
    return _load_module(
        f"{package_name}.codex_reference",
        root / "harness/codex_reference.py",
        sources["harness/codex_reference.py"],
    )


def run_projection(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return dict(NOOP)
    root = find_harness_root(payload.get("cwd"))
    if root is None:
        return dict(NOOP)
    sources = _read_reviewed_runtime(root)
    if sources is None:
        return dict(NOOP)
    forwarded = {field: payload.get(field) for field in FORWARDED_FIELDS}
    try:
        reference = _load_reference_module(root, sources)
        output = reference.session_start_hook_output(root, forwarded)
    except Exception:
        return dict(NOOP)
    if not isinstance(output, dict) or output.get("continue") is not True:
        return dict(NOOP)
    return output


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, UnicodeError):
        payload = None
    print(json.dumps(run_projection(payload), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
