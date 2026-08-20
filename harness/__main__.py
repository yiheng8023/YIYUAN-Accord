from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .control import host_check, verify_product


def _emit(report: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return
    if "adapter" in report:
        print(
            f"{report['adapter']}: "
            f"{'static-ready' if report['valid'] else 'invalid'}, "
            f"behavior={report['behaviorEvidenceState']}"
        )
    else:
        print(
            f"{report['productId']} {report['release']}: "
            f"contract={'valid' if report['valid'] else 'invalid'}, "
            f"release={report['completionState']}"
        )
    for error in report["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, default=Path.cwd())
    verify_parser.add_argument("--json", action="store_true")

    host_parser = subparsers.add_parser("host-check")
    host_parser.add_argument("--root", type=Path, default=Path.cwd())
    host_parser.add_argument("--adapter", required=True)
    host_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "host-check":
        report = host_check(args.root, args.adapter)
    else:
        report = verify_product(args.root)
    _emit(report, args.json)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
