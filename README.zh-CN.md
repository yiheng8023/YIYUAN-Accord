# Agent Autonomy Harness

[English](README.md) | 简体中文

最短路径：[验证当前 checkout](#从这里开始) · [理解闭环](#harness-做什么) · [选择深入路径](#渐进式路径)

Agent Autonomy Harness 是一个 Agent 中立产品：它在真实任务中保持目标、能力路线、
授权边界、生命周期、连续性、证据和清理的一致性，而不是让用户亲自编排每个 Agent、
Skill、MCP、Plugin、Hook、线程、工作树和管理器。

它不是“大而全的 Skills 列表”。外围能力是可替换输入；Harness 负责判断何时需要、
授予什么边界、怎样观察效果，以及何时释放路线。

## 从这里开始

前置条件：Git 与 Python 3.10 或更高版本。当前 checkout 只使用 Python 标准库；本地
验证不需要安装包、连接账号或调用外部服务。

```powershell
git clone https://github.com/yiheng8023/agent-autonomy-harness.git
cd agent-autonomy-harness
python -B -m harness verify --root . --json
```

accepted 的 v0.1 checkout 会报告 `5/5` 项结果、`4/4` 项护栏、无 active
increment，且 completion 为 `accepted`。这一仓库绑定的验收不证明生产、Release
公开分发、广泛价值或跨宿主结论。

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

当前 O3 证据只在一个来源绑定的当前宿主任务上运行过一次该闭环，不代表通用生命周期
支持。

## 验收标准

机器可读的版本验收权威是 [product/acceptance.json](product/acceptance.json)。产品
accepted 必须同时满足五项结果、四项护栏、program 已完成、没有 active increment，
并且 increment/work 图全部进入终态。测试数、库存、fixture 和研究量可以支持结果，
但不能替代结果。

当前证据边界：

- O2 把一个用户提供的真实任务绑定到非空能力路线；
- O3 绑定一份 60 项非笛卡尔评价和一次六相位当前宿主生命周期收据，并保留明确的
  attestation 限制；
- O4 把一个 fresh receiver 绑定到一个仓库状态，物质性复述为零；
- O5 只覆盖命名的 Harness 清理目标，不覆盖无关宿主存储。

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

## 产品契约

当前机器权威保持精简：

- `product/constitution.json`：目的、不变量、可适应表面和规划方法；
- `product/program.json`：有限因果工序及全部终态 work 图；
- `product/acceptance.json`：五项产品结果和四项强制护栏；
- `harness/`：公开产品控制核心；
- `tests/product/`：通过公开 CLI seam 的 mutation 测试。

历史研究和前身 payload 可从 Git 历史取回，但不会因为可取回而成为当前权威。详见
[历史边界](docs/operations/HISTORY.md)。

## 社区与权利

社区支持为 best effort。分享证据前请阅读[支持说明](SUPPORT.zh-CN.md)、
[贡献指南](CONTRIBUTING.md)、[行为准则](CODE_OF_CONDUCT.md)和[安全策略](SECURITY.md)，
并移除凭据、私有记忆、账号状态、受限材料和敏感日志。

仓库自有代码和文档使用 Apache-2.0，除非文件另有声明；第三方材料保持原权利。详见
[LICENSE](LICENSE)、[NOTICE](NOTICE)与[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

自愿赞助说明见 [SPONSORING.zh-CN.md](SPONSORING.zh-CN.md)；赞助不购买支持优先级、
功能、发布权威或技术影响力。
