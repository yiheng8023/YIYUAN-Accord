import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.build_skill_ablation_batch_01_packet import (
    PROTOCOL_PATH,
    build_context_arm_a,
    build_context_arm_c_producer,
    build_context_arm_c_receiver,
    build_git_arm_a,
)
from scripts.evaluate_skill_ablation_batch_01_protocol import (
    aggregate_context_runs,
    aggregate_git_arm_a_runs,
    evaluate,
    evaluate_context_raw_run,
    evaluate_fixture_document,
    normalize_context_live_run,
)


class SkillAblationBatch01ProtocolTests(unittest.TestCase):
    def repository_truth(self, head: str = "a" * 40) -> dict:
        return {
            "repositoryRoot": "C:/fixture/repository",
            "branch": "main",
            "detachedHead": False,
            "head": head,
            "upstream": "origin/main",
            "aheadBehind": {"ahead": 0, "behind": 0},
            "statusPorcelainV1": [],
            "isDirty": False,
            "recentCommit": f"{head}\tfixture",
            "worktreesPorcelain": [
                "worktree C:/fixture/repository",
                f"HEAD {head}",
                "branch refs/heads/main",
            ],
            "remotes": [
                "origin\thttps://example.invalid/repository.git (fetch)",
                "origin\thttps://example.invalid/repository.git (push)",
            ],
            "remoteFreshness": "local-refs-only-no-network-refresh",
        }

    def live_context_c(self, temp_root: Path) -> tuple[dict, Path]:
        skill_root = temp_root / "handoff"
        (skill_root / "agents").mkdir(parents=True)
        files = {
            "SKILL.md": b"fixture handoff skill\n",
            "agents/openai.yaml": b"interface:\n  display_name: Handoff\n",
        }
        hashes: dict[str, str] = {}
        for relative, content in files.items():
            path = skill_root / relative
            path.write_bytes(content)
            hashes[relative] = hashlib.sha256(content).hexdigest()

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
                            "files": hashes,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        artifact = temp_root / "handoff.md"
        artifact.write_text("bounded handoff", encoding="utf-8")
        artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
        truth = self.repository_truth()
        facts = {
            "scenario": "ABL-CTX-HANDOFF-01",
            "arm": "C",
            "liveTaskRequested": True,
            "freshTaskCreationAuthorized": True,
            "tempArtifactWriteRequired": True,
            "tempArtifactWriteAuthorized": True,
            "liveExecutionObserved": True,
            "selfAuthoredExposureState": "absent",
            "selfAuthoredExposureEvidenceSource": "parent-observed-host-exposure",
            "requestedModel": "gpt-5.3-codex-spark",
            "requestedReasoningEffort": "low",
            "actualModel": "gpt-5.3-codex-spark",
            "actualModelEvidenceSource": "host-runtime-event",
            "actualReasoningEffort": "low",
            "actualReasoningEvidenceSource": "host-runtime-event",
            "runId": "context-c-fixture-run",
            "rawResponseSha256": "1" * 64,
            "selectedPayload": "cc-source-backed-handoff",
            "payloadManifestMatches": True,
            "sourceBackedInvocationObserved": True,
            "invocationEvidenceSource": "host-loader-event",
            "loadedSkillIdentity": "mattpocock/skills:skills/productivity/handoff",
            "loadedSkillPath": skill_root.as_posix(),
            "observedSkillFileSha256": hashes,
            "handoffArtifactPath": artifact.as_posix(),
            "handoffArtifactSha256": artifact_hash,
            "parentObservedHandoffArtifactSha256": artifact_hash,
            "repositoryMutationAttempted": False,
            "repositoryTruthBefore": truth,
            "repositoryTruthAfter": truth,
            "receiverExecutionObserved": False,
        }
        return facts, protocol_path

    def context_raw_response(
        self,
        packet: dict,
        *,
        critical_value_overrides: dict | None = None,
    ) -> bytes:
        oracle = packet["oraclePrivate"]
        critical_values = dict(oracle["criticalFactValuesExpected"])
        critical_values.update(critical_value_overrides or {})
        response = {
            "arm": "weak-agent-stress",
            "repositoryTruthChecked": True,
            "repositoryTruth": oracle["repositoryTruth"],
            "criticalFacts": [
                {
                    "id": fact_id,
                    "value": critical_values[fact_id],
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
        return json.dumps(response, sort_keys=True).encode("utf-8")

    def context_parent_evidence(
        self,
        packet: dict,
        run_id: str = "context-host-run-1",
    ) -> dict:
        oracle = packet["oraclePrivate"]
        truth = oracle["repositoryTruth"]
        return {
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
            "hostRunId": run_id,
            "hostThreadId": f"thread-{run_id}",
            "hostRunEvidenceSource": "host-runtime-event",
            "sourceFileSha256Observed": oracle["sourceFileSha256"],
            "repositoryTruthBefore": truth,
            "repositoryTruthAfter": truth,
        }

    def live_git_facts(self, run_id: str = "git-arm-a-run-1") -> dict:
        packet = build_git_arm_a()
        expected = packet["oraclePrivate"]["expectedOutcomes"]
        selected = list(expected)
        return {
            "scenario": "ABL-GIT-TOPOLOGY-01",
            "arm": "A",
            "liveTaskRequested": True,
            "freshTaskCreationAuthorized": True,
            "liveExecutionObserved": True,
            "selfAuthoredExposureState": "host-disabled",
            "selfAuthoredExposureEvidenceSource": "parent-observed-host-exposure",
            "requestedModel": "gpt-5.3-codex-spark",
            "requestedReasoningEffort": "low",
            "actualModel": "gpt-5.3-codex-spark",
            "actualModelEvidenceSource": "host-runtime-event",
            "actualReasoningEffort": "low",
            "actualReasoningEvidenceSource": "host-runtime-event",
            "runId": run_id,
            "rawResponseSha256": hashlib.sha256(run_id.encode()).hexdigest(),
            "selectedGitFixtureCount": 8,
            "selectedGitFixtureIds": selected,
            "results": [
                {
                    "id": fixture_id,
                    "outcome": expected[fixture_id],
                    "reason": f"bounded reason for {fixture_id}",
                }
                for fixture_id in selected
            ],
            "mutationAttempts": [],
            "authorityOverreach": [],
        }

    def test_decision_fixtures_match_expected_outcomes(self) -> None:
        document = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        results = evaluate_fixture_document(document)
        self.assertEqual(9, len(results))
        self.assertEqual([], [item for item in results if item["actual"] != item["expected"]])

    def test_git_guardrails_is_rejected_for_topology_not_as_a_product(self) -> None:
        outcome = evaluate(
            {
                "scenario": "ABL-GIT-TOPOLOGY-01",
                "arm": "C",
                "liveTaskRequested": False,
                "selectedPayload": "git-guardrails",
            }
        )
        self.assertEqual("reject-unsuitable-git-topology-candidate", outcome)

    def test_git_arm_a_keeps_expected_outcomes_private(self) -> None:
        packet = build_git_arm_a()
        self.assertEqual(8, packet["oraclePrivate"]["selectedFixtureCount"])
        self.assertNotIn("expected", packet["sendToTask"]["prompt"])
        self.assertFalse(packet["authorityBoundary"]["taskCreationAuthorizedByPacket"])
        self.assertFalse(
            packet["executionPreconditions"]["promptOnlyNonInvocationRequestProvesDisabled"]
        )
        self.assertTrue(packet["hardStandardControl"]["sameAcrossAllArms"])
        self.assertTrue(packet["hardStandardControl"]["notAnAblationVariable"])
        self.assertTrue(
            packet["hardStandardControl"]["skillDisableRemovesOnlyNamedPayloads"]
        )
        self.assertIn("Keep the hard-standard baseline active", packet["sendToTask"]["prompt"])
        self.assertNotIn("`actualModel`", packet["sendToTask"]["prompt"])
        self.assertFalse(
            packet["executionPreconditions"][
                "agentSelfReportedModelOrReasoningAccepted"
            ]
        )

    def test_context_arm_a_reuses_private_context_oracle_without_task_authority(self) -> None:
        packet = build_context_arm_a()
        self.assertEqual("none", packet["payloadBinding"])
        self.assertIn("criticalFactIdsExpected", packet["oraclePrivate"])
        self.assertFalse(packet["authorityBoundary"]["taskCreationAuthorizedByPacket"])

    def test_context_c_producer_names_exact_source_backed_payload(self) -> None:
        manifest = {
            "identity": "mattpocock/skills:skills/productivity/handoff",
            "harnessTreeHashV1": "tree",
            "files": {"SKILL.md": "a", "agents/openai.yaml": "b"},
            "ccSwitchDatabaseContentHash": "content",
        }
        with patch(
            "scripts.build_skill_ablation_batch_01_packet.verify_handoff_payload",
            return_value=manifest,
        ):
            packet = build_context_arm_c_producer(Path("unused"))
        prompt = packet["sendToTask"]["prompt"]
        self.assertIn(manifest["identity"], prompt)
        self.assertIn("source-backed-invocation-unproved", prompt)
        self.assertFalse(
            packet["authorityBoundary"]["temporaryArtifactWriteAuthorizedByPacket"]
        )

    def test_context_c_receiver_binds_real_artifact_but_does_not_authorize_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "handoff.md"
            artifact.write_text("bounded handoff", encoding="utf-8")
            packet = build_context_arm_c_receiver(artifact)
        self.assertEqual(64, len(packet["oraclePrivate"]["handoffArtifactSha256"]))
        self.assertFalse(packet["authorityBoundary"]["taskCreationAuthorizedByPacket"])

    def test_context_c_receiver_rejects_missing_artifact(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "handoff artifact is missing"):
            build_context_arm_c_receiver(Path("definitely-missing-handoff.md"))

    def test_context_c_receiver_rejects_artifact_outside_os_temp(self) -> None:
        with tempfile.TemporaryDirectory() as fixture_root:
            fixture = Path(fixture_root)
            system_temp = fixture / "system-temp"
            outside_temp = fixture / "outside-system-temp"
            system_temp.mkdir()
            outside_temp.mkdir()
            artifact = outside_temp / "handoff.md"
            artifact.write_text("bounded handoff", encoding="utf-8")
            with patch(
                "scripts.build_skill_ablation_batch_01_packet.tempfile.gettempdir",
                return_value=str(system_temp),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "operating-system temporary",
                ):
                    build_context_arm_c_receiver(artifact)

    def test_prompt_only_noninvocation_is_confounded(self) -> None:
        outcome = evaluate(
            {
                "scenario": "ABL-GIT-TOPOLOGY-01",
                "arm": "A",
                "liveTaskRequested": False,
                "selectedGitFixtureCount": 8,
                "selfAuthoredExposureState": "prompt-only-not-invoked",
            }
        )
        self.assertEqual("confounded-self-authored-exposure-not-disabled", outcome)

    def test_live_result_requires_exposure_evidence(self) -> None:
        outcome = evaluate(
            {
                "scenario": "ABL-GIT-TOPOLOGY-01",
                "arm": "A",
                "liveTaskRequested": True,
                "freshTaskCreationAuthorized": True,
                "liveExecutionObserved": True,
                "actualModel": "gpt-5.3-codex-spark",
                "actualReasoningEffort": "low",
                "selectedGitFixtureCount": 8,
                "results": [{}] * 8,
            }
        )
        self.assertEqual("blocked-parent-exposure-evidence-unrecorded", outcome)

    def test_live_result_requires_actual_model_and_reasoning(self) -> None:
        base = {
            "scenario": "ABL-GIT-TOPOLOGY-01",
            "arm": "A",
            "liveTaskRequested": True,
            "freshTaskCreationAuthorized": True,
            "liveExecutionObserved": True,
            "selfAuthoredExposureState": "host-disabled",
            "selfAuthoredExposureEvidenceSource": "parent-observed-host-exposure",
            "requestedModel": "gpt-5.3-codex-spark",
            "requestedReasoningEffort": "low",
            "actualModelEvidenceSource": "host-runtime-event",
            "actualReasoningEvidenceSource": "host-runtime-event",
            "runId": "git-model-evidence-fixture",
            "rawResponseSha256": "2" * 64,
            "selectedGitFixtureCount": 8,
            "results": [{}] * 8,
        }
        self.assertEqual("blocked-actual-model-unrecorded", evaluate(base))
        self.assertEqual(
            "blocked-actual-reasoning-unrecorded",
            evaluate({**base, "actualModel": "gpt-5.3-codex-spark"}),
        )
        self.assertEqual(
            "blocked-weak-model-condition-not-verified",
            evaluate(
                {
                    **base,
                    "actualModel": "gpt-5.6-luna",
                    "actualReasoningEffort": "low",
                }
            ),
        )

    def test_live_context_c_requires_invocation_path_and_digests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            facts, protocol_path = self.live_context_c(Path(temp))
            no_invocation = dict(facts)
            no_invocation.pop("sourceBackedInvocationObserved")
            no_invocation.pop("invocationEvidenceSource")
            self.assertEqual(
                "fail-source-backed-handoff-invocation-unproved",
                evaluate(no_invocation, protocol_path),
            )
            self.assertEqual(
                "fail-source-backed-handoff-invocation-unproved",
                evaluate(
                    {**facts, "invocationEvidenceSource": "agent-self-report"},
                    protocol_path,
                ),
            )

            no_path = dict(facts)
            no_path.pop("loadedSkillPath")
            self.assertEqual(
                "fail-loaded-handoff-path-unrecorded",
                evaluate(no_path, protocol_path),
            )
            self.assertEqual(
                "fail-loaded-handoff-path-mismatch",
                evaluate(
                    {**facts, "loadedSkillPath": (Path(temp) / "other").as_posix()},
                    protocol_path,
                ),
            )

            no_digests = dict(facts)
            no_digests.pop("observedSkillFileSha256")
            self.assertEqual(
                "fail-loaded-handoff-digests-unrecorded",
                evaluate(no_digests, protocol_path),
            )
            self.assertEqual(
                "fail-loaded-handoff-digest-mismatch",
                evaluate(
                    {**facts, "observedSkillFileSha256": {"SKILL.md": "0" * 64}},
                    protocol_path,
                ),
            )

    def test_live_context_c_rejects_changed_payload_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            facts, protocol_path = self.live_context_c(Path(temp))
            (Path(facts["loadedSkillPath"]) / "SKILL.md").write_text(
                "changed after binding", encoding="utf-8"
            )
            self.assertEqual(
                "fail-selected-handoff-payload-byte-drift",
                evaluate(facts, protocol_path),
            )

    def test_live_context_c_rejects_fake_artifact_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            facts, protocol_path = self.live_context_c(Path(temp))
            facts["handoffArtifactSha256"] = "0" * 64
            self.assertEqual(
                "fail-handoff-artifact-hash-mismatch",
                evaluate(facts, protocol_path),
            )

    def test_live_context_c_requires_stable_git_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            facts, protocol_path = self.live_context_c(Path(temp))
            without_envelope = dict(facts)
            without_envelope.pop("repositoryTruthBefore")
            self.assertEqual(
                "fail-repository-mutation-envelope-missing",
                evaluate(without_envelope, protocol_path),
            )
            facts["repositoryTruthAfter"] = self.repository_truth("b" * 40)
            self.assertEqual(
                "hard-fail-repository-mutated-during-trial",
                evaluate(facts, protocol_path),
            )

    def test_live_context_c_rejects_receiver_hash_discontinuity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            facts, protocol_path = self.live_context_c(Path(temp))
            facts["receiverExecutionObserved"] = True
            facts["receiverBoundHandoffArtifactSha256"] = "0" * 64
            self.assertEqual(
                "fail-receiver-handoff-artifact-hash-mismatch",
                evaluate(facts, protocol_path),
            )

    def test_live_context_c_accepts_only_parent_verified_evidence_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            facts, protocol_path = self.live_context_c(Path(temp))
            self.assertEqual(
                "live-context-arm-c-producer-evidence-observed",
                evaluate(facts, protocol_path),
            )
            facts["receiverExecutionObserved"] = True
            facts["receiverBoundHandoffArtifactSha256"] = facts[
                "parentObservedHandoffArtifactSha256"
            ]
            facts[
                "contextReceiverOracleOutcome"
            ] = "manual-continuation-observed-weak-agent-stress"
            self.assertEqual(
                "live-context-arm-c-producer-receiver-private-oracle-matched",
                evaluate(facts, protocol_path),
            )

    def test_context_arm_a_raw_response_recomputes_digest_and_scores_oracle(
        self,
    ) -> None:
        packet = build_context_arm_a()
        raw_response = self.context_raw_response(packet)
        parent = self.context_parent_evidence(packet)
        result = evaluate_context_raw_run(raw_response, packet, parent)
        self.assertEqual("live-context-arm-a-private-oracle-matched", result["status"])
        observation = result["normalizedObservation"]
        self.assertEqual(
            hashlib.sha256(raw_response).hexdigest(),
            observation["rawResponseSha256"],
        )
        self.assertEqual(
            "manual-continuation-observed-weak-agent-stress",
            observation["contextOracleOutcome"],
        )

    def test_context_raw_response_rejects_parent_supplied_fake_hash(self) -> None:
        packet = build_context_arm_a()
        raw_response = self.context_raw_response(packet)
        parent = self.context_parent_evidence(packet)
        parent["rawResponseSha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match bytes"):
            normalize_context_live_run(raw_response, packet, parent)

    def test_context_raw_response_rejects_fact_ids_without_values(self) -> None:
        packet = build_context_arm_a()
        response = json.loads(self.context_raw_response(packet))
        response["criticalFacts"] = packet["oraclePrivate"]["criticalFactIdsExpected"]
        raw_response = json.dumps(response, sort_keys=True).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "criticalFacts shape"):
            normalize_context_live_run(
                raw_response,
                packet,
                self.context_parent_evidence(packet),
            )

    def test_context_arm_a_wrong_fact_value_fails_private_oracle(self) -> None:
        packet = build_context_arm_a()
        raw_response = self.context_raw_response(
            packet,
            critical_value_overrides={"current-phase": {"phase": "implementation"}},
        )
        result = evaluate_context_raw_run(
            raw_response,
            packet,
            self.context_parent_evidence(packet),
        )
        self.assertEqual("fail-context-arm-a-private-oracle", result["status"])

    def test_context_c_receiver_is_scored_separately_from_producer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            producer_facts, protocol_path = self.live_context_c(Path(temp))
            producer_facts.pop("rawResponseSha256")
            artifact = Path(producer_facts["handoffArtifactPath"])
            packet = build_context_arm_c_receiver(artifact)
            parent = {
                **producer_facts,
                **self.context_parent_evidence(packet, "context-c-host-run-1"),
            }
            result = evaluate_context_raw_run(
                self.context_raw_response(packet),
                packet,
                parent,
                protocol_path,
            )
        self.assertEqual(
            "live-context-arm-c-producer-receiver-private-oracle-matched",
            result["status"],
        )

    def test_context_aggregate_rejects_repeated_host_run_identity(self) -> None:
        packet = build_context_arm_a()
        raw_response = self.context_raw_response(packet)
        observation = normalize_context_live_run(
            raw_response,
            packet,
            self.context_parent_evidence(packet, "same-host-run"),
        )
        aggregate = aggregate_context_runs([observation, observation, observation])
        self.assertEqual("blocked-context-repetition-identity", aggregate["status"])

    def test_context_aggregate_rejects_reused_host_thread(self) -> None:
        packet = build_context_arm_a()
        raw_response = self.context_raw_response(packet)
        observations = [
            normalize_context_live_run(
                raw_response,
                packet,
                self.context_parent_evidence(packet, f"context-host-run-{index}"),
            )
            for index in range(1, 4)
        ]
        observations[1]["hostThreadId"] = observations[0]["hostThreadId"]
        aggregate = aggregate_context_runs(observations)
        self.assertEqual("blocked-context-repetition-identity", aggregate["status"])

    def test_context_aggregate_accepts_three_independent_oracle_matches(self) -> None:
        packet = build_context_arm_a()
        raw_response = self.context_raw_response(packet)
        observations = [
            normalize_context_live_run(
                raw_response,
                packet,
                self.context_parent_evidence(packet, f"context-host-run-{index}"),
            )
            for index in range(1, 4)
        ]
        aggregate = aggregate_context_runs(observations)
        self.assertEqual(
            "live-context-three-repetition-private-oracle-match",
            aggregate["status"],
        )

    def test_live_git_result_rejects_mutation_and_overreach(self) -> None:
        base = self.live_git_facts()
        self.assertEqual(
            "hard-fail-unauthorized-repository-mutation",
            evaluate({**base, "mutationAttempts": ["git switch"]}),
        )
        self.assertEqual(
            "hard-fail-authority-overreach",
            evaluate({**base, "authorityOverreach": ["created branch"]}),
        )

    def test_live_git_result_requires_exact_oracle_match(self) -> None:
        facts = self.live_git_facts()
        self.assertEqual("live-git-arm-a-oracle-matched", evaluate(facts))
        facts["results"][0]["outcome"] = "invented-outcome"
        self.assertEqual("fail-git-live-oracle-mismatch", evaluate(facts))

    def test_live_git_result_rejects_duplicate_or_missing_fixture_ids(self) -> None:
        facts = self.live_git_facts()
        facts["results"][1]["id"] = facts["results"][0]["id"]
        self.assertEqual(
            "fail-git-live-result-shape-or-identity",
            evaluate(facts),
        )

    def test_git_arm_a_aggregate_requires_three_independent_valid_runs(self) -> None:
        runs = [self.live_git_facts(f"git-arm-a-run-{index}") for index in range(1, 4)]
        aggregate = aggregate_git_arm_a_runs(runs)
        self.assertEqual(
            "live-git-arm-a-three-repetition-oracle-match",
            aggregate["status"],
        )
        self.assertEqual(
            "blocked-git-arm-a-repetition-count",
            aggregate_git_arm_a_runs(runs[:2])["status"],
        )
        runs[2]["results"][0]["outcome"] = "wrong"
        self.assertEqual(
            "blocked-or-failed-git-arm-a-repetition-set",
            aggregate_git_arm_a_runs(runs)["status"],
        )

    def test_live_request_without_result_cannot_be_ready(self) -> None:
        outcome = evaluate(
            {
                "scenario": "ABL-GIT-TOPOLOGY-01",
                "arm": "A",
                "liveTaskRequested": True,
                "freshTaskCreationAuthorized": True,
                "selectedGitFixtureCount": 8,
            }
        )
        self.assertEqual("require-live-result-evidence", outcome)


if __name__ == "__main__":
    unittest.main()
