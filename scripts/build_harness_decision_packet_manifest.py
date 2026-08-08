#!/usr/bin/env python3
"""Emit or atomically persist the thirteen-scenario decision manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.harness_decision_packet import ROOT
from scripts.harness_decision_packet_manifest import (
    BatchBindingError,
    build_decision_packet_manifest,
    serialize_decision_packet_manifest,
    write_manifest_atomically,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = build_decision_packet_manifest(args.root)
        data = serialize_decision_packet_manifest(manifest)
        if args.output is not None:
            write_manifest_atomically(args.output, data)
    except BatchBindingError as error:
        sys.stderr.buffer.write(
            json.dumps(
                error.as_dict(), ensure_ascii=False, sort_keys=True
            ).encode("utf-8")
            + b"\n"
        )
        return 2
    except OSError as error:
        envelope = {
            "status": "error",
            "code": "output-write-failed",
            "message": str(error),
        }
        sys.stderr.buffer.write(
            json.dumps(envelope, ensure_ascii=False, sort_keys=True).encode("utf-8")
            + b"\n"
        )
        return 2
    if args.output is None:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
