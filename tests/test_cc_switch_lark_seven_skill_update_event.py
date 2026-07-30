from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_cc_switch_lark_seven_skill_update_event import (
    EVIDENCE_PATH,
    ROOT,
    validate_event,
)


class CcSwitchLarkSevenSkillUpdateEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / EVIDENCE_PATH).read_text(encoding="utf-8")
        )

    def test_current_event_passes(self) -> None:
        validate_event(deepcopy(self.document), root=ROOT)

    def test_rejects_missing_skill(self) -> None:
        document = deepcopy(self.document)
        document["skills"].pop()
        with self.assertRaisesRegex(RuntimeError, "Skill set drifted"):
            validate_event(document, root=ROOT)

    def test_rejects_whole_tree_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["skills"][0]["wholeTreeEqualityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "binding drifted"):
            validate_event(document, root=ROOT)

    def test_rejects_stale_row_repair_overclaim(self) -> None:
        document = deepcopy(self.document)
        document["decision"]["broaderStaleRowRepairComplete"] = True
        with self.assertRaisesRegex(RuntimeError, "decision boundary"):
            validate_event(document, root=ROOT)

    def test_rejects_source_commit_drift(self) -> None:
        document = deepcopy(self.document)
        document["upstreamObservation"]["headCommit"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "upstream evidence"):
            validate_event(document, root=ROOT)

    def test_rejects_cleanup_authorization(self) -> None:
        document = deepcopy(self.document)
        document["claimBoundary"]["cleanupAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "claim boundary"):
            validate_event(document, root=ROOT)


if __name__ == "__main__":
    unittest.main()
