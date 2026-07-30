from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_human_ai_collaboration_tdd_current_self_authored_treatment_gap_audit import (
    AUDIT_PATH,
    DOCUMENTATION_PATH,
    ROOT,
    validate_audit,
)


def load() -> dict:
    return json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))


class CurrentSelfAuthoredTddTreatmentGapAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load()

    def test_current_audit_is_valid(self) -> None:
        validate_audit(self.document)

    def test_rejects_source_hash_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["sourceBindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source binding digest"):
            validate_audit(document)

    def test_rejects_self_chain_promoted_to_treatment(self) -> None:
        document = copy.deepcopy(self.document)
        document["classification"]["upstreamSelfAuthoredOrchestration"][
            "singleTddMethod"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "upstream-orchestration"):
            validate_audit(document)

    def test_rejects_approved_adapted_tdd_reclassified_as_self(self) -> None:
        document = copy.deepcopy(self.document)
        document["classification"]["approvedAdaptedTddPayload"][
            "memberOfSelfAuthoredControlChain"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "reclassified"):
            validate_audit(document)

    def test_rejects_runner_or_ledger_promoted_to_treatment(self) -> None:
        document = copy.deepcopy(self.document)
        document["classification"]["runnerAndLedger"]["role"] = (
            "tdd-method-treatment"
        )
        with self.assertRaisesRegex(RuntimeError, "runner or ledger"):
            validate_audit(document)

    def test_rejects_self_build_necessity_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["selfAuthoredTddImplementationNecessary"] = True
        with self.assertRaisesRegex(RuntimeError, "self-authored treatment need"):
            validate_audit(document)

    def test_rejects_stale_superpowers_admission_state(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCandidateAssessment"]["superpowers620"][
            "diagnosticOnlyAdmissionPresent"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "current-candidate assessment"):
            validate_audit(document)

    def test_rejects_residual_gap_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["absenceConstitutesResidualGapProof"] = True
        with self.assertRaisesRegex(RuntimeError, "self-authored treatment need"):
            validate_audit(document)

    def test_rejects_self_authoring_authority_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["absenceAuthorizesSelfAuthoring"] = True
        with self.assertRaisesRegex(RuntimeError, "self-authored treatment need"):
            validate_audit(document)

    def test_rejects_hard_standard_credit_to_candidate(self) -> None:
        document = copy.deepcopy(self.document)
        document["classification"]["hardStandards"][
            "candidateCreditAllowed"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "hard-standard"):
            validate_audit(document)

    def test_rejects_model_or_candidate_activity(self) -> None:
        for key in (
            "modelRequestCount",
            "candidateDispatchCount",
            "candidateSkillInvocationCount",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(self.document)
                document["executionBoundary"][key] = 1
                with self.assertRaisesRegex(
                    RuntimeError, "execution boundary"
                ):
                    validate_audit(document)

    def test_rejects_external_or_configuration_side_effects(self) -> None:
        for key in (
            "installationPerformed",
            "globalConfigurationChanged",
            "ccSwitchChanged",
            "externalAccessUsed",
            "programMapChanged",
            "globalVerifierChanged",
        ):
            with self.subTest(key=key):
                document = copy.deepcopy(self.document)
                document["executionBoundary"][key] = True
                with self.assertRaisesRegex(
                    RuntimeError, "execution boundary"
                ):
                    validate_audit(document)

    def test_rejects_claim_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["selfAuthoredResidualGapProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_audit(document)

    def test_rejects_missing_documented_layer_boundary(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for binding in self.document["sourceBindings"]:
            source = ROOT / binding["path"]
            target = root / binding["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        documentation = (ROOT / DOCUMENTATION_PATH).read_text(encoding="utf-8")
        documentation = documentation.replace("Runner and ledger", "Infra")
        target_documentation = root / DOCUMENTATION_PATH
        target_documentation.parent.mkdir(parents=True, exist_ok=True)
        target_documentation.write_text(documentation, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "documentation boundary"):
            validate_audit(self.document, root=root)


if __name__ == "__main__":
    unittest.main()
