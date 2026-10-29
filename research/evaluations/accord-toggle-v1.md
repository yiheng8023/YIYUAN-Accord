# Accord 启用与未启用：评价初版

2026-10-29。本文、[六份合成任务材料](../../evals/comparisons/accord-toggle-v1.json)、[文件检查工具](../../scripts/grade_accord_comparison.py)及其[校准反例](../../tests/product/test_accord_comparison.py)共同构成开发期初版。它们用来校准任务、判分和记录方式；**尚无真实双组运行或产品增益结论**。工程与产品主线见[当前计划](../../docs/operations/PLAN-v3.3.md#后续候选适配与对照展示)。

## 回答什么问题

在某个明确的宿主、模型、环境和任务范围内，启用 Accord 对完整交付、可靠性、可避免的人工作业以及总成本带来了什么变化？何时有益、无差异或有负担？先回答这些问题，再决定改进和传播内容。

同一宿主的未启用组就是有效的候选基线，不要求先找到同类产品。需要证明的是两组条件可比，不能以默认弱配置、被移除的其它插件或开发者暗中救援制造差值。整体启用差值只归于受测组合；某个 Hook、Skill 或机制的单独贡献需要另行消融证据。

功能验收、工程质量、实际使用价值与发行分别判断。已有 A01–A08、质量底线和历史失败保持；本初版不改写其通过记录，也不成为日常用户的新流程。3.3.2 保留为发展节点，当前 3.3.4 发行包和标签独立保存。评价材料本身不要求新发版；若发现真实缺陷，则按受影响对象、兼容性、风险和修复验证决定维护或发版。

## 软件工程是基础

复用 [PLAN 的动态评价](../../docs/operations/PLAN-v3.3.md#全维度动态评价框架)、[现有验收](../../docs/operations/ACCEPTANCE-v3.3.md)及 [reshaping-guidance](../../product/reshaping-guidance.json)，按需要取用，不增加一套相互竞争的质量总分。

| 观察对象 | 对照中可见的事实 | 仍需工程检查的部分 |
|---|---|---|
| 功能正确与完整 | 必要要求逐项实现、遗漏、错误、实际成品 | 受影响调用者、接口契约、边界输入及回归 |
| 可靠性与恢复 | 中断后的完整性、原目标和决定保留、错误与修复 | 生命周期、并发/状态一致性、异常与退出；成功一次不等于可靠性已证明 |
| 兼容与协作 | 实际宿主和第三方组合中是否干扰或失效 | 通用职责与宿主实现的边界、共享状态所有权、接口变动影响 |
| 用户体验与控制 | 可避免催促、纠错、救援及其时间；结果可理解性 | 首次启用/信任、必要决定、无障碍与真实用户反馈；不能把少提问当成好结果 |
| 性能与资源 | 端到端时间、模型/工具用量、可得资源峰值及退出成本 | 冷热启动、缓存、并发、长期运行和维护成本 |
| 安全、隐私和原件保护 | 授权遵守、输入保护、暴露/误写和实际资源后态 | 适用的威胁模型、依赖和变更审阅；本合成任务不构成安全认证 |
| 可维护、可测试与可观察 | 这轮修改能否解释、定位、验证及回退 | 职责耦合、重复表示、测试误判、证据链和升级/移除成本；文件少或测试多不是质量分 |

[ISO/IEC 25010:2023 官方摘要](https://www.iso.org/standard/78176.html)提供覆盖产品全生命周期的质量模型参考；[SWEBOK 官方知识领域](https://www.computer.org/education/bodies-of-knowledge/software-engineering/topics)提供需求、架构、测试、运维、维护和质量等工程视角。这些参考帮助查遗漏，不替本项目选择指标、权重或接受风险；本文没有完成标准符合性评价，也未据摘要复刻完整标准。

## 三层判定，不急于合成总分

1. **任务必要结果与不可抵消底线**：正确、完整、原件保护、实际授权和任务适用的工程要求逐项判断。失败、未知、不适用分开；不适用需要理由。局部有用成果仍记录，但不能用省时或平均分抵消必要结果失败。
2. **原始度量**：保留单位、分母、观察区间、来源和缺失原因。先展示每个配对和失败，再做适用范围内的汇总。成功案例耗时不能替代全部尝试的耗时与成功率。
3. **偏好取舍**：只有实际决策需要时才使用权重。说明代表谁、适用何种任务，在揭盲前冻结归一化和权重，并检查合理权重变化是否改变结论。不用本批结果的最大/最小值临时归一化迎合赢家。

首轮不计算综合分，不预设 Accord 必须获胜，也不指定永久的“最佳”模型、工具路线或人工交互次数。

| 原始度量 | 记录口径 |
|---|---|
| 必要要求 | 每项 pass / fail / unknown / not-applicable，附成品或实际来源；任务总体结论另判 |
| 人工介入 | 必要授权/身份动作、真实偏好/需求新增、可避免催促、纠错、救援分别计次数与主动操作秒数；模糊项保留待判 |
| 时间 | 首次输入到完成核验和资源退出的端到端秒数；准备、排队/服务等待、正常用户等待、救援和退出另列。不用只计成功模型调用的时间 |
| 用量与资源 | 实际输入/输出/缓存 token、工具调用、可得资源峰值及单位；缺测为 null 并说明原因，不填零、不把账户配额当费用 |
| 可靠性 | 原始失败、重试、救援后的完成、未捕获触发、重复有害效果分别记录；普通重复读取不直接算错误 |
| 变更与维护 | 受影响职责/接口/消费者、必要修改及验证/回退成本；小样本任务不能推出长期维护收益 |

## 配对与执行前冻结

沿用 [LAUNCH 公平对照条件](../../docs/operations/LAUNCH-v3.3.md#启用与未启用对照准备)。每对至少冻结：宿主实际二进制/后端/OS、精确 Accord 包、模型/推理强度、可用子模型与工具、权限、资源和时间上限、工作目录与材料摘要、原生恢复方式、顺序、救援及中止规则、评分版本。

新会话与中立工作目录必须检查祖先/用户/项目指令、记忆、已加载 Skill、Hook、插件及状态。此仓库的 AGENTS 含 Accord 指导，不能直接作为未启用组工作目录。两组保有相同的原生及第三方能力与获准调度选择；不强制相同工具序列。只切换目标 Accord，不能用全局禁插件开关顺便删去基线能力。停用不清除已进入上下文的指导。

现有 `observe_codex_entry.py` 的 `installed-plugin` 路线要求 Accord 已启用；`native-package-hooks` 路线会忽略用户配置并禁用其它插件/App，不能直接充当这一公平对照。进一步核对 [Codex 0.165.0 配置加载源码](https://github.com/openai/codex/blob/360319d8dee62d87e2d59fc0c21805d79519cfed/codex-rs/config/src/loader/mod.rs#L406)及[插件加载器](https://github.com/openai/codex/blob/360319d8dee62d87e2d59fc0c21805d79519cfed/codex-rs/core-plugins/src/loader.rs#L829)，可用进程参数 `-c 'plugins.yiyuan-accord-codex@yiyuan-accord.enabled=false'`，启用组改为 `true`。本机两个新进程在同一中立临时目录中的目标 marketplace 清单分别观察到 installed=true、version=3.3.4、enabled=false/true；两进程自然退出，配置与用户 AGENTS 摘要未变，临时目录已移除。该观察只覆盖配置清单，不证明实际模型上下文、其它组件一致或无记忆污染。

真正派发前，仍须核实际两臂加载、其它有效条件一致和中立目录信任；缺少这些观察时保留未决，不启动伪对照。关闭插件不会撤回其它来源中的相同指导，源码标签与本机版本字符串也不单独证明构建身份。优先扩展已有适用观察器的期望状态和参数绑定，复用原生进程控制/记录/清理，不为评价再建常驻控制层。

初次预检已遇到远程 Skill 清单的启动时序差异；有界延后复读才观察到两组相同的306项非目标 Skill及正文摘要。原生无业务模型探测另确认两组均会加载包含项目历史的个人记忆；共同的进程级禁用记忆已核无记忆注入，用户元指导和其它组件保持。这限定为该受控条件下的插件增量，不能称默认配置或完全无相关指导。首个业务尝试的独立产物读取被拒绝，尚未形成有效配对；实际状态见[当前接续](../../docs/operations/CONTINUATION.md#目标与当前写者)。观察器读取失败和产品任务失败应分别记录，不能删除尝试或用执行者自述补齐独立成品证据。

原始资料与期望答案分开。执行者只得到准备目录内的输入和同等任务请求，不给评分源码、答案或 Accord 提示。公开的合成题属于校准/开发集；应记录答案可访问性和潜在训练污染，不能作为保密的正式测试集。正式评价另取未用于优化的新任务材料和适用的真实任务。

## 三类、六份材料

| 材料 | 用途与触发 | 自动检查 | 不能据此推出 |
|---|---|---|---|
| S1A / S1B | 一次输入即可完成的数量汇总，保留零值和排除项 | 原件字节、分类/总数、排除 ID | 不证明复杂推理、跨宿主或长期收益 |
| C1A / C1B | 初版返回后追加会改变既有汇总的规则，并增加一个消费者 | 旧汇总已修正、新看板与当前规则一致 | 两轮顺序变化不等于任意实时打断处理 |
| R1A / R1B | 已有完整输出、仍有必要业务成果未完成且原轮活动时，原生中断、确认终态，再在同一线程恢复 | 每批完整记录、总索引、数量、原件 | 文件成品不证明原生恢复；不测外部交易的恰好一次效果 |

这些是有意小型化的**合成数据工作**，用于验证题目和检查器能否发现差异，不是已经证明代表用户工作分布的样本；工程评价另按上表取证，不能因材料主要是数据任务而省略软件工程。两个材料变体也不是同一任务的独立重复。

十二次运行只是六对试行的候选规模，不是统计功效结论。先做材料和判分校准，再在派发前冻结具体试行批次；同类两对可交换启用/未启用先后。若做正式效果估计，应先确定目标任务分布、最小有意义差异和变异，再决定独立任务数与重复次数，并报告不确定性。多重复不能补齐缺失的任务类型。

中断任务必须冻结触发谓词、观测方式和中断/退出时限，并保存中断前后成果快照，证实仍有必要业务未完成。文件已全部交付、仅结束文字未写完不能算业务恢复。未捕获预定节点、工具不支持或宿主已经结束的运行都要保留，标为“恢复触发未实现”；不能事后改称恢复成功，也不能只保留抓到节点的好结果。不得删除成果或限制合法批处理来制造中断条件。只提供预定中性续作输入，不由观察器补状态、答案或替 Agent 修复。达到超时/失败规则后保留结果与消耗，救援后成功另列。

## 校准和使用

以下命令只准备任务输入或读取结果，不调用模型、不安装/启用插件、不改信任与配置。`prepare` 只接受不存在的新目录，其父目录须已存在。选择属于该次试验的中立位置；示例中的占位路径需换成实际路径，不能用 Accord 源码仓库作基线目录。

```powershell
python -B scripts/grade_accord_comparison.py prepare --case S1A --workspace C:/comparison-work/S1A-on
python -B scripts/grade_accord_comparison.py grade --case S1A --workspace C:/comparison-work/S1A-on
python -B -m unittest tests.product.test_accord_comparison
```

初版请求、变化输入和期望产物在材料文件中有完整定义。`prepare` 返回请求供执行器按时发送；不会将答案或请求脚本写进任务目录。C1 的初版可用 `--stage initial` 检查，最终用默认 `final`；发送变化输入前保留初版实际结果，包括失败。R1 的触发与中性恢复输入在材料中，须另经真实宿主观测。

检查工具输出的 `fileCriteria=pass` **只表示列明的文件谓词通过**；`runValidity`、`taskOutcome`、`incrementalValue` 始终保留 `unverified`。缺输入、无法安全读取、格式失真与内容错误分开保留。它不执行产物代码，也不检查未列出的全部路径、网络、宿主身份或所有副作用；执行者结束并交接文件后才运行。不要把退出码 0 或自填记录作为全面通过。

校准至少覆盖：正确但没有 Accord 术语的成品；合法排版/数组顺序变化；错误总数却声称成功；变化后只改新看板、旧汇总仍错误；完整索引但漏交一批；原件被改；重复记录代替缺失记录；类型、重复 JSON 键和不完整数据。参考成品通过只能说明检查器可接受该构造，必须再从原始材料独立验算答案，并检查刻意错误的拒绝。

涉及语义、用户负担和轨迹的部分先由两个评审者对匿名随机排序的校准材料独立判断，记录分歧及原因，再修订口径。成品盲评与过程评审分开；过程无法完全盲化须披露。开发者自审不能称独立用户评价。判据改动后保留旧判分，正式比较使用新鲜任务；不能修改口径后只重报有利结果。

## 一份配对记录应保留什么

复用实际宿主轨迹、产物和已有核验结果，避免要求执行 Agent 逐步自填长表。评价者在独立目录保存以下字段；每个事实绑定具体来源和时间，所有未知项保留原因。

| 记录 | 必要内容 |
|---|---|
| 身份与条件 | pair/run/case/stage ID、材料/评分器摘要、开始前冻结记录、实际线程、宿主与包摘要、模型、有效工具/插件/Hook/指令/记忆、预算与权限 |
| 输入和事件 | 初始请求、预定变化/中断/恢复、实际触发、人工介入类别和时间、错误、救援、配置漂移 |
| 结果 | 实际产物摘要、检查器逐项结果、独立语义判断与分歧、必要结果失败/未知/不适用、原件和资源后态 |
| 消耗 | 各段及总时间、原始用量、人工主动时间、冷/热与缓存条件、未知成本，失败尝试和救援消耗 |
| 结论范围 | 运行有效性与产品失败分别判断；每对原始差异、全部失败/平局/退化、样本覆盖及未测项；原始记录私有、公开内容脱敏 |

同一任务/输入哈希并不证明同一环境；两份记录写得相同也不证明条件相同。上游/模型/配置实质漂移时停止相依配对，保留原尝试，再按新条件冻结；不静默删样本。对照只放大可核实的差异，不声称推断出精确隐藏成本或不可见机制。

## 从评价进入有限重塑

审查从目的和用户结果开始，沿设计预期 → 通用职责 → 宿主适配与生态协作 → 具体实现 → 验证与运维向下展开；修改后的证据沿实际依赖向上核验。所有既有设计和实现均可质疑，但是否更改由问题、收益、风险及证据决定，不因项目经过数月就假定必须重写。

优先核三个问题：宿主更新后哪些职责已有更好原生路径；Accord 的补充是否仍必要且不与宿主/第三方争抢状态或生命周期；预期能力是否经正常入口实际发生并改善结果。仓库顶层的 `runtime/task-checkpoint.cjs` 实际依赖 Codex 输入读取，不能按目录名称把它当成通用层；代码重复、模块位置或旧计划本身都不是缺陷证明。

每个有实际证据的候选改进保留一条足够的决定记录：问题与影响、来源、责任所在、继续保持/简化/替换/移除的可行选项、受影响调用和历史结论、验证与回退办法、预期及实际维护成本。先处理关键短板与不必要耦合，小范围验证，再决定扩大、保持或撤回；允许“无需修改”成为结果。重塑不是同时重写全部系统，也不是通过减要求解决验收失败。

对宿主更新先固定精确条件：可行时比较同一 Accord 在新旧宿主上的变化；对 Accord 候选改进比较同一宿主上的新旧实现。宿主×Accord 组合的交互效应只在取得相应组合证据后讨论；条件不可复现时明确混杂，不把上游收益记到 Accord 名下。旧数据按原版本保留，不能自动失效，也不能自动沿用为新条件结论。

官方公开目录仍是可选分发渠道；新宿主适配保留候选地位。后续方向的核心是巩固、验证与持续迭代，不预设具体版本号或时间承诺。真实收益摘要再进入 README，同一真实运行再供 NEXUS 素材；公开传播按原适用授权另核，不用校准样例充当宣传实测。

## 方法参考与限制

2026-10-29核查：[OpenAI 的评价方法说明](https://openai.com/index/trustworthy-third-party-evaluations-foundations/)强调受测声明与运行条件；[Anthropic 的 Agent 评测说明](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)区分真实结果与轨迹，并讨论判分校准。这里只借鉴方法，不依赖某厂商产品或把它们视为 Accord 的评价权威。

当前文件检查不能证明宿主有效隔离、真实使用效果、安全覆盖、长期成本或统计显著性。可用的评价方法和工程质量要继续校准，未知不是零分、完成或默认通过。

## English summary

This is a developer calibration kit, not measured product value or a release gate. Six synthetic data tasks cover a simple baseline, a later requirement change and interrupted file processing. They calibrate input/output checks; they are not a representative user sample or a power analysis. The preparer exports inputs only. The read-only grader checks listed file facts and keeps run validity, task outcome and incremental value unverified. Review behavior, actual host isolation, human effort, total costs and resource exit separately.

Keep non-compensable requirements, raw measurements and optional stakeholder preferences distinct. No composite score is prescribed. Preserve failures, ties, unknowns, valid alternative output forms and evaluator disagreements. Inspect effective configuration and guidance before native paired trials; a global plugin-disable switch is not a fair Accord-only control. Public calibration material must not be represented as an unseen test set.

Software engineering quality remains fundamental: correctness, reliability, compatibility, user control, security, maintainability, testability and lifecycle costs need suitable evidence beyond task scores. Question design and implementation from intended outcomes down through portable duties, host adaptation and integration; verify changes back through their affected dependencies. Prefer bounded, reversible improvements, including retaining what already works. Future work centers on consolidation and iteration, with host expansion optional and no promised version numbers. Existing releases and historical evidence remain immutable; findings determine whether an actual product change and new release are needed.
