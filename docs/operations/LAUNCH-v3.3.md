# 3.3 发布材料工作稿

状态：通用发布准备，未排期、未提交，3.3尚未完成验收或正式发布。本文复用[共识计划](PLAN-v3.3.md)的W08/S5，不新增产品验收或发布日期。

## 文案底稿

以下表达产品定位和设计目标；正式发布前须按精确版本的验收结果校准，不能直接作为已实现能力声明。

| 字段 | 英文稿 | 中文含义 |
|---|---|---|
| 产品名 | YIYUAN Accord | 项目统一名称 |
| Tagline | Keep human-AI work aligned from intent to delivery | 让人与AI的协作从意图到交付保持一致 |
| Description | An open-source collaboration reliability system for AI agents. Designed to preserve goals, handle changes, coordinate capabilities, and verify delivery throughout ongoing work. | 面向AI Agent的开源协作可靠性系统，旨在持续工作中承接目标、处理变化、协调能力并核验交付。 |

项目发布说明底稿：

> We started YIYUAN Accord after repeated collaboration failures: an interruption could displace the original goal, a handoff could lose constraints, and passing checks could still leave the actual job unfinished.
>
> The project explores how agents can carry those responsibilities through real work, combining host capabilities with scoped coordination and verification. Users keep control over their decisions and changes of direction.
>
> The project remains independent and vendor-neutral. For the release, we will show the exact supported environment, a reproducible task, the verified outcome, and the remaining limitations.

正式稿须填入已验版本、实际使用入口和演示链接，并按实际成品校准能力与限制。涉及工具或模型的致谢须据实说明其作用，不能声称全部历史由同一模型构建。

## 首次使用者说明与发布字段草案

以下中英介绍、结构字段和检查清单面向非技术首次使用者。它们已经过开发期核对与修订，仍须在发布前按精确版本和实际验收结果更新；不构成支持、效果、安装或发布承诺。 素材绑定01397fbe的2026-09-24快照；其中开发构建号仅标识该快照，不能用作当前源包或安装身份。

## YIYUAN Accord 3.3：让 Agent 协调协作（草案）

> **草案，非正式发行说明。** 3.3仍在开发，尚未完成验收或发布；目前没有可供常规安装的已接受3.3发行版。素材快照中的 Codex 开发包标识为 `3.3.0-dev.1+codex.20260924001947`，不代表正式发行版本。

### 你可以怎样开始

你不需要先学习插件、命令或模型设置。用日常语言告诉 Agent 你想达成什么结果；可以补充背景、限制、你在意的事项，以及希望怎样确认事情做完。例如：“请把这些材料整理成一份我能发给团队的简明说明，保留原文，并告诉我哪些内容还不能确定。”这只是表达目标的示例，不是特定功能或结果的保证。

### Agent 怎样协调工作

Accord 的设计目标是让 Agent 从理解目标开始，判断是否可行和还缺什么条件，在获准范围内选择、组合宿主已有能力与 Accord 组件，随着情况变化调整做法，并检查实际结果。若条件不足或影响先前判断，Agent 应说明、修正受影响的工作，并保留尚未完成的事项以便继续。用户不必预先掌握工具协调、配置或任务交接。

3.3当前聚焦 OpenAI 执行环境中具有实际交付价值、并有条件承担必要协作职责的入口；当前开发包是 Codex 适配。适不适用要看具体宿主和实际验收，不能只凭它在网页还是云端运行、能否安装插件或是否支持 Hook 来判断。普通 Chat 不是默认的独立交付项；Claude 不在3.3分发范围。这一阶段聚焦不改变项目的供应商中立定位。

### 哪些决定仍由你掌握

你决定要达成什么、是否改变方向，以及是否授权会产生实质影响的操作。Agent 应在授权范围内行动；需要你的判断、授权或本人操作时，应把具体事项交还给你。Agent 负责核验交付并纠正已发现的问题；你可以审阅和纠正结果，决定是否接受，而不必替 Agent 承担每一步检查。能力协调不会绕过宿主权限，也不意味着每一步都自动完成；自动交接仍在开发中。

### 条件、成本与尚待核实

3.3使用宿主已有模型、受支持工具和 Accord 组件，不要求额外部署专用第三方决策模型；宿主自身的要求和费用仍适用。协作介入可能增加上下文占用、等待时间、计算成本、指令冲突或维护负担。现有材料没有证明它一定能省时、省钱或提高可靠性，也没有证明所有入口都能完成上述工作。

3.3仍在开发，尚未完成验收或发布，因此这里描述的是设计方向和当前范围，不是已验证的普遍效果。具体入口的支持情况、实际行为、安装使用方式、发布时间及效果仍待核实。本文是介绍草案，不是安装指南或发布日期通知。

