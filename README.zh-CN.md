# YIYUAN Accord

把用户想要的结果推进到可验证、可恢复的闭环，同时不让用户管理 Agent 的工具、拓扑或内部工序。

YIYUAN Accord 是一个开放、Agent 中立的人机协作可靠性契约与评估框架。它帮助 Agent 围绕用户当前目标，选择最小充分路径，并在真实决策边界保留人的权限。

它根据用户纠正和实际观测效果持续校准，并以验证、明确未知和残留清理结束任务。

项目的广义使命是改善人与 AI 的协作；当前产品面与证据严格限定为人与 Agent 的协作场景。

[English](README.md)

> **当前推荐版本：**安装 [Releases](https://github.com/yiheng8023/YIYUAN-Accord/releases)
> 中最新发布的 v2.0.1 公开预览版。本源码树是 `v2.0.1-preview.2`
> 分发；只有匹配的 GitHub 预发行版存在后，它才成为已发布推荐版本。

> GitHub 可能仍把历史 v2.0 标成“最新”，因为
> [预发行版不能获得该标记](https://docs.github.com/en/rest/releases/releases#update-a-release)；
> 它不是本项目给新用户的当前推荐版本。

---

## 公开预览版

本次发布是公开预览版，不是生产稳定性声明。当前测试集有意保持有限，因此更多用户的代表性使用、反例和失败记录属于下一层证据。

请在 [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues) 中提供精确 tag 与 revision、宿主与版本、安装方式、目标、初始状态、实际结果、人工介入、物质影响或残留，以及仍未知的内容。

不得提交凭据或私密会话原文。

---

## 30 秒开始

### 安装前确认

普通 Codex 用户只需要：

- 支持插件的 ChatGPT 桌面端 Codex 或 Codex CLI；
- 能够访问公开 GitHub 仓库，并有权修改自己的用户级插件配置；
- 安装后新建任务或会话。

Codex IDE 扩展目前不支持插件。普通使用不需要检出源码或准备 Python；
这些属于下文的验证与贡献者路径。Accord 不绑定固定宿主版本，因此应记录
实际使用的版本，而不是把某次测试版本写成永久依赖。

### 在 Codex 中安装

安装精确、不可变的公开预览版 tag：

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v2.0.1-preview.2
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

重启桌面端或新开 CLI 会话。打开 **Plugins** 或运行 `/plugins`，确认
`YIYUAN Accord for Codex` 与 `deliver-demand-driven-outcome` Skill 已出现。

新建任务后，像平常一样说明想要的结果。例如：*“把这个安装路径改准确，
保留无关改动，验证结果，并告诉我还有什么没被证明。”* 只有在需要确定性
启用检查时，才显式选择该 Skill。

### 安装改变什么

安装只会让一个渐进披露的 Skill 可供新任务使用。它不会增加 Runtime、Hook、
MCP server、App、后台进程、状态存储或自动项目修改，也不会追溯影响安装时
已经打开的任务。

克隆仓库不等于安装插件。Codex 可能把 checkout 中的 `AGENTS.md` 当作本地
项目说明读取，但这不表示 Accord 已安装。正常工作时允许隐式调用 Skill；
宿主原生行为已经充分时，它应保持安静。

插件市场声明位于 [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json)，
插件包位于 [`plugins/yiyuan-accord-codex`](plugins/yiyuan-accord-codex)。

OpenAI 当前官方资料见[插件使用](https://learn.chatgpt.com/docs/plugins)与
[插件打包](https://developers.openai.com/plugins/build/plugins)。

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

## Claude 客户端与 Claude Code

Claude 网页聊天、Claude Desktop 的 **Chat** 页和 Cowork 当前都可使用插件中的
Skill。持久安装时，在 **Customize > Plugins** 的 Personal plugins 区域选择
**Add marketplace**，从 GitHub 仓库
`https://github.com/yiheng8023/YIYUAN-Accord` 添加市场，再安装
**YIYUAN Accord for Claude**。在新聊天中输入 `/`，确认
`deliver-demand-driven-task` 可见。

Claude Code 的持久 CLI 路线是：

```powershell
claude plugin marketplace add yiheng8023/YIYUAN-Accord@v2.0.1-preview.2
claude plugin install yiyuan-accord-claude@yiyuan-accord
```

市场应注册仓库根；`plugins/yiyuan-accord-claude` 只是包目录，不是市场根。
安装和启用只让宿主可按需发现 Skill，不表示每条消息都会调用，也不证明
Claude Code、网页、Desktop 与 Cowork 的行为等价。

### Claude Code 单会话参考路径

在仓库根目录为一个本地会话加载参考投影：

```powershell
claude --plugin-dir ./plugins/yiyuan-accord-claude
```

在 `/help` 中确认 `/yiyuan-accord-claude:deliver-demand-driven-task` 已出现。该直接加载方式不会创建持久安装；参见 [Claude Code 官方插件说明](https://code.claude.com/docs/en/plugins)。

checkout 变化后可运行 `/reload-plugins`，它只重载当前会话。要停用这种直接加载的插件，结束会话并在下次启动时不再传入 `--plugin-dir`。这不会移除另行持久安装的插件。

---

## 更新、禁用与移除

先在执行安装的同一表面确认状态。Codex CLI 安装使用
`codex plugin list --json`，Claude CLI 安装使用
`claude plugin list --json`；Claude 客户端安装先查看
**Customize > Plugins**。
两个表面的清单暂时不同属于需要记录的宿主状态，不能自动证明另一处安装失败。

刷新已经配置的 Git 市场：

```powershell
codex plugin marketplace upgrade yiyuan-accord
```

不可变发布 ref 不会自动前进到新 tag。更新或回滚时，把 `VERSION_TAG` 替换成目标精确 tag，移除现有插件和市场，然后重新安装并新建任务：

```powershell
codex plugin remove yiyuan-accord-codex@yiyuan-accord
codex plugin marketplace remove yiyuan-accord
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref VERSION_TAG
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

需要保留市场但暂时停用时，在 **Plugins** 中禁用或重新启用。上面前两条命令会彻底移除插件和市场记录。

Claude CLI 管理的持久安装使用以下命令核对、刷新、更新或移除；客户端管理的安装则在 **Customize > Plugins** 中完成同样生命周期操作：

```powershell
claude plugin list --json
claude plugin marketplace update yiyuan-accord
claude plugin update yiyuan-accord-claude@yiyuan-accord
claude plugin uninstall yiyuan-accord-claude@yiyuan-accord
```

移除 marketplace 也会卸载由它安装的插件。不要直接编辑 Claude 的全局配置文件来代替这些宿主命令。

### 回滚与故障排查

回滚只选择更早的不可变 tag，绝不移动已有 tag。启用状态不清楚时，先检查宿主实际列出的插件或 Skill，再新建任务或会话，并运行对应的宿主检查。

安装表面没有列出插件，只能说明该处尚未观察到安装。若插件被列为已启用、
但当前会话没有暴露 Skill，应把 Skill 可见性或会话加载状态记为 unknown，
再走宿主的 reload 或新会话路径；不要把这种差异改写成 `enabled=false`。
安全软件、宿主配置、模型路由和会话中断都是测试变量，应与项目行为分开记录。

报告仓库缺陷时，请提供精确 revision、宿主版本、相关配置边界和验证器输出。不得附带凭据或原始私密会话内容。

---

## 验证源码与投影包

准备 Python 3.10–3.14，并克隆精确发布：

```powershell
git clone --branch v2.0.1-preview.2 --single-branch https://github.com/yiheng8023/YIYUAN-Accord.git
```

运行 canonical verifier：

```powershell
python -B -m yiyuan_accord verify --root . --json
```

静态检查两个参考宿主投影：

```powershell
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

这些检查只验证仓库与投影包的一致性，不会安装插件、证明宿主实际行为、满足真实场域验收、授予发布权限或证明生产安全。

---

## 仓库包含什么

- **当前 schema-v2 权威集合**：
  [`constitution.json`](product/constitution.json)、
  [`program.json`](product/program.json) 与
  [`acceptance.json`](product/acceptance.json)
- **派生术语与边界**：[`CONTEXT.md`](CONTEXT.md)
- **数据驱动的通用验证器**：
  [`yiyuan_accord/control.py`](yiyuan_accord/control.py)
- **可替换、无运行时的 Skill 投影**：Codex 与 Claude 适配投影；现有行为证据仍分别绑定具体宿主表面
- **帮助与干扰代表任务**：
  [`evals/golden-tasks.json`](evals/golden-tasks.json)

可移植契约是 **K1–K5**。**H1–H10** 宿主规则和 **L1–L7** 试错标准把宿主漂移与历史失败留在核心之外。

这三份文件只是当前可审查拓扑，并非不容置疑的真理或永久数量。未来的合并、拆分、替换或退役必须保留来源，并显式迁移 schema、验证器、映射与受影响证据。

---

## 边界与证据

Accord 不增加安装器、后台 Runtime、Hook、MCP 服务、App、状态库或自动用户配置写入。它依赖宿主当前能力，并把宿主专属生命周期工序留在可替换投影中。

v2.0.1-preview.2 是基于不可变 v2.0 的公开预览版分发与易用性修补，不主张通用人机协作正确性、广泛真实场域有效性、跨宿主或跨表面等价、对所有用户都降低负担或生产安全。

验证器通过只证明该 checkout 的有限仓库契约。已接纳行为样本仍绑定具体任务、宿主、投影和 revision。保留的 `GT-07:cleanup` 失败继续收窄主张，不会被改写成成功。

精确标准与发布门位于 [`product/acceptance.json`](product/acceptance.json)，有限发布主张见 [`docs/releases/v2.0.1-preview.2.md`](docs/releases/v2.0.1-preview.2.md)。

---

## 本次发布之后

v2.0.1-preview.2 是一个有限阶段，不是使命终点。后续工作只从已观察的残余缺口、真实任务证据或重大宿主变化中准入。当前持续证据通道包括 Claude 客户端实际行为、真实场域效果、跨宿主或长期证据，以及代表任务 `GT-06`、`GT-09` 和 `GT-10`。

宿主能力增强后，Accord 可以简化或退役投影，而不是自动增加机制。缺失功能只有在用户价值、风险降低或恢复收益大于代码、认知、生命周期和运行成本时才恢复。

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
