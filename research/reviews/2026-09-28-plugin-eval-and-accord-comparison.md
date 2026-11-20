# Claude Code plugin eval 与 Accord 对照展示

2026-09-28 官方资料核实；未运行 eval、调用模型或测试 Accord。本机版本、账号可用性及真实执行后态未核。

**官方明示**（[eval 文档][E]）：

- 命令为 `claude plugin eval .`；`init` 可交互建案例，`init --bare <name>` 只建模板。最低 Claude Code 2.1.269；装有 Git 时须 ≥2.31。2.1.283 前未检查旧 Git，相关隔离不能倒推成立。
- 默认每案例每组3次，有／无插件两组；可用 `--ablation none` 关闭对照。评分是 grader 加权通过率再跨运行平均；阈值默认1.0，Δ不决定退出码。六类为 `regex`、`tool_used`、`tool_order`、`file_exists`、`llm`、`baseline`，无自定义代码 grader。可查最终回答、轨迹、文件及 mock 调用；LLM 轨迹只看首尾各12条。Skill触发检查通常不计双组分数；全数grader被排除或显式`arm: both`等设置可改变此规则。
- 每次新建非交互 `claude -p`；默认10轮／300秒，上限200轮／3600秒。`history_file` 装入旧对话，案例提示成为下一用户轮；可用 fixture、scaffold 和 MCP mock。
- 临时 home／工作区／配置排除用户及项目设置、CLAUDE.md、记忆、其它插件、Skills、Hooks、MCP；管理策略及允许的环境变量仍适用。目标插件自身的 Skills、Hooks、agents 会加载；Hooks、真实MCP及获准scaffold在Agent沙箱外运行，不能称全环境隔离。Artifact工具关闭。
- 写／shell／网络工具需命令行授权；真实MCP默认不启动。原生Windows无shell沙箱后端，含shell授权的套件须用WSL2。Skill字段不能扩大eval授权。
- 执行、judge及交互init计账户用量／账单；`--max-cost-usd` 无默认上限，只限标价估算且在途运行可超额。JSON、HTML和退出码可接CI；订阅且Artifact可用时，直接运行默认发布私有报告；API-key或Claude会话发起默认本地，`--no-publish` 保持本地。

**对 Accord 的推论**：适合作为未来Claude适配的限定案例对照及传播材料候选。应固定插件／模型／题目／判据，保留负Δ、失败、成本及原始产物；默认3次不是普遍收益证明。文档未承诺实时用户多轮编排、跨进程恢复、长期协作或跨宿主有效性；这些仍须独立设计并实测。Claude分数不能代验Codex或Accord整体验收，当前未取得对照收益证据。

**本次用户确认的定位**：plugin eval是传播素材的一部分，而非全部；完整能力与价值还须结合真实交付、持续协作、纠偏恢复、人工负担及资源成本的证据。

补充：[manifest][P] 支持 `experimental.evals` 定位套件；[Skills][S] 区分技能内容持续与授权按用户轮清除，不能由内容可见推断持续权限或可靠行为。

[E]: https://code.claude.com/docs/en/plugin-evals
[P]: https://code.claude.com/docs/en/plugins-reference
[S]: https://code.claude.com/docs/en/skills
<a id="claude-code-read-only-feasibility"></a>

## 2026-11-18 Claude Code 只读可行性初查

优先评估本地交互式 CLI 的一个实际入口。官方接口支持插件载入、输入观察、会话恢复和压缩通知，本机 `claude --version` 返回 2.1.326。版本检查与文档能建立接口可行性，实际启用、Hook 交付、权限和恢复行为仍待验证。SDK 只在交互式 CLI 缺必要信号且真实需求值得引入时单独核查。

