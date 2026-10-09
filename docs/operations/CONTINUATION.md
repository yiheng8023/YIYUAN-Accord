# 当前接续

更新：2026-10-09 · N33-20260909 / r39。本页只保存当前事实、权限、未完责任与下一依赖。[计划](PLAN-v3.3.md)拥有共识与工序；[基线](BASELINE-v3.3.md)、[验收](ACCEPTANCE-v3.3.md)和[机器投影](../../product/development.json)各保原职责。实时仓库、原生输入与资源事实优先。

## 当前动作

2026-10-09 [GT-11/GT-12合成事件汇总修复](../../product/cases/adaptive-event-summary-v3.3.json)已实际结束：同一Sol/medium/default worker两阶段各通过独立40项检查，按新seq规则将样例23修为19并纠正报告；快捷入口撤回后使用剩余合法入口，真实Job内存160→96MiB、CPU10%/8活跃进程限制及两次自然Job0/句柄关闭均已核。四次Goal为null，230项保护材料/dirty notes保持。原实例not-admitted：交付/最后只读检查在345.675/355.281秒，原生终态363.837超过共享worker360；Root阶段间调度消耗共同窗口，不能归因worker独占耗时。Root约379.6秒完成机械检查及源码/报告读取，609秒保存完整材料判断；该保存时间不能证明此前所有语义判断均超时，完整语义QA在600内仍未充分证实。有效软件/纠正/资源事实保留，不追认或重跑；两条结束实例保cbd精确定义后转历史，17范围/13case/7声明缺口/5无case保持。现装及原限额不变。

新增两条合法声明曾使a3/cbd CI的旧硬编码缺口计数失败（9快速门失败、2native lifecycle成功）；已修测试夹具：当前诊断独立按source计算完整缺口，固定反例明确构造无资源/环境case基线，新13/15布局回归仍保持0accepted及功能/候选false。标准与产品准入器未降低；原CI失败保留，修正提交的托管结果另核。

2026-10-09资源监督器实测：既有772aaa宽限候选在全新自有Windows进程夹具中取得三项有限事实：正常worker85后尾进程自然退出（2.331秒/Job0）；原10秒恢复截止后一次terminate（10.997秒/tool124/Job0）；显式查询故障保null/75/unknown，独立进程句柄另证退出，不回填原记录。原整轮仍not-admitted：外层在driver0后立即强退残余，且原PLAN限额2进程/场景、实际各4；不能将限额事后改称估计。14.796秒后外层Job0、句柄失效，源/配置不变，额外PID角色unknown。外层最小派生5纯回归通过，并在另一次独立外层专项验证中，预先设置/回读8活跃进程上限和160MiB，实际4进程、2.300秒自然退出/Job0/句柄失效。未重跑内层三场景、旧业务或模型；原失败保留。这关闭了监督器宽限从mock到有限真实OS观察的工具缺口，不代完整R2/R3或正式资源/环境验收。原件与判定见私有accord-job-grace-native-20261009-01及outer-regression。

2026-10-09隔离方案核对已结束：不实施“startup时自动接受旧工作区标记”的候选。固定官方0.161.0源码有先UserPromptSubmit失败、随后才运行pending startup的路径，可能只有匿名workspace水印；该方案会掩盖同任务刚丢失的指令。已用真实helper的无效传输→延后startup→新输入顺序补回归，连同原逐会话恢复、暂停/中断和变化水印4项通过；独立源审查确认反例。已有token-bound恢复可仅处理对应会话并保其它任务，当前已结束只读probe及旧v2仍不重放。该水印原归属未知没有消失，但不是继续泛查IDE入口或新建自动初始化机制的理由；下一在确需状态恢复的实际任务中按原生完整输入/权限和当前token使用既有路径，独立主线不依赖清除此旧标记。产品运行包与现装未改。

