# YIYUAN Accord 重构与长期演化报告

## ——以真实结果为锚，以减法、克制、兜底、补位为核心原则

**日期：2026-08-20**

---

# 一、报告定位

本报告不是一次普通代码审查，也不是针对当前 O2、O4 或某几个 validator 的局部修复建议。

当前 YIYUAN Accord 已经经历了多轮设计、实现、实验、失败、反证和修正。这个过程没有白费，它帮助项目逐渐从最初偏“工具与 Skills 管理”的思路，收敛到了一个更本质的问题：

> **如何让用户尽量停留在“表达目标和作出关键判断”这一层，而把工具发现、能力选择、执行、恢复、验证、转场和清理等认知与操作负担转移给 Agent。**

这个方向应继续坚持。

当前真正需要解决的问题是：

> **为了构建一个降低人机协作复杂性的系统，项目自身重新制造出了大量流程、规则、状态、验证和证明复杂性。**

因此，下一阶段不应该首先追问：

> 如何继续完善当前体系？

而应该重新追问：

> **如果今天基于已有全部认知重新设计 YIYUAN Accord，最少到底需要保留什么？**

---

# 二、最高校准：真实需求、真实环境、真实结果

“减法、克制、兜底、补位”非常适合作为项目核心原则。

但它们之上仍然需要一个共同锚点：

# Reality First

即：

> **以真实需求、真实环境和真实结果作为最终校准。**

这不是第五条并列原则，而是四条原则判断正确与否的上位依据。

因为四条原则都可能被机械化：

- 减法可能退化为“为了简单而简单”；
- 克制可能退化为“不愿承担责任”；
- 兜底可能膨胀成第二套完整 runtime；
- 补位可能退化为“看到任何功能缺口都自行实现”。

因此真正目标不是：

> 越少越好。

而是：

> **不必要的东西越少越好，必要的东西必须存在。**

所有架构、流程、验证和能力选择最终都应回到：

```text
真实目标
+
真实宿主状态
+
真实任务效果
+
真实用户负担
+
真实风险
↓
工程决策
```

---

# 三、四项核心原则

# 1. 减法

> **遇到问题时优先删除错误和多余结构，而不是增加新机制。**

过去很容易出现这样的修复模式：

```text
发现问题
→ 增加规则
→ 增加状态
→ 增加 validator
→ 增加 generation
→ 增加 evidence
```

下一阶段应强制反转顺序：

```text
发现问题
↓
错误假设？
↓
过时约束？
↓
重复机制？
↓
宿主已经原生解决？
↓
已有上游能力可以复用？
↓
抽象层级是不是错了？
↓
删除或降级是否足够？
↓
仍存在真实残余缺口？
↓
才允许增加机制
```

应正式建立：

# Subtraction Before Addition

---

# 2. 克制

> **能做，不代表应该做。**

YIYUAN Accord 不应该因为技术上可以：

- 管理模型；
- 管理 provider；
- 管理 Skills；
- 管理 MCP；
- 管理插件；
- 管理任务；
- 管理 Git；
- 管理 context；
- 管理 worktree；
- 管理权限；
- 管理 Agent；

就把它们全部变成 YIYUAN Accord 产品边界。

真正判断标准应是：

> **如果 YIYUAN Accord 不承担这件事，是否真的存在没人负责、并且会影响用户结果的协作缺口？**

YIYUAN Accord 应允许正确答案是：

> 什么也不做。

因此：

# No-op 是一级能力。

---

# 3. 兜底

> **YIYUAN Accord 不承诺发现所有失败；在可观察、可控制的边界内，它必须限制关键失败的扩大，并在边界外保持 unknown、缩小声明或诚实停止。**

这是对“兜底”非常重要的校准。

兜底不能理解成：

> 原生失败以后 YIYUAN Accord 必须拥有完整替代实现。

否则马上又会产生：

```text
native route
→ YIYUAN Accord fallback
→ fallback validator
→ fallback recovery
→ fallback state
→ fallback fallback
```

真正的兜底应该包括：

