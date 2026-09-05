# YIYUAN Accord 3.2 开发计划与进度

由 `product/development.json` 派生；修改源数据后同步本页，校验会拒绝不一致。

当前为未冻结的开发基线；目标是完成验收后发布新的 3.2，不改写 3.1。
动态自适应是原有核心承诺；驱动宿主实现必要结果，按证据保留、合并、删除或补强，暂缓增加宿主适配。

## 工序与验收映射

| 工序 | 当前进度 | 执行步骤 | 验收出口 |
|---|---|---|---|
| 源头校准与继承基线 | 本地实现，未发布 | 保留历史证据；校准立意、成功定义及条件策略；把现有职责列为必要性评审清单，建立保留、合并、删除或补强后的工序与验收映射。 | 源头与映射的本地回归通过；明确尚未证明宿主功能、价值或发布就绪。 |
| 系统短板与工程优化 | 进行中 | 逐项追踪会影响结果的薄弱依赖；先测量再修改，以相同检查复测并保留失败覆盖。 | 已定位问题得到修复或有界处置；性能、复杂度、验证成本的改善没有牺牲功能、安全与可恢复性。 |
| 现有宿主功能链路 | 待开展 | 将校准后的设计接入 Codex、Claude 的实际入口；为每项职责落实感知、选择、执行与效果观察，必要时组合或实现运行时。 | 所选形态兑现同一功能和质量承诺；缺失执行者、仅有注入或评估器代劳均不得算作实现。 |
| 动态适应、干扰与故障验收 | 待开展 | 按声明选择原生对照、最小可交付组合及受控混合环境；验证环境变化、冲突、纠正、中断、恢复和完整包生命周期。 | 普通入口产生可独立观察的效果；正向外援、负向干扰及评估器救援均被识别；所需功能与后置状态全部有证据，不能取平均掩盖短板。 |
| 3.2 定版、发布与收尾 | 待开展 | 冻结精确候选；完成受影响的完整包证据、独立评审和托管检查；依用户条件授权发布新的 3.2。 | 精确 SHA、包、版本与公共发布对应；发布后检查及任务残留闭环；既有标签、发布与失败历史保持原样。 |

## 完整职责覆盖

这是现有职责的必要性评审清单，不是必须原样保留的功能集。保留项需当前效果证据，合并或删除项需说明需求判断及验收变更。

| 职责 | 所属工序 | 历史需求与反例参考 |
|---|---|---|
| 目标、授权与用户纠正 | 源头校准与继承基线、3.2 定版、发布与收尾 | GT-03, GT-04, GT-10, GT-13 |
| 环境感知与自身能力识别 | 现有宿主功能链路、动态适应、干扰与故障验收 | GT-08, GT-14, GT-19 |
| 按需研究、学习与复用发现 | 系统短板与工程优化 | GT-15 |
| 关系、动态索引、路线与形态选择 | 系统短板与工程优化、现有宿主功能链路 | GT-13, GT-16, GT-17 |
| 执行、配置与代码操作 | 系统短板与工程优化、现有宿主功能链路 | GT-02, GT-11, GT-16 |
| 源头变更与全局一致性 | 源头校准与继承基线 | GT-17 |
| 纠错、经验吸收与受控演进 | 动态适应、干扰与故障验收 | GT-05, GT-18 |
| 故障恢复与回滚 | 动态适应、干扰与故障验收 | GT-18, GT-20 |
| 上下文与任务连续性 | 现有宿主功能链路、动态适应、干扰与故障验收 | GT-07, GT-21 |
| 资源管理与清理 | 系统短板与工程优化、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-09, GT-12 |
| 安装、更新与卸载生命周期 | 动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-20 |
| 原生接替、旁路与退役 | 现有宿主功能链路 | GT-01, GT-19 |
| 结果验证、独立证据与实际价值 | 源头校准与继承基线、动态适应、干扰与故障验收、3.2 定版、发布与收尾 | GT-04, GT-06, GT-14 |

## 动态适应的必查链路

