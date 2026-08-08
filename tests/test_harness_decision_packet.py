import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.harness_decision_packet import (
    build_decision_packet,
    DecisionPacketError,
    canonical_sha256,
    load_authority_bundle,
    serialize_decision_packet,
    validate_decision_request,
    validate_authority_bundle,
    validate_bound_source_digests,
    validate_decision_packet,
)

ROOT = Path(__file__).resolve().parent.parent
REQUEST_PATH = Path("tests/fixtures/harness-decision-request-gen-research-01.json")


class HarnessDecisionPacketContractTests(unittest.TestCase):
    def load_request(self) -> dict[str, object]:
        return json.loads((ROOT / REQUEST_PATH).read_text(encoding="utf-8"))

    def test_portfolio_request_is_valid_and_canonical(self) -> None:
        request = self.load_request()
        validate_decision_request(request)
        self.assertEqual(64, len(canonical_sha256(request)))

    def test_boolean_activation_authority_is_rejected(self) -> None:
        request = self.load_request()
        request["activationAuthority"] = True
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-activation-authority", raised.exception.code)

    def test_unknown_request_field_is_rejected(self) -> None:
        request = self.load_request()
        request["selectedSkill"] = "skill.curated.grill-with-docs"
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-request-shape", raised.exception.code)

    def test_task_time_request_accepts_complete_evidence_objects(self) -> None:
        request = self.load_request()
        request["evidenceLane"] = "task-time"
        request["observedAvailability"] = {
            "asOf": "2026-08-08T00:00:00Z",
            "host": "codex-desktop",
            "availableRouteClasses": ["N", "C", "H"],
            "evidencePaths": ["tests/fixtures/live-availability.json"],
        }
        request["taskBinding"] = {
            "taskId": "task.example",
            "goal": "Produce a source-bound decision packet.",
            "target": "GEN-RESEARCH-01",
            "verificationSurface": "focused unittest",
        }
        request["currentCapabilityGap"] = {
            "requiredCapability": "source-bound route evaluation",
            "observedLimitation": "no validated route decision exists",
            "evidencePaths": ["tests/fixtures/gap-evidence.json"],
        }
        request["activationAuthority"] = {
            "evidencePath": "tests/fixtures/authority.json",
            "scope": "evaluate-only",
        }

        validate_decision_request(request)

    def test_missing_request_field_is_rejected(self) -> None:
        request = self.load_request()
        del request["currentCapabilityGap"]
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_request(request)
        self.assertEqual("invalid-request-shape", raised.exception.code)

    def test_invalid_nullable_evidence_objects_are_rejected(self) -> None:
        invalid_cases = (
            ("observedAvailability", {}, "invalid-observed-availability"),
            ("taskBinding", {}, "invalid-task-binding"),
            ("currentCapabilityGap", {}, "invalid-capability-gap"),
            ("activationAuthority", {}, "invalid-activation-authority"),
        )
        for field, value, expected_code in invalid_cases:
            with self.subTest(field=field):
                request = self.load_request()
                request[field] = value
                with self.assertRaises(DecisionPacketError) as raised:
                    validate_decision_request(request)
                self.assertEqual(expected_code, raised.exception.code)

    def test_invalid_scalar_fields_are_rejected(self) -> None:
        invalid_cases = (
            ("schema", 2, "invalid-request-schema"),
            ("requestId", "", "invalid-request-id"),
            ("scenarioId", "lowercase", "invalid-scenario-id"),
            ("evidenceLane", "production", "invalid-evidence-lane"),
            ("expectedSemanticAuthorityId", "", "invalid-authority-id"),
        )
        for field, value, expected_code in invalid_cases:
            with self.subTest(field=field):
                request = self.load_request()
                request[field] = value
                with self.assertRaises(DecisionPacketError) as raised:
                    validate_decision_request(request)
                self.assertEqual(expected_code, raised.exception.code)


