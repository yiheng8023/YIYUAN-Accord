# YIYUAN Accord

把用户想要的结果推进到可验证、可恢复的闭环，同时不让用户管理 Agent 的工具、拓扑或内部工序。

YIYUAN Accord 是一个开放、Agent 中立、机制中立、产品形态中立的人机协作系统：由小型可移植可靠性内核与动态适配、可替换的结果交付行为组成。它帮助 Agent 围绕用户当前目标选择充分路径，并在真实决策边界保留人的权限。当前产品方向是完整、有界的自举能力，而不是把插件、Hook、Runtime 或单独的自进化循环当成产品本身。

它根据用户纠正和实际观测效果持续校准，并以验证、明确未知和残留清理结束任务。

项目的广义使命是改善人与 AI 的协作；当前产品面与证据严格限定为人与 Agent 的协作场景。

[English](README.md)

> **当前版本：**使用不可变、非预发行的
> [`v3.0.1`](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.0.1)
> 正式版。
> 不要从持续移动的 `main` checkout 安装。

---

## 发布成熟度与证据

v3.0.1 是项目正式版，不再使用预发行标签。“正式版”只表示这个精确仓库、
包、有限声明与已声明的本地/托管门禁通过，不表示普遍行为、生产安全或所有
Agent 与客户端表面都已证明。测试集仍有意保持有限，因此代表性使用、反例
与失败属于持续证据。

