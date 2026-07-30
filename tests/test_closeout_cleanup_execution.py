from __future__ import annotations

import copy
import json
import unittest

from scripts.inventory_closeout_cleanup_debt import canonical_sha256
from scripts.validate_closeout_cleanup_execution import (
    RECORD_PATH,
    ROOT,
    validate_execution,
)


class CloseoutCleanupExecutionTests(unittest.TestCase):
    def test_repository_cleanup_execution_is_current(self) -> None:
        document = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))
        validate_execution(document, root=ROOT)
        self.assertEqual(
            "repository-local-temporary-debt-cleaned-stage-checkpoint",
            document["status"],
        )
        self.assertEqual(35, document["cleanupExecution"]["targetCount"])
        self.assertFalse((ROOT / ".tmp").exists())

    def test_digest_and_scope_promotions_fail_closed(self) -> None:
        document = json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))
        promoted = copy.deepcopy(document)
        promoted["claimBoundary"]["programCloseoutProved"] = True
        promoted["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in promoted.items()
                if key != "reportSha256"
            }
        )
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_execution(promoted, root=ROOT)

if __name__ == "__main__":
    unittest.main()
