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

> **This branch develops 3.2.** Its packages are `3.2.0-dev.5`, not a published release or an update to your installed version. Published [v3.1.0](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.1.0) remains unchanged.
>
> Start with [current limitations](#what-is-proven-and-what-is-not), the [development plan](docs/operations/PLAN-v3.2.md), or the [unreleased changelog](CHANGELOG.md). Do not install from moving `main` or this development branch.

## What problem it addresses

Agents can produce substantial work while losing the goal, repeating decisions, leaving interrupted tasks unfinished, or confusing a successful check with a delivered result. Users then become coordinators of the tool.

Accord aims to reduce that avoidable work. The user supplies intent, consequential decisions, acceptance and accountability. Within that authority, the Agent should handle discovery, execution, correction, verification, continuity and cleanup.

You should not have to learn internal terminology or invoke a special command on every task. For example:

> Continue this project toward the agreed release. Preserve existing work, check the actual result, and ask me only when a decision or new authority is genuinely needed.

This is a design objective, not a promise that installing a plugin makes every host capable of it. If the native Agent already handles the task adequately, Accord should not add ceremony.

## What you actually get

Both released 3.1 packages contain a `deliver-demand-driven-outcome` Skill, host metadata and a short-lived `SessionStart` Hook helper. The current 3.2 development packages retain that shape while revising the guidance.

- **Skill:** instructions the host Agent can use for an applicable task. Visibility and invocation are separate from a useful effect.
- **Hook:** a stateless hint on supported `compact` or `resume` events. It stays silent on `startup` and `clear`; it does not inspect task meaning, recover a failed process or complete a handoff.
- **Repository tools:** contract checks and a reference core for maintainers. The reference core is not installed or called by either plugin.

The packages add no persistent service, MCP server, SDK dependency, conversation database or telemetry collector. They do not replace your instruction or configuration files. Installation still changes the host's plugin registration and cache through its lifecycle.

This describes the present package, not a permanent ban on runtime support. 3.2 may replace a Skill, Hook or other mechanism when the required outcome and evidence justify it.

## How 3.2 is being judged

Safety and the agreed result come before reducing code, cost or intervention. Within those limits, the route adapts to the task rather than following a universal SOP.

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

**3.2 is not yet ready for release.** Some native-only development probes already completed the task without Accord. Current discovery probes also expose non-delivery within budget and inaccurate output descriptions. Invocation has not established added value.

The [changelog](CHANGELOG.md) and [development source](product/development.json) separate implemented changes, counterevidence and open work. Ordinary-entry effects, environment adaptation, surviving failure ownership, handoff and full package lifecycle still need suitable verification.

## Try the published version

Ask a capable Agent host to handle the lifecycle:

> Inspect this host and install YIYUAN Accord from the exact v3.1.0 tag. Preserve unrelated configuration and plugins, request any necessary trust, and verify registration, newly loaded visibility and remaining limitations.

This is the intended interaction, not a guarantee that every host can complete it unattended. Plugin support, repository access and authority to change plugin state are prerequisites. The Hook additionally needs Node on `PATH` and a supported host trust flow.

Do not bypass trust or edit global settings to simulate supported installation. If a prerequisite is absent, report it. GUI labels change; use the actual client's supported entry instead of an old screenshot.

<details>
<summary>CLI installation references</summary>

These are recorded exact-tag routes, not a fresh lifecycle acceptance result for every client. Inspect current command support before changing state.

Codex:

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.1.0
codex plugin add yiyuan-accord-codex@yiyuan-accord
codex plugin list --json
```

Claude Code:

```powershell
claude plugin marketplace add "https://github.com/yiheng8023/YIYUAN-Accord.git#v3.1.0" --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
claude plugin marketplace list --json
claude plugin list --json
```

The repository root is the marketplace, not the package subdirectory. Preserve same-named state owned by other scopes or installations.

</details>

### Check the effect, not just the installation

Let the Agent verify the exact source and installed bytes, enabled registration, newly loaded Skill visibility and relevant invocation separately. Open a fresh task/session before judging changed loaded behavior. A listing or reload command alone is insufficient.

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

Before releasing 3.2, reconcile release notes with the exact candidate; commit and push all in-scope changes; complete necessary functional, value and lifecycle evidence, independent review and hosted checks; then publish and verify the same commit under the bound human authorization.

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