持续移动的 `main` 当前是自举可行性调研与内核塑形中的活动开发计划。精确 revision
`ae7294652761abceb753f0571ee82c7ddeae06af` 作为已验证但未发布的 v3.1.0
历史基线保留；后续产品共识推翻了它的 `ready` 状态，但不抹去其有限证据。
因此 `main` 不是发布候选、安装源或已发布升级。P0-P3 有界逻辑调研现已完成，
语义、隔离、评估设计和 P4 产品形态纵切也已完成。P4 只准入确定性、无副作用、
纯数据的最小参考内核；它现已通过一个策略驱动的 `reconcile_closure` 接口实现。
该接口拒绝观察者与对象同一身份，并要求实验决策具有匹配的独立后状态才能闭环；
这些只是结构绑定，不是对真实来源或隔离性的自证。精确检查点
`553f5a97e08390117e877e7b913c7a501018bfa5` 现保留失败的 GT-14 至 GT-16
尝试：fixture 执行与清理已观察到，但未保留任务要求的环境组成、轮子/来源和全向量源事实。
在精确行为 revision `1bbcc9542c92674dc0b5adcb032d6f9b01248531` 上，当前契约下新鲜的
GT-14 至 GT-16 观察仅对当前组成准入、基于一手资料且不新增依赖的有界评价循环可行性，
以及一次性纯数据最小形态自举通过；失败路线与成本继续保留为反证。精确
`84447a7a1b9557e22ef5585d159459e8701fa40e` 只保留为已被替代契约下的历史事实。
后续 `f0ed9ce715afdbc5d9eb75e08225e9a1e46c554c` 的 GT-17/18 尝试及其
`08eb72a57cdb4b0d27de1df16ebeccccd1e04f9e` 旧验证器放行被独立复审否决：
GT-17 清理未绑定来源，GT-18 也未保留每阶段完整向量及载体
源/目标状态，因此只能作为来源不充分的反例。在精确 revision
`7d7a7e57b7eea02afcda21880d2f018cbc7dda0c` 上，新的来源完整重放仅对
GT-17 的有界证据纠偏，以及 GT-18 的一次合成四阶段全向量序列通过；后者保留真实载体
源/目标状态、回滚、原生无新增路线保留、后续失效、替换、退役与零任务资源。来源可追溯的
全系统平衡自审和受影响表面确定性重验收已经完成。在精确 revision
`2460adcff02bd56144f8d3f647ecef27cd5fefd0` 上，当前契约下新鲜的 GT-18 仅对一次合成四阶段
不可变全向量序列通过：代理硬门槛退化被否决并回滚，原生无新增路线仅被有界保留，后续失效
后经三条精确一次性载体边替换。新鲜 GT-19 仅对一次 Codex 本地环境感知责任分配序列通过：
声明和稀疏交集没有触发退役；观察到的同责任原生后继只允许可逆的局部退役；证据过期后 Accord
分配恢复。受阻路线、转录与查询纠错、GT-19 首次独立审查失败及高评价成本继续作为反证。
但该 GT-19 现在只保留为历史证据：它没有绑定当前类型化状态回执、用户介入失效、来源
优先级或逐责任实现模式。新的工作树源记录保留了 schema 和零规则执行策略失败，随后一个基于
精确稀疏字节的临时只读 Codex 臂与独立的合成四阶段 typed-receipt 探针完全一致，并清除了任务
副本。当前工作包已在 Skill 后增加一个共享的短时 `SessionStart` 事件适配器：`startup` 与
`clear` 保持静默，`compact` 与 `resume` 仅把受支持的事件字段作为非权威提示放入类型化最小连续性上下文，
不新增持久进程或状态。公开接缝测试、两端包字节一致性、隔离原生发现和 App Server 结构化
查询可行性通过；一个一次性 Claude 会话也实际触发了精确复制适配器的
`SessionStart:startup` 并正确保持静默。另一个 ephemeral Codex App Server 线程禁用了已枚举的安装态
Hook，通过官方 `thread/compact/start` 触发候选会话 Hook，独立观察到注入的
`signal.source=compact`，随后 Agent 以零工具调用精确返回注入的 schema 值。安装包实例的
零 turn `resume` 现在证明只恢复 goal 支撑的官方状态，`SessionStart` 要到首个 turn 才执行；
同一官方 resume 响应已直接触发状态重感知、当前回执和纯内核调用。首个安装包 turn 仍作为
“已启用但未受信”的 `NO_CONTEXT` 对照保留。两项路径与当前 HooksListResponse 结构纠正都在模型调用前
停止并完成清理；随后一个单独获批、模型身份与版本仅作为运行时 provenance 的只读 turn 在
`thread/start` 与 `thread/resume` 请求 `config` 中提供运行时 `bypass_hook_trust`。安装态同步
`SessionStart:resume` Hook 精确启动、完成各一次，
注入 `yiyuan-accord-hook-context/v1` 与 `signal.source=resume`，Agent 以零工具精确返回
`HOOK_CONTEXT_RESUME`，清理通过。一般枚举的 `trustStatus` 仍为 modified，事件还报告
`permission_mode=bypassPermissions`，因此这个宽泛绕过只能作为测试控制，不能充当生产信任机制或
产品价值证据。安装包 `compact`、会话态 `resume`、语义级指令使用、Hook 驱动的官方状态重感知与
内核调用、产品结果、拓扑执行、窄化信任生命周期以及 Node 可移植性仍未证明。GT-21 的精确证据
现仅对一个当前宿主的事件到结果路线、一个充分简单路线和一次先验收目标再释放源的零历史交接
有界通过；GT-20 的精确证据另仅对一次性非空 Windows Codex 与 Claude 配置域中的失败更新保留、
精确更新、用户与外来状态保护、原生移除及受限惰性宿主缓存有界通过。以 `85a917a` 为精确切点的
source-bound 全系统重验收已经有界完成，当前阶段是独立 exact-tree review；它们都不是 candidate
或 release 证据。生产信任、非受管或跨 OS/跨宿主行为、Claude 实际 Hook 激活、价值以及更新后
客户端的当前入口兼容性仍为未知。受保护的外来 `.tmp` 仍是 clean exact candidate blocker，本次
重验收既不检查也不删除它。修订后的
GT-07 在精确 `cb11759` 上仅对一次新鲜零历史目标接收与源释放顺序通过；没有执行真实的压缩或
对话分叉操作。中文宿主界面的裸词“分支”可能同时指 Git branch 与 task/chat fork；Accord 始终
限定为“Git 分支（ref）”或“对话分叉（复制历史）”，不按本地化标签或复用图标猜测拓扑。代码
拓扑、对话拓扑与本地/云端执行放置彼此独立；换对话不意味着换 branch、
worktree、repository fork 或执行环境。稀疏的宿主原生能力面与 Accord 责任分配面只能暴露候选
交集，是否真正冗余仍须通过当前准入、结果和生命周期证据。真实机制、持久连续性、跨宿主或
群体价值与发布仍受门控。

