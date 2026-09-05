# YIYUAN Accord 3.2 开发计划与进度

由 `product/development.json` 派生；修改源数据后同步本页，校验会拒绝不一致。

当前为未冻结的开发基线；目标是完成验收后发布新的 3.2，不改写 3.1。
动态自适应是原有核心承诺；驱动宿主实现必要结果，按证据保留、合并、删除或补强，暂缓增加宿主适配。

## 工序与验收映射

| 工序 | 当前进度 | 执行步骤 | 验收出口 |
|---|---|---|---|
| 源头校准与继承基线 | 本地实现，未发布 | 保留历史证据；校准立意、成功定义及条件策略；把现有职责列为必要性评审清单，建立保留、合并、删除或补强后的工序与验收映射。 | 源头与映射的本地回归通过；明确尚未证明宿主功能、价值或发布就绪。 |
| 系统短板与工程优化 | 本地实现，未发布 | 先核对官方原生能力、当前宿主暴露和 Accord 职责映射；按同一事实源派生索引与影响关系，列明缺口及验收，再追踪薄弱依赖并测量优化。 | 已定位工程问题与映射在本地回归通过；未闭合的实际执行、恢复和适应职责转入下一工序，不据此宣称全部系统质量已验证。 |
| 整体执行链、原生覆盖与遗留形态审查 | 进行中 | 用无需内部操作术语的真实需求验证普通入口交付与用户负担，并与适用原生基线比较；主动发现未列出的设计盲区和跨功能断点。按需论证目标、手段、可行条件和授权，证据足够即进入下一安全实现或核验。沿触发、选择、执行及状态、故障接管、验收和清理检查整体连接；能力/按钮清单要服务于实际操作，原生足够则退出，缺口时比较成熟候选后再补。Skill/Hook 等形态可改，同步受影响声明、工序和验收。 | 必要端到端链路和适用故障后态兑现；局部功能 PASS、指令加载或评估器代劳不能代替整体完成。若改变形态，应有配套入口、依赖、执行者与精确包验证。 |
| 动态适应、干扰与故障验收 | 待开展 | 按声明选择原生对照、最小可交付组合及受控混合环境；验证环境变化、冲突、纠正、中断、恢复和完整包生命周期。 | 普通入口产生可独立观察的效果；正向外援、负向干扰及评估器救援均被识别；所需功能与后置状态全部有证据，不能取平均掩盖短板。 |
| 3.2 定版、发布与收尾 | 待开展 | 将变更、移除/替代、兼容与未验证项写入 CHANGELOG.md，定版时逐项对照精确候选及证据；提交并推送完整候选，完成受影响完整包证据、独立评审和托管检查，再依条件授权发布新的 3.2。 | 精确 SHA、包、版本与公共发布对应；发布后检查及任务残留闭环；既有标签、发布与失败历史保持原样。 |

## 完整职责覆盖

The inherited responsibilities below are a review inventory, not an immutable feature list. Review necessity against the user's actual goal: retain, delegate to the host, merge, retire or fill a demonstrated gap. Record retired/merged responsibilities and their changed acceptance explicitly rather than silently dropping coverage. Preserve the outcomes that remain necessary, not every historical implementation or test. Decomposition and test identifiers are revisable mappings. Actively discover unlisted design defects, broken cross-function relations, entry/configuration blind spots and unnecessary mechanisms through task-relevant official changes, realistic normal-entry work, counterexamples and failure observations. Known findings seed but never bound the review. Prioritize consequences and affected dependencies; end a research branch when sufficient evidence supports the next safe implementation or validation. Complete outcomes and independently observed value, not counts of documents, tests, rules or components, determine completeness.

| 职责 | 所属工序 | 历史需求与反例参考 |
|---|---|---|
| 目标、授权与用户纠正 | 源头校准与继承基线、整体执行链、原生覆盖与遗留形态审查、3.2 定版、发布与收尾 | GT-03, GT-04, GT-10, GT-13 |
| 环境感知与自身能力识别 | 整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收 | GT-08, GT-14, GT-19 |
| 按需研究、学习与复用发现 | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查 | GT-15 |
| 关系、动态索引、路线与形态选择 | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查 | GT-13, GT-16, GT-17 |
| 执行、配置与代码操作 | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查 | GT-02, GT-11, GT-16 |
| 源头变更与全局一致性 | 源头校准与继承基线 | GT-17 |
| 纠错、经验吸收与受控演进 | 动态适应、干扰与故障验收 | GT-05, GT-18 |
| 故障恢复与回滚 | 整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收 | GT-18, GT-20 |
| 上下文与任务连续性 | 整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收 | GT-07, GT-21 |
| 资源管理与清理 | 系统短板与工程优化、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-09, GT-12 |
| 安装、更新与卸载生命周期 | 动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-20 |
| 原生接替、旁路与退役 | 整体执行链、原生覆盖与遗留形态审查 | GT-01, GT-19 |
| 结果验证、独立证据与实际价值 | 源头校准与继承基线、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-04, GT-06, GT-14 |

