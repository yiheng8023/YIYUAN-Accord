# Agent Autonomy Harness

[English](README.md) | 简体中文

一个跨 Agent 的自治协作与能力编排底座。它的北极星是把 Agent 学习、能力选择、
资源调度、上下文连续性和工程协作负担从用户头脑中移走，让用户主要聚焦创造、
决策和有边界的授权。

## 决策卡

- **当前状态：** 处于调研与可证伪验证期；尚未证明跨宿主中立运行时、广泛候选
  价值或自研残余缺口。
- **当前 Skill 权威：** 活跃的“适配后第三方 payload”发布数量为 `0`。既有
  19-Skill/40-file 清单已降级为弃用的过渡证据，只保留哈希绑定历史，不再作为当前
  安装或更新来源。
- **当前运行边界：** 可移植决策合同、宿主中立适配合同与宿主特定实现是三个分离
  层次。CC Switch 是受支持场景下的一个当前操作适配器，不是可移植产品合同；授权、
  生命周期与权限强制权威仍属于宿主原生控制面。
- **当前行动：** 从已命名的 CC Switch、官方和经审查外部来源建立有边界、来源保真、
  默认不活跃的候选池；按精确版本审查后，才进入单独授权的管理器事务。具体任务中的
  启用保持最小、按需。真实任务的 Harness 与轻量路径对照并行推进；复用和组合留下可
  复现残余缺口后才自研。
- **证据入口：** [当前计划](docs/strategy/RESEARCH-AND-POC-PLAN.md)、
  [非激活 Skill 来源池](docs/strategy/SKILL-PORTFOLIO-INACTIVE-SOURCE-CANDIDATE-POOL-2026-08-02.md)、
  [场景矩阵](docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md)与
  [接续记录](docs/operations/CONTINUATION.md)。

## 当前阶段

本私有仓库于 2026-07-18 从 `agent-skills-curated` 的完整 Git 历史启动。既有能力
策展系统作为第一个受治理组件和证据基础完整保留，但它不再代表整个产品身份。

当前阶段是外部调研和可证伪验证，不预先宣称所有 Agent 宿主都提供所需控制面。
首批三条验证链路是：

1. 上下文生命周期 -> 适时生成仓库锚定交接 -> 同工作区新线程接续；
2. 任务拓扑 -> 分支/工作树判断 -> 有边界执行和清理；
3. MCP 按任务启用 -> 租约/空闲释放 -> 故障恢复。

先验证原生与官方能力，再比较成熟外部实现，最后才对确有证据的残余缺口自研。
授权弹窗只是宿主原生授权与权限强制面的一种形式；其他宿主可使用权限规则或等价的
宿主自有机制。本项目只应减少并尊重这些交互，不重复造审批系统。

## 从这里开始

- [产品北极星](docs/strategy/PRODUCT-NORTH-STAR.md)
- [外部调研与 PoC 计划](docs/strategy/RESEARCH-AND-POC-PLAN.md)
- [接续交接](docs/operations/CONTINUATION.md)
- [启动权威记录](registry/agent-autonomy-harness-bootstrap-2026-07-18.json)

运行 `python -B scripts/verify_bootstrap.py` 可验证新仓库身份和迁移锚点。

---

## 继承的能力策展组件

这是一个公开安全、跨 Agent 的权威仓库，负责经过审查的 Skill 正文、来源、治理证据、
能力拓扑和确定性发布清单。

## 仓库职责

本仓库治理可复用 Skill 从准入到批准发布的完整资产链，并作为面向 Agent 的中立生产者。
Codex 与 Claude 是当前已描述的消费侧示例，但证据状态不同：Codex 已有固定版本的当前
消费者仓静态证据，但真实状态仍有缺口；Claude 在本仓仍只是概念性链路示例。两者都还不是当前已支持映射，
也不构成本仓模型边界。公开读者应从公开安全模板 `codex-user-config-template` 与
`claude-user-config-template` 开始理解消费侧结构；这两个模板展示的是更通用的
agent 环境迁移、云端同步/备份、验证和恢复模式，不证明当前消费者状态。

## 本仓库提供什么

- 当前第三方候选的固定来源、许可证、来源证明、审查裁决和上游精确身份；
- `skills/` 中作为弃用过渡证据保留的历史适配 Skill 正文；
- 安全、可移植性、重叠、生命周期和冲突证据；
- Skills、能力、关系、冲突和 Recipes 的权威 registry；
- 确定性的派生投影和 schema 1 发布清单。

继承发布包含 19 个 Skills、40 个文件：5 个来自 `addyosmani/agent-skills`，
13 个来自 `mattpocock/skills`，1 个来自 `kepano/obsidian-skills`。由于这些 payload
做过中立化或通用化，它们现已降级为弃用过渡证据。当前策略不改写第三方 Skill 正文；
精确历史清单仅用于来源、迁移和回滚分析。

## 战略定位

经过审查的 Skills 是独立、有边界的资源治理流程中的首个末端 MVP。
它们是低负担、跨 Agent 的切入点，可以为内外部消费者携带指导、资源、脚本和
确定性检查；它们不是唯一可能的末端，也不把上游发现范围限制为 Skills。

本仓是多领域治理仓。人机协作短板只是一个以证据驱动的需求通道，不是本仓全部使命。
稳定原则是“复用优先于自制”：先建立需求证据，再比较原生、官方、运行时、单 Skill、
组合 Skill 和其它 Harness 替代方案；只有证明存在剩余缺口后，才允许仓库自制。
第三方正文始终由上游所有并保持不变。
发现数量、流行度或历史草案都不能单独证明缺口。