```text
成功恢复
或
安全回滚
或
安全降级
或
请求必要的人类决策
或
明确缩小声明
或
诚实停止
```

因此：

# Honest Stop Is a Valid Safety Outcome

不能完成，但没有失控、没有误导、没有留下危险状态，本身就是一种合格兜底。

---

# 4. 补位

> **只补真正存在的残余责任缺口，而不是看到功能缺口就自己实现。**

这一点尤其需要校准。

假设 Codex 缺少功能 X，并不自动意味着：

> YIYUAN Accord 应该实现 X。

真正应该问的是：

> **X 是否应该由 YIYUAN Accord 负责？**

YIYUAN Accord 很多时候真正应该补的是：

- 谁判断应该使用哪个现有能力；
- 谁负责多个能力之间的协调；
- 谁负责错误恢复；
- 谁负责权限边界；
- 谁负责状态对账；
- 谁负责转场；
- 谁负责结束以后清理。

也就是说，YIYUAN Accord 更应该关注：

# Responsibility Gap

而不是：

# Feature Gap

这可以显著避免 YIYUAN Accord 最终变成一个巨大的工具平台。

---

# 四、第一项重大校准：必须系统吸收上游官方能力和推荐实践

下一代 YIYUAN Accord 不应该继续闭门推导宿主应该如何工作。

在为一个重要宿主补充机制以前，应首先系统研究：

- 官方产品手册；
- 官方 Developer Documentation；
- 官方最佳实践；
- 官方推荐使用方式；
- 官方安全模型；
- 官方 Use Cases；
- 官方 Skills / plugins / MCP / API 能力；
- 官方配置模型；
- 官方 Changelog；
- 官方团队自身如何使用产品；
- 官方正在推荐或弃用的工作方式。

以 Codex 为例，OpenAI 当前公开的内部使用实践明确建议：对于较大修改可以先让 Codex形成实现方案；持续改善 Agent 的开发环境；使用轻量 task queue 保存工作；通过 `AGENTS.md` 提供持久仓库上下文。citeturn278598search0

OpenAI 当前 Codex Use Cases 还明确展示了诸如“保存重复工作为 Skill”“给 Codex 一个持久目标”“为 Codex 提供可组合 CLI”“运行并验证重复操作”等模式。citeturn315441search0turn315441search1

这些都意味着：

> **很多 YIYUAN Accord 想解决的问题，应该先问宿主或生态是否已经存在成熟机制。**

---

# 五、建立正式的 Upstream Guidance Intake

建议任何 Host Adapter 或新能力开发前，都先执行：

```text
Official docs
+
Official product manual
+
Official recommended practices
+
Official native capabilities
+
Maintained external ecosystem
↓
Current host capability model
↓
Real task probe
↓
Residual gap
↓
Minimum residual supplementation
```

形成正式原则：

# Before Authoring, Inspect Upstream

任何新 YIYUAN Accord 机制必须回答：

1. 当前宿主是否已经原生解决？
2. 官方推荐如何解决？
3. 官方现有实现是否充分？
4. 是否存在维护良好的成熟外部实现？
5. 实际任务中缺口是否仍然存在？
6. 这个缺口到底属于功能缺口、协调缺口还是责任缺口？
7. YIYUAN Accord 最少补多少即可？

没有明确 residual gap：

> 不实现。

---

# 六、但官方不是最高权威

同时必须防止另一个极端：

> 从自研过度变成官方文档崇拜。

官方文档应被视为：

# High-Weight Evidence

而不是：

# Portable-Core Authority

因为：

```text
官方说支持
≠ 当前版本一定如此
≠ 当前账号一定具备
≠ 当前 OS 行为相同
≠ 当前权限配置相同
≠ 当前 task context 一定能成功
```

因此应采用：

# Read Upstream, Trust Conditionally, Verify Consequentially

流程：

```text
官方声明 / 官方推荐
↓
Expected capability
↓
当前环境轻量验证
↓
Effective capability
↓
执行
```

---

# 七、OpenAI 当前模型指导本身就是重要经验来源