2026-10-09真实IDE回读：用户在新空白对话完成一次限定只读核验。实际扩展26.1007.21434的后端为0.162.0-alpha.17.2；原生记录确认vscode来源、Sol/medium、完整入口指导和输入notice在首工具前到达，一次accord-state.inspect_task_state成功并与实际thread/turn/输入epoch对应。新指令全文及SHA已保全，但回执为quarantined-native-input、needsNativeReplay=true、unbound；原因是继承工作区旧失败水印。该标记只有schema/generation，mtime为9月12日，原归属/原因未知，不能据日期判安全可删。现装与候选状态helper字节相同，已有测试明确要求此隔离行为；只证明当前机制后果，不据此自动放宽恢复条件。原对话23.151秒终态，无状态写入或replay；旧v2和共享标记未动。私有accord-ide-live-20261009-01保原生记录/回执/标记和FACTS。IDE组件连接已有实证，完整恢复及交付仍未验；当前只读探针已结束，不要求用户重复发送。

2026-10-09 CI纠偏已获新托管结果：111b7030 / CI37893087158全部11项成功；a356 / CI37887791818原10成功/1失败保留。原失败仅Windows/Python3.10的source-pump queued用例：收到一次释放回执后最终记录提交unknown。原用例本地0.813秒过；仅延迟最后持久化4300ms即复现同code/stage/终态/单次释放签名。功能夹具不应把磁盘速度当协议断言，现统一20秒source run并由同deadline预留8/6秒给plan/recovery，外层30秒（双交接50秒）；显式4秒短期限反例仍正确失败且不重放，原adoption10ms及普通3秒守卫保持。69项本地会话/连接与独立复审通过；产品运行字节、25成员包、真实案例限额及CI job timeout未变。原CI未保底层持久化耗时，因此只确认并修期限敏感性，不声称已证明平台故障。

2026-10-09入口范围对齐：基线、计划、验收说明和机器说明中残留r37/pending/未定稿已纠正为r38最终选择、r39保持的6selected/3deferred及selectionFinal=true，独立Chat模式均deferred。原日期观察/未知/失败保原；并未完成入口行为验收。当前官方仍不支持IDE插件，Remote复用主机需实际配对/权限，现有manifest仍兼容；不新增格式迁移、Cloud、延期IDE/Chat任务。所有expected字段、9行/modeCatalog/已选集合和17scope/F-A未改，仅澄清延期模式适用性检查不冒运行通过。

R3下一依赖按实际入口差异处理：CLI/Desktop/SDK复用已有子范围证据并核候选变化；VS Code复用本次真实组件/输入捕获与状态读取，必要实际任务的输入恢复与交付仍待验，不再盘点已证连接、重跑探针或继续同一startup豁免调查；Work Local补实际cwd下正确状态联读；Remote补已配对主机上的输入/审批、暂停/撤权及断连后态。当前IDE指令禁止replay/状态写入，不能代旧未知责任消失。共同后端事实可复用，各自UI/权限差异不能省略；没有当前源码/账户/设备依据时保具体unknown，不对已延期入口重复准备。

本次[调用者影响核对](../../product/cases/consumer-impact-v3.3.json)两阶段实际完成（145.077/98.048秒），同一Sol/medium/default任务在私有工具撤回后用只读替代，纳入新增合成调用者并撤回安装建议。原件/配置/190tracked保持、命令与轮次结束已核。原worker把未给定摘要算法错误推成必须提供归档，整案not-admitted；Root另交校正报告并独立复算两侧树摘要，不能追认worker原通过。原checker与helper路径前缀口径不一致，原FAIL保留，派生检查只证定位等价。原case精确定义保6fd67b63和摘要后转历史，不重跑；17scope/13活动case、7声明缺口/5无case保持，数字不是完成率。

2026-10-09关联路径纠偏：730的普通context修复仍漏了交接源/目标和普通owner回复后态。新增五个反例证明原实现会误保最初proposal或清空实际请求；现普通与交接共用接收守卫，先保请求后核变化，各类回复后再核绑定再清pending，失败不重放。AGENTS同步明确复用有效授权、沿受影响调用阶段及过期指引纠偏；不写入案例预算或新增审批。新源码候选`20261009113418`/25成员/`71aea2fe`，主用户现装仍114112/e4c0。这里只证可变借用接口的确定性守卫，不晋完整自主性或组合验收。

