# DevDay 后 ChatGPT/Codex 变化对 Accord 3.3 收尾的影响

核验时点：2026-09-30，Asia/Shanghai；官方原文抓取于 11:39–11:41。研究基点：`main` / `b8fcaf4d15074674d3abe548ea63f23f455cd926`，开始及写入前 `HEAD...origin/main=0/0`、工作树干净。本文只作来源研究和工程判断，不是宿主采用、案例准入或发布凭证。

**结论：应继续收敛现有 3.3 职责，优先比较原生机制。** 新文档提供了持续委派、事件触发和托管会话的候选，但没有证明当前账号具备这些条件，也没有证明它们承担了 Accord 的身份绑定、未知效果保护、单写者接管和退出责任。最先改变下一动作的是协调位置和真实版本的绑定；不应先增加适配器、事件服务或调度器。

研究以 [September 28–October 2, 2026](https://learn.chatgpt.com/docs/whats-new/september-28-october-2-2026) 为导航，实际读取下列具体文档及原文。周报标题覆盖未来日期，不能据此把所有功能认定为已于 9 月 28 日全量上线。没有明确发布日期的文档，只证明本次读取时的公开契约。下文“官方契约”表示来源明示；“工程判断”表示对 Accord 的有限推论；“未知”表示尚无该账号/控制者/精确包的行为证据。

## 1. Cloud 的协调位置决定配置消费与恢复承担者

**官方契约。** 当前 Codex Cloud 以发布的准备文件系统创建独立任务，已有任务保持自己的文件；Install script 与 Start skill 是准备/启动通道。仓库 Skills 可用，本机个人 Skills 不同步；默认 VM 状态可恢复至上次启动轮次或恢复后最多七天。Legacy 仍承接 Code Review、Linear/GitHub 集成。[Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)

Work Sync 的适用新任务采用云协调；旧任务不升级。设备在新轮次开始时不可用，可改用云容器，但不能在一轮中途切换，也不能继承本机文件、工具及企业执行要求。[Get started with ChatGPT Work](https://learn.chatgpt.com/docs/get-started-with-work#continue-work-across-devices)

云协调下，本机配置、插件及命令 Hook 不受支持；local-only Work/Codex 保留其支持的本地 Hook。Work Cloud local access 和 dots 的管理员 remote MCP Hook 另受 managed policy、remote hooks 及账户条件限制。MCP Hook 不启动/重连 server，SessionEnd 不支持；错误、超时等不等于阻断工具。[Hooks](https://learn.chatgpt.com/docs/hooks#mcp-tool-hooks)

**工程判断。** PLAN 已于 9 月 30 日纳入这一边界，本文复核，不另开 Cloud 重试。原本机 stdio runtime 的发现或成功调用不能证明云协调器采用；Start skill 也未被证明是每轮职责入口。发布快照与任务保存可以替代重复准备的一部分，但不能替代关键状态、效果和恢复来源核对。

**下一条件/未知。** 先找到同一实际控制者受支持的指导、身份、状态和恢复组合，再核入口 UI/权限与退出。当前账号能否使用该组合、Accord 状态能否保留仍未知；不创建或发布环境。适用来源：[Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)、[Work 跨设备](https://learn.chatgpt.com/docs/get-started-with-work#continue-work-across-devices)、[Hooks](https://learn.chatgpt.com/docs/hooks#managed-hooks-from-requirementstoml)。

## 2. Dots 是原生持续责任候选，停止语义仍须逐层对账

**官方契约。** Dots 可跨对话保存 notes、主动暂停/唤醒并委派 Work/Codex 任务；自己的云电脑可持续运行。当前 dot 使用 GPT-6 Astra，逐步开放。其个人电脑连接独立于 Codex 连接和 Work Sync。Pause 只停主任务；委派和定时任务分别停止，停止不会撤销已完成动作。[Meet dots](https://learn.chatgpt.com/docs/dots)

**工程判断。** 这是对自建固定唤醒/持续协调层的实质替代候选；需比较已有职责的同等效果和生命周期后再缩减实现。它不是现有 SDK 源会话的自动升级，也未证明提供 fresh 接管、单写者或未知效果对账。Dots 的云协调 Hook 限制沿用上项。[Meet dots](https://learn.chatgpt.com/docs/dots)、[Hooks](https://learn.chatgpt.com/docs/hooks#managed-hooks-from-requirementstoml)

**下一条件/未知。** 先只读核当前账户可用性、控制者和责任链；实际 dot 尚未创建/连接/采用。原生候选不新增入口 ID 或改判现有 scope。本任务主模型仍按用户选择的 `gpt-6.1-sol` 绑定；dot 的产品模型不能据此改变主任务模型。[Meet dots](https://learn.chatgpt.com/docs/dots)

## 3. MCP Events 与 Plugin Extensions 改变触发和交互，不提供全生命周期保障

**官方契约。** MCP Events 要求 MCP 2.0，ChatGPT 当前仅支持 webhook 投递；用户指定监测对象和动作。`2xx` 是接收回执，处理异步；事件可能乱序/重复，`cursor=null` 的漏失不能通过协议恢复。server 须持久保留订阅，并处理刷新、撤权及 unsubscribe。[MCP Events](https://developers.openai.com/plugins/build/mcp-events)

**工程判断。** 有授权的事件监测可比较原生订阅与轮询成本；事件回执不能冒充业务完成、当前输入身份或恢复确认。不能仅把 Accord stdio 改为 HTTP 就推定具备这些语义。当前无外部事件任务，先不建 server 或订阅。[MCP Events](https://developers.openai.com/plugins/build/mcp-events)

Plugin Extensions 提供 sidebar、对话 panel、文件查看/编辑、设置、forms 和模型与 App context 通道；composer mention 限桌面，Free/Go web 扩展仍属 coming soon。[Plugin Extensions](https://developers.openai.com/plugins/build/extensions)

**工程判断/未知。** UI 通道可降低特定交互负担，但文档没有给出 Accord 所需的可信 session/epoch、接管或效果恢复保证。功能表面清点应补识别这些通道，实际使用仍随任务选择；当前没有足以要求新增 Accord 面板的缺口。[Plugin Extensions](https://developers.openai.com/plugins/build/extensions)

## 4. Agents API 的托管执行框架 可减少新应用的编排负担，不能代验已选 SDK 路线

**官方契约。** Agents API 由 OpenAI 运行 Codex执行框架，保存 session 配置、turn 和 items，提供自动 compaction、multi-agent 与 MCP；Agents SDK 则让应用负责部署、存储、审批和集成。这些 session 与 sandbox 是不同资源。[Agents：运行时比较](https://developers.openai.com/api/docs/guides/agents#compare-agent-runtimes)

官方恢复流程要求先查 session/turn/items 与已完成效果。失败 turn 可能已写文件或调用外部工具；流断开不证明终态，继续前须查保存状态。[Errors and recovery](https://developers.openai.com/api/docs/guides/agents-api/errors#recovery)

**工程判断。** 对未来获准的 API 应用，托管会话可替代部分私有 agent loop、历史保存和压缩编排；仍须补业务权限、效果对账及收尾。它与本版已选本地 SDK、app-server、普通插件路径不同，不能把文档当现有机械交接链已被替代或 A05 已通过。[Agents](https://developers.openai.com/api/docs/guides/agents)、[Errors and recovery](https://developers.openai.com/api/docs/guides/agents-api/errors)

**下一条件/未知。** 只有现有缺口确实需要新的托管运行时，才绑定 API 账户、预算、执行位置、状态和清理后比较。本次没有这项实施任务，也没有 API 调用或费用。文档未独立建立其首次发布日期，本文不把它写成 DevDay 当天才新增。[Agents](https://developers.openai.com/api/docs/guides/agents)

## 5. CLI 0.159 的输入/启动变化要求更新精确条件，不扩大重验

**官方契约。** 9 月 29 日 changelog 列：0.159.0 增加 opt-in `instant_interrupt`，可在模型响应或长 code-mode 调用中接受新输入；0.159.1 更新 `gpt-6.1-sol` 目录默认；0.159.2 修复 Windows 后台/沙箱命令的短暂 console 窗口。0.159.0 还移除自动 follow-up suggestions 与 bundled plugin-creator。[ChatGPT & Codex changelog](https://learn.chatgpt.com/docs/changelog)

**工程判断。** 后续案例绑定真实调用者版本与实际开关，重点重验受影响的输入、暂停、在途效果和启动边界；官方修复不证明 Desktop 内置版本已升级或当前闪窗同因。移除 plugin-creator 不表示 Accord Skills 被移除。重启、reload 和更换消费者仍按既有生命周期执行；Root 的本机 05 更新与闪窗核验承担实际证明。[Changelog](https://learn.chatgpt.com/docs/changelog)

新模型/Ultrafast 的可见性不构成当前选择或购买条件；本次保持用户已选主模型，不新增 $500 套餐或模型业务。[本周官方更新](https://learn.chatgpt.com/docs/whats-new/september-28-october-2-2026)

## 对当前收尾的最小处置

1. 继续已具备条件的普通交付、连续性和组合收敛；先复用真实宿主压缩/持久状态，再补未承担的责任，不等待新产品全部调查。
2. 入口判断沿原本地/远程主机、托管执行、交互/触发三线处理；云协调访问本机、local-only Work、Remote、新 Codex Cloud/Legacy 保留各自控制者，pending 不因发布信息晋升。
3. Dots、Events、Extensions、Agents API 作为已识别候选；只有它们能解决实际缺口且取得相应权限时进入实例比较。现有实现只在同职责效果及生命周期证据充分后替换。
4. 由 Root 完成本机真实版本/更新证明，按精确依赖核受影响机制；不把新闻、目录、安装或局部回执认定为功能采用。

仓库依据：[AGENTS](../../AGENTS.md)、[PLAN 当前入口边界](../../docs/operations/PLAN-v3.3.md)、[当前推进顺序](../../docs/operations/PLAN-v3.3.md#当前推进顺序)、[CONTINUATION](../../docs/operations/CONTINUATION.md)、[development 投影](../../product/development.json)。当前仍为 17 必要 scope、10 活动 case，完整 A01–A08 未闭合，`functionalCompletion=false`、`candidateEligible=false`。这些标准及旧失败身份保持；本文没有更新任何准入状态。

## 来源与留存

主要来源共 10 个，均实际读取；网页 `.md` 不被浏览工具支持时，直接抓取官方原始 Markdown。S08 初始猜测路径及 S10 的 `.md` 返回 404，失败记录保留；随后找到真实官方入口并成功抓取，不用失败路径支撑结论。外部新闻、演示和二手材料未作为证据。

原文及带 UTC 抓取时间、内容类型、字节数的清单保存在 `C:\Users\15521\.codex\backups\accord-devday-impact-20260930-01`；原始清单保留失败尝试，`source-manifest-recovered.json` 记录 S08/S10 的成功补读。SHA-256 校验原始下载字节，不是正文解释的正确性证明。

| ID | 官方来源 | 保存文件 | SHA-256 |
|---|---|---|---|
| S01 | [本周更新](https://learn.chatgpt.com/docs/whats-new/september-28-october-2-2026) | S01.md | `4BB49CE26492A01291DC9FADEC611D62CBF64BE00202753EEB299409562D2BCA` |
| S02 | [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments) | S02.md | `94343705B3F9A527DD824F873F86A2DBBF0F0B3FE430EE62132BECF29969E536` |
| S03 | [Get started with Work](https://learn.chatgpt.com/docs/get-started-with-work) | S03.md | `98B032A4C12A8D38A5F5CF95B3AF2CEAF542DB6483E9E2E6DBEB8ED434B19577` |
| S04 | [MCP Events](https://developers.openai.com/plugins/build/mcp-events) | S04.md | `6EC59370AAB08E5C8C6925C2635C6D003971B8B65E0317329E52315EFDD72F70` |
| S05 | [Meet dots](https://learn.chatgpt.com/docs/dots) | S05.md | `8C2CA0CBDF2D2B2B70E8D7DBD99977E9EEE844310100A5894CA8DD8470D2D640` |
| S06 | [Plugin Extensions](https://developers.openai.com/plugins/build/extensions) | S06.md | `69B4AE4586373160B2593DF0C095CB232CC438F347AA47515463DFEBC58BF55F` |
| S07 | [Hooks](https://learn.chatgpt.com/docs/hooks) | S07.md | `724881D81F1A9FDB35EA42D4851A11B1F6606BBC6E9D2D05C1E8C466FC25C630` |
| S08 | [Errors and recovery](https://developers.openai.com/api/docs/guides/agents-api/errors) | S08.md | `115F09F9E461B09E6563478B7198369F925826BF50E1CFDE04C211FC7AA869F5` |
| S09 | [Agents](https://developers.openai.com/api/docs/guides/agents) | S09.md | `DF4F61B609550619A3F9E445C66D28318B9F681AFFE1A819EF0098CDE32BF43A` |
| S10 | [Changelog](https://learn.chatgpt.com/docs/changelog) | S10.html | `427C4A6A56BF7528C243525E9F72DC93713CC9AE89DFD8767E41261E8B4DA44E` |

本研究只新建本文件与上述取证留存；没有提交、推送、安装、启用、Cloud 创建、账户连接、外部写入或模型任务。Root 负责集成审查，本文不据此新增实施授权。
