from pathlib import Path
import unittest

from scripts.project_offline_plugin_projection import (
    ProjectionRejected,
    RECORD_PATH,
    build_projection_preview,
    validate_repository_record,
)


ROOT = Path(__file__).resolve().parent.parent


class OfflinePluginProjectionPocTests(unittest.TestCase):
    def test_repository_record_replays_the_preview_and_failures(self) -> None:
        record = validate_repository_record(ROOT)

        self.assertEqual(
            "offline-preview-verified-release-not-eligible",
            record["status"],
        )
        self.assertTrue((ROOT / RECORD_PATH).is_file())

    def test_repository_owned_fixture_maps_to_two_non_release_previews(self) -> None:
        source = {
            "schema": 1,
            "id": "synthetic-harness-plugin-fixture",
            "name": "harness-projection-fixture",
            "version": "0.0.0-poc",
            "description": "Synthetic metadata for offline projection testing.",
            "author": {"name": "Agent Autonomy Harness"},
            "repository": "https://github.com/yiheng8023/agent-autonomy-harness",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": False,
            "releaseEligible": False,
            "components": [
                {
                    "id": "fixture-skill",
                    "kind": "skill",
                    "sourceClass": "repository-owned-synthetic-fixture",
                    "lifecycleAuthority": "fixture-only-no-runtime",
                    "fixtureOnly": True,
                }
            ],
        }

        self.assertEqual(
            build_projection_preview(source),
            {
                "schema": 1,
                "status": "preview-only-not-installable",
                "canonicalSourceId": "synthetic-harness-plugin-fixture",
                "portableAgentPlugins": {
                    "manifestPath": "plugin.json",
                    "manifest": {
                        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                        "name": "harness-projection-fixture",
                        "version": "0.0.0-poc",
                        "description": "Synthetic metadata for offline projection testing.",
                        "author": {"name": "Agent Autonomy Harness"},
                        "repository": "https://github.com/yiheng8023/agent-autonomy-harness",
                        "license": "MIT",
                    },
                    "fixedComponentLocations": {"skills": "skills/"},
                },
                "openAi": {
                    "manifestPath": ".codex-plugin/plugin.json",
                    "manifest": {
                        "name": "harness-projection-fixture",
                        "version": "0.0.0-poc",
                        "description": "Synthetic metadata for offline projection testing.",
                        "author": {"name": "Agent Autonomy Harness"},
                        "repository": "https://github.com/yiheng8023/agent-autonomy-harness",
                        "license": "MIT",
                        "skills": "./skills/",
                    },
                },
                "ownership": [
                    {
                        "componentId": "fixture-skill",
                        "sourceClass": "repository-owned-synthetic-fixture",
                        "lifecycleAuthority": "fixture-only-no-runtime",
                        "packagedByPreview": True,
                        "runtimeAuthorityAssigned": False,
                    }
                ],
                "claimBoundary": {
                    "createsPluginFiles": False,
                    "provesInstallability": False,
                    "provesHostConformance": False,
                    "provesRuntimeBehavior": False,
                    "provesReleaseReadiness": False,
                },
            },
        )

    def test_cc_switch_managed_third_party_payload_is_rejected(self) -> None:
        source = {
            "schema": 1,
            "id": "forbidden-cc-payload",
            "name": "forbidden-cc-payload",
            "version": "0.0.0-poc",
            "description": "Must fail before projection.",
            "author": {"name": "Fixture"},
            "repository": "https://example.invalid/fixture",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": False,
            "releaseEligible": False,
            "components": [
                {
                    "id": "third-party-skill",
                    "kind": "skill",
                    "sourceClass": "third-party-exact-upstream",
                    "lifecycleAuthority": "cc-switch",
                    "fixtureOnly": False,
                }
            ],
        }

        with self.assertRaises(ProjectionRejected) as raised:
            build_projection_preview(source)

        self.assertEqual(
            raised.exception.as_dict(),
            {
                "status": "rejected",
                "code": "cc-managed-third-party-bundling",
                "componentId": "third-party-skill",
                "message": "CC Switch-managed third-party payloads cannot enter a Harness plugin projection.",
            },
        )

    def test_same_component_cannot_have_two_lifecycle_authorities(self) -> None:
        source = {
            "schema": 1,
            "id": "dual-authority-fixture",
            "name": "dual-authority-fixture",
            "version": "0.0.0-poc",
            "description": "Must fail before projection.",
            "author": {"name": "Fixture"},
            "repository": "https://example.invalid/fixture",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": False,
            "releaseEligible": False,
            "components": [
                {
                    "id": "shared-skill",
                    "kind": "skill",
                    "sourceClass": "repository-owned-synthetic-fixture",
                    "lifecycleAuthority": "fixture-only-no-runtime",
                    "fixtureOnly": True,
                },
                {
                    "id": "shared-skill",
                    "kind": "skill",
                    "sourceClass": "official-runtime-owned",
                    "lifecycleAuthority": "openai-plugin-runtime",
                    "fixtureOnly": False,
                },
            ],
        }

        with self.assertRaises(ProjectionRejected) as raised:
            build_projection_preview(source)

        self.assertEqual(
            raised.exception.as_dict(),
            {
                "status": "rejected",
                "code": "dual-lifecycle-authority",
                "componentId": "shared-skill",
                "message": "One component cannot be projected with multiple lifecycle authorities.",
            },
        )

    def test_portable_core_cannot_depend_on_cc_switch(self) -> None:
        source = {
            "schema": 1,
            "id": "manager-dependent-fixture",
            "name": "manager-dependent-fixture",
            "version": "0.0.0-poc",
            "description": "Must fail before projection.",
            "author": {"name": "Fixture"},
            "repository": "https://example.invalid/fixture",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": True,
            "releaseEligible": False,
            "components": [],
        }

        with self.assertRaises(ProjectionRejected) as raised:
            build_projection_preview(source)

        self.assertEqual(
            raised.exception.as_dict(),
            {
                "status": "rejected",
                "code": "portable-core-manager-dependency",
                "message": "The portable Harness core cannot depend on CC Switch.",
            },
        )

    def test_offline_preview_cannot_declare_release_eligibility(self) -> None:
        source = {
            "schema": 1,
            "id": "release-eligible-fixture",
            "name": "release-eligible-fixture",
            "version": "0.0.0-poc",
            "description": "Must fail before projection.",
            "author": {"name": "Fixture"},
            "repository": "https://example.invalid/fixture",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": False,
            "releaseEligible": True,
            "components": [],
        }

        with self.assertRaises(ProjectionRejected) as raised:
            build_projection_preview(source)

        self.assertEqual(
            raised.exception.as_dict(),
            {
                "status": "rejected",
                "code": "release-eligibility-promotion",
                "message": "An offline projection preview cannot declare plugin release eligibility.",
            },
        )

    def test_mcp_component_maps_to_each_formats_fixed_location(self) -> None:
        source = {
            "schema": 1,
            "id": "synthetic-mcp-fixture",
            "name": "synthetic-mcp-fixture",
            "version": "0.0.0-poc",
            "description": "Synthetic MCP metadata for offline projection testing.",
            "author": {"name": "Agent Autonomy Harness"},
            "repository": "https://github.com/yiheng8023/agent-autonomy-harness",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": False,
            "releaseEligible": False,
            "components": [
                {
                    "id": "fixture-mcp-server",
                    "kind": "mcp-server",
                    "sourceClass": "repository-owned-synthetic-fixture",
                    "lifecycleAuthority": "fixture-only-no-runtime",
                    "fixtureOnly": True,
                }
            ],
        }

        preview = build_projection_preview(source)

        self.assertEqual(
            preview["portableAgentPlugins"]["fixedComponentLocations"],
            {"mcp": "mcp.json"},
        )
        self.assertEqual(
            preview["openAi"]["manifest"]["mcpServers"],
            "./.mcp.json",
        )

    def test_unsupported_component_kind_is_rejected(self) -> None:
        source = {
            "schema": 1,
            "id": "unsupported-component-fixture",
            "name": "unsupported-component-fixture",
            "version": "0.0.0-poc",
            "description": "Must fail before projection.",
            "author": {"name": "Fixture"},
            "repository": "https://example.invalid/fixture",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": False,
            "releaseEligible": False,
            "components": [
                {
                    "id": "fixture-hook",
                    "kind": "hook",
                    "sourceClass": "repository-owned-synthetic-fixture",
                    "lifecycleAuthority": "fixture-only-no-runtime",
                    "fixtureOnly": True,
                }
            ],
        }

        with self.assertRaises(ProjectionRejected) as raised:
            build_projection_preview(source)

        self.assertEqual(
            raised.exception.as_dict(),
            {
                "status": "rejected",
                "code": "unsupported-component-kind",
                "componentId": "fixture-hook",
                "message": "The offline projection PoC supports only skill and mcp-server components.",
            },
        )

    def test_official_runtime_owned_component_is_not_copied(self) -> None:
        source = {
            "schema": 1,
            "id": "runtime-owned-fixture",
            "name": "runtime-owned-fixture",
            "version": "0.0.0-poc",
            "description": "Must fail before projection.",
            "author": {"name": "Fixture"},
            "repository": "https://example.invalid/fixture",
            "license": "MIT",
            "portableCoreDependsOnCcSwitch": False,
            "releaseEligible": False,
            "components": [
                {
                    "id": "runtime-skill",
                    "kind": "skill",
                    "sourceClass": "official-runtime-owned",
                    "lifecycleAuthority": "openai-plugin-runtime",
                    "fixtureOnly": False,
                }
            ],
        }

        with self.assertRaises(ProjectionRejected) as raised:
            build_projection_preview(source)

        self.assertEqual(
            raised.exception.as_dict(),
            {
                "status": "rejected",
                "code": "runtime-owned-component-bundling",
                "componentId": "runtime-skill",
                "message": "Official runtime-owned components must remain owned by their runtime.",
            },
        )


if __name__ == "__main__":
    unittest.main()
