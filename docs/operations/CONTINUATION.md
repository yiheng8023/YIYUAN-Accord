# 当前接续

更新：2026-09-21 · N33-20260909 / r28。47d8e606的CI已结束，7项成功、4项失败；四个失败均为新增离线测试未规范化系统临时目录别名，已本地真实复现并修正，修复后的完整CI待核。Linux/macOS原生冷恢复及其独立artifact回读通过，原生结果与整个CI状态分开。资源/环境原案报告遗漏仍不准入，指导修正仍待必要行为核验。以实时Git、工具目录和当前receipt为准。
[计划与工序](PLAN-v3.3.md#当前推进顺序)拥有共识与路线；[基线](BASELINE-v3.3.md)、[验收](ACCEPTANCE-v3.3.md)与product/development.json分别展开结果、判据及机器投影。

## 目标、共识和授权


**当前继续开发：2026-09-19用户确认调研及勘误共识，要求按需对齐基线、计划、验收和README后直接实施。Jev邀请不是开发前提；采用其适用方法但不添加必需评估服务、固定provider顺序或零资源成本承诺。降低不必要第三方依赖，继续按价值复用宿主、工具和成熟实现。**

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

CI节奏共识已按9月20日用户确认写入计划：本地小改/针对性核验与提交可以及时进行，相关变更形成完整工作段后再集中推送，避免尚未完成的有效全矩阵反复被取消。必要平台覆盖和最终候选门槛不变；纯接续记录不触发无价值重跑。最近完整绿色仍为ac5dd3e8；47d8e606失败与本批修复分别保留。后续推送按工作段及实际验证需要判断，不回到每个对话小片立即推送。

## 当前事实

| 项目 | 已核事实与边界 |
|---|---|
| 仓库与写者 | 本批起点main与origin/main均为47d8e606、工作区干净。root修复两项测试的临时目录准备并增加轻量CI前置检查；Sol子代理独立回读成功的两平台冷恢复artifact后停止。产品runtime、安全检查与当前包身份均不变，相关修复和记录集中推送。 |
| 已安装开发包 | 3.3.0-dev.1+codex.20260921033628，22文件，SHA 8f749addccd25d111ebb6feaab7287009d2072dcaad109facdd48ff9ffe75213，Git市场ref=f3cf8951；5启用Skill/6受信任Hook。9月21日04安装完成，fresh MCP目录3工具；现存Desktop工具面仍2个只读工具，旧worker本轮读取当前context成功。不要求为本次CLI验证重启Desktop，不把fresh目录当GUI采用。 |
| 当前源候选 | 3.3.0-dev.1+codex.20260921132343，24文件，SHA 81c5ccd5426a9f60ef315e75cecae90ec006d2b789efbc19373f18fce2b94d07。增加已settle目标的新controller恢复与旧执行者标记失效；共享安装仍33628，源级机制与实际模型/安装采用分开。原资源/环境报告失败不改标。 |
| 实际采用 | 前轮用户重启后原任务调用inspect_task_state(contextAssessment)返回continue-bounded，sourceReleaseAllowed=false；旧epoch反例返回reassess。输入/状态字节保持。首次缺原生计数的unknown和之后有据评估分别留证。当时实际Goal读为null，仅证明当时无Goal。 |
| 当前任务状态 | session=01a09602-a44d-79f2-8ad6-d104863ca7d1；前轮快照turn=01a0c254-fad6-7e20-8d34-5ca30d315948、epoch=21f132d6-76b4-4091-a28a-7d136abec733；Astra/0.155.0-alpha.9.2，checkpoint unbound，35条捕获输入，needsNativeReplay/needsResumeReconciliation=false。上述是快照，后续写入须重读。自定义828400窗口不作为默认规格。 |
| 已完成CI | 精确47d8e606的[35606566345](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/35606566345)为7成功/4失败：5个Linux Python job及两个Native lifecycle通过，Windows/macOS的3.10/3.14均仅新增两项离线路径测试失败；原失败保留，修复CI另核。精确ac5dd3e8的[35595120028](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/35595120028)已11/11成功；e22fba76的[35586935086](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/35586935086)已11/11成功；268ae48b的[35578392461](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/35578392461)已11/11成功；b5bc28fb的[35569973358](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/35569973358)已11/11成功；f3cf8951的[35560235516](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/35560235516)已11/11成功，两平台MCP原件另行独立回读通过；前批7e08773c也11/11成功。前批Windows/macOS完整回归约38–43分钟；不因正常等待另触发矩阵。下一批精确状态按GitHub回查。 |
| 前批本地回归 | helper完整140/140；MCP完整37/37；开发契约87/87（185.942秒）。三项静态检查、插件/Skill校验、actionlint及源码/随包一致性通过。实际代码/测试2273747字节、160文件、主指导13654字节；局部通过不等于正式准入。 |
| 当前原生SDK组合 | accord-sdk-native-20260921-01的单次真实宿主固定响应组合通过，原始记录与独立复核保留；3项离线夹具与19项交付契约检查共22项通过，三项静态契约和actionlint通过。修正Node测试漏计后当前实际2555271代码/测试字节、171文件、主指导13785字节。两平台原生artifact已独立回读，13份冻结源码均逐字节匹配ac5dd3e8；各2次交接/10固定响应，exit0/forced=false/所属进程组absent，不将POSIX未知进程计数填成0。 |
| 当前SDK后续交接检查 | 同一connection + carrier + SQLite两次transfer、目标接收期context/nested拒绝、adopt当前refs/lease/idle目标、settle前后超时与不重放已检查；carrier31 + session12 + 包/交付契约25，共68项通过，三项静态契约通过。实际2472548代码/测试字节、169文件、主指导13785字节。零真实模型/宿主新实验，不作普通自主行为或完整A05判定。 |
| 前批SDK机制检查 | 真实connection + carrier core + SQLite组合通过；连接26、记录器7、session8、既有handoff29，共70项本地通过；开发契约87/87（148.531秒）通过。三项静态契约检查通过；原批实际代码/测试2437451字节、169文件、主指导13785字节。未调用真实模型或安装新包，不是A05整项/GUI准入。 |
| 当前场景检查 | 当前准入类19项中1项因新增范围后旧预期未同步而失败，原结果保留；修正后受影响2项通过。指导修正后三项直接入口/恢复检查通过，Skill/插件校验通过。真实任务观察与正式判定另列。 |
| 原生写入接线 | 三个隔离固定响应案、零真实模型。01/02被宿主审批拒绝；02 CLI覆盖键错误，所谓预批准实际未生效。03正确到达工具，缺receipt拒绝且没有状态写入；观察器误检查被宿主移除的isError而整案失败。原失败不改标；离线回读证实拒绝语义，脚本已按status/result/error修正，不重跑本例。 |
| 资源/环境真实结果 | 精确916ff322/f3安装包33628，CLI0.155.1/App Server/Terra medium；一条普通输入，403.712秒，无追加救场。1→1并发在160→96MiB真实Job预算下复用两项完成8项；CSV/512MiB原始展开内容及13原件hash/mtime独立一致。两worker及外层Job自然exit0/进程0；Goal前后null、实际default模式、当前完整指导送达，continuity/verify两Skill实际读取。原报告漏记后来的清理策略拒绝及处理，两个case整案均不准入。已解决的自检常量笔误另记，不据此判业务数据错误。 |
| 云环境 | 最近只读核对为YIYUAN-Accord、目录/workspace/YIYUAN-Accord，3个历史任务保留；universal、自动初始化、Agent网络关闭、缓存开启。当前新包云端行为未验证。 |
| 正式验收 | 17项必要scope，11项有定义、6项未绑定；定义不等于通过。4个OpenAI入口纳入开发、7个待判，selectionFinal=false。A01–A08整项完成仍0/8，functionalCompletion/candidateEligible=false；早期SDK子范围保留其原包身份。 |

## 本批实现与下一实际动作

CI修复：Windows RUNNER~1与macOS /var均是系统临时根的别名。两项新离线测试把别名直接送入严格ordinary目录检查，或与已解析文件路径比较，导致每个受影响job各1 error/1 failure。真实Windows短路径复现同样两错；仅将两项自建临时根resolve(strict=True)，同一复现2/2、完整离线组7/7及静态检查通过。安全检查、产品runtime和包身份未改。CI在完整回归前运行该轻量组，提前报相同准备错误；不跳过平台、用例或完整矩阵。此时计量2666313代码/测试字节、171文件、主指导13785字节；原批2666188保留原身份。诊断原件在accord-ci-diagnosis-20260921-01，空复现目录已清理。

新增manage_task_state复用既有bind/pause/retire和状态存储，不增加服务或业务文件执行器。原生元数据绑定根任务和turn，调用者保留已观察epoch/revision；helper在最终发布/删除前再次核对turn，涵盖人类输入epoch未变而宿主续作换轮次的情况。绑定保留暂停；解除用户暂停或取消仍需实际用户决定。理由、注解和metadata不是授权证明，不通过关键词或自报布尔值推断权限。

执行异常报告效果未知并要求查后态；超长成功结果保留精简成功回执，不把已执行写入说成未发生。MCP框架可以在调用前拒绝；不得为绕过拒绝改审批策略或换通道。隔离03使用进程内逐工具预批准只检验无receipt拒绝，不改共享配置、产品默认或沙箱。固定0.155.1源码说明CLI覆盖键左侧按点分割而非TOML引号解析；App Server把MCP isError映射成failed状态，结果本体不重复该字段。已有原始回执足够定位，不盲目重复试验。

当前冷恢复切片：claimScope只在已确认的inactive scope上原子旋转标记，不改writer/历史或清active transfer；restoreCodexSourceSession需要旧ACK中的expectedScope，准备核验后先claim/readback，再原生resume与后验。新标记在ready前及普通turn前后重核；旧basis跨实例不能重复resume，失效恢复对象不能fallback建新source。普通create/hot不要求未用claim能力。recorder10/session20/离线fixture7及交付/包契约25共62项通过，三项静态契约和actionlint通过。实际代码/测试2666188字节、171文件、主指导13785字节；代码/测试预算按本批必要恢复与验证实现调整为2850000，保留至少5%余量，不新增文件或主指导额度。

accord-sdk-restore-20260921-01由root独占执行一次：旧01只读复制ledger、三份session和keep，不复制host索引或Goal库。真实0.155.1/Node24.20.0以新controller恢复旧第三任务，7个RPC有唯一成功响应（initialize1/read4/resume1/turn1），无thread/start或新交接；一次原子claim先于resume，真实context工具调用成功，2个固定响应、0真实模型。两条settled transfer状态/revision不变，scope writer保持且token旋转，仅第三session追加一轮，另两份逐字节保持。Job自然exit0、forced=false、readerStopped、activeProcesses0，fixture停止；旧根完整nofollow inventory、执行源/保护原件/共享config保持。冷恢复仅针对已正常释放的controller，不证明crash、活跃transfer、未知业务效果、Goal迁移、自动择时或普通GUI采用。

可搬迁回读首次发现CI清单漏带workspace/keep.txt，原失败保留；补artifact路径后离线回读通过，没有放松检查或重跑宿主。原执行脚本、13份冻结源、RPC、ledger和native sessions均保留；两个全历史展开弃用提示和一个虚拟模型metadata fallback警告不隐去。运行时使用summary/excludeTurns，受控小历史展开仅用于独立核验。独立审查者停止后，由root核对并清理53份搬迁验证副本及空state/temp目录，原01与新01的必要证据保留，清理后回读仍通过。

本批原生SDK组合已执行一次：新增两个fixture复用既有_Fixture/_App/OS控制，13份执行源事前冻结；11份原有实现逐字节匹配e22fba76，2份新观察器按原执行字节保全。CLI0.155.1/Node24.20.0实际完成3任务、6个completed turn、2次transfer及2次adopt；29个RPC各有唯一成功回执，2次退订仅指向前两任务，两record均revision19/settled1且最终writer为第三任务。10次localhost固定响应、零真实模型；Job自然exit0/进程0、reader与fixture均停止，源码/keep/可执行文件/共享config前后hash保持。独立raw/SQLite/rollout回读通过；可搬迁artifact通过，重复响应/错误terminal/重复工具reply/错误writer四个副本反例被拒。原始context实际unknown，6个虚拟模型metadata fallback警告和3个分页全历史展开弃用提示保留；不作动态压力择时、语义/性能或GUI通过结论。

下一按依赖推进：

1. **沿剩余实际入口与恢复缺口推进。** target创建期工具绑定、接收阶段事件泵及显式adoptTarget已经接通，同一scope连续两次transfer、旧lease和未知settle不重放已有固定协议检查。Windows真实0.155.1组合已按冻结条件检查；CI继续复用同一夹具核对Linux/macOS差异，之后按必要业务范围补真实择时/语义接管。不得重复本次或已闭合的单步协议链。跨controller断线恢复仍未闭合，不将当前same-controller路径外推。
2. **保留已执行场景并验证候选修正。** 916ff322的唯一普通任务已执行、原失败和正确子事实已保全，不重跑批处理或事后改写原报告。当前修正明确：后续核验/恢复/清理改变事实时，应更新受影响的文件，聊天说明不能替代写回；原Skill已被读取，不能归因为没有触发，也不再加一条泛化提醒。修正属于指导候选，待后续必要组合行为核验；不另造全域错误账本、关键词解释器或强制每轮审查。
3. **完整工作段集成。** 原生写入工具的两平台拒绝/缓存替换与退出链已核实，既有小链不重复。当前新验收包依赖集已在运行前声明，排除未用的fresh传输/dispatcher实现和展示/法律资产；实际执行或后续影响超出集合须拒绝复用，不事后增删集合。余下fresh连续性、入口和组合工作继续按真实依赖推进。
4. **补剩余结果条件，复用已闭合证据。** 现有同任务压缩恢复、普通五轮链、宿主升级及固定交接协议保留原条件。A05的fresh适用路径与跨控制者未知效果恢复、跨入口选择、A07压力调整后必要续做和退出、A08组合/净影响仍未闭合。先复用官方能力和现有执行者；只为真实残余缺口补接线或试验。
5. **条件满足后发布3.3.0。** 前瞻绑定余下6个未定义scope及实际条件，完成必要行为、组合和独立审查，形成精确候选，校正README/发布说明并核对发布后态。已有条件授权不重复询问；未知和未完成不以局部绿灯抵消。

普通连续性当前路径是原生压缩→SessionStart/compact职责/状态恢复→按需补读原输入→核对实际后续动作。自然恢复原始2691–2915行及业务后续已留证；这支持有限同任务连续性，不是全历史无损或fresh接管。当前任务create_thread需用户明确新任务请求，handoff_thread不能搬自己，fork复制历史；不绕过这些具体接口条件，也不外推所有入口均不可实现。

fresh核心已有carrier-handoff.cjs、runHandoffProposal和stdio/WebSocket连接；原完整调用者及SQLite ledger此前只在测试中组装。本批新增随包codex-session.cjs创建源任务、注册两动态工具并泵事件，carrier-recorder.cjs用Node内置SQLite保存scope/revision/lease；无需集成方复制测试实现。仍要求实际获准且幸存的已初始化连接、当前权限/计划与独立语义核验，借用资源由原owner收尾；失败不重放、转移后源不可续写，当前新增同一controller下显式adoptTarget：核验record/当前目标/权限和effects后settle旧transfer，再以目标为source发起新的transfer。接收阶段的工具请求也被泵送，在途嵌套交接拒绝且不排队。实际模型择时与断线后的controller恢复仍未闭合。MCP状态工具不替代App Server控制，不新增常驻服务或私有IPC。官方loaded-thread resume可重放pending requests；另一个订阅者仍在时源连接关闭不等于释放。dynamicTools需thread/start注册，resume不补注册；排队用户消息也不是只读探测。

验收复用已支持前瞻packageFiles依赖集：纯function单入口可以保留未变依赖上的旧原包证据，版本只规范化默认cache时间戳；基础版本/语义依赖/依赖集合改变拒绝。生命周期、impact、多入口及A08仍要求当前整包；当前独立评审/重核保留。不回写旧定义以适配已执行结果，不把未选依赖当作无影响证明。

本次只读审查发现观察器可能在配置恢复失败时仍以0退出；已在真实模型执行前修正，并补当前Hook指导/原生mode/Goal/最终用量与资源后态核对。输入生成器从本次工具调用原文执行后留存，未冒称事前冻结；真实模型准备时与压缩原件一起冻结。机械预检属于较早工具身份；最终显式runtime-root、CPU查询和cache前后快照随后在普通任务中实际执行，保留各自精确身份，不重盖预检。

## 证据导航、历史限制与清理

原件默认在C:/Users/15521/.codex/backups/。详细旧经过及完整索引保留于[8d724a1b接续前态](https://github.com/yiheng8023/YIYUAN-Accord/blob/8d724a1b9d18dc15810ffc21896f0b8fdb8b5c8d/docs/operations/CONTINUATION.md)和[历史试验记录](PROCEDURE-v3.3.md)。本次删除接续页内互相冲突的过时“当前”段落及重复经过，不删除原始证据或重写历史结论。只按下一依赖读取对应原件，避免整页反复回放。

| 定位 | 可复用范围和限制 |
|---|---|
| accord-sdk-restore-20260921-01 | 单次真实宿主恢复旧01第三任务，旧根不写；新scope标记、原生resume和一次context调用及进程后态独立回读通过。retained含原生历史、13份执行源及必要prior副本，workspace原件随portable artifact保留；首次漏workspace的回读失败和修正另记。不是故障注入或完整A05；不要原地重跑。 |
| accord-sdk-restore-hosted-20260921-01 | 47d8e606的Ubuntu/macOS冷恢复artifact各55文件，13份执行源码与原Git逐字节匹配；冻结checker和独立RPC/ledger/session/退出核对通过，0start/1resume/1turn/2固定响应，旧原件inventory保持、进程组absent。两个Native job通过不等于整体CI成功。 |
| accord-ci-diagnosis-20260921-01 | 保留35606566345的四个失败job日志、短路径真实复现脚本及修复后结果；原问题为测试目录别名，未改原生机制或放宽安全检查。空复现根已清理；修复后托管结论另核。 |
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

尚存功能债务都沿既有W01–W08/A01–A08：普通入口实际采用、动态组合、自主连续性和未知效果恢复、入口最终集合、资源压力及组合净影响、发布材料。安装和局部读取成功不抵消这些缺口。Jev原直连初筛及两份外部报告勘误保留accord-jev-trial-20260919-01，classifier-dev固定94dd3ae只作为远程分类封装参考；未添加必需服务或默认调用，私人性能/费用不发布，也不重复试验。用户服务端密钥由用户管理。

本轮不把调用方自检或cleanup失误归给被测Agent：目录诊断客户端漏initialized已独立留证；caller首次空目录回收在遇到嵌套空目录时停止，随后逐一核对并仅清除8个空目录，原报告/成果不变。源码候选变化不倒改这些原始结果。

本批修正复杂度计量漏项：当前productCodeAndTestBytes纳入tests/product下的Node测试调用者，含此前已有carrier_handoff_host.cjs；Python产品模块/测试和随包runtime口径保持，开发scripts不属于该指标。旧字节数保留其原计量口径，不能拿旧静态PASS证明当前预算满足；在用候选按修正后统计重核。该修正不改变已执行协议或业务结果，不据此重复原生/模型试验。
