from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_human_ai_collaboration_release_change_zero_model_protocol import (
    FIXTURE_PATH,
    PREFLIGHT_PATH,
    PROTOCOL_PATH,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


class ReleaseChangeZeroModelProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        self.preflight = json.loads(
            (ROOT / PREFLIGHT_PATH).read_text(encoding="utf-8")
        )
        self.fixture = json.loads(
            (ROOT / FIXTURE_PATH).read_text(encoding="utf-8")
        )

    def validate(
        self,
        *,
        protocol: dict | None = None,
        preflight: dict | None = None,
        fixture: dict | None = None,
    ) -> dict[str, int]:
        return validate_protocol(
            protocol if protocol is not None else self.protocol,
            preflight if preflight is not None else self.preflight,
            fixture if fixture is not None else self.fixture,
            root=ROOT,
        )

    def test_current_offline_protocol_is_valid(self) -> None:
        counts = self.validate()
        self.assertEqual(3, counts["candidateCount"])
        self.assertEqual(4, counts["hostClassCount"])
        self.assertEqual(15, counts["hardOracleMissingEvidenceCount"])

    def test_rejects_live_fixture_promotion(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["liveFixtureFrozen"] = True

        with self.assertRaisesRegex(RuntimeError, "falsely claims a live fixture"):
            self.validate(fixture=fixture)

    def test_rejects_invented_release_target(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["releaseRollbackFixture"][
            "targetRepositoryOrService"
        ] = "invented-service"

        with self.assertRaisesRegex(RuntimeError, "invented live evidence"):
            self.validate(fixture=fixture)

    def test_rejects_hard_oracle_go_promotion(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["hardOracle"]["expectedGoNoGo"] = "GO"

        with self.assertRaisesRegex(RuntimeError, "hard oracle was promoted"):
            self.validate(fixture=fixture)

    def test_rejects_missing_hard_oracle_evidence_code(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["hardOracle"]["requiredMissingEvidenceCodes"].remove(
            "missing-release-version"
        )

        with self.assertRaisesRegex(RuntimeError, "missing-evidence set drifted"):
            self.validate(fixture=fixture)

    def test_rejects_missing_hard_oracle_unknown_field(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["hardOracle"]["requiredUnknownFields"].remove(
            "releaseRollbackFixture.communicationEvidence"
        )

        with self.assertRaisesRegex(RuntimeError, "unknown-field set drifted"):
            self.validate(fixture=fixture)

    def test_rejects_new_release_contract_evidence_in_negative_control(self) -> None:
        for field, value in (
            ("releaseVersion", "v1.2.3"),
            ("communicationEvidence", {"plan": "invented"}),
            ("postChangeVerificationEvidence", {"status": "invented"}),
        ):
            with self.subTest(field=field):
                fixture = copy.deepcopy(self.fixture)
                fixture["releaseRollbackFixture"][field] = value
                with self.assertRaisesRegex(RuntimeError, "invented live evidence"):
                    self.validate(fixture=fixture)

    def test_rejects_offline_classifier_result_drift(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["offlineRollbackMechanismCalibration"][
            "expectedClassifierResult"
        ]["decision"] = "reject"

        with self.assertRaisesRegex(RuntimeError, "classifier result drifted"):
            self.validate(fixture=fixture)

    def test_rejects_protocol_source_digest_drift(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["sourceBindings"][0]["sha256"] = "0" * 64

        with self.assertRaisesRegex(RuntimeError, "source binding digest drifted"):
            self.validate(protocol=protocol)

    def test_rejects_protocol_source_binding_path_removal(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["sourceBindings"] = [
            item
            for item in protocol["sourceBindings"]
            if item["path"]
            != (
                "registry/"
                "other-cc-and-external-skill-scenario-coverage-audit-2026-07-27.json"
            )
        ]

        with self.assertRaisesRegex(RuntimeError, "binding path set drifted"):
            self.validate(protocol=protocol)

    def test_rejects_protocol_source_binding_role_promotion(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["sourceBindings"][0]["role"] = "authorizes-live-release"

        with self.assertRaisesRegex(RuntimeError, "binding role or field set"):
            self.validate(protocol=protocol)

    def test_rejects_preflight_source_binding_path_removal(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        preflight["sourceBindings"] = [
            item
            for item in preflight["sourceBindings"]
            if item["path"] != "sources/addyosmani-agent-skills/LICENSE"
        ]

        with self.assertRaisesRegex(RuntimeError, "binding path set drifted"):
            self.validate(preflight=preflight)

    def test_rejects_preflight_file_binding_drift(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["candidatePreflightBinding"]["sha256"] = "0" * 64

        with self.assertRaisesRegex(RuntimeError, "preflight binding drifted"):
            self.validate(protocol=protocol)

    def test_rejects_missing_host_class(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["hostDifferences"].pop()

        with self.assertRaisesRegex(RuntimeError, "host split drifted"):
            self.validate(protocol=protocol)

    def test_rejects_missing_host_future_evidence_gate(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["hostDifferences"][0]["requiredFutureEvidence"] = []

        with self.assertRaisesRegex(RuntimeError, "host was promoted"):
            self.validate(protocol=protocol)

    def test_rejects_duplicate_host_identity_with_promoted_shadow(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        duplicate = copy.deepcopy(protocol["hostDifferences"][0])
        duplicate["liveArmEligible"] = True
        protocol["hostDifferences"].insert(0, duplicate)

        with self.assertRaisesRegex(RuntimeError, "duplicate identities"):
            self.validate(protocol=protocol)

    def test_rejects_duplicate_protocol_arm_with_promoted_shadow(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        duplicate = copy.deepcopy(protocol["candidateArms"][0])
        duplicate["formalLiveArmEligible"] = True
        protocol["candidateArms"].insert(0, duplicate)

        with self.assertRaisesRegex(RuntimeError, "duplicate identities"):
            self.validate(protocol=protocol)

    def test_rejects_duplicate_preflight_candidate_with_promoted_shadow(
        self,
    ) -> None:
        preflight = copy.deepcopy(self.preflight)
        duplicate = copy.deepcopy(preflight["candidates"][0])
        duplicate["formalLiveArmEligible"] = True
        preflight["candidates"].insert(0, duplicate)

        with self.assertRaisesRegex(RuntimeError, "duplicate identities"):
            self.validate(preflight=preflight)

    def test_rejects_candidate_exposure_promotion(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        candidate = next(
            item
            for item in protocol["candidateArms"]
            if item["candidateId"]
            == "skill.curated.ci-cd-and-automation"
        )
        candidate["currentTaskScopedExposureState"] = "proved"

        with self.assertRaisesRegex(RuntimeError, "arm was promoted"):
            self.validate(protocol=protocol)

    def test_rejects_candidate_loader_promotion(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.shipping-and-launch"
        )
        candidate["currentHostEvidence"]["loaderInvocationState"] = "proved"

        with self.assertRaisesRegex(RuntimeError, "live state was promoted"):
            self.validate(preflight=preflight)

    def test_rejects_candidate_release_digest_drift(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.ci-cd-and-automation"
        )
        candidate["identity"]["repositoryPayloadSha256"] = "f" * 64

        with self.assertRaisesRegex(RuntimeError, "release identity drifted"):
            self.validate(preflight=preflight)

    def test_rejects_curated_candidate_class_promotion(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.ci-cd-and-automation"
        )
        candidate["candidateClass"] = "installed-current-cc"

        with self.assertRaisesRegex(RuntimeError, "release identity drifted"):
            self.validate(preflight=preflight)

    def test_rejects_curated_registry_status_promotion(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.shipping-and-launch"
        )
        candidate["identity"]["registryStatus"] = "current-cc-live"

        with self.assertRaisesRegex(RuntimeError, "release identity drifted"):
            self.validate(preflight=preflight)

    def test_rejects_candidate_license_drift(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.shipping-and-launch"
        )
        candidate["source"]["license"] = "unknown"

        with self.assertRaisesRegex(RuntimeError, "source or license drifted"):
            self.validate(preflight=preflight)

    def test_rejects_candidate_admission_promotion_or_drift(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.ci-cd-and-automation"
        )
        candidate["admission"]["disposition"] = "auto-execute"

        with self.assertRaisesRegex(RuntimeError, "admission drifted"):
            self.validate(preflight=preflight)

    def test_rejects_composed_first_treatment(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.shipping-and-launch"
        )
        candidate["overlap"]["firstComparisonTreatment"] = "compose"

        with self.assertRaisesRegex(RuntimeError, "overlap boundary drifted"):
            self.validate(preflight=preflight)

    def test_rejects_candidate_execution_authority(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        candidate = next(
            item
            for item in preflight["candidates"]
            if item["candidateId"]
            == "skill.curated.shipping-and-launch"
        )
        candidate["executionAuthorized"] = True

        with self.assertRaisesRegex(RuntimeError, "live state was promoted"):
            self.validate(preflight=preflight)

    def test_rejects_fixture_argument_not_bound_to_disk_object(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["unvalidatedShadowClaim"] = "live-ready"

        with self.assertRaisesRegex(RuntimeError, "hash-bound file object"):
            self.validate(fixture=fixture)

    def test_rejects_preflight_argument_not_bound_to_disk_object(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        preflight["unvalidatedShadowClaim"] = "live-ready"

        with self.assertRaisesRegex(RuntimeError, "hash-bound file object"):
            self.validate(preflight=preflight)

    def test_rejects_nonzero_model_counter(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["executionCounters"]["modelRequestCount"] = 1

        with self.assertRaisesRegex(RuntimeError, "key or value set drifted"):
            self.validate(protocol=protocol)

    def test_rejects_claim_boundary_promotion(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["claimBoundary"]["provesCandidateBehaviorOrValue"] = True

        with self.assertRaisesRegex(RuntimeError, "key or value set drifted"):
            self.validate(protocol=protocol)

    def test_rejects_empty_boundary_maps_for_all_artifacts(self) -> None:
        cases = (
            ("protocol-authority", "protocol", "authorityBoundary"),
            ("protocol-execution", "protocol", "executionCounters"),
            ("protocol-claim", "protocol", "claimBoundary"),
            ("preflight-authority", "preflight", "authorityBoundary"),
            ("preflight-execution", "preflight", "executionBoundary"),
            ("preflight-claim", "preflight", "claimBoundary"),
            ("fixture-authority", "fixture", "authorityBoundary"),
            ("fixture-execution", "fixture", "executionBoundary"),
            ("fixture-claim", "fixture", "claimBoundary"),
        )
        for name, artifact, field in cases:
            with self.subTest(name=name):
                protocol = copy.deepcopy(self.protocol)
                preflight = copy.deepcopy(self.preflight)
                fixture = copy.deepcopy(self.fixture)
                target = {
                    "protocol": protocol,
                    "preflight": preflight,
                    "fixture": fixture,
                }[artifact]
                target[field] = {}
                with self.assertRaisesRegex(
                    RuntimeError, "key or value set drifted"
                ):
                    self.validate(
                        protocol=protocol,
                        preflight=preflight,
                        fixture=fixture,
                    )

    def test_rejects_missing_boundary_keys_for_all_artifacts(self) -> None:
        cases = (
            ("protocol-authority", "protocol", "authorityBoundary"),
            ("protocol-execution", "protocol", "executionCounters"),
            ("protocol-claim", "protocol", "claimBoundary"),
            ("preflight-authority", "preflight", "authorityBoundary"),
            ("preflight-execution", "preflight", "executionBoundary"),
            ("preflight-claim", "preflight", "claimBoundary"),
            ("fixture-authority", "fixture", "authorityBoundary"),
            ("fixture-execution", "fixture", "executionBoundary"),
            ("fixture-claim", "fixture", "claimBoundary"),
        )
        for name, artifact, field in cases:
            with self.subTest(name=name):
                protocol = copy.deepcopy(self.protocol)
                preflight = copy.deepcopy(self.preflight)
                fixture = copy.deepcopy(self.fixture)
                target = {
                    "protocol": protocol,
                    "preflight": preflight,
                    "fixture": fixture,
                }[artifact]
                target[field].pop(next(iter(target[field])))
                with self.assertRaisesRegex(
                    RuntimeError, "key or value set drifted"
                ):
                    self.validate(
                        protocol=protocol,
                        preflight=preflight,
                        fixture=fixture,
                    )

    def test_rejects_failure_fallback_semantic_rewrite(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["failureFallback"] = [
            {"condition": "anything", "outcome": "GO"}
        ] * 5

        with self.assertRaisesRegex(RuntimeError, "failure fallback drifted"):
            self.validate(protocol=protocol)

    def test_rejects_stop_condition_semantic_rewrite(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["stopConditions"] = ["continue-live"] * 7

        with self.assertRaisesRegex(RuntimeError, "stop conditions drifted"):
            self.validate(protocol=protocol)

    def test_rejects_falsifiable_conclusion_promotion(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["falsifiableConclusions"]["supportedNow"].append(
            "The candidates are live-ready and superior."
        )

        with self.assertRaisesRegex(RuntimeError, "falsifiable conclusions"):
            self.validate(protocol=protocol)

    def test_rejects_next_gate_promotion(self) -> None:
        protocol = copy.deepcopy(self.protocol)
        protocol["nextGate"] = "Deploy now."

        with self.assertRaisesRegex(RuntimeError, "Release/change next gate"):
            self.validate(protocol=protocol)

    def test_rejects_preflight_failure_fallback_removal(self) -> None:
        preflight = copy.deepcopy(self.preflight)
        preflight["failureFallback"].pop()

        with self.assertRaisesRegex(RuntimeError, "failure fallback drifted"):
            self.validate(preflight=preflight)

    def test_rejects_fixture_stop_boundary_removal(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["hardOracle"]["requiredStopBefore"].remove("deploy")

        with self.assertRaisesRegex(RuntimeError, "stop boundary drifted"):
            self.validate(fixture=fixture)


if __name__ == "__main__":
    unittest.main()
