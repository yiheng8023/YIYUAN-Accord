# YIYUAN Accord

<p align="center">
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/yiheng8023/YIYUAN-Accord/validate.yml?branch=main&amp;label=CI&amp;logo=github" alt="CI 状态"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/releases/latest"><img src="https://img.shields.io/github/v/release/yiheng8023/YIYUAN-Accord?color=blue&amp;label=Release" alt="最新发布版本"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/stargazers"><img src="https://img.shields.io/github/stars/yiheng8023/YIYUAN-Accord?style=flat&amp;logo=github&amp;color=ffaa00" alt="GitHub Stars"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/network/members"><img src="https://img.shields.io/github/forks/yiheng8023/YIYUAN-Accord?style=flat&amp;logo=github&amp;color=grey" alt="GitHub Forks"></a>
  <img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10 至 3.14 CI">
  <img src="https://img.shields.io/badge/CI-Ubuntu%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="Ubuntu、Windows 与 macOS CI">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/yiheng8023/YIYUAN-Accord?color=green" alt="Apache-2.0 许可证"></a>
</p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a> | <a href="README.md">English</a>
</p>

Accord 的目标很简单：用户专注创造与决策，Agent 承担实现目标所需、已经获得授权的工作。

当前，Accord 通过 Codex 和 Claude 插件提供协作指引，并在仓库中提供合同与证据检查工具。它不是一个独立工作的自治助手。是否真正完成任务、减少人工介入，需要在实际宿主中验证。

