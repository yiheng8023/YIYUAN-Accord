# 3.3 发布材料工作稿

用途：3.3发布材料及核对依据，本文本身不构成验收、发布回执或日期通知。版本状态、未完项和实际发布记录以[共识计划](PLAN-v3.3.md)、[当前接续](CONTINUATION.md)及精确版本公开记录为准；本文复用W08/S5，不新增产品验收或发布日期。

## 文案底稿

以下表达产品定位和设计目标；正式发布前须按精确版本的验收结果校准，不能直接作为已实现能力声明。

| 字段 | 英文稿 | 中文含义 |
|---|---|---|
| 产品名 | YIYUAN Accord | 项目统一名称 |
| Declaration | Empower every dream. | 宣言：助力每一个梦想。 |
| Mission | Support reliable long-term human–AI collaboration | 为人与AI的长期协作提供协调与可靠性支持 |
| Tagline | Make tools adapt to people, rather than making people adapt to tools. | 让工具适应人，而非人适应工具。 |
| Description | An open-source human–AI collaboration system whose general design is independent of any vendor or host. It aims to let users describe goals while the assistant and host coordinate capabilities, settings, execution, changes and result checks. | 通用设计不绑定模型厂商或宿主的开源人机协作系统，旨在让用户直接描述目标，由助手与宿主共同协调能力、设置、执行、变化和结果核验。 |

项目发布说明底稿：

> We started YIYUAN Accord after repeated collaboration failures: an interruption could displace the original goal, a handoff could lose constraints, and passing checks could still leave the actual job unfinished.
>
> The project explores how agents can carry those responsibilities through real work, combining host capabilities with scoped coordination and verification. Users keep control over their decisions and changes of direction.
>
> The project remains independent and vendor-neutral. For the release, we will show the exact supported environment, a reproducible task, the verified outcome, and the remaining limitations.

正式稿须填入已验版本、实际使用入口和演示链接，并按实际成品校准能力与限制。涉及工具或模型的致谢须据实说明其作用，不能声称全部历史由同一模型构建。

## 首次使用者说明与发布字段草案

以下中英介绍、结构字段和检查清单面向非技术首次使用者，按精确版本及其有效证据使用；不构成普遍支持、效果或发布承诺。构建身份、安装采用和入口验收分别以当前接续及其来源为准，不从旧构建观察继承。

## YIYUAN Accord 3.3：让 Agent 协调协作（草案）

> **版本与证据说明。** 本介绍表达3.3的定位和适用边界；精确版本身份、安装采用、入口验收与发布记录须分别核对。候选冻结不证明资格、发布就绪或发布完成；单项、旧版本或辅助执行观察不构成完整功能与各入口验收。

### 你可以怎样开始

你不需要先学习插件、命令或模型设置。用日常语言告诉 Agent 你想达成什么结果；可以补充背景、限制、你在意的事项，以及希望怎样确认事情做完。例如：“请把这些材料整理成一份我能发给团队的简明说明，保留原文，并告诉我哪些内容还不能确定。”这只是表达目标的示例，不是特定功能或结果的保证。

### Agent 怎样协调工作

Accord 的设计目标是让 Agent 从理解目标开始，判断是否可行和还缺什么条件，在获准范围内选择、组合宿主能力、Accord 组件与适用的第三方能力，随着情况变化调整做法，并核验实际结果和所属资源后态。若条件不足或影响先前判断，Agent 应说明、修正受影响的工作，并保留尚未完成的事项以便继续。用户不必预先掌握工具协调、配置或任务交接。

3.3当前范围为已选OpenAI本地执行及其Remote控制路线，包括CLI、SDK、Codex Desktop、VS Code、Work Local/Remote和手机Remote；本包为Codex适配。各入口及模式支持仍须实际验收，Linux/macOS CLI和通用连续性保留；其它执行位置没有当前适配承诺。普通Chat独立用途、网页Chat、JetBrains及Xcode本版延期，能力仍未知；研究或内容能否构成完整结果仍按具体任务判断，这不恢复本版已延期的适配。Claude不在3.3分发范围，供应商中立定位保持。