2026-10-09前一源码工序（730，关联路径现已补齐）：本轮修复一个确定的连续性接口缺口：普通source run等待请求期间借用连接身份/版本/回调变化，原实现仍先回复context请求，随后才失败且丢失该pending请求。现接收前后核绑定，先保全已消费请求，再决定处理；回复后也核绑定再清请求。四个反例先失败后通过，会话/连接65项测试及独立正反复审通过。只证本地协议与SQLite组合，不外推原生冻结连接曾跨连接响应、模型自主性或完整F05/A05。新源码候选`20261009104813`/25成员/`5989b262`，主用户现装仍`20261008114112`/`e4c0`，没有安装或授信变更。前0e1802ef/CI37869819255已success；当前候选托管检查另核。

[原生新CI比较](../../product/cases/ci-comparison-native-v3.3.json)已真实完成：fresh原生worker约166秒交付新7814条索引、九矩阵比较和报告，独立原文/计算/语义核验通过。原生日志确认0.162.0-alpha.2、Sol/medium/default、Goal前后null、累计usage在限内；自主选读核验Skill并用于结果检查。两路并发在实际160→96MiB、CPU10%条件下均自然结束，所属Job0，首批cache、16业务原件、189主仓tracked文件和配置保持。八矩阵步骤减少18～372秒，Windows/Python3.10增加420秒，不据此宣称因果提速或净收益。

本轮纠正前态判定：07ea冻结CONT已引用114112/e4c0安装报告及25成员实际回读链，同配置和真实原生入口支持其适用，package-before条件充分。没有每轮必须新建快照的标准；SDK02清单仅作既有补充，after-only不充before。整案仍未正式准入：原600秒含必要QA，约260秒的oracle通过/报告读取和598.932秒的机械后验，不充分证明全部语义与原生事实核对在窗口内完成，记未验证而非worker超时。后续额外复审或登记时间本身不构成超时。原两固定声明仍保07ea历史，不重跑已完成比较；future-only采集只是一种充分方法。详见私有ROOT-ADJUDICATION.md和本轮工序纠偏；e2e/CI37835688818已success。

[CI索引02](../../product/cases/ci-timing-index-v3.3-02.json)已一次执行结束：真实0.161.0/Sol-medium/default、Goal前后null、完整入口及当前输入回执已核；约52.259秒、原生自然exit0/Job0，共享配置和主仓原件保持。但shell及备用Node通道在读业务材料前遭遇Windows sandbox setup错误，模型如实保未完成，未生成业务成果；不由原生completed状态晋通过。匹配日志定位到占用中node_repl.exe的ACL更新错误32，以及受保护PCManger授读失败。Root未杀其它会话进程、改ACL或重跑02。

所需维护成果已由Root当前健康本地通道在独立`accord-ci-index-maintenance-20261009-01`完成：9日志/7814条索引，独立原文校验、原件/两首批cache保持均过，中文报告明确单独路线。维护监督器另暴露正常worker退出85后立即强制收尾尚存所属进程的问题；派生宽限修正的7项纯测及后来有限OS事实见本页上方，原业务没有重跑或运行96MiB阶段。Root复用两份已核cache，顺序解析余7份交付，不将它追认SDK或资源/环境验收。独立oracle原“总结与step结束同秒”额外假设已在派生副本修为真实时间范围，7原测+2反例及全数据过；原工具、原oracle、原失败保留。数据/报告/自动校验约398秒，独立语义复审约649秒，整段未达原600秒计划，不声称时限通过。

下一必要方向为收敛这些已知工具/宿主前提并利用健康原生能力推进其它实际职责；不再重复相同SDK实例。02两固定声明保d8988f98后移出活动必过集合，全部父范围/限额保持。Windows错误未解决前不关闭未知用户组件或修改安全配置。

用户确认后，[CI时序索引一次实例](../../product/cases/ci-timing-index-v3.3.json)在模型输入前2.0528秒被Root调用者误拒：把请求中的cwd写根错误要求原样回显。固定0.161.0官方源码把cwd作为隐含写根、从返回的显式writableRoots去除；其余已核控制相符。未发turn/start、0业务输入，无cache或交付物；原配置字节/mtime未变，所属Job强制收尾exit124/active0、reader停止。原失败、授权、源码和回执保持，不追认成功或重跑。

