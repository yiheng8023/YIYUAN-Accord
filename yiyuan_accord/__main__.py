import argparse
import json
from pathlib import Path

from .control import host_check, verify_product


def _emit(report, as_json):
    print(json.dumps(report, ensure_ascii=False, sort_keys=True,
                     indent=None if as_json else 2))


def main():
    parser = argparse.ArgumentParser(prog="python -m yiyuan_accord")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("verify", "host-check"):
        child = subparsers.add_parser(command)
        child.add_argument("--root", type=Path, default=Path.cwd())
        child.add_argument("--json", action="store_true")
        if command == "host-check":
            child.add_argument("--adapter", required=True)

    args = parser.parse_args()
    report = (host_check(args.root, args.adapter) if args.command == "host-check"
              else verify_product(args.root))
    _emit(report, args.json)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
