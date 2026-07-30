from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_semantic_authority_current_matt_static_admission import (
    ADMISSION_PATH,
    ROOT,
    validate_admission,
)


class CurrentMattSemanticAuthorityStaticAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8"))

    def validate(self, document: dict | None = None) -> None:
        validate_admission(document or self.document, root=ROOT)

    def test_current_admission_is_valid(self) -> None:
        self.validate()

    def test_rejects_missing_relative_dependency(self) -> None:
        document = copy.deepcopy(self.document)
        document["exactPackageFiles"] = [
            row
            for row in document["exactPackageFiles"]
            if not row["path"].endswith("ADR-FORMAT.md")
        ]
        with self.assertRaisesRegex(RuntimeError, "package file set"):
            self.validate(document)

    def test_rejects_worktree_hash_as_raw_identity(self) -> None:
        document = copy.deepcopy(self.document)
        row = next(
            item
            for item in document["exactPackageFiles"]
            if item["path"].endswith("domain-modeling/SKILL.md")
        )
        row["sha256"] = (
            "004d5cb6258658f2e9cbf0d9f90bdc9104f8b83bd296556783800c31d503814f"
        )
        with self.assertRaisesRegex(RuntimeError, "package pin drifted"):
            self.validate(document)

    def test_rejects_static_review_execution_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["candidateExecutionAdmissionSatisfied"] = True
        with self.assertRaisesRegex(RuntimeError, "decision overclaimed"):
            self.validate(document)

    def test_rejects_portability_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["portabilityReview"]["portableWithoutHostAdapterProved"] = True
        with self.assertRaisesRegex(RuntimeError, "portability boundary"):
            self.validate(document)

    def test_rejects_cc_update_eligibility(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["consumerInstallOrCcUpdateEligible"] = True
        with self.assertRaisesRegex(RuntimeError, "decision overclaimed"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
