from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_mcp_thread_creator_close_observer_acquisition_path_admission import (
    CONCLUSION,
    PROBE_PATH,
    PROTOCOL_PATH,
    RECORD_PATH,
    REPORT_BINDINGS,
    validate_admission,
    validate_formal_report,
    validate_protocol_probe_conflict,
)


ROOT = Path(__file__).resolve().parent.parent


class McpThreadCreatorCloseObserverAcquisitionPathAdmissionTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.record = json.loads(
            (ROOT / RECORD_PATH).read_text(encoding="utf-8")
        )
        self.reports = [
            json.loads((ROOT / binding["path"]).read_text(encoding="utf-8"))
            for binding in REPORT_BINDINGS
        ]

    def validate(self, record: dict | None = None) -> None:
        validate_admission(
            self.record if record is None else record,
            root=ROOT,
        )

    def test_current_admission_and_all_three_reports_are_valid(self) -> None:
        self.validate()
        self.assertEqual(self.record["status"], CONCLUSION)
        self.assertEqual(len(self.reports), 3)

    def test_rejects_source_binding_sha_mutation(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["sourceBindings"]["currentProbe"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "source bindings drifted"):
            self.validate(mutated)

    def test_rejects_live_admission_status(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["status"] = "live-ready"
        with self.assertRaisesRegex(RuntimeError, "identity or status drifted"):
            self.validate(mutated)

    def test_rejects_live_admission_decision(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["admissionDecision"][
            "currentProtocolProbePairAdmittedForLiveExecution"
        ] = True
        with self.assertRaisesRegex(
            RuntimeError, "promoted beyond evidence"
        ):
            self.validate(mutated)

    def test_rejects_second_subscription_promotion(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["machineVerifiedObservation"][
            "secondIndependentlyReleasableSubscriptionObserved"
        ] = True
        with self.assertRaisesRegex(
            RuntimeError, "observation was promoted"
        ):
            self.validate(mutated)

    def test_rejects_owner_lease_release_and_resource_claims(self) -> None:
        for claim in self.record["claimBoundary"]:
            with self.subTest(claim=claim):
                mutated = copy.deepcopy(self.record)
                mutated["claimBoundary"][claim] = True
                with self.assertRaisesRegex(
                    RuntimeError,
                    "subscription/owner/lease/release/resource claim",
                ):
                    self.validate(mutated)

    def test_rejects_live_execution_authorization(self) -> None:
        for key in (
            "appServerStartAuthorized",
            "loopbackTransportExecutionAuthorized",
            "modelTurnAuthorized",
            "externalNetworkUseAuthorized",
            "configurationMutationAuthorized",
            "installationAuthorized",
            "liveProtocolExecutionAuthorized",
        ):
            with self.subTest(key=key):
                mutated = copy.deepcopy(self.record)
                mutated["executionBoundary"][key] = True
                with self.assertRaisesRegex(
                    RuntimeError, "execution boundary was expanded"
                ):
                    self.validate(mutated)

    def test_rejects_historical_mutation_authorization(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["requiredOfflineAmendment"][
            "oldProtocolMutationAuthorized"
        ] = True
        with self.assertRaisesRegex(
            RuntimeError, "history-preservation boundary drifted"
        ):
            self.validate(mutated)

    def test_rejects_candidate_sequence_as_live_authorization(self) -> None:
        mutated = copy.deepcopy(self.record)
        mutated["requiredOfflineAmendment"][
            "candidateSequenceIsLiveAuthorization"
        ] = True
        with self.assertRaisesRegex(
            RuntimeError, "history-preservation boundary drifted"
        ):
            self.validate(mutated)

    def test_protocol_and_probe_currently_require_resume(self) -> None:
        protocol = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        probe_source = (ROOT / PROBE_PATH).read_text(encoding="utf-8")
        validate_protocol_probe_conflict(protocol, probe_source)

    def test_rejects_protocol_without_resume_setup(self) -> None:
        protocol = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        protocol["design"]["setupSequence"] = [
            "Connection B calls directly."
        ]
        with self.assertRaisesRegex(
            RuntimeError, "protocol no longer requires thread/resume"
        ):
            validate_protocol_probe_conflict(
                protocol,
                (ROOT / PROBE_PATH).read_text(encoding="utf-8"),
            )

    def test_rejects_probe_without_resume_call(self) -> None:
        protocol = json.loads(
            (ROOT / PROTOCOL_PATH).read_text(encoding="utf-8")
        )
        with self.assertRaisesRegex(
            RuntimeError, "probe no longer contains"
        ):
            validate_protocol_probe_conflict(
                protocol,
                "# offline candidate without a resume RPC\n",
            )

    def test_rejects_report_auto_attach_path_mutation(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        mutated["thread"]["subscriptionAcquisitionPath"] = "thread-resume"
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(RuntimeError, "acquisition path"):
            validate_formal_report(mutated)

    def test_rejects_same_bridge_identity(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        mutated["connections"]["owner-b"]["bridgeProcess"]["pid"] = (
            mutated["connections"]["owner-a"]["bridgeProcess"]["pid"]
        )
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(RuntimeError, "distinct bridge"):
            validate_formal_report(mutated)

    def test_rejects_connection_b_thread_mismatch(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        for entry in mutated["connections"]["owner-b"]["requestLedger"]:
            if entry.get("threadId"):
                entry["threadId"] = "different-thread"
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(RuntimeError, "one thread"):
            validate_formal_report(mutated)

    def test_rejects_connection_b_resume_in_formal_report(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        mutated["connections"]["owner-b"]["requestLedger"][3][
            "method"
        ] = "thread/resume"
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(RuntimeError, "direct call evidence"):
            validate_formal_report(mutated)

    def test_rejects_missing_connection_b_direct_call(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        for entry in mutated["connections"]["owner-b"]["requestLedger"]:
            if entry.get("phase") == "owner-b-joined-call":
                entry["phase"] = "other"
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(RuntimeError, "direct call evidence"):
            validate_formal_report(mutated)

    def test_rejects_sentinel_instance_mismatch(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        mutated["sentinel"]["ownerBJoinedCall"]["instanceId"] = (
            "different-instance"
        )
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(RuntimeError, "same exact Sentinel"):
            validate_formal_report(mutated)

    def test_rejects_model_turn(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        mutated["thread"]["modelTurnRequests"] = 1
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(RuntimeError, "contains a model turn"):
            validate_formal_report(mutated)

    def test_rejects_second_subscription_report_promotion(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        mutated["classification"][
            "secondConnectionSubscriptionObserved"
        ] = True
        mutated["reportSha256"] = _rehash(mutated)
        with self.assertRaisesRegex(
            RuntimeError, "non-subscription boundary drifted"
        ):
            validate_formal_report(mutated)

    def test_rejects_report_canonical_hash_drift(self) -> None:
        mutated = copy.deepcopy(self.reports[0])
        mutated["thread"]["modelTurnRequests"] = 1
        with self.assertRaisesRegex(RuntimeError, "canonical hash drifted"):
            validate_formal_report(mutated)


def _rehash(report: dict) -> str:
    without_hash = dict(report)
    without_hash.pop("reportSha256", None)
    encoded = json.dumps(
        without_hash,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    import hashlib

    return hashlib.sha256(encoded).hexdigest().upper()


if __name__ == "__main__":
    unittest.main()
