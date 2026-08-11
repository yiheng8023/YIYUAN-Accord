from copy import deepcopy
from contextlib import contextmanager, redirect_stderr
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import verify as verify_script  # noqa: E402
from contracts import ContractError  # noqa: E402
from revalidate_skill_ablation_host_transaction import (  # noqa: E402
    canonical_sha256 as canonical_skill_ablation_revalidation_sha256,
)
from inventory_closeout_cleanup_debt import (  # noqa: E402
    canonical_sha256 as canonical_cleanup_preview_sha256,
)
from build_skill_source_lineage_collision_index import (  # noqa: E402
    canonical_sha256 as canonical_lineage_index_sha256,
)


SELECTION_DOCUMENT = "sources/addyosmani-agent-skills/selection.json"


@contextmanager
def without_task4_manifest_poc_replay():
    with patch.object(
        verify_script,
        "validate_harness_decision_packet_manifest_poc",
    ) as task4_validator, patch.object(
        verify_script,
        "validate_program_acceptance_authority_v2_rehearsal",
        return_value={},
        create=True,
    ):
        yield task4_validator


class SourceSelectionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.selection = verify_script.load(SELECTION_DOCUMENT)

    def assert_verify_rejects(self, selection: dict[str, object]) -> None:
        original_load = verify_script.load

        def load_with_mutation(path: str) -> dict[str, object]:
            if path == SELECTION_DOCUMENT:
                return deepcopy(selection)
            return original_load(path)

        with patch.object(
            verify_script,
            "load",
            side_effect=load_with_mutation,
        ), without_task4_manifest_poc_replay():
            with self.assertRaises(ValueError):
                verify_script.verify()

    def test_rejects_selection_with_wrong_source(self) -> None:
        selection = {**self.selection, "source": "github:example/other"}

        self.assert_verify_rejects(selection)

    def test_rejects_selection_missing_nonadopt_candidate(self) -> None:
        selection = deepcopy(self.selection)
        decisions = selection["decisions"]
        name = next(
            name for name, disposition in decisions.items() if disposition != "adopt"
        )
        del decisions[name]

        self.assert_verify_rejects(selection)

    def test_rejects_selection_with_zero_adopts(self) -> None:
        selection = deepcopy(self.selection)
        selection["decisions"] = {
            name: "merge" if disposition == "adopt" else disposition
            for name, disposition in selection["decisions"].items()
        }

        self.assert_verify_rejects(selection)


