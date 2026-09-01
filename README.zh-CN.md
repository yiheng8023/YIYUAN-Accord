# YIYUAN Accord

把用户想要的结果推进到可验证、可恢复的闭环，同时不让用户管理 Agent 的工具、对话切换或内部工序。

YIYUAN Accord 是一个开放、Agent 中立的人机协作系统。

它帮助 Agent 始终围绕当前目标，在工作变化时动态调整，并以可验证的结果、明确的未知和受控清理完成收尾。

它可以使用不同宿主与机制。具体工具只是路线的一部分，不是产品本身。

项目的广义使命是改善人与 AI 的协作；当前产品面与证据严格限定为人与 Agent 的协作场景。

[English](README.md)

> **已发布稳定后备版本：** [`v3.0.1`](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.0.1)；**待发布版本线：** [`v3.1.0`](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.1.0)
>
> 只有 v3.1.0 链接对应的不可变、非预发行 GitHub Release 已存在时，才可使用该版本；此前请使用 v3.0.1。仓库文本不能自证发布。
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

下列不可变命令指向 `v3.1.0`，只有对应公开 Release 已存在时才可使用。待发布期间，请把相同命令中的精确不可变 ref 改为 `v3.0.1`；不要使用持续移动的 `main`。

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

上次验证 v3.0.1 时，后续操作是重启桌面端或新建 CLI 会话。

打开 **Plugins** 或运行 `/plugins`，确认 `YIYUAN Accord for Codex` 与 `deliver-demand-driven-outcome` 可见。

在当前客户端上重新确认之前，只能把这些标签和位置当作历史观察。

### Claude 客户端与 Claude Code

上次验证 v3.0.1 时，Claude Desktop Chat、Claude 网页聊天和 Cowork 使用 **Customize > Plugins**。

已记录的路线把 `https://github.com/yiheng8023/YIYUAN-Accord` 添加为个人 marketplace，安装 **YIYUAN Accord for Claude**，然后新建聊天。

客户端更新后，不得假设该路线、文案或位置仍然相同。

Claude Code 持久安装：

```powershell
claude plugin marketplace add yiheng8023/YIYUAN-Accord@v3.1.0 --scope user
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

匹配的不可变 GitHub tag 与 Release 决定 `v3.1.0` 是否已经公开发布。

仓库文本、测试、本地 tag 或候选记录都不能自证这个外部事实。

项目正式版只对精确仓库、包、声明的有限结论与已完成发布门负责。

它不证明普遍行为、生产安全、所有用途适用性，也不证明所有 Agent、操作系统和客户端界面兼容。

精确公开声明上限包含五项有限结论：

- v3.1.0 的上下文自适应协作闭环一致性；
- 当前 Codex 与 Claude 投影的静态包一致性；
- 一项有界、单臂的协作闭环内部实践结果；
- 针对连续性、修复与资源治理的本地回归重放结果；
- 从干净 v3.1.0 checkout 复现结果的能力。

另有仓库证据支持无副作用参考内核和下述有界宿主场景，但它们不扩大上述五项公开声明。

有界宿主证据只覆盖一条事件到结果路线、一条保持静默的充分路线、一次已验证的新对话交接，以及一次性非空 Windows Codex 与 Claude 重放中的历史生命周期子事实。精确审查切点 `c5a0668` 否定了宽泛 GT-20 结论：直接调用 Node runtime 不能证明宿主激活，源路径缺失的 preflight 拒绝也不能证明变更阶段的失败更新恢复。因此 GT-20 已按 schema-v6 overlay 重开；受影响面重新验收与四项新鲜独立审查均为 pending。

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
claude plugin marketplace add yiheng8023/YIYUAN-Accord@VERSION_TAG --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
```

只移除这条用户级路线安装的 Claude Code 投影时，执行前两条命令后停止，并确认该 scope 中的插件与 marketplace 登记都已不存在。

只有确认当前 GUI 路线仍存在后，才使用对应的 **Customize > Plugins** 操作。

优先使用宿主支持的原生重载和生命周期操作。

这些精确 ref 命令执行的是显式替换，不是原子就地更新。应先记录旧精确 tag；若目标安装失败，重新安装该 tag，验证健康状态，并报告未激活时段。

生命周期命令可以刷新安装文件，但不会替换当前任务或会话已经加载的能力。判断新版本前必须新建任务或会话；自报版本、`/reload-plugins` 或缓存变化本身都不是已加载行为完成热更新的证据。

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

| 微信支付（人民币） | 支付宝（人民币） |
| --- | --- |
| ![微信支付收款码](docs/assets/sponsoring/wechat-pay.png) | ![支付宝收款码](docs/assets/sponsoring/alipay.png) |

付款前请核对收款方。完整条款见 [`SPONSORING.zh-CN.md`](SPONSORING.zh-CN.md)。

### 免责声明与合规说明

YIYUAN Accord 是独立的社区开源项目。

它不是 OpenAI、Anthropic、Codex、Claude、Claude Code 或 GitHub 的产品，也不代表这些组织的赞助或背书。

第三方名称与商标归各自权利人所有。

用户仍需审查 Agent 输出，并遵守适用法律、合同、宿主条款、许可证和组织政策。

本软件按 Apache-2.0 许可证以“原样”方式提供，不附带任何保证或条件，详见 [`LICENSE`](LICENSE)。

正式发布不证明生产安全，也不证明对特定用途的适用性。