> **当前分支正在开发 3.2。** 包版本为 `3.2.0-dev.6`，尚未正式发布，也不会自动更新你安装的版本。已发布的 [v3.1.0](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.1.0) 保持不变。
>
> 可先看[当前能力边界](#已经证明什么还有什么没证明)、[开发计划](docs/operations/PLAN-v3.2.md)或[未发布更新日志](CHANGELOG.md)。不要从持续变化的 `main` 或本开发分支安装。

## 它想解决什么问题

Agent 可能做了很多工作，却偏离目标、重复询问已经决定的事、中断后留下烂尾任务，或把测试通过误认为实际交付。用户于是成了工具的协调员。

Accord 希望减少这些额外负担。用户表达意图，参与关键决策和验收，承担主体责任；Agent 在授权范围内负责发现可用能力、执行、纠偏、验证、接续和清理。

用户不应先学习内部术语，也不应每次都手动调用某个命令。例如：

> 请按已经对齐的目标继续推进这个项目。保留已有工作，核验实际结果；只有真正需要我决定或新增授权时再问我。

这是设计目标，不是“装上插件就保证实现”的承诺。如果原生 Agent 已经做得足够好，Accord 就不应额外制造流程。

## 装上后实际得到什么

已发布的 3.1 两个插件包都包含一个 `deliver-demand-driven-outcome` Skill、宿主元数据，以及短时运行的 `SessionStart` Hook 辅助程序。当前 3.2 开发包仍采用这一形态，正在修订指引。

- **Skill**：宿主 Agent 可在适用任务中使用的协作指引。可见、调用和产生有用效果是不同的事。
- **Hook**：在受支持的 `compact` 或 `resume` 事件上提供无状态提示；`startup` 和 `clear` 保持静默。它不理解任务语义，也不负责恢复故障进程或完成交接。
- **仓库工具**：供维护者使用的合同检查与参考核心。两个插件都不会安装或调用该参考核心。

插件没有新增常驻服务、MCP server、SDK 依赖、会话数据库或遥测收集器，也不替换你的指令和配置文件。安装仍会通过宿主生命周期改变插件登记与缓存。

这只是当前交付形态，不是永久禁止运行时。3.2 可以根据必要结果和实际证据，替换 Skill、Hook 或其它机制。

## 3.2 用什么标准改进

安全和约定的结果，先于减少代码、成本或介入。满足这些要求的前提下，路线应随任务调整，而不是套用全局固定 SOP。

把原生能力作为低负担起点，而不是停止发现的理由。关键缺口或可信的改善机会，可以触发已安装清单以外的比较，借用宿主发现能力和可靠外部渠道。比较完整效果与全生命周期成本；发现不等于获准安装。继续检索不太可能改变选择时，就回到交付。

评审既覆盖已知故障，也主动寻找**尚未列出的设计盲区、链路断点和环境干扰**。不能因实现困难就丢掉必要结果，也不必因 3.1 曾经存在就保留某个机制。

真正的衡量标准是：普通使用时，结果是否更可靠，用户是否少了不必要的协调、纠正和恢复工作。规则更多、动作更显眼、Skill 被调用或检查变绿，都不能单独证明价值。

### 宿主不只是一个名称

盘点先区分 Codex/ChatGPT 与 Claude 家族，再区分 CLI、桌面模式、IDE 集成、网页/云端、移动/远控和可编程入口。其它厂商适配暂缓。

同一底层引擎，不代表相同配置、权限、已加载能力或执行位置。CLI 测试成功，不能替客户端、IDE 或云端验收；宿主名称也不能代替实际模型与提供商身份。

带日期与来源的[入口和能力矩阵](docs/operations/PLAN-v3.2.md#宿主家族与入口边界)是评审依据，不是兼容性承诺。初始宿主与自定义宿主都要考虑，开发者独有的扩展不能默认为其他用户也拥有。

## 已经证明什么，还有什么没证明

[v3.1.0](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.1.0) 于 2026-09-03 从 [258611b](https://github.com/yiheng8023/YIYUAN-Accord/commit/258611be47c47a884b6d1a2e96889cf688ca7e68) 发布，tag 与 Release 保持不可变。

它的有限结论包括协作合同一致性、Codex/Claude 静态包一致性、一次有界内部实践、连续性/修复/资源治理的本地回归，以及精确源码的可复现性。详细证据和排除项见[发布记录](docs/releases/v3.1.0.md)。

这些检查不证明广泛用户收益、自动崩溃恢复、当前客户端兼容、生产安全或所有入口可用，也不能用于验收已经改变的 3.2 包。

**3.2 目前尚未达到发布条件。** 一些开发对照中，原生宿主不用 Accord 也能完成任务；当前发现/复用测试还暴露了预算内未交付、结果说明不准确等问题。调用指引并未证明增量价值。

[更新日志](CHANGELOG.md)与[开发源](product/development.json)分别记录已实现变更、反例和未完成项。普通入口的效果、环境适应、故障后的接管者、交接和完整包生命周期，仍需相应验证。

## 尝试已发布版本

可以让有相应能力的 Agent 宿主接管安装：

> 先检查当前宿主，再从精确的 v3.1.0 tag 安装 YIYUAN Accord。保留无关配置和插件，遇到必要信任时请我决定，并验证登记、新任务中的可见性和仍未确认的部分。

这是期望的交互方式，不保证每个宿主都能无人介入地完成。前提是宿主支持插件、能访问仓库，且获准修改插件状态。Hook 还需要 `PATH` 中的 Node 和宿主支持的信任流程。

不要绕过信任或直接修改全局设置来伪造受支持安装。前提缺失就说明缺口。GUI 标签会变化，应查看当前客户端支持的入口，而不是照搬旧截图。

<details>
<summary>CLI 安装参考命令</summary>

这是已记录的精确 tag 路线，不是对所有当前客户端重新完成的生命周期验收。改变状态前先核对实际命令支持。

Codex：

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.1.0
codex plugin add yiyuan-accord-codex@yiyuan-accord
codex plugin list --json
```

Claude Code：

```powershell
claude plugin marketplace add "https://github.com/yiheng8023/YIYUAN-Accord.git#v3.1.0" --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
claude plugin marketplace list --json
claude plugin list --json
```

仓库根目录才是 marketplace，不是插件包子目录。保留其它 scope 或安装来源拥有的同名状态。

</details>

### 核对效果，不只核对安装

让 Agent 分别核对精确来源与已安装字节、启用登记、新加载的 Skill 可见性及相关调用。判断已加载行为是否更新前，应新建任务或会话；列表或重载命令本身不够。

再观察真实、已经授权的任务：结果是否完成，用户仍需手动管理什么，有没有损害无关状态或留下残留。显式调用可用于检查暴露，但不能证明普通入口自动生效或带来收益。

如果暂时看不到收益，就如实记录，继续判断必要性。不要为了让 Accord 有存在感，虚构原生能力缺口或增加动作。

### 更新、回滚与移除

用户给出一次明确意图，Agent 负责识别当前登记、保留外来和共享状态、使用宿主支持的操作并核验结果。变更版本前先记录旧精确 tag。

精确 tag 不会自动前进。已记录的替换路线是移除 Accord 包及其专属 marketplace 登记，再安装选定 tag；这不是原子热更新。目标安装失败时，可能需要恢复旧 tag 并核验健康状态。

会话已加载内容与已安装文件是两种状态。不得越过宿主生命周期删除缓存，也不能把惰性缓存称作物理零残留。命令细节和历史限制保留在[不可变的 3.1 README](https://github.com/yiheng8023/YIYUAN-Accord/blob/v3.1.0/README.zh-CN.md#更新回滚移除与源码验证)，使用前仍须复核当前宿主支持。

## 开发、评估与贡献

当前分支从 [product/development.json](product/development.json)、[可见计划](docs/operations/PLAN-v3.2.md)、[架构](docs/architecture.md)和[接续导航](docs/operations/CONTINUATION.md)开始。冻结的 3.1 权威文件与 Golden Tasks 是历史输入，不是当前开发验收。

维护者可在不安装插件的情况下运行：

```powershell
python -B -m yiyuan_accord verify-development --json
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

只有 `python3` 时替换启动器即可。CI 覆盖 Ubuntu、Windows、macOS 上的 Python 3.10–3.14，并使用 Node 24 检查 Hook。这是维护工具验证，不是跨宿主行为验收，也不是用户必须安装 Python 的要求。

发布 3.2 前，更新日志须与精确候选对应；提交、推送全部版本内变更，完成必要功能、价值、生命周期、独立评审与托管检查，再按已绑定的人工授权发布同一提交并核验后态。

参与方式见 [CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md)和 [SUPPORT.md](SUPPORT.md)。[报告问题](https://github.com/yiheng8023/YIYUAN-Accord/issues)时说明期望与实际结果、精确版本、宿主入口、相关自定义因素和人工介入，不提交凭据或私密会话原文。

---

## 愿景与共创

易元联创（YIYUAN NEXUS）将持续探索人机协作及其相关领域。YIYUAN Accord 并不以永久存在为目标：它会随前沿智能、人类与机器能力及协作方式的变化而演进。前沿智能的进步既为 Accord 提供新的能力，也持续检验其必要性、边界与实际价值；当使命已经完成、被更好的机制承接，或不再需要时，项目也应能够负责任地有序谢幕。

易元联创目前仅有一名作者兼维护者，能力、精力和资源有限。我们期待与社区联合创作、协同前行。在现实能力与资源边界内，Accord 将持续维护和演进，逐步增加更多宿主适配。路线方向不代表当前已经支持，也不构成发布时间或兼容性承诺。

参与方式见 [`CONTRIBUTING.md`](CONTRIBUTING.md)；问题与建议可通过 [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues) 提交。

---

## 社区

### 贡献者

诚挚感谢所有贡献代码、评审、文档、问题报告与证据的参与者。

<p align="center">
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=yiheng8023/YIYUAN-Accord" alt="YIYUAN Accord 贡献者">
  </a>
</p>

### Star 增长趋势

[![YIYUAN Accord Star History](https://api.star-history.com/svg?repos=yiheng8023/YIYUAN-Accord&type=Date)](https://star-history.com/#yiheng8023/YIYUAN-Accord&Date)

---

## 项目支持与法律

### 项目与许可

公开项目与网站是 [github.com/yiheng8023/YIYUAN-Accord](https://github.com/yiheng8023/YIYUAN-Accord)。

发布者是 [yiheng8023](https://github.com/yiheng8023)。

YIYUAN Accord 采用 Apache-2.0 许可证。

该许可证允许商用、修改与再分发，但不允许把修改版或再分发版冒充为官方版本，或暗示其受到官方赞助与背书。

本仓库是规范公开来源；官方版本由相互匹配的 Git tag 与 GitHub Release 记录识别。独立安装后，Codex 与 Claude 插件包内也会保留各自的 `LICENSE` 与 `NOTICE`。

YIYUAN Accord、YIYUAN NEXUS 名称与图形商标保持独立，详见 [`NOTICE`](NOTICE)、[`docs/license-policy.md`](docs/license-policy.md) 与 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

社区支持按 [`SUPPORT.md`](SUPPORT.md) 所述尽力提供。

### 自愿赞助与支持

赞助完全自愿。

赞助不购买支持 SLA、处理优先级、发布权限、安全保证、治理例外、功能承诺或对技术决策的影响力。

如果 Accord 对你有所帮助，可以通过仓库所有者的[公开 PayPal 页面](https://www.paypal.com/ncp/payment/LNTF8KXGJXMZY)支持维护。

<table>
  <tr>
    <th width="300">微信支付（人民币）</th>
    <th width="300">支付宝（人民币）</th>
  </tr>
  <tr>
    <td align="center" valign="middle" width="300" height="430"><img src="docs/assets/sponsoring/wechat-pay.png" alt="微信支付自愿赞助收款码" width="260"></td>
    <td align="center" valign="middle" width="300" height="430"><img src="docs/assets/sponsoring/alipay.png" alt="支付宝自愿赞助收款码" width="260"></td>
  </tr>
</table>

付款前请核对收款方。完整条款见 [`SPONSORING.zh-CN.md`](SPONSORING.zh-CN.md)。

### 免责声明与合规说明

YIYUAN Accord 是独立的社区开源项目。

它不是 OpenAI、Anthropic、Codex、Claude、Claude Code 或 GitHub 的产品，也不代表这些组织的赞助或背书。

第三方名称与商标归各自权利人所有。

用户仍需审查 Agent 输出，并遵守适用法律、合同、宿主条款、许可证和组织政策。

本软件按 Apache-2.0 许可证以“原样”方式提供，不附带任何保证或条件，详见 [`LICENSE`](LICENSE)。

正式发布不证明生产安全，也不证明对特定用途的适用性。
