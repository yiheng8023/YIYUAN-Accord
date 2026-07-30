from __future__ import annotations

import copy
import json
import unittest

from scripts.evaluate_human_ai_collaboration_unknown_quadrant_packet_overlay import (
    EXPECTED_CLASSES,
    FIXTURE_PATH,
    ROOT,
    evaluate_document,
    evaluate_overlay,
)


class UnknownQuadrantPacketOverlayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.bindings = {
            item["path"]: item
            for item in self.document["sourceBindings"]
        }

    def test_base_overlays_and_faults_match(self) -> None:
        result = evaluate_document(self.document)
        self.assertEqual(5, len(result["baseResults"]))
        self.assertEqual(
            {"compatible-zero-model-private-overlay"},
            {item["actual"] for item in result["baseResults"]},
        )
        self.assertEqual(5, len(result["faultResults"]))
        self.assertEqual(
            [],
            [
                item
                for item in result["faultResults"]
                if item["actual"] != item["expected"]
            ],
        )
        self.assertEqual(EXPECTED_CLASSES, set(result["unknownClasses"]))

    def test_private_oracle_exposure_fails(self) -> None:
        overlay = copy.deepcopy(self.document["overlays"][0])
        overlay["privateOracleExposedToAgent"] = True
        self.assertEqual(
            "fail-private-oracle-exposure",
            evaluate_overlay(
                overlay,
                binding=self.bindings[overlay["sourcePath"]],
                root=ROOT,
            ),
        )

    def test_source_packet_mutation_fails(self) -> None:
        overlay = copy.deepcopy(self.document["overlays"][0])
        overlay["sourcePacketModified"] = True
        overlay["publicPacketUnchanged"] = False
        self.assertEqual(
            "fail-source-packet-mutation",
            evaluate_overlay(
                overlay,
                binding=self.bindings[overlay["sourcePath"]],
                root=ROOT,
            ),
        )

    def test_live_authority_expansion_fails(self) -> None:
        overlay = copy.deepcopy(self.document["overlays"][0])
        overlay["modelDispatchAuthorized"] = True
        self.assertEqual(
            "fail-live-authority-expansion",
            evaluate_overlay(
                overlay,
                binding=self.bindings[overlay["sourcePath"]],
                root=ROOT,
            ),
        )


if __name__ == "__main__":
    unittest.main()
