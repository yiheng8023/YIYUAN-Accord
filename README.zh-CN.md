# Agent Autonomy Harness

[English](README.md) | 简体中文

一个面向 Agent 自主性、人机协作、能力编排、生命周期控制与证据化工程的 Agent 中立
研究 Harness。

它的北极星是把 Agent 机制的学习与编排负担从用户脑中移出，同时保留人对目标、创造性
判断、重要决策和有界授权的控制。

## 决策卡

- **仓库状态：**公开研究与可证伪 PoC。当前没有宿主中立的生产运行时，也没有证明候选
  能力具有广泛价值或自研残余缺口已经成立。
- **当前 Skill 权威：**活跃的适配后第三方 payload 发布数量为 `0`。继承的 19 Skill、
  40 文件发布只是弃用的过渡证据，不是当前安装、更新、路由或产品来源。
- **当前非活跃池：**17 个经过审查的精确上游候选。其中 16 个依赖完整候选已由
  CC Switch v3.19.2 管理，并在普通重启后保持所有宿主开关关闭、消费者投影为 0；
  `customer-research` 仍仅供审查，没有安装。
- **当前闸门：**组合策展不要求绑定真实任务，可以按有界批次继续精确上游、非活跃的
  候选发现与审查。只有进入任务时激活，或主张行为、价值、可移植性和生产适用性前，
  才需要自然发生的真实任务以及当前路径缺口证据。
- **管理器边界：**CC Switch 在适用场景下是可替换的操作适配器，不是可移植产品契约。
  PR 6086 及其 Fork 只是可选上游贡献，不是 Harness 依赖。
- **插件姿态：**Harness 保持独立的 Agent 中立产品，只把插件作为可生成的消费者投影。
  当前状态是兼容插件、管理器无关但不具备发布资格；插件不得打包 CC Switch 管理的
  第三方 payload，也不得为同一组件制造第二个生命周期权威。
- **当前 Matt 来源：**25 个受管 payload 匹配精确发布
  `v1.2.3@6acc160e`，CC Switch 来源元数据已通过可恢复、仅元数据事务 pin 到该 tag。
  这不证明调用、行为、价值、可移植性或生产就绪。
- **决策包机制：**一个结构化 `GEN-RESEARCH-01` 请求现在可生成确定性、绑定来源的
  六路决策包。它保留未知项、证据上限、回退顺序、授权闸门和全为 false 的主张上限；
  14 项注入式越权全部 fail closed，且 `selectedRoute` 保持 `null`。这只是零模型机制
  证据，不是执行或价值证明。

详细的当前调度规则见[目标模式执行投影](docs/operations/CURRENT-GOAL-MODE-PROMPT.md)。

## 决策包机制

运行仓库自有且不执行候选能力的示例：

```powershell
python -B scripts/build_harness_decision_packet.py tests/fixtures/harness-decision-request-gen-research-01.json
```

该命令只向 stdout 输出规范 JSON。它不调用模型或候选、不选择路线、不安装或启用任何
能力、不连接账号、不修改管理器或消费者，也不发布或释放。决策包通过只证明其证据上限
内的来源绑定与 fail-closed 机制。

## 本项目解决什么问题

Agent 生态包含原生能力、Skills、MCP、Plugins、Apps、Hooks、仓库、线程、工作树和权限
表面。普通用户不应为了完成日常任务而学习并手动编排所有这些机制。

目标体验是一个有边界的自主闭环：

1. 理解真实任务与授权边界；
2. 观察当前宿主和协作状态；
3. 选择最小充分能力路径；
4. 只激活任务真正需要的能力；
5. 验证效果、释放闲置资源并暴露清理债；
6. 在协作迁移时保留基于仓库的连续性。

这不代表所有宿主当前都已暴露所需控制面。缺失的遥测或执行能力本身也是明确研究结果。

## 产品边界

Harness 明确分离五层：

1. **可移植决策核心**——意图、路由、上下文生命周期、任务拓扑、验证、交接与收口；
2. **运行时生命周期平面**——观测状态、期望状态、所有权、租约、释放、恢复和清理证据；
3. **宿主适配器**——Codex、Claude Code、Kimi 及未来宿主的事件、Hooks、API、命令和
   降级路径；
4. **能力生态治理**——跨能力类型的发现、精确版本、许可证、安全、依赖、重叠、维护、
   权限和准入；
5. **消费者投影**——独立治理的安装与运行时分发，包括适用时的 CC Switch 与宿主原生
   插件管理器。插件只是产品的一种投影，不是产品权威或通用能力管理器。

宿主原生授权与权限执行始终拥有最终权威。Harness 可以减少不必要提示，但不绕过或复制
宿主权限系统。

## 能力治理

除非证据证明另一条有界路径更好，否则使用以下顺序：

