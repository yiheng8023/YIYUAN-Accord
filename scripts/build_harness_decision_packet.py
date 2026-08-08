#!/usr/bin/env python3
"""Emit a source-bound Harness decision packet to stdout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from harness_decision_packet import (
    DecisionPacketError,
    ROOT,
    build_decision_packet,
    serialize_decision_packet,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        packet = build_decision_packet(args.root, request)
    except (DecisionPacketError, OSError, json.JSONDecodeError) as exc:
        error = (
            exc.as_dict()
            if isinstance(exc, DecisionPacketError)
            else {
                "status": "error",
                "code": "request-read-failed",
                "message": str(exc),
            }
        )
        sys.stderr.buffer.write(
            json.dumps(error, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
        )
        return 2
    sys.stdout.buffer.write(serialize_decision_packet(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
