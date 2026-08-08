#!/usr/bin/env python3
"""Build deterministic, non-installable plugin projection previews."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


AGENT_PLUGINS_SCHEMA = (
    "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
)
ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path("registry/offline-plugin-projection-poc-2026-08-08.json")
DOCUMENTATION_PATH = Path(
    "docs/strategy/OFFLINE-PLUGIN-PROJECTION-POC-2026-08-08.md"
)


class ProjectionRejected(ValueError):
    """Structured fail-closed result for an invalid projection request."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        component_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.component_id = component_id

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": "rejected",
            "code": self.code,
        }
        if self.component_id is not None:
            result["componentId"] = self.component_id
        result["message"] = str(self)
        return result


def build_projection_preview(source: dict[str, Any]) -> dict[str, Any]:
    """Project one canonical metadata object without writing plugin files."""
    if source.get("portableCoreDependsOnCcSwitch"):
        raise ProjectionRejected(
            "portable-core-manager-dependency",
            "The portable Harness core cannot depend on CC Switch.",
        )
    if source.get("releaseEligible"):
        raise ProjectionRejected(
            "release-eligibility-promotion",
            "An offline projection preview cannot declare plugin release eligibility.",
        )

    authorities_by_component: dict[str, str] = {}
    for component in source["components"]:
        if component["kind"] not in {"skill", "mcp-server"}:
            raise ProjectionRejected(
                "unsupported-component-kind",
                "The offline projection PoC supports only skill and mcp-server components.",
                component_id=component["id"],
            )
        existing_authority = authorities_by_component.get(component["id"])
        if (
            existing_authority is not None
            and existing_authority != component["lifecycleAuthority"]
        ):
            raise ProjectionRejected(
                "dual-lifecycle-authority",
                "One component cannot be projected with multiple lifecycle authorities.",
                component_id=component["id"],
            )
        authorities_by_component[component["id"]] = component[
            "lifecycleAuthority"
        ]
        if component["sourceClass"] == "official-runtime-owned":
            raise ProjectionRejected(
                "runtime-owned-component-bundling",
                "Official runtime-owned components must remain owned by their runtime.",
                component_id=component["id"],
            )
        if (
            component["sourceClass"] == "third-party-exact-upstream"
            and component["lifecycleAuthority"] == "cc-switch"
        ):
            raise ProjectionRejected(
                "cc-managed-third-party-bundling",
                "CC Switch-managed third-party payloads cannot enter a Harness plugin projection.",
                component_id=component["id"],
            )

    shared_manifest = {
        key: deepcopy(source[key])
        for key in (
            "name",
            "version",
            "description",
            "author",
            "repository",
            "license",
        )
    }
    components = source["components"]
    has_skills = any(item["kind"] == "skill" for item in components)
    has_mcp = any(item["kind"] == "mcp-server" for item in components)

    portable_manifest = {
        "$schema": AGENT_PLUGINS_SCHEMA,
        **deepcopy(shared_manifest),
    }
    openai_manifest = deepcopy(shared_manifest)
    portable_locations: dict[str, str] = {}
    if has_skills:
        portable_locations["skills"] = "skills/"
        openai_manifest["skills"] = "./skills/"
    if has_mcp:
        portable_locations["mcp"] = "mcp.json"
        openai_manifest["mcpServers"] = "./.mcp.json"

    return {
        "schema": 1,
        "status": "preview-only-not-installable",
        "canonicalSourceId": source["id"],
        "portableAgentPlugins": {
            "manifestPath": "plugin.json",
            "manifest": portable_manifest,
            "fixedComponentLocations": portable_locations,
        },
        "openAi": {
            "manifestPath": ".codex-plugin/plugin.json",
            "manifest": openai_manifest,
        },
        "ownership": [
            {
                "componentId": item["id"],
                "sourceClass": item["sourceClass"],
                "lifecycleAuthority": item["lifecycleAuthority"],
                "packagedByPreview": True,
                "runtimeAuthorityAssigned": False,
            }
            for item in components
        ],
        "claimBoundary": {
            "createsPluginFiles": False,
            "provesInstallability": False,
            "provesHostConformance": False,
            "provesRuntimeBehavior": False,
            "provesReleaseReadiness": False,
        },
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_poc_record(
    record: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id") == "offline-plugin-projection-poc-2026-08-08"
        and record.get("asOf") == "2026-08-08"
        and record.get("status")
        == "offline-preview-verified-release-not-eligible",
        "Offline plugin projection PoC identity drifted",
    )
    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and (root / DOCUMENTATION_PATH).is_file(),
        "Offline plugin projection PoC documentation binding drifted",
    )
    contract = record.get("taskContract", {})
    _require(
        all(
            _nonempty(contract.get(key))
            for key in (
                "goal",
                "mode",
                "authorityBoundary",
                "verificationSurface",
            )
        ),
        "Offline plugin projection PoC task contract drifted",
    )

    mapping = record.get("fieldMapping", {})
    _require(
        mapping.get("portableAgentPlugins")
        == {
            "manifest": "plugin.json",
            "skills": "skills/",
            "mcp": "mcp.json",
        }
        and mapping.get("openAi")
        == {
            "manifest": ".codex-plugin/plugin.json",
            "skills": "./skills/",
            "mcpServers": "./.mcp.json",
        },
        "Offline plugin projection PoC field mapping drifted",
    )

    fixture = record.get("canonicalFixture", {})
    expected_preview = record.get("expectedPreview")
    _require(
        build_projection_preview(fixture) == expected_preview,
        "Offline plugin projection PoC preview replay drifted",
    )

    failures = record.get("failureCases", [])
    expected_codes = {
        "cc-managed-third-party-bundling",
        "dual-lifecycle-authority",
        "portable-core-manager-dependency",
        "release-eligibility-promotion",
        "unsupported-component-kind",
        "runtime-owned-component-bundling",
    }
    _require(
        {item.get("expectedRejection", {}).get("code") for item in failures}
        == expected_codes,
        "Offline plugin projection PoC failure inventory drifted",
    )
    for failure in failures:
        try:
            build_projection_preview(failure["source"])
        except ProjectionRejected as exc:
            actual = exc.as_dict()
        else:
            raise RuntimeError(
                "Offline plugin projection PoC failure did not reject"
            )
        _require(
            actual == failure.get("expectedRejection"),
            "Offline plugin projection PoC rejection replay drifted",
        )

    ownership = record.get("ownershipPolicy", {})
    _require(
        ownership.get("oneLifecycleAuthorityPerComponent") is True
        and ownership.get("ccManagedThirdPartyPayloadMayBeBundled") is False
        and ownership.get("portableCoreDependsOnCcSwitch") is False
        and ownership.get("runtimeAuthorityAssignedByPreview") is False,
        "Offline plugin projection PoC ownership policy drifted",
    )
    acceptance = record.get("acceptanceBoundary", {})
    _require(
        acceptance.get("canonicalInventoryBefore")
        == {"verified": 46, "partial": 15, "planned": 0}
        and acceptance.get("canonicalInventoryAfter")
        == {"verified": 46, "partial": 15, "planned": 0}
        and acceptance.get("criteriaAdvanced") == [],
        "Offline plugin projection PoC acceptance boundary drifted",
    )
    authority = record.get("authorityBoundary", {})
    expected_authority_keys = {
        "pluginCreationAuthorized",
        "installationAuthorized",
        "enablementAuthorized",
        "hostExecutionAuthorized",
        "accountConnectionAuthorized",
        "modelDispatchAuthorized",
        "ccSwitchMutationAuthorized",
        "consumerMutationAuthorized",
        "thirdPartyVendoringAuthorized",
        "publicationAuthorized",
        "releaseAuthorized",
        "universalManagerImplementationAuthorized",
    }
    _require(
        set(authority) == expected_authority_keys
        and all(value is False for value in authority.values()),
        "Offline plugin projection PoC authority boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    expected_claim_keys = {
        "provesPluginExists",
        "provesPluginInstallability",
        "provesHostConformance",
        "provesInvocationOrInstructionDelivery",
        "provesRuntimeBehavior",
        "provesTaskValue",
        "provesCrossHostPortability",
        "provesProductionReadiness",
        "provesReleaseReadiness",
        "provesCcSwitchReplacementNeed",
    }
    _require(
        set(claims) == expected_claim_keys
        and all(value is False for value in claims.values()),
        "Offline plugin projection PoC claim boundary drifted",
    )


def validate_repository_record(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    validate_poc_record(record, root=root)
    return record


def main() -> int:
    validate_repository_record(ROOT)
    print("Offline plugin projection PoC validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