本仓要交付的是“决策就绪的外脑”，而不是越来越大的 inventory。消费方应获得经过治理的
少量路由、替代方案、冲突、证据边界和复查信号，而不是反复穷举未知 Skills；由此降低筛选、
路由、上下文和维护负担，让人主要投入创作与决策。本仓不宣称提高模型能力上限，也不把
某一 Agent 的验证结果泛化为所有 Agent 的一致行为。

稳定工序采用依赖图，而不是强制线性流水线：消费投影是可选分支，生命周期治理是跨阶段
回路，标准抽取只在重复证据成立时进入条件分支。公共发现、社区提交、带日期的研究语料及
其他只读来源信号可以广泛进入候选面，但必须在本仓绑定需求、基线、精确来源固定、审查和
验收后，才能影响精选决策。总控修订与
Round 02 收口都已经形成明确的 owner 接受事件。Round 02 已关闭；Round 03 能力调研
重基线已经接受，有边界的只读调研已在需求与基线工序关口之后激活。当前 initiative
是能力调研与残余缺口证明阶段。

可靠性采用分层保障，而不是只依赖文本：instructions 与 rules 可以路由到 Skills 和
Recipes；脚本、schemas 与 validators 负责可机器检查的行为；消费侧控制和项目内置
硬标准仍属于更高权威的集成面。当前档位、字段和评审项只是工作假设与观测协议，
不是硬标准。标准候选工作推迟到价值能在多个独立来源、Agent 或宿主、任务类型和
真实反馈周期中稳定复现，且净收益成立并取得单独权威决策之后。本仓不负责准入、
发布或安装项目硬标准。用户配置仓在这条链路中只承担消费、验证和
反馈，不是跨项目调研或标准的长期载体。`YIYUAN-CALIBRATION` 中已固定的人机协作
短板语料只作为只读候选、证据和研究输入；CALIBRATION 不是 Skill 或 Manager 产品权威。
标准准入与最终承载仍属于适用的项目权威。

继承的适配发布已经弃用，不代表当前的人机协作短板覆盖。当前已描述的消费路径在受支持
场景下使用 CC Switch 承担来源、安装、更新、分发、备份和恢复。它是可替换的消费适配器，
不是 Harness 的可移植依赖或所有宿主的统一运行模型。这也不代表现有池子已经完成迁移：
2026-07-18 只读审计发现 43 个当前 CC Switch 目标、42 个本地数据库记录、0 个来源仓
记录和 1 个缺失数据库行；19 个历史 curated 目标仍逐目录匹配本仓适配发布。因此来源
保真池验收保持部分完成，等待逐 Skill 迁移复核与单独授权的迁移证据。本仓默认保持外部
Skill 原文不变，只负责安全、
质量、优劣、重叠、冗余、来源与短板覆盖决策。只有可复现的残余缺口成立后，才进入仓库
自研。此前的自研 Manager 仅保留为历史实验与证据，不再属于现行产品路线。
首轮只读迁移复核现已形成 16 个上游原文替换候选和 3 个退役或被替代候选，但不授权
任何真实变更。
一次性 CC Switch 3.17.0 来源管理预览已经在不改变真实 Skill 树的前提下验证来源登记、
来源启停、异源同目录冲突、选择性投影、备份、恢复和迁移快照合同。但原版 Windows
测试边界有五处绕过 `CC_SWITCH_TEST_HOME`，完整 7/7 结果依赖 `C:/tmp` 中仅用于诊断的
路径修正。因此验收继续保持 partial，不声称已经完成真实来源型迁移或网络更新。
后续回环更新夹具验证了 v1 安装、v2 更新检测、更新前备份、替换和手工恢复 v1，
同时证明 CC Switch 更新器不是原子事务。第一次运行还暴露了第二个 Windows 测试 Home
优先级缺陷，并曾短暂在真实 CC Switch 存储中产生纯测试记录和 fixture 载荷。两次清理
事务均先取得一致性数据库副本，再按身份和完整字段核验删除 2 条测试 Skill 行、1 条
测试来源行、载荷和备份。最终数据库回到 248 条 Skill、5 条来源；修正后的第二次运行
没有新增真实 fixture。
因此第一次真实金丝雀必须采用单 Skill 预览、外部前态快照、可读备份和明确恢复演练，
不能直接使用自动更新。
只读金丝雀决策包现已选定 `handoff`：它的语义差异最小、没有可执行面，已固定本地与
目标哈希，并预览了“卸载—安装”所有权转换和回滚；在该预览阶段执行尚未授权。CC Switch 只保存会
移动的 `main`，不保存已审 commit，因此任何真实变更前都必须重新核对外部 revision pin。
随后获授权的本地金丝雀已通过 CC Switch 自身的来源、备份、安装、投影和更新检查路径
成功执行。第一次哈希尝试因 Windows checkout 与 GitHub archive 的换行字节差异而失败
关闭并恢复本地状态；采用 archive 精确字节的结果已成为来源型条目，且 `handoff` 没有
更新。另观测到 20 个 `larksuite/cli` 更新信号，全部留在闸门外等待复核。由于 WebDAV
同步是另一笔外部写入决策，CC Switch 目前仍保持关闭。
发布不设增长配额：只要证据支持，保持、组合、替换、淘汰、弃用或退役与新增同样合法。
当前机器目标是“来源保真的跨 Agent 能力治理”，并用独立退役记录防止历史工作
悄然变成重新启动权限。

