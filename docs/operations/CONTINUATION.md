# 当前接续

更新：2026-09-24 · N33-20260909 / r31。a6505491的CI35938423931已11/11成功，覆盖本批源持久性前置检查；先前CI结果保留原提交范围。已settle目标的新controller恢复已有三平台原生结果及独立回读；已reconcile后的收尾连接通过93项本地检查及精确45507f46托管回归；当前用既有失ACK夹具补其必要原生组合；9月23日01原案因测试夹具作用域错误失败并保留；修复后的02原生收尾组合及可搬迁回读通过，固定4响应、零模型，独立原始RPC/SQLite/资源回读通过；新增收尾组合Linux/macOS artifact也已独立回读通过。51aafb31的CI35815649409原失败保持；新macOS退出回执自然释放、当前/最近OS错误均null，未复现但不宣称旧根因已确定。资源/环境原案报告遗漏仍不准入；34028/CLI0.156.1普通派生报告修订已观察，首次成品混淆副本可见性与历史未决状态，经root及独立审查修正，不计自主通过。以实时Git、工具目录和当前receipt为准。
[计划与工序](PLAN-v3.3.md#当前推进顺序)拥有共识与路线；[基线](BASELINE-v3.3.md)、[验收](ACCEPTANCE-v3.3.md)与product/development.json分别展开结果、判据及机器投影。

## 目标、共识和授权


**当前继续开发：2026-09-22用户决定3.3先内化Jev/Laya等适用设计，借助宿主已有模型、工具和必要Accord组件完成职责；专用第三方决策模型产品接入留待后续版本。停止本版追加此类旁路评估/接入待办，原研究与试验保留。用户无需额外部署模型；一般工具、插件、服务和成熟实现仍按价值复用，不新增训练、托管项目或零成本承诺。**

- 完成3.3功能、质量和必要验收后发布3.3.0，保持原main检出。该发布已有条件授权，尚未就绪；不得重复索要同一授权，也不得降低功能或质量底线。
- 适配按工作形态、执行位置、接入方式和操作系统分层；IDE品牌作为集成实例，共同机制复用、实质差异另核。用户没有Mac/Xcode或JetBrains，不要求为本项目采购或补装；用现有设备、官方来源及托管CI推进，实例未知不冒充支持，也不阻塞其它可行工作。
- 设计供应商中立，本版仅交付适用OpenAI入口。Work/云端、跨项目及远程衔接按真实价值与可行职责判断；普通Chat不是默认独立交付项，Claude适配留给后续版本。
- 动态适应由语义、事件、当前状态和反馈驱动。组件可临时组合、替换、返回重判和退出，数量不固定；单段依赖可用DAG，整体允许受控恢复回路。负边界防止无依据动作，正向目标、验收和反馈推动完成；既不穷举需求，也不把“未越界”当交付。
- 9月20日执行纠偏适用于所有能力：落实已有的按价值复用和职责分工原则，先核对必要结果、已有承担者及真实缺口；风险提醒不自动新增实现或验证工程，负责协调/交付不等于包办底层能力。已撤回刚添加的独立语言覆盖待办与专项验收表述，有限已执行证据保留，不因改写文档重跑。模型/推理选择及主任务/子代理授权分别判断；固定上游研究在accord-model-route-review-20260920-01，未切换当前主模型或推理强度。
- 上游不限Skill，但整体规范不可缺。当前由插件自身与宿主连接承担，不要求修改用户AGENTS.md。共享资源及后来介入组件的影响都要核对；协调不取得无关历史、组件或任务的所有权。
- 默认不启用Plan/Goal；兼容用户明确选择。本开发任务不开Goal。新账户、信任、数据、实质费用、无关共享或外部写入仍各有边界；此前单次关闭源沙箱试验权限已用完。
- 用户已授权按需提交、推送及检查。本公开仓库按验证需要使用标准托管CI，不适用私仓2000分钟限制。云环境、IDE及开发对话保持；归档或删除对话另需明确授权。
- 用户已明确授权按最新共识按需更新README；旧“暂只改Ubuntu→Linux”限制已被本次指令替代。本轮仅作必要现状与依赖说明，发布前仍整体核对。知乎/Reddit等仅是[传播候选](LAUNCH-v3.3.md)，没有排期或发帖授权。
- 2026-09-20用户撤去已放弃活动的专项资格、排期和投稿事项；当前计划仅保留通用发布素材及其它传播候选，不恢复旧活动待办。

CI节奏共识已按9月20日用户确认写入计划：本地小改/针对性核验与提交可以及时进行，相关变更形成完整工作段后再集中推送，避免尚未完成的有效全矩阵反复被取消。必要平台覆盖和最终候选门槛不变；纯接续记录不触发无价值重跑。最新完整绿色为a6505491；47d8e606失败及其修复前后结果分别保留。后续推送按工作段及实际验证需要判断，不回到每个对话小片立即推送。

2026-09-23补充：本机Max/Ultra由用户开放，候选支持、显示/启用和实际选择分开核实；不自动打开隐藏档位，不固定主/子代理模型梯子。第三方Skill的隐式策略与显式使用边界已同步计划、基线、验收和机器投影，映射原W02/W06/W08及A02/A06/A08；必要适配先找实际缺口，普通行为尚未验。Matt既有源文件与上游、管理器投影核对一致；该静态结论不证明隐式采用。该r30静态策略已按上述r31校准，避免默认显式被误当永久限制。用户授权删除的两项非Matt技能及旧WSL配置已在本机处理，保留恢复备份；Computer Use应用授权项仍由桌面端使用。

## 当前事实

| 项目 | 已核事实与边界 |
|---|---|
| 仓库与写者 | 本批开始main=origin/main=a6505491，工作区干净；root负责集成与安装收尾，为唯一仓库写者。限定独立审查者仅只读核对代码与来源，未执行共享变更。旧轮次写者及交接记录保留其历史范围。 |
| 已安装开发包 | 3.3.0-dev.1+codex.20260924001947，24文件，SHA c10422444c4c75e73cb0724b7da5f7b4b538433b0d4f62e6db2762851023a8f7；Git市场ref=a6505491。复用进程级Git URL映射从已核本地提交取数，注册仍为原GitHub来源，持久Git配置和其余共享配置保持；安装/Git字节一致，fresh目录5启用Skill/6启用trusted Hook。旧包及配置留作恢复，5个CLI域与1个发现域均自然释放。当前任务的既有指导/MCP采用另核，不以目录发现代证。 |
| 当前源候选 | 3.3.0-dev.1+codex.20260924001947，24文件，SHA c10422444c4c75e73cb0724b7da5f7b4b538433b0d4f62e6db2762851023a8f7。基于74845补SDK源创建的实际持久性确认：明确请求ephemeral=false，回执未明确为false则保留ID/原回执，停止writer绑定和首轮发送。普通入口指导与Stop未改；CI通过后开发安装已同步该候选。旧宿主/行为证据保持原包身份，不因本地检查移为新候选通过。 |
| 实际采用 | 前轮用户重启后原任务调用inspect_task_state(contextAssessment)返回continue-bounded，sourceReleaseAllowed=false；旧epoch反例返回reassess。输入/状态字节保持。首次缺原生计数的unknown和之后有据评估分别留证。当时实际Goal读为null，仅证明当时无Goal。 |
| 当前任务状态 | 9月23日resume后原native状态仍标输入恢复。root从当前任务rollout确认本轮原文、turn/model/cwd，与实时MCP元数据一致后，沿已有令牌绑定replay恢复当前输入；原生read_task_input回读441字符/hash一致，source=retained-native-replay，两恢复标记false。根任务仍unbound，无完整项目checkpoint；旧缺失输入未重建。原生上下文来源恢复可观察，计数仅响应边界和本机实际设置，不作默认规格或接管许可。 |
| 已完成CI | 精确a6505491的[35938423931](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/35938423931)11/11成功，包括Linux/macOS原生链与三平台Python矩阵。早先68f44925/35836060018成功、05cd9359/35834166597摘要失败和其它历史结论保持原提交/包身份；不将当前绿色改标为全部行为准入或发布就绪。 |
| 前批本地回归 | helper完整140/140；MCP完整37/37；开发契约87/87（185.942秒）。三项静态检查、插件/Skill校验、actionlint及源码/随包一致性通过。实际代码/测试2273747字节、160文件、主指导13654字节；局部通过不等于正式准入。 |
| 当前原生SDK组合 | accord-sdk-native-20260921-01的单次真实宿主固定响应组合通过，原始记录与独立复核保留；3项离线夹具与19项交付契约检查共22项通过，三项静态契约和actionlint通过。修正Node测试漏计后当前实际2555271代码/测试字节、171文件、主指导13785字节。两平台原生artifact已独立回读，13份冻结源码均逐字节匹配ac5dd3e8；各2次交接/10固定响应，exit0/forced=false/所属进程组absent，不将POSIX未知进程计数填成0。 |
| 当前SDK后续交接检查 | 同一connection + carrier + SQLite两次transfer、目标接收期context/nested拒绝、adopt当前refs/lease/idle目标、settle前后超时与不重放已检查；carrier31 + session12 + 包/交付契约25，共68项通过，三项静态契约通过。实际2472548代码/测试字节、169文件、主指导13785字节。零真实模型/宿主新实验，不作普通自主行为或完整A05判定。 |
| 前批SDK机制检查 | 真实connection + carrier core + SQLite组合通过；连接26、记录器7、session8、既有handoff29，共70项本地通过；开发契约87/87（148.531秒）通过。三项静态契约检查通过；原批实际代码/测试2437451字节、169文件、主指导13785字节。未调用真实模型或安装新包，不是A05整项/GUI准入。 |
| 当前场景检查 | 当前准入类19项中1项因新增范围后旧预期未同步而失败，原结果保留；修正后受影响2项通过。指导修正后三项直接入口/恢复检查通过，Skill/插件校验通过。真实任务观察与正式判定另列。 |
| 原生写入接线 | 三个隔离固定响应案、零真实模型。01/02被宿主审批拒绝；02 CLI覆盖键错误，所谓预批准实际未生效。03正确到达工具，缺receipt拒绝且没有状态写入；观察器误检查被宿主移除的isError而整案失败。原失败不改标；离线回读证实拒绝语义，脚本已按status/result/error修正，不重跑本例。 |
| 资源/环境真实结果 | 精确916ff322/f3安装包33628，CLI0.155.1/App Server/Terra medium；一条普通输入，403.712秒，无追加救场。1→1并发在160→96MiB真实Job预算下复用两项完成8项；CSV/512MiB原始展开内容及13原件hash/mtime独立一致。两worker及外层Job自然exit0/进程0；Goal前后null、实际default模式、当前完整指导送达，continuity/verify两Skill实际读取。原报告漏记后来的清理策略拒绝及处理，两个case整案均不准入。已解决的自检常量笔误另记，不据此判业务数据错误。 |
| 云环境 | 最近只读核对为YIYUAN-Accord、目录/workspace/YIYUAN-Accord，3个历史任务保留；universal、自动初始化、Agent网络关闭、缓存开启。当前新包云端行为未验证。 |
| 正式验收 | 17项必要scope，11项有定义、6项未绑定；定义不等于通过。4个OpenAI入口纳入开发、7个待判，selectionFinal=false。A01–A08整项完成仍0/8，functionalCompletion/candidateEligible=false；早期SDK子范围保留其原包身份。 |
| 9月23日收尾组合 | CLI0.156.0/Node24.20.0；02实际2次thread/start、3次turn/start、4次本地固定响应、1次source unsubscribe，SQLite revision19/settled且writer为目标。keep、共享配置、可执行文件与执行源码保持；Job自然exit0/forced=false/readerStopped/activeProcesses0，home/state/temp已回收。原件及CI同形搬迁副本回读通过，缺配置观察、额外native-home文件、重复RPC回执三个反例拒绝；临时副本已清理。独立审查另核15个RPC的唯一成功响应、实际idle/terminal与SQLite，未仅复跑检查器。38项离线carrier及2项路由/共识定向检查通过。此为固定协议组合，不证明自主择时、普通模型行为、完整A05或GUI采用。 |

## 本批实现与下一实际动作

9月24日普通证据接回准入的核对已完成：accord-installed-cadence-20260920-01的31份冻结源和5条输入Hash仍匹配，原五轮正确行为继续保留；它的CLI0.155.1/Terra、完整安装Hook、900秒条件与旧正式case的0.154/Sol、源Hook、600秒不一致，也没有对应v5观察记录/当前候选审查包，原时点已超86400秒。因此不改标通过、不重标时间、不为变绿重跑原五轮。准入器新增caseRejections固定原因码，区分定义/包/依赖、时效、条件和实际结果等拒绝；旧errors、准入条件及计数保持。完整准入54项回归通过，独立复核通过；旧原件与差异依据在accord-evidence-admission-review-20260924-01。后续必要普通工作段须在执行前把实际条件、候选/依赖及正式observe/recheck和审查连接一并绑定；开发观察不自动成为正式准入。插件包和安装保持01947，不另更新缓存或要求重启。

当前0.156.1的完整experimental公开Schema已核：thread/start没有客户指定threadId或创建幂等键，thread/started通知只有thread，thread/read需要精确ID。SDK当前日志未提供可按原请求ID取回迟到ACK的入口；回执从未收到时更不能猜测最近任务。保留SOURCE_START_UNKNOWN和owner对账符合现有边界，不因此追加推断式认领/通用恢复框架或宣称完整A05。原件在accord-source-recovery-interface-20260924-01，重复导出已清理，保留完整v2及ClientRequest Schema；无新模型或原生执行试验。

9月24日本批独立推进SDK源任务持久性边界：新增两个固定回执反例（ephemeral为true、缺失），修复前均未被拒绝；修复后保留sourceThreadId/原回执且SQLite尚无writer、无turn/start，重复run保持失败。源会话21、原生夹具单测7、开发契约87，共115项通过，插件校验/语法/产品契约通过，限定独立复核通过。既有0.155.1原生源回执已核字段为false，仅证字段可用；未新增原生或模型试验。完全丢失初次ACK仍须owner对账，A05整项与17范围完成计数不变。私有记录在accord-source-persistence-20260924-01；精确提交包字节与CI已通过，开发安装/原生发现及所属进程收尾已完成（accord-shared-plugin-update-20260924-01）。下一回到既定有真实交付价值的普通工作段与必要连续性，不重复固定协议，云端403保持独立待处理。

当前安装对齐已完成：原CLI直接add不同固定ref被拒，原config哈希与旧安装保持；核对0.156.0官方源码确认市场remove仅移除该条目/快照后，按原生remove→add精确9aae2880→plugin add完成。旧22文件包和原配置留可恢复备份；24文件与源码一致，5Skill/6trusted Hook来自新缓存路径。五条CLI命令（含首次被拒）与一个只读读取域自然退出、所属进程0；没有真实模型、额外信任或模式启用。空验证工作区已移除，update.py/rebind.py均为一次性脚本，不得重跑。

后续按已具备的安装条件绑定有独立交付价值的普通工作段，优先结合A07实际续做/退出及必要报告纠偏观察A05。无自然转移需要时只记健康续作，不能扩大为自主接管；不缩窗、填充上下文或重复已闭合的固定协议来凑验收。仍未执行新的普通模型案例，scope定义/通过计数不变。

CI故障处理（51aafb31）：macOS原生MCP主体返回completed、状态工具完成/无回执写入按预期拒绝、缓存替换前后MCP均connected；退出回执exit0/readerStopped=true，但forced=true且processGroupState=unobservable，整案保持失败。原始29份执行源已与该提交Git字节逐一对齐，原件和诊断在accord-ci-diagnosis-20260923-01。旧观察器吞掉具体OSError，无法据此确认权限、瞬时错误或进程残留的根因。

本地已修两处观察/收尾缺陷：POSIX sample保留当前及最近OS错误；MCP测试即使app.close抛错仍尝试fixture.close并保存失败结果/可用资源回执，正文失败与收尾失败分别保留。未知或强制释放仍拒绝通过，超时与资源判据不变。144项受影响Windows回归及现有WSL/Linux上的3项真实进程组测试通过，静态开发校验通过；没有新原生宿主MCP或模型试验。修正不是macOS根因已解决的证明；旧轮已收齐10成功/1失败；本批已随9aae2880推送，CI11/11成功；新macOS原件29份源码独立匹配、自然退出且无当前/历史探测错误。旧OS根因保持未确认，不再为无新反例而盲目重跑。原失败在退出异常前未复制keep.txt到retained，CI现另保留原workspace/keep.txt，确保该失败路径的原件可独立核对。



原生机制核对：官方0.156.0固定源码fe74a774及其选择器测试确认显式加载不受allow_implicit_invocation=false排除，但enabled=false仍拒绝。私有accord-skill-invocation-native-20260923-01隔离两次固定响应：普通请求无控制Skill名称/描述/正文，显式Skill输入后正文送达；2固定响应/0真实模型，Skill、源码及共享配置hash保持，两个应用进程均自然exit0/forced=false/readerStopped/activeProcesses0。调用者预选不代验Agent语义选择或委托来源；当前Desktop/CLI任务是否具备同等调度路径仍未知，不能据此宣称Matt Skills已全面自动调用。独立源码/原件复核通过；调用者在审查结束后保全控制Skill副本与原始请求，再回收home/state/temp/workspace/skill-root五个自有目录，cleanup.json保留该人工观察器动作，不计Agent自主收尾。

r31实施增量：非技术用户无需知道Skill名称和时机；由Agent在真实委托内判断适用性并复用宿主/原管理器盘点。纠正刚提交的r30指导中只能用户亲自选择的过度收紧：默认关闭隐式匹配不等于永久禁止授权协调；当前入口支持且目标控制权、启用状态、委托与选择来源成立时，沿原生显式路径代选。格式化Skill输入不制造授权或伪称用户亲选；停用/排除和新增副作用边界仍有效，已有委托无需每次确认。当前源候选经Skill/插件校验、8项包身份/模型路由/共识检查及三项静态校验通过。本轮已按下述原生路径对齐共享安装，普通语义选路与完整链行为仍待验。

最新CI处置：05cd9359的35834166597已结束，2项原生生命周期成功、9项验证均在产品契约检查失败，后续测试未运行。九项同因是完整包摘要绑定了Windows工作区CRLF清单，而Git按.gitattributes提交为LF；干净检出复现，本机旧工作区自洽通过不代表提交通过。已将本地清单对齐提交原字节并将机器投影/当前源摘要校正为750f9ef8；74845版本及Git中的24份包文件不变。修复68f44925在独立干净检出通过三项静态校验后推送，新CI35836060018已11/11成功；原失败日志保留accord-ci-diagnosis-20260923-03。

本轮实际恢复与更新：accord-live-input-recovery-20260923-01保留当前原文来源、旧状态、一次令牌绑定replay和原生回读；只恢复本轮输入及其上下文来源，不计完整历史或fresh接管。accord-shared-plugin-update-20260923-02保留首次GitHub克隆curl28/early EOF失败，当时市场条目已移除但旧包完整。确认当前后态后复用Git进程级url.insteadOf，从本机已通过CI且逐字节核对的提交取数；原GitHub配置来源及未相关设置保持，未放宽协议/信任/网络安全设置。安装74845成功，7个受控命令/发现执行范围自然退出，两个所属空目录已清理；备份和原始回执保留。一次性脚本不重跑，不新增模型调用或常驻进程。

当前源码修正：回读上一普通任务原始事件，SessionStart、UserPromptSubmit和Stop均有实际完成记录；不是Hook未触发，也没有状态检查器证明语义通过。执行者只核对自写一致字段，未进行来源对照；专用核验Skill未读取，但不能据此断言唯一因果。改写现有短入口核验段及路由，并限定专用Skill中的历史失效判断；没有新增Hook、判定器、模型服务或固定审查顺序。新候选74845的两Skill/插件校验、三项静态契约和4项入口/未决状态测试通过，独立文本审查无实质问题；行为仍未验证。基线、验收与r31已包含这些职责，不新增共识或必要scope；机器投影仅同步候选身份。下一按实际功能工作段取得当前候选的有用普通链证据，不重放旧报告求通过。

本轮普通任务：accord-report-reconcile-20260923-01保留旧资源批次原件，使用其成品/运行记录和后续可见调用副本生成修订说明，未重跑批处理。实际CLI已更新0.156.1，模型目录及原生配置核对为Luna/medium、default、Goal前后null；34028入口完整送达，100.469秒/一轮自然完成。原稿补记清理拒绝，却将有限副本缺文件误列为历史未解决工作，且JSON漏记Markdown已写的校验常量笔误；首次结果needs-correction保留。root修订后独立来源审查通过，原始输入/hash/mtime、35份冻结执行源和共享配置保持，进程自然exit0/forced=false/所属进程0、reader停止，临时缓存和空state已回收。此为有评估者纠正的普通报告交付，不冒充原案重验、自主通过、压力响应或自动交接；正式计数不变。现有指导已要求保留有效历史、核对关联成品，不为此样本再堆一条规则；后续按实际普通链的复核与承担者缺口推进，不重复报告或批处理试验。

本轮开发自用：以独立有限材料委派子代理整理安装交接说明，请求Luna/medium且不继承旧对话。原材料遗漏恢复定位与实际处理步骤，root补充已有事实后接续修订；两份成品及五份原输入/补充hash已独立回读。仅说明这一内部说明任务的材料承接与修订，不证明模型成本优势、原生Hook采用、自主择时或完整A05；正式计数不变。原件在accord-install-handoff-20260923-01。下一仍按既有普通任务与A07剩余需求前瞻绑定，不能为交接本身制造工作。

自主连续性仍须先绑定实际普通任务、候选及执行入口；健康完成且未出现迁移必要性只能计对应子事实，不强制制造交接或扩大上下文来凑通过。下一普通场景尚未执行，scope仍未绑定，不增加已定义/已通过计数。

本批完成：在既有owned stdio/固定响应失ACK夹具增加finalize-receipt场景，从source启动起复用随包SQLite记录器，保留原始回执和受控callback故障，再reconcile→finalize→真实退订一次→settle/readback。只补新收尾连接，不重跑旧场景，也不为拼整链再建controller重复已验证的SDK restore。执行前冻结源码/身份/权限/判据，root在全新accord-finalize-receipt-native-20260923-01独占一次真实执行。CLI已由用户升级为0.156.0，实际身份另冻；原案在reconcile之后因Node夹具plan作用域错误未进入finalize。该原案保持失败；修复后仅在全新02执行一次并通过。首次离线检查器缺ROOT导入且误要求owned config文件（实际通过argv配置），已离线修正并验证native-home全清单/hash；未为修正观察器重跑宿主，原执行源与失败输出不改写。

本批收尾连接已实现并独立复核：固定0.155.1源码确认unsubscribe针对请求connection，原连接关闭由宿主移除其订阅。finalizeReconciledHandoff消费已确认的revision/lease/receipt digest，fresh核对source/target、权限、暂停、效果及单写者；不再次turn/start或resume源。同原连接按实际退订及后验判定，新controller按独立原连接关闭证据释放；notSubscribed/notLoaded不代证其它controller静止。

其自身release-authorized/observed/held状态可在核对现态和原intent后恢复：未知unsubscribe保留pending/requestRef，绝不重发；原native intent可由新controller转为有据prior-controller-closed，nativeStatus=null且保留原intent。original、reconciliation、既有finalizer三个已知角色按实际connection去重核证，缺关闭/静止证据则hold，不因接替者再次中断永久卡住。CAS仅实际调用后标未知；每次记录直接前驱lease，ephemeral三态保持。原失败与reconciliation保留，最终形状复用原settle/restore，不增schema、服务或扫描器。

验证：carrier38/recorder10/session20及交付/包契约25，共93项本地通过；独立carrier38项及源码镜像复核通过，Node语法和三项静态契约通过。真实SQLite的reconcile→finalize→settle→claim→SDK restore组合通过，跨controller分支0 thread/start、turn/start、unsubscribe。当前代码/测试2735137字节、171文件、主指导13785字节，预算2900000保持至少5%余量。这些本地检查当时尚无新原生运行；9月23日02已补固定响应原生组合及独立回读，仍不代表真实模型、任意crash、默认GUI采用或整项A05完成。先前三平台结果保留原包身份。

CI修复：Windows RUNNER~1与macOS /var均是系统临时根的别名。两项新离线测试把别名直接送入严格ordinary目录检查，或与已解析文件路径比较，导致每个受影响job各1 error/1 failure。真实Windows短路径复现同样两错；仅将两项自建临时根resolve(strict=True)，同一复现2/2、完整离线组7/7及静态检查通过。安全检查、产品runtime和包身份未改。CI在完整回归前运行该轻量组，提前报相同准备错误；不跳过平台、用例或完整矩阵。此时计量2666313代码/测试字节、171文件、主指导13785字节；原批2666188保留原身份。诊断原件在accord-ci-diagnosis-20260921-01，空复现目录已清理。

新增manage_task_state复用既有bind/pause/retire和状态存储，不增加服务或业务文件执行器。原生元数据绑定根任务和turn，调用者保留已观察epoch/revision；helper在最终发布/删除前再次核对turn，涵盖人类输入epoch未变而宿主续作换轮次的情况。绑定保留暂停；解除用户暂停或取消仍需实际用户决定。理由、注解和metadata不是授权证明，不通过关键词或自报布尔值推断权限。

执行异常报告效果未知并要求查后态；超长成功结果保留精简成功回执，不把已执行写入说成未发生。MCP框架可以在调用前拒绝；不得为绕过拒绝改审批策略或换通道。隔离03使用进程内逐工具预批准只检验无receipt拒绝，不改共享配置、产品默认或沙箱。固定0.155.1源码说明CLI覆盖键左侧按点分割而非TOML引号解析；App Server把MCP isError映射成failed状态，结果本体不重复该字段。已有原始回执足够定位，不盲目重复试验。

前批已settle冷恢复切片：claimScope只在已确认的inactive scope上原子旋转标记，不改writer/历史或清active transfer；restoreCodexSourceSession需要旧ACK中的expectedScope，准备核验后先claim/readback，再原生resume与后验。新标记在ready前及普通turn前后重核；旧basis跨实例不能重复resume，失效恢复对象不能fallback建新source。普通create/hot不要求未用claim能力。recorder10/session20/离线fixture7及交付/包契约25共62项通过，三项静态契约和actionlint通过。实际代码/测试2666188字节、171文件、主指导13785字节；代码/测试预算按本批必要恢复与验证实现调整为2850000，保留至少5%余量，不新增文件或主指导额度。

accord-sdk-restore-20260921-01由root独占执行一次：旧01只读复制ledger、三份session和keep，不复制host索引或Goal库。真实0.155.1/Node24.20.0以新controller恢复旧第三任务，7个RPC有唯一成功响应（initialize1/read4/resume1/turn1），无thread/start或新交接；一次原子claim先于resume，真实context工具调用成功，2个固定响应、0真实模型。两条settled transfer状态/revision不变，scope writer保持且token旋转，仅第三session追加一轮，另两份逐字节保持。Job自然exit0、forced=false、readerStopped、activeProcesses0，fixture停止；旧根完整nofollow inventory、执行源/保护原件/共享config保持。冷恢复仅针对已正常释放的controller，不证明crash、活跃transfer、未知业务效果、Goal迁移、自动择时或普通GUI采用。

可搬迁回读首次发现CI清单漏带workspace/keep.txt，原失败保留；补artifact路径后离线回读通过，没有放松检查或重跑宿主。原执行脚本、13份冻结源、RPC、ledger和native sessions均保留；两个全历史展开弃用提示和一个虚拟模型metadata fallback警告不隐去。运行时使用summary/excludeTurns，受控小历史展开仅用于独立核验。独立审查者停止后，由root核对并清理53份搬迁验证副本及空state/temp目录，原01与新01的必要证据保留，清理后回读仍通过。

本批原生SDK组合已执行一次：新增两个fixture复用既有_Fixture/_App/OS控制，13份执行源事前冻结；11份原有实现逐字节匹配e22fba76，2份新观察器按原执行字节保全。CLI0.155.1/Node24.20.0实际完成3任务、6个completed turn、2次transfer及2次adopt；29个RPC各有唯一成功回执，2次退订仅指向前两任务，两record均revision19/settled1且最终writer为第三任务。10次localhost固定响应、零真实模型；Job自然exit0/进程0、reader与fixture均停止，源码/keep/可执行文件/共享config前后hash保持。独立raw/SQLite/rollout回读通过；可搬迁artifact通过，重复响应/错误terminal/重复工具reply/错误writer四个副本反例被拒。原始context实际unknown，6个虚拟模型metadata fallback警告和3个分页全历史展开弃用提示保留；不作动态压力择时、语义/性能或GUI通过结论。

云端只读核对已按用户明确同意单次完成（约3分2秒），任务为“检查 YIYUAN Accord 开发包接入条件”。实际检出8e6015fd、平台work分支、/workspace/YIYUAN-Accord；原生命令回执确认可用CLI为0.144.0-alpha.4、plugin list为空、MCP仅make_pr、无Accord Skill，Git结束时干净。Node24.15.0/SQLite/WebSocket是云端报告值，保持证据来源层级；CLI文件版本不当作当前控制者版本。现有包在该云任务未装载，不代表云端不可适配；下一准备与该版本相容的原生注册、信任及加载/恢复方案，涉及安装/启用/信任或设置变更时另需具体授权。本次授权没有覆盖这些动作，也不允许重建或重复发送已结束任务。原件与结果在accord-entry-route-review-20260923-01，正式准入与17项范围保持不变。

本次获准的云端接入验证已停止并完成回滚：原任务临时注册/安装74845及24文件核对成功，但0.144.0-alpha.4原生目录只有4个唯一Hook（两个SessionStart、UserPromptSubmit、Stop），缺SessionEnd/Interrupt，未达到预绑6项授信门槛，未进入原任务采用阶段。可见原生命令证实插件/市场移除、列表为空，config恢复前态相同字节、Git干净；所属AppServer PID4888 exit0/forced=false且后验不存在，原有宿主进程保持。最后只读回执核对发现原始RPC请求流水未保存，精确方法次数未知；不把预定客户端代码当实际调用记录。私有备份与版本差异诊断材料保留，结果在accord-cloud-route-20260923-01/cloud-pilot-result.json；不要重跑旧方案。下一按实际事件职责评估已有替代路径，六项仅属本次门槛，不等于所有宿主通用必备数量，也不能凭四项发现宣称整链通过。

缺失事件职责审查已完成：官方0.144.0-alpha.4源码表明原生取消终止本轮并记录TurnAborted，不经正常Stop续行；现有输入/resume更新epoch、迟到回调约束及显式retire分别承担后续核对和有责任者的回收。7项既有本地检查通过；没有仅为补事件名新增运行时的理由。旧回执不等于仍在执行，外部效果/写者和原云控制者实际采用仍未知，未提高准入。9月24日新的有界授权已执行收尾：四项真实Hook授信成功；同容器下一原生输入未获得指导/状态工具，原任务采用未成立。前后容器和配置延续，因此转查受支持的原控制者装载/刷新与初始化时机，不循环重装。已原生移除本次插件/市场，撤去四项信任，配置逐字节恢复fee05670前态，make_pr与仓库保持；所属PID5455自然exit0且后验不存在。新方案已结束，原六项试验同样不重跑。结果在accord-cloud-route-20260923-01/cloud-adoption-result.json。证据在accord-cloud-route-20260923-01/missing-event-duty-review.md及cloud-adoption-proposal.md。计划/架构/机器观察同步；基线与验收结果判据不变。 装载源码复核已完成：0.144每轮复用会话配置及插件缓存；同server的安装/配置刷新只通知自己的线程，不能由独立检查server刷新原云任务。当前没有原控制者受支持连接；官方环境详情可读，但点击编辑到/edit后返回403，未更改设置，已请用户仅确认其手动访问。下一先核入口可用性和启动前装载条件，不循环安装或预先编造新运行时。详见私有loading-path-review.md。

下一按依赖推进：

1. **沿剩余实际入口与恢复缺口推进。** target创建期工具绑定、接收阶段事件泵及显式adoptTarget已经接通，同一scope连续两次transfer、旧lease和未知settle不重放已有固定协议检查。Windows真实0.155.1组合已按冻结条件检查；Linux/macOS同项与已settle新controller恢复已通过原生CI及独立回读。后续按必要业务范围补真实择时/语义接管，已找回首轮回执后的finalize→settle→restore连接及其自身中断恢复已通过本地组合，新增原生组合已在9月23日02核对；完成本批集成与托管验证后，绑定路线中立的普通自主连续性；不得重复已闭合协议链或把干净退出后的恢复外推到所有断线情况。
2. **保留已执行场景并验证候选修正。** 916ff322的唯一普通任务已执行、原失败和正确子事实已保全，不重跑批处理或事后改写原报告。当前修正明确：后续核验/恢复/清理改变事实时，应更新受影响的文件，聊天说明不能替代写回；原Skill已被读取，不能归因为没有触发，也不再加一条泛化提醒。修正属于指导候选，待后续必要组合行为核验；不另造全域错误账本、关键词解释器或强制每轮审查。
3. **完整工作段集成。** 原生写入工具的两平台拒绝/缓存替换与退出链已核实，既有小链不重复。当前新验收包依赖集已在运行前声明，排除未用的fresh传输/dispatcher实现和展示/法律资产；实际执行或后续影响超出集合须拒绝复用，不事后增删集合。余下fresh连续性、入口和组合工作继续按真实依赖推进。
4. **补剩余结果条件，复用已闭合证据。** 现有同任务压缩恢复、普通五轮链、宿主升级及固定交接协议保留原条件。A05的fresh适用路径与跨控制者未知效果恢复、跨入口选择、A07压力调整后必要续做和退出、A08组合/净影响仍未闭合。先复用官方能力和现有执行者；只为真实残余缺口补接线或试验。
5. **条件满足后发布3.3.0。** 前瞻绑定余下6个未定义scope及实际条件，完成必要行为、组合和独立审查，形成精确候选，校正README/发布说明并核对发布后态。已有条件授权不重复询问；未知和未完成不以局部绿灯抵消。

A05按实际结果判断路线：原生压缩、范围级临时委派/fresh子代理、工作树及其他足够宿主组合可承担适用责任；必要转移仍须自主择时、关键状态承接、接管与实际续做、转交范围单写者及失败恢复证据。App Server控制连接是现有SDK路线的局部前提，缺失仅限制该路线的采用声明，不是全入口架构门槛；不把源主对话退出或顶层新任务当通用条件。下一先前瞻绑定v33-autonomous-continuity的实际普通任务和当前有效设置，复用已有自然压缩/委派/SDK机制证据；不为凑观察刻意膨胀上下文，也不把部分健康续作代成全部A05通过。

普通连续性当前路径是原生压缩→SessionStart/compact职责/状态恢复→按需补读原输入→核对实际后续动作。自然恢复原始2691–2915行及业务后续已留证；这支持有限同任务连续性，不是全历史无损或fresh接管。当前任务create_thread需用户明确新任务请求，handoff_thread不能搬自己，fork复制历史；不绕过这些具体接口条件，也不外推所有入口均不可实现。

fresh核心已有carrier-handoff.cjs、runHandoffProposal和stdio/WebSocket连接；原完整调用者及SQLite ledger此前只在测试中组装。本批新增随包codex-session.cjs创建源任务、注册两动态工具并泵事件，carrier-recorder.cjs用Node内置SQLite保存scope/revision/lease；无需集成方复制测试实现。仍要求实际获准且幸存的已初始化连接、当前权限/计划与独立语义核验，借用资源由原owner收尾；失败不重放、转移后源不可续写，当前新增同一controller下显式adoptTarget：核验record/当前目标/权限和effects后settle旧transfer，再以目标为source发起新的transfer。接收阶段的工具请求也被泵送，在途嵌套交接拒绝且不排队。已settle、前controller静止的新controller恢复已接通并经三平台原生核验；已找回首轮续作回执后的确定性收尾已补齐并通过本地组合；必要原生组合、实际模型择时及其它未知效果恢复仍须各自证据。MCP状态工具不替代App Server控制，不新增常驻服务或私有IPC。官方loaded-thread resume可重放pending requests；另一个订阅者仍在时源连接关闭不等于释放。dynamicTools需thread/start注册，resume不补注册；排队用户消息也不是只读探测。

验收复用已支持前瞻packageFiles依赖集：纯function单入口可以保留未变依赖上的旧原包证据，版本只规范化默认cache时间戳；基础版本/语义依赖/依赖集合改变拒绝。生命周期、impact、多入口及A08仍要求当前整包；当前独立评审/重核保留。不回写旧定义以适配已执行结果，不把未选依赖当作无影响证明。

本次只读审查发现观察器可能在配置恢复失败时仍以0退出；已在真实模型执行前修正，并补当前Hook指导/原生mode/Goal/最终用量与资源后态核对。输入生成器从本次工具调用原文执行后留存，未冒称事前冻结；真实模型准备时与压缩原件一起冻结。机械预检属于较早工具身份；最终显式runtime-root、CPU查询和cache前后快照随后在普通任务中实际执行，保留各自精确身份，不重盖预检。

## 证据导航、历史限制与清理

原件默认在C:/Users/15521/.codex/backups/。详细旧经过及完整索引保留于[8d724a1b接续前态](https://github.com/yiheng8023/YIYUAN-Accord/blob/8d724a1b9d18dc15810ffc21896f0b8fdb8b5c8d/docs/operations/CONTINUATION.md)和[历史试验记录](PROCEDURE-v3.3.md)。本次删除接续页内互相冲突的过时“当前”段落及重复经过，不删除原始证据或重写历史结论。只按下一依赖读取对应原件，避免整页反复回放。

历史退出证据限定（9月22日回查）：accord-owned-connection-20260920-03、accord-continuation-reconcile-20260920-01及accord-rpc-recovery-hosted-20260920-01的旧桥资源回执未单独记录forced。它们支持native/bridge根进程exit0及最终所属域释放（Windows activeProcesses0、POSIX PG absent），不能据旧README的naturally措辞推成全域未经强制收尾；reader只可按原执行顺序有限推断，共享config前后保持也不能从owned home配置推出。原件和协议结果保留，不因该限定重跑旧链；后续accord-sdk-*中明确forced/reader/shared-hash的独立证据不受此缺口反向影响。

| 定位 | 可复用范围和限制 |
|---|---|
| accord-live-input-recovery-20260923-01 | 当前根任务原文、真实turn及恢复令牌核对后一次replay，native read_task_input文本/hash及恢复标记核验；只恢复当前输入，不重建旧输入、不等于完整checkpoint或接管。 |
| accord-shared-plugin-update-20260923-02 | 68f44925/74845安装；原网络失败、来源恢复、24文件身份、配置语义、5Skill/6trusted Hook及7个受控进程域回执均保留；当前GUI/普通行为另核。 |
| accord-report-reconcile-20260923-01 | 当前安装34028/CLI0.156.1/Luna medium普通报告修订；原生入口参与、原件保护、自然退出有证据，首稿语义需外部修正；初稿及独立审查后成品分别保留。不改旧资源案失败，不计完整自主行为或交接验收。 |
| accord-install-handoff-20260923-01 | 内部安装交接说明：五份保护输入、补充恢复事实、两份交付及两次独立核验保留；源材料缺项经补充修订。仅有限材料承接，不计自主交接、模型比较或整项验收。 |
| accord-ci-diagnosis-20260923-02 | 新9aae2880 macOS MCP artifact：原件29份执行源匹配Git，status passed/3固定响应/零模型；自然释放且observationError/lastObservationError=null。只说明本次未复现，不能补造旧异常原因。 |
| accord-shared-plugin-update-20260923-01 | 真实现有Git市场对齐9aae2880/34028，首次同名异ref拒绝与恢复路径均保留；24文件一致，5启用Skill/6trusted Hook，仅目标ref改变，6个所属执行域自然退出。原配置、旧包与原生回执保留；一次性脚本勿重跑，不代表原有GUI任务已采用或普通功能通过。 |
| accord-finalize-hosted-20260923-01 | f0ec857b的Ubuntu/macOS收尾artifact，各11份执行源匹配原Git；每端15个RPC唯一成功响应（其中6个生命周期效果请求）、2start/3turn/1unsubscribe、SQLite revision19/settled/目标writer。exit0/forced=false/readerStopped/进程组absent，POSIX未知进程数保持null。修正独立报告最初将6个效果请求误称全部RPC的表述；root逐项复核全15回执，原始artifact不改。 |
| accord-sdk-restore-20260921-01 | 单次真实宿主恢复旧01第三任务，旧根不写；新scope标记、原生resume和一次context调用及进程后态独立回读通过。retained含原生历史、13份执行源及必要prior副本，workspace原件随portable artifact保留；首次漏workspace的回读失败和修正另记。不是故障注入或完整A05；不要原地重跑。 |
| accord-sdk-restore-hosted-20260921-01 | 47d8e606的Ubuntu/macOS冷恢复artifact各55文件，13份执行源码与原Git逐字节匹配；冻结checker和独立RPC/ledger/session/退出核对通过，0start/1resume/1turn/2固定响应，旧原件inventory保持、进程组absent。两个Native job通过不等于整体CI成功。 |
| accord-ci-diagnosis-20260921-01 | 保留35606566345的四个失败job日志、短路径真实复现脚本及修复后结果；原问题为测试目录别名，未改原生机制或放宽安全检查。空复现根已清理；修复后73f4c6b8托管11/11通过，fixed-ci.json保留完整回执。 |
| accord-sdk-hosted-20260921-01 | ac5dd3e8的Linux/macOS原生SDK artifact本地独立回读：每端13份冻结源码匹配原Git，2交接/2adopt/10固定响应；CLI0.155.1/Node24.20、natural exit0/readerStopped/所属PG absent。属于固定协议范围，未推断POSIX全局进程数、性能或模型判断。 |
| accord-sdk-native-20260921-01 | 单次真实0.155.1/Node24.20固定响应两轮SDK交接；原始RPC、SQLite、verifier、13份冻结源、3份原生rollout及进程回执保留。独立检查器初版mode=ro产生空WAL/SHM，修正为已关闭且checkpointed库的immutable只读后仅离线复核，原执行源和结果不改写；副作用与定向清理另有回执。隔离native home与keep工作区为后续恢复依据保留，空state/temp和派生pyc已回收；不要原地重新执行。 |
| accord-project-assignment-observation-20260921-01 | 用户提供的两张原图及hash：同一批处理对话从最近移至Playground。后续09:51:12Z只读接口仍返回原cwd、projectId=null/notLoaded；不猜测中间操作，不把界面移动当执行迁移/上下文减负。未移动或重跑该任务，原场景判定不变。 |
| accord-entry-source-review-20260921-01 | 官方Hook/Work文档及固定0.155.1压缩源码的只读来源，含hash和失败抓取记录；IDE官方当前声明与旧alpha实测范围冲突保留未知。不增装PreCompact/PostCompact、不阻断原生压缩。 |
| accord-mcp-hosted-20260921-02 | f3cf8951两平台原生0.155.1：27份执行源与原Git逐一匹配；缺receipt写入正确拒绝，缓存替换保持3工具，3固定响应/0模型，原件保持、exit0/所属进程组absent，5根清理回执保留。不是正向checkpoint写入或普通模型采用。 |
| accord-shared-plugin-update-20260921-04 | f3/33628/8f安装：源码/市场/缓存22文件一致，5Skill/6trusted Hook，除市场ref外配置及其它插件保持；5CLI与读取域自然退出。fresh目录3工具；首个诊断客户端漏发initialized通知的拒绝原件保留，修正客户端后读取通过。无模型调用，一次性update.py勿重跑。 |
| accord-resource-change-20260921-01 | 复用既有批处理/WindowsJob的新容量变化场景。fixture-src保留唯一机械预检与最终源身份；36份来源在模型前冻结。native/结构检查通过，语义审查保留报告遗漏FAIL；独立核验、原报告/CSV/两份run-record及native历史全部留存。累计uncached input56775/output6865/total732824不是上下文占用或完整费用。配置只精确恢复本工作区注册，恢复副本已退役；8个空目录在核验后由caller移除，不归功于Agent。一次性prepare/run勿重跑。 |
| accord-context-assessment-live-20260921-01 | 用户重启后当前原生MCP正向评估与旧epoch反例，前后状态哈希、原始工具结果及独立检查；真实调用但不是自动刷新、全A05或fresh接管。 |
| accord-native-state-write-20260921-01 / -02 / -03；accord-native-state-write-review-20260921-01 | 三案原failed状态不变。01/02审批拒绝，03工具无receipt拒绝；独立读回保留各自后态。执行源、原RPC/固定响应、结果/manifest及完整运行根压缩留存；15个运行根已回收，各域自然exit0/activeProcesses0/readerStopped。没有正向状态写入或真实模型采用证明。一次性目录不重跑。 |
| accord-shared-plugin-update-20260921-03 | 7e/14633/90f安装，源码/市场/缓存22文件一致、5Skill/6trusted Hook，其它插件和配置保持；5CLI/2reader及目录进程自然退出。原“待重启”已由本轮实际调用解除，不改写旧快照。一次性update.py和此前更新脚本勿重跑。 |
| accord-context-assessment-20260921-01 | 冻结源码直接调用返回continue-bounded；不是当时Desktop采用。初次过期和后续有据时限均保留，本轮live补其采用缺口。 |
| accord-natural-continuity-20260921-01 | 原生2691–2915行预冻结，压缩、职责/恢复注入、后续Goal读取/提交及同轮完成的独立回读。响应边界578656→96614不是瞬时占用或节费；无绑定checkpoint、无本次read_task_input，不外推完整恢复。 |
| accord-mcp-hosted-20260921-01 | 7e精确Linux/macOS artifact按RPC/源码/metadata核对，新参数可见但未执行assessment；每平台2本地响应/0模型，exit0/所属进程组absent，不宣称POSIX全系统进程0。 |
| accord-installed-cadence-20260920-01；accord-ordinary-conditions-20260921-01 | 原93b5完整安装、CLI0.155.1/Terra medium的5/5真实普通链，暂停/修订/原件及资源后态核对通过；不是版本因果、GUI或自动交接。旧正式定义0.154/Sol/source-Hook/600与实际条件不符，三case仍不准入，Goal整段unknown。不要重复第五阶段或修改旧条件凑通过。 |
| accord-source-choice-20260920-01；accord-language-boundary-20260920-01 | 前者普通小任务完成且未多余交接；后者业务语义通过但严格环境隔离未通过。均保留原包、真实范围及共享信任精确恢复，不发展独立语言测试项目、不因显示编码误判而改写成果。 |
| accord-continuation-reconcile-20260920-01；accord-rpc-recovery-reopen-20260920-01；accord-rpc-recovery-hosted-20260920-01 | 原RPC回读、同一scope/revision/lease未知效果收敛或新进程只读恢复；无重复派发，限定固定响应与原控制条件。不是跨控制者接管、断电或业务语义完整恢复。源文件和失败pending按各案原始身份保留。 |
| accord-host-upgrade-20260920-01 / -02及对应CI | 01版本预检失败保留；02同一暂停任务从0.154.0到0.155.1、失败候选拒绝/重试/卸载后保持，通过固定响应机制检查。不是自动升级、GUI采用或全A06。 |
| accord-entry-connection-20260920-01；accord-control-endpoint-20260920-01–04 | 固定0.155.1源码及私有目录、proxy字节隧道、标准WebSocket、物化任务/双订阅者条件。04保留1006关闭/强制监听器退出，不说优雅关闭；无真实模型。现有Desktop未由此取得控制权，不重复整轮调研或启动共享daemon。 |
| accord-owned-connection-20260920-01–03；accord-proposal-events-20260920-01；accord-source-context-20260920-01 | 分别限定真实流连接、已有有序后缀的提议回执筛选、首个usage前unknown及之后可观察。各案固定响应验证原版本机制，不代验模型择时、任意实时无空窗或GUI。 |
| accord-ws-handoff-20260920-01；accord-ws-listener-close-20260920-01 | 前者协议handed-off但退出码未知，整案非通过；后者独立确认所属监听器关闭，未重播交接。原生历史/SQLite侧文件与异常均保留。 |
| accord-semantic-handoff-20260920-01；accord-semantic-handoff-20260920-incident-01 | 子代理旧清理误删RPC/SQLite/verifier/冻结源，完整控制链验收引用已撤回。独立抢救的两份原生历史及匹配原哈希报告只支持有限模型行为/业务结果。不得恢复该旧清理代理、重建假回执或重跑来掩盖损失。 |

清理立即前核对实际写者、运行阶段、唯一证据和保留需求；子代理最终回复本身不排除队列写入。需要隔离时将审过成果转移到独立执行者拥有的路径再回收。不得按目录名删除证据、IDE工作区或用户要求保留的对话。此前163根顶层盘点、处理2个重复工作区和剩余13个候选的边界仍在旧索引，未自动授权全量删除。

本批独立复核后补存后置scope核对失败前的原生terminal，避免失败快照退回较早的turn/start回执；相应反例通过。子代理测试生成的4个pyc在全部写者停止后按实际枚举精确回收。此前还修正检查脚本的宿主结果读取假设；旧失败不冒充全绿，未走到的缓存替换步骤保持未执行。新CI复用同一隔离fixture补实际平台检查，不创建新模型试验。代码/测试体积上限2700000、171文件、主指导36000字节；本次增量用于同controller目标热接续、接收阶段事件处理和重复交接/settle故障检查，复用已有SDK与SQLite记录器，没有新增常驻服务、自研数据库或账号依赖。最新实际计量以verify-development为准，旧预算逐次经过保留Git，不作为当前上限。

尚存功能债务都沿既有W01–W08/A01–A08：普通入口实际采用、动态组合、自主连续性和未知效果恢复、入口最终集合、资源压力及组合净影响、发布材料。安装和局部读取成功不抵消这些缺口。Jev原直连初筛及两份外部报告勘误保留accord-jev-trial-20260919-01，classifier-dev固定94dd3ae只作为远程分类封装参考；未添加必需服务或默认调用，私人性能/费用不发布，也不重复试验。用户服务端密钥由用户管理。Laya固定42626c3的源码/模型说明核对及四个合成英文样本公开演示结果保留accord-laya-review-20260922-01；主分类符合预设但取消检查概率有否定误判，只支持窄观察，不代验全域准确性。r29将这些专用判断模型的接入及追加试用后置，不删除原件，也不将其变成3.3等待项。

本轮不把调用方自检或cleanup失误归给被测Agent：目录诊断客户端漏initialized已独立留证；caller首次空目录回收在遇到嵌套空目录时停止，随后逐一核对并仅清除8个空目录，原报告/成果不变。源码候选变化不倒改这些原始结果。

本批修正复杂度计量漏项：当前productCodeAndTestBytes纳入tests/product下的Node测试调用者，含此前已有carrier_handoff_host.cjs；Python产品模块/测试和随包runtime口径保持，开发scripts不属于该指标。旧字节数保留其原计量口径，不能拿旧静态PASS证明当前预算满足；在用候选按修正后统计重核。该修正不改变已执行协议或业务结果，不据此重复原生/模型试验。