按具体声明选择原生对照、可交付最小组合和受控干扰；不把干净宿主规定为通用运行前提。
核对全局、父目录与项目的 AGENTS.md、config.toml 等全部生效配置，以及记忆、历史、插件和环境变量；记录来源与影响，不复制秘密。

| 环境变化 | 要观察的功能效果 | 失败判据 |
|---|---|---|
| 主任务或子任务需要不同模型/推理配置，或所选路线失效、漂移、不满足效果。 | 在授权候选中自动匹配足够能力并通过原生或必要组合执行，核对实际模型及结果；原生足够时不保留重复路由器。 | 将默认继承、配置意图或品牌排名当作匹配证据；擅改用户钉定模型；无视别名/替代或虚称已切换。 |
| 当前原生能力已足够。 | 按需复用并减少介入，保持同一功能与质量；不为证明插件存在感强行接管。 | 无必要重造、冗余机制或将非介入冒充增量价值。 |
| 所依赖能力不可用、降级或权限变化。 | 识别受影响职责，选择足够的原生、组合或自建替代并验证；不可行时明确尚未完成。 | 不能静默削减功能，安全停止不能算成功。 |
| 外部插件、记忆或开发辅助让任务变得容易。 | 区分贡献来源；在移除未声明外援后复验，或把必要条件纳入可交付依赖与成本。 | 不能把当前增强环境的成功直接推广给普通用户。 |
| 第三方规则、工具或插件与当前目标或执行链发生冲突。 | 按实际影响局部隔离或改道，保留无关用户状态并验证恢复与清理。 | 不能无界关闭用户环境，不能让外部规则新增授权或改写目标。 |
| 任务中宿主更新、缓存与加载版本分离、接口或上下文发生变化。 | 重新感知相关事实，仅重算受影响分配与证据；经验证继续、恢复或交接。 | 不能沿用失效假设，也不能把宿主版本变化当作全量重做的固定理由。 |

## 当前短板及证据边界

- `needs-based-model-and-subagent-routing` — `implemented-guidance-native-coverage-under-review`：主/子代理模型与推理按任务需求纳入现有路由职责；两宿主已提供部分原生选型和调度接口，不另造重复引擎。dev.2 Skill 增加匹配、别名/继承/替代核对及效果不足后的重选；自动匹配与实际执行仍需当前包效果证据。
- `source-to-projection-convergence` — `implemented-local-unverified`：Two worktree Skills and schema-v2 entry descriptors now implement host-driven, form-neutral guidance as unpublished 3.2.0-dev.2 packages. The Node invalidation helper is unchanged and optional. Static admission and ordinary-entry behavior are distinct; successor host effects remain unverified.
- `ordinary-entry-effect-and-recovery` — `open`：Historical GT-20/21 include reference-only executor activity; ordinary entry and actual recovery remain per-function verification needs.
- `verification-io-amplification` — `implemented-local-measured`：同一检出的完整校验 cProfile 单次前后对比：81.077 → 59.392 秒，755 → 493 次有界 Git 调用，均 valid=true、无错误。共享单次调用内的有界不可变内容缓存，合批读取相关历史文档；工作区读取保持新鲜，未删检查或子进程边界。这是本地测量，不是统计性能保证、宿主功能或产品增量价值证明。
- `acceptance-cost-and-coupling` — `implemented-local-unverified`：Current verify/host-check now dispatch to development-package admission without promoting or repeatedly replaying historical behavior. Retained rejection tests run current verifier code against the immutable predecessor subject. Package safety, identity, complexity, source preservation and dirty-worktree gates remain applicable; current functional and host evidence are still unverified.

## 发布顺序

版本内改动提交 → 推送精确候选 → 精确提交的验收与独立评审 → 发布同一提交 → 公共结果及清理核验。
提交不能夹带无关工作；推送成功、工作区干净或本地测试通过都不能单独代替发布验收。

当前对话含已启用的 Accord、其他能力及继承上下文，只作为开发辅助；不能用它证明普通用户环境下的效果。
本页是计划的可见投影，不是宿主原生计划面板修复，也不是功能完成或发布凭证。