2026-07-18 的公共发现投影记录了 188 个去重公共来源 ID 和 20 个平衡、固定 revision
的结构预检。用户另外提供的 GitHub 公开星标清单补充了其中未出现的 5 个来源，但不把发现
范围限制在该清单内。5 个来源的“不执行静态复核”现已完成。Loopy 后续也已收口：18 个
确定性合同夹具全部通过后，又在用户明确授权下完成精确固定版本的可丢弃 Agent 对照试验；
原生、现有链路与 Loopy 三臂共 12/12 次运行正确，Loopy 没有误启循环，但也没有在上下文
成本成比例的前提下相对两个基线都体现实质增益。因此其完整正文仅作参考、不准入，本证据
仍未批准任何来源或组件。

星标清单新带来的 5 个来源也已完成预检：1 个只作发现索引，2 个复用历史组件评审，
1 个因许可证证据不完整且高度重叠而仅作参考，1 个属于外部 Skill 工具而不是准入候选。
对固定索引进行精确提取后得到 20 个直接安装坐标，其中 16 个不在广泛发现投影内；这
16 个来源目前有 14 个可解析、2 个已失效，任何可能后继都不会被自动替换。PM Skills
当前版本只有两份 Skill 正文共 5 行变化，因此旧的套件拆分仍可复用，而宿主命令变化
继续单独搁置。

第三轮十项结果包已经为本批需求组装完成。其 62 行 STM/P/SG 坐标包络现已全部进入
8 条来源支持的需求线，没有未评估坐标；但仍不宣称完整需求模型和长期证据已经收官。
新增的
`STM-11`/`P1`/`P2`/`SG-01` 意图绑定线已经有按比例使用的原生、现有链路、curated、
recipe、runtime、fallback 和人类权威路径，因此当前既不触发外部发现，也不触发自研。
新增的 `STM-20`/`P9`/`SG-05` 权限边界线把提示/Skill 引导、宿主运行时强制和负责主体
权威分开，现有路径同样没有证明残余 Skill 或 Hook 缺口。
新增的 `STM-07`/`P4`/`SG-03` 前提线保持比例化质疑、文档盘问按需启用，并为开放或
发散工作保留原生快路径。
最后的 `STM-09`/`P17`/`P20`/`SG-10` 线把即时辅助、长期认知、真实监控、维护者学习和
反堆积边界分开。
所以当前状态仍是 partial，不是调研
收官：没有残余缺口成立，不授权候选准入、自研 Skill 或 Hook，也不支持抽取硬标准。
Loopy 行为闸门已经执行并裁定为仅作参考。下一闸门是复核完整的已选坐标包络，同时
保持需求模型、长期认知、生产监控和跨宿主证据限制开放；已经关闭的需求线只有在各自
记录的触发器出现时才重新评估。

本仓实行“严格准入、自由消费”。保持上游原文不等于整套照单全收：多 Skill 来源必须按
来源、套件、组件和能力四层评审，Hook 另行准入。用户仍可自由添加、删除、组合、fork
或修改 Skills；修改后的派生版本只是不自动继承原始摘要与本仓验证。Harness 按开放、
辅助、守护三种任务姿态实施比例化干预，原生推理、无需 Skill、无需 Hook 和无需额外
结构始终是有效结果。
未来任何残余缺口自研 Skill 或 Hook 都必须基于任务、风险、权限、宿主能力、用户姿态和
反馈透明地动态适配，不得静默自改、扩权或自动发布。

动态 MCP 与协作拓扑控制现阶段只是有日期的研究缺口，不是实现承诺。Codex 已有普通
MCP、插件 MCP 的启动期启停以及工具白名单/黑名单，必须先评估这些原生能力；会话中
热切换、卸载已运行 MCP、精确上下文/压缩遥测仍未证明。产品中立的指令与检查合同留在
本仓，你的 Codex 自用实现属于私有用户配置。公共用户配置不手工维护第三份全文；未来
如需公共版本，应是脱敏、生成、明确非权威的投影。

战略目标到验收、验证和证据的稳定映射位于
`registry/program-acceptance-map.json`。局部或带日期的证据必须保持 partial 或
stale；仓库验证器通过不能证明当前 live Agent 状态。

## 本仓库不负责什么

本仓库不负责用户配置、认证、运行时记忆、Plugins、Apps、MCP 账号状态、安装权限
或 live 环境状态；不执行安装，不写入 `codex-user-config`、`claude-user-config`
这类私有消费配置仓，也不写入 live Agent 环境。
任何跨仓写入（包括可能的 CALIBRATION 交接）都属于需要单独授权的事务，不是本仓验证
或发布流程可以顺带执行的隐含副作用。

本治理仓不再拥有或改写第三方 Skill 正文；它治理来源、审查、路由、组合、准入元数据和
产品中立能力分类，不治理、也不盘点官方、
运行时所有、内置或第一方 Skill 正文。它们只能作为带日期的重叠审查证据出现；这类
证据不是受管 inventory、仓库所有权或当前运行时可用性的证明。

来自 Agent、运行时、平台或工具生态的官方 Skills、能力包、workflow templates 或类似
公开能力包，可以作为带日期的“官方外部能力基线”记录。基线用于覆盖关系对照、缺口分析
和路由校准，不是受管 inventory。本仓用基线矩阵裁定 `covered`、`reference`、
`adapt-candidate` 或 `skip`；不会盲目导入官方仓库，也不会在未验证流程、资源、脚本、
触发描述和产物标准之前宣称完整覆盖。当前第一份基线实例是
`docs/anthropic-official-skills-coverage.md`。