## 宿主家族与入口边界

入口资料核对时间：`2026-09-05T02:30:47Z`。以下是开发盘点，不是各入口已适配或验收通过。

按宿主家族、具体入口/模式、执行位置、版本、提供商/模型、身份权限及实际生效配置绑定证据；同引擎或共享配置只说明待验证的关系，不允许 CLI、客户端、IDE、网页/云端和 API 互相继承效果。入口集合随官方发布和任务相关性增删，不构建全量笛卡尔积。两家族的入口盘点不是每个入口已适配的承诺；额外厂商仍暂缓。官方账户不可用的入口保留资料与未知，不规避访问限制。

| 入口 / 官方来源 | 执行位置 | 环境与权限边界 | 当前观察与未实测项 |
|---|---|---|---|
| `cx-cli` [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) | 本地终端；远程终端仍由该机器执行 | 绑定该 CLI 的配置、权限、提供商与工作目录。 | 本机 0.153.3；仅接口观察。 |
| `cx-desktop` [Codex 桌面入口](https://learn.chatgpt.com/docs/app) | 本地项目/工作树或委派云端，按任务区分 | 界面入口、内嵌引擎与独立 CLI 版本分别识别。 | 本机 OpenAI.Codex 26.901.4073.0；非候选效果验收。 |
| `cx-vscode` [Codex VS Code / 兼容编辑器](https://learn.chatgpt.com/docs/codex/ide) | 本地交互或云端委派 | 编辑器版本、远程工作区、扩展实际加载与云端环境分别核对。 | 本机 openai.chatgpt 26.901.22334 仅安装记录；兼容编辑器未测。 |
| `cx-jetbrains` [Codex JetBrains 集成](https://learn.chatgpt.com/docs/codex/ide) | IDE 自有集成；执行后端待核 | 不是 VS Code 扩展的同一入口；不继承其配置或插件效果。 | 官方资料支持；未实测。 |
| `cx-xcode` [Codex Xcode 集成](https://learn.chatgpt.com/docs/codex/ide) | IDE 自有集成；执行后端待核 | 按 Xcode 代理接口与权限核对，不假设加载相同 Skill/Hook。 | 官方资料支持；未实测。 |
| `cx-cloud` [Codex web / 云端任务](https://learn.chatgpt.com/docs/cloud) | 托管隔离环境 | 仓库、账户、依赖、网络与环境配置独立；本地插件不自动存在。 | 官方资料支持；本轮无云端候选实测。 |
| `chatgpt-web` [ChatGPT 网页入口](https://learn.chatgpt.com/docs/web) | 网页会话；实际工具执行位置待核 | ChatGPT 会话不等于 Codex 本地任务，不继承本地文件与插件权限。 | 官方资料支持；本轮未实测。 |
| `chatgpt-desktop` [ChatGPT 桌面 Chat / Work](https://learn.chatgpt.com/docs/app) | 按会话模式与执行目标区分 | 同一客户端可有不同模式；品牌或安装包名称不是模式能力证明。 | 官方资料支持；本机安装记录不证明各模式可用。 |
| `chatgpt-mobile` [ChatGPT iOS / Android](https://help.openai.com/en/collections/3742473-chatgpt) | 移动客户端；执行位置按具体能力核对 | 不默认获得本地 Codex 的配置、Shell 或插件入口。 | 官方入口资料支持；未实测。 |
| `cx-sdk` [Codex SDK / App Server](https://learn.chatgpt.com/docs/codex-sdk) | 调用方与目标 Codex 执行器 | SDK、协议与直接模型 API 不等同；版本、身份、配置及会话路由需绑定。 | 源码/CLI schema 观察；未安装 SDK 或运行认证调用。 |
| `cx-integrations` [Codex GitHub / GitLab / Linear / Slack 等触发入口](https://learn.chatgpt.com/docs/cloud) | 触发前端与云端执行器分离 | 组织授权、连接和任务环境另验；入口目录不授权连接或发布。 | 官方资料支持；未实测、未新增连接。 |
| `cc-cli` [Claude Code CLI](https://code.claude.com/docs/en/platforms) | 本地或远程终端机器 | 现有授权 CC Switch / DeepSeek 路线仅归因到已观察 CLI 会话。 | 2.1.261；dev.3 观察有失败，整体效果未验证。 |
| `cc-desktop` [Claude Desktop Code](https://code.claude.com/docs/en/desktop) | 本地、SSH 或云端会话分别绑定 | 本地 Code 可消费桌面 MCP 配置且有不同优先级；网关资料不证明本机 DeepSeek 路线可用。 | 本机 Claude 1.46388.3.0 仅安装记录；Code 候选效果未测。 |
| `cc-vscode` [Claude Code VS Code](https://code.claude.com/docs/en/vs-code) | 编辑器会话；具体执行目标待核 | 官方说明支持第三方提供商；实际扩展配置/加载/权限与该路线仍须验证。 | 本机 anthropic.claude-code 2.1.261 仅安装记录；未实测。 |
| `cc-jetbrains` [Claude Code JetBrains](https://code.claude.com/docs/en/platforms) | IDE 终端内 CLI | IDE 上下文桥接仍是独立边界；不能用 CLI 成功证明集成效果。 | 官方资料支持；未实测。 |
| `cc-cloud` [Claude Code web / 云端](https://code.claude.com/docs/en/web-quickstart) | 默认托管云端；组织自托管条件另核 | 账户、计划、仓库及环境独立；不假设现有第三方路线能调用。 | 官方资料支持；用户报告官方账户不可用，未实测、不绕过访问限制。 |
| `cc-remote` [Claude 移动端 / Remote Control / Dispatch](https://code.claude.com/docs/en/platforms) | 分别指向云端、现有本地会话或 Desktop | 移动入口不是独立本地执行器；配对、账户及会话存续条件分别核对。 | 官方资料支持；未实测、未配对。 |
| `claude-chat` [Claude Chat 网页 / 桌面 / 移动入口](https://academy.claude.com/tutorials/navigating-the-claude-desktop-app) | 聊天能力与 Code 执行入口分开 | 共享客户端不代表相同插件、配置或本地操作权。 | 官方资料支持；不由 CLI 第三方模型可用性外推。 |
| `claude-cowork` [Claude Cowork](https://support.claude.com/en/articles/13345190-get-started-with-claude-cowork) | 知识工作入口；具体运行位置按会话核对 | 模式、账户、文件/连接授权与 Code 分开评估；不是新增适配承诺。 | 官方资料支持；未实测。 |
| `cc-sdk` [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) | 调用方启动的 Agent 执行器 | SDK、CLI、直接模型 API 与第三方提供商兼容性分开；不新增依赖。 | 官方源码参考；未安装或运行 SDK。 |
| `cc-integrations` [Claude CI / Slack / Channels / 定时触发](https://code.claude.com/docs/en/platforms) | CI、云端或已运行本地会话，按入口区分 | 触发器不等于执行器；组织身份、连接、寿命与清理分别核对。 | 官方资料支持；未启用任何新连接或调度。 |

## 原生能力与 Accord 职责矩阵

资料核对时间：`2026-09-05T00:58:21Z`。这是现有两宿主的开发评审快照，不是永久能力目录或当前行为验收。
原生项的条件和效果尚需在实际客户端、模型路线及权限下核对。接口存在、配置可见、实际执行和结果成立分别取证。

| 原生能力 / 来源 | 能力层 | 已核对的接口或能力 | 适用条件与未证实边界 |
|---|---|---|---|
| `cx-state` [模型、能力和配置查询](https://learn.chatgpt.com/docs/app-server) | host-runtime | model/list、provider capabilities、feature、skills/hooks/apps、配置与配额查询。 | 按实际运行客户端复核；模式目录不是模型质量排名；查询权限与秘密字段需另行约束。 |
| `cx-actors` [子代理与模型配置](https://learn.chatgpt.com/docs/agent-configuration/subagents) | host-runtime | 子代理原生调度与 model / reasoning 配置、继承。 | 用户选型和委派授权优先；实际执行模型与任务适配待验，不能由默认继承推得最优。 |
| `cx-execution` [执行与中断](https://learn.chatgpt.com/docs/app-server) | host-runtime | turn/start、turn/interrupt、command/exec 及结构化交互。 | 接口存在不等于本任务获准调用，也不等于目标结果完成。 |
| `cx-continuity` [会话与上下文连续性](https://learn.chatgpt.com/docs/app-server) | host-runtime | thread/start/read/resume/fork/compact/start；tokenUsage/status 事件；archive、unsubscribe 与 closed 后态。 | 原生接口不等于接通自动交接。2026-09-05 官方文档区分归档与卸载：archive 可影响派生后代；unsubscribe 不保证立即卸载。核对实际入口、版本、所有权和依赖，保护目的端；新任务、历史分叉和同会话压缩用途不同。 |
| `cx-extensions` [插件、Skills 与 MCP](https://learn.chatgpt.com/docs/plugins) | host-runtime | 原生打包、发现、安装、信任与工具连接入口。 | 官方、第三方、自定义能力分层；安装、启用、暴露和效果分开核对。 |
| `cx-hooks` [生命周期事件与扩展](https://learn.chatgpt.com/docs/hooks) | host-runtime | SessionStart、压缩、工具、子代理和结束等事件。 | 事件不是完整当前状态；失效、超时、信任与处理器类型有不同边界，不默认保证阻断或恢复。 |
| `cc-tools` [工具执行与原生工作循环](https://code.claude.com/docs/en/how-claude-code-works) | host-runtime | 文件、搜索、命令、网络工具及观察—行动—验证循环。 | 模型和权限影响执行；语言服务器等额外能力仍有安装条件。 |
| `cc-actors` [子代理与模型覆盖](https://code.claude.com/docs/en/sub-agents) | host-runtime | 独立子代理上下文、调用级选型、定义、环境与父模型继承。 | 按当前版本核对优先级及替代模型；第三方提供商是否支持每项行为仍待验。 |
| `cc-model-policy` [模型切换与故障回退](https://code.claude.com/docs/en/model-config) | host-runtime | 模型选项、opusplan 阶段切换、条件故障回退。 | 不是通用最优匹配；模型别名与服务端身份分开，不向 DeepSeek 移植 Claude 专有模型语义。 |
| `cc-advisor` [条件式专家咨询](https://code.claude.com/docs/en/advisor) | host-runtime | 实验性的 Anthropic 服务端 advisor 工具。 | 有模型、服务端与网关条件；当前 DeepSeek 路线尚不具备可采信支持证据。 |
| `cc-extensions` [Skills、插件与连接扩展](https://code.claude.com/docs/en/features-overview) | host-runtime | Skills、MCP、插件及按需工作流的可组合入口。 | 安装与可见不能证明使用；额外技能、连接或服务能力须单独归因。 |
| `cc-hooks` [事件处理与工具约束](https://code.claude.com/docs/en/hooks) | host-runtime | 工具、会话、压缩、子代理等事件处理器。 | 须核对事件、处理器支持和失败语义；现有 Accord helper 仅失效提示。 |
| `cc-memory` [指令与记忆载体](https://code.claude.com/docs/en/memory) | host-runtime | CLAUDE.md、条件规则及自动记忆承载上下文。 | 记忆不是强制权限或实时状态；尊重用户记忆写入授权，纳入干扰与版本归因。 |
| `cc-recovery` [文件检查点与回溯](https://code.claude.com/docs/en/checkpointing) | host-runtime | 直接文件编辑的检查点与 rewind。 | 不覆盖 Bash 修改或所有外部副作用，不能代替 Git 或普遍回滚保证。 |
| `cc-sdk` [可编程 Agent 宿主接口](https://code.claude.com/docs/en/agent-sdk/overview) | host-runtime | Python / TypeScript SDK 复用工具、Agent 循环、会话、Hooks 与权限。 | SDK 与直接模型 Client API 不是同一能力；授权、依赖和当前提供商兼容性待核，尚未引入。 |
| `cc-permissions` [权限与策略](https://code.claude.com/docs/en/permissions) | host-runtime | 宿主执行权限、允许/询问/拒绝规则及配置层次。 | 提示词不是权限强制；配置优先级、工具可见性和任务权限应分别验证。 |
| `gpt6-cognition` [GPT-6 Astra 模型原生判断与协作](https://developers.openai.com/api/docs/guides/latest-model) | model | 官方说明涵盖多步工作、需求纠正、指令理解及子任务委派能力。 | 这是特定模型的官方描述，不是本项目效果验收；上下文冲突或过度指导仍可能干扰它。先观察无 Accord 基线，不固定假设模型存在旧缺陷。 |
| `gpt6-protocol` [GPT-6 Astra 与 API 协作能力](https://developers.openai.com/api/docs/guides/latest-model) | model-api-composition | 异步工具调用、执行中接收纠正、会话内推理配置调整。 | 依赖具体 API、模式及宿主接入；应用仍执行工具并管理待完成工作。API 文档支持不证明当前 Desktop/CLI 已暴露，也不能推断为独立持久执行器。 |

| Accord 职责 | 原生候选关系 | Accord 必要介入的假设 | 下一效果验证 |
|---|---|---|---|
| 目标、授权与用户纠正 | cx-state, cx-execution, cc-permissions, cc-tools, gpt6-cognition, gpt6-protocol | 用原生审批与交互；Accord 只补目标、纠正与后续行动的一致性。 | 用户中途纠正或撤权，观察后续实际效果而不只看答复。 |
| 环境感知与自身能力识别 | cx-state, cx-hooks, cx-extensions, cc-extensions, cc-hooks, cc-permissions | 按需读取当前事实；分别绑定宿主、提供商、插件与个人配置，不建第二套全量宿主目录。 | 对比声明、配置、实际暴露；制造一个局部未知并观察受影响决策。 |
| 按需研究、学习与复用发现 | cc-tools, cx-extensions, cc-extensions, gpt6-cognition | 复用足够的原生、现有授权生态及适用证据；缺口影响决策时发现已安装清单以外的成熟候选，自建前比较适用性，不另造已有的完整发现/选择/执行链。 | 现有足够或调研仍适用时不重复对齐/检索；缺口、证据失效时定向外查。核对维护、许可、兼容、安全、成本及实际效果；发现不授权安装。 |
| 关系、动态索引、路线与形态选择 | cx-state, cx-actors, cc-actors, cc-model-policy, cc-advisor, cc-sdk, gpt6-cognition, gpt6-protocol | 从需求与现状推导稀疏路线；主/子代理选型走原生接口，必要时组合，不另设固定模型排名。 | 匹配不同需求、显式选型和不足后的重选；核对实际模型、效果与成本。 |
| 执行、配置与代码操作 | cx-execution, cc-tools, cc-sdk | 原生工具承担操作；缺少的执行能力才组合或实现。 | 普通入口下完成实际变更，保留无关状态，禁止评估器救援冒充产品执行。 |
| 源头变更与全局一致性 | cx-execution, cc-tools, cc-memory, gpt6-cognition | 复用编辑与检查工具；Accord 补源头变更对计划、实现和验收的影响追踪。 | 改变一项前提，只更新受影响关系与声明；检查遗漏的消费者。 |
| 纠错、经验吸收与受控演进 | cx-continuity, cc-memory, cc-tools, gpt6-cognition | 复用授权状态载体；记录适用条件与反例，避免局部经验变成全局规则。 | 纠正后再次触发同类任务，核对适用性、恢复和不相关任务不受影响。 |
| 故障恢复与回滚 | cx-execution, cc-recovery, cc-tools | 优先原生恢复；仅为未覆盖副作用补偿，明确幸存执行者与可恢复范围。 | 注入中途失败，核对独立后态、并发及外部状态保护。 |
| 上下文与任务连续性 | cx-continuity, cc-actors, cc-sdk, cc-memory, gpt6-protocol | 优先用宿主运行时闭合自主触发、必要状态、接收核对和安全释放；按实际缺口补执行、持久状态或幸存接管者，不预设仅缺语义提示。 | 从普通入口观察无需反复人工提示的接续：目的端核对最新目标、纠正、未完工作和上下游，再释放来源；注入目的端失败、移交中变更及重复信号，验证安全来源、单一写入者和无误伤。归档成功不得代替资源释放后态。 |
| 资源管理与清理 | cx-state, cx-execution, cx-hooks, cc-tools, cc-hooks, cc-sdk | 优先宿主配额、中断和资源控制；补归属判断及独立清理核对。 | 任务资源释放且共享资源不变；未知资源不得据推断删除。 |
| 安装、更新与卸载生命周期 | cx-extensions, cc-extensions | 使用原生插件生命周期；仅补实证缺失的补偿和后态验证。 | 精确当前候选包的安装、更新失败、成功更新和卸载；确认加载与残留。 |
| 原生接替、旁路与退役 | cx-state, cx-extensions, cc-extensions, cc-model-policy, gpt6-cognition | 原生同责效果足够则旁路或退役重复实现，保留必要结果责任。 | 新原生能力接替后核对效果、恢复及清理；其后失效时重新评估。 |
| 结果验证、独立证据与实际价值 | cx-execution, cc-tools, cc-sdk, gpt6-cognition | 复用宿主测试/观察；按声明补独立验收、对照与贡献归因。 | 全链路结果及后态可观察；区分宿主本来就会与 Accord 的必要帮助。 |

### 事实、索引、图与运行时

One versioned semantic source supplies the native matrix, Accord duty matrix and sparse dependency views. Acceptance duties own outcomes, dependencies and evidence; workSequence owns procedures and exits. This map references them instead of copying a second authority. It is a task-relevant review inventory, not every vendor product or host x model x tool combination. Separate model cognition, host runtime and model/API composition; a host-labelled review row scopes relevance, not exclusive model ownership or automatic endpoint exposure.

At a relevant decision, inspect the running client, actual provider/model, policy and exposed interface. Version/feature/configuration/package/permission changes, a supported invalidation event, source contradiction, missing observation or failed effect reopen affected applicability. Re-read supported state and only the needed official documentation; no automatic network watcher or fixed global expiry is installed. Retain the dated observation as history, never as permanently current support.

The dev.3 host Skill supplies adaptive guidance, not a proven system executor. Historical dev.2 Claude Code/DeepSeek probes show bounded native repair and same-session resume after a normal process restart with input drift. The resume deliverable arm invoked the Skill and emitted a successful Hook hint, but native control also succeeded. These observations do not qualify changed dev.3 behavior, incremental value, surviving failure ownership, zero-history handoff or package lifecycle. closure.py is a no-I/O reference core and the graph HTML is a simulated PoC; neither is a live host index or automatic executor.

运行时分配要求：不预设必须依赖独立运行时，也不预设无运行时足够。按所需可靠性绑定触发者、实际执行者、必要状态载体和故障后的接管者，再判断宿主原生机制、Hook、脚本、Skill 或其它对象的组合是否兑现；一轮任务可只需宿主现有 Agent 循环和上下文。对确定触发、强制约束、跨轮状态、无人值守推进或故障后继续执行，核验实际职责与效果，而非用对象名称代替判断。仅在现有组合确有执行、状态或恢复缺口时补足相应机制，包括有依据的持久运行时。Skill 是可解释指导，不是独立调度器或强制执行保证；历史良好体验也不能单独归因于运行时。任何组合仍须验收普通入口、失败及独立后态。

源数据中的职责依赖、工序、场景和能力引用构成评审关系；它们不证明插件已经执行该链路。

### 本机接口观察（非行为验收）

- `codex-continuity-history-review` — 2026-09-05 source review: pre-Accord 65466c565096b5c175c8b3b1242aa5bf6439b82d; current dev.3 Hook; Codex CLI 0.153.3 help and official App Server documentation。The old Hook stored bounded session lifecycle counters and advised the Agent to perform a native transition; it did not create or verify destinations itself. Its two-compaction threshold and copied-history fork route are historical choices, not current requirements. Dev.3 emits a stateless resume/compact hint. Current official documentation exposes token-usage and status events, fresh start/read and distinct archive/unsubscribe controls; archive can cascade to spawned descendants, while unsubscribe is not immediate runtime unload. Historical and current source/interface inspection, not an observed automatic handoff or a causal comparison of runtimes. The old Hook was labelled an unbound mechanism candidate at this revision. Documentation does not prove current Desktop exposure or lifecycle effects; CLI help does not verify these method semantics. Recheck the target entry/version before execution. No task was created, archived or unloaded by this review.
- `codex-cli-schema` — Codex CLI 0.153.3; default non-experimental generated ClientRequest.json。99 method variants; model/list, modelProvider/capabilities/read, experimentalFeature/list, skills/list, hooks/list, app/installed, plugin/list/install/uninstall, thread/start/read/resume/fork/compact/start, turn/start/interrupt, config/read, configRequirements/read, account/rateLimits/read and command/exec are present. Background-terminal list/clean are absent from the default schema, not proven unsupported. Schema existence only; no daemon query, model request or method effect. CLI version is not Desktop engine identity. Generated task-owned schema files are disposable.
- `codex-cli-flags` — Codex CLI 0.153.3。multi_agent, hooks and plugins stable/enabled; step_model_switching under-development/disabled. Plugin add/list/marketplace/remove subcommands exposed. CLI configuration and help snapshot only, not all Desktop feature state or task-fit behavior.
- `claude-cli-help` — Claude Code 2.1.261; existing authorized DeepSeek route。model, agents, fallback-model, plugin-dir, restricted, setting-sources, strict-mcp-config, permission-mode, resume and fork-session flags exposed. Local option existence, not API compatibility or successful execution. Prior package probes remain separately bounded and cannot qualify the changed candidate. No official Claude account access is assumed.

## 动态适应的必查链路

按具体声明选择原生对照、可交付最小组合和受控干扰；不把干净宿主规定为通用运行前提。
环境处理：Prefer bounded task-owned isolation for evaluation and conflict-specific containment in real use. Preserve the user's healthy environment and unrelated capabilities. If interference cannot be isolated, bind it as a declared dependency or hold the affected claim unknown; do not silently assume ordinary users have it. Observe only decision-relevant effective state: distinguish configuration intent, inherited or managed policy, setting precedence, session overrides and actual loaded capabilities. An AGENTS.md or similarly named file has authority only if the host actually consumes it under the applicable scope; a config file alone is not a state receipt. Use supported host queries first, minimize private content and never collect credentials. Unknown effective fields limit dependent claims rather than defaulting to an official-pristine environment.

| 环境变化 | 要观察的功能效果 | 失败判据 |
|---|---|---|
| 受支持宿主为默认配置且未添加第三方 Skills/MCP/插件/App，当前可用能力不足。 | 在声明的最小宿主前提下核对实际可用工具；按需使用官方目录/文档/源码、维护中的第三方或可靠外部渠道发现候选。发现本身不强制新增插件；缺联网、账号、权限或执行条件时明确缺口，取得必要授权后再接入并验证。 | 不能假定开发者增强环境普遍存在，也不能把默认配置等同零前提万能环境；不得静默调用未声明外援、无授权安装，或将发现候选当成功执行。 |
| 当前共识足够，或后续出现影响下一安全决策的需求变化、证据失效或能力缺口。 | 足够时直接复用并推进；不足时按受影响部分澄清/外查官方和维护中的成熟候选，在自建承诺前比较。允许安全有界试验逐步形成认识；发现不授权安装或改变目标/验收。 | 不能每轮强制全量需求访谈或联网；不能把现有清单当全部候选，也不能借动态之名静默放宽验收或在关键未知下冒进。 |
| 用户自定义指令、设置或扩展可能影响当前决定与效果，或声明配置与会话加载状态不一致。 | 只核对相关作用域、继承/覆盖和实际加载行为；兼容帮助可用，冲突按影响局部处理。验收绑定必要条件，并区分用户外援与可交付能力。 | 不能只读配置即宣称生效/隔离；不能擅改用户共享配置、采集凭据或将未知环境当官方初始状态，不能把额外帮助算作 Accord 固有增益。 |
| 模型更新使原有弱项消失，或对指导、上下文和工具的响应方式改变。 | 在同等任务及宿主条件下重新建立无 Accord 的模型原生基线；确认冗余或干扰后按同责效果削减介入，仅补残余缺口。 | 不能固化旧模型缺陷、将模型能力算作插件增益，或将 API 功能宣传当作当前宿主的执行证据。 |
| 主任务或子任务需要不同模型/推理配置，或所选路线失效、漂移、不满足效果。 | 在授权候选中自动匹配足够能力并通过原生或必要组合执行，核对实际模型及结果；原生足够时不保留重复路由器。 | 将默认继承、配置意图或品牌排名当作匹配证据；擅改用户钉定模型；无视别名/替代或虚称已切换。 |
| 当前原生能力已足够。 | 按需复用并减少介入，保持同一功能与质量；不为证明插件存在感强行接管。 | 无必要重造、冗余机制或将非介入冒充增量价值。 |
| 所依赖能力不可用、降级或权限变化。 | 识别受影响职责，选择足够的原生、组合或自建替代并验证；不可行时明确尚未完成。 | 不能静默削减功能，安全停止不能算成功。 |
| 外部插件、记忆或开发辅助让任务变得容易。 | 区分贡献来源；在移除未声明外援后复验，或把必要条件纳入可交付依赖与成本。 | 不能把当前增强环境的成功直接推广给普通用户。 |
| 第三方规则、工具或插件与当前目标或执行链发生冲突。 | 按实际影响局部隔离或改道，保留无关用户状态并验证恢复与清理。 | 不能无界关闭用户环境，不能让外部规则新增授权或改写目标。 |
| 任务中宿主更新、缓存与加载版本分离、接口或上下文发生变化。 | 重新感知相关事实，仅重算受影响分配与证据；经验证继续、恢复或交接。 | 不能沿用失效假设，也不能把宿主版本变化当作全量重做的固定理由。 |

## 当前短板及证据边界

- `readme-source-and-claim-alignment` — `implemented-local-not-functional-acceptance`：文案审查发现中英文 README 把冻结 schema-v3 当作当前开发权威、称条件策略为固定常量，并使用未经证明的 30 秒开始标题。已重写定位、实际包内容、版本与证据边界；保留安装和历史生命周期参考、社区与法律信息。由内容和源码事实判断，不因旧模型参与写作就认定缺陷；文案清晰不证明运行时收益。
- `candidate-shape-and-whole-chain-review` — `reviewed-not-architecture-frozen`：dev.3 仍是单 Skill 加固定 SessionStart Hint 的候选形态；开发校验器也按该形态核验，不是通用形态引擎。已移除源数据中脚本/参考文件的冗余禁令，仍拒绝未声明文件及包摘要不符。Skill/Hook、核心、运行时及其数量均可因完整职责而改变，届时同步改声明、校验和验收，不靠放松摘要绕过。当前 Hook 只在恢复/压缩时输出提示；无状态查询、调度或恢复执行。纯核心及图 PoC 未接入普通入口，不能拼成一个已经闭合的系统。
- `native-accord-capability-map` — `mapped-interface-evidence-not-runtime-closure`：已建立有日期和来源的原生能力—Accord 职责关系，连接当前工序、验收与变更重查；动态图 PoC 和纯核心不是实时宿主索引或执行器，普通入口的全链路闭环仍待验证。
- `needs-based-model-and-subagent-routing` — `implemented-guidance-native-coverage-under-review`：主/子代理模型与推理按任务需求纳入现有路由职责；两宿主已提供部分原生选型和调度接口，不另造重复引擎。dev.2 Skill 增加匹配、别名/继承/替代核对及效果不足后的重选；自动匹配与实际执行仍需当前包效果证据。
- `conditional-alignment-and-external-discovery` — `observed-research-to-delivery-gap-open`：保留 dev.3 首轮反例；本轮同参考复测中原生组交付两文件但说明有误，当前包组达到宿主预算时只完成脚本。只改发现描述的实验组交付两文件，但三个可用组均未调用 Skill，不能归因于正文或证明描述修复了激活/取数；该变体未合入。三份脚本各通过 7 项评估器离线控制流检查，不是真实 SDK 运行。论证应区分事实、推断和未知，把必要条件转为可执行路径，证据足够即推进；下一步须区分普通入口选择、研究取数和模型/工具波动，不叠加全局规则或靠增加预算宣称修复。
- `source-to-projection-convergence` — `implemented-local-unverified`：Both worktree Skills now project conditional alignment, external discovery and effective-environment guidance as unpublished 3.2.0-dev.3 packages. Schema-v2 entry descriptors and optional Node hints are unchanged. These are context-triggered duties, not a fixed SOP. Static admission does not prove current host effects.
- `ordinary-entry-effect-and-recovery` — `open`：整体目标仍是 Agent 承担必要任务机制；交接、按钮、Git 或 Shell 都只是例子，用户无需先学习内部操作词汇。当前 dev.3 的自然语言订单场景与原生对照都产生正确结果并保护全部输入，无额外用户操作；两组均未调用 Skill，支持该场景原生足够，不证明 Accord 增量收益、任意配置兼容或资源回收能力。按需求、能力发现/匹配、执行、状态/资源、纠偏、恢复和验收的依赖继续闭合。历史状态 Hook 与原生 Agent 接续组合只是已追溯案例，自动交接、幸存接管者与完整生命周期仍待验。
- `historical-reference-identity-coupling` — `implemented-bounded-regression-verified`：当前开发校验允许简单 Markdown 正文中的不可变历史链接：仓库须与正式身份一致，完整提交须为本地 HEAD 的祖先，目标对象类型和路径须存在。仅排除已核验引用片段，周边文本、现役文件路径、代码/配置、代码块、图像和嵌套伪装仍受扫描；查询有界、单次缓存，无法核验则拒绝。旧版默认扫描不变，无整文件新增豁免、网络访问或依赖。四项新增回归覆盖正常引用、伪造目标、可执行/字面量语境及资源边界。范围不含任意未链接历史叙述、JSON 文本或完整 Markdown 语义识别；这是维护工具修正，不是宿主功能或价值证据。
- `verification-io-amplification` — `implemented-local-measured`：同一检出的完整校验 cProfile 单次前后对比：81.077 → 59.392 秒，755 → 493 次有界 Git 调用，均 valid=true、无错误。共享单次调用内的有界不可变内容缓存，合批读取相关历史文档；工作区读取保持新鲜，未删检查或子进程边界。这是本地测量，不是统计性能保证、宿主功能或产品增量价值证明。
- `acceptance-cost-and-coupling` — `implemented-local-unverified`：Current verify/host-check now dispatch to development-package admission without promoting or repeatedly replaying historical behavior. Retained rejection tests run current verifier code against the immutable predecessor subject. Package safety, identity, complexity, source preservation and dirty-worktree gates remain applicable; current functional and host evidence are still unverified.

## 发布顺序

更新日志：[CHANGELOG.md](../../CHANGELOG.md)。当前为未发布开发摘要；定版时以精确候选及验收证据核对，不混入历史发布账本。

版本内改动提交 → 推送精确候选 → 精确提交的验收与独立评审 → 发布同一提交 → 公共结果及清理核验。
提交不能夹带无关工作；推送成功、工作区干净或本地测试通过都不能单独代替发布验收。

当前对话含已启用的 Accord、其他能力及继承上下文，只作为开发辅助；不能用它证明普通用户环境下的效果。
本页是计划的可见投影，不是宿主原生计划面板修复，也不是功能完成或发布凭证。
