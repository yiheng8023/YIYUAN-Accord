# YIYUAN Accord 3.2 开发计划与进度

由 `product/development.json` 派生；修改源数据后同步本页，校验会拒绝不一致。

当前为未冻结的开发基线；目标是完成验收后发布新的 3.2，不改写 3.1。
动态自适应是原有核心承诺；驱动宿主实现必要结果，按证据保留、合并、删除或补强，暂缓增加宿主适配。

## 工序与验收映射

| 工序 | 当前进度 | 执行步骤 | 验收出口 |
|---|---|---|---|
| 源头校准与继承基线 | 本地实现，未发布 | 从必要用户结果反证现有立意与职责分工，不预设 Skill、Hook、核心、索引、图或数量正确；区分任务执行、用户生命周期和维护验收，校准受影响基线与映射，保留无关的已验证事实及历史。 | 职责必要性、实际承担者与剩余缺口已明确；受影响源、计划、工序和验收一致且本地回归通过。这只关闭本轮源头校准，不证明宿主效果或最终架构充分。 |
| 系统短板与工程优化 | 本地实现，未发布 | 核对相关官方能力、实际宿主暴露和职责；需要时从同一事实源派生关系视图或索引，按真实调用者、影响及成本删减或补强，再测量受影响工程路径。 | 已定位工程问题与映射在本地回归通过；未闭合的实际执行、恢复和适应职责转入下一工序，不据此宣称全部系统质量已验证。 |
| 当前开发证据准入通路 | 进行中 | 按获批校准预绑定整版必需范围，分别落实每宿主功能、适用生命周期及整体价值；每宿主完整职责/质量/场景只记一次总账，不对三类声明重复展开全集。继续绑定真实作用域、入口、关键环境轴、判据和独立来源。先提交定义及实现 A，再观察 E，最后在候选 B 计算准入并接受绑定 B 的真实独立评审。调整必需清单或适用范围须按验收变更复核；按受影响依赖复用证据，保留静态检查和有据成本预算。 | 同一公开入口区分必需功能声明闭合与整版资格；漏范围、删用例、跨宿主拼半套或换入口/环境不能掩盖缺口。继续拒绝旧定义、来源不足、过期/漂移、跨事件或矛盾后态、未闭合残留及缺失独立评审。合成回归仅验证准入器；真实范围、判据充分性和来源接入仍未完成，授权、精确推送、托管及公共后态独立成立。 |
| 整体执行链、原生覆盖与遗留形态审查 | 待开展 | 用无需内部操作术语的真实需求验证普通入口交付与用户负担，并与适用原生基线比较；主动发现未列出的设计盲区和跨功能断点。按需论证目标、手段、可行条件和授权，证据足够即进入下一安全实现或核验。沿触发、发现与比较、执行及状态、故障接管、验收和清理检查整体连接；原生是起点而非停止规则，缺口或可信净收益机会才扩展检索，复用足够的宿主发现与执行链。自举同理。检查资产必要性、调用者、过期导航与维护负担，按证据保留、合并、替换或退役；同步受影响声明、工序和验收，历史证据不改写，功能不降格。 | 必要端到端链路和适用故障后态兑现；局部功能 PASS、指令加载或评估器代劳不能代替整体完成。若改变形态，应有配套入口、依赖、执行者与精确包验证。 |
| 动态适应、干扰与故障验收 | 待开展 | 按声明选择原生对照、最小可交付组合与受控混合环境；同一被测执行/状态变化联合核验适用纠正、恢复及资源后态，实际跨载体或来源转移才核验目的端与来源释放，不强制交接。精确包安装前和卸载后由仍可用的生命周期执行者承担；不依赖评估器救援或被移除的 Skill。 | 普通入口产生可独立观察的效果；正向外援、负向干扰及评估器救援均被识别；所需功能与后置状态全部有证据，不能取平均掩盖短板。 |
| 3.2 定版、发布与收尾 | 待开展 | 依据已建立的当前证据准入通路计算候选资格，不将静态 PASS 当作功能验收。复核资产必要性与受影响功能，按精确候选及证据校准 CHANGELOG.md；提交并推送完整候选，核对精确包、独立评审与托管检查，再依已有条件授权发布新的 3.2。发布后按用户新增授权，盘点其现有 Codex/Claude 中 Accord 的安装来源及共享关系，经受支持的宿主或实际管理器将已安装 Accord 升至该精确版本；先确认备份和可用回退路径，保护配置、模型路线、其他扩展及正在运行的任务。不顺带升级宿主应用、安装缺失组件或绕过账户限制。 | 精确 SHA、包、版本与公共发布对应；发布后检查及任务残留闭环；既有标签、发布与失败历史保持原样。另核验本机选定 Accord 的安装版本、实际激活和普通入口效果，不把缓存更新当生效；更新失败须恢复最后安全版本并披露未完成项，未经验证不关闭本机升级。 |

## 系统质量与工序映射

