# YIYUAN Accord

Turn a desired outcome into a verified, recoverable finish—without forcing the user to manage the Agent's tools, topology, or internal mechanics.

YIYUAN Accord is an open, Agent-neutral and mechanism-neutral human-Agent
collaboration system: a small portable reliability kernel plus adaptive,
replaceable outcome-delivery behavior.

It anchors the Agent to the user's current goal, selects the minimum sufficient route, and preserves human authority at real decision boundaries.

It reconciles corrections and observed effects, then closes with verification, explicit unknowns, and residue cleanup.

The broader mission is advancing human-AI collaboration. The current product surface and empirical evidence are deliberately scoped to human-Agent collaboration.

[简体中文](README.zh-CN.md)

> **Current release:** use the immutable
> [`v3.0.0`](https://github.com/yiheng8023/YIYUAN-Accord/tree/v3.0.0)
> full release when that tag exists. Until then, the last published installable
> version remains
> [`v2.0.1-preview.1`](https://github.com/yiheng8023/YIYUAN-Accord/tree/v2.0.1-preview.1).
> Never install from a moving `main` checkout.

---

## Release maturity and evidence

v3.0.0 is a full project release rather than another prerelease. “Full release”
means the exact repository, packages, finite claims and declared local/hosted
gates passed; it does not mean universal behavior, production safety or every
Agent and client surface is proven. The test corpus remains deliberately finite,
so representative use, counterexamples and failures belong to continuing
evidence.

Report feedback in [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues). Include:

- exact tag and revision;
- host, version, and installation route;
- requested outcome and starting state;
- observed result and human interventions; and
- material effects, residue, and remaining unknowns.

Never include credentials or private session content.

---

## Start in 30 seconds

### Before installation

Use a current Codex or Claude surface with plugin support, network access to the
public repository, permission to change user-level plugin configuration, and a
new task or session after installation. Accord does not require one fixed host
or model version; record the version and route actually used.

### Codex

Install the exact immutable tag:

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.0.0
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

Restart the desktop app or start a new CLI session. Open **Plugins** or run
`/plugins`, then confirm `YIYUAN Accord for Codex` and
`deliver-demand-driven-outcome` are present.

### Claude clients and Claude Code

In Claude Desktop Chat, Claude web chat or Cowork, open
**Customize > Plugins**, add
`https://github.com/yiheng8023/YIYUAN-Accord` as a personal marketplace, install
**YIYUAN Accord for Claude**, start a new chat and confirm
`deliver-demand-driven-outcome` is visible.

For a persistent Claude Code installation:

```powershell
claude plugin marketplace add yiheng8023/YIYUAN-Accord@v3.0.0
claude plugin install yiyuan-accord-claude@yiyuan-accord
```

The repository root is the marketplace; the package subdirectory is not. For a
single development session only, run
`claude --plugin-dir ./plugins/yiyuan-accord-claude` from the repository root
and confirm `/yiyuan-accord-claude:deliver-demand-driven-outcome` in `/help`.
Use `/reload-plugins` after checkout changes.

### What installation changes

Installation makes one progressively disclosed adaptive Skill available. The
v3 packages themselves add no Runtime, Hook, MCP server, App, state store,
background process or automatic project mutation. This package fact is not a
permanent product prohibition: a later task may use or propose another bounded
mechanism when current evidence and authority justify it.

Installation, enablement and visibility do not imply activation. During normal
work the host may invoke the Skill implicitly for a relevant nontrivial task;
it should stay silent when a healthy native route is sufficient. Select the
Skill explicitly only for a deterministic exposure check.

---

## What It Changes

You describe the intended outcome in natural language.

Accord guides the Agent to own supported operational mechanics while reserving consequential judgment, new trust grants, cost commitments, public release, and irreversible side effects for the human.

Accord does not require an Agent to imitate a person. People, models, and their
shared information are all finite; this project works only on the collaboration
boundary it can actually influence.

Different machine-native routes are welcome when they deliver the human outcome
with less burden and honest evidence.

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

Accord is not a prompt template that users must study. A plain request is
always sufficient.

---

## Update, rollback, removal and source verification

Confirm lifecycle state on the same surface that installed the package. Use
`codex plugin list --json`, `claude plugin list --json`, or
**Customize > Plugins**; a difference between surfaces is observed host state,
not automatic proof of failure.

An immutable ref never advances. To update or roll back Codex, remove the
installed package and marketplace, then reinstall the intended exact tag:

```powershell
codex plugin remove yiyuan-accord-codex@yiyuan-accord
codex plugin marketplace remove yiyuan-accord
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref VERSION_TAG
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

For Claude Code, use the host lifecycle commands; use **Customize > Plugins**
for the equivalent client actions:

```powershell
claude plugin marketplace update yiyuan-accord
claude plugin update yiyuan-accord-claude@yiyuan-accord
claude plugin uninstall yiyuan-accord-claude@yiyuan-accord
```

Prefer native hot reload when supported. Otherwise use an atomic versioned
replacement, verify health and restore the prior exact version on failure.
Never move an existing tag or edit global host configuration as a substitute
for supported lifecycle commands.

For source verification, clone the exact tag and use a Python interpreter with
the required standard-library capabilities. The current release CI exercises
CPython 3.10–3.14; that matrix is compatibility evidence, not a permanent
version whitelist or part of Accord's product identity. Run:

```powershell
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

These checks validate deterministic repository and package conformance. They do
not install a plugin, prove implicit activation, establish field value, grant
release authority or establish production safety.

---

## What the repository contains

- **Current schema-v3 authority set**:
  [`constitution.json`](product/constitution.json),
  [`program.json`](product/program.json), and
  [`acceptance.json`](product/acceptance.json)
- **Accepted, revisable reshape and dynamic-index guidance**:
  [`reshaping-guidance.json`](product/reshaping-guidance.json)
- **Derived Vocabulary & Boundary**: [`CONTEXT.md`](CONTEXT.md)
- **Data-Driven Generic Verifier**:
  [`yiyuan_accord/control.py`](yiyuan_accord/control.py)
- **Adaptive v3 host projections**: Codex and Claude packages with one shared
  `deliver-demand-driven-outcome` Skill name and host-specific manifests
- **Representative Help-and-Interference Tasks**:
  [`evals/golden-tasks.json`](evals/golden-tasks.json)

The portable contract is **K1–K5**. Host rules **H1–H10** and learned-failure rules **L1–L7** keep host drift and trial history outside the core.

Those three authority files are the current reviewable bootstrap, not
unquestionable truth, a permanent file count or a ceiling defined by the
capabilities visible in today's hosts.

A later merge, split, replacement, or retirement must preserve provenance and
migrate the schema, verifier, mappings, and affected evidence explicitly.

---

## Adaptive product boundary

Accord is not limited to the capability surface of Codex, Claude or any other
concrete Agent. Each Agent and host capability surface is a replaceable adapter
plus a freshness-bound observation. The portable product covers the
Agent-neutral dynamic relation from requirement to capability, authority, route,
observed effect and evidence; native, official, maintained, composed or bounded
authored mechanisms can enter when current facts and lifecycle value justify
them.

A Skill, plugin, App, MCP, Hook, configuration, state, runtime, cloud carrier or
another mechanism is neither mandatory nor permanently forbidden. Visibility or
installation does not imply activation. A sufficient native path should produce
no avoidable intervention, while a residual gap can justify scoped machinery
with interference, update, rollback and retirement controls.

The v3 repository candidate maps one real outcome across plan, context-tailored
process, acceptance and a compact goal projection; replays the exact adaptive
Skill on the bounded GT-11 slice; and requires all eight repository criteria.
The canonical verifier does not evaluate hosted, human, tag, public Release or
cleanup completion. Those gates remain external and ordered for the unchanged
SHA. Immutable v2.0 and v2.0.1-preview.1 remain historical public facts;
preview.2 was never published and must not be tagged. See
[`product/reshaping-guidance.json`](product/reshaping-guidance.json) and
[`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md).

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

The software is provided under Apache-2.0 on an “AS IS” basis, without warranties or conditions; see [`LICENSE`](LICENSE). A full project release does not establish production safety or fitness for a particular purpose.
