# YIYUAN Accord

<p align="center">
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/yiheng8023/YIYUAN-Accord/validate.yml?branch=main&amp;label=CI&amp;logo=github" alt="CI 状态"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/releases/latest"><img src="https://img.shields.io/github/v/release/yiheng8023/YIYUAN-Accord?color=blue&amp;label=Release" alt="最新发布版本"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/stargazers"><img src="https://img.shields.io/github/stars/yiheng8023/YIYUAN-Accord?style=flat&amp;logo=github&amp;color=ffaa00" alt="GitHub Stars"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/network/members"><img src="https://img.shields.io/github/forks/yiheng8023/YIYUAN-Accord?style=flat&amp;logo=github&amp;color=grey" alt="GitHub Forks"></a>
  <img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10 至 3.14 CI">
  <img src="https://img.shields.io/badge/CI-Ubuntu%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Ubuntu、Windows 与 macOS CI">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/yiheng8023/YIYUAN-Accord?color=green" alt="Apache-2.0 许可证"></a>
</p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a> | <a href="README.md">English</a>
</p>

一份轻量协作契约：把用户想要的结果推进到可验证、可恢复的闭环，同时不让用户管理 Agent 的工具、对话切换或内部工序。

YIYUAN Accord 是一个开放、Agent 中立的人机协作系统。

它要求 Agent 始终围绕当前目标，在工作变化时动态调整，并以与结论相称的证据、明确的未知和受控清理完成收尾。

它可以使用不同宿主与机制。具体工具只是路线的一部分，不是产品本身。

项目的广义使命是改善人与 AI 的协作；当前产品面与证据严格限定为人与 Agent 的协作场景。

> **当前发布版本线：** [`v3.1.0`](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.1.0)，精确、非预发行、无附加资产，且项目治理要求不得移动或改写。
>
> GitHub 仍是发布事实的权威来源；本仓库只记录已观察到的 Release，不声称仓库文本能够自证发布。
>
> 不要从持续移动的 `main` checkout 安装。