Derive the applicable floor for each required system quality from the bound result and risk. A failed or unknown required floor cannot be offset by speed, low cost, code reduction or a high average score elsewhere. Explicitly justify non-applicability; it does not remove product responsibilities. Optimize the weakest consequential dependency first and check its affected consumers. Baseline, plan shape, procedures and acceptance are revisable hypotheses within the bound goal. At material counterevidence or host change, revise only affected source and consumers, retain prior exact evidence as history, and explain the changed acceptance. Do not preserve a step count or mechanism merely to keep the original plan. Human and Agent understanding is provisional: alignment, research, planning, execution and review are conditional responsibilities, not a mandatory sequence or complete-specification gate. Continue safe work from current sufficient agreement; revisit only decisions affected by material uncertainty, changed needs or evidence. Any changed goal, authority or acceptance must be reconciled explicitly, never used to conceal an unmet commitment. Each applicable quality floor must be mapped to execution stages as well as listed; these many-to-many links are reviewable allocations, not a universal SOP or evidence that the floor has passed. Native goal mode is optional: ongoing planning and execution must correct or pause affected work when later intent, authority or evidence conflicts.

| 质量维度 | 必要底线 | 承担工序 | 当前验收 |
|---|---|---|---|
| 合规与安全 | No unauthorized or prohibited effects; truthful claim and ownership handling. | 源头校准与继承基线、整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | 未验证 |
| 功能覆盖 | Every bound function and quality requirement is fulfilled through an available executor. | 源头校准与继承基线、系统短板与工程优化、当前开发证据准入通路、整体执行链、原生覆盖与遗留形态审查 | 未验证 |
| 普通入口集成 | The selected ordinary entry connects trigger, current facts, decision, execution and independent post-state. | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查 | 未验证 |
| 恢复与生命周期 | Applicable failure, restoration, continuity, update and removal paths preserve user state and close attributable residue. | 当前开发证据准入通路、整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | 未验证 |
| 变化适应 | Relevant host, model, permission and active-package drift invalidates and revalidates only dependent assumptions and claims. | 动态适应、干扰与故障验收、3.2 定版、发布与收尾 | 未验证 |
| 证据完整性 | Current claims bind current subjects; independent observation and experimental execution remain distinguished. | 源头校准与继承基线、当前开发证据准入通路、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | 未验证 |
| 用户负担与干扰 | Necessary human decisions remain human-owned while Agent mechanics and unnecessary ceremony are not transferred to the user. | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | 未验证 |
| 可维护性与资源成本 | Verification, context, modules and resource use remain sustainable without weakening functional or evidence guarantees. | 系统短板与工程优化、当前开发证据准入通路、3.2 定版、发布与收尾 | 未验证 |

## 完整职责覆盖

The inherited responsibilities below are a review inventory, not an immutable feature list. Review necessity against the user's actual goal: retain, delegate to the host, merge, retire or fill a demonstrated gap. Record retired/merged responsibilities and their changed acceptance explicitly rather than silently dropping coverage. Preserve the outcomes that remain necessary, not every historical implementation or test. Decomposition and test identifiers are revisable mappings. Actively discover unlisted design defects, broken cross-function relations, entry/configuration blind spots and unnecessary mechanisms through task-relevant official changes, realistic normal-entry work, counterexamples and failure observations. Known findings seed but never bound the review. Prioritize consequences and affected dependencies; end a research branch when sufficient evidence supports the next safe implementation or validation. Complete outcomes and independently observed value, not counts of documents, tests, rules or components, determine completeness.

| 职责 | 所属工序 | 历史需求与反例参考 |
|---|---|---|
| 目标、授权与用户纠正 | 源头校准与继承基线、整体执行链、原生覆盖与遗留形态审查、3.2 定版、发布与收尾 | GT-03, GT-04, GT-10, GT-13 |
| 环境感知与自身能力识别 | 整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收 | GT-08, GT-14, GT-19 |
| 按需研究、学习与复用发现 | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查 | GT-15 |
| 关系判断、路线与形态选择 | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查 | GT-13, GT-16, GT-17 |
| 执行、配置与代码操作 | 系统短板与工程优化、整体执行链、原生覆盖与遗留形态审查 | GT-02, GT-11, GT-16 |
| 源头变更与全局一致性 | 源头校准与继承基线、当前开发证据准入通路 | GT-17 |
| 纠错、经验吸收与受控演进 | 动态适应、干扰与故障验收 | GT-05, GT-18 |
| 故障恢复与回滚 | 整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-18, GT-20 |
| 上下文与任务连续性 | 整体执行链、原生覆盖与遗留形态审查、动态适应、干扰与故障验收 | GT-07, GT-21 |
| 资源管理与清理 | 系统短板与工程优化、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-09, GT-12 |
| 安装、更新与卸载生命周期 | 当前开发证据准入通路、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-20 |
| 原生接替、旁路与退役 | 整体执行链、原生覆盖与遗留形态审查 | GT-01, GT-19 |
| 结果验证、独立证据与实际价值 | 源头校准与继承基线、当前开发证据准入通路、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-04, GT-06, GT-14 |

## 当前证据准入

准入契约：`yiyuan-accord-evidence-admission/v2`；已声明 0 个作用域、0 个用例。数量不是通过记录。

