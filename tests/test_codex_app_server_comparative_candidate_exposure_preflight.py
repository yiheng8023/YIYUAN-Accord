from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_codex_app_server_comparative_candidate_exposure_preflight import (
    EVIDENCE_PATH,
    validate_preflight,
)


ROOT = Path(__file__).resolve().parent.parent


class CodexComparativeCandidateExposurePreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_preflight_is_valid(self) -> None:
        validate_preflight(self.document, root=ROOT)

    def test_rejects_superpowers_exposure_overclaim(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"][
            "superpowersTddCandidateSpecificExposureProved"
        ] = True

        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_preflight(document, root=ROOT)

    def test_rejects_failed_attempt_prepost_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["postflightSnapshot"][
            "failedSuperpowersAttemptsHavePerAttemptPrePostProof"
        ] = True

        with self.assertRaisesRegex(RuntimeError, "promoted"):
            validate_preflight(document, root=ROOT)

    def test_rejects_content_rejection(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["superpowersTddContentRejected"] = True

        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_preflight(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