普通对话沿用宿主常规流程，Accord不会为达成闭环而自动追加对话回合；结束本轮时仍须保留未完事项。任务恢复与按需交接保留。需要长程持续执行时，由用户明确选择宿主的目标模式等控制。

### 哪些决定仍由你掌握

你明确选择的模型、推理强度和使用限制应持续生效，适用的现有配置应保持稳定。子任务的模型与推理强度应按实际需要及当前宿主支持选择，不固定档位数量，也不要求与主模型相同；保留足够的当前配置同样合理。这不自动授权更改主模型。对于既有授权未涵盖的变更，包括改变你固定的选择或跨越服务商、账户、数据访问、重大费用边界，Agent 应先说明影响并取得必要决定；已有明确授权无需重复确认。

你决定要达成什么、是否改变方向，以及是否授权会产生实质影响的操作。Agent 应在授权范围内行动；需要你的判断、授权或本人操作时，应把具体事项交还给你。Agent 负责核验交付并纠正已发现的问题；你可以审阅和纠正结果，决定是否接受，而不必替 Agent 承担每一步检查。能力协调不会绕过宿主权限，也不意味着每一步都自动完成；恢复和交接依赖受支持的宿主接口、有效授权及连续性核验；包内可选交接接口不提供默认宿主控制连接或自动时机。

### 条件、成本与尚待核实

3.3使用宿主已有模型、受支持工具和 Accord 组件，不要求额外部署专用第三方决策模型；宿主自身的要求和费用仍适用。协作介入可能增加上下文占用、等待时间、计算成本、指令冲突或维护负担。现有材料没有证明它一定能省时、省钱或提高可靠性，也没有证明所有入口都能完成上述工作。

这里描述3.3的设计方向和范围，不是已验证的普遍效果。具体入口、行为、安装使用和效果主张须绑定精确版本及实际证据；发布时间与结果以对应公开记录为准。本文提供产品介绍，不代替安装指南或发布回执。

## YIYUAN Accord 3.3: letting an Agent coordinate the work (draft)

> **Version and evidence.** This introduction describes the purpose and boundaries of 3.3. Verify the exact version, actual installation, entry acceptance and publication record separately. Candidate freezing does not establish qualification, release readiness or publication. Individual, earlier-version or assisted observations do not establish complete functionality or acceptance across entries.

### How to get started

You do not need to learn plugins, commands, or model settings first. Tell the Agent in everyday language what outcome you want. You can add background, constraints, what matters to you, and how you would like the result checked. For example: “Please turn these materials into a concise note I can share with my team, preserve the original text, and tell me what is still uncertain.” This illustrates how to state a goal; it is not a promise of a particular feature or result.

### How the Agent coordinates the work

Accord is designed to have the Agent start by understanding the goal, assess feasibility and missing conditions, choose and combine host capabilities, Accord components and suitable third-party capabilities within its authorization, adapt as circumstances change, and verify the actual result and owned resource state. If conditions are missing or earlier judgments are affected, the Agent should explain and correct the affected work, while preserving unfinished items for continuation. Users need not first learn tool coordination, configuration, or task handoff.

Version 3.3 covers selected local OpenAI execution paths and their Remote controls, including CLI, SDK, Codex Desktop, VS Code, Work Local/Remote and mobile Remote; this package provides the Codex adaptation. Each entry and mode still needs actual acceptance. Linux/macOS CLI and shared continuity remain; other execution locations have no current adaptation commitment. Independent ordinary Chat, web Chat, JetBrains and Xcode are deferred for this release, with capabilities still unknown. Research or content may form a complete result for a specific task; this does not reopen deferred adaptation. Claude is outside 3.3 distribution. Vendor independence is unchanged.

Ordinary conversations follow the host's normal flow. Accord does not add turns to force completion; unfinished duties remain when a turn ends. Task recovery and appropriate handoff are preserved. Long-running controls such as the host's Goal mode remain the user's explicit choice.

