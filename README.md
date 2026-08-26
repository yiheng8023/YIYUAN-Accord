# YIYUAN Accord

Turn a desired outcome into a verified, recoverable finish—without forcing the user to manage the Agent's tools, topology, or internal mechanics.

YIYUAN Accord is an open, Agent-neutral and mechanism-neutral human-Agent
collaboration system: a small portable reliability kernel plus adaptive,
replaceable outcome-delivery behavior.

It anchors the Agent to the user's current goal, selects the minimum sufficient route, and preserves human authority at real decision boundaries.

It reconciles corrections and observed effects, then closes with verification, explicit unknowns, and residue cleanup.

The broader mission is advancing human-AI collaboration. The current product surface and empirical evidence are deliberately scoped to human-Agent collaboration.

[简体中文](README.zh-CN.md)

> **Current public recommendation:** use the immutable
> [`v2.0.1-preview.1`](https://github.com/yiheng8023/YIYUAN-Accord/tree/v2.0.1-preview.1)
> Public Preview. The current `main` tree is active reshaping work, not an
> installation or release candidate. The unreleased preview.2 route is retired.

> GitHub may still mark historical v2.0 as `Latest` because
> [prereleases cannot receive that marker](https://docs.github.com/en/rest/releases/releases#update-a-release);
> it is not the project's recommendation.

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

## Use the published preview

Do not install from the current `main` checkout. The current public
recommendation is the immutable
[`v2.0.1-preview.1`](https://github.com/yiheng8023/YIYUAN-Accord/tree/v2.0.1-preview.1).
Follow that tag's
[published README](https://github.com/yiheng8023/YIYUAN-Accord/blob/v2.0.1-preview.1/README.md)
for its exact installation, verification, update and removal paths.

The `v2.0.1-preview.2` packages in `main` are an unreleased historical
checkpoint. Their release route was retired before publication and they are not
a replacement recommendation, rolling tag or local-candidate installation
path.

For source review or contribution, use the current checkout only after reading
`product/reshaping-guidance.json` and
`docs/operations/CONTINUATION.md`. The repository is structurally valid but
intentionally not candidate-ready.

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

## Current development checkout

The current checkout is for review and reshaping, not ordinary installation.
Its Codex and Claude packages preserve the preview.2 checkpoint so their exact
distribution and host observations remain inspectable. They do not define the
future mechanism set.

An already installed and enabled preview.2 plugin may remain available as a
latent capability. Installation or visibility does not imply per-message
activation, effective behavior or product value. Do not reinstall it from
`main`, and do not treat disabling it as the only way to prevent interference;
a future behavior-bearing candidate must demonstrate applicability, isolation,
update or atomic replacement, health checking and rollback.

Contributors can run:

```powershell
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

These checks validate the current repository and historical package
conformance. They do not install a plugin, prove effective behavior, qualify the
reshaped product, authorize publication or establish production safety.

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
- **Historical preview.2 reference projections**: Codex and Claude packages
  whose exact behavior evidence remains bound to specific host surfaces and
  does not limit future mechanism choice
- **Representative Help-and-Interference Tasks**:
  [`evals/golden-tasks.json`](evals/golden-tasks.json)

The portable contract is **K1–K5**. Host rules **H1–H10** and learned-failure rules **L1–L7** keep host drift and trial history outside the core.

Those three authority files are the current reviewable bootstrap, not
unquestionable truth, a permanent file count or a ceiling defined by the
capabilities visible in today's hosts.

A later merge, split, replacement, or retirement must preserve provenance and
migrate the schema, verifier, mappings, and affected evidence explicitly.

---

## Current reshaping boundary

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

The current verifier proves only structural conformance of this active reshaping
state and the integrity of retained historical package evidence. It reports zero
current verified criteria and no release candidate. The immutable v2.0 and
v2.0.1-preview.1 releases remain historical public facts; preview.2 was not
published and must not be tagged.

The completed reshaping increment mapped one real outcome across plan,
context-tailored process, acceptance and a compact goal projection, then
replayed the smallest adaptive vertical slice. The next bounded step is to
turn that accepted active baseline into a separately replayed `v3.0.0` full
release candidate without inheriting preview.2 authority or package readiness.
See
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

The software is provided under Apache-2.0 on an “AS IS” basis, without warranties or conditions; see [`LICENSE`](LICENSE). This Public Preview does not establish production safety or fitness for a particular purpose.
