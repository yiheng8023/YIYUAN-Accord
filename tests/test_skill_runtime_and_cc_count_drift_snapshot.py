from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.validate_skill_runtime_and_cc_count_drift_snapshot import (
    EVIDENCE_PATH,
    ROOT,
    validate_snapshot,
)


class SkillRuntimeAndCcCountDriftSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_snapshot_passes(self) -> None:
        validate_snapshot(deepcopy(self.document), root=ROOT)

    def test_rejects_ui_count_as_physical_count(self) -> None:
        document = deepcopy(self.document)
        document["ccSwitchObservation"]["countSemantics"][
            "uiOrEnabledRowCountEqualsPhysicalUniqueSkillCount"
        ] = True
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_stale_row_resolution_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["ccSwitchStaleRowGapResolved"] = True
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_runtime_payload_copy_decision(self) -> None:
        document = deepcopy(self.document)
        document["decision"][
            "copySuperpowersRuntimePayloadsIntoCcForCodex"
        ] = True
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_global_bootstrap_default(self) -> None:
        document = deepcopy(self.document)
        document["superpowers620GovernanceReview"][
            "globalDefaultRejections"
        ] = []
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_behavioral_value_claim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"][
            "superpowers620WeakAgentValueProved"
        ] = True
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_fake_digest_key_with_valid_sha(self) -> None:
        document = deepcopy(self.document)
        digests = document["externalSourceRevalidation"]["superpowers"][
            "selectedSkillDigests"
        ]
        digest = digests.pop("writing-skills")
        digests["fake-skill"] = digest
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_package_arithmetic_drift(self) -> None:
        document = deepcopy(self.document)
        document["externalSourceRevalidation"]["superpowers"][
            "currentRuntimePackageFileCount"
        ] = 73
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_selective_candidate_promotion(self) -> None:
        document = deepcopy(self.document)
        document["superpowers620GovernanceReview"][
            "selectiveReuseCandidates"
        ][0]["disposition"] = "adopt-global-default"
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_behavioral_baseline_promotion(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["superpowers620IsBehavioralBaseline"] = True
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_telemetry_without_user_acceptance(self) -> None:
        document = deepcopy(self.document)
        document["superpowers620GovernanceReview"][
            "conditionalExternalEffect"
        ]["requiresOfferAndUserAcceptance"] = False
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_null_host_with_runtime_error(self) -> None:
        document = deepcopy(self.document)
        document["host"] = None
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_missing_governance_list_with_runtime_error(self) -> None:
        document = deepcopy(self.document)
        document["superpowers620GovernanceReview"].pop(
            "selectiveReuseCandidates"
        )
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_missing_claim_boundary_key(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"].pop("safeCleanupOrMigrationProved")
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_enabled_repository_identity_drift(self) -> None:
        document = deepcopy(self.document)
        document["ccSwitchObservation"]["database"]["enabledRepositories"][
            0
        ] = "example/replacement@main"
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_source_repository_identity_drift(self) -> None:
        document = deepcopy(self.document)
        document["externalSourceRevalidation"]["superpowers"][
            "repository"
        ] = "example/superpowers"
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)

    def test_rejects_unsafe_next_action(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["nextBoundedAction"] = (
            "Migrate and delete the old sources now."
        )
        with self.assertRaises(RuntimeError):
            validate_snapshot(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
