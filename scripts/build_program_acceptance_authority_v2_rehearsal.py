from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.program_acceptance_authority_v2 import AcceptanceAuthorityError
from scripts.program_acceptance_authority_v2_rehearsal import run_rehearsal


def _envelope(error: AcceptanceAuthorityError | OSError) -> dict[str, object]:
    if isinstance(error, AcceptanceAuthorityError):
        payload: dict[str, object] = {"status": "error", "code": error.code, "message": str(error)}
        if error.path is not None:
            payload["path"] = error.path
        return payload
    return {"status": "error", "code": "acceptance-rehearsal-output-write-failed", "message": str(error)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output-root")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.output_root is not None:
            result = run_rehearsal(root, Path(args.output_root))
        else:
            with tempfile.TemporaryDirectory(prefix="acceptance-authority-v2-rehearsal-") as parent:
                result = run_rehearsal(root, Path(parent) / "rehearsal")
    except (AcceptanceAuthorityError, OSError) as error:
        print(json.dumps(_envelope(error), ensure_ascii=False, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
