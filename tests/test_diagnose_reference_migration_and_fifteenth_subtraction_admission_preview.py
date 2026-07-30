from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_diagnose_reference_migration_and_fifteenth_subtraction_admission_preview import (
    EVIDENCE_PATH,
    ROOT,
    validate_preview,
)


class DiagnoseReferenceMigrationAndFifteenthSubtractionAdmissionPreviewTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_preview_passes(self) -> None:
        validate_preview(deepcopy(self.document), root=ROOT)

    def test_rejects_patching_legacy_cc_router(self) -> None:
        document = deepcopy(self.document)
        legacy = next(
            item
            for item in document["exactIdentityReferences"]
            if item["owner"] == "legacy-cc-capability-router"
        )
        legacy["proposedText"] = "patch this copy"
        with self.assertRaisesRegex(RuntimeError, "source-authority migration"):
            validate_preview(document, root=ROOT)

    def test_rejects_current_admission_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["conditionalSubtraction"]["diagnoseCurrentlyAdmitted"] = True
        with self.assertRaisesRegex(RuntimeError, "conditional subtraction"):
            validate_preview(document, root=ROOT)

    def test_rejects_satisfied_unexecuted_gate(self) -> None:
        document = deepcopy(self.document)
        document["dependencyOrder"][0]["satisfied"] = True
        with self.assertRaisesRegex(RuntimeError, "dependency order"):
            validate_preview(document, root=ROOT)

    def test_rejects_common_root_portability_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["conditionalSubtraction"]["crossHostPortabilityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "conditional subtraction"):
            validate_preview(document, root=ROOT)

    def test_rejects_mutation_authority(self) -> None:
        document = deepcopy(self.document)
        document["conditionalSubtraction"]["managerRemovalAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "conditional subtraction"):
            validate_preview(document, root=ROOT)

    def test_rejects_reference_migration_completion_claim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["referenceMigrationApplied"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_preview(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
