#!/usr/bin/env python3
"""Replay the pinned Kimi Hook mechanisms in an isolated zero-model root.

This is an evidence instrument, not a host adapter. It extracts every bound
artifact from one exact Git commit, verifies all artifacts before use, executes
only the three pinned JavaScript Hooks against synthetic local fixtures, and
writes one no-overwrite atomic report. It never reads or writes the live Kimi
configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

try:
    from .evaluate_context_pressure_advisory import evaluate_advisory
except ImportError:
    from evaluate_context_pressure_advisory import evaluate_advisory


PINNED_REVISION = "3d51621f5f74b5f56cc286e233d2b2396fb62c3f"
EXPECTED_ARTIFACTS = {
    "AGENTS.md": "ff87576699d4dfbfb11ca33f8819ff98805561c11c55d67b51e36c88e6125673",
    "hooks/mcp-gate.mjs": "b1a21741b99c8da39c10c0da4acd9e77052ad7704a7cdc6c5a0519f6c2f16af9",
    "hooks/session-start.mjs": "7d32d1f2ae9c80eda12af2722cc0dcfb59b6f4af7bbe3574f240dbc7aead122d",
    "hooks/context-usage.mjs": "884c40f92e9fdc7e9da8b1a2a03647746a0ca26820f09c7f6709586fde1e35ae",
    "skills/mcp-gate/SKILL.md": "c183602591390d19cd028cb11dbbf71512d139be836664808875b812b9a141de",
    "config.hooks.toml": "aaff759ee5d57d11165e1025c66158ff2674b677fe8366eabb0139d2cc012bb3",
    "config.permission.toml": "a876381226447b6cd66de851443b95a9e3b64eded9a10d2bc085643fb808c7b3",
    "mcp-gate.json": "8e007ccf299637b3d54193cc8686bf9a525fbe4713b4569b56e52c1c469be79e",
}
ARTIFACT_TREATMENTS = {
    "AGENTS.md": "rule-text-static-binding",
    "config.hooks.toml": "hook-registration-static-binding",
    "config.permission.toml": "bound-context-not-replay-input",
    "hooks/context-usage.mjs": "executed-synthetic-fixture",
    "hooks/mcp-gate.mjs": "executed-synthetic-fixture",
    "hooks/session-start.mjs": "executed-synthetic-fixture",
    "mcp-gate.json": "configuration-seed-then-synthetic-mutation",
    "skills/mcp-gate/SKILL.md": "operator-contract-static-binding",
}
EXPECTED_NODE_VERSION = "v24.18.0"
EXPECTED_CANDIDATE_HOOK_SOURCE_BYTES = 7286
EXPECTED_CANDIDATE_HOOK_SOURCE_LINES = 169
EXPECTED_CASE_IDS = {
    "mcp-explicit-off",
    "mcp-pinned-default-on",
    "mcp-default-off",
    "mcp-explicit-on",
    "mcp-built-in-pass",
    "mcp-missing-gate-fail-open",
    "session-fresh-injection",
    "session-stale-handoff-excluded",
    "context-low-continue",
    "context-warning-wait",
    "context-warning-hysteresis",
    "context-critical-wait",
    "context-compaction-reset",
}
EXPECTED_CLAIM_BOUNDARY = {
    "compatibilityPrBound": False,
    "allThreeHooksAreIndependentPrototypes": False,
    "lane2ExecutablePrototypeExists": False,
    "ccSwitchWorktreePracticeArtifactBound": False,
    "allBoundArtifactsExecuted": False,
    "hostHookRegistrationProved": False,
    "skillInstructionDeliveryProved": False,
    "permissionRuleEffectProved": False,
    "liveHostAcceptanceProved": False,
    "liveModelBehaviorProved": False,
    "pressureAttributionProved": False,
    "resourceSavingsProved": False,
    "crossHostParityProved": False,
    "dynamicMcpLifecycleProved": False,
    "residualSelfAuthoredGapProved": False,
}
EXPECTED_TOPOLOGY = {
    "userConfirmed": True,
    "executablePrototypeCount": 2,
    "sharedInfrastructureCount": 1,
    "ruleTextGroupCount": 2,
    "lanes": [
        {
            "id": "lane-1-context-lifecycle-handoff",
            "executablePrototype": "hooks/context-usage.mjs",
            "sharedInfrastructure": ["hooks/session-start.mjs"],
            "ruleText": "AGENTS.md#上下文交接协议",
            "runtimeState": "handoff.md",
        },
        {
            "id": "lane-2-branch-worktree-judgment",
            "executablePrototype": None,
            "sharedInfrastructure": [],
            "ruleText": "AGENTS.md#Git纪律",
            "practice": "cc-switch-worktree-practice-unbound",
        },
        {
            "id": "lane-3-mcp-on-demand-activation",
            "executablePrototype": "hooks/mcp-gate.mjs",
            "sharedInfrastructure": ["hooks/session-start.mjs"],
            "supportingArtifacts": [
                "mcp-gate.json",
                "skills/mcp-gate/SKILL.md",
                "config.hooks.toml",
            ],
        },
    ],
}
HOOK_ROLES = {
    "mcp-gate": "executable-prototype-lane-3",
    "context-usage": "executable-prototype-lane-1",
    "session-start": "shared-injection-infrastructure",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalized_evaluator_bytes() -> bytes:
    return Path(__file__).read_bytes().replace(b"\r\n", b"\n")


def expected_evidence_cost() -> dict[str, Any]:
    evaluator = _normalized_evaluator_bytes()
    return {
        "sourceArtifactCount": len(EXPECTED_ARTIFACTS),
        "mechanismCaseCount": len(EXPECTED_CASE_IDS),
        "ruleCaseCount": 2,
        "userActionCount": 0,
        "modelRequestCount": 0,
        "candidateHookSourceBytes": EXPECTED_CANDIDATE_HOOK_SOURCE_BYTES,
        "candidateHookSourceLines": EXPECTED_CANDIDATE_HOOK_SOURCE_LINES,
        "evaluatorSourceBytes": len(evaluator),
        "evaluatorSourceLines": len(evaluator.decode("utf-8").splitlines()),
        "evaluatorSourceSha256": hashlib.sha256(evaluator).hexdigest(),
        "evaluatorToCandidateHookByteRatio": round(
            len(evaluator) / EXPECTED_CANDIDATE_HOOK_SOURCE_BYTES,
            3,
        ),
        "excludesTestsReportsAndDocumentation": True,
    }


def validate_temporary_parent(temporary_parent: Path) -> Path:
    parent = temporary_parent.resolve()
    system_temp = Path(tempfile.gettempdir()).resolve()
    if not parent.is_dir():
        raise RuntimeError("temporary parent must already exist")
    if parent != system_temp and not parent.is_relative_to(system_temp):
        raise RuntimeError("temporary parent must be inside the system temporary root")
    return parent


def _run(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _git_text(repository: Path, *args: str) -> str:
    result = _run(["git", "-C", str(repository), *args])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _git_bytes(repository: Path, object_spec: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), "show", object_spec],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def load_and_verify_sources(repository: Path) -> tuple[dict[str, bytes], str]:
    repository = repository.resolve()
    resolved = _git_text(repository, "rev-parse", f"{PINNED_REVISION}^{{commit}}")
    if resolved != PINNED_REVISION:
        raise RuntimeError("pinned Kimi revision did not resolve exactly")
    head = _git_text(repository, "rev-parse", "HEAD")
    sources: dict[str, bytes] = {}
    failures: list[str] = []
    for relative_path, expected_sha in EXPECTED_ARTIFACTS.items():
        content = _git_bytes(repository, f"{PINNED_REVISION}:{relative_path}")
        actual_sha = hashlib.sha256(content).hexdigest()
        if actual_sha != expected_sha:
            failures.append(f"{relative_path}:{actual_sha}")
        sources[relative_path] = content
    if failures:
        raise RuntimeError("pinned Kimi artifact mismatch: " + ", ".join(failures))
    return sources, head


def _write_sources(root: Path, sources: dict[str, bytes]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for relative_path, content in sources.items():
        target = root / "source" / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        paths[relative_path] = target
    return paths


def _invoke_hook(
    node: str,
    hook: Path,
    home: Path,
    payload: dict[str, Any] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["KIMI_CODE_HOME"] = str(home)
    return _run(
        [node, str(hook)],
        env=env,
        stdin=(json.dumps(payload, ensure_ascii=False) if payload is not None else None),
    )


def _harness_context_state(pressure: bool) -> dict[str, Any]:
    return evaluate_advisory(
        {
            "signalProvenance": "host-event",
            "signalObserved": True,
            "pressureIndicated": pressure,
            "criticalFactDriftObserved": False,
            "threadCreationAuthorized": False,
            "ctx0405PacketPrepared": True,
            "automaticCreationClaimed": False,
            "losslessHandoffClaimed": False,
            "crossHostParityClaimed": False,
            "fixedPercentageClaimed": False,
            "terraCountsAsWeakAgentAcceptance": False,
        }
    )


def _case(
    case_id: str,
    hook: str,
    result: subprocess.CompletedProcess[str],
    passed: bool,
    *,
    harness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": case_id,
        "hook": hook,
        "role": HOOK_ROLES[hook],
        "passed": passed,
        "exitCode": result.returncode,
        "stdoutSha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
        "stderrSha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest(),
    }
    if harness is not None:
        row.update(
            {
                "harnessState": harness["state"],
                "harnessClassification": harness["classification"],
                "harnessFollowOn": harness["followOn"],
            }
        )
    return row


def _write_wire(home: Path, session_id: str, total_input: int) -> None:
    wire = home / "sessions" / "fixture" / session_id / "agents" / "main" / "wire.jsonl"
    wire.parent.mkdir(parents=True, exist_ok=True)
    wire.write_text(
        json.dumps(
            {
                "usage": {
                    "inputOther": total_input,
                    "inputCacheRead": 0,
                    "inputCacheCreation": 0,
                }
            },
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _run_mechanism_cases(
    node: str,
    paths: dict[str, Path],
    root: Path,
) -> tuple[list[dict[str, Any]], int]:
    home = root / "kimi-home"
    home.mkdir(parents=True)
    gate_path = home / "mcp-gate.json"
    gate_path.write_bytes(paths["mcp-gate.json"].read_bytes())
    pinned_gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
    gate_payload = {"default": "off", "servers": {"blocked": "off", "allowed": "on"}}
    (home / "MEMORY.md").write_text("memory fixture\n", encoding="utf-8")
    handoff = home / "handoff.md"
    handoff.write_text("handoff fixture\n", encoding="utf-8")
    (home / "config.toml").write_text(
        'default_model = "fixture"\n\n[models."fixture"]\nmax_context_size = 1000\n',
        encoding="utf-8",
        newline="\n",
    )

    mcp_hook = paths["hooks/mcp-gate.mjs"]
    session_hook = paths["hooks/session-start.mjs"]
    context_hook = paths["hooks/context-usage.mjs"]
    cases: list[dict[str, Any]] = []
    process_count = 0

    def invoke(hook: Path, payload: dict[str, Any] | None = None) -> subprocess.CompletedProcess[str]:
        nonlocal process_count
        process_count += 1
        return _invoke_hook(node, hook, home, payload)

    result = invoke(mcp_hook, {"tool_name": "mcp__unknown__call"})
    cases.append(
        _case(
            "mcp-pinned-default-on",
            "mcp-gate",
            result,
            pinned_gate_payload == {"default": "on", "servers": {}}
            and result.returncode == 0,
        )
    )
    gate_path.write_text(json.dumps(gate_payload), encoding="utf-8")
    result = invoke(mcp_hook, {"tool_name": "mcp__blocked__call"})
    cases.append(_case("mcp-explicit-off", "mcp-gate", result, result.returncode == 2))
    result = invoke(mcp_hook, {"tool_name": "mcp__unknown__call"})
    cases.append(_case("mcp-default-off", "mcp-gate", result, result.returncode == 2))
    result = invoke(mcp_hook, {"tool_name": "mcp__allowed__call"})
    cases.append(_case("mcp-explicit-on", "mcp-gate", result, result.returncode == 0))
    result = invoke(mcp_hook, {"tool_name": "shell_command"})
    cases.append(_case("mcp-built-in-pass", "mcp-gate", result, result.returncode == 0))
    gate_path.unlink()
    result = invoke(mcp_hook, {"tool_name": "mcp__blocked__call"})
    cases.append(
        _case("mcp-missing-gate-fail-open", "mcp-gate", result, result.returncode == 0)
    )
    gate_path.write_text(json.dumps(gate_payload), encoding="utf-8")

    result = invoke(session_hook)
    fresh_pass = (
        result.returncode == 0
        and "memory fixture" in result.stdout
        and "gated OFF: blocked" in result.stdout
        and "handoff fixture" in result.stdout
    )
    cases.append(_case("session-fresh-injection", "session-start", result, fresh_pass))
    stale_time = time.time() - 8 * 24 * 3600
    os.utime(handoff, (stale_time, stale_time))
    result = invoke(session_hook)
    stale_pass = (
        result.returncode == 0
        and "memory fixture" in result.stdout
        and "gated OFF: blocked" in result.stdout
        and "handoff fixture" not in result.stdout
    )
    cases.append(
        _case("session-stale-handoff-excluded", "session-start", result, stale_pass)
    )

    session_id = "comparison-session"
    payload = {"session_id": session_id}

    _write_wire(home, session_id, 500)
    result = invoke(context_hook, payload)
    harness = _harness_context_state(False)
    cases.append(
        _case(
            "context-low-continue",
            "context-usage",
            result,
            result.returncode == 0 and result.stdout == "" and harness["state"] == "CONTINUE",
            harness=harness,
        )
    )

    _write_wire(home, session_id, 750)
    result = invoke(context_hook, payload)
    harness = _harness_context_state(True)
    cases.append(
        _case(
            "context-warning-wait",
            "context-usage",
            result,
            result.returncode == 0 and "75.0%" in result.stdout and harness["state"] == "WAIT",
            harness=harness,
        )
    )

    result = invoke(context_hook, payload)
    cases.append(
        _case(
            "context-warning-hysteresis",
            "context-usage",
            result,
            result.returncode == 0 and result.stdout == "",
            harness=harness,
        )
    )

    _write_wire(home, session_id, 900)
    result = invoke(context_hook, payload)
    harness = _harness_context_state(True)
    cases.append(
        _case(
            "context-critical-wait",
            "context-usage",
            result,
            result.returncode == 0 and "90.0%" in result.stdout and harness["state"] == "WAIT",
            harness=harness,
        )
    )

    _write_wire(home, session_id, 500)
    result = invoke(context_hook, payload)
    harness = _harness_context_state(False)
    cases.append(
        _case(
            "context-compaction-reset",
            "context-usage",
            result,
            result.returncode == 0 and result.stdout == "" and harness["state"] == "CONTINUE",
            harness=harness,
        )
    )
    return cases, process_count


def build_report(repository: Path, temporary_parent: Path, node: str) -> dict[str, Any]:
    temporary_parent = validate_temporary_parent(temporary_parent)
    sources, source_head = load_and_verify_sources(repository)
    node_version_result = _run([node, "--version"])
    if node_version_result.returncode != 0:
        raise RuntimeError("Node.js runtime is unavailable")

    syntax_checks = 0
    temporary_path: Path | None = None
    with tempfile.TemporaryDirectory(
        prefix="aah-kimi-hook-replay-",
        dir=temporary_parent,
    ) as temporary_root:
        temporary_path = Path(temporary_root)
        paths = _write_sources(temporary_path, sources)
        for relative_path in (
            "hooks/mcp-gate.mjs",
            "hooks/session-start.mjs",
            "hooks/context-usage.mjs",
        ):
            result = _run([node, "--check", str(paths[relative_path])])
            syntax_checks += 1
            if result.returncode != 0:
                raise RuntimeError(f"Node syntax check failed for {relative_path}")
        cases, hook_processes = _run_mechanism_cases(node, paths, temporary_path)
    temporary_removed = temporary_path is not None and not temporary_path.exists()
    hook_sources = [
        sources["hooks/mcp-gate.mjs"],
        sources["hooks/session-start.mjs"],
        sources["hooks/context-usage.mjs"],
    ]
    candidate_hook_bytes = sum(len(content) for content in hook_sources)
    candidate_hook_lines = sum(len(content.decode("utf-8").splitlines()) for content in hook_sources)
    if (
        candidate_hook_bytes != EXPECTED_CANDIDATE_HOOK_SOURCE_BYTES
        or candidate_hook_lines != EXPECTED_CANDIDATE_HOOK_SOURCE_LINES
    ):
        raise RuntimeError("pinned Kimi Hook source cost drifted")
    agents_text = sources["AGENTS.md"].decode("utf-8")
    rule_cases = [
        {
            "id": "lane-1-context-handoff-rules",
            "role": "rule-text",
            "passed": all(
                phrase in agents_text
                for phrase in (
                    "## 上下文交接协议",
                    "主动维护 `~/.kimi-code/handoff.md`",
                    "新会话经 SessionStart hook 自动载入 handoff.md 完成接力",
                )
            ),
        },
        {
            "id": "lane-2-git-discipline-rules",
            "role": "rule-text-no-executable-prototype",
            "passed": all(
                phrase in agents_text
                for phrase in (
                    "## Git 纪律",
                    "主动建议并创建分支或 worktree",
                    "worktree 用于并发任务隔离",
                )
            ),
        },
    ]

    report: dict[str, Any] = {
        "schema": 1,
        "id": "kimi-three-hook-comparison-replay-v1",
        "status": "valid-mechanism-replay-only",
        "evaluationDate": "2026-08-01",
        "source": {
            "repository": "kimi-code-user-config",
            "pinnedRevision": PINNED_REVISION,
            "headAtRun": source_head,
            "headMatchesPinnedRevision": source_head == PINNED_REVISION,
            "artifacts": [
                {"path": path, "sha256": sha}
                for path, sha in sorted(EXPECTED_ARTIFACTS.items())
            ],
        },
        "topology": EXPECTED_TOPOLOGY,
        "artifactTreatments": dict(ARTIFACT_TREATMENTS),
        "runtime": {
            "nodeVersion": node_version_result.stdout.strip(),
            "syntaxCheckProcessCount": syntax_checks,
            "hookProcessCount": hook_processes,
        },
        "mechanismCases": cases,
        "ruleCases": rule_cases,
        "evidenceCost": expected_evidence_cost(),
        "temporaryCarrier": "system-temporary-directory",
        "liveConfigurationRead": False,
        "liveConfigurationWritten": False,
        "networkCapabilityInvokedByEvaluator": False,
        "modelRequestSent": False,
        "isolatedTemporaryRootRemoved": temporary_removed,
        "claimBoundary": dict(EXPECTED_CLAIM_BOUNDARY),
    }
    report["reportSha256"] = canonical_sha256(report)
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    body = dict(report)
    digest = body.pop("reportSha256", None)
    if digest != canonical_sha256(body):
        failures.append("hard-fail-kimi-replay-report-digest")
    if (
        report.get("schema") != 1
        or report.get("id") != "kimi-three-hook-comparison-replay-v1"
        or report.get("status") != "valid-mechanism-replay-only"
    ):
        failures.append("hard-fail-kimi-replay-identity")
    source = report.get("source", {})
    expected_artifacts = [
        {"path": path, "sha256": sha}
        for path, sha in sorted(EXPECTED_ARTIFACTS.items())
    ]
    if (
        source.get("pinnedRevision") != PINNED_REVISION
        or source.get("headAtRun") != PINNED_REVISION
        or source.get("headMatchesPinnedRevision") is not True
        or source.get("artifacts") != expected_artifacts
    ):
        failures.append("hard-fail-kimi-replay-source-identity")
    if report.get("topology") != EXPECTED_TOPOLOGY:
        failures.append("hard-fail-kimi-replay-topology")
    if report.get("artifactTreatments") != ARTIFACT_TREATMENTS:
        failures.append("hard-fail-kimi-replay-artifact-treatment")
    if report.get("runtime") != {
        "nodeVersion": EXPECTED_NODE_VERSION,
        "syntaxCheckProcessCount": 3,
        "hookProcessCount": len(EXPECTED_CASE_IDS),
    }:
        failures.append("hard-fail-kimi-replay-runtime-identity")
    if report.get("evidenceCost") != expected_evidence_cost():
        failures.append("hard-fail-kimi-replay-evidence-cost")
    cases = report.get("mechanismCases", [])
    if (
        not isinstance(cases, list)
        or len(cases) != len(EXPECTED_CASE_IDS)
        or any(not isinstance(row, dict) for row in cases)
        or {row.get("id") for row in cases if isinstance(row, dict)} != EXPECTED_CASE_IDS
        or any(row.get("passed") is not True for row in cases if isinstance(row, dict))
    ):
        failures.append("hard-fail-kimi-replay-mechanism-cases")
    roles = {row.get("hook"): row.get("role") for row in cases if isinstance(row, dict)}
    if roles != HOOK_ROLES:
        failures.append("hard-fail-kimi-replay-hook-role-classification")
    rule_cases = report.get("ruleCases")
    if (
        not isinstance(rule_cases, list)
        or rule_cases
        != [
            {
                "id": "lane-1-context-handoff-rules",
                "role": "rule-text",
                "passed": True,
            },
            {
                "id": "lane-2-git-discipline-rules",
                "role": "rule-text-no-executable-prototype",
                "passed": True,
            },
        ]
    ):
        failures.append("hard-fail-kimi-replay-rule-text-binding")
    states = {
        row.get("id"): row.get("harnessState")
        for row in cases
        if isinstance(row, dict) and row.get("id", "").startswith("context-")
    }
    if states != {
        "context-low-continue": "CONTINUE",
        "context-warning-wait": "WAIT",
        "context-warning-hysteresis": "WAIT",
        "context-critical-wait": "WAIT",
        "context-compaction-reset": "CONTINUE",
    }:
        failures.append("hard-fail-kimi-replay-harness-context-decisions")
    if report.get("claimBoundary") != EXPECTED_CLAIM_BOUNDARY:
        failures.append("hard-fail-kimi-replay-claim-promotion")
    if (
        report.get("liveConfigurationRead") is not False
        or report.get("liveConfigurationWritten") is not False
        or report.get("networkCapabilityInvokedByEvaluator") is not False
        or report.get("modelRequestSent") is not False
        or report.get("isolatedTemporaryRootRemoved") is not True
        or report.get("temporaryCarrier") != "system-temporary-directory"
    ):
        failures.append("hard-fail-kimi-replay-side-effect-boundary")
    return list(dict.fromkeys(failures))


def write_report_atomically(output: Path, report: dict[str, Any]) -> None:
    output = output.resolve()
    if output.exists():
        raise RuntimeError("Kimi replay report already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
        ) as handle:
            staging = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if output.exists():
            raise RuntimeError("Kimi replay report already exists")
        try:
            os.link(staging, output)
        except FileExistsError as error:
            raise RuntimeError("Kimi replay report already exists") from error
        staging.unlink()
        staging = None
    finally:
        if staging is not None and staging.exists():
            staging.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-repository", type=Path, required=True)
    parser.add_argument("--temporary-parent", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument("--node", default=shutil.which("node"))
    args = parser.parse_args()
    if not args.node:
        raise SystemExit("Node.js runtime was not found")
    try:
        report = build_report(args.source_repository, args.temporary_parent, args.node)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    failures = validate_report(report)
    if failures:
        for failure in failures:
            print(failure)
        return 1
    write_report_atomically(args.output_report, report)
    print(report["reportSha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
