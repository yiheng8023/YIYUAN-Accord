from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_handoff_loader_cli_capability_probe import (
    EVIDENCE_PATH,
    ROOT,
    validate_probe,
)


class HandoffLoaderCliCapabilityProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_probe_passes(self) -> None:
        validate_probe(deepcopy(self.document), root=ROOT)

    def test_rejects_artifact_content_drift(self) -> None:
        document = deepcopy(self.document)
        document["pairedBehaviorProbe"]["explicitCueArm"]["contentLines"][0] = (
            "# Changed"
        )
        with self.assertRaisesRegex(RuntimeError, "artifact digest"):
            validate_probe(document, root=ROOT)

    def test_rejects_loader_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["exactLoaderInvocationProved"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_probe(document, root=ROOT)

    def test_rejects_visibility_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["comparison"]["skillWasKnownToBeModelVisible"] = True
        with self.assertRaisesRegex(RuntimeError, "comparison boundary"):
            validate_probe(document, root=ROOT)

    def test_rejects_cleanup_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["cleanup"]["temporaryPositiveDirectoryRemoved"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup evidence"):
            validate_probe(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