| 我想…… | 从这里开始 |
| --- | --- |
| 使用 Accord | [30 秒开始](#30-秒开始) |
| 理解或评估它 | [它改变什么](#它改变什么)与[发布状态、证据与能力边界](#发布状态证据与能力边界) |
| 开发或维护它 | [开发者与维护者](#开发者与维护者) |

---

## 这是什么

Accord 帮助 Agent 始终围绕用户当前要的结果，选择最小充分路线，保留人的决定权，并以证据而不是流程仪式完成收尾。

它不是提示词模板、万能 Runtime、控制平面、能力目录，也不声称每个 Agent 和宿主都能可靠工作。

它的便携内核只规定少数稳定协作约束；具体任务、宿主、证据、权限与生命周期条件决定其余行为。

Codex 与 Claude 是当前参考宿主，不是产品边界、永久依赖或享有特权的模型系列。

普通自然语言请求就足够了。用户不必先学习 Accord 的内部术语。

例如：

> 请把这个项目继续推进到可以发布。保留已有工作，核验实际结果；只有遇到真正需要我决定或授权的事情时再告诉我。

---

## 它改变什么

你只需用自然语言说明想要的结果。

Accord 要求 Agent 承担其能力范围内的工序，同时把后果性判断、新信任授予、成本承诺、公开发布和不可逆影响留给人类决定。

其可移植循环由五个稳定常量驱动：

1. **目标锚定**：从用户当前目标和即时纠正出发。
2. **最小路径**：选择真正能够交付结果的最小充分路线。
3. **决定权与权限保留**：只在继续推进需要新的人工判断或授权时停下。
4. **依赖校准**：新证据推翻旧证明后，从最早受影响的依赖边界重做校准。
5. **诚实收尾**：核对实际效果，说明未知，并清理可归因的临时残留。

其余因素由实际任务与宿主环境按需决定。

Accord 不要求 Agent 模仿人类或照搬人的执行方式。只要结果可靠、负担更低、证据诚实，就允许采用适合机器的执行路线。

如果宿主原生能力已经充分闭合责任，Accord 就应该保持安静。

---

## 适合什么情况

- **目标漂移**：任务产生大量看似合理的工作，却逐渐偏离用户真正要的结果。
- **长链中断**：长任务被暂停、纠正，或需要换一个对话载体继续。
- **伪绿灯陷阱**：测试、报告、提交或托管绿灯被误当成现实交付。
- **决策边界**：日常工序应继续，但新信任、成本、公开发布或不可逆影响必须由人决定。
- **级联纠偏**：需求变化或假设失败，使下游工作失效。
- **复杂收尾**：安装、验证、清理、公开状态和用户可见效果必须彼此区分。

Accord 不是每个任务都必须执行的固定流程。简单请求遇到健康直接路线时，应该继续保持简单。

它不替代专业领域知识，不给 Agent 自行扩权，不保证自动激活，也不把正式发布等同于生产安全。

---

## 30 秒开始

### 安装前确认

下列精确 tag 命令指向当前公开版本 `v3.1.0`。不得把这个 ref 换成持续移动的 `main`。

在具备相应能力的 Agent 宿主中，只需给出一次生命周期意图，例如：“从精确的 `VERSION_TAG` 安装 YIYUAN Accord，保留无关宿主状态，验证最终登记；遇到新的信任或权限边界时再停下询问。”下列命令块是透明的运维参考和人工后备路线，不要求用户逐个组装 Accord 的内部组件。

本文中的 GUI 标签是 **v3.0.1 最后验证的历史路径**，不是当前客户端入口声明。

后续客户端更新后，Codex、Claude 与 ChatGPT 的 GUI 入口都保持未知，直到在不改设置的前提下重新查看实际宿主。

执行 GUI 安装或生命周期操作前，应记录客户端、版本、可见入口和实际结果。v3.0.1 没有单独验证 ChatGPT GUI 安装路径。

已记录的 Codex 与 Claude 路线要求宿主支持插件、能够访问公开仓库、允许修改用户级插件状态、`node --version` 能在 `PATH` 中成功运行，并在安装后新建任务或会话。

期望 Hook 激活前，必须通过宿主支持的信任流程审查并信任这个非托管 Accord Hook。不得把 `bypass_hook_trust`、`bypassPermissions` 或直接改 settings 当作生产捷径。若当前宿主没有受支持的信任入口，Skill 仍可能可见，但 Hook 辅助连续性保持不可用且未经验证。

Accord 不绑定固定模型名称、型号、版本或提供商路线。模型身份与版本只是单次运行的来源记录，不是产品身份或路线权威。

### Codex

安装精确、不可变的 tag：

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.1.0
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

安装后先检查宿主报告的登记状态。安装或登记不能证明可见、激活或行为；检查新加载的可见性或行为前，应新建 CLI 任务或会话。Desktop 客户端必须另行完成当前宿主验证。

打开 **Plugins** 或运行 `/plugins`，确认 `YIYUAN Accord for Codex` 与 `deliver-demand-driven-outcome` 可见。

在当前客户端上重新确认之前，只能把这些标签和位置当作历史观察。

### Claude 客户端与 Claude Code

上次验证 v3.0.1 时，Claude Desktop Chat、Claude 网页聊天和 Cowork 使用 **Customize > Plugins**。

已记录的路线把 `https://github.com/yiheng8023/YIYUAN-Accord` 添加为个人 marketplace，安装 **YIYUAN Accord for Claude**，然后新建聊天。

客户端更新后，不得假设该路线、文案或位置仍然相同。

Claude Code 持久安装：

```powershell
claude plugin marketplace add "https://github.com/yiheng8023/YIYUAN-Accord.git#v3.1.0" --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
```

仓库根目录是 marketplace；插件包子目录不是。

仅用于一次开发会话时，在仓库根目录运行 `claude --plugin-dir ./plugins/yiyuan-accord-claude`。

在 `/help` 中确认 `/yiyuan-accord-claude:deliver-demand-driven-outcome`。checkout 变化后使用 `/reload-plugins`。

### 安装会改变什么

当前包提供一个渐进披露的动态适配 Skill、一个短时无状态的 `SessionStart` Hook 适配器和所需宿主 manifest。仓库另含一个无副作用纯内核参考实现；两个插件包都不会安装或调用它。

它们不新增常驻 Runtime、MCP server、App、状态存储、浏览器桥、SDK 客户端、后台进程或自动项目修改。

它们不会替换项目或用户的 `AGENTS.md`、`CLAUDE.md`、`config.toml` 或 settings 文件。

Hook 适配器不读取私密会话原文，不写持久状态，也不启动后台进程。

`startup` 与 `clear` 保持静默；受支持的 `compact` 与 `resume` 事件只提供非权威连续性提示。

这些提示必须先重新查看当前允许的状态，才能参与决策。

Hook 只能识别对话载体事件，不能理解任务语义：受支持的 `compact` 或 `resume` 即使发生在后续简单请求之前，也可能加入这段有界提示。它不读取对话正文，也不保存跨事件状态。简单路线在 `compact` 或 `resume` 后的干扰仍未经验证，因此明确披露，不能当作零干扰。

安装、启用和可见不等于激活。激活本身也不证明 Agent 已使用、执行完成、结果成立、独立证据充分或产生价值。

直接 App Server 客户端仍只是评价路线，不是新增安装态产品服务或第二 API。

---

## 确认生效

请把确认拆成五个不同问题：

1. **已安装**：宿主是否报告预期包和启用状态？
2. **来源已绑定**：是否登记了不可变 ref，已安装包字节是否匹配该精确 Release？
3. **可见**：当前宿主中是否出现预期 Skill 或插件？
4. **已激活**：相关宿主事件或任务是否实际调用它？
5. **有效果**：它是否帮助完成目标，并且没有不可接受的干扰或残留？

Codex 可先查看 `codex plugin list --json`，再在新任务中确认当前插件和 Skill 列表。该清单能确认安装/启用状态及其报告的版本和仓库，却不暴露不可变 marketplace ref 或 Git SHA，不能单独证明精确来源。

Claude Code 应同时查看 `claude plugin marketplace list --json` 与 `claude plugin list --json`，再在新会话中通过 `/help` 确认当前命令列表。清单报告了 ref 也不能取代已安装字节验证。

GUI 客户端应查看实际界面，不依赖其它版本的截图或标签。

确定性暴露检查可以显式选择 Skill；普通工作不应要求每次显式调用。

相关宿主可以隐式选择 Skill，而充分的原生路线应该保持安静。

可见性检查不是现场价值测试。请分别记录目标、初始状态、Agent 与人的动作、实际效果、残留和仍未知的环节。

---

## 它如何工作

最简协作循环是：

`目标 → 最小路线 → 权限边界 → 依赖校准 → 验证与清理`

结果始终绑定用户最新纠正。宿主事实、证据、权限、成本、失败或生命周期状态变化时，路线可以变化。

一次纠正只重新打开最早受影响的依赖及其下游工作，不要求重做无关证明。

闭环需要在行动本应产生影响的位置看到具体效果。计划、测试、报告、回执、提交或托管绿灯可以支持结果，但不会自动成为结果。

### 动态责任分配

Accord 不受 Codex、Claude 或任何具体 Agent 能力面的限制。

每项责任可以由 Accord 内化、Agent 原生或 Accord-Agent 组合完成；一条路线可以混用三种模式。

插件名称、机制大类或整任务标签不能代替逐责任分配。

Skill、插件、App、MCP、Hook、配置、状态、Runtime、云端载体和未来机制，既不是必选项，也不是永久禁区。

只有某个机制能在当前权限、证据、干扰、成本、恢复与退役边界内闭合责任时，才应准入。

研究遵循同一规则。

新鲜、充分的证据不增加研究步骤。会改变路线的物质未知，才可能需要官方文档、源仓库、论文、宿主原生事实或公共线索。

公共线索可以开启调查或提供反例，但不能单独支撑有后果的结论。

便携内核不新增强制研究 API、账号连接、常驻服务、提供商绑定或默认联网搜索。

### 状态与证据

Accord 优先使用受支持、当前且结构化的宿主状态，而不是猜测。

它只规范化当前结果所需字段，不重建第二套完整宿主能力权威库。

冲突、过期、缺少绑定或未暴露的事实继续保持未知。

机器字段、API/CLI 操作名和官方英文原词承载规范语义；中文译名只用于显示解释，不作为机器 alias 接受。branch 不等于 fork，scheduled automation 不等于 plan step，task/thread/chat/conversation 必须结合对象与生命周期判断，approval policy 也不同于 sandbox access。

共享状态、观察或上下文注入，不证明 Agent 已经使用信息或产生预期效果。

### 连续性与拓扑

对话、任务、会话、Git 分支、worktree、repository fork 与本地或云端执行位置是不同关系。

换一个对话不会静默移动代码或 Git 状态。

顺序交接必须先验证目标载体，再释放来源；复制历史的对话分叉只用于真实因果分支，不用于普通接续。

### 阶段规划

复杂项目的基线、计划、工序、验收标准和目标投影是版本化阶段视图，不是永久真理。

阶段收官形成可引用快照，绑定相关项目视图、证据、有限声明、未知与失效触发器。

未来规划按需从项目全景、最新已接受快照和新鲜环境事实重新派生。

它可以覆盖维护、迭代、更新、有限重构、宿主适配、退役、替换和后续开发，但不会自动变成长期路线图。

项目把这个更完整的循环称为**完整、有界的自举能力**。

它表示感知当前条件，复用或建立最小授权路线，验证结果，并在明确证据与权限边界内治理纠偏或退役。

从“借助宿主完成自举”的视角看，该循环包含八类责任：自知、自洽、有界自治、按需自学、自纠、自愈、外部可证与受治理自进化。

它们不是八个内置模块，也不表示 Accord 要脱离宿主独立运行。Accord 驱动上游 AI Agent、宿主原生能力与生态。

只有充分可复用路线被证据否定后，才补最小、可替换缺口。

每项实质责任由 Accord 内化、Agent 原生完成，或由两者组合完成。“自证”只能表示为独立复核准备有来源的证据，不能由项目自行证明自己正确、有价值或已发布。

v3.1.0 公开声明上限仍是下文五项有限结论；不声称长期自主学习、万能自愈或持续复利式自进化。

### 资源治理

Accord 把资源视为动态路线变量。

它区分所有者和状态，只使用完成结果所需的最小并发与预算，并且只释放任务专属资源。

共享资源和所有权未知的资源必须保留。

宿主原生限额、中断、清理和回收机制健康、充分时，应优先复用。

清理命令不是清理证明。闭环要核验清理后的状态，并报告无法安全移除的残留。

Accord 不会静默收集或上传遥测数据。

完整的便携接口、宿主准入、证据、资源、复杂度和演进模型见 [`docs/architecture.md`](docs/architecture.md)。

---

## 发布状态、证据与能力边界

精确、非预发行、无附加资产的 `v3.1.0` GitHub Release 已于
2026-09-03 从精确 revision
[`258611be47c47a884b6d1a2e96889cf688ca7e68`](https://github.com/yiheng8023/YIYUAN-Accord/commit/258611be47c47a884b6d1a2e96889cf688ca7e68)
发布，现为公开推荐版本；项目治理要求不得移动或改写该 tag 与 Release。
这是对 GitHub 任务时实时观察的派生记录；仓库文本、
测试、本地 tag 或候选记录都不能自证这个外部事实。

项目正式版只对精确仓库、包、声明的有限结论与已完成发布门负责。

它不证明普遍行为、生产安全、所有用途适用性，也不证明所有 Agent、操作系统和客户端界面兼容。

精确公开声明上限包含五项有限结论：

- v3.1.0 的上下文自适应协作闭环一致性；
- 当前 Codex 与 Claude 投影的静态包一致性；
- 一项有界、单臂的协作闭环内部实践结果；
- 针对连续性、修复与资源治理的本地回归重放结果；
- 从干净 v3.1.0 checkout 复现结果的能力。

另有仓库证据支持无副作用参考内核和下述有界宿主场景，但它们不扩大上述五项公开声明。

有界宿主证据只覆盖一条事件到结果路线、一条保持静默的充分路线、一次已验证的新对话交接，以及一次性非空 Windows Codex 与 Claude 重放中的生命周期事实。精确审查切点 `c5a0668` 否定了宽泛 GT-20 结论；精确 `7a3950e` 保留纠正后的 schema-v6 零模型原生生命周期、可重算暂存和路径隐私机制事实。精确 `f4c0251` 与已采纳的 schema-v7 v5 记录验证了一次隔离 Codex Agent 决策及评估器介导的有界补偿。候选身份只由机器生命周期状态和精确的任务时评审包决定：active/reopened 投影没有候选；原始派生表面不变、ready/closed、八项标准全部 verified 且精确评审包通过时，才选定该精确 SHA。两种状态都不证明宿主自动、原地或崩溃原子回滚、Claude Agent 等价、当前客户端行为、跨系统等价、产品价值或任何后续发布门。

已观察的 `bypass_hook_trust` / `bypassPermissions` 路线只是测试控制，不是生产信任路线。

失败、部分完成和已被替代的尝试继续作为反证保留，而不是被改写成成功。

历史 Claude GT-07 清理失败不纳入保留的行为声明。

当前未知包括生产信任、一次性会话测试之外的 Claude Hook 现场激活、更新后客端 GUI 兼容性，以及非受管或跨 OS 行为。

广泛跨宿主行为、群体价值与评价条件之外的行为也继续保持未知。

安装证据不会自动转移为激活或效果证据。

历史行为证据也不会自动转移到发生变化的字节、包、Skill、Hook 或宿主投影。

完整 SHA、Golden Task、审查、失败和实验历史见 [`docs/releases/v3.1.0.md`](docs/releases/v3.1.0.md)。

架构与证据语义见 [`docs/architecture.md`](docs/architecture.md)。

当前仓库状态、下一门槛和接续方式见 [`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md)。

精确的有限验收合同见 [`product/acceptance.json`](product/acceptance.json)。

---

## 更新、回滚、移除与源码验证

下列 GUI 生命周期标签仍是历史观察。依赖任何菜单、标签或动作前，先查看当前客户端。

请通过执行安装的同一入口确认生命周期状态。

优先路线是每次更新、回滚或移除只由用户给出一次意图，由 Agent 查看当前宿主、把受支持的原生生命周期作为一个有界操作执行，保留外来状态、核验最终状态，并只在真正出现新信任或权限决定时返回。下列命令用于审计和人工恢复，不把内部组件顺序转嫁给用户。

上次验证 v3.0.1 时，使用过 `codex plugin list --json`、`claude plugin list --json` 与 **Customize > Plugins**。

不同视图显示不同，是应记录的宿主事实，不自动证明另一处安装失败。

不可变 ref 不会自动前进。

Codex 更新或回滚时，先移除已安装包和 marketplace，再安装目标精确 tag：

```powershell
codex plugin remove yiyuan-accord-codex@yiyuan-accord
codex plugin marketplace remove yiyuan-accord
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref VERSION_TAG
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

只移除这条路线安装的 Codex 投影时，执行前两条命令后停止，并确认插件与 marketplace 登记都已不存在。

更改 Claude Code 前，先通过列表命令确认这个用户级登记确实属于上述路线。若无法安全区分不同 scope 的同名状态，应停止并报告这个适配缺口。

Claude Code 更新或回滚时，先移除当前用户级包和 marketplace，再登记并安装目标精确 tag：

```powershell
claude plugin uninstall yiyuan-accord-claude@yiyuan-accord --scope user
claude plugin marketplace remove yiyuan-accord --scope user
claude plugin marketplace add "https://github.com/yiheng8023/YIYUAN-Accord.git#VERSION_TAG" --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
```

只移除这条用户级路线安装的 Claude Code 投影时，执行前两条命令后停止，并确认该 scope 中的插件与 marketplace 登记都已不存在。

只有确认当前 GUI 路线仍存在后，才使用对应的 **Customize > Plugins** 操作。

优先使用宿主支持的原生重载和生命周期操作。

这些精确 ref 命令执行的是显式替换，不是原子就地更新。应先记录旧精确 tag；若目标安装失败，重新安装该 tag，验证健康状态，并报告未激活时段。

当前 schema-v7 v5 回放只覆盖可变本地 marketplace 评估机制，不验证这条公开 immutable-ref 卸载/重装路线，也不声称原子热更新。

生命周期命令可以刷新安装文件，但不会替换当前任务或会话已经加载的能力。判断新版本前必须新建任务或会话；自报版本、`/reload-plugins` 或缓存变化本身都不是已加载行为完成热更新的证据。

仅观察到 Desktop 版本并不能验证新任务可见性、激活或后状态。仓库目前只保留上文所述的有限 CLI 观察；它们不能证明一般性的 CLI 支持，也不能推出任何 Desktop 行为结论。如需 Desktop 安装或热替换，必须另行取得当前宿主行为证据与授权。

不得移动已有 tag，也不得直接编辑全局宿主配置来代替受支持的生命周期命令。

移除必须保留既有用户配置、并发用户修改、共享状态和外来插件。

宿主所有的惰性缓存不是 Accord 活动状态，但也不能称为物理零残留。

不得绕开宿主生命周期删除受其有界清理合同约束的缓存。

### 源码验证

请使用具备所需标准库能力的 Python 解释器验证精确源码 checkout：

```powershell
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

当前 Release CI 覆盖 CPython 3.10–3.14。

类 Unix 环境若只提供 `python3`，只需把上述命令的启动器替换为 `python3`；Accord 不要求额外创建 `python` 别名。Release 工作流会显式配置 Node.js 24 来测试打包 Hook，不依赖 runner 镜像碰巧自带的版本。

该矩阵只是当前兼容性证据，不是永久版本白名单，也不是 Accord 产品身份的一部分。

这些检查验证仓库与包的确定性一致性。

它们不会安装插件、证明激活、建立现场价值、授予发布权限、证明公开发布或证明生产安全。

---

## 开发者与维护者

当前 schema-v3 权威集合是：

- [`product/constitution.json`](product/constitution.json)
- [`product/program.json`](product/program.json)
- [`product/acceptance.json`](product/acceptance.json)

已接受、可修订的重塑与动态索引指导在 [`product/reshaping-guidance.json`](product/reshaping-guidance.json)。

[`CONTEXT.md`](CONTEXT.md) 是派生术语表，只解释概念，不增加语义权威。

通用验证器是 [`yiyuan_accord/control.py`](yiyuan_accord/control.py)。

帮助与干扰代表任务在 [`evals/golden-tasks.json`](evals/golden-tasks.json)。

Codex 与 Claude 包共享 `deliver-demand-driven-outcome` Skill 名，同时保留各自宿主 manifest。

详细发布证据在 [`docs/releases/v3.1.0.md`](docs/releases/v3.1.0.md)。

架构与信任边界在 [`docs/architecture.md`](docs/architecture.md)。

当前接续与门槛顺序在 [`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md)。

维护与贡献规则在 [`CONTRIBUTING.md`](CONTRIBUTING.md)，安全报告入口在 [`SECURITY.md`](SECURITY.md)。

发布依次经过精确本地验证、独立审查、同 revision 推送、托管检查、具名真人授权、不可变 tag 与 Release、公开复核和清理。

这些阶段彼此独立；一项通过不会替另一项制造证据。

请通过 [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues) 报告问题。

请提供精确 tag 与 revision、宿主与版本、安装路线、目标、初始状态、实际结果、人工介入、物质影响、残留和未知。

不得提交凭据、私密会话原文或未净化的宿主日志。

---

## 愿景与共创

易元联创（YIYUAN NEXUS）将持续探索人机协作及其相关领域。YIYUAN Accord 并不以永久存在为目标：它会随前沿智能、人类与机器能力及协作方式的变化而演进。前沿智能的进步既为 Accord 提供新的能力，也持续检验其必要性、边界与实际价值；当使命已经完成、被更好的机制承接，或不再需要时，项目也应能够负责任地有序谢幕。

易元联创目前仅有一名作者兼维护者，能力、精力和资源有限。我们期待与社区联合创作、协同前行。在现实能力与资源边界内，Accord 将持续维护和演进，逐步增加更多宿主适配。路线方向不代表当前已经支持，也不构成发布时间或兼容性承诺。

参与方式见 [`CONTRIBUTING.md`](CONTRIBUTING.md)；问题与建议可通过 [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues) 提交。

---

## 社区

### 贡献者

诚挚感谢所有贡献代码、评审、文档、问题报告与证据的参与者。

<p align="center">
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=yiheng8023/YIYUAN-Accord" alt="YIYUAN Accord 贡献者">
  </a>
</p>

### Star 增长趋势

[![YIYUAN Accord Star History](https://api.star-history.com/svg?repos=yiheng8023/YIYUAN-Accord&type=Date)](https://star-history.com/#yiheng8023/YIYUAN-Accord&Date)

---

## 项目支持与法律

### 项目与许可

公开项目与网站是 [github.com/yiheng8023/YIYUAN-Accord](https://github.com/yiheng8023/YIYUAN-Accord)。

发布者是 [yiheng8023](https://github.com/yiheng8023)。

YIYUAN Accord 采用 Apache-2.0 许可证。

该许可证允许商用、修改与再分发，但不允许把修改版或再分发版冒充为官方版本，或暗示其受到官方赞助与背书。

本仓库是规范公开来源；官方版本由相互匹配的 Git tag 与 GitHub Release 记录识别。独立安装后，Codex 与 Claude 插件包内也会保留各自的 `LICENSE` 与 `NOTICE`。

YIYUAN Accord、YIYUAN NEXUS 名称与图形商标保持独立，详见 [`NOTICE`](NOTICE)、[`docs/license-policy.md`](docs/license-policy.md) 与 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

社区支持按 [`SUPPORT.md`](SUPPORT.md) 所述尽力提供。

### 自愿赞助与支持

赞助完全自愿。

赞助不购买支持 SLA、处理优先级、发布权限、安全保证、治理例外、功能承诺或对技术决策的影响力。

如果 Accord 对你有所帮助，可以通过仓库所有者的[公开 PayPal 页面](https://www.paypal.com/ncp/payment/LNTF8KXGJXMZY)支持维护。

<table>
  <tr>
    <th width="300">微信支付（人民币）</th>
    <th width="300">支付宝（人民币）</th>
  </tr>
  <tr>
    <td align="center" valign="middle" width="300" height="430"><img src="docs/assets/sponsoring/wechat-pay.png" alt="微信支付自愿赞助收款码" width="260"></td>
    <td align="center" valign="middle" width="300" height="430"><img src="docs/assets/sponsoring/alipay.png" alt="支付宝自愿赞助收款码" width="260"></td>
  </tr>
</table>

付款前请核对收款方。完整条款见 [`SPONSORING.zh-CN.md`](SPONSORING.zh-CN.md)。

### 免责声明与合规说明

YIYUAN Accord 是独立的社区开源项目。

它不是 OpenAI、Anthropic、Codex、Claude、Claude Code 或 GitHub 的产品，也不代表这些组织的赞助或背书。

第三方名称与商标归各自权利人所有。

用户仍需审查 Agent 输出，并遵守适用法律、合同、宿主条款、许可证和组织政策。

本软件按 Apache-2.0 许可证以“原样”方式提供，不附带任何保证或条件，详见 [`LICENSE`](LICENSE)。

正式发布不证明生产安全，也不证明对特定用途的适用性。