### Decisions that remain yours

Your explicit choices of model and reasoning effort, and your usage restrictions, remain in force; an adequate configuration should stay stable. Subtask models and efforts should fit actual needs and current host support, with no fixed tier count or requirement to match the main model. Keeping an adequate existing choice is also valid. This does not itself authorize changing the main model. If a change is not already covered by your authorization, the Agent should explain its impact and obtain the necessary decision before acting. This includes changing a pinned choice or crossing boundaries involving providers, accounts, data access or significant cost. Existing explicit authorization does not require repeated confirmation.

You decide what outcome you want, whether to change direction, and whether to authorize actions with material consequences. The Agent should act within its authorization and bring specific decisions, permissions, or actions back to you when needed. The Agent is responsible for checking its deliverables and correcting identified problems. You can review and challenge the result and decide whether to accept it, without taking over every verification step. Coordinating capabilities does not bypass host permissions or mean every step happens automatically; recovery and handoff depend on supported host interfaces, valid authority and verified continuity. The optional packaged handoff interface supplies no default host control connection or automatic timing.

### Conditions, costs, and what remains unverified

Version 3.3 uses host-provided models, supported tools, and Accord components; it does not require deploying an additional dedicated third-party decision model. Normal host requirements and costs still apply. Coordination may add context use, waiting time, compute cost, instruction conflicts, or maintenance burden. The available materials do not prove that it will save time or money, improve reliability, or complete the described work across all entry points.

This description covers the design intent and scope of 3.3, not verified universal results. Claims about entry support, behavior, installation, use and effects require the exact version and applicable evidence. Publication dates and results follow the corresponding public records. This introduction does not replace installation guidance or a publication receipt.

### 结构字段 / Structured fields

```json
{
  "audience": "People encountering YIYUAN Accord for the first time, including readers without a technical background.",
  "stage": "Product introduction and release-copy reference; exact-version acceptance, publication and public post-state require their own evidence. Candidate freezing is not publication proof.",
  "productName": "YIYUAN Accord",
  "declaration": "Empower every dream.",
  "mission": "Support reliable long-term human–AI collaboration.",
  "version": {
    "release": "3.3.0",
    "note": "The version identifies the target package, not qualification, actual host adoption or publication. Verify each against the exact candidate and its source records. Earlier observations retain their original identities and conditions.",
    "developmentPackageSnapshot": null
  },
  "scope": {
    "purpose": "Designed to help an Agent understand a goal, assess feasibility and missing conditions, compose host capabilities, Accord components and suitable third-party capabilities within authorization, adapt to changes, verify results and owned resource state, correct affected work, and preserve unfinished items.",
    "howToStart": "State the desired outcome in everyday language; optionally add background, constraints, priorities, and how to check the result. No technical setup knowledge is assumed in this introductory explanation.",
    "normalInteraction": "Preserve task duties, recovery and appropriate handoff without automatically adding conversation turns. Host long-running controls remain the user's explicit choice.",
    "subtaskAllocation": "Select models and efforts against actual task needs and current host support; no fixed tier count or requirement to inherit. Keeping an adequate current choice is valid. Preserve user-pinned main-model choices and authority boundaries; optimality remains unverified.",
    "userDecisions": "The user retains decisions about the desired outcome, changes of direction, authorizations with material consequences, and acceptance. Explicit choices of model and reasoning effort, and usage restrictions, remain in force; keep an adequate configuration stable. Subtask delegation does not itself authorize changing the main model. A change not already covered by existing authorization, including changing a pinned choice or crossing provider, account, data access or significant cost boundaries, requires explaining its impact and obtaining the necessary user decision. Existing explicit authorization does not require repeated confirmation. The Agent owns verification and correction; users may inspect and challenge outputs without taking over each verification step.",
    "focus": "OpenAI execution environments with practical delivery value and a feasible way to fulfill necessary collaboration duties; this package provides the Codex adaptation.",
    "limits": [
      "These are design aims, not accepted results across all entry points.",
      "Suitability depends on the specific host and actual acceptance; plugin visibility or Hook support alone does not establish it.",
      "Independent ordinary Chat, web Chat, JetBrains and Xcode are deferred for this release; capabilities remain unknown. Task-specific research or content usefulness does not reopen deferred adaptation.",
      "Claude is outside the 3.3 distribution scope.",
      "Agent actions remain within authorization and host permissions. Recovery and handoff require supported host interfaces, valid authority and verified continuity; the optional handoff interface supplies no default host control connection or automatic timing."
    ]
  },
  "verification": {
    "status": "Support claims require an exact-version suitability decision and actual acceptance; consult the current continuation and acceptance sources for results and unfinished duties.",
    "unverified": [
      "Support and actual behavior for specific entry points",
      "User installation and use instructions",
      "Publication timing",
      "Effects on time, cost, reliability, and task completion"
    ],
    "note": "Do not infer universal behavior or user instructions from a package version, candidate freezing or maintainer checks."
  },
  "cost": "Uses host-provided models, supported tools, and Accord components; no additional dedicated third-party decision model is required. Normal host requirements and costs apply. Coordination may add context use, waiting time, compute cost, instruction conflicts, or maintenance burden. No time, cost, or reliability improvement is verified.",
  "publication": "Verify applicable existing human authorization and every condition before publication, then verify the same exact version in public records. This text is not evidence of readiness, a publication date or completed publication.",
  "languages": [
    "zh-CN",
    "en"
  ]
}
```

