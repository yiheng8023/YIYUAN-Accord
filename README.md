# YIYUAN Accord

Turn a desired outcome into a verified, recoverable finish—without forcing the user to manage the Agent's tools, topology, or internal mechanics.

YIYUAN Accord is an open, Agent-neutral collaboration reliability contract and evaluation framework.

It anchors the Agent to the user's current goal, selects the minimum sufficient route, and preserves human authority at real decision boundaries.

It reconciles corrections and observed effects, then closes with verification, explicit unknowns, and residue cleanup.

The broader mission is advancing human-AI collaboration. The current product surface and empirical evidence are deliberately scoped to human-Agent collaboration.

[简体中文](README.zh-CN.md)

---

## Public Preview

This release is a public preview, not a production-stability claim. The test corpus is deliberately finite, so representative use, counterexamples, and failures from more users belong to the next evidence layer.

Report feedback in [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues). Include:

- exact tag and revision;
- host, version, and installation route;
- requested outcome and starting state;
- observed result and human interventions; and
- material effects, residue, and remaining unknowns.

Never include credentials or private session content.

---

## What It Changes

You describe the intended outcome in natural language.

Accord guides the Agent to own supported operational mechanics while reserving consequential judgment, new trust grants, cost commitments, public release, and irreversible side effects for the human.

Accord does not require an Agent to imitate a person. People, models, and their
shared information are all finite; this project works only on the collaboration
boundary it can actually influence. Different machine-native routes are welcome
when they deliver the human outcome with less burden and honest evidence.

Its portable loop operates on five stable constants:

1. **Outcome Anchor**: Start from the user's current goal and active corrections.
2. **Minimum Route**: Select the smallest sufficient execution path that can genuinely deliver the outcome.
3. **Authority Preservation**: Stop and surface only decisions that require new human judgment or authority.
4. **Dependency Reconciliation**: When a correction or new evidence invalidates current proof, replay from the earliest affected dependency boundary.
5. **Honest Closure**: Verify concrete effects, transparently disclose what remains unproven, and clean up transient execution residue.

Everything else is activated on demand by the task and host environment. If the host's native capability is already sufficient, Accord deliberately stays out of the way.

---

## When It Is Useful

- **Goal Drift**: A task drifts from the requested outcome despite generating a large volume of plausible, busy work.
- **Interrupted Workflows**: A long-running task is paused, corrected, or handed off across different execution carriers.
- **False Green Lights**: Tests, reports, intermediate commits, or hosted green checks are mistaken for real-world delivery.
- **Decision Boundaries**: The Agent should autonomously handle routine mechanics, but must strictly halt before genuine human decisions, privilege escalations, tangible costs, or irreversible mutations.
- **Cascade Corrections**: A mid-flight fix or updated rule invalidates earlier evidence, requiring a bounded downstream replay.

Accord is not a prompt template that users must study. A plain request is always sufficient—for example: *“Make this installation path accurate, preserve unrelated changes, verify it, and tell me what remains unproven.”*

---

## Install and use

Cloning is not plugin installation. Codex may read this checkout's `AGENTS.md` as local project guidance; that does not mean the YIYUAN Accord plugin is installed.

### Codex

Install the immutable v2.0.1-preview.1 public preview from its Git marketplace:

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v2.0.1-preview.1
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

Before that tag exists, release evaluators must exercise the exact clean source
bundle instead of treating an unavailable remote ref as installed:

```powershell
codex plugin marketplace add .
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

This local route proves only activation of the candidate package in that source
bundle. It does not verify a Git ref, GitHub availability, or the later public
installation route. Use the removal commands below when the walkthrough ends.

Then restart the desktop app to reload the catalog. Open **Plugins** (or run `/plugins` in the CLI), confirm that `YIYUAN Accord for Codex` and its `deliver-demand-driven-outcome` Skill are present, and Start a new task.

For a deterministic activation check, select the Skill explicitly in the UI/CLI. For normal work, state the outcome naturally; the Skill permits implicit invocation, but must remain silent when native behavior is already sufficient.

The repository-local catalog is [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json). The Codex package is [`plugins/yiyuan-accord-codex`](plugins/yiyuan-accord-codex).

OpenAI's current documentation covers [plugin packaging](https://developers.openai.com/plugins/build/plugins) and [using plugins](https://learn.chatgpt.com/docs/plugins).

### Claude Code

From the repository root, load the reference projection for one local session:

```powershell
claude --plugin-dir ./plugins/yiyuan-accord-claude
```

Confirm `/yiyuan-accord-claude:deliver-demand-driven-task` appears in `/help`. This direct-load route does not create a persistent installation. See the [official Claude Code plugin guide](https://code.claude.com/docs/en/plugins).

Changes to the checkout can be reloaded with `/reload-plugins`. To disable or remove a direct-loaded package, end the session and omit `--plugin-dir` next time.

---

## Update, disable or remove

Inspect the effective Codex installation with `codex plugin list --json`. Refresh a configured Git marketplace with:

```powershell
codex plugin marketplace upgrade yiyuan-accord
```

An immutable release ref never advances to a later tag. To update or roll back, replace `VERSION_TAG` with the intended exact tag, remove the installed plugin and marketplace, then install again and Start a new task:

```powershell
codex plugin remove yiyuan-accord-codex@yiyuan-accord
codex plugin marketplace remove yiyuan-accord
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref VERSION_TAG
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

Use **Plugins** to disable or re-enable the plugin without removing its marketplace. The first two commands remove both entries completely.