随后一个不启动模型回合的一次性 App Server 序列先观察到 ephemeral thread 不支持目标状态读取，
再用一个任务专属官方 goal 状态形成可恢复线程。`thread/resume` 恢复了官方状态，但安装态
`SessionStart:resume` 在首个 turn 前不会执行。以官方 resume 响应本身作为事件后，一次性直接客户端
查询当前结构化配置、Hook、Skill、权限和 goal 面，把 5 个决策相关字段归一化成当前回执并实际调用纯内核。
内核正确返回 `hold-unknown`，因为编排器不能独立证明自己的产品结果。这证明一条
“官方 resume 事件 → 状态 → 回执 → 内核”路径，不代表 App Server 客户端已经成为产品形态，
也不证明 Agent 语义使用或产品结果。

责任实现与状态协调是两个正交维度。派生索引除宿主能力 H 面、Accord 分配 A 面外，还按需
投影字段权威与新鲜度 S 面。物质边界优先读取宿主支持的官方结构化查询或状态接口，再读取
其它当前类型化的官方宿主状态、Accord 自有字段，并只为未暴露事实做有界观察。Accord 直接
消费官方事实，只规范化当前结果义务所需字段，不重建第二套宿主能力权威库。每个字段都绑定规范化决策目标和值、唯一写者、
有界读者、回退优先级和当前代次；冲突、未绑定值或缺失保持未知。状态共享本身不证明
Agent 已使用、已经执行、产生结果或带来价值。若官方载体以更低总负担证明关闭同一状态
责任，被替代的 Runtime、适配器或轮子就进入可逆减法评估，而不是永久保留两套路径。

候选证据现在按任务稀疏失效，而不是看标签或被任意仓库变更整体推翻。每个必需 Golden Task
声明它实际覆盖的可执行或指令文件；晋升时必须同时绑定源记录中的祖先 revision、当前任务与
评估摘要、精确宿主投影，并证明该任务行为对象的当前字节未变。仅证据或展示层提交不会迫使
无关任务重跑，但参考内核或 Skill 发生相关变化会使对应证据失效。

计划已在实现前研究一手资料、既有失败与适用的现成方案，划分各项自举子能力，
并在一次性隔离环境中验证最高风险假设，随后才准入最小参考内核。产品形态继续
由闭环所需属性与全生命周期成本决定；发布是最后阶段。

形成任何未来候选之前，计划现在还要求完成一次来源可追溯的全系统平衡自审，
以最小可逆方式整改有证据支持的最弱环节，并重新验收所有受影响维度及其相互作用。
产品价值、环境自适应、证据、权限、用户负担、隐私与供应链信任、可靠性、资源、
架构、生命周期、文档与治理属于不可相互补偿的耦合维度：平均分不能掩盖阻断项或
会改变发布决定的未知项。自审只是后续独立审查的输入，不能替代独立审查。每项比较
还必须先绑定版本化、声明范围内的基线、目标与反事实；公开 v3.0.1、未发布精确检查点、
当前审计快照和受控行为对照臂只支持各自问题，不能相互借用证据强度。
插件与 Skill 是当前投影，不被预设为足够或不足；若完整责任确需多种载体协作，
系统一致性由共同的结果、权限、证据与生命周期合同维持，而不是由单一 Runtime
或状态层强行统一。每个被保留的能力可以在当前闭环中承担可替换的深模块角色，
但宿主原生或外部能力仍是经适配器接入的依赖，不会因此变成 Accord 自有实现。
实现按每项责任分配为三种模式：Accord 内化、Agent 原生、Accord-Agent 组合；同一路线可以
混用三种模式，不能用来源标签、插件名称或整任务分类代替逐责任分配。观察或上下文注入可以
促成路线，但不能据此证明 Agent 已使用、已经执行、结果成立、独立证据充分或产品产生价值。
新共识立即约束方向，但只有通过命题矛盾、类别、边界与依赖检查并修复所有受影响投影后，
才晋升为新的实现基线。

