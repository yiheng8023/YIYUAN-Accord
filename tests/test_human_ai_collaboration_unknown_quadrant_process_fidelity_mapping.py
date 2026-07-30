from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_human_ai_collaboration_unknown_quadrant_process_fidelity_mapping import (
    DOCUMENTATION_PATH,
    MAPPING_PATH,
    NARRATIVE_PATHS,
    ROOT,
    validate_mapping,
)


def load() -> dict:
    return json.loads((ROOT / MAPPING_PATH).read_text(encoding="utf-8"))


class UnknownQuadrantProcessFidelityMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load()

    def test_current_mapping_is_valid(self) -> None:
        validate_mapping(self.document)

    def test_rejects_missing_quadrant(self) -> None:
        document = copy.deepcopy(self.document)
        document["quadrants"].pop()
        with self.assertRaisesRegex(RuntimeError, "quadrant set"):
            validate_mapping(document)

    def test_rejects_hard_standard_as_skill_treatment(self) -> None:
        document = copy.deepcopy(self.document)
        document["systemLayerBoundary"]["hardStandards"]["skillTreatment"] = True
        with self.assertRaisesRegex(RuntimeError, "hard standards"):
            validate_mapping(document)

    def test_rejects_quiz_as_acceptance_substitute(self) -> None:
        document = copy.deepcopy(self.document)
        document["lifecycle"][2]["artifactPolicy"] = (
            "Quiz completion replaces tests and acceptance."
        )
        with self.assertRaisesRegex(RuntimeError, "quiz or explanation"):
            validate_mapping(document)

    def test_rejects_known_unknown_promoted_to_certainty(self) -> None:
        document = copy.deepcopy(self.document)
        document["quadrants"][1]["falsifier"] = (
            "Explicit uncertainty may be silently assumed."
        )
        with self.assertRaisesRegex(RuntimeError, "known-unknown"):
            validate_mapping(document)

    def test_rejects_unknown_unknown_completeness_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["quadrants"][3]["forbiddenClaim"] = (
            "A scan proves completeness."
        )
        with self.assertRaisesRegex(RuntimeError, "unknown-unknown"):
            validate_mapping(document)

    def test_rejects_new_skill_necessity_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["newSkillImplementationNecessary"] = True
        with self.assertRaisesRegex(RuntimeError, "self-build need"):
            validate_mapping(document)

    def test_rejects_model_or_candidate_activity(self) -> None:
        for key in (
            "modelRequestCount",
            "candidateDispatchCount",
            "candidateSkillInvocationCount",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(self.document)
                document["executionBoundary"][key] = 1
                with self.assertRaisesRegex(RuntimeError, "execution boundary"):
                    validate_mapping(document)

    def test_rejects_claim_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["weakAgentValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_mapping(document)

    def test_rejects_missing_narrative_pointer(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for binding in self.document["sourceBindings"]:
            source = ROOT / binding["path"]
            target = root / binding["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        documentation = root / DOCUMENTATION_PATH
        documentation.parent.mkdir(parents=True, exist_ok=True)
        documentation.write_bytes((ROOT / DOCUMENTATION_PATH).read_bytes())
        first = sorted(NARRATIVE_PATHS)[0]
        for path in NARRATIVE_PATHS:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            content = (ROOT / path).read_text(encoding="utf-8")
            if path == first:
                content = content.replace(
                    "unknown-quadrant process-fidelity mapping",
                    "unknown-class notes",
                )
            target.write_text(content, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "narrative pointer"):
            validate_mapping(self.document, root=root)


if __name__ == "__main__":
    unittest.main()
