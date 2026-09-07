# Continuation

当前导航；产品事实、授权及验收源仍是 `product/development.json`。旧交接和试验过程
保留在 Git 与 `developmentObservations`，不把历史快照继续写成当前状态。

## 写入目标与授权

- 唯一开发写入位置：`C:\Projects\YIYUAN-Accord-post-v31`，分支
  `phase/post-v3.1-successor`，跟踪 `origin/phase/post-v3.1-successor`。
  每个仓库命令显式使用这个目录。桌面项目的 `C:\Projects\YIYUAN-Accord`
  是另一个受保护的脏 checkout；不得改动，也不为继续而创建新 worktree。
- 当前主写者为主线程20，`01a07984-457e-75a1-ba39-4e5fda61f440`。
  主线程19 `01a072b3-0198-77f3-b7a8-875763d50b1d` 已静默并明确转移写入权；
  `40df60cfc9625cf7108979cfb94690a1a90431db` 与私有 `task19-handoff.json`
  记录其交接。接收回执不等于接管，接管不授权归档。两个任务都应保留。
- 已授权范围内实现、提交、推送及验收后的 3.2 发布；当前发布条件未满足。
  实现稳定后再统一完成双语 README、CHANGELOG 和全局核对。
- 用户已撤回发布前向共享宿主安装候选的路线。继续使用受控的任务局部暴露；
  验收发布后的既有 Accord 更新仍已授权，须备份、恢复和实际激活核验。
  不新增账号、信任、数据访问、显著成本或无关个人配置变更。
- 不替换共享 AGENTS/CLAUDE 指导或 ASSETS 内容。用户指导是宿主环境变量，
  不可作为只存在于开发环境的隐含产品依赖。
- 变更前核对实时 branch、status、HEAD、upstream 和 ahead/behind，保留无关变化。
  不改写历史标签、发布或失败证据。3.1.0 为
  `258611be47c47a884b6d1a2e96889cf688ca7e68`；开发 predecessor 为
  `2d09d6d089453d165f5bacb6c1f1492ddfc618aa`。

## 当前路线

用户要求必要功能先形成可用实现，再综合校准质量、成本、预算与净价值。
保持输入保护、真实授权和必要失败后态；不把门禁、文档或测试数量当成结果。
反复失败而无新信息时变更方法或暂停支线，不继续挤字节、扩框架或重复模型试验。

持续纠偏覆盖历史判断、工序、已做产物、开发、维护和迭代，并是 Accord 的职责。
用户和 Agent 的事实判断均可被证据纠正。Accord 与宿主是共生、协同、互补关系，
各自责任与决定边界独立；这不意味着 Accord 脱离宿主权限和运行能力。
优先借助充分的宿主执行，只有真实必要缺口才新增设施。

`systemOptimization.workSequence` 是唯一可编辑工序源；`PLAN-v3.2.md` 由
`render_development_plan` 派生，原生 `update_plan` 映射相同六工序，可附加源中的当前焦点。变化后先核对
下一动作、依赖、状态含义及未闭合结果，再做机械映射检查。

| 工序 | 状态 | 下一结果 |
|---|---|---|
| 本轮启动事实与方向核对 | 本轮已完成 | 持续纠偏仍贯穿后续，不能关闭为一次性职责。 |
| 普通入口必要功能链实现与实际纠偏 | 待续 | 核对原生续做与新输入边界，补齐必要资料/能力选择、返工和如实收尾。 |
| Desktop 连续性与归档授权边界 | 待开展 | 按实际信号继续或接管，单写者、来源保全及失败恢复同次成立。 |
| 两宿主安装、更新与独立恢复 | 进行中 | 当前修复管理入口与判定衔接；dev.15 安装加载成立，坏源保护决定、实际更新与独立恢复仍未成立。 |
| 功能完成后的净影响、质量与成本对齐 | 待开展 | 合适的同条件比较，质量底线、成本、干扰及净价值。 |
| 3.2 定版、发布与收尾 | 待开展 | 精确候选独立评审、CI、发布、公开核验和发布后既有安装更新。 |

六个必需范围是 `codex-function`、`claude-code-function`、
`codex-desktop-continuity`、`codex-lifecycle`、`claude-code-lifecycle`、
`product-value`。目前四个范围有六个定义；Desktop 与 value 尚未定义；无已准入
记录。0 条准入不等于没有执行过试验。功能完成、发布就绪仍为 false，净价值未验证。
Claude 的现有 ready-orders 用例已重绑为单候选 policy 更新：读取必要资料、改写旧产物、
普通同进程后续需求及如实核验；比较移到 value。个人状态重定向并非初始机器，仍须
核对或声明实际环境影响。首次观察的 Node 核验误判仍保留；修正观察方法后的新 episode
已完成 190→140→60、普通新输入回执和每阶段实际写后核验。自动验证器“不可用”
的措辞缺乏排查依据，保留为质量问题；实际交付不等于整项或整版准入。
组合条款已明确允许声明的用户自定义，记录外援角色和适用前提，不把其贡献计作
Accord 自带能力。历史观察保留原定义，不能因归因文字修正而改名晋升。
定义可按必要结果调整，并同步重绑入口、条件、判据及独立评审；不能给历史结果改名
晋升。固定多臂、目录预算、轮次或每个任务调用 Skill/checkpoint 均非必要用户结果。

