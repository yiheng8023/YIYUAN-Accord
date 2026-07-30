#!/usr/bin/env python3
"""Validate current Matt semantic-authority static admission evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ADMISSION_PATH = Path(
    "registry/human-ai-collaboration-semantic-authority-current-matt-static-admission-2026-07-28.json"
)
PROTOCOL_PATH = Path(
    "registry/human-ai-collaboration-semantic-authority-continuity-protocol-2026-07-28.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _index(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    result = {str(row.get(key)): row for row in rows if isinstance(row, dict)}
    _require(len(result) == len(rows), f"{label} identities drifted")
    return result


def validate_admission(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("status")
        == "source-license-and-static-review-pass-isolated-projection-open-no-execution"
        and document.get("scenarioId") == "HAC-SEMANTIC-AUTHORITY-01"
        and document.get("matrixCellId") == "SEM-03",
        "Current Matt static admission identity drifted",
    )
    source = document.get("source", {})
    revision = "ed37663cc5fbef691ddfecd080dff42f7e7e350d"
    _require(
        source.get("repository") == "https://github.com/mattpocock/skills"
        and source.get("revision") == revision
        and source.get("retrieval") == "public-git-clone-plus-git-cat-file-blob"
        and source.get("headVerified") is True
        and source.get("worktreeCleanAtObservation") is True
        and source.get("rawBlobBytesUsedForIdentity") is True
        and source.get("windowsCheckoutBytesUsedForIdentity") is False,
        "Current Matt source boundary drifted",
    )
    license_record = document.get("license", {})
    _require(
        license_record.get("spdx") == "MIT"
        and license_record.get("path") == "LICENSE"
        and license_record.get("gitBlobSha1")
        == "f1dd2c09108dde1a5f56097cee8461b3ea834499"
        and license_record.get("bytes") == 1068
        and license_record.get("sha256")
        == "0e7ac423bf2c6e223b7c5b156f8cf72da49d748e56a1641402c31f22ad07dbb5"
        and license_record.get("substantialPortionNoticeRequired") is True,
        "Current Matt license evidence drifted",
    )

    files = _index(document.get("exactPackageFiles", []), "path", "Package file")
    expected = {
        "skills/engineering/grill-with-docs/SKILL.md": (
            245,
            "bed05d2bd3245306267cea57cd696b5dd94d50fe",
            "610d091047bcfb9db0f75c057d15538481a721111579fc5ec7f83ad9131a2165",
        ),
        "skills/engineering/grill-with-docs/agents/openai.yaml": (
            145,
            "5dbe2780a51be3e9b118bd7758a73e54a9384e11",
            "94cd0ab161fb468a836349f5ed482ba58ce8e709a05c57ce533d739dbd35cca9",
        ),
        "skills/engineering/domain-modeling/SKILL.md": (
            3427,
            "d0f7e1a5ccb06a7184056ff9af02b67bc77f9dda",
            "152e2c97239affb12a60c5f4a7e74ab546a49ae169688c81f4e2ccc42dafa579",
        ),
        "skills/engineering/domain-modeling/CONTEXT-FORMAT.md": (
            2299,
            "eaf2a18573f0a2d8c69ed53e29e4d9e21baf81d8",
            "b8cc318f2a4285b530e908b6bc43901c3c5cd11100362636bbc4216639bef597",
        ),
        "skills/engineering/domain-modeling/ADR-FORMAT.md": (
            2766,
            "da7e78ec1c220cd0aedf7ad36424c9398034f375",
            "f1f36cd3f8d3b6474ddd5855da4e233bfc4ae1a1c5024909ccf11871819a41b2",
        ),
        "skills/engineering/domain-modeling/agents/openai.yaml": (
            101,
            "7f1522d2f11506ee205275ab7c282aa52366ecf6",
            "f6bf2aa996c6e6f53fdd0708e18a0d16a56aed8322cca59fedbe3c0d2c75f06b",
        ),
        "skills/productivity/grilling/SKILL.md": (
            843,
            "52d8eb3cadd2dca62634d5dccfa73ea6b725b117",
            "44331dda57f461db4fec3f2efb6ddabe7aaaa0a57ae0f88a883bc61aed8a0587",
        ),
        "skills/productivity/grilling/agents/openai.yaml": (
            105,
            "85b12607d0025c24c90b79162efe8685c16ba7da",
            "cf29b9a8dbf35a58a908a6ca4f64dcd86c2b2130291eee0a78b9f706b138825b",
        ),
    }
    _require(set(files) == set(expected), "Current Matt package file set drifted")
    for path, (size, blob, digest) in expected.items():
        row = files[path]
        _require(
            row.get("bytes") == size
            and row.get("gitBlobSha1") == blob
            and row.get("sha256") == digest
            and str(row.get("role", "")).strip(),
            f"Current Matt package pin drifted: {path}",
        )

    closure = document.get("dependencyClosure", {})
    _require(
        closure.get("entrySkill") == "grill-with-docs"
        and closure.get("namedSkillDependencies") == ["grilling", "domain-modeling"]
        and closure.get("exactPackageFileCount") == 8
        and closure.get("dependencyInventoryCompleteForObservedRevision") is True
        and len(closure.get("relativeFileDependencies", [])) == 2
        and len(closure.get("metadataFilesIncluded", [])) == 3,
        "Current Matt dependency closure drifted",
    )
    static = document.get("staticReview", {})
    for key in (
        "executableFileCount",
        "scriptFileCount",
        "dependencyInstallInstructionCount",
        "externalNetworkInstructionCount",
        "credentialOrSecretRequestCount",
        "deleteOrDestructiveCommandCount",
        "mcpAppOrAccountDependencyCount",
    ):
        _require(static.get(key) == 0, f"Current Matt static review drifted: {key}")
    _require(
        static.get("repositoryDocumentWriteBehaviorPresent") is True
        and static.get("humanDecisionConfirmationRequiredByGrilling") is True
        and static.get("compositionEntryImplicitInvocationAllowed") is False
        and static.get("disposableNoNetworkTrialStaticReviewPassed") is True,
        "Current Matt static behavior boundary drifted",
    )
    portability = document.get("portabilityReview", {})
    _require(
        portability.get("portableWithoutHostAdapterProved") is False
        and portability.get("slashNamedSkillCompositionRequiresHostResolution")
        is True
        and portability.get("relativeFormatFilesMustRemainCoLocated") is True
        and portability.get("isolatedProjectionRequiredBeforeExecution") is True,
        "Current Matt portability boundary drifted",
    )
    normalization = document.get("checkoutNormalizationHazard", {})
    _require(
        normalization.get("coreAutocrlf") is True
        and normalization.get("gitAttributesText") == "unspecified"
        and normalization.get("gitAttributesEol") == "unspecified"
        and normalization.get("rawBlobIdentityRequired") is True
        and len(normalization.get("observedConversions", [])) == 4
        and all(
            row.get("rawSha256") != row.get("worktreeSha256")
            and row.get("rawBytes") != row.get("worktreeBytes")
            for row in normalization.get("observedConversions", [])
        ),
        "Current Matt checkout normalization evidence drifted",
    )

    custody = document.get("temporarySourceCustody", {})
    _require(
        custody.get("retainedAsProductPayload") is False
        and custody.get("removedAfterEvidenceCapture") is True,
        "Current Matt temporary source custody drifted",
    )
    decision = document.get("decision", {})
    _require(
        decision.get("sourceAndHashAdmissionSatisfied") is True
        and decision.get("licenseProvenanceSecurityPortabilityReviewSatisfied")
        is True
        and decision.get("isolatedProjectionEligible") is True
        and decision.get("isolatedProjectionImplemented") is False
        and decision.get("dependencyCompleteExposureProved") is False
        and decision.get("loaderInvocationProved") is False
        and decision.get("candidateExecutionAdmissionSatisfied") is False
        and decision.get("consumerInstallOrCcUpdateEligible") is False,
        "Current Matt static admission decision overclaimed",
    )
    authority = document.get("authorityBoundary", {})
    for key in (
        "readPublicSourceAuthorized",
        "writeRepositoryAdmissionRecordAuthorized",
        "temporaryCloneAuthorized",
        "temporaryCloneCleanupAuthorized",
    ):
        _require(authority.get(key) is True, f"Current Matt authority missing: {key}")
    for key, value in authority.items():
        if key not in {
            "readPublicSourceAuthorized",
            "writeRepositoryAdmissionRecordAuthorized",
            "temporaryCloneAuthorized",
            "temporaryCloneCleanupAuthorized",
        }:
            _require(value is False, f"Current Matt authority expanded: {key}")
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Current Matt static admission claim boundary was promoted",
    )

    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    current = next(
        row
        for row in protocol["treatments"]
        if row["id"] == "SEM-MATT-CURRENT-COMPOSITION"
    )
    _require(
        current.get("revision") == revision
        and current.get("licenseProvenanceSecurityPortabilityRecheckSatisfied")
        is True
        and protocol["executionAdmission"][
            "exactCurrentComponentsRetrievedAndHashVerified"
        ]
        is True
        and protocol["executionAdmission"][
            "licenseProvenanceSecurityPortabilityRecheckSatisfied"
        ]
        is True,
        "Current Matt admission was not reconciled into protocol",
    )

    documentation = root / str(document.get("documentation"))
    _require(documentation.is_file(), "Current Matt static admission doc is missing")
    text = " ".join(documentation.read_text(encoding="utf-8").split())
    for phrase in (
        "eight files, not three",
        "not yet admitted for execution",
        "Markdown and YAML only",
        "not a no-side-effect treatment",
        "core.autocrlf=true",
        "must use Git blob/raw bytes",
        "Exposure will still not prove loader invocation",
    ):
        _require(phrase in text, f"Current Matt static admission doc missing: {phrase}")


def main() -> int:
    document = json.loads((ROOT / ADMISSION_PATH).read_text(encoding="utf-8"))
    validate_admission(document, root=ROOT)
    print("Current Matt semantic-authority static admission validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
