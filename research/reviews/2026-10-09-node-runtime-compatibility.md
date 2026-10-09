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
