# YIYUAN Accord 3.2 开发计划与进度

由 `product/development.json` 派生；修改源数据后同步本页，校验会拒绝不一致。

当前为未冻结的开发基线；目标是完成验收后发布新的 3.2，不改写 3.1。
动态自适应是原有核心承诺；驱动宿主实现必要结果，按证据保留、合并、删除或补强，暂缓增加宿主适配。

## 工序与验收映射

| 工序 | 当前进度 | 执行步骤 | 验收出口 |
|---|---|---|---|
| 源头校准与继承基线 | 本地实现，未发布 | 保留历史证据；校准立意、成功定义及条件策略；把现有职责列为必要性评审清单，建立保留、合并、删除或补强后的工序与验收映射。 | 源头与映射的本地回归通过；明确尚未证明宿主功能、价值或发布就绪。 |
| 系统短板与工程优化 | 本地实现，未发布 | 先核对官方原生能力、当前宿主暴露和 Accord 职责映射；按同一事实源派生索引与影响关系，列明缺口及验收，再追踪薄弱依赖并测量优化。 | 已定位工程问题与映射在本地回归通过；未闭合的实际执行、恢复和适应职责转入下一工序，不据此宣称全部系统质量已验证。 |
| 模型、宿主原生覆盖与运行时拓扑核验 | 进行中 | 从实际需求与能力矩阵选择关键职责；按所需可靠性核对触发者、执行者、必要状态和故障接管者，选择适合的执行及状态拓扑；先验证宿主原生运行时，缺失时组合或实现必要机制。 | 普通入口实际兑现同一功能与质量；需确定触发、持续状态或恢复的职责有相应运行时支持，Skill 宣示、模拟图或评估器代劳不计完成。 |
| 动态适应、干扰与故障验收 | 待开展 | 按声明选择原生对照、最小可交付组合及受控混合环境；验证环境变化、冲突、纠正、中断、恢复和完整包生命周期。 | 普通入口产生可独立观察的效果；正向外援、负向干扰及评估器救援均被识别；所需功能与后置状态全部有证据，不能取平均掩盖短板。 |
| 3.2 定版、发布与收尾 | 待开展 | 冻结精确候选；完成受影响的完整包证据、独立评审和托管检查；依用户条件授权发布新的 3.2。 | 精确 SHA、包、版本与公共发布对应；发布后检查及任务残留闭环；既有标签、发布与失败历史保持原样。 |

## 完整职责覆盖

这是现有职责的必要性评审清单，不是必须原样保留的功能集。保留项需当前效果证据，合并或删除项需说明需求判断及验收变更。

| 职责 | 所属工序 | 历史需求与反例参考 |
|---|---|---|
| 目标、授权与用户纠正 | 源头校准与继承基线、3.2 定版、发布与收尾 | GT-03, GT-04, GT-10, GT-13 |
| 环境感知与自身能力识别 | 模型、宿主原生覆盖与运行时拓扑核验、动态适应、干扰与故障验收 | GT-08, GT-14, GT-19 |
| 按需研究、学习与复用发现 | 系统短板与工程优化 | GT-15 |
| 关系、动态索引、路线与形态选择 | 系统短板与工程优化、模型、宿主原生覆盖与运行时拓扑核验 | GT-13, GT-16, GT-17 |
| 执行、配置与代码操作 | 系统短板与工程优化、模型、宿主原生覆盖与运行时拓扑核验 | GT-02, GT-11, GT-16 |
| 源头变更与全局一致性 | 源头校准与继承基线 | GT-17 |
| 纠错、经验吸收与受控演进 | 动态适应、干扰与故障验收 | GT-05, GT-18 |
| 故障恢复与回滚 | 模型、宿主原生覆盖与运行时拓扑核验、动态适应、干扰与故障验收 | GT-18, GT-20 |
| 上下文与任务连续性 | 模型、宿主原生覆盖与运行时拓扑核验、动态适应、干扰与故障验收 | GT-07, GT-21 |
| 资源管理与清理 | 系统短板与工程优化、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-09, GT-12 |
| 安装、更新与卸载生命周期 | 动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-20 |
| 原生接替、旁路与退役 | 模型、宿主原生覆盖与运行时拓扑核验 | GT-01, GT-19 |
| 结果验证、独立证据与实际价值 | 源头校准与继承基线、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-04, GT-06, GT-14 |

