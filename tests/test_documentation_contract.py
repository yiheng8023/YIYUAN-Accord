from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class DocumentationContractTests(unittest.TestCase):
    def test_entry_surfaces_show_one_current_decision_before_evidence_depth(self) -> None:
        english = read("README.md")
        chinese = read("README.zh-CN.md")
        plan = read("docs/strategy/RESEARCH-AND-POC-PLAN.md")
        normalized_english = " ".join(english.split())
        compact_chinese = "".join(chinese.split())
        normalized_plan = " ".join(plan.split())

        self.assertLess(english.index("## Decision card"), english.index("## Current phase"))
        self.assertLess(chinese.index("## 决策卡"), chinese.index("## 当前阶段"))
        self.assertLess(
            plan.index("## Current decision gate"),
            plan.index("Working scenario and evidence gate:"),
        )
        for phrase in (
            "Current state:",
            "Current operating boundary:",
            "portable decision contract, host-neutral adapter contract, and host-specific implementation",
            "Current action:",
            "source-preserving, inactive candidate pool",
            "Evidence archive:",
        ):
            with self.subTest(surface="English", phrase=phrase):
                self.assertIn(phrase, normalized_english)
        for phrase in (
            "当前状态：",
            "当前运行边界：",
            "可移植决策合同、宿主中立适配合同与宿主特定实现",
            "当前行动：",
            "来源保真、默认不活跃的候选池",
            "证据入口：",
        ):
            with self.subTest(surface="Chinese", phrase=phrase):
                self.assertIn("".join(phrase.split()), compact_chinese)
        for phrase in (
            "one decision-relevant real task",
            "exact comparison artifacts",
            "user-confirmed kimi topology",
            "composition rather than replacement",
            "net benefit",
            "no new governance layer",
        ):
            with self.subTest(surface="Plan", phrase=phrase):
                self.assertIn(phrase, normalized_plan.lower())

    def test_kimi_comparison_surfaces_separate_replay_from_real_task_evidence(self) -> None:
        plan = read("docs/strategy/RESEARCH-AND-POC-PLAN.md")
        continuation = read("docs/operations/CONTINUATION.md")
        intake = read("audits/kimi-three-hook-comparison-intake-2026-08-01/REPORT.md")
        normalized_plan = " ".join(plan.split())
        normalized_continuation = " ".join(continuation.split())
        normalized_intake = " ".join(intake.split())
        normalized_plan_lower = normalized_plan.lower()
        normalized_continuation_lower = normalized_continuation.lower()
        replay_link = (
            "../../audits/kimi-three-hook-comparison-replay-2026-08-01/REPORT.json"
        )

        self.assertIn(replay_link, normalized_plan)
        self.assertIn(replay_link, normalized_continuation)

        for phrase in (
            "13",
            "3.592",
            "single-purpose evidence instrument",
            "only the three hook bodies execute",
            "all eight artifacts were executed is false",
            "does not prove host hook registration",
            "residual self-authored gap",
        ):
            with self.subTest(surface="plan", phrase=phrase):
                self.assertIn(phrase.lower(), normalized_plan_lower)
            with self.subTest(surface="continuation", phrase=phrase):
                self.assertIn(phrase.lower(), normalized_continuation_lower)

        self.assertIn(
            "3d51621f5f74b5f56cc286e233d2b2396fb62c3f",
            normalized_continuation,
        )

        for phrase in (
            "hooks/mcp-gate.mjs",
            "hooks/session-start.mjs",
            "hooks/context-usage.mjs",
            "173234",
            "1048576",
            "CONTINUE",
            "user-confirmed two executable prototypes",
            "not independently replayable from this repository alone",
            "does not unload schemas, processes, or connections",
            "retained mechanism replay follow-on",
            "not an independent prototype arm",
            "only the three hook bodies execute",
            "does not prove host hook registration",
        ):
            with self.subTest(surface="intake", phrase=phrase):
                self.assertIn(phrase.lower(), normalized_intake.lower())

        self.assertIn(
            "No live-host acceptance, pressure attribution, resource savings, "
            "cross-host parity, dynamic MCP lifecycle, or residual self-authored "
            "gap is proved",
            normalized_plan,
        )
        self.assertIn(
            "the compatibility PR, cc-switch worktree-practice artifact, live-host "
            "acceptance, real pressure attribution, resource savings, cross-host "
            "parity, dynamic MCP lifecycle, and same-task lane value remain open",
            normalized_continuation,
        )
        self.assertIn(
            "not pressure attribution, a stable benchmark, resource-savings "
            "evidence, cross-host parity, or a live-model result",
            normalized_intake,
        )
        self.assertIn("No live model ran", normalized_plan)
        self.assertIn("no live Kimi configuration", normalized_continuation)
        self.assertIn("live-model result", normalized_intake)
        self.assertIn(
            "exact-comparison gate therefore remains open",
            normalized_plan,
        )
        self.assertIn("exact-comparison gate is not closed", normalized_continuation)
        self.assertIn("exact-comparison gate remains open", normalized_intake)

    def test_portability_boundary_separates_contract_adapter_and_host_probe(self) -> None:
        architecture = " ".join(read("docs/architecture.md").split())
        plan = " ".join(
            read("docs/strategy/RESEARCH-AND-POC-PLAN.md").split()
        )

        for phrase in (
            "A host-local calibration probe is not a product adapter",
            "portable decision contract, host-neutral adapter contract, and host-specific implementation and evidence",
            "must not define a portable lane from one Agent's artifact shape",
            "thin host adapters translate only the unavoidable execution edge",
            "A targeted adapter may remain honestly host-specific",
            "A generalized product claim needs evidence from materially different host mechanisms",
            "must negotiate or degrade explicitly",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, architecture)

        for phrase in (
            "cross-host contract gate",
            "two executable prototypes (`context-usage`, `mcp-gate`)",
            "one shared injection infrastructure",
            "it is not a universal runtime",
        ):
            with self.subTest(surface="plan", phrase=phrase):
                self.assertIn(phrase, plan)

    def test_cross_host_mcp_mapping_is_bounded_to_mechanisms_and_degradation(self) -> None:
        plan = " ".join(read("docs/strategy/RESEARCH-AND-POC-PLAN.md").split())
        continuation = " ".join(read("docs/operations/CONTINUATION.md").split())
        mapping_link = (
            "../../registry/"
            "cross-host-mcp-lifecycle-contract-mapping-2026-08-02.json"
        )

        for surface in (plan, continuation):
            with self.subTest(surface=surface[:32]):
                self.assertIn(mapping_link, surface)
                self.assertIn("pre-tool call", surface)
                self.assertIn("0.146.0", surface)
                self.assertIn("residual self-authored", surface)

        for phrase in (
            "portable decision contract, host-neutral adapter contract, and host-specific implementation",
            "three of three",
            "bounded native-current-version win",
            "does not prove task-end release",
            "stable resource benefit",
        ):
            with self.subTest(surface="plan", phrase=phrase):
                self.assertIn(phrase, plan)

        for phrase in (
            "request acceptance does not prove runtime state",
            "exact process identity",
            "No model turn or model request",
            "self-authored controller remains ineligible",
            "universal MCP lifecycle",
        ):
            with self.subTest(surface="continuation", phrase=phrase):
                self.assertIn(phrase, continuation)

    def test_operational_manager_and_host_enforcement_are_adapter_neutral(self) -> None:
        agents = read("AGENTS.md")
        english = read("README.md")
        chinese = read("README.zh-CN.md")
        architecture = read("docs/architecture.md")
        normalized_agents = " ".join(agents.split())
        normalized_english = " ".join(english.split())
        compact_chinese = "".join(chinese.split())
        normalized_architecture = " ".join(architecture.split())

        self.assertIn(
            "native host authorization and permission enforcement surfaces",
            normalized_agents,
        )
        self.assertIn(
            "native host authorization and permission enforcement surfaces",
            normalized_english,
        )
        self.assertIn("宿主原生授权与权限强制面", compact_chinese)
        self.assertIn(
            "CC Switch is one current operational adapter where supported, "
            "not the portable product contract.",
            normalized_english,
        )
        self.assertIn(
            "CCSwitch是受支持场景下的一个当前操作适配器，不是可移植产品合同",
            compact_chinese,
        )
        self.assertIn(
            "Operational managers are replaceable adapters, not the portable contract.",
            normalized_architecture,
        )
        self.assertNotIn(
            "Host approval dialogs remain the permission enforcement surface",
            english,
        )
        self.assertNotIn("宿主原生授权弹窗继续负责权限强制", chinese)
        self.assertNotIn("这是目标运行模型", chinese)

    def test_readmes_use_matching_language_switches_and_role_structure(self) -> None:
        english = read("README.md")
        chinese = read("README.zh-CN.md")

        self.assertIn("English | [简体中文](README.zh-CN.md)", english)
        self.assertIn("[English](README.md) | 简体中文", chinese)

        for heading in (
            "## Repository Role",
            "## What This Repository Provides",
            "## What This Repository Does Not Own",
            "## Relationship To The Paired Repository",
            "## Layout",
            "## Verification",
            "## Update Rules",
            "## Safety Boundaries",
        ):
            with self.subTest(readme="English", heading=heading):
                self.assertIn(heading, english)

        for heading in (
            "## 仓库职责",
            "## 本仓库提供什么",
            "## 本仓库不负责什么",
            "## 与配对仓库的关系",
            "## 目录结构",
            "## 验证方式",
            "## 更新规则",
            "## 安全边界",
        ):
            with self.subTest(readme="Chinese", heading=heading):
                self.assertIn(heading, chinese)

    def test_governance_documents_define_current_noninterchangeable_layers(self) -> None:
        corpus = " ".join(
            "\n".join(
                (
                read("AGENTS.md"),
                read("README.md"),
                read("docs/architecture.md"),
                read("policies/intake.md"),
                read("docs/official-external-capability-baselines.md"),
                read("docs/anthropic-official-skills-coverage.md"),
                read("docs/starred-capability-source-discovery.md"),
                )
            ).split()
        )

        for phrase in (
            "Official, runtime-owned, or built-in Skill bodies",
            "dated overlap evidence",
            "third-party payloads exact upstream",
            "third-party candidate",
            "must not enter an execution path",
            "admitted repository-authored residual-gap payload",
            "future active release inventory",
            "deprecated adapted transition release",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, corpus)

    def test_starred_sources_are_discovery_hints_not_approval(self) -> None:
        discovery = read("docs/starred-capability-source-discovery.md")
        corpus = "\n".join((read("README.md"), read("policies/intake.md")))

        for phrase in (
            "Discovery surface",
            "not approval",
            "not installation",
            "not managed inventory",
            "third-party skill source",
            "official external baseline",
            "index / awesome list",
            "risk / exclusion",
            "Third-party Skill bodies remain exact upstream",
            "separate authority",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, discovery)

        for phrase in (
            "Stars are only discovery hints",
            "do not prove license safety",
            "must not enter `skills/`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, corpus)

    def test_official_external_baselines_are_not_managed_inventory(self) -> None:
        baseline_policy = read("docs/official-external-capability-baselines.md")
        coverage = read("docs/anthropic-official-skills-coverage.md")
        corpus = "\n".join(
            (
                read("README.md"),
                read("AGENTS.md"),
                read("docs/architecture.md"),
                read("policies/intake.md"),
            )
        )

        for phrase in (
            "Official External Capability Baselines",
            "dated external baseline",
            "not managed inventory",
            "not proof of live availability",
            "coverage comparison",
            "gap analysis",
            "routing calibration",
            "review-candidate",
            "exact upstream identity and bytes",
            "separately authorized manager or host transaction",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, baseline_policy)

        for phrase in (
            "Anthropic official Skills",
            "first recorded instance",
            "source-available",
            "all-rights-reserved",
            "covered",
            "reference",
            "skip",
            "release-manifest.json",
            "Current authority note",
            "exact upstream",
            "historical matrix remains evidence only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, coverage)

        for phrase in (
            "official external capability baselines",
            "does not approve import",
            "license/provenance",
            "exact upstream",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, corpus)

    def test_pairing_and_router_boundaries_are_explicit(self) -> None:
        corpus = "\n".join(
            (read("AGENTS.md"), read("README.md"), read("docs/architecture.md"))
        )

        for phrase in (
            "capability decision router",
            "native reasoning",
            "recipe or DAG",
            "no skill needed",
            "human confirmation",
            "does not install",
            "does not write to `codex-user-config`",
            "does not write to a live Agent environment",
            "derived projections",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, corpus)

    def test_runtime_resolution_is_documented_as_a_structural_contract(self) -> None:
        for path in ("README.md", "README.zh-CN.md"):
            text = read(path)
            with self.subTest(path=path):
                self.assertIn("visible-capability-inventory", text)
                self.assertIn("runtimeResolution", text)

    def test_governance_roadmap_matches_current_contract_state(self) -> None:
        design = read("docs/superpowers/specs/2026-06-22-governance-contracts-design.md")

        for phrase in (
            "Current Implementation State",
            "Batch A is complete",
            "`registry/skills.json` remains schema 1",
            "manifest v2 has not been published",
            "The next bounded task is not a manifest upgrade",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, design)

        self.assertNotIn(
            "Batch A is the next implementation target after user review",
            design,
        )

    def test_skill_v2_contract_decision_avoids_second_truth_source(self) -> None:
        decision = read("docs/decisions/2026-06-23-skill-v2-contract-decision.md")

        for phrase in (
            "Decision: do not promote Skill v2 metadata into a new authoritative skills registry yet",
            "`registry/skills.json` remains the schema-1 approved release inventory",
            "`registry/routing.json` remains the authority for Skill routing metadata",
            "`registry/capabilities.json` remains the authority for abstract lifecycle coverage",
            "No second Skill truth source",
            "No manifest v2 publication",
            "Future promotion gate",
            "5-8 representative Skills",
            "legacy-pending",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, decision)


if __name__ == "__main__":
    unittest.main()
