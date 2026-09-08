# YIYUAN Accord

<p align="center">
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/yiheng8023/YIYUAN-Accord/validate.yml?branch=main&amp;label=CI&amp;logo=github" alt="CI status"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/releases/latest"><img src="https://img.shields.io/github/v/release/yiheng8023/YIYUAN-Accord?color=blue&amp;label=Release" alt="Latest release"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/stargazers"><img src="https://img.shields.io/github/stars/yiheng8023/YIYUAN-Accord?style=flat&amp;logo=github&amp;color=ffaa00" alt="GitHub stars"></a>
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/network/members"><img src="https://img.shields.io/github/forks/yiheng8023/YIYUAN-Accord?style=flat&amp;logo=github&amp;color=grey" alt="GitHub forks"></a>
  <img src="https://img.shields.io/badge/Python-3.10%E2%80%933.14-3776AB?logo=python&amp;logoColor=white" alt="Python 3.10 through 3.14 CI">
  <img src="https://img.shields.io/badge/CI-Ubuntu%20%7C%20Windows%20%7C%20macOS-lightgrey" alt="CI on Ubuntu, Windows, and macOS">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/yiheng8023/YIYUAN-Accord?color=green" alt="Apache-2.0 license"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文</a>
</p>

Accord's goal is simple: users focus on ideas and decisions; the Agent takes care of the authorized work needed to deliver them.

Today, Accord supplies collaboration guidance through Codex and Claude plugins, plus repository tools for checking its contracts and evidence. It is not a separate autonomous worker. Reliable end-to-end behavior and added value must be demonstrated in the host where it is used.

