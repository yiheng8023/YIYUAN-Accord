import copy
import json
import unittest

from scripts.build_multidimensional_software_engineering_source_snapshot import (
    EVALUATION_CONTRACT_PATH,
    OBSERVATION_PATH,
    ROOT,
    SNAPSHOT_CONTRACT_PATH,
    SNAPSHOT_PATH,
    SourceSnapshotError,
    build_snapshot,
)
from scripts.validate_multidimensional_software_engineering_source_snapshot import (
    validate_snapshot,
)


class MultidimensionalSoftwareEngineeringSourceSnapshotTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evaluation_contract = json.loads(
            (ROOT / EVALUATION_CONTRACT_PATH).read_text(encoding="utf-8")
        )
        cls.snapshot_contract = json.loads(
            (ROOT / SNAPSHOT_CONTRACT_PATH).read_text(encoding="utf-8")
        )
        cls.observation = json.loads(
            (ROOT / OBSERVATION_PATH).read_text(encoding="utf-8")
        )
        cls.snapshot = json.loads(
            (ROOT / SNAPSHOT_PATH).read_text(encoding="utf-8")
        )

    def test_checked_in_snapshot_matches_offline_rebuild(self) -> None:
        validate_snapshot()

    def test_missing_source_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.observation)
        mutated["sourceObservations"].pop()
        with self.assertRaisesRegex(SourceSnapshotError, "source set"):
            build_snapshot(
                self.evaluation_contract,
                self.snapshot_contract,
                mutated,
            )

    def test_locator_drift_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.observation)
        mutated["sourceObservations"][0]["locator"] = "https://example.invalid/"
        with self.assertRaisesRegex(SourceSnapshotError, "locator drifted"):
            build_snapshot(
                self.evaluation_contract,
                self.snapshot_contract,
                mutated,
            )

    def test_unadmitted_refresh_trigger_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.observation)
        mutated["refreshTrigger"] = "browse everything continuously"
        with self.assertRaisesRegex(SourceSnapshotError, "refresh trigger"):
            build_snapshot(
                self.evaluation_contract,
                self.snapshot_contract,
                mutated,
            )

    def test_unretained_network_receipt_cannot_be_claimed(self) -> None:
        mutated = copy.deepcopy(self.observation)
        mutated["networkReceiptRetained"] = True
        with self.assertRaisesRegex(SourceSnapshotError, "capture boundary"):
            build_snapshot(
                self.evaluation_contract,
                self.snapshot_contract,
                mutated,
            )

    def test_iso_content_use_escalation_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.observation)
        iso = next(
            item
            for item in mutated["sourceObservations"]
            if item["id"] == "iso-12207-2026"
        )
        iso["evidenceUsability"] = "bounded-public-summary"
        iso["claimSupportStatus"] = "bounded-summary-only"
        with self.assertRaisesRegex(SourceSnapshotError, "Restricted ISO"):
            build_snapshot(
                self.evaluation_contract,
                self.snapshot_contract,
                mutated,
            )

    def test_mutable_unpinned_source_cannot_gain_normative_force(self) -> None:
        mutated = copy.deepcopy(self.observation)
        samm = next(
            item
            for item in mutated["sourceObservations"]
            if item["id"] == "owasp-samm-v2"
        )
        samm["claimSupportStatus"] = "versioned-public-guidance"
        with self.assertRaisesRegex(SourceSnapshotError, "normative force"):
            build_snapshot(
                self.evaluation_contract,
                self.snapshot_contract,
                mutated,
            )

    def test_archived_source_requires_digest(self) -> None:
        mutated = copy.deepcopy(self.observation)
        source = next(
            item
            for item in mutated["sourceObservations"]
            if item["id"] == "slsa-1.2"
        )
        source["contentArchiveAvailable"] = True
        with self.assertRaisesRegex(SourceSnapshotError, "lacks a digest"):
            build_snapshot(
                self.evaluation_contract,
                self.snapshot_contract,
                mutated,
            )

    def test_manifest_digest_drift_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.snapshot)
        mutated["manifestSha256"] = "0" * 64
        with self.assertRaisesRegex(SourceSnapshotError, "offline rebuild"):
            validate_snapshot(mutated)


if __name__ == "__main__":
    unittest.main()