OpenAI 当前 GPT-5.6 官方模型指导明确建议：

- 使用更精简的 prompt；
- 每条 instruction 尽量只表达一次；
- 只暴露当前任务真正相关的工具；
- 工具描述应简洁而精确；
- 从有效配置开始逐组删除 instruction、example 或 tool，再通过代表性 eval 重新测试；
- 长会话会放大重复 prompt 和工具内容带来的成本与干扰。citeturn329667search0turn315441search2

OpenAI 披露的一组内部 coding-agent eval 中，更瘦的 system prompt 在那组测试里同时提高了评分并明显降低 token 与成本；官方也明确要求把这些结果只当方向性参考，并在自己的代表性工作负载上重新验证。citeturn329667search0

这与当前 YIYUAN Accord 的问题高度一致：

> **更强的 Agent 并不天然需要更多规则；很多时候恰恰需要更少、更准、更相关的规则。**

因此：

# Prompt / Instruction Complexity 也必须进入 Complexity Budget。

---

# 八、当前项目最明显的结构性反差

当前 Codex 实际产品投影已经相当轻。

Codex Skill 本身约 3.5 KB，并明确要求轻量应用；参考 Codex adapter 也直接定义为 thin、stateless projection。

但其外围已经形成：

- `yiyuan_accord/control.py` 约 346 KB；
- `test_product_control.py` 约 406 KB；
- O2 / O4 多个数万字节的专属 validator；
- generation-specific registration；
- evidence；
-环境 manifest；
- immutable binding；
-停止记录。



因此已经形成：

```text
很薄的实际用户行为
          ↓
巨大的研发与证明体系
```

这不是代码行数本身的问题。

而是系统复杂性开始主要服务：

> 证明自身。

而不是：

> 用户结果。

---

# 九、研究体系与产品体系必须分离

严格的：

- preregistration；
- exact version；
- validator identity；
- SHA；
- immutable revision；
- cohort；
- evidence lineage；

在正式实验中完全有价值。

但它们不应该默认成为每次产品迭代的工作方式。

建议建立两条轨道：

## Product Track

回答：

> YIYUAN Accord 有没有真正改善协作？

重点测量：

- task success；
-结果质量；
-human burden；
-time to result；
-recovery；
-continuity；
-cleanup；
-YIYUAN Accord interference。

---

## Research Track

回答：

> 我们有多强的证据能够对外作出某种声明？

包括：

- controlled experiment；
- preregistration；
- exact environment；
- reproducibility；
- field evidence；
- cross-host；
- cross-platform。

原则：

# Evidence Strength Should Match Claim Strength

普通产品改进不应该要求科研级证明。

但如果准备声明：

> “跨 Agent 普遍有效”

就必须提供与这一强声明相匹配的证据。

---

# 十、O1–O5 应保留，但改变职责

O1–O5 可以继续存在。

它们很适合表示：

> Evidence / Research Maturity。

但不应继续成为唯一 Product Progress。

建议未来分开：

## Product Maturity

```text
experimental
usable
reference-ready
stable
```

## Evidence Maturity

```text
anecdotal
controlled
reproduced
field-observed
cross-host
cross-platform
```

这样完全可以：

```text
Product: usable
Evidence: controlled
```

而不需要为了从 1/5 变成 5/5 不断制造研究机制。

---

# 十一、当前 Exact Identity 抽象需要降级

最近 O4 第二代提供了非常有价值的反证。

实验绑定 Codex 0.147.0，四个 repository counterexample 已经通过，但真正创建 App Server 前实时 Codex 更新到 0.148.0。

Exact drift gate 因此停止整套实验，没有创建任务线程、没有模型 turn、没有 compaction 或 transition，O4 不获得信用。

对于严格实验：

> 这是正确的。

对于产品运行：

> 这不应成为默认逻辑。

因为现代 Agent Host 是持续变化系统。

因此产品适配应从：

# Identity Exactness

转向：

# Capability Compatibility

---

# 十二、版本是 Evidence，能力才决定路线

