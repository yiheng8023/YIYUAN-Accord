# 3.3.4 节点：宿主演进与现有资产核查

观察日：2026-10-30；源码起点 `6d3314af8734927fedfcbb1ba254a84fb5f013f1`；发行主体 `e58f016a05a242da429bb766da5b8b2bb75e4ca8`。这是后续改进的事实基线与适用性判断，不是新发行、全部宿主兼容或价值验收。

## 结论与核查顺序

先核宿主变化、实际载体及资产消费者，再决定有限重塑。当前源码关系审阅和两对合成任务试行均有用，但不足以替代这项前置核查。“动态适应”应复用可发现、可核验的稳定能力；依赖发生实质变化时，适配层仍要随之调整。没有一种静态提示词或接口能保证适应所有未来变化。

从用户给定的2026-06-21节点开始，读取官方日志、发布说明和当前协议；将每项变化对应到载体版本、实际启用条件、Accord资产、消费者及证据。区分保留、调整、替换、退役、补证；有明确问题和验证路径后才实施。当前重点是巩固与持续迭代，扩张不成为默认目标，也不预设未来版本号。

## 官方变化及其影响

### 2026-11-02 原生工具完成事件的生命周期字段

本地CLI0.166.0固定响应集成在第一次handoff派发拒绝item层`startedAtMs`／`completedAtMs`；原HEAD完整副本与包实现一致，确认严格白名单存在兼容缺口。原3/11响应失败保留，不归咎于模型或新转发入口。官方固定提交`6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`的[ThreadItem序列化](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L234)展平payload并声明两个可缺省的`Option<i64>`字段；[完成事件](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server-protocol/src/protocol/v2/item.rs#L1501)的item使用该类型。仅查看payload schema会漏掉外层展平字段，不能把其中没有声明当作实际事件不携带。

当前最小修正只接受这两个附带字段的缺省/null及JS整数投影，未知字段仍拒绝；保留调用身份、参数、输出、成功终态与事件顺序检查。JS数字已不能还原边界附近的原始整数文本，时间元数据不作为身份、授权或排序依据。修正涉及分发代码；当前测试、原生验证及发布状态以[接续](../../docs/operations/CONTINUATION.md#目标与当前写者)为准，固定源码不等于所有二进制或宿主均已验收。

### 前置日志盘点

本次官方[主日志](https://learn.chatgpt.com/docs/changelog)正文提取109条，条目日期06-22至10-27。另读带日期周报、具体GitHub release及当前文档。没有穷举每个alpha/rc、IDE独立版本、平台build或网页部署；边缘日期无条目不证明无变化。历史网页是本次可获取的版本，不冒充发布当天不可变快照。下表只选会改变本项目判断的变化；右列是核查方向，不是已确认缺陷。

| 日期与来源 | 已记录变化 | Accord相关依赖与判断 |
|---|---|---|
| [06-18 / CLI 0.141](https://github.com/openai/codex/releases/tag/rust-v0.141.0) | 区间前置版本已有远端relay、执行器插件及Hook信任修正 | 作为起点线索；不证明06-21本机已安装或启用。 |
| [07-09 / Desktop](https://learn.chatgpt.com/docs/changelog#codex-2026-07-09-app) | Codex并入ChatGPT桌面，视图并存 | 产品外壳、协调端、执行端分别识别。 |
| [07-21 / CLI 0.145](https://github.com/openai/codex/releases/tag/rust-v0.145.0) | opt-in多代理支持模型、effort及角色恢复 | 核实际委派接口和采用值；不固定继承Root或宣称每个载体均支持。 |
| [08-07 / CLI 0.147](https://github.com/openai/codex/releases/tag/rust-v0.147.0) | 可移植插件及目录发现演进 | manifest、来源、安装、可见与采用各自验证。 |
| [08-18 / CLI 0.148](https://github.com/openai/codex/releases/tag/rust-v0.148.0)、[08-26 / 0.150](https://github.com/openai/codex/releases/tag/rust-v0.150.0) | async/MCP Hook、Interrupt及原生任务操作 | 对照现有6项Hook注册（5类事件）与状态调用者；存在新事件不等于应当注册。 |
| [09-03 / CLI 0.153](https://github.com/openai/codex/releases/tag/rust-v0.153.0) | 上下文管理和异步提问有实验/账户门控 | 压缩、同任务上下文更新、fresh task和fork不能混称；核实际工具暴露。 |
| [09-09 / CLI 0.154](https://github.com/openai/codex/releases/tag/rust-v0.154.0) | 外部插件更新/回退刷新session；其它App打开活动聊天只读 | 沿实际加载核验复用刷新；保留单写者，不默认要求重开聊天。 |
| [09-17 / CLI 0.155](https://github.com/openai/codex/releases/tag/rust-v0.155.0) | daemon恢复线程/Goal；Python SDK发布与runtime对齐 | 核SDK绑定二进制；已接收输入与已执行效果分开。 |
| [09-28—10-02 / 周报](https://learn.chatgpt.com/docs/whats-new/september-28-october-2-2026) | Work Cloud可协同本地计算机；插件与共享任务持续演进 | 本地执行不是本地协调的证据；不能把旧Work-local范围自动延伸到新组合。 |
| [10-15 / CLI 0.163](https://github.com/openai/codex/releases/tag/rust-v0.163.0)、[10-23 / 0.164](https://github.com/openai/codex/releases/tag/rust-v0.164.0) | 即时steering、中断、恢复与压缩修正 | 重核输入来源、控制状态、后台效果和权限；不凭新版本号删除补偿机制。 |
| [10-27 / CLI 0.165](https://github.com/openai/codex/releases/tag/rust-v0.165.0) | fresh profile默认memory v2、对话内effort、实验attached forks | 对照要绑定记忆、模型和上下文；新profile与既有profile不自动等价。 |

当前[Work说明](https://learn.chatgpt.com/docs/get-started-with-work#continue-work-across-devices)明确区分云端协调和本机执行，已有任务不自动转换，离线后的云执行也有新turn等条件。当前[插件说明](https://learn.chatgpt.com/docs/plugins#use-plugins-from-a-supported-surface)中IDE原生插件、云编排Work Hook的限制，按[用户指南](../../docs/user-guide.md#当前入口与运行条件)适用，不能由旧CLI/SDK观察替代。

当前[Hook说明](https://learn.chatgpt.com/docs/hooks#common-input-fields)明确transcript格式不是稳定接口。这与现有`codex-context.cjs`、`task-checkpoint.cjs`的输入读取直接相关：应以支持的结构化来源为优先候选，但替换必须保留原始输入、身份、暂停、未知效果和最终写入校验。格式风险不等于当前守卫应删除。

## 当前实际载体

以下为本机2026-10-30的有限观察，版本声明、磁盘文件和活动进程分开；不是完整入口验收。

| 载体 | 身份 | 当前证据限制 |
|---|---|---|
| Windows Desktop | 产品26.1023.51421，build22530，prod；Appx26.1023.6621.0 | 包清单及一次官方渠道查询一致；不混用产品、Appx与后端版本。 |
| Desktop后端 | 0.165.0-alpha.1.2；SHA `0c09e45bc76433756eb2d492f6db0ce6f269967e6618f4a6ae73e2fa239694b8` | 包内/提取文件一致，3个活动codex进程使用该路径；当前原生调用也报告该版本，具体连接PID未核。 |
| 独立npm CLI | 0.165.0；SHA `d4b2e6a054ea1dfe53217f9d8942c5f8a9f4b76171a1e0bb76ced5759915300a` | 两对试行使用此主体，不是Desktop alpha。 |
| VS Code / Codex扩展 | 1.143.1 stable / 26.1021.22027 | 已安装；本次未观察Code进程，不证明扩展加载。 |
| IDE内置后端 | 0.164.0-alpha.11.1；SHA `4fd2f057bad603bf53dc202457ffd0c3591de62e867a8b01e73816e3fbce5a73` | 内置文件存在；有效配置覆盖、当前执行和插件行为未验。 |
| SDK/观察器 | 由调用方绑定具体后端 | 当前CI起点0.154、替换0.156；本机试行0.165。App Server观察器不是独立SDK安装证明。 |
| Work / Remote | 本轮未新建或切换这些路线 | 协调位置、执行器、连接、实际加载与Hook参与逐项待证，不从本机工具或界面名称推定。 |

当前Accord MCP响应器实际报告3.3.4，来源为本机3.3.4包；这是该响应器观测，不证明所有Hook或未打开入口已采用。发行包30成员相对e58无差分；本轮未安装、更新信任或修改全局配置。

### 2026-11-02 结构化来源与剩余耦合

本节是后续有限观察，以上2026-10-30主体保持。实际执行文件分别回读为npm CLI `0.166.0`（SHA256 `9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`）及Desktop包内后端`0.166.0-alpha.5.1`（SHA256 `3097c909fb6d5cd63510d44aceb1d42df9f6e85722a3e447e477def1ecf60e16`），后者所在Appx为`26.1027.3384.0`。当前原生调用报告同一后端版本，但未绑定其连接PID；版本一致不代入口验收。

分别执行两文件的`app-server generate-json-schema`，默认／包含实验字段各一组，四命令均exit0。CLI输出321／467文件，Desktop输出320／466文件；同模式下选定的7个v2 schema（read、turns/items分页的参数与响应、tokenUsage通知）逐字相同，未据此判断整个协议相同。`--experimental`仅扩大生成内容，没有启用运行特性；未启动App Server、读取真实聊天或调用模型。

官方[Hook说明](https://learn.chatgpt.com/docs/hooks#common-input-fields)仍将transcript格式列为不稳定接口；[App Server说明](https://learn.chatgpt.com/docs/app-server#threads)提供独立读取与分页接口。所查schema保留`includeTurns`，但对分页线程不宜把整段hydration视为未来稳定替代；`Turn.itemsView=full`仅描述该turn持久items，不能代完整线程、输入来源或授权。`Thread.sessionId`为会话树身份，不能一概当作`Thread.id`。含实验字段的`readState`是未读位置／修订信息，不是容量或输入完整性证明。

| 职责 | 当前实际消费者 | 可替代边界 |
|---|---|---|
| 容量与新鲜度 | checkpoint的`observeContext`及connection/session回调；普通MCP另调用rollout reader | 已有同连接通知路径消费`last`、可选window和模型／压缩事件。`total`不当占用；普通MCP没有等价的完整事件流输入，不能仅凭schema存在迁移。 |
| 输入与控制完整性 | `scanNativeInputs`、分页取回／对账及bind／pause／retire前后检查 | 原文和媒体coverage、Hook／行hash、来源注解、字节前缀和未知控制须保留；结构化当前turn结果不等价。 |
| 执行关联与恢复 | turn关联、目标读回及独立verifier | root／parent／trigger关系、原写者停止、暂停和未知效果分别核验；容量、idle或notLoaded都不提供这些结论。 |

所查四份通知schema均声明标准`item/completed + functionCallOutput`，未在其通知集合列出`rawResponseItem/completed`；这不证明宿主永不发送额外事件。原remaining正例主要构造旧原始形状，产品已有标准decoder。本轮补2项标准通知回归：第三方namespace不冒充核心容量来源，后续可见item、新usage或unknown输出不沿用旧remaining；保持响应边界占用、效率未知及不授予release。补审发现fixture遗漏必填`completedAtMs`，补齐后核对四schema的必要字段与标量类型，并以缺字段反例校准；不是通用schema符合性评价。相关10项checkpoint检查与完整26项connection检查共36项成功，原先的字段投影结果另保留。固定输出文案不是schema保证，也未观察真实宿主发送。

`error.willRetry`及`thread/environment/disconnected`仍需其实际语义证据；环境断开不等于传输EOF，当前未据此新设拒绝条件。下一步若普通MCP能取得无需新接管的同聊天通知流，再核连接／turn／model／压缩代际、journal淘汰、时间及断连；此前保留已受守卫的rollout路径，复用现有SDK路径，不新增常驻桥接服务。

## 资产、消费者与初步处置

起点224个跟踪文件；以下计数用于定位，不表示完备性或有效性。私有运行证据、安装缓存、NEXUS不计入该总数。新增本报告后为225文件；首项兼容修正、3.3.5发行及安装阶段的宿主变化见[当前接续](../../docs/operations/CONTINUATION.md#目标与当前写者)，不把原盘点改写为225份逐行全审。

| 资产 | 当前消费者/依赖 | 初步处置 |
|---|---|---|
| 通用契约、F/A判据、机器投影 | 开发校验、准入、审查及维护CLI | 保留必要结果与历史身份；校准当前宿主适用性，机器投影不成为独立用户决策。 |
| 插件包30成员：Skills、Hooks、MCP及适配实现 | 宿主插件发现、Hook进程、MCP调用；可选外部控制者 | 保留已发行字节，优先核输入格式与实际入口变化；新能力不自动启用。 |
| 仓库runtime8文件 | 测试/开发调用与包内对应实现 | 2个薄facade、6个完整重复实现有现存调用者及一致性守卫；列为维护成本候选，不能直接删除。 |
| Python产品模块12、脚本8 | 开发校验/准入、观察器、生命周期与独立来源消费 | 分清开发工具与用户运行依赖；按已绑定源码和后端复用证据。 |
| 测试34、案例文件28、eval历史记录42 | 单元/静态/原生固定响应、资格与历史审阅 | 保存原失败和原对象；CI旧后端覆盖不变成当前所有宿主覆盖。 |
| 对照协议、材料、判分与私有试行 | 开发评价和有界语义复核 | 两对结果复用；补代表性与完整成本前，不推广收益或重跑已闭业务。 |
| README/指南、PLAN/BASELINE/ACCEPTANCE/CONT、更新日志 | 用户、贡献者、开发接续及部分机器消费者 | 更新受影响视图；应用任务不要求维护开发接续页，后者不替代运行状态。 |
| NEXUS品牌、传播清单和旧媒体 | 独立传播资产及其发布/撤回记录 | 原3.2.1已发布推广视频已撤回；源资产、发布历史与产品发行保留。旧候选许可不授予重发，新传播按当前事实准备并另核发布授权。 |

### 2026-11-02 根runtime的有限处置

上表的2个facade／6份完整副本保留2026-10-30盘点身份。`d9c5d103`已将recorder转发，成为3个facade／5份完整副本；本轮逐份追查这些副本的实际入口、相对依赖、独立执行快照和源码约束，给出以下处置，不要求全部改写。

| 根入口 | 本轮处置 | 依据与后续重开条件 |
|---|---|---|
| `accord-hook.cjs`（4,201字节） | 保留完整实现 | 是读取stdin并注册事件的直接命令。可设计转发，但本轮节省有限且需重验入口与历史包；没有必须迁移的已证问题。 |
| `task-checkpoint.cjs`（132,985字节） | 保留完整实现 | 同时作为库和CLI；`require.main`控制CLI，未导出main，且指导和帮助引用自身目录／文件。普通require转发不能保持该入口。 |
| `carrier-handoff.cjs`（121,508字节） | 根入口改为202字节精确转发 | 包实现只依赖Node内置库，无相对文件、目录或CLI入口语义。保留包内原实现，减少121,306字节重复维护；源码守卫仍要求原完整副本或精确摘要与目标的转发文本。 |
| `codex-connection.cjs`（23,928字节） | 本轮保留完整实现 | 转发会将相对加载的checkpoint迁到包内，须共同补齐其依赖和冻结快照；与纯handoff库不是同等小的变更。有实际维护负担或明确替代设计时再评估。 |
| `codex-session.cjs`（58,999字节） | 本轮保留完整实现 | 依赖handoff和connection；整项转发会改变这条依赖链的加载位置，涉及包内session、handoff、connection、checkpoint、context。后续按这组依赖整体判断，不单改一行。 |

独立分发仍以30成员插件包为主体，包不反向依赖仓库根入口。handoff改动同步了当前固定响应执行／退役恢复快照及session快照的包实现来源，增加独立两文件加载、缺件拒绝和转发篡改检查。当前源码集合的要求不用于改签旧快照；旧证据保留其原来源及绑定核验器身份；当前恢复器不自动执行旧核验器，也不静默补缺。适用验证和精确后态见[接续](../../docs/operations/CONTINUATION.md#目标与当前写者)。

本轮后态是4个facade／4份完整副本。收益限定为仓库重复维护量减少；独立执行快照仍需携带实现，不能宣称同量制品缩小、执行加速或任务效果提升。其余四项已有本轮保留决定，只有新事实影响上述依据时再重开，不作为必须持续删减的开放待办。

## 下一轮有界工作及复验条件

1. **先核会话来源兼容。** 当前Goal自动续轮曾报告`native-call-turn-conflict`，后续输入检查报告`native-input-origin-unavailable`。已有检查点保留、未重放或放宽身份校验。冻结最小原始来源与实际调用顺序，再判断宿主格式变化、错误推断或真实身份冲突；有区分反例后才修适配。
2. **修正当前支持与复用表述。** 用协调端/执行端/交互端、具体版本与加载条件取代单一Work或IDE标签。当前未核入口保持未知；不因此自动撤销历史精确资格或增加云端承诺。
3. **比较宿主已有能力与现有组件职责。** 先追原生Goal/任务/模型配置/上下文/插件刷新及Accord真实调用者，再决定保留、简化或替换。根runtime重复仅是候选；删除前必须核消费者迁移、包独立可用、验证和回退。
4. **沿证据设计下一组对照。** 先解决会影响组间公平和实际能力的适配问题；同时衡量软件工程质量、用户负担及完整成本。两对小样本不为整个项目代验。

Goal正文修订已准备；通过公开App Server接口读取同一活动Goal成功，原位写入被宿主以“已有活动写者”拒绝，读回原正文与active状态未变。未接管、未另建Goal、未重置用量。当前细化目标以[计划](../../docs/operations/PLAN-v3.3.md#当前目标细化)及最新用户输入承接；这个限制与Accord检查点的来源兼容问题分别诊断。

## 证据留存与未决

官方正文、109条索引、载体摘要、资产消费者明细和Goal操作前后记录私有保存在`.tmp/host-asset-baseline-20261030-01/`，不发布原生对话或用户路径。主日志本次缓存SHA为`ca0f90b1eae95019887e74faf55a82388c030fc1b5b924e843dac790d177a30d`。独立研究、载体与资产盘点由不同审阅者完成，Root负责交叉核对和共享文件唯一写入。

仍缺IDE独立版本史、所有预发行/平台部署历史以及Work/Remote当前执行证据；按实际依赖继续补核，不能宣称全覆盖。旧#1033失败和#1034后继CI各保主体，终态见[接续](../../docs/operations/CONTINUATION.md#目标与当前写者)。CI全绿也只关闭对应工程核验，不结束本轮宿主与资产演进责任。本报告本身不授予发行、目录提交、传播或新信任权限。


## 2026-10-31 后续补核：实际载体与历史接口

本节补充10-30快照，保留上文原载体身份。本机独立CLI现为0.166.0，二进制SHA256 `9d563ee4e0441ff9d59d612013e0460ddf8e5709735c2d9f6b98b7ef8ca4eb42`；本聊天原生MCP调用报告hostVersion为0.166.0-alpha.5.1，实际加载Accord338。该调用元数据不单独证明协调位置，或全部Desktop文件、IDE、Work等入口均已更新。

上游约定补核（2026-10-31）：固定官方0.166 tag所指commit `6ff1e1ca`的[完整读取兼容实现](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server/src/request_processors/thread_processor.rs#L3185-L3218)与[分页展开](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/app-server/src/request_processors/thread_processor.rs#L3540-L3608)表明，includeTurns=true仍展开turn与item页至nextCursor结束；paginated会发弃用提醒，并非该版本已移除完整读取。两份公开类型与本机二进制生成的ThreadReadParams/Turn逐字节相同，实机单turn的76item与5页回读一致；这支持继续复用该兼容接口，不据此新增一套分页组件。两个类型相同不是完整binary构建证明；多turn、变化中一致性及其它载体运行验收仍保持其实际范围。

本次直接原生读/页操作只针对已完成的自有研究线程，未启动模型、resume、interrupt或重放业务；接口读可能维护宿主的历史投影，不能笼统等同于磁盘零写。已有恢复仍保身份、原文、暂停、未知效果及独立验证。源码契约、实机单样本、当前候选b2b3的本地工程检查和应用验收各自保其身份；没有以该源码补核升级正式安装或扩展宿主范围。

现有读取器补核（2026-10-31）：固定读关闭追加时，旧token_count允许有限重读，而实际0.166的token_usage_record与命令型item_completed会得到未知，随后稳定读取又正常。独立复现仅支持这个两形状的覆盖缺口；已接入严格同身份、同turn、完整封套/终态的小修正，保持原前缀及真实用户、暂停、压缩、未知控制拒绝。与应用中一次正确cursor后的实时证据变化成因分别保留；不因空待核列表推断未知来源已就绪，也不自动忽略已识别的页面元数据。两条现有Skill分别补完整cursor/unknown分支与人类操作前的控制交还；未发布工作包b0645f44已完成518项适用回归及三静态（原213项代码字节不变复用、新305项整套分批），首次整套300秒超时保留；当前3.3.9元数据候选继续精确核验，正式安装338未变。应用现场的原失败与人工介入见[评价记录](../evaluations/accord-toggle-v1.md#2026-10-31-真实未完应用的安全接续观察)，不将普通续作改签完整原生恢复。