## 原生能力与 Accord 职责矩阵

资料核对时间：`2026-09-05T00:58:21Z`。这是现有两宿主的开发评审快照，不是永久能力目录或当前行为验收。
原生项的条件和效果尚需在实际客户端、模型路线及权限下核对。接口存在、配置可见、实际执行和结果成立分别取证。

| 原生能力 / 来源 | 能力层 | 已核对的接口或能力 | 适用条件与未证实边界 |
|---|---|---|---|
| `cx-state` [模型、能力和配置查询](https://learn.chatgpt.com/docs/app-server) | host-runtime | model/list、provider capabilities、feature、skills/hooks/apps、配置与配额查询。 | 按实际运行客户端复核；模式目录不是模型质量排名；查询权限与秘密字段需另行约束。 |
| `cx-actors` [子代理与模型配置](https://learn.chatgpt.com/docs/agent-configuration/subagents) | host-runtime | 子代理原生调度与 model / reasoning 配置、继承。 | 用户选型和委派授权优先；实际执行模型与任务适配待验，不能由默认继承推得最优。 |
| `cx-execution` [执行与中断](https://learn.chatgpt.com/docs/app-server) | host-runtime | turn/start、turn/interrupt、command/exec 及结构化交互。 | 接口存在不等于本任务获准调用，也不等于目标结果完成。 |
| `cx-continuity` [会话与上下文连续性](https://learn.chatgpt.com/docs/app-server) | host-runtime | thread/start/read/resume/fork/compact/start。 | 原生会话操作不能独自证明语义交接正确；新任务、历史分叉和同会话压缩用途不同。 |
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
| 按需研究、学习与复用发现 | cc-tools, cx-extensions, cc-extensions, gpt6-cognition | 复用原生搜索和已授权资料能力；只补来源适用性与复用决策。 | 有足够证据时不多查；资料过期、能力缺口时定向补证。 |
| 关系、动态索引、路线与形态选择 | cx-state, cx-actors, cc-actors, cc-model-policy, cc-advisor, cc-sdk, gpt6-cognition, gpt6-protocol | 从需求与现状推导稀疏路线；主/子代理选型走原生接口，必要时组合，不另设固定模型排名。 | 匹配不同需求、显式选型和不足后的重选；核对实际模型、效果与成本。 |
| 执行、配置与代码操作 | cx-execution, cc-tools, cc-sdk | 原生工具承担操作；缺少的执行能力才组合或实现。 | 普通入口下完成实际变更，保留无关状态，禁止评估器救援冒充产品执行。 |
| 源头变更与全局一致性 | cx-execution, cc-tools, cc-memory, gpt6-cognition | 复用编辑与检查工具；Accord 补源头变更对计划、实现和验收的影响追踪。 | 改变一项前提，只更新受影响关系与声明；检查遗漏的消费者。 |
| 纠错、经验吸收与受控演进 | cx-continuity, cc-memory, cc-tools, gpt6-cognition | 复用授权状态载体；记录适用条件与反例，避免局部经验变成全局规则。 | 纠正后再次触发同类任务，核对适用性、恢复和不相关任务不受影响。 |
| 故障恢复与回滚 | cx-execution, cc-recovery, cc-tools | 优先原生恢复；仅为未覆盖副作用补偿，明确幸存执行者与可恢复范围。 | 注入中途失败，核对独立后态、并发及外部状态保护。 |
| 上下文与任务连续性 | cx-continuity, cc-actors, cc-sdk, cc-memory, gpt6-protocol | 复用会话/上下文能力；Accord 补最小语义移交和目标核对。 | 目标与代码身份在接收端核对后再释放来源；接收失败保留安全来源。 |
| 资源管理与清理 | cx-state, cx-execution, cx-hooks, cc-tools, cc-hooks, cc-sdk | 优先宿主配额、中断和资源控制；补归属判断及独立清理核对。 | 任务资源释放且共享资源不变；未知资源不得据推断删除。 |
| 安装、更新与卸载生命周期 | cx-extensions, cc-extensions | 使用原生插件生命周期；仅补实证缺失的补偿和后态验证。 | 精确 dev.2 包的安装、更新失败、成功更新和卸载；确认加载与残留。 |
| 原生接替、旁路与退役 | cx-state, cx-extensions, cc-extensions, cc-model-policy, gpt6-cognition | 原生同责效果足够则旁路或退役重复实现，保留必要结果责任。 | 新原生能力接替后核对效果、恢复及清理；其后失效时重新评估。 |
| 结果验证、独立证据与实际价值 | cx-execution, cc-tools, cc-sdk, gpt6-cognition | 复用宿主测试/观察；按声明补独立验收、对照与贡献归因。 | 全链路结果及后态可观察；区分宿主本来就会与 Accord 的必要帮助。 |

### 事实、索引、图与运行时

One versioned semantic source supplies the native matrix, Accord duty matrix and sparse dependency views. Acceptance duties own outcomes, dependencies and evidence; workSequence owns procedures and exits. This map references them instead of copying a second authority. It is a task-relevant review inventory, not every vendor product or host x model x tool combination. Separate model cognition, host runtime and model/API composition; a host-labelled review row scopes relevance, not exclusive model ownership or automatic endpoint exposure.

At a relevant decision, inspect the running client, actual provider/model, policy and exposed interface. Version/feature/configuration/package/permission changes, a supported invalidation event, source contradiction, missing observation or failed effect reopen affected applicability. Re-read supported state and only the needed official documentation; no automatic network watcher or fixed global expiry is installed. Retain the dated observation as history, never as permanently current support.

The delivered host Skill guides task-time discovery, decision, execution and verification, but its actual use and end-to-end effects remain unverified for dev.2. closure.py is a no-I/O reference decision core; research/PROTOTYPE-dynamic-relation-graph.html is a simulated in-memory PoC. Neither is a live host index or automatic executor. This development view does not close that ordinary-entry integration gap.

运行时分配要求：依赖运行时不等于必须自建运行时。按所需可靠性绑定触发者、实际执行者、必要状态载体和故障后的接管者；一轮任务可只需宿主现有 Agent 循环和上下文。要求确定触发、强制约束、跨轮或跨会话状态、无人值守推进或故障后继续执行时，核验宿主是否覆盖这些职责；缺失则组合或实现最小足够运行时，包括必要的持久机制。Skill 是 Agent 可解释的指导，不是独立调度器或强制执行保证。运行时增加也不自动证明业务效果；仍验收普通入口、失败及独立后态。当前缺口未闭合前不宣称仅靠 Skill 足够。

源数据中的职责依赖、工序、场景和能力引用构成评审关系；它们不证明插件已经执行该链路。

### 本机接口观察（非行为验收）

- `codex-cli-schema` — Codex CLI 0.153.3; default non-experimental generated ClientRequest.json。99 method variants; model/list, modelProvider/capabilities/read, experimentalFeature/list, skills/list, hooks/list, app/installed, plugin/list/install/uninstall, thread/start/read/resume/fork/compact/start, turn/start/interrupt, config/read, configRequirements/read, account/rateLimits/read and command/exec are present. Background-terminal list/clean are absent from the default schema, not proven unsupported. Schema existence only; no daemon query, model request or method effect. CLI version is not Desktop engine identity. Generated task-owned schema files are disposable.
- `codex-cli-flags` — Codex CLI 0.153.3。multi_agent, hooks and plugins stable/enabled; step_model_switching under-development/disabled. Plugin add/list/marketplace/remove subcommands exposed. CLI configuration and help snapshot only, not all Desktop feature state or task-fit behavior.
- `claude-cli-help` — Claude Code 2.1.261; existing authorized DeepSeek route。model, agents, fallback-model, plugin-dir, restricted, setting-sources, strict-mcp-config, permission-mode, resume and fork-session flags exposed. Local option existence, not API compatibility or successful execution. Prior dev.1 probe is separately bounded and cannot qualify dev.2. No official Claude account access is assumed.

## 动态适应的必查链路

按具体声明选择原生对照、可交付最小组合和受控干扰；不把干净宿主规定为通用运行前提。
核对全局、父目录与项目的 AGENTS.md、config.toml 等全部生效配置，以及记忆、历史、插件和环境变量；记录来源与影响，不复制秘密。

| 环境变化 | 要观察的功能效果 | 失败判据 |
|---|---|---|
| 模型更新使原有弱项消失，或对指导、上下文和工具的响应方式改变。 | 在同等任务及宿主条件下重新建立无 Accord 的模型原生基线；确认冗余或干扰后按同责效果削减介入，仅补残余缺口。 | 不能固化旧模型缺陷、将模型能力算作插件增益，或将 API 功能宣传当作当前宿主的执行证据。 |
| 主任务或子任务需要不同模型/推理配置，或所选路线失效、漂移、不满足效果。 | 在授权候选中自动匹配足够能力并通过原生或必要组合执行，核对实际模型及结果；原生足够时不保留重复路由器。 | 将默认继承、配置意图或品牌排名当作匹配证据；擅改用户钉定模型；无视别名/替代或虚称已切换。 |
| 当前原生能力已足够。 | 按需复用并减少介入，保持同一功能与质量；不为证明插件存在感强行接管。 | 无必要重造、冗余机制或将非介入冒充增量价值。 |
| 所依赖能力不可用、降级或权限变化。 | 识别受影响职责，选择足够的原生、组合或自建替代并验证；不可行时明确尚未完成。 | 不能静默削减功能，安全停止不能算成功。 |
| 外部插件、记忆或开发辅助让任务变得容易。 | 区分贡献来源；在移除未声明外援后复验，或把必要条件纳入可交付依赖与成本。 | 不能把当前增强环境的成功直接推广给普通用户。 |
| 第三方规则、工具或插件与当前目标或执行链发生冲突。 | 按实际影响局部隔离或改道，保留无关用户状态并验证恢复与清理。 | 不能无界关闭用户环境，不能让外部规则新增授权或改写目标。 |
| 任务中宿主更新、缓存与加载版本分离、接口或上下文发生变化。 | 重新感知相关事实，仅重算受影响分配与证据；经验证继续、恢复或交接。 | 不能沿用失效假设，也不能把宿主版本变化当作全量重做的固定理由。 |

## 当前短板及证据边界

- `native-accord-capability-map` — `mapped-interface-evidence-not-runtime-closure`：已建立有日期和来源的原生能力—Accord 职责关系，连接当前工序、验收与变更重查；动态图 PoC 和纯核心不是实时宿主索引或执行器，普通入口的全链路闭环仍待验证。
- `needs-based-model-and-subagent-routing` — `implemented-guidance-native-coverage-under-review`：主/子代理模型与推理按任务需求纳入现有路由职责；两宿主已提供部分原生选型和调度接口，不另造重复引擎。dev.2 Skill 增加匹配、别名/继承/替代核对及效果不足后的重选；自动匹配与实际执行仍需当前包效果证据。
- `source-to-projection-convergence` — `implemented-local-unverified`：Two worktree Skills and schema-v2 entry descriptors now implement host-driven, form-neutral guidance as unpublished 3.2.0-dev.2 packages. The Node invalidation helper is unchanged and optional. Static admission and ordinary-entry behavior are distinct; successor host effects remain unverified.
- `ordinary-entry-effect-and-recovery` — `open`：Historical GT-20/21 include reference-only executor activity; ordinary entry and actual recovery remain per-function verification needs.
- `verification-io-amplification` — `implemented-local-measured`：同一检出的完整校验 cProfile 单次前后对比：81.077 → 59.392 秒，755 → 493 次有界 Git 调用，均 valid=true、无错误。共享单次调用内的有界不可变内容缓存，合批读取相关历史文档；工作区读取保持新鲜，未删检查或子进程边界。这是本地测量，不是统计性能保证、宿主功能或产品增量价值证明。
- `acceptance-cost-and-coupling` — `implemented-local-unverified`：Current verify/host-check now dispatch to development-package admission without promoting or repeatedly replaying historical behavior. Retained rejection tests run current verifier code against the immutable predecessor subject. Package safety, identity, complexity, source preservation and dirty-worktree gates remain applicable; current functional and host evidence are still unverified.

## 发布顺序

版本内改动提交 → 推送精确候选 → 精确提交的验收与独立评审 → 发布同一提交 → 公共结果及清理核验。
提交不能夹带无关工作；推送成功、工作区干净或本地测试通过都不能单独代替发布验收。

当前对话含已启用的 Accord、其他能力及继承上下文，只作为开发辅助；不能用它证明普通用户环境下的效果。
本页是计划的可见投影，不是宿主原生计划面板修复，也不是功能完成或发布凭证。
