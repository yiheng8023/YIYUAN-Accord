import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_ID = "skill.curated.git-guardrails"


def load(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GitGuardrailsSuspensionTests(unittest.TestCase):
    def test_repository_release_surfaces_are_suspended(self) -> None:
        skills = {
            item["id"]: item for item in load("registry/skills.json")["skills"]
        }
        routes = {
            item["skill"]: item for item in load("registry/routing.json")["routes"]
        }
        manifest_paths = {
            item["path"] for item in load("release-manifest.json")["files"]
        }

        self.assertNotIn(SKILL_ID, skills)
        self.assertNotIn(SKILL_ID, routes)
        self.assertFalse(
            any(path.startswith("skills/git-guardrails/") for path in manifest_paths)
        )
        self.assertFalse((ROOT / "skills/git-guardrails").exists())

    def test_admission_retains_review_value_without_execution_eligibility(self) -> None:
        admissions = {
            item["skill"]: item
            for item in load("registry/admissions.json")["admissions"]
        }
        admission = admissions[SKILL_ID]

        self.assertEqual(admission["disposition"], "recipe-only")
        self.assertFalse(admission["validated"])
        self.assertIn(
            "registry/git-guardrails-interception-evidence-contract-2026-07-24.json",
            admission["reviewRefs"],
        )

    def test_contract_keeps_live_cc_outside_repository_transaction(self) -> None:
        contract = load(
            "registry/git-guardrails-interception-evidence-contract-2026-07-24.json"
        )
        drift = contract["repositoryAdmissionDrift"]

        self.assertEqual(
            drift["coherentSuspensionTransactionState"],
            "repository-release-suspended",
        )
        self.assertFalse(drift["liveCcPayloadChangedByThisReview"])


if __name__ == "__main__":
    unittest.main()
