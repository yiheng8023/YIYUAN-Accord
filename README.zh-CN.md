# YIYUAN Accord

YIYUAN Accord 是一个开放、Agent 中立的人机协作可靠性契约与评估框架。它帮助 Agent
从用户真正想要的结果出发，选择最小充分路径，保留人的权限与最终问责，依据真实影响持续
纠偏，并以诚实验证和清理闭环。

项目的广义使命是改善人与 AI 的协作；当前产品面与证据严格限定为人与 Agent 的协作。

[English](README.md)

## 先开始使用

克隆仓库后，用 Python 3.10 或更高版本运行产品验证器。v2.0 正式发布后，应从不可变 tag
复现该版本：

```powershell
git clone --branch v2.0 --single-branch https://github.com/yiheng8023/YIYUAN-Accord.git
```

在选定的 checkout 中运行：

```powershell
python -B -m yiyuan_accord verify --root . --json
```

静态检查两个参考宿主投影：

```powershell
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

这些命令只验证仓库与投影包的一致性，不会安装插件、启用 Skill、证明宿主行为或授予发布
权限。

## 在 Agent 宿主中启用

克隆不等于安装插件。Codex 可能把当前 checkout 的 `AGENTS.md` 当作项目说明读取，但这不表示
YIYUAN Accord 插件已经安装。

### Codex

1. 用 ChatGPT 桌面版或 Codex CLI 打开本仓库。首次克隆或修改本地市场后，重启桌面端以重新
   加载目录。
2. 打开 **Plugins**（CLI 中运行 `/plugins`），刷新仓库本地市场并安装
   `yiyuan-accord-codex`。CLI 无法自动发现时，已发布的 v2.0 可用不会跟随未来 `main`
   变化的命令接入：`codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v2.0`，再运行
   `codex plugin add yiyuan-accord-codex@yiyuan-accord`。
3. 新建任务；确认已安装插件及 `deliver-demand-driven-outcome` Skill 已出现在列表中。需要确定性
   验证时，显式选择该 Skill。
4. 运行 Codex `host-check`，再用全新 Golden Tasks 验证实际行为。

本地市场声明是 [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json)，插件包是
[`plugins/yiyuan-accord-codex`](plugins/yiyuan-accord-codex)。OpenAI 当前官方说明明确要求显式
安装，并在目录变化后重载宿主、安装后新建任务：见[打包插件](https://developers.openai.com/plugins/build/plugins)
与[使用插件](https://learn.chatgpt.com/docs/plugins)。

### Claude Code

在仓库根目录为一个本地会话直接加载插件：

```powershell
claude --plugin-dir ./plugins/yiyuan-accord-claude
```

随后确认 `/yiyuan-accord-claude:deliver-demand-driven-task` 已出现。该方式用于本地使用与测试，
不会建立持久安装；参见 [Claude Code 官方插件说明](https://code.claude.com/docs/en/plugins)。

宿主没有明确列出插件或 Skill，就不能称为已启用。本项目有意不提供安装器、后台运行时、
Hook、MCP 服务、App、状态库或自动用户配置写入。

## 产品包含什么

- 三份语义权威：[`constitution.json`](product/constitution.json)、
  [`program.json`](product/program.json) 与
  [`acceptance.json`](product/acceptance.json)
- 统一术语与边界：[`CONTEXT.md`](CONTEXT.md)
- 一个数据驱动的通用验证器：
  [`yiyuan_accord/control.py`](yiyuan_accord/control.py)
- 可替换、无运行时的 Codex 与 Claude Code Skill 投影
- 帮助与干扰代表任务：[`evals/golden-tasks.json`](evals/golden-tasks.json)

可移植循环是 K1–K5：目标优先、最小充分路径、人类权限、持续校准与闭环。H1–H10 宿主规则
和 L1–L7 试错标准把宿主漂移与历史失败留在核心之外。

## 证据与发布状态

本 checkout 描述 v2.0 源码线；外部状态由精确 revision 与 tag 决定，而不是由分支名决定。
验证器通过表示当前 checkout 符合有限仓库契约，其中包括已接纳代表性观察的完整性与验收映射；
它不会独立重放宿主行为，也不等于精确候选本地复核、托管验证、真实场域价值、生产安全、
公开授权或项目收官。精确验收条件和外部门见
[`product/acceptance.json`](product/acceptance.json)，有限主张与保留行为失败见
[`docs/releases/v2.0.md`](docs/releases/v2.0.md)。

上一公开 tag 保持不可变历史；其观察不会被改名或复用为 v2.0 身份与投影的证据。

## 需要时再深入

- 架构与信任边界：[`docs/architecture.md`](docs/architecture.md)
- 维护者续接：[`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md)
- 后续开发、维护与参与贡献：[`CONTRIBUTING.md`](CONTRIBUTING.md)
- 安全边界与报告：[`SECURITY.md`](SECURITY.md)
- 项目分析输入：[`research/reviews`](research/reviews)

YIYUAN Accord 采用 Apache-2.0 许可证，另见 [`NOTICE`](NOTICE) 与
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
