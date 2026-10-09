# MCP 任务状态调用指南

适用对象：维护者、原生 MCP 接入者及消费此指南的 Agent。原调用模板依据源码 `315e2476e4818545d0dbb6a2c241be72b01ceae4`；输入隔离补充依据 `73120669` 与2026-10-06原生回执对账。

## 调用前：取得可用的最新观察

先通过宿主已获授权的原生 MCP 路径调用 `inspect_task_state`，参数为 `{cwd: absoluteWorkspace}`。确认返回 `checkpoint.state === "observed"`，读取 `checkpoint.snapshot` 的当前 `epoch`、`revision`、完整合同、pause 与恢复标志。每次管理调用都取同一次最新观察的 epoch/revision；更新后的 revision 再 inspect 取得。旧 `checkpoint.epoch` 是上次绑定依据，不可替代 snapshot.epoch。缺失或不可用观察保持未决。[读取实现 174–207](../runtime/native-state-mcp.cjs#L174)、[snapshot 757–785](../runtime/task-checkpoint.cjs#L757)。

`cwd` 是调用者选择的绝对工作区；inputs 路径与每个 outputs.path 均相对该工作区。管理共同必填字段是 cwd、action、epoch、expectedRevision。当前 root/session/turn 身份由原生调用元数据提供；调用者 arguments 不填 session_id、threadId、nativeTurnId 或伪造 metadata。后代共享 session 的身份差异会被拒绝。[参数与身份 guard 309–376](../runtime/native-state-mcp.cjs#L309)、[相对路径 1269](../runtime/task-checkpoint.cjs#L1269)。

若细节标为 `omitted-bounded-result`，先读 `checkpointSource.path` 的完整字节，对实际解析的同一份字节计算 SHA-256 并比对 checkpointSource.sha256，取得完整合同。保存文件只有基线/谓词；当前业务文件观察需另行检查。依赖动作前再次 inspect 并核对当前输入、epoch、revision、digest、pause 与恢复标志；变化或未知仍未决，不能把省略字段当空值。[超长返回 246–267](../runtime/native-state-mcp.cjs#L246)、[架构 110–117](architecture.md#L110)。

## 输入隔离不等于本轮正文缺失

`needsNativeReplay=true` 表示助手的输入基准尚不能用于绑定或续轮，不单独证明本轮正文漏收。先区分 `inputReceipt.present`、`failureWatermarkScopes` 和 `inputSource`，再将捕获文本与实际当前任务的原生输入、身份及轮次核对。完整捕获可以与 `quarantined-native-input` 同时存在；这既不是恢复成功，也不是输入必然缺失。

未能确定会话归属的工作区故障标记会影响同工作区尚未确认该标记的会话。旧标记只含 generation 时，文件时间不能补出原事件、原会话或丢失内容。不得因新会话、标记较旧或当前正文完整便删除共享标记、设置自动过期或宣称旧责任已恢复。

`SessionStart(source=startup)` 也不单独证明此前没有输入。已核官方 `rust-v0.161.0` 在部分启动错误路径先运行 UserPromptSubmit，再于后续正常轮次消费待执行的 startup；若先前输入传输失败，可能只留下匿名工作区水印，没有本会话回执。不能将随后 startup 看到的 generation 自动记为已确认基线。已有回归覆盖这个顺序，以及按会话核对后只恢复本会话、仍保共享水印和其它暂停任务的既有路径；没有新增自动初始化或清理接口。

实际需要恢复本任务时，使用既有最新 recovery epoch 与宿主保留的真实当前输入，按该会话进行核对和恢复；不能从哈希重构输入，也不能借此解除其他会话的隔离或暂停。不要为改判已结束案例而事后重放。只停止依赖该未恢复输入基准的动作；助手恢复状态、独立来源证明的当前任务事实和其他已授权职责分别记账，不把局部隔离误报为全宿主故障或完成。

## bind：每次完整绑定当前合同

五字段每次必填且不默认继承：`result` 是当前授权结果；`inputs` 是完整受保护输入列表（无保护输入时 `[]` 合法）；`outputs` 是完整非空输出谓词列表；`nextAction` 是具体下一动作；`canContinue` 兼容保留为当前安全且已授权工作是否仍可进行的判断记录，不触发新回合或执行。输入与输出合计最多 100 项；path-only 输出仅检查文件，精确要求用 sha256 或 JSON Pointer 值谓词表达。[schema 73–105](../runtime/native-state-mcp.cjs#L73)、[bind guard 330–360](../runtime/native-state-mcp.cjs#L330)。

以下三段是调用参数模板：只生成 MCP tools/call 的 params，不连接、不调用工具、不自动判断 permission。`latest` 必须是真实最新 inspect 结果的 structuredContent（或宿主规范化结果中已解析的同一对象）；所有文字、路径、布尔判断由接入者按当前任务证据填入。准备参数后若输入或状态变化，重新 inspect 并审查。禁止用本指南里的占位名称当任务事实。

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

`reviewedContract` 必须含已审查的全部五字段：inputs 是完整相对路径列表（确认无保护输入才填 []），outputs 是完整非空谓词列表。模板逐项选取字段；既有变更所需的可选修订字段按下文实际审核后添加到 arguments。既有绑定重新提交仍需五字段。`canContinue: false` 适用于等待必要用户观察、决定、授权或外部条件；未完成项目或 mode=active 不足以支持 true。false 不表示完成、取消或用户 pause，也不阻止后续用户输入。[可行性记录语义](../runtime/native-state-mcp.cjs#L100)。

保存合同的 `checkpoint.inputs` 含 `{path, observed}` 指纹对象；重绑参数 `inputs` 则只接受相对路径字符串。核对保护和变更处置后取各项 path，不直接把保存的对象列表作为参数，也不省略已有保护。首次绑定的 snapshot 可为 mode=unbound、revision=0、checkpoint=null；仍须有真实输入及可用恢复标志，再提交完整的新合同。

修订输出谓词需 `revisionReason`；变更或移除旧输入需每个受影响输入的 `inputRevisions: [{path, observed, reason}]`，observed 精确匹配当前 inspection.inputs[].current 指纹；不存在文件为 `{present:false}`，存在文件为 `{present:true, sha256}`。初始绑定或新增保护不需此处分；额外/重复处分会失败。核对实际用户决定和受影响范围，再提交完整合同。[输入修订 641–670](../runtime/task-checkpoint.cjs#L641)、[合同修订 674–723](../runtime/task-checkpoint.cjs#L674)。

`unresolved` 省略才继承旧未决条件；显式列表替换它们，移除/重述旧条件需 revisionReason 和事实或授权范围变更依据。任何未决条件阻止 verified-local 与成功退役。重绑保留旧 pause；仅在实际恢复授权成立且 prior.mode=paused 时附非空 `resumeReason` 解除。reason 文字不是授权证据。恢复隔离/输入丢失不是 resumeReason 能解决的条件；本管理工具不 replay 或 recover-lock。[未决与恢复规则 1274–1280](../runtime/task-checkpoint.cjs#L1274)。

## pause：保存暂停及未完成条件

pause 需要已有 checkpoint、当前 epoch/revision 及非空 reason；写 mode=paused、revision 加一并保留合同。先确认当前暂停决定和责任，不把等待观察时的 canContinue=false 自动解释成用户暂停。[pause 824–834](../runtime/task-checkpoint.cjs#L824)。

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

显式用户取消另需已核实的取消决定，并提交 `disposition: "user-cancelled"` 与非空 reason；字段仍是调用者声明。无 checkpoint 时只退役 receipt：先确认 snapshot.mode=unbound、revision=0、`needsNativeReplay=false`、`needsResumeReconciliation=false`，当前输入已协调，再提供非空 reason。只移除本任务 checkpoint/receipt 状态，不写业务输出。[退役实现 815–845](../runtime/task-checkpoint.cjs#L815)、[限制 1277](../runtime/task-checkpoint.cjs#L1277)。

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

bind 缺参返回 `invalid-task-state-binding`、requiredFields/missingFields 及 `effect: "not-requested"`：该 guard 在 operate 前拒绝，补齐并重新取得最新观察，不宣称业务已变更。真正进入 operate 后的异常带 `effect: "unknown-check-post-state"`，reason保留对应诊断原因；实际 mutation 后传输失败也可能丢失成功回执。两者先 inspect 后状态并核对保留证据，再决定下一安全动作；已发生或未知效果先对账，不能自动重试，不能一概声称零写入。成功但细节超长返回精简成功回执；回查完整合同。[guard/执行 309–388](../runtime/native-state-mcp.cjs#L309)、[传输边界 459–480](../runtime/native-state-mcp.cjs#L459)。

宿主拒绝可能发生在 adapter 前；按实际 disposition 保留未完成工作，不能换策略或路线绕过拒绝。App Server 的工具错误有结果，宿主拒绝无结果；其规范化结果不重复原始 MCP isError。管理记录、原生 metadata、工具 annotations、原因文字及本地谓词均不证明 permission、当前意图、写者所有权、接管或外部验收。[架构 118–135](architecture.md#L118)。

验证边界：本指南按源码静态核对，模板仅做隔离参数构造核对；未调用真实 MCP 状态、模型业务、CLI 或 SDK，未建立新信任。普通模型行为与真实宿主接入仍未验证。本次是已有仓库交付补充，不是新 case 或 F-A 通过证据。
