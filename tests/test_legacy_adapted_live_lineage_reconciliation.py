import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "registry/legacy-adapted-live-lineage-reconciliation-2026-08-02.json"


class LegacyAdaptedLiveLineageReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_nineteen_split_into_thirteen_exact_derivatives_and_six_upstreams(self) -> None:
        exact = self.evidence["liveByteExactDeprecatedDerivatives"]
        upstream = self.evidence["sameNameIndependentUpstreams"]
        self.assertEqual(len(exact), 13)
        self.assertEqual(len(upstream), 6)
        self.assertEqual(
            {item["name"] for item in exact} | {item["name"] for item in upstream},
            set(self.evidence["deprecatedReleaseSkillNames"]),
        )
        self.assertFalse({item["name"] for item in exact} & {item["name"] for item in upstream})

    def test_exact_derivatives_are_local_and_projection_links_point_to_cc(self) -> None:
        for item in self.evidence["liveByteExactDeprecatedDerivatives"]:
            with self.subTest(name=item["name"]):
                self.assertEqual(item["managerSource"], "local-or-unattributed")
                self.assertTrue(item["legacyTreeExact"])
                self.assertIn(item["agentsProjectionKind"], {"symlink", "junction"})
                self.assertIn(item["codexProjectionKind"], {"symlink", "junction"})
                self.assertEqual(len(item["treeManifestSha256"]), 64)

    def test_upstream_same_names_are_not_removal_candidates(self) -> None:
        for item in self.evidence["sameNameIndependentUpstreams"]:
            with self.subTest(name=item["name"]):
                self.assertEqual(item["managerSource"], "mattpocock/skills")
                self.assertFalse(item["legacyTreeExact"])
                self.assertEqual(item["disposition"], "retain-as-independent-upstream-object")

    def test_router_dependency_blocker_was_repaired_without_mutating_cc(self) -> None:
        repair = self.evidence["dependencyRepair"]
        self.assertEqual(repair["consumerCommit"], "5b49c53b4dc220b6b10f5caf29d3aef8a7841327")
        self.assertFalse(repair["deprecatedDiagnoseIdentityReferencedByLiveConsumerProjection"])
        self.assertEqual(self.evidence["executionCounters"]["ccSwitchMutations"], 0)
        self.assertFalse(self.evidence["authorityBoundary"]["removalExecuted"])


if __name__ == "__main__":
    unittest.main()