## 与配对仓库的关系

依赖与权威方向保持单向：

```text
当前公开读者入口
  codex-user-config-template
  claude-user-config-template
    → 展示公开安全结构、占位值和用户自建指引

当前私有消费仓
  codex-user-config
  claude-user-config
    → 可消费固定且已审查的版本和 release manifest
    → 规划、备份、安装、验证和回滚受管 Skill 路径

agent-skills-curated
  → 负责已审查 Skill 正文、来源、拓扑、冲突、政策、审计和确定性清单
  → 不反向写入私有消费配置仓或 live Agent 环境
```

公开模板不包含维护者的私有配置、记忆、账号假设、偏好或本机状态；它们是外部用户理解
消费侧模式的公开入口。私有配置仓不能仅因现在或历史上存在，就被假定为当前下游或已
支持消费者；必须先有带日期的消费者自有映射与验证记录。

消费侧模式是通用的，即使具体实现会因 agent 而异。未来其它 agent 或工具链只要完成
运行时文件、设置、记忆、hooks、工具、权限和恢复行为的映射，也可以拥有自己的公开模板
和私有 overlay。

消费仓不接管第三方 Skill 正文治理；精选仓不接管消费者侧安装或运行时集成。每个消费仓
负责自己的消费侧集成；本仓保持 agent 中立，不绑定任何单一 agent。

真实用户配置仓可能包含个人信息、偏好、记忆快照、账号假设、本地恢复策略或私有运行选择，
除非经过专门脱敏，否则应保持私有。如需公开配置示例，应另建 `codex-user-config-template`
或 `claude-user-config-template` 这类公开模板，使用占位值和用户自建指引，而不是复制私人仓库。

发现来源、配置仓、公开模板、本治理仓和 CC Switch 各自保有有边界的职责。本仓独立拥有
候选审查、路由、组合、准入元数据和自研残余缺口发布决策；上游拥有第三方正文；CC Switch
为受支持 Agent 提供运行管理；消费环境拥有
各自的 instructions、Skills、Hook 与实时加载行为。

共享 Skills 及其可移植的“指令/规则、Skills、Hook、验证反馈”链路是本仓持有的 Agent
中立权威，不得整体并入 `codex-user-config` 之类的单一 Agent 消费仓。后者只拥有 Codex
专属的安装、运行路径、Hook 部署、验证与回滚适配。

## 能力分层与路由

三层资产不可混同：

1. 官方、运行时所有、内置或第一方 Skill 只能出现在带日期的重叠证据中；其正文和
   运行时身份都不是受管 inventory，不复制，也不在本仓发布；
2. 第三方候选保持上游精确版本；其来源、许可证、安全、依赖、可移植性、重叠、维护和
   验证通过后，才可进入单独授权的管理器事务，正文不进入本仓当前产品发布；
3. 仓库自研残余缺口 Skill 只有在必要性与准入闭环后，才可进入未来活跃发布。当前活跃
   的适配后第三方 payload 数量为 0；`registry/skills.json`、`registry/routing.json` 和
   `release-manifest.json` 仅保留弃用的 schema 1 过渡发布供历史验证。

仓库自制的缺口补位 Skill 只是候选来源，不是第四个发布层，也不是平台、运行时或厂商
第一方基线。它必须先有剩余缺口证据、替代方案比较、设计来源与许可证说明，并通过安全、
可移植性、重叠、验证和 owner 批准；在通过同一精选准入边界前始终不可执行。

配置仓拥有的 `capability-router` 是“能力决策路由器”，不是尽量选择 Skill 的
skill-router。候选决策包括原生推理、官方或运行时能力、精选 Skill、外部能力元数据、
Recipe/DAG、请求人工确认和无需 Skill。第三方候选不是可执行路由目标；高风险、歧义、
冲突、权限变化、写入、安装、删除、迁移、发布或回滚必须请求人工确认。

路由不只是任务入口的一次性判断。多步骤工作应在事件驱动的复判 checkpoint 重新评估：
阶段边界、新上下文、失败或阻塞、产生副作用动作前、切换能力类别前，以及最终验证前。
路由投影为这些 checkpoint 提供确定性策略输入；它不要求每个原子步骤都路由，也不证明
live 能力当前可用。

`capability-router` 是已描述的 Codex 消费机制，不是通用前置，也不证明当前实时加载。
消费者调用链因 Agent 而异。Claude Code 在本仓只保留为“直接呈现能力”的概念示例；
在具备带日期的官方来源复核、消费者自有清单、优先级映射、行为探针和备份/恢复证据前，
不能把它写成已验证链路。Codex 已有当前静态部分证据，但仍不是完整实时映射。其它 Agent
同样必须先形成证据化映射，才能在本仓描述其安装、路由或恢复行为。本仓只在结构上命名
机制，保持 Agent 中立、开放、兼容，不得为任何单一 Agent 的链路写死。

Schema 2 的运行时覆盖通过结构契约保持产品中立：`runtime-resolved` 能力必须携带
`runtimeResolution: visible-capability-inventory`。该字段只命名解析机制，不命名产品、
厂商、所有者，也不假定任何 live 能力存在；消费者必须探测当前可见且已授权的能力清单。

## 目录结构

