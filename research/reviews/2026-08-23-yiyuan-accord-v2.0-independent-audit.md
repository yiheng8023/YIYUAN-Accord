# YIYUAN Accord v2.0 全维度独立审计报告

**报告性质：** 从零开始、只读、固定 SHA、独立分析审计  
**审计日期：** 2026-08-23（UTC+08:00）  
**auditedSha：** `2b2b5fbc90f9659c48853d84ae0600f66329ad02`  
**仓库：** https://github.com/yiheng8023/YIYUAN-Accord  
**精确提交：** https://github.com/yiheng8023/YIYUAN-Accord/commit/2b2b5fbc90f9659c48853d84ae0600f66329ad02  
**GitHub Actions：** https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/32605119408  

---

## 0. 模型条件

**界面可见条件（由用户在本任务中明确给出）：**

- 模型：**GPT-5.6 Sol**
- 推理档位：**Pro**
- 本任务中未提供界面可见的降级提示

本报告不声称能够验证隐藏服务端路由、内部 fallback、请求级调度或未向用户显示的模型状态。

---

# 1. 执行摘要

## 1.1 一句话总判断

> **当前精确 SHA 已经是一个结构收敛、边界诚实、适合继续做外部独立审计与普通 Codex Cloud 精确验证的候选基线；但它尚未满足 v2.0 公开发布和有限收官条件，主要阻断点不是核心架构失控，而是零余量复杂度预算、证据独立复核、文档生命周期闭环、阶段导航一致性，以及尚未完成的外部门。**

## 1.2 两个 Go / No-Go

| 问题 | 结论 | 说明 |
|---|---|---|
| 当前 SHA 是否适合作为继续外部审计与普通 Codex Cloud 验证的候选基线 | **GO（有条件）** | SHA 固定、公开可访问、`main` 在审计时指向该 SHA、三系统 Actions 成功、8/8 criteria、两套静态 host-check 与 11/11 tests 在托管日志中通过；当前没有发现 P0。 |
| 当前是否已经满足 v2.0 公开发布与有限收官条件 | **NO-GO** | 普通 Codex Cloud 的该 SHA 任务时验证尚未完成；针对该 SHA 的具名人类发布授权、v2.0 tag、GitHub Release、公开面复验和最终清理均未发生；此外仍有发布前 P1 需处理。 |

## 1.3 总体评价

### 已经做对的部分

1. 产品名称、slug、Python 模块、插件路径和主要公开表面已经迁移到 `YIYUAN Accord / yiyuan-accord / yiyuan_accord`。
2. 广义使命与当前可验证产品面分离得较清楚：
   - 广义使命：改善 human-AI collaboration；
   - 当前产品面：human-Agent collaboration。
3. `constitution / program / acceptance` 三份语义权威已形成清楚分工。
4. 当前实现没有扩张成 Runtime、Hook、MCP、App、身份系统或控制平面。
5. Codex 与 Claude Code 保持为可替换参考宿主，而非 portable core。
6. 行为评估保留 GT-07、GT-08 的失败，未改写为成功。
7. 静态检查、代表行为、托管验证、具名人类授权、公开发布和生产证明被明确区分。
8. 路径、symlink、JSON、Git 子进程、插件包表面和自证边界的静态防护总体扎实。
9. 两个月试错已经较系统地沉淀为 K1–K5、H1–H10、L1–L7 和 Golden Tasks。

### 仍需发布前收口的部分

1. `productCodeAndTestBytes` 恰好达到 `120000` 硬上限，零余量不可作为长期可维护状态。
2. `requiredTestCount` 被固定为恰好 `11`，会对新增必要回归测试产生反向激励。
3. `CONTEXT.md` 自称“canonical domain language”，但又不是三份语义权威之一，存在事实上的第四语义源风险。
4. `CONTINUATION.md` 在这个已经提交并推送的精确 SHA 中仍写“下一门是提交候选”，其静态导航状态已经落后于实际 Git 事实。
5. 当前行为证据具有较强的内部完整性绑定，但源记录本质上仍是由同一目标载体整理的可发布事件摘要；在 release gate 之前需要独立的人类/第二观察面与原始宿主记录对照。
6. README 的安装和启用说明基本准确，但升级、禁用、卸载、回滚与常见故障诊断仍不完整。
7. “Python 3.10 或更高”目前只在 GitHub Actions 中固定测试 Python 3.10，支持声明应收窄或扩展版本矩阵。
8. 普通 Codex Cloud、具名人类授权、tag/release、公开复验和最终清理尚未完成。

---

# 2. 审计范围、方法与材料完整性

## 2.1 固定代码基线

本次只审计：

`2b2b5fbc90f9659c48853d84ae0600f66329ad02`

没有以审计期间继续变化的默认分支内容替代该 SHA。

已核验：

- 提交公开可访问；
- commit message：`feat: reshape as YIYUAN Accord v2.0`；
- 父提交：`6d857517455b6f3f86a4c9cbd79fc618febbbe00`；
- tree SHA：`6bce328d256674000644beb5465f43a33e3b7e87`；
- diff 统计：3479 additions、3340 deletions、6819 total changes；
- commit 未签名；
- 审计时 `main` 指向该 SHA；
- Actions run `32605119408` 的 `head_sha` 为该 SHA，结论为 success。

主要来源：

- Commit API：  
  https://api.github.com/repos/yiheng8023/YIYUAN-Accord/commits/2b2b5fbc90f9659c48853d84ae0600f66329ad02
- Branch API：  
  https://api.github.com/repos/yiheng8023/YIYUAN-Accord/branches/main
- Actions：  
  https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/32605119408

## 2.2 阅读顺序

本次按用户指定顺序完成：

1. `README.md`、`README.zh-CN.md`、`CONTEXT.md`
2. `product/constitution.json`
3. `product/program.json`
4. `product/acceptance.json`
5. `yiyuan_accord/`
6. `tests/product/test_product_control.py`
7. `.github/workflows/validate.yml`
8. `.agents/plugins/marketplace.json`
9. `plugins/yiyuan-accord-codex/`
10. `plugins/yiyuan-accord-claude/`
11. `evals/golden-tasks.json`
12. `evals/evidence/2026-08-22-v20-representative-source.json`
13. 七份 2026-08-22 v2.0 observation
14. architecture、continuation、security、support、contributing、release notes、license surfaces
15. `research/reviews/` 三份非权威材料
16. YIYUAN-CALIBRATION 固定研究快照
17. OpenAI、Codex 开源源码和 Claude Code 当前官方资料