## 首次使用者发布准备清单 / First-use release checklist

本清单列出首次使用说明和既定发布工作的核对职责，不以空复选框单独判定实际状态；完成情况须回查精确候选及当前来源。文稿面向首次接触且没有技术背景的用户，不提供旧版迁移操作。
This checklist records duties for first-use copy and the existing release work; unchecked boxes alone do not establish current status. Determine completion from the exact candidate and current sources. The copy serves first-time, nontechnical users and includes no migration procedure.

- [ ] 按精确候选完成必要功能、入口适用性、生命周期、系统影响、独立审查和托管检查；区分设计方向与已验事实。 / Complete the required function, entry suitability, lifecycle, system-impact, independent-review and hosted checks for the exact candidate; separate design aims from demonstrated facts.
- [ ] 用自然语言目标示例解释开始方式；核实真实安装与使用入口后再补操作说明，不编造按钮、命令、支持范围或时间。 / Explain how to start with an ordinary goal; add setup instructions only after verifying the actual installation and use entry, without inventing controls, commands, support or dates.
- [ ] 保持职责清晰：Agent核验和纠正交付，用户保留目标、方向、必要授权和接受结果的决定；不把每一步检查退回用户。 / Keep responsibility clear: the Agent verifies and corrects delivery; users retain goals, direction, necessary authorization and acceptance, without taking over every check.
- [ ] 同步核对中文稿、英文稿、结构字段、README与清单的受众、用途、阶段、范围、费用和未决事项；未验入口不写成已支持。 / Reconcile audience, purpose, status, scope, cost and unresolved items across both languages, structured fields, README and this checklist; do not present unverified entries as supported.
- [ ] 根据实际使用条件写明运行环境与权限要求，保留已有设置、组件及用户选择。 / Explain evidenced runtime and permission prerequisites while preserving existing settings, components and user choices.
- [ ] 将依赖版本与实际入口/后端、接口、OS/架构和权限共同核验；分开宿主内部运行时、npm启动器/SDK及独立Hook/MCP进程，不因版本数字相同或单项最低要求就宣布组合兼容。 / Verify dependencies with the actual entry/backend, interfaces, OS/architecture and permissions. Distinguish the host's internal runtime, npm launcher/SDK and independent Hook/MCP processes; matching version numbers or one component's minimum requirement do not establish compatibility.
- 当前包的具体前提已在两语README说明：实际宿主启动环境可发现并执行兼容的 `node`；CI的Node 24覆盖不定义最低版本。普通入口不要求Python、第三方npm或额外第三方Skill/MCP；可选SDK记录器的内建SQLite要求另列。发布前仍须核实际入口，不以静态 `host-check` 或测试用绝对Node路径代验。 / Both READMEs now describe the current prerequisite: the actual host launch environment must find and execute compatible `node`. Node 24 CI coverage does not define a minimum version. The ordinary entry needs no Python, third-party npm packages or additional third-party Skills/MCP servers; the optional SDK recorder's built-in SQLite requirement is separate. Actual entry verification remains open; static `host-check` or a test's absolute Node path does not replace it.
- [运行时评估](../../research/reviews/2026-10-09-node-runtime-compatibility.md)已用于上述说明：当前受测推荐为Node24维护线，已有24.19.0/24.21.0有限回归；其它主版本、最早兼容补丁和完整宿主采用仍未验，不硬编码“16.9起支持”或“22.5有SQLite即足够”。 / The [runtime assessment](../../research/reviews/2026-10-09-node-runtime-compatibility.md) informs this guidance: maintained Node24 is the current tested recommendation, with bounded24.19.0/24.21.0 checks; other major versions, the earliest compatible patch and complete host adoption remain unverified. API introduction dates do not establish package support.
- [ ] 发布说明清楚列出普通前提、受测版本、安装/验证与常见故障处理，复用兼容共享Node；必要宿主兼容、启用/信任和实际参与仍核验。可选Setup界面、零Node自动准备及运行时打包不阻塞3.3发布，原元数据观察不晋功能验收。 / Explain ordinary prerequisites, tested versions, installation checks and common failures; reuse compatible shared Node. Preserve necessary host compatibility, enablement/trust and participation checks. Optional Setup UI, automatic zero-Node preparation and runtime packaging do not block3.3; metadata remains a limited observation.
- [ ] 保留“无需额外部署专用决策模型”与“宿主条件和费用仍适用”的区别；无比较证据时不承诺省时、省钱或更可靠。 / Distinguish no additional dedicated decision-model deployment from the host's continuing requirements and fees; make no unproven time, cost or reliability claims.
- [ ] 发布前核对已有适用授权及其条件，只发布获准的精确候选，并核对公开结果；资料不足不等于授权必然不存在，也不自动要求重复授权。 / Before publication, check applicable existing authorization and its conditions, publish only the authorized exact candidate and verify the public result; missing supplied evidence does not itself establish absence of authority or require renewed authorization.