## YIYUAN Accord 3.3: letting an Agent coordinate the work (draft)

> **Draft, not an official release note.** Version 3.3 is in development and has not completed acceptance or publication. There is currently no accepted 3.3 release for normal installation. The Codex development package in the source snapshot is identified as `3.3.0-dev.1+codex.20260924001947`; this is not an official release version.

### How to get started

You do not need to learn plugins, commands, or model settings first. Tell the Agent in everyday language what outcome you want. You can add background, constraints, what matters to you, and how you would like the result checked. For example: “Please turn these materials into a concise note I can share with my team, preserve the original text, and tell me what is still uncertain.” This illustrates how to state a goal; it is not a promise of a particular feature or result.

### How the Agent coordinates the work

Accord is designed to have the Agent start by understanding the goal, assess feasibility and missing conditions, choose and combine host capabilities and Accord components within its authorization, adapt as circumstances change, and check the actual result. If conditions are missing or earlier judgments are affected, the Agent should explain and correct the affected work, while preserving unfinished items for continuation. Users need not first learn tool coordination, configuration, or task handoff.

The current 3.3 focus is OpenAI execution environments with practical delivery value and a feasible way to fulfill necessary collaboration duties. The current development package is the Codex adaptation. Suitability depends on the specific host and actual acceptance; it cannot be determined just by whether the environment is web-based or cloud-based, supports plugin installation, or supports Hooks. Ordinary Chat is not a default standalone deliverable, and Claude is outside the 3.3 distribution scope. This phase focus does not change the project's vendor-neutral position.

### Decisions that remain yours

You decide what outcome you want, whether to change direction, and whether to authorize actions with material consequences. The Agent should act within its authorization and bring specific decisions, permissions, or actions back to you when needed. The Agent is responsible for checking its deliverables and correcting identified problems. You can review and challenge the result and decide whether to accept it, without taking over every verification step. Coordinating capabilities does not bypass host permissions or mean every step happens automatically; automatic handoff remains in development.

### Conditions, costs, and what remains unverified

Version 3.3 uses host-provided models, supported tools, and Accord components; it does not require deploying an additional dedicated third-party decision model. Normal host requirements and costs still apply. Coordination may add context use, waiting time, compute cost, instruction conflicts, or maintenance burden. The available materials do not prove that it will save time or money, improve reliability, or complete the described work across all entry points.

Version 3.3 remains in development and has not completed acceptance or publication. This description therefore covers design intent and current scope, not verified universal results. Support for specific entry points, actual behavior, installation and use, publication timing, and effects remain to be verified. This is an introductory draft, not installation guidance or a date announcement.

### 结构字段 / Structured fields

```json
{
  "audience": "People encountering YIYUAN Accord for the first time, including readers without a technical background.",
  "stage": "Draft only; 3.3 is in development and has not completed acceptance or publication. There is no accepted 3.3 release for normal installation.",
  "productName": "YIYUAN Accord",
  "version": {
    "release": "3.3 (development; not an accepted release)",
    "note": "Package identity from source snapshot 01397fbe; not a current installation or official release identity.",
    "developmentPackageSnapshot": "3.3.0-dev.1+codex.20260924001947"
  },
  "scope": {
    "purpose": "Designed to help an Agent understand a goal, assess feasibility and missing conditions, coordinate available host capabilities and Accord components within authorization, adapt to changes, check results, correct affected work, and preserve unfinished items.",
    "howToStart": "State the desired outcome in everyday language; optionally add background, constraints, priorities, and how to check the result. No technical setup knowledge is assumed in this introductory explanation.",
    "userDecisions": "The user retains decisions about the desired outcome, changes of direction, authorizations with material consequences, and acceptance. The Agent owns verification and correction; users may inspect and challenge outputs without taking over each verification step.",
    "focus": "OpenAI execution environments with practical delivery value and a feasible way to fulfill necessary collaboration duties; the current development package provides the Codex adaptation.",
    "limits": [
      "These are design aims, not accepted results across all entry points.",
      "Suitability depends on the specific host and actual acceptance; web or cloud location, plugin installation, or Hook support alone does not establish it.",
      "Ordinary Chat is not a default standalone deliverable.",
      "Claude is outside the 3.3 distribution scope.",
      "Agent actions remain within authorization and host permissions; automatic handoff remains in development."
    ]
  },
  "verification": {
    "status": "3.3 acceptance is unfinished; support claims require a suitability decision and actual acceptance.",
    "unverified": [
      "Support and actual behavior for specific entry points",
      "User installation and use instructions",
      "Publication timing",
      "Effects on time, cost, reliability, and task completion"
    ],
    "note": "Do not infer universal behavior or user instructions from the development package identifier or maintainer checks."
  },
  "cost": "Uses host-provided models, supported tools, and Accord components; no additional dedicated third-party decision model is required. Normal host requirements and costs apply. Coordination may add context use, waiting time, compute cost, instruction conflicts, or maintenance burden. No time, cost, or reliability improvement is verified.",
  "publication": "3.3 has not been published. Check the applicable existing human authorization and all its conditions before any publication; this draft does not establish readiness, a publication date, or installation guidance.",
  "languages": [
    "zh-CN",
    "en"
  ]
}
```

