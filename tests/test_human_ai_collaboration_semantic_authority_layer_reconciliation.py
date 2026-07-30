from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_human_ai_collaboration_semantic_authority_layer_reconciliation import (
    EVIDENCE_PATH,
    ROOT,
    validate_reconciliation,
)


class SemanticAuthorityLayerReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_reconciliation_passes(self) -> None:
        validate_reconciliation(deepcopy(self.document), root=ROOT)

    def test_rejects_monolith_current_upstream_claim(self) -> None:
        document = deepcopy(self.document)
        document["currentLocalCcObservation"][
            "localPayloadEqualsCurrentUpstream"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "local CC boundary"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_universal_grilling(self) -> None:
        document = deepcopy(self.document)
        document["routingBoundary"]["mandatoryForEveryCodeTask"] = True
        with self.assertRaisesRegex(RuntimeError, "routing boundary"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_hard_standard_replacement(self) -> None:
        document = deepcopy(self.document)
        document["semanticAuthorityPlane"][
            "hardStandardsRemainIndependentAndMandatory"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "plane drifted"):
            validate_reconciliation(document, root=ROOT)

    def test_rejects_value_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["tokenReductionMeasured"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_reconciliation(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
