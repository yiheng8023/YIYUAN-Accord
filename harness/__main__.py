from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .codex_reference import session_start_hook_output
from .control import (
    expire_current_initial_authorization_private_evidence,
    verify_product,
)

MAX_HOOK_INPUT_CHARACTERS = 65_536


def _bounded_hook_payload() -> object | None:
    try:
        raw = sys.stdin.read(MAX_HOOK_INPUT_CHARACTERS + 1)
        if len(raw) > MAX_HOOK_INPUT_CHARACTERS:
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, OSError, RecursionError, UnicodeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, default=Path.cwd())
    verify_parser.add_argument("--json", action="store_true")
    codex_parser = subparsers.add_parser("codex-session-start")
    codex_parser.add_argument("--root", type=Path, default=Path.cwd())
    expiry_parser = subparsers.add_parser(
        "expire-current-cohort-private-evidence"
    )
    expiry_parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    if args.command == "codex-session-start":
        payload = _bounded_hook_payload()
        print(
            json.dumps(
                session_start_hook_output(args.root, payload),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

    if args.command == "expire-current-cohort-private-evidence":
        errors: list[str] = []
        if expire_current_initial_authorization_private_evidence(
            args.root,
            errors,
        ):
            print("current v1.1 cohort private evidence expiry cleanup verified")
            return 0
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return (
            4
            if errors
            == ["current v1.1 binding authorization expiry cleanup is not due"]
            else 3
        )

    report = verify_product(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"{report['productId']} {report['release']}: "
            f"{report['programStatus']}, {report['completionState']} "
            f"({report['outcomes']['verified']}/{report['outcomes']['total']} outcomes)"
        )
        for error in report["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
