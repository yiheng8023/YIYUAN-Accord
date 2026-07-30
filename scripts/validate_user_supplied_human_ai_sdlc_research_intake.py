#!/usr/bin/env python3
"""Validate the bounded intake of the user-supplied human-AI SDLC report."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_PATH = (
    "registry/user-supplied-human-ai-sdlc-research-intake-2026-07-24.json"
)
DOCUMENTATION_PATH = (
    "docs/strategy/USER-SUPPLIED-HUMAN-AI-SDLC-RESEARCH-INTAKE-2026-07-24.md"
)
RESTORED_ARCHIVE_PATH = (
    "sources/user-supplied-human-ai-sdlc-research/"
    "hmc_report.agent.final.restored-2026-07-26.zip"
)
RESTORED_ARCHIVE_BYTES = 549186
RESTORED_ARCHIVE_SHA256 = (
    "C59510DB88911D920228803ACE53A2A97D77B9DF7E0EBF79D067BEFC4D02A3BD"
)
EXPECTED_MEMBER_HASHES = {
    "hmc_report.agent.final.md": (
        308391,
        "EF7AD703A31175565966716F28824AC3C1CC4AFE8091B4BBB07E62D08A730949",
    ),
    "hmc_report_sec02_chart1.png": (
        159117,
        "2DE38A2DAD0BC36983F4C1DAC0509B8FF6865BF9A6FC8B679480462FE9EFDC5F",
    ),
    "hmc_report_sec03_chart1.png": (
        211841,
        "F3755B7C4EE0A9FB17991CEA418E467AC67AA441F7C68A6CA9A7D69B37D52DF1",
    ),
    "hmc_report_sec05_chart1.png": (
        86648,
        "6D620A40088145BEBAD2373185E294AC27869F99932469D6077361DEE110CC6F",
    ),
}
EXPECTED_AUDIT_IDS = {
    "audit.dora-2025-adoption-amplifier",
    "audit.stack-overflow-2025-trust",
    "audit.jetbrains-2025-adoption-integration",
    "audit.metr-early-2025-productivity",
    "audit.mozannar-cups-verification-cost",
    "audit.shen-tamkin-skill-formation",
    "audit.stanford-early-career-employment",
    "audit.faros-review-and-incident-metrics",
}
PRIMARY_SOURCE_LEDGER_PATH = (
    "registry/"
    "human-ai-collaboration-high-impact-primary-source-claim-ledger-"
    "2026-07-27.json"
)
EXPECTED_REPAIRED_CLAIM_IDS = [
    "claim.dora-2025-organizational-amplifier-and-delivery-tension",
    "claim.stack-overflow-2025-trust-and-rework",
    "claim.metr-2025-experienced-oss-productivity-perception-gap",
    "claim.laban-2025-multi-turn-unreliability",
    "claim.shen-tamkin-2026-skill-formation",
]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _index(items: Any, field: str, label: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(items, list), f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        _require(isinstance(item, dict), f"{label} entries must be objects")
        key = item.get(field)
        _require(_nonempty(key), f"{label} entry needs {field}")
        _require(key not in result, f"{label} duplicate {field}: {key}")
        result[key] = item
    return result


def validate_intake(document: dict[str, Any], *, root: Path = ROOT) -> None:
    """Reject evidence promotion, source drift, or loss of the repair boundary."""
    _require(document.get("schema") == 1, "Intake schema must be 1")
    _require(
        document.get("id")
        == "user-supplied-human-ai-sdlc-research-intake-2026-07-24",
        "Intake identity drifted",
    )
    _require(
        document.get("status") == "retained-research-input-not-accepted-evidence",
        "Intake status was promoted",
    )

    authority = document.get("authorityBoundary")
    _require(isinstance(authority, dict), "Authority boundary is missing")
    _require(
        authority.get("calibrationState") == "paused-read-only",
        "Paused CALIBRATION boundary drifted",
    )
    for key in (
        "calibrationWriteAuthorized",
        "assetsAdmissionAuthorized",
        "hardStandardPromotionAuthorized",
        "skillOrHookMutationAuthorizedByThisRecord",
        "runtimeMutationAuthorizedByThisRecord",
        "externalCapabilityInstallationAuthorizedByThisRecord",
        "gitCommitOrPushAuthorizedByThisRecord",
    ):
        _require(authority.get(key) is False, f"Authority promoted: {key}")

    source = document.get("sourceArtifact")
    _require(isinstance(source, dict), "Source artifact is missing")
    _require(source.get("producerReportedByUser") == "Kimi", "Producer report drifted")
    _require(source.get("producerIndependentlyVerified") is False, "Producer was overclaimed")
    _require(source.get("archiveName") == "hmc_report.agent.final.zip", "Archive name drifted")
    _require(source.get("archiveBytes") == 549186, "Archive size drifted")
    _require(
        source.get("archiveSha256")
        == "53DDB51DF05A739EBBF68418D5B9F312AC28142C43C19DE1AE8D5CECECE5D39F",
        "Archive hash drifted",
    )
    _require(source.get("localAbsolutePathRetainedInPortableRecord") is False, "Local path leaked")
    _require(source.get("archiveExecuted") is False, "Archive execution boundary drifted")
    restored = source.get("restoredArchiveObservation")
    _require(isinstance(restored, dict), "Restored archive observation is missing")
    _require(
        restored.get("containerSha256") == RESTORED_ARCHIVE_SHA256,
        "Restored archive container hash drifted",
    )
    _require(
        restored.get("originalContainerSha256Equal") is False
        and restored.get("memberNamesSizesAndSha256Equal") is True,
        "Restored archive container/member distinction drifted",
    )
    _require(
        restored.get("gitOrRemoteDurabilityProved") is False,
        "Restored archive durability was overclaimed",
    )
    _require(
        restored.get("repositorySourceCustodyCreated") is True
        and restored.get("repositoryRelativePath") == RESTORED_ARCHIVE_PATH
        and restored.get("repositoryCustodyBytes") == RESTORED_ARCHIVE_BYTES
        and restored.get("repositoryCustodySha256") == RESTORED_ARCHIVE_SHA256
        and restored.get("repositoryCustodyHashVerified") is True,
        "Repository source custody metadata drifted",
    )
    archive_path = root / RESTORED_ARCHIVE_PATH
    _require(archive_path.is_file(), "Repository source custody archive is missing")
    _require(
        archive_path.stat().st_size == RESTORED_ARCHIVE_BYTES,
        "Repository source custody archive size drifted",
    )
    _require(
        hashlib.sha256(archive_path.read_bytes()).hexdigest().upper()
        == RESTORED_ARCHIVE_SHA256,
        "Repository source custody archive hash drifted",
    )
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        _require(
            len(names) == len(EXPECTED_MEMBER_HASHES)
            and set(names) == set(EXPECTED_MEMBER_HASHES),
            "Repository source custody archive member set drifted",
        )
        for name, (size, digest) in EXPECTED_MEMBER_HASHES.items():
            payload = archive.read(name)
            _require(
                len(payload) == size,
                f"Repository source custody member size drifted: {name}",
            )
            _require(
                hashlib.sha256(payload).hexdigest().upper() == digest,
                f"Repository source custody member hash drifted: {name}",
            )
    _require(
        _nonempty(restored.get("cleanupBoundary")),
        "Restored archive cleanup boundary is missing",
    )
    members = _index(source.get("members"), "name", "Archive members")
    _require(set(members) == set(EXPECTED_MEMBER_HASHES), "Archive member set drifted")
    for name, (size, digest) in EXPECTED_MEMBER_HASHES.items():
        _require(members[name].get("bytes") == size, f"Member size drifted: {name}")
        _require(members[name].get("sha256") == digest, f"Member hash drifted: {name}")
    _require(
        source.get("portableCustody")
        == (
            "repository-local source custody plus cryptographic identity and bounded "
            "audit; source content remains unaccepted evidence and Git or remote "
            "durability remains unproved"
        ),
        "Portable custody boundary drifted",
    )

    structure = document.get("reportStructure")
    _require(isinstance(structure, dict), "Report structure is missing")
    for key, expected in (
        ("lineCount", 1187),
        ("decodedCharacterCount", 183824),
        ("urlOccurrenceCount", 908),
        ("uniqueUrlCount", 503),
        ("referenceEntryCount", 292),
        ("referenceUrlCount", 278),
    ):
        _require(structure.get(key) == expected, f"Report structure drifted: {key}")
    declared = structure.get("declaredMethod")
    _require(
        isinstance(declared, dict) and declared.get("independentlyReproduced") is False,
        "Declared research method was promoted to reproduced evidence",
    )

    historical = document.get("historicalComparison")
    _require(isinstance(historical, dict), "Historical comparison is missing")
    _require(
        historical.get("priorKimiReportProvableFromRepository") is False,
        "Earlier Kimi provenance was invented",
    )
    _require(
        historical.get("classification")
        == "substantive-software-engineering-specialization-expansion-not-a-new-mother-framework",
        "Historical comparison classification drifted",
    )

    lifecycle = document.get("lifecycleProjection")
    _require(isinstance(lifecycle, dict), "Lifecycle projection is missing")
    _require(
        len(lifecycle.get("directlyDiscussedSlices", [])) == 11,
        "Direct lifecycle discussion set drifted",
    )
    _require(
        len(lifecycle.get("partialOrWeakSlices", [])) == 3,
        "Partial lifecycle set drifted",
    )
    _require(lifecycle.get("fullSoftwareLifecycleCoverageAccepted") is False, "Full lifecycle was overclaimed")
    _require(lifecycle.get("wholeHumanAiCollaborationCoverageAccepted") is False, "Whole domain was overclaimed")

    process_loss = document.get("processLossCrossCutAudit")
    _require(isinstance(process_loss, dict), "Process-loss cross-cut audit is missing")
    _require(
        process_loss.get("classification")
        == "substantive-explicit-mechanism-coverage-structural-modeling-incomplete",
        "Process-loss coverage classification drifted",
    )
    _require(
        process_loss.get("sourceMemberSha256")
        == EXPECTED_MEMBER_HASHES["hmc_report.agent.final.md"][1],
        "Process-loss source binding drifted",
    )
    mechanisms = process_loss.get("observedMechanisms")
    _require(
        isinstance(mechanisms, list)
        and {item.get("lineRange") for item in mechanisms if isinstance(item, dict)}
        == {"218-226", "324-344", "422-442", "691-694"},
        "Process-loss mechanism evidence drifted",
    )
    _require(
        process_loss.get("consistencyImpact")
        == (
            "Each transformation output can become the next transformation input, "
            "so an unobserved local distortion may cascade through decomposition, "
            "routing, delegation, implementation, review, and acceptance into "
            "global end-to-end inconsistency; a final-looking artifact cannot alone "
            "prove chain fidelity."
        ),
        "Process-loss end-to-end consistency impact drifted",
    )
    _require(
        isinstance(process_loss.get("notYetUnifiedAs"), list)
        and len(process_loss["notYetUnifiedAs"]) >= 4,
        "Process-loss structural gaps are missing",
    )
    _require(_nonempty(process_loss.get("claimLimit")), "Process-loss claim limit is missing")

    audit = document.get("citationIntegrityAudit")
    _require(isinstance(audit, dict), "Citation integrity audit is missing")
    _require(audit.get("sampleRepresentsWholeReport") is False, "Audit sample was overgeneralized")
    _require(audit.get("automatedCountsValidateClaimEntailment") is False, "URL counts became entailment proof")
    observations = _index(audit.get("observations"), "id", "Citation audit observations")
    _require(set(observations) == EXPECTED_AUDIT_IDS, "Citation audit observation set drifted")
    for item in observations.values():
        for field in (
            "reportClaim",
            "inlineTargetClass",
            "primaryUrl",
            "primarySourceResult",
            "disposition",
        ):
            _require(_nonempty(item.get(field)), f"Citation audit field missing: {field}")
    summary = audit.get("sampleSummary")
    _require(isinstance(summary, dict), "Citation sample summary is missing")
    for key in (
        "reportHighConfidenceLabelsAccepted",
        "allReportClaimsAccepted",
        "bodyLinksSafeAsEvidenceLedger",
    ):
        _require(summary.get(key) is False, f"Citation result was promoted: {key}")
    _require(summary.get("bibliographyUsefulForRepair") is True, "Repair value was discarded")

    repair = document.get("primarySourceRepair")
    _require(isinstance(repair, dict), "Primary-source repair binding is missing")
    _require(
        repair.get("ledgerPath") == PRIMARY_SOURCE_LEDGER_PATH
        and repair.get("status")
        == "bounded-subset-repaired-design-input-only"
        and repair.get("claimCount") == len(EXPECTED_REPAIRED_CLAIM_IDS)
        and repair.get("repairedClaimIds")
        == EXPECTED_REPAIRED_CLAIM_IDS,
        "Primary-source repair binding drifted",
    )
    for key in (
        "wholeReportAccepted",
        "studyResultsIndependentlyReproduced",
        "matrixEvidenceStatePromotionAuthorized",
        "hardStandardPromotionAuthorized",
        "selfAuthoredCapabilityMutationAuthorized",
    ):
        _require(
            repair.get(key) is False,
            f"Primary-source repair was overclaimed: {key}",
        )
    _require(
        _nonempty(repair.get("claimLimit")),
        "Primary-source repair claim limit is missing",
    )
    _require(
        (root / PRIMARY_SOURCE_LEDGER_PATH).is_file(),
        "Primary-source repair ledger is missing",
    )

    decision = document.get("decision")
    _require(isinstance(decision, dict), "Intake decision is missing")
    _require(decision.get("retainResearchInput") is True, "Research input was discarded")
    _require(decision.get("duplicateAndDiscard") is False, "Report was mislabeled as a duplicate")
    for key in (
        "replacePriorBroadResearch",
        "replaceCoverageRebaseline",
        "promoteClaimsWithoutRepair",
        "changeSelfAuthoredSkillChainNow",
        "changeHardStandardsNow",
    ):
        _require(decision.get(key) is False, f"Intake decision overclaimed: {key}")
    _require(_nonempty(decision.get("nextBoundedResult")), "Next bounded result is missing")

    _require(document.get("documentation") == DOCUMENTATION_PATH, "Documentation path drifted")
    documentation = root / DOCUMENTATION_PATH
    _require(documentation.is_file(), "Intake documentation is missing")
    normalized = " ".join(documentation.read_text(encoding="utf-8").split())
    for phrase in (
        "not accepted evidence",
        "cannot be called either the first or a repeated Kimi report",
        "body links are not safe as an evidence ledger",
        "Software engineering remains a priority specialization",
        "Process Loss Cross-Cut",
        "Do not change the mother framework",
    ):
        _require(phrase in normalized, f"Documentation boundary missing: {phrase}")

    for integration_path in (
        "docs/strategy/HUMAN-AI-COLLABORATION-COVERAGE-REBASELINE-2026-07-24.md",
        "docs/strategy/HUMAN-AI-COLLABORATION-SCENARIO-EVIDENCE-MATRIX-BATCH-01-2026-07-24.md",
        "docs/operations/CONTINUATION.md",
    ):
        text = (root / integration_path).read_text(encoding="utf-8")
        _require(
            "USER-SUPPLIED-HUMAN-AI-SDLC-RESEARCH-INTAKE-2026-07-24.md" in text,
            f"Intake integration link missing: {integration_path}",
        )


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    validate_intake(_load(root / EVIDENCE_PATH), root=root)
    print("user-supplied human-AI SDLC research intake: valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
