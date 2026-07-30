from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_context_pressure_evidence_envelope import (
    evaluate_fixture_document,
    expected_binding,
    validate_context_pressure_evidence_envelope,
)

FIXTURE = Path(__file__).parent / "fixtures" / "context-pressure-provenance-evidence-envelope-2026-07-24.json"


class ContextPressureEvidenceEnvelopeTests(unittest.TestCase):
    def test_positive_and_negative_fixtures(self) -> None:
        document = json.loads(FIXTURE.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(11, len(results))
        for result in results:
            with self.subTest(case=result["id"]):
                self.assertEqual(result["expectedStatus"], result["actualStatus"])
                self.assertEqual(
                    result["expectedFailureCodes"],
                    result["actualFailureCodes"],
                )

    def test_valid_record_never_promotes_broad_claims(self) -> None:
        envelope = json.loads(FIXTURE.read_text(encoding="utf-8"))["baseEnvelope"]
        result = validate_context_pressure_evidence_envelope(
            envelope,
            expected_binding(envelope),
        )
        self.assertEqual("advisory-evidence-ready-offline-only", result["status"])
        self.assertTrue(all(value is False for value in result["claimBoundary"].values()))
        self.assertNotIn("observedValue", result)
        self.assertNotIn("evidenceArtifact", result)


if __name__ == "__main__":
    unittest.main()