## 首次使用者发布准备清单 / First-use release checklist

这些项目尚未由本草案完成。3.3仍在开发、未完整验收、未发布；文稿面向首次接触且没有技术背景的用户，不提供旧版迁移操作。
These items remain open. Version 3.3 is in development, acceptance and publication are unfinished. The copy serves first-time, nontechnical users and includes no migration procedure.

- [ ] 按精确候选完成必要功能、入口适用性、生命周期、系统影响、独立审查和托管检查；区分设计方向与已验事实。 / Complete the required function, entry suitability, lifecycle, system-impact, independent-review and hosted checks for the exact candidate; separate design aims from demonstrated facts.
- [ ] 用自然语言目标示例解释开始方式；核实真实安装与使用入口后再补操作说明，不编造按钮、命令、支持范围或时间。 / Explain how to start with an ordinary goal; add setup instructions only after verifying the actual installation and use entry, without inventing controls, commands, support or dates.
- [ ] 保持职责清晰：Agent核验和纠正交付，用户保留目标、方向、必要授权和接受结果的决定；不把每一步检查退回用户。 / Keep responsibility clear: the Agent verifies and corrects delivery; users retain goals, direction, necessary authorization and acceptance, without taking over every check.
- [ ] 同步核对中文稿、英文稿、结构字段、README与清单的受众、用途、阶段、范围、费用和未决事项；未验入口不写成已支持。 / Reconcile audience, purpose, status, scope, cost and unresolved items across both languages, structured fields, README and this checklist; do not present unverified entries as supported.
- [ ] 根据实际使用条件写明运行环境与权限要求，保留已有设置、组件及用户选择。 / Explain evidenced runtime and permission prerequisites while preserving existing settings, components and user choices.
- [ ] 保留“无需额外部署专用决策模型”与“宿主条件和费用仍适用”的区别；无比较证据时不承诺省时、省钱或更可靠。 / Distinguish no additional dedicated decision-model deployment from the host's continuing requirements and fees; make no unproven time, cost or reliability claims.
- [ ] 发布前核对已有适用授权及其条件，只发布获准的精确候选，并核对公开结果；资料不足不等于授权必然不存在，也不自动要求重复授权。 / Before publication, check applicable existing authorization and its conditions, publish only the authorized exact candidate and verify the public result; missing supplied evidence does not itself establish absence of authority or require renewed authorization.

以上待办服务于本次首次使用说明及既定发布工作，不新增迁移、安装、发布或对外发帖授权。
This checklist serves first-use copy and the existing release work; it grants no migration, installation, publication or posting authority.

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
| 精确发行与更新日志 | 3.3开发中 | 验收、候选审查、正式发布授权及同版本公开后态成立 |
| README整体修订 | 用户已授权按最新共识按需更新，发布前仍需整体校准 | 发布前按实际成品整体复核中英文定位、能力及限制、安装使用、示例、徽章与链接，不能仅沿用开发期文案 |
| 安装与使用入口 | 待正式版本绑定 | 新用户能取得精确包，按真实支持条件完成安装和使用；市场收录不冒充必需前提 |
| 演示及效果说明 | 已有局部试验，不是完整演示 | 同版本真实完整任务、可复验成品、参与边界及限制 |
| 发布页面 | 本文仅底稿 | 更新文案、缩略图、截图、视频、关联工具致谢和可用链接；在实际发布表单重新检查限制 |

2026-09-14用户提议增加知乎和Reddit，当前作为传播候选，尚未排期或发布。建议知乎以中文案例解释问题、设计取舍和适用边界；Reddit以英文演示、复现材料及具体问题征求社区反馈。优先复用同一真实成果并按平台改写；以项目为传播主体，明确作者关系，不将渠道数量或曝光作为产品质量。Reddit的[官方反垃圾信息规则](https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam)要求避免重复群发，并检查各社区具体规则；实际选定社区和发布前再核对。具体平台规则在实际发布前核对。渠道选择不改变项目优先、版本验收及正式对外提交的原有边界。
