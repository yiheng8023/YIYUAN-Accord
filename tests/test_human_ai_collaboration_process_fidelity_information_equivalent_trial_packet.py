import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
    BUILD_MANIFEST_NAME,
    PACKAGE_FILE_NAMES,
    PUBLIC_BUNDLE_NAME,
    TRIAL_PACKET_NAME,
    build_packet_package,
)
from scripts.validate_human_ai_collaboration_process_fidelity_information_equivalent_trial_packet import (
    evaluate_packet_package,
    validate_packet_package,
)


ROOT = Path(__file__).resolve().parent.parent


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class InformationEquivalentProcessFidelityPacketTests(unittest.TestCase):
    def _build(self, base: Path) -> Path:
        output = base / "packet"
        result = build_packet_package(output, root=ROOT)
        self.assertEqual(result["dispatchCount"], 0)
        self.assertFalse(result["agentRunStartedAtBuildTime"])
        self.assertFalse(result["privateOracleContentWritten"])
        return output

    def test_current_packet_build_and_preflight_are_zero_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            self.assertEqual(
                sorted(item.name for item in output.iterdir()),
                sorted(PACKAGE_FILE_NAMES),
            )
            report = validate_packet_package(output, root=ROOT)
            self.assertEqual(
                report["status"],
                "passed-zero-dispatch-live-authority-still-required",
            )
            self.assertEqual(report["dispatchCount"], 0)
            self.assertEqual(report["scoredArmIds"], [])
            self.assertFalse(report["liveTaskCreationAuthorized"])

    def test_builder_refuses_nonempty_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "packet"
            output.mkdir()
            (output / "existing.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "empty directory"):
                build_packet_package(output, root=ROOT)
            self.assertEqual(
                (output / "existing.txt").read_text(encoding="utf-8"),
                "preserve",
            )

    def test_public_bundle_drift_blocks_without_dispatch_or_scoring(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            bundle_path = output / PUBLIC_BUNDLE_NAME
            bundle = _load(bundle_path)
            bundle["sourcePacket"][0]["text"] += " drift"
            _write(bundle_path, bundle)
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn(
                "fail-public-information-bundle",
                report["failureCodes"],
            )
            self.assertEqual(report["dispatchCount"], 0)
            self.assertEqual(report["scoredArmIds"], [])

    def test_private_oracle_content_injection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            packet_path = output / TRIAL_PACKET_NAME
            packet = _load(packet_path)
            packet["arms"][0]["publicMessagePlan"][0]["payload"][
                "privateExpectedState"
            ] = "supported"
            _write(packet_path, packet)
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn(
                "fail-arm-information-equivalence-or-confound",
                report["failureCodes"],
            )
            self.assertEqual(report["dispatchCount"], 0)

    def test_model_confound_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            packet_path = output / TRIAL_PACKET_NAME
            packet = _load(packet_path)
            packet["arms"][1]["requestedModel"] = "gpt-5.6-terra"
            _write(packet_path, packet)
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn(
                "fail-arm-information-equivalence-or-confound",
                report["failureCodes"],
            )
            self.assertEqual(report["scoredArmIds"], [])

    def test_source_backed_locator_or_hash_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            packet_path = output / TRIAL_PACKET_NAME
            packet = _load(packet_path)
            packet["arms"][2]["publicMessagePlan"][0]["payload"][
                "requiredCanonicalSha256"
            ] = "0" * 64
            _write(packet_path, packet)
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn(
                "fail-arm-information-equivalence-or-confound",
                report["failureCodes"],
            )
            self.assertEqual(report["dispatchCount"], 0)

    def test_automatic_thread_claim_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            packet_path = output / TRIAL_PACKET_NAME
            packet = _load(packet_path)
            packet["authorityBoundary"][
                "automaticThreadCreationClaimed"
            ] = True
            _write(packet_path, packet)
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn("fail-authority-promotion", report["failureCodes"])
            self.assertEqual(report["dispatchCount"], 0)

    def test_missing_arm_cannot_be_scored_or_ranked(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            packet_path = output / TRIAL_PACKET_NAME
            packet = _load(packet_path)
            packet["arms"].pop()
            _write(packet_path, packet)
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn(
                "fail-arm-information-equivalence-or-confound",
                report["failureCodes"],
            )
            self.assertEqual(report["scoredArmIds"], [])

    def test_parent_root_or_command_projection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            packet_path = output / TRIAL_PACKET_NAME
            packet = _load(packet_path)
            packet["agentVisibleProjection"][
                "parentEvidenceRootIsRuntimeWorkspaceRoot"
            ] = True
            packet["agentVisibleProjection"][
                "shellOrCommandExecutionAllowed"
            ] = True
            _write(packet_path, packet)
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn(
                "fail-agent-visible-projection",
                report["failureCodes"],
            )
            self.assertEqual(report["dispatchCount"], 0)

    def test_manifest_drift_and_extra_file_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = self._build(Path(raw))
            manifest_path = output / BUILD_MANIFEST_NAME
            manifest = _load(manifest_path)
            manifest["dispatchCount"] = 1
            _write(manifest_path, manifest)
            (output / "EXTRA.txt").write_text("unexpected", encoding="utf-8")
            report = evaluate_packet_package(output, root=ROOT)
            self.assertIn("fail-package-file-set", report["failureCodes"])
            self.assertIn("fail-build-manifest", report["failureCodes"])
            self.assertEqual(report["dispatchCount"], 0)


if __name__ == "__main__":
    unittest.main()
