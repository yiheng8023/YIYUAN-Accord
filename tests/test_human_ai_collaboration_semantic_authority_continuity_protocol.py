from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_semantic_authority_continuity_protocol import (
    PROTOCOL_PATH,
    ROOT,
    validate_protocol,
)


class SemanticAuthorityContinuityProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads((ROOT / PROTOCOL_PATH).read_text(encoding="utf-8"))

    def validate(self, document: dict | None = None) -> None:
        validate_protocol(document or self.document, root=ROOT)

    def test_current_protocol_is_valid(self) -> None:
        self.validate()

    def test_rejects_mutable_live_local_treatment_path(self) -> None:
        document = copy.deepcopy(self.document)
        local = next(
            item
            for item in document["treatments"]
            if item["id"] == "SEM-LOCAL-ADAPTED-MONOLITH"
        )
        local["path"] = (
            "C:/Users/15521/.cc-switch/skills/grill-with-docs/SKILL.md"
        )
        with self.assertRaisesRegex(RuntimeError, "local treatment drifted"):
            self.validate(document)

    def test_rejects_live_run_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["liveExecutionStarted"] = True
        with self.assertRaisesRegex(RuntimeError, "decision overclaimed"):
            self.validate(document)

    def test_rejects_self_authored_arm(self) -> None:
        document = copy.deepcopy(self.document)
        document["fixtureDesign"]["selfAuthoredSkillArmPresent"] = True
        with self.assertRaisesRegex(RuntimeError, "fixture boundary"):
            self.validate(document)

    def test_rejects_unpinned_current_component_url(self) -> None:
        document = copy.deepcopy(self.document)
        current = next(
            item
            for item in document["treatments"]
            if item["id"] == "SEM-MATT-CURRENT-COMPOSITION"
        )
        current["components"][0]["rawUrl"] = (
            "https://raw.githubusercontent.com/mattpocock/skills/main/"
            "skills/engineering/grill-with-docs/SKILL.md"
        )
        with self.assertRaisesRegex(RuntimeError, "component pin drifted"):
            self.validate(document)

    def test_rejects_literal_context_filename_requirement(self) -> None:
        document = copy.deepcopy(self.document)
        document["fixtureDesign"]["literalContextMdFilenameRequired"] = True
        with self.assertRaisesRegex(RuntimeError, "fixture boundary"):
            self.validate(document)

    def test_rejects_silent_model_substitution(self) -> None:
        document = copy.deepcopy(self.document)
        document["modelPolicy"]["silentModelSubstitutionAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "weak-Agent policy"):
            self.validate(document)

    def test_rejects_non_fresh_lifecycle_phase(self) -> None:
        document = copy.deepcopy(self.document)
        document["lifecycleSequence"][2]["freshThreadRequired"] = False
        with self.assertRaisesRegex(RuntimeError, "lifecycle sequence"):
            self.validate(document)

    def test_rejects_cc_mutation_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["authorityBoundary"][
            "ccSwitchInstallUpdateReplaceOrDeleteAuthorized"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "authority expanded"):
            self.validate(document)

    def test_rejects_dependency_complete_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        current = next(
            item
            for item in document["treatments"]
            if item["id"] == "SEM-MATT-CURRENT-COMPOSITION"
        )
        current["dependencyCompleteExposureProved"] = False
        with self.assertRaisesRegex(RuntimeError, "exposure was not recorded"):
            self.validate(document)

    def test_rejects_current_host_refresh_exposure_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["executionAdmission"]["currentHostRefreshExposureProved"] = False
        with self.assertRaisesRegex(RuntimeError, "current-host exposure"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