class StructuralValidationIntegrationTests(unittest.TestCase):
    def test_unrelated_verifier_mutation_helper_skips_task4_matrix(self) -> None:
        path = "registry/program-acceptance-map.json"
        document = verify_script.load(path)
        document["objectives"][0]["acceptanceIds"] = ["acceptance.missing"]

        with patch.object(
            verify_script,
            "validate_harness_decision_packet_manifest_poc",
        ) as task4_validator:
            self.assert_verify_runtime_error(
                path,
                document,
                "unknown acceptance id",
            )

        task4_validator.assert_not_called()

    def test_normal_verify_invokes_task4_validator_once(self) -> None:
        with patch.object(
            verify_script,
            "validate_harness_decision_packet_manifest_poc",
        ) as task4_validator:
            verify_script.verify()

        task4_validator.assert_called_once_with(verify_script.ROOT)

    def test_verify_calls_acceptance_authority_v2_rehearsal_once(self) -> None:
        with patch.object(
            verify_script,
            "validate_program_acceptance_authority_v2_rehearsal",
            return_value={},
            # Do not create a missing production verifier alias in this test.
        ) as validator:
            verify_script.verify()

        validator.assert_called_once_with(verify_script.ROOT)

    def test_acceptance_authority_v2_rehearsal_is_required_verifier_input(self) -> None:
        for path in (
            "schemas/program-acceptance-authority-v2.schema.json",
            "schemas/program-acceptance-current-selector-v1.schema.json",
            "schemas/program-acceptance-transition-receipt-v1.schema.json",
            "schemas/program-acceptance-migration-inventory-v1.schema.json",
            "scripts/program_acceptance_authority_v2.py",
            "scripts/program_acceptance_migration_inventory.py",
            "scripts/program_acceptance_authority_v2_rehearsal.py",
            "scripts/build_program_acceptance_authority_v2_rehearsal.py",
            "scripts/validate_program_acceptance_authority_v2_rehearsal.py",
            "tests/test_program_acceptance_authority_v2.py",
            "tests/test_program_acceptance_migration_inventory.py",
            "tests/test_program_acceptance_authority_v2_rehearsal.py",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/curation-program-plan-v2.json",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/snapshots/v2/g000001.json",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/snapshots/v2/g000002.json",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000000-to-g000001.json",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000001-to-g000002.json",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/transitions/g000002-to-g000001-rollback.json",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/selectors/current-g000002.json",
            "tests/fixtures/program-acceptance-authority-v2-rehearsal/selectors/current-g000001-rollback.json",
            "registry/program-acceptance-authority-v2-migration-inventory-2026-08-10.json",
            "registry/program-acceptance-authority-v2-zero-model-rehearsal-2026-08-10.json",
            "docs/strategy/PROGRAM-ACCEPTANCE-AUTHORITY-V2-ZERO-MODEL-REHEARSAL-2026-08-10.md",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_tdd_successor_contract_is_integrated_into_narrative_surfaces(
        self,
    ) -> None:
        successor_name = (
            "HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-DISPATCH-"
            "SUCCESSOR-CONTRACT-V2-2026-07-27.md"
        )
        for path in (
            "docs/curation-program-plan.md",
            "docs/strategy/RESEARCH-AND-POC-PLAN.md",
            "docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md",
            "docs/operations/CONTINUATION.md",
        ):
            text = (verify_script.ROOT / path).read_text(encoding="utf-8")
            self.assertIn(successor_name, text, msg=f"{path} lacks successor")
            self.assertIn("NO-GO", text, msg=f"{path} lacks NO-GO boundary")
            self.assertRegex(
                text,
                r"does not authorize|no model or candidate dispatch is authorized",
                msg=f"{path} lacks live-effect boundary",
            )

    def test_current_identity_surfaces_do_not_use_retired_topology_names(self) -> None:
        for path in (
            "README.md",
            "README.zh-CN.md",
            "docs/curation-harness-model.md",
            "docs/public-private-boundary.md",
            "docs/starred-capability-source-discovery.md",
            "docs/superpowers/specs/2026-07-15-production-capability-manager-design.md",
        ):
            text = (verify_script.ROOT / path).read_text(encoding="utf-8").casefold()
            for phrase in (
                "yiyuan-meridian",
                "resource-radar",
                "open-resource-governance",
                "upstream radar",
                "retired matrix",
            ):
                self.assertNotIn(phrase, text, msg=f"{path} retains {phrase}")

    def test_admission_and_routing_contracts_are_required_verifier_inputs(self) -> None:
        for path in (
            "registry/admissions.json",
            "registry/routing.json",
            "schemas/v1/admissions.schema.json",
            "schemas/v1/routing.schema.json",
            "scripts/build_release_manifest.py",
            "generated/routing-index.json",
            "registry/scenarios.json",
            "schemas/v1/scenarios.schema.json",
            "scripts/simulate_routing.py",
            "generated/routing-simulation-report.json",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_schema2_capability_contract_is_a_required_verifier_input(self) -> None:
        self.assertIn(
            "schemas/v2/capabilities.schema.json", verify_script.REQUIRED_FILES
        )

    def test_context_continuation_protocol_is_a_required_verifier_input(self) -> None:
        for path in (
            "docs/context-continuation-paired-trial-protocol-2026-07-19.md",
            "scripts/build_context_continuation_trial_packet.py",
            "scripts/evaluate_context_continuation_trial.py",
            "tests/fixtures/context-continuation-paired-trial-2026-07-19.json",
            "tests/test_context_continuation_trial_packet.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_context_continuation_protocol_rejects_fixture_expectation_drift(self) -> None:
        document = verify_script.load(
            "tests/fixtures/context-continuation-paired-trial-2026-07-19.json"
        )
        document["fixtures"][-1]["expected"] = "manual-continuation-observed-baseline"
        with self.assertRaisesRegex(RuntimeError, "deterministic fixture failed"):
            verify_script.validate_context_continuation_trial_protocol(document)

    def test_context_continuation_protocol_rejects_sol_as_baseline(self) -> None:
        document = verify_script.load(
            "tests/fixtures/context-continuation-paired-trial-2026-07-19.json"
        )
        document["trialArms"][0]["requestedModelId"] = "gpt-5.6-sol"
        with self.assertRaisesRegex(RuntimeError, "baseline model selection drifted"):
            verify_script.validate_context_continuation_trial_protocol(document)

    def test_context_continuation_protocol_rejects_mandatory_pair(self) -> None:
        document = verify_script.load(
            "tests/fixtures/context-continuation-paired-trial-2026-07-19.json"
        )
        document["executionPolicy"]["pairedRunAlwaysRequired"] = True
        with self.assertRaisesRegex(RuntimeError, "conditional execution policy"):
            verify_script.validate_context_continuation_trial_protocol(document)

    def test_context_handoff_packet_freshness_is_required(self) -> None:
        for path in (
            "docs/context-handoff-packet-freshness-2026-07-24.md",
            "registry/context-handoff-packet-freshness-2026-07-24.json",
            "tests/fixtures/context-handoff-packet-freshness-2026-07-24.json",
            "scripts/validate_context_handoff_packet_freshness.py",
            "tests/test_context_handoff_packet_freshness.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_context_handoff_packet_freshness_rejects_claim_promotion(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/context-handoff-packet-freshness-2026-07-24.json"
        )
        fixture = verify_script.load(
            "tests/fixtures/context-handoff-packet-freshness-2026-07-24.json"
        )
        document["claimBoundary"]["createsThread"] = True
        with self.assertRaisesRegex(RuntimeError, "contract drifted"):
            verify_script.validate_context_handoff_packet_freshness_contract(
                document,
                fixture,
            )

    def test_context_handoff_packet_freshness_requires_prompt_tamper_case(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/context-handoff-packet-freshness-2026-07-24.json"
        )
        fixture = verify_script.load(
            "tests/fixtures/context-handoff-packet-freshness-2026-07-24.json"
        )
        fixture["cases"] = [
            case
            for case in fixture["cases"]
            if case["id"] != "prompt-tamper"
        ]
        with self.assertRaisesRegex(RuntimeError, "fixture drifted"):
            verify_script.validate_context_handoff_packet_freshness_contract(
                document,
                fixture,
            )

    def test_context_handoff_packet_freshness_rejects_boundary_promotions(
        self,
    ) -> None:
        fixture = verify_script.load(
            "tests/fixtures/context-handoff-packet-freshness-2026-07-24.json"
        )
        for key in (
            "provesAtomicSnapshot",
            "provesSourceSemanticFreshness",
        ):
            with self.subTest(key=key):
                document = verify_script.load(
                    "registry/context-handoff-packet-freshness-2026-07-24.json"
                )
                document["claimBoundary"][key] = True
                with self.assertRaisesRegex(RuntimeError, "contract drifted"):
                    verify_script.validate_context_handoff_packet_freshness_contract(
                        document,
                        fixture,
                    )

    def test_git_topology_protocol_is_a_required_verifier_input(self) -> None:
        for path in (
            "docs/git-topology-decision-poc-2026-07-19.md",
            "scripts/evaluate_git_topology_trial.py",
            "scripts/observe_git_snapshot.py",
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json",
            "tests/test_git_snapshot_integration.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_git_topology_protocol_rejects_fixture_expectation_drift(self) -> None:
        document = verify_script.load(
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"
        )
        document["fixtures"][-1]["expected"] = "recommend-isolated-worktree"
        with self.assertRaisesRegex(RuntimeError, "deterministic fixture failed"):
            verify_script.validate_git_topology_trial_protocol(document)

    def test_git_topology_protocol_rejects_user_repository_mutation_authority(self) -> None:
        document = verify_script.load(
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"
        )
        document["authorityBoundary"]["userRepositoryMutationAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary drifted"):
            verify_script.validate_git_topology_trial_protocol(document)

    def test_git_topology_protocol_rejects_live_remote_integration_overclaim(self) -> None:
        document = verify_script.load(
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"
        )
        document["integrationEvidence"]["claimBoundary"]["provesExternalRemoteFreshness"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            verify_script.validate_git_topology_trial_protocol(document)

    def test_git_topology_protocol_requires_observed_copy_path_boundary(self) -> None:
        document = verify_script.load(
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"
        )
        document["integrationEvidence"]["claimBoundary"][
            "provesCopyPathEnumeration"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            verify_script.validate_git_topology_trial_protocol(document)

    def test_git_topology_protocol_requires_content_conflict_observation_boundary(
        self,
    ) -> None:
        document = verify_script.load(
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"
        )
        document["integrationEvidence"]["claimBoundary"][
            "provesDisposableContentConflictStatusObservation"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            verify_script.validate_git_topology_trial_protocol(document)

    def test_git_topology_protocol_rejects_conflict_recovery_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"
        )
        document["integrationEvidence"]["claimBoundary"][
            "provesConflictResolutionOrAbortSafety"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            verify_script.validate_git_topology_trial_protocol(document)

    def test_git_topology_protocol_rejects_filesystem_zero_write_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "tests/fixtures/git-topology-decision-fixtures-2026-07-19.json"
        )
        document["integrationEvidence"]["claimBoundary"][
            "provesFilesystemZeroWriteObserver"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary drifted"):
            verify_script.validate_git_topology_trial_protocol(document)

    def test_mcp_current_host_inventory_is_a_required_verifier_input(self) -> None:
        for path in (
            "docs/mcp-current-host-inventory-2026-07-19.md",
            "registry/mcp-current-host-inventory-2026-07-19.json",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_mcp_current_host_inventory_rejects_lifecycle_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-current-host-inventory-2026-07-19.json"
        )
        document["authorityBoundary"]["mcpEnableDisable"] = True
        with self.assertRaisesRegex(RuntimeError, "authority overclaim"):
            verify_script.validate_mcp_current_host_inventory(document)

    def test_mcp_current_host_inventory_rejects_resource_attribution_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-current-host-inventory-2026-07-19.json"
        )
        document["processObservation"]["resourceSnapshot"][
            "specificMcpResourceAttribution"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "resource attribution overclaim"):
            verify_script.validate_mcp_current_host_inventory(document)

    def test_mcp_current_host_inventory_reconciles_resource_totals(self) -> None:
        document = verify_script.load(
            "registry/mcp-current-host-inventory-2026-07-19.json"
        )
        document["processObservation"]["resourceSnapshot"]["byName"][0][
            "workingSetBytes"
        ] += 1
        with self.assertRaisesRegex(RuntimeError, "aggregate does not reconcile"):
            verify_script.validate_mcp_current_host_inventory(document)

    def test_mcp_runtime_refresh_contract_is_required(self) -> None:
        for path in (
            "docs/mcp-runtime-refresh-interface-and-trial-protocol-2026-07-19.md",
            "registry/mcp-runtime-refresh-interface-review-2026-07-19.json",
            "registry/codex-app-server-isolated-mcp-status-probe-2026-07-19.json",
            "docs/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.json",
            "docs/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json",
            "docs/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.json",
            "docs/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.md",
            "registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json",
            "docs/mcp-app-server-0.145.0-reload-release-attribution-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-reload-release-attribution-evidence-2026-07-27.json",
            "docs/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.md",
            "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.json",
            "tests/fixtures/mcp-runtime-refresh-trial-2026-07-19.json",
            "scripts/evaluate_mcp_runtime_refresh_trial.py",
            "tests/test_mcp_runtime_refresh_trial.py",
            "scripts/probe_codex_app_server_mcp_status.py",
            "tests/test_codex_app_server_mcp_status_probe.py",
            "scripts/mcp_lifecycle_sentinel.py",
            "scripts/probe_codex_app_server_mcp_tool_call.py",
            "scripts/probe_codex_app_server_mcp_idle_unload.py",
            "scripts/probe_codex_app_server_mcp_startup_profiles.py",
            "scripts/probe_codex_app_server_mcp_child_exit_recovery.py",
            "scripts/probe_codex_app_server_mcp_reload_release_attribution.py",
            "scripts/validate_mcp_reload_release_attribution_evidence.py",
            "scripts/probe_codex_app_server_mcp_thread_unsubscribe_release_attribution.py",
            "scripts/validate_mcp_thread_unsubscribe_release_attribution_evidence.py",
            "tests/test_codex_app_server_mcp_tool_call_probe.py",
            "tests/test_codex_app_server_mcp_idle_unload_probe.py",
            "tests/test_codex_app_server_mcp_startup_profiles_probe.py",
            "tests/test_codex_app_server_mcp_child_exit_recovery_probe.py",
            "tests/test_codex_app_server_mcp_reload_release_attribution_probe.py",
            "tests/test_mcp_reload_release_attribution_evidence.py",
            "tests/test_codex_app_server_mcp_thread_unsubscribe_release_attribution_probe.py",
            "tests/test_mcp_thread_unsubscribe_release_attribution_evidence.py",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/README.md",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/run-01.json",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/formal-01.json",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/formal-02.json",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/formal-03.json",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/evidence-01.json",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/evidence-02.json",
            "audits/mcp-reload-release-attribution-0.145.0-2026-07-27/evidence-03.json",
            "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-2026-07-27/README.md",
            "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-2026-07-27/calibration-01.json",
            "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-2026-07-27/evidence-01.json",
            "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-2026-07-27/evidence-02.json",
            "audits/mcp-thread-unsubscribe-release-attribution-0.145.0-2026-07-27/evidence-03.json",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_verify_invokes_reload_release_attribution_validator(self) -> None:
        path = (
            "registry/mcp-app-server-0.145.0-reload-release-attribution-"
            "evidence-2026-07-27.json"
        )
        document = verify_script.load(path)
        document["claimBoundary"]["taskEndImmediateReleaseProved"] = True
        original_load = verify_script.load

        def load_with_mutation(candidate: str) -> dict[str, object]:
            if candidate == path:
                return deepcopy(document)
            return original_load(candidate)

        with patch.object(
            verify_script,
            "load",
            side_effect=load_with_mutation,
        ), without_task4_manifest_poc_replay():
            with self.assertRaisesRegex(
                RuntimeError,
                "Reload-release claim boundary drifted",
            ):
                verify_script.verify()

    def test_verify_invokes_thread_unsubscribe_attribution_validator(
        self,
    ) -> None:
        path = (
            "registry/mcp-app-server-0.145.0-thread-unsubscribe-release-"
            "attribution-evidence-2026-07-27.json"
        )
        document = verify_script.load(path)
        document["claimBoundary"]["unsubscribeIsTaskEndProved"] = True
        original_load = verify_script.load

        def load_with_mutation(candidate: str) -> dict[str, object]:
            if candidate == path:
                return deepcopy(document)
            return original_load(candidate)

        with patch.object(
            verify_script,
            "load",
            side_effect=load_with_mutation,
        ), without_task4_manifest_poc_replay():
            with self.assertRaisesRegex(
                RuntimeError,
                "Thread-unsubscribe claim boundary drifted",
            ):
                verify_script.verify()

    def test_codex_isolated_mcp_status_probe_rejects_reload_overclaim(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-isolated-mcp-status-probe-2026-07-19.json"
        )
        document["unsupportedClaims"]["runtimeRefreshObserved"] = True
        with self.assertRaisesRegex(RuntimeError, "unsupported behavior overclaimed"):
            verify_script.validate_codex_app_server_isolated_mcp_status_probe(document)

    def test_codex_isolated_mcp_status_probe_rejects_request_firewall_drift(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-isolated-mcp-status-probe-2026-07-19.json"
        )
        document["runner"]["requestMethods"].append("config/mcpServer/reload")
        with self.assertRaisesRegex(RuntimeError, "request firewall"):
            verify_script.validate_codex_app_server_isolated_mcp_status_probe(document)

    def test_mcp_runtime_refresh_rejects_live_release_overclaim(self) -> None:
        review = verify_script.load(
            "registry/mcp-runtime-refresh-interface-review-2026-07-19.json"
        )
        trial = verify_script.load(
            "tests/fixtures/mcp-runtime-refresh-trial-2026-07-19.json"
        )
        review["claimClassification"]["oldRuntimeOrProcessReleaseObserved"] = True
        with self.assertRaisesRegex(RuntimeError, "live behavior overclaimed"):
            verify_script.validate_mcp_runtime_refresh_interface_and_trial(
                review, trial
            )

    def test_mcp_runtime_refresh_rejects_fixture_expectation_drift(self) -> None:
        review = verify_script.load(
            "registry/mcp-runtime-refresh-interface-review-2026-07-19.json"
        )
        trial = verify_script.load(
            "tests/fixtures/mcp-runtime-refresh-trial-2026-07-19.json"
        )
        trial["fixtures"][-1]["expected"] = (
            "observed-runtime-refresh-release-still-unknown"
        )
        with self.assertRaisesRegex(RuntimeError, "deterministic fixture failed"):
            verify_script.validate_mcp_runtime_refresh_interface_and_trial(
                review, trial
            )

    def test_mcp_0_145_direct_call_rejects_single_instance_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.json"
        )
        document["primaryLiveProbe"]["runtimeInstances"][
            "singleRuntimeInstanceProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "live probe evidence"):
            verify_script.validate_mcp_app_server_0_145_direct_tool_call_evidence(
                document
            )

    def test_mcp_0_145_direct_call_rejects_idle_release_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["thirtyMinuteIdleUnloadProved"] = True
        with self.assertRaisesRegex(RuntimeError, "lifecycle behavior overclaimed"):
            verify_script.validate_mcp_app_server_0_145_direct_tool_call_evidence(
                document
            )

    def test_mcp_0_145_direct_call_rejects_exact_instance_cleanup_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.json"
        )
        document["primaryLiveProbe"]["shutdownObservation"][
            "exactInstanceCleanupProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "live probe evidence"):
            verify_script.validate_mcp_app_server_0_145_direct_tool_call_evidence(
                document
            )

    def test_mcp_0_145_direct_call_requires_all_attempt_manifests(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.json"
        )
        document["repeatedObservation"]["perAttemptEventManifests"].pop()
        with self.assertRaisesRegex(RuntimeError, "repeated evidence"):
            verify_script.validate_mcp_app_server_0_145_direct_tool_call_evidence(
                document
            )

    def test_mcp_0_145_direct_call_rejects_hot_switch_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["sameThreadHotEnableDisableProved"] = True
        with self.assertRaisesRegex(RuntimeError, "lifecycle behavior overclaimed"):
            verify_script.validate_mcp_app_server_0_145_direct_tool_call_evidence(
                document
            )

    def test_mcp_0_145_new_thread_rejects_reload_causation_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-new-thread-reload-evidence-2026-07-23.json"
        )
        document["claimBoundary"][
            "newThreadStateChangeCausedByReloadProved"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "lifecycle behavior overclaimed"):
            verify_script.validate_mcp_app_server_0_145_new_thread_reload_evidence(
                document
            )

    def test_mcp_0_145_new_thread_rejects_status_runtime_equivalence(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-new-thread-reload-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["statusEqualsLoadedThreadRuntimeProved"] = True
        with self.assertRaisesRegex(RuntimeError, "lifecycle behavior overclaimed"):
            verify_script.validate_mcp_app_server_0_145_new_thread_reload_evidence(
                document
            )

    def test_mcp_0_145_new_thread_requires_five_classified_instances(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-new-thread-reload-evidence-2026-07-23.json"
        )
        document["processObservation"]["instances"].pop()
        with self.assertRaisesRegex(RuntimeError, "process evidence"):
            verify_script.validate_mcp_app_server_0_145_new_thread_reload_evidence(
                document
            )

    def test_mcp_0_145_idle_unload_requires_actual_thirty_minutes(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json"
        )
        document["idleObservation"]["actualDurationMilliseconds"] = 1799999
        with self.assertRaisesRegex(RuntimeError, "timing evidence"):
            verify_script.validate_mcp_app_server_0_145_idle_unload_evidence(
                document
            )

    def test_mcp_0_145_idle_unload_rejects_causation_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["threadClosedCausedSentinelExitProved"] = True
        with self.assertRaisesRegex(RuntimeError, "behavior overclaimed"):
            verify_script.validate_mcp_app_server_0_145_idle_unload_evidence(
                document
            )

    def test_mcp_0_145_idle_unload_rejects_resource_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.json"
        )
        document["resourceObservation"]["singleRunProvesStableResourceSavings"] = True
        with self.assertRaisesRegex(RuntimeError, "resource boundary"):
            verify_script.validate_mcp_app_server_0_145_idle_unload_evidence(
                document
            )

    def test_mcp_0_145_startup_profiles_reject_hot_switch_overclaim(self) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["sameThreadHotSwitchingProved"] = True
        with self.assertRaisesRegex(RuntimeError, "behavior overclaimed"):
            verify_script.validate_mcp_app_server_0_145_startup_profile_evidence(
                document
            )

    def test_mcp_0_145_startup_profiles_require_disabled_zero_processes(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.json"
        )
        document["profiles"]["disabled"]["sentinelInstancesPerRun"] = [0, 1]
        with self.assertRaisesRegex(RuntimeError, "functional evidence"):
            verify_script.validate_mcp_app_server_0_145_startup_profile_evidence(
                document
            )

    def test_mcp_0_145_startup_profiles_reject_filter_resource_claim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["toolFilteringReducesResourceUseProved"] = True
        with self.assertRaisesRegex(RuntimeError, "behavior overclaimed"):
            verify_script.validate_mcp_app_server_0_145_startup_profile_evidence(
                document
            )

    def test_mcp_0_145_child_exit_rejects_same_thread_recovery_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["sameThreadRecoveryProved"] = True
        with self.assertRaisesRegex(RuntimeError, "recovery overclaimed"):
            verify_script.validate_mcp_app_server_0_145_child_exit_recovery_evidence(
                document
            )

    def test_mcp_0_145_child_exit_rejects_generic_controller_claim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["genericRecoveryControllerJustified"] = True
        with self.assertRaisesRegex(RuntimeError, "recovery overclaimed"):
            verify_script.validate_mcp_app_server_0_145_child_exit_recovery_evidence(
                document
            )

    def test_mcp_0_145_child_exit_preserves_run02_owned_kill_evidence(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.json"
        )
        document["runs"][1]["appServerHandleKillSent"] = False
        with self.assertRaisesRegex(RuntimeError, "run02 appServerHandleKillSent"):
            verify_script.validate_mcp_app_server_0_145_child_exit_recovery_evidence(
                document
            )

    def test_skill_portfolio_and_closeout_gate_is_required(self) -> None:
        for path in (
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json",
            "docs/strategy/RESEARCH-AND-POC-PLAN.md",
            "docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md",
            "docs/strategy/SKILL-PORTFOLIO-REBASELINE-AND-CLOSEOUT-GATES.md",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_skill_portfolio_gate_rejects_parallel_manager(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["decision"]["parallelManagerImplementationAllowed"] = True
        with self.assertRaisesRegex(RuntimeError, "CC Switch reuse decision"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_skill_portfolio_gate_rejects_parallel_physical_runtime_authority(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["decision"]["onePhysicalRuntimeAuthorityPerSharedSkill"] = False
        with self.assertRaisesRegex(RuntimeError, "CC Switch reuse decision"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_skill_portfolio_gate_allows_zero_self_authored_payloads(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["decision"]["selfAuthoredPayloadCountMayBeZero"] = False
        with self.assertRaisesRegex(RuntimeError, "CC Switch reuse decision"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_skill_portfolio_gate_rejects_universal_paired_model_requirement(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["weakAgentValidationPolicy"]["allPocsRequirePairedModelRuns"] = True
        with self.assertRaisesRegex(RuntimeError, "weak-Agent validation policy"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_closeout_gate_rejects_implied_deletion_authority(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["closeoutGate"]["completionImpliesDeletionAuthority"] = True
        with self.assertRaisesRegex(RuntimeError, "cleanup requirement"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_inherited_payload_migration_gate_rejects_bulk_catalog_removal(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["inheritedPayloadMigrationGate"]["bulkNameOrCatalogPresenceIsSufficient"] = True
        with self.assertRaisesRegex(RuntimeError, "migration gate"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_inherited_payload_migration_gate_requires_behavioral_equivalence(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["inheritedPayloadMigrationGate"][
            "nameDescriptionContentDirectoryOrCatalogMatchIsSufficient"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "migration gate"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_skill_portfolio_gate_rejects_navigation_evidence_promotion(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json"
        )
        document["datedNavigationEvidence"][0]["currentInventoryEvidence"] = True
        with self.assertRaisesRegex(RuntimeError, "dated navigation evidence"):
            verify_script.validate_skill_portfolio_and_closeout_gate(document)

    def test_skill_portfolio_inventory_is_a_required_verifier_input(self) -> None:
        for path in (
            "docs/skill-portfolio-and-closeout-inventory-2026-07-19.md",
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json",
            "scripts/inventory_skill_portfolio.py",
            "tests/test_skill_portfolio_inventory.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_skill_portfolio_inventory_rejects_cleanup_authority_overclaim(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json"
        )
        document["claimBoundary"]["authorizesCleanupOrDeletion"] = True
        with self.assertRaisesRegex(RuntimeError, "authority overclaim"):
            verify_script.validate_skill_portfolio_and_closeout_inventory(document)

    def test_skill_portfolio_inventory_requires_exact_bootstrap_cleanup_targets(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json"
        )
        bootstrap_item = next(
            item
            for item in document["closeoutInventory"]
            if item["purpose"] == "bootstrap-copies-patch-scan-input-and-stale-plan-snapshot"
        )
        bootstrap_item["targets"] = []
        with self.assertRaisesRegex(RuntimeError, "closeout item is incomplete"):
            verify_script.validate_skill_portfolio_and_closeout_inventory(document)

    def test_skill_portfolio_inventory_tracks_mcp_schema_temp_artifact(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json"
        )
        mcp_item = next(
            item
            for item in document["closeoutInventory"]
            if item["purpose"] == "mcp-stable-and-experimental-app-server-schema-generation"
        )
        self.assertEqual(
            mcp_item["targets"],
            ["C:/tmp/agent-autonomy-harness-mcp-schema-20260719"],
        )
        self.assertEqual(mcp_item["disposition"], "retain-authoritative")
        self.assertFalse(mcp_item["eligibleForCurrentAction"])

    def test_skill_portfolio_inventory_tracks_isolated_mcp_status_homes(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json"
        )
        item = next(
            item
            for item in document["closeoutInventory"]
            if item["purpose"] == "isolated-codex-app-server-status-probe-failed-and-successful-homes"
        )
        self.assertEqual(len(item["targets"]), 2)
        self.assertEqual(item["disposition"], "retain-authoritative")
        self.assertFalse(item["eligibleForCurrentAction"])

    def test_skill_portfolio_inventory_tracks_mcp_0_145_direct_call_roots(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json"
        )
        item = next(
            item
            for item in document["closeoutInventory"]
            if item["purpose"]
            == "codex-0.145.0-direct-mcp-tool-call-schema-and-five-isolated-probe-roots"
        )
        self.assertEqual(len(item["targets"]), 6)
        self.assertEqual(item["disposition"], "retain-authoritative")
        self.assertFalse(item["eligibleForCurrentAction"])

    def test_skill_portfolio_inventory_tracks_comparative_treatment_cleanup_targets(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json"
        )
        self.assertEqual(len(document["closeoutInventory"]), 10)
        item = next(
            item
            for item in document["closeoutInventory"]
            if item["purpose"]
            == "weak-agent-incident-treatment-fidelity-and-source-pin-temporary-artifacts"
        )
        self.assertEqual(len(item["targets"]), 43)
        self.assertEqual(item["disposition"], "delete-after-authorization")
        self.assertFalse(item["eligibleForCurrentAction"])

    def test_skill_portfolio_inventory_rejects_current_cleanup_phase(self) -> None:
        document = verify_script.load(
            "registry/skill-portfolio-and-closeout-inventory-2026-07-19.json"
        )
        document["currentCleanupPhase"] = True
        with self.assertRaisesRegex(RuntimeError, "timing boundary"):
            verify_script.validate_skill_portfolio_and_closeout_inventory(document)

    def test_source_pinned_debugging_projection_protocol_is_required(self) -> None:
        for path in (
            "registry/source-pinned-debugging-skill-projection-protocol-2026-07-24.json",
            "docs/source-pinned-debugging-skill-projection-protocol-2026-07-24.md",
            "scripts/build_source_pinned_skill_projection.py",
            "scripts/probe_source_pinned_skill_projection_preflight.py",
            "scripts/validate_source_pinned_debugging_skill_projection_protocol.py",
            "tests/test_source_pinned_skill_projection.py",
            "tests/test_source_pinned_skill_projection_preflight.py",
            "registry/source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24.json",
            "docs/source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24.md",
            "scripts/validate_source_pinned_debugging_skill_projection_preflight_evidence.py",
            "tests/test_source_pinned_debugging_skill_projection_preflight_evidence.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_closeout_cleanup_debt_preview_is_a_required_verifier_input(
        self,
    ) -> None:
        for path in (
            "docs/closeout-cleanup-debt-preview-2026-07-24.md",
            "registry/closeout-cleanup-debt-preview-2026-07-24.json",
            "scripts/inventory_closeout_cleanup_debt.py",
            "tests/test_closeout_cleanup_debt_preview.py",
            "docs/closeout-cleanup-execution-2026-07-30.md",
            "registry/closeout-cleanup-execution-2026-07-30.json",
            "scripts/validate_closeout_cleanup_execution.py",
            "tests/test_closeout_cleanup_execution.py",
            "audits/mcp-thread-creator-connection-close-calibration-attempt-2026-07-27/normalized-evidence.json",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_closeout_cleanup_debt_preview_rejects_deletion_authority(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/closeout-cleanup-debt-preview-2026-07-24.json"
        )
        document["authorityBoundary"]["deletionAuthorized"] = True
        document["reportSha256"] = canonical_cleanup_preview_sha256(
            {
                key: value
                for key, value in document.items()
                if key != "reportSha256"
            }
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "hard-fail-authority-promotion",
        ):
            verify_script.validate_closeout_cleanup_debt_preview(document)

    def test_closeout_cleanup_debt_preview_is_frozen_historical_evidence(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/closeout-cleanup-debt-preview-2026-07-24.json"
        )
        verify_script.validate_closeout_cleanup_debt_preview(document)

    def test_program_acceptance_keeps_final_cleanup_as_a_partial_exact_target_gate(
        self,
    ) -> None:
        acceptance = verify_script.load("registry/program-acceptance-map.json")
        program = verify_script.load("registry/curation-program-plan.json")
        criterion = next(
            item
            for item in acceptance["acceptanceCriteria"]
            if item["id"] == "acceptance.final-program-cleanup-gate"
        )
        self.assertEqual(criterion["assessment"], "partial")
        self.assertIn(
            "evidence.closeout-cleanup-debt-preview-2026-07-24",
            criterion["evidenceIds"],
        )
        self.assertIn(
            "evidence.closeout-cleanup-execution-2026-07-30",
            criterion["evidenceIds"],
        )
        gate = next(
            item
            for item in program["sequenceGates"]
            if item["id"] == "gate.final-program-cleanup-before-final-closeout"
        )
        self.assertEqual(gate["blockedUntil"], "any declared final program closeout")

    def test_rejects_final_cleanup_gate_without_separate_authority(
        self,
    ) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        gate = next(
            item
            for item in document["sequenceGates"]
            if item["id"] == "gate.final-program-cleanup-before-final-closeout"
        )
        gate["prerequisite"] = gate["prerequisite"].replace(
            "separate cleanup authority, ",
            "",
        )
        self.assert_verify_runtime_error(
            path,
            document,
            "final cleanup gate missing boundary: separate cleanup authority",
        )

    def test_skill_source_authority_reconciliation_is_required(self) -> None:
        for path in (
            "docs/skill-source-authority-and-runtime-reconciliation-2026-07-19.md",
            "registry/skill-source-authority-and-runtime-reconciliation-2026-07-19.json",
            "scripts/reconcile_skill_source_authority.py",
            "tests/test_skill_source_authority_reconciliation.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_skill_source_authority_rejects_runtime_install_inference(self) -> None:
        document = verify_script.load(
            "registry/skill-source-authority-and-runtime-reconciliation-2026-07-19.json"
        )
        document["decisions"]["installRuntimeMatchesIntoCcToEqualizeCounts"] = True
        with self.assertRaisesRegex(RuntimeError, "reuse decision"):
            verify_script.validate_skill_source_authority_reconciliation(document)

    def test_skill_source_authority_rejects_projection_repair_authority(self) -> None:
        document = verify_script.load(
            "registry/skill-source-authority-and-runtime-reconciliation-2026-07-19.json"
        )
        document["authorityBoundary"]["projectionRepairAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "mutation overclaim"):
            verify_script.validate_skill_source_authority_reconciliation(document)

    def test_skill_source_lineage_collision_index_is_required(self) -> None:
        for path in (
            "docs/skill-source-lineage-collision-index-2026-07-24.md",
            "registry/skill-source-lineage-collision-index-2026-07-24.json",
            "scripts/build_skill_source_lineage_collision_index.py",
            "tests/test_skill_source_lineage_collision_index.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_skill_source_lineage_collision_index_rejects_migration_authority(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-source-lineage-collision-index-2026-07-24.json"
        )
        document["authorityBoundary"]["migrationAuthorized"] = True
        document["reportSha256"] = canonical_lineage_index_sha256(
            {
                key: value
                for key, value in document.items()
                if key != "reportSha256"
            }
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "hard-fail-authorityBoundary-promotion",
        ):
            verify_script.validate_skill_source_lineage_collision_index(
                document
            )

    def test_skill_source_lineage_collision_index_rejects_derived_drift(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-source-lineage-collision-index-2026-07-24.json"
        )
        rebuilt = deepcopy(document)
        rebuilt["groups"][0]["collisionRelation"] = "equal"
        rebuilt["reportSha256"] = canonical_lineage_index_sha256(
            {
                key: value
                for key, value in rebuilt.items()
                if key != "reportSha256"
            }
        )
        with patch.object(
            verify_script,
            "build_skill_source_lineage_collision_index",
            return_value=rebuilt,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "derived record drifted",
            ):
                verify_script.validate_skill_source_lineage_collision_index(
                    document
                )

    def test_skill_source_lineage_collision_index_rejects_upstream_as_local_provenance(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-source-lineage-collision-index-2026-07-24.json"
        )
        legacy_matt = next(
            group
            for group in document["groups"]
            if group["id"] == "legacy-matt-mapped-mixed-snapshot"
        )
        legacy_matt["immutableRevisionOrUnknown"] = legacy_matt[
            "reviewedUpstreamRevision"
        ]
        document["reportSha256"] = canonical_lineage_index_sha256(
            {
                key: value
                for key, value in document.items()
                if key != "reportSha256"
            }
        )
        with self.assertRaisesRegex(RuntimeError, "legacy Matt boundary"):
            verify_script.validate_skill_source_lineage_collision_index(
                document
            )

    def test_cc_switch_recovery_gap_and_overlap_matrix_are_required(self) -> None:
        for path in (
            "docs/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.md",
            "registry/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.json",
            "docs/cc-switch-3.18-recovery-preflight-2026-07-23.md",
            "registry/cc-switch-3.18-recovery-preflight-2026-07-23.json",
            "docs/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.md",
            "registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json",
            "scripts/build_cc_skill_recovery_snapshot.py",
            "tests/test_build_cc_skill_recovery_snapshot.py",
            "docs/skill-ablation-cli-host-preflight-2026-07-23.md",
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json",
            "docs/context-evidence-envelope-2026-07-23.md",
            "registry/context-evidence-envelope-2026-07-23.json",
            "docs/strategy/SKILL-ECOSYSTEM-OVERLAP-AND-ABLATION-MATRIX-2026-07-23.md",
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json",
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json",
            "scripts/evaluate_skill_overlap_attribution.py",
            "tests/test_skill_overlap_attribution.py",
            "tests/fixtures/skill-overlap-scenario-packets-2026-07-23.json",
            "scripts/evaluate_skill_overlap_scenarios.py",
            "tests/test_skill_overlap_scenarios.py",
            "docs/mcp-task-lifecycle-evidence-contract-2026-07-23.md",
            "registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json",
            "tests/fixtures/mcp-task-lifecycle-evidence-2026-07-23.json",
            "scripts/evaluate_mcp_task_lifecycle_evidence.py",
            "tests/test_mcp_task_lifecycle_evidence.py",
            "docs/skill-live-run-evidence-contract-2026-07-23.md",
            "registry/skill-live-run-evidence-contract-2026-07-23.json",
            "tests/fixtures/skill-live-run-evidence-2026-07-23.json",
            "scripts/evaluate_skill_live_run_evidence.py",
            "tests/test_skill_live_run_evidence.py",
            "docs/strategy/EXPERIMENT-CONTRACT-REUSE-MAP-2026-07-23.md",
            "registry/experiment-contract-reuse-map-2026-07-23.json",
            "docs/git-host-authorization-trial-contract-2026-07-23.md",
            "registry/git-host-authorization-trial-contract-2026-07-23.json",
            "docs/context-pressure-advisory-contract-2026-07-23.md",
            "registry/context-pressure-advisory-contract-2026-07-23.json",
            "tests/fixtures/context-pressure-advisory-2026-07-23.json",
            "scripts/evaluate_context_pressure_advisory.py",
            "tests/test_context_pressure_advisory.py",
            "docs/instruction-carrier-adherence-contract-2026-07-23.md",
            "registry/instruction-carrier-adherence-contract-2026-07-23.json",
            "tests/fixtures/instruction-carrier-adherence-2026-07-23.json",
            "scripts/evaluate_instruction_carrier_adherence.py",
            "tests/test_instruction_carrier_adherence.py",
            "docs/instruction-carrier-trial-preflight-contract-2026-07-23.md",
            "registry/instruction-carrier-trial-preflight-contract-2026-07-23.json",
            "scripts/build_instruction_carrier_trial_packet.py",
            "tests/test_instruction_carrier_trial_packet.py",
            "docs/git-host-preflight-evidence-contract-2026-07-23.md",
            "registry/git-host-preflight-evidence-contract-2026-07-23.json",
            "tests/fixtures/git-host-preflight-evidence-2026-07-23.json",
            "scripts/evaluate_git_host_preflight_evidence.py",
            "tests/test_git_host_preflight_evidence.py",
            "docs/mcp-task-selection-decision-contract-2026-07-23.md",
            "registry/mcp-task-selection-decision-contract-2026-07-23.json",
            "tests/fixtures/mcp-task-selection-decision-2026-07-23.json",
            "scripts/evaluate_mcp_task_selection_decision.py",
            "tests/test_mcp_task_selection_decision.py",
            "docs/handoff-loader-trial-preflight-contract-2026-07-24.md",
            "registry/handoff-loader-trial-preflight-contract-2026-07-24.json",
            "scripts/build_handoff_loader_trial_packet.py",
            "tests/test_handoff_loader_trial_packet.py",
            "docs/git-readonly-preflight-envelope-contract-2026-07-24.md",
            "registry/git-readonly-preflight-envelope-contract-2026-07-24.json",
            "scripts/build_git_readonly_preflight_envelope.py",
            "tests/test_git_readonly_preflight_envelope.py",
            "docs/mcp-lifecycle-trial-skeleton-contract-2026-07-24.md",
            "registry/mcp-lifecycle-trial-skeleton-contract-2026-07-24.json",
            "tests/fixtures/mcp-lifecycle-trial-skeleton-2026-07-24.json",
            "scripts/build_mcp_lifecycle_trial_skeleton.py",
            "tests/test_mcp_lifecycle_trial_skeleton.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_instruction_carrier_preflight_rejects_live_claim(self) -> None:
        document = verify_script.load(
            "registry/instruction-carrier-trial-preflight-contract-2026-07-23.json"
        )
        document["claimBoundary"]["builderCountsAsLiveHostProof"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_instruction_carrier_trial_preflight_contract(
                document
            )

    def test_git_host_preflight_rejects_bound_repository_claim(self) -> None:
        document = verify_script.load(
            "registry/git-host-preflight-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/git-host-preflight-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["boundUserRepositoryPreflightProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_git_host_preflight_evidence_contract(
                document,
                fixtures,
            )

    def test_git_host_preflight_rejects_fixture_promotion(self) -> None:
        document = verify_script.load(
            "registry/git-host-preflight-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/git-host-preflight-evidence-2026-07-23.json"
        )
        fixtures["fixtures"][0]["expectedStatus"] = (
            "live-bound-repository-safety-proved"
        )
        with self.assertRaisesRegex(RuntimeError, "fixtures drifted"):
            verify_script.validate_git_host_preflight_evidence_contract(
                document,
                fixtures,
            )

    def test_mcp_task_selection_rejects_always_on_policy(self) -> None:
        document = verify_script.load(
            "registry/mcp-task-selection-decision-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
        )
        document["policy"]["defaultPermanentActivation"] = True
        with self.assertRaisesRegex(RuntimeError, "policy drifted"):
            verify_script.validate_mcp_task_selection_decision_contract(
                document,
                fixtures,
            )

    def test_mcp_task_selection_rejects_actuation_claim(self) -> None:
        document = verify_script.load(
            "registry/mcp-task-selection-decision-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
        )
        document["claimBoundary"]["mcpActivationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_mcp_task_selection_decision_contract(
                document,
                fixtures,
            )

    def test_mcp_task_selection_rejects_fixture_promotion(self) -> None:
        document = verify_script.load(
            "registry/mcp-task-selection-decision-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
        )
        fixtures["fixtures"][0]["expectedStatus"] = (
            "live-activation-and-release-proved"
        )
        with self.assertRaisesRegex(RuntimeError, "fixtures drifted"):
            verify_script.validate_mcp_task_selection_decision_contract(
                document,
                fixtures,
            )

    def test_handoff_loader_preflight_rejects_claim_promotion(self) -> None:
        document = verify_script.load(
            "registry/handoff-loader-trial-preflight-contract-2026-07-24.json"
        )
        document["claimBoundary"]["loaderInvocationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_handoff_loader_trial_preflight_contract(document)

    def test_handoff_loader_preflight_rejects_shape_only_capture_admission(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/handoff-loader-trial-preflight-contract-2026-07-24.json"
        )
        document["captureCapabilityEvidenceRegistry"]["claimBoundary"][
            "shapeValidReferenceIsAdmissionEvidence"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "capture registry"):
            verify_script.validate_handoff_loader_trial_preflight_contract(
                document
            )

    def test_git_readonly_preflight_rejects_claim_promotion(self) -> None:
        document = verify_script.load(
            "registry/git-readonly-preflight-envelope-contract-2026-07-24.json"
        )
        document["claimBoundary"]["creationSafetyProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_git_readonly_preflight_envelope_contract(document)

    def test_mcp_lifecycle_skeleton_rejects_claim_promotion(self) -> None:
        document = verify_script.load(
            "registry/mcp-lifecycle-trial-skeleton-contract-2026-07-24.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-lifecycle-trial-skeleton-2026-07-24.json"
        )
        selection_fixtures = verify_script.load(
            "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
        )
        document["claimBoundary"]["resourceBenefitProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_mcp_lifecycle_trial_skeleton_contract(
                document,
                fixtures,
                selection_fixtures,
            )

    def test_mcp_lifecycle_skeleton_rejects_fixture_promotion(self) -> None:
        document = verify_script.load(
            "registry/mcp-lifecycle-trial-skeleton-contract-2026-07-24.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-lifecycle-trial-skeleton-2026-07-24.json"
        )
        selection_fixtures = verify_script.load(
            "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
        )
        fixtures["fixtures"][1]["expectedFailures"] = []
        with self.assertRaisesRegex(RuntimeError, "fixtures drifted"):
            verify_script.validate_mcp_lifecycle_trial_skeleton_contract(
                document,
                fixtures,
                selection_fixtures,
            )

    def test_mcp_same_thread_refresh_rejects_release_claim_promotion(self) -> None:
        document = verify_script.load(
            "registry/mcp-same-thread-refresh-evidence-contract-2026-07-24.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-same-thread-refresh-evidence-2026-07-24.json"
        )
        selection_fixtures = verify_script.load(
            "tests/fixtures/mcp-task-selection-decision-2026-07-23.json"
        )
        document["claimBoundary"]["taskEndReleaseProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_mcp_same_thread_refresh_evidence_contract(
                document,
                fixtures,
                selection_fixtures,
            )

    def test_mcp_task_lifecycle_contract_rejects_live_claim(self) -> None:
        document = verify_script.load(
            "registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-task-lifecycle-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["taskEndExactExitProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_mcp_task_lifecycle_evidence_contract(
                document,
                fixtures,
            )

    def test_mcp_task_lifecycle_contract_rejects_fixture_promotion(self) -> None:
        document = verify_script.load(
            "registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-task-lifecycle-evidence-2026-07-23.json"
        )
        fixtures["fixtures"][-1]["expected"]["countsAsLiveHostProof"] = True
        with self.assertRaisesRegex(RuntimeError, "fixtures drifted"):
            verify_script.validate_mcp_task_lifecycle_evidence_contract(
                document,
                fixtures,
            )

    def test_mcp_task_lifecycle_contract_rejects_always_on_policy(self) -> None:
        document = verify_script.load(
            "registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-task-lifecycle-evidence-2026-07-23.json"
        )
        document["operatingPolicy"]["permanentlyActiveByDefault"] = True
        with self.assertRaisesRegex(RuntimeError, "operating policy drifted"):
            verify_script.validate_mcp_task_lifecycle_evidence_contract(
                document,
                fixtures,
            )

    def test_mcp_task_lifecycle_contract_rejects_premature_release_trace(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/mcp-task-lifecycle-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/mcp-task-lifecycle-evidence-2026-07-23.json"
        )
        valid = fixtures["fixtures"][-1]
        valid["facts"]["leaseReferenceTrace"].insert(
            3,
            {"event": "server-release"},
        )
        with self.assertRaisesRegex(RuntimeError, "fixtures drifted"):
            verify_script.validate_mcp_task_lifecycle_evidence_contract(
                document,
                fixtures,
            )

    def test_skill_live_run_contract_rejects_weak_acceptance_overclaim(self) -> None:
        document = verify_script.load(
            "registry/skill-live-run-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/skill-live-run-evidence-2026-07-23.json"
        )
        document["claimBoundary"]["fiveArmComparisonExecuted"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_skill_live_run_evidence_contract(
                document,
                fixtures,
            )

    def test_skill_live_run_contract_rejects_fixture_drift(self) -> None:
        document = verify_script.load(
            "registry/skill-live-run-evidence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/skill-live-run-evidence-2026-07-23.json"
        )
        fixtures["fixtures"][0]["expectedStatus"] = "live-run-evidence-valid"
        with self.assertRaisesRegex(RuntimeError, "fixtures drifted"):
            verify_script.validate_skill_live_run_evidence_contract(
                document,
                fixtures,
            )

    def test_experiment_reuse_map_rejects_duplicate_evidence_claim(self) -> None:
        document = verify_script.load(
            "registry/experiment-contract-reuse-map-2026-07-23.json"
        )
        document["mappings"][1]["claimBoundary"][
            "sameScenarioEvidenceMayBeCountedTwice"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "Git overlap reuse mapping"):
            verify_script.validate_experiment_contract_reuse_map(document)

    def test_git_host_contract_rejects_inherited_merge_authority(self) -> None:
        document = verify_script.load(
            "registry/git-host-authorization-trial-contract-2026-07-23.json"
        )
        document["phases"][2]["authorizationInheritedFromCreate"] = True
        with self.assertRaisesRegex(RuntimeError, "phase boundary overclaimed"):
            verify_script.validate_git_host_authorization_trial_contract(document)

    def test_context_pressure_contract_rejects_automatic_creation(self) -> None:
        document = verify_script.load(
            "registry/context-pressure-advisory-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/context-pressure-advisory-2026-07-23.json"
        )
        document["invariants"]["automaticThreadCreationForbidden"] = False
        with self.assertRaisesRegex(RuntimeError, "invariant drifted"):
            verify_script.validate_context_pressure_advisory_contract(
                document,
                fixtures,
            )

    def test_context_pressure_provenance_rejects_telemetry_claim(self) -> None:
        document = verify_script.load(
            "registry/context-pressure-provenance-evidence-envelope-2026-07-24.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/context-pressure-provenance-evidence-envelope-2026-07-24.json"
        )
        document["claimBoundary"]["countsAsLiveHostTelemetryProof"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_context_pressure_provenance_evidence_envelope_contract(
                document,
                fixtures,
            )

    def test_instruction_carrier_contract_rejects_universal_claim(self) -> None:
        document = verify_script.load(
            "registry/instruction-carrier-adherence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/instruction-carrier-adherence-2026-07-23.json"
        )
        document["claimBoundary"]["crossAgentParityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_instruction_carrier_adherence_contract(
                document,
                fixtures,
            )

    def test_instruction_carrier_contract_rejects_fixture_promotion(self) -> None:
        document = verify_script.load(
            "registry/instruction-carrier-adherence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/instruction-carrier-adherence-2026-07-23.json"
        )
        fixtures["fixtures"][0]["expectedStatus"] = (
            "live-host-adherence-evidence-valid"
        )
        with self.assertRaisesRegex(RuntimeError, "fixtures drifted"):
            verify_script.validate_instruction_carrier_adherence_contract(
                document,
                fixtures,
            )

    def test_instruction_carrier_contract_rejects_semantic_key_substitution(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/instruction-carrier-adherence-contract-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/instruction-carrier-adherence-2026-07-23.json"
        )
        document["requiredParentEvidence"][5] = (
            "unrelated placeholder that preserves list length"
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "parent evidence requirements drifted",
        ):
            verify_script.validate_instruction_carrier_adherence_contract(
                document,
                fixtures,
            )

        document = verify_script.load(
            "registry/instruction-carrier-adherence-contract-2026-07-23.json"
        )
        document["attributionSeparation"]["renamedUnrelatedBoundary"] = (
            document["attributionSeparation"].pop(
                "hostApprovalDoesNotProveCarrierAdherence"
            )
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "attribution separation drifted",
        ):
            verify_script.validate_instruction_carrier_adherence_contract(
                document,
                fixtures,
            )

    def test_cc_switch_live_drift_rejects_count_reconciliation_drift(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.json"
        )
        document["liveCounts"]["claudeBrokenProjections"] = 175
        with self.assertRaisesRegex(RuntimeError, "counts do not reconcile"):
            verify_script.validate_cc_switch_live_drift_and_transaction_gate(document)

    def test_cc_switch_live_drift_rejects_premature_deletion(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.json"
        )
        document["portfolioDecision"]["eligiblePayloadDeletionsNow"] = 1
        with self.assertRaisesRegex(RuntimeError, "outran the recovery evidence"):
            verify_script.validate_cc_switch_live_drift_and_transaction_gate(document)

    def test_cc_switch_live_drift_rejects_copy_only_canary_as_gate(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-live-drift-and-transaction-gate-2026-07-23.json"
        )
        document["orderedTransaction"][2] = (
            "run-copy-only-uninstall-restore-canary"
        )
        with self.assertRaisesRegex(RuntimeError, "ordered transaction gate"):
            verify_script.validate_cc_switch_live_drift_and_transaction_gate(document)

    def test_cc_switch_recovery_rejects_live_mutation_overclaim(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-recovery-preflight-2026-07-23.json"
        )
        document["liveStateMutation"]["skillDeleted"] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed live mutation"):
            verify_script.validate_cc_switch_recovery_preflight(document)

    def test_cc_switch_recovery_rejects_secret_boundary_drift(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-recovery-preflight-2026-07-23.json"
        )
        document["secretBoundary"]["settingsRead"] = True
        with self.assertRaisesRegex(RuntimeError, "secret boundary"):
            verify_script.validate_cc_switch_recovery_preflight(document)

    def test_cc_switch_recovery_rejects_projection_links_as_cloud_artifacts(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-recovery-preflight-2026-07-23.json"
        )
        document["officialCloudSyncSourceReview"][
            "agentProjectionLinksIncludedAsArtifacts"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "cloud-sync source boundary"):
            verify_script.validate_cc_switch_recovery_preflight(document)

    def test_cc_switch_recovery_rejects_fatal_skill_projection_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-recovery-preflight-2026-07-23.json"
        )
        document["officialCloudSyncSourceReview"][
            "skillProjectionFailureIsFatal"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "cloud-sync source boundary"):
            verify_script.validate_cc_switch_recovery_preflight(document)

    def test_cc_switch_stale_row_gap_rejects_supported_bulk_overclaim(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json"
        )
        document["decision"]["supportedBulkMutationAvailableNow"] = True
        with self.assertRaisesRegex(RuntimeError, "bypassed the capability gap"):
            verify_script.validate_cc_switch_stale_row_reconciliation_gap(document)

    def test_cc_switch_stale_row_gap_rejects_direct_database_repair(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json"
        )
        document["decision"]["directSqliteRepairAccepted"] = True
        with self.assertRaisesRegex(RuntimeError, "bypassed the capability gap"):
            verify_script.validate_cc_switch_stale_row_reconciliation_gap(document)

    def test_cc_switch_stale_row_gap_rejects_reversible_disable_claim(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json"
        )
        document["decision"]["perItemDisableIsReversibleWithoutSsotBody"] = True
        with self.assertRaisesRegex(RuntimeError, "bypassed the capability gap"):
            verify_script.validate_cc_switch_stale_row_reconciliation_gap(document)

    def test_cc_switch_stale_row_gap_rejects_body_canary_as_recovery(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json"
        )
        document["decision"]["bodyPresentGuiCanaryProvesMissingBodyRecovery"] = True
        with self.assertRaisesRegex(RuntimeError, "bypassed the capability gap"):
            verify_script.validate_cc_switch_stale_row_reconciliation_gap(document)

    def test_cc_switch_stale_row_gap_rejects_unobserved_gui_mutation(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-3.18-stale-row-reconciliation-gap-2026-07-23.json"
        )
        document["canaryPreflight"]["desktopControl"]["ccUiMutationOccurred"] = True
        with self.assertRaisesRegex(RuntimeError, "canary preflight"):
            verify_script.validate_cc_switch_stale_row_reconciliation_gap(document)

    def test_skill_ecosystem_matrix_rejects_superiority_claim(self) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        document["currentPortfolioDecision"]["superiorityClaimSupported"] = True
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_bulk_install(self) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        document["currentPortfolioDecision"]["bulkInstallWholeRepositories"] = True
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        with self.assertRaisesRegex(RuntimeError, "overclaimed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_content_overlap_as_equivalence(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        document["claimBoundary"]["contentOverlapProvesBehavioralEquivalence"] = True
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_host_block_as_residual_gap(self) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        document["claimBoundary"]["hostBlockedArmProvesResidualGap"] = True
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        with self.assertRaisesRegex(RuntimeError, "claim boundary overclaimed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_unpinned_matt_content_identity(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        document["baselines"]["mattPocock"]["currentContentReviewGitBlobShas"][
            "skills/engineering/implement/SKILL.md"
        ] = "unverified"
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        with self.assertRaisesRegex(RuntimeError, "source pins drifted"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_scenario_readiness_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        document["scenarios"][0]["livePacketReady"] = True
        with self.assertRaisesRegex(RuntimeError, "readiness overclaimed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_terra_as_weak_acceptance(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        document["attributionProtocol"]["terraLowCountsAsWeakAcceptance"] = True
        with self.assertRaisesRegex(RuntimeError, "attribution protocol drifted"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_cc_static_behavior_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        document["ccInstalledStaticComparisonCohort"]["claimBoundary"][
            "behavioralValueProved"
        ] = True
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        with self.assertRaisesRegex(RuntimeError, "static cohort drifted or overclaimed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_fixture_expectation_drift(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        fixtures["fixtures"][0]["expected"] = "skill-value-unobserved"
        with self.assertRaisesRegex(RuntimeError, "deterministic fixture failed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures
            )

    def test_skill_ecosystem_matrix_rejects_scenario_example_drift(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        packets = verify_script.load(
            "tests/fixtures/skill-overlap-scenario-packets-2026-07-23.json"
        )
        packets["fixtures"][0]["examples"][0]["expected"] = (
            "fail-int-unit-coverage"
        )
        with self.assertRaisesRegex(RuntimeError, "deterministic example failed"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures, packets
            )

    def test_skill_ecosystem_matrix_rejects_deterministic_packet_as_live(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ecosystem-overlap-and-ablation-matrix-2026-07-23.json"
        )
        fixtures = verify_script.load(
            "tests/fixtures/skill-overlap-attribution-fixtures-2026-07-23.json"
        )
        packets = verify_script.load(
            "tests/fixtures/skill-overlap-scenario-packets-2026-07-23.json"
        )
        packets["liveEvidenceBoundary"][
            "deterministicExamplesCountAsLiveBehavior"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "live boundary drifted"):
            verify_script.validate_skill_ecosystem_overlap_and_ablation_matrix(
                document, fixtures, packets
            )

    def test_skill_ablation_cli_preflight_rejects_model_verification_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json"
        )
        document["judgment"]["requestedModelIndependentlyVerified"] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed weak acceptance"):
            verify_script.validate_skill_ablation_cli_host_preflight(document)

    def test_skill_ablation_cli_preflight_rejects_login_side_effect(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json"
        )
        document["liveLoginStatus"]["loginAttempted"] = True
        with self.assertRaisesRegex(RuntimeError, "login boundary"):
            verify_script.validate_skill_ablation_cli_host_preflight(document)

    def test_skill_ablation_cli_preflight_rejects_spark_entitlement_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json"
        )
        document["officialSparkAvailabilityReview"][
            "currentUserPlanOrSparkEntitlementVerifiedByThisReview"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "official Spark boundary"):
            verify_script.validate_skill_ablation_cli_host_preflight(document)

    def test_skill_ablation_cli_preflight_rejects_unavailable_custom_agent_selector(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json"
        )
        document["desktopSubagentSurfaceReview"][
            "currentCallableSpawnSupportsCustomAgentSelector"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "desktop subagent surface"):
            verify_script.validate_skill_ablation_cli_host_preflight(document)

    def test_skill_ablation_cli_preflight_rejects_confounded_repetition_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json"
        )
        document["desktopSubagentSurfaceReview"][
            "threeConfoundedDiagnosticRepetitionsExecuted"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "desktop subagent surface"):
            verify_script.validate_skill_ablation_cli_host_preflight(document)

    def test_skill_ablation_cli_preflight_rejects_visible_skill_as_disabled_arm(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json"
        )
        document["claimBoundary"]["visibleSelfAuthoredSkillsCanCountAsDisabledArm"] = (
            True
        )
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            verify_script.validate_skill_ablation_cli_host_preflight(document)

    def test_codex_cli_route_diagnostic_rejects_formal_acceptance_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.json"
        )
        document["modelJudgment"]["formalWeakAgentArmExecuted"] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed acceptance"):
            verify_script.validate_codex_cli_model_route_and_mcp_startup_diagnostic(
                document
            )

    def test_codex_cli_route_diagnostic_rejects_two_visible_server_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.json"
        )
        document["mcpStartupObservation"]["visibleLogicalFailureCount"] = 2
        with self.assertRaisesRegex(RuntimeError, "MCP startup classification"):
            verify_script.validate_codex_cli_model_route_and_mcp_startup_diagnostic(
                document
            )

    def test_codex_cli_route_diagnostic_rejects_root_cause_overclaim(self) -> None:
        document = verify_script.load(
            "registry/codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.json"
        )
        document["mcpJudgment"]["rootCauseProved"] = True
        with self.assertRaisesRegex(RuntimeError, "overclaimed root cause"):
            verify_script.validate_codex_cli_model_route_and_mcp_startup_diagnostic(
                document
            )

    def test_codex_cli_route_diagnostic_rejects_raw_log_admission(self) -> None:
        document = verify_script.load(
            "registry/codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.json"
        )
        document["sensitiveEvidenceBoundary"]["rawDebugLogCopiedIntoRepository"] = (
            True
        )
        with self.assertRaisesRegex(RuntimeError, "sensitive-evidence boundary"):
            verify_script.validate_codex_cli_model_route_and_mcp_startup_diagnostic(
                document
            )

    def _rehash_codex_skill_exposure(self, document: dict) -> None:
        document["reportSha256"] = verify_script.canonical_skill_exposure_sha256(
            {
                key: value
                for key, value in document.items()
                if key != "reportSha256"
            }
        )

    def test_codex_skill_exposure_rejects_model_substitution(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-task-scoped-skill-exposure-evidence-2026-07-24.json"
        )
        document["threadTelemetry"]["model"] = "gpt-5.6-sol"
        self._rehash_codex_skill_exposure(document)

        with self.assertRaisesRegex(RuntimeError, "fail-model-mismatch"):
            verify_script.validate_codex_app_server_task_scoped_skill_exposure_evidence(
                document
            )

    def test_codex_skill_exposure_rejects_enabled_user_skill_leak(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-task-scoped-skill-exposure-evidence-2026-07-24.json"
        )
        document["exposureComparison"][
            "allDisabledUserSkillsDisabled"
        ] = False
        self._rehash_codex_skill_exposure(document)

        with self.assertRaisesRegex(RuntimeError, "fail-disabled-user-skill-leak"):
            verify_script.validate_codex_app_server_task_scoped_skill_exposure_evidence(
                document
            )

    def test_codex_skill_exposure_rejects_forbidden_action(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-task-scoped-skill-exposure-evidence-2026-07-24.json"
        )
        document["markerTurn"]["forbiddenItemTypesObserved"] = ["mcpToolCall"]
        self._rehash_codex_skill_exposure(document)

        with self.assertRaisesRegex(
            RuntimeError,
            "hard-fail-forbidden-action-observed",
        ):
            verify_script.validate_codex_app_server_task_scoped_skill_exposure_evidence(
                document
            )

    def test_codex_skill_exposure_rejects_five_arm_overclaim(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-task-scoped-skill-exposure-evidence-2026-07-24.json"
        )
        document["claimBoundary"]["provesFiveArmAblationOutcome"] = True
        self._rehash_codex_skill_exposure(document)

        with self.assertRaisesRegex(RuntimeError, "hard-fail-claim-boundary"):
            verify_script.validate_codex_app_server_task_scoped_skill_exposure_evidence(
                document
            )

    def test_codex_selected_skill_exposure_rejects_second_enabled_user(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-selected-skill-exposure-evidence-2026-07-24.json"
        )
        document["exposureComparison"]["selectedEnabledUserSkillCount"] = 2
        self._rehash_codex_skill_exposure(document)

        with self.assertRaisesRegex(RuntimeError, "fail-selected-user-skill-count"):
            verify_script.validate_codex_app_server_selected_skill_exposure_evidence(
                document
            )

    def test_codex_selected_skill_exposure_rejects_loader_overclaim(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-selected-skill-exposure-evidence-2026-07-24.json"
        )
        document["claimBoundary"]["provesSkillLoaderInvocation"] = True
        self._rehash_codex_skill_exposure(document)

        with self.assertRaisesRegex(RuntimeError, "hard-fail-claim-boundary"):
            verify_script.validate_codex_app_server_selected_skill_exposure_evidence(
                document
            )

    def test_codex_selected_skill_exposure_rejects_hidden_turn_claim(self) -> None:
        document = verify_script.load(
            "registry/codex-app-server-selected-skill-exposure-evidence-2026-07-24.json"
        )
        document["processBoundary"]["turnStarted"] = True
        self._rehash_codex_skill_exposure(document)

        with self.assertRaisesRegex(RuntimeError, "process boundary"):
            verify_script.validate_codex_app_server_selected_skill_exposure_evidence(
                document
            )

    def test_context_evidence_envelope_rejects_live_thread_overclaim(self) -> None:
        document = verify_script.load(
            "registry/context-evidence-envelope-2026-07-23.json"
        )
        document["liveEvidence"]["freshThreadTrialExecuted"] = True
        with self.assertRaisesRegex(RuntimeError, "liveEvidence overclaimed"):
            verify_script.validate_context_evidence_envelope(document)

    def test_context_evidence_envelope_rejects_boolean_only_regression(self) -> None:
        document = verify_script.load(
            "registry/context-evidence-envelope-2026-07-23.json"
        )
        document["verifiedLocal"]["negativeProbes"][0]["expected"] = (
            "manual-continuation-observed-baseline"
        )
        with self.assertRaisesRegex(RuntimeError, "falsification probes drifted"):
            verify_script.validate_context_evidence_envelope(document)

    def test_skill_ablation_batch_01_is_required(self) -> None:
        for path in (
            "docs/skill-ablation-batch-01-selection-2026-07-19.md",
            "registry/skill-ablation-batch-01-selection-2026-07-19.json",
            "docs/skill-ablation-batch-01-protocol-2026-07-19.md",
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json",
            "docs/skill-ablation-batch-01-host-preflight-2026-07-19.md",
            "registry/skill-ablation-batch-01-host-preflight-2026-07-19.json",
            "scripts/build_skill_ablation_batch_01_packet.py",
            "scripts/evaluate_skill_ablation_batch_01_protocol.py",
            "tests/test_skill_ablation_batch_01_protocol.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_skill_ablation_protocol_rejects_agent_self_report_as_loader_event(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        contract = document["liveEvidenceContract"]["contextArmC"]
        contract["agentSelfReportAccepted"] = True
        with self.assertRaisesRegex(RuntimeError, "live evidence contract drifted"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_rejects_agent_self_report_as_host_evidence(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["liveEvidenceContract"]["shared"][
            "agentSelfReportedModelReasoningOrExposureAccepted"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "live evidence contract drifted"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_rejects_single_run_as_formal_pass(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["claimBoundary"]["singleGitRunPassesFormalArm"] = True
        with self.assertRaisesRegex(RuntimeError, "claim overreach"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_rejects_single_context_run_as_formal_pass(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["claimBoundary"]["singleContextRunPassesFormalArm"] = True
        with self.assertRaisesRegex(RuntimeError, "claim overreach"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_requires_raw_context_digest_recomputation(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["liveEvidenceContract"]["shared"][
            "rawResponseDigestRecomputedFromRawUtf8Bytes"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "live evidence contract drifted"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_keeps_producer_and_receiver_quality_separate(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["claimBoundary"]["producerOnlyEvidenceProvesReceiverQuality"] = True
        with self.assertRaisesRegex(RuntimeError, "claim overreach"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_rejects_unbound_fresh_task_authority(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["authorityBoundary"]["freshTaskCreation"] = True
        with self.assertRaisesRegex(RuntimeError, "live authority overclaim"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_cli_preflight_rejects_self_report_as_host_evidence(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-cli-host-preflight-2026-07-23.json"
        )
        document["repositoryOnlyEvaluatorHardening"][
            "agentSelfReportAcceptedAsActualConditionEvidence"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "evaluator hardening drifted"):
            verify_script.validate_skill_ablation_cli_host_preflight(document)

    def test_skill_ablation_batch_01_rejects_live_task_creation_authority(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-selection-2026-07-19.json"
        )
        document["authorityBoundary"]["freshTaskCreationAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority overclaim"):
            verify_script.validate_skill_ablation_batch_01_selection(document)

    def test_skill_ablation_batch_01_rejects_self_authored_arm_c(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-selection-2026-07-19.json"
        )
        document["scenarios"][0]["armD"] = "already-enabled"
        with self.assertRaisesRegex(RuntimeError, "self-authored deferral"):
            verify_script.validate_skill_ablation_batch_01_selection(document)

    def test_skill_ablation_batch_01_rejects_hard_standard_as_variable(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-selection-2026-07-19.json"
        )
        document["ablationInvariant"]["hardStandardsAreAblationVariables"] = True
        with self.assertRaisesRegex(RuntimeError, "hard-standard invariant"):
            verify_script.validate_skill_ablation_batch_01_selection(document)

    def test_skill_ablation_batch_01_rejects_luna_terra_equivalence_overclaim(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-selection-2026-07-19.json"
        )
        document["commonAcceptance"][
            "historicalLunaAndCurrentTerraAreAutomaticallyEquivalent"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "common acceptance boundary"):
            verify_script.validate_skill_ablation_batch_01_selection(document)

    def test_skill_ablation_batch_01_rejects_external_payload_ownership(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-selection-2026-07-19.json"
        )
        document["productBodyBoundary"]["externalPayloadBecomesLongTermRepositoryOwnership"] = True
        with self.assertRaisesRegex(RuntimeError, "product body boundary"):
            verify_script.validate_skill_ablation_batch_01_selection(document)

    def test_skill_ablation_batch_01_rejects_git_guardrails_as_topology_arm(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-selection-2026-07-19.json"
        )
        git_scenario = next(
            item for item in document["scenarios"] if item["id"] == "ABL-GIT-TOPOLOGY-01"
        )
        git_scenario["armC"] = "approved-git-guardrails-exact-digest"
        with self.assertRaisesRegex(RuntimeError, "reviewed external arms"):
            verify_script.validate_skill_ablation_batch_01_selection(document)

    def test_skill_ablation_protocol_rejects_prompt_only_disable_as_proof(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["selfAuthoredExposureGate"]["promptOnlyNonInvocationRequestAccepted"] = True
        with self.assertRaisesRegex(RuntimeError, "exposure gate"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_rejects_skill_waiving_hard_standard(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["hardStandardControl"]["notCreditedAsSkillValue"] = False
        with self.assertRaisesRegex(RuntimeError, "hard-standard control"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_protocol_rejects_global_config_authority_overclaim(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["authorityBoundary"]["globalCodexConfigMutation"] = True
        with self.assertRaisesRegex(RuntimeError, "live authority overclaim"):
            verify_script.validate_skill_ablation_batch_01_protocol(document)

    def test_skill_ablation_host_preflight_rejects_formal_arm_overclaim(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-host-preflight-2026-07-19.json"
        )
        protocol = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["judgment"]["formalArmAExecuted"] = True
        with self.assertRaisesRegex(RuntimeError, "judgment drifted"):
            verify_script.validate_skill_ablation_batch_01_host_preflight(
                document, protocol
            )

    def test_skill_ablation_host_preflight_rejects_hard_standard_removal(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-host-preflight-2026-07-19.json"
        )
        protocol = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["interpretationBoundary"]["hardStandardsWereRemovalTarget"] = True
        with self.assertRaisesRegex(RuntimeError, "interpretation drifted"):
            verify_script.validate_skill_ablation_batch_01_host_preflight(
                document, protocol
            )

    def test_skill_ablation_host_preflight_rejects_diagnostic_disagreement_rewrite(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-host-preflight-2026-07-19.json"
        )
        protocol = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["capacityDiagnostic"]["comparison"][
            "visibilityMatchesWeakPreflight"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "capacity diagnostic drifted"):
            verify_script.validate_skill_ablation_batch_01_host_preflight(
                document, protocol
            )

    def test_skill_ablation_host_preflight_rejects_startup_list_loader_overclaim(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-batch-01-host-preflight-2026-07-19.json"
        )
        protocol = verify_script.load(
            "registry/skill-ablation-batch-01-protocol-2026-07-19.json"
        )
        document["officialHostBoundary"][
            "initialListAbsenceProvesLoaderUnavailable"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "list-budget boundary drifted"):
            verify_script.validate_skill_ablation_batch_01_host_preflight(
                document, protocol
            )

    def test_skill_ablation_host_transaction_rejects_authority_overclaim(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["authorityBoundary"]["globalCodexConfigMutationAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority overclaim"):
            verify_script.validate_skill_ablation_host_config_transaction(document)

    def test_skill_ablation_host_transaction_requires_exact_rollback(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["transaction"]["orderedSteps"][6] = "leave the modified config in place"
        with self.assertRaisesRegex(RuntimeError, "rollback sequence drifted"):
            verify_script.validate_skill_ablation_host_config_transaction(document)

    def test_skill_ablation_host_transaction_rejects_hard_standard_relaxation(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["hardStandardInvariant"]["skillDisableMayRelaxAcceptance"] = True
        with self.assertRaisesRegex(RuntimeError, "hard-standard invariant drifted"):
            verify_script.validate_skill_ablation_host_config_transaction(document)

    def test_skill_ablation_host_transaction_revalidation_is_required(self) -> None:
        for path in (
            "docs/skill-ablation-host-transaction-revalidation-2026-07-24.md",
            "registry/skill-ablation-host-transaction-revalidation-2026-07-24.json",
            "scripts/revalidate_skill_ablation_host_transaction.py",
            "tests/test_skill_ablation_host_transaction_revalidation.py",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_skill_ablation_revalidation_rejects_status_promotion(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-transaction-revalidation-2026-07-24.json"
        )
        transaction = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["status"] = "preconditions-match-authorization-still-required"
        body = deepcopy(document)
        body.pop("reportSha256")
        document["reportSha256"] = (
            canonical_skill_ablation_revalidation_sha256(body)
        )
        with self.assertRaisesRegex(RuntimeError, "fail-status-binding"):
            verify_script.validate_skill_ablation_host_transaction_revalidation(
                document,
                transaction,
            )

    def test_skill_ablation_revalidation_rejects_claim_promotion(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-transaction-revalidation-2026-07-24.json"
        )
        transaction = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["claimBoundary"]["countsAsSkillDisablement"] = True
        body = deepcopy(document)
        body.pop("reportSha256")
        document["reportSha256"] = (
            canonical_skill_ablation_revalidation_sha256(body)
        )
        with self.assertRaisesRegex(RuntimeError, "hard-fail-claim-promotion"):
            verify_script.validate_skill_ablation_host_transaction_revalidation(
                document,
                transaction,
            )

    def test_skill_ablation_revalidation_rejects_content_promotion(self) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-transaction-revalidation-2026-07-24.json"
        )
        transaction = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["contentBoundary"]["configContentIncluded"] = True
        body = deepcopy(document)
        body.pop("reportSha256")
        document["reportSha256"] = (
            canonical_skill_ablation_revalidation_sha256(body)
        )
        with self.assertRaisesRegex(RuntimeError, "hard-fail-content-boundary"):
            verify_script.validate_skill_ablation_host_transaction_revalidation(
                document,
                transaction,
            )

    def test_skill_ablation_revalidation_rejects_source_digest_substitution(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-transaction-revalidation-2026-07-24.json"
        )
        transaction = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["sourceContract"]["sha256"] = "0" * 64
        body = deepcopy(document)
        body.pop("reportSha256")
        document["reportSha256"] = (
            canonical_skill_ablation_revalidation_sha256(body)
        )
        with self.assertRaisesRegex(
            RuntimeError,
            "fail-source-contract-binding",
        ):
            verify_script.validate_skill_ablation_host_transaction_revalidation(
                document,
                transaction,
            )

    def test_skill_ablation_revalidation_rejects_atomic_snapshot_promotion(
        self,
    ) -> None:
        document = verify_script.load(
            "registry/skill-ablation-host-transaction-revalidation-2026-07-24.json"
        )
        transaction = verify_script.load(
            "registry/skill-ablation-host-config-transaction-2026-07-19.json"
        )
        document["cohortBoundary"]["atomicSnapshotProved"] = True
        body = deepcopy(document)
        body.pop("reportSha256")
        document["reportSha256"] = (
            canonical_skill_ablation_revalidation_sha256(body)
        )
        with self.assertRaisesRegex(RuntimeError, "hard-fail-cohort-boundary"):
            verify_script.validate_skill_ablation_host_transaction_revalidation(
                document,
                transaction,
            )

    def test_program_acceptance_map_is_a_required_verifier_input(self) -> None:
        self.assertIn(
            "registry/program-acceptance-map.json",
            verify_script.REQUIRED_FILES,
        )

    def test_production_capability_manager_design_is_a_required_verifier_input(self) -> None:
        self.assertIn(
            "docs/superpowers/specs/2026-07-15-production-capability-manager-design.md",
            verify_script.REQUIRED_FILES,
        )

    def test_production_capability_manager_gate_records_are_required(self) -> None:
        for path in (
            "registry/production-capability-manager-design-acceptance-event-2026-07-15.json",
            "registry/production-capability-manager-topology-impact-package-2026-07-15.json",
            "registry/production-capability-manager-topology-acceptance-event-2026-07-15.json",
            "registry/production-capability-manager-external-ecosystem-and-stack-review-2026-07-15.json",
            "registry/production-capability-manager-repository-slug-acceptance-event-2026-07-16.json",
            "registry/agent-capability-manager-stack-and-foundation-authorization-event-2026-07-16.json",
            "registry/agent-capability-manager-foundation-slice-plan-2026-07-16.json",
            "registry/agent-capability-manager-foundation-slice-implementation-evidence-2026-07-16.json",
            "registry/production-capability-manager-post-matrix-reintake-2026-07-17.json",
            "registry/agent-capability-manager-codex-readonly-adapter-slice-plan-2026-07-17.json",
            "registry/agent-capability-manager-codex-readonly-adapter-implementation-evidence-2026-07-17.json",
            "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json",
            "registry/cc-switch-live-source-ownership-reconciliation-2026-07-18.json",
            "registry/cc-switch-disposable-source-management-preview-2026-07-18.json",
            "registry/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.json",
            "registry/dynamic-runtime-control-gap-review-2026-07-18.json",
            "registry/legacy-curated-skill-source-migration-review-2026-07-18.json",
            "registry/adaptive-harness-source-suite-and-user-sovereignty-acceptance-event-2026-07-18.json",
            "docs/superpowers/specs/2026-07-15-production-capability-manager-topology-impact.md",
            "docs/superpowers/plans/2026-07-15-production-capability-manager-topology-gate.md",
            "docs/production-capability-manager-external-ecosystem-and-stack-review-2026-07-15.md",
            "docs/superpowers/plans/2026-07-16-agent-capability-manager-foundation-slice.md",
            "docs/agent-capability-manager-foundation-slice-implementation-evidence-2026-07-16.md",
            "docs/production-capability-manager-post-matrix-reintake-2026-07-17.md",
            "docs/superpowers/plans/2026-07-17-agent-capability-manager-codex-readonly-adapter-slice.md",
            "docs/agent-capability-manager-codex-readonly-adapter-implementation-evidence-2026-07-17.md",
            "docs/cc-switch-source-preserving-skill-pool-strategy-2026-07-17.md",
            "docs/cc-switch-live-source-ownership-reconciliation-2026-07-18.md",
            "docs/cc-switch-live-source-ownership-reconciliation-2026-07-18.zh-CN.md",
            "docs/cc-switch-disposable-source-management-preview-2026-07-18.md",
            "docs/cc-switch-disposable-source-management-preview-2026-07-18.zh-CN.md",
            "docs/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.md",
            "docs/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.zh-CN.md",
            "docs/dynamic-runtime-control-gap-review-2026-07-18.md",
            "docs/dynamic-runtime-control-gap-review-2026-07-18.zh-CN.md",
            "docs/legacy-curated-skill-source-migration-review-2026-07-18.md",
            "docs/legacy-curated-skill-source-migration-review-2026-07-18.zh-CN.md",
            "docs/adaptive-harness-source-suite-and-user-sovereignty-2026-07-18.md",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_rejects_post_matrix_reintake_that_promotes_calibration_to_product_authority(self) -> None:
        path = "registry/production-capability-manager-post-matrix-reintake-2026-07-17.json"
        document = verify_script.load(path)
        document["authorityModel"]["calibrationRole"] = "product-authority"
        self.assert_verify_runtime_error(path, document, "CALIBRATION must remain read-only research input")

    def test_rejects_post_matrix_reintake_that_keeps_retired_control_plane_dependencies(self) -> None:
        path = "registry/production-capability-manager-post-matrix-reintake-2026-07-17.json"
        document = verify_script.load(path)
        document["authorityModel"]["meridianOrRadarControlPlaneRequired"] = True
        self.assert_verify_runtime_error(path, document, "retired control-plane dependency")

    def test_rejects_codex_adapter_plan_that_authorizes_live_agent_or_hook_writes(self) -> None:
        path = "registry/agent-capability-manager-codex-readonly-adapter-slice-plan-2026-07-17.json"
        document = verify_script.load(path)
        document["authorityBoundary"]["realAgentConfigurationWriteAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "must not authorize real Agent or Hook writes")

    def test_rejects_codex_adapter_evidence_that_claims_real_home_or_hook_observation(self) -> None:
        path = "registry/agent-capability-manager-codex-readonly-adapter-implementation-evidence-2026-07-17.json"
        document = verify_script.load(path)
        document["authorityBoundary"]["realAgentHomeReadObserved"] = True
        self.assert_verify_runtime_error(path, document, "must not claim real Agent home or Hook observation")

    def test_acceptance_map_records_verified_codex_readonly_adapter_preview(self) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        criterion = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"] == "acceptance.manager-codex-readonly-adapter-preview"
        )
        self.assertEqual(criterion["assessment"], "verified")
        self.assertIn(
            "evidence.agent-capability-manager-foundation-slice-implementation",
            criterion["evidenceIds"],
        )
        self.assertIn(
            "evidence.agent-capability-manager-codex-readonly-adapter-implementation",
            criterion["evidenceIds"],
        )

    def test_rejects_manager_topology_package_that_authorizes_repository_creation(self) -> None:
        path = "registry/production-capability-manager-topology-impact-package-2026-07-15.json"
        document = verify_script.load(path)
        document["repositoryCreationAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "repository creation must remain unauthorized")

    def test_rejects_manager_topology_acceptance_that_authorizes_implementation(self) -> None:
        path = "registry/production-capability-manager-topology-acceptance-event-2026-07-15.json"
        document = verify_script.load(path)
        document["authorization"]["managerProductImplementationAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "must not authorize managerProductImplementationAuthorized")

    def test_rejects_manager_ecosystem_review_that_skips_reuse_first(self) -> None:
        path = "registry/production-capability-manager-external-ecosystem-and-stack-review-2026-07-15.json"
        document = verify_script.load(path)
        document["reuseStrategy"]["decision"] = "build-from-scratch"
        self.assert_verify_runtime_error(path, document, "must preserve reuse-before-authoring")

    def test_rejects_manager_ecosystem_review_that_enables_telemetry_or_side_effects(self) -> None:
        path = "registry/production-capability-manager-external-ecosystem-and-stack-review-2026-07-15.json"
        document = verify_script.load(path)
        document["authorization"]["productImplementationAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "must not authorize side effects")

    def test_rejects_manager_repository_slug_decision_that_claims_namespace_reservation(self) -> None:
        path = "registry/production-capability-manager-repository-slug-acceptance-event-2026-07-16.json"
        document = verify_script.load(path)
        document["namingEvidence"]["reservationClaimed"] = True
        self.assert_verify_runtime_error(path, document, "must not claim reservation")

    def test_rejects_manager_repository_slug_decision_that_authorizes_creation(self) -> None:
        path = "registry/production-capability-manager-repository-slug-acceptance-event-2026-07-16.json"
        document = verify_script.load(path)
        document["authorization"]["managerRepositoryCreationAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "must not authorize managerRepositoryCreationAuthorized")

    def test_rejects_manager_foundation_authorization_that_enables_real_agent_writes(self) -> None:
        path = "registry/agent-capability-manager-stack-and-foundation-authorization-event-2026-07-16.json"
        document = verify_script.load(path)
        document["authorization"]["realAgentConfigurationWriteAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "must not authorize realAgentConfigurationWriteAuthorized")

    def test_rejects_manager_foundation_plan_without_rollback_coverage(self) -> None:
        path = "registry/agent-capability-manager-foundation-slice-plan-2026-07-16.json"
        document = verify_script.load(path)
        document["verticalSlice"]["acceptanceTests"] = []
        self.assert_verify_runtime_error(path, document, "acceptance or safety coverage is incomplete")

    def test_rejects_manager_foundation_evidence_that_claims_real_agent_writes(self) -> None:
        path = "registry/agent-capability-manager-foundation-slice-implementation-evidence-2026-07-16.json"
        document = verify_script.load(path)
        document["authorityBoundary"]["realAgentConfigurationWritesObserved"] = True
        self.assert_verify_runtime_error(path, document, "must not claim real Agent writes")

    def test_rejects_manager_foundation_evidence_without_msrv_verification(self) -> None:
        path = "registry/agent-capability-manager-foundation-slice-implementation-evidence-2026-07-16.json"
        document = verify_script.load(path)
        document["verification"]["minimumSupportedToolchain"]["rustc"] = "unverified"
        self.assert_verify_runtime_error(path, document, "minimum supported Rust verification drifted")

    def test_manager_initiative_is_superseded_but_preserves_foundation_evidence(self) -> None:
        document = verify_script.load("registry/curation-program-plan.json")
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"] == "initiative.production-capability-manager-topology-design"
        )
        self.assertEqual(initiative["status"], "superseded")
        self.assertEqual(
            initiative["foundationImplementationEvidence"],
            "registry/agent-capability-manager-foundation-slice-implementation-evidence-2026-07-16.json",
        )
        self.assertIn(
            "preserve historical design and implementation evidence",
            initiative["allowedActions"],
        )
        self.assertIn("further Manager implementation", initiative["blockedActions"])
        self.assertEqual(
            initiative["supersedingDecisionEvidence"],
            "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json",
        )

    def test_manager_initiative_preserves_post_matrix_and_codex_preview_history(self) -> None:
        document = verify_script.load("registry/curation-program-plan.json")
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"] == "initiative.production-capability-manager-topology-design"
        )
        self.assertEqual(
            initiative["postMatrixReintakeEvidence"],
            "registry/production-capability-manager-post-matrix-reintake-2026-07-17.json",
        )
        self.assertEqual(
            initiative["codexReadonlyAdapterSlicePlan"],
            "registry/agent-capability-manager-codex-readonly-adapter-slice-plan-2026-07-17.json",
        )
        allowed = " ".join(initiative["allowedActions"]).lower()
        self.assertIn("preserve historical design and implementation evidence", allowed)
        self.assertIn("read-only verification that the retired local experiment remains absent", allowed)
        blocked = " ".join(initiative["blockedActions"]).lower()
        self.assertIn("real agent adapter or configuration writes", blocked)
        self.assertIn("hook enablement or mutation", blocked)

    def test_rejects_cc_switch_strategy_that_authorizes_manager_implementation(self) -> None:
        path = "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json"
        document = verify_script.load(path)
        document["customManagerRetirement"]["furtherImplementationAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "Custom Manager retirement boundary drifted: furtherImplementationAuthorized")

    def test_rejects_cc_switch_strategy_that_rewrites_upstream_skills(self) -> None:
        path = "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json"
        document = verify_script.load(path)
        document["currentStrategy"]["payloadPolicy"] = "adapt-by-default"
        self.assert_verify_runtime_error(path, document, "CC Switch current strategy drifted: payloadPolicy")

    def test_rejects_cc_switch_strategy_that_claims_install_authority(self) -> None:
        path = "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json"
        document = verify_script.load(path)
        document["authorityBoundary"]["currentTransactionSkillInstallationAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "must not authorize download, install, live mutation, commit, or push")

    def test_rejects_cc_switch_strategy_that_allows_wholesale_codex_user_config_consolidation(self) -> None:
        path = "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json"
        document = verify_script.load(path)
        document["chainBoundary"]["wholeRepositoryConsolidationIntoCodexUserConfigAllowed"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "CC Switch cross-Agent chain boundary drifted: wholeRepositoryConsolidationIntoCodexUserConfigAllowed",
        )

    def test_rejects_cc_switch_strategy_that_lets_consumer_config_replace_portable_authority(self) -> None:
        path = "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json"
        document = verify_script.load(path)
        document["chainBoundary"]["consumerConfigurationMayReplacePortableCoreAuthority"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "CC Switch cross-Agent chain boundary drifted: consumerConfigurationMayReplacePortableCoreAuthority",
        )

    def test_program_plan_preserves_agent_neutral_portable_authority(self) -> None:
        document = verify_script.load("registry/curation-program-plan.json")
        boundary = document["strategicPositioning"]["portableAuthorityBoundary"]
        self.assertEqual(boundary["authorityRepository"], "agent-skills-curated")
        self.assertFalse(boundary["wholeRepositoryConsolidationIntoSingleAgentConsumerAllowed"])
        self.assertFalse(boundary["consumerConfigurationMayReplacePortableAuthority"])
        self.assertIn("codex-specific", boundary["codexUserConfigRole"])

    def test_rejects_adaptive_policy_that_turns_curation_into_mirroring(self) -> None:
        path = "registry/adaptive-harness-source-suite-and-user-sovereignty-acceptance-event-2026-07-18.json"
        document = verify_script.load(path)
        document["valueProposition"]["curationIsNotMirroring"] = False
        self.assert_verify_runtime_error(path, document, "Adaptive Harness value proposition drifted: curationIsNotMirroring")

    def test_rejects_adaptive_policy_without_independent_hook_admission(self) -> None:
        path = "registry/adaptive-harness-source-suite-and-user-sovereignty-acceptance-event-2026-07-18.json"
        document = verify_script.load(path)
        document["sourceSuiteSelection"]["hookAdmissionIsIndependentFromSkillAdmission"] = False
        self.assert_verify_runtime_error(path, document, "Source-suite selection boundary drifted: hookAdmissionIsIndependentFromSkillAdmission")

    def test_rejects_adaptive_policy_that_makes_skills_universal(self) -> None:
        path = "registry/adaptive-harness-source-suite-and-user-sovereignty-acceptance-event-2026-07-18.json"
        document = verify_script.load(path)
        document["adaptiveHarness"]["noSkillIsValid"] = False
        self.assert_verify_runtime_error(path, document, "Adaptive Harness proportionality boundary drifted: noSkillIsValid")

    def test_rejects_adaptive_policy_that_allows_hidden_self_modification(self) -> None:
        path = "registry/adaptive-harness-source-suite-and-user-sovereignty-acceptance-event-2026-07-18.json"
        document = verify_script.load(path)
        document["selfAuthoredAdaptiveCapabilities"]["silentCodeOrPolicySelfModificationAllowed"] = True
        self.assert_verify_runtime_error(path, document, "Self-authored adaptive capability boundary drifted: silentCodeOrPolicySelfModificationAllowed")

    def test_rejects_adaptive_policy_that_turns_auto_hook_into_universal_strictness(self) -> None:
        path = "registry/adaptive-harness-source-suite-and-user-sovereignty-acceptance-event-2026-07-18.json"
        document = verify_script.load(path)
        document["selfAuthoredAdaptiveCapabilities"]["onModeIsExplicitPolicyNotUniversalMaximumStrictness"] = False
        self.assert_verify_runtime_error(path, document, "Self-authored adaptive capability boundary drifted: onModeIsExplicitPolicyNotUniversalMaximumStrictness")

    def test_rejects_adaptive_policy_that_prematurely_claims_a_hard_standard(self) -> None:
        path = "registry/adaptive-harness-source-suite-and-user-sovereignty-acceptance-event-2026-07-18.json"
        document = verify_script.load(path)
        document["standardizationMaturityBoundary"]["currentArtifactsAreHardStandards"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Adaptive Harness standardization boundary drifted: currentArtifactsAreHardStandards",
        )

    def test_rejects_discovery_profile_without_explicit_public_query(self) -> None:
        path = "registry/github-skill-discovery-profile.json"
        document = verify_script.load(path)
        document["queries"][0]["query"] = "agent skills"
        self.assert_verify_runtime_error(
            path,
            document,
            "GitHub Skill discovery query must be explicitly public-only",
        )

    def test_rejects_public_preflight_that_authorizes_hook_enablement(self) -> None:
        path = "registry/public-skill-source-discovery-preflight-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["hookAdmissionOrEnablementAuthorized"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Public Skill source decision must remain false: hookAdmissionOrEnablementAuthorized",
        )

    def test_rejects_public_preflight_with_duplicate_source_ids(self) -> None:
        path = "registry/public-skill-source-discovery-preflight-2026-07-18.json"
        document = verify_script.load(path)
        document["discoveredSourceIds"][1] = document["discoveredSourceIds"][0]
        self.assert_verify_runtime_error(
            path,
            document,
            "Public Skill source durable source projection contains duplicates",
        )

    def test_rejects_user_starred_list_as_an_exclusive_discovery_boundary(self) -> None:
        path = "registry/user-starred-skill-source-list-intake-2026-07-18.json"
        document = verify_script.load(path)
        document["role"]["limitsDiscoveryToThisList"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "User-starred Skill source intake role boundary drifted",
        )

    def test_rejects_static_review_as_a_premature_hard_standard(self) -> None:
        path = "registry/public-skill-source-static-review-batch-2026-07-18.json"
        document = verify_script.load(path)
        document["workingArtifactBoundary"]["hardStandard"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Public Skill source static review became a premature standard",
        )

    def test_rejects_static_review_that_re_admits_the_loopy_legacy_alias(self) -> None:
        path = "registry/public-skill-source-static-review-batch-2026-07-18.json"
        document = verify_script.load(path)
        loopy = next(
            item
            for item in document["reviews"]
            if item["sourceId"] == "github:Forward-Future/loopy"
        )
        alias = next(
            item
            for item in loopy["componentDecisions"]
            if item["component"] == "skills/loop-library"
        )
        alias["disposition"] = "continue-admission-review"
        self.assert_verify_runtime_error(
            path,
            document,
            "Public Skill source static review lost Loopy alias deduplication",
        )

    def test_rejects_context_mode_as_direct_skill_or_hook_admission(self) -> None:
        path = "registry/public-skill-source-static-review-batch-2026-07-18.json"
        document = verify_script.load(path)
        context_mode = next(
            item
            for item in document["reviews"]
            if item["sourceId"] == "github:mksglu/context-mode"
        )
        context_mode["disposition"] = "approve-direct-skill-and-hook-admission"
        self.assert_verify_runtime_error(
            path,
            document,
            "Public Skill source static review context-mode boundary drifted",
        )

    def test_rejects_loopy_comparison_that_claims_unproven_superiority(self) -> None:
        path = "registry/loopy-demand-level-alternative-comparison-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["qualityOrSuperiorityProven"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Loopy demand-level comparison overclaimed: qualityOrSuperiorityProven",
        )

    def test_loopy_contract_fixtures_are_paired_but_not_behavior_proof(self) -> None:
        protocol = verify_script.load("registry/loopy-contract-fixture-protocol-2026-07-18.json")
        self.assertEqual(protocol["localContractEvidence"]["fixtureCount"], 18)
        self.assertEqual(protocol["decision"]["loopyPreferredScenarioCount"], 0)
        self.assertEqual(protocol["decision"]["loopyControlledTrialCandidateScenarioCount"], 1)
        self.assertFalse(protocol["decision"]["qualityOrSuperiorityProven"])
        self.assertFalse(protocol["decision"]["controlledAgentTrialAuthorized"])

    def test_rejects_loopy_contract_fixture_expectation_drift(self) -> None:
        path = "tests/fixtures/loopy-contract-paired-fixtures-2026-07-18.json"
        document = verify_script.load(path)
        document["fixtures"][0]["expected"] = "candidate-for-controlled-agent-trial"
        self.assert_verify_runtime_error(
            path,
            document,
            "Loopy deterministic contract fixture failed",
        )

    def test_rejects_premature_loopy_candidate_execution_authorization(self) -> None:
        path = "registry/loopy-contract-fixture-protocol-2026-07-18.json"
        document = verify_script.load(path)
        document["controlledAgentTrial"]["candidateExecutionAuthorized"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Loopy controlled Agent trial authorization boundary drifted",
        )

    def test_loopy_disposable_agent_trial_is_reference_only_after_valid_runs(self) -> None:
        document = verify_script.load("registry/loopy-disposable-agent-trial-result-2026-07-18.json")
        self.assertEqual(document["method"]["formalRunCount"], 12)
        self.assertEqual(document["observations"]["formalTaskCorrectCount"], 12)
        self.assertEqual(document["observations"]["falsePositiveLoopSelectionCount"], 0)
        self.assertEqual(document["observations"]["currentChainSkillBodyReadCount"], 0)
        self.assertTrue(document["observations"]["currentChainSelectedNativeNoSkillPath"])
        self.assertEqual(document["decision"]["fullBodyDisposition"], "reference-only-not-admitted")
        self.assertFalse(document["decision"]["materialBenefitOverBothBaselines"])
        self.assertTrue(document["authorization"]["consumedByThisTrial"])
        self.assertFalse(document["authorization"]["furtherCandidateExecutionAuthorized"])

    def test_rejects_loopy_trial_superiority_upgrade(self) -> None:
        path = "registry/loopy-disposable-agent-trial-result-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["materialBenefitOverBothBaselines"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Loopy disposable Agent trial overclaimed: materialBenefitOverBothBaselines",
        )

    def test_rejects_loopy_trial_raw_evidence_hash_drift(self) -> None:
        path = "registry/loopy-disposable-agent-trial-result-2026-07-18.json"
        document = verify_script.load(path)
        document["rawEvidence"]["sha256"] = "0" * 64
        self.assert_verify_runtime_error(
            path,
            document,
            "Loopy disposable Agent trial raw evidence drifted",
        )

    def test_rejects_user_starred_preflight_that_authorizes_download(self) -> None:
        path = "registry/user-starred-new-source-preflight-2026-07-18.json"
        document = verify_script.load(path)
        document["batchDecision"]["sourceDownloadAuthorizedByThisEvidence"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "User-starred new-source preflight overclaimed: sourceDownloadAuthorizedByThisEvidence",
        )

    def test_rejects_vercel_cli_as_a_skill_admission_candidate(self) -> None:
        path = "registry/user-starred-new-source-preflight-2026-07-18.json"
        document = verify_script.load(path)
        vercel = next(
            item
            for item in document["sources"]
            if item["sourceId"] == "github:vercel-labs/skills"
        )
        vercel["disposition"] = "direct-skill-admission-candidate"
        self.assert_verify_runtime_error(
            path,
            document,
            "User-starred new-source disposition drifted: github:vercel-labs/skills",
        )

    def test_user_starred_child_preflight_preserves_unavailable_license_unknowns(self) -> None:
        document = verify_script.load("registry/user-starred-index-child-source-preflight-2026-07-18.json")
        self.assertEqual(document["summary"]["treeOkCount"], 14)
        self.assertEqual(document["summary"]["treeUnavailableCount"], 2)
        self.assertEqual(document["summary"]["licenseMissingAmongAvailableCount"], 4)
        self.assertEqual(document["summary"]["licenseUnknownBecauseUnavailableCount"], 2)

    def test_rejects_stale_index_source_automatic_substitution(self) -> None:
        path = "registry/user-starred-index-stale-source-resolution-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["automaticSubstitutionCount"] = 1
        self.assert_verify_runtime_error(
            path,
            document,
            "User-starred stale-source decision drifted",
        )

    def test_user_starred_child_classification_verifies_bounded_stop_not_completeness(self) -> None:
        document = verify_script.load(
            "registry/user-starred-index-child-source-classification-2026-07-18.json"
        )
        self.assertEqual(len(document["sources"]), 14)
        self.assertEqual(len(document["clusters"]), 4)
        self.assertEqual(document["representativeSelection"]["selectedCount"], 0)
        self.assertTrue(document["stopDecision"]["boundedRoundVerified"])
        self.assertFalse(document["stopDecision"]["ecosystemComplete"])
        self.assertFalse(document["stopDecision"]["allFutureDiscoveryStopped"])
        self.assertEqual(document["acceptanceAssessment"]["to"], "verified")

    def test_rejects_user_starred_child_classification_ecosystem_overclaim(self) -> None:
        path = "registry/user-starred-index-child-source-classification-2026-07-18.json"
        document = verify_script.load(path)
        document["reviewBoundary"]["ecosystemCompletenessClaimed"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "User-starred child-source classification boundary drifted",
        )

    def test_lifecycle_metabolism_verifies_feedback_but_not_skill_retirement(self) -> None:
        document = verify_script.load(
            "registry/lifecycle-metabolism-reconciliation-2026-07-18.json"
        )
        assessments = {
            item["acceptanceId"]: item["to"]
            for item in document["acceptanceAssessment"]
        }
        self.assertEqual(len(document["triggerMatrix"]), 6)
        self.assertEqual(assessments["acceptance.feedback-loop"], "verified")
        self.assertEqual(
            assessments["acceptance.deprecation-retirement-loop"], "verified"
        )
        self.assertFalse(
            document["boundaries"]["approvedSkillRetirementMaturityClaimed"]
        )

    def test_lifecycle_metabolism_fixtures_cover_positive_and_negative_paths(self) -> None:
        document = verify_script.load(
            "tests/fixtures/lifecycle-metabolism-fixtures-2026-07-18.json"
        )
        results = verify_script.evaluate_lifecycle_metabolism_fixture_document(document)
        self.assertEqual(sum(item["decision"] == "accept" for item in results), 5)
        self.assertEqual(sum(item["decision"] == "reject" for item in results), 3)
        reasons = {item["reasonCode"] for item in results if item["decision"] == "reject"}
        self.assertEqual(
            reasons,
            {
                "immutable-intake-required",
                "release-safeguards-incomplete",
                "feedback-cannot-approve",
            },
        )

    def test_rejects_lifecycle_metabolism_skill_retirement_overclaim(self) -> None:
        path = "registry/lifecycle-metabolism-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["boundaries"]["approvedSkillRetirementMaturityClaimed"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Lifecycle metabolism authority boundary drifted",
        )

    def test_cross_agent_claim_ledger_verifies_limits_not_behavior(self) -> None:
        document = verify_script.load(
            "registry/cross-agent-claim-limit-reconciliation-2026-07-18.json"
        )
        self.assertEqual(len(document["claimLedger"]), 9)
        self.assertTrue(
            document["decision"]["everyEntryHasAllRequiredDimensions"]
        )
        self.assertEqual(document["decision"]["to"], "verified")
        self.assertTrue(
            all(value is False for value in document["universalClaimFirewall"].values())
        )

    def test_rejects_cross_agent_behavior_overclaim(self) -> None:
        path = "registry/cross-agent-claim-limit-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["universalClaimFirewall"]["crossHostBehaviorProven"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Cross-Agent claim-limit universal firewall drifted",
        )

    def test_rejects_cross_agent_claim_without_loader_dimension(self) -> None:
        path = "registry/cross-agent-claim-limit-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        del document["claimLedger"][0]["conditions"]["loader"]
        self.assert_verify_runtime_error(
            path,
            document,
            "Cross-Agent claim-limit dimensions incomplete",
        )

    def test_consumer_mapping_gap_stays_partial_and_non_vacuous(self) -> None:
        document = verify_script.load(
            "registry/consumer-mapping-evidence-gap-reconciliation-2026-07-18.json"
        )
        consumers = {item["id"]: item for item in document["consumers"]}
        self.assertEqual(consumers["consumer.codex"]["evidenceState"], "current-static-partial")
        self.assertEqual(consumers["consumer.claude-code"]["evidenceState"], "conceptual-only")
        self.assertEqual(document["boundaries"]["currentSupportedConsumerMappingCount"], 0)
        self.assertTrue(document["boundaries"]["externalConsumerReadPerformed"])
        self.assertTrue(document["boundaries"]["liveAgentHomeReadPerformed"])
        self.assertEqual(document["consumerReadSnapshot"]["fixtureResult"]["passed"], 5)
        self.assertEqual(document["liveAgentHomeSnapshot"]["skillDirectoryCount"], 73)
        self.assertEqual(
            document["liveAgentHomeSnapshot"]["transaction"]["driftedClaimedSkillCount"],
            19,
        )
        self.assertEqual(document["liveAgentHomeSnapshot"]["skillLock"]["managedSkillCount"], 27)
        self.assertEqual(document["liveAgentHomeSnapshot"]["ccSwitchProjection"]["count"], 43)
        self.assertEqual(
            document["liveAgentHomeSnapshot"]["ccSwitchProjection"]["sourceBackedDatabaseRowCount"],
            0,
        )
        self.assertEqual(document["liveAgentHomeSnapshot"]["consumerRepoManaged"]["count"], 3)
        self.assertEqual(document["acceptanceAssessment"]["to"], "partial")
        self.assertIn("cannot become verified", document["acceptanceAssessment"]["nonVacuityRule"])

    def test_rejects_static_consumer_snapshot_as_live_mapping(self) -> None:
        path = "registry/consumer-mapping-evidence-gap-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        codex = next(
            item for item in document["consumers"]
            if item["id"] == "consumer.codex"
        )
        codex["currentMappingAccepted"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Consumer-mapping current support overclaimed: consumer.codex",
        )

    def test_rejects_consumer_snapshot_that_wrote_external_repository(self) -> None:
        path = "registry/consumer-mapping-evidence-gap-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["consumerReadSnapshot"]["externalRepositoryWritePerformed"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Consumer-mapping current Codex snapshot overclaimed",
        )

    def test_rejects_live_agent_home_snapshot_that_hides_transaction_drift(self) -> None:
        path = "registry/consumer-mapping-evidence-gap-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["liveAgentHomeSnapshot"]["transaction"]["driftedClaimedSkillCount"] = 0
        self.assert_verify_runtime_error(
            path,
            document,
            "Consumer-mapping live curated transaction evidence drifted",
        )

    def test_rejects_live_agent_home_snapshot_that_overclaims_source_backing(self) -> None:
        path = "registry/consumer-mapping-evidence-gap-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["liveAgentHomeSnapshot"]["ccSwitchProjection"]["sourceBackedDatabaseRowCount"] = 43
        self.assert_verify_runtime_error(
            path,
            document,
            "CC Switch live reconciliation and consumer projection drifted",
        )

    def test_rejects_conceptual_consumer_as_current_supported_mapping(self) -> None:
        path = "registry/consumer-mapping-evidence-gap-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        claude = next(
            item for item in document["consumers"]
            if item["id"] == "consumer.claude-code"
        )
        claude["currentMappingAccepted"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Consumer-mapping current support overclaimed: consumer.claude-code",
        )

    def test_user_sovereignty_is_verified_while_foreign_coexistence_stays_partial(self) -> None:
        document = verify_script.load(
            "registry/user-sovereignty-and-foreign-coexistence-reconciliation-2026-07-18.json"
        )
        assessments = {
            item["acceptanceId"]: item["to"]
            for item in document["acceptanceAssessment"]
        }
        self.assertEqual(len(document["ownershipClasses"]), 6)
        self.assertEqual(
            assessments["acceptance.user-sovereign-capability-governance"],
            "verified",
        )
        self.assertEqual(
            assessments["acceptance.foreign-managed-capability-coexistence"],
            "partial",
        )
        self.assertFalse(
            document["ownershipTransitionContract"]["unknownOwnershipMayBeClaimed"]
        )
        self.assertTrue(document["authorityAndDataBoundary"]["liveCcSwitchReadObserved"])
        self.assertTrue(document["authorityAndDataBoundary"]["realAgentHomeReadObserved"])

    def test_cc_switch_live_source_reconciliation_stays_partial(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-live-source-ownership-reconciliation-2026-07-18.json"
        )
        shared = document["sharedAgentHomeSnapshot"]
        database = document["ccSwitchDatabaseSnapshot"]["activeSharedRootProjectionClassification"]
        legacy = document["legacyCuratedSlice"]
        self.assertEqual(shared["ccSwitchTargetCount"], 43)
        self.assertEqual(shared["ccSwitchSymbolicLinkCount"], 42)
        self.assertEqual(database["sourceBackedDatabaseRowCount"], 0)
        self.assertEqual(database["missingDatabaseRowCount"], 1)
        self.assertEqual(legacy["exactTreeMatchesCurrentCuratedRepository"], 19)
        self.assertTrue(document["authorityReconciliation"]["ccSwitchOperationalDistributionObserved"])
        self.assertFalse(document["authorityReconciliation"]["currentActiveProjectionSourcePreserving"])
        assessments = {
            item["acceptanceId"]: item["to"]
            for item in document["acceptanceReconciliation"]
        }
        self.assertEqual(assessments["acceptance.cc-switch-source-preserving-skill-pool"], "partial")

    def test_rejects_cc_switch_live_source_reconciliation_overclaim(self) -> None:
        path = "registry/cc-switch-live-source-ownership-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["ccSwitchDatabaseSnapshot"]["activeSharedRootProjectionClassification"]["sourceBackedDatabaseRowCount"] = 43
        self.assert_verify_runtime_error(path, document, "CC Switch active source classification drifted")

    def test_rejects_old_transaction_as_unresolved_rollback_authority(self) -> None:
        path = "registry/cc-switch-live-source-ownership-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["migrationContract"]["rollbackToOldTransactionAllowedWithoutOwnershipResolution"] = True
        self.assert_verify_runtime_error(path, document, "CC Switch migration boundary drifted")

    def test_acceptance_map_keeps_cc_switch_source_preservation_partial(self) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        criterion = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"] == "acceptance.cc-switch-source-preserving-skill-pool"
        )
        self.assertEqual(criterion["assessment"], "partial")
        self.assertIn(
            "evidence.cc-switch-live-source-ownership-reconciliation-2026-07-18",
            criterion["evidenceIds"],
        )
        self.assertIn(
            "evidence.legacy-curated-skill-source-migration-review-2026-07-18",
            criterion["evidenceIds"],
        )
        self.assertIn(
            "evidence.cc-switch-disposable-source-management-preview-2026-07-18",
            criterion["evidenceIds"],
        )

    def test_cc_switch_disposable_preview_preserves_live_boundary(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-disposable-source-management-preview-2026-07-18.json"
        )
        self.assertEqual(
            document["diagnosticIsolationPatch"]["patchedSkillSyncResult"],
            {
                "passed": 7,
                "failed": 0,
                "covered": document["diagnosticIsolationPatch"]["patchedSkillSyncResult"]["covered"],
            },
        )
        self.assertEqual(
            document["repositoryOwnedDisposableContractTest"]["passed"], 1
        )
        self.assertFalse(
            document["upstreamWindowsIsolationFinding"]["realDirectoryMutationObserved"]
        )
        self.assertIn("no real CC Switch database", document["nonActions"][0])

    def test_cc_switch_disposable_update_proves_manual_not_automatic_recovery(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.json"
        )
        self.assertEqual(document["loopbackFixture"]["result"]["passed"], 1)
        self.assertFalse(
            document["confirmedProductGap"]["automaticRollbackOnReplacementFailure"]
        )
        self.assertTrue(document["confirmedProductGap"]["manualRecoveryProven"])
        self.assertFalse(document["revisedCanaryGate"]["realMigrationAuthorized"])
        self.assertFalse(
            document["revisedCanaryGate"]["automaticUpdateAllowedForFirstCanary"]
        )
        cleanup = document["isolationIncidentAndCleanup"]["postCleanupVerification"]
        self.assertEqual(cleanup["fixtureDatabaseRows"], 0)
        self.assertEqual(cleanup["fixtureSkillRows"], 0)
        self.assertEqual(cleanup["fixtureRepositoryRows"], 0)
        self.assertEqual(cleanup["fixtureBackupDirectories"], 0)
        self.assertFalse(cleanup["fixtureSsotPresent"])
        self.assertEqual(cleanup["ccSwitchSkillRowCount"], 248)
        self.assertEqual(cleanup["ccSwitchRepositoryRowCount"], 5)
        self.assertEqual(
            len(document["isolationIncidentAndCleanup"]["preCleanupDatabaseBackups"]),
            2,
        )

    def test_rejects_cc_switch_disposable_update_as_atomic_transaction(self) -> None:
        path = "registry/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.json"
        document = verify_script.load(path)
        document["confirmedProductGap"]["automaticRollbackOnReplacementFailure"] = True
        self.assert_verify_runtime_error(
            path, document, "CC Switch updater transaction gap drifted"
        )

    def test_rejects_unverified_cc_switch_fixture_cleanup(self) -> None:
        path = "registry/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.json"
        document = verify_script.load(path)
        document["isolationIncidentAndCleanup"]["postCleanupVerification"]["fixtureDatabaseRows"] = 1
        self.assert_verify_runtime_error(
            path, document, "CC Switch isolation incident cleanup evidence drifted"
        )

    def test_cc_switch_handoff_canary_preview_is_pinned_and_not_authorized(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-handoff-real-canary-readonly-preview-2026-07-18.json"
        )
        self.assertEqual(document["candidate"]["liveIdentity"], "local:handoff")
        self.assertEqual(
            document["candidate"]["reviewedRevision"],
            "9603c1cc8118d08bc1b3bf34cf714f62178dea3b",
        )
        self.assertEqual(document["selectionReview"]["executableSurfaces"], [])
        self.assertFalse(document["liveBeforeState"]["databaseHashMatchesCurrentSsot"])
        self.assertFalse(document["decision"]["liveCanaryAuthorized"])
        self.assertFalse(document["decision"]["automaticUpdateAuthorized"])

    def test_rejects_cc_switch_handoff_canary_pin_drift(self) -> None:
        path = "registry/cc-switch-handoff-real-canary-readonly-preview-2026-07-18.json"
        document = verify_script.load(path)
        document["candidate"]["remoteMainObservedRevision"] = "0" * 40
        self.assert_verify_runtime_error(
            path, document, "CC Switch handoff canary source pin drifted"
        )

    def test_cc_switch_handoff_canary_execution_is_source_backed_and_bounded(self) -> None:
        document = verify_script.load(
            "registry/cc-switch-handoff-real-canary-execution-2026-07-18.json"
        )
        self.assertEqual(document["acceptedAttempt"]["passed"], 1)
        self.assertEqual(
            document["acceptedAttempt"]["newIdentity"],
            "mattpocock/skills:skills/productivity/handoff",
        )
        self.assertFalse(document["sourceUpdateCheck"]["handoffUpdateReported"])
        self.assertEqual(document["sourceUpdateCheck"]["otherUpdateSignalCount"], 20)
        self.assertFalse(document["sourceUpdateCheck"]["otherUpdatesExecuted"])
        self.assertFalse(document["quiescenceAndBackup"]["externalSyncPerformedByThisTask"])
        self.assertTrue(document["postAuthorizationSync"]["ownerAuthorized"])
        self.assertTrue(document["postAuthorizationSync"]["handoffSourceBackedStateIntact"])
        self.assertEqual(
            document["postAuthorizationSync"]["observedRuntimeDeltas"]["removedMcpIds"],
            ["fetch", "sequential-thinking", "time"],
        )
        self.assertTrue(document["claimLimits"]["webDavSyncVerified"])

    def test_rejects_cc_switch_handoff_canary_execution_update_drift(self) -> None:
        path = "registry/cc-switch-handoff-real-canary-execution-2026-07-18.json"
        document = verify_script.load(path)
        document["sourceUpdateCheck"]["handoffUpdateReported"] = True
        self.assert_verify_runtime_error(
            path, document, "CC Switch handoff source update-check evidence drifted"
        )

    def test_rejects_cc_switch_handoff_post_authorization_sync_drift(self) -> None:
        path = "registry/cc-switch-handoff-real-canary-execution-2026-07-18.json"
        document = verify_script.load(path)
        document["postAuthorizationSync"]["handoffSourceBackedStateIntact"] = False
        self.assert_verify_runtime_error(
            path, document, "CC Switch post-authorization WebDAV sync evidence drifted"
        )

    def test_dynamic_runtime_control_stays_native_first_and_unimplemented(self) -> None:
        document = verify_script.load(
            "registry/dynamic-runtime-control-gap-review-2026-07-18.json"
        )
        self.assertTrue(document["currentJudgment"]["staticStartupControlAvailable"])
        self.assertFalse(document["currentJudgment"]["midSessionHotEnableDisableProven"])
        self.assertFalse(document["currentJudgment"]["residualGapProvenForRepositoryAuthoring"])
        self.assertEqual(
            document["futureAdaptiveContract"]["modes"], ["off", "auto", "on"]
        )
        self.assertEqual(
            document["instructionCarrierBoundary"]["publicConsumerVersion"]["defaultDecision"],
            "no-third-hand-maintained-full-copy",
        )
        self.assertFalse(
            document["instructionCarrierBoundary"]["crossRepositoryWritesAuthorizedNow"]
        )

    def test_rejects_dynamic_runtime_control_authoring_overclaim(self) -> None:
        path = "registry/dynamic-runtime-control-gap-review-2026-07-18.json"
        document = verify_script.load(path)
        document["currentJudgment"]["residualGapProvenForRepositoryAuthoring"] = True
        self.assert_verify_runtime_error(
            path, document, "Dynamic runtime-control judgment drifted"
        )

    def test_legacy_curated_skill_migration_review_has_bounded_dispositions(self) -> None:
        document = verify_script.load(
            "registry/legacy-curated-skill-source-migration-review-2026-07-18.json"
        )
        dispositions = {
            item["skill"]: item["provisionalDisposition"]
            for item in document["skills"]
        }
        self.assertEqual(len(dispositions), 19)
        self.assertEqual(
            sum(value == "replace-with-reviewed-source-backed-upstream-exact" for value in dispositions.values()),
            16,
        )
        self.assertEqual(
            {name for name, value in dispositions.items() if value == "retire-or-supersede"},
            {"git-guardrails", "setup-project-skills", "ubiquitous-language"},
        )
        self.assertFalse(document["observations"]["migrationAuthorized"])
        self.assertTrue(document["migrationGate"]["currentLiveStateFrozenUntilGate"])

    def test_rejects_legacy_curated_skill_migration_as_bulk_authority(self) -> None:
        path = "registry/legacy-curated-skill-source-migration-review-2026-07-18.json"
        document = verify_script.load(path)
        document["migrationGate"]["bulkReplacementAuthorized"] = True
        self.assert_verify_runtime_error(path, document, "Legacy curated Skill migration authority drifted")

    def test_rejects_retaining_legacy_derivative_without_supported_gap(self) -> None:
        path = "registry/legacy-curated-skill-source-migration-review-2026-07-18.json"
        document = verify_script.load(path)
        skill = next(item for item in document["skills"] if item["skill"] == "handoff")
        skill["provisionalDisposition"] = "retain-as-explicit-adapted-derivative"
        self.assert_verify_runtime_error(path, document, "Legacy curated Skill provisional dispositions drifted")

    def test_rejects_unknown_ownership_takeover(self) -> None:
        path = "registry/user-sovereignty-and-foreign-coexistence-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["ownershipTransitionContract"]["unknownOwnershipMayBeClaimed"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "User-sovereignty ownership transition boundary drifted",
        )

    def test_rejects_pm_delta_review_as_current_revision_admission(self) -> None:
        path = "registry/pm-skills-current-revision-delta-review-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["currentRevisionAdmissionAuthorized"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "PM Skills delta review overclaimed: currentRevisionAdmissionAuthorized",
        )

    def test_capability_survey_package_is_coordinate_ready_but_demand_model_open(self) -> None:
        document = verify_script.load("registry/round03-capability-survey-result-package-2026-07-18.json")
        self.assertEqual(len(document["components"]), 10)
        self.assertEqual(len(document["coordinateMatrix"]), 62)
        self.assertEqual(document["scopeSummary"]["selectedBatchCoordinateCount"], 62)
        self.assertEqual(document["scopeSummary"]["notSelectedUnassessedCoordinateCount"], 0)
        self.assertTrue(document["scopeSummary"]["coordinateEnvelopeSelectionComplete"])
        self.assertTrue(document["decision"]["wholeCoordinateCorpusDecisionReady"])
        self.assertFalse(document["decision"]["wholeDemandModelClosureClaimed"])
        self.assertFalse(document["scopeSummary"]["surveyClosureClaimed"])
        self.assertFalse(document["decision"]["candidateExecutionAuthorized"])

    def test_coordinate_envelope_reconciliation_separates_gap_classes(self) -> None:
        document = verify_script.load("registry/round03-complete-coordinate-envelope-reconciliation-2026-07-18.json")
        self.assertEqual(document["coordinateEnvelope"]["coordinateRowCount"], 62)
        self.assertTrue(document["coordinateEnvelope"]["wholeCoordinateCorpusDecisionReady"])
        self.assertEqual(
            {item["state"] for item in document["gapClasses"]},
            {
                "none-supported-in-bounded-envelope",
                "open-not-a-skill-gap",
                "deferred-not-a-capability-gap",
            },
        )
        self.assertEqual(document["decision"]["operatingMode"], "evidence-triggered-monitoring-and-recheck")
        self.assertFalse(document["decision"]["wholeDemandModelClosureClaimed"])

    def test_rejects_coordinate_envelope_as_whole_demand_model_closure(self) -> None:
        path = "registry/round03-complete-coordinate-envelope-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["wholeDemandModelClosureClaimed"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Round 03 coordinate-envelope reconciliation overclaimed: wholeDemandModelClosureClaimed",
        )

    def test_rejects_coordinate_envelope_lane_count_drift(self) -> None:
        path = "registry/round03-complete-coordinate-envelope-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["coordinateEnvelope"]["evidenceLaneCoordinateMembershipCounts"]["EL-01"] = 13
        self.assert_verify_runtime_error(
            path,
            document,
            "Round 03 coordinate-envelope reconciliation counts drifted",
        )

    def test_intent_binding_lane_uses_current_paths_without_gap_inference(self) -> None:
        document = verify_script.load("registry/round03-intent-binding-demand-review-2026-07-18.json")
        self.assertEqual(
            document["demandRecord"]["coordinateIds"],
            {"STM": ["STM-11"], "P": ["P1", "P2"], "SG": ["SG-01"]},
        )
        self.assertEqual(len(document["alternatives"]), 7)
        self.assertTrue(document["decision"]["currentPathSufficientForBoundedDemand"])
        self.assertEqual(document["decision"]["supportedResidualGapCount"], 0)
        self.assertFalse(document["decision"]["externalCandidateDiscoveryRequiredNow"])

    def test_rejects_intent_binding_lane_gap_upgrade(self) -> None:
        path = "registry/round03-intent-binding-demand-review-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["repositoryAuthoredSkillOrHookEligible"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Round 03 intent-binding review overclaimed: repositoryAuthoredSkillOrHookEligible",
        )

    def test_authority_boundary_lane_separates_guidance_enforcement_and_authority(self) -> None:
        document = verify_script.load("registry/round03-authority-boundary-demand-review-2026-07-18.json")
        self.assertEqual(
            document["demandRecord"]["coordinateIds"],
            {"STM": ["STM-20"], "P": ["P9"], "SG": ["SG-05"]},
        )
        self.assertEqual(len(document["alternatives"]), 8)
        self.assertTrue(document["decision"]["runtimeEnforcementRemainsHostOwned"])
        self.assertTrue(document["decision"]["accountableAuthorityRemainsExternal"])
        self.assertEqual(document["decision"]["supportedResidualGapCount"], 0)
        self.assertFalse(document["decision"]["externalCandidateDiscoveryRequiredNow"])

    def test_rejects_authority_boundary_lane_runtime_authority_upgrade(self) -> None:
        path = "registry/round03-authority-boundary-demand-review-2026-07-18.json"
        document = verify_script.load(path)
        document["decision"]["repositoryAuthoredSkillOrHookEligible"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Round 03 authority-boundary review overclaimed: repositoryAuthoredSkillOrHookEligible",
        )

    def test_premise_challenge_lane_preserves_open_divergent_fast_path(self) -> None:
        document = verify_script.load("registry/round03-premise-challenge-demand-review-2026-07-18.json")
        self.assertEqual(document["demandRecord"]["coordinateIds"], {"STM": ["STM-07"], "P": ["P4"], "SG": ["SG-03"]})
        self.assertEqual(len(document["alternatives"]), 7)
        self.assertTrue(document["decision"]["openDivergentFastPathPreserved"])
        self.assertEqual(document["decision"]["supportedResidualGapCount"], 0)
        self.assertFalse(document["decision"]["externalCandidateDiscoveryRequiredNow"])

    def test_cognitive_monitoring_lane_keeps_longitudinal_evidence_open(self) -> None:
        document = verify_script.load("registry/round03-cognitive-offload-monitoring-demand-review-2026-07-18.json")
        self.assertEqual(document["demandRecord"]["coordinateIds"], {"STM": ["STM-09"], "P": ["P17", "P20"], "SG": ["SG-10"]})
        self.assertEqual(len(document["alternatives"]), 8)
        self.assertEqual(document["decision"]["coordinateEnvelopeSelectedCount"], 62)
        self.assertTrue(document["decision"]["longitudinalCognitionEvidenceOpen"])
        self.assertFalse(document["decision"]["wholeDemandModelClosureClaimed"])
        self.assertEqual(document["decision"]["supportedResidualSkillGapCount"], 0)

    def test_rejects_capability_survey_package_coordinate_gap_inference(self) -> None:
        path = "registry/round03-capability-survey-result-package-2026-07-18.json"
        document = verify_script.load(path)
        row = document["coordinateMatrix"][0]
        row["disposition"] = "supported-residual-gap"
        self.assert_verify_runtime_error(
            path,
            document,
            "Round 03 capability-survey coordinate matrix is not deterministic",
        )

    def test_acceptance_map_records_adaptive_curation_and_user_sovereignty(self) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        criteria = {item["id"]: item for item in document["acceptanceCriteria"]}
        for criterion_id in [
            "acceptance.strict-admission-free-consumption",
            "acceptance.source-suite-selective-admission",
            "acceptance.adaptive-harness-proportionality",
            "acceptance.self-authored-dynamic-adaptation",
        ]:
            self.assertEqual(criteria[criterion_id]["assessment"], "verified")
            self.assertIn(
                "evidence.adaptive-harness-source-suite-and-user-sovereignty",
                criteria[criterion_id]["evidenceIds"],
            )

    def test_acceptance_map_records_verified_public_source_balanced_preflight(self) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        criteria = {item["id"]: item for item in document["acceptanceCriteria"]}
        criterion = criteria["acceptance.public-source-balanced-preflight"]
        self.assertEqual(criterion["assessment"], "verified")
        self.assertEqual(
            criterion["evidenceIds"],
            [
                "evidence.public-skill-source-discovery-preflight-2026-07-18",
                "evidence.user-starred-skill-source-list-intake-2026-07-18",
            ],
        )
        self.assertIn(
            "registry/public-skill-source-discovery-preflight-2026-07-18.json",
            verify_script.REQUIRED_FILES,
        )
        static_criterion = criteria["acceptance.public-source-static-review"]
        self.assertEqual(static_criterion["assessment"], "verified")
        self.assertEqual(
            static_criterion["evidenceIds"],
            ["evidence.public-skill-source-static-review-batch-2026-07-18"],
        )
        next_gate_criterion = criteria["acceptance.public-source-next-gate-triage"]
        self.assertEqual(next_gate_criterion["assessment"], "verified")
        self.assertEqual(
            next_gate_criterion["evidenceIds"],
            [
                "evidence.loopy-demand-level-alternative-comparison-2026-07-18",
                "evidence.user-starred-new-source-preflight-2026-07-18",
            ],
        )

    def test_repository_community_configuration_is_required_and_valid(self) -> None:
        for path in [
            ".github/FUNDING.yml",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/ISSUE_TEMPLATE/candidate-source.yml",
            ".github/ISSUE_TEMPLATE/governance-or-verification.yml",
            "SUPPORT.md",
            "SUPPORT.zh-CN.md",
            "SPONSORING.md",
            "SPONSORING.zh-CN.md",
        ]:
            self.assertIn(path, verify_script.REQUIRED_FILES)
        verify_script.validate_repository_community_configuration()

    def test_rejects_cc_switch_strategy_without_manager_retirement_execution_evidence(self) -> None:
        path = "registry/cc-switch-source-preserving-skill-pool-strategy-acceptance-event-2026-07-17.json"
        document = verify_script.load(path)
        document["customManagerRetirement"]["executionEvidence"]["existsAfterDeletion"] = True
        self.assert_verify_runtime_error(path, document, "Custom Manager retirement execution evidence drifted")

    def test_acceptance_map_records_verified_manager_foundation_closure(self) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        objective = next(
            item
            for item in document["objectives"]
            if item["id"] == "objective.custom-manager-retirement-evidence-preservation"
        )
        self.assertIn(
            "acceptance.manager-foundation-transaction-closure",
            objective["acceptanceIds"],
        )
        criterion = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"] == "acceptance.manager-foundation-transaction-closure"
        )
        self.assertEqual(criterion["assessment"], "verified")

    def test_current_capability_governance_no_longer_depends_on_custom_manager_identity(self) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        objective_ids = {item["id"] for item in document["objectives"]}
        self.assertNotIn("objective.production-capability-manager", objective_ids)
        self.assertIn("objective.source-preserving-cross-agent-capability-governance", objective_ids)
        criterion_ids = {item["id"] for item in document["acceptanceCriteria"]}
        self.assertNotIn("acceptance.manager-user-sovereignty", criterion_ids)
        self.assertIn("acceptance.user-sovereign-capability-governance", criterion_ids)
        self.assertIn("acceptance.custom-manager-retirement-reconciliation", criterion_ids)

    def test_rejects_custom_manager_retirement_reactivation(self) -> None:
        path = "registry/custom-manager-retirement-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["currentProductDirection"]["customManagerActive"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Custom Manager retirement state drifted",
        )

    def test_release_evolution_contract_has_no_skill_count_growth_quota(self) -> None:
        document = verify_script.load(
            "registry/evidence-backed-release-evolution-reconciliation-2026-07-18.json"
        )
        self.assertEqual(
            [item["id"] for item in document["allowedOutcomes"]],
            [
                "retain",
                "add",
                "replace-or-supersede",
                "compose-or-route",
                "deprecate-or-retire",
            ],
        )
        self.assertEqual(
            document["currentDecision"]["currentOutcome"],
            "retain-current-release-and-monitor-evidence",
        )
        self.assertFalse(document["currentDecision"]["releaseChangeRequiredNow"])

    def test_rejects_forced_release_growth_when_supported_gap_is_zero(self) -> None:
        path = "registry/evidence-backed-release-evolution-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        document["currentDecision"]["releaseChangeRequiredNow"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Evidence-backed release evolution current retain decision drifted",
        )

    def test_layered_reliability_projection_closes_only_projection_criteria(self) -> None:
        acceptance = verify_script.load("registry/program-acceptance-map.json")
        criteria = {item["id"]: item for item in acceptance["acceptanceCriteria"]}
        self.assertEqual(
            criteria["acceptance.layered-reliability-model"]["assessment"],
            "verified",
        )
        self.assertEqual(
            criteria["acceptance.project-standard-precedence"]["assessment"],
            "verified",
        )
        self.assertEqual(
            criteria["acceptance.standard-candidate-contract"]["assessment"],
            "partial",
        )
        self.assertEqual(
            criteria["acceptance.standard-revalidation-cascade"]["assessment"],
            "partial",
        )

    def test_rejects_layered_projection_overclaim_of_standard_maturity(self) -> None:
        path = "registry/layered-reliability-projection-reconciliation-2026-07-18.json"
        document = verify_script.load(path)
        standard = next(
            item
            for item in document["keptOpen"]
            if item["acceptanceId"] == "acceptance.standard-candidate-contract"
        )
        standard["assessment"] = "verified"
        self.assert_verify_runtime_error(
            path,
            document,
            "Layered reliability kept-open boundary drifted",
        )

    def test_decision_ready_projection_records_repository_evidence_without_consumer_overclaim(self) -> None:
        document = verify_script.load(
            "registry/decision-ready-consumer-projection-evaluation-2026-07-18.json"
        )
        self.assertEqual(document["fixtureResult"]["scenarioCount"], 105)
        self.assertEqual(document["fixtureResult"]["failed"], 0)
        self.assertEqual(
            document["acceptanceAssessment"]["assessment"],
            "partial",
        )
        self.assertEqual(
            document["structuralBurdenProxy"]["baselineGovernedPayloadEntriesToEnumerate"],
            28,
        )

    def test_rejects_decision_ready_projection_consumer_verification_overclaim(self) -> None:
        path = "registry/decision-ready-consumer-projection-evaluation-2026-07-18.json"
        document = verify_script.load(path)
        document["acceptanceAssessment"]["assessment"] = "verified"
        self.assert_verify_runtime_error(
            path,
            document,
            "Decision-ready consumer projection acceptance boundary drifted",
        )

    def test_github_configuration_evidence_binds_codeql_to_recorded_remote_revision(self) -> None:
        document = verify_script.load(
            "registry/github-repository-configuration-evidence-2026-07-18.json"
        )
        security = document["securityConfiguration"]
        self.assertEqual(security["secretScanning"], "enabled")
        self.assertEqual(security["secretScanningPushProtection"], "enabled")
        self.assertEqual(security["dependabotSecurityUpdates"], "enabled-not-paused")
        self.assertEqual(security["privateVulnerabilityReporting"], "enabled")
        self.assertEqual(security["codeScanningDefaultSetup"], "configured")
        self.assertEqual(
            security["firstCodeScanningAnalysis"],
            "completed-zero-results-for-recorded-remote-main",
        )
        self.assertEqual(security["codeScanningAlertCount"], 0)
        self.assertFalse(security["firstCodeScanningAnalysisVerificationRequired"])
        self.assertFalse(document["communityAndSponsorship"]["localFilesPublished"])

    def test_rejects_github_configuration_codeql_result_drift(self) -> None:
        path = "registry/github-repository-configuration-evidence-2026-07-18.json"
        document = verify_script.load(path)
        document["securityConfiguration"]["firstCodeScanningAnalysis"] = "passed"
        self.assert_verify_runtime_error(
            path,
            document,
            "GitHub repository security evidence drifted: firstCodeScanningAnalysis",
        )

    def test_round03_demand_coordinate_contract_is_a_required_verifier_input(self) -> None:
        for path in (
            "registry/round03-demand-coordinate-source-contract.json",
            "registry/round03-demand-records-batch-01.json",
            "registry/round03-native-runtime-baseline-2026-07-15.json",
            "registry/round03-public-discovery-snapshot-2026-07-15.json",
            "registry/round03-representative-source-review-batch-01.json",
            "registry/round03-alternative-comparison-batch-01.json",
            "registry/round03-evidence-protocol-batch-01.json",
            "tests/fixtures/round03-evidence-fixtures-batch-01.json",
            "registry/round03-capability-survey-rebaseline-acceptance-event-2026-07-15.json",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

    def test_current_verifier_accepts_the_checked_in_schema2_capability_registry(self) -> None:
        document = verify_script.load("registry/capabilities.json")
        self.assertEqual(document["schema"], 2)
        verify_script.validate_capabilities_document(document, "registry/capabilities.json")

    def test_verifier_rejects_orphan_recipe_coverage(self) -> None:
        document = verify_script.load("registry/recipes.json")
        document["recipes"] = [
            recipe
            for recipe in document["recipes"]
            if recipe["id"] != "recipe.test-strategy"
        ]
        self.assert_verify_contract_error(
            "registry/recipes.json", document, "/scenarios/9/expectedSkills/0"
        )

    def assert_verify_contract_error(
        self, path: str, mutation: dict[str, object], pointer: str
    ) -> None:
        original_load = verify_script.load

        def load_with_mutation(candidate: str) -> dict[str, object]:
            if candidate == path:
                return deepcopy(mutation)
            return original_load(candidate)

        with patch.object(
            verify_script,
            "load",
            side_effect=load_with_mutation,
        ), without_task4_manifest_poc_replay():
            with self.assertRaises(ContractError) as raised:
                verify_script.verify()
        self.assertEqual(raised.exception.pointer, pointer)

    def assert_verify_runtime_error(
        self,
        path: str,
        mutation: dict[str, object],
        message: str,
    ) -> None:
        original_load = verify_script.load

        def load_with_mutation(candidate: str) -> dict[str, object]:
            if candidate == path:
                return deepcopy(mutation)
            return original_load(candidate)

        with patch.object(
            verify_script,
            "load",
            side_effect=load_with_mutation,
        ), without_task4_manifest_poc_replay():
            with self.assertRaisesRegex(RuntimeError, message):
                verify_script.verify()

    def test_rejects_program_objective_with_unknown_acceptance_reference(self) -> None:
        path = "registry/program-acceptance-map.json"
        document = verify_script.load(path)
        document["objectives"][0]["acceptanceIds"] = ["acceptance.missing"]
        self.assert_verify_runtime_error(path, document, "unknown acceptance id")

    def test_top_level_verify_rejects_skill_runtime_behavioral_overclaim(self) -> None:
        path = "registry/skill-runtime-and-cc-count-drift-snapshot-2026-07-27.json"
        document = verify_script.load(path)
        document["decision"]["superpowers620IsBehavioralBaseline"] = True
        self.assert_verify_runtime_error(
            path,
            document,
            "Skill runtime drift portfolio decision changed",
        )

    def test_program_map_rejects_missing_skill_runtime_backlink(self) -> None:
        path = "registry/program-acceptance-map.json"
        document = verify_script.load(path)
        criterion = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"]
            == "acceptance.cc-switch-source-preserving-skill-pool"
        )
        criterion["evidenceIds"].remove(
            "evidence.skill-runtime-and-cc-count-drift-snapshot-2026-07-27"
        )
        self.assert_verify_runtime_error(
            path,
            document,
            "does not reference supported evidence",
        )

    def test_program_map_rejects_process_fidelity_subgate_promotion(self) -> None:
        path = "registry/program-acceptance-map.json"
        document = verify_script.load(path)
        criterion = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        criterion["graduationSubgates"][0]["status"] = "closed"
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity graduation subgates",
        )

    def test_program_map_rejects_cleanup_observation_date_drift(self) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        program = verify_script.load("registry/curation-program-plan.json")
        evidence = next(
            item
            for item in document["evidence"]
            if item["id"]
            == "evidence.closeout-cleanup-debt-preview-2026-07-24"
        )
        evidence["asOf"] = "2026-07-24"
        with self.assertRaisesRegex(RuntimeError, "lastObservedDate"):
            verify_script.validate_program_acceptance_map(document, program)

    def test_program_map_requires_current_self_authored_tdd_gap_audit_edges(
        self,
    ) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        program = verify_script.load("registry/curation-program-plan.json")
        evidence_id = (
            "evidence.human-ai-collaboration-tdd-current-self-authored-"
            "treatment-gap-audit-2026-07-27"
        )
        criterion = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"] == "acceptance.repository-authored-gap-fill-gate"
        )
        criterion["evidenceIds"].remove(evidence_id)
        with self.assertRaisesRegex(
            RuntimeError,
            "does not reference supported evidence",
        ):
            verify_script.validate_program_acceptance_map(document, program)

    def test_program_map_requires_release_change_protocol_on_software_lifecycle(
        self,
    ) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        program = verify_script.load("registry/curation-program-plan.json")
        evidence_id = (
            "evidence.human-ai-collaboration-release-change-zero-model-"
            "protocol-2026-07-27"
        )
        software_lifecycle = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"]
            == "acceptance.software-engineering-lifecycle-specialization"
        )
        self.assertIn(evidence_id, software_lifecycle["evidenceIds"])
        evidence = next(
            item
            for item in document["evidence"]
            if item["id"] == evidence_id
        )
        evidence["kind"] = "drifted-release-change-protocol-kind"
        with self.assertRaisesRegex(
            RuntimeError,
            "Release/change zero-model protocol evidence graph",
        ):
            verify_script.validate_program_acceptance_map(document, program)

    def test_program_map_requires_current_tdd_readiness_on_software_lifecycle(
        self,
    ) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        program = verify_script.load("registry/curation-program-plan.json")
        evidence_id = (
            "evidence.human-ai-collaboration-tdd-current-execution-readiness-"
            "reconciliation-2026-07-27"
        )
        software_lifecycle = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"]
            == "acceptance.software-engineering-lifecycle-specialization"
        )
        self.assertIn(evidence_id, software_lifecycle["evidenceIds"])
        evidence = next(
            item
            for item in document["evidence"]
            if item["id"] == evidence_id
        )
        evidence["kind"] = "drifted-tdd-readiness-kind"
        with self.assertRaisesRegex(
            RuntimeError,
            "Current TDD execution-readiness evidence graph",
        ):
            verify_script.validate_program_acceptance_map(document, program)

    def test_program_map_requires_tdd_successor_contract_on_software_lifecycle(
        self,
    ) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        program = verify_script.load("registry/curation-program-plan.json")
        evidence_id = (
            "evidence.human-ai-collaboration-tdd-noncomparative-dispatch-"
            "successor-contract-v2-2026-07-27"
        )
        software_lifecycle = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"]
            == "acceptance.software-engineering-lifecycle-specialization"
        )
        self.assertIn(evidence_id, software_lifecycle["evidenceIds"])
        evidence = next(
            item
            for item in document["evidence"]
            if item["id"] == evidence_id
        )
        evidence["kind"] = "drifted-tdd-successor-contract-kind"
        with self.assertRaisesRegex(
            RuntimeError,
            "TDD non-comparative dispatch successor evidence graph",
        ):
            verify_script.validate_program_acceptance_map(document, program)

    def test_program_map_requires_access_comms_process_loss_evidence(
        self,
    ) -> None:
        document = verify_script.load("registry/program-acceptance-map.json")
        program = verify_script.load("registry/curation-program-plan.json")
        evidence_id = (
            "evidence.human-ai-collaboration-access-comms-zero-model-"
            "calibration-2026-07-27"
        )
        criterion = next(
            item
            for item in document["acceptanceCriteria"]
            if item["id"] == "acceptance.end-to-end-process-fidelity"
        )
        self.assertIn(evidence_id, criterion["evidenceIds"])
        evidence = next(
            item
            for item in document["evidence"]
            if item["id"] == evidence_id
        )
        evidence["kind"] = "drifted-access-comms-kind"
        with self.assertRaisesRegex(
            RuntimeError,
            "Access/comms zero-model calibration evidence graph",
        ):
            verify_script.validate_program_acceptance_map(document, program)

    def test_program_rejects_stale_process_fidelity_evidence_index(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"]
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        )
        initiative.pop("currentProcessFidelityDispatchLedgerContract")
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity current evidence index drifted",
        )

    def test_program_rejects_missing_cumulative_loss_evidence_index(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"]
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        )
        initiative.pop(
            "currentProcessFidelityCumulativeLossAccountingEvidence"
        )
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity current evidence index drifted",
        )

    def test_program_rejects_missing_lifecycle_thin_slice_index(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"]
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        )
        initiative.pop(
            "currentSoftwareLifecycleThinSliceZeroModelCalibrationEvidence"
        )
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity current evidence index drifted",
        )

    def test_program_rejects_missing_release_change_protocol_index(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"]
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        )
        initiative.pop("currentReleaseChangeZeroModelProtocol")
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity current evidence index drifted",
        )

    def test_program_rejects_missing_current_tdd_readiness_index(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"]
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        )
        initiative.pop("currentTddExecutionReadinessReconciliation")
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity current evidence index drifted",
        )

    def test_program_rejects_missing_tdd_successor_contract_index(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"]
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        )
        initiative.pop(
            "currentTddNoncomparativeDispatchSuccessorContractV2"
        )
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity current evidence index drifted",
        )

    def test_program_rejects_missing_access_comms_protocol_index(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        initiative = next(
            item
            for item in document["currentInitiatives"]
            if item["id"]
            == "initiative.human-ai-collaboration-coverage-rebaseline"
        )
        initiative.pop("currentAccessCommsZeroModelProtocol")
        self.assert_verify_runtime_error(
            path,
            document,
            "process-fidelity current evidence index drifted",
        )

    def test_program_rejects_missing_round03_rebaseline_initiative(self) -> None:
        path = "registry/curation-program-plan.json"
        document = verify_script.load(path)
        document["currentInitiatives"] = [
            item
            for item in document["currentInitiatives"]
            if item["id"]
            != "initiative.round03-capability-survey-rebaseline"
        ]
        self.assert_verify_runtime_error(
            path,
            document,
            "required initiatives are missing",
        )

    def test_rejects_verified_program_acceptance_without_evidence(self) -> None:
        path = "registry/program-acceptance-map.json"
        document = verify_script.load(path)
        criterion = document["acceptanceCriteria"][0]
        criterion["assessment"] = "verified"
        criterion["evidenceIds"] = []
        self.assert_verify_runtime_error(
            path,
            document,
            "verified acceptance requires evidence",
        )

    def test_round02_is_closed_only_after_owner_acceptance(self) -> None:
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        round02 = next(
            item
            for item in rounds["rounds"]
            if item["id"] == "round-02-source-intake-and-filtering"
        )
        self.assertEqual(round02["status"], "closed")
        self.assertEqual(round02["lifecycle"]["execute"], "closed")
        self.assertEqual(round02["lifecycle"]["acceptance"], "passed")
        self.assertEqual(round02["lifecycle"]["stageCloseout"], "closed")
        self.assertEqual(round02["closeoutOutcome"], "complete")
        self.assertIn(
            "registry/round02-stage-closeout-acceptance-event-2026-07-15.json",
            round02["evidence"],
        )

    def test_round02_closeout_review_prepares_but_does_not_apply_owner_decision(self) -> None:
        review = verify_script.load("registry/round02-stage-closeout-review.json")
        self.assertEqual(review["status"], "owner_decision_required")
        self.assertEqual(review["recommendedOutcome"], "complete")
        self.assertEqual(
            review["recommendedNextDecision"],
            "close-round-02-and-pause-for-round-03-rebaseline",
        )
        self.assertTrue(review["authorityBoundary"]["ownerDecisionRequired"])
        self.assertFalse(review["authorityBoundary"]["roundStateMutationApplied"])
        self.assertFalse(review["authorityBoundary"]["round03ActivationAuthorized"])
        self.assertFalse(review["authorityBoundary"]["remotePushAuthorized"])

    def test_round02_closeout_review_rejects_premature_state_mutation(self) -> None:
        path = "registry/round02-stage-closeout-review.json"
        review = verify_script.load(path)
        review["authorityBoundary"]["roundStateMutationApplied"] = True
        self.assert_verify_runtime_error(path, review, "authority boundary drifted")

    def test_round02_closeout_acceptance_does_not_activate_round03_or_push(self) -> None:
        event = verify_script.load(
            "registry/round02-stage-closeout-acceptance-event-2026-07-15.json"
        )
        self.assertEqual(event["authoritySource"], "owner-selected-option-1")
        self.assertTrue(event["roundStateMutationAuthorized"])
        self.assertFalse(event["round03ActivationAuthorized"])
        self.assertFalse(event["remotePushAuthorized"])
        self.assertFalse(event["globalProgramCompletionClaimed"])

    def test_round03_rebaseline_acceptance_activates_only_bounded_research(self) -> None:
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        round03 = next(
            item
            for item in rounds["rounds"]
            if item["id"] == "round-03-adaptation-and-curated-admission"
        )
        rebaseline = verify_script.load(
            "registry/round03-capability-survey-rebaseline.json"
        )
        self.assertEqual(round03["status"], "active")
        self.assertEqual(round03["lifecycle"]["execute"], "active")
        self.assertEqual(rebaseline["status"], "accepted")
        self.assertTrue(rebaseline["activationGate"]["executionActivated"])
        self.assertFalse(
            rebaseline["activationGate"]["externalDiscoveryAuthorizedByThisRecord"]
        )
        carrier = rebaseline["gapFillCarrierDecision"]
        self.assertIn("residual gap is supported", carrier["entryCondition"].lower())
        self.assertIn(
            "repository-authored Skill with a consumer-owned Hook",
            carrier["options"],
        )
        self.assertTrue(carrier["default"].lower().startswith("no hook"))

        event = verify_script.load(
            "registry/round03-capability-survey-rebaseline-acceptance-event-2026-07-15.json"
        )
        authorization = event["authorization"]
        self.assertTrue(authorization["publicReadOnlyMetadataDiscoveryAuthorized"])
        self.assertTrue(authorization["currentRepositoryEvidenceWritesAuthorized"])
        self.assertFalse(authorization["candidateExecutionAuthorized"])
        self.assertFalse(authorization["runtimeMutationAuthorized"])
        self.assertFalse(authorization["crossRepositoryWriteAuthorized"])
        self.assertFalse(authorization["remotePushAuthorized"])

    def test_round03_rebaseline_rejects_implicit_discovery_activation(self) -> None:
        path = "registry/round03-capability-survey-rebaseline.json"
        rebaseline = verify_script.load(path)
        rebaseline["activationGate"]["externalDiscoveryAuthorizedByThisRecord"] = True
        self.assert_verify_runtime_error(path, rebaseline, "activation gate drifted")

    def test_round03_demand_contract_pins_sources_without_promoting_them(self) -> None:
        contract = verify_script.load(
            "registry/round03-demand-coordinate-source-contract.json"
        )
        self.assertEqual(contract["status"], "verified-input-contract")
        self.assertEqual(
            {item["family"]: item["count"] for item in contract["coordinateFamilies"]},
            {"STM": 26, "P": 24, "SG": 12},
        )
        self.assertTrue(contract["readiness"]["sourceIdentityVerified"])
        self.assertTrue(contract["readiness"]["firstGovernedDemandBatchVerified"])
        self.assertTrue(contract["readiness"]["datedNativeRuntimeBaselineVerified"])
        self.assertFalse(contract["readiness"]["demandRecordExtractionComplete"])
        self.assertTrue(contract["readiness"]["externalDiscoveryAuthorized"])
        self.assertTrue(
            all(not item["bodyRedistributionAuthorized"] for item in contract["sources"])
        )

    def test_round03_demand_contract_rejects_source_identity_drift(self) -> None:
        path = "registry/round03-demand-coordinate-source-contract.json"
        contract = verify_script.load(path)
        contract["sources"][0]["sha256"] = "0" * 64
        self.assert_verify_runtime_error(path, contract, "source identity drifted")

    def test_round03_demand_contract_rejects_discovery_authority_drift(self) -> None:
        path = "registry/round03-demand-coordinate-source-contract.json"
        contract = verify_script.load(path)
        contract["readiness"]["externalDiscoveryAuthorized"] = False
        self.assert_verify_runtime_error(path, contract, "readiness drifted")

    def test_round03_first_demand_batch_preserves_partial_non_discovery_state(self) -> None:
        batch = verify_script.load("registry/round03-demand-records-batch-01.json")
        self.assertEqual(batch["status"], "verified-read-only-demand-batch")
        self.assertEqual(
            [record["sourceLaneId"] for record in batch["records"]],
            ["EL-01", "EL-02", "EL-03", "EL-04"],
        )
        self.assertFalse(batch["scope"]["demandExtractionComplete"])
        self.assertTrue(batch["batchDecision"]["publicCandidateDiscoveryMayStart"])
        self.assertEqual(
            [record["sourceLaneId"] for record in batch["records"] if record["candidateDiscoveryEligible"]],
            ["EL-01", "EL-02", "EL-04"],
        )

    def test_round03_first_demand_batch_rejects_premature_gap_or_discovery_claim(self) -> None:
        path = "registry/round03-demand-records-batch-01.json"
        batch = verify_script.load(path)
        batch["records"][0]["residualGapState"] = "supported"
        batch["records"][0]["candidateDiscoveryEligible"] = True
        self.assert_verify_runtime_error(path, batch, "demand record gate drifted")

    def test_round03_first_demand_batch_rejects_coordinate_mapping_drift(self) -> None:
        path = "registry/round03-demand-records-batch-01.json"
        batch = verify_script.load(path)
        batch["records"][1]["coordinateIds"]["SG"] = ["SG-01"]
        self.assert_verify_runtime_error(path, batch, "SG mapping drifted")

    def test_round03_first_demand_batch_rejects_evidence_vocabulary_drift(self) -> None:
        path = "registry/round03-demand-records-batch-01.json"
        batch = verify_script.load(path)
        batch["records"][1]["evidenceState"]["applicability"] = ["project hypothesis"]
        self.assert_verify_runtime_error(path, batch, "evidence vocabulary drifted")

    def test_demand_coordinate_contract_is_verified_without_model_closure(self) -> None:
        reconciliation = verify_script.load(
            "registry/demand-coordinate-contract-reconciliation-2026-07-18.json"
        )
        self.assertEqual(reconciliation["contractChecks"]["demandRecordCount"], 8)
        self.assertEqual(reconciliation["contractChecks"]["uniqueCoordinateCount"], 62)
        self.assertEqual(reconciliation["decision"]["to"], "verified")
        self.assertFalse(reconciliation["modelBoundary"]["wholeDemandModelExhaustive"])
        self.assertFalse(reconciliation["modelBoundary"]["demandRecordExtractionComplete"])

    def test_demand_coordinate_contract_rejects_model_exhaustiveness_overclaim(self) -> None:
        path = "registry/demand-coordinate-contract-reconciliation-2026-07-18.json"
        reconciliation = verify_script.load(path)
        reconciliation["modelBoundary"]["wholeDemandModelExhaustive"] = True
        self.assert_verify_runtime_error(
            path,
            reconciliation,
            "Demand-coordinate reconciliation model boundary overclaimed",
        )

    def test_demand_coordinate_contract_rejects_missing_evidence_state(self) -> None:
        path = "registry/round03-intent-binding-demand-review-2026-07-18.json"
        review = verify_script.load(path)
        del review["demandRecord"]["evidenceState"]
        self.assert_verify_runtime_error(
            path,
            review,
            "Demand-coordinate reconciliation evidence state incomplete",
        )

    def test_demand_coordinate_contract_rejects_missing_held_claim(self) -> None:
        path = "registry/round03-demand-records-batch-01.json"
        batch = verify_script.load(path)
        batch["records"][0]["heldClaims"] = []
        self.assert_verify_runtime_error(path, batch, "demand record heldClaims incomplete")

    def test_round03_native_runtime_baseline_is_host_bounded_and_non_executing(self) -> None:
        baseline = verify_script.load("registry/round03-native-runtime-baseline-2026-07-15.json")
        self.assertFalse(baseline["scope"]["crossHostClaim"])
        self.assertEqual(baseline["observations"]["skillNameSurface"]["skillFileCount"], 422)
        self.assertFalse(baseline["observations"]["hookMetadata"]["filePresenceProvesActivation"])
        self.assertFalse(baseline["baselineDecision"]["candidateExecutionAuthorized"])
        self.assertFalse(baseline["baselineDecision"]["residualGapProven"])

    def test_round03_native_runtime_baseline_rejects_hook_activation_overclaim(self) -> None:
        path = "registry/round03-native-runtime-baseline-2026-07-15.json"
        baseline = verify_script.load(path)
        baseline["observations"]["hookMetadata"]["filePresenceProvesActivation"] = True
        self.assert_verify_runtime_error(path, baseline, "Hook metadata boundary drifted")

    def test_native_runtime_baseline_gap_stays_partial_for_review_only_lanes(self) -> None:
        gap = verify_script.load(
            "registry/native-runtime-baseline-evidence-gap-reconciliation-2026-07-18.json"
        )
        self.assertEqual(gap["formalBaseline"]["demandRecordCount"], 4)
        self.assertEqual(gap["currentSurveyScope"]["demandRecordCount"], 8)
        self.assertEqual(len(gap["reviewOnlyLanes"]), 4)
        self.assertEqual(gap["decision"]["to"], "partial")
        self.assertFalse(gap["criterionSufficiency"]["everySurveyedDemandAreaCovered"])

    def test_native_runtime_baseline_gap_rejects_full_coverage_overclaim(self) -> None:
        path = "registry/native-runtime-baseline-evidence-gap-reconciliation-2026-07-18.json"
        gap = verify_script.load(path)
        gap["currentSurveyScope"]["everySurveyedDemandAreaHasFormalBaseline"] = True
        self.assert_verify_runtime_error(
            path,
            gap,
            "Native/runtime baseline gap current scope overclaimed",
        )

    def test_native_runtime_baseline_gap_rejects_review_as_formal_baseline(self) -> None:
        path = "registry/native-runtime-baseline-evidence-gap-reconciliation-2026-07-18.json"
        gap = verify_script.load(path)
        gap["reviewOnlyLanes"][0]["qualifiesAsFormalBaseline"] = True
        self.assert_verify_runtime_error(
            path,
            gap,
            "Native/runtime baseline gap review-only lane set drifted",
        )

    def test_round03_native_runtime_baseline_rejects_human_authority_skill_routing(self) -> None:
        path = "registry/round03-native-runtime-baseline-2026-07-15.json"
        baseline = verify_script.load(path)
        baseline["demandBaselines"][2]["publicMetadataDiscoveryEligible"] = True
        baseline["demandBaselines"][2]["externalMetadataQuestion"] = "Find a Skill to replace domain authority."
        self.assert_verify_runtime_error(path, baseline, "demand baseline incomplete")

    def test_round03_public_discovery_is_public_pinned_and_non_approving(self) -> None:
        snapshot = verify_script.load("registry/round03-public-discovery-snapshot-2026-07-15.json")
        self.assertEqual(snapshot["dataBoundary"]["githubVisibility"], "public-only")
        self.assertTrue(
            all(
                "is:public" in query["query"]
                for query_round in snapshot["queryRounds"]
                for query in query_round["queries"]
            )
        )
        self.assertEqual(len(snapshot["representativeSources"]), 9)
        self.assertTrue(all(len(source["commit"]) == 40 for source in snapshot["representativeSources"]))
        self.assertFalse(snapshot["snapshotDecision"]["thirdPartyCandidateApproved"])
        self.assertFalse(snapshot["snapshotDecision"]["residualGapProven"])

    def test_round03_public_discovery_rejects_private_query_drift(self) -> None:
        path = "registry/round03-public-discovery-snapshot-2026-07-15.json"
        snapshot = verify_script.load(path)
        snapshot["queryRounds"][0]["queries"][0]["query"] = "agent skills"
        self.assert_verify_runtime_error(path, snapshot, "query evidence drifted")

    def test_round03_public_discovery_rejects_premature_candidate_approval(self) -> None:
        path = "registry/round03-public-discovery-snapshot-2026-07-15.json"
        snapshot = verify_script.load(path)
        snapshot["snapshotDecision"]["thirdPartyCandidateApproved"] = True
        self.assert_verify_runtime_error(path, snapshot, "non-approval decision drifted")

    def test_round03_public_discovery_rejects_unpinned_representative(self) -> None:
        path = "registry/round03-public-discovery-snapshot-2026-07-15.json"
        snapshot = verify_script.load(path)
        snapshot["representativeSources"][2]["commit"] = "main"
        self.assert_verify_runtime_error(path, snapshot, "representative source drifted")

    def test_round03_representative_review_separates_skills_tools_official_and_index(self) -> None:
        review = verify_script.load("registry/round03-representative-source-review-batch-01.json")
        decision = review["batchDecision"]
        self.assertEqual(decision["reviewedSourceCount"], 9)
        self.assertEqual(decision["skillContentComparisonCount"], 2)
        self.assertEqual(decision["nonSkillToolingAlternativeCount"], 4)
        self.assertEqual(decision["approvedCandidateCount"], 0)
        handoff = next(item for item in review["reviews"] if item["sourceId"] == "github:cskwork/handoff-skill")
        self.assertFalse(handoff["contentIdentity"]["exactDuplicate"])

    def test_round03_representative_review_rejects_license_blob_drift(self) -> None:
        path = "registry/round03-representative-source-review-batch-01.json"
        review = verify_script.load(path)
        review["reviews"][2]["licenseReview"]["evidence"][0]["gitBlob"] = "0" * 40
        self.assert_verify_runtime_error(path, review, "license review drifted")

    def test_round03_representative_review_rejects_premature_approval(self) -> None:
        path = "registry/round03-representative-source-review-batch-01.json"
        review = verify_script.load(path)
        review["batchDecision"]["approvedCandidateCount"] = 1
        self.assert_verify_runtime_error(path, review, "review decision drifted")

    def test_round03_representative_review_rejects_official_body_admission(self) -> None:
        path = "registry/round03-representative-source-review-batch-01.json"
        review = verify_script.load(path)
        review["reviews"][0]["disposition"] = "candidate"
        self.assert_verify_runtime_error(path, review, "official body exclusion drifted")

    def test_round03_alternative_comparison_covers_all_paths_without_proving_a_gap(self) -> None:
        comparison = verify_script.load(
            "registry/round03-alternative-comparison-batch-01.json"
        )
        self.assertEqual(len(comparison["comparisons"]), 4)
        self.assertTrue(
            all(len(item["alternatives"]) == 9 for item in comparison["comparisons"])
        )
        decision = comparison["batchDecision"]
        self.assertEqual(decision["supportedResidualGapCount"], 0)
        self.assertEqual(decision["unprovenResidualGapCount"], 3)
        self.assertEqual(decision["nonExternalSkillGapCount"], 1)
        self.assertFalse(decision["repositoryAuthoredSkillEligible"])
        self.assertFalse(decision["hookEligible"])

    def test_round03_alternative_comparison_rejects_premature_gap_claim(self) -> None:
        path = "registry/round03-alternative-comparison-batch-01.json"
        comparison = verify_script.load(path)
        comparison["batchDecision"]["supportedResidualGapCount"] = 1
        self.assert_verify_runtime_error(path, comparison, "batch decision drifted")

    def test_round03_alternative_comparison_rejects_hook_eligibility(self) -> None:
        path = "registry/round03-alternative-comparison-batch-01.json"
        comparison = verify_script.load(path)
        comparison["batchDecision"]["hookEligible"] = True
        self.assert_verify_runtime_error(path, comparison, "batch decision drifted")

    def test_round03_alternative_comparison_rejects_lane_hook_drift(self) -> None:
        path = "registry/round03-alternative-comparison-batch-01.json"
        comparison = verify_script.load(path)
        comparison["comparisons"][0]["hookDecision"] = "enable-hook"
        self.assert_verify_runtime_error(path, comparison, "Hook default drifted")

    def test_round03_evidence_protocol_verifies_local_fixtures_but_not_live_evidence(self) -> None:
        protocol = verify_script.load("registry/round03-evidence-protocol-batch-01.json")
        self.assertTrue(protocol["localEvidence"]["deterministicEvaluationPassed"])
        self.assertEqual(protocol["localEvidence"]["fixtureCount"], 19)
        self.assertTrue(
            all(slot["status"].startswith("pending-") for slot in protocol["liveEvidenceSlots"])
        )
        self.assertIn("no Hook", protocol["hookRule"])

    def test_round03_evidence_protocol_rejects_fixture_expectation_drift(self) -> None:
        path = "tests/fixtures/round03-evidence-fixtures-batch-01.json"
        fixtures = verify_script.load(path)
        fixtures["fixtures"][0]["expected"] = "resume-from-repository-truth"
        self.assert_verify_runtime_error(path, fixtures, "deterministic evidence fixture failed")

    def test_round03_evidence_protocol_rejects_premature_live_claim(self) -> None:
        path = "registry/round03-evidence-protocol-batch-01.json"
        protocol = verify_script.load(path)
        protocol["liveEvidenceSlots"][0]["status"] = "verified"
        self.assert_verify_runtime_error(path, protocol, "prematurely claimed")

    def test_program_step_status_validation_is_not_snapshot_hardcoded(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        program["steps"][0]["status"] = "evidence-recorded"
        verify_script.validate_curation_program_plan(program, rounds)

    def test_program_rejects_current_state_mismatch(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        program["currentState"] = "complete"
        with self.assertRaisesRegex(
            RuntimeError,
            "currentState must match the current step status",
        ):
            verify_script.validate_curation_program_plan(program, rounds)

    def test_program_treats_calibration_as_read_only_research_input(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        delivery = program["strategicPositioning"]["standardCandidateDelivery"]
        self.assertEqual(delivery["calibrationRepository"], "YIYUAN-CALIBRATION")
        self.assertEqual(
            delivery["calibrationRepositoryRole"],
            "read-only-candidate-evidence-and-research-input",
        )
        self.assertFalse(delivery["calibrationRepositoryInMeridianMatrix"])
        self.assertFalse(delivery["consumerConfigurationMayBeDurableAuthority"])
        self.assertEqual(delivery["projectAdmissionAuthority"], "applicable-project-authority")
        self.assertEqual(delivery["finalStandardsCarrier"], "applicable-project-authority")
        self.assertEqual(delivery["finalCarrierModes"], ["built-in", "knowledge-base"])
        objective = next(
            item
            for item in program["strategicObjectives"]
            if item["id"] == "objective.standard-candidate-extraction"
        )
        self.assertIn("acceptance.calibration-reference-boundary", objective["acceptanceIds"])

    def test_program_rejects_calibration_as_meridian_matrix_node(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        program["strategicPositioning"]["standardCandidateDelivery"][
            "calibrationRepositoryInMeridianMatrix"
        ] = True
        with self.assertRaisesRegex(RuntimeError, "read-only research input"):
            verify_script.validate_curation_program_plan(program, rounds)

    def test_program_rejects_calibration_as_final_standards_carrier(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        program["strategicPositioning"]["standardCandidateDelivery"][
            "finalStandardsCarrier"
        ] = "YIYUAN-CALIBRATION"
        with self.assertRaisesRegex(RuntimeError, "applicable project admission and carriage"):
            verify_script.validate_curation_program_plan(program, rounds)

    def test_program_control_includes_missing_objectives_and_stable_lanes(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        objective_ids = {item["id"] for item in program["strategicObjectives"]}
        required_objectives = {
            "objective.multi-domain-coverage",
            "objective.evidence-backed-release-evolution",
            "objective.evidence-backed-demand-model",
            "objective.reuse-before-build-gap-proof",
            "objective.full-chain-capability-coverage",
            "objective.decision-ready-external-brain",
            "objective.source-preserving-cross-agent-capability-governance",
            "objective.custom-manager-retirement-evidence-preservation",
        }
        self.assertTrue(required_objectives <= objective_ids)
        lane_ids = {
            item["id"] for item in program["programArchitecture"]["operatingLanes"]
        }
        self.assertTrue(
            {
                "lane.demand-evidence",
                "lane.native-official-runtime-baseline",
                "lane.solution-alternative-comparison",
                "lane.residual-gap-decision",
                "lane.standard-extraction-and-calibration-handoff",
            }
            <= lane_ids
        )

    def test_program_objective_set_is_extensible(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        acceptance = verify_script.load("registry/program-acceptance-map.json")
        future_objective = {
            "id": "objective.future-reviewed-extension",
            "statement": "Preserve reviewed extension points without weakening current authority.",
            "authorityOwner": "agent-skills-curated",
            "nonGoals": ["bypassing governed program review"],
            "acceptanceIds": ["acceptance.future-terminal-boundary"],
        }
        program["strategicObjectives"].append(future_objective)
        acceptance["objectives"].append(
            {
                "id": future_objective["id"],
                "acceptanceIds": future_objective["acceptanceIds"],
            }
        )
        verify_script.validate_curation_program_plan(program, rounds)
        verify_script.validate_program_acceptance_map(acceptance, program)

    def test_program_rejects_runtime_sync_as_mandatory_stable_lane(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        program["programArchitecture"]["operatingLanes"].append(
            {
                "id": "lane.mandatory-local-runtime-sync",
                "purpose": "Require every release to mutate a local consumer runtime.",
                "requiredInputs": ["curated release"],
                "allowedOutputs": ["local runtime mutation"],
                "blockedTransitions": ["none"],
                "verificationSurface": ["local path changed"],
                "rerouteTriggers": ["local runtime unavailable"],
            }
        )
        with self.assertRaisesRegex(RuntimeError, "consumer runtime sync"):
            verify_script.validate_curation_program_plan(program, rounds)

    def test_program_rejects_gap_fill_without_residual_gap_gate(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        origin = next(
            item
            for item in program["candidateOriginPolicy"]["classes"]
            if item["id"] == "repository-authored-gap-fill-candidate"
        )
        origin["eligibilityGate"] = "discovery-only"
        with self.assertRaisesRegex(RuntimeError, "residual gap"):
            verify_script.validate_curation_program_plan(program, rounds)

    def test_capability_survey_acceptance_contract_is_complete(self) -> None:
        acceptance = verify_script.load("registry/program-acceptance-map.json")
        criterion_ids = {item["id"] for item in acceptance["acceptanceCriteria"]}
        self.assertTrue(
            {
                "acceptance.native-runtime-baseline",
                "acceptance.discovery-clustering-stop-rule",
                "acceptance.alternative-comparison",
                "acceptance.residual-gap-proof",
                "acceptance.capability-survey-result-package",
                "acceptance.complete-coordinate-envelope-reconciliation",
                "acceptance.cross-agent-claim-limits",
                "acceptance.solution-neutral-collaboration-rebaseline",
                "acceptance.software-engineering-lifecycle-specialization",
                "acceptance.end-to-end-process-fidelity",
                "acceptance.ai-independent-hard-standard-boundary",
            }
            <= criterion_ids
        )
        criteria = {item["id"]: item for item in acceptance["acceptanceCriteria"]}
        self.assertEqual(criteria["acceptance.capability-survey-result-package"]["assessment"], "verified")
        self.assertEqual(criteria["acceptance.full-chain-coverage-matrix"]["assessment"], "verified")
        self.assertEqual(criteria["acceptance.residual-gap-proof"]["assessment"], "partial")
        self.assertEqual(criteria["acceptance.cross-agent-claim-limits"]["assessment"], "verified")
        self.assertEqual(
            criteria["acceptance.solution-neutral-collaboration-rebaseline"][
                "assessment"
            ],
            "partial",
        )
        self.assertEqual(
            criteria["acceptance.software-engineering-lifecycle-specialization"][
                "assessment"
            ],
            "partial",
        )
        self.assertEqual(
            criteria["acceptance.end-to-end-process-fidelity"]["assessment"],
            "partial",
        )
        self.assertEqual(
            criteria["acceptance.ai-independent-hard-standard-boundary"][
                "assessment"
            ],
            "verified",
        )

    def test_residual_gap_proof_stays_partial_and_non_vacuous(self) -> None:
        gap = verify_script.load(
            "registry/residual-gap-proof-evidence-gap-reconciliation-2026-07-18.json"
        )
        self.assertTrue(gap["proofContract"]["rejectionFirewallVerified"])
        self.assertFalse(gap["proofContract"]["positiveSupportPathExercised"])
        self.assertEqual(gap["boundedEvidence"]["supportedResidualSkillGapCount"], 0)
        self.assertFalse(gap["nonVacuityRule"]["zeroSupportedGapsProvesPositiveSupportPath"])
        self.assertEqual(gap["decision"]["to"], "partial")

    def test_residual_gap_proof_rejects_positive_path_overclaim(self) -> None:
        path = "registry/residual-gap-proof-evidence-gap-reconciliation-2026-07-18.json"
        gap = verify_script.load(path)
        gap["proofContract"]["positiveSupportPathExercised"] = True
        self.assert_verify_runtime_error(
            path,
            gap,
            "Residual-gap proof reconciliation proof contract overclaimed",
        )

    def test_residual_gap_proof_rejects_open_evidence_gap_as_skill_gap(self) -> None:
        path = "registry/residual-gap-proof-evidence-gap-reconciliation-2026-07-18.json"
        gap = verify_script.load(path)
        gap["gapClassSeparation"][1]["isResidualSkillGap"] = True
        self.assert_verify_runtime_error(
            path,
            gap,
            "Residual-gap proof reconciliation gap-class separation overclaimed",
        )

    def test_manager_and_coverage_acceptance_contracts_are_mapped_honestly(self) -> None:
        acceptance = verify_script.load("registry/program-acceptance-map.json")
        criteria = {item["id"]: item for item in acceptance["acceptanceCriteria"]}
        self.assertEqual(
            criteria["acceptance.evidence-backed-release-evolution"]["assessment"],
            "verified",
        )
        self.assertEqual(criteria["acceptance.manager-design-contract"]["assessment"], "verified")
        self.assertEqual(
            criteria["acceptance.manager-topology-impact-gate"]["assessment"],
            "verified",
        )
        self.assertEqual(
            criteria["acceptance.native-task-orchestration-boundary"]["assessment"],
            "partial",
        )
        evidence = next(
            item
            for item in acceptance["evidence"]
            if item["id"] == "evidence.production-capability-manager-design"
        )
        self.assertEqual(
            evidence["path"],
            "docs/superpowers/specs/2026-07-15-production-capability-manager-design.md",
        )

    def test_manager_is_superseded_and_does_not_replace_active_survey(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        self.assertEqual(program["currentInitiativeId"], "initiative.capability-survey-gap-proof")
        manager = next(
            item
            for item in program["currentInitiatives"]
            if item["id"] == "initiative.production-capability-manager-topology-design"
        )
        self.assertEqual(manager["status"], "superseded")
        self.assertIn(
            "acceptance.manager-foundation-transaction-closure",
            manager["acceptanceIds"],
        )
        self.assertNotIn("acceptance.evidence-backed-release-evolution", manager["acceptanceIds"])
        blocked = " ".join(manager["blockedActions"]).lower()
        for phrase in [
            "real agent adapter or configuration writes",
            "existing-repository integration writes",
            "hook enablement or mutation",
            "remote push",
        ]:
            self.assertIn(phrase, blocked)
        self.assertIn("further manager implementation", blocked)
        allowed = " ".join(manager["allowedActions"]).lower()
        self.assertIn("preserve historical design and implementation evidence", allowed)
        self.assertIn("read-only verification that the retired local experiment remains absent", allowed)

    def test_manager_preserves_historical_gates_and_source_preflight_is_current(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        gate = next(
            item
            for item in program["sequenceGates"]
            if item["id"] == "gate.manager-topology-before-repository-creation"
        )
        text = " ".join(str(value) for value in gate.values()).lower()
        self.assertEqual(gate["status"], "historical-satisfied")
        for phrase in [
            "owner-reviewed written manager design",
            "meridian topology-impact package",
            "completed local manager repository-creation decision",
            "bookmark and radar",
            "rollback",
            "retirement",
        ]:
            self.assertIn(phrase, text)
        current_gate = next(
            item
            for item in program["sequenceGates"]
            if item["id"] == "gate.manager-post-matrix-reintake-before-adapter-work"
        )
        current_text = " ".join(str(value) for value in current_gate.values()).lower()
        self.assertEqual(current_gate["status"], "historical-satisfied")
        for phrase in [
            "dated repository truth",
            "calibration read-only",
            "historical curated and manager authority",
            "real agent and hook write prohibition",
        ]:
            self.assertIn(phrase, current_text)
        source_gate = next(
            item
            for item in program["sequenceGates"]
            if item["id"] == "gate.source-preflight-before-download-or-install"
        )
        source_text = " ".join(str(value) for value in source_gate.values()).lower()
        for phrase in ["metadata license provenance", "non-active pool", "non-execution boundary"]:
            self.assertIn(phrase, source_text)

    def test_native_task_orchestration_is_parent_reconciled_and_write_isolated(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        parallel = " ".join(
            program["programArchitecture"]["executionSemantics"]["safeParallelism"]
        ).lower()
        for phrase in ["child tasks", "parent reconciliation", "shared-checkout writes", "isolation"]:
            self.assertIn(phrase, parallel)

    def test_standard_revalidation_requires_accepted_standard_and_affected_graph(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        gate = next(
            item
            for item in program["sequenceGates"]
            if item["id"] == "gate.accepted-standard-before-revalidation"
        )
        text = " ".join(str(value) for value in gate.values()).lower()
        for phrase in ["standard accepted", "affected-graph query", "bounded batches", "new baseline"]:
            self.assertIn(phrase, text)

    def test_manager_design_semantic_contract_rejects_missing_parent_authority(self) -> None:
        design_path = ROOT / "docs/superpowers/specs/2026-07-15-production-capability-manager-design.md"
        original_read_text = Path.read_text

        def read_text_without_parent_authority(path: Path, *args: object, **kwargs: object) -> str:
            content = original_read_text(path, *args, **kwargs)
            if path == design_path:
                return content.replace(
                    "The parent task owns experiment design",
                    "The coordinator handles experiment design",
                )
            return content

        with patch.object(
            Path,
            "read_text",
            read_text_without_parent_authority,
        ), without_task4_manifest_poc_replay():
            with self.assertRaisesRegex(
                RuntimeError,
                "parent task owns experiment design",
            ):
                verify_script.verify()

    def test_program_records_owner_acceptance_and_activates_capability_survey(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        self.assertEqual(
            program["currentInitiativeId"],
            "initiative.capability-survey-gap-proof",
        )
        completeness = next(
            item
            for item in program["currentInitiatives"]
            if item["id"] == "initiative.program-control-completeness-reconciliation"
        )
        current = next(
            item
            for item in program["currentInitiatives"]
            if item["id"] == program["currentInitiativeId"]
        )
        self.assertEqual(completeness["status"], "accepted")
        self.assertEqual(current["status"], "active")
        rebaseline = next(
            item
            for item in program["currentInitiatives"]
            if item["id"] == "initiative.round03-capability-survey-rebaseline"
        )
        self.assertEqual(rebaseline["status"], "accepted")
        event = verify_script.load("registry/program-control-acceptance-event-2026-07-15.json")
        self.assertEqual(
            event["acceptedBaselineCommit"],
            "7513da41e9c2950de1a6132ce9c9d65fb11a8098",
        )
        self.assertEqual(event["decision"], "accepted-and-merged-locally")
        self.assertFalse(event["remotePushAuthorized"])

    def test_program_control_acceptance_event_does_not_authorize_remote_push(self) -> None:
        path = "registry/program-control-acceptance-event-2026-07-15.json"
        event = verify_script.load(path)
        event["remotePushAuthorized"] = True
        self.assert_verify_runtime_error(path, event, "must not authorize remote push")

    def test_program_declares_dependency_graph_order_semantics(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        semantics = program["programArchitecture"]["executionSemantics"]
        self.assertEqual(
            semantics["model"],
            "dependency-graph-with-optional-and-cross-cutting-lanes",
        )
        self.assertEqual(
            semantics["corePath"],
            [
                "lane.demand-evidence",
                "lane.native-official-runtime-baseline",
                "lane.discovery-and-clustering",
                "lane.representative-deep-review",
                "lane.solution-alternative-comparison",
                "lane.residual-gap-decision",
                "lane.candidate-governance-and-adaptation",
                "lane.admission-verification-and-release",
            ],
        )
        self.assertEqual(
            semantics["optionalBranches"],
            ["lane.consumer-evidence-and-feedback"],
        )
        self.assertEqual(
            semantics["crossCuttingLanes"],
            ["lane.lifecycle-metabolism"],
        )
        self.assertEqual(
            semantics["conditionalBranches"],
            ["lane.standard-extraction-and-calibration-handoff"],
        )

    def test_program_rejects_lifecycle_that_requires_consumer_evidence(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        lifecycle = next(
            item
            for item in program["programArchitecture"]["operatingLanes"]
            if item["id"] == "lane.lifecycle-metabolism"
        )
        lifecycle["requiredInputs"] = ["release and consumer evidence"]
        with self.assertRaisesRegex(RuntimeError, "lifecycle.*consumer"):
            verify_script.validate_curation_program_plan(program, rounds)

    def test_program_requires_source_pin_before_representative_deep_review(self) -> None:
        program = verify_script.load("registry/curation-program-plan.json")
        rounds = verify_script.load("registry/curation-expansion-rounds.json")
        review = next(
            item
            for item in program["programArchitecture"]["operatingLanes"]
            if item["id"] == "lane.representative-deep-review"
        )
        review["requiredInputs"] = [
            "clustered shortlist",
            "dated metadata",
            "review questions",
        ]
        with self.assertRaisesRegex(RuntimeError, "source pin"):
            verify_script.validate_curation_program_plan(program, rounds)

    def test_rejects_skill_unknown_field_before_semantic_access(self) -> None:
        document = verify_script.load("registry/skills.json")
        document["skills"][0]["statuz"] = "approved"
        self.assert_verify_contract_error(
            "registry/skills.json", document, "/skills/0/statuz"
        )

    def test_rejects_malformed_registry_as_contract_error(self) -> None:
        document = verify_script.load("registry/skills.json")
        document["skills"] = {"not": "an array"}
        self.assert_verify_contract_error("registry/skills.json", document, "/skills")

    def test_main_reports_contract_error_without_traceback(self) -> None:
        error = ContractError("registry/skills.json", "/skills", "must be an array")
        stderr = StringIO()
        with patch.object(verify_script, "verify", side_effect=error):
            with redirect_stderr(stderr):
                result = verify_script.main()

        self.assertEqual(result, 1)
        self.assertEqual(
            stderr.getvalue(),
            "Contract error: registry/skills.json:/skills: must be an array\n",
        )
        self.assertNotIn("Traceback", stderr.getvalue())


class ReferenceValidationIntegrationTests(unittest.TestCase):
    def test_verify_rejects_missing_curated_capability_owner(self) -> None:
        path = "registry/capabilities.json"
        document = verify_script.load(path)
        document["capabilities"][0]["canonicalOwner"] = "skill.curated.missing"
        original_load = verify_script.load

        def load_with_mutation(candidate: str) -> dict[str, object]:
            if candidate == path:
                return deepcopy(document)
            return original_load(candidate)

        with patch.object(
            verify_script,
            "load",
            side_effect=load_with_mutation,
        ), without_task4_manifest_poc_replay():
            with self.assertRaises(ContractError) as raised:
                verify_script.verify()

        self.assertEqual(raised.exception.document, path)
        self.assertEqual(raised.exception.pointer, "/capabilities/0/canonicalOwner")


class EvaluationStandardsReconciliationIntegrationTests(unittest.TestCase):
    def test_verify_calls_evaluation_software_engineering_reconciliation_once(
        self,
    ) -> None:
        with patch.object(
            verify_script,
            "validate_program_acceptance_authority_v2_rehearsal",
            return_value={},
        ), patch.object(
            verify_script,
            "validate_evaluation_software_engineering_standards_coverage_reconciliation_v1",
            create=True,
        ) as validator:
            verify_script.verify()

        validator.assert_called_once_with(verify_script.ROOT)

    def test_reconciliation_files_are_required_verifier_inputs(self) -> None:
        for path in (
            "registry/evaluation-software-engineering-standards-coverage-reconciliation-v1-2026-08-11.json",
            "scripts/validate_evaluation_software_engineering_standards_coverage_reconciliation_v1.py",
            "tests/test_evaluation_software_engineering_standards_coverage_reconciliation_v1.py",
            "docs/strategy/EVALUATION-SOFTWARE-ENGINEERING-STANDARDS-COVERAGE-RECONCILIATION-V1-2026-08-11.md",
            "docs/superpowers/specs/2026-08-11-evaluation-software-engineering-standards-coverage-reconciliation-v1-design.md",
            "docs/superpowers/plans/2026-08-11-evaluation-software-engineering-standards-coverage-reconciliation-v1.md",
            "docs/superpowers/specs/2026-08-11-evidence-binding-precision-reconciliation-v1-design.md",
            "docs/superpowers/plans/2026-08-11-evidence-binding-precision-reconciliation-v1.md",
        ):
            self.assertIn(path, verify_script.REQUIRED_FILES)

if __name__ == "__main__":
    unittest.main()
