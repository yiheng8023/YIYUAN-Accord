import copy
import json
from pathlib import Path
import unittest

from scripts.validate_process_fidelity_chained_transform_trial_protocol_v2_amendment import (
    AMENDMENT_PATH,
    validate_amendment,
)


ROOT = Path(__file__).resolve().parent.parent


class ProcessFidelityChainedTransformProtocolV2AmendmentTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / AMENDMENT_PATH).read_text(encoding="utf-8")
        )

    def test_current_amendment_is_valid(self) -> None:
        validate_amendment(self.document, root=ROOT)

    def test_unconditional_source_exposure_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["recoveryGateAmendment"][
            "sourceAnchorPayloadExposurePolicy"
        ] = "always"
        with self.assertRaisesRegex(RuntimeError, "recovery gate"):
            validate_amendment(mutated, root=ROOT)

    def test_downstream_after_invalid_detection_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["recoveryGateAmendment"][
            "invalidDetectionDisposition"
        ] = "continue"
        with self.assertRaisesRegex(RuntimeError, "recovery gate"):
            validate_amendment(mutated, root=ROOT)

    def test_live_dispatch_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"]["liveDispatchAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "execution boundary"):
            validate_amendment(mutated, root=ROOT)

    def test_claim_promotion_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["claimBoundary"]["formalCohortStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_amendment(mutated, root=ROOT)


if __name__ == "__main__":
    unittest.main()
