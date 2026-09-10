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

Accord 为人与 AI 的长期协作提供协调与可靠性保障：用户提出目标或初步构想后，Agent 在授权范围内澄清需求、评估可行性、补足必要条件，并持续负责执行、纠偏、恢复和结果验证。用户不需要先学会工具、配置、模型调度或任务交接；熟练用户同样保有直接操作和调整路线的自主权。

项目开源，不以盈利为目标，以工业/商业生产级标准建设，追求平权、普惠和用户自主。项目决策以用户权益、可验证价值和可持续维护为依据，商业资助与平台关系不改变供应商中立原则。通用协作设计与具体宿主适配分离，按实际价值复用宿主能力和成熟资源。

> **3.3 正在开发，尚未完成验收或发布。** 本版只交付 OpenAI 范围的适配，ChatGPT 与 Codex 各适用入口分别核验；Claude 不在 3.3 分发范围。聚焦一个供应商的当前入口是版本安排，不改变项目中立性。
>
> 当前设计、历史处置、系统图、未完工作和收官标准统一见 [3.3 共识节点与计划](docs/operations/PLAN-v3.3.md)。[v3.2.1](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.2.1) 是保留的发布基点，旧版本范围与证据以其精确 tag 为准，不继承为 3.3 支持声明。

## 协作问题与目标

Agent 可能做了很多工作，却偏离目标、忽略一句话中的部分意图、中断后丢失未完责任，或把局部测试通过误认为交付完成。用户于是成了工具协调员和故障恢复者。

Accord 希望把这些责任交回 Agent：理解连续输入，主动研究和创造可建立的条件，按需组织宿主、自身与外部能力，纠正受影响的历史判断和产物，核验结果及资源后态。只有真正需要用户决定、授权或本人完成的步骤，才以普通语言说明。

这是需要持续验证的目标。世界级是改进志向；实际成熟度由普通使用中的结果、可靠性、用户负担和完整成本证明。

## 如何工作

起点—过程—结果是一组可以并行、嵌套和反馈的关系。语义解释变化，事件触发相关重审，负边界保护目标、授权和证据；具体路径由任务决定。局部确定性操作可以标准化，全程不套固定 SOP。

插件是具体宿主中的交付形式。Accord 的协作职责贯穿用户意图、宿主与外围能力、实际结果；关键判断、状态变化和结果反馈需接通，但不要求所有调用经过统一代理，也不取得高于用户或宿主的权限。用户操作引起重要变化且意图不明时才确认预期结果，明确选择持续有效；纠偏不能擅自恢复用户设置。

动态适应面向实际环境。Accord 应利用宿主已有的获准能力逐步建立缺失条件、验证生效并形成恢复路径，即驱动宿主自举；不要求用户先重置成默认环境。开发隔离只是定位原因的手段，实际适应与自举能力仍须通过真实任务验证。

