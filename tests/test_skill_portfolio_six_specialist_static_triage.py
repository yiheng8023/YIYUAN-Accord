from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_skill_portfolio_six_specialist_static_triage import (
    EVIDENCE_PATH,
    ROOT,
    validate_triage,
)


class SkillPortfolioSixSpecialistStaticTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_triage_passes(self) -> None:
        validate_triage(deepcopy(self.document), root=ROOT)

    def test_rejects_open_format_removal_preview(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["retainActive"] = []
        document["decision"]["readyForManagerRemovalPreview"].append(
            "obsidian-open-format-knowledge-files"
        )
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_triage(document, root=ROOT)

    def test_rejects_unbound_disciplined_source_claim(self) -> None:
        document = deepcopy(self.document)
        document["items"][0]["sourceAuthorityBound"] = True
        with self.assertRaisesRegex(RuntimeError, "Disciplined-coding"):
            validate_triage(document, root=ROOT)

    def test_rejects_playwright_runtime_install_overclaim(self) -> None:
        document = deepcopy(self.document)
        playwright = next(
            item for item in document["items"] if item["name"] == "playwright"
        )
        playwright["playwrightCliGloballyInstalled"] = True
        with self.assertRaisesRegex(RuntimeError, "Playwright carrier"):
            validate_triage(document, root=ROOT)

    def test_rejects_networkx_health_overclaim(self) -> None:
        document = deepcopy(self.document)
        security = next(
            item
            for item in document["items"]
            if item["name"] == "security-ownership-map"
        )
        security["networkxInstalledInCurrentPython"] = True
        with self.assertRaisesRegex(RuntimeError, "Security ownership"):
            validate_triage(document, root=ROOT)

    def test_rejects_direct_uninstall_authority(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["directUninstallAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_triage(document, root=ROOT)

    def test_rejects_behavioral_value_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["behavioralValueProvedForAllSix"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_triage(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
