#!/usr/bin/env python3
"""Validate the dated self-authored control-chain carrier audit."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
AUDIT_PATH = Path(
    "registry/human-ai-collaboration-self-authored-control-chain-"
    "carrier-audit-2026-07-28.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _index(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    result = {str(row.get(key)): row for row in rows if isinstance(row, dict)}
    _require(len(result) == len(rows), f"{label} identities drifted")
    return result


def validate_audit(document: dict, *, root: Path = ROOT) -> None:
    _require(
        document.get("schema") == 1
        and document.get("id")
        == "human-ai-collaboration-self-authored-control-chain-carrier-audit-2026-07-28"
        and document.get("status")
        == "current-carrier-audit-partial-no-portfolio-mutation",
        "Control-chain audit identity drifted",
    )
    for relative in document.get("sourceBindings", {}).values():
        _require((root / relative).is_file(), f"Control-chain source missing: {relative}")

    observation = document.get("currentCarrierObservation", {})
    _require(
        observation.get("globalAgents", {}).get("sha256")
        == "29b7e7970a686e48a9d70d4d21a4151acec1d57d73cf83ba62e22836a2301b23"
        and observation.get("repositoryAgents", {}).get("sha256")
        == "db4f5ccb824600eb38cd318eba56a37566f23012a8673410cdb98037aba0fcac",
        "Control-chain AGENTS observation drifted",
    )
    skills = _index(observation.get("skills", []), "name", "Control Skill")
    _require(
        set(skills)
        == {"intent-contract", "capability-router", "closure-contract"},
        "Control-chain Skill set drifted",
    )
    expected = {
        "intent-contract": (
            29139,
            "1d67e4b84856bcd0828d89b82803a7275d95d8e586fd8efcd127f89e82845753",
            23075,
            "7eb8e46648d3b4889fe16e6c650a5f51a4ed1cf0baaeb46e70d9e24e6073befc",
        ),
        "capability-router": (
            22018,
            "eb9f7d253d12682a3e8b9f87faf5bad4284a2d268b25c30cc5ad9f6dd36eb8fe",
            16581,
            "3f1fd8597314ad501fa813864b0c73d7182ab64349f97a1bff640a508af5a127",
        ),
        "closure-contract": (
            12187,
            "59edfc131c45b7aa1ef85a1737317a0cc97adcfb0ddceb7ee81e9c744b13bbb3",
            7872,
            "b3515179f8304c2fa0b1a2a88450c2ccc98ab9cfdbb144b0b829526757052524",
        ),
    }
    for name, (size, digest, cc_size, cc_digest) in expected.items():
        row = skills[name]
        _require(
            row.get("currentBytes") == size
            and row.get("currentSha256") == digest
            and row.get("agentsAndCodexByteEqual") is True
            and row.get("ccSwitchBytes") == cc_size
            and row.get("ccSwitchSha256") == cc_digest
            and row.get("ccSwitchByteEqualToCurrent") is False,
            f"Control-chain carrier relation drifted: {name}",
        )
        _require(
            row.get("currentExactLineOverlapWithGlobalAgents", 0) > 0
            and row.get("currentExactThreeLineWindowOverlapWithGlobalAgents", 0)
            > 0,
            f"Control-chain overlap evidence missing: {name}",
        )

    startup = observation.get("startupVisibleCatalog", {})
    _require(
        startup.get("visibleEntriesPerLogicalName") == 2
        and len(startup.get("observedRoots", [])) == 2
        and startup.get("loaderInvocationProved") is False,
        "Control-chain startup catalog boundary drifted",
    )
    recalibration = observation.get("ownerRecalibration20260729", {})
    _require(
        recalibration.get("commonAgentsSkillsRootMustBeRetained") is True
        and recalibration.get("rootRetentionImpliesPayloadRetention") is False
        and recalibration.get("hostSpecificSkillPackagesMayDiffer") is True
        and recalibration.get("claudeCodexByteParityRequired") is False
        and recalibration.get("currentTurnImplicitSelectionLikeBehaviorObserved")
        is True
        and recalibration.get("nativeRuntimeCauseProved") is False
        and recalibration.get("selfAuthoredSkillCauseProved") is False
        and recalibration.get("hookCauseProved") is False
        and recalibration.get("composedCauseProved") is False
        and recalibration.get("stableFreshTaskImplicitSelectionProved") is False
        and recalibration.get("nativeFirstCausalAblationRequired") is True
        and recalibration.get("liveMutationAuthorized") is False,
        "Control-chain owner recalibration drifted",
    )
    native_evidence = observation.get("nativeImplicitInvocationEvidence20260729", {})
    official = native_evidence.get("officialDocumentation", {})
    isolation = native_evidence.get("isolation", {})
    control = native_evidence.get("control", {})
    treatment = native_evidence.get("treatment", {})
    cleanup = native_evidence.get("cleanup", {})
    limits = native_evidence.get("claimLimits", {})
    _require(
        native_evidence.get("hostVersion") == "0.145.0"
        and official.get("implicitInvocationByDescriptionDocumented") is True
        and official.get("allowImplicitInvocationDefaultTrueDocumented") is True
        and official.get("fullSkillBodyReadAfterSelectionDocumented") is True
        and official.get("userSkillRootDocumentedAs") == "$HOME/.agents/skills"
        and all(
            isolation.get(key) is True
            for key in (
                "freshEphemeralTaskPerArm",
                "temporaryCodexHome",
                "globalAgentsExcluded",
                "codexPrivateSkillRootExcluded",
                "hookExcluded",
                "projectAgentsExcluded",
                "threeSelfAuthoredAgentsSkillsTemporarilyMoved",
                "commonAgentsSkillsRootRetained",
                "samePromptBothArms",
                "sentinelTokenAbsentFromDescription",
            )
        )
        and control.get("exitCode") == 0
        and control.get("matchedPrivateBodyToken") is False
        and treatment.get("exitCode") == 0
        and treatment.get("fullSkillBodyReadVisible") is True
        and treatment.get("response") == "PURPLE_COMPASS_RECEIPT_7D29"
        and treatment.get("matchedPrivateBodyToken") is True
        and native_evidence.get("causalPass") is True
        and all(value is True for value in cleanup.values())
        and limits.get("nativeImplicitInvocationCapabilityProvedCurrentHost")
        is True
        and limits.get("earlierMixedCarrierTurnAttributed") is False
        and limits.get("universalTriggerReliabilityProved") is False
        and limits.get("selfAuthoredIncrementalValueProved") is False
        and limits.get("desktopAppServerExactChainFactorialSatisfied") is False,
        "Control-chain native implicit invocation evidence drifted",
    )
    dependencies = _index(
        observation.get("currentPackageDependencies", []),
        "skillName",
        "Control Skill dependency",
    )
    _require(
        set(dependencies) == {"intent-contract", "capability-router"},
        "Control-chain dependency set drifted",
    )
    expected_dependencies = {
        "intent-contract": (
            "references/intake-contract.md",
            20948,
            "66e3990e36f3771c5bd22136834100b7aba799c6416968f486e5929204392b93",
            18294,
            "8cae799380bed8b98eebecd43bbade44ad9cdb9b2551b4486c5c948b7c44f1b9",
        ),
        "capability-router": (
            "references/routing-contract.md",
            10108,
            "17d7ef3892f2794f78321615f276d89e5040059b6bf49793c2edebbfe5e90c3b",
            4794,
            "1ab6f8d5d344dc48386513305bcc5610f6654f27db850b7894d7fe9c53dba85e",
        ),
    }
    for name, (relative, size, digest, cc_size, cc_digest) in expected_dependencies.items():
        row = dependencies[name]
        _require(
            row.get("relativePath") == relative
            and row.get("currentBytes") == size
            and row.get("currentSha256") == digest
            and row.get("agentsAndCodexByteEqual") is True
            and row.get("ccSwitchBytes") == cc_size
            and row.get("ccSwitchSha256") == cc_digest
            and row.get("ccSwitchByteEqualToCurrent") is False,
            f"Control-chain dependency relation drifted: {name}",
        )

    hook = document.get("hookObservation", {})
    probe = hook.get("boundedSyntheticProbe", {})
    _require(
        hook.get("policyStatus") == "candidate"
        and hook.get("mode") == "auto"
        and hook.get("event") == "UserPromptSubmit"
        and hook.get("mayDeny") is False
        and hook.get("mayMutateExternalState") is False
        and hook.get("externalTransmission") == "deny"
        and hook.get("handlerFailure") == "fail-open-with-evidence",
        "Control-chain Hook boundary drifted",
    )
    _require(
        probe.get("positiveOutputBytes") == 428
        and probe.get("negativeOutputBytes") == 0
        and probe.get("sampleCountPerClass") == 1
        and probe.get("latencyGeneralizationAllowed") is False,
        "Control-chain Hook probe drifted",
    )
    live_hook = hook.get("liveRecheck20260729", {})
    _require(
        hook.get("observationDate") == "2026-07-28"
        and hook.get("historicalObservationNotCurrentState") is True
        and live_hook.get("hooksJsonExists") is True
        and live_hook.get("hooksJsonValue") == {}
        and live_hook.get("activeHookRegistrationObserved") is False
        and live_hook.get("hooksDirectoryExists") is True
        and live_hook.get("hooksDirectoryFileCount") == 0
        and live_hook.get("historicalConfigStateEntryExists") is True
        and live_hook.get(
            "historicalStateOrDirectoryCountsAsInvocationEvidence"
        )
        is False,
        "Control-chain current Hook recheck drifted",
    )

    findings = _index(document.get("findings", []), "id", "Finding")
    _require(
        set(findings)
        == {
            "CHAIN-01",
            "CHAIN-02",
            "CHAIN-03",
            "CHAIN-04",
            "CHAIN-05",
            "CHAIN-06",
            "CHAIN-07",
        },
        "Control-chain finding set drifted",
    )
    _require(
        len(document.get("coverageAssessment", [])) == 5,
        "Control-chain coverage assessment drifted",
    )
    verification = document.get("focusedVerification", {})
    _require(
        verification.get(
            "semanticAuthorityProjectionExposureProtocolAndAuditTests"
        )
        == 23
        and verification.get("carrierOverlapHandoffAndContextTests") == 60
        and verification.get("allPassedAtObservation") is True
        and verification.get(
            "repositoryVerifierPassedAfterEvidenceAndTemporaryRootReconciliation"
        )
        is True,
        "Control-chain verification boundary drifted",
    )
    _require(
        verification.get(
            "exactTemporaryProjectionAndReportRemovedAfterEvidencePersistence"
        )
        is True,
        "Control-chain temporary-root reconciliation drifted",
    )

    decision = document.get("decision", {})
    for key in (
        "selfAuthoredChainPresumedCorrect",
        "selfAuthoredResidualGapProved",
        "implicitLoadingCountsAsMaturity",
        "hookDefaultValueProved",
        "skillInstallUpdateDeleteReplaceOrRetireAllowed",
        "ccSwitchMutationAllowed",
        "weakModelDispatchAllowedByThisAudit",
        "agentsSkillsRootRemovalAllowed",
        "hostSpecificByteParityRequired",
    ):
        _require(decision.get(key) is False, f"Control-chain decision promoted: {key}")
    _require(
        decision.get("nativeFirstCausalAblationRequired") is False
        and decision.get(
            "nativeImplicitInvocationCapabilityProvedCurrentHost"
        )
        is True
        and decision.get("selfAuthoredIncrementalValueAblationRequired") is True,
        "Control-chain native baseline decision drifted",
    )
    _require(
        all(value is False for value in document.get("claimBoundary", {}).values()),
        "Control-chain claim boundary was promoted",
    )

    documentation = root / str(document.get("documentation"))
    _require(documentation.is_file(), "Control-chain audit documentation is missing")
    text = " ".join(documentation.read_text(encoding="utf-8").split())
    for phrase in (
        "remains a falsifiable upstream candidate",
        "On 2026-07-28",
        "There is no current Hook registration",
        "retained common compatibility root",
        "cannot attribute that behavior to a native runtime capability",
        "This proves current-host native implicit discovery",
        "Current host evidence still separates",
        "No portfolio mutation is eligible from this audit",
    ):
        _require(phrase in text, f"Control-chain documentation missing: {phrase}")


def main() -> int:
    document = json.loads((ROOT / AUDIT_PATH).read_text(encoding="utf-8"))
    validate_audit(document, root=ROOT)
    print("Self-authored control-chain carrier audit validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