- `skills/`：精选批准的可移植 Skill 正文；
- `sources/`：不可变来源锁、许可证、选择和哈希；
- `registry/`：人工维护的拓扑与发布清单权威；
- `policies/`：准入、可移植性、安全、重叠和生命周期规则；
- `audits/`：来源级审查与证据；
- `docs/decisions/`：已经接受的治理决策，用于约束后续 contract 变更；
- `docs/official-external-capability-baselines.md`：官方外部能力基线的通用处理规则；
- `docs/anthropic-official-skills-coverage.md`：第一份官方基线实例的带日期覆盖矩阵；
- `docs/mvp02-preflight-readiness.md`：已被 bounded owner 批准消费的 MVP-02
  preflight 历史记录；
- `docs/mvp02-post-approval-execution-plan.md`：窄范围适配草案步骤的已执行计划；
  已停在 release 或 runtime 闸门之前；
- `docs/mvp02-adapted-draft-review.md`：非运行时适配草案审查证据；不是批准
  payload、不是路由、也不是 live install；
- `docs/mvp03-release-or-routing-preflight.md`：下一闸门预检与授权请求；不是
  release、routing、manifest 或 runtime 批准；
- `docs/mvp03-release-or-routing-review-template.md`：仅模板的候选审查契约；只有
  owner 批准后才能使用，不是候选裁决；
- `docs/mvp03-release-or-routing-approval-request.md`：MVP-03 候选审查的正式
  owner 授权请求；现在已被 bounded approval event 消费；
- `docs/mvp03-release-or-routing-candidate-review.md`：MVP-03 逐候选处置证据；
  不是 approved payload、不是 manifest、不是 routing，也不是 live install；
- `docs/mvp03-release-routing-execution.md`：owner 批准后的后续闸门；将两个
  候选合并进现有 approved Skill payload，将 `spec-driven-development` 建模为
  recipe/routing projection，并把 runtime install proof 交给消费仓执行；
- `docs/mvp06-lifecycle-feedback.md`：来自已验证消费仓安装结果的生命周期反馈，
  包含资源雷达去重元数据，以及下一批前先暂停观察的决策；
- `registry/program-acceptance-map.json`：稳定的战略目标、验收、验证和证据关系，
  并记录诚实的当前评估；
- `docs/curation-program-plan.md`：机器计划的人类投影、战略基线、交付生命周期和
  当前阶段收官对账状态；
- `docs/curation-harness-model.md`：持续策展闭环、首个末端 MVP、分层可靠性、
  多 Agent 消费边界和标准候选边界；
- `docs/superpowers/specs/2026-07-15-production-capability-manager-design.md`：
  已被替代的自研 Manager 历史设计与有边界实验沿革；
- `docs/cc-switch-source-preserving-skill-pool-strategy-2026-07-17.md`：
  当前 owner 已接受的 CC Switch 复用、上游原文保留与残余缺口自研策略；
- `docs/cc-switch-live-source-ownership-reconciliation-2026-07-18.zh-CN.md`：
  真实只读投影证明 CC Switch 已承担运行分发，但 43 个当前目标的来源仓记录仍为 0，
  来源迁移尚未完成；
- `docs/cc-switch-disposable-source-management-preview-2026-07-18.zh-CN.md`：
  一次性来源、冲突、备份、恢复合同证据，以及原版 Windows 测试隔离限制；
- `docs/cc-switch-disposable-source-update-and-recovery-review-2026-07-18.zh-CN.md`：
  回环来源更新、非原子失败、手工恢复、隔离事故、精确清理和修订后的真实金丝雀门；
- `docs/cc-switch-handoff-real-canary-readonly-preview-2026-07-18.zh-CN.md`：
  选定的单 Skill 金丝雀、精确前态/目标哈希、移动分支固定限制、受限所有权转换、验收与
  回滚预览；
- `docs/cc-switch-handoff-real-canary-execution-2026-07-18.zh-CN.md`：
  已授权的本地来源型迁移、失败关闭的 archive 字节哈希修正、全库后态审计、无增量更新
  检查、用户授权后的 WebDAV 同步后态，以及尚未完成的跨设备一致性边界；
- `docs/dynamic-runtime-control-gap-review-2026-07-18.zh-CN.md`：
  原生 MCP 启动控制、尚未证明的热切换/上下文遥测，以及产品中立、自用私有、公共投影
  三者边界；
- `docs/legacy-curated-skill-source-migration-review-2026-07-18.zh-CN.md`：
  对 19 个历史适配衍生物逐 Skill 只读复核，形成 16 个上游原文替换候选和 3 个退役
  或被替代候选，不授权真实变更；
- `docs/custom-manager-retirement-reconciliation-2026-07-18.zh-CN.md`：
  当前产品中立的治理身份、历史 Manager 证据保留和明确的重新启动闸门；
- `docs/evidence-backed-release-evolution-reconciliation-2026-07-18.zh-CN.md`：
  不设 Skill 数量 KPI、保持/新增/替换/组合/退役等合法结果，以及当前“保持并监测”决策；
- `docs/layered-reliability-projection-reconciliation-2026-07-18.zh-CN.md`：
  在治理投影范围内验证最小充分分层与项目硬标准优先级，并继续保留运行时与标准化边界；
- `docs/decision-ready-consumer-projection-evaluation-2026-07-18.zh-CN.md`：
  记录仓库 fixture 路由与结构负担证据，同时明确保留带日期的消费方自有验证；
