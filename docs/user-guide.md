# User guide / 用户指南

[中文](#中文使用指南) · [English](#english-user-guide) · [README](../README.md)

## 中文使用指南

本页承接 README 的安装、使用、隐私与原理细节。它说明当前发行的条件，不把通用设计、源码接口或历史验证当作所有宿主都已支持的承诺。

### 当前入口与运行条件

Accord 的通用设计与模型厂商、宿主适配分离；当前正式分发为 OpenAI 环境下的 Codex 适配。其它宿主的资料和历史包不代表本版提供相应支持。

以下入口说明于 **2026-10-29** 核对当前[官方插件文档](https://learn.chatgpt.com/docs/plugins#use-plugins-from-a-supported-surface)与[Hook 文档](https://learn.chatgpt.com/docs/hooks)。产品与上游会变化，安装执行者须核对具体版本和有效设置。

| 入口 | 当前使用说明 |
|---|---|
| Codex CLI、桌面中的 Codex | 使用实际支持插件、Hook 与 MCP 的版本和作用域，完成启用与 Hook 信任后核验加载。 |
| Codex IDE 扩展 | 当前官方文档明确不支持原生插件入口。VS Code 终端中的 CLI、SDK 本地后端与 IDE 扩展原生加载是不同路线。仓库已有 IDE 观察保留原版本与条件，不构成当前任意扩展版本的支持承诺。 |
| 本地编排、本地执行的 Work | 仅在所选版本确实支持插件及所需 Hook/MCP 时使用；不要因能本地执行工具便推断编排也在本地。 |
| 云端编排的 Work、Synced Work | 当前官方文档不支持插件 Hook；Synced Work 的管理员 MCP Hook 不等同于本包的本机命令 Hook，不作为本包的替代安装路线。 |
| Remote 桌面或手机 | 可作为已选本地宿主的交互控制通道；须核主机实际参与及控制端差异，手机不是独立运行本包的环境。 |
| SDK、普通 Chat、网页 Chat、其它 IDE | SDK 的版本绑定后端验证不产生通用安装界面；普通 Chat 独立用途、网页 Chat、JetBrains 与 Xcode 未纳入当前适配承诺。按具体路线的证据判断。 |

当前 Hook 和状态 MCP 通过独立的 `node` 命令运行。安装执行者应确认**实际宿主进程**能找到兼容 Node；另一个终端能运行，或宿主内部自带 Node，都不能替代该核验。

- 当前受测推荐为维护中的 Node 24。CI 使用 Node 24，本地有限检查覆盖 24.19.0、24.21.0；最低兼容版本、其它主版本及全部 24.x 补丁未获统一验证。见[运行时评估](../research/reviews/2026-10-09-node-runtime-compatibility.md)。
- 优先复用合适的已有运行时；缺少依赖时，由执行者说明并在必要授权内准备。普通入口不需要 Python、第三方 npm 包、额外模型部署、评估模型账号或第三方 Skill/MCP 服务；具体任务可能另需工具或访问条件。
- 有限范围转移与可选 SDK 记录器需要 Node 内建的 `node:sqlite.DatabaseSync`；入口加载、状态读取和 Skill 库存不打开该记录器。共用解释器的其它组件须同时满足双方要求。

### 首次安装与信任

三个动作分别完成：**安装插件、启用插件、信任 Hook**。还需确认实际加载，不能只看“已安装”。

1. 核对当前宿主、运行时、已有配置和插件，以及正式发行的精确 tag。当前版本为 [v3.3.4](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.3.4)，插件 ID 为 `yiyuan-accord-codex`，来源名为 `yiyuan-accord`。
2. 在需要登记来源时，可采用[官方 marketplace 命令](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli)：

   ```sh
   codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.3.4
   ```

   这条命令只登记来源。CLI 在 `/plugins` 中切到该来源，查看并安装 YIYUAN Accord；桌面使用实际可用的插件目录与来源入口。本项目来源不等于已被官方公共目录收录。
3. 确认宿主或组织允许使用插件，再在目标作用域启用 Accord。CLI 可对 `/plugins` 内已安装项按 `Space` 启停；桌面的全局插件使用开关和单插件启用分别核对，具体界面以所用版本为准。
4. **首次使用前审阅并信任 Accord 的当前 Hook 定义。** CLI 输入 `/hooks`。桌面的具体审阅/信任方式尚未跨版本统一核实，由安装执行者核对当前版本的受支持路径；没有可用路径时明确报告限制，不据安装成功声称已生效，也不把另一 CLI 的信任状态直接外推到桌面。安装、启用不会自动授予 Hook 信任；定义变化后需重新审阅。不要用手工修改信任摘要或全量放行代替审阅。当前[官方信任规则](https://learn.chatgpt.com/docs/hooks#plugin-bundled-hooks)说明未获信任的插件 Hook 会被跳过，CLI 操作见[审阅与信任](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks)。
5. 按宿主要求新建会话，让执行者核对实际 Hook 参与、MCP 连接、插件来源和版本。已加载的旧会话、目录中可见的 Skill、静态 `host-check` 都不能单独证明这些结果。

如果已有具备相应权限的 AI 助手，可以直接交给它：

> 请从 https://github.com/yiheng8023/YIYUAN-Accord 核对当前正式版本和我的宿主条件，保留无关配置、已有插件和未完工作，在授权范围内完成安装并验证生效。遇到需要我决定的插件启用、Hook 信任或本人操作时，先把具体事项与影响准备好再告诉我。

插件未启用或 Hook 未获信任时，不能依赖 Accord 自己完成这些前置动作。宿主提供的可选 `onboardingSkill` 声明也不保证存在独立 Setup 按钮；普通安装请求可由已有健康执行者处理，无需反复寻找或重装。

### 从目标开始

可以说：“把这份材料整理成可交付成果”“按这些条件完成修改”“继续未完工作，先核对上次实际做到了哪里”。你无需先把请求翻译成 Skill 名、工具调用或检查点格式。

Accord 的目标是让助手按实际任务研究可行性，发现宿主设置、选项、模型、权限、工具、项目和会话操作、记忆、自动化及扩展能力，协调需要的部分并验证结果。工具列表不是发现范围的全集，发现也不代表全部启用。已选模型、推理强度、限制和用户操作继续有效；不要求先重置环境，不因发现另一种配置便擅自改回默认。

子代理是可选能力。不可用或关闭时使用足够的单代理路线，保留必要核验缺口；委派不自动授权改变主模型。变更固定选择或跨越既有授权未涵盖的账户、数据、服务商与重大费用边界时，先说明影响并取得必要决定；已有明确授权不重复索取。

开始、过程与结果可以反馈、并行和嵌套。组件帮助保持目标、解释变化、修正受影响产物、恢复未完工作，并核验交付和资源后态；它不要求所有调用经过一个统一代理。第三方 App、Skill、MCP 等按用途组合、复用和退出，保护用户与其它任务仍在使用的共享依赖。

### 输入保存与隐私

启用输入 Hook 后，根任务的原生输入文字保留在本机既有回执中，用于恢复；每份回执上限为 **8 MiB**。其中可能含敏感信息，中断时即使没有检查点也可能保留，结束会话不保证立即删除。状态按任务生命周期处理，清理前须确认未完工作和恢复依据。

这不是完整对话或进度记录，也不产生新授权。子代理使用宿主自己的任务状态，不承接根检查点。请勿公开上传原始回执、凭据或私人会话；报告问题可先描述现象，由执行者选取必要且脱敏的证据。保留、退役及失败边界见[架构](architecture.md#current-release-and-scoped-connections)与[状态调用指南](task-state-clients.md)。

### 排查、更新与退出

| 现象 | 由执行者优先核对 |
|---|---|
| 安装后看不到或不参与 | 入口是否支持插件、组织与全局开关、目标作用域内的启用状态、新会话是否加载。 |
| Skill 可见，协调或恢复未发生 | 当前 Hook 是否启用、定义是否获信任、宿主是否能运行 Node、实际事件回执与 MCP 连接。 |
| 显示旧版本或更新后无变化 | 安装来源与精确包、当前加载进程/会话；新进程成功不证明已有会话已恢复。 |
| 输入或身份恢复被拒绝 | 保留真实输入、回执和原失败，由受支持状态读取核对；不要手工改写会话身份或恢复记录。 |

切换版本、回滚或移除前，使用不依赖待变更插件的健康执行者，核对未完任务、稍后才触发的 Hook、有效权限和恢复副本。无法确认安全切换时保留准备成果；备份存在不等于已经恢复。安装状态、已进入上下文的内容、连接与运行进程分别核验和处理，卸载本身不能证明后两者已消失。维护引导见[生命周期 Skill](../plugins/yiyuan-accord-codex/skills/manage-plugin-lifecycle/SKILL.md)。

### 版本与证据

| 版本 | 公开记录与含义 |
|---|---|
| 3.3.2 | `ef8bde2a` 的原绑定 18 案、17 范围、52 义务资格及 11 项 CI，详见[发行复核](../research/reviews/2026-10-21-functional-realization-release-audit.md)。 |
| 3.3.3 | `1d965e79` 修复新版根会话格式误判，保留身份、输入和恢复校验。 |
| 3.3.4 | `e58f016a` 的文字与维护说明补丁，发行和 CI 记录见[更新日志](../CHANGELOG.md)及[当前接续](operations/CONTINUATION.md#当前事实)。 |

原始失败、版本、环境和条件保持原身份；后续文档不移动发行标签，也不把旧通过直接当作新版本通过。CLI、SDK、桌面、IDE、Work 与 Remote 之间，仅在核对适用性和差异后复用相应机制证据；历史入口观察不能覆盖现行官方已知限制。

Accord 不训练模型、不扩大上下文、不越过宿主权限，也不注册 Stop 自动续轮或自动增加对话回合。长程控制由用户选择宿主的相应能力。参考指导、接口可用或人工救援不能代替普通任务中的实际效果；必要条件不足时保留限制和未完事项。

协调可能增加上下文、延迟、计算、指令冲突与维护负担。增量价值需要公平对照并同时考虑质量、自动化程度、人工协调和总成本；合理额外开销不等于失败，“省用量但仍需用户盯着”也不能替代必要自动化。当前[对照方案](operations/LAUNCH-v3.3.md#启用与未启用对照准备)仅作准备，尚不提供实测收益或统计结论。

### 原理与进阶阅读

当前包通过一个协调入口 Skill、四个专用 Skill、原生事件 Hook 与可选状态机制参与工作。入口采用[英文元指导](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/meta-guidance.md)，以[中文原文](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/meta-guidance.zh-CN.md)为语义基准；它不改变宿主优先级，也不要求用户创建或替换 `AGENTS.md`。

状态工具读取已存根任务状态和输入，评估有界工作段，并管理 Accord 自有检查点；它们不重放输入、不写业务文件、不改变宿主模式、不派发交接。共享处理器在已有所属执行来源失效时可能保护性停止该执行并留证。单独的 `coordinate_task_execution` 提供能力库存、受托 Skill 准备及受当前根任务约束的有限目标，默认只读；范围写入另需实际原生限制、来源静止、写者归属及独立核验。它不控制已有 GUI 线程或自动替换根助手。详见[能力接口](../plugins/yiyuan-accord-codex/skills/coordinate-capabilities/references/native-capabilities.md)和[交接接口](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/native-handoff.md)。

自举、自纠、恢复与长期演进是[设计和验收方向](operations/PLAN-v3.3.md#自举的能力维度与证据)，不把“自知、自洽、自治、自学、自纠、自愈、自证、自进化”八项称为全部实现。详细职责、来源覆盖、动态顺序与资源治理见[系统图](operations/PLAN-v3.3.md#稳定关系与动态方法)、[工序关系](operations/PLAN-v3.3.md#工序与依赖)、[架构](architecture.md)、[验收](operations/ACCEPTANCE-v3.3.md)及[词表](../GLOSSARY.md)。

### 维护者检查

以下检查不要求安装插件；Python 属于维护工具要求：

```sh
python -B -m yiyuan_accord verify-development --json
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
```

仅有 `python3` 时替换启动器。CI 覆盖 Linux、Windows、macOS 的 Python 3.10–3.14 和 Node 24；这不代表所有用户宿主已获行为验收。静态 `host-check` 不检查用户宿主运行时或实际参与。发布需符合[现行计划](operations/PLAN-v3.3.md)中的范围、证据、评审、精确提交及授权条件；冻结候选不是发布回执。历史 3.1 文件与 Golden Tasks 不定义当前后继版本的验收。贡献见[CONTRIBUTING](../CONTRIBUTING.md)，求助见[SUPPORT](../SUPPORT.md#支持说明)。

## English user guide

This guide carries the installation, use, privacy and mechanism details behind the README. General design, source interfaces and historical observations do not establish support for every host.

### Current entries and runtime

Accord's general design is separate from vendor-specific adapters. The current distribution provides a Codex adaptation for OpenAI environments; historical packages and research on other hosts do not establish current support.

The following entry limits were checked on **2026-10-29** against the current official [plugin](https://learn.chatgpt.com/docs/plugins#use-plugins-from-a-supported-surface) and [Hook](https://learn.chatgpt.com/docs/hooks) documentation. The installation executor must recheck the actual version and effective settings as both projects evolve.

| Entry | Current use |
|---|---|
| Codex CLI and desktop Codex | Use a version and scope that support plugins and the required Hooks/MCP; enable, trust and verify actual loading. |
| Codex IDE extension | Current official documentation excludes native plugins. CLI in a VS Code terminal, an SDK local backend and native IDE loading are distinct routes. Earlier repository observations retain their exact versions and conditions, rather than promising support in every current extension. |
| Locally orchestrated and executed Work | Use only when the selected version supports the required plugin Hooks/MCP. Local tool execution alone does not establish local orchestration. |
| Cloud-orchestrated Work and Synced Work | Plugin Hooks are not supported in the current official documentation. Administrator MCP Hooks in Synced Work do not replace this package's local command Hooks. |
| Remote desktop or mobile | May control a selected local host, subject to actual host participation and material client differences. Mobile is not an independent environment running this package. |
| SDK, ordinary Chat, web Chat and other IDEs | Backend-specific SDK evidence creates no universal installation UI. Independent ordinary Chat, web Chat, JetBrains and Xcode are outside current adaptation commitments; assess the exact route. |

The current Hooks and state MCP launch a separate `node` executable. The executor must check that the **actual host process** can find and run compatible Node; another terminal or a host's internal Node installation is insufficient evidence.

- Maintained Node 24 is the tested recommendation. CI uses Node 24; bounded local checks cover 24.19.0 and 24.21.0. The minimum version, other majors and every 24.x patch are not uniformly verified. See the [runtime assessment](../research/reviews/2026-10-09-node-runtime-compatibility.md).
- Reuse a suitable runtime. If missing, the executor prepares the dependency within the necessary authority. Ordinary use needs no Python, third-party npm packages, separate model deployment, evaluation-model account or extra third-party Skill/MCP service; individual tasks may need other tools or access.
- Scoped transfer and the optional SDK recorder require Node's built-in `node:sqlite.DatabaseSync`. Entry loading, state reads and Skill inventory do not open that recorder. Components sharing an interpreter must meet both sets of requirements.

### First installation and trust

Complete **installation, enablement and Hook trust** separately, then verify actual loading. An installed label is insufficient.

1. Check the host, runtime, existing configuration/plugins and exact official release tag. The current release is [v3.3.4](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.3.4); the plugin ID is `yiyuan-accord-codex`, in the `yiyuan-accord` marketplace.
2. Where source registration is needed, use the official [marketplace command](https://developers.openai.com/plugins/build/plugins#add-a-marketplace-from-the-cli):

   ```sh
   codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.3.4
   ```

   This registers the source only. In CLI `/plugins`, select it, inspect and install YIYUAN Accord. On desktop use the actual plugin directory/source entry. A repository marketplace is not a listing in the official public directory.
3. Confirm that the host or organization permits plugins and enable Accord in the intended scope. CLI `/plugins` uses `Space` to toggle an installed item. On desktop check global plugin use and the individual plugin separately; labels vary by version.
4. **Before first use, review and trust Accord's current Hook definitions.** Use CLI `/hooks`. A desktop review/trust method has not been uniformly verified across versions; the installation executor must check the supported route in the actual version. If none is available, report that limitation rather than treating installation as participation or extrapolating another CLI's trust state to desktop. Installation or enablement does not trust Hooks automatically; changed definitions require fresh review. Do not substitute manually edited trust hashes or blanket approval. The official [trust rule](https://learn.chatgpt.com/docs/hooks#plugin-bundled-hooks) says untrusted plugin Hooks are skipped; see [review and trust](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks) for CLI operations.
5. Start a new session as required by the host. The executor checks actual Hook participation, MCP connection, source and version. An old loaded session, visible Skill or static `host-check` result cannot establish these facts alone.

You can ask an existing assistant with suitable authority:

> Check the current official release at https://github.com/yiheng8023/YIYUAN-Accord and my host's conditions. Preserve unrelated configuration, plugins and unfinished work; install within my authority and verify actual participation. Prepare the concrete impact before asking for any necessary plugin enablement, Hook trust decision or personal action.

An inactive or untrusted Accord cannot perform its own missing prerequisites. The optional `onboardingSkill` declaration does not guarantee a dedicated Setup button. An ordinary installation request can use an existing healthy executor without repeated UI searches or reinstalls.

### Start with the goal

Ask for a deliverable, a change under stated conditions, or continuation after checking what actually happened. You need not translate your request into Skill names, tool calls or checkpoint formats.

Accord aims to have the assistant assess feasibility and discover relevant host settings, options, models, permissions, tools, project/session operations, memory, automations and extensions. The exposed tool list is not the whole discovery boundary; discovering capabilities does not enable all of them. Explicit model/effort choices, restrictions and user actions remain effective. No reset to defaults is required, and an alternative configuration is not permission to undo your choices.

Subagents are optional. When unavailable or disabled, use an adequate single-agent route and retain any necessary review gap. Delegation does not authorize changing the main model. Explain and obtain a necessary decision before changing a pinned choice or crossing an uncovered account, data, provider or significant-cost boundary; do not ask again for existing clear authority.

Starting conditions, work and results may feed back, run in parallel and nest. Coordination connects faithful goals, changed requirements, affected artifacts, recovery, verified delivery and resource state without routing every call through one proxy. Compose and retire third-party Apps, Skills and MCP capabilities by need, protecting shared dependencies still serving the user or other tasks.

### Input retention and privacy

With the input Hook enabled, root-task native input text is retained in an existing local receipt for recovery, bounded to **8 MiB per receipt**. It may contain sensitive information and survive interruption even without a checkpoint. Session exit does not guarantee immediate deletion. Follow the task lifecycle and check unfinished work and recovery needs before cleanup.

This is not complete conversation history or a progress record, and grants no new authority. Subagents use their native task state rather than adopting the root checkpoint. Do not publish raw receipts, credentials or private transcripts; describe the problem first and let the executor select necessary redacted evidence. See the [architecture](architecture.md#current-release-and-scoped-connections) and [state-client guide](task-state-clients.md) for retention, retirement and failure boundaries.

### Troubleshooting, updates and exit

| Symptom | Executor's first checks |
|---|---|
| Installed but invisible or inactive | Entry support, organization/global gates, enablement in the intended scope, and a newly loaded session. |
| Skill visible but coordination or recovery absent | Hook enablement and trust of the current definition, host access to Node, actual event receipts and MCP connection. |
| Old version shown or update has no effect | Exact source/package and actually loaded process/session; fresh-process success does not prove an existing session recovered. |
| Input or identity recovery rejected | Preserve actual input, receipts and original failure; use supported inspection rather than rewriting identity or recovery records. |

Before update, rollback or removal, use a healthy executor independent of the plugin being changed. Check unfinished work, later-triggered Hooks, authority and a recovery copy. If a safe switch cannot be established, preserve preparation. A backup is not completed recovery. Installed files, loaded context, connections and processes have separate lifecycles; uninstalling alone does not establish that context or activity disappeared. See the [lifecycle Skill](../plugins/yiyuan-accord-codex/skills/manage-plugin-lifecycle/SKILL.md).

### Versions and evidence

| Version | Public record and meaning |
|---|---|
| 3.3.2 | Original qualification of 18 bound cases, 17 scopes and 52 duties, with 11 CI checks, at `ef8bde2a`; see the [release review](../research/reviews/2026-10-21-functional-realization-release-audit.md). |
| 3.3.3 | `1d965e79` fixes rejection of the newer root-session format while preserving identity, input and recovery guards. |
| 3.3.4 | Wording and maintenance guidance at `e58f016a`; release and CI records are in the [changelog](../CHANGELOG.md) and [current continuation](operations/CONTINUATION.md#当前事实). |

Original failures, versions, environments and conditions retain their identities. Later documentation does not move release tags or validate changed versions through an old PASS. Reuse common-mechanism evidence across CLI, SDK, desktop, IDE, Work or Remote only after checking applicability and differences. Historical observations do not override known current upstream limitations.

Accord does not train models, enlarge context or bypass host permissions. It registers no Stop auto-continuation and adds no conversation turns. Users select the host's long-running controls. Guidance, interface availability or evaluator rescue does not establish ordinary-use outcomes; preserve real limitations and unfinished work when conditions are insufficient.

Coordination may add context, latency, compute, instruction conflicts and maintenance. Incremental value needs a fair comparison accounting for quality, automation, human coordination and total cost. Reasonable extra cost is not failure; lower usage that still leaves the user supervising cannot replace necessary automation. The [comparison protocol](operations/LAUNCH-v3.3.md#启用与未启用对照准备) is preparation only, with no measured benefit or statistical conclusion yet.

### Principles and further reading

The current package combines one coordination entry Skill, four specialist Skills, native event Hooks and optional state mechanisms. Entry uses the [English meta-guidance](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/meta-guidance.md), with the [Chinese source](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/meta-guidance.zh-CN.md) as the semantic basis. It does not change host instruction priority or require creating/replacing your `AGENTS.md`.

State tools read saved root state/input, assess a bounded work span and manage Accord checkpoints. They do not replay input, write business files, change host modes or dispatch handoff. Their shared handler may protectively stop owned execution when its source becomes invalid and retain evidence. The separate `coordinate_task_execution` provides inventory, delegated Skill preparation and bounded targets under the current root task. It defaults to read-only; scoped writes additionally need verified effective native restrictions, source quiescence, writer ownership and independent checks. It does not control existing GUI threads or automatically replace the root assistant. See the [capability](../plugins/yiyuan-accord-codex/skills/coordinate-capabilities/references/native-capabilities.md) and [handoff](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/native-handoff.md) interfaces.

Bootstrap, correction, recovery and long-term evolution are [design and acceptance directions](operations/PLAN-v3.3.md#自举的能力维度与证据), not a claim that all eight dimensions—self-knowledge, coherence, autonomy, learning, correction, recovery, evidence and evolution—are implemented. Full duties, justified source coverage, dynamic ordering and resource stewardship remain in the [system diagram](operations/PLAN-v3.3.md#稳定关系与动态方法), [procedure relationships](operations/PLAN-v3.3.md#工序与依赖), [architecture](architecture.md), [acceptance criteria](operations/ACCEPTANCE-v3.3.md) and [glossary](../GLOSSARY.md).

### Maintainer checks

These checks do not require plugin installation; Python is a maintainer dependency:

```sh
python -B -m yiyuan_accord verify-development --json
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
```

Use `python3` where appropriate. CI covers Python 3.10–3.14 on Linux, Windows and macOS, with Node 24; this does not qualify behavior in every user host. Static `host-check` does not test the actual host runtime or participation. Publication follows the scope, evidence, review, exact-commit and authority conditions in the [current plan](operations/PLAN-v3.3.md). A frozen candidate is not a release receipt. Historical 3.1 documents and Golden Tasks do not define successor acceptance. See [Contributing](../CONTRIBUTING.md) and [Support](../SUPPORT.md).