普通运行逻辑应当是：

```text
Host changed
↓
Compatibility probe
↓
Required semantics still satisfied?
       /               \
     yes                no
      ↓                  ↓
continue           adapt/degrade/stop
```

Version、SHA、model identity 等继续记录。

但默认角色应该是：

> attribution metadata。

而不是：

> permanent execution authority。

Exact pin 主要保留给：

- release artifact；
- security reproduction；
-科研实验；
-已知版本缺陷；
-二进制完整性本身就是研究对象的场景。

---

# 十三、Declared Capability 不等于 Effective Capability

第二次 O2 尝试也暴露了重要事实。

Codex `:workspace` profile 的压力 probe 曾观察到：

- root 内写全部允许；
- root 外写全部拒绝；
-无异常；
-无残留。

但实际 nontrivial goal 执行时，task-root write 又被拒绝。

这意味着能力不是简单：

```text
workspace_write = true
```

更接近：

```text
host
+ version
+ cwd
+ repo identity
+ project boundary
+ task root
+ policy
+ lifecycle state
+ invocation route
→ effective capability
```

因此必须增加：

# Effective Capability Principle

> 对具有实质副作用的能力，在真正 task context 中验证关键行为，而不是仅依据配置名称或单一 synthetic probe。

---

# 十四、Unknown 必须成为一等状态

YIYUAN Accord 不可能完整观察：

-系统指令；
-managed policy；
-真实 context capacity；
-compaction threshold；
-provider 内部 routing；
-所有账号配置；
-隐藏权限；
-所有宿主内部状态。

因此状态不能只是：

```text
true / false
```

至少应允许：

```text
observed true
observed false
reported
inferred
unknown
```

原则：

# Unknown Remains Unknown

没看到：

> 不能推断不存在。

对于重要 unknown：

```text
unknown
→ stronger verification
→ conservative route
→ degrade/escalate/stop when necessary
```

---

# 十五、不要制造复杂的上下文预测器

Context continuity 是真实问题。

但如果宿主不给可靠 token / capacity / compact threshold，就不应该为了预测上下文耗尽再造复杂系统。

更稳的办法是：

# Continuity by Construction

维护非常小的 durable state：

```yaml
goal:
current_state:
settled_decisions:
constraints:
important_evidence:
open_questions:
resources_changed:
next_action:
```

只在重要状态变化时更新。

于是：

- compaction；
- fork；
- new task；
-更换 Agent；
-重启；

都变成：

> 恢复同一个目标状态。

这样 context threshold 的不可观察性从：

> 系统致命问题

降级为：

> 性能优化问题。

---

# 十六、核心原则不应该变成超级 SOP

当前 AGENTS 与 constitution 中存在：

> exactly one causal increment / at most one work item

之类规则。

它们适合作为某类受控实验条件。

但现实工作天然可能是 DAG。

建议改成：

# Bounded Causal DAG

串行的原因应该是：

- 真实数据依赖；
-资源冲突；
-授权依赖；
-effect conflict；
-必须先验证前一步。

并行的条件是：

-因果独立；
-资源独立；
-授权独立；
-可安全 reconciliation；
-并行收益显著。

同时：

# Parallelism Must Pay Rent

能够并行也不意味着必须并行。

还要计算：

- coordination cost；
- merge cost；
- token cost；
-重复探索；
-冲突风险；
-reconciliation complexity。

OpenAI 当前 GPT-5.6 文档也只建议在复杂任务能够干净地拆成独立 workstream 时，多 Agent 并行才可能降低 wall-clock time 和改善结果。citeturn329667search0

---

# 十七、引入 Progressive Assurance

这是下一版非常重要的校准。

当前另一个极端风险是：

> 为了反对科研级过度验证，把所有验证都砍掉。

不应该。

正确方法应该是：

# Verification Strength ∝ Risk and Claim

例如：

### 低风险、可逆

```text
轻量结果验证
```

### 中风险

```text
effect verification
+
basic rollback check
```

### 高影响写操作

```text
explicit boundary
+
strong effect validation
+
recovery path
```

