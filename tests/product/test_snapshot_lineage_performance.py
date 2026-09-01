from collections import Counter
from pathlib import Path
import unittest
from unittest.mock import patch

import yiyuan_accord.control as product_control


ROOT = Path(__file__).resolve().parents[2]
HISTORICAL_REVIEW_CUT = "c5a06688feee7e93edc58a309679594bcc32bed6"


class SnapshotLineagePerformanceTests(unittest.TestCase):
    def test_revision_tree_cache_has_an_aggregate_memory_bound(self):
        listing = (
            b"100644 blob " + b"1" * 40 + b"\tproduct/program.json\0"
        )
        cache = product_control._SnapshotBlobCache()
        with patch(
            "yiyuan_accord.control._bounded_git_bytes",
            return_value=listing,
        ), patch.object(
            product_control,
            "_SNAPSHOT_V1_TREE_CACHE_BYTES",
            len(listing) - 1,
            create=True,
        ):
            with self.assertRaisesRegex(
                ValueError, "snapshot tree cache aggregate bound is invalid",
            ):
                cache.read(
                    ROOT, "product/program.json", HISTORICAL_REVIEW_CUT,
                )

    def test_one_revision_carry_reuses_bounded_snapshot_blob_reads(self):
        documents = product_control._snapshot_v1_documents(
            ROOT, HISTORICAL_REVIEW_CUT,
        )
        expected = product_control._snapshot_v1_binding_state(
            ROOT, documents[1], documents[2], documents[3], documents[0],
            documents[4], HISTORICAL_REVIEW_CUT,
        )
        calls = []
        bounded_git = product_control._bounded_git_bytes

        def capture(root, arguments, limit=262_144, input_bytes=None):
            calls.append(tuple(arguments))
            return bounded_git(root, arguments, limit, input_bytes)

        with patch(
            "yiyuan_accord.control._bounded_git_bytes", side_effect=capture,
        ):
            frozen, contract_valid = product_control._snapshot_v1_run_status(
                ROOT, expected, (HISTORICAL_REVIEW_CUT,), {},
            )

        self.assertTrue(frozen)
        self.assertTrue(contract_valid)
        blob_reads = [
            call for call in calls
            if call and call[0] in {"show", "cat-file"}
            and not (call[0] == "cat-file" and call[1:2] == ("--batch",))
        ]
        identities = Counter(call[-1] for call in blob_reads)
        self.assertEqual(
            [identity for identity, count in identities.items() if count > 1],
            [],
            "one carry validation must not reread the same historical blob",
        )
        snapshot_git_reads = [
            call for call in calls
            if call and call[0] in {"ls-tree", "show", "cat-file"}
        ]
        self.assertLessEqual(
            len(snapshot_git_reads), 35,
            "one historical revision must fit the bounded snapshot Git-read budget",
        )


if __name__ == "__main__":
    unittest.main()