## 2.3 审计方法

本报告持续区分：

- **事实：** 可从精确 SHA、托管日志或官方资料直接确认；
- **推断：** 从多项事实组合得到，但不是仓库直接声明；
- **评价：** 对设计质量、风险和发布状态的专业判断；
- **建议：** 尚未成为产品权威的整改输入；
- **未知：** 当前材料无法证明。

本次没有：

- 修改仓库；
- 创建 issue、PR、branch、tag、release；
- 安装插件；
- 部署；
- 写入外部系统；
- 把研究报告中的指令当作本任务指令。

## 2.4 无法独立核验的项目

1. 未能在本审计容器中重新 clone 并执行全部命令，因此 Actions 结果是通过公开 workflow/run/job 日志核验，而不是本地二次执行。
2. 无法访问 X 帖子正文：  
   https://x.com/goan999999/status/2090076819815026918  
   因此不能评价该帖具体主张。
3. 无法通过本次工具完整列举 GitHub Releases/Tags API；但：
   - acceptance 中 release authorization 仍为未请求；
   - release notes 使用未来时态；
   - Actions checkout 日志没有显示 v2.0 发布完成证据；
   - 未找到 v2.0 公开 release 的直接证据。  
   因此“尚未发布”具有强支持，但最终发布状态仍应在 release gate 中用 GitHub API 再核验。
4. 普通 Codex Cloud 的该 SHA 验证记录未提供。
5. 行为 evidence bundle 没有附原始、不可选择性编辑的完整宿主日志或外部签名；其真实性需要 exact-local independent review 进一步确认。

---

# 3. 当前产品事实快照

| 事项 | 结论 | 类型 |
|---|---|---|
| 产品名为 YIYUAN Accord | 已确认 | 事实 |
| slug 为 `yiyuan-accord` | 已确认 | 事实 |
| Python 模块为 `yiyuan_accord` | 已确认 | 事实 |
| compatibility aliases 为空 | 已确认 | 事实 |
| 广义 mission 面向 human-AI | 已确认 | 事实 |
| 当前 product scope 限于 human-Agent | 已确认 | 事实 |
| 当前不是 Runtime / control plane / sandbox / permission system | 已确认 | 事实 |
| `main` 在审计时指向 audited SHA | 已确认 | 事实 |
| audited commit 父提交为 v1.2 SHA | 已确认 | 事实 |
| audited commit 未签名 | 已确认 | 事实 |
| GitHub Actions 三系统 job 全部成功 | 已确认 | 事实 |
| workflow 使用 Python 3.10 | 已确认 | 事实 |
| verifier 报告 8/8 criteria | 已确认自托管日志 | 事实 |
| Codex/Claude host-check 为 static-ready | 已确认自托管日志 | 事实 |
| static-ready 等于行为已验证 | 不成立 | 事实/边界 |
| product tests 11/11 通过 | 已确认自托管日志 | 事实 |
| tests 无 skip / expected failure | 已确认自托管日志 | 事实 |
| production code + product test bytes = 120000 | 已确认自托管日志 | 事实 |
| 120000 等于当前硬上限 | 已确认 | 事实 |
| 七个 release sample 中 GT-01~05 通过 | 已确认 | 事实 |
| GT-07、GT-08 保留失败 | 已确认 | 事实 |
| GT-07 四项 exclusion 已进入 release notes | 已确认 | 事实 |
| GT-08 official-guidance exclusion 已进入 release notes | 已确认 | 事实 |
| GT-07/08 按当前 acceptance 必须阻断 release | 不成立 | 事实 |
| GT-07/08 限制对应宿主/行为主张 | 成立 | 事实 |
| 普通 Codex Cloud exact-SHA gate 已通过 | 无证据 | 未知/未完成 |
| v2.0 具名人类 release authorization 已取得 | 否 | 事实 |
| v2.0 tag / release 已完成 | 未找到证据 | 未完成/待 API 最终核验 |
| 当前已证明 production deployment safety | 否，release notes 明确排除 | 事实 |

---

# 4. 产品定位与核心命题评估

## 4.1 名称与使命是否清晰

### 事实

`README` 与 `constitution` 均把：

- human-AI collaboration 作为广义使命；
- human-Agent collaboration 作为当前有限产品面。

`CONTEXT.md` 也定义：

- Agent 是具有 goal-directed loop 的系统；
- 普通 AI/model 不因能生成输出就自动成为 Agent；
- 当前 verified product scope 只覆盖 human-Agent。

### 评价

**清晰且不冲突。**

这种二层结构比把所有 human-AI 问题都塞入 v2.0 更诚实，也有利于控制发布主张。

### 建议

保持不变。只需在 README 首页用一句更短的中文/英文对照强化：

> 广义使命面向人类与 AI；v2.0 可验证产品面只覆盖人类与 Agent。

不要再扩范围。

## 4.2 YIYUAN Accord 作为名称是否合适

### 评价

名称是合理的：

- “Accord”强调协议、共识、责任与边界；
- 不暗示 Runtime、控制平面或强制治理；
- 比旧名更符合“协作可靠性契约”的产品形态。

### 结论

**保持名称，不建议再次重命名。**

## 4.3 核心原则

当前 K1–K5、H1–H10、L1–L7 已把两个月试错中的高价值规律压缩为：

- 目标优先；
- 最小充分路径；
- 人类权威；
- 持续校准；
- 结果闭环；
- 官方/原生优先；
- effective capability；
- unknown；
- host drift；
- outcome over process；
- subtraction before repair；
- progressive assurance；
- help + interference；
- failure retained；
- retirement。

### 评价

这组原则已经足够，**不建议新增新的永久原则层**。后续经验优先进入：

- Golden Task；
- regression；
- claim boundary；
- maintenance trigger；

而不是继续增加核心条款。

---

# 5. 用户启用路径与 README 渐进式披露审计

## 5.1 README 已经回答了什么

README 当前较快回答了：

1. 这是什么；
2. 不是什么；
3. 如何 clone 和运行 verifier；
4. 当前 release 状态；
5. 如何在本地 marketplace 中测试 Codex plugin；
6. 正式 tag 发布后的 Codex CLI 安装命令；
7. Claude Code 的 `--plugin-dir` 本地加载方式；
8. 如何确认 Skill 在新任务/会话中出现；
9. static readiness 与 behavior evidence 的区别。

### 评价

