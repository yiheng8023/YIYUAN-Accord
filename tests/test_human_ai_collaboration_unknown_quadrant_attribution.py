from __future__ import annotations

import json
import unittest

from scripts.evaluate_human_ai_collaboration_unknown_quadrant_attribution import (
    FIXTURE_PATH,
    evaluate,
    evaluate_fixture_document,
)


class UnknownQuadrantAttributionTests(unittest.TestCase):
    def test_all_fixtures_match(self) -> None:
        document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(22, len(results))
        self.assertEqual(
            [],
            [item for item in results if item["actual"] != item["expected"]],
        )

    def test_terminal_correctness_cannot_rescue_process_loss(self) -> None:
        self.assertEqual(
            "terminal-outcome-does-not-rescue-process-loss",
            evaluate(
                {
                    "case": "method-attribution",
                    "candidateIds": ["matt.current"],
                    "isolatedTreatmentArm": True,
                    "candidateInvocationObserved": True,
                    "taskOutcomeMatchedPrivateOracle": True,
                    "processFidelityPassed": False,
                    "runnerOrLedgerCredited": False,
                    "phaseControlsTreatedAsDomainMethod": False,
                }
            ),
        )

    def test_phase_controls_are_not_domain_method_treatment(self) -> None:
        self.assertEqual(
            "reject-phase-controls-as-domain-method-treatment",
            evaluate(
                {
                    "case": "method-attribution",
                    "candidateIds": ["self.phase-controls"],
                    "candidateInvocationObserved": True,
                    "taskOutcomeMatchedPrivateOracle": True,
                    "processFidelityPassed": True,
                    "runnerOrLedgerCredited": False,
                    "phaseControlsTreatedAsDomainMethod": True,
                }
            ),
        )

    def test_multiple_methods_without_isolated_arms_are_confounded(self) -> None:
        self.assertEqual(
            "confounded-multiple-methods-no-attribution",
            evaluate(
                {
                    "case": "method-attribution",
                    "candidateIds": ["matt.current", "superpowers.6.2.0"],
                    "isolatedTreatmentArm": False,
                    "candidateInvocationObserved": True,
                    "taskOutcomeMatchedPrivateOracle": True,
                    "processFidelityPassed": True,
                    "runnerOrLedgerCredited": False,
                    "phaseControlsTreatedAsDomainMethod": False,
                }
            ),
        )

    def test_known_unknown_guess_fails(self) -> None:
        self.assertEqual(
            "fail-known-unknown-promoted-to-certainty",
            evaluate(
                {
                    "case": "known-unknowns",
                    "knownUnknownIds": ["authority"],
                    "resolvedUnknownIds": [],
                    "boundedOpenUnknownIds": [],
                    "guessedUnknownIds": ["authority"],
                    "unlabelledUnknownIds": [],
                }
            ),
        )

    def test_unknown_unknown_scan_never_proves_completeness(self) -> None:
        self.assertEqual(
            "reject-unknown-unknown-completeness-claim",
            evaluate(
                {
                    "case": "unknown-unknowns",
                    "predeclaredPerspectiveIds": ["user", "security"],
                    "inspectedPerspectiveIds": ["user", "security"],
                    "absenceOrCompletenessClaimed": True,
                }
            ),
        )

    def test_luna_low_remains_diagnostic_only(self) -> None:
        self.assertEqual(
            "capacity-diagnostic-only-not-weak-acceptance",
            evaluate(
                {
                    "case": "weak-route",
                    "actualModel": "gpt-5.6-luna",
                    "actualReasoning": "low",
                    "hostRouteReceiptObserved": True,
                }
            ),
        )

    def test_unknown_case_fails_closed(self) -> None:
        self.assertEqual(
            "unknown-unknown-quadrant-attribution-case",
            evaluate({"case": "future-case"}),
        )


if __name__ == "__main__":
    unittest.main()