最小纯修正只区分请求与原生返回的期待，仍精确核cwd、唯一额外写根、字段/类型、网络和临时目录；原请求权限不变。原始返回重放、4项回归/11拒绝变体及独立复核通过，尚未在新实例执行。原两次声明共属一个已结束实例，已按既有历史处置保全4fcd63fa精确定义后移出当前必过集合，父职责/限额不变。私有`accord-resource-ci-index-20261008-01/sandbox-diagnosis`保FACTS、固定官方源、patch、测试和REVIEW。下一次必要执行应先采用这份已证修正并重新前绑实际路线，复用未开展业务的原日志/工具，不重开安装、泛查入口或延长旧窗口。

前一提交063585c5的CI37744728055已success。其提速仅复用同一多变异方法内的有界精确历史Git读取，原21次校验和全部断言保持且通过，Git调用6742→2163；第二个整方法候选未通过原断言，已撤回。没有扩上限、弱化判据或据此声称产品净收益。PLAN旧ACK执行待办、Cloud继续方向和普通Chat pending已纠正；当前工作不再重开这些已闭分支。

主用户已按本次明确许可完成候选114112更新。独立后读核实25成员/e4c0包、五个官方CLI自然exit0且所属Job0，24.179秒收口；11份配置阶段记录仅预期市场ref改变，旧包/原配置保全。重开原线程已收到114112恢复指导与简短输入notice，MCP只读调用正常并读到当前新epoch和原13项未完责任。原安装器未验字段保持，后验另记`accord-local-adoption-20261008-01/post-update/ADOPTION-RESULT.md`；本次许可已消费，不重跑。下一步回到必要普通成果、能力/连续性和完整系统验收，不再反复安装或为入口另造空线程探针。

4a464748的CI37724704741终态为9成功、2原生lifecycle失败，暴露了上轮漏改的观测器消费者：Ubuntu/macOS热更新原请求已有新格式回执，检查器却只认旧全文前缀并返回空值。本轮兼容新旧提示，同时保持developer来源、末条回执和精确路径/epoch/暂停/信任核验；新增当前分发Hook输出到检查器的直接回归。复审还修正了persistent入口的旧同条消息假设：完整指导和输入回执可以分处两条当前轮次的Hook消息，但均须在模型活动前到达。相关正反回归及独审通过，原CI失败不追认；修正提交的托管结果已通过，见上段。

已修复重复全文的源码连接：SessionStart/SubagentStart保留完整元指导，UserPromptSubmit只送达输入与状态提示及获准指导定位；指导文件缺失不再连带阻断输入捕获。正常、隔离、暂停、压缩与恢复职责保持，缺失/变化指导仍须在依赖动作前核定。当前原线程已观察到新版入口和状态读取；实际token/时延、所有组件分支及跨入口仍未验，不由本次更新扩大结论。

已有原生正文传递证据已补读：精确0d8 / CI37704527081的Ubuntu与macOS lifecycle原ZIP中，当时源码候选162254的25文件与原安装一致，四执行源对应；真实SessionStart完成事件的完整正文与同thread/turn首条provider请求developer input[2]逐字符相等，分别11100/11106字节，Meta原始4444字节及5118摘要保留。实际CLI0.154.0、loopback固定回复、0真实模型，只证这两个运行中的执行/完整注入/传递；不能代真实模型采用、Windows0.161/其它入口或全F/A。两运行直接子进程自然0、同POSIX组absent，边界不扩。来源：`accord-existing-hook-input-evidence-20261008-01`的原ZIP/FACTS/RESULT，独立原件复核一致；本轮未重跑宿主或模型。

