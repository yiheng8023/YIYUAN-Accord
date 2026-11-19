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