请在 [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues) 中提供精确 tag 与 revision、宿主与版本、安装方式、目标、初始状态、实际结果、人工介入、物质影响或残留，以及仍未知的内容。

不得提交凭据或私密会话原文。

---

## 30 秒开始

### 安装前确认

使用当前支持插件的 Codex 或 Claude 表面，具备访问公开仓库的网络、修改
用户级插件配置的权限，并在安装后新建任务或会话。Accord 不绑定某个固定
宿主或模型版本；请记录实际使用的版本与路线。

### Codex

安装精确、不可变的 tag：

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.0.1
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

重启桌面端或新建 CLI 会话，打开 **Plugins** 或运行 `/plugins`，确认
`YIYUAN Accord for Codex` 与 `deliver-demand-driven-outcome` 已出现。

### Claude 客户端与 Claude Code

在 Claude Desktop Chat、Claude 网页聊天或 Cowork 中打开
**Customize > Plugins**，把
`https://github.com/yiheng8023/YIYUAN-Accord` 添加为个人 marketplace，
安装 **YIYUAN Accord for Claude**，新建聊天并确认
`deliver-demand-driven-outcome` 可见。

Claude Code 持久安装：

```powershell
claude plugin marketplace add yiheng8023/YIYUAN-Accord@v3.0.1
claude plugin install yiyuan-accord-claude@yiyuan-accord
```

仓库根目录是 marketplace，包子目录不是。仅用于单次开发会话时，从仓库
根目录运行 `claude --plugin-dir ./plugins/yiyuan-accord-claude`，并在
`/help` 中确认 `/yiyuan-accord-claude:deliver-demand-driven-outcome`。
checkout 变化后使用 `/reload-plugins`。

### 安装改变什么

公开 v3.0.1 包只会让一个渐进式披露的动态适配 Skill 可用，不新增 Runtime、
Hook、MCP server、App、状态存储、后台进程或自动项目修改。精确历史基线
`ae729465` 包含较早的无状态 `SessionStart` 上下文 Hook；当前开发候选修改了
该 Hook 的 matcher 与提醒文本。两个版本都不读取会话原文、不写状态、不启动
后台进程，但不能把当前 matcher 或文本字节追溯成历史 revision 的事实。这些只是
版本化包事实，不是产品身份或永久机制禁区；当前提醒要求 Agent 重感知被允许的
状态并逐责任分配实现模式，但提醒本身既不是实时回执，也不是 Agent 使用、执行、
结果、证据或价值。Hook 信任、宿主实际触发以及从激活到效果的链路仍需独立证据。

安装、启用和可见不等于激活。正常工作中，宿主可为相关的非简单任务隐式
调用 Skill；原生路线健康充分时它应保持安静。只有确定性暴露检查才需要
显式选择 Skill。

