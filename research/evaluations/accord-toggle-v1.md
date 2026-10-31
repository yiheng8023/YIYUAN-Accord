# Accord 启用与未启用：评价初版

2026-10-29初版。本文、[六份合成任务材料](../../evals/comparisons/accord-toggle-v1.json)、[文件检查工具](../../scripts/grade_accord_comparison.py)及其[校准反例](../../tests/product/test_accord_comparison.py)共同构成开发期初版，用来校准任务、判分和记录方式。初版建立时尚未执行真实双组运行；随后已完成[2026-10-30首轮有限试行](#2026-10-30-首轮有限试行)。**两对小样本不支持普遍产品增益结论**。工程与产品主线见[当前计划](../../docs/operations/PLAN-v3.3.md#后续候选适配与对照展示)。

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

初次预检已遇到远程 Skill 清单的启动时序差异；有界延后复读才观察到两组相同的306项非目标 Skill及正文摘要。原生无业务模型探测另确认两组均会加载包含项目历史的个人记忆；共同的进程级禁用记忆已核无记忆注入，用户元指导和其它组件保持。这限定为该受控条件下的插件增量，不能称默认配置或完全无相关指导。首个业务尝试的独立产物读取被拒绝，未形成有效配对；原失败与之后独立批次分别保留，见下文及[当前接续](../../docs/operations/CONTINUATION.md#目标与当前写者)。观察器读取失败和产品任务失败应分别记录，不能删除尝试或用执行者自述补齐独立成品证据。

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

准备目录也是有效条件。2026-10-30的本机 Windows/Python3.14.8/CLI0.165 无模型预检中，`tempfile.mkdtemp`根下的沙箱新建文件无法被外层读回；同一 Temp 父目录下新建普通继承目录后，相同命令的新文件可在退出前后读回，两次均自然退出且保护配置未变。Python在Windows对`0o700`的[特殊权限处理](https://docs.python.org/3.14/library/os.html#os.mkdir)与该现象吻合，但未读取旧产物的实际ACL，不能宣称所有权限问题已解释。后续独立试行仅调整双方合成业务目录的准备方式，保留原失败，不改ACL、沙箱或共享设置；私有状态和同身份测试的临时目录不作全局替换。普通目录检查、执行者自读和原生轮次完成均不替代独立产物读回。

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

### 2026-10-30 首轮有限试行

`pilot-02`只覆盖S1A简单汇总和C1A两轮需求修订：各一对、四次运行、六个业务阶段，顺序为S1关闭→启用、C1启用→关闭。主体为本机Windows、CLI0.165.0、Accord3.3.4、原生报告的`gpt-6.1-sol/medium`；两组使用相同公开材料、workspace-write、approval never、无人工救援和进程级关闭记忆，共同用户元指导及其它组件保留。执行前冻结包、材料、判分器、观察器与运行条件，每轮重核非目标Skill来源；这不是默认配置全景或未公开测试集。实际宿主权限允许网络，任务请求禁止主动联网；模型工具轨迹未见网络、安装或共享配置命令，不等于宿主/MCP后台零通信。前述无模型文件探测单独使用networkAccess=false，未假称它与正式业务的全部环境相同。

| 任务 | Accord | 文件阶段检查 | 端到端秒 | 原生累计输入token | 其中缓存输入 | 输出token |
|---|---|---|---:|---:|---:|---:|
| S1A | 关闭 | 1/1通过 | 42.22 | 107,256 | 93,440 | 738 |
| S1A | 启用 | 1/1通过 | 48.29 | 122,536 | 104,192 | 861 |
| C1A | 启用 | 2/2通过 | 68.87 | 253,836 | 233,472 | 1,961 |
| C1A | 关闭 | 2/2通过 | 65.89 | 191,408 | 176,384 | 1,537 |

两个分开的AI评审对匿名随机排列成品独立验算，四份最终成品和C1中间成果均符合相应请求；这是开发者控制的试验与代理评审，不是独立用户评价。初次材料未提供S1执行前输入参照，原件保持先记未知，补入冻结材料派生字节与原prepare摘要后，交付端输入与执行前绑定摘要一致。补证不是补造执行前快照，也不证明运行中从未改后恢复。另一代理按实际请求、配置、工具和退出记录完成非盲过程复核，未见使这两对限定观察作废的新问题；文件通过不自动升级为全面验收。

时间覆盖工作区准备、能力就绪观察、模型轮次、成品检查和退出；token来自每个原生线程最后的累计报告，包含重复上下文和缓存，不能当成独立信息量或费用。另有首次`pilot-01`未配对失败：41.33秒、原生累计80,702token；四次无业务加载探测累计117,864token，均单独保留，不塞进有效配对，也不从总投入中抹去。人工主动时间、账单费用、连续资源峰值及整个开发工程成本未完整测量。

**这批小任务未显示成品收益差异，启用组两次均使用更多报告token和时间。** 只有每类一对，模型随机性、缓存与运行顺序仍限制因果解释；不能推断普遍性能劣化，也不能证明更复杂任务的收益。启用组两次主动读取了验证Skill，这提供了研究简单任务指导成本的具体线索，但尚不支持仅凭两例删改运行机制。中断恢复、交接、跨宿主与第三方业务协同未由本批验证，后续应使用新材料检验必要机制及轻量任务负担，不为证明价值选择性加码或隐去平局。

审查从目的和用户结果开始，沿设计预期 → 通用职责 → 宿主适配与生态协作 → 具体实现 → 验证与运维向下展开；修改后的证据沿实际依赖向上核验。所有既有设计和实现均可质疑，但是否更改由问题、收益、风险及证据决定，不因项目经过数月就假定必须重写。

优先核三个问题：宿主更新后哪些职责已有更好原生路径；Accord 的补充是否仍必要且不与宿主/第三方争抢状态或生命周期；预期能力是否经正常入口实际发生并改善结果。仓库顶层的 `runtime/task-checkpoint.cjs` 实际依赖 Codex 输入读取，不能按目录名称把它当成通用层；代码重复、模块位置或旧计划本身都不是缺陷证明。

每个有实际证据的候选改进保留一条足够的决定记录：问题与影响、来源、责任所在、继续保持/简化/替换/移除的可行选项、受影响调用和历史结论、验证与回退办法、预期及实际维护成本。先处理关键短板与不必要耦合，小范围验证，再决定扩大、保持或撤回；允许“无需修改”成为结果。重塑不是同时重写全部系统，也不是通过减要求解决验收失败。

对宿主更新先固定精确条件：可行时比较同一 Accord 在新旧宿主上的变化；对 Accord 候选改进比较同一宿主上的新旧实现。宿主×Accord 组合的交互效应只在取得相应组合证据后讨论；条件不可复现时明确混杂，不把上游收益记到 Accord 名下。旧数据按原版本保留，不能自动失效，也不能自动沿用为新条件结论。

官方公开目录仍是可选分发渠道；新宿主适配保留候选地位。后续方向的核心是巩固、验证与持续迭代，不预设具体版本号或时间承诺。真实收益摘要再进入 README，同一真实运行再供 NEXUS 素材；公开传播按原适用授权另核，不用校准样例充当宣传实测。

### 2026-10-31 既有轨迹的负担分解

这次只复算同一批留存的四份原生记录，没有新模型运行或业务重放。按顶层`type=token_usage_record`读取每个不同响应的`payload.usage`，逐响应求和均与原`finalUsage`一致；不重复累加线程/轮次累计镜像，缓存输入已含在输入中，推理输出也不另加一次。

| 既有任务 | 工具调用（启用/关闭） | 模型响应（启用/关闭） | 报告总token差 | 未缓存输入差 | 端到端秒差 |
|---|---:|---:|---:|---:|---:|
| S1A | 3/3 | 4/4 | +15,403 | +4,528 | +6.070 |
| C1A | 6/5 | 8/7 | +62,852 | +5,340 | +2.979 |

两次启用运行各读取核验Skill一次，未发现同一运行重复读取。S1首个模型响应的输入已比关闭组多2,986token，发生在该Skill读取之前，故不能把全部增量归因于读取；C1首响应也已多2,983。C1额外一次响应是候选来源，但不能独自解释全部差额。入口已有简短协调指导，也不证明核验Skill的专用细节已经送达或首次读取多余。

缓存输入差分别为10,752和57,088，输出差分别为123和424。原顺序、缓存内容/命中条件和随机波动未被分离；报告总token不等于同比账单费用、计算量或时延。这些结果仍只属于3.3.4/CLI0.165.0的原两对任务，不评价当前开发修订性能，也不为求正向结论补跑旧任务。后续只对新材料中会改变方案选择的问题取证。

### 2026-10-31 新的普通维护研究

这是一项有实际维护用途的研究：用真实运行时代码和当前二进制生成的协议类型，判断结构化接口覆盖与仍需保留的来源义务。它不是前述六份合成数据题的重跑，也不新增正式验收case。语料快照为`a5b303ff`/未发布f050，执行条件为正式3.3.8/2c33、CLI0.166.0、同一ChatGPT CLI账户与Sol/high；模型/effort由宿主记录，后端未独立证明。

单项开关先在零模型下核验：77条非目标本地插件元数据、67条其它Skill记录相同，Accord启用Skill为0/5，均无加载错误、自然退出/Job0；该数不是已安装插件数，不证明所有动态组件或缓存字节相同。正式运行使用同一目录、原请求、11份真实runtime及146份协议类型的引用闭包，只改变进程级目标开关；记忆关闭、私有写沙箱/网络关闭、共同祖先指导是两组共同实验条件，不代表默认配置。两组实际请求字节及共同指导正文分别同hash，输入/配置/338包保持；冻结随机顺序为开启→关闭，各仅运行一次，未向执行者补答案或延长窗口。

| 观察 | 开启 | 关闭 |
|---|---:|---:|
| 原执行及资源终态 | 自然exit0、Job0 | 触360秒后强制停止、Job0；原生interrupted |
| 执行至关闭，秒 | 336.985 | 360.174 |
| 父线程报告输入token | 2,875,478 | 3,120,634* |
| 父线程其中缓存输入 | 2,728,448 | 2,987,776* |
| 父线程报告输出token | 12,730 | 13,226* |
| 父线程输入＋输出 | 2,888,208 | 3,133,860* |
| 子线程末次累计输入token | 1,642,353 | 2,219,713 |
| 子线程其中缓存输入 | 1,532,288 | 2,087,936 |
| 子线程末次累计输出token | 8,466 | 6,491 |
| 子线程输入＋输出 | 1,650,819 | 2,226,204 |
| 匿名成品静态审阅 | 所核关键事实无阻断错误 | 所核关键事实无阻断错误 |

\*关闭组父线程无`turn.completed`终态用量，只列最后完整响应边界的累计counter，不包含未知中断尾部。每组均自行调用一个子代理，表中按线程保留宿主报告的counter；尚未独立核对跨线程计数与账单归属，故不相加、不把父线程用量当作整组总成本。缓存输入是输入子集，推理输出不重复相加。此处时间是父执行至关闭的墙钟，不累加重叠的子任务时间，也不包括准备和后续独审；完整账单、人工总负担、缓存/顺序/随机性及并行环境影响未分离，不能把两列直接当作完成同等执行的总成本。

开启组的原生developer入口、连续性/能力/核验Skill读取及研究Skill读取有记录；所核父、子线程的MCP调用均为0，不能据此判断未参与。关闭组未见该Accord入口。两次核验Skill文件读取中存在组合输出截断，不能仅凭同文件名判断冗余。开启组对子代理显式选择`Sol/high`，关闭组未指定模型与强度；两次均选择不继承聊天历史，宿主最终报告均为`Sol/high`，不代后端证明或选择机制的因果收益。两个子线程均完成，35条命令均已终态，其中开启/关闭各3/1条失败记录保留，文件写入均已结束；没有再派生子代理。参与、读取、遵守及因果收益仍分开。两份AI匿名静态审阅保留各一处非阻断定位补强，未回填原报告，也不代表独立用户研究或运行验收。关闭组报告虽可用，原执行失败不改签；它没有证成真正尚有必要业务未交的恢复案例，故不充当原计划的真实恢复观察。

产物提供了当前维护线索：真实回读的空`text_elements`与失败交接恢复的精确形状比较存在误拒，已另经公开入口mock区别复现；分页/完整视图与来源投影仍需逐项核实。这些是工程输入，不是替换实现或证明普遍收益的结论；本次338观察不资格化f050或后续候选。后续零模型核对中，已完成研究线程的76个item与5页分页逐ID一致，turns/list的summary只含2项；不能以summary/full单字段判定整个历史。公开mock另证恢复core会接受显式summary并交独立verify决定，随后最小修正对该标记前置持有，私有新测试在旧runtime失败、候选通过。该工程修正没有改签原研究或证明真实接管；完整turn集与真正未完业务恢复的范围继续独立保留。

### 0.166 约定与自然恢复材料的后续核对

上游约定补核（2026-10-31）：固定官方0.166 tag所指commit `6ff1e1ca`的[完整读取兼容实现](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server/src/request_processors/thread_processor.rs#L3185-L3218)与[分页展开](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server/src/request_processors/thread_processor.rs#L3540-L3608)表明，includeTurns=true仍展开turn与item页至nextCursor结束；paginated会发弃用提醒，并非该版本已移除完整读取。两份公开类型与本机二进制生成的ThreadReadParams/Turn逐字节相同，实机单turn的76item与5页回读一致；这支持继续复用该兼容接口，不据此新增一套分页组件。两个类型相同不是完整binary构建证明；多turn、变化中一致性及其它载体运行验收仍保持其实际范围。

自然压缩后的开发观察（2026-10-31）：原生日志记录05:01:29.915Z的compacted事件，之后同一Root线程/turn/epoch及7保护输入经来源核对仍匹配。压缩前兼容代码和151项/三静态执行已完成；真正待交的是父子用量限定、原失败、文档与资源后态。压缩后448750e6补齐这些必要限定并关闭中立目录，随后继续了新守卫开发。独审支持“开发期同聊天压缩后连续推进”的有界观察，不构成应用侧中断恢复验收、跨聊天接管、全环境无其它写者或Accord因果收益；无预注册对照、完整人工/费用总账。它不要求普通用户维护项目接续文件，也不替代计划中真正未完应用任务的恢复观察。

## 方法参考与限制

2026-10-29核查：[OpenAI 的评价方法说明](https://openai.com/index/trustworthy-third-party-evaluations-foundations/)强调受测声明与运行条件；[Anthropic 的 Agent 评测说明](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)区分真实结果与轨迹，并讨论判分校准。这里只借鉴方法，不依赖某厂商产品或把它们视为 Accord 的评价权威。

当前文件检查不能证明宿主有效隔离、真实使用效果、安全覆盖、长期成本或统计显著性。可用的评价方法和工程质量要继续校准，未知不是零分、完成或默认通过。

## English summary

This is a developer calibration kit, not measured product value or a release gate. Six synthetic data tasks cover a simple baseline, a later requirement change and interrupted file processing. They calibrate input/output checks; they are not a representative user sample or a power analysis. The preparer exports inputs only. The read-only grader checks listed file facts and keeps run validity, task outcome and incremental value unverified. Review behavior, actual host isolation, human effort, total costs and resource exit separately.

The first bounded native pilot completed two pairs (four runs, six stages) on Windows with Codex 0.165.0 and Accord 3.3.4. Both arms met the file requirements; the enabled arm used more reported tokens and time in these two cases. Separate AI artifact reviews and a non-blind process review support this limited observation, not independent user research or a general benefit/performance claim. Retain the earlier unreadable-output attempt and all preparation costs. Memory was disabled in both processes, shared user guidance remained, and directory preparation was corrected without changing sandbox permissions; this is not a default-configuration benchmark.

A later real maintenance-research pair used installed3.3.8/CLI0.166 with controlled shared settings. Both reports passed the bounded anonymous static review; only the enabled execution ended naturally. The disabled run reached its original360second limit and has only a last-response usage counter. Each arm also used one completed child agent. Parent and child counters are reported separately without claiming a reconciled whole-run cost. Preserve the failure, failed commands and unknown tail; this single pair proves neither general value nor qualification of the unpublished source snapshot or its successors. A later zero-model read matched all76items against five pages in the one completed research turn. A separate mocked consumer distinction justified holding explicit partial input views before verification; neither observation establishes arbitrary history completeness or real recovery. Genuine unfinished-business recovery remains separate.

Keep non-compensable requirements, raw measurements and optional stakeholder preferences distinct. No composite score is prescribed. Preserve failures, ties, unknowns, valid alternative output forms and evaluator disagreements. Inspect effective configuration and guidance before native paired trials; a global plugin-disable switch is not a fair Accord-only control. Public calibration material must not be represented as an unseen test set.

Software engineering quality remains fundamental: correctness, reliability, compatibility, user control, security, maintainability, testability and lifecycle costs need suitable evidence beyond task scores. Question design and implementation from intended outcomes down through portable duties, host adaptation and integration; verify changes back through their affected dependencies. Prefer bounded, reversible improvements, including retaining what already works. Future work centers on consolidation and iteration, with host expansion optional and no promised version numbers. Existing releases and historical evidence remain immutable; findings determine whether an actual product change and new release are needed.