自知、自洽、自治、自学、自纠、自愈、自证和自进化，是支撑自举的能力维度。认知上的监测与调整须连接工程上的执行、反馈和恢复；工程自举不以主观意识为前提。经验需经过验证才能复用，判断与结果须接受可反驳的证据检查，改进要能发现退化并撤回有害变化。这些是[设计与验收方向](docs/operations/PLAN-v3.3.md#自举的能力维度与证据)，不代表八项已全部实现。

当前开发包通过 Skill、原生事件提示和可选任务状态机制参与宿主工作，仓库工具用于合同和证据检查。可见、调用、执行和产生可靠效果是不同阶段。组件数量、是否需要运行时及其形态，均按真实缺口和生命周期成本选择。

宿主的按钮、菜单、快捷键、设置、任务与项目操作、模型、权限、记忆、自动化、运行环境及扩展能力，都属于发现范围；不能只查看当前工具列表。Agent 逐项判断用途和条件，按需使用，核验效果及退出状态。覆盖不等于全部启用，未知不能冒充已覆盖。

生态矩阵管理也是核心职责：插件、App、Skill、MCP 等扩展的组合、依赖、冲突和生命周期都需按任务管理。安装、上下文暴露、连接与进程占用分别核对，选择合适作用域，按需启用、复用和退出，避免无界全局常驻。退出时保护用户选择及其它任务的共享依赖，并验证实际释放；不能假定卸载会清除已进入上下文的内容。

## 能力边界与当前证据

3.3 已有局部普通任务、输入纠正、文件状态、上下文评估及受控接管观察，但完整普通入口、自主继承、失败恢复、环境变化和系统净影响仍未验收。不同入口、版本和配置不能互相代验；开发脚本、控制器代办和人工提示不能证明普通用户可自主得到同样结果。

Accord 不训练模型、不扩大原生上下文，也不越过宿主的权限或接口边界。必要条件不足时，Agent 研究可行替代或补足办法；真实限制仍需说明并保留未完责任。参考核心或提示词不能单独充当执行和权限保障。

介入可能增加上下文占用、时间、费用、指令冲突或维护负担。按实际结果评估净影响；同等效果下优先低负担路线，必要时缩小、替换或退役介入。错误组件造成的既有影响仍须追溯和修正。

当前未完项见[共识节点](docs/operations/PLAN-v3.3.md)，判据见[验收视图](docs/operations/ACCEPTANCE-v3.3.md)，带条件的观察见[历史试验记录](docs/operations/PROCEDURE-v3.3.md)。历史事实见[更新日志](CHANGELOG.md)与各版本发布记录，历史通过结果不能作为当前版本的验收依据。

## 安装与维护

正式发布后的宿主安装、传播材料更新、OpenAI 插件市场投放及项目治理安排见[发布后计划](docs/operations/PLAN-v3.3.md#发布后的部署传播与治理)。市场收录是后续目标，尚未完成；长期以项目或组织为管理主体，避免依赖个人账号作为唯一控制点。

3.3 尚无已接受的发布可供正式安装。使用历史版本时，先核对同名 GitHub Release 与不可变 tag；不把持续变化的开发分支当作稳定发行。

可以把安装意图交给具备相应能力的 Agent：

> 核对已接受的精确版本和当前宿主条件，保留无关配置与插件，在授权范围内完成安装并验证实际生效；遇到必要信任或本人动作时，准备好具体事项再告诉我。

登记、安装字节、当前任务可见性、实际参与及效果分别核验。启用 Hook 需要相应运行环境、原生事件和宿主信任。更新、回滚与移除需健康执行者和恢复路径；已加载内容、安装状态和运行资源分别处理。完整历史命令和边界可查看 [v3.2.1 README](https://github.com/yiheng8023/YIYUAN-Accord/blob/v3.2.1/README.zh-CN.md)，执行前核对当前宿主支持。

## 开发、评估与贡献

当前分支先读[共识节点与计划](docs/operations/PLAN-v3.3.md)及[接续导航](docs/operations/CONTINUATION.md)，按需参考[机器投影](product/development.json)和[架构](docs/architecture.md)。冻结的 3.1 权威文件与 Golden Tasks 是历史输入，不是当前开发验收。

维护者可在不安装插件的情况下运行：

```powershell
python -B -m yiyuan_accord verify-development --json
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
```

只有 `python3` 时替换启动器即可。CI 覆盖 Ubuntu、Windows、macOS 上的 Python 3.10–3.14，并使用 Node 24 检查 Hook。这是维护工具验证，不是跨宿主行为验收，也不是用户必须安装 Python 的要求。

发布要求更新日志、提交推送的版本内变更、必要功能/生命周期/净影响证据、独立评审与托管检查相符，再按已绑定的人工授权发布同一提交并核验公共后态。冻结候选不是发布凭证。

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

本仓库是规范公开来源；官方版本由相互匹配的 Git tag 与 GitHub Release 记录识别。独立安装后，当前分发插件包内也会保留各自的 `LICENSE` 与 `NOTICE`。

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

它不是 OpenAI、Codex 或 GitHub 的产品，也不代表这些组织的赞助或背书。

第三方名称与商标归各自权利人所有。

用户仍需审查 Agent 输出，并遵守适用法律、合同、宿主条款、许可证和组织政策。

本软件按 Apache-2.0 许可证以“原样”方式提供，不附带任何保证或条件，详见 [`LICENSE`](LICENSE)。

正式发布不证明生产安全，也不证明对特定用途的适用性。