### 权限、安全、发布、不可逆

```text
human authority
+
strong evidence
+
fail closed
```

因此：

> 不是少验证。

而是：

> **只做与风险和声明强度匹配的验证。**

---

# 十八、Human Burden 不是唯一目标

YIYUAN Accord 的重要价值确实是减少用户认知和操作负担。

但如果优化目标写成：

```text
human round trips ↓
```

最简单的方法就是：

> Agent 什么都自己决定。

这会提高风险。

真正目标应该是：

# Minimum Necessary Human Burden Under Acceptable Quality and Risk

综合目标至少包括：

```text
结果质量
+
安全
+
必要人类负担
+
时间
+
成本
+
可恢复性
```

用户介入：

> 不是越少越好。

而是：

> **只保留真正属于人的那一部分。**

---

# 十九、Human Authority ≠ Human Approval Everywhere

OpenAI 目前在内部部署 Codex 时使用的原则也很清楚：让 Agent 在明确技术边界内保持高生产力，低风险日常动作尽量无摩擦，而高风险动作进入审核；sandbox 定义技术边界，approval policy 决定何时需要审批。citeturn278598search1

GPT-5.6 官方模型指导也建议使用相当紧凑的 autonomy policy：安全且范围内的本地修改和非破坏性验证可以继续，而外部写入、破坏性行为、购买或重大 scope expansion 应停下来确认；官方还提醒重复写“ask first”等审批要求可能造成不必要的中断。citeturn329667search0

因此 YIYUAN Accord authority 不应无限扩大 operation table。

更长期的抽象应该接近：

```text
risk
× reversibility
× existing authority
× blast radius
× trust/data/cost change
→ autonomy level
```

---

# 二十、复杂度不能只用代码量衡量

下一阶段减法不能只看 LOC。

真正需要控制的是：

# Total Coordination Complexity

包括：

-默认 prompt；
-默认 instructions；
-默认加载 Skill；
-工具暴露数量；
-概念数量；
-state 数量；
-state transition；
-approval point；
-thread / branch / worktree；
-evidence ceremony；
-必须知道的命令；
-必须同步的配置；
-用户需要学习的内容；
-Agent 每次必须读取的上下文。

一个只有几百行的系统，也可能因为几十条规则和二十个状态非常复杂。

---

# 二十一、建立 Complexity Budget

任何新增：

-规则；
-state；
-validator；
-adapter；
-Hook；
-Skill；
-plugin；
-workflow；
-持久资源；

必须回答：

1. 它解决什么真实问题？
2. 是否已经发生或存在充分证据？
3. 官方/宿主有没有已有解决方案？
4. 外部生态是否已有成熟实现？
5. 更轻方案为什么不够？
6. 它增加了多少协调复杂度？
7. 删除它具体会造成什么损失？
8. 它未来什么时候应该退役？

原则：

# Complexity Must Pay Rent

---

# 二十二、补位机制出生时就必须定义退休条件

过去通常是：

> 做出来以后，将来再考虑删。

下一代应反过来：

> **任何 YIYUAN Accord-specific residual mechanism，在诞生时就必须说明它何时失去存在价值。**

建议每项补位都携带：

```yaml
reason_for_existence:
entry_condition:
residual_gap:
exit_condition:
retirement_trigger:
```

例如：

```text
Codex 原生支持 X
+
compatibility eval 通过
↓
YIYUAN Accord X mechanism retire
```

这能够把：

> 可退役

从善意愿望变成工程属性。

---

# 二十三、Self-Complexity Guardrail

此次项目经历本身已经证明：

> **任何用于降低复杂性的系统，都需要控制自身复杂性。**

应该新增：

# Self-Complexity Guardrail

当出现：

```text
mechanism A
↓
mechanism B 用来管理 A
↓
mechanism C 用来证明 B
↓
mechanism D 用来恢复 C
```

默认触发架构审查。

特别是：

```text
validator-v1
→ validator-v2
→ ...
```

这种第二代、第三代同类修复出现时：

