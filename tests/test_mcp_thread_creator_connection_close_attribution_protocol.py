from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.validate_mcp_thread_creator_connection_close_attribution_protocol import (
    BOUND_FILE_SHA256,
    EXPECTED_NON_CLAIMS,
    EXPECTED_OUTCOMES,
    PROTOCOL_PATH,
    PROTOCOL_SOURCE_SHA256,
    file_sha256,
    load_and_validate_protocol,
    validate_protocol,
)


ROOT = Path(__file__).resolve().parent.parent


class McpThreadCreatorConnectionCloseProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol_path = ROOT / PROTOCOL_PATH
        self.document = json.loads(
            self.protocol_path.read_text(encoding="utf-8")
        )

    def validate(self, document: dict | None = None) -> None:
        validate_protocol(
            self.document if document is None else document,
            root=ROOT,
        )

    def test_current_protocol_source_digest_and_bindings_are_valid(self) -> None:
        self.assertEqual(
            file_sha256(self.protocol_path), PROTOCOL_SOURCE_SHA256
        )
        load_and_validate_protocol(root=ROOT)

    def test_bound_probe_fixture_and_probe_test_hashes_are_exact(self) -> None:
        self.assertEqual(len(BOUND_FILE_SHA256), 3)
        for relative_path, expected in BOUND_FILE_SHA256.items():
            self.assertEqual(file_sha256(ROOT / relative_path), expected)

    def test_rejects_protocol_source_digest_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mutated_path = Path(directory) / "protocol.json"
            mutated_path.write_bytes(
                self.protocol_path.read_bytes() + b"\n"
            )
            with self.assertRaisesRegex(
                RuntimeError, "source digest drifted"
            ):
                load_and_validate_protocol(
                    root=ROOT,
                    protocol_path=mutated_path,
                )

    def test_rejects_bound_probe_file_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            protocol_destination = temp_root / PROTOCOL_PATH
            protocol_destination.parent.mkdir(
                parents=True, exist_ok=True
            )
            shutil.copy2(self.protocol_path, protocol_destination)
            for relative_path in BOUND_FILE_SHA256:
                source = ROOT / relative_path
                destination = temp_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            probe_path = next(
                temp_root / path
                for path in BOUND_FILE_SHA256
                if path.startswith("scripts/")
            )
            probe_path.write_bytes(probe_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                RuntimeError, "Bound file SHA256 drifted"
            ):
                load_and_validate_protocol(root=temp_root)

    def test_rejects_live_status_promotion(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["status"] = "live-paired-runs-passed"
        with self.assertRaisesRegex(
            RuntimeError, "identity or status drifted"
        ):
            self.validate(mutated)

    def test_rejects_repetition_reduction(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["design"]["repetitions"] = 1
        with self.assertRaisesRegex(RuntimeError, "paired design drifted"):
            self.validate(mutated)

    def test_rejects_observer_or_app_server_liveness_weakening(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["design"]["window"]["forbiddenActions"].remove(
            "observer connection close"
        )
        with self.assertRaisesRegex(
            RuntimeError, "forbidden window actions drifted"
        ):
            self.validate(mutated)

    def test_rejects_host_rpc_inside_window(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["design"]["window"]["forbiddenActions"].remove(
            "mcpServer/tool/call"
        )
        with self.assertRaisesRegex(
            RuntimeError, "forbidden window actions drifted"
        ):
            self.validate(mutated)

    def test_rejects_post_call_before_evidence_seal(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["design"]["evidenceSeal"] = (
            "The observer post-window call may happen before sealing."
        )
        with self.assertRaisesRegex(
            RuntimeError, "evidence ordering drifted"
        ):
            self.validate(mutated)

    def test_rejects_pre_registered_outcome_mutation(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["preRegisteredOutcomes"][
            "creator-connection-close-release-associated-bounded"
        ] = "Any treatment stop is attributed to connection close."
        with self.assertRaisesRegex(
            RuntimeError, "preregistered outcomes drifted"
        ):
            self.validate(mutated)
        self.assertEqual(
            set(self.document["preRegisteredOutcomes"]),
            set(EXPECTED_OUTCOMES),
        )

    def test_rejects_task_end_claim_promotion(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["nonClaims"].remove("Connection close is task end.")
        with self.assertRaisesRegex(
            RuntimeError, "forbidden claims drifted"
        ):
            self.validate(mutated)
        self.assertEqual(set(self.document["nonClaims"]), EXPECTED_NON_CLAIMS)

    def test_rejects_added_positive_claim_surface(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["positiveClaims"] = {
            "creatorConnectionIsLeaseOwner": True
        }
        with self.assertRaisesRegex(
            RuntimeError, "top-level surface drifted"
        ):
            self.validate(mutated)

    def test_rejects_lease_or_reference_count_claim_promotion(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["nonClaims"].remove(
            "A public or internal reference count exists."
        )
        with self.assertRaisesRegex(
            RuntimeError, "forbidden claims drifted"
        ):
            self.validate(mutated)

    def test_rejects_liveness_validity_weakening(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["validityRequirements"][7] = (
            "Connection B and the app-server may exit during the window."
        )
        with self.assertRaisesRegex(
            RuntimeError, "validity requirements drifted"
        ):
            self.validate(mutated)

    def test_rejects_model_or_account_authority_promotion(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"]["modelOrAccountUseAuthorized"] = True
        with self.assertRaisesRegex(
            RuntimeError, "execution boundary was weakened"
        ):
            self.validate(mutated)

    def test_rejects_live_loopback_execution_authority_promotion(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["executionBoundary"][
            "loopbackTransportExecutionAuthorized"
        ] = True
        with self.assertRaisesRegex(
            RuntimeError, "execution boundary was weakened"
        ):
            self.validate(mutated)

    def test_rejects_missing_raw_artifact(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["requiredArtifactsPerArm"].remove("rpc-ledger.json")
        with self.assertRaisesRegex(
            RuntimeError, "required artifact set drifted"
        ):
            self.validate(mutated)


if __name__ == "__main__":
    unittest.main()
