# Continuation

发布后当前导航，更新于 2026-09-08。冻结的开发定义、计划和验收记录绑定各自原提交；
它们不是发布后实时状态。原始过程保留在 Git 与私有证据中，不覆盖失败记录。

## 当前发布事实

- [v3.2.0 正式 Release](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.2.0)
  已于 2026-09-07 20:04:35 UTC 发布，匿名公共接口核验为最新、非草稿、非预发布。
- 不可变发布提交：`14693d58e2296cbe0b7b4cf15eacc9cb54462bad`。
  发布时远端 main、接续分支与 v3.2.0 tag 同指该提交；之后的导航维护不移动 tag。
- [同提交九项 CI](https://github.com/yiheng8023/YIYUAN-Accord/actions/runs/34155028222)
  全部通过。最终两阶段验收准入 11 项记录，两个独立评审者覆盖四个视角。
  功能与有限影响条件通过；增量收益仍未验证，不据此承诺普遍可靠性增益。
- `product/development.json` 和由其派生的 `PLAN-v3.2.md` 保留该发布提交的冻结候选定义。
  其中“未发布/未验证”是当时静态表示，实际准入与发布以绑定 14693d5 的验收报告和公开
  Release 为准，不能把修改静态状态当成验收，也不能继续把冻结时的待办当成当前任务。

## 写入目标与用户边界

- 唯一开发写入位置：`C:\Projects\YIYUAN-Accord-post-v31`，
  `phase/post-v3.1-successor` 跟踪同名远端；每个仓库命令显式指定工作目录。
- 主线程20 `01a07984-457e-75a1-ba39-4e5fda61f440` 保持主写；主线程19已静默转移写入权。
  保留两任务，交接和完成均不授权归档。
- `C:\Projects\YIYUAN-Accord` 是曾明确保护的原始 main checkout，仍在 c5a0668，
  存有 15 项未暂存修改和 2 项未跟踪文件。17 个文件已完整备份且逐项重核未变化，
  对应界面 +7,795/-547；没有未推送的 3.2 实现藏在这组旧混合稿中。
  旧审计识别已吸收中间稿、失败候选副本和过时状态混合，没有独有当前有效实现。
  不整批重新提交它们，不公开含私有路径的旧证据。同步原始 checkout 前仍须明确适用的
  清理授权；备份原件保留，禁止 force push 或改写发布标签。
- 发布及既有 Accord 更新已授权；用户随后明确授权四个新增 Codex Hook 的精确信任。
  此次授权不扩大为其它插件、账户、路由或共享治理配置的修改。
- 发布前 Codex dev.16 单次共享安装例外已闭合，不可复用。不得替换共享 AGENTS/CLAUDE
  或 ASSETS 指导；用户自定义环境须披露，不能成为未声明的产品依赖。
- 传播素材已有可用图文与口播稿，用户决定慢慢调整；不主动扩大制作或实际社交发帖。

## 六工序与当前结果映射

| 工序 | 当前结果 | 仍需保留的边界 |
|---|---|---|
| 本轮启动事实与方向核对 | 已完成 | 持续纠偏覆盖历史判断与资产，事实可纠正计划。 |
| 普通入口必要功能链实现与实际纠偏 | 已完成绑定范围的准入 | 旧失败和后置本地补验保留原身份，不称宿主自主恢复。 |
| Desktop 连续性与归档授权边界 | 已完成绑定范围的准入 | 不承诺普遍自主接管或最佳迁移时机。 |
| 两宿主安装、更新与独立恢复 | 发布前声明组合已准入；本机正式更新已执行 | 发布后新鲜激活与缓存/登记分开观察。 |
| 功能完成后的净影响、质量与成本对齐 | 条件使用评估完成 | 有限 Claude 配对未观察到可靠性增益；不重复试验求胜。 |
| 3.2 定版、发布与收尾 | 提交、推送、正式发布、图文交付完成 | 发布后激活后态与受保护旧 checkout 收尾仍需分别闭合。 |

原生 update_plan 映射这六工序；当前第六项保持进行中，不将发布成功扩大成所有本机收尾完成。
Accord 与宿主共生，各自保留责任与决定边界，借助充分的原生能力，不把流程或文档当成结果。

## 发布后安装与激活

- Codex 0.153.4：原生登记启用 3.2.0，12 文件完整包匹配发布源码。
  摘要 `edd4f5958313555d76e8906d36b1781ff5d47d11dbcccaee958c5521c234697f`。
- Claude Code 2.1.263：user scope 原生登记启用 3.2.0，9 文件完整包匹配发布源码。
  摘要 `9a5056261f77a84636527f2883dedec3e1e56a01a7563ba5ab7402f851c949c6`。
- 两边 marketplace 固定 v3.2.0；旧 Claude 3.1 的七文件恢复副本与原登记已保全。
  更新未改变其它插件登记及无关配置。四项 Codex 信任通过原生 config/batchWrite 写入，
  原生 hooks/list 读回五项全部 trusted；仅增加四项授权字段，其余配置语义一致，无 bypass。
- Codex 新鲜 ephemeral 原生会话完成一次显式选 Skill 的只读检查，真实读取插件清单与
  Skill，SessionStart、UserPromptSubmit、Stop 均 completed。继承 openai/gpt-6-astra/high，
  限只读、无网络，21 秒完成；自然退出、Job 0。它证明这次加载/调用，不证明普通任务普遍收益
  或现有 Desktop 会话热更新，也不把未观察到的事件标为本次执行通过。
- Claude 第一次检查因调用器将 prompt 放在可变长工具参数后而缺少 print 输入，方法失败保留。
  修正为 stdin 输入后，第二次原生会话 26.180 秒完成，init 列出实际 3.2.0 插件及 Skill，
  仅两次 Read，清单/Skill 返回全字节匹配现装文件；完整九文件匹配发布源码。
  实际报告模型 deepseek-v4-flash-vision-exp[1m]，报告费用 USD 0.197705，计费基准未知，
  不作为独立账单。自然 exit 0、Job 0。第一次缺输入错误的脱敏重构匹配原 stderr 摘要，
  不归因 Accord、账户或模型路由故障；两次观察保留独立身份。

## 证据与后续动作

私有证据位于 `C:\Users\15521\.codex\backups\accord-evaluation-20260905T215550Z-8ff0643a`
下的 `task20-functional-chain-20260907`。重要索引：

- `final-candidate-qualification.json`、`final146-review-bundle.json`：14693d5 的真实准入，禁止覆盖重跑。
- `v3.2.0-public-verification.json`：公共 Release、tag/main、公开原文件核验。
- `post-release-installed-packages-verification.json`：两包逐字节、无关配置及素材 ZIP 核验；
  其中信任待批是写入时事实，后续批准与执行见下一项，不回写旧观察。
- `authorized-trust-codex-loading.json`、`authorized-trust-config-verification.json`：四项授权与真实信任后态。
- `postrelease-codex-activation-loading.json`：上述新鲜会话与真实事件，不用总结代替原始事件。
- `postrelease-claude-activation/RESULT.md`：第一次调用方法失败及所属目录保全/清理。
- `postrelease-claude-activation-corrected/`：修正方法后的原生加载、读取、模型/成本及后态。
- `protected-main-postrelease-recheck.json`：17 个原文件、备份与旧审计的当次关联复核。
  原件 ZIP 摘要 `34c11c27d699bb56410ae688a3a46aca562a3c3eabf58690e867d018b121f4fe`。

两宿主新鲜加载/读取已观察；完成各自所属资源后态核对，再按明确授权同步受保护原始 checkout。
不重开已经完成的候选验收、有限价值比较或 GitHub 发布；传播内容按用户后续反馈调整。
