from __future__ import annotations

import copy
import json
import unittest

from scripts.validate_human_ai_collaboration_self_authored_control_chain_carrier_audit import (
    AUDIT_PATH,
    ROOT,
    validate_audit,
)


class SelfAuthoredControlChainCarrierAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))

    def validate(self, document: dict | None = None) -> None:
        validate_audit(document or self.document, root=ROOT)

    def test_current_audit_is_valid(self) -> None:
        self.validate()

    def test_rejects_agents_codex_equality_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"]["skills"][0][
            "agentsAndCodexByteEqual"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "carrier relation"):
            self.validate(document)

    def test_rejects_cc_switch_equality_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"]["skills"][1][
            "ccSwitchByteEqualToCurrent"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "carrier relation"):
            self.validate(document)

    def test_rejects_hook_mode_rewrite(self) -> None:
        document = copy.deepcopy(self.document)
        document["hookObservation"]["mode"] = "off"
        with self.assertRaisesRegex(RuntimeError, "Hook boundary"):
            self.validate(document)

    def test_rejects_historical_hook_as_current_registration(self) -> None:
        document = copy.deepcopy(self.document)
        document["hookObservation"]["liveRecheck20260729"][
            "activeHookRegistrationObserved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "current Hook recheck"):
            self.validate(document)

    def test_rejects_dependency_pin_drift(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"]["currentPackageDependencies"][0][
            "currentSha256"
        ] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "dependency relation"):
            self.validate(document)

    def test_rejects_implicit_loading_maturity_promotion(self) -> None:
        document = copy.deepcopy(self.document)
        document["decision"]["implicitLoadingCountsAsMaturity"] = True
        with self.assertRaisesRegex(RuntimeError, "decision promoted"):
            self.validate(document)

    def test_rejects_common_agents_root_removal(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"]["ownerRecalibration20260729"][
            "commonAgentsSkillsRootMustBeRetained"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "owner recalibration"):
            self.validate(document)

    def test_rejects_native_causation_from_current_turn(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"]["ownerRecalibration20260729"][
            "nativeRuntimeCauseProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "owner recalibration"):
            self.validate(document)

    def test_rejects_native_sentinel_causal_pass_rollback(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"][
            "nativeImplicitInvocationEvidence20260729"
        ]["causalPass"] = False
        with self.assertRaisesRegex(RuntimeError, "native implicit invocation"):
            self.validate(document)

    def test_rejects_native_evidence_as_self_authored_value(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"][
            "nativeImplicitInvocationEvidence20260729"
        ]["claimLimits"]["selfAuthoredIncrementalValueProved"] = True
        with self.assertRaisesRegex(RuntimeError, "native implicit invocation"):
            self.validate(document)

    def test_rejects_cross_host_byte_parity_requirement(self) -> None:
        document = copy.deepcopy(self.document)
        document["currentCarrierObservation"]["ownerRecalibration20260729"][
            "claudeCodexByteParityRequired"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "owner recalibration"):
            self.validate(document)

    def test_rejects_portfolio_mutation_claim(self) -> None:
        document = copy.deepcopy(self.document)
        document["claimBoundary"]["portfolioMutationJustified"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            self.validate(document)


if __name__ == "__main__":
    unittest.main()