| 职责 | 先复用的宿主机制 | 最小后续核验 |
| --- | --- | --- |
| 入口、信任、更新及退出 | 插件由宿主管理，作用域及组织策略由宿主决定。更新后既有会话可以继续运行旧组件，官方提供 `/reload-plugins` 和下一次启动两条采用路径。 | 选定作用域和精确宿主版本，核实际加载、授权、升级和移除后的状态；保留宿主原信任决定。 [插件管理](https://code.claude.com/docs/en/discover-plugins) |
| 输入与任务边界 | `UserPromptSubmit` 提供会话身份、工作目录、权限模式和提交文本；`SessionStart` 区分启动、恢复、清空、压缩和派生。 | 核正常提示、带附件或多个输入形态是否能关联到准确轮次、内容和任务。检查同会话新任务和退出边界。Codex 的回执解析器和状态文件约定属于 Codex 适配。 [Hook 参考](https://code.claude.com/docs/en/hooks#userpromptsubmit) |
| 权限、暂停与迟到效果 | 原生权限对话和策略优先。SDK 文档提供中断当前响应且保留会话的接口。 | 交互式 CLI 的暂停和取消单独核验。记录停止前后的工具实际效果；`Stop`、`StopFailure` 以及会话结束各有不同生命周期。 [权限事件](https://code.claude.com/docs/en/hooks#permissionrequest) · [SDK 中断](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode#interrupt-a-response) |
| 压缩、续作和回收 | 原生 `resume`／`continue` 恢复会话。`PostCompact` 提供压缩完成观察，完成与结束事件可作为核对时机。 | 验证未完任务与已有结果、原约束及授权能对账，迟到效果可辨，下一输入能自然开始，所属工作资源实际停止或交还。 [压缩事件](https://code.claude.com/docs/en/hooks#postcompact) · [会话恢复](https://code.claude.com/docs/en/agent-sdk/sessions) |

共用层保留目标、权限、暂停、接续、结果验收的语义和可复用夹具。宿主层承担事件解码、会话与工作区绑定、来源与信任、执行及包生命周期。历史 Claude 生命周期记录 [efea8371](https://github.com/yiheng8023/YIYUAN-Accord/commit/efea8371630843e481ef0f7ed6fec8383a4ecb45) 可回看故障和验证方法。观察链 [735a5919](https://github.com/yiheng8023/YIYUAN-Accord/commit/735a5919e0f40d13d003e45be08b7292fbf1643f) 和 Codex 包中的 Claude 专属分支 [fcf88bdf](https://github.com/yiheng8023/YIYUAN-Accord/commit/fcf88bdf08401d3e926c2545a645b3b78e212b9a) 已退役，其当时的验收保留在原入口与版本。

候选结论为有依据进入单入口实证的准备。先有真实需求和一个受控验证范围，再决定是否实施。Claude 自带的插件对照工具可复用来检查后续限定场景，输入、授权及恢复仍按实际行为取证。本轮资料核查不涉及插件安装、配置写入、模型调用、适配实现或交付版本选择。 [插件对照官方说明](https://code.claude.com/docs/en/plugin-evals)

### 2026-11-18 CLI 与桌面 Code 入口复核

本机独立 CLI 的 `claude --version` 返回 2.1.326。Windows 注册的 Claude Desktop 包为 5.11492.5.0，应用清单登记了桌面入口。这两个版本分别描述 CLI 和外层桌面应用。桌面 Code 会话实际加载的引擎构建、provider、有效设置与组件仍待场景证据。此次读取只涉及版本和包身份。

Anthropic 官方说明，本地桌面 **Code** 和独立 CLI 共用底层引擎、本地配置及项目记忆，但会话列表独立，有各自的权限与插件交互。CLI 的 `/desktop` 是官方迁移路径，会保存会话并退出原 CLI；采用与单写者仍按后态核验。桌面不同模式的插件约束分别成立，Cowork 的账户同步机制与本地 Code 的设置来源各有边界。 [桌面 Code](https://code.claude.com/docs/en/desktop) · [本地设置与优先级](https://code.claude.com/docs/en/settings)

优先在独立交互式 CLI 证明一个真实链路，再用桌面本地 Code 核同一任务的实际入口条件。共享事件或配置以相同语义复用，插件是否可发现、信任是否有效、是否加载，以及实际输入、退出和接续按各入口核对。需要跨端时优先评估官方迁移能力。只有出现影响必要职责的差异才考虑适配特例；本节不预设新增宿主的实现或发行版本。

<a id="claude-code-feasibility-r116"></a>

### 2026-11-18 当前工具与历史包的只读核验

本次独立 CLI 返回 2.1.327，当前桌面安装记录显示 Claude 6.6395.0，开始菜单登记了 Squirrel 应用入口。前次 MSIX 观察保留原时点，当前登记未证明桌面 Code 会话的后端版本。CLI 帮助确认可通过 `--plugin-dir` 只在一次会话中加载本地包，为后续隔离实证提供入口。本次没有启动交互会话、安装插件、改写现有设置或调用模型。 [CLI 参考](https://code.claude.com/docs/en/cli-reference)

从 `efea8371630843e481ef0f7ed6fec8383a4ecb45` 提取历史 Claude 包，在当前 CLI 上执行 `claude plugin validate`。普通模式退出 0，清单错误为 0；严格模式因包名含 `claude` 的同名警告退出 1。校验器识别一项 Skill 和五个 Hook（SessionStart、PostToolBatch、UserPromptSubmit、Stop、SessionEnd）。单独提取的子包同时报告目录用 README 和图标缺失；这两项按真实投稿树重核，尤其 README 可由仓库根提供。静态结果只覆盖这份历史包及校验器。 [清单规范](https://code.claude.com/docs/en/plugins-reference#validate-the-manifest)

后续单入口实证优先核以下差异：

- **输入与授权。** 宿主定时任务也能触发 `UserPromptSubmit`，Hook 超时时默认可能继续投递提示。测试需区分真实用户输入、宿主触发和回执缺失，用原生授权及事件辨别三者。 [输入 Hook](https://code.claude.com/docs/en/hooks#userpromptsubmit)
- **执行停止和资源归还。** 工具批结束可复用 `PostToolBatch` 的批次信号。停止请求、工具终态和实际输出分别观察；退出 Hook 的默认时间很短，应明确哪些工作可在退出时完成、哪些需由下次接续对账。 [工具批完成](https://code.claude.com/docs/en/hooks#posttoolbatch) · [退出事件](https://code.claude.com/docs/en/hooks#sessionend)
- **接续和下一任务。** 先在 CLI 完成一个带授权和中断的真实任务，核实恢复内容、迟到效果、未完工作和退出后态。需要跨端时先试官方迁移，核 CLI 实际退出及同一会话在桌面接续。CLI 与桌面各自验证插件加载及信任。 [桌面迁移](https://code.claude.com/docs/en/desktop#coming-from-the-cli)

<a id="claude-code-cli-deepseek"></a>

### 2026-11-19 Claude Code CLI 第三方模型实测

Windows 独立 CLI 2.1.328 在隔离工作目录按会话加载历史包 `3.2.0-dev.16`，通过 DeepSeek 的 Anthropic 兼容入口运行 `deepseek-flash`。任务是读取三个公开文档，核对 3.3.18 的四条安装命令是否指向同一精确提交。插件出现在实际会话的加载列表中，启动时的 `SessionStart` 执行成功。 [DeepSeek 的 Claude Code 集成说明](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/)

在首个读取请求发出后，向宿主发送原生中断。收到宿主确认后，首个读取仍回传了一条带错误标记的结果，随后原轮结束。原轮结束前未观察到新工具调用。接着在同一会话读完三个文档，报告的四条安装命令均指向正式发行提交，也正常回答了下一项请求。进程退出后，以同一会话 ID 执行 `--resume`，恢复时的 `SessionStart` 通过，随后实际读了 `LICENSE` 并正确摘要了 NOTICE 条款。两次进程均自然退出，任务文件保持原样。 [Claude Agent SDK 的原生中断示例](https://github.com/anthropics/claude-agent-sdk-python/blob/main/examples/streaming_mode.py)

该结果覆盖上述只读 CLI 会话、原生中断和接续。文件写入后的迟到效果、其余 Hook 事件、Accord 的增量收益以及 Desktop Code 的实际加载与权限仍待各自取证。桌面使用独立的第三方推理配置，需在实际 Code 会话核对后端版本、模型路由和插件加载。 [CC Switch 桌面提供商说明](https://ccswitch.io/en/docs?item=claude-desktop&section=providers) · [Claude Code 桌面版本说明](https://code.claude.com/docs/en/desktop#claude-code-version-in-the-code-tab)

<a id="claude-code-current-candidate"></a>

### 2026-11-19 基于 Accord 3.3.18 的本地候选

`3.3.18-claude-dev.1` 使用主分支 `71541c3dd52b8ac61de9b14a2a2ea7a688ac6a3c` 对应的通用指导与当时的本地 Claude 适配源码。该分支的 ChatGPT/Codex 包与 3.3.18 发行提交 `699b24c3092edbafc431f0760a539eeca3f175e3` 的包源码相同。生成包保留当时的入口 Skill 正文、元指导和可复用的专业职责，按 Claude 接口提供能力、连续性和生命周期说明。该次 `build.json` 记录逐文件摘要，包括当时本地构建器和 Hook。历史 `3.2.0-dev.16` 的观察保留原身份。[实现与构建](../../docs/architecture.md#local-claude-code-candidate)

| 观察 | 实际结果 |
| --- | --- |
| 包与插件目录 | Claude Code 2.1.328 的严格校验均通过。首轮本地目录缺描述，补齐后复验通过。公开目录的图标与安装文案提示不影响本地校验结果。 |
| 加载和指导 | 在有空格的本地路径用 `--plugin-dir` 加载候选。会话报告五项 Accord Skills。原生 `SessionStart:startup` 和后续 `SessionStart:resume` 均返回当前完整入口正文及英文元指导。 |
| 取消和迟到结果 | 通过 CLI 的流式会话在第一条 `Read` 请求后发送原生中断。发送后 103 毫秒收到确认，147 毫秒观察到原轮终态。已派发的读取在确认后回传错误。原轮结束前没有后续工具调用。 |
| 同会话恢复和新任务 | 同一会话的续作实际读取三个公开文档，核对四条安装命令及同一精确提交。随后读 `LICENSE` 完成新请求。进程退出后，对同一会话执行 `--resume`，完成 `NOTICE` 的真实读取和摘要。两次进程均自然退出，源文件及用户提供商配置的字节保持一致。 |
| 桌面准备 | 当时本机登记 Squirrel 6.6395.0，当前用户无 MSIX 注册。第三方入口缓存中的 2.1.326 后端单独执行原生目录严格校验通过。后续的实际会话见[桌面任务](#claude-code-desktop-guidance)。 |

Windows 独立 CLI 2.1.328 使用已有 DeepSeek `deepseek-flash` 路由。原件标识为 `accord-claude-3318-20261119`，两份原生事件日志及摘要与构建清单分别核对。以上行为属于只读 CLI 路径；写入类迟到效果、交互式终端取消、真实子代理及压缩事件、桌面接续和启用带来的增量价值分别取证。阶段收尾以本地候选和已证范围为准。 [原生中断](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode#interrupt-a-response) · [桌面内核](https://code.claude.com/docs/en/desktop#claude-code-version-in-the-code-tab) · [MSIX 部署](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows)

用户反馈当天更新了独立 CLI 后，重新读取仍是实测的 2.1.328，桌面第三方入口仍只有 2.1.326 缓存。2.1.328 的发行记录涉及自动压缩后系统提示重建及恢复时延后工具调用的宿主控制。桌面实际采用需结合 `/status`、Hook 输出和已派发工具的后态核对，另验 GUI 进程可用的 Node.js。 [2.1.328 发行说明](https://github.com/anthropics/claude-code/releases/tag/v2.1.328)

<a id="claude-code-windows-packaging"></a>

### 2026-11-19 Claude Desktop Windows 安装形态核对

用户此前用过微软商店版，目前为方便汉化采用 Squirrel。汉化项目记录了 Win32 Squirrel、官网通用安装器和微软商店的分发差别，以及两种形态同机时显式选定资源路径的方式。复用该项目的注册 MSIX 6.6395.0.0 原始界面清单，从同版 Squirrel 6.6395.0 的未修改 `ion-dist.asar` 备份逐项读取 68 个脚本成员并计算 SHA256，全部与清单一致。核验摘要为 `MSIX-RESOURCE-PARITY.json`。[汉化项目的实机记录和安装说明](https://github.com/yiheng8023/claude-chinese/blob/969e9ef3a944341a3fe8f4e990143b4bf242f2bd/README.md#L41-L88)

2026-11-18 的 Windows AppX 日志确认同版 MSIX 于北京时间 12:24 部署成功，19:10 移除成功。Squirrel 6.6395.0 的独立安装目录内程序文件创建于 18:51，处于 MSIX 登记时段内。由此核实同机安装曾并存。证据覆盖本机安装状态。

此结果支持复用所查的界面资源证据。实际 Code 内核按会话更新，本地插件作用域、Hook 执行和操作结果按实测确认。Anthropic 为 Windows MSIX 提供单独的部署和管理方式。当前验证优先使用已有 Squirrel 的本地 Code，包装相关差异在影响目标场景时补测。 [Windows 部署说明](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows) · [Code 内核版本](https://code.claude.com/docs/en/desktop#claude-code-version-in-the-code-tab)

r120 本机核对了 Microsoft Store 商品 `9P6K58THS811`。WinGet 把现有 Squirrel 6.6395.0 匹配到同一商品。按确切商品执行商店安装后 WinGet 报成功，AppX 中无 Claude 包注册，启动项仍只有原先的 Squirrel。Anthropic 官方签名的单独部署包实际为 5.11492.5.0，注册返回 `0x80073D28`，指出打包服务要求管理员权限。Squirrel 启动器、界面包、快捷方式及三份被测 Claude 配置摘要一致。原始结果见 `MSIX-RESULT.json`。[Microsoft Store 商品](https://apps.microsoft.com/detail/9p6k58ths811) · [Anthropic 的 Windows 部署说明](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows)

当前以已实测的 Squirrel 作为 Windows 本地 Code 的适配及验收入口。若 MSIX 用户反馈或宿主更新指向实质差异，按具体应用版本、Code 内核、候选包版本和可复查的操作结果补验。沿用与包装无关的同版原件，宿主或 Accord 的差异按实际成因处置。

本机 Squirrel 已进入本地 Code，选中仅含五份公开项目文件副本的临时工作区，界面显示现有 DeepSeek 模型。新工作区触发原生信任提示。在另一份空测试配置中，用桌面缓存的 2.1.326 执行原生 `plugin marketplace add --scope local` 与 `plugin install --scope local`，两步均通过。候选目录和启用项写入临时项目的 `.claude/settings.local.json`，真实用户配置的被测文件摘要保持一致。此项核验覆盖原生加载配置和作用域，实际桌面会话需在用户信任的工作区另取加载和行为证据。 [设置范围](https://code.claude.com/docs/en/settings) · [桌面插件作用域](https://code.claude.com/docs/en/desktop#install-plugins)

<a id="claude-code-desktop-guidance"></a>

### 2026-11-19 实际桌面任务和指导截短修复

用户信任临时项目后，Squirrel 6.6395.0 的本地 Code 以 2.1.326 运行候选。首轮实际执行三次只读操作，原始文档中的四条发布安装命令指向同一完整提交。三次读取先于停止记录返回，原报告当时仍处于生成阶段。停止后到下一条用户输入之间未出现新工具调用或工具结果。同会话续作复用了核查结果，随后读取 `NOTICE` 完成新任务。五份测试文档摘要一致。原生请求标签为 `claude-sonnet-5`，回复记录为 `deepseek-flash`；文档结论另从源文件复核。

`3.3.18-claude-dev.1` 的 `SessionStart` 返回 11,213 个字符。桌面转交的上下文只保留了开头 1,961 个连续匹配的字符，完整职责未到达首个请求。`3.3.18-claude-dev.2` 复用当前 Skill 的关键段落，附接续职责和 Skill 入口，完整元指导与协调 Skill 随包保留。实际桌面首请求包含全部 1,580 字节的短指导，原生记录也确认临时项目的 `AGENTS.md` 与随包中文元指导相同。新版独立 CLI 复验中断、同会话续作、新任务及冷恢复。中英文元指导单独移到另一目录仍可由相对链接找到同附的中文原文。产物与原件核对记录在 `DESKTOP-DEV1-RESULT.json`、`DESKTOP-R2-RESULT.json` 和 `r2-cli`。

本次桌面行为观察适用于所测本地只读路径。桌面写入、其它模型的任务质量、MSIX 特有行为和启用增益按具体问题另取证。 [Claude 的 AGENTS.md 加载说明](https://code.claude.com/docs/en/memory#agentsmd)

<a id="claude-code-cli-interrupted-write"></a>

### 2026-11-19 CLI 权限与中断后的实际写入

独立 Windows CLI 2.1.328 以 `deepseek-flash` 加载 `3.3.18-claude-dev.2`。只开放 Bash，MCP 为零。任务用已知内容的合成文件和前台写入器，单独观测原生事件、进程和磁盘。

- 写入器将首个标记刷盘后发出原生中断。13 毫秒收到确认，25 毫秒收到轮次错误终态，此时写入进程仍存活。619 毫秒首次观测到该进程退出。跨过预定 6 秒提交点后于 8.009 秒读回，首个标记保留，第二个文件始终未出现。相同脚本的无中断对照产生了第二个文件。
- 拒绝分支的原生 `permission_denials` 命中模型实际请求的工具调用，工具返回错误，目标文件不存在。随后同一会话的新任务成功写出精确预期内容。完整重跑自然退出，所属进程数为零。
- 首轮观测器在拒绝分支遇到非对象消息字段后异常，先前的写入进程已单独核对退出，余下进程由 Job 回收。修正观测器后的完整重跑完成两次读回。两轮临时配置已释放，被测的正式提供商设置摘要相同。原件保留于 `accord-claude-write-20261119-01`，核验摘要为 `VERIFIED.json`。

对照限定为该受控写入指令与停止时点，用来核查实际效果。内建 `Write`、桌面与远端副作用，以及 Accord 启用与未启用的差异各需对应证据。[原生中断接口](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode#interrupt-a-response)

<a id="claude-code-desktop-write"></a>

### 2026-11-19 Windows 本地 Code 的写入权限与后续任务

Windows Squirrel 6.6395.0 使用内置 Claude Code 2.1.326 与 `deepseek-flash`，实际权限模式为 `acceptEdits`。按 r122 源码重建 `3.3.18-claude-dev.2`，市场清单及 14 个包内成员与此前候选逐字节相同。通过宿主原生项目级登记加载。原生 Hook 返回的指导与构建产物相符，并完整进入首个实际模型请求，共 1,580 个 UTF-8 字节。

- 第一条任务指向两个合成目标。内建 `Write` 成功写入允许的文件，内容通过独立读回。宿主按项目权限明确拒绝了第二次 `Write`，原生工具返回错误，受限目标未出现在磁盘上，也未改走替代写入。
- 同一会话接到独立的新任务后，内建 `Write` 成功写入另一允许的文件，字节与预期一致。任务终止正常，所属桌面窗口退出。临时插件及市场登记已移除，试验写入与项目设置已清理，受观测的原有配置文件摘要保持一致。

原件保留于本地 `accord-r122-desktop-write-20261119-01`，核验摘要为 `VERIFIED.json`。结果适用于这条 Windows 本地 Code 路径和受测权限。进行中写入被取消后的实际停止与迟到效果，按桌面入口继续取证。

<a id="claude-code-foundation-fallback"></a>

### 2026-11-19 完整协调 Skill 读取随包元指导

独立审查发现 dev.2 原样沿用了 Codex 的完整协调 Skill。其开头将英文元指导视为已由原生入口送达，但 Claude Hook 只发送短指导。dev.3 使用 Claude 自己的开头，明确复用会话中已有元指导或读取随包英文译文。原职责继续从共同来源生成。与 r122 实测包相比，14 个成员中只有插件版本清单和完整协调 Skill 的摘要变化，市场清单和 Hook 脚本字节一致。

- 原生 CLI 2.1.328 对插件和市场分别通过严格校验。构建回归模拟 `NOTICE` 写入失败，检查当时两个发现清单均未出现，清理后同一目标可以重试。生命周期隔离回归用临时增补模拟宿主说明变化。
- 在没有项目级元指导文件的临时目录，以 `deepseek-flash` 显式请求采用协调 Skill。两次只读任务的原生记录均有 1,580 字节短指导和成功的 Skill 调用。第一轮未观察到参考读取。第二轮调整测试的权限表述，并保留会话记录以复核正文送达，确认完整 Skill 进入会话、同一任务随后成功 `Read` 随包英文译文。两轮均正常结束。条件并非完全相同，实际读取有差异，尚无法将差异归因于某一个条件。
- 两个运行范围自然退出，Windows Job 活跃进程归零，临时工作区和配置目录已回收，原提供商配置摘要一致。摘要保留为 `CLI-01-OBSERVED.json`、`CLI-02-OBSERVED.json` 和 `build.json`。桌面端后继候选的实际读取仍需观察。

在 r124 重建 dev.3，构建记录与 r123 一致，插件和市场分别通过独立 CLI 2.1.328 的严格校验。当前 Desktop 会自动引入用户级指导和其它已启用 Hook。在任务级设置中独立保留 Accord Hook，同时排除这些其它自动行为的路径尚未核实。保留桌面实测缺口和既有用户配置，配置摘要复核一致。本轮的 [CLI 观察](#claude-code-foundation-fallback) 和 [dev.2 桌面观察](#claude-code-desktop-write) 各沿原入口和条件引用。

<a id="claude-code-desktop-isolation"></a>

### Windows Squirrel 的 Desktop Code 隔离条件

Anthropic 为 Desktop 本地 Code 记录了 `CLAUDE_CONFIG_DIR`，设置后应完全退出并重开 Desktop。它有应用启动侧的设置入口，与在普通保存的 Local 环境中逐会话添加变量的入口有别。该目录承载 Code 的设置、历史和插件。Desktop 同时可引入自身的 MCP 配置及账户连接的能力，实际加载来源须分别核对。[本地会话的环境变量](https://code.claude.com/docs/en/desktop#environment-variables-in-local-sessions) · [共享配置](https://code.claude.com/docs/en/desktop#shared-configuration) · [设置文件](https://code.claude.com/docs/en/settings#settings-files-and-who-they-affect)

对本机 Squirrel 6.6395.0 的程序包只读复核，Code 根的选择分支会读 `CLAUDE_CONFIG_DIR`。Windows 的 `claude_desktop_config.json` 还有以 `LOCALAPPDATA` 为根的查找分支，相关代码与保留的本地原始备份一致。因此，同用户的隔离启动若只换 Code 根或独立窗口，仍需从真正启动的本地 Code 会话核 Desktop MCP 的有效来源。`--setting-sources` 等独立 CLI 参数在 Desktop 的公开对照中没有等效入口。[CLI 参数对照](https://code.claude.com/docs/en/desktop#cli-flag-equivalents)

安全的验证条件是独立的设置和工作目录、已有认证的适用模型入口，以及生效的工作区信任与宿主管理策略。先核 `/status` 的桌面实际引擎，读回配置根、候选注册、Hook、Plugin、Skill 和 MCP 来源，再核任务实际行为。若同用户无法获得这些条件，可在已有授权的干净 Windows 测试用户或主机按同版 Squirrel 复验，并留意账户同步。本轮只完成官方资料和本机程序路径的核查。dev.3 的桌面加载和读取仍须实机绑定。[Desktop 内核版本](https://code.claude.com/docs/en/desktop#claude-code-version-in-the-code-tab)

r125 对 Squirrel 6.6395.0 的本机隔离准备做了子进程对照。一个临时子进程实际继承了独立的 `CLAUDE_CONFIG_DIR`、`APPDATA` 和 `LOCALAPPDATA`，Windows 的已知文件夹查询仍返回现有用户的本地与漫游应用数据目录。程序包中也核到相应的应用数据回退路径，Squirrel 入口还可能启动原安装的更新器。已检查的三处 Desktop MCP 配置文件各有零个本地服务器。账户侧连接和 Local Code 实际采用的根仍需读回。这一轮未进入 Desktop Code，也未取得 dev.3 的桌面行为证据。当时尚无已核可用且获准使用的独立 Windows 环境。[Windows 已知文件夹](https://learn.microsoft.com/en-us/windows/win32/shell/known-folders) · [Desktop MCP 来源](https://code.claude.com/docs/en/desktop#mcp-servers-from-the-claude-desktop-chat-app)

<a id="claude-code-windows-test-profile"></a>

#### r126 独立用户预检（2026-11-20）

经用户授权创建专用的标准本地 Windows 用户。以该用户令牌启动后台进程并加载其配置文件，核到本地和漫游应用数据的系统已知文件夹都位于独立用户目录，环境变量也指向实际根。目标进程可见机器级 Node 路径，并读回 dev.3 的 14 个成员和市场清单，摘要与原候选一致。候选及市场均通过 CLI 2.1.328 的严格校验。预检时该用户目录中尚未观察到 Squirrel 应用入口或 Claude 本地、漫游配置。[Windows 用户账户](https://support.microsoft.com/en-us/windows/security/identity-signin/manage-user-accounts-in-windows) · [Windows 已知文件夹查询](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetknownfolderpath)

官方 Win32 x64 下载入口本次返回版本 `5.11492.5` 的引导器，文件的 Anthropic Authenticode 签名有效，目标用户读回的 SHA-256 一致。历史观察的 Squirrel `6.6395.0` 保持原范围，同版官方安装入口仍待核。采用当前引导器时，以目标桌面实际安装的版本和 Local Code 的 `/status` 建立当次基线。独立用户的后台预检已完成。交互登录、桌面安装和实际运行、适用模型授权及工作区信任仍待对应读回或确认。[官方 Win32 下载](https://releases.claude.com/api/desktop/win32/x64/exe/latest/redirect) · [桌面部署说明](https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows) · [Desktop Code 引擎版本](https://code.claude.com/docs/en/desktop#claude-code-version-in-the-code-tab)

<a id="claude-code-isolated-desktop-install"></a>

#### r127 独立标准用户安装与启动（2026-11-20）

按授权以同一个官方引导器在专用标准用户内安装。安装前由目标令牌确认独立配置目录，未发现已有的 Squirrel 或 Claude MSIX 注册。安装后读回签名有效的 Squirrel `5.11492.5`、启动入口和原生更新器，目标用户的 MSIX 注册仍为零。随后的独立进程读回及实际窗口路径均指向该用户的 `app-5.11492.5`。原 Squirrel `6.6395.0` 的行为证据沿旧条件引用。

本轮使用备用用户令牌启动，已确认桌面进程及窗口身份。窗口文档尚未呈现可核的本地 Code 状态，跨用户激活复试也未成功。合成工作区已准备，等待可操作的目标窗口、有效模型与工作区信任后读取实际内核、登记候选并取完整的 dev.3 行为证据。安装、启动和待取得的 Code 实测各依其原件记录。[Desktop Code 内核读回](https://code.claude.com/docs/en/desktop#claude-code-version-in-the-code-tab) · [备用用户令牌的组策略边界](https://learn.microsoft.com/en-us/troubleshoot/windows-client/group-policy/group-policy-not-applied-user-account-runas)

<a id="claude-code-isolated-desktop-gateway"></a>

#### r128 桌面更新与测试模型准备（2026-11-20）

再次打开隔离账号的应用时，运行进程与窗口已指向 Squirrel `6.6395.1`，该版主程序的 Anthropic Authenticode 签名有效。窗口重新创建后，跨 Windows 用户激活仍失败。运行中的桌面外壳和真实 Local Code 会话继续分别核对。

用户授权本次合成试验复用现有 DeepSeek。CC Switch 4.0.35 的本机 Desktop 网关已核对到当前 DeepSeek 记录，`claude-sonnet-5` 的上游映射为 `deepseek-flash`。本机网关的鉴权模型列表回读通过。标准用户写入 Claude 托管注册表路径被 Windows 拒绝，随后确认目标配置项仍不存在。改走 Claude 官方本地导入，将仅含测试模型配置和本机网关凭据的临时文件放入隔离用户的私有目录。DeepSeek 上游密钥继续由 CC Switch 管理。实机仍待进入该用户可操作的窗口、应用配置并信任合成工作区；尚无本轮的 Code 内核或推理结果。[CC Switch 桌面模型映射](https://github.com/farion1231/cc-switch/blob/v4.0.35/src-tauri/src/claude_desktop_config.rs) · [Claude 本地配置导入](https://claude.com/docs/third-party/claude-desktop/in-app-configuration#set-up-a-device-without-mdm)

在本轮后续操作中，用户手动导入配置，界面进入 Gateway。Windows 重启后的首次重开出现 `Claude Desktop failed to launch`。用同一启动方式改跑只读探针，确认备用账户进程继承了外层账户的环境。改用由 Windows 为备用账户生成的环境，核回该账户的用户目录、本地和漫游 AppData，同一桌面程序成功打开。用户截图确认 Gateway 仍有效显示，并在 Code 新建页选中本地合成工作区。仍待对应会话核内核、有效信任、加载及推理结果。[Windows 进程环境](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithlogonw) · [Code 内核读回](https://code.claude.com/docs/en/desktop#claude-code-version-in-the-code-tab)

同时读回本机独立 Codex CLI `0.171.0`、ChatGPT 客户端 `26.1117.3838.0`（所带 Codex CLI `0.171.0-alpha.13`）和独立 Claude CLI `2.1.329`。后者对同一 dev.3 插件及市场分别原生严格校验，两个退出码均为零。校验器另给出目录上架文案和图标提示，不改变本地校验结果。旧会话证据仍使用其实际运行版本。[Codex CLI 发行说明](https://github.com/openai/codex/releases/tag/rust-v0.171.0) · [Claude CLI 发行说明](https://github.com/anthropics/claude-code/releases/tag/v2.1.329)

<a id="claude-code-dev3-desktop-read"></a>

#### r128 桌面工作区与 dev.3 指导实测（2026-11-20）

Gateway 新建页未列出 `/status`。从带标签 `R128-DESKTOP-DEV3-001` 的真实只读轮次、原生会话文件和运行进程核实，隔离 Squirrel `6.6395.1` 的本地 Code 内核为 `2.1.326`，实际返回模型为 `deepseek-flash`，权限模式为 `auto`。工作区信任已实际记录，原生项目设置选择本地 dev.3 市场和插件，候选的 14 个包内成员及市场清单与构建摘要一致。已检查用户、项目及三处 Desktop 本地 MCP 配置，均无登记。所查工作区和测试用户路径内未发现 `AGENTS.md` 或 `CLAUDE.md`。

- 首轮原生 `SessionStart` 成功，标准输出中的 1,580 字节短指导与候选 Hook 的相同启动输入逐字节匹配。唯一工具操作为读取合成记录，回答正确指出记录缺少 Code 内核版本的读回证据。
- 同一会话的 `R128-DESKTOP-DEV3-002` 实际调用协调 Skill，原生记录含 Skill 正文。随后 `Read` 成功返回精确 dev.3 候选包路径下的英文元指导及合成记录。原始合成文件在两次观察中的摘要一致。模型声称完成与原生工具结果分别取证。
- 随后的独立任务 `R128-DESKTOP-DEV3-003` 使用本项目明示的允许和拒绝规则，按当前权限模式实际派发两次原生 `Write`。允许目标的内容经磁盘读回正确。拒绝目标回传权限错误，文件未出现，此轮无其他工具调用。原始合成文件继续保留。
- 两次 75 秒前台写入均得到成功结果，目标文件如期出现。第二次用户确认未及时按下停止。之后的 `005` 读取独立完成，这部分对应自然完成后的新任务。
- `004C` 将原定写入窗口延长至 150 秒。原生中断记录发生在前台写入器运行期间，Bash 回传中断错误。系统采样读回写入进程退出，并在原定执行时间之后再次确认目标文件缺席。接续的独立只读任务 `006` 成功读回允许目标的一行内容，同一会话正常完成。证据分别来自原生轮次、操作系统进程和磁盘。
- 取证范围为该隔离 Windows 本地 Code 会话及实际使用的包、模型、命令和观察窗口。普通任务是否自动采用完整元指导和实际出站请求组装仍需独立证据。临时导入文件在路由实测后已移除。一次自然完成轮次还记录了 `mcp__ccd_turn__wrap_up`，后续对照以实际工具定义及投递来源为准。
- 实测结束后读回隔离账户的 Claude 桌面与 Code 进程均已退出。本次导入的 Gateway 配置、项目级插件和市场登记、信任以及临时权限均已撤回。合成产物收作证据，工作区的原始合成文件摘要一致。共享 CC Switch 监听仍在。

<a id="claude-code-glm-flash-r128"></a>

#### r128 智谱 Flash 两条接入路径复验（2026-11-20）

- 独立 Claude CLI `2.1.329` 使用专用配置根、空 MCP 配置和合成文件。实际请求通过智谱 Anthropic Messages 接入，返回 `glm-5.3-flash`。初始化记录发现 `3.3.18-claude-dev.3`，候选 14 个包内成员与构建摘要一致。原生 `SessionStart` 正常，1,580 字节指导摘要匹配；唯一 `Read` 工具调用读回合成文件，最终回复与原件完全一致，过程正常退出。本机使用的原 CLI 设置在前后读回一致。[智谱的 Claude Code 接入](https://docs.bigmodel.cn/cn/coding-plan/tool/claude)
- CC Switch `4.0.36` 的 Desktop 代理模式从设备活动状态选择路由。旧直连选择和数据库旧当前标记对应其他配置。按实际活动路由读回 `claude-sonnet-5` 映射到智谱 `glm-5.3-flash`。初次用 Desktop 配置文件中的保存值查询本机模型目录，返回 401。按网关的原生认证来源取本机令牌后，模型目录返回 200。另发一条合成 Messages 请求返回 200，响应模型为 `glm-5.3-flash`，内容匹配，活动路由前后读回一致。[路由选择源码](https://github.com/farion1231/cc-switch/blob/v4.0.36/src-tauri/src/mode/current.rs#L63-L85) · [网关处理器](https://github.com/farion1231/cc-switch/blob/v4.0.36/src-tauri/src/proxy/handlers.rs)
- 主账号 Squirrel 安装索引和可执行文件均显示 `6.28899.2`。初查时该账号的 `2.1.328` 缓存仍在分段下载，主账号入口供汉化适配。实际 Code 会话在独立标准用户实测。
- 独立标准用户用 Squirrel 更新器从本机已核验的官方包更新到 `6.28899.2`。更新后安装索引中的包名、SHA1 和长度均与来源一致，实际安装的 `Claude.exe` 与包中签名有效的文件逐字节匹配。通过 Squirrel 安装入口打开新版，核对实际 Code 进程与原生记录均为 `2.1.328`，两轮实际返回模型均为 `glm-5.3-flash`。
- 用户确认本轮合成工作区信任后，`R128-DESKTOP-628899-01` 的 `SessionStart` 原生执行成功，短指导与候选的 1,580 字节内容一致。模型调用 dev.3 协调 Skill 并用原生 `Read` 正确读回探针。首轮明确要求的英文元指导未单独读取。同一会话的 `R128-DESKTOP-628899-02` 只补验该项，原生 `Read` 的文件与候选包成员摘要一致，返回内容及最终答复与原文一致。两轮正常结束，原合成文件摘要一致。
- 测试客户端正常退出。精确进程读回为零，临时网关、导入文件、工作区信任及项目权限和市场登记均已撤回。升级包与提取文件的临时副本已移除，合成探针及脱敏见证保留。执行中取消、写入权限和迟到效果沿 `6.6395.1` 的原测试条件引用。普通任务的隐式采用另按真实任务观察。

脱敏见证包括 `cli-witness.json`、`cli-native-witness.json`、`desktop-authenticated-catalog.json`、`desktop-glm-message-witness.json`，以及新版隔离桌面的 `updated-desktop-witness.json`、`native-observation.json`、`guidance-observation.json` 和 `cleanup-witness.json`。合成任务用于兼容性核对，供应商改变后的成本或 Accord 增量另按同条件的真实对照判断。

<a id="claude-candidate-publish-rollback"></a>

### r129 本地候选的构建回滚（2026-11-20）

在独立临时目标注入最终市场清单移动失败，旧构建留下 CLI 插件清单和构建记录。第二次构建同一路径被拒绝。自动检查也在旧代码复现了构建记录移动失败后的半成品。修复把构建记录和完整包置于市场清单之前。在移动失败时，按阶段回收仍与已构建内容一致的产物。已发生变化的路径保留并报告。输出为空并被移除后可重试同一路径。

Windows 的 10 项 Claude 适配测试通过，Ubuntu WSL 中两项发布故障回归通过。重建的 14 个包内成员和市场清单摘要与 r128 实测的 dev.3 一致，构建器的源码摘要更新。Claude CLI 2.1.329 的插件和市场严格检查均通过。目录工具报告缺发布图标及本地候选未提供公开市场安装行的提示，两项均不改变严格检查结果。运行结论沿原候选对应的实际会话。[开发架构](../../docs/architecture.md#local-claude-code-candidate)

<a id="claude-code-desktop-preflight-card"></a>

### dev.3 Windows Squirrel 本地 Code 预检与收尾卡

适用于下一次已获授权的隔离实测。dev.3 已在 Squirrel 6.6395.1 验证插件加载、指导读取、写入取消及其后态，在 Squirrel 6.28899.2 复验智谱路由下的只读链路。更换包、入口、版本或模型后，按实际受影响的步骤复验。[dev.3 桌面记录](#claude-code-dev3-desktop-read) · [智谱只读复验](#claude-code-glm-flash-r128)

#### 启动前

1. **核准候选和范围。** 读取构建记录、市场清单、14 个包成员摘要及插件与市场各自的原生校验。固定实际试验用的 Squirrel 安装、测试工作区和候选版本。包身份或登记权限有缺口时，暂停登记。
2. **核准隔离入口。** 清点候选、临时工作区、启动设置和配置基线，确认已有适用模型权限、工作区信任及管理策略。使用 Desktop 启动侧的 `CLAUDE_CONFIG_DIR`，完全退出再启动。保存的 Local 环境给会话传变量，仍须从实际启动的 Desktop 核 Code 与应用数据根。同用户无法排除既有指导、Hook 或账户连接时，暂停该入口的实机任务，待有可用且已获授权的独立 Windows 用户或主机再验证。

#### 实机核对

3. **读回有效配置和能力。** 用本地 Code 的原生会话及进程记录确认 Squirrel 和 Code 引擎版本、模型、权限、Code 配置根、项目级登记、指导、插件、Hook 和 Skill。另核 Desktop 的应用数据路径、MCP 配置与账户连接的实际来源。关键来源仍未知时，暂停依赖该隔离的行为试验。
4. **检查 dev.3 指导是否生效。** 在无预载完整元指导的受控任务中显式选协调 Skill，核短指导进入首个实际模型请求、完整 Skill 实际送达，以及原生 `Read` 返回随包英文译文。缺少任一证据时，保留相应环节待核。
5. **核权限和后续任务。** 仅在已确认权限边界后使用合成目标。记录内建 `Write` 的允许及独立字节读回、受限请求的原生拒绝及文件缺席，检查是否有替代写入。另起同会话的新任务，验证新的允许文件。任一目标或权限有疑问时，暂停写入。
6. **查清取消后的实际效果。** 从原生事件确认取消发生在授权写入进行中，单独记录取消回执、原轮终态、所属操作或进程实际停止、目标文件读回及观察窗口内的迟到效果。缺少哪个环节就保留该环节待核。

#### 收尾

7. **收回本次资源并核对原状。** 先确认任务及所属进程结束，再移除本次登记、临时文件、工作区和配置。撤销本次启动设置，读回资源清理结果，并比较原有配置与信任状态。仍有写者或归属不清时暂停相应清理，记录实际后态。

此卡为两份独立草稿经匿名复核后的维护合稿。[两组原始结果与范围](../evaluations/accord-toggle-v1.md#desktop-preflight-pair-3318)

<a id="accord-foundation-without-agents"></a>

### r127 元指导由 Accord 独立送达的范围

在独立 Codex 配置和工作区使用 CLI 0.170.0，发行版 3.3.18 的 30 个包成员核验一致。原生 `thread/start` 返回零个指引文件来源。开启并按规格摘要信任此次试验范围的 Hook 后，在首个请求第 4 项的 `developer` 消息中核到完整的英文元指导与协调正文，合计 12,144 UTF-8 字节，逐字节匹配对应的原生 Hook 输出。它在第 5 项的任务输入之前。请求由本机固定回包接收，原生轮次完成，未使用付费模型。完整送达支持 Accord 作为本地 Codex 的早期指导来源，实际决策和效果还需相应行为证据。宿主层级和授权规则继续适用。[Codex 启动 Hook](https://learn.chatgpt.com/docs/hooks#sessionstart) · [Codex 指引文件发现](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

Claude dev.3 的启动 Hook 给出短指导与读取定位。隔离 CLI 和 Windows 本地 Code 均已实测显式采用协调 Skill 并按需读取随包译文。普通轮次的完整前置送达还需独立证据。Claude 自身的 `CLAUDE.md` 和有条件的 `AGENTS.md` 发现规则也应计入实际来源。[dev.3 CLI 观察](#claude-code-foundation-fallback) · [dev.3 桌面实测](#claude-code-dev3-desktop-read) · [Claude Hook 的附加上下文](https://code.claude.com/docs/en/hooks#add-context-for-claude) · [Claude 指引文件发现](https://code.claude.com/docs/en/memory#when-claude-code-reads-agentsmd)

本机 Codex 用户级 `AGENTS.md` 的核心正文与随包英文元指导一致，项目 `AGENTS.md` 则保有独立的仓库职责。Claude 用户级 `CLAUDE.md` 为另一实际来源。用户级副本在 Accord 未启用或更新后 Hook 尚待重新允许时仍有作用。本轮按所核入口使用单一送达证据，现有指引文件保留。随包中文原文继续对应 CALIBRATION 的来源稿。
