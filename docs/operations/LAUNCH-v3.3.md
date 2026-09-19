# 3.3 发布材料工作稿

状态：通用发布准备，未排期、未提交，3.3尚未完成验收或正式发布。本文复用[共识计划](PLAN-v3.3.md)的W08/S5，不新增产品验收或发布日期。

## 文案底稿

以下表达产品定位和设计目标；正式发布前须按精确版本的验收结果校准，不能直接作为已实现能力声明。

| 字段 | 英文稿 | 中文含义 |
|---|---|---|
| 产品名 | YIYUAN Accord | 项目统一名称 |
| Tagline | Keep human-AI work aligned from intent to delivery | 让人与AI的协作从意图到交付保持一致 |
| Description | An open-source collaboration reliability system for AI agents. Designed to preserve goals, handle changes, coordinate capabilities, and verify delivery throughout ongoing work. | 面向AI Agent的开源协作可靠性系统，旨在持续工作中承接目标、处理变化、协调能力并核验交付。 |

项目发布说明底稿：

> We started YIYUAN Accord after repeated collaboration failures: an interruption could displace the original goal, a handoff could lose constraints, and passing checks could still leave the actual job unfinished.
>
> The project explores how agents can carry those responsibilities through real work, combining host capabilities with scoped coordination and verification. Users keep control over their decisions and changes of direction.
>
> The project remains independent and vendor-neutral. For the release, we will show the exact supported environment, a reproducible task, the verified outcome, and the remaining limitations.

正式稿须填入已验版本、实际使用入口和演示链接，并按实际成品校准能力与限制。涉及工具或模型的致谢须据实说明其作用，不能声称全部历史由同一模型构建。

## 演示与可复用素材

采用一条约60–90秒的真实任务录屏，脚本为待验证的拍摄意图：

1. 用户提出可核验的实际目标，展示源材料及初始限制。
2. 用户补充或改变条件，Agent解释影响并继续必要工作。
3. 仅在正式支持且自然需要时展示恢复或承接；保留实际边界和等待，不拼接不同试验冒充一条自主链。
4. 展示成品、独立检查、受保护材料和未完事项的最终处置。

封面和三张配图分别解释问题、实际协作过程、可核验结果及支持范围。优先从同一真实录屏提取，沿用README系统图；图示标明职责关系，不把设计图当执行证据。获准公开前排除凭据、私人对话和无关账号信息。尚未拍摄或制作图片、视频。

## 发布前待补齐的事实

| 内容 | 当前情况 | 完成条件 |
|---|---|---|
| 精确发行与更新日志 | 3.3开发中 | 验收、候选审查、正式发布授权及同版本公开后态成立 |
| README整体修订 | 用户已授权按最新共识按需更新，发布前仍需整体校准 | 发布前按实际成品整体复核中英文定位、能力及限制、安装使用、示例、徽章与链接，不能仅沿用开发期文案 |
| 安装与使用入口 | 待正式版本绑定 | 新用户能取得精确包，按真实支持条件完成安装和使用；市场收录不冒充必需前提 |
| 演示及效果说明 | 已有局部试验，不是完整演示 | 同版本真实完整任务、可复验成品、参与边界及限制 |
| 发布页面 | 本文仅底稿 | 更新文案、缩略图、截图、视频、关联工具致谢和可用链接；在实际发布表单重新检查限制 |

2026-09-14用户提议增加知乎和Reddit，当前作为传播候选，尚未排期或发布。建议知乎以中文案例解释问题、设计取舍和适用边界；Reddit以英文演示、复现材料及具体问题征求社区反馈。优先复用同一真实成果并按平台改写；以项目为传播主体，明确作者关系，不将渠道数量或曝光作为产品质量。Reddit的[官方反垃圾信息规则](https://support.reddithelp.com/hc/en-us/articles/360043504051-Spam)要求避免重复群发，并检查各社区具体规则；实际选定社区和发布前再核对。具体平台规则在实际发布前核对。渠道选择不改变项目优先、版本验收及正式对外提交的原有边界。
