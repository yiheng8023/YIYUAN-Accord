#!/usr/bin/env python3
"""Validate the Agent Plugins 1.0.0 source and strategy rebaseline."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RECORD_PATH = Path("registry/agent-plugins-1.0.0-strategic-impact-2026-08-07.json")
DOCUMENTATION_PATH = Path(
    "docs/research/agent-plugins-1.0.0-strategic-impact-2026-08-07.md"
)
ACCEPTANCE_PATH = Path("registry/program-acceptance-map.json")
SPEC_REVISION = "bd383552095128f6effe895b9257cfd580a6d179"
SITE_REVISION = "e139c26382e8dacfde2f61675e413286054e5be6"
EXPECTED_OBJECTS = {
    "README.md": ("23cbb482afd9cd0ad5b30a18a2454c98b7b262bd", 1384),
    "spec/1.0.0.md": ("c95263bd61fc16608390006bc461e964ce21cd12", 42751),
    "schemas/1.0.0/plugin.schema.json": (
        "8fed0e1fe45d0464aee880d3fbab228b71ecfc1e", 1805
    ),
    "schemas/1.0.0/mcp.schema.json": (
        "a9139a4259b932c60b5351c8d9da6a5c60c97646", 3408
    ),
    "GOVERNANCE.md": ("15446ab2fea8bd54acfe47a548eedae0a0d0e754", 6324),
    "MAINTAINERS.md": ("5c138016d2bc039d82eae2cf802b973faa5af681", 419),
    "FUTURE_CONSIDERATIONS.md": (
        "e7589b0ab0cf6e68a672bc3f54a6fbabf2c0fb4e", 3175
    ),
    "LICENSE.md": ("b1c2f51d0884b9d5b04c960e5726ebd19b8565f4", 754),
}
EXPECTED_TSC = {
    ("Clare Liguori", "Amazon"),
    ("Roshan Sadanani", "Cursor"),
    ("Harald Kirschner", "Microsoft"),
    ("Gav Verma", "OpenAI"),
    ("Jonathan Hefner", "Vercel"),
}
EXPECTED_CLIENTS = {
    "VS Code": ("stdio", "streamable-http", "sse"),
    "Cursor": ("stdio", "streamable-http", "sse"),
    "GitHub Copilot": ("stdio", "streamable-http", "sse"),
    "ChatGPT & Codex": ("stdio", "streamable-http"),
    "Kiro": ("stdio", "streamable-http", "sse"),
}
EXPECTED_AFFECTED_LAYERS = {
    "capability-source-metadata",
    "package-conformance",
    "consumer-projection-mapping",
    "host-extension-boundaries",
}
EXPECTED_RETAINED_AUTHORITY = {
    "intent-and-task-contract",
    "capability-routing-and-rerouting",
    "source-review-and-admission",
    "installation-enablement-update-and-rollback",
    "host-owned-authorization-and-sandboxing",
    "context-thread-worktree-and-resource-lifecycle",
    "process-loss-receipts-and-human-gates",
    "verification-acceptance-and-closure",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_record(
    record: dict[str, Any],
    *,
    acceptance: dict[str, Any] | None = None,
    root: Path = ROOT,
) -> None:
    _require(
        record.get("schema") == 1
        and record.get("id") == "agent-plugins-1.0.0-strategic-impact-v1"
        and record.get("asOf") == "2026-08-07"
        and record.get("status")
        == "primary-source-verified-strategic-rebaseline-no-runtime-adoption",
        "Agent Plugins record identity drifted",
    )
    _require(
        record.get("documentation") == DOCUMENTATION_PATH.as_posix()
        and (root / DOCUMENTATION_PATH).is_file(),
        "Agent Plugins documentation binding drifted",
    )
    contract = record.get("taskContract", {})
    _require(
        all(
            _nonempty(contract.get(key))
            for key in (
                "goal", "sourceBoundary", "accountAndDataBoundary",
                "authorityBoundary", "verificationSurface",
            )
        ),
        "Agent Plugins task contract drifted",
    )
    user_source = record.get("userSource", {})
    _require(
        user_source.get("originalPublisherOrPostLocatorProvided") is False
        and user_source.get("attributionVerified") is False,
        "Agent Plugins user-source attribution boundary drifted",
    )

    snapshot = record.get("sourceSnapshot", {})
    specification = snapshot.get("specificationRepository", {})
    site = snapshot.get("documentationRepository", {})
    _require(
        specification.get("revision") == SPEC_REVISION
        and specification.get("headMatchedRevisionAtReview") is True
        and specification.get("specificationVersion") == "1.0.0"
        and specification.get("repositoryStatusLabel") == "Published"
        and specification.get("tagsObserved") == []
        and specification.get("githubReleasesObserved") == [],
        "Agent Plugins specification identity or publication observation drifted",
    )
    _require(
        re.fullmatch(r"[0-9a-f]{40}", SPEC_REVISION) is not None
        and re.fullmatch(r"[0-9a-f]{40}", SITE_REVISION) is not None,
        "Agent Plugins source revision is not exact",
    )
    publication = specification.get("publicationCommit", {})
    _require(
        publication.get("revision")
        == "1fc1b6270e3cc492ec2d24ad7a34277c6d53b9c1"
        and publication.get("committedAt") == "2026-07-24T15:20:57Z",
        "Agent Plugins publication commit drifted",
    )
    actual_objects = {
        item["path"]: (item.get("oid"), item.get("size"))
        for item in specification.get("selectedGitObjects", [])
        if isinstance(item, dict) and _nonempty(item.get("path"))
    }
    _require(actual_objects == EXPECTED_OBJECTS, "Agent Plugins Git objects drifted")
    _require(
        site.get("revision") == SITE_REVISION
        and site.get("headMatchedRevisionAtReview") is True
        and site.get("deployedSpecificationStatusLabel") == "Working Draft"
        and site.get("statusConflictWithSpecificationRepository") is True,
        "Agent Plugins publication-status conflict drifted",
    )

    governance = snapshot.get("governance", {})
    tsc = governance.get("initialTechnicalSteeringCommittee", [])
    _require(
        governance.get("model") == "open-vendor-neutral-community-governed"
        and governance.get("noVendorReservedSeats") is True
        and governance.get("noSingleVendorCoreMaintainerMajority") is True
        and {(item.get("name"), item.get("affiliation")) for item in tsc}
        == EXPECTED_TSC
        and [item.get("name") for item in tsc if item.get("leadCoreMaintainer")]
        == ["Jonathan Hefner"],
        "Agent Plugins governance roster drifted",
    )
    portable = snapshot.get("portableContract", {})
    _require(
        portable.get("manifest") == "plugin.json"
        and portable.get("componentTypes") == ["agent-skills", "mcp-servers"]
        and portable.get("skillsLocation") == "skills/"
        and portable.get("mcpLocation") == "mcp.json"
        and portable.get("isolatesIndependentComponentFailures") is True
        and portable.get("fatalRootManifestViolationsRejectPlugin") is True
        and portable.get("packageContainmentIsSubprocessSandbox") is False,
        "Agent Plugins portable contract drifted",
    )
    actual_clients = {
        item["name"]: tuple(item.get("mcpTransports", []))
        for item in snapshot.get("officialCompatibleClients", [])
        if isinstance(item, dict) and item.get("skills") is True
    }
    _require(actual_clients == EXPECTED_CLIENTS, "Agent Plugins client matrix drifted")
    _require(
        snapshot.get("openAiProductTerminology", {}).get(
            "identicalToAgentPluginsV1PortableComponentSet"
        ) is False,
        "Agent Plugins and OpenAI product terminology were conflated",
    )
    _require(
        snapshot.get("rawThirdPartyBodyRetained") is False
        and snapshot.get("thirdPartyCodeExecuted") is False
        and snapshot.get("dependenciesInstalled") is False
        and snapshot.get("liveExternalStateMutated") is False,
        "Agent Plugins read-only boundary drifted",
    )

    verdicts = {
        item["id"]: item.get("verdict")
        for item in record.get("claimAdjudication", [])
        if isinstance(item, dict) and _nonempty(item.get("id"))
    }
    _require(
        verdicts.get("unqualified-final-ga-release")
        == "not-safe-due-upstream-status-conflict-and-no-tag"
        and verdicts.get("all-excerpt-brands-are-participants-or-clients")
        == "unsupported",
        "Agent Plugins claim adjudication drifted",
    )
    strategy = record.get("strategicDecision", {})
    _require(
        strategy.get("impact") == "high-packaging-layer-not-whole-product"
        and strategy.get("decision")
        == "adopt-agent-plugins-as-current-external-packaging-interoperability-floor"
        and set(strategy.get("affectedHarnessLayers", []))
        == EXPECTED_AFFECTED_LAYERS
        and set(strategy.get("retainedHarnessAuthority", []))
        == EXPECTED_RETAINED_AUTHORITY
        and strategy.get("directHarnessReplacement") is False
        and strategy.get("runtimeAdoptionAuthorized") is False,
        "Agent Plugins strategic decision drifted",
    )
    authority = record.get("authorityBoundary", {})
    _require(
        authority.get("publicSourceResearchAuthorized") is True
        and authority.get("repositoryEvidenceWriteAuthorized") is True
        and all(
            authority.get(key) is False
            for key in (
                "installAuthorized", "enableAuthorized", "executeAuthorized",
                "modelDispatchAuthorized", "accountConnectionAuthorized",
                "ccSwitchMutationAuthorized", "consumerMutationAuthorized",
                "migrationAuthorized", "publicationAuthorized", "releaseAuthorized",
            )
        ),
        "Agent Plugins authority boundary drifted",
    )
    claims = record.get("claimBoundary", {})
    _require(
        claims.get("provesDocumentedCompatibleClientMatrix") is True
        and all(
            claims.get(key) is False
            for key in (
                "provesLiveClientConformance", "provesInstallationOrEnablement",
                "provesInvocationOrInstructionDelivery", "provesRuntimeBehavior",
                "provesCrossHostParity", "provesSecurityOrSandboxing",
                "provesOperationalValue", "provesProductionReadiness",
            )
        ),
        "Agent Plugins claim boundary drifted",
    )

    if acceptance is not None:
        counts: dict[str, int] = {}
        for criterion in acceptance.get("acceptanceCriteria", []):
            status = criterion.get("assessment")
            counts[status] = counts.get(status, 0) + 1
        boundary = record.get("acceptanceBoundary", {})
        _require(
            counts == {
                "verified": boundary.get("verifiedCriteria"),
                "partial": boundary.get("partialCriteria"),
            }
            and boundary.get("plannedCriteria") == 0
            and boundary.get("criteriaAdvancedByThisResearch") == [],
            "Agent Plugins acceptance non-promotion drifted",
        )

    document = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for phrase in (
        SPEC_REVISION, SITE_REVISION, "Published", "Working Draft", "CC Switch",
        "It does not replace the Harness product", "No\nPlugin, Skill, MCP server",
    ):
        _require(phrase in document, "Agent Plugins documentation drifted")


def validate_repository_record(root: Path = ROOT) -> dict[str, Any]:
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    acceptance = json.loads((root / ACCEPTANCE_PATH).read_text(encoding="utf-8"))
    validate_record(record, acceptance=acceptance, root=root)
    return record


def main() -> int:
    validate_repository_record(ROOT)
    print("Agent Plugins 1.0.0 strategic-impact validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