Bind requiredCoverage from authorized product needs before collecting evidence, independently of available or successful cases. All three claim groups remain required. An undefined required scope stays unbound; removing its cases, scope or claim cannot erase the obligation. Every delivered host needs required function and package-lifecycle scopes, plus complete duty, quality and scenario accounting across its required scopes once, not once per claim. Overall incremental value requires suitable bounded comparisons; native-sufficient duties need not individually demonstrate Accord gain, and one host's value cannot be attributed to another. Scope and oracle adequacy, representative whole-chain coverage and the legitimacy of any reduction require independent review; fresh hashes alone do not validate them. Each scope fixes its entry, decisive environment axes and applicable requirements; cases may vary other conditions for legitimate transitions but cannot borrow another scope's effects. The entry inventory is not a promise to test every entry. A caller-selected authenticated, independent, bounded read-only observer supplies checked same-episode facts, current conditions and authentic final-candidate reviews. Callable shape and digest echo do not authenticate those sources. Compute conditional admission by exact source/package/oracle identity, applicable coverage and final freshness, not stored assessments or diagnostics. Changes to requiredCoverage or applicable definitions invalidate dependent evidence. Static claimCeiling, empty cases and undeclared or unresolved requirements cannot grant qualification. Human authority, hosted checks and publication remain separate.

计划只投影验收定义；实际资格由受检来源、精确主体和当前条件计算。静态 CLI 与合成测试不证明实际功能。

- `function` 必需作用域：codex-function, claude-code-function, codex-desktop-continuity；未绑定或缺证据仍未完成。
- `package-lifecycle` 必需作用域：codex-lifecycle, claude-code-lifecycle；未绑定或缺证据仍未完成。
- `incremental-value` 必需作用域：product-value；未绑定或缺证据仍未完成。


## 宿主家族与入口边界

入口资料核对时间：`2026-09-05T02:30:47Z`。以下是开发盘点，不是各入口已适配或验收通过。

按宿主家族、具体入口/模式、执行位置、版本、提供商/模型、身份权限及实际生效配置绑定证据；同引擎或共享配置只说明待验证的关系，不允许 CLI、客户端、IDE、网页/云端和 API 互相继承效果。入口集合随官方发布和任务相关性增删，不构建全量笛卡尔积。两家族的入口盘点不是每个入口已适配的承诺；额外厂商仍暂缓。官方账户不可用的入口保留资料与未知，不规避访问限制。