> 默认先重新审视抽象，而不是继续创建下一代。

---

# 二十四、强 Agent 特别容易产生 Repair-by-Addition

Codex 的优势恰恰也是风险：

-执行能力非常强；
-能长期遵循复杂规则；
-能够继续补全状态机；
-能够把抽象要求工程化到底。

如果目标写成：

> 把验证体系做严谨。

它会非常认真地继续强化验证体系。

因此 YIYUAN Accord 应加入一个适用于强 Agent 的元规则：

# Outcome Over Process

只要不突破安全和权威边界：

> 流程服务结果，而不是结果服务流程。

---

# 二十五、还必须防止 Proof Proxy

当：

```text
O1–O5
G1–G4
test count
evidence credit
```

比“用户到底有没有得到更好结果”更容易计算时，Agent 很容易优化这些代理指标。

因此：

> Product Metrics 与 Research Metrics 必须隔离。

不能让：

> 证明活动

成为：

> 产品活动的替代品。

---

# 二十六、Codex Skill 应采用 Progressive Disclosure

当前 Skill 本体已经比较小，这是正确方向。

但它仍要求符合条件的任务读取完整约 12.5 KB profile。

更合理的是：

```text
core
├── capability      按需
├── authority       按需
├── recovery        按需
├── continuity      按需
└── cleanup         按需
```

Core 应尽量短：

1. 从用户目标工作；
2. 优先使用充分现有能力；
3. 无因果必要性不增加机制；
4. 保护关键人类权威；
5. 出现实质偏差时恢复；
6. 验证结果并清理自身影响。

---

# 二十七、No-op / Non-Interference 应升为正式产品属性

建议明确：

# Non-Interference

> 当宿主原生能力已经能够安全、可靠、低负担地完成任务时，YIYUAN Accord 不增加无必要的流程、工具、审批、状态、拓扑或持久资源。

Golden Tasks 中必须专门验证：

> YIYUAN Accord 能不能忍住不介入。

---

# 二十八、`control.py` 应停止成为第二份 Constitution

当前 `control.py` 已经复制大量 purpose、success definition、progress rule 等产品语义。

结果变成：

```text
Product contract
↓
Python 再写一次
↓
hash
↓
tests
```

建议建立真正唯一语义真源：

```text
core/contract.*
```

Code 负责验证：

- schema；
-引用完整性；
-authority；
-state transition；
-evidence integrity；
-forbidden effect；
-cleanup；
-compatibility。

不要再次复制整段产品哲学。

---

# 二十九、Golden Tasks 应替代自证循环成为第一验证面

下一阶段优先运行真实或高度真实的任务：

1. 极简单任务；
2. 中型 bug；
3. 大仓库理解；
4. 当前能力不足；
5. 需要发现 Skill / CLI / plugin；
6. 出现新权限边界；
7. 执行失败并恢复；
8. 用户中途纠正；
9. 长任务发生 carrier transition；
10. 天然适合并行；
11. 不适合并行；
12. 宿主版本变化但行为兼容；
13. 官方声明支持但实际失效；
14. context 信号 unknown；
15. 必须诚实停止的任务。

---

# 三十、指标应该同时测“帮助”和“干扰”

## Positive Metrics

```text
task success
result quality
recovery success
correction retention
continuity
cleanup
time to result
```

## Human Burden

```text
human actions
human round trips
human tool learning
human recovery work
human context reconstruction
```

## YIYUAN Accord Interference

```text
extra instructions
extra questions
extra tools
extra approvals
extra tasks
extra branches/worktrees
extra context
extra validation
extra latency
```

真正目标是：

> **在质量和风险可接受的情况下，最小化总协作成本。**

---

# 三十一、建议的新 Portable Kernel

经过上述减法，真正长期稳定的 Kernel 不应包含很多实现机制。

建议核心只保留五项：

## K1 — Goal First

用户从目标和意图进入。

---

## K2 — Minimum Sufficient Route

Agent 使用当前现实条件下的最小充分路线。

---

## K3 — Human Authority

