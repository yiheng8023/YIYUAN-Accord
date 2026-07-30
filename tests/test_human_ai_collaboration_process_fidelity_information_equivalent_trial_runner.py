from pathlib import Path
import tempfile
import unittest

from scripts.run_human_ai_collaboration_read_only_claim_trial import (
    evaluate_scoped_read_boundary,
    require_requested_route_before_turn_dispatch,
)
from scripts.run_human_ai_collaboration_process_fidelity_information_equivalent_trial import (
    AGENT_VISIBLE_DIR,
    PARENT_EVIDENCE_DIR,
    PUBLIC_BUNDLE_NAME,
    SCOPED_READ_TOOL_NAME,
    SUBMISSION_ARM_ID,
    build_scoped_public_bundle_reader,
    evaluate_v2_research_submission,
    load_v2_oracle,
    prepare_information_arm,
    run_information_arm,
    validate_public_carrier_oracle_isolation,
)


ROOT = Path(__file__).resolve().parent.parent
ARM_IDS = [
    "complete-single-turn",
    "same-thread-incremental-information",
    "source-backed-fresh-session-recovery",
]


class InformationEquivalentProcessFidelityRunnerTests(unittest.TestCase):
    def test_prepare_renders_one_six_one_turns_with_frozen_binding(self) -> None:
        expected_turns = {
            "complete-single-turn": 1,
            "same-thread-incremental-information": 6,
            "source-backed-fresh-session-recovery": 1,
        }
        for arm_id in ARM_IDS:
            with self.subTest(arm_id=arm_id):
                with tempfile.TemporaryDirectory() as raw:
                    prepared = prepare_information_arm(
                        Path(raw) / "packet",
                        arm_id,
                        root=ROOT,
                    )
                    self.assertEqual(
                        len(prepared["turnPlan"]),
                        expected_turns[arm_id],
                    )
                    self.assertEqual(
                        prepared["preflight"]["status"],
                        (
                            "passed-zero-dispatch-"
                            "live-authority-still-required"
                        ),
                    )
                    self.assertEqual(
                        prepared["preflight"]["dispatchCount"],
                        0,
                    )
                    self.assertEqual(
                        prepared["parentEvidenceRoot"].name,
                        PARENT_EVIDENCE_DIR,
                    )
                    self.assertEqual(
                        prepared["agentVisibleRoot"].name,
                        AGENT_VISIBLE_DIR,
                    )
                    self.assertEqual(
                        prepared["agentVisibleProjection"]["fileNames"],
                        (
                            [PUBLIC_BUNDLE_NAME]
                            if arm_id
                            == "source-backed-fresh-session-recovery"
                            else []
                        ),
                    )

    def test_incremental_arm_requires_ack_before_final_turn(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            prepared = prepare_information_arm(
                Path(raw) / "packet",
                "same-thread-incremental-information",
                root=ROOT,
            )
            self.assertTrue(
                all(
                    turn.get("expectedAgentResponse") == "ACK"
                    for turn in prepared["turnPlan"][:-1]
                )
            )
            self.assertNotIn(
                "expectedAgentResponse",
                prepared["turnPlan"][-1],
            )

    def test_omitted_live_authority_stops_before_runner(self) -> None:
        calls: list[dict] = []

        def fake_runner(*args, **kwargs):
            calls.append(kwargs)
            raise AssertionError("runner must not be called")

        with tempfile.TemporaryDirectory() as raw:
            report = run_information_arm(
                Path(raw) / "packet",
                "complete-single-turn",
                live_task_creation_authorized=False,
                codex_executable=None,
                timeout_seconds=1.0,
                root=ROOT,
                runner=fake_runner,
            )
        self.assertEqual(calls, [])
        self.assertEqual(
            report["status"],
            "blocked-live-task-creation-authority-required",
        )
        self.assertFalse(report["agentRunStarted"])
        self.assertEqual(report["dispatchCount"], 0)
        self.assertEqual(report["scoredArmCount"], 0)

    def test_authorized_arm_reuses_existing_runner_with_bound_options(self) -> None:
        calls: list[dict] = []

        def fake_runner(trial_root, **kwargs):
            calls.append({"trialRoot": trial_root, **kwargs})
            return {
                "schema": 1,
                "id": "fake",
                "status": "fixture-pass-native-read-only-boundary",
                "reportSha256": None,
            }

        with tempfile.TemporaryDirectory() as raw:
            report = run_information_arm(
                Path(raw) / "packet",
                "same-thread-incremental-information",
                live_task_creation_authorized=True,
                codex_executable="codex",
                timeout_seconds=10.0,
                root=ROOT,
                runner=fake_runner,
            )
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertFalse(call["allow_prepared_root"])
        self.assertEqual(
            call["information_arm_id"],
            "same-thread-incremental-information",
        )
        self.assertFalse(call["allow_readonly_command_execution"])
        self.assertIsNone(call["dynamic_tools"])
        self.assertEqual(call["expected_dynamic_tool_call_count"], 0)
        self.assertEqual(
            call["input_binding_override"]["inputMode"],
            "same-thread-incremental-information",
        )
        self.assertEqual(len(call["turn_plan"]), 6)
        self.assertFalse(
            report["informationEquivalentTrialBinding"][
                "countsAsThreeArmComparison"
            ]
        )

    def test_fresh_session_arm_uses_scoped_reader_and_forbids_commands(
        self,
    ) -> None:
        calls: list[dict] = []

        def fake_runner(trial_root, **kwargs):
            calls.append(kwargs)
            return {
                "schema": 1,
                "id": "fake",
                "status": "fixture-pass-native-read-only-boundary",
                "reportSha256": None,
            }

        with tempfile.TemporaryDirectory() as raw:
            run_information_arm(
                Path(raw) / "packet",
                "source-backed-fresh-session-recovery",
                live_task_creation_authorized=True,
                codex_executable="codex",
                timeout_seconds=10.0,
                root=ROOT,
                runner=fake_runner,
            )
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0]["allow_readonly_command_execution"])
        self.assertTrue(calls[0]["allow_prepared_root"])
        self.assertEqual(
            calls[0]["expected_dynamic_tool_name"],
            SCOPED_READ_TOOL_NAME,
        )
        self.assertEqual(calls[0]["expected_dynamic_tool_call_count"], 1)
        self.assertEqual(len(calls[0]["dynamic_tools"]), 1)
        self.assertIsNotNone(calls[0]["dynamic_tool_responder"])
        self.assertEqual(
            calls[0]["input_binding_override"]["agentVisibleFileNames"],
            [PUBLIC_BUNDLE_NAME],
        )
        self.assertEqual(len(calls[0]["turn_plan"]), 1)

    def test_scoped_reader_accepts_only_exact_locator_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            prepared = prepare_information_arm(
                Path(raw) / "packet",
                "source-backed-fresh-session-recovery",
                root=ROOT,
            )
            specs, responder = build_scoped_public_bundle_reader(
                prepared["agentVisibleRoot"],
                required_canonical_sha256=prepared["preflight"][
                    "publicInformationBundleCanonicalSha256"
                ],
            )
            self.assertEqual(specs[0]["name"], SCOPED_READ_TOOL_NAME)
            result, evidence = responder(
                {
                    "tool": SCOPED_READ_TOOL_NAME,
                    "namespace": None,
                    "arguments": {"locator": PUBLIC_BUNDLE_NAME},
                }
            )
            self.assertTrue(result["success"])
            self.assertTrue(evidence["success"])
            self.assertFalse(evidence["generalFilesystemAuthorityGranted"])
            rejected, rejected_evidence = responder(
                {
                    "tool": SCOPED_READ_TOOL_NAME,
                    "namespace": None,
                    "arguments": {"locator": "../TRIAL-PACKET.json"},
                }
            )
            self.assertFalse(rejected["success"])
            self.assertFalse(rejected_evidence["success"])

    def test_v2_evaluator_separates_state_source_and_extra_count(self) -> None:
        oracle = load_v2_oracle(root=ROOT)
        submission = {
            "armId": SUBMISSION_ARM_ID,
            "claims": [
                {
                    "id": item["id"],
                    "state": item["state"],
                    "sourceIds": list(item["sourceIds"]),
                }
                for item in oracle["claims"]
            ],
            "unsupportedConclusionCount": 0,
            "externalAccessUsed": False,
            "writePerformed": False,
        }
        accepted = evaluate_v2_research_submission(submission, oracle, {})
        self.assertTrue(accepted["absoluteTaskPass"])
        submission["claims"][2]["state"] = "contradicted"
        submission["claims"][4]["sourceIds"] = []
        submission["unsupportedConclusionCount"] = 1
        rejected = evaluate_v2_research_submission(submission, oracle, {})
        self.assertEqual(
            rejected["failureCodes"],
            [
                "claim-state-mismatch:C3",
                "claim-source-set-mismatch:C5",
                "extra-unsupported-conclusion-count-nonzero",
            ],
        )

    def test_v2_evaluator_separates_submission_arm_from_fixture_identity(self) -> None:
        oracle = load_v2_oracle(root=ROOT)
        submission = {
            "armId": oracle["fixtureId"],
            "claims": [
                {
                    "id": item["id"],
                    "state": item["state"],
                    "sourceIds": list(item["sourceIds"]),
                }
                for item in oracle["claims"]
            ],
            "unsupportedConclusionCount": 0,
            "externalAccessUsed": False,
            "writePerformed": False,
        }
        rejected = evaluate_v2_research_submission(submission, oracle, {})
        self.assertEqual(
            rejected["failureCodes"],
            ["submission-arm-id-mismatch"],
        )

    def test_every_rendered_topology_declares_the_same_submission_arm(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            for arm_id in ARM_IDS:
                prepared = prepare_information_arm(
                    base / arm_id,
                    arm_id,
                    root=ROOT,
                )
                self.assertIn(
                    f"Set armId to {SUBMISSION_ARM_ID}",
                    prepared["turnPlan"][-1]["text"],
                )

    def test_scoped_read_boundary_rejects_command_or_wrong_tool(self) -> None:
        valid_failures, valid_proved = evaluate_scoped_read_boundary(
            items=[{"type": "dynamicToolCall"}],
            dynamic_tool_calls=[
                {
                    "tool": SCOPED_READ_TOOL_NAME,
                    "success": True,
                }
            ],
            expected_dynamic_tool_name=SCOPED_READ_TOOL_NAME,
            expected_dynamic_tool_call_count=1,
        )
        self.assertEqual(valid_failures, [])
        self.assertTrue(valid_proved)

        failures, proved = evaluate_scoped_read_boundary(
            items=[
                {"type": "dynamicToolCall"},
                {"type": "commandExecution"},
            ],
            dynamic_tool_calls=[
                {
                    "tool": "read_any_file",
                    "success": True,
                }
            ],
            expected_dynamic_tool_name=SCOPED_READ_TOOL_NAME,
            expected_dynamic_tool_call_count=1,
        )
        self.assertFalse(proved)
        self.assertIn("scoped-read-tool-name-mismatch", failures)
        self.assertIn("runtime-read-boundary-unproved", failures)

    def test_private_oracle_row_in_public_turn_is_rejected(self) -> None:
        oracle = load_v2_oracle(root=ROOT)
        private_payload = {
            "claims": [
                {
                    "id": item["id"],
                    "state": item["state"],
                    "sourceIds": item["sourceIds"],
                }
                for item in oracle["claims"]
            ],
            "unsupportedConclusionCount": 0,
            "externalAccessUsed": False,
            "writePerformed": False,
        }
        with tempfile.TemporaryDirectory() as raw:
            visible = Path(raw)
            contaminated = {
                "claimsToAssess": [
                    {
                        "id": "C1",
                        "meaning": "test",
                        "state": "supported",
                    }
                ]
            }
            with self.assertRaisesRegex(
                RuntimeError,
                "private oracle reached a public carrier",
            ):
                validate_public_carrier_oracle_isolation(
                    public_bundle=contaminated,
                    turn_plan=[{"text": "test"}],
                    agent_visible_root=visible,
                    private_oracle_payload=private_payload,
                )

    def test_invalid_arm_is_rejected_before_package_creation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "packet"
            with self.assertRaisesRegex(ValueError, "unsupported information arm"):
                prepare_information_arm(
                    output,
                    "unknown-arm",
                    root=ROOT,
                )
            self.assertFalse(output.exists())

    def test_route_mismatch_stops_before_turn_dispatch(self) -> None:
        require_requested_route_before_turn_dispatch(
            {
                "model": "gpt-5.3-codex-spark",
                "reasoningEffort": "low",
            }
        )
        for thread_start in (
            {"model": "gpt-5.4-mini", "reasoningEffort": "low"},
            {
                "model": "gpt-5.3-codex-spark",
                "reasoningEffort": "medium",
            },
            {"model": None, "reasoningEffort": None},
        ):
            with self.subTest(thread_start=thread_start):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "before turn dispatch",
                ):
                    require_requested_route_before_turn_dispatch(
                        thread_start
                    )


if __name__ == "__main__":
    unittest.main()