- `docs/github-repository-configuration-evidence-2026-07-18.zh-CN.md`：
  记录 GitHub 元数据、社区文件发布边界、赞助入口、已启用的安全设置，以及只覆盖所记远端
  `main` revision 的 CodeQL 零结果分析，不外推到本地未发布工作；
- `docs/adaptive-harness-source-suite-and-user-sovereignty-2026-07-18.md`：
  当前“严格准入、自由消费”、来源套件选择性评审与开放/辅助/守护比例化 Harness 契约；
- `docs/round-lifecycle-contract.md`：迭代式策展轮次的计划、执行、验收和阶段性
  收官契约；
- `docs/round02-candidate-review-2026-07-02.md`：round-02 逐来源候选处置证据；
  不是 approved payload、不是 manifest、不是 routing，也不是本地 runtime sync；
- `docs/round02-obsidian-adaptation-gate.md`：Obsidian 子批次适配草案闸门；
  记录 open-format、CLI 与 Defuddle 处置，但不批准 payload、routing、manifest 或本地 sync；
- `docs/round02-pm-execution-adaptation-gate.md`：PM AI-shipping 与执行文档
  适配草案闸门；analytics、market/GTM、discovery、legal/privacy、script/tooling 组另行审查；
- `docs/round02-pm-analytics-adaptation-gate.md`：PM analytics 与 data-safety
  适配草案闸门；记录 analytics runtime-equivalence 与 synthetic data/SQL tooling
  处置，但不批准 payload、routing、manifest、执行或本地 sync；
- `docs/round02-pm-market-discovery-adaptation-gate.md`：PM market 与
  product-discovery 适配草案闸门；记录 strategy evidence 与 discovery research
  处置，但不批准 payload、routing、manifest、外部调研、参与者数据处理或本地 sync；
- `docs/round02-pm-toolkit-boundary-adaptation-gate.md`：PM toolkit 高边界
  适配草案闸门；记录 legal/privacy reference 与 personal-document/copyediting
  处置，但不批准 payload、routing、manifest、法律/合规声明、简历数据处理或本地 sync；
- `docs/round02-huashu-design-guidance-adaptation-gate.md`：Huashu design
  guidance 适配草案闸门；记录 design-direction 与 brand-asset provenance
  处置，但不批准 payload、routing、manifest、工具链、打包资产、外部媒体生成或本地 sync；
- `docs/round02-huashu-toolchain-media-adaptation-gate.md`：Huashu toolchain
  与 media 适配草案闸门；记录 HTML deck/export、voiceover/TTS 与打包资产再分发边界，
  但不批准 payload、routing、manifest、依赖安装、生成媒体、资产复用或本地 sync；
- `docs/round02-release-readiness-review.md`：Round-02 GitHub 侧 readiness
  review；汇总 3 个已审查来源和 7 个子闸门，但不批准 release payload、routing、
  manifest 变更、发布或本地 sync；
- `docs/round02-release-admission-review-template.md`：未来 owner 批准后才可使用的
  Round-02 release/admission review 模板契约；不是候选裁决，也不批准 payload、
  routing、manifest、install、发布或本地 sync；
- `docs/round02-release-admission-approval-request.md`：进入 Round-02
  release/admission 审查阶段所需的最小正式授权请求；现在已被有界 approval event
  消费，但仍阻断 payload、manifest、routing、live install、发布和本地 sync；
- `docs/round02-release-admission-candidate-review.md`：Round-02
  release/admission 候选逐项 disposition 证据；不是 approved payload、manifest、
  routing、publication 或本地 sync；
- `docs/round02-release-execution-approval-request.md`：下一道 GitHub-only
  approved-payload 与 routing 提案 gate 的正式授权请求；排除 adapter runtime、
  reference-only 晋升、已拒绝资产、发布、live install 和本地 sync；
- `docs/round02-approved-payload-routing-proposal-template.md`：未来 owner 批准后才可使用的
  Round-02 approved-payload/routing proposal 模板契约；不是 release execution，
  也不是本地 sync；
- `docs/round02-approved-payload-routing-proposal.md`：owner 已批准的 GitHub-only
  执行记录；准入 Obsidian 开放格式 payload，合并有边界的 Round-02 改进，更新
  routing/manifest/generated 投影，并继续阻止本地 sync；
- `docs/round02-local-runtime-sync-approval-request.md`：将已验证的 Round-02
  release payload 同步到本地 cc-switch、agents 和 Codex Skill 目录前所需的最小
  有界授权请求；不是 sync approval，也不是本地写入；
- `docs/round02-local-runtime-sync-execution.md`：已记录的本地 runtime sync
  执行结果；将 cc-switch hash 对齐到 Round-02 manifest，并记录 agents 与 Codex
  使用 Junction fallback 链接；
- `docs/round02-stage-closeout-review.zh-CN.md`：Round 02 逐项收口决策包；建议关闭
  本轮并暂停，先重基线 Round 03，但它本身不关闭轮次，也不授权远端推送；
- `docs/round02-stage-closeout-acceptance.zh-CN.md`：所有者接受 Round 02 有边界的
  `complete` 结论，并继续明确残余风险与不授权事项；
- `docs/round03-capability-survey-rebaseline.zh-CN.md`：用证据优先的能力调研替换
  已与实际成果重叠的旧 Round 03 计划；现已接受并进入有边界的只读执行；
- `docs/round03-capability-survey-rebaseline-acceptance.zh-CN.md`：所有者激活事件投影及其
  明确的调研授权和不授权边界；
