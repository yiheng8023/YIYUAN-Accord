from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.program_acceptance_authority_v2 import AcceptanceAuthorityError
from scripts.program_acceptance_authority_v2_rehearsal import validate_repository_record


def main() -> int:
    try:
        result = validate_repository_record(Path(".").resolve())
    except AcceptanceAuthorityError as error:
        print(json.dumps({"status": "error", "code": error.code, "message": str(error)}, sort_keys=True, separators=(",", ":")), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
