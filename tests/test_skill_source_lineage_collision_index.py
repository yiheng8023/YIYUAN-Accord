from __future__ import annotations

import copy
import unittest

from scripts.build_skill_source_lineage_collision_index import (
    GROUP_IDS,
    SOURCE_PATHS,
    build_index,
    canonical_sha256,
    validate_index,
)


class SkillSourceLineageCollisionIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = build_index()

    def test_index_is_dated_and_non_authorizing(self) -> None:
        document = self.document
        self.assertEqual(list(GROUP_IDS), [
            group["id"]
            for group in document["groups"]
        ])
        self.assertEqual(
            list(SOURCE_PATHS),
            [record["path"] for record in document["sourceRecords"]],
        )
        self.assertEqual(
            ["2026-07-18", "2026-07-19", "2026-07-23"],
            document["summary"]["datedSourceRecordDates"],
        )
        self.assertFalse(document["summary"]["currentRuntimeSnapshot"])
        self.assertFalse(
            document["summary"]["allOccurrencesExhaustivelyIndexed"]
        )
        self.assertEqual([], validate_index(document))

    def test_handoff_keeps_exact_unknown_and_historical_occurrences_distinct(
        self,
    ) -> None:
        group = self.document["groups"][0]
        self.assertEqual(
            [
                "source-backed-upstream-archive-exact",
                "historical-one-file-body",
                "legacy-rewritten-uncompared-occurrence",
            ],
            [
                occurrence["representationClass"]
                for occurrence in group["observations"]
            ],
        )
        self.assertEqual(
            "unknown",
            group["observations"][2]["artifactDigest"],
        )
        self.assertEqual(
            "unknown",
            group["observations"][2]["immutableRevisionOrUnknown"],
        )
        self.assertEqual(
            "9603c1cc8118d08bc1b3bf34cf714f62178dea3b",
            group["observations"][2]["reviewedUpstreamRevision"],
        )

    def test_legacy_matt_and_superpowers_do_not_gain_equality_claims(
        self,
    ) -> None:
        groups = {
            group["id"]: group
            for group in self.document["groups"]
        }
        self.assertEqual(
            0,
            groups["legacy-matt-mapped-mixed-snapshot"][
                "wholeTreeExactMatchesToCurrentUpstream"
            ],
        )
        self.assertEqual(
            "local-digests-pinned-upstream-byte-equality-unproved",
            groups["superpowers-local-plugin-sample"][
                "collisionRelation"
            ],
        )
        self.assertEqual(
            "unknown",
            groups["legacy-matt-mapped-mixed-snapshot"][
                "immutableRevisionOrUnknown"
            ],
        )
        self.assertEqual(
            "unknown",
            groups["superpowers-local-plugin-sample"][
                "immutableRevisionOrUnknown"
            ],
        )
        self.assertEqual(
            "unknown-current",
            groups["superpowers-local-plugin-sample"]["activeState"],
        )
        self.assertTrue(
            groups["superpowers-local-plugin-sample"][
                "comparisonBaseline"
            ]
        )
        self.assertEqual(
            "freeze-unresolved-or-runtime-owned-do-not-copy",
            groups["runtime-plugin-alias-reconciliation-gap"][
                "disposition"
            ],
        )
        self.assertFalse(
            self.document["claimBoundary"][
                "localSuperpowersBytesEqualReleaseProved"
            ]
        )

    def test_selected_cc_samples_keep_content_lineage_separate_from_install_provenance(
        self,
    ) -> None:
        groups = {
            group["id"]: group
            for group in self.document["groups"]
        }
        selected = groups["selected-cc-three-source-reconciliation"]
        observations = {
            item["logicalSkillId"]: item
            for item in selected["observations"]
        }
        self.assertEqual(
            "crlf-normalized-exact-historical-upstream",
            observations["grill-me"]["sourceReconciliation"][
                "relationship"
            ],
        )
        for name in ("grill-with-docs", "review"):
            source = observations[name]["sourceReconciliation"]
            self.assertTrue(source["ccBytesEqualRepositoryPayload"])
            self.assertEqual(
                0,
                source["normalizedLcsLineEvidence"][
                    "historicalUpstreamOnlyLines"
                ],
            )
            self.assertFalse(
                source["exactInstallOrCcSourceRowProvenanceProved"]
            )
        self.assertEqual(
            "content-bytes-only-no-loader-or-cc-source-row-proof",
            selected["projectionState"],
        )
        self.assertFalse(
            self.document["claimBoundary"][
                "selectedCcInstallOrSourceRowProvenanceProved"
            ]
        )

    def test_authority_promotion_and_source_digest_drift_fail_closed(
        self,
    ) -> None:
        promoted = copy.deepcopy(self.document)
        promoted["authorityBoundary"]["migrationAuthorized"] = True
        promoted["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in promoted.items()
                if key != "reportSha256"
            }
        )
        self.assertIn(
            "hard-fail-authorityBoundary-promotion",
            validate_index(promoted),
        )

        drifted = copy.deepcopy(self.document)
        drifted["sourceRecords"][0]["sha256"] = "0" * 64
        drifted["reportSha256"] = canonical_sha256(
            {
                key: value
                for key, value in drifted.items()
                if key != "reportSha256"
            }
        )
        self.assertIn(
            "fail-source-record-digest",
            validate_index(drifted),
        )


if __name__ == "__main__":
    unittest.main()
