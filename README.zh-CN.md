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
在精确 revision `84447a7a1b9557e22ef5585d159459e8701fa40e` 与
`f0ed9ce715afdbc5d9eb75e08225e9a1e46c554c` 上，源事实完整的 GT-14 至
GT-18 观察现仅对当前组成准入、先复用后构建、一次性纯数据自举、九个表面的共识
对齐以及一组四阶段受控演化序列通过。后者拒绝并回滚了代理指标改善但硬门退化的
方案，只在独立后状态成立后保留净改进，又在后续条件失效时替换并退役该改进；
一次性载体已清除。真实机制、持久演化、跨宿主或群体价值与发布仍受门控；当前
下一工序是不可用平均分抵消硬门的全系统平衡自审。

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
或状态层强行统一。

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
Hook、MCP server、App、状态存储、后台进程或自动项目修改。未发布的 v3.1.0
历史包基线还包含一个无状态 `SessionStart` 上下文 Hook：它不读取会话原文、
不写状态、不启动后台进程。这些只是版本化包事实，不是产品身份或永久机制禁区；
Hook 信任、宿主实际触发以及从激活到效果的链路仍需独立证据。

安装、启用和可见不等于激活。正常工作中，宿主可为相关的非简单任务隐式
调用 Skill；原生路线健康充分时它应保持安静。只有确定性暴露检查才需要
显式选择 Skill。

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

### 资源治理

Accord 把资源使用视为动态路线变量：观测需求、容量与当前暴露，区分资源
身份、所有者、租约和状态，采用满足结果所需的最小并发与预算；压力变化时
重新平衡或降级；只释放可归因的任务专属资源，并核验释放后的状态与残留。
共享资源或所有权未知的资源必须保留。

宿主原生的限额、中断、清理与回收能力健康且充分时优先使用；宿主能够证实
闭合完整循环时，Accord 不重复创建控制器，并应退役冗余逻辑。性能跟踪或
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
