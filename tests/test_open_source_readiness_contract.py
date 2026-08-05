from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OpenSourceReadinessContractTests(unittest.TestCase):
    def test_public_entrypoints_link_the_readiness_contract(self) -> None:
        link = "docs/operations/OPEN-SOURCE-READINESS.md"
        self.assertIn(link, (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn(link, (ROOT / "README.zh-CN.md").read_text(encoding="utf-8"))

    def test_contract_separates_local_evidence_from_live_controls(self) -> None:
        text = " ".join(
            (ROOT / "docs/operations/OPEN-SOURCE-READINESS.md")
            .read_text(encoding="utf-8")
            .split()
        )
        for phrase in (
            "Public-data and secret boundary",
            "Rights and provenance",
            "Reproducibility",
            "Live GitHub controls",
            "Enabling repository security or branch settings is an external state change",
            "Public visibility does not imply production readiness",
            "A bounded high-confidence scan covered the 172 pre-existing reachable commits",
            "gitleaks` was not installed",
            "anonymous clean clone must verify each exact pushed revision",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_current_security_docs_route_sensitive_reports_privately(self) -> None:
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
        issue_config = (
            ROOT / ".github/ISSUE_TEMPLATE/config.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("Private vulnerability reporting is enabled", security)
        self.assertIn("Private vulnerability reporting is enabled", support)
        self.assertIn("security/advisories/new", issue_config)
        self.assertIn("Use private vulnerability reporting", issue_config)

    def test_dated_minimum_live_security_baseline_keeps_optional_controls_explicit(self) -> None:
        text = " ".join(
            (ROOT / "docs/operations/OPEN-SOURCE-READINESS.md")
            .read_text(encoding="utf-8")
            .split()
        )
        for phrase in (
            "minimum-live-security-baseline-applied",
            "Dependabot vulnerability alerts and security updates were enabled",
            "Secret scanning and push protection were enabled",
            "Private vulnerability reporting was enabled",
            "force pushes and branch deletion were blocked",
            "Normal direct pushes remain allowed",
            "non-provider patterns and validity checks remain disabled",
            "No required pull request, review, status check, or CodeQL workflow was added",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        plan = " ".join(
            (ROOT / "docs/strategy/RESEARCH-AND-POC-PLAN.md")
            .read_text(encoding="utf-8")
            .split()
        )
        self.assertIn("dated minimum live security baseline", plan)
        self.assertIn("does not close open-source readiness", plan)


if __name__ == "__main__":
    unittest.main()
