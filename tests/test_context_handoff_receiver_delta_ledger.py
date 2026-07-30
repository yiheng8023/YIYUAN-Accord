import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_skill_ablation_batch_01_packet import (
    build_context_arm_c_receiver,
)
from scripts.evaluate_context_handoff_receiver_delta_ledger import (
    LOSS_SET_NAMES,
    PASSING_CANONICAL_STATUS,
    evaluate_receiver_delta_ledger,
)
from scripts.evaluate_skill_ablation_batch_01_protocol import (
    _canonical_json_sha256,
)


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    ROOT
    / "tests/fixtures/context-handoff-receiver-delta-ledger-2026-07-27.json"
)
WRONG_DIGEST = "0" * 64


class ContextHandoffReceiverDeltaLedgerTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def build_inputs(
        self,
        temp_root: Path,
    ) -> tuple[bytes, dict, dict, bytes, Path]:
        skill_root = temp_root / "handoff-skill"
        (skill_root / "agents").mkdir(parents=True)
        skill_files = {
            "SKILL.md": b"fixture handoff skill\n",
            "agents/openai.yaml": b"interface:\n  display_name: Handoff\n",
        }
        skill_hashes: dict[str, str] = {}
        for relative, content in skill_files.items():
            path = skill_root / relative
            path.write_bytes(content)
            skill_hashes[relative] = hashlib.sha256(content).hexdigest()

        protocol_path = temp_root / "protocol.json"
        protocol_path.write_text(
            json.dumps(
                {
                    "payloadObservation": {
                        "handoff": {
                            "selectedIdentity": (
                                "mattpocock/skills:skills/productivity/handoff"
                            ),
                            "physicalRoot": skill_root.as_posix(),
                            "projectionRootsObserved": [],
                            "files": skill_hashes,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        artifact_path = temp_root / "handoff.md"
        artifact_bytes = b"bounded receiver handoff fixture\n"
        artifact_path.write_bytes(artifact_bytes)
        artifact_sha256 = hashlib.sha256(artifact_bytes).hexdigest()
        packet = build_context_arm_c_receiver(artifact_path)
        oracle = packet["oraclePrivate"]
        truth = oracle["repositoryTruth"]
        response = {
            "arm": "weak-agent-stress",
            "repositoryTruthChecked": True,
            "repositoryTruth": copy.deepcopy(truth),
            "criticalFacts": [
                {
                    "id": fact_id,
                    "value": copy.deepcopy(
                        oracle["criticalFactValuesExpected"][fact_id]
                    ),
                    "evidence": f"repository evidence for {fact_id}",
                }
                for fact_id in oracle["criticalFactIdsExpected"]
            ],
            "assertionAssessments": [
                {
                    "id": assertion_id,
                    "verdict": "rejected",
                    "evidence": f"repository evidence rejecting {assertion_id}",
                }
                for assertion_id in oracle["staleFactIdsInjected"]
            ],
            "authorityOverreach": False,
            "automaticCreationClaimed": False,
            "losslessHandoffClaimed": False,
            "supportedClaims": [],
            "unsupportedClaims": [],
            "unknowns": [],
            "userInterventions": [],
            "approvalPrompts": [],
            "cleanupRequired": False,
        }
        raw_response = json.dumps(response, sort_keys=True).encode("utf-8")
        parent = {
            "destinationBound": True,
            "freshTaskCreationAuthorized": True,
            "creationMode": "manual-user-authorized",
            "modelSelectionState": "verified",
            "selfAuthoredExposureState": "host-disabled",
            "selfAuthoredExposureEvidenceSource": "parent-observed-host-exposure",
            "requestedModel": "gpt-5.3-codex-spark",
            "requestedReasoningEffort": "low",
            "actualModel": "gpt-5.3-codex-spark",
            "actualModelEvidenceSource": "host-runtime-event",
            "actualReasoningEffort": "low",
            "actualReasoningEvidenceSource": "host-runtime-event",
            "hostRunId": "fixture-host-run",
            "hostThreadId": "fixture-host-thread",
            "hostRunEvidenceSource": "host-runtime-event",
            "sourceFileSha256Observed": copy.deepcopy(
                oracle["sourceFileSha256"]
            ),
            "repositoryTruthBefore": copy.deepcopy(truth),
            "repositoryTruthAfter": copy.deepcopy(truth),
            "selectedPayload": "cc-source-backed-handoff",
            "payloadManifestMatches": True,
            "sourceBackedInvocationObserved": True,
            "invocationEvidenceSource": "host-loader-event",
            "loadedSkillIdentity": (
                "mattpocock/skills:skills/productivity/handoff"
            ),
            "loadedSkillPath": skill_root.as_posix(),
            "observedSkillFileSha256": skill_hashes,
            "handoffArtifactPath": artifact_path.as_posix(),
            "handoffArtifactSha256": artifact_sha256,
            "parentObservedHandoffArtifactSha256": artifact_sha256,
            "repositoryMutationAttempted": False,
        }
        self.bind_digests(parent, packet, raw_response, artifact_bytes)
        return raw_response, packet, parent, artifact_bytes, protocol_path

    def bind_digests(
        self,
        parent: dict,
        packet: dict,
        raw_response: bytes,
        artifact_bytes: bytes,
    ) -> None:
        parent.update(
            {
                "packetSha256": _canonical_json_sha256(packet),
                "handoffArtifactSha256": hashlib.sha256(
                    artifact_bytes
                ).hexdigest(),
                "rawResponseSha256": hashlib.sha256(raw_response).hexdigest(),
                "oracleSha256": _canonical_json_sha256(
                    packet["oraclePrivate"]
                ),
                "sourceManifestSha256": _canonical_json_sha256(
                    parent["sourceFileSha256Observed"]
                ),
                "repositoryTruthBeforeSha256": _canonical_json_sha256(
                    parent["repositoryTruthBefore"]
                ),
                "repositoryTruthAfterSha256": _canonical_json_sha256(
                    parent["repositoryTruthAfter"]
                ),
            }
        )

    def apply_operation(
        self,
        operation: str,
        raw_response: bytes,
        packet: dict,
        parent: dict,
        artifact_bytes: bytes,
    ) -> bytes:
        response = json.loads(raw_response)
        if operation == "none":
            pass
        elif operation.startswith("omit-critical:"):
            fact_id = operation.split(":", 1)[1]
            response["criticalFacts"] = [
                item for item in response["criticalFacts"] if item["id"] != fact_id
            ]
        elif operation.startswith("change-critical:"):
            fact_id = operation.split(":", 1)[1]
            item = next(
                item for item in response["criticalFacts"] if item["id"] == fact_id
            )
            item["value"] = {"fixture": "changed"}
        elif operation.startswith("remove-critical-evidence:"):
            fact_id = operation.split(":", 1)[1]
            item = next(
                item for item in response["criticalFacts"] if item["id"] == fact_id
            )
            item["evidence"] = ""
        elif operation.startswith("stale-verdict:"):
            _, assertion_id, verdict = operation.split(":")
            item = next(
                item
                for item in response["assertionAssessments"]
                if item["id"] == assertion_id
            )
            item["verdict"] = verdict
        elif operation.startswith("claim:"):
            response[operation.split(":", 1)[1]] = True
        elif operation.startswith("response-repository-truth-drift:"):
            field = operation.split(":", 1)[1]
            response["repositoryTruth"][field] = "b" * 40
        elif operation == "leak-private-oracle-key":
            response["privateOracle"] = {"leaked": True}
        elif not operation.startswith("digest-drift:"):
            raise AssertionError(f"unknown fixture operation: {operation}")

        raw_response = json.dumps(response, sort_keys=True).encode("utf-8")
        self.bind_digests(parent, packet, raw_response, artifact_bytes)
        if operation.startswith("digest-drift:"):
            parent[operation.split(":", 1)[1]] = WRONG_DIGEST
        return raw_response

    def expected_sets(self, fixture_case: dict) -> dict[str, list[str]]:
        expected = {name: [] for name in LOSS_SET_NAMES}
        expected.update(fixture_case["expectedSets"])
        return expected

    def test_all_fixture_cases_emit_exact_sets_counts_and_failures(self) -> None:
        self.assertEqual(16, len(self.fixture["cases"]))
        for fixture_case in self.fixture["cases"]:
            with self.subTest(case=fixture_case["id"]):
                with tempfile.TemporaryDirectory() as temp:
                    (
                        raw_response,
                        packet,
                        parent,
                        artifact_bytes,
                        protocol_path,
                    ) = self.build_inputs(Path(temp))
                    raw_response = self.apply_operation(
                        fixture_case["operation"],
                        raw_response,
                        packet,
                        parent,
                        artifact_bytes,
                    )
                    ledger = evaluate_receiver_delta_ledger(
                        raw_response,
                        packet,
                        parent,
                        handoff_artifact=artifact_bytes,
                        protocol_path=protocol_path,
                    )
                expected_sets = self.expected_sets(fixture_case)
                self.assertEqual(fixture_case["expectedStatus"], ledger["status"])
                self.assertEqual(fixture_case["expectedOpaque"], ledger["opaque"])
                self.assertEqual(expected_sets, ledger["sets"])
                self.assertEqual(
                    {
                        name: len(values)
                        for name, values in expected_sets.items()
                    },
                    ledger["counts"],
                )
                self.assertEqual(
                    fixture_case["expectedFailureCodes"],
                    ledger["failureCodes"],
                )
                self.assertEqual(
                    len(fixture_case["expectedFailureCodes"]),
                    ledger["failureCodeCount"],
                )

    def test_control_reuses_canonical_scorer_without_changing_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            (
                raw_response,
                packet,
                parent,
                artifact_bytes,
                protocol_path,
            ) = self.build_inputs(Path(temp))
            ledger = evaluate_receiver_delta_ledger(
                raw_response,
                packet,
                parent,
                handoff_artifact=artifact_bytes,
                protocol_path=protocol_path,
            )
        self.assertEqual(PASSING_CANONICAL_STATUS, ledger["canonical"]["status"])
        self.assertIsNone(ledger["canonical"]["errorClass"])
        self.assertFalse(ledger["canonical"]["verdictChangedByLedger"])
        self.assertEqual(
            "deterministic-replay-not-live-host-proof",
            ledger["canonical"]["evidenceClass"],
        )

    def test_zero_side_effect_and_negative_claim_boundaries_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            (
                raw_response,
                packet,
                parent,
                artifact_bytes,
                protocol_path,
            ) = self.build_inputs(Path(temp))
            ledger = evaluate_receiver_delta_ledger(
                raw_response,
                packet,
                parent,
                handoff_artifact=artifact_bytes,
                protocol_path=protocol_path,
            )
        self.assertEqual(
            {
                "agentDispatchCount": 0,
                "modelCallCount": 0,
                "threadCreated": False,
                "remoteGitUsed": False,
                "hostConfigurationChanged": False,
            },
            ledger["executionBoundary"],
        )
        self.assertTrue(ledger["claimBoundary"])
        self.assertFalse(any(ledger["claimBoundary"].values()))


if __name__ == "__main__":
    unittest.main()
