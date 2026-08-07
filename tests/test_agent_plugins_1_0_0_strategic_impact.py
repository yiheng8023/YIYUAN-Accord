from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.validate_agent_plugins_1_0_0_strategic_impact import (
    ACCEPTANCE_PATH,
    EXPECTED_AFFECTED_LAYERS,
    EXPECTED_CLIENTS,
    EXPECTED_OBJECTS,
    EXPECTED_RETAINED_AUTHORITY,
    RECORD_PATH,
    SITE_REVISION,
    SPEC_REVISION,
    validate_record,
    validate_repository_record,
)


ROOT = Path(__file__).resolve().parent.parent


def load_record() -> dict:
    return json.loads((ROOT / RECORD_PATH).read_text(encoding="utf-8"))


def load_acceptance() -> dict:
    return json.loads((ROOT / ACCEPTANCE_PATH).read_text(encoding="utf-8"))


class AgentPluginsStrategicImpactTests(unittest.TestCase):
    def test_repository_record_is_valid(self) -> None:
        self.assertEqual(
            "primary-source-verified-strategic-rebaseline-no-runtime-adoption",
            validate_repository_record(ROOT)["status"],
        )

    def test_exact_sources_and_status_conflict_are_frozen(self) -> None:
        snapshot = load_record()["sourceSnapshot"]
        specification = snapshot["specificationRepository"]
        site = snapshot["documentationRepository"]
        objects = {
            item["path"]: (item["oid"], item["size"])
            for item in specification["selectedGitObjects"]
        }
        self.assertEqual(SPEC_REVISION, specification["revision"])
        self.assertEqual(SITE_REVISION, site["revision"])
        self.assertEqual(EXPECTED_OBJECTS, objects)
        self.assertEqual("Published", specification["repositoryStatusLabel"])
        self.assertEqual("Working Draft", site["deployedSpecificationStatusLabel"])
        self.assertTrue(site["statusConflictWithSpecificationRepository"])

    def test_client_matrix_excludes_unverified_news_brands(self) -> None:
        clients = load_record()["sourceSnapshot"]["officialCompatibleClients"]
        actual = {item["name"]: tuple(item["mcpTransports"]) for item in clients}
        self.assertEqual(EXPECTED_CLIENTS, actual)
        for unsupported in ("Claude Code", "Warp", "Cloudflare", "Adobe", "DeepSeek"):
            self.assertNotIn(unsupported, actual)

    def test_packaging_impact_does_not_replace_harness_authority(self) -> None:
        strategy = load_record()["strategicDecision"]
        self.assertEqual(EXPECTED_AFFECTED_LAYERS, set(strategy["affectedHarnessLayers"]))
        self.assertEqual(EXPECTED_RETAINED_AUTHORITY, set(strategy["retainedHarnessAuthority"]))
        self.assertFalse(strategy["directHarnessReplacement"])
        self.assertFalse(strategy["runtimeAdoptionAuthorized"])

    def test_spec_revision_mutation_fails_closed(self) -> None:
        record = load_record()
        record["sourceSnapshot"]["specificationRepository"]["revision"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "specification identity"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_status_conflict_erasure_fails_closed(self) -> None:
        record = load_record()
        record["sourceSnapshot"]["documentationRepository"][
            "statusConflictWithSpecificationRepository"
        ] = False
        with self.assertRaisesRegex(RuntimeError, "publication-status conflict"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_unsupported_client_promotion_fails_closed(self) -> None:
        record = load_record()
        record["sourceSnapshot"]["officialCompatibleClients"].append(
            {"name": "Warp", "skills": True, "mcpTransports": ["stdio"]}
        )
        with self.assertRaisesRegex(RuntimeError, "client matrix"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_direct_replacement_promotion_fails_closed(self) -> None:
        record = load_record()
        record["strategicDecision"]["directHarnessReplacement"] = True
        with self.assertRaisesRegex(RuntimeError, "strategic decision"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_install_authority_promotion_fails_closed(self) -> None:
        record = load_record()
        record["authorityBoundary"]["installAuthorized"] = True
        with self.assertRaisesRegex(RuntimeError, "authority boundary"):
            validate_record(record, acceptance=load_acceptance(), root=ROOT)

    def test_acceptance_promotion_fails_closed(self) -> None:
        record = load_record()
        acceptance = copy.deepcopy(load_acceptance())
        acceptance["acceptanceCriteria"][0]["assessment"] = "partial"
        with self.assertRaisesRegex(RuntimeError, "acceptance non-promotion"):
            validate_record(record, acceptance=acceptance, root=ROOT)


if __name__ == "__main__":
    unittest.main()
