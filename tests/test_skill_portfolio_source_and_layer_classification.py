from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_skill_portfolio_source_and_layer_classification import (
    validate_classification,
)


ROOT = Path(__file__).resolve().parent.parent


class SkillPortfolioSourceAndLayerClassificationTest(unittest.TestCase):
    def test_current_classification(self) -> None:
        document = json.loads(
            (
                ROOT
                / "registry/skill-portfolio-source-and-layer-classification-2026-07-28.json"
            ).read_text(encoding="utf-8")
        )
        validate_classification(document, root=ROOT)

    def test_rejects_nested_source_grouping(self) -> None:
        document = json.loads(
            (
                ROOT
                / "registry/skill-portfolio-source-and-layer-classification-2026-07-28.json"
            ).read_text(encoding="utf-8")
        )
        document["standards"]["portablePhysicalSourceGroupingInsideActiveSkillRoot"] = True
        with self.assertRaisesRegex(ValueError, "directory or metadata boundary"):
            validate_classification(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
