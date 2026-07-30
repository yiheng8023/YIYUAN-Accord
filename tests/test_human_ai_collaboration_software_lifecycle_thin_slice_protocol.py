from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

from scripts.validate_human_ai_collaboration_software_lifecycle_thin_slice_protocol import (
    PROTOCOL_PATH,
    validate_protocol,
)


class SoftwareLifecycleThinSliceProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )

    def test_protocol_passes(self) -> None:
        validate_protocol(deepcopy(self.document), root=ROOT)

    def test_missing_claim_boundary_key_fails_closed(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"].pop("provesLosslessEndToEndProcess")
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_protocol(document, root=ROOT)

    def test_duplicate_or_reordered_stage_fails_closed(self) -> None:
        document = deepcopy(self.document)
        document["stages"][3] = deepcopy(document["stages"][2])
        with self.assertRaisesRegex(RuntimeError, "stage identity"):
            validate_protocol(document, root=ROOT)

    def test_schema_hash_drift_fails_closed(self) -> None:
        document = deepcopy(self.document)
        document["contractBindings"]["stageEnvelopeSchema"][
            "fileSha256"
        ] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "schema hash"):
            validate_protocol(document, root=ROOT)

    def test_permissive_nested_object_schema_fails_closed(self) -> None:
        document = deepcopy(self.document)
        schema_path = (
            ROOT
            / document["contractBindings"]["stageEnvelopeSchema"]["path"]
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["properties"]["protocolBinding"]["additionalProperties"] = True
        schemas = {
            "stageEnvelopeSchema": schema,
            "acceptedInvariantLedgerSchema": json.loads(
                (
                    ROOT
                    / document["contractBindings"][
                        "acceptedInvariantLedgerSchema"
                    ]["path"]
                ).read_text(encoding="utf-8")
            ),
            "humanAuthorityReceiptSchema": json.loads(
                (
                    ROOT
                    / document["contractBindings"][
                        "humanAuthorityReceiptSchema"
                    ]["path"]
                ).read_text(encoding="utf-8")
            ),
        }
        with self.assertRaisesRegex(RuntimeError, "not closed"):
            validate_protocol(document, root=ROOT, schemas=schemas)

    def test_authority_inheritance_or_self_issue_fails_closed(self) -> None:
        document = deepcopy(self.document)
        document["authorityReceiptRules"][
            "noGateAuthorityInheritance"
        ] = False
        document["authorityReceiptRules"][
            "agentSelfIssuedReceiptAccepted"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "receipt rules"):
            validate_protocol(document, root=ROOT)

    def test_live_or_external_authority_promotion_fails_closed(self) -> None:
        document = deepcopy(self.document)
        document["authorityBoundary"]["liveAgentRunAuthorizedByThisProtocol"] = (
            True
        )
        with self.assertRaisesRegex(RuntimeError, "authority was promoted"):
            validate_protocol(document, root=ROOT)

    def test_weak_agent_route_stays_future_and_exact(self) -> None:
        document = deepcopy(self.document)
        document["executionModes"]["futureNativeWeakAgent"][
            "requestedModel"
        ] = "gpt-5.6-sol"
        with self.assertRaisesRegex(RuntimeError, "weak-Agent future"):
            validate_protocol(document, root=ROOT)

    def test_zero_model_boundary_cannot_impersonate_live_route(self) -> None:
        document = deepcopy(self.document)
        document["executionModes"]["current"]["actualRouteObserved"] = True
        with self.assertRaisesRegex(RuntimeError, "zero-model boundary"):
            validate_protocol(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