- `docs/round03-demand-coordinate-source-contract.zh-CN.md`：锁定 STM/P/SG 只读输入、
  证据状态和晋升防火墙；不复制外部研究正文，也不授权发现执行；
- `docs/demand-coordinate-contract-reconciliation-2026-07-18.zh-CN.md`：对账 8 条
  来源支持的需求记录和全部 62 行有界坐标，验证有界合同，同时保持需求模型穷尽开放；
- `docs/native-runtime-baseline-evidence-gap-reconciliation-2026-07-18.zh-CN.md`：
  区分覆盖 4 条需求的日期化单宿主元数据基线与后续 4 条仅评审需求线，因此基线验收
  继续保持部分完成；
- `docs/residual-gap-proof-evidence-gap-reconciliation-2026-07-18.zh-CN.md`：验证
  残余缺口拒绝侧防火墙，同时因当前没有受支持正例而保持正向证明路径部分完成且非真空；
- `docs/starred-capability-source-discovery.md`：用户 star 发现面的初筛，用于后续候选来源、
  基线、索引和排除项治理；
- `docs/public-skill-source-static-review-batch-2026-07-18.zh-CN.md`：首批 5 个来源的
  精确版本、不执行静态复核与组件处置；
- `docs/loopy-demand-level-alternative-comparison-2026-07-18.zh-CN.md`：原生、现有链路
  与 Loopy 精确正文的对比，以及纯夹具下一闸门；
- `docs/user-starred-new-source-preflight-2026-07-18.zh-CN.md`：星标清单新增 5 个来源的
  当前元数据、历史证据复用、漂移、许可证和下一闸门初筛；
- `docs/user-starred-index-stale-source-resolution-2026-07-18.zh-CN.md`：两个失效直接安装
  坐标的只读处置，且不静默替换可能后继；
- `docs/user-starred-index-child-source-classification-2026-07-18.zh-CN.md`：对 14 个可用
  固定子来源完成聚类，记录当前无需求关联选择，并在不宣称全网完整的前提下验证
  本轮边际收益停止规则；
- `docs/lifecycle-metabolism-reconciliation-2026-07-18.zh-CN.md`：依据已观察到的消费者
  证据验证本仓反馈回流路径，并用确定性夹具验证已批准 Skill 的弃用、迁移、回滚
  和退休合同；真实消费者的成熟度证据仍然开放；
- `docs/cross-agent-claim-limit-reconciliation-2026-07-18.zh-CN.md`：为 9 类证据记录
  宿主、模型、推理、加载器、激活、权限、工作区、日期、反例和重检边界；验证的是
  主张防火墙，不是跨 Agent 行为或一致性；
- `docs/consumer-mapping-evidence-gap-reconciliation-2026-07-18.zh-CN.md`：区分 Codex
  的当前静态部分证据、Claude 的概念性证据和当前已支持实时消费者映射；只读共享目录
  快照记录 73 个 Skills、旧事务 19 个漂移声明、锁文件声明的 27 个 Lark Skills，以及
  27 个外部或未知目录，但不主张所有权或变更权限；
- `docs/user-sovereignty-and-foreign-coexistence-reconciliation-2026-07-18.zh-CN.md`：
  验证外部所有权默认、明确可预览可逆转换，以及不假定账号或遥测；多 Agent 运行共存
  证据继续保持部分完成；
- `docs/pm-skills-current-revision-delta-review-2026-07-18.zh-CN.md`：PM Skills 精确的一提交
  增量复核，将两份 Skill 正文共 5 行变化与较大的宿主命令变化分开；
- `docs/loopy-contract-fixture-protocol-2026-07-18.zh-CN.md`：18 个确定性配对合同夹具，
  以及当时尚未授权的历史试验边界；
- `docs/loopy-disposable-agent-trial-result-2026-07-18.zh-CN.md`：已授权的 12 次原生、
  现有链路与 Loopy 行为对照，以及“仅作参考”的裁决；
- `docs/round03-intent-binding-demand-review-2026-07-18.zh-CN.md`：来源绑定的
  `STM-11`/`P1`/`P2`/`SG-01` 对比，以及“现有路径足够”的裁决；
- `docs/round03-authority-boundary-demand-review-2026-07-18.zh-CN.md`：来源绑定的
  `STM-20`/`P9`/`SG-05` 分层权限对比，以及“无残余缺口”的裁决；
- `docs/round03-premise-challenge-demand-review-2026-07-18.zh-CN.md`：来源绑定的
  `STM-07`/`P4`/`SG-03` 平衡质疑和开放发散裁决；
- `docs/round03-cognitive-offload-monitoring-demand-review-2026-07-18.zh-CN.md`：来源绑定的
  最终坐标线，以及长期认知和生产监控证据限制；
- `docs/round03-capability-survey-result-package-2026-07-18.zh-CN.md`：本批十项结果包、
  可供决策的 62 行有界坐标包络、开放需求模型证据与明确非授权边界；
- `docs/round03-complete-coordinate-envelope-reconciliation-2026-07-18.zh-CN.md`：
  62/62 状态校准、四类开放缺口区分，以及“证据触发的监测与复查”决策；