当前包把 Skill 与 Hook 保留在插件所有的路径内，不替换项目或用户的
`AGENTS.md`、`CLAUDE.md`、`config.toml` 或 settings 文件。这只是静态包事实，
本身还不是“即插即用、即卸即走”的行为证明。GT-21 现仅以冻结字节有界证明一条事件失效、
状态重感知、纯内核调用、类型化最小上下文、Agent 可观察使用与结果链，以及充分简单路线静默和
拓扑安全的新对话交接。GT-20 现另仅在非空的一次性 Windows Codex 与 Claude 配置域中有界证明：
建立来源信任后，用户每次只需给出一次生命周期意图；失败更新保留最后验证版本；精确更新成功；
既有配置、并发用户修改、共享与外来状态保持不变；移除后 Accord 注册、暴露、进程和数据等活动
状态为零。宿主所有、不可调用并按其受限自动回收约定处理的惰性缓存不叫物理零残留，Accord 也
不得绕开宿主生命周期删除它。这些结果不外推到生产、非受管或跨 OS 宿主、Claude 实际激活、
更新后客户端当前入口、跨宿主价值、candidate 或 release。

---

## 它改变什么

用户只需用自然语言说明期望交付的结果。Accord 要求 Agent 承担其能力范围内的工序，同时把后果性判断、新信任授予、成本承诺、公开发布和不可逆影响留给人类决定。

Accord 不要求 Agent 模拟人。人、模型以及双方掌握的信息都存在局限；本项目只改善自身能够影响的协作边界，只要能以更低负担和诚实证据实现人的目标，就允许采用不同于人的机器原生路径。

其可移植循环由五个稳定常量构成：

1. **目标锚定**：以用户当前目标和即时纠正为起点。
2. **最小路径**：选择真正能交付结果的最小充分执行路线。
3. **权限留存**：只在需要新人类判断或权限的真实边界停下并说明。
4. **溯源校准**：纠正或新证据推翻当前证明后，从最早受影响的依赖边界重做校准。
5. **诚实收尾**：核对实际效果，透明说明未知，并清理可控残留。

其余因素都由任务和宿主按需激活。如果宿主原生路径已经充分，Accord 就应该保持安静与克制。

---

## 适合什么情况

- **目标漂移**：任务虽产生了大量看似合理、忙碌的过程产物，但已实质偏离用户真正需要的结果。
- **长链中断**：长任务可能被外部中断、中途纠正，或需要换一个任务载体接续执行。
- **伪绿灯陷阱**：测试通过、报告生成、中间提交或平台托管绿灯被盲目误当成现实交付。
- **决策边界控制**：Agent 应完成其能力范围内的工序，但在真实人类决策、新权限、明显成本或不可逆影响前必须停下。
- **级联失效回放**：一次局部修补或新规则可能推翻旧证据，需要有界地重放下游结果。

Accord 不是要求用户额外学习的提示词模板，普通请求就足够了。

---

## 更新、回滚、移除与源码验证

请在执行安装的同一表面确认生命周期状态：使用
`codex plugin list --json`、`claude plugin list --json` 或
**Customize > Plugins**。不同表面的列表差异是应记录的宿主状态，不是另一
安装必然失败的证明。

不可变 ref 不会自动前进。Codex 更新或回滚时，先移除已安装包与
marketplace，再安装目标精确 tag：

```powershell
codex plugin remove yiyuan-accord-codex@yiyuan-accord
codex plugin marketplace remove yiyuan-accord
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref VERSION_TAG
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

Claude Code 使用宿主生命周期命令；Claude 客户端使用
**Customize > Plugins** 中的对应操作：

```powershell
claude plugin marketplace update yiyuan-accord
claude plugin update yiyuan-accord-claude@yiyuan-accord
claude plugin uninstall yiyuan-accord-claude@yiyuan-accord
```

宿主支持时优先使用原生热加载；否则采用原子化版本替换、健康检查，并在
失败时恢复上一精确版本。不得移动已有 tag，也不得用直接编辑全局宿主配置
代替受支持的生命周期命令。

“即插即用”不等于隐藏来源信任、权限、数据、成本或破坏性授权；它指这些不可
回避的边界明确后，用户无需逐个安装或卸载 Accord 内部组件。若某宿主无法在
不覆盖用户状态的前提下完成该事务，就应把它记录为适配缺口，不能包装成安装
成功。

源码验证应 clone 精确 tag，并使用具备所需标准库能力的 Python 解释器。当前
Release CI 覆盖 CPython 3.10–3.14；该矩阵只是当前兼容性证据，不是永久版本
白名单，也不属于 Accord 的产品身份。运行：

```powershell
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

