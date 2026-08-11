#!/usr/bin/env python3
"""Verify the current Agent Autonomy Harness product control contract."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.control import verify_product  # noqa: E402


def main() -> int:
    report = verify_product(ROOT)
    if "--json" in sys.argv:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    elif report["valid"]:
        print(
            f"Agent Autonomy Harness {report['release']} product control PASS: "
            f"{report['outcomes']['verified']}/{report['outcomes']['total']} outcomes, "
            f"{report['guardrails']['passed']}/{report['guardrails']['total']} guardrails."
        )
    else:
        for error in report["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