以上待办服务于本次首次使用说明及既定发布工作，不新增迁移、安装、发布或对外发帖授权。
This checklist serves first-use copy and the existing release work; it grants no migration, installation, publication or posting authority.

## 启用与未启用对照准备

2026-10-29：本节承接用户确认的 README 与传播方向。用户随后同意建立对照初版，并要求软件工程评价与有限重塑作为后续主线；具体任务、判分校准、记录口径与限制见[评价初版](../../research/evaluations/accord-toggle-v1.md)。**当前为材料和方法校准，尚未运行真实双组对照或形成收益结论**。版本发布、功能验收、CI、安装和增量价值分别判断；不预设正收益，也不为传播挑选弱基线。

目标：在相同可用条件下，比较启用与未启用 Accord 对完整交付、变化处理、恢复、用户负担及总成本的实际影响。必要自动化与质量保持，合理额外开销不等于失败。

| 配对前冻结的条件 | 执行与记录要求 |
|---|---|
| 版本与入口 | 绑定宿主、后端、OS、插件包和精确版本/摘要。只切换目标作用域内 Accord 的启用状态，不用全局禁插件开关顺便移除其它能力。核对当前入口的实际 Hook 支持。 |
| 模型与工具 | 两组保有相同的主模型/推理选择、可用子模型、原生和第三方工具、权限及资源上限。保留各组获准调度与恢复能力，记录实际选择、并发和切换，不能强制对照组走较弱路线。 |
| 指令、记忆与材料 | 两组用新会话、相同中立目录和材料快照。核对实际生效的用户/项目指令、记忆、已加载 Skill 和状态。当前产品仓库本身含 Accord 指导，不直接拿来作为未启用基线；禁用或卸载不能清除已经进入上下文的指导。 |
| 输入与人工介入 | 用相同初始需求、预定变化和恢复输入；运行前冻结救援规则。分别记录必要授权/本人动作与可避免的催促、纠错和救场，不给任一组隐藏辅导，也不抹去安装与首次信任成本。 |
| 判据与成本 | 先核可独立检查的成品、原件保护、要求完整性和真实效果，再报告人工次数/时间、端到端时间、模型/工具用量、冷/热加载、缓存、并发及退出成本。不可取得的字段保留未知；账户配额不是本任务费用。 |