1. 健康的原生或运行时所有能力；
2. 合适的官方能力；
3. 已审查且持续维护的外部实现；
4. 组合已有能力；
5. 只有复现性残余缺口成立后才自研。

三种所有权类别不得混同：

- 官方、运行时所有或内置能力保持环境所有的带日期基线，不在本仓复制；
- 第三方候选保持精确上游正文。本仓保存审查、来源、兼容、路由与生命周期证据，不发布
  改写后的当前 payload；
- 仓库自研 Skill 或其它实现只有经过残余缺口证明和正常准入后，才可能进入未来发布；
  有效准入数量可以一直为零。

列出、获取、安装、启用、暴露、调用、指令交付、行为、价值和可移植性是相互独立的证据
状态，前一项不能自动证明后一项。

## 当前研究线

前三条 PoC 线是：

1. 上下文生命周期 -> 基于仓库的及时交接 -> 接续；
2. 任务拓扑 -> 分支/工作树判断 -> 有界执行和清理；
3. 任务级 MCP 生命周期 -> 释放 -> 失败恢复。

项目还研究跨 Agent 语义连续性、过程损失、资源压力归因和多维软工评价。当前模拟或
零模型证据不能证明真实领域、跨宿主、生产或广泛人群价值。

## 从这里开始

- [产品北极星](docs/strategy/PRODUCT-NORTH-STAR.md)
- [架构](docs/architecture.md)
- [研究与 PoC 计划](docs/strategy/RESEARCH-AND-POC-PLAN.md)
- [场景与证据矩阵](docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md)
- [最新接续记录](docs/operations/CONTINUATION.md)
- [开源就绪契约](docs/operations/OPEN-SOURCE-READINESS.md)
- [当前 Skill 组合权威](registry/skill-portfolio-current-authority.json)
- [项目验收映射](registry/program-acceptance-map.json)

## 仓库结构

- `docs/strategy/`：当前产品、研究、评价与证明计划；
- `registry/`：受治理的政策、证据、拓扑、准入和事件数据；
- `audits/`：有边界的来源与运行时证据；
- `sources/`：来源固定、许可证、选择与来源证明；
- `policies/` 与 `schemas/`：可机器检查的治理契约；
- `scripts/` 与 `tests/`：构建器、验证器、模拟与测试；
- `generated/`：派生投影，不具有独立权威；
- `skills/` 与 `release-manifest.json`：弃用的适配后第三方过渡证据，仅为历史和确定性
  验证保留。

## 验证

执行有界仓库检查：

```bash
python -B scripts/verify_bootstrap.py
python -B scripts/verify.py
```

完整本地测试面：

```bash
python -B -m unittest discover -s tests -v
```

验证器通过只证明它实际覆盖的检查，不证明当前宿主实时状态、候选价值、发布就绪或用户
验收。托管 CI 只是可选佐证，不是需要付费的验收依赖。

## 贡献与支持

- [贡献指南](CONTRIBUTING.md)
- [安全政策](SECURITY.md)
- [行为准则](CODE_OF_CONDUCT.md)
- [支持范围](SUPPORT.zh-CN.md)

欢迎提交候选来源、来源修正、安全发现、宿主证据、反例和确定性验证改进。贡献不等于
准入、安装、激活、发布或支持优先级。

## 开源与安全边界

本公开仓库采用分层权利模型：

- 仓库自有代码与治理机制：Apache-2.0；
- 仓库自有文档与公开治理文本：见[许可证政策](docs/license-policy.md)；
- 第三方材料：遵循原许可证以及 [NOTICE](NOTICE)、
  [许可证政策](docs/license-policy.md) 和
  [历史适配 payload 声明](THIRD_PARTY_NOTICES.md) 的边界。

不得发布凭据、私有记忆、账号状态、专有输入、受限来源正文或未经脱敏的消费者配置。
运行时安装、账号连接、外部写入和信任边界变化仍需单独授权。

公开可见不等于开源链路收口。当前闸门与带日期局限见
[开源就绪契约](docs/operations/OPEN-SOURCE-READINESS.md)。

## 历史证据

本仓库于 2026-07-18 从 `agent-skills-curated` 的完整 Git 历史启动。这个字面仓库名、历史
`skill.curated.*` ID、旧授权事件和弃用 manifest 身份仍是有效历史证据，但不再代表当前
产品身份或路由权威。

当前边界记录在
[`registry/skill-portfolio-current-authority.json`](registry/skill-portfolio-current-authority.json)。
迁移历史可在
[`docs/legacy-curated-skill-source-migration-review-2026-07-18.zh-CN.md`](docs/legacy-curated-skill-source-migration-review-2026-07-18.zh-CN.md)
和 Git 历史中查阅。

## 赞助

赞助完全可选，不购买支持优先级、准入、发布决定、治理例外、功能承诺或技术影响力。
详见[赞助说明](SPONSORING.zh-CN.md)。
