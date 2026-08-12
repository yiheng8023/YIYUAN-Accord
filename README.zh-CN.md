# Agent Autonomy Harness

[English](README.md) | 简体中文

最短路径：[验证当前 checkout](#从这里开始) · [理解闭环](#harness-做什么) · [选择深入路径](#渐进式路径)

Agent Autonomy Harness 是一个正在构建的 Agent 中立产品：它的目标是在真实任务中保持目标、能力路线、
授权边界、生命周期、连续性、证据和清理的一致性，而不是让用户亲自编排每个 Agent、
Skill、MCP、Plugin、Hook、线程、工作树和管理器。

它不是“大而全的 Skills 列表”。外围能力是可替换输入；产品契约要求 Harness 判断何时需要、
授予什么边界、怎样观察效果，以及何时释放路线。

当前实现验证这份契约及其因果工序；任务执行、行为评价和跨宿主适配仍是 v0.2 的
planned 结果，不是当前运行时能力声明。

## 从这里开始

前置条件：Git 与 Python 3.10 或更高版本。当前 checkout 只使用 Python 标准库；本地
验证不需要安装包、连接账号或调用外部服务。

```powershell
git clone https://github.com/yiheng8023/agent-autonomy-harness.git
cd agent-autonomy-harness
python -B -m harness verify --root . --json
```

当前 `main` 是 paused 的 v0.2 工序，会报告 `0/5` 项结果、`4/4` 项护栏、
no active increment，completion 为 `in-progress`。当前 increment graph 为空；已关闭的
零 outcome 修复只保留在 Git 历史中，不再累积成当前工作队列。仅护栏的权威重置已在
`a5a0834` 推送，但计为零产品进展。随后基于六条真实 Harness 任务完成了能力链与
当前资产审计，建立路线增量评价和干净树基线，但没有验证 O4 或任何其他结果。
accepted 的 v0.1 仓库控制里程碑固定在
`be498f9`；它是历史，不证明终极产品命题已经完成。paused 只限制结果增量，不限制
回溯反例分析、有限组合策展、机制验证或权威缺陷修复。历史失败可以触发重规划，但
不会因此成为验收权威。下一结果增量只围绕已绑定的自然任务开启；不会要求用户为了
维持仓库忙碌而虚构任务。

完整确定性产品测试：

```powershell
python -B -m unittest discover -s tests/product -v
```

## Harness 做什么

对一个已绑定任务，Harness 明确保持以下闭环：

1. 绑定真实目标、输入、授权和验证表面；
2. 在原生、官方、已审查外部、组合或自研能力之间选择；
3. 在有意义的副作用前预览路线；
4. 只在已授予的任务边界内激活；
5. 观察结果、用户干预和 claim ceiling；
6. 仅在宿主或消费者确实需要时投影；
7. 回滚、清理，并留下可接续记录。

历史 v0.1 的 O3 证据只在一个来源绑定的当前宿主任务上运行过一次该闭环。v0.2 现在
直接检验这套闭环能否在重复自然任务中降低用户的工具学习和编排负担。

## 验收标准

机器可读的版本验收权威是 [product/acceptance.json](product/acceptance.json)。产品
accepted 必须同时满足五项结果、四项护栏、program 已完成、没有 active increment，
并且 work 图全部进入终态。测试数、库存、fixture、membership 和研究量可以支持结果，
但不能替代结果。

当前 v0.2 结果是：

- O1：在预注册评价协议下，一个自然真实任务以零用户工具编排干预完成自主闭环；
- O2：在重复真实任务中降低用户工具编排干预；
- O3：广泛能力组合可并存，并形成基于真实边际价值的能力决策；
- O4：形成已接受的 Agent 中立软工评价体系和最低标准；
- O5：通过 Codex 与不同的第二 Agent 宿主或运行时（使用其自身薄适配器）完成可移植闭环；同宿主第二适配器只能作为一致性证据，不能通过 O5。

## 渐进式路径

| 你的目的 | 下一处 |
| --- | --- |
| 判断 checkout 是否内部一致 | 上面的单命令[验证](#从这里开始) |
| 理解产品边界与扩展接缝 | [架构](docs/architecture.md) |
| 查看目的、工序和验收权威 | [宪法](product/constitution.json)、[工序](product/program.json)与[验收](product/acceptance.json) |
| 接续当前仓库工作 | 先核对实时 Git，再读[接续](docs/operations/CONTINUATION.md) |
| 提交一个聚焦改动 | [贡献指南](CONTRIBUTING.md) |
| 提问或报告非敏感问题 | [支持说明](SUPPORT.zh-CN.md) |
| 报告漏洞或敏感问题 | [安全策略](SECURITY.md) |
| 核对来源与权利 | [NOTICE](NOTICE)、[第三方声明](THIRD_PARTY_NOTICES.md)与[许可策略](docs/license-policy.md) |

## 能力顺序与授权

对已绑定需求，依次优先健康的原生/运行时能力、合适的官方能力、已审查且维护良好的
外部实现、现有能力组合；只有可重复的剩余缺口才允许自研。

安装、启用、账号连接、显著费用、真实 dispatch、消费者修改、验收、公开分发和发布
是不同状态迁移。原生宿主授权始终有效。

`AGENTS.md` 只是执行指导，Skills 与 Hooks 只是建议性执行输入，自研 Skills 是可替换
宿主投影，外围生态是可替换能力输入。它们都不能设定产品方向、在没有观察问题时制造
因果工作、扩张授权，或晋升证据与验收。已绑定用户意图和当前产品权威优先；冲突或
制造额外过程损失的路线必须被拒绝或降级。

## 产品契约

当前机器权威保持精简：

- `product/constitution.json`：目的、不变量、可适应表面和规划方法；
- `product/program.json`：有限因果工序和当前 active 或 paused 状态；
- `product/acceptance.json`：五项产品结果和四项强制护栏；
- `harness/`：公开产品控制核心；
- `tests/product/`：通过公开 CLI seam 的 mutation 测试。

历史 v0.1 证据、研究和前身 payload 可从 Git 历史取回，但不会因为可恢复而成为
当前权威。详见[历史边界](docs/operations/HISTORY.md)。

## 社区与权利

社区支持为 best effort。分享证据前请阅读[支持说明](SUPPORT.zh-CN.md)、
[贡献指南](CONTRIBUTING.md)、[行为准则](CODE_OF_CONDUCT.md)和[安全策略](SECURITY.md)，
并移除凭据、私有记忆、账号状态、受限材料和敏感日志。

仓库自有代码和文档使用 Apache-2.0，除非文件另有声明；第三方材料保持原权利。详见
[LICENSE](LICENSE)、[NOTICE](NOTICE)与[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

自愿赞助说明见 [SPONSORING.zh-CN.md](SPONSORING.zh-CN.md)；赞助不购买支持优先级、
功能、发布权威或技术影响力。
