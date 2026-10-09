# Node 运行时兼容性与安装条件研究

日期：2026-10-09。源码绑定：`7dd1b6b097ee746a6273ded69eb73ec778230d26`；对象为 `plugins/yiyuan-accord-codex` 当前开发包（委派输入标识 `20261009113418` / 25 成员）。本报告只研究运行时条件，不授予发布、安装、信任或宿主采用验收。本次未执行测试、安装组件或启动 CLI/AppServer；测试结果与两个本地 Node 版本按主任务提供的观察归属列出。

## 结论与建议

**建议将当前受测的 Node 24 维护版本作为本版推荐运行基线，明确其它主版本尚未验证；不宣称“最低兼容 Node 16.9”或“Node 22.5 起支持”。** API 年代可以排除一部分旧版本，不能证明完整运行路径、文件系统行为、SQLite 锁语义和宿主加载均兼容。CI 当前只选择 Node 24，README 明示最低支持版本尚未确定（[CI L53–57](../../.github/workflows/validate.yml#L53-L57)、[README 中文 L115](../../README.zh-CN.md#L115)）。

可用于安装条件的建议措辞（待 Root 按实际证据采纳）：

> 本版以 Node 24 为受测运行时基线，其它主版本尚未验证。实际宿主进程须能找到并运行 `node`；终端可用或安装目录自带 Node 不等于插件能够使用。普通 Hook 与状态 MCP 不依赖 Python、第三方 npm 包或 SQLite。显式使用可选 SDK recorder 时，还须确认该 Node 提供内建 `node:sqlite.DatabaseSync`，以及本版使用的构造参数、事务与锁等待行为。

“Node 24”是测试和维护选择，不是所有 24.x 补丁版本均已逐一验过的陈述。给定 24.21.0 recorder 观察之外，Root 已用现有桌面捆绑 24.19.0 运行指定 17 项本地回归；本研究只读核对其原始记录。两者不能自动扩大到本包完整测试或默认宿主成功采用。

## 已核源码事实：普通入口

Hook 命令以裸 `node` 启动包内 `.cjs`（[hooks L9、20、31、43、55、66](../../plugins/yiyuan-accord-codex/hooks/hooks.json#L9)）；状态 MCP 同样使用 `command: node`（[.mcp.json L4–6](../../plugins/yiyuan-accord-codex/.mcp.json#L4)）。`accord-hook` 引用 `task-checkpoint`；后者使用 Node 内建模块并预加载包内 `codex-context`；MCP 引用同一 checkpoint。普通入口没有对 recorder 的加载边（[accord-hook L37](../../plugins/yiyuan-accord-codex/runtime/accord-hook.cjs#L37)、[task-checkpoint L5–15](../../plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs#L5)、[native-state-mcp L5–9](../../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs#L5)）。

| 实际使用 | 源码定位 | 官方 API／语言依据 | 结论边界 |
| --- | --- | --- | --- |
| `require('node:…')` | checkpoint L5–8；MCP L5–8 | [CommonJS 文档](https://nodejs.org/api/modules.html#built-in-modules)：`require` 的 `node:` 支持为 16.0.0／14.18.0 | 很老 Node 不能照原样加载；不等于这两个版本兼容全部代码 |
| `Object.hasOwn` | checkpoint L138、266、385 等 | [Node 16.9.0 发布说明](https://nodejs.org/en/blog/release/v16.9.0)：V8 9.3 引入 | 普通状态路径具有这一必要特性；16.9 只是特性界线 |
| `Array.prototype.at(-1)` | [codex-context L164](../../plugins/yiyuan-accord-codex/runtime/codex-context.cjs#L164) | [Node 16.6.0 发布说明](https://nodejs.org/en/blog/release/v16.6.0)：V8 9.2 引入 | 原生 transcript 观察路径实际使用，不是只有测试使用 |
| `crypto.randomUUID()` | [checkpoint L51、116、754](../../plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs#L51) | [crypto 文档](https://nodejs.org/api/crypto.html#cryptorandomuuidoptions)：15.6.0／14.17.0 | 状态临时文件和代际标识使用 |
| `util.TextDecoder('utf-8', {fatal:true})` | [MCP L8、449](../../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs#L449) | [util 文档](https://nodejs.org/api/util.html#class-utiltextdecoder)：8.3.0 起；全局版本 11.0.0 起 | 本代码显式从 util 导入，不依赖全局版本 |
| 文件 flush | [checkpoint L53–60](../../plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs#L53) | [fsyncSync](https://nodejs.org/api/fs.html#fsfsyncsyncfd)：0.1.96 起 | 先写 fd，再显式 fsync，关闭并 rename；没有使用较新的 `writeFileSync(...,{flush:true})` 选项 |
| `realpathSync`／Windows `realpathSync.native` | checkpoint L37；[codex-context L80](../../plugins/yiyuan-accord-codex/runtime/codex-context.cjs#L80) | [fs 文档](https://nodejs.org/api/fs.html#fsrealpathsyncnativepath-options)：普通版本 0.1.31；native 9.2.0 | 安全路径核验仍需在目标 OS/文件系统验证，API 存在不能证明路径语义相同 |
| `lstatSync`、`fstatSync` 的 `{bigint:true}` | [codex-context L151、179、197、208](../../plugins/yiyuan-accord-codex/runtime/codex-context.cjs#L151) | [fs.lstatSync](https://nodejs.org/api/fs.html#fslstatsyncpath-options)／[fs.fstatSync](https://nodejs.org/api/fs.html#fsfstatsyncfd-options)：10.5.0 接受 bigint 选项 | 对文件身份／大小快照使用 BigInt stat；没有因此引入更高主版本依赖 |
| 可选链 `?.`、空值合并 `??` | checkpoint L26、1090、1099 | [Node 14.0.0 发布说明](https://nodejs.org/en/blog/release/v14.0.0)：默认启用 | 不转译的 `.cjs` 必须由能解析这些语法的 Node 加载 |

上述表格是有定位的必要条件清单，不是完整动态兼容性证明。源码还使用常规 Buffer、Map、Set、Promise、对象展开／`Object.fromEntries` 等；没有把它们每个年代的最大值计算成“最低支持版本”。`fsyncSync` 官方语义依赖 OS／设备，checkpoint 自己也保留目录项耐久性、断电保证的验证边界（[checkpoint L1263](../../plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs#L1263)）。

## 已核事实与推断：可选 SDK recorder

SQLite 只在 `openCarrierRecorder` 内调用 `loadDatabaseSync`，且在创建数据库文件前完成模块／导出检查（[recorder L177–185、396–404](../../plugins/yiyuan-accord-codex/runtime/carrier-recorder.cjs#L177)）。缺失模块或 `DatabaseSync` 函数会拒绝为 `SQLITE_UNAVAILABLE`；普通入口不需要预先满足这个可选条件。

| 条件 | 官方事实 | 本项目含义 |
| --- | --- | --- |
| 模块／导出 | [Node 24 SQLite 文档](https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html)：22.5.0 引入；22.13.0／23.4.0 不再要求 `--experimental-sqlite`；24.15.0 升为 release candidate | “免 flag”不等于稳定 API，也不等于本 recorder 已测 |
| 旧 flag | [22.12.0 官方文档](https://nodejs.org/download/release/v22.12.0/docs/api/sqlite.html)：仍要求 `--experimental-sqlite` | 本包普通 Hook／MCP 命令不添加该 flag；SDK 的调用者也不能从包中推定已启用 |
| `allowExtension:false` | [22.12 文档](https://nodejs.org/download/release/v22.12.0/docs/api/sqlite.html#new-databasesynclocation-options) 没有此选项；[22.13 构造文档](https://nodejs.org/download/release/v22.13.0/docs/api/sqlite.html#new-databasesynclocation-options) 已列出；[24 文档扩展 API](https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html#databaseloadextensionpath-entrypoint) 定位扩展加载能力到 22.13.0／23.5.0 | [recorder L404、411、418](../../plugins/yiyuan-accord-codex/runtime/carrier-recorder.cjs#L404) 显式禁用；传入未知选项是否忽略／报错不能代替验证其效果 |
| 构造 `timeout` | [22.16.0 官方文档](https://nodejs.org/download/release/v22.16.0/docs/api/sqlite.html#class-databasesync) 确认 22.16.0 添加；[24 文档](https://nodejs.org/download/release/latest-v24.x/docs/api/sqlite.html#class-databasesync) 确认 24.0.0 添加 | 同三个构造点实际传入；默认 5000ms，上限 30000ms（L16–17、392–394） |
| 后续 PRAGMA | [recorder L304–307、420–421](../../plugins/yiyuan-accord-codex/runtime/carrier-recorder.cjs#L304) | 创建路径设置 WAL/FULL/foreign_keys 后 BEGIN EXCLUSIVE；重开先只读验证，再可写验证，最后才设 FULL／busy_timeout；后设 PRAGMA 不能覆盖前面的构造和验证阶段 |

**推断：** 22.16.0 是 Node 22 线上“本源码所用 SQLite 构造选项已见官方文档”的候选测试起点，不是该包已验证最低版本。22.5.0 或 22.13.0 即使可加载 SQLite，也不足以据此承诺当前 busy timeout 语义；更不能把设置 `PRAGMA busy_timeout` 当成所有此前阶段的等价替代。

SQL 实际使用 `CREATE TABLE … WITHOUT ROWID`、`CHECK`、位置参数 `?`、普通 INSERT/SELECT/UPDATE、`sqlite_master`、`table_info`、`quick_check(1)`，事务为 DEFERRED／IMMEDIATE／EXCLUSIVE，成功 COMMIT、失败 ROLLBACK（[recorder L226–255、303–362、478–490](../../plugins/yiyuan-accord-codex/runtime/carrier-recorder.cjs#L226)）。没有使用 STRICT、RETURNING 或 UPSERT 来提高 SQLite SQL 版本要求。`WITHOUT ROWID` 的官方最低 SQLite 版本是 3.8.2（[SQLite 官方文档](https://www.sqlite.org/withoutrowid.html#compatibility)）；这仍不是最低 Node 版本证明。

IMMEDIATE 在 BEGIN 时争取写事务；WAL 下 EXCLUSIVE 与 IMMEDIATE 等价，锁冲突仍可能 BUSY（[SQLite 事务文档](https://www.sqlite.org/lang_transaction.html#deferred_immediate_and_exclusive_transactions)）。`busy_timeout` 每个连接设置 busy handler；FULL/WAL 的耐久性与文件系统条件不能简化成跨设备保证（[SQLite PRAGMA 文档](https://www.sqlite.org/pragma.html#pragma_busy_timeout)、[synchronous](https://www.sqlite.org/pragma.html#pragma_synchronous)）。本项目以 `updated.changes !== 1` 检查 CAS（L490），以及安全整数 revision（L293），因此 SQL 能执行之外还须测试 JS 值类型和并发结果。

## 项目证据归属

| 证据 | 当前能证明 | 当前不能证明 |
| --- | --- | --- |
| CI 源码 Node 24；Linux/Windows/macOS 维护测试配置，[validate.yml L24–79、100](../../.github/workflows/validate.yml#L24) | 版本线被选择，product 测试会被 discover | 当前 HEAD 云端已 PASS、其它 Node 版本已测、默认宿主都采用 |
| 主任务提供 PATH Node 24.21.0、桌面 bundled Node 24.19.0 | 两个实际版本的本地观察；本研究未重跑版本查询 | 裸 node 必由 bundled Node 提供；24.19.0 全功能通过 |
| Root 在现有 bundled 24.19.0 上的 17 项本地回归；下列原件 | exitCode 0；recorder 11 项及普通 Hook/state/MCP 6 项通过；unittest 耗时 11.433s，外层计时 11.860s；测试仅在子进程 PATH 选择该二进制，记录含 29 个保护文件 changed=[] | 完整测试套件、全部 24.x、旧版本支持或真实宿主采用 |
| 主任务提供上一轮 recorder 11 测试在 24.21.0 通过 | 有特定版本的本地 recorder 测试观察 | 本研究独立复现、当前完整包全套验收或当前 hosted 验收 |
| [test_carrier_recorder L176–219](../../tests/product/test_carrier_recorder.py#L176) | 源码包含 missing-module／missing-export 回归，要求 entryGuidance 非空、入口 SQLite 请求为 0、recorder 两次拒绝且目录字节集合不变 | 模拟缺失不是在所有旧 Node 真实运行；测试定义本身不是已通过记录 |
| Node 16/18/20/22/26 文档 | API 年代、官方维护状态、可规划的候选矩阵 | Accord 本包或任意宿主路径的动态兼容性 |

Root 17 项回归原件：[RUNTIME-CHECK.json](C:/Users/15521/.codex/backups/accord-node-runtime-compatibility-20261009-01/RUNTIME-CHECK.json)、[stderr.txt](C:/Users/15521/.codex/backups/accord-node-runtime-compatibility-20261009-01/stderr.txt)、[sources-before.json](C:/Users/15521/.codex/backups/accord-node-runtime-compatibility-20261009-01/sources-before.json)。本研究已只读核对结果 JSON 的版本、Node SHA-256、测试选择、exitCode、保护集合计数和 changed，以及 stderr 尾部 17 项／OK，并抽读保护输入索引；没有重新执行该测试或独立重算 29 项哈希。Node SHA-256 为 `3602f2bb1a10f2cbab4c36886218a33c1ab3db87290e73b033c46c77147d0237`。Root 应保留这些原件并在当前验收记录绑定本地有限证据；本报告不把记录核对称为独立运行复现。

## 宿主与依赖的联合兼容

2026-10-09按用户补充，在`a8dea65478123ee8ddc9d705b545609af29befcc`基础上核对这一层：前文只回答包内API和有限Node测试，不能单独形成宿主支持结论。应绑定**实际入口及后端版本、所用接口、实际运行时路径/版本、OS/架构、权限和包身份**；宿主应用、扩展和实际后端不能只记一个产品名。

| 运行关系 | 应检查的兼容条件 |
| --- | --- |
| 扩展与宿主共用解释器 | 同时满足宿主声明的运行时范围与扩展实际API要求；运行时由宿主控制时，不擅自替换宿主内部组件 |
| Accord当前Hook/状态MCP独立进程 | 宿主支持相应事件/stdio与消息协议，允许启动命令，并传入可用路径、环境和权限；再核该进程的Node是否满足本包要求。无需让它与宿主内部Node版本号相同 |
| 调用方程序及SDK | 使用哪个SDK就核哪个包的版本要求和后端绑定；Accord当前自有CJS调用适配器没有导入`@openai/codex-sdk`，不能把二者的要求混为一项 |
| 手机等远端控制入口 | Node及本地工具条件属于实际执行主机；控制端另核输入、审批和结果等差异，不要求手机安装同一运行时 |

[官方插件文档](https://developers.openai.com/plugins/build/plugins)要求Hook脚本位于实际执行环境且按当前定义获信任；[Hooks文档](https://learn.chatgpt.com/docs/hooks)描述命令处理器与宿主事件/输入输出约定。这些是宿主连接条件，不能由本地Node单测替代。具体入口的支持声明与实际观察仍按当前项目适用性记录处理，不从通用文档跨入口外推。

一个具体的分层反例：本机`@openai/codex` **0.162.0** 的`package.json`声明`engines.node >=16`，`bin/codex.js`选择平台可执行文件并用`spawn`启动它；这是本次只读核定的npm启动器要求，不是Accord所有组件的Node下界。[官方Codex TypeScript SDK文档](https://learn.chatgpt.com/docs/codex-sdk)另声明Node18+，也不等于Accord可选SQLite路径只需Node18。本机启动器的原始字段与文件hash保存在私有`accord-node-runtime-compatibility-20261009-01/HOST-LAYERS.json`；不将本机样本宣称为所有宿主的统一约束。

因此，Node24仍是当前受测推荐，须与所选宿主的实际条件一起成立；没有宿主统一Node范围的来源时，不猜范围，也不将“未公布”视为不兼容。升级宿主、后端、运行时或包后，只重核受影响的接口和行为，不要求穷举所有版本组合。这是既有环境验收的分层对应，不新增宿主、依赖安装或版本矩阵任务。

## 官方维护状态与待验

截至 2026-10-09，官方发布页列 24 与 22 为 LTS、26 为 Current，20 及更早相关主线 EOL；[官方发布表](https://nodejs.org/en/about/previous-releases) 与 [官方 schedule.json](https://raw.githubusercontent.com/nodejs/Release/main/schedule.json) 给出：24 尚在 Active LTS，2026-10-20 进入 Maintenance、2028-04-30 结束；22 在 Maintenance，2027-04-30 结束；26 计划 2026-10-28 才进入 LTS。故维护选择支持优先 24，但上游支持状态不强制 Accord 同时承诺 22／26。

明确保留的 unknown：更老 Node 全运行路径；Node 24 最早经项目测试的补丁版本；桌面 bundled 24.19.0 的完整包测试（已有指定 17 项有限回归）；当前 HEAD 的云端测试结果；目标宿主 PATH／信任／环境传递；不同 OS／文件系统的锁和耐久性效果。

可证伪下一步（建议，未执行）：若确有 Node 22 支持需求，在隔离维护环境用 22.16.0 与当前受维护 22.x，针对同一包身份运行普通 Hook/checkpoint/context/MCP 和 recorder 测试，并加入双进程持锁场景，分别验证创建、只读预检、可写重开、CAS 的等待上限与错误结果。记录 `process.version`、`process.execPath`、SQLite 版本、OS、命令／flag 和准确包哈希；任何选项被忽略、入口失败、目录意外改动或锁语义不符都反驳扩展支持。通过后才能决定是否增加 CI 和支持条件。若没有这一需求，保持 Node 24 受测基线，按实际宿主另行验证裸 node 的加载与参与即可。

Root采纳范围（2026-10-09）：安装说明采用Node24维护版本作为当前受测推荐，仍不定义最低兼容版本、不排除未来经验证的其它版本。本轮没有更换用户运行时或为旧版本安装另一个Node；后续扩展版本仅在实际需要时进行。

## 前置依赖的安装与维护方案（候选，未采用）

2026-10-09追加；只读研究绑定源码`66e61e74c2afb8463afca5279fb95ecc4f0f1c92`。以下为讨论候选，不是已采用设计、实现授权或新增发布门槛；未安装、下载运行时二进制、启动宿主或验证方案。

**建议分层处理：优先复用正式受支持且实际可调用的运行时；缺失时由健康安装执行者提供隔离、版本固定的便携Node；暂不为“单文件”改造核心。** 用户承担选择与必要授权，执行者承担检查、准备、验证和回退。若用户希望零技术准备，产品需要交付可在零Node环境启动的安装入口，不能只把手动依赖清单变成更长文档。

| 候选路线 | 新手负担／主要代价 | 当前判断 |
| --- | --- | --- |
| 正式宿主管理的运行时 | 最少额外安装；版本由宿主维护，需要稳定调用契约与实际入口证明 | 有正式支持时优先；宿主内部存在Node不等于插件可用 |
| 已有系统Node | 无需重复安装；PATH、版本及实际子进程须核验 | 健康兼容时复用，保护用户项目与系统选择 |
| 隔离便携Node＋原有CJS | 用户无需管理系统Node；产品承担OS/架构包、来源验证、安全更新及启动连接 | 较小改动的低负担候选，先验证宿主如何稳定选中运行时 |
| SEA可执行文件 | 用户免单独安装Node；产品承担运行时及打包、签名、逐平台测试和重建 | 后续候选；不因“单文件”直接采用 |
| npm/npx安装脚本 | 本身需要可工作的执行工具，不能独立填补零Node首启动 | 可作为已有环境的交付方式，不作bootstrap兜底 |

### 原生入口与零Node首启动

[OpenAI官方包装文档](https://developers.openai.com/plugins/build/plugins)提供`onboardingSkill`：安装后运行setup，可在新会话或当前安装会话调用包内Skill；这为低负担引导提供连接。它没有在本次查阅中建立“宿主自动安装Node并稳定提供给Hook/MCP”的承诺，该能力保持unknown。文档另确认npm marketplace来源要求已有npm CLI，下载时不运行lifecycle scripts；Hook须在执行环境存在并经信任审查。当前含Hook插件也受该页所列公开目录资格限制。上述事实只归属于当前官方文档，不以manifest未列某字段推断宿主绝无依赖管理能力。

因此候选setup须能在Accord Hook/MCP未启动时，由独立于Accord自身的健康宿主Agent、OS原生脚本或另行构建的安装器执行。仅增加Node脚本、npm install或npx命令不能解决零Node启动。优先查正式宿主接口；私有应用缓存中的Node路径只能作已观察本机样本，不能写成跨升级稳定的产品契约。当前源码Hook与MCP均用裸`node`，仅把二进制放进目录不会使它自动被采用（[Hook](../../plugins/yiyuan-accord-codex/hooks/hooks.json)、[MCP](../../plugins/yiyuan-accord-codex/.mcp.json)）。需要验证受支持的相对启动器、明确路径或局部环境绑定；不得默认改全局PATH、替换宿主内部Node或要求管理员权限。

首启动准备应与日常Hook执行分开：当前Hook超时为3秒、MCP启动预算为10秒，不能依赖在这些窗口内完成网络下载和依赖安装，也不应每次对话重复探测、下载或启动更新服务。setup首先验证主机、运行时和来源，再按宿主支持的方式激活并回读；如果MCP启动失败会阻断setup Skill，原生引导路线即尚未成立，须由独立安装入口承担。应优先复用现有生命周期职责，只在确有接口差异时增加薄的setup入口，不复制第二套安装管理逻辑。

### 便携交付、SEA与来源

[Node官方下载页](https://nodejs.org/en/download)提供预构建独立二进制入口；这支持候选便携分发，不证明任意目标OS/架构均有官方产物或已适合本产品。在线候选安装器按OS/架构与明确版本获取官方产物；离线候选包预置同一产物和验证材料，避免首启动联网。两者应给用户一个明确的准备结果，不要求新手自己操作密钥工具。[Node官方校验说明](https://github.com/nodejs/node/blob/v24.x/README.md#verifying-binaries)要求先验证发布者签署的`SHASUMS256.txt.asc`，再检查产物哈希；只比较与同一未知下载源一起取得的hash不足以建立来源信任。发布端可承担上游签名核验，客户端验证产品签名的固定manifest与产物哈希；签名与密钥来源需有独立可信引导。

[Node 24 SEA文档](https://nodejs.org/download/release/latest-v24.x/docs/api/single-executable-applications.html)确认免用户单装Node，其本质是将单个CommonJS入口注入Node二进制，当前为Stability 1.1。blob生成与目标Node版本须相同；跨平台构建禁用snapshot/code cache，平台CI覆盖有限。注入后需处理二进制签名，Windows签名可选不等于分发信任充分。默认`require`仅加载内建模块；相对CJS需打包或`createRequire`，assets通过SEA API读取，`__dirname`对应可执行文件目录。由此推断：Accord现有模块、原文资源和路径边界需额外验证；SEA仍携带Node及其安全维护责任，补丁需重建、签名和回归，不能只更新旁置node文件。

[Node 24.21.0官方LICENSE](https://raw.githubusercontent.com/nodejs/node/v24.21.0/LICENSE)包含Node的许可条件及多个第三方组件通知，Node主体要求随复制保留版权与许可声明。候选交付应保留所选准确版本的完整LICENSE/第三方通知，并记录上游URL、版本、平台、原始hash和签名核验、产品封装hash及变更；不能把这些组件重新标成Accord许可。SEA同样需要保留对应材料。本研究未对最终再分发组合作法律结论，也未检查实际归档内的文件组成。

### 依赖更新与回退治理

[Node官方发布工作组](https://github.com/nodejs/Release#release-schedule)区分Active LTS与Maintenance；Maintenance主要接收安全和关键修复，罕见安全修复也可能引入通常属于major的变化。因此候选政策为维护受测Node24线，关注官方安全公告与EOL；按漏洞对实际入口的影响优先处理补丁，不直接追全局latest，也不冻结旧补丁到EOL。主版本迁移单独评估需求与受影响接口。

更新候选流程：确认维护责任方与实际执行位置→选定准确补丁并核来源→隔离回归普通Hook/checkpoint/context/MCP及启用中的可选recorder→真实宿主启动与交互验证→记录兼容组合→切换。只测试受影响组合，已有24.19/24.21有限证据不代未来补丁验收。宿主托管runtime由宿主更新并触发兼容复核；系统Node由其既有管理者维护；产品私有runtime或SEA由产品维护，用户不应被迫追版本。

建议按不可变版本目录并存，保留独立安装执行者与已验证旧包，通过宿主支持的方式切换并核对新进程实际采用；有活动writer时先协调，防止进程占用及新旧消费者混跑。回退还须核checkpoint/state兼容性，不能因旧二进制能启动就覆盖新状态；已知脆弱旧运行时不作无限期回退。恢复、保留与清理遵循已有[lifecycle Skill](../../plugins/yiyuan-accord-codex/skills/manage-plugin-lifecycle/SKILL.md)，其指导不授予本轮安装权限。将本地MCP改成远程服务会改变数据、执行位置与治理边界，不能从依赖问题自动推出该改造。

若采用私有运行时，宜放在明确属于Accord的用户数据目录，以版本身份管理，避免把活动可执行文件放在更新时会被替换的插件缓存里。默认保护系统Node、全局PATH及其它项目；用户已有健康环境可以复用，但不能只因版本号合适就借用不可稳定调用的私有路径。更新何时自动执行须服从用户已选择的策略和授权，不能由“首次同意安装”无限扩张；升级权限、来源或数据范围改变时需新决定。卸载与旧版本清理只处理归属明确且无活跃使用的Accord组件，任务数据/恢复材料按保留决定处理，不清理用户已有Node。

新手体验的目标是不用识别依赖名、选择Node版本或修环境变量；必要的安装、信任或组织授权仍由用户掌控。由产品/执行者自动完成平台选择、来源校验、局部准备、宿主连接和功能自检，集中说明确需人处理的事项；不能承诺所有宿主上零弹窗。评价同时看必要人工步骤、失败可恢复性、首用成功、下载/存储/启动成本及后续维护负担，而不是只看安装命令有多短。

### 最小可证伪验证（建议，未执行）

1. 在无Node/npm、无管理员的干净用户环境，setup仍可启动并在准备后实际驱动Hook与stdio MCP；须先核缺运行时/MCP不可用时setup是否仍能调用、新会话与会话内安装两个入口。若只能提示用户运行npx/修PATH，零准备目标未达成。若选择提供离线发行，再分别验证对应离线路径，不将所有候选形态自动列为3.3必过项。
2. 与用户已有不同Node并存；验证系统Node/PATH、用户项目与宿主内部文件未变，真实插件进程采用指定版本。空格路径、非ASCII路径与目标OS/架构各按实际支持范围检查。
3. 损坏产物、错误架构、下载中断与签名不符须在启用前拒绝；原健康安装保持可用。验证源材料、许可通知及版本记录完整。
4. 切换后分别核新Hook、现有/新MCP消费者与有限功能回归；回退在模拟失败及活动进程占用时保持已知状态，不能只看installer exitCode。
5. 若选择SEA，再核内嵌原文与模块路径、安全边界、OS签名及Node安全补丁重建成本；若宿主升级改变runtime连接，则正式托管优先路线被反驳，转向经过验证的隔离路线。

建议3.3先解决已声明入口上的实际首次安装闭环，优先验证原生setup与薄安装准备；不先承诺全平台通用安装器、离线包或SEA。验证结果决定所需最小形态，这些备选不会自动扩大当前发布范围。

## 后续采用与有限验证（2026-10-09）

用户同意上述轻量路线，并明确不默认携带全部第三方工具或依赖。前文“候选、未采用/未执行”保留提出时状态；本节记录后续的有限采用，不能倒写为前文测试已通过。源码候选151947以官方`extensions.com.openai.onboardingSkill`复用现有生命周期Skill，加入前置检查、可靠runtime复用、最小授权准备和真实采用核验；仍25成员/5Skills，不新增运行时或服务。维护方承担版本兼容、来源、升级/恢复责任；用户保留必要决定，具体依赖按任务发现。离线包/SEA未选为本版默认方案。

Root先以CLI0.162读取四个未安装本地marketplace变体（原版/有效setup/禁用目标/缺失目标），均返回onboardingSkill=null。该共同未安装条件不足以证明安装后的禁用和缺目标行为。随后按用户同意的最小验证，在全新任务自有profile仅一次安装151947：原生plugin/read由installed=false/null变为installed=true/enabled=true和正确setup Skill；25个缓存成员逐字节匹配源候选050e45a6。返回的Skill路径是marketplace来源，不是已观察的缓存内模型调用。

被测App Server的PATH仅System32；runner在启动前拒绝发现node，现有Job helper直接转交env，App Server继承它。观察器本身通过绝对路径运行Node，因此这不等于无Node干净机器验收。两次均0模型、未授Hook信任、原生exit0/Job0，分别7/6个raw响应与结构回执一致；原流还有remoteControl通知，不能以未采集的events空数组推断无通知。67/93运行文件留存后，各4个自有运行目录已清理；主用户安装与配置未改。

后一次binding继承的businessForbidden列表误留plugin/install，和明确的一次隔离安装authority/请求链不一致。原binding与实际安装回执保留，另记RECONCILIATION；这是前绑文本纠偏，不能称该次没有安装。后续派发核对声明与真实方法相符，不重跑本次。原件位于私有backups下accord-onboarding-preview-20261009-01和accord-onboarding-installed-preview-20261009-01。

下一有效缺口是实际健康宿主能进入setup并完成必要运行时与Hook/MCP连接，不是再读取同一metadata。当前裸node启动方式未改变；仅放入私有二进制不能证明宿主会采用。完整零准备体验、更新回退和用户负担仍待实证。本次不增加scope/case，不改变全部F/A或旧失败，产品功能/候选状态仍false。