空线程正文核验的错误预期已定位。官方Codex `rust-v0.161.0` / `979011409de0a60b52f179721948e65531d26144` 在会话创建时排队启动Hook，`run_turn` 才在前序条件成立后执行，并关联该实际turn ID。03只创建线程、没有turn/start，还要求事件turnId=null；延长等待不能补足触发条件。固定源码、原请求和独立复核见[来源核对](PROCEDURE-v3.3.md#2026-10-08-sessionstart-source-correction)。五项纯谓词检查已过，包含原谓词拒绝合法轮次形状的对照；不是新原生执行或原实例通过。

下一步集中于真正必要普通成果中的指导采用及剩余功能/影响，复用已证机制传递和已有安装，不再为相同加载事实另造探针。首条模型请求里SessionStart与UserPromptSubmit各带一份全文，该重复已由本次职责拆分修正；实际token、费用或时延改善仍无实测结论。实际模型、信任及其它效果按对应现有权限判断；需要新边界时只呈完整具体方案。原02/03实例已结束，不复跑、补ACK或复制grant/clock。当前源码纠偏、必要维护及普通原生协作仍可推进，普通回合不自动续轮。

本次同时纠正了旧接续页中的待登录、待认证、待安装及旧宿主/CI值。完整前页固定在[7258af8a快照](https://github.com/yiheng8023/YIYUAN-Accord/blob/7258af8a95693ad8c288a07657fd315f818f2b8d/docs/operations/CONTINUATION.md)和私有 `accord-sessionstart-trigger-20261008-01/continuation-before.md`；历史记录不再充当下一动作。

## 当前状态与权限

| 对象 | 已核状态与边界 |
|---|---|
| 发布目标 | 在原检出main完成必要功能、质量、完整验收及精确候选后，按用户既有条件授权发布3.3.0。当前 `functionalCompletion=false`、`candidateEligible=false`，尚无发布资格。传播、市场提交和后续版本不计入本版收官。 |
| 版本与入口 | 源码候选`20261009113418`，25成员，包SHA `71aea2fe68fa34e903991e3015f7fc94ac4e0d9662dcad42d5b4c1affe8044bc`；主用户现装仍`20261008114112`/`e4c0ce9df44857dc5cc665f292342cd631fc87a08b93d9af70e4267d3de1b435`，原线程Hook/MCP采用事实仍归于该旧安装。此次只修可变借用连接守卫，不改变现装或要求立即更新。隔离profile仍`20261006162254`；不以源码修正冒所有组件/入口验收。 |
| 宿主与模型 | 最新原线程MCP：Astra / `0.162.0-alpha.2` / default；主模型由用户切换，effort/Fast未独立核定。隔离原实例使用CLI `0.161.0`，临时线程配置Sol/medium但0模型轮次；配置不等于模型已执行。子代理按任务选择，用户启停/选择始终保留，不设固定模型或档位梯子。 |
| 元指导与代码 | 原文4444个CRLF字节，SHA `511861ec00a15e051c97221d9d62e9586856a5d659724eff2d2953f002f457bc`。入口Hook、主协调正文与原文未改；现装状态helper已作输入提示分工修正，变化的能力协调/生命周期Skill正文已从当前安装路径读取。可见与读取不证明其所有业务分支已验。 |
| Stop与长程 | 自动续轮、Stop注册及其预算已退休；旧callback仅防误识别。未完责任、恢复和交接保持；普通继续不启Plan/Goal，长程控制只按用户明确选择。 |
| CI | 最新d13c08bd / CI37902406821已11/11成功；前111b / CI37893087158亦11/11成功，a356原10成功/1失败保留。实际安装仍固定35b源码及其已过CI，不随后续记录提交漂移。有效在途CI不因普通聊天或低价值推送取消，不重复轮询已闭矩阵。 |

- Root负责main整合，保留唯一活动分支及无关改动。必要实现、修复、检查、commit/push和既有订阅下的普通原生委派已授权，不因换任务名或旧实例许可消费就重复请示同一实际范围。
- 安装/新信任、账户或数据接入、重要费用、超范围共享/外部写入、用户线程归档仍保对应明确权限。不得恢复过期窗口、复制旧grant或以新判据追认失败；完整方案完成后才处理真正的新边界。
- 3.3仅承诺用户最终选定的六条OpenAI执行/控制路线及现选模式，`selectionFinal=true`。普通Chat独立模式、网页聚合、JetBrains/Xcode内置集成本版延期、能力未知。插件使用许可、启用、必要信任及实际加载须分开核；子代理并非用户必开前提。
- Cloud当前适配及相关工序已取消；两个不可删除账户草稿按用户决定留置，不再调查。3.3后可能先有维护小版本，3.4五宿主仅为待讨论候选。

## 有效结果与保留的失败

| 已闭部分 | 可复用事实与明确限制 |
|---|---|
| 隔离认证 | 原owner成功登录，匹配loginId、227.593秒内返回、Job0；原390秒整案因Root延迟未闭，保持失败。后来独立新进程只读确认chatgpt/file认证、2.530秒自然退出/Job0，补足持久性事实。无需重新登录。 |
| 隔离安装02 | 官方本地市场登记及安装成功，缓存25文件逐项匹配，发现5Skills/6Hooks；检查器误拒原生sha256标签，整案held。14.390秒内native自然0/owner1/未强杀/Job0；没有信任、线程或模型效果。 |
| 剩余入口03 | 未重装；实际仅主SessionStart、SessionEnd trusted，另4disabled；1ephemeral、readOnly/networkfalse/never、0turn，无正文事件。90秒工作限结束，同工作门挡住unsubscribe，请求及ACK未证；EOF后native自然0/owner1/未强杀/Job0，92.547秒收口。64源、凭据及主用户/项目保护配置未变。原held保持，工作/收尾门已作离线派生纠偏及2边界检查，未实跑或补ACK。 |
| SDK机制准入 | 精确29715162上的两个Windows SDK机制案例已正式observe/recheck，原始来源/配置/退出与审查已核。只覆盖其原定义和条件；后续观察器变更重绑当前声明，不继承旧执行为新源验收。原a5限证和失败保留。 |
| 普通CI判定成果 | `v33-native-exact-ci-decision-01`交付真实工具与两阶段结果；新目标及撤回联网/委派后，从旧passed正确改为unknown，26项oracle两阶段通过，997.436秒收口，原件/配置不变。0607778f上有限正式准入已闭；越界列出Root目录metadata的P2保留，不冒零访问或全政策合规。 |
| 能力选择与交付 | 备件有无Skill cue的有限自主选择；Root受托代选、业务写前读取Implement/TDD、四实物及独立后置QA有正向事实。原UTF8的980/1200窗口失败与后来软件QA通过分别保留；不为native activation形式重做业务。 |
| 连续性与恢复 | C02受控能力失效后有源自主proposal、语义继承、一写者首续作、独立QA和源订阅释放；原C01首turn前历史读取失败保持。独立fixed-response原生场景另证正常释放缺ACK后的跨控制者收尾，不能替代模型行为、普通择时或完整组合。N失败及原catalog条件不变，不重跑。 |

## 剩余主线

当前声明诊断为17范围、13活动case，7范围存在声明绑定缺口，其中5范围没有case。合成事件修复的两阶段软件/纠正/资源事实保留，但原窗口条件未全证，已结束实例转历史，不再作为未来必过或重跑义务。原生CI比较及01/02历史不变。数字来自机器声明，不是完成率，也不是完整实际验收结果。

| 仍缺范围 | 下一必要内容 |
|---|---|
| 能力协调 | research-learning-and-reuse、recovery-and-lifecycle、capability-loss及default-host-without-extra-extensions的充分绑定与实际结果；继续保持作者政策、用户禁用/排除、同名/同义仲裁与真实目标控制。 |
| 连续性 | recovery-and-rollback及capability-loss正式绑定；普通择时、变化后继承/暂停/纠偏、适用失败恢复和必要原件/资源条件。旧workspace未知责任保持。健康任务不强制交接，不把分散实例拼成同episode。 |
| environment-adaptation | 新原生比较已证实际条件变化下的充分路线、完整结果和退出；已装字节before已由既有充分前态证据补核，剩余是原600秒内完整语义/原生事实QA时点未充分证明，不追认。 |
| resource-pressure-and-exit | 新原生比较已实测160/96MiB两阶段自然退出及partial保留；原监督器强退原件保持，正式条件缺口另列。 |
| codex-lifecycle | 复用已证完整注入/传递机制，补真实模型采用、当前适用入口、变更/失败/恢复及有效用户环境的充分证据，尚无父case。不得由认证、安装或目录发现代证。 |
| system-integration | 尚无必要职责共同成立的完整case；覆盖当前目标所需职责、八质量轴及适用场景。足够原生能力承担职责或合理不介入也可成立，不为覆盖强行调用所有机制。 |
| system-impact-assessment | 尚无父case；需独立核结果、用户干预/纠偏/恢复负担和相关总成本/净影响。能力可见、安装和局部成功不等于价值。 |

W01/W03/W04的变化处理与历史受影响成果纠偏、W06/W07的环境资源、W08整链责任继续存在。A01–A08和全部质量底线保持；三项有限准入不关闭父范围，前瞻登记也不增加实际通过。最终收口仍须当前候选独审、托管检查、适用入口/条件和有序发布后态。

## 证据入口与禁止重放

仅在对应依赖需要时读取；私有根为 `C:\Users\15521\.codex\backups\`。下列结果及旧窗口不是下一轮执行命令。

- 当前触发源：`accord-sessionstart-trigger-20261008-01/sources.json`、官方固定源、原页和机器诊断；公开解释见本页上方来源核对。
- 历史162254候选传递：`accord-existing-hook-input-evidence-20261008-01/artifact-index.json`、两原ZIP、`FACTS.json`与`RESULT.md`；原生事件与固定provider实际输入逐字符对应，机制与真实模型采用分开。
- 当前安装/入口：`accord-isolated-install-20261008-01`保原拒绝及wrapper失败；`accord-isolated-install-20261008-02/actual/POSTSTATE-FACTS.json`与原回执；`accord-isolated-entry-20261008-03/SLICE-RESULT.md`及actual原件。原02/03及grant/clock不复跑，不补ACK或重新安装。
- 认证：`accord-isolated-auth-ready-20261007-01/actual/ACTUAL-RESULT.json`保原390秒失败；`accord-auth-persistence-read-20261008-01/ROOT-VERIFICATION.json`保后来独立读回。
- 已准入机制/普通成果：`accord-sdk-admission-20261007-01/ADMISSION.json`；`accord-exact-ci-checker-20261007-01`的原件、工具、两阶段QA与ADMISSION。按原精确主体及边界复用，不改变P2。
- C02与历史读取：`accord-controlled-capability-loss-20261006-02/ROOT-RESULT.json`；`accord-sdk-history-readonly-20261006-01/FACTS.json`和原始帧。历史读取只证明原范围，不能代源释放或恢复控制；旧input-loss marker归属unknown且未清/replay，不再无价值调查。
- ACK恢复与N处置：`accord-native-release-fixture-20261006-01/ACTUAL-RESULT.json`、`accord-native-recovery-coverage-20261006-01`；N原失败在`accord-release-ack-recovery-20261006-01/ACTUAL-RESULT.json`，退休登记在`accord-f05-closeout-disposition-20261006-01`。fixed-response与模型事实分开，原定义/失败/限制不改。
- 备件/排考/UTF8、catalog/retro/词表/concept/stateclient、资源/环境及旧SDK实例均按原件保留；已闭业务不重播，旧240/600/20等窗口不扩。更新09已核后态，04/05强制退出和旧恢复记录保留，闪窗按用户决定搁置，不复活退休缓存。
- IDE v2 `01a0e4dd-45c9-7a82-97f3-2d7bc0e9ae1a`输入缺失与禁止replay保持；Work projectless与Root cwd不混绑。GLM/Gemini工作树已可恢复归档、main唯一，用户会话保留，旧空目录占用不强杀。
- 新IDE只读核验：`accord-ide-live-20261009-01/FACTS.json`及所列原生记录、输入、共享标记副本。与旧v2是不同线程，原指令完整仍被旧工作区水印隔离；不是输入缺失的复现，也不是恢复通过。保原探针禁止replay，未改变共享状态。

更早历史见[87c13c8c快照](https://github.com/yiheng8023/YIYUAN-Accord/blob/87c13c8c7571dfb48c3897b5be631075c5719ce9/docs/operations/CONTINUATION.md)、[试验记录](PROCEDURE-v3.3.md)和私有`accord-release-gate-correction-20261006-01`原件。精简当前页不删除或改变历史身份、失败、授权、未完责任。
