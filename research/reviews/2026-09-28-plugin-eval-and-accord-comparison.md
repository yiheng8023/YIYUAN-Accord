# Claude Code plugin eval 与 Accord 对照展示

2026-09-28 官方资料核实；未运行 eval、调用模型或测试 Accord。本机版本、账号可用性及真实执行后态未核。

**官方明示**（[eval 文档][E]）：

- 命令为 `claude plugin eval .`；`init` 可交互建案例，`init --bare <name>` 只建模板。最低 Claude Code 2.1.269；装有 Git 时须 ≥2.31。2.1.283 前未检查旧 Git，相关隔离不能倒推成立。
- 默认每案例每组3次，有／无插件两组；可用 `--ablation none` 关闭对照。评分是 grader 加权通过率再跨运行平均；阈值默认1.0，Δ不决定退出码。六类为 `regex`、`tool_used`、`tool_order`、`file_exists`、`llm`、`baseline`，无自定义代码 grader。可查最终回答、轨迹、文件及 mock 调用；LLM 轨迹只看首尾各12条。Skill触发检查通常不计双组分数；全数grader被排除或显式`arm: both`等设置可改变此规则。
- 每次新建非交互 `claude -p`；默认10轮／300秒，上限200轮／3600秒。`history_file` 装入旧对话，案例提示成为下一用户轮；可用 fixture、scaffold 和 MCP mock。
- 临时 home／工作区／配置排除用户及项目设置、CLAUDE.md、记忆、其它插件、Skills、Hooks、MCP；管理策略及允许的环境变量仍适用。目标插件自身的 Skills、Hooks、agents 会加载；Hooks、真实MCP及获准scaffold在Agent沙箱外运行，不能称全环境隔离。Artifact工具关闭。
- 写／shell／网络工具需命令行授权；真实MCP默认不启动。原生Windows无shell沙箱后端，含shell授权的套件须用WSL2。Skill字段不能扩大eval授权。
- 执行、judge及交互init计账户用量／账单；`--max-cost-usd` 无默认上限，只限标价估算且在途运行可超额。JSON、HTML和退出码可接CI；订阅且Artifact可用时，直接运行默认发布私有报告；API-key或Claude会话发起默认本地，`--no-publish` 保持本地。

**对 Accord 的推论**：适合作为未来Claude适配的限定案例对照及传播材料候选。应固定插件／模型／题目／判据，保留负Δ、失败、成本及原始产物；默认3次不是普遍收益证明。文档未承诺实时用户多轮编排、跨进程恢复、长期协作或跨宿主有效性；这些仍须独立设计并实测。Claude分数不能代验Codex或Accord整体验收，当前未取得对照收益证据。

**本次用户确认的定位**：plugin eval是传播素材的一部分，而非全部；完整能力与价值还须结合真实交付、持续协作、纠偏恢复、人工负担及资源成本的证据。

补充：[manifest][P] 支持 `experimental.evals` 定位套件；[Skills][S] 区分技能内容持续与授权按用户轮清除，不能由内容可见推断持续权限或可靠行为。

[E]: https://code.claude.com/docs/en/plugin-evals
[P]: https://code.claude.com/docs/en/plugins-reference
[S]: https://code.claude.com/docs/en/skills