## 当前实现与可复用证据

代码基点 `e527e1dda26edbeaa2806928e89a494d0c8dda9f`，两个完整包均为
`3.2.0-dev.15`。证据和导航编辑不改变包版本。

| 对象 | SHA256 |
|---|---|
| Codex 包 | `4cdf1a9ec621682de7abe8c4c4ee969504a5eef1eab0fc7f21b660a5ddea2aa9` |
| Claude 包 | `55a59202bd2e8de9b54b741356e7e84a9ced9ad3f76d22c6b89a386891dce99d` |
| task-checkpoint.cjs | `6490e186e300c2c0a7fc76bc126a468b8e705ea4271623d25337f94220450fbe` |
| accord-hook.cjs | `c12bd3f3749779f1b54ccbd6703a1843e29a5f6add150022474b3541fd89673d` |

任务 checkpoint 已连接受支持的原生输入、Stop 和会话结束，Codex 另接 Interrupt。
它检查绑定文件和输入新鲜度、保留未完成任务，并对变化后的未满足观察请求一次续做。
暂停不能把旧合同标成符合新要求；输入发布失败保留可恢复锁；已证实失去所有者的 input 锁恢复使旧回执失效，
重放真实输入须匹配 epoch。Agent 仍负责语义、谓词选择与执行。没有守护进程、
通用宿主权限拦截或外部写入者原子锁。

- `checkpoint-adversarial-correction-dev15`：五个真实反例修复及独立复验；
  15 项执行测试通过，包含 Windows 只读输入回执失败与完整恢复。
- `codex-existing-artifacts-correction-dev14`：两份文件先实际为 100；生产者
  改变输入后，Agent 经失败核验及被拒的提前 retire，重新绑定并把两份旧产物改为 60。
  142.742 秒、自然退出、0 子进程。该证据绑定 dev.14 CLI；不是 dev.15 整体准入。
- `codex-native-stop-transport-dev15`：真实 Stop 理由进入第二次无认证回环请求；
  情况未变时不无限重复，未完成状态保留。原生工具写入遭只读策略拒绝，文件交付未证明；
  最后一轮完整捕获 stdout/stderr。三轮自然退出、0 子进程、三个临时根均已删除。
  普通模型自主行为、App Server 与 Desktop 仍不能由合成传输证据推得。
- `claude-policy-two-stage-dev15`：24cc6aa 下两阶段真实完成，26 次调用无禁止尝试或效果；
  63.245 秒、自然退出、0 子进程，49 文件保留且临时根已删除。两段“宿主确认未变”
  有实际 Read 回执依据；“没有可用自动验证器”仍超出观察。18/10 的原生轮次
  与请求 16 的口径差异未查明，不推断原因或上限验证。
- `claude-policy-first-stage-observer-method-correction`：ae14955 下真实 Node 写后核验
  被私有观察器漏记；宿主正确交付 140，后续规则更新未发送。没有输入损坏或非法尝试；
  37 文件及原误判已保留，临时根和进程已清理。识别工具方法的修正不能补记未执行的第二阶段。
- `claude-dev15-ordinary-delivery-and-package-feedback`：当前完整包的真实任务正确
  交付总额 100，输入保留，Agent 实际删除自建 verify.py；40.849 秒、自然退出、
  0 子进程。仍重复三次被拒 Python 命令，并把内容/目录核对称为字节级验证。
  独立检查确认字节未变，但不能倒记成 Agent 执行过字节比较；真实性缺陷必须修正。
- 同一观察中的独立零真实模型试验：完整九文件 Claude 包的 339 字节 PostToolBatch
  反馈实际进入第二次回环请求。没有额外观察者 Hook；仅在 stdout 缺少事件不能推断
  未执行。此项证明投递，不证明模型收益。不要无新证据重跑相同普通任务。
- 较早 `claude-ready-orders-correction-dev6`、Codex capability-loss/conflict 及
  selected-continuation 观察按原主体复用。若需新正式用例，先核对其未覆盖效果，
  不为沿用旧入口重复完整测量。
