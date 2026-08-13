from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .codex_reference import session_start_hook_output
from .control import verify_product


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, default=Path.cwd())
    verify_parser.add_argument("--json", action="store_true")
    codex_parser = subparsers.add_parser("codex-session-start")
    codex_parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    if args.command == "codex-session-start":
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, OSError, UnicodeError):
            payload = None
        print(
            json.dumps(
                session_start_hook_output(args.root, payload),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0

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