### Rollback and Troubleshoot

Rollback selects an earlier immutable tag; never move an existing tag. If activation is unclear, inspect the host's actual plugin or Skill list, then start a new task or session and run the matching host check.

If the host does not list the package or Skill, it is not enabled. Endpoint protection, host configuration, model routes, and interrupted sessions are test variables; record them separately from product behavior.

For a repository defect, report the exact revision, host version, relevant configuration boundary, and verifier output. Never include credentials or raw private session content.

---

## Verify the source and packages

Clone the exact release with Python 3.10–3.14 available:

```powershell
git clone --branch v2.0.1-preview.1 --single-branch https://github.com/yiheng8023/YIYUAN-Accord.git
```

Run the canonical verifier:

```powershell
python -B -m yiyuan_accord verify --root . --json
```

Check either reference projection statically:

```powershell
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

These checks validate repository and package conformance. They do not install a plugin, prove effective host behavior, satisfy field acceptance, authorize a release, or establish production safety.

---

## What the repository contains

- **Current schema-v2 authority set**:
  [`constitution.json`](product/constitution.json),
  [`program.json`](product/program.json), and
  [`acceptance.json`](product/acceptance.json)
- **Derived Vocabulary & Boundary**: [`CONTEXT.md`](CONTEXT.md)
- **Data-Driven Generic Verifier**:
  [`yiyuan_accord/control.py`](yiyuan_accord/control.py)
- **Replaceable, Runtime-Free Skill Projections**: Reference adapter projections for Codex and Claude Code
- **Representative Help-and-Interference Tasks**:
  [`evals/golden-tasks.json`](evals/golden-tasks.json)

The portable contract is **K1–K5**. Host rules **H1–H10** and learned-failure rules **L1–L7** keep host drift and trial history outside the core.

Those three files are the current reviewable topology, not unquestionable truth or a permanent file count. A later merge, split, replacement, or retirement must preserve provenance and migrate the schema, verifier, mappings, and affected evidence explicitly.

---

## Boundaries and evidence

Accord adds no installer, background runtime, Hook, MCP server, App, state store, or automatic user-configuration mutation. It relies on current host capabilities and keeps host-specific lifecycle mechanics in replaceable projections.

The v2.0.1-preview.1 line is a Public Preview presentation and usability repair over immutable v2.0.

It does not claim universal human-AI correctness, broad field effectiveness, cross-host equivalence, lower burden for every user, or production safety.

A valid verifier result proves only the finite repository contract for that checkout. Accepted behavior samples remain task-, host-, projection-, and revision-bound.

The retained `GT-07:cleanup` failure continues to narrow the claim instead of being rewritten as success.

Exact criteria and release gates are in [`product/acceptance.json`](product/acceptance.json). Finite release claims are summarized in [`docs/releases/v2.0.1-preview.1.md`](docs/releases/v2.0.1-preview.1.md).

---

## After this release

v2.0.1-preview.1 is a finite stage, not the end of the mission. Later work is admitted only from observed residual gaps, real-task evidence, or material host changes.

The continuing lanes include field effect, cross-host or longitudinal evidence, and representative tasks `GT-06`, `GT-09`, and `GT-10`.

Host improvements may let Accord simplify or retire a projection instead of adding machinery.

A missing feature is restored only when its user value, risk reduction, or recovery benefit exceeds its code, cognition, lifecycle, and operating cost.

---

## Project and license

The public project and website are [github.com/yiheng8023/YIYUAN-Accord](https://github.com/yiheng8023/YIYUAN-Accord). The publisher is [yiheng8023](https://github.com/yiheng8023).

Architecture and trust boundaries are in [`docs/architecture.md`](docs/architecture.md). Maintenance and contributions are described in [`CONTRIBUTING.md`](CONTRIBUTING.md).

Security reporting is in [`SECURITY.md`](SECURITY.md), and maintainer continuation is in [`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md).

YIYUAN Accord is Apache-2.0 licensed. The YIYUAN NEXUS name and symbol remain separate trademarks; see [`NOTICE`](NOTICE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

---

## Voluntary sponsorship and support

Sponsorship is optional. It does not purchase a support SLA, priority, release authority, safety guarantee, governance exception, feature commitment, or influence over technical decisions.

If Accord is useful to you, you may support its maintenance through the repository owner's [published PayPal page](https://www.paypal.com/ncp/payment/LNTF8KXGJXMZY).

| WeChat Pay (CNY) | Alipay (CNY) |
| --- | --- |
| ![WeChat Pay QR code](docs/assets/sponsoring/wechat-pay.png) | ![Alipay QR code](docs/assets/sponsoring/alipay.png) |

Verify the recipient before paying. See the full [`SPONSORING.md`](SPONSORING.md) terms. Community support remains best effort under [`SUPPORT.md`](SUPPORT.md).

---

## Disclaimer and compliance

YIYUAN Accord is an independent community open-source project. It is not an OpenAI, Anthropic, Codex, Claude, Claude Code, or GitHub product, and those parties do not sponsor or endorse it.

Third-party names and marks belong to their respective owners. The YIYUAN NEXUS mark identifies this distribution and is governed separately by [`NOTICE`](NOTICE).

Users remain responsible for reviewing Agent outputs and complying with applicable laws, contracts, host terms, licenses, and organizational policies.

The software is provided under Apache-2.0 on an “AS IS” basis, without warranties or conditions; see [`LICENSE`](LICENSE). This Public Preview does not establish production safety or fitness for a particular purpose.