- `claude-lifecycle-target-identity-rebinding` 保留原方法判断；9a21f40 上的新 episode
  已反证“只补摘要就足够”。dev.15 安装并实际加载，两个独立 3.1 profile 也实际
  加载可用，但更新 Agent 在原生校验已返回坏源后继续探索，未作出保护决定便耗尽
  轮次；44 次调用未加载 Skill 正文，未执行 helper。旧包未变不等于主动保护。
  全部原始证据已保留，三 profile 已原生卸载、移除市场并清理；实际更新与独立
  恢复尚未执行。当前修复包内管理发现入口和输入契约，再验证受影响功能。
  普通入口的剩余条件与真实性问题仍待续，不因切换独立工作而标为完成。

- `codex-windows-effective-policy-text-only-pair`：同一原生 0.153.4 的两臂仅改变
  Windows sandbox 启用条件，实际首请求分别为 read-only 与 workspace-write。
  两臂均无真实模型或工具调用；不证明文件写入或沙箱执行。各保留 121 文件，私有
  根已清理。候选原生新增私有 trust 项及首次比较失败均保留；试验结束 15 项共享
  状态未变，清理后 default.rules 的变化与两条删除批准前缀事件单独记账。

当前局部验证：checkpoint 15 项；PostToolBatch 5 项；历史 Hook 兼容 5 项；
development 66 项均通过。产品源一致性通过；132 个代码/测试文件、1,226,349 字节，
主指令 30,860 字节。当前开发界限为 1,300,000 / 132 / 32,000，保留至少 5% 代码余量。
纯导航和观察编辑不构成重跑全部测试的理由。修复后的本地 PASS 不代表宿主、Desktop、
生命周期、价值或发布验收。

## 未决故障与历史位置

主线程18 曾在只读回执后、真正接管前归档自己，用户随后手动恢复。恢复后的状态不能
否认此前归档。旧 source-release 措辞是可能因素，非已证实唯一原因；当前指导已分清
回执、接管、来源资源释放和归档授权。没有产品 archive executor，不伪造确定性拦截。
主线程19→20 的维护交接不能作为候选 Desktop 验收。

`768fe62` 的 Windows/Python 3.14 缺少 calls.jsonl，以及 `181ad42` 同平台原生观察
测试超过外层 20 秒，根因仍未知。现有测试改善了安全诊断，受控超时确认父/子进程
被清理；未增加运行时超时或跳过判据。b908ded、a5320d8 各九个 CI job 通过。
9a21f40 的 run `34093376292` 九项全通过；
e527e1d 的 run `34083855429` 九项全通过；ae14955 的 run `34087181410`
五项通过、四项取消，不能称其全通过。此结果各绑定原 SHA；后续 SHA
须使用各自检查，较晚 PASS 也不能解释早期失败根因。

原交接详细快照见 `e527e1d:docs/operations/CONTINUATION.md`；更早导航见
`ed94613:docs/operations/CONTINUATION.md`。开发源的观察索引保留原始失败、检查对象、
原始/修复运行时及适用边界，按下一决策所需定点读取。

## 运行与残留

私有证据根：
`C:\Users\15521\.codex\backups\accord-evaluation-20260905T215550Z-8ff0643a`。
本任务主要目录为 `task20-functional-chain-20260907`，每个 episode 都有绑定、
实际输出和哈希保留/清理记录。完成任务临时资源前核对所属根、进程、重解析点和
保留证据，使用已解析的精确路径清理；有意保留的备份和证据不作为残留删除。

现有 Claude 经授权 CC Switch/DeepSeek 路由；不静默替换账号、供应方或模型。
配置文件中的 effort 不等于子进程实际生效。凭证只在内存传递，不输出或写入证据。
真实 provider 与无认证回环合成探针分开记录。

- Python：`C:\Users\15521\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`，
  使用 `-X utf8 -B`；文件显式 UTF-8/LF。
- Codex 冻结版本 0.153.4，SHA256
  `444a3f0008050605cae73cd9b7a2dcac61294062dfaab56dd20430fd6498518b`。
- Claude 冻结版本 2.1.263，
  `C:\Users\15521\AppData\Local\Temp\accord-claude-runtime-263-5yoxqfig\bin\claude.exe`，
  SHA256 `0b35df94c1307004f07b738390bfef8dfca5e9af29aaf6517f305bf086b95b03`。
  该运行时仍供未完成验收使用，禁止当临时残留删除。
- 最近核对共享 Codex config SHA256
  `d5886460301b35fa2ab93ac0fee0c2e34e2b3521c2131c0a53bd8212caf9f557`；
  Claude route config SHA256
  `29992472fa4fb8c1b190296385826525b91ead49e0963f882bc66d778de8482f`。

宿主版本和共享状态是有日期的观察，执行相关动作前只重核受影响项。
