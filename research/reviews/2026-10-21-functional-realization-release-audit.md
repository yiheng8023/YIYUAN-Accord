# 按需功能可实现性与发布依据复核

2026-10-21。复核来源为主仓 `519d1a9ea378afa8b56532ef91d3cd2ffaa5ef58`、3.3.1发行源 `28d78e2b0ebadaefdac8e1f1382148dab72e207f`、当前安装、原始行为材料和正式准入报告。本次不执行新业务、安装、登录、迁移或发布；研究记录不修改历史资格、发行标签或第三方源。

## 当前结论

**动态按需原则成立，但没有发生调用不能证明该能力在需要时可用。现有材料不足以维持“全部必要功能已经达到设计预期”的无条件结论。** 已发布、CI成功以及18案/17scope形式准入都是可核实的历史事实；它们不能替代原功能要求到普通入口可实现路径的证明。此前把这些事实作为整体设计完成的充分依据，把关不够。

这次不是要求每次调用所有工具，或穷举所有Skill和宿主版本。要证明的是：适用需求出现时能够发现需要，在普通支持条件下选到可执行路线、建立获准前提，并从结果和失败中闭环；不能通过苛刻前提、维护者专用控制器或“本次不需要”的判断，把必要分支永久排除。

用户本轮再次明确：所举功能不是核查全集；Skill协调针对一般默认显式调用的Skill，Matt只是实例。该通用要求与原PLAN第三方Skill条款相符，不是新增Matt专用功能。

## 已核的实现与证据边界

| 功能连接 | 原始正向与可达路线 | 本次未被证明的部分 | 判断 |
| --- | --- | --- | --- |
| 默认显式Skill的受托采用 | 10月11日Root自选retro与writing-for-agents，原生正文早于工具动作送达，接管报告实际采用。正常CLI输入支持所选`$skill`，不必修改第三方匹配开关 | 当前默认Desktop/IDE需要时自行发现并建立通用途径、对非Matt条目的适时选择及实际采用 | 有限正向成立；不能由单例或指导正文认定通用默认链已交付，也不能仅因没有专用MCP就认定不可实现 |
| 自主连续性与必要接管 | 原开发任务有三次真实压缩及随后有用续作；受控SDK还有提议、单写者转移及目标续作证据 | 默认普通入口在确需fresh接管时，自主判断、接通执行并由独立目标安全续作 | 健康同任务继续合理；它没有验证必要接管分支。未见必需迁移被漏办的原始反例，不等于该分支已验 |
| 发现外围能力 | 曾实际比较App Server、官方Python SDK、LangGraph、Temporal；实际选用已有Skill | 裸宿主普通需求中，自主识别缺口或改进机会、发现外部候选、形成有据建议并在授权后采用的完整链 | 现装能力使用、维护者方案研究及新的资格意见，不能相互替代 |
| fork、worktree等宿主能力 | 前身有真实fork链，开发中有隔离写者/复现CI的worktree使用 | 当前默认任务的触发充分性，以及调用是否由Accord带来 | 不强迫不必要调用；调用存在不自动证明Accord因果贡献。fork、工作树、压缩、fresh接管用途不同 |

