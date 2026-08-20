# Agent Autonomy Harness

[English](README.md)

Agent Autonomy Harness 是一个开放、Agent 中立的人机协作质量安全网。它从用户真正想要的
结果出发，只在宿主原生能力不足时补最小缺口，并把人类权威、持续纠偏、后果级验证、恢复
与清理放在同一条闭环里。

它不是通用 Agent runtime、能力市场、模型路由器、身份/审计系统或上下文预测器。它也不
承诺一次发布解决所有人机协作问题。

## 为什么重塑

约两个月的真实 Codex 协作试错证明：项目初衷没有问题，但强 Agent 会出现
repair-by-addition、proof proxy、历史证据反向控制当前产品、上下文与拓扑负担转嫁、以及
局部通过被误读为收官等系统性偏差。v1.2 不抹去这些失败，而是把它们压缩为可迁移标准和
Golden Tasks；旧代际验证器退出默认路径，详细事实仍可由 Git 历史复现。

项目专项审计已保存在
[2026-08-20 重构与长期演化报告](research/reviews/2026-08-20-agent-autonomy-harness-refactor-and-evolution-report.md)。
共享的人机协作短板研究仍由
[YIYUAN-CALIBRATION 固定修订](https://github.com/yiheng8023/YIYUAN-CALIBRATION/tree/e060a08f05361cb4cc9a67be050236cdbbde1de5/common/human-ai-collaboration-shortfalls)
唯一托管，本项目只引用和吸收其结论。

## 产品内核

| ID | 约束 |
| --- | --- |
| K1 | Goal First：保持一个当前、可追踪的目标与阶段 |
| K2 | Minimum Sufficient Route：原生优先，无必要则 no-op |
| K3 | Human Authority：保留真正的人类判断、授权与否决权 |
| K4 | Continuous Reconciliation：在材料检查点对照目标、事实、效果与资源 |
| K5 | Close the Loop：按主张层级验证、恢复、清理并限制结论 |

K1–K5 之上有两组可执行约束：

- H1–H10 宿主准入标准：官方指引优先但有条件信任、能力而非版本、effective 而非
  declared、unknown 一等、漂移重验、不让用户补偿 Agent 缺口、宿主改进后退休补丁。
- L1–L7 试错经验标准：结果高于过程、重复修复先做减法、总复杂度必须付租金、渐进式
  assurance、同时测帮助和干扰、连续性不绑定通用阈值、失败作为反例而非继承证明。

## 当前交付面

- 三份语义权威：
  [constitution](product/constitution.json)、
  [program](product/program.json)、
  [acceptance](product/acceptance.json)
- 一个数据驱动的通用验证命令：`python -B -m harness verify`，实现由
  [control.py](harness/control.py) 与纯准入护栏
  [guardrails.py](harness/guardrails.py) 组成
- 两个无 runtime、无强制 Hook 的薄 Skill 投影：
  [Codex](plugins/agent-autonomy-harness-codex) 与
  [Claude Code](plugins/agent-autonomy-harness-claude)
- 一组同时度量帮助与干扰的
  [Golden Tasks](evals/golden-tasks.json)

~~~powershell
python -B -m harness verify --root . --json
python -B -m harness host-check --adapter codex --root . --json
python -B -m harness host-check --adapter claude-code --root . --json
python -B -m unittest discover -s tests/product -v
~~~

host-check 只证明投影静态准入；它明确不会把 Skill 可见、插件已安装或 JSON 通过冒充
宿主行为。真实行为要在精确宿主上运行 Golden Tasks，并保留独立观察。

第一轮 Codex GT-02 已把这一区分变成真实反例：Agent 做出了正确、有界的仓库修复，保留了
无关 dirty 状态，却留下两个未披露的 Python 缓存文件；在一次同目的提示词修复后，失败仍
重复。因此该任务和 Codex 清理行为保持失败。Harness 能通过的只是更窄的能力——及时发现、
保留并限制该失败的主张；评估器事后清理不能把宿主失败改写为通过。

## 状态与收官边界

v1.2 正在进行一次全局减法重塑。当前目标模式提示词已在
[product/program.json](product/program.json) 中准备，但宿主里的旧目标仍保持暂停；
仓库文件不会假装已经替换宿主生命周期。

有限发布需要 R1–R4 与 Q1–Q4 的确定性和代表性证据，以及具名人类对精确候选、主张上限、
发布与公开的授权。仓库只能记录“已请求”状态，不能自行铸造这项人类授权；发布时的临时
外部授权输入必须绑定干净的精确 HEAD。真实场域效果、广泛人群的负担改善、所有 Agent/宿主等价性和长期组织
影响是发布后持续证据通道，不是为了拖延本次有限发布，也不会被本次发布虚构为已证明。

v1.2 的有限代表样本是 GT-01、GT-02 与 GT-07。样本任务失败会阻断精确宿主行为资格；只要
失败仍被保留、残留处置明确、发布主张排除该行为，它不会自动把“Harness 正确评估并暴露
失败”误判为产品不合格。

收官是一个可维护开源基线，不是学习终点。后续真实失败可以增加 Golden Task、收窄主张、
简化或退休投影，或开启一个新的有界增量。

## 参与

直接说明目标、问题或观察即可，不必先学习 Harness 术语、工具或拓扑。维护者和 Agent 负责
把输入映射到当前权威、选择最小路线、验证并清理。参见
[CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md) 和
[历史边界](docs/operations/HISTORY.md)。
