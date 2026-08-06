from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.evaluate_repository_authored_gap_fill_candidate import (
    GATE_PATH,
    evaluate_candidate,
    validate_gate_record,
    validate_repository_gate,
)


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_ID = "evidence.repository-authored-gap-fill-gate-2026-08-06"


def complete_synthetic_candidate() -> dict:
    return {
        "id": "synthetic-gap-fill-candidate",
        "originClass": "repository-authored-gap-fill-candidate",
        "incumbentExemptionRequested": False,
        "residualGap": {
            "status": "supported",
            "demandCoordinateId": "synthetic-demand-coordinate",
            "reproductionEvidenceIds": ["synthetic-reproduction-evidence"],
        },
        "alternatives": {
            route: {
                "status": "exhausted-with-evidence",
                "evidenceIds": [f"synthetic-{route}-evidence"],
            }
            for route in (
                "native-runtime",
                "official-runtime",
                "task-bound-targeted-discovery",
                "reviewed-maintained-external",
                "composition",
                "non-skill-harness",
                "project-standard",
                "human-control",
            )
        },
        "designProvenance": {
            "repositoryOwned": True,
            "rationale": "synthetic validator fixture only",
            "evidenceIds": ["synthetic-design-evidence"],
        },
        "licenseOwnership": {
            "confirmed": True,
            "licenseId": "LicenseRef-Synthetic",
        },
        "reviews": {
            name: {"status": "passed", "evidenceIds": [f"synthetic-{name}-evidence"]}
            for name in ("security", "portability", "overlap")
        },
        "tests": {
            "status": "passed",
            "evidenceIds": ["synthetic-test-evidence"],
        },
        "ownerApproval": {
            "status": "approved",
            "receiptId": "synthetic-owner-approval",
        },
    }