这些检查验证仓库与包的确定性一致性，不会安装插件、证明隐式激活、建立
现场价值、授予发布权限或证明生产安全。

---

## 维护者与源码核验参考

- **当前 schema-v3 权威集合**：
  [`constitution.json`](product/constitution.json)、
  [`program.json`](product/program.json) 与
  [`acceptance.json`](product/acceptance.json)
- **已接受、可修订的重塑与动态索引指导**：
  [`reshaping-guidance.json`](product/reshaping-guidance.json)
- **派生术语与边界**：[`CONTEXT.md`](CONTEXT.md)
- **数据驱动的通用验证器**：
  [`yiyuan_accord/control.py`](yiyuan_accord/control.py)
- **v3 动态适配宿主投影**：Codex 与 Claude 包统一使用
  `deliver-demand-driven-outcome` Skill 名，并保留宿主专用 manifest
- **帮助与干扰代表任务**：
  [`evals/golden-tasks.json`](evals/golden-tasks.json)

上述源码把可移植协作约束、宿主专用规则和从失败中保留的防护边界分开。
其内部编号只服务于维护、自动检查和精确证据绑定；普通使用者只需面对结果、
重要状态、需要本人决定的边界和诚实的能力限制。

这三份权威文件只是当前可审查的启动拓扑，并非不容置疑的真理、永久数量，
更不是由今天宿主可见能力决定的覆盖上限。未来的合并、拆分、替换或退役
必须保留来源，并显式迁移 schema、验证器、映射与受影响证据。

---

## 动态适配产品边界

Accord 不受 Codex、Claude 或任何具体 Agent 能力面的限制。每个具体 Agent
及其宿主能力面都只是可替换适配器和带新鲜度边界的观测快照。可移植产品
覆盖的是 Agent 中立的“需求—能力—权限—路线—实际效果—证据”动态关系；
当现场事实与生命周期价值成立时，原生、官方、受维护、组合或受控新建的
机制都可以进入路线。

Accord 之前的系统现在是这个更大协作系统中的 Agent 执行与宿主适配子域。其
有价值的能力和失败教训按当前代表需求选择性召回，再通过官方能力发现、动态
路由、热更新和退役机制重新塑形，而不是恢复原来“遇到一个问题堆一层实现”
的整体架构。

Skill、插件、App、MCP、Hook、配置、状态、Runtime、云端载体或其他机制，
既不是必选项，也不是永久禁区。可见或安装不等于激活；原生路径充分时应当
没有不必要介入，存在未闭合的结果义务或不可靠关系时，则可以引入具备干扰、
更新、回滚和退役控制的局部机制。

Accord 前身的 Agent 执行子域原有过程损失控制使命也被保留：Agent 应使最新需求与纠偏、目标、
权限、路线、实现、证据、验收和最终声明持续对齐。健康对话不因流程而强行交接；
一旦出现实质偏离，就定位最早受影响边界，只回放其下游工作。

摘要、容量压力和交接只是目前观察到的高频风险，不是封闭清单；任何可能让目标、
状态、权限、证据、资源、拓扑、时序或因果关系丢失、失真、过期或错绑的条件都应
触发有界重建。不同宿主对项目、工作区、任务、线程、对话和会话的叫法会先映射到
彼此独立的规范关系。功能大同小异只会开启组合或替代评估，不能单凭名称或大类功能
判定可互换、已调用或应当退役。

### 资源治理

Accord 把资源使用视为动态路线变量：观测需求、容量与当前暴露，区分资源
身份、所有者、租约和状态，采用满足结果所需的最小并发与预算；压力变化时
重新平衡或降级；只释放可归因的任务专属资源，并核验释放后的状态与残留。
共享资源或所有权未知的资源必须保留。