首轮可选三类同材料、同交付要求的真实任务；具体材料、预算、触发节点、重复次数和判据在实际派发前冻结，不由下表自动授予执行或新增费用：

| 类别 | 真实触发 | 主要核验 |
|---|---|---|
| 中途需求变化 | 到预定工作节点后追加影响已有输出的一项要求 | 是否修正受影响成果，同时保住原件、其它要求及有效工作；实际人工介入。 |
| 中断与续作 | 在相同语义节点中断，沿双方共同支持的原生路线恢复 | 目标、暂停、授权和未完工作是否准确继承；先核既有实际效果与写者，避免重复动作，核最终完整性和恢复成本。 |
| 简单任务基线 | 一次输入即可完成的低风险转换或小修改，不刻意制造故障 | 正确成品、响应速度、额外流程、用户负担与总成本；保留无增益或退化。 |

试行建议每类两个独立配对，交换两组先后顺序，共十二次运行；此为有限场景观察的起点，不是统计功效计算、统计显著性、全任务收益或所有入口的证明。先校准任务和判分，再按目标问题、材料覆盖及实际变异冻结样本；两个材料变体不等于同任务的独立重复。任务提示不预先点名 Accord 或其 Skill。运行中上游、模型、权限或配置漂移时停止相依配对，核清差异后另绑；保留原失败和已经发生的效果。

每次保留任务/材料摘要、实际配置、时间和用量、输入与介入时间线、输出和独立检查、资源退出及异常。完整私有记录与可公开脱敏报告分开。最终展示成对结果、全部试行的成功/失败/无差异和适用限制，不拼接不同实例作一条自主成功链；检查点、调用次数、录屏流畅或评分本身不作为净价值。README 只放可回查的摘要，完整报告和复现条件保持公开可发现；图示场景标明设计目标。

传播素材优先复用同一真实运行的录像、成品与报告，在 NEXUS 资产体系维护；不得把原始私人回执写入公开仓库。本节没有制作新视频、图片或向社媒发布，实际对外发布仍按对应授权核对。

### Comparison protocol in English

Status: **method and material calibration; no native paired trials or measured benefits yet**. The user authorized a [calibration kit](../../research/evaluations/accord-toggle-v1.md), software-engineering quality mapping and a roadmap centered on consolidation and bounded reshaping. Compare enabled and disabled Accord against the same required deliverable, quality and automation level. Version qualification, CI, installation and incremental value remain separate findings.

Before dispatch, freeze paired host/backend/package versions and hashes, OS, main model/effort, available submodels, native and external tools, permissions, resource limits and task materials. Toggle only Accord in the target scope, preserving other plugins and both groups' native scheduling/recovery capabilities. Record actual allocation rather than forcing identical tool paths. Check current entry and Hook support.

Use fresh sessions and equal neutral workspaces. Inspect effective user/project instructions, memory, loaded Skills and state; this product repository's Accord instructions would contaminate a disabled baseline. Disabling or uninstalling does not erase loaded context. Give both arms the same initial request, scheduled change and recovery input, with a rescue policy set in advance. Separate necessary authorization/personal actions from avoidable prompting, correction and rescue. Include setup and first-use trust costs; give neither arm hidden coaching.

