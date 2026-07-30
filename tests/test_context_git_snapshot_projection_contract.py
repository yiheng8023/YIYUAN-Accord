from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_context_git_snapshot_projection_contract import (
    REGISTRY_PATH,
    ROOT,
    validate_contract,
)


class ContextGitSnapshotProjectionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / REGISTRY_PATH).read_text(encoding="utf-8")
        )

    def test_current_contract_passes(self) -> None:
        validate_contract(self.document)

    def test_input_hash_drift_fails_closed(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["inputs"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "input drifted"):
            validate_contract(changed)

    def test_no_upstream_invention_fails_closed(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["projectionContract"][
            "noUpstreamInventsOriginMainOrZeroZero"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "contract drifted"):
            validate_contract(changed)

    def test_claim_promotion_fails_closed(self) -> None:
        changed = copy.deepcopy(self.document)
        changed["claimBoundary"]["automaticThreadCreationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            validate_contract(changed)

    def test_new_thread_or_controller_promotion_fails_closed(self) -> None:
        for key in (
            "newThreadOrModelRunStarted",
            "selfAuthoredRuntimeControllerJustified",
        ):
            with self.subTest(key=key):
                changed = copy.deepcopy(self.document)
                changed["decision"][key] = True
                with self.assertRaisesRegex(
                    RuntimeError,
                    "decision drifted",
                ):
                    validate_contract(changed)


if __name__ == "__main__":
    unittest.main()
