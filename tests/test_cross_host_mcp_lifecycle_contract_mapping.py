from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from scripts.validate_cross_host_mcp_lifecycle_contract_mapping import (
    MAPPING_PATH,
    SOURCE_SPECS,
    validate_mapping,
)


ROOT = Path(__file__).resolve().parent.parent


class CrossHostMcpLifecycleContractMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = json.loads(
            (ROOT / MAPPING_PATH).read_text(encoding="utf-8")
        )

    def test_current_mapping_passes_without_generalized_runtime_claim(self) -> None:
        validate_mapping(copy.deepcopy(self.document), root=ROOT)
        self.assertEqual(
            "cross-host-contract-mapped-current-codex-bounded-native-win-no-generalized-runtime-claim",
            self.document["status"],
        )
        self.assertFalse(
            self.document["decision"]["generalizedRuntimeCapabilityProved"]
        )
        self.assertFalse(
            self.document["decision"]["selfAuthoredControllerEligible"]
        )
        self.assertTrue(
            self.document["decision"]["materiallyDifferentMechanismsMapped"]
        )
        self.assertTrue(
            self.document["decision"][
                "boundedCurrentCodexConfigDisablePlusReloadReleaseProved"
            ]
        )
        self.assertNotIn(
            "boundedCurrentCodexReloadReleaseProved",
            self.document["decision"],
        )
        self.assertTrue(all(value is False for value in self.document["claimBoundary"].values()))
        for key in (
            "generalizedRuntimeCapabilityProved",
            "crossHostParityProved",
            "sameSessionDynamicLifecycleProved",
            "stableResourceBenefitProved",
            "residualSelfAuthoredGapProved",
            "selfAuthoredControllerEligible",
        ):
            with self.subTest(decision=key):
                self.assertFalse(self.document["decision"][key])

    def test_portable_adapter_and_host_implementation_layers_stay_distinct(self) -> None:
        layers = self.document["architectureLayers"]
        self.assertEqual(
            [
                "portable-decision-contract",
                "host-neutral-adapter-contract",
                "host-specific-implementation-and-evidence",
            ],
            [item["id"] for item in layers],
        )
        neutral = layers[1]
        self.assertFalse(neutral["isUniversalRuntimeImplementation"])
        self.assertEqual(
            "host-native-enforcement-and-lifecycle-remain-authoritative",
            neutral["authorityBoundary"],
        )
        host_layer = layers[2]
        self.assertNotIn("currentHostAdapters", host_layer)
        self.assertEqual(
            ["kimi-code-synthetic-mechanism", "codex-cli-app-server"],
            host_layer["mappedHostMechanismFamilies"],
        )

    def test_kimi_topology_is_not_collapsed_into_three_independent_prototypes(self) -> None:
        kimi = self.document["hostMappings"][0]
        self.assertEqual(
            {
                "executablePrototypes": [
                    "hooks/context-usage.mjs",
                    "hooks/mcp-gate.mjs",
                ],
                "sharedInjectionInfrastructure": "hooks/session-start.mjs",
                "ruleTextGroups": [
                    "AGENTS.md#上下文交接协议",
                    "AGENTS.md#Git纪律",
                ],
                "lane2ExecutablePrototype": None,
            },
            kimi["hostMechanismTopology"],
        )

    def test_current_codex_win_is_version_and_operation_bounded(self) -> None:
        codex = self.document["hostMappings"][1]
        self.assertEqual(
            "codex-cli-app-server-0.146.0-windows",
            codex["hostId"],
        )
        self.assertEqual(
            "three-of-three-exact-baseline-release-after-config-disable-and-reload",
            codex["contractProjection"]["runtime-released"],
        )
        self.assertEqual(
            "current-for-0.146.0-reload-release-only-historical-for-startup-idle-and-unsubscribe",
            codex["freshness"],
        )

    def test_source_binding_drift_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["sourceBindings"][0]["fileSha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "projection drift"):
            validate_mapping(mutated, root=ROOT)

    def test_mechanism_collapse_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.document)
        mutated["hostMappings"][1]["mechanismClass"] = mutated[
            "hostMappings"
        ][0]["mechanismClass"]
        with self.assertRaisesRegex(RuntimeError, "projection drift"):
            validate_mapping(mutated, root=ROOT)

    def test_claim_or_self_authored_promotion_fails_closed(self) -> None:
        promoted = copy.deepcopy(self.document)
        promoted["claimBoundary"]["crossHostParityProved"] = True
        with self.assertRaisesRegex(RuntimeError, "projection drift"):
            validate_mapping(promoted, root=ROOT)

        self_authored = copy.deepcopy(self.document)
        self_authored["decision"]["selfAuthoredControllerEligible"] = True
        with self.assertRaisesRegex(RuntimeError, "projection drift"):
            validate_mapping(self_authored, root=ROOT)

    def test_historical_and_synthetic_evidence_cannot_be_promoted(self) -> None:
        promoted = copy.deepcopy(self.document)
        kimi, codex = promoted["hostMappings"]
        kimi["evidenceState"] = "live-host-behavior-proved"
        codex["freshness"] = "current-host-proof"
        with self.assertRaisesRegex(RuntimeError, "projection drift"):
            validate_mapping(promoted, root=ROOT)

    def test_source_semantic_drift_fails_before_projection_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_root:
            isolated_root = Path(temporary_root)
            for relative, _ in SOURCE_SPECS:
                target = isolated_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)

            startup_path = isolated_root / SOURCE_SPECS[3][0]
            startup = json.loads(startup_path.read_text(encoding="utf-8"))
            startup["supportedConclusions"][
                "startupProfileDirectCallBoundaryObservedForThisHostAndSentinel"
            ] = False
            startup_path.write_text(
                json.dumps(startup, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "Codex startup evidence drifted",
            ):
                validate_mapping(copy.deepcopy(self.document), root=isolated_root)

    def test_release_request_call_gate_and_process_release_stay_distinct(self) -> None:
        states = self.document["portableContract"]["lifecycleStates"]
        self.assertEqual(
            [
                "selected",
                "activation-authorized",
                "call-admitted",
                "schema-exposed",
                "runtime-loaded",
                "release-requested",
                "runtime-released",
                "recovered",
            ],
            states,
        )
        self.assertEqual(
            "call-admission-only-no-schema-or-process-release",
            self.document["hostMappings"][0]["effectiveBoundary"],
        )
        self.assertEqual(
            "bounded-current-config-disable-reload-release-plus-version-bound-startup-new-thread-and-idle-fallback",
            self.document["hostMappings"][1]["effectiveBoundary"],
        )
        self.assertEqual(
            "not-observed-schema-list-not-called",
            self.document["hostMappings"][1]["contractProjection"][
                "schema-exposed"
            ],
        )
        self.assertEqual(
            "current-native-disable-reload-only-for-tested-boundary-otherwise-version-bound-startup-new-thread-or-idle-path",
            self.document["hostMappings"][1]["degradedFallback"],
        )


if __name__ == "__main__":
    unittest.main()