Skill源策略和用户停用仍须遵守。默认`allow_implicit_invocation:false`是宿主匹配限制，不独立构成禁止受托选择；官方说明显式调用仍有效。确有禁止或不可用条件时，应暴露受限功能和可行替代，不能伪造人类点名或改变源策略来制造成功。[OpenAI Docs](https://learn.chatgpt.com/docs/build-skills#optional-metadata)。详细原件和通用途径见[Skill来源核查](2026-10-21-codex-skill-coordination-boundaries.md)。

## 具体的验收映射问题

1. **A05的总通过超过了直接可见的子范围证据。** 原[验收表](../../docs/operations/ACCEPTANCE-v3.3.md#L105)分别要求无人提醒的风险发现、健康继续、必要迁移与独立接管，并规定缺完整链只通过已验子项。机器投影把A05仅映射到`v33-autonomous-continuity`，该scope只有`v33-autonomous-continuity-live-development-01`一个case。正式报告的该原资格仍明确：`Original lack of necessarily triggered durable Root transfer, independent wakeup ... remains unknown`，列为`outside-case-claim`。历史健康继续有据，但不能据此宣称必要接管分支已被普通入口证据覆盖。
2. **聚合检查不能自行发现语义漏项。** [admission.py第1513–1547行](../../yiyuan_accord/admission.py#L1513)核已定义case、职责/质量/情境标签及缺失scope，生成`functionalCompletion`和A01–A08完成状态。这对已绑定定义有用，但如果必要路径没有成为足够明确的case判据，或来源审查把它放到范围外，标签全齐仍可能全绿。问题位于原要求、机器投影、来源判断与整体结论之间；不能只增加计数或修一处调用。这不独立证明聚合算法有bug；需要追查将仍必要的责任裁定为`outside-case-claim`的依据，以及它为何被认为足以支持总通过。
3. **新资格决定不是新功能执行。** routing-02的新段确实改变Root工作表，有真实后果；其`newBusinessExecution=0`和`newHostOrPluginManagement=0`也同样真实。它合法保留历史行为的身份，不能被读作新版本刚完成普通Skill调度或外围发现。复用证据本身没有错误，错误是超出原主体、路径、条件和后果解释它。
4. **当前职责未因记录限制而自动取消。** PLAN仍要求裸宿主能力发现、必要接续路径和非技术用户无需救场；10月16日版本更明确写过不能因GUI控制/无存活恢复者唤醒未实现而缩小必要职责签发布。后期摘要保留限制或删去旧段落，不独立构成用户批准取消功能。用户明确撤回的Stop自动续轮另当别论，不据此要求任意停止后的自动唤醒。

以上足以撤回“设计预期已经全面达标”的判断；尚不足以断言所有实现都无效、所有默认路线都不可达，或擅自改签原始资格与不可变发行。

## 全部F/A关系的影响检查

本次已核全F01–F08与A01–A08映射；下表不是重新签发各功能的通过证书，也不是新增测试清单。

| 结果 | 关联验收与已有材料 | 本次影响处置 |
| --- | --- | --- |
| F01 目标/授权 | A01；真实steering、CLI交付及父交付材料 | 保留原正向。核查子任务路由/接管时原目标和委托是否完整继承，不因本次A02/A05问题直接作废 |
| F02 能力选择与组织 | A02；能力盘点、routing、Skill原生采用 | 通用显式Skill协调、外围发现和默认可达性存在上述关键未证；总完成结论需重核 |
| F03 自主推进/恢复 | A03；实际工具失败恢复、暂停及继续 | 保留原作用域；受控执行、必要用户决定、可避免催促与普通轮次结束分别判断，不以撤回Stop代替恢复能力 |
| F04 全程纠偏 | A04；原steering及system-integration | 本次反例已触及映射和发布判断，应修正现行解释；原有效纠正和历史失败均保留 |
| F05 连续性/接管 | A05；健康同任务续作与受控SDK转移 | 分开已验分支与普通必要接管的未证；不能由未触发推出具备，也不能强行迁移造正例 |
| F06 环境/生命周期 | A06；包更新、加载/采用及环境恢复 | 安装与当前MCP采用原证据保持；若选择/控制桥依赖额外条件，必须纳入交付、失败与退出责任 |
| F07 成品/资源 | A07；CLI成品、压力/资源及退出 | 原成品不重建。独立资源释放仍需守所有权；子CLI、控制连接或临时能力引入后不能漏算维护和退出 |
| F08 系统/发布 | A08依赖A01–A07；现有限影响评价 | 上游必要功能有未证，整体完成解释不能直接沿用。`incrementalValue=unverified`原限制保持；CI、源码下载和安装证明不补功能缺口 |

## 后续应修的对象

先以原必要结果检查设计→触发→发现→前提建立→执行→反馈/恢复→验收的对应关系。可达但未采用时，先判断当时是否确有适用需要、充分授权及合理触发条件；只有确认遗漏，才定位并修正指导、选择或执行连接。前提无法在默认支持环境建立的，改适配机制或如实提交功能受限决定；证据遗漏的，补原要求范围内的必要验证；投影或聚合扩大结论的，修映射及发布判定。不能先统一归因宿主、靠改措辞收官、把用户重新发提醒当自动恢复，也不另建全量路由平台或强制每个工具演示。

本次未作产品修改或重签资格；既有正式准入与发行保留历史身份，其支持整体功能完成的充分性因上述缺口待重新裁定。是否需要实现修复，仍取决于进一步定位。后续处理以具体受影响连接为对象，复用仍有效原件，不重跑已闭业务，不用新版本号或更多文档代替功能结果。

## 关键原件

- `C:/Users/15521/.codex/backups/accord-global-document-release-quality-20261021-01/qualification-refresh/ADMISSION.json`：`report.acceptanceRequirements`、`currentApplicability/v33-autonomous-continuity-live-development-01/original/qualification/knownFailuresAndLimits`及routing-02。原`functionalCompletion=true`、`candidateEligible=true`保留，不改原文件。
- `product/development.json#/acceptance/admission`：18个case、17个scope及A01–A08映射；A05仅绑定自主连续性scope。
- `plugins/yiyuan-accord-codex/skills/maintain-task-continuity/SKILL.md:103–123`、`references/native-handoff.md:1–31`：同任务恢复与fresh转移的连接区别，调用者负责择时，安装不供应普通Desktop/IDE控制连接。
- `C:/Users/15521/.codex/backups/accord-r23-semantic-20261015-01/r3-review/r3-verdict.json:784,997,2205,2223`；`root-adjudication.json:111–126`：真实压缩/续作及普通择时/迁移限制。
- `C:/Users/15521/.codex/backups/accord-current-applicability-20261019-01/current-reuse-autonomy/root-context-assessment.json:39–65`：当时`continue-bounded/fits`，不是fresh接管或未来容量保证。
- `C:/Users/15521/.codex/backups/accord-scope-qualification-finalize-20261020-02/current-qualification-decision.json`及`decision-worklist-effect.json`：新资格判断和实际工作表效果。
- `C:/Users/15521/.codex/backups/accord-final-source-assembly-20261021-01/coverage-source-facts-final.json:8186–8208`：有限必要职责与动态UI/生态未知的边界；它不是所有能力未来按需可用的证明。
- `C:/Users/15521/.codex/backups/accord-capability-use-map-20261019-01/actual-use-map.json`：受控提议/接管、现装Skill和MCP的实际贡献。
- `C:/Users/15521/.codex/backups/accord-capability-options-20260912/decision.json`、`docs/operations/PROCEDURE-v3.3.md:87–91,1782–1784`：外围方案比较及前身fork原始来源导航，保其提示和因果边界。

本次三个独立调查分别负责Skill/宿主语义、连续性、能力发现/因果归属；Root核对机器聚合、A05直接映射、原资格限制和文档历史。调查均未新增模型业务样本。报告写入不构成新产品能力或新通过条件。

另由Astra高强度独立质疑上述判断：确认必要接管证据与A05总通过不相称；不支持据此断言Skill实现缺失、聚合算法有bug或全部验收失效。已据其反证收紧本报告：相同关键策略/调用条件的通用适用性不按作者穷举，未采用先核是否应采用，影响复核不等于全部推翻重验。