> **Current release: [v3.2.1](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.2.1).** Before installing, verify the matching GitHub Release and immutable tag; installed versions do not update automatically. Earlier release tags remain unchanged.
>
> Start with [scope and limitations](#what-is-proven-and-what-is-not), [what changed](CHANGELOG.md), or the [3.3 plan](docs/operations/PLAN-v3.3.md) (development starts with ChatGPT/Codex; functionality not yet accepted). The [historical 3.2 plan](docs/operations/PLAN-v3.2.md) retains its original scope. Use an accepted exact tag rather than a moving branch.

## What problem it addresses

Agents can produce substantial work while losing the goal, repeating decisions, leaving interrupted tasks unfinished, or confusing a successful check with a delivered result. Users then become coordinators of the tool.

Accord aims to reduce that avoidable work. The user supplies intent, consequential decisions, acceptance and accountability. Within that authority, the Agent should handle discovery, execution, correction, verification, continuity and cleanup.

You should not have to learn internal terminology or invoke a special command on every task. For example:

> Continue this project toward the agreed release. Preserve existing work, check the actual result, and ask me only when a decision or new authority is genuinely needed.

This is a design objective, not a promise that installing a plugin makes every host capable of it. If the native Agent already handles the task adequately, Accord should not add ceremony.

## What you actually get

Both 3.2 packages contain a `deliver-demand-driven-outcome` Skill, host metadata, a short-lived `SessionStart` hint and an optional task-local file checkpoint connected to supported native events. The Claude package adds advisory tool-result feedback and an optional update-inspection helper.

- **Skill:** instructions the host Agent can use for an applicable task. Visibility and invocation are separate from a useful effect.
- **Session hint:** a stateless hint on supported `compact` or `resume` events; this hint stays silent on `startup` and `clear`.
- **Optional checkpoint:** checks task files against Agent-selected conditions, tracks input freshness and unfinished work, and requests bounded continuation through supported native events. The Agent owns task meaning, execution and recovery.
- **Repository tools:** contract checks and a reference core for maintainers. The reference core is not installed or called by either plugin.

The packages add no persistent service, MCP server, SDK dependency, conversation database or telemetry collector. They do not replace your instruction or configuration files. Installation still changes the host's plugin registration and cache through its lifecycle.

This describes the present package, not a permanent ban on runtime support. 3.2 may replace a Skill, Hook or other mechanism when the required outcome and evidence justify it.

## Operating costs and capability limits

Accord injects guidance and optional hints to influence Agent decisions and actions. Loaded content uses context; extra checks or tool calls may also add tokens, latency and charges. These are operating costs to measure, not evidence of harm or benefit by themselves. Evaluate outcomes, reliability, rework, user effort and full lifecycle cost together, while preserving required safety and authorization. Small successful samples do not establish savings.

Possible adverse effects include conflicting instructions, displaced useful context, excessive intervention, unnecessary questions or checks, misrouting and variable behavior. Development observations have included unused Skills, non-delivery within budget, inaccurate output descriptions and an unauthorized attempt to archive a source task during handoff. Guidance has been revised; that does not prove these problems are resolved on every host, or that Accord caused every failure. See the scoped counterevidence in the [development source](product/development.json). Ordinary-use gains remain unverified.

Accord organizes and guides existing capabilities. **It does not train or modify the model, enlarge its native context capacity, or bypass host interfaces, permissions and execution limits.** It cannot guarantee completion, automatic recovery or reliable handoff. Authorized external tools can extend the composed system's task range while adding dependencies and cost; this does not raise the intrinsic capability ceiling of the model or host.

Testable critical constraints should use repeatable checks, with counterexamples that challenge the checks themselves. Checks may omit requirements or encode wrong expectations; reconcile intent, authority, decision criteria and actual results. The current plugins provide guidance and context hints, do not intercept host tool calls, and are not a permission barrier. Repository checks do not prove host enforcement. See the [contributor guidance](CONTRIBUTING.md#verification-and-publication).

Compare the intervention's value on verified tasks. When costs or interference outweigh benefits, narrow its use, disable it or remove it through supported host controls and verify the remaining state.

## How 3.2 is being judged

Safety and the agreed result come before reducing code, cost or intervention. Within those limits, the route adapts to the task rather than following a universal SOP.

User intent and authority, revisable plans, and progress presentation have separate roles. New evidence can change the route, procedure and explicitly justified acceptance; the progress view maps the current plan. No planning or scheduling tool is a mandatory execution prerequisite for the project.

Use native capabilities as a low-burden starting point, not a stopping rule. A meaningful gap or plausible improvement can justify comparing maintained alternatives beyond installed tools, using supported host discovery and reliable external sources. Compare full effects and lifecycle cost; discovery does not authorize installation. Stop research when further search is unlikely to change the choice, then return to delivery.

Review covers known failures **and unlisted design, integration and environmental blind spots**. A necessary outcome cannot disappear merely because its implementation is inconvenient; a redundant mechanism need not survive because it existed in 3.1.

The key question is whether ordinary use produces better supported outcomes or less avoidable user intervention, correction and recovery. More rules, visible activity, Skill calls or green checks are not evidence of benefit.

### Hosts and entry points

The review distinguishes Codex/ChatGPT and Claude families, then their CLI, desktop modes, IDE integrations, web/cloud, mobile/remote and programmatic entries. Other vendors are deferred.

A shared engine does not imply identical settings, permissions, installed capabilities or execution locations. A successful CLI test cannot qualify Desktop, an IDE or cloud. Model/provider identity is also separate from the host name.

See the dated [entry and capability matrix](docs/operations/PLAN-v3.2.md#宿主家族与入口边界). A listed entry is not a compatibility promise. Default hosts and customized hosts both need applicable evidence; development-only extensions must not be assumed available to other users.

## What is proven and what is not

[v3.1.0](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.1.0) was published on 2026-09-03 at [258611b](https://github.com/yiheng8023/YIYUAN-Accord/commit/258611be47c47a884b6d1a2e96889cf688ca7e68). Its tag and Release are immutable.

Its finite claims cover collaboration-contract conformance, static Codex/Claude package conformance, one bounded internal-use result, local continuity/repair/resource regressions and reproducibility from the exact checkout. See the [release evidence and exclusions](docs/releases/v3.1.0.md).

Those checks do not prove broad user benefit, automatic crash recovery, current-client compatibility, production safety or every entry point. They also do not qualify changed 3.2 bytes.

The retained local observations cover real delivery and correction, response to an in-flight question, capability failure and source conflict, declared installation/update/recovery compositions, and two Desktop continuity branches. Current applicability is assessed against complete package changes, including actual dev.17 native input callbacks and local failure/recovery checks. These are finite observations with explicit human or surviving-manager assistance, not universal autonomous behavior.

The bounded Claude comparison delivered and checked both stages with and without Accord. It found no observed reliability increment; one pair's time, denials or reported costs cannot establish causal benefit. Earlier non-delivery and inaccurate descriptions remain in the evidence. The final checkpoint also preserves recovery context when input fails during retirement; 25 local runtime regressions passed.

The two latest native input methods remain recorded as failed overall: Claude made one loopback request of unknown purpose, while Codex needed forced cleanup of an unidentified child after its main process exited. Their captured input receipts remain valid limited facts. Codex reports receiving the input context; Claude's corresponding hint consumption is unproven. Post-exit local replay is not autonomous host recovery. Complete evidence was retained and the owned roots removed.

The [changelog](CHANGELOG.md) and [source](product/development.json) separate implementation, original observations, counterevidence and current qualification. Exact release acceptance and hosted results belong to the matching Release; a CLI static PASS does not supply them.

Candidate qualification requires the declared functions, lifecycle and a sufficient impact assessment for each host. A claim of improvement over native behavior separately requires positive evidence; this candidate makes no such supported claim. The earlier positive-witness release gate and its unmet hypothesis remain in history. The revised gate still rejects unresolved material regressions, input/authority harm and unknowns essential to the declared use. Completing an assessment alone does not establish suitability or release readiness.

Development observations cover specific Windows local Codex and Claude Code entries, with an existing authorized model route, required file/command permissions and observed package loading. Codex App Server evidence does not automatically cover Desktop, IDE or cloud entries. Desktop observations cover the declared maintenance continuation and user-authorized takeover. Other combinations require their own applicability check. Ordinary Claude use does not require Codex, Python or the development evaluation scripts.

Healthy automatic compaction followed by reconciled useful work supports same-carrier continuation. A user-requested takeover supports that actual transfer, not autonomous early detection. Prediction, optimal transfer margins and runtime unloading remain unproven. If a task depends on those guarantees, the missing evidence becomes a necessary gap; the retained samples cannot waive it.

The host Agent interprets the Skill. Enabled Hooks require Node on `PATH`, the relevant native events and host trust support. Each input Hook maintains a temporary freshness receipt and supplies a hint even when no file checkpoint is bound. Unbound, reconciled receipts are removed on a supported session end or by a surviving caller after verified exit. Input-failure watermarks remain until their owning state directory can safely be retired; one task must not clear another session's uncertainty. If a failure cannot be stored, freshness is unknown and the native caller must hold continuation. Input/state JSON is limited to 128 KiB; an oversized input requires recovery through a sufficient native path, not silent truncation. Without Hook support, the host's ordinary task path remains responsible and any missing continuation effect must be disclosed.

Installation, update and recovery need a healthy executor independent of the damaged/replaced plugin, a verifiable accepted source and the necessary authority. The retained Claude damaged-cache/source-conflict recovery used a healthy Codex manager with explicit authorization and assistance. It does not prove automatic manager discovery or unattended Claude recovery, and it does not make those development tools ordinary-use prerequisites.

## Install an accepted exact version

Ask a capable Agent host to handle the lifecycle:

> Verify that v3.2.1 has a matching accepted GitHub Release, then inspect this host and install that exact tag. Preserve unrelated configuration and plugins, request necessary trust, and verify registration, visibility in the session actually being used and remaining limitations. If the release is unavailable, stop rather than installing a moving development branch.

This is the intended interaction, not a guarantee that every host can complete it unattended. Plugin support, repository access and authority to change plugin state are prerequisites. The Hook additionally needs Node on `PATH` and a supported host trust flow.

Do not bypass trust or edit global settings to simulate supported installation. If a prerequisite is absent, report it. GUI labels change; use the actual client's supported entry instead of an old screenshot.

<details>
<summary>CLI installation references</summary>

These use the recorded exact-tag route with the selected 3.2 tag. First verify its Release and current command support; this is not fresh lifecycle acceptance for every client.

Codex:

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.2.1
codex plugin add yiyuan-accord-codex@yiyuan-accord
codex plugin list --json
```

Claude Code:

```powershell
claude plugin marketplace add "https://github.com/yiheng8023/YIYUAN-Accord.git#v3.2.1" --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
claude plugin marketplace list --json
claude plugin list --json
```

The repository root is the marketplace, not the package subdirectory. Preserve same-named state owned by other scopes or installations.

</details>

### Check the effect, not just the installation

Let the Agent verify the exact source and installed bytes, enabled registration, Skill visibility in the session actually being used, and relevant invocation separately. An already open session may retain an older Skill catalog after installation or update; successful loading in another fresh session does not establish that the original session refreshed. Prefer supported host refresh or re-entry controls and check actual exposure in the original task. An independent CLI/App Server query does not establish that an already running Desktop process refreshed. If Desktop still exposes the old catalog even in a new task, use the supported application restart, preserve unfinished work, and check the actually loaded version afterwards. [Official skill refresh guidance](https://learn.chatgpt.com/docs/build-skills). If a new task is necessary, obtain the applicable authorization and preserve the goal and unfinished work; do not automatically create or archive tasks. A listing or reload command alone is insufficient.

When an installation appears inactive, distinguish missing Skill exposure, exposure without selection, selection followed by failed execution, and execution without observable benefit. A Hook hint does not mean the full Skill was loaded. Checkpoint `unbound` means no file-result conditions are bound; it alone does not prove plugin failure. The Agent should own these checks and supported recovery without requiring the user to keep naming the Skill during ordinary use.

When checking input-triggered behavior, distinguish a message submitted in the user input box from a tool-output task continuation; the latter is not automatically equivalent to `UserPromptSubmit`. Check the delivered event, Skill loading and outcome for the actual entry separately.

Then inspect a real, authorized task: what was delivered, what the user still had to manage, and whether unrelated state or residue was left behind. Explicit Skill selection can test exposure; it cannot prove ordinary activation or incremental value.

If there is little observable benefit, record that finding. Do not invent a missing native capability or add activity to make Accord noticeable.

### Update, roll back or remove

Give one bounded lifecycle intent. The Agent should identify the current registration, preserve foreign/shared state, use supported host operations and verify the result. Record the old exact tag before changing versions.

Exact tags do not advance automatically. The recorded replacement route removes the Accord package and its owned marketplace registration, then installs the chosen exact tag. This is not an atomic hot update; a failed target may require restoring the previous tag and verifying recovery.

Loaded sessions and installed files are different states. Do not delete host-owned caches outside supported lifecycle rules or call an inert cache physical zero residue. CLI commands and historical limits remain available in the [immutable 3.1 README](https://github.com/yiheng8023/YIYUAN-Accord/blob/v3.1.0/README.md#update-rollback-removal-and-source-verification); recheck current host support before use.

## Develop, evaluate or contribute

For this branch, start with [product/development.json](product/development.json), the [visible plan](docs/operations/PLAN-v3.2.md), [architecture](docs/architecture.md) and [continuation](docs/operations/CONTINUATION.md). Frozen 3.1 authority and Golden Tasks are historical inputs, not current development acceptance.

Maintainer checks do not require plugin installation:

```powershell
python -B -m yiyuan_accord verify-development --json
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

Use `python3` where that is the available launcher. CI exercises Python 3.10–3.14 across Ubuntu, Windows and macOS, with Node 24 for Hook checks. That is maintainer validation, not cross-host behavior acceptance or an end-user Python requirement.

Publication requires matching release notes, committed and pushed in-scope changes, necessary functional/lifecycle/impact evidence, independent review and hosted checks, followed by publication and public verification of the same commit under the bound human authorization. A frozen candidate is not a release receipt.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [SUPPORT.md](SUPPORT.md). In an [issue](https://github.com/yiheng8023/YIYUAN-Accord/issues), describe the desired and observed result, exact version, host/entry, relevant customization and human intervention. Never upload credentials or private raw transcripts.

---

## Vision and collaboration

YIYUAN NEXUS will continue to explore human-machine collaboration and related fields. YIYUAN Accord is not intended to exist forever: it will evolve as frontier intelligence, human and machine capabilities, and patterns of collaboration change. Progress in frontier intelligence both gives Accord new capabilities and continually tests its necessity, boundaries, and real-world value. When its mission has been fulfilled, carried forward by better mechanisms, or is no longer needed, the project should be able to conclude responsibly and in an orderly way.

YIYUAN NEXUS currently has one author-maintainer, with limited capacity, time, and resources. We welcome the community to create and advance it together. Within those practical limits, Accord will continue to be maintained and evolved, with progressively broader host adaptation as an ongoing direction. A roadmap direction is not a claim of current support or a commitment to a release date or compatibility outcome.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) to participate. Submit problems and suggestions through [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues).

---

## Community

### Contributors

Thank you to everyone who contributes code, reviews, documentation, issue reports, and evidence.

<p align="center">
  <a href="https://github.com/yiheng8023/YIYUAN-Accord/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=yiheng8023/YIYUAN-Accord" alt="YIYUAN Accord contributors">
  </a>
</p>

### Star history

[![YIYUAN Accord Star History](https://api.star-history.com/svg?repos=yiheng8023/YIYUAN-Accord&type=Date)](https://star-history.com/#yiheng8023/YIYUAN-Accord&Date)

---

## Project support and legal

### Project and license

The public project and website are [github.com/yiheng8023/YIYUAN-Accord](https://github.com/yiheng8023/YIYUAN-Accord).

The publisher is [yiheng8023](https://github.com/yiheng8023).

YIYUAN Accord is licensed under Apache-2.0.

Commercial use, modification, and redistribution are permitted under that
license; they do not grant permission to present a modified or redistributed
version as official, sponsored, or endorsed.

The canonical public source is this repository. Official versions are
identified by matching Git tags and GitHub Release records, and each standalone
Codex or Claude plugin package carries its own `LICENSE` and `NOTICE` after
installation.

The YIYUAN Accord and YIYUAN NEXUS names and symbols remain separate
trademarks. See [`NOTICE`](NOTICE), [`docs/license-policy.md`](docs/license-policy.md),
and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

Community help is provided on a best-effort basis under [`SUPPORT.md`](SUPPORT.md).

### Voluntary sponsorship and support

Sponsorship is optional.

It does not purchase a support SLA, priority, release authority, safety guarantee, governance exception, feature commitment, or influence over technical decisions.

If Accord is useful, you may support maintenance through the repository owner's [published PayPal page](https://www.paypal.com/ncp/payment/LNTF8KXGJXMZY).

<table>
  <tr>
    <th width="300">WeChat Pay (CNY)</th>
    <th width="300">Alipay (CNY)</th>
  </tr>
  <tr>
    <td align="center" valign="middle" width="300" height="430"><img src="docs/assets/sponsoring/wechat-pay.png" alt="WeChat Pay voluntary sponsorship QR code" width="260"></td>
    <td align="center" valign="middle" width="300" height="430"><img src="docs/assets/sponsoring/alipay.png" alt="Alipay voluntary sponsorship QR code" width="260"></td>
  </tr>
</table>

Verify the recipient before paying. See [`SPONSORING.md`](SPONSORING.md) for the complete terms.

### Disclaimer and compliance

YIYUAN Accord is an independent community open-source project.

It is not an OpenAI, Anthropic, Codex, Claude, Claude Code, or GitHub product. Those parties do not sponsor or endorse it.

Third-party names and marks belong to their respective owners.

Users remain responsible for reviewing Agent outputs and complying with applicable laws, contracts, host terms, licenses, and organizational policies.

The software is provided under Apache-2.0 on an “AS IS” basis, without warranties or conditions. See [`LICENSE`](LICENSE).

A full project release does not establish production safety or fitness for a particular purpose.