比旧版明显更面向用户，渐进式披露方向正确。

## 5.2 Codex 说明与当前官方机制的符合性

截至 2026-08-23，OpenAI 官方资料支持：

- repo/local marketplace；
- 修改本地 marketplace 后重启桌面端；
- `codex plugin marketplace add owner/repo --ref <ref>`；
- `codex plugin add PLUGIN@MARKETPLACE`；
- `/plugins` 浏览、安装、启用、禁用、卸载；
- 安装后新建 chat / CLI session 使 bundled Skill 生效。

因此 README 中的：

```text
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v2.0
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

与当前官方 CLI/源码一致。

官方资料：

- https://developers.openai.com/plugins/build/plugins
- https://learn.chatgpt.com/docs/plugins
- https://github.com/openai/codex/blob/8e649e3afa5cdddfb09a1b85a090b94775045d9b/codex-rs/cli/src/plugin_cmd.rs

## 5.3 Claude 说明与当前官方机制的符合性

Claude Code 官方资料支持：

```text
claude --plugin-dir ./my-plugin
/plugin-name:skill-name
/reload-plugins
```

`--plugin-dir` 是无需安装、面向本地开发与测试的加载方式。当前 README 对其“session-only”边界的表达基本正确。

官方资料：

- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/discover-plugins

## 5.4 发布前仍缺的用户生命周期

### P1 缺口

README 尚未完整覆盖：

#### Codex

- 检查安装状态；
- 禁用；
- 重新启用；
- 卸载；
- marketplace 更新/移除；
- tag 升级；
- plugin 未显示时的诊断；
- 安装后是否需要新会话/重启。

至少应补：

```text
codex plugin list --json
codex plugin remove yiyuan-accord-codex@yiyuan-accord
```

并说明可使用 `/plugins` 进行 enable/disable/uninstall。

#### Claude Code

- `--plugin-dir` 退出会话后不形成持久安装；
- 变更后 `/reload-plugins`；
- 如何用 `/help` 确认 Skill；
- 如何结束加载；
- 若未来引入 marketplace，应单独写持久安装/卸载边界，不与 `--plugin-dir` 混淆。

### 评价

这不是要增加产品机制，只是补齐已有机制的完整用户生命周期。它应在 v2.0 发布前完成。

---

# 6. 架构、代码质量、复杂度、安全与供应链审计

## 6.1 架构是否真正完成减法

### 事实

当前生产模块分为：

- `control.py`
- `evidence.py`
- `guardrails.py`
- `identity.py`
- CLI entrypoints

宿主投影仅包含：

- host-native manifest；
- `adapter.json`；
- 一个 Skill；
- Codex 的轻量 UI metadata。

没有：

- Runtime；
- Hook；
- MCP；
- App；
- state store；
-后台进程；
-永久能力 registry。

### 评价

**总体已经完成实质减法与合理模块化。**

不是“只改文档”；旧 generation-specific verifier path 已退出当前树。

## 6.2 隐藏复杂度

仍存在三类隐藏复杂度：

1. `surfaceMarkers` 和大量 exact-string contract；
2. `goalModePrompt` 重复列出阶段、criteria、release gates 和历史边界；
3. complexity 指标可能把复杂度推向 JSON、docs、evidence，而不仅是 Python code。

这些不是当前 P0，但属于 P2 维护风险。

## 6.3 120000 字节零余量专项判断

### 事实

托管 verifier 输出：

```text
productCodeAndTestBytes = 120000
maxProductCodeAndTestBytes = 120000
```

同时：

```text
requiredTestCount = 11
testsRun = 11
```

### 评价

**零余量不合理。**

原因不是 120000 这个绝对数字大或小，而是：

- 任何必要修复都可能先让 verifier 失败；
- 新增一个必要安全回归测试反而会破坏“恰好 11”；
- 维护者会受到“删测试、压缩可读性、把逻辑搬到未计量文件、直接调高预算”的错误激励；
- complexity budget 从护栏变成代理目标。

### 建议的处理顺序

1. **先做减法审查，不改标准：**
   - 删除重复 helper；
   - 合并重复结构验证；
   - 把可由数据 schema 表达的重复代码数据化；
   - 删除无净收益 string marker；
   - 不牺牲可读性和测试覆盖。
2. 目标是形成真实余量，建议至少 5%–10%。
3. 把 `requiredTestCount == 11` 改为：
   - 必需 test markers / test classes；
   - `testsRun >= minimum`；
   - zero skipped；
   - zero expected failure；
   - 关键 adversarial tests 必须存在。
4. 硬 cap 可以暂时保留 120000；若在独立审查后确认无法安全减少，再以书面因果理由调整 cap，并同时重新建立余量。  
   **不得只为绿灯直接提高上限。**

## 6.4 路径、symlink 与文件边界

### 事实

`guardrails.py` 和 `identity.py`：

- 拒绝绝对路径；
- 拒绝 `..`；
- 拒绝 Windows drive/path escape；
- 检查 resolved path 是否仍在 repository root；
- 检查 symlink traverse；
- package digest 由受控表面计算；
- forbidden paths 仅限仓库相对路径。

### 评价

对于一个本地、非特权、stdlib-only verifier，当前路径边界总体达到合理的生产级静态标准。

## 6.5 JSON 与输入边界

### 事实

- duplicate JSON keys 失败关闭；
- 非有限数值失败；
- UTF-8；
- 文件大小上限；
- observation shape 和 exact fields 严格；
- source record hash、task digest、evaluation digest、projection digest 和 chronology 被绑定。

### 评价

扎实，建议保持。

## 6.6 Git 子进程

### 事实

Git 调用使用参数数组，不通过 shell 拼接；设置 timeout；对缺少 Git 或非 checkout 状态有明确处理。

### 评价

未发现命令注入型 P0/P1。

## 6.7 Prompt injection 与不可信材料

### 事实

- Skill 明确把 report、memory、retrieved text、tool output 视为证据，不因存在而成为指令；
- GT-04 专门验证 report-is-evidence-not-authority；
- constitution 区分 authority 与不可信输入。

### 评价

方向和回归测试正确。

## 6.8 插件供应链

### 正面

- OpenAI / Claude manifest 都非常薄；
- 没有 executable Hook/MCP/App；
- Codex release 安装计划使用 `--ref v2.0`；
- GitHub Actions 使用精确 action SHA；
- workflow `contents: read`，checkout 不持久化凭据；
- Python 生产代码无第三方运行时依赖。

### 风险

- audited commit 未签名；
- `main` 的 branch protection 没有强制 required status checks；
- release tag 尚未存在；
- README 尚未写完整升级、卸载和回滚；
- 没有独立的 threat model / dependency inventory 概览。

### 评级

P2 维护与发布治理问题，不是当前 P0。

---

# 7. Golden Tasks、行为证据、失败保留与主张上限审计

## 7.1 Release sample

当前 finite release sample：

- GT-01：pass
- GT-02：pass
- GT-03：pass
- GT-04：pass
- GT-05：pass
- GT-07：fail
- GT-08：fail

Acceptance 明确：

- must-pass：GT-01、GT-03、GT-04、GT-05；
- GT-07/08 可以作为 retained failure；
- 失败必须转为公开、排序后的 claim exclusions。

## 7.2 GT-07

### 事实

Claude Code + DeepSeek backend 的该次运行没有观察到：

- `record-capacity-as-unknown`
- `use-a-conservative-task-bound-transition-rule`
- `prepare-and-verify-destination`
- `reconcile-before-source-release`

任务仍为 failed，四项进入公开 exclusions。

### 评价

这是正确的失败处理。

### Release 影响

按当前 acceptance：

- **不阻断有限 v2.0 release；**
- **阻断对该精确 Claude/DeepSeek 路线的 continuity behavior qualification；**
- 不得在 README 或 release notes 暗示 Claude continuity 已证明。

### 路线

放入 post-v2.0 近期维护，重新设计更真实的 carrier transition task 后复测；不要在发布前叠加新的 prompt/Hook/runtime。

## 7.3 GT-08

### 事实

Codex 运行中：

- proportional probe：observed；
- retain unknown：observed；
- fallback/honest stop：observed；
- current official guidance resolution：not observed。

该失败被保留，未声称 universal host support。

### 当前外部核验

本次审计已从 OpenAI 当前官方资料确认：

- repo/local marketplace；
- `codex plugin marketplace add owner/repo --ref ...`；
- `codex plugin add PLUGIN@MARKETPLACE`；
- `/plugins`；
- 新 chat/CLI session；
- remove/uninstall；
- local marketplace 后重启桌面端。

### 处置

不能回写历史把 GT-08 改为 pass。

合理做法：

- 维持 GT-08 failure；
- 把本次官方资料核验作为新的 maintenance input；
- post-v2.0 重新执行新的 GT-08 observation；
- 不将其变成 v2.0 release blocker。

## 7.4 证据真实性与独立性

### 正面

当前 verifier 会验证：

- exact task digest；
- evaluation contract digest；
- exact projection identity；
- typed host/session；
- capture time ≤ observation time；
- source record hash；
- required/prohibited behavior completeness；
- human burden；
- effect/residue/cleanup；
- failure 与 exclusion 一致；
- must-pass task 不能失败。

这明显强于“在 JSON 里写 verified=true”。

### 关键局限

`evals/evidence/2026-08-22-v20-representative-source.json` 的 payload 是整理后的可发布 JSON 字符串摘要，而不是：

- 原始完整 CLI JSONL；
- Claude 原始 result file；
- 第三方只读 task URL；
- cryptographic signature；
- 独立人类审核记录。

所有 observation 的 observer 都是同一个 Codex goal carrier identity；包括 Claude GT-07。

因此当前证据能强力证明：

> 仓库内 observation、source bundle、task contract 和 claim exclusion 的内部一致性。

但不能单独证明：

> 每个宿主事件在现实中完整、无遗漏、未被选择性整理地发生。

### 结论

在发布前的 `exact-local-verification-and-review` 中必须增加一个有界动作：

1. 独立审阅者对七条 source payload 与原始宿主日志/任务记录逐项比对；
2. 核对 session ID、host version、prompt、tool/event、effect、cleanup；
3. 输出外部 review record，绑定 audited candidate SHA；
4. 该 review record 不写回 candidate，不造新的身份平台。

这是 P1 release gate，不需要新 Runtime 或 audit system。

---

# 8. “计划—工序—验收—目标提示词”映射审计

## 8.1 总体结论

结构层面映射较完整：

- increment / work item 映射 R1–R4/Q1–Q4；
- 四个 work stages 有同序 stop condition；
- 六个 release gates 有依赖；
- goalModePrompt 包含 workStageIds、releaseGateIds、mapsTo；
- tests 会破坏这些映射并确认 fail closed。

## 8.2 映射矩阵

| 层 | 当前内容 | 映射状态 | 风险 |
|---|---|---|---|
| Constitution | identity、domain、K/H/L、boundary、evidence、evolution | 清楚 | `CONTEXT.md` 可能补充了未回写的规范定义 |
| Acceptance | R1–R4/Q1–Q4、sample、exclusions、claim ceiling、external operands | 清楚 | “independent evidence”的现实证明仍需外部 review |
| Program increment | identity migration + framework alignment | 清楚 | 已 completed，不能再把未完成外部门写成 increment 完成 |
| Work stages | identity → static → representative → freeze | 同序 | `CONTINUATION` 的 live next-gate 文案滞后 |
| Release gates | repository → exact local → hosted → human → tag/release → verify/cleanup | 严格 | external gate 事实不能存入 candidate，自然需要 task-time carrier |
| Goal prompt | 重复描述全部 stages/gates/claim boundaries | 形式完整 | 太长、重复语义，存在事实第四权威和维护成本 |
| Tests | 校验 mapsTo、stage order、release order、surface markers | 强 | exact string markers 脆弱 |

## 8.3 形式对齐但语义风险

### A. `CONTEXT.md`

它写着“canonical domain language”，又不属于三份 semantic authority。

建议二选一：

1. 把真正规范性的定义移入 `constitution.domainModel`，CONTEXT 只做带 JSON Pointer 的解释投影；或
2. 把 CONTEXT 明确改成“canonical explanatory vocabulary derived from constitution”，每个定义标出来源路径，不允许添加新 obligation。

不建议新增第四 authority。

### B. `goalModePrompt`

当前 prompt 很完整，但重复了：

- 八 criteria；
- 四 stages；
- 六 gates；
-历史边界；
-外部证据；
- Skill dependency；
- release action。

建议不改变语义，只做减法：

- 保留当前 stage；
- 保留下一门；
- 保留 mapsTo；
- 保留关键禁令；
- 其余从 program/acceptance 读取。

### C. `CONTINUATION.md`

它在这个已经 commit/push 的精确 SHA 中仍说：

> 下一门是 repository-candidate：commit complete authorized WIP。

这在审计时已经是过时导航。

建议改成时间中立：

> 首先通过 live Git、Actions、Codex Cloud 和任务外部记录确定第一个未完成 gate；仓库文件不能自证 external gate。

对于当前 SHA，合理下一步是：

1. 解决本报告 P1；
2. 形成新的精确候选；
3. exact local independent review；
4. push 同一 SHA；
5. GitHub Actions + ordinary Codex Cloud。

---

# 9. Codex、Claude Code 当前官方能力与未来漂移

## 9.1 Codex 同源关系

OpenAI 官方说明：

- Web、CLI、IDE、桌面端由同一 Codex harness 驱动；
- Codex Core 包含 agent loop、thread lifecycle、config/auth、tools/extensions；
- App Server 提供双向 JSON-RPC/JSONL 表面；
- Codex Web 在容器环境运行同一 harness，但存在未开源托管后端；
- CLI 源码公开。

官方来源：

- https://openai.com/index/unlocking-the-codex-harness/
- https://github.com/openai/codex

### 结论

仓库正确地把 Codex 当作参考宿主，不应复制它的 Runtime。

## 9.2 Codex plugin 官方机制

截至 2026-08-23：

- local/repo marketplace 仍是当前官方能力；
- local marketplace 改动后桌面端需重启；
- CLI marketplace/add/remove 存在；
- `/plugins` 支持 install/uninstall/enable/disable；
- 新安装 Skill 在新 chat/CLI session 中生效。

当前 Codex 文档方向基本正确，只需补全生命周期。

## 9.3 Claude Code plugin 官方机制

截至 2026-08-23：

- `.claude-plugin/plugin.json` 是官方 manifest；
- `skills/` 在 plugin root；
- `--plugin-dir` 直接加载，无需持久安装；
- Skill namespaced；
- `/reload-plugins` 重新加载；
- marketplace install 是另一条持久分发路径。

当前 Claude 投影正确保持了 session-only 测试边界。

## 9.4 Claude Code + DeepSeek

GT-07 的 host identity 正确写为：

> Claude Code with DeepSeek Anthropic-compatible backend

没有把它写成 Anthropic Claude 模型行为证据。这一点应保持。

## 9.5 普通 Codex Cloud 与 Trusted Access for Cyber

普通 Codex Cloud 用于：

- GitHub repo；
- isolated cloud environment；
- background task；
- summary/diff review。

Trusted Access for Cyber / Daybreak 是针对经批准的特定网络安全工作和模型访问的独立治理路径。

因此：

> **本项目进行普通 Codex Cloud exact-SHA 验证，不需要先取得 ChatGPT Cyber / Trusted Access。**

官方来源：

- https://learn.chatgpt.com/docs/cloud
- https://help.openai.com/en/articles/20001258-trusted-access-for-cyber

## 9.6 事件刷新而非永久 registry

当前架构采用：

> 在 release 前或重大 host/version/maturity/permission/deprecation 事件发生后，重新核验官方资料和 exact host；不维护永久能力注册表。

### 评价

合理，足够。

### 需要补的不是 registry，而是一个 owner/cadence 条目

每个 supported host 只需在维护文档记录：

- owner；
- last reviewed date；
- official source URLs；
- exact tested version；
- trigger；
- residual gap；
- retirement condition。

不要新建动态能力平台。

---

# 10. 连续性、自动压缩与任务转场

## 10.1 是否有官方“固定多少轮后换对话”

截至 2026-08-23，本次在 OpenAI 当前一手资料中**未找到**：

> 经过固定 N 轮对话后必须切换新对话。

OpenAI 当前 long-running work 文档反而建议：

- 相关工作留在同一 chat/session；
- 独立任务使用单独 chat；
- 同一连接源避免两个任务同时写；
- 使用清晰 outcome、constraints、verification；
- 同一 session 中 steer 或请求 status recap。

官方来源：

https://learn.chatgpt.com/docs/long-running-work

因此不得制造：

- 固定轮数；
- 固定 token 百分比；
- 固定摘要占比；
- 通用 60%/80% 常量。

用户观察到 60% 后效率下降、80% 后明显变慢，应作为经验信号和待验证假设。

## 10.2 当前规则是否合理

当前规则：

> 可靠宿主信号优先；无信号时记录 unknown，并保守转场。

**合理。**

## 10.3 可改进之处

不要增加 context predictor，而是增加事件型转场判定：

1. 宿主明确报告 compaction / context pressure；
2. Agent 开始重复读取已经稳定的事实；
3. 已确认 correction 被再次丢失；
4. summary 占比导致当前关键状态难以辨认；
5. 即将进入高风险、不可逆或长期阶段；
6. 工具结果或最终消息发生 delivery failure；
7. carrier 中断、网络丢失或宿主重启；
8. 需要并行独立任务且不存在共享写冲突。

最小 durable state：

```yaml
goal:
phase:
settled_corrections:
constraints:
authority:
current_checkout:
material_evidence:
effects_and_residue:
next_gate:
```

转场条件：

```text
准备 destination
→ 载入最小 state
→ 验证目标、修正、Git、权限和 next gate
→ 再释放 source
```

GT-07 失败说明这条能力当前尚未在 Claude/DeepSeek 路线证明，不能夸大。

---

# 11. Findings

## 11.1 P0 — 必须立即阻断

**无已确认 P0。**

本次没有发现可直接证明的：

- 未授权发布；
- secret 泄漏；
- 任意命令注入；
- 路径逃逸；
- symlink 越界；
- destructive cleanup；
- release self-authorization；
- 隐藏 GT 失败；
- 已发生的生产安全事故。

---

## 11.2 P1 — v2.0 发布前必须解决

| ID | Finding | 事实证据 | 影响 | 反证/不确定性 | 最小整改 | 对应验收/阶段 |
|---|---|---|---|---|---|---|
| P1-01 | 复杂度硬预算零余量，且 test count 固定为恰好 11 | Actions verifier：120000/120000；workflow 要求 testsRun==e | 必要修复/测试会先失败，诱导删测试、压可读性或调预算 | 当前代码仍通过，不代表不可维护 | 先减法形成 5%–10% 余量；`requiredTestCount` 改为 minimum + required markers；不得直接为绿灯调高 cap | Q3/Q4；static-conformance |
| P1-02 | `CONTEXT.md` 有事实第四语义源风险 | 它自称 canonical domain language，但 authority 只列三份 JSON | definitions 可与 constitution 静默漂移 | verifier 有 marker 检查，但不是完整语义映射 | 把规范定义归入 constitution，CONTEXT 改为带 source pointer 的派生解释 | R1/Q2；identity-authority |
| P1-03 | `CONTINUATION.md` 的 next gate 在 audited commit 中已滞后 | 文件仍要求“commit WIP”，但 audited SHA 已 commit/push 且 Actions 完成 | 后续 Agent 可能重复提交或误判阶段 | 文件声明先恢复 live Git，部分缓解 | 改为条件式“查找第一个未完成 external gate”；不要在 repo 中硬写 live gate 已完成 | Q4；documentation/continuity |
| P1-04 | 行为 source bundle 尚缺独立原始记录复核 | source payload 是整理后的字符串摘要；observer 为同一 Codex goal carrier；verifier承认不认证现实 observer | 代表行为的真实性/完整性不能仅凭 repo hash 独立证明 | 内部 digest/chronology/claim 绑定非常强 | exact-local review 中由独立人/第二观察面逐项对原始 host logs/session IDs；review 绑定 candidate SHA，保存在 candidate 外 | R3/Q2/Q4；exact-local-review |
| P1-05 | README 缺升级、禁用、卸载、回滚与故障诊断 | 当前只完整覆盖 install/enable/verify | 普通用户生命周期不闭环 | 产品没有 Runtime，整改成本低 | 补 Codex list/remove/browser、marketplace update/remove、新 session；补 Claude reload/session-only/退出边界 | R2/R4；docs/host projection |
| P1-06 | Python 支持声明大于当前托管矩阵 | README 写 3.10+；Actions 只运行 3.10 | 新版 Python 兼容性未知 | 代码可能实际兼容，但未形成当前 SHA 证据 | 要么收窄为 3.10 tested；要么增加最新稳定 Python 的 non-blocking/blocking matrix | R4/Q2；CI |
| P1-07 | 有序外部门尚未完成 | 普通 Codex Cloud、exact human authorization、tag/release、public verification/cleanup 无完成证据 | 直接阻断公开发布和有限收官 | GitHub Actions 三系统已经通过 | 解决前述 P1 后生成新 SHA，按 gates 严格执行，不跳门 | R4/Q1/Q2/Q4；release gates |
| P1-08 | 独立首次用户文档走查尚未形成证据 | 当前样本主要是 fixture 和维护者控制的 host tasks | 无法证明普通用户能独立启用和确认生效 | 不需要大规模 field study | 由用户本人之外至少一位同事按 README 从 clean state 完成 Codex 或 Claude 路径；只声明内部便利样本 | R2/R3；exact-local-review |

---

## 11.3 P2 — 发布后近期解决

| ID | Finding | 影响 | 最小路线 |
|---|---|---|---|
| P2-01 | `goalModePrompt` 和 string markers 重复语义较多 | 文案修改可能触发脆弱失败；形成第四权威压力 | 发布后做 data-driven projection，保留 IDs/order/禁令，不全文重复 |
| P2-02 | Complexity 指标可把复杂度迁移到 JSON/docs/evidence | 量化指标可能被 gaming | 用 review checklist + trend，不再只用单一 bytes |
| P2-03 | GT-07 continuity 在 Claude/DeepSeek 失败 | 该路线不能声称 continuity qualification | 设计真实 carrier-transition task 后复测；不加 Hook/runtime |
| P2-04 | GT-08 未在该次 observation 中查官方 guidance | host-admission 流程不完整 | 以本次官方核验为新输入，下一版本重跑；旧 failure 保留 |
| P2-05 | Commit 未签名、branch protection 未强制 status checks | release governance 较弱 | 为 release tag 采用签名或明确 unsigned policy；配置 required checks |
| P2-06 | 缺简洁 threat model / dependency inventory | 安全边界对外不够可审阅 | 发布后近期补一页 threat model 与 stdlib/plugin-only inventory |
| P2-07 | 缺 delivery-loss / missing-turn Golden Task | 当前连续性偏 context-centric | 把本次对话输出丢失转成独立可复现候选任务 |
| P2-08 | 缺 compound request / false-premise 代表任务 | shortfall 覆盖仍有空白 | 每类只增一个高价值任务，不扩大为完整 taxonomy backlog |

---

## 11.4 P3 — 可选改进

| ID | 建议 | 边界 |
|---|---|---|
| P3-01 | 按职责拆分单一 test 文件 | 只有当可读性收益明显且不增加重复 fixture 时 |
| P3-02 | 从 authority 自动生成部分 README/CONTEXT 片段 | 不引入新的 build/runtime dependency |
| P3-03 | 为 release evidence 提供可选 machine-readable review manifest | 不建设身份或审计平台 |
| P3-04 | 收集更多 external-user 样本 | 不把少量样本夸大为 population effectiveness |
| P3-05 | 评估第三个宿主 | 只有出现真实需求和维护 owner 时 |

---

# 12. 建议保持不变

1. **产品名称 YIYUAN Accord。**
2. **广义 human-AI mission + 当前 human-Agent scope。**
3. **无 compatibility alias 的 breaking identity migration。**
4. **三份语义权威。**
5. **K1–K5、H1–H10、L1–L7。**
6. **不成为 Runtime、control plane、sandbox、permission system。**
7. **Codex/Claude 只是 reference hosts。**
8. **Skill-only 薄投影。**
9. **不默认增加 Hook、MCP、App。**
10. **用户级自研 Skills 不是 release dependency。**
11. **YIYUAN-CALIBRATION 唯一 read-only custody。**
12. **static / behavior / hosted / human / release / production 的分层。**
13. **GT-07、GT-08 保持失败。**
14. **exact retainedBehaviorExclusions。**
15. **严格 external gate 顺序。**
16. **可靠信号优先、unknown fallback、无固定轮数/百分比。**
17. **event-triggered host capability review，不建永久 registry。**
18. **路径、symlink、duplicate JSON、self-attestation 的 fail-closed 防护。**
19. **报告、测试、commit、push 都不是项目结果。**

---

# 13. 最小、严格有序的整改与再验证计划

## 阶段 1：冻结当前基线

输入：audited SHA。  
动作：保留本报告与现有 SHA，不改写 GT 历史。  
停止条件：所有 P1 有 owner 和明确处置。  
回滚条件：任何整改引入 Runtime/Hook/MCP/App 或恢复旧 identity。

## 阶段 2：发布前最小修复

严格顺序：

1. 修正 `CONTEXT.md` 权威定位；
2. 修正 `CONTINUATION.md` 时间中立 gate 导航；
3. 修正 complexity/test-count 规则并通过减法形成余量；
4. 补 README lifecycle；
5. 收窄或扩展 Python support matrix；
6. 更新相应 tests，不删除关键回归。

停止条件：

- 无 P1-01~P1-06；
- 8/8 criteria；
- 两 host-check；
- test suite 全通过；
- 无 skip；
- 有真实余量；
- 无旧 identity；
- diff 无无关变更。

## 阶段 3：新候选冻结

任何变更都生成新 SHA，不沿用 audited SHA 的 candidate-specific evidence。

执行：

- clean checkout；
- local verifier；
- host-check；
- tests；
- diff/link/identity/residue；
- independent evidence source review；
- 一位同事按 README 完成 clean-state walkthrough。

停止条件：

- 独立 review 无 P0/P1；
- evidence bundle 与 raw host records 对齐；
- ordinary-user walkthrough 闭环。

## 阶段 4：托管验证

先 push 同一 SHA，再：

1. GitHub Actions：Windows/macOS/Ubuntu；
2. ordinary Codex Cloud：精确 SHA；
3. 不需要 Trusted Access for Cyber；
4. 记录环境、命令、结果、residue 和限制。

失败时回退到最小受影响阶段，所有候选相关后续证据失效。

## 阶段 5：具名人类发布门

只在 exact hosted gate 通过后，提交：

- exact SHA；
- finite claims；
- not implied；
- GT-07/08 exclusions；
- P2/post-release 路线；
- security/support 边界。

未经明确授权，停止。

## 阶段 6：发布与复验

- lightweight `v2.0` tag；
- no assets；
- GitHub Release body 与 tracked release notes 完全一致；
- 核验 local/remote tag；
- 核验 release API；
- 核验安装命令；
- 清理任务资源；
- 重放 local checks。

---

# 14. 是否需要修改 constitution、program、acceptance、goalModePrompt

## Constitution

**不建议整体重写。**

仅建议：

- 明确 `CONTEXT.md` 是派生解释表面；
- 如确有规范定义只存在于 CONTEXT，将其最小结构化地归入 `domainModel`；
- 不新增原则层。

## Acceptance

**总体保持。**

只建议在 exact-local review 的 pass rule 中进一步明确：

> 独立审阅必须把 publishable source record 与原始 host log / session source 对照；repo 内 hash 只证明 capture 后完整性，不证明事件真实性。

不要修改 GT-07/08 为 pass，也不要把它们加入 must-pass。

## Program

**需要有界修改。**

1. complexity budget：
   - 取消 exact `requiredTestCount == 11`；
   - 改为 minimum + required markers；
   - 建立余量。
2. `goalModePrompt` 减少重复文本。
3. 不把 external gate 完成状态写回 candidate。
4. CONTINUATION 改为动态判断第一个未完成门。

## GoalModePrompt

**建议减法，不改变语义。**

保留：

- 当前阶段；
- 当前 next gate；
- criteria IDs；
- 不得把报告/测试/push 当结果；
- human boundary；
- failure return rule。

删去可直接从 program/acceptance 读取的长篇重复说明。

---

# 15. 对 17 个核心审计问题的直接结论

1. **定位与使命：** 清晰，不冲突。
2. **旧名称：** 当前主要活跃表面未发现旧名，verifier 和代码搜索均支持 no-alias；历史中保留是正确的。
3. **README：** 首次入口已明显改善，但完整用户 lifecycle 尚未闭环。
4. **Codex/Claude 启用：** 当前说明基本符合 2026-08-23 官方机制；需补卸载/升级/诊断。
5. **C/P/A/stages/gates/prompt：** 结构同序；CONTEXT、goal prompt 和 CONTINUATION 存在语义/时效风险。
6. **减法/模块化：** 已实质完成；仍有 string contract 和 evidence ceremony 隐藏成本。
7. **120000 零余量：** 不合理，先减法形成余量，不得只调预算。
8. **行为证据：** 内部完整性强；现实事件独立真实性需外部 review。
9. **GT-07/08：** 不阻断当前 finite release policy；严格限制局部行为主张；保持失败。
10. **安全：** 当前类别下静态边界总体良好，无 P0；供应链治理和 threat model 可加强。
11. **宿主绑架：** 当前已保持可替换 reference host，未被严重绑架。
12. **事件刷新矩阵：** 足够；补 owner/date/trigger 即可，不建 registry。
13. **用户级自研 Skills：** 仓库正确保持非依赖边界；不建议重加。
14. **计划收敛：** 基本收敛；只解决 P1 和 external gates，其余移后。
15. **用户/同事样本：** 发布前做一轮 docs walkthrough；只称内部便利样本，不泛化。
16. **试错沉淀：** 已较充分；遗漏重点是 delivery failure、compound request、premise challenge、真实用户 lifecycle。
17. **遗漏同步面：** CONTEXT、CONTINUATION、README lifecycle、Python support、branch/release governance、evidence review record。

---

# 16. Post-v2.0 有限路线图

## 0–30 天

- 重新执行 GT-08，记录当前官方 Codex plugin guidance；
- 设计更真实的 GT-07 carrier transition；
- 增加 delivery-loss 回归；
- 收集用户本人和一位同事的真实使用样本；
- 修正发现的文档与安装摩擦；
- 配置 required CI checks / release tag integrity。

## 30–90 天

- 完成 compound request、premise challenge 两个高价值任务；
- 对 Codex / Claude host drift 做一次 event-triggered review；
- 删除无净收益 marker / prompt duplication；
- 发布第一个 maintenance report：help、interference、failure、retirement。

## 90 天以后

只有满足以下条件才扩宿主或机制：

- 有真实用户需求；
- 有 owner；
- 当前 native route 不足；
- 有 bounded Golden Task；
- 有维护成本预算；
- 有 retirement condition。

不启动“全宿主”“全行业”“通用治理平台”大重构。

---

# 17. 最终四张清单

## 17.1 已确认事实

- audited SHA 可公开访问；
- 父提交为 v1.2 SHA；
- main 在审计时指向 audited SHA；
- commit 未签名；
- Actions exact SHA 三系统成功；
- verifier 8/8；
- 两 host-check static-ready；
- tests 11/11；
- 代码+测试字节 120000/120000；
- identity migration 完成于主要活跃表面；
- GT-01~05 pass；
- GT-07/08 fail；
- exact exclusions 公开；
- release authorization 未请求；
- 普通 Codex Cloud 尚无完成证据；
- K/H/L、thin projections、no-runtime boundary 存在；
- CALIBRATION 保持唯一 custody。

## 17.2 仍属未知

- source bundle 与原始完整 host logs 是否逐字一致；
- 普通 Codex Cloud exact-SHA 结果；
- v2.0 tag/release 的最终 API 状态；
- 新用户在无口头知识下能否完整启用；
- Python 最新稳定版本兼容性；
- Claude/DeepSeek continuity 修复效果；
- 长期用户负担和 field effectiveness；
- 跨宿主等价性；
- 生产部署安全性。

## 17.3 需要人工判断

- complexity cap 的最终数值与最低余量；
- 是否要求 signed tag/commit；
- Python 支持版本范围；
- 是否把 Claude/DeepSeek 标为 experimental；
- v2.0 公开 claim ceiling；
- retained failures 的最终发布说明；
- exact candidate 的发布授权；
- post-v2.0 host owner 与维护承诺。

## 17.4 建议下一步

1. 接受 audited SHA 作为外部审计基线；
2. 不发布；
3. 按 P1-01~P1-06 做一次最小修复；
4. 生成新 clean SHA；
5. 完成独立 evidence review 和同事 README walkthrough；
6. 推送同一 SHA；
7. 跑 GitHub Actions + ordinary Codex Cloud；
8. 再请求具名人类发布授权；
9. 发布、复验、清理；
10. GT-07/08 与新增 shortfall tasks 进入 post-v2.0，不无限延长当前 release。

---

# 18. 主要精确来源

## YIYUAN Accord

- 精确提交：  
  https://github.com/yiheng8023/YIYUAN-Accord/commit/2b2b5fbc90f9659c48853d84ae0600f66329ad02
- README：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/README.md
- CONTEXT：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/CONTEXT.md
- Constitution：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/product/constitution.json
- Program：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/product/program.json
- Acceptance：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/product/acceptance.json
- Verifier：  
  https://github.com/yiheng8023/YIYUAN-Accord/tree/2b2b5fbc90f9659c48853d84ae0600f66329ad02/yiyuan_accord
- Tests：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/tests/product/test_product_control.py
- Workflow：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/.github/workflows/validate.yml
- Golden Tasks：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/evals/golden-tasks.json
- Evidence source：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/evals/evidence/2026-08-22-v20-representative-source.json
- Release body：  
  https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/docs/releases/v2.0.md
- Actions：  
  https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/32605119408

## Shared research

- https://github.com/yiheng8023/YIYUAN-CALIBRATION/tree/e060a08f05361cb4cc9a67be050236cdbbde1de5/common/human-ai-collaboration-shortfalls

## OpenAI / Codex

- https://openai.com/index/unlocking-the-codex-harness/
- https://github.com/openai/codex
- https://developers.openai.com/plugins/build/plugins
- https://learn.chatgpt.com/docs/plugins
- https://learn.chatgpt.com/docs/cloud
- https://learn.chatgpt.com/docs/long-running-work

## Claude Code

- https://code.claude.com/docs/en/plugins
- https://code.claude.com/docs/en/discover-plugins

---


## 18.1 关键事实定位索引（精确 SHA）

以下链接固定到 audited SHA，不随 `main` 后续变化：

| 主题 | 精确定位 |
|---|---|
| 产品定位、首次入口、Codex/Claude 启用 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/README.md#L1-L220 |
| 领域词汇与 human-AI / human-Agent 边界 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/CONTEXT.md#L1-L240 |
| 唯一产品宪章 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/product/constitution.json#L1-L320 |
| 工序、工作阶段、release gates、goalModePrompt、复杂度预算 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/product/program.json#L1-L360 |
| R1–R4 / Q1–Q4、sample policy、exclusions、external operands | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/product/acceptance.json#L1-L380 |
| Identity 和历史边界检查 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/yiyuan_accord/identity.py#L1-L520 |
| 路径、symlink、插件包、release surface guardrails | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/yiyuan_accord/guardrails.py#L1-L980 |
| 总验证流程与 complexity computation | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/yiyuan_accord/control.py#L1-L1040 |
| Evidence source / observation / chronology / exclusion binding | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/yiyuan_accord/evidence.py#L1-L520 |
| 产品回归测试 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/tests/product/test_product_control.py#L1-L520 |
| 三系统 CI | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/.github/workflows/validate.yml#L1-L80 |
| Codex marketplace | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/.agents/plugins/marketplace.json#L1-L30 |
| Codex Skill | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/plugins/yiyuan-accord-codex/skills/deliver-demand-driven-outcome/SKILL.md#L1-L100 |
| Claude Skill | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/plugins/yiyuan-accord-claude/skills/deliver-demand-driven-task/SKILL.md#L1-L100 |
| Golden Tasks | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/evals/golden-tasks.json#L1-L320 |
| 代表行为源记录 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/evals/evidence/2026-08-22-v20-representative-source.json#L1-L220 |
| GT-07 retained failure | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/evals/observations/2026-08-22-v20-claude-gt07.json#L1-L100 |
| GT-08 retained failure | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/evals/observations/2026-08-22-v20-codex-gt08.json#L1-L100 |
| 架构和 evidence independence 边界 | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/docs/architecture.md#L1-L220 |
| 当前 continuation / release route | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/docs/operations/CONTINUATION.md#L1-L180 |
| Security boundary | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/SECURITY.md#L1-L100 |
| v2.0 claim ceiling 和 retained exclusions | https://github.com/yiheng8023/YIYUAN-Accord/blob/2b2b5fbc90f9659c48853d84ae0600f66329ad02/docs/releases/v2.0.md#L1-L100 |

## 最终结论

当前 SHA 的核心方向没有必要再进行全局推倒重来。真正正确的收敛动作是：

> **保持产品内核、失败诚实、宿主可替换和严格发布门不变；只解决少量明确 P1，完成 ordinary Codex Cloud、独立审阅、具名授权和公开发布闭环，然后把其余问题转入有限的 post-v2.0 维护路线。**

这才符合 YIYUAN Accord 自己提出的：

**真实结果、减法、克制、最小充分路径、失败沉淀和长期可维护演化。**
