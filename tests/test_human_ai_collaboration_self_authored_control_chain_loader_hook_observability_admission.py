from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_self_authored_control_chain_loader_hook_observability_admission import (
    ADMISSION_PATH,
    ROOT,
    validate_admission,
)


class SelfAuthoredControlChainLoaderHookObservabilityAdmissionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / ADMISSION_PATH).read_text(encoding="utf-8")
        )

    def test_current_admission_is_valid(self) -> None:
        validate_admission(self.document, root=ROOT)

    def test_rejects_loader_event_overclaim(self) -> None:
        document = copy.deepcopy(self.document)
        document["admissionAssessment"][
            "independentScenarioRelevantSkillLoaderEventAvailable"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_admission(document, root=ROOT)

    def test_rejects_candidate_failure_conflation(self) -> None:
        document = copy.deepcopy(self.document)
        document["classification"]["candidateFailure"] = True
        with self.assertRaisesRegex(RuntimeError, "classification"):
            validate_admission(document, root=ROOT)

    def test_rejects_model_dispatch_credit(self) -> None:
        document = copy.deepcopy(self.document)
        document["admissionAssessment"]["modelDispatchCount"] = 1
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            validate_admission(document, root=ROOT)

    def test_rejects_protocol_amendment_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"][
            "protocolAcceptanceAmendmentAuthorized"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "authority"):
            validate_admission(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
