# MCP 任务状态调用指南

本文的三个状态工具与3.3.2包另加的 `coordinate_task_execution` 分工不同。后者用于原生Skill库存、受托输入准备及有限新目标执行；最终`ef8bde2a`已完成原绑定18案/17scope/52义务及A01–A08来源消费、Root采用和精确11/11 CI。公开发行与本机实际参与后态见[当前接续](operations/CONTINUATION.md#当前事实)；旧案例、源码声明或缓存存在均不证明所有入口完成。按需读取包内[能力接口](../plugins/yiyuan-accord-codex/skills/coordinate-capabilities/references/native-capabilities.md)或[接管接口](../plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/references/native-handoff.md#ordinary-root-task-through-the-mcp-execution-interface)，不能把下文状态参数模板用于派发执行。

适用对象：维护者、原生 MCP 接入者及消费此指南的 Agent。原调用模板依据源码 `315e2476e4818545d0dbb6a2c241be72b01ceae4`；输入隔离补充依据 `73120669` 与2026-10-06原生回执对账。

状态及输入读取本身不写检查点或业务文件、不派发新任务；共享 MCP 处理器仍会核对本进程已有所属执行，来源失效时可保护性停止它并保留操作证据。因此两个读取工具不声明为全环境只读；直接 helper 的 `status` 仍是只读查询。

## 调用前：取得可用的最新观察

先通过宿主已获授权的原生 MCP 路径调用 `inspect_task_state`，参数为 `{cwd: absoluteWorkspace}`。确认返回 `checkpoint.state === "observed"`，读取 `checkpoint.snapshot` 的当前 `epoch`、`revision`、完整合同、pause 与恢复标志。每次管理调用都取同一次最新观察的 epoch/revision；更新后的 revision 再 inspect 取得。旧 `checkpoint.epoch` 是上次绑定依据，不可替代 snapshot.epoch。缺失或不可用观察保持未决。[读取实现](../runtime/native-state-mcp.cjs)、[snapshot](../runtime/task-checkpoint.cjs)。

`cwd` 是调用者选择的绝对工作区；inputs 路径与每个 outputs.path 均相对该工作区。管理共同必填字段是 cwd、action、epoch、expectedRevision。当前 root/session/turn 身份由原生调用元数据提供；调用者 arguments 不填 session_id、threadId、nativeTurnId 或伪造 metadata。后代共享 session 的身份差异会被拒绝。[参数与身份 guard](../runtime/native-state-mcp.cjs)、[相对路径](../runtime/task-checkpoint.cjs)。

若细节标为 `omitted-bounded-result`，先读 `checkpointSource.path` 的完整字节，对实际解析的同一份字节计算 SHA-256 并比对 checkpointSource.sha256，取得完整合同。保存文件只有基线/谓词；当前业务文件观察需另行检查。依赖动作前再次 inspect 并核对当前输入、epoch、revision、digest、pause 与恢复标志；变化或未知仍未决，不能把省略字段当空值。[超长返回](../runtime/native-state-mcp.cjs)、[架构：完整状态与有界返回](architecture.md#current-candidate-and-scoped-connections)。

## 输入隔离不等于本轮正文缺失

Codex multi-agent v2 的根会话文件也可能带第二个 UUID 后缀，子代理文件则可能没有该后缀。3.3.3 兼容修复（先在 `3.3.2-dev.21` 验证）对带后缀路径要求明确的 v2 元数据，并核对文件名首 UUID、`meta.id`、`meta.session_id` 与绑定线程一致；继续要求根来源字符串白名单，拒绝子代理分类及非空父线程/代理路径。原生调用的 thread/tree 隔离不变，后缀本身不提供身份或权限。

保留窗从原输入的 `turn_context` 开始，紧前 `task_started` 可能已在窗外，因此不新增“必须读到首次启动事件”的条件。后续容量重试、恢复、人类与 App 消息续轮仍按各自归属链核验；输入摘要、暂停、读取预算、文件变更和提交前复核均保留。旧版 `capacity-retry-subagent-rollout` 也可能来自合法的新格式根会话，须核对实际元数据后更新兼容实现，不能重写回执、变更线程身份或清除水印来放行。

当前实现沿用3.3.2开发期加入的机制：在有原生轮次校验的健康bind中，将`nativeInputOriginProof`随检查点一次原子保存；它绑定当时的精确回执、输入基准、epoch、session和工作区，仅供再次核验时定位原生来源。客户端不传此字段，只读inspect不保存它，也不修改输入回执。普通查找窗仍为16 MiB，保留证明后的原锚点至当前末尾验证窗仍为32 MiB；旧basis、漂移、暂停或超过验证窗都不会因已有proof而自动放行。该机制不滚动原锚点，也不独自证明无限连续性或接管完成。

`includeNativeInputs:true` 的证据摘要过大时，`nativeInputEvidence.details` 为 `omitted-bounded-result`，保留真实来源、完整性和恢复标志，并给出各列表的 `counts`；列表和对账 cursor 被省略，不表示空输入或已读完。按其 `detailRead` 使用可用、兼容的现有 helper 执行只读 `status` 请求，保持相同的宿主环境和状态存储选择。核对返回的 storage、epoch、revision 及原生来源/宿主，再读取完整证据与需要的源部件；任何变化或不可用仍待核。只有取得并审查完整来源后，才使用其新鲜 cursor 对账。回退不安装组件、不改共享配置、不写状态，也不授予新的权限；helper 路径不可用时保留未决并寻找已获授权的兼容入口。

`needsNativeReplay=true` 表示助手的输入基准尚不能用于绑定或续轮，不单独证明本轮正文漏收。先区分 `inputReceipt.present`、`failureWatermarkScopes` 和 `inputSource`，再将捕获文本与实际当前任务的原生输入、身份及轮次核对。完整捕获可以与 `quarantined-native-input` 同时存在；这既不是恢复成功，也不是输入必然缺失。

未能确定会话归属的工作区故障标记会影响同工作区尚未确认该标记的会话。旧标记只含 generation 时，文件时间不能补出原事件、原会话或丢失内容。不得因新会话、标记较旧或当前正文完整便删除共享标记、设置自动过期或宣称旧责任已恢复。

`SessionStart(source=startup)` 也不单独证明此前没有输入。已核官方 `rust-v0.161.0` 在部分启动错误路径先运行 UserPromptSubmit，再于后续正常轮次消费待执行的 startup；若先前输入传输失败，可能只留下匿名工作区水印，没有本会话回执。不能将随后 startup 看到的 generation 自动记为已确认基线。已有回归覆盖这个顺序，以及按会话核对后只恢复本会话、仍保共享水印和其它暂停任务的既有路径；没有新增自动初始化或清理接口。

实际需要恢复本任务时，使用既有最新 recovery epoch 与宿主保留的真实当前输入，按该会话进行核对和恢复；不能从哈希重构输入，也不能借此解除其他会话的隔离或暂停。不要为改判已结束案例而事后重放。只停止依赖该未恢复输入基准的动作；助手恢复状态、独立来源证明的当前任务事实和其他已授权职责分别记账，不把局部隔离误报为全宿主故障或完成。

已捕获的多纯文本按当前轮次、原生 part 种类/数量和真实捕获 hash 核对；不按版本猜测拼接。每个原始 part 保留独立描述，仍经已有 enrichment/sourcePart/reconcile 完成覆盖；后续 Skill 原文独立待核，未捕获证明的多文本保持 unsupported。

原生 `ContextCompaction` 完成通知按当前线程、局部轮次及具体 item 核对：输入起点可越过该通知，但控制摘要与上下文代际仍记录压缩；旧计量失效后须有新观察，不因通知解除暂停或补造输入。

所有依赖保存合同的普通状态变更都先核同一份结构/身份规则；无效 checkpoint 保留并报告，不因空谓词而自动退休。

容量错误后的宿主`resume_interrupted_task`仅在此前精确`server_overloaded`及完整容量消息、同Root归属、空parent/agent、有序context、原输入及恢复/暂停守卫全部成立时参与容量证明。触发名称本身不解除真实中断或暂停，也不授予新权限。

## 已有输入依据下的原生 App 消息续轮

正常完成后的 `app_tool_send_message` 轮次与容量重试不同。已有可核输入依据时，适配器联合核对原生启动归属、接收 turn/context/cwd/model，以及同轮 `codex_app/send_message_to_thread` 入站记录。发送方 root 可以不同于接收 turn；各轮完成事件必须保持其实际归属。仅有触发名称、XML 文本或普通 stdout 均不足以建立关联。带 `call_id` 的本地调用结果不能充当入站委派证明。

该关联保留原输入 anchor、回执和人类文本 hash，不把工具正文转换为 `UserPromptSubmit` 或新的授权。原暂停、恢复隔离、权限、来源字节及提交前复核仍适用；调用者须核对消息的真实职责、已发生效果和必要授权。连续工具轮次及与合法容量重试的混合链均需完整有序证明，容量边的原错误与归属约束不变。

已识别的入站任务记录进入控制摘要。使用旧 cursor 协调、提交或进行来源一致性重读时，迟到的任务记录不能作为普通工具输出自动放行。它们仍不进入人类输入记录列表；`latestNativeInputsComplete`、执行关联、授权与业务完成分别判断。

无既有回执、输入 basis 或可信原生来源定位的工具冷启动不由此分支解决。不能伪造用户输入、移动旧 anchor 或清除失败水印来补齐它；独立核实真实指令后已获授权的只读工作，与依赖绑定的写入分别处置。

## bind：每次完整绑定当前合同

五字段每次必填且不默认继承：`result` 是当前受托、待实现的完整目标及范围；`inputs` 是完整受保护输入列表（无保护输入时 `[]` 合法）；`outputs` 是完整非空输出谓词列表；`nextAction` 是具体下一动作；`canContinue` 兼容保留为当前安全且已授权工作是否仍可进行的判断记录，不触发新回合或执行。输入与输出合计最多 100 项；path-only 输出仅检查文件，精确要求用 sha256 或 JSON Pointer 值谓词表达。[schema](../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs#L102)、[bind guard](../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs#L392)。

`result` 跨工作段保留总体目标；阶段成果、版本和 CI 进度放在 `nextAction`、必要的 `unresolved` 及有来源的结果记录中。必要重绑或恢复时核对这些字段是否仍服务同一目标；局部工序完成或局部等待只影响其依赖，不替代完整目标，也不阻断独立可做工作。目标确因实际用户决定或已授权范围变化而改变时，核实依据和影响后修订；文字变化本身既不证明也不否定授权。运行时只保存正文，不判断目标语义。

以下模板只生成 MCP tools/call 的 params，不连接、不调用工具、不自动判断 permission。`latest` 必须是真实最新 inspect 结果的 structuredContent（或宿主规范化结果中已解析的同一对象）；所有文字、路径、布尔判断由接入者按当前任务证据填入。准备参数后若输入或状态变化，重新 inspect 并审查。禁止用本指南里的占位名称当任务事实。

```js
function bindParams(latest, absoluteWorkspace, reviewedContract) {
  const snapshot = latest.checkpoint.snapshot;
  return {name: "manage_task_state", arguments: {
    cwd: absoluteWorkspace, action: "bind",
    epoch: snapshot.epoch, expectedRevision: snapshot.revision,
    result: reviewedContract.result,
    inputs: reviewedContract.inputs,
    outputs: reviewedContract.outputs,
    nextAction: reviewedContract.nextAction,
    canContinue: reviewedContract.canContinue
  }};
}
```

`reviewedContract` 必须含已审查的全部五字段：inputs 是完整相对路径列表（确认无保护输入才填 []），outputs 是完整非空谓词列表。模板逐项选取字段；既有变更所需的可选修订字段按下文实际审核后添加到 arguments。既有绑定重新提交仍需五字段。`canContinue: false` 适用于等待必要用户观察、决定、授权或外部条件；未完成项目或 mode=active 不足以支持 true。false 不表示完成、取消或用户 pause，也不阻止后续用户输入。[可行性记录语义](../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs)。

保存合同的 `checkpoint.inputs` 含 `{path, observed}` 指纹对象；重绑参数 `inputs` 则只接受相对路径字符串。核对保护和变更处置后取各项 path，不直接把保存的对象列表作为参数，也不省略已有保护。首次绑定的 snapshot 可为 mode=unbound、revision=0、checkpoint=null；仍须有真实输入及可用恢复标志，再提交完整的新合同。

修订输出谓词需 `revisionReason`；变更或移除旧输入需每个受影响输入的 `inputRevisions: [{path, observed, reason}]`，observed 精确匹配当前 inspection.inputs[].current 指纹；不存在文件为 `{present:false}`，存在文件为 `{present:true, sha256}`。初始绑定或新增保护不需此处分；额外/重复处分会失败。核对实际用户决定和受影响范围，再提交完整合同。[输入修订](../runtime/task-checkpoint.cjs)、[合同修订](../runtime/task-checkpoint.cjs)。

`unresolved` 省略才继承旧未决条件；显式列表替换它们，移除/重述旧条件需 revisionReason 和事实或授权范围变更依据。任何未决条件阻止 verified-local 与成功退役。重绑保留旧 pause；仅在实际恢复授权成立且 prior.mode=paused 时附非空 `resumeReason` 解除。reason 文字不是授权证据。恢复隔离/输入丢失不是 resumeReason 能解决的条件；本管理工具不 replay 或 recover-lock。[未决与恢复规则](../runtime/task-checkpoint.cjs)。

## reconcile-input：审查来源后对账并重绑

当返回 `native-input-reconciliation-required` 时，以同一工作区调用 `inspect_task_state` 并传 `includeNativeInputs: true`。核对实际 root/turn、宿主、输入依据、待处理记录、来源及覆盖；按需读取原始内容并审查用户意图和授权。没有可信来源、可用 cursor 或受支持内容时保持未决。上文超长回退须先取得完整证据，不把省略列表当空值。

`read_task_input` 可用该观察的 `nativeInputEvidence.cursor`，结合记录的 `recordOffset`、`recordSha256` 和有序 part 的索引读取 `sourcePart`；必须提供同次 `snapshot.epoch` 作为 `expectedReceiptEpoch`，不能同时传 `index`。文本按 Unicode 字符分页，`maxChars` 默认 4000、最大 16000，后续使用返回的 `next`。受支持的单个 inline PNG 可作为临时图像内容返回，受既有 8 MiB 输入字节预算约束；不读取包装路径或抓取远程 URL。读取、字节覆盖、理解和授权分别判断，不产生回执写入或解除隔离。[读取 schema 与 guard](../plugins/yiyuan-accord-codex/runtime/native-state-mcp.cjs)。

```js
function sourcePartParams(latest, absoluteWorkspace, reviewedRecord, partIndex) {
  const snapshot = latest.checkpoint.snapshot;
  return {name: "read_task_input", arguments: {
    cwd: absoluteWorkspace, expectedReceiptEpoch: snapshot.epoch,
    sourcePart: {evidenceCursor: snapshot.nativeInputEvidence.cursor,
      recordOffset: reviewedRecord.recordOffset,
      recordSha256: reviewedRecord.recordSha256, partIndex}
  }};
}

function reconcileInputParams(latest, absoluteWorkspace) {
  const snapshot = latest.checkpoint.snapshot;
  return {name: "manage_task_state", arguments: {
    cwd: absoluteWorkspace, action: "reconcile-input",
    epoch: snapshot.epoch, expectedRevision: snapshot.revision,
    evidenceCursor: snapshot.nativeInputEvidence.cursor
  }};
}
```

仅在实际审查完待处理输入及覆盖、权限和身份后提交对账；适配器从原生调用元数据取得身份，继续检查轮次、来源与 cursor，不能由参数伪造。它写入本任务输入回执并生成新 epoch，不写业务文件、不触发执行，也不解除 pause、恢复标志或水印。成功后重新 inspect，按新 epoch 和最新 revision 审查并完整 bind 上述五字段；旧合同不会自动重绑。失败或传输不确定时先核对后态，不能盲目重试。对账不证明语义理解、用户授权或完成。[对账实现](../plugins/yiyuan-accord-codex/runtime/task-checkpoint.cjs)。

## pause：保存暂停及未完成条件

pause 需要已有 checkpoint、当前 epoch/revision 及非空 reason；写 mode=paused、revision 加一并保留合同。先确认当前暂停决定和责任，不把等待观察时的 canContinue=false 自动解释成用户暂停。[pause](../runtime/task-checkpoint.cjs)。

```js
function pauseParams(latest, absoluteWorkspace, verifiedPauseReason) {
  const snapshot = latest.checkpoint.snapshot;
  return {name: "manage_task_state", arguments: {
    cwd: absoluteWorkspace, action: "pause",
    epoch: snapshot.epoch, expectedRevision: snapshot.revision,
    reason: verifiedPauseReason
  }};
}
```

## retire：有证据及授权才移除本任务状态

调用者先核对真实目标完成证据，以及当前仍适用的用户授权与宿主批准；同一目标、范围内未撤销的既有授权继续有效，无须重复确认。管理器只核当前输入、非paused状态、本地谓词及未决条件；`verified-local` 不证明目标语义或外部验收。

显式用户取消另需已核实的取消决定，并提交 `disposition: "user-cancelled"` 与非空 reason；字段仍是调用者声明。无 checkpoint 时只退役 receipt：先确认 snapshot.mode=unbound、revision=0、`needsNativeReplay=false`、`needsResumeReconciliation=false`，当前输入已协调，再提供非空 reason。只移除本任务 checkpoint/receipt 状态，不写业务输出。[退役实现](../runtime/task-checkpoint.cjs)、[限制](../runtime/task-checkpoint.cjs)。

```js
function retireParams(latest, absoluteWorkspace) {
  const snapshot = latest.checkpoint.snapshot;
  return {name: "manage_task_state", arguments: {
    cwd: absoluteWorkspace, action: "retire",
    epoch: snapshot.epoch, expectedRevision: snapshot.revision
  }}; // 正常已有 checkpoint 退役；其他分支按上文补声明/理由
}
```

## 回查：区分未请求与效果未知

原生输入核验的内建来源失败带 `nativeInputDiagnostic`，可随 `native-input-evidence-unavailable` 或原生续轮关联的 `native-call-turn-conflict` 返回；仅身份不符、缺少证明等未产生具体读源原因的拒绝不补造诊断。`stage` 为 `initial-validation`（首次核验）或 `commit-recheck`（状态提交/退役前复核），`readerReason` 为有限的内建来源原因；未知值统一为 `reader-reason-unavailable`。例如来源在读取后变化可得到 `transcript-path-changed-after-read`。helper 保留原退出码和错误行，并另输出一行同名 JSON；MCP 保留原 reason/isError/effect。任意异常属性、原始文本、路径和输入不会作为这些字段反射。没有该字段不等于核验成功，也不能猜测失败阶段。

这些信息用于定位被拒边界，不授予重试、恢复、放宽防护或新的权限；仍须核对实际输入、来源和操作后态。此修正不宣称已找出全部历史失败的触发原因，也不启用日志观察器。`inspect_task_state` 的运行时指纹包含 `manageTaskState` 和 `nativeInputDiagnostic`，可核本次改变的已加载函数；它们仍不覆盖闭包、常量、整个软件包或其它进程。

bind 缺参返回 `invalid-task-state-binding`、requiredFields/missingFields 及 `effect: "not-requested"`：该 guard 在 operate 前拒绝，补齐并重新取得最新观察，不宣称业务已变更。真正进入 operate 后的异常带 `effect: "unknown-check-post-state"`，reason保留对应诊断原因；实际 mutation 后传输失败也可能丢失成功回执。两者先 inspect 后状态并核对保留证据，再决定下一安全动作；已发生或未知效果先对账，不能自动重试，不能一概声称零写入。成功但细节超长返回精简成功回执；回查完整合同。[guard/执行](../runtime/native-state-mcp.cjs)、[传输边界](../runtime/native-state-mcp.cjs)。

宿主拒绝可能发生在 adapter 前；按实际 disposition 保留未完成工作，不能换策略或路线绕过拒绝。App Server 的工具错误有结果，宿主拒绝无结果；其规范化结果不重复原始 MCP isError。管理记录、原生 metadata、工具 annotations、原因文字及本地谓词均不证明 permission、当前意图、写者所有权、接管或外部验收。[架构：调用身份与效果边界](architecture.md#current-candidate-and-scoped-connections)。

验证边界：本指南按源码静态核对，模板仅做隔离参数构造核对；未调用真实 MCP 状态、模型业务、CLI 或 SDK，未建立新信任。本指南的静态核对本身不提供普通模型行为或真实宿主接入证据；产品当前已验证范围及限制见[当前接续](operations/CONTINUATION.md#当前事实)。本指南不是新增 case 或 F-A 通过证据。
