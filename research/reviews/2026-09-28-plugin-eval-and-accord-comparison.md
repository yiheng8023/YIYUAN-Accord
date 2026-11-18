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
