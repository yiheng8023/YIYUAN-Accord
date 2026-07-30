from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_maintenance_migration_protocol import (
    PROTOCOL_PATH,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


class MaintenanceMigrationProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_protocol(document or self.document, root=ROOT)

    def test_current_protocol_is_valid(self) -> None:
        self.validate()

    def test_rejects_live_run_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveExecutionStarted"] = False
        with self.assertRaisesRegex(RuntimeError, "decision overclaimed"):
            self.validate(document)

    def test_rejects_upstream_local_equality_conflation(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidatePins"][0]["upstreamCrossCheck"][
            "localEqualsUpstreamPinnedBlob"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "upstream/adaptation"):
            self.validate(document)

    def test_rejects_adaptation_review_completion_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionGate"][
            "candidateAdaptationDiffReviewCompleted"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "review completion"):
            self.validate(document)

    def test_rejects_private_oracle_completion_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionGate"]["privateOracleImplemented"] = False
        with self.assertRaisesRegex(RuntimeError, "implementation gate"):
            self.validate(document)

    def test_rejects_selected_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionGate"][
            "candidateSpecificSelectedExposureProved"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "preflight gate"):
            self.validate(document)

    def test_rejects_security_vendoring_route(self) -> None:
        document = copy.deepcopy(self.document)
        security = next(
            item
            for item in document["candidatePins"]
            if item["id"] == "official.codex-security.finding-discovery"
        )
        security["suitability"] = "project-source-pinned-copy"
        with self.assertRaisesRegex(RuntimeError, "Security deferral"):
            self.validate(document)

    def test_rejects_unknown_consumer_erasure(self) -> None:
        document = copy.deepcopy(self.document)
        opaque = next(
            item
            for item in document["fixtureDesign"]["affectedConsumerModel"]
            if item["id"] == "consumer.opaque-batch"
        )
        opaque["state"] = "inactive"
        with self.assertRaisesRegex(RuntimeError, "consumer model"):
            self.validate(document)

    def test_rejects_invalid_run_counting(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionGate"]["invalidEnvironmentOrMeasurementRunsCount"] = 4
        with self.assertRaisesRegex(RuntimeError, "repetition boundary"):
            self.validate(document)

    def test_rejects_removal_readiness_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["provesRemovalReadiness"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