宿主原生的限额、中断、清理与回收能力健康且充分时优先使用；宿主能够证实
闭合某项责任时，Accord 对该分配保持无动作，并只在替代路线的结果、清理、
可逆观察、独立退役后态和重检触发器齐备后退役冗余逻辑。宿主漂移或证据过期
必须重新计算；一项责任被覆盖不等于整个产品应退役。性能跟踪或
清理命令只是诊断或控制证据，不等于自动优化或释放证明；跟踪只按需开启，
不得静默收集或上传。

不可变的 v3.0.1 正式版把一个真实结果映射为计划、因地制宜的工序、验收和
精简目标投影；在有界 GT-07 连续性、GT-11 修复与 GT-12 资源治理切片上回放
精确动态适配 Skill；并要求八项仓库验收全部满足。其精确 tag revision
[`24cf9f3`](https://github.com/yiheng8023/YIYUAN-Accord/commit/24cf9f3750ecd700944988e81a519db54b67b8e8)
在发布前通过精确本地、独立审查与
[多操作系统 GitHub Actions 矩阵](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/33047474095)。

canonical verifier 有意不证明托管系统、人类权限、tag 或公开 Release 创建、
安装更新与清理完成态。这些门禁已作为不可变正式版前后的任务时证据完成；
机器可读的 program 与 acceptance 文件保留候选期发布合同，不把外部事实
倒写成仓库自证。不可变的 v2.0 与 v2.0.1-preview.1 仍是公开历史事实；
preview.2 未曾发布，不得打 tag。详见
[`product/reshaping-guidance.json`](product/reshaping-guidance.json) 与
[`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md)。

---

## 项目与许可

项目网站是 [github.com/yiheng8023/YIYUAN-Accord](https://github.com/yiheng8023/YIYUAN-Accord)，发布者是 [yiheng8023](https://github.com/yiheng8023)。

架构与信任边界见 [`docs/architecture.md`](docs/architecture.md)，维护与参与贡献见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

安全报告入口见 [`SECURITY.md`](SECURITY.md)，维护者续接说明见 [`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md)。

YIYUAN Accord 采用 Apache-2.0 许可证。YIYUAN NEXUS 名称与图形商标保持独立，详见 [`NOTICE`](NOTICE) 与 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

---

## 自愿赞助与支持

赞助完全自愿，不购买支持 SLA、处理优先级、发布权限、安全保证、治理例外、功能承诺或对技术决策的影响力。

如果 Accord 对你有所帮助，可以通过仓库所有者[公开的 PayPal 页面](https://www.paypal.com/ncp/payment/LNTF8KXGJXMZY)支持项目维护。

| 微信支付（人民币） | 支付宝（人民币） |
| --- | --- |
| ![微信支付收款码](docs/assets/sponsoring/wechat-pay.png) | ![支付宝收款码](docs/assets/sponsoring/alipay.png) |

付款前请核对收款方。完整条款见 [`SPONSORING.zh-CN.md`](SPONSORING.zh-CN.md)，社区支持按 [`SUPPORT.md`](SUPPORT.md) 所述尽力提供。

---

## 免责声明与合规说明

YIYUAN Accord 是独立的社区开源项目，不是 OpenAI、Anthropic、Codex、Claude、Claude Code 或 GitHub 的产品，也不代表其赞助或背书。

第三方名称与商标归各自权利人所有。YIYUAN NEXUS 商标仅用于标识本发行物，并由 [`NOTICE`](NOTICE) 单独约束。

用户仍需自行审查 Agent 输出，并遵守适用法律、合同、宿主条款、许可证和组织政策。

本软件按 Apache-2.0 许可证以“按原样”方式提供，不附带任何保证或条件，详见 [`LICENSE`](LICENSE)。项目正式发布不证明生产安全或对特定用途的适用性。
