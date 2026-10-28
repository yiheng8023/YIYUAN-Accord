import argparse
import json
import sys
from pathlib import Path

from .control import host_check, verify_product
from .development import verify_development


def _emit(report, as_json):
    print(json.dumps(report, ensure_ascii=False, sort_keys=True,
                     indent=None if as_json else 2))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="python -m yiyuan_accord",
        description=("Maintainer source and admission checks for YIYUAN Accord. "
                     "A successful check does not by itself establish live host "
                     "behavior, release authorization or product value."))
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands = {
        "verify": "Check product sources, preserved predecessor integrity and applicable admission records.",
        "host-check": "Check an adapter declaration for static consistency; does not start or qualify a live host.",
        "verify-development": "Check the current development contract and its machine projections.",
    }
    for command, description in commands.items():
        child = subparsers.add_parser(command, help=description, description=description)
        child.add_argument("--root", type=Path, default=Path.cwd(),
                           help="Repository directory (default: current directory).")
        child.add_argument("--json", action="store_true",
                           help="Emit compact single-line JSON instead of indented JSON.")
        if command == "host-check":
            child.add_argument("--adapter", required=True,
                               help="Adapter declaration ID, for example codex.")

    args = parser.parse_args()
    if args.command == "host-check":
        report = host_check(args.root, args.adapter)
    elif args.command == "verify-development":
        report = verify_development(args.root)
    else:
        report = verify_product(args.root)
    _emit(report, args.json)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
