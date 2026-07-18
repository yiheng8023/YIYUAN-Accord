import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "README.zh-CN.md",
    "AGENTS.md",
    "docs/strategy/PRODUCT-NORTH-STAR.md",
    "docs/strategy/RESEARCH-AND-POC-PLAN.md",
    "docs/operations/CONTINUATION.md",
    "registry/agent-autonomy-harness-bootstrap-2026-07-18.json",
]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


for relative in REQUIRED:
    require((ROOT / relative).is_file(), f"missing bootstrap file: {relative}")

document = json.loads(
    (ROOT / "registry/agent-autonomy-harness-bootstrap-2026-07-18.json").read_text(
        encoding="utf-8"
    )
)
require(document.get("schema") == 1, "bootstrap schema drifted")
require(document.get("id") == "agent-autonomy-harness-bootstrap-2026-07-18", "bootstrap identity drifted")
require(document.get("status") == "private-repository-bootstrapped-from-complete-curation-history", "bootstrap status drifted")
require(document.get("migration", {}).get("sourceCommit") == "a5f4451dcdaf897dc8c17c4a9f5620addcf29181", "source commit drifted")
require(document.get("migration", {}).get("sourceRepositoryDeletedByThisTask") is False, "source deletion boundary drifted")
require(len(document.get("firstProofLanes", [])) == 3, "first proof-lane inventory drifted")
require(not any(document.get("claimLimits", {}).values()), "an unproven bootstrap claim was promoted")
require(
    document.get("codexWorkspaceHandoff")
    == {
        "localRepositoryCreated": True,
        "projectRegisteredInCodex": False,
        "projectRegistrationToolAvailable": False,
        "projectScopedContinuationThreadCreated": False,
    },
    "Codex workspace handoff boundary drifted",
)
require(
    document.get("verificationState", {}).get("remoteActionsState")
    == "billing-blocked-jobs-not-started",
    "remote CI boundary drifted",
)

readme = (ROOT / "README.md").read_text(encoding="utf-8")
readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
require("Agent Autonomy Harness" in readme, "English README identity drifted")
require("自治协作与能力编排" in readme_zh, "Chinese README identity drifted")
require("scripts/verify_bootstrap.py" in readme, "bootstrap verification not documented")

print("Agent Autonomy Harness bootstrap validation passed.")
