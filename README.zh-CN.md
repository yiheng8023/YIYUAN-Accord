# YIYUAN Accord

把用户想要的结果推进到可验证、可恢复的闭环，同时不让用户管理 Agent 的工具、拓扑或内部工序。

YIYUAN Accord 是一个开放、Agent 中立、机制中立的人机协作系统：由小型可移植可靠性内核与动态适配、可替换的结果交付行为组成。它帮助 Agent 围绕用户当前目标选择充分路径，并在真实决策边界保留人的权限。

它根据用户纠正和实际观测效果持续校准，并以验证、明确未知和残留清理结束任务。

项目的广义使命是改善人与 AI 的协作；当前产品面与证据严格限定为人与 Agent 的协作场景。

[English](README.md)

> **当前公开推荐版本：**使用不可变的
> [`v2.0.1-preview.1`](https://github.com/yiheng8023/YIYUAN-Accord/tree/v2.0.1-preview.1)
> 公开预览版。当前 `main` 正在进行产品重塑，不是安装或发布候选；
> 未发布的 preview.2 路线已经退役。

> GitHub 可能仍把历史 v2.0 标成“最新”，因为
> [预发行版不能获得该标记](https://docs.github.com/en/rest/releases/releases#update-a-release)；
> 它不是本项目给新用户的当前推荐版本。

---

## 公开预览版

本次发布是公开预览版，不是生产稳定性声明。当前测试集有意保持有限，因此更多用户的代表性使用、反例和失败记录属于下一层证据。

请在 [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues) 中提供精确 tag 与 revision、宿主与版本、安装方式、目标、初始状态、实际结果、人工介入、物质影响或残留，以及仍未知的内容。

不得提交凭据或私密会话原文。

---

## 使用已发布预览版

不要从当前 `main` 安装。当前公开推荐版本是不可变的
[`v2.0.1-preview.1`](https://github.com/yiheng8023/YIYUAN-Accord/tree/v2.0.1-preview.1)；
请按该 tag 的
[已发布 README](https://github.com/yiheng8023/YIYUAN-Accord/blob/v2.0.1-preview.1/README.zh-CN.md)
执行精确的安装、验证、更新与移除路径。

`main` 中的 `v2.0.1-preview.2` 包只是未发布的历史检查点。其发布路线
已在发布前退役；它不是新的推荐版本、滚动 tag 或面向普通用户的本地候选
安装入口。

审查源码或参与贡献前，请先读
`product/reshaping-guidance.json` 与
`docs/operations/CONTINUATION.md`。当前仓库结构有效，但有意不满足候选
就绪条件。

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

## 当前开发 checkout

当前 checkout 用于审查和重塑，不面向普通安装。其 Codex 与 Claude 包保留
preview.2 检查点，以便继续核验精确分发内容与宿主观测；它们不定义未来
机制集合。

已经安装并启用的 preview.2 插件可以继续作为潜在能力存在。安装或可见不
代表每条消息都会激活，也不证明有效行为或产品价值。不要从 `main`
重新安装；也不要把禁用当成隔离干扰的唯一办法。未来有行为变化的候选必须
证明适用性、隔离、热更新或原子替换、健康检查和回滚。

贡献者可以运行：

```powershell
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

这些检查验证当前仓库结构和历史包的一致性，不会安装插件、证明有效行为、
验证重塑后的产品、授予发布权限或证明生产安全。

---

## 仓库包含什么

- **当前 schema-v3 权威集合**：
  [`constitution.json`](product/constitution.json)、
  [`program.json`](product/program.json) 与
  [`acceptance.json`](product/acceptance.json)
- **已接受、可修订的重塑与动态索引指导**：
  [`reshaping-guidance.json`](product/reshaping-guidance.json)
- **派生术语与边界**：[`CONTEXT.md`](CONTEXT.md)
- **数据驱动的通用验证器**：
  [`yiyuan_accord/control.py`](yiyuan_accord/control.py)
- **历史 preview.2 参考投影**：Codex 与 Claude 包；其精确行为证据仍分别
  绑定具体宿主表面，不限制未来机制选择
- **帮助与干扰代表任务**：
  [`evals/golden-tasks.json`](evals/golden-tasks.json)

可移植契约是 **K1–K5**。**H1–H10** 宿主规则和 **L1–L7** 试错标准把宿主漂移与历史失败留在核心之外。

这三份权威文件只是当前可审查的启动拓扑，并非不容置疑的真理、永久数量，
更不是由今天宿主可见能力决定的覆盖上限。未来的合并、拆分、替换或退役
必须保留来源，并显式迁移 schema、验证器、映射与受影响证据。

---

## 当前重塑边界

Accord 不受 Codex、Claude 或任何具体 Agent 能力面的限制。每个具体 Agent
及其宿主能力面都只是可替换适配器和带新鲜度边界的观测快照。可移植产品
覆盖的是 Agent 中立的“需求—能力—权限—路线—实际效果—证据”动态关系；
当现场事实与生命周期价值成立时，原生、官方、受维护、组合或受控新建的
机制都可以进入路线。

Skill、插件、App、MCP、Hook、配置、状态、Runtime、云端载体或其他机制，
既不是必选项，也不是永久禁区。可见或安装不等于激活；原生路径充分时应当
没有不必要介入，存在残余缺口时则可以引入具备干扰、更新、回滚和退役控制
的局部机制。

当前验证器只证明本次活动重塑状态的结构一致性，以及保留历史包证据的完整
性；它报告当前验收为 0/8、没有发布候选。不可变的 v2.0 与
v2.0.1-preview.1 仍是公开历史事实；preview.2 未曾发布，不得打 tag。

已完成的重塑增量把一个真实结果映射为计划、因地制宜的工序、验收和精简
目标投影，并回放了最小动态适配纵向切片。下一项有界工作，是在不继承
preview.2 权威或包就绪状态的前提下，把这份已接受的活动基线另行形成
`v3.0.0` 正式发布候选。详见
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

本软件按 Apache-2.0 许可证以“按原样”方式提供，不附带任何保证或条件，详见 [`LICENSE`](LICENSE)。本公开预览版不证明生产安全或对特定用途的适用性。