Start with three task types: an added requirement affecting earlier output; interruption and native recovery at the same semantic milestone; and a simple one-prompt task without an artificial fault. Check the actual deliverable, complete requirements, protected originals, corrected effects, retained goals/pauses/authority, no duplicate actions and resource exit. Record human effort, full elapsed time, model/tool use, cold/warm loading, caching, concurrency and recovery/exit costs. Unknown costs stay unknown; account quota is not task cost. Reasonable overhead does not excuse missing automation or quality, nor imply failure by itself.

A possible pilot uses two independent pairs per type, counterbalancing order: twelve runs. This is not a power calculation; calibrate tasks and grading, then freeze the sample count from the question, task coverage and observed variability. Different material variants are not repeated trials of the same task. Freeze budget, milestones and criteria before execution. Such a pilot supports bounded observations, not statistical significance, all-task gains or cross-entry claims. Do not name Accord or its Skills in ordinary task prompts. Material upstream/model/configuration drift holds the affected pair for reconciliation; original failures and effects remain recorded.

Retain configuration, input/intervention timelines, outputs, independent checks, usage and cleanup for every run. Publish paired successes, failures, ties and regressions with limitations and reproducible conditions. Private raw records and public redacted reports are separate; do not splice episodes into one autonomous chain. Checkpoints, call counts, smooth video or scores alone are not value evidence. The README will carry a traceable summary; full reports remain discoverable. Reuse those same real runs for NEXUS communication assets, subject to separate publication authority. No new video, image or social post has been produced here.

## 演示与可复用素材

采用一条约60–90秒的真实任务录屏，脚本为待验证的拍摄意图：

1. 用户提出可核验的实际目标，展示源材料及初始限制。
2. 用户补充或改变条件，Agent解释影响并继续必要工作。
3. 仅在正式支持且自然需要时展示恢复或承接；保留实际边界和等待，不拼接不同试验冒充一条自主链。
4. 展示成品、独立检查、受保护材料和未完事项的最终处置。

封面和三张配图分别解释问题、实际协作过程、可核验结果及支持范围。优先从同一真实录屏提取，沿用README系统图；图示标明职责关系，不把设计图当执行证据。获准公开前排除凭据、私人对话和无关账号信息。尚未拍摄或制作图片、视频。

## 发布前待补齐的事实

| 内容 | 当前情况 | 完成条件 |
|---|---|---|
| 精确发行与更新日志 | 以当前接续和精确版本公开记录核对 | 验收、候选审查、已有适用发布授权及其条件、同版本公开后态成立 |
| README整体修订 | 入口分层由双语 README 与[用户指南](../user-guide.md)承接 | 每次改动按实际成品复核中英文定位、能力及限制、安装使用、图示与链接，不能仅沿用开发期文案 |
| 安装与使用入口 | 以3.3.4精确发行、当前支持入口、启用和首次 Hook 信任说明为基准 | 新用户能取得精确包，按真实支持条件完成安装和使用；市场收录不冒充必需前提，指南不代验每位用户的实际加载 |
| 演示及效果说明 | 已有局部试验，不是完整演示 | 同版本真实完整任务、可复验成品、参与边界及限制 |
| 发布页面 | 本文仅底稿 | 更新文案、缩略图、截图、视频、关联工具致谢和可用链接；在实际发布表单重新检查限制 |

2026-09-14用户提议增加知乎和Reddit，当前作为传播候选，尚未排期或发布。建议知乎以中文案例解释问题、设计取舍和适用边界；Reddit以英文演示、复现材料及具体问题征求社区反馈。优先复用同一真实成果并按平台改写；以项目为传播主体，明确作者关系，不将渠道数量或曝光作为产品质量。Reddit的[官方反垃圾信息规则](https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam)要求避免重复群发，并检查各社区具体规则；实际选定社区和发布前再核对。具体平台规则在实际发布前核对。渠道选择不改变项目优先、版本验收及正式对外提交的原有边界。
