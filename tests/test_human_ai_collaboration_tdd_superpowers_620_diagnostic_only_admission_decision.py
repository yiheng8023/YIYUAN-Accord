from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_human_ai_collaboration_tdd_superpowers_620_diagnostic_only_admission_decision import (
    DECISION_PATH,
    PROGRAM_PATH,
    ROOT,
    validate_decision,
)


def load() -> dict:
    return json.loads((ROOT / DECISION_PATH).read_text(encoding="utf-8"))


class Superpowers620TddDiagnosticOnlyAdmissionDecisionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.document = load()

    def test_current_decision_is_valid(self) -> None:
        validate_decision(self.document)

    def test_rejects_source_binding_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source binding digest"):
            validate_decision(document)

    def test_rejects_release_commit_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateIdentity"]["releaseCommit"] = "wrong"
        with self.assertRaisesRegex(RuntimeError, "release identity"):
            validate_decision(document)

    def test_rejects_manifest_identity_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateIdentity"]["pluginManifest"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "plugin manifest"):
            validate_decision(document)

    def test_rejects_candidate_file_digest_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["candidateIdentity"]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "file identity"):
            validate_decision(document)

    def test_rejects_release_admission_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["approvedReleaseAdmission"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary promoted"):
            validate_decision(document)

    def test_rejects_current_execution_authority(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["candidateExecutionAuthorizedNow"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary promoted"):
            validate_decision(document)

    def test_rejects_non_python_command_priority(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticScope"]["exactPythonCommandPriority"] = [
            "npm",
            "test",
        ]
        with self.assertRaisesRegex(RuntimeError, "Python command priority"):
            validate_decision(document)

    def test_rejects_fixture_scaffold_deletion(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticScope"]["conflictControls"][
            "authorizedFixtureScaffoldMustNotBeDeletedOrMutatedBeforeValidRed"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "conflict control"):
            validate_decision(document)

    def test_rejects_other_test_repair(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticScope"]["conflictControls"][
            "unrelatedTestFailurePolicy"
        ] = "fix-other-tests"
        with self.assertRaisesRegex(RuntimeError, "conflict control"):
            validate_decision(document)

    def test_rejects_broadened_mutable_file_scope(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticScope"]["allowedMutableFiles"].append("TASK.json")
        with self.assertRaisesRegex(RuntimeError, "mutable-file allowlist"):
            validate_decision(document)

    def test_rejects_writing_skills_enablement(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticScope"]["excludedCapabilitiesAndEffects"].remove(
            "superpowers:writing-skills"
        )
        with self.assertRaisesRegex(RuntimeError, "excluded capability"):
            validate_decision(document)

    def test_rejects_candidate_value_or_residual_gap_claim(self) -> None:
        for key in (
            "sourceOrPackageIdentityProvesValue",
            "diagnosticAdmissionProvesSelfAuthoredResidualGap",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(self.document)
                document["claimBoundary"][key] = True
                with self.assertRaisesRegex(RuntimeError, "claim boundary"):
                    validate_decision(document)

    def test_rejects_hard_standard_credit(self) -> None:
        document = copy.deepcopy(self.document)
        document["diagnosticScope"]["hardStandardsCreditedToCandidate"] = True
        with self.assertRaisesRegex(RuntimeError, "hard-standard control"):
            validate_decision(document)

    def test_rejects_missing_review_evidence(self) -> None:
        document = copy.deepcopy(self.document)
        document["review"]["security"]["evidence"] = []
        with self.assertRaisesRegex(RuntimeError, "review evidence"):
            validate_decision(document)

    def _mutated_root(self, mutate) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        program = json.loads((ROOT / PROGRAM_PATH).read_text(encoding="utf-8"))
        mutate(program)
        program_path = root / PROGRAM_PATH
        program_path.parent.mkdir(parents=True, exist_ok=True)
        program_path.write_text(
            json.dumps(program, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        for source in self.document["sourceBindings"]:
            source_path = ROOT / source["path"]
            target_path = root / source["path"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(source_path.read_bytes())
        for path in (
            "registry/admissions.json",
            "release-manifest.json",
            self.document["documentation"],
        ):
            source_path = ROOT / path
            target_path = root / path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(source_path.read_bytes())
        return root

    def test_rejects_acceptance_assessment_change(self) -> None:
        def mutate(program):
            criterion = next(
                item
                for item in program["acceptanceCriteria"]
                if item["id"] == "acceptance.third-party-admission-gates"
            )
            criterion["assessment"] = "partial"

        root = self._mutated_root(mutate)
        with self.assertRaisesRegex(RuntimeError, "assessment drifted"):
            validate_decision(self.document, root=root)

    def test_rejects_missing_or_duplicate_backlink(self) -> None:
        evidence_id = (
            "evidence.human-ai-collaboration-tdd-superpowers-620-"
            "diagnostic-only-admission-decision-2026-07-27"
        )
        for mode in ("missing", "duplicate"):
            with self.subTest(mode=mode):
                def mutate(program, mode=mode):
                    criterion = next(
                        item
                        for item in program["acceptanceCriteria"]
                        if item["id"]
                        == "acceptance.third-party-admission-gates"
                    )
                    if mode == "missing":
                        criterion["evidenceIds"].remove(evidence_id)
                    else:
                        criterion["evidenceIds"].append(evidence_id)

                root = self._mutated_root(mutate)
                with self.assertRaisesRegex(RuntimeError, "backlink"):
                    validate_decision(self.document, root=root)

    def test_rejects_release_value_or_residual_gap_evidence_projection(
        self,
    ) -> None:
        def mutate(program):
            evidence = next(
                item
                for item in program["evidence"]
                if item["id"].startswith(
                    "evidence.human-ai-collaboration-tdd-superpowers-620-"
                )
            )
            evidence["kind"] = "release-value-and-residual-gap-evidence"
            evidence["supports"].append("acceptance.residual-gap-proof")

        root = self._mutated_root(mutate)
        with self.assertRaisesRegex(RuntimeError, "evidence projection"):
            validate_decision(self.document, root=root)


if __name__ == "__main__":
    unittest.main()