关键目标、专业判断、新信任、新数据、新成本、不可逆影响及最终责任保留给人。

---

## K4 — Continuous Reconciliation

持续比较：

```text
目标
修正
权威
预期
现实效果
证据
资源状态
```

发生实质偏差时恢复。

---

## K5 — Close the Loop

Agent 负责：

```text
执行
→ 恢复
→ 验证
→ 对账
→ 释放
→ 清理
```

---

# 三十二、Kernel 之上的四项哲学

可以理解为：

```text
          真实世界
              │
    ┌─────────┴─────────┐
    │                   │
   减法                 克制
    │                   │
    └──────┐       ┌────┘
           兜底 · 补位
               │
          YIYUAN Accord Kernel
```

四项原则共同回答：

### 减法

什么可以不做？

### 克制

什么不属于我做？

### 兜底

如果外部东西失败，如何不失控？

### 补位

还有哪一点真的没人解决？

---

# 三十三、建议 Host Adapter Standard

未来每个宿主至少遵守：

### H1 — Official Guidance First

先查当前官方产品手册和推荐实践。

### H2 — Native First

健康原生能力优先。

### H3 — Capability Over Version

兼容能力优先于纯版本相等。

### H4 — Effective Over Declared Capability

真实任务能力优先于配置名称。

### H5 — Unknown Is First-Class

未知不能假定不存在。

### H6 — Drift Is Normal

宿主演化是正常环境条件。

### H7 — Verify Consequential Effects

原生优先不等于盲信。

### H8 — No User Compensation

不得用用户学习和手工操作补偿宿主不足。

### H9 — Host Details Stay Outside Portable Core

`:workspace`、SessionStart 等属于 adapter。

### H10 — Native Improvement Retires YIYUAN Accord Logic

宿主解决以后 YIYUAN Accord 主动退出。

---

# 三十四、建议新的目录边界

```text
YIYUAN-Accord/
│
├── core/
│   ├── contract
│   ├── principles
│   └── schemas
│
├── adapters/
│   ├── codex/
│   ├── claude/
│   └── ...
│
├── evals/
│   ├── golden-tasks/
│   ├── compatibility/
│   └── regression/
│
├── research/
│   ├── protocols/
│   ├── experiments/
│   ├── evidence/
│   └── history/
│
└── docs/
```

关系：

```text
core
↓
adapters

core
↓
evals

research
↔ informs / falsifies claims
```

但：

```text
research ≠ runtime authority
research ≠ automatic work generator
```

---

# 三十五、当前历史不应该删除

v0.x、v1.0、v1.1、v1.2：

-失败尝试；
-counterevidence；
-O2 permission failure；
-O4 version drift；
-旧 validators；
-旧 registrations；

都值得保留。

但保留方式应该是：

> historical / research evidence。

而不是：

> 所有未来运行必须继续携带全部历史复杂性。

Git 历史本身就是很好的历史载体。

不要为了“历史存在”而让所有历史逻辑永远留在当前产品主路径。

---

# 三十六、当前应暂停的工作

在完成本轮重新校准以前，建议暂停：

- O4 第三代 controlled attempt；
-新的 generation-specific validator；
-新的 exact-host freeze；
-继续扩大 `control.py`；
-为了 O1–O5 credit 继续增加机制；
-继续把实验全过程写进 README 主入口。

当前最高价值工作不是：

> 多获得一个 outcome credit。

而是：

> **重新确认项目应该剩下什么。**

---

# 三十七、下一轮 Codex 首先应该做什么

不要马上重构代码。

先执行：

# Upstream & Repository Reconciliation

系统研究当前 OpenAI 官方：

- Codex 产品手册；
- Codex Developer Docs；
- Codex Use Cases；
- OpenAI 内部 Codex 使用经验；
- GPT-5.6 模型指导；
- Skills；
- plugins；
- MCP；
- AGENTS；
- sandbox / approval；
- task / goal / parallelism；
- context / compaction；
- Changelog；
-安全与 telemetry。