- `LICENSE`、`NOTICE` 与 `THIRD_PARTY_NOTICES.md`：仓库许可证、归属声明和第三方 Skill notice；
- `CONTRIBUTING.md`、`CODE_OF_CONDUCT.md` 与 `SECURITY.md`：公开贡献、社区协作和安全报告边界；
- `docs/license-policy.md`：仓库自有代码、文档、生成投影、第三方 Skill 正文和官方基线的分层许可证策略；
- `docs/public-private-boundary.md`：公开/私有发布边界和用户配置模板指引；
- `docs/sustainability.md`：成本姿态、赞助边界与 free-first 纪律；
- `generated/`：确定性派生投影，不是第二真相源；
- `registry/routing.json` 与 `registry/scenarios.json`：历史适配路由元数据和 105 场景
  结构化策略语料；
- `registry/skill-portfolio-current-authority.json`：当前 Skill payload 与
  “组合建设/任务启用”权威；
- `registry/skill-portfolio-inactive-source-candidate-pool-2026-08-02.json`：
  当前有界来源筛选与 9 个来源的精确下载审查批次；
- `registry/skill-portfolio-exact-acquisition-static-preflight-2026-08-02.json`：
  精确干净下载、静态依赖信号与冲突证据；
- `registry/legacy-adapted-live-lineage-reconciliation-2026-08-02.json`：
  将 13 个逐文件一致的弃用派生体与 6 个同名 Matt 上游 Skill 分离；
- `registry/cc-switch-legacy-adapted-thirteen-removal-event-2026-08-02.json`：
  这 13 个派生体的管理器减法事件、保留备份、事后状态与清理边界；
- `registry/skill-portfolio-kepano-obsidian-adjudication-2026-08-02.json` 及其
  管理器注册事件：精确五项审查、三项暂缓安装候选与不安装的来源发现；
- `registry/skill-portfolio-phuryn-pm-representative-adjudication-2026-08-03.json`：
  对 68 项 PM 目录中 13 项代表样本进行精确 Git 对象审查，形成三项待对照候选及明确的
  依赖、重叠、偏好模板和高风险领域暂缓裁决；未注册来源，也未安装；
- `release-manifest.json`：弃用过渡 payload 的精确路径、大小和哈希；
- `scripts/`：只负责验证和确定性投影生成。

## 验证方式

```bash
python -B -m unittest discover -s tests -v
python -B scripts/build_release_manifest.py --check
python -B scripts/build_topology.py --check
python -B scripts/simulate_routing.py --all
python -B scripts/verify.py
```

验证覆盖 registry 契约、引用、派生文件一致性、来源证据、精确 payload、输入绑定的
路由投影、全部 27 个生命周期节点和 105 个确定性对抗场景。自然语言理解仍由 Agent
负责；模拟器验证归一化后的策略决策，不伪装成关键词分类器。它不会安装 Skill。

## 更新规则

每个上游版本都必须作为新的不可变准入：固定版本、保存许可证和来源证明、审查可执行
面、评估安全、依赖、可移植性、重叠和维护状态，然后在不改写正文的前提下记录审查与
管理器事务裁决。任何候选裁决本身都不等于运行时批准。

官方外部能力基线可以用于覆盖关系对照，但使用前仍需经过许可证、来源证明、安全、依赖、
可移植性、重叠和维护审查。source-available 或 all-rights-reserved 的官方内容只能
作为 reference，除非另有明确授权路径。

用户 star 的仓库可以作为发现入口，但 star 不等于批准。一个来源可能被归类为官方基线、
第三方候选、发现索引、外部能力元数据、仅 reference 或 reject；在正常准入流程闭环前，
不得进入 `skills/`、manifest、generated routing projection 或 live 执行路径。

历史发现记录可以保留为来源证据，但任何发现来源都没有优先准入通道。任何候选在本仓
完成 intake、精确来源审查、验证、拓扑/元数据更新，以及适用的管理器/消费侧授权前始终
只是 advisory。

## 安全边界

- `generated/` 只是 registry 真相的派生投影；
- 候选内容或带日期的重叠证据不得被描述为已经安装或可以执行；
- 跨 Agent 可移植性不得削弱权限、安全、证据、许可证或真实环境限制；
- 安装、账号连接、外部写入和信任边界变化由消费者侧处理，并需适用的授权。

## 公开发布状态

本仓按公开安全原则设计，但公开可见不等于降低发布闸门。第三方再分发边界、来源证明、
私有 overlay 排除和赞助入口仍由仓库所有者作为发布决策单独控制。仓库自有代码和治理机制
采用 Apache-2.0；仓库自有文档和公开治理文本按
[`docs/license-policy.md`](docs/license-policy.md) 的分层策略治理。当前路径不需要 GitHub Pro
或 Team；只有当私有 Actions 分钟、组织治理或多人审查确实需要时，才考虑升级。

## 赞助

如果本项目对你有帮助，并希望支持持续维护、来源复核、文档、测试与社区工作，欢迎自愿赞助。
赞助完全可选，不购买支持优先级、准入、发布决策、治理例外、功能承诺或技术影响力。

| 微信支付（人民币） | 支付宝（人民币） |
| --- | --- |
| ![微信支付收款码](https://raw.githubusercontent.com/yiheng8023/home-edge-bootstrap-public/main/docs/assets/sponsoring/wechat-pay.png) | ![支付宝收款码](https://raw.githubusercontent.com/yiheng8023/home-edge-bootstrap-public/main/docs/assets/sponsoring/alipay.png) |

跨境或其他受支持币种可使用
[PayPal 付款链接](https://www.paypal.com/ncp/payment/LNTF8KXGJXMZY)。付款前请核对结算页显示的收款方。
完整边界见[赞助说明](SPONSORING.zh-CN.md)。