| 入口 / 官方来源 | 执行位置 | 环境与权限边界 | 当前观察与未实测项 |
|---|---|---|---|
| `cx-cli` [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) | 本地终端；远程终端仍由该机器执行 | 绑定该 CLI 的配置、权限、提供商与工作目录。 | 2026-09-05 更新后复核：本机 0.153.4（前次 0.153.3）；仅接口观察，不继承旧行为证据。 |
| `cx-desktop` [Codex 桌面入口](https://learn.chatgpt.com/docs/app) | 本地项目/工作树或委派云端，按任务区分 | 界面入口、内嵌引擎与独立 CLI 版本分别识别。 | 2026-09-06 只读复核：OpenAI.Codex 26.901.5280.0。当前工具进程的父链为该 Desktop 应用→npm Codex 执行器→PowerShell；执行器路径当前磁盘字节对应 0.153.4，SHA256 444a3f0008050605cae73cd9b7a2dcac61294062dfaab56dd20430fd6498518b。该事实不证明驻留映像未漂移、有效权限、候选任务局部加载或普通入口效果；个人安装仍为3.1。 |
| `cx-vscode` [Codex VS Code / 兼容编辑器](https://learn.chatgpt.com/docs/codex/ide) | 本地交互或云端委派 | 编辑器版本、远程工作区、扩展实际加载与云端环境分别核对。 | 本机 openai.chatgpt 26.901.22334 仅安装记录；兼容编辑器未测。 |
| `cx-jetbrains` [Codex JetBrains 集成](https://learn.chatgpt.com/docs/codex/ide) | IDE 自有集成；执行后端待核 | 不是 VS Code 扩展的同一入口；不继承其配置或插件效果。 | 官方资料支持；未实测。 |
| `cx-xcode` [Codex Xcode 集成](https://learn.chatgpt.com/docs/codex/ide) | IDE 自有集成；执行后端待核 | 按 Xcode 代理接口与权限核对，不假设加载相同 Skill/Hook。 | 官方资料支持；未实测。 |
| `cx-cloud` [Codex web / 云端任务](https://learn.chatgpt.com/docs/cloud) | 托管隔离环境 | 触发前端与托管执行分开；绑定账户、仓库、实际分支/SHA、初始化/维护脚本、网络及缓存状态。本地插件不自动存在，旧缓存也不能代表当前包；不与 ChatGPT Work 或本地入口互相继承证据。 | 2026-09-06 复核官方云端及环境文档（https://learn.chatgpt.com/docs/environments/cloud-environment）；仍未进行云端候选实测，未新增账户/仓库连接或修改云环境。 |
| `chatgpt-web` [ChatGPT 网页入口](https://learn.chatgpt.com/docs/web) | 网页会话；实际工具执行位置待核 | ChatGPT 会话不等于 Codex 本地任务，不继承本地文件与插件权限。 | 官方资料支持；本轮未实测。 |
| `chatgpt-desktop` [ChatGPT 桌面 Chat / Work](https://learn.chatgpt.com/docs/app) | 按会话模式与执行目标区分 | 同一客户端可有不同模式；品牌或安装包名称不是模式能力证明。 | 官方资料支持；本机安装记录不证明各模式可用。 |
| `chatgpt-mobile` [ChatGPT iOS / Android](https://help.openai.com/en/collections/3742473-chatgpt) | 移动客户端；执行位置按具体能力核对 | 不默认获得本地 Codex 的配置、Shell 或插件入口。 | 官方入口资料支持；未实测。 |
| `cx-sdk` [Codex SDK / App Server](https://learn.chatgpt.com/docs/codex-sdk) | 调用方与目标 Codex 执行器 | SDK、协议与直接模型 API 不等同；版本、身份、配置及会话路由需绑定。 | 2026-09-06：0.153.4 本地 App Server 零模型探测观察到 standalone Skill 临时暴露及撤销；不是 SDK、完整插件、普通入口或云端效果验收。未安装 SDK 或运行认证调用。 |
| `cx-integrations` [Codex GitHub / GitLab / Linear / Slack 等触发入口](https://learn.chatgpt.com/docs/cloud) | 触发前端与云端执行器分离 | 组织授权、连接和任务环境另验；入口目录不授权连接或发布。 | 官方资料支持；未实测、未新增连接。 |
| `cc-cli` [Claude Code CLI](https://code.claude.com/docs/en/platforms) | 本地或远程终端机器 | 现有授权 CC Switch / DeepSeek 路线仅归因到已观察 CLI 会话。 | 2026-09-06 桌面更新后复核仍为2.1.261，执行文件SHA256 f2f5d1a155167488aeb32cd263e15436253c7b1681ae147c9e73e4d6bbc3c852未变。dev.6双轮140→60诊断两组通过且均未调用Skill；不由桌面更新自动废弃该有界CLI事实，也不外推整项功能或桌面效果。 |
| `cc-desktop` [Claude Desktop Code](https://code.claude.com/docs/en/desktop) | 本地、SSH 或云端会话分别绑定 | 本地 Code 可消费桌面 MCP 配置且有不同优先级；网关资料不证明本机 DeepSeek 路线可用。 | 2026-09-06 用户报告客户端更新后，只读安装包复核为 Claude 1.46388.4.0（前次1.46388.3.0）；本次未观测到运行中的Claude进程。安装版本不证明Code模式、现有模型路线、候选激活或桌面效果，相关入口证据仍待核。 |
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
| 按需研究、学习与复用发现 | cc-tools, cx-extensions, cc-extensions, gpt6-cognition | 借用实际可调用的宿主发现/推荐与生命周期；缺口或可信净收益机会触发已安装清单外的有界比较，不建第二套目录。 | 原生能完成但外部候选更合适；领域变化、目录不可调用、无新增收益反例。核对证据、许可、权限及总成本，发现不等于安装授权。 |
| 关系判断、路线与形态选择 | cx-state, cx-actors, cc-actors, cc-model-policy, cc-advisor, cc-sdk, gpt6-cognition, gpt6-protocol | 按完整效果与全生命周期负担选择路线，复用足够的宿主判断和调度；索引、图及比较核心只在真实调用需求下采用，不是必需中间层。 | 更优外部方案胜出、同等适配选择原生、无裁决依据保留未知、未安装候选不得冒充可执行；核对主/子代理实际模型。 |
| 执行、配置与代码操作 | cx-execution, cc-tools, cc-sdk | 原生工具承担操作；缺少的执行能力才组合或实现。 | 普通入口下完成实际变更，保留无关状态，禁止评估器救援冒充产品执行。 |
| 源头变更与全局一致性 | cx-execution, cc-tools, cc-memory, gpt6-cognition | 复用编辑与检查工具；Accord 补源头变更对计划、实现和验收的影响追踪。 | 改变一项前提，只更新受影响关系与声明；检查遗漏的消费者。 |
| 纠错、经验吸收与受控演进 | cx-continuity, cc-memory, cc-tools, gpt6-cognition | 当前纠正由 Agent 与任务状态立即承担；有复用价值且获准时才持久化经验，不把学习流水线作为纠错前提。 | 当前任务纠正立即改变后续实际动作；另测获准跨任务经验的适用、恢复及无关任务不受影响。 |
| 故障恢复与回滚 | cx-execution, cc-recovery, cc-tools | 优先原生恢复；仅为未覆盖副作用补偿，明确幸存执行者与可恢复范围。 | 注入中途失败，核对独立后态、并发及外部状态保护。 |
| 上下文与任务连续性 | cx-continuity, cc-actors, cc-sdk, cc-memory, gpt6-protocol | 优先用宿主运行时闭合自主触发、必要状态、接收核对和安全释放；按实际缺口补执行、持久状态或幸存接管者，不预设仅缺语义提示。 | 在获授权普通入口检验事实核对→送达移交→确认接管与单写者→来源资源释放。交接、完成或清理均不得触发未经用户明确授权的任务归档；任何归档实验也先取得该独立授权。注入目的端失败、移交中纠正、重复信号与用户恢复后的状态，核查最后安全来源、目的端及原始动作。当前未执行新的归档实验；本次开发对话故障不能证明修复后行为。 |
| 资源管理与清理 | cx-state, cx-execution, cx-hooks, cc-tools, cc-hooks, cc-sdk | 借用宿主控制释放任务资源与临时暴露；停止使用、停用、卸载、退役分别判断，保护用户与共享资产。 | 任务结束后核验归属和后态；缺少局部停用接口不扩大为全局卸载，复用未知时可逆保留，漂移后重验。 |
| 安装、更新与卸载生命周期 | cx-extensions, cc-extensions | 安装前、卸载后仍由可用的原生生命周期承担；实证缺口才补具有独立可用性的补偿与后态检查。 | 精确候选安装、更新失败、成功更新和卸载；核对执行者在各失败窗口的可用性、加载与残留，不以评估器补救充当产品能力。 |
| 原生接替、旁路与退役 | cx-state, cx-extensions, cc-extensions, cc-model-policy, gpt6-cognition | 必要功能由已验证同责方案接替；无必要资产按需求、调用关系和维护成本退役，自举也不预设自带执行器。 | 核对宿主接替的完整效果、故障与清理；识别误导现行导航的历史资产，删减不能丢失仍需功能或历史证据。 |
| 结果验证、独立证据与实际价值 | cx-execution, cc-tools, cc-sdk, gpt6-cognition | 普通任务核验结果与后态；维护者另做产品资格、对照与贡献归因，不把每次使用变成评审实验。 | 全链路结果及后态可观察；区分宿主本来就会与 Accord 的必要帮助。 |

### 当前能力依据与执行边界

One versioned semantic source owns outcomes and evidence requirements; workSequence owns procedures and exits. Duty ids join the review views without a second authority. Indexes, graphs, matrices and caches are replaceable representations justified by actual consumers and decision or maintenance benefit, not required product modules. Direct task-time queries may suffice. dependsOn is implementation-order review, not a live feedback or execution graph. This dated inventory is not every vendor or host/model/tool combination; model, host and composed capability remain distinct.

At a relevant decision, inspect the running client, actual provider/model, policy and exposed interface. Version/feature/configuration/package/permission changes, a supported invalidation event, source contradiction, missing observation or failed effect reopen affected applicability. Re-read supported state and only the needed official documentation; no automatic network watcher or fixed global expiry is installed. Retain the dated observation as history, never as permanently current support.

The current host Skill supplies adaptive guidance, not a proven system executor. Historical dev.2 native repair and same-session resume observations do not qualify this candidate, incremental value, surviving failure ownership, zero-history handoff or package lifecycle. closure.py remains a no-I/O reference core: callers supply candidates and comparison facts; it does not discover tools or establish their truth. Keeping that reference outside the ordinary entry is not itself a defect. The uncalled simulated graph demonstration has been retired from the current tree; its historical paths resolve at their original revisions. Needed discovery, decisions and effects still require sufficient observable host or composed execution.

运行时分配要求：不预设必须依赖独立运行时，也不预设无运行时足够。按所需可靠性绑定触发者、实际执行者、必要状态载体和故障后的接管者，再判断宿主原生机制、Hook、脚本、Skill 或其它对象的组合是否兑现；一轮任务可只需宿主现有 Agent 循环和上下文。对确定触发、强制约束、跨轮状态、无人值守推进或故障后继续执行，核验实际职责与效果，而非用对象名称代替判断。仅在现有组合确有执行、状态或恢复缺口时补足相应机制，包括有依据的持久运行时。Skill 是可解释指导，不是独立调度器或强制执行保证；历史良好体验也不能单独归因于运行时。任何组合仍须验收普通入口、失败及独立后态。

源数据中的职责依赖、工序、场景和能力引用构成评审关系；它们不证明插件已经执行该链路。

### 本机接口观察（非行为验收）

- `codex-continuity-history-review` — 2026-09-05 source review: pre-Accord 65466c565096b5c175c8b3b1242aa5bf6439b82d; current dev.3 Hook; Codex CLI 0.153.3 help and official App Server documentation。The old Hook stored bounded session lifecycle counters and advised the Agent to perform a native transition; it did not create or verify destinations itself. Its two-compaction threshold and copied-history fork route are historical choices, not current requirements. Dev.3 emits a stateless resume/compact hint. Current official documentation exposes token-usage and status events, fresh start/read and distinct archive/unsubscribe controls; archive can cascade to spawned descendants, while unsubscribe is not immediate runtime unload. Historical and current source/interface inspection, not an observed automatic handoff or a causal comparison of runtimes. The old Hook was labelled an unbound mechanism candidate at this revision. Documentation does not prove current Desktop exposure or lifecycle effects; CLI help does not verify these method semantics. Recheck the target entry/version before execution. No task was created, archived or unloaded by this review.
- `codex-cli-schema` — Codex CLI 0.153.3; default non-experimental generated ClientRequest.json。99 method variants; model/list, modelProvider/capabilities/read, experimentalFeature/list, skills/list, hooks/list, app/installed, plugin/list/install/uninstall, thread/start/read/resume/fork/compact/start, turn/start/interrupt, config/read, configRequirements/read, account/rateLimits/read and command/exec are present. Background-terminal list/clean are absent from the default schema, not proven unsupported. Schema existence only; no daemon query, model request or method effect. CLI version is not Desktop engine identity. Generated task-owned schema files are disposable.
- `codex-cli-flags` — Codex CLI 0.153.3。multi_agent, hooks and plugins stable/enabled; step_model_switching under-development/disabled. Plugin add/list/marketplace/remove subcommands exposed. CLI configuration and help snapshot only, not all Desktop feature state or task-fit behavior.
- `codex-cli-standalone-skill-exposure` — 2026-09-05T16:33:26Z; Codex CLI 0.153.4 binary SHA256 444a3f0008050605cae73cd9b7a2dcac61294062dfaab56dd20430fd6498518b; dev.5 Skill SHA256 e5d9d484d4f9062256ab587d4b12362e9530e5981a54dee8166d3873971aae08 from committed 9ba285aa092d1b26a48f3c3e2863cc4d5c0b62c5。The exact candidate Skill was absent, then listed enabled, then absent (0/1/0); each listing had zero discovery errors and 39 other Skills. The process exited normally with code 0 after stdin closed, without forced termination or config.toml creation; the Skill bytes were unchanged. The task-owned process was absent and all 75 temporary files (2718512 bytes) were removed with the temporary root verified absent. An initial parser-only attempt exited 2: --ignore-user-config and --ignore-rules belong to exec, not global app-server options. Bounded no-model native discovery/withdrawal observation, not Agent use, ordinary-entry autonomy, Hook execution, complete plugin loading/lifecycle, functional acceptance, incremental value or Codex cloud/Desktop engine evidence. Empty CODEX_HOME did not eliminate other Skill discovery; their origins, private/managed configuration and causal effects were not established, so this is not official-pristine or fully controlled composition evidence. No personal Accord installation was changed. The temporary probe and host state were disposable diagnostics, not an authenticated admission or final-review bundle.
- `claude-cli-help` — Claude Code 2.1.261; existing authorized DeepSeek route。model, agents, fallback-model, plugin-dir, restricted, setting-sources, strict-mcp-config, permission-mode, resume and fork-session flags exposed. Local option existence, not API compatibility or successful execution. Prior package probes remain separately bounded and cannot qualify the changed candidate. No official Claude account access is assumed.

## 动态适应的必查链路

按具体声明选择原生对照、可交付最小组合和受控干扰；不把干净宿主规定为通用运行前提。
环境处理：Prefer bounded task-owned isolation for evaluation and conflict-specific containment in real use. Preserve the user's healthy environment and unrelated capabilities. If interference cannot be isolated, bind it as a declared dependency or hold the affected claim unknown; do not silently assume ordinary users have it. Observe only decision-relevant effective state: distinguish configuration intent, inherited or managed policy, setting precedence, session overrides and actual loaded capabilities. An AGENTS.md or similarly named file has authority only if the host actually consumes it under the applicable scope; a config file alone is not a state receipt. Use supported host queries first, minimize private content and never collect credentials. Unknown effective fields limit dependent claims rather than defaulting to an official-pristine environment.

| 环境变化 | 要观察的功能效果 | 失败判据 |
|---|---|---|
| 受支持宿主未添加第三方扩展；现有能力有缺口或存在值得核实的净收益机会。 | 在声明的最小宿主前提下核对实际可用工具；按需使用官方目录/文档/源码、维护中的第三方或可靠外部渠道发现候选。发现本身不强制新增插件；缺联网、账号、权限或执行条件时明确缺口，取得必要授权后再接入并验证。 | 不能假定开发者增强环境普遍存在，也不能把默认配置等同零前提万能环境；不得静默调用未声明外援、无授权安装，或将发现候选当成功执行。 |
| 当前共识与证据足够，或出现影响下一安全决策的需求/领域变化、证据失效、能力缺口或可信净收益机会。 | 没有决策相关收益时复用并推进；否则有界澄清/外查，比较适用原生、官方支持渠道及可靠外部候选，证据足够即交付。原生可完成不等于最合适；发现不授权安装或改变目标/验收。 | 不能每轮强制全量需求访谈或联网；不能把现有清单当全部候选，也不能借动态之名静默放宽验收或在关键未知下冒进。 |
| 用户自定义指令、设置或扩展可能影响当前决定与效果，或声明配置与会话加载状态不一致。 | 只核对相关作用域、继承/覆盖和实际加载行为；兼容帮助可用，冲突按影响局部处理。验收绑定必要条件，并区分用户外援与可交付能力。 | 不能只读配置即宣称生效/隔离；不能擅改用户共享配置、采集凭据或将未知环境当官方初始状态，不能把额外帮助算作 Accord 固有增益。 |
| 模型更新使原有弱项消失，或对指导、上下文和工具的响应方式改变。 | 在同等任务及宿主条件下重新建立无 Accord 的模型原生基线；确认冗余或干扰后按同责效果削减介入，仅补残余缺口。 | 不能固化旧模型缺陷、将模型能力算作插件增益，或将 API 功能宣传当作当前宿主的执行证据。 |
| 主任务或子任务需要不同模型/推理配置，或所选路线失效、漂移、不满足效果。 | 在授权候选中自动匹配足够能力并通过原生或必要组合执行，核对实际模型及结果；原生足够时不保留重复路由器。 | 将默认继承、配置意图或品牌排名当作匹配证据；擅改用户钉定模型；无视别名/替代或虚称已切换。 |
| 当前原生路线足够、负担合理，且没有值得继续比较的决策相关改善机会。 | 按需复用并减少介入，保持同一功能与质量；不为证明插件存在感强行接管。 | 无必要重造、冗余机制或将非介入冒充增量价值。 |
| 所依赖能力不可用、降级或权限变化。 | 识别受影响职责，选择足够的原生、组合或自建替代并验证；不可行时明确尚未完成。 | 不能静默削减功能，安全停止不能算成功。 |
| 外部插件、记忆或开发辅助让任务变得容易。 | 区分贡献来源；在移除未声明外援后复验，或把必要条件纳入可交付依赖与成本。 | 不能把当前增强环境的成功直接推广给普通用户。 |
| 第三方规则、工具或插件与当前目标或执行链发生冲突。 | 按实际影响局部隔离或改道，保留无关用户状态并验证恢复与清理。 | 不能无界关闭用户环境，不能让外部规则新增授权或改写目标。 |
| 任务中宿主更新、缓存与加载版本分离、接口或上下文发生变化。 | 仅重算受影响事实与分配；对同一被测执行/状态变化联合核验适用的纠正、恢复及资源后态。原位继续可原位核对；实际跨载体或来源转移时才要求目的端核对后安全释放来源。失败保留最后安全状态及适用幸存接管者，重复信号不造成多写入者或循环交接。 | 不能沿用失效假设、以版本变化强制全量重做、用各项孤立 PASS 拼成整体闭环，或在目的端未核对前释放来源。 |
| 原生能完成，但未安装的外部候选可能显著改善质量、风险或总成本。 | 复用宿主可调用目录/推荐，有界外查并验证比较依据；更优且已准入的候选可胜出。缺少安装、连接或数据授权时只推荐并解释必要条件，继续可独立执行的安全工作。 | 不能以原生足够终止必要比较、因市场支持就信任候选，或把目录可见当作已安装/可执行。 |
| 任务从原工作领域转向需更深证据或高风险判断的领域，例如软件用户提出医学知识问题。 | 按问题深度与风险判断需要权威资料、专项工具、模型或专业人员；先复用可靠现有能力，必要时发现外部候选并说明能力与授权边界。 | 不能自动把领域标签等同专业资质、把专项插件作为唯一答案、未经授权外发敏感信息，或将通用回答/工具结果冒充专业诊断。 |
| 能力临时参与任务后不再需要，或未来复用、维护成本与可信状态发生变化。 | 核对归属及依赖，释放任务资源和临时暴露并验证后态；复用不确定时在支持范围内可逆停用而非猜测永久卸载。未来重用时按漂移重验；无必要的任务资产在授权范围内退役。 | 不能任务一结束便卸载用户共享工具、将不再调用冒充已停用，或没有作用域控制便无界清理。 |

## 当前短板及证据边界

- `handoff-archive-authority` — `guidance-corrected-behavior-unverified`：主线程18在只读接收后、实际移交消息送达前调用自身归档，执行随即中断；用户手动恢复。当前任务曾误以恢复后的未归档状态和不完整工具摘要否认历史动作。已回查原始调用；已安装3.1 Skill及当前指令的释放来源含义未细分，是可能促因，不能单独归因。修复明确任务归档必须由用户授权，接收核对不等于接管，先确认移交和单写者再释放来源资源。无仓库归档执行器可作确定性回归，不新增虚假拦截器或归档实验；当前仅源/指令修复，宿主行为仍须独立验证。 独立范围审查将此次受影响Desktop结果显式纳入必需功能范围codex-desktop-continuity；原五项义务保留。该范围暂未绑定，有效会话状态、候选任务局部加载、同次移交的独立动作/接管/后态来源及失败判据仍需核对。CLI或App Server结果不得替代Desktop；不新增归档实验或提前变更个人安装的权限。
- `sequential-correction-observer` — `implemented-live-diagnostic-verified`：两个跨轮证据反例及目录内Read误判均先失败再最小修复；单轮checkpoint、末轮记录和其他越界拒绝保留。96项相关回归、读取修复后的18项观察器回归及独立复核通过。完整实现与判据A=bc1195f先提交并推送，随后真实双轮E两组均由140改为60，逐轮回读、输入保护、正常结束和任务清理成立。详细观测见claude-ready-orders-correction-dev6；这是观察通路诊断，不补齐整项职责、自主恢复、归档修复行为或增量价值。真实scopes/cases及独立来源准入仍未完成。
- `readme-source-and-claim-alignment` — `implemented-local-not-functional-acceptance`：文案审查发现中英文 README 把冻结 schema-v3 当作当前开发权威、称条件策略为固定常量，并使用未经证明的 30 秒开始标题。已重写定位、实际包内容、版本与证据边界；保留安装和历史生命周期参考、社区与法律信息。由内容和源码事实判断，不因旧模型参与写作就认定缺陷；文案清晰不证明运行时收益。
- `candidate-shape-and-whole-chain-review` — `source-allocation-reopened-effects-unverified`：当前 dev.6 是单 Skill 加可选 SessionStart Hint；Hint 没有查询、调度或恢复执行。普通入口引导、纯参考判定和维护验收应按实际职责分开，未连接核心或图本身不构成缺陷。13 项是覆盖清单，不是 13 个自建模块。已区分当前纠错与跨任务学习、任务核验与产品价值对照，并明确安装前/卸载后须由仍可用的执行者接管；组合充分性仍待真实普通入口、失败和后态证据。
- `native-accord-capability-map` — `mapped-interface-evidence-not-runtime-closure`：当前有来源的矩阵及职责关系用于开发评审，不是实时能力库或已经运行的图。索引/图是可删改手段，保住的是关系判断与必要效果；工序 dependsOn 不证明运行反馈、交接或清理。先查真实调用者，再按同次转移的可观察后态验证宿主组合。 已删除未被插件、代码或测试调用的 39982 B 内存模拟 HTML，保留精确历史定位；当前术语入口不再把旧图模型当成必需架构。这是活跃资产删减，不是宿主运行加速或动态发现功能验收。
- `needs-based-model-and-subagent-routing` — `implemented-guidance-native-coverage-under-review`：主/子代理模型与推理按任务需求纳入现有路由职责；两宿主已提供部分原生选型和调度接口，不另造重复引擎。dev.2 Skill 增加匹配、别名/继承/替代核对及效果不足后的重选；自动匹配与实际执行仍需当前包效果证据。
- `conditional-alignment-and-external-discovery` — `observed-research-to-delivery-gap-open`：保留自然预算失败与产物反例，但调用数不等于成功取回。新诊断发现进度事件触发采集上限、WebFetch 列出但权限拒绝两项干扰；合并已知进度并维持有界采集后，无网页组正常结束并调用 Skill，但有提示参数和文案缺陷；列出未放行组的 4 次获取全部被拒，代码参数与参考不符；仅临时放行两个公开域名后 7 次获取成功、3 次域外拒绝，产物通过 8 项离线检查，却在截止时没有正常终态。详见 claude-effective-research-and-capture-dev3。旧取数成功无法重查的字段保留未知；不归咎模型或正文，不撤销旧自然失败，不以禁网、改描述或扩大预算冒充修复。下一步核验有效权限、资料取回、按证据执行及 Agent 自主核验的完整结果。
- `source-to-projection-convergence` — `implemented-local-unverified`：Both current worktree Skills are unpublished 3.2.0-dev.6. The continuity correction distinguishes fact checks from confirmed takeover and requires explicit user authorization for task archival. AGENTS, source, acceptance and navigation are aligned; installed 3.1 and historical definitions remain unchanged. Fresh exact-package ordinary-entry, failure and lifecycle evidence remains required.
- `ordinary-entry-effect-and-recovery` — `open`：整体目标仍是Agent承担必要任务机制；用户无需先学习交接、按钮、Git或Shell等内部操作词汇。历史dev.3/dev.5诊断保持原样；dev.6在已提交判据的Claude用户配置双轮观察中，两组均从140改为60并核验实际产物，但都未调用Accord Skill。其他用户扩展仍在，不称干净宿主、独立原生归因或Accord增量价值；样本不证明整项职责、任意环境兼容或生命周期。继续从具体声明绑定普通入口、必要作用域、整体及故障判据与独立来源，沿发现/匹配、执行、状态/资源、纠偏、恢复和验收闭合。自动交接、幸存接管者与完整生命周期仍待验。
- `historical-reference-identity-coupling` — `implemented-bounded-regression-verified`：当前开发校验允许简单 Markdown 正文中的不可变历史链接：仓库须与正式身份一致，完整提交须为本地 HEAD 的祖先，目标对象类型和路径须存在。仅排除已核验引用片段，周边文本、现役文件路径、代码/配置、代码块、图像和嵌套伪装仍受扫描；查询有界、单次缓存，无法核验则拒绝。旧版默认扫描不变，无整文件新增豁免、网络访问或依赖。四项新增回归覆盖正常引用、伪造目标、可执行/字面量语境及资源边界。范围不含任意未链接历史叙述、JSON 文本或完整 Markdown 语义识别；这是维护工具修正，不是宿主功能或价值证据。
- `verification-io-amplification` — `implemented-local-measured`：同一检出的完整校验 cProfile 单次前后对比：81.077 → 59.392 秒，755 → 493 次有界 Git 调用，均 valid=true、无错误。共享单次调用内的有界不可变内容缓存，合批读取相关历史文档；工作区读取保持新鲜，未删检查或子进程边界。这是本地测量，不是统计性能保证、宿主功能或产品增量价值证明。
- `acceptance-cost-and-coupling` — `conditional-evaluator-implemented-real-scope-and-source-binding-open`：当前公开 Python 验证入口可接入由调用方独立认证的有界只读观察者，按显式入口/环境作用域核对完整包、定义/判据、同次执行后态、当前条件及绑定候选的独立评审。静态 CLI、历史阶段及 developmentObservations 不晋升。正反合成回归已覆盖合法复用与错误准入，但真实 scopes/cases 为空，尚无实际候选资格；调用函数或摘要回显不能认证事实。已实现有界 Claude 诊断入口与固定 ready-orders 判据，逐臂独立工作区、即时回读和清理；显式复用宿主用户配置，不由观察器私读凭据。该样本不覆盖整项职责，也不证明私有配置未变或增量收益，暂不计入准入。继续绑定充分的真实判据、适用范围和来源核验，不能把维护者工具当作用户功能或收益。

## 发布与收尾约束

以下逐项来自当前发布条件；列出不等于通过。发布前证据和发布后收尾按下节顺序落实，不能相互替代。

- 完整改动已提交并推送精确候选
- 必要功能与质量验收全部成立
- 精确包及受影响宿主具有新鲜证据
- 独立评审及托管检查通过
- 精确候选与正式发布目标核对一致
- 按序发布并核验公共后态及任务残留
- 更新日志与精确候选及证据相符

## 发布顺序

更新日志：[CHANGELOG.md](../../CHANGELOG.md)。当前为未发布开发摘要；定版时以精确候选及验收证据核对，不混入历史发布账本。

版本内改动提交 → 推送精确候选 → 精确提交的验收与独立评审 → 发布同一提交 → 公共结果及清理核验。
提交不能夹带无关工作；推送成功、工作区干净或本地测试通过都不能单独代替发布验收。

当前对话含已启用的 Accord、其他能力及继承上下文，只作为开发辅助；不能用它证明普通用户环境下的效果。
本页是计划的可见投影，不是宿主原生计划面板修复，也不是功能完成或发布凭证。