class RepositoryAuthoredGapFillGateTests(unittest.TestCase):
    def test_gate_record_binds_human_readable_documentation(self) -> None:
        record = json.loads((ROOT / GATE_PATH).read_text(encoding="utf-8"))

        self.assertEqual(
            "docs/strategy/REPOSITORY-AUTHORED-GAP-FILL-GATE-2026-08-06.md",
            record["documentation"],
        )
        self.assertTrue((ROOT / record["documentation"]).is_file())

    def test_gate_validator_rejects_acceptance_downgrade(self) -> None:
        load = lambda path: json.loads((ROOT / path).read_text(encoding="utf-8"))
        record = load("registry/repository-authored-gap-fill-gate-2026-08-06.json")
        acceptance = load("registry/program-acceptance-map.json")
        criterion = next(
            row
            for row in acceptance["acceptanceCriteria"]
            if row["id"] == "acceptance.repository-authored-gap-fill-gate"
        )
        criterion["assessment"] = "planned"

        with self.assertRaisesRegex(RuntimeError, "acceptance"):
            validate_gate_record(
                record,
                program=load("registry/curation-program-plan.json"),
                acceptance=acceptance,
                authority=load("registry/skill-portfolio-current-authority.json"),
                projection=load(
                    "registry/portfolio-tasktime-projection-contract-2026-08-06.json"
                ),
                root=ROOT,
            )

    def test_acceptance_map_verifies_only_the_gate_mechanism(self) -> None:
        acceptance = json.loads(
            (ROOT / "registry/program-acceptance-map.json").read_text(
                encoding="utf-8"
            )
        )
        criteria = {row["id"]: row for row in acceptance["acceptanceCriteria"]}
        evidence = {row["id"]: row for row in acceptance["evidence"]}

        criterion = criteria["acceptance.repository-authored-gap-fill-gate"]
        self.assertEqual("verified", criterion["assessment"])
        self.assertIn(EVIDENCE_ID, criterion["evidenceIds"])
        self.assertEqual(
            "registry/repository-authored-gap-fill-gate-2026-08-06.json",
            evidence[EVIDENCE_ID]["path"],
        )
        self.assertEqual(
            ["acceptance.repository-authored-gap-fill-gate"],
            evidence[EVIDENCE_ID]["supports"],
        )

    def test_repository_gate_contract_is_valid(self) -> None:
        record = validate_repository_gate()

        self.assertEqual("repository-authored-gap-fill-gate-v1", record["id"])
        self.assertEqual("verified-synthetic-gate-mechanism-only", record["status"])
        self.assertEqual(
            "registry/repository-authored-gap-fill-gate-2026-08-06.json",
            str(GATE_PATH).replace("\\", "/"),
        )

    def test_missing_residual_gap_blocks_admission(self) -> None:
        result = evaluate_candidate(
            {
                "id": "synthetic-gap-fill-candidate",
                "originClass": "repository-authored-gap-fill-candidate",
                "residualGap": {"status": "not-supported"},
            }
        )

        self.assertEqual("blocked", result["decision"])
        self.assertIn("residual-gap-not-supported", result["blockers"])
        self.assertFalse(result["executionAuthorized"])

    def test_complete_fixture_is_mechanism_eligible_but_not_executable(self) -> None:
        result = evaluate_candidate(complete_synthetic_candidate())

        self.assertEqual("mechanism-eligible", result["decision"])
        self.assertEqual([], result["blockers"])
        self.assertFalse(result["executionAuthorized"])
        self.assertEqual("synthetic-gate-mechanism-only", result["claimBoundary"])

    def test_each_required_gate_fails_closed(self) -> None:
        mutations: list[tuple[str, dict, str]] = []

        candidate = complete_synthetic_candidate()
        candidate["originClass"] = "third-party-candidate"
        mutations.append(("origin", candidate, "wrong-origin-class"))

        candidate = complete_synthetic_candidate()
        candidate["residualGap"]["reproductionEvidenceIds"] = []
        mutations.append(
            ("residual-evidence", candidate, "residual-gap-evidence-incomplete")
        )

        for route in complete_synthetic_candidate()["alternatives"]:
            candidate = complete_synthetic_candidate()
            candidate["alternatives"][route]["status"] = "viable"
            mutations.append(
                (route, candidate, f"alternative-not-exhausted:{route}")
            )

        scalar_mutations = {
            "design-provenance": (
                ("designProvenance", "repositoryOwned"),
                False,
                "design-provenance-incomplete",
            ),
            "license-ownership": (
                ("licenseOwnership", "confirmed"),
                False,
                "license-ownership-unconfirmed",
            ),
            "security-review": (
                ("reviews", "security", "status"),
                "pending",
                "security-review-incomplete",
            ),
            "portability-review": (
                ("reviews", "portability", "status"),
                "pending",
                "portability-review-incomplete",
            ),
            "overlap-review": (
                ("reviews", "overlap", "status"),
                "pending",
                "overlap-review-incomplete",
            ),
            "tests": (
                ("tests", "status"),
                "pending",
                "tests-incomplete",
            ),
            "owner-approval": (
                ("ownerApproval", "status"),
                "pending",
                "owner-approval-missing",
            ),
        }
        for case_id, (path, value, blocker) in scalar_mutations.items():
            candidate = copy.deepcopy(complete_synthetic_candidate())
            target = candidate
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            mutations.append((case_id, candidate, blocker))

        for case_id, candidate, blocker in mutations:
            with self.subTest(case_id=case_id):
                result = evaluate_candidate(candidate)
                self.assertEqual("blocked", result["decision"])
                self.assertIn(blocker, result["blockers"])
                self.assertFalse(result["executionAuthorized"])

    def test_incumbent_self_authored_carriers_cannot_request_exemption(self) -> None:
        candidate = complete_synthetic_candidate()
        candidate["incumbentExemptionRequested"] = True

        result = evaluate_candidate(candidate)

        self.assertEqual("blocked", result["decision"])
        self.assertIn("incumbent-exemption-forbidden", result["blockers"])
        self.assertFalse(result["executionAuthorized"])


if __name__ == "__main__":
    unittest.main()