class HarnessDecisionPacketAuthorityTests(HarnessDecisionPacketContractTests):
    def test_current_gen_research_authority_reopens_original_evidence(self) -> None:
        request = self.load_request()
        bundle = load_authority_bundle(ROOT, request)
        validate_authority_bundle(bundle, request)
        self.assertEqual("GEN-RESEARCH-01", bundle["scenario"]["scenarioId"])
        self.assertEqual(
            [
                "registry/human-ai-collaboration-scenario-evidence-matrix-"
                "batch-01-2026-07-24.json"
            ],
            [item["path"] for item in bundle["sourceEvidence"]],
        )
        self.assertFalse(
            bundle["semanticAuthority"]["document"]["legacyAdaptedRelease"]
            ["routingProjectionCurrentAuthority"]
        )

    def test_unknown_scenario_fails_closed(self) -> None:
        request = self.load_request()
        request["scenarioId"] = "GEN-UNKNOWN-01"
        with self.assertRaises(DecisionPacketError) as raised:
            load_authority_bundle(ROOT, request)
        self.assertEqual("unknown-scenario", raised.exception.code)

    def test_expected_authority_id_must_match(self) -> None:
        request = self.load_request()
        request["expectedSemanticAuthorityId"] = "stale-authority"
        with self.assertRaises(DecisionPacketError) as raised:
            load_authority_bundle(ROOT, request)
        self.assertEqual("semantic-authority-id-mismatch", raised.exception.code)

    def test_bound_original_evidence_digest_drift_is_rejected(self) -> None:
        request = self.load_request()
        bundle = load_authority_bundle(ROOT, request)
        records = [
            bundle["semanticAuthority"],
            bundle["coverage"],
            bundle["scheduler"],
            bundle["acceptance"],
            *bundle["sourceEvidence"],
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            for record in records:
                source = ROOT / record["path"]
                destination = temporary_root / record["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            evidence_path = temporary_root / bundle["sourceEvidence"][0]["path"]
            evidence_path.write_bytes(evidence_path.read_bytes() + b"\n")

            with self.assertRaises(DecisionPacketError) as raised:
                validate_bound_source_digests(temporary_root, bundle)
            self.assertEqual("evidence-source-digest-drift", raised.exception.code)


class HarnessDecisionPacketBuildTests(HarnessDecisionPacketContractTests):
    def test_v1_fixture_bytes_remain_exact_after_shared_helper_refactor(self) -> None:
        expected = (ROOT / "tests/fixtures/harness-decision-packet-gen-research-01.json").read_bytes()
        actual = serialize_decision_packet(build_decision_packet(ROOT, self.load_request()))
        self.assertEqual(expected, actual)

    def assert_packet_mutation_rejected(
        self,
        mutate,
        expected_code: str,
    ) -> None:
        packet = build_decision_packet(ROOT, self.load_request())
        mutated = copy.deepcopy(packet)
        mutate(mutated)
        body = {key: value for key, value in mutated.items() if key != "packetSha256"}
        mutated["packetSha256"] = canonical_sha256(body)
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_packet(ROOT, mutated)
        self.assertEqual(expected_code, raised.exception.code)

    def test_gen_research_packet_preserves_all_evidence_states(self) -> None:
        packet = build_decision_packet(ROOT, self.load_request())
        validate_decision_packet(ROOT, packet)
        self.assertEqual("coverage-packet-only", packet["decisionState"])
        self.assertIsNone(packet["selectedRoute"])
        self.assertEqual({"N", "O", "E", "C", "H", "R"}, set(packet["routeCoverage"]))
        self.assertEqual("unassessed", packet["routeCoverage"]["O"]["state"])
        self.assertEqual("unassessed", packet["routeCoverage"]["E"]["state"])
        self.assertEqual(
            "not-eligible-no-residual-gap",
            packet["routeCoverage"]["R"]["state"],
        )
        self.assertEqual(["N", "C", "H"], packet["fallbackOrder"])
        self.assertFalse(any(packet["claimBoundary"].values()))

    def test_repeated_build_is_byte_identical(self) -> None:
        request = self.load_request()
        first = serialize_decision_packet(build_decision_packet(ROOT, request))
        second = serialize_decision_packet(build_decision_packet(ROOT, request))
        self.assertEqual(first, second)

    def test_task_time_insufficiency_states_never_select_a_route(self) -> None:
        request = self.load_request()
        request["evidenceLane"] = "task-time"
        cases = (
            ("needs-task-binding", None),
            (
                "needs-current-capability-gap",
                (
                    "taskBinding",
                    {
                        "taskId": "task.example",
                        "goal": "Evaluate current route sufficiency.",
                        "target": "GEN-RESEARCH-01",
                        "verificationSurface": "bounded packet validation",
                    },
                ),
            ),
            (
                "needs-live-availability",
                (
                    "currentCapabilityGap",
                    {
                        "requiredCapability": "source-bound route evaluation",
                        "observedLimitation": "no validated route decision exists",
                        "evidencePaths": ["tests/fixtures/gap-evidence.json"],
                    },
                ),
            ),
            (
                "needs-activation-authority",
                (
                    "observedAvailability",
                    {
                        "asOf": "2026-08-08T00:00:00Z",
                        "host": "codex-desktop",
                        "availableRouteClasses": ["N", "C", "H"],
                        "evidencePaths": ["tests/fixtures/live-availability.json"],
                    },
                ),
            ),
            (
                "needs-human-judgment",
                (
                    "activationAuthority",
                    {
                        "evidencePath": "tests/fixtures/authority.json",
                        "scope": "evaluate-only",
                    },
                ),
            ),
        )
        for expected_state, update in cases:
            if update is not None:
                field, value = update
                request[field] = value
            with self.subTest(expected_state=expected_state):
                packet = build_decision_packet(ROOT, request)
                self.assertEqual(expected_state, packet["decisionState"])
                self.assertIsNone(packet["selectedRoute"])

    def test_packet_digest_mutation_is_rejected(self) -> None:
        packet = build_decision_packet(ROOT, self.load_request())
        mutated = copy.deepcopy(packet)
        mutated["packetSha256"] = "0" * 64
        with self.assertRaises(DecisionPacketError) as raised:
            validate_decision_packet(ROOT, mutated)
        self.assertEqual("packet-digest-mismatch", raised.exception.code)

    def test_unassessed_route_promotion_is_rejected(self) -> None:
        self.assert_packet_mutation_rejected(
            lambda packet: packet["routeCoverage"]["O"].__setitem__(
                "state", "represented-source-static"
            ),
            "unassessed-route-promotion",
        )

    def test_residual_route_promotion_is_rejected(self) -> None:
        self.assert_packet_mutation_rejected(
            lambda packet: packet["routeCoverage"]["R"].__setitem__(
                "state", "represented-residual-gap"
            ),
            "residual-gap-promotion",
        )

    def test_behavior_claim_promotion_is_rejected(self) -> None:
        self.assert_packet_mutation_rejected(
            lambda packet: packet["claimBoundary"].__setitem__(
                "candidateCausationProved", True
            ),
            "claim-boundary-promotion",
        )

    def test_deprecated_routing_authority_promotion_is_rejected(self) -> None:
        request = self.load_request()
        bundle = load_authority_bundle(ROOT, request)
        mutated = copy.deepcopy(bundle)
        mutated["semanticAuthority"]["document"]["legacyAdaptedRelease"][
            "routingProjectionCurrentAuthority"
        ] = True
        with self.assertRaises(DecisionPacketError) as raised:
            validate_authority_bundle(mutated, request)
        self.assertEqual("deprecated-routing-authority-promotion", raised.exception.code)

    def test_portable_core_cc_switch_dependency_is_rejected(self) -> None:
        request = self.load_request()
        bundle = load_authority_bundle(ROOT, request)
        mutated = copy.deepcopy(bundle)
        mutated["semanticAuthority"]["document"]["managerBoundary"][
            "portableProductDependency"
        ] = True
        with self.assertRaises(DecisionPacketError) as raised:
            validate_authority_bundle(mutated, request)
        self.assertEqual("portable-core-dependency-promotion", raised.exception.code)

    def test_cli_emits_canonical_packet_without_repository_writes(self) -> None:
        before = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "scripts/build_harness_decision_packet.py",
                str(REQUEST_PATH),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        after = subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout

        self.assertEqual(0, result.returncode)
        self.assertEqual(b"", result.stderr)
        self.assertEqual(before, after)
        packet = json.loads(result.stdout)
        self.assertEqual(result.stdout, serialize_decision_packet(packet))
        self.assertIsNone(packet["selectedRoute"])

    def test_cli_invalid_request_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            request_path = Path(temporary_directory) / "invalid.json"
            request_path.write_text("{", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "scripts/build_harness_decision_packet.py",
                    str(request_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
            )

        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        error = json.loads(result.stderr)
        self.assertEqual("request-read-failed", error["code"])