OpenAI 当前官方资料本身已经明确覆盖了 Codex 实践指南、开发文档、Use Cases、Academy 资源以及持续更新内容，因此这些资料应该成为 Codex reference adapter 的高权重输入。citeturn278598search3turn278598search8turn315441search4

然后建立矩阵：

| 当前 YIYUAN Accord 机制 | 宿主原生能力 | 官方推荐 | 实测行为 | Residual Gap | 决策 |
|---|---|---|---|---|---|
| A | 已解决 | 推荐原生 | 有效 | 无 | 删除 |
| B | 部分解决 | 推荐 X | 部分有效 | Y | 最小补位 |
| C | 官方有能力 | 当前环境失效 | 不可靠 | Z | 兜底 |
| D | 无对应能力 | 无 | 真实缺口 | D | 考虑实现 |

---

# 三十八、特别约束：不要把“简化重构”重新做成一个大系统

这是下一轮最重要的一条执行警告。

Codex 很可能读完本报告以后开始设计：

```text
new kernel engine
new compatibility engine
new assurance engine
new retirement manager
new DAG scheduler
new upstream registry
```

如果发生这种情况：

> 重构已经失败。

本轮应当明确以：

```text
DELETE
MERGE
SIMPLIFY
DOWNGRADE
ARCHIVE
```

为主。

新增机制必须极少。

成功标准之一应该是：

> **概念明显减少。**

同时：

-默认 instruction 减少；
-默认状态减少；
-默认文件减少；
-默认流程减少；
-默认验证减少；
-默认宿主假设减少。

如果只是把旧复杂性换了新名字：

> 不算重构成功。

---

# 三十九、最终项目定义建议

> **YIYUAN Accord 是一套轻量、Agent-neutral、以用户目标为入口的人机协作契约。它以真实需求、真实环境和真实结果为校准，遵循减法、克制、兜底和补位原则：优先复用宿主及现有生态已经充分的能力，不重复制造已有机制；不因为能够控制就扩张产品边界；只针对真实存在且应该由 YIYUAN Accord 承担的残余责任缺口进行最小补位；并在宿主失败、能力不足、环境不可观测或执行发生偏差时提供必要恢复、降级和诚实停止能力。人始终保留对目标、重要专业判断、信任、数据、成本、不可逆影响和最终责任的权威。具体模型、工具、Skill、插件、MCP、Agent、Git 拓扑、任务拓扑、上下文机制和宿主实现都是可替换、可演化、可退役的实现层，而不是产品本体。**

同时增加正式负定义：

> **YIYUAN Accord 的价值不以自身介入次数、控制范围、规则数量、代码规模、验证数量或存在感衡量。原生能力已经充分时，正确行为就是不增加 YIYUAN Accord 机制。**

---

# 四十、最终判断

当前项目真正进入了一个重要阶段。

过去的复杂设计帮助我们发现了很多真实问题：

-规则会不断累积；
-验证会变成代理目标；
-精确身份不等于兼容性；
-声明能力不等于有效能力；
-宿主持续漂移；
-很多状态不可观察；
-强 Agent 会局部优化；
-修复容易退化为增加机制；
-研究方法可以反过来绑架产品。

这些都不是失败。

真正的失败反而是：

> 已经发现这些问题以后，还继续沿原路径机械扩张。

下一阶段应证明的不是：

> YIYUAN Accord 能控制多少东西。

而是：

> **YIYUAN Accord 是否有能力只承担真正应该承担的那一小部分。**

理想形态应该越来越接近：

```text
用户表达目标
        ↓
Agent 使用自身和现有生态能力
        ↓
YIYUAN Accord：
必要时减法
必要时约束
缺口处补位
失败时兜底
        ↓
完成结果
        ↓
验证、清理、退出
```

最终：

> **YIYUAN Accord 应在需要的时候出现，在不需要的时候消失。**

而从长期演化角度看，还有一句应当成为项目持续自检的问题：

> **如果宿主、模型和生态不断变强，YIYUAN Accord 有没有能力跟着变得越来越小？**

如果答案是肯定的，这个项目才真正具备长期生命力。
