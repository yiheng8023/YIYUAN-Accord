# YIYUAN Accord

Turn a desired outcome into a verified, recoverable finish—without forcing the user to manage the Agent's tools, conversation handoffs, or internal mechanics.

YIYUAN Accord is an open, Agent-neutral collaboration system.

It helps an Agent stay aligned with the current goal, adapt when the work changes, and finish with a verified result, explicit unknowns, and controlled cleanup.

It can use different hosts and mechanisms. Specific tools are parts of a route, not the product by themselves.

The broader mission is better human-AI collaboration. The current product surface and evidence are deliberately limited to human-Agent collaboration.

[简体中文](README.zh-CN.md)

> **Published stable fallback:** [`v3.0.1`](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.0.1). **Release line (pending):** [`v3.1.0`](https://github.com/yiheng8023/YIYUAN-Accord/releases/tag/v3.1.0).
>
> Use v3.1.0 only after its link resolves to the matching immutable, non-prerelease GitHub Release; until then use v3.0.1. Repository text cannot self-attest publication.
>
> Never install from a moving `main` checkout.

| I want to... | Start here |
| --- | --- |
| Use Accord | [Start in 30 seconds](#start-in-30-seconds) |
| Understand or evaluate it | [What It Changes](#what-it-changes) and [Release status and evidence limits](#release-status-and-evidence-limits) |
| Develop or maintain it | [For developers and maintainers](#for-developers-and-maintainers) |

---

## What Accord is

Accord helps an Agent stay aligned with the user's current outcome, choose the smallest sufficient route, preserve human authority, and close with evidence rather than ceremony.

It is not a prompt template, universal runtime, control plane, capability catalog, or claim that every Agent and host will behave reliably.

Its portable core defines a few stable collaboration constraints. Task, host, evidence, authority, and lifecycle conditions determine the rest at run time.

Codex and Claude are current reference hosts. They are not the product boundary, permanent dependencies, or privileged model families.

A normal request is enough. Users do not need to learn Accord's internal vocabulary before asking for an outcome.

For example:

> Continue this project until it is ready to release. Preserve existing work, verify the actual result, and ask me only when a real decision or new authority is required.

---

## What It Changes

You describe the intended result in natural language.

Accord asks the Agent to own supported operational mechanics while reserving consequential judgment, new trust, cost commitments, public release, and irreversible effects for the human.

Its portable loop is driven by five stable constants:

1. **Outcome Anchor** — Start from the user's current goal and active corrections.
2. **Minimum Route** — Choose the smallest sufficient path that can genuinely deliver the result.
3. **Authority Preservation** — Stop only when progress requires new human judgment or authorization.
4. **Dependency Reconciliation** — When evidence changes, replay from the earliest affected dependency boundary.
5. **Honest Closure** — Verify effects, disclose unknowns, and clean up attributable transient residue.

Everything else is selected on demand from the actual task and host environment.

Accord does not require an Agent to imitate a person. Machine-native routes are welcome when they reduce burden and still preserve honest evidence.

If a healthy native capability already closes the responsibility, Accord should remain quiet.

---

## When It Is Useful

- **Goal drift** — A task produces plausible work while moving away from the requested outcome.
- **Interrupted work** — A long task is paused, corrected, or continued in another conversation carrier.
- **False green lights** — Tests, reports, commits, or hosted checks are mistaken for real delivery.
- **Decision boundaries** — Routine mechanics should continue, but new trust, cost, publication, or irreversible effects require a person.
- **Cascade corrections** — A changed requirement or failed assumption invalidates dependent work.
- **Complex closeout** — Installation, verification, cleanup, public state, and user-visible effects must remain distinct.

Accord is not a mandatory workflow for every task. A simple request with a healthy direct route should stay simple.

It does not replace domain expertise, grant authority to an Agent, guarantee automatic activation, or turn a formal release into proof of production safety.

---

## Start in 30 seconds

### Before installation

The immutable commands below target `v3.1.0`. Use them only after its matching public Release exists. While it is pending, use the same commands with the exact immutable ref changed to `v3.0.1`; do not use moving `main`.

The GUI labels in this README are **v3.0.1 historical routes**, not current-entry claims.

After later client updates, Codex, Claude, and ChatGPT GUI entry points are unknown until the actual host is inspected again without changing its settings.

Before a GUI installation or lifecycle action, record the client, version, visible route, and observed result. No separate ChatGPT GUI installation route was verified for v3.0.1.

The recorded Codex and Claude routes require plugin support, access to the public repository, permission to change user-level plugin state, and a fresh task or session.

Accord does not bind operation to a fixed model name, model version, or provider route. Model identity and version are run-time provenance, not product identity or route authority.

### Codex

Install the exact immutable tag:

```powershell
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref v3.1.0
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

When v3.0.1 was last verified, the next step was to restart the desktop client or open a new CLI session.

Open **Plugins** or run `/plugins`, then look for `YIYUAN Accord for Codex` and `deliver-demand-driven-outcome`.

Treat those labels and locations as historical observations until confirmed on the current client.

### Claude clients and Claude Code

When v3.0.1 was last verified, Claude Desktop Chat, Claude web chat, and Cowork used **Customize > Plugins**.

The recorded route added `https://github.com/yiheng8023/YIYUAN-Accord` as a personal marketplace, installed **YIYUAN Accord for Claude**, and opened a new chat.

Do not assume that route, wording, or location remains current after a client update.

For a persistent Claude Code installation:

```powershell
claude plugin marketplace add yiheng8023/YIYUAN-Accord@v3.1.0 --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
```

The repository root is the marketplace. The package subdirectory is not.

For one development session, run `claude --plugin-dir ./plugins/yiyuan-accord-claude` from the repository root.

Confirm `/yiyuan-accord-claude:deliver-demand-driven-outcome` in `/help`. Use `/reload-plugins` after checkout changes.

### What installation changes

The packages expose one progressively disclosed adaptive Skill, one short-lived stateless `SessionStart` Hook adapter, and the required host manifests. The repository separately contains a side-effect-free pure-core reference implementation; it is not installed or invoked by either plugin package.

They add no persistent Runtime, MCP server, App, state store, browser bridge, SDK client, background process, or automatic project mutation.

They do not replace project or user `AGENTS.md`, `CLAUDE.md`, `config.toml`, or settings files.

The Hook adapter does not read private conversation transcripts, write durable state, or start a background process.

`startup` and `clear` remain silent. Supported `compact` and `resume` events provide only non-authoritative continuity hints.

Those hints require the current permitted state to be inspected again before they can support a decision.

Installation, enablement, and visibility do not imply activation. Activation does not by itself prove Agent use, execution, outcome, independent evidence, or value.

The direct App Server client remains an evaluator route, not an additional installed product service or second API.

---

## Confirm it works

Treat confirmation as four separate questions:

1. **Installed** — Does the host report the expected package and exact source?
2. **Visible** — Does the expected Skill or plugin appear in the current host?
3. **Activated** — Did the relevant host event or task actually invoke it?
4. **Effective** — Did it contribute to the requested result without unacceptable interference or residue?

For Codex, inspect `codex plugin list --json`, then confirm the current plugin and Skill list in a fresh task.

For Claude Code, inspect `claude plugin list --json`, then confirm the current command list through `/help` in a fresh session.

For GUI clients, inspect the current interface instead of relying on screenshots or labels from another version.

A deterministic exposure check may select the Skill explicitly. Ordinary work should not require explicit invocation.

A relevant host may select the Skill implicitly, while a sufficient native route should remain quiet.

Presence checks are not field-value tests. Record the requested outcome, starting state, Agent and human actions, observed effect, residue, and remaining unknowns separately.

---

## How It Works

The compact collaboration loop is:

`Outcome → Minimum route → Authority boundary → Dependency reconciliation → Verification and cleanup`

The outcome stays bound to the user's latest correction. The route may change when host facts, evidence, permissions, costs, failures, or lifecycle state change.

A correction reopens only the earliest affected dependency and its downstream work. It does not require restarting unrelated proof.

Closure requires concrete effects where the action was meant to matter. A plan, test, report, receipt, commit, or hosted green check supports the result but is not automatically the result.

### Adaptive responsibility allocation

Accord is not limited to Codex, Claude, or any other concrete Agent.

Each responsibility may be Accord-contained, Agent-native, or Accord-Agent-composed. One route may mix all three modes.

A plugin name, mechanism family, or whole-task label cannot replace responsibility-level allocation.

Skill, plugin, App, MCP, Hook, configuration, state, runtime, cloud carrier, and future mechanisms are neither mandatory nor permanently forbidden.

A mechanism is admitted only when it closes a current responsibility with acceptable authority, evidence, interference, cost, recovery, and retirement behavior.

Research follows the same rule.

Fresh and sufficient evidence adds no research step. A material unknown may justify bounded use of official documentation, source repositories, papers, host-native facts, or public leads.

A public lead may open an investigation or supply a counterexample. It cannot alone support a consequential conclusion.

The portable core adds no mandatory research API, account connection, persistent service, provider binding, or default network search.

### State and evidence

Accord prefers supported, current, structured host state over inference.

It normalizes only the fields needed by the present outcome. It does not recreate a second authoritative database of every host capability.

Conflicts, stale values, missing bindings, and unexposed facts remain unknown.

Shared state, observation, or context injection is not evidence that an Agent used the information or produced the intended effect.

### Continuity and topology

A conversation, task, session, Git branch, worktree, repository fork, and local or cloud execution placement are different relations.

Moving to another conversation does not silently move code or Git state.

A sequential handoff verifies the destination before releasing the source. A copied-history fork is reserved for a genuine causal branch, not routine continuation.

### Stage planning

For a complex project, baselines, plans, processes, acceptance criteria, and goal projections are versioned stage views rather than timeless truth.

A closed stage becomes a referenceable snapshot that binds its project views, evidence, finite claims, unknowns, and invalidation triggers.

Future planning is derived on demand from the project panorama, the latest accepted snapshot, and fresh environment facts.

It may cover maintenance, iteration, updates, bounded refactoring, host adaptation, retirement, replacement, and later development without becoming an automatic roadmap.

The project calls this wider loop **complete, bounded self-bootstrapping**.

It means sensing current conditions, reusing or establishing a minimum authorized route, verifying consequences, and governing correction or retirement within explicit evidence and authority limits.

Viewed through a host-leveraged lens, that loop has eight responsibility families: self-knowledge, self-coherence, bounded autonomy, on-demand learning, correction, recovery, external verifiability, and governed evolution.

They are not eight built-in modules or claims that Accord works independently. Accord drives the upstream AI Agent, host-native capabilities, and ecosystem.

It adds only the smallest replaceable gap after sufficient reusable routes fail on evidence.

Each material duty is Accord-contained, Agent-native, or composed between them. “Self-proof” means preparing source-bound evidence for independent checking, never letting the project certify its own correctness, value, or publication.

The v3.1.0 public claim ceiling remains the five finite statements below. Long-term autonomous learning, universal recovery, and compounding self-evolution are not claimed.

### Resource stewardship

Accord treats resources as dynamic route variables.

It attributes ownership and state, uses the minimum sufficient concurrency and budget, and releases only task-owned resources.

Shared resources and resources of unknown ownership are preserved.

Native limits, interruption, cleanup, and reclamation are reused when they are healthy and sufficient.

A cleanup command is not proof of cleanup. Closure verifies the resulting state and reports residue that cannot be safely removed.

Accord does not silently collect or upload telemetry.

See [`docs/architecture.md`](docs/architecture.md) for the complete portable interface, host admission, evidence, resource, complexity, and evolution model.

---

## Release status and evidence limits

The matching immutable GitHub tag and Release determine whether `v3.1.0` is publicly released.

Repository text, tests, a local tag, or a candidate record cannot self-attest that external fact.

A full project release is a finite statement about the exact repository, packages, declared claims, and completed release gates.

It does not establish universal behavior, production safety, fitness for every purpose, or compatibility with every Agent, operating system, and client interface.

The exact public claim ceiling contains five finite statements:

- context-adaptive collaboration-closure conformance for v3.1.0;
- static package conformance for the current Codex and Claude projections;
- one bounded single-arm collaboration-closure dogfood result;
- replayed local regression results for continuity, repair, and resource stewardship; and
- reproducibility from a clean v3.1.0 checkout.

Separate repository evidence includes a side-effect-free reference core and the bounded host scenarios below. It does not expand those five public claims.

Bounded host evidence covers one event-to-consequence path, one silent sufficient route, one verified fresh handoff, and one disposable non-empty Windows Codex-and-Claude lifecycle.

The observed `bypass_hook_trust` / `bypassPermissions` path was a test control, not a production trust route.

It also preserves failed, partial, and superseded attempts as counterevidence rather than rewriting them as success.

The historical Claude GT-07 cleanup failure is excluded from retained behavior claims.

Current unknowns include production trust, live Claude Hook activation outside the disposable session-only test, updated-client GUI compatibility, and unmanaged or cross-OS behavior.

Broad cross-host behavior, population-level value, and behavior outside the evaluated conditions also remain unknown.

Installation evidence does not transfer automatically to activation or effect.

Historical behavior evidence does not transfer automatically to changed bytes, packages, Skills, Hooks, or host projections.

Detailed SHA, Golden Task, review, failure, and experiment history belongs in [`docs/releases/v3.1.0.md`](docs/releases/v3.1.0.md).

Architecture and evidence semantics belong in [`docs/architecture.md`](docs/architecture.md).

The current repository state, next gate, and continuation procedure belong in [`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md).

The exact finite acceptance contract is in [`product/acceptance.json`](product/acceptance.json).

---

## Update, rollback, removal, and source verification

The GUI lifecycle labels below remain historical observations. Inspect the current client before depending on any menu, label, or action.

Confirm lifecycle state through the same entry point that performed installation.

When v3.0.1 was last verified, useful state views included `codex plugin list --json`, `claude plugin list --json`, and **Customize > Plugins**.

A difference between those views is observed host state, not automatic proof that another installation failed.

An immutable ref never advances automatically.

To update or roll back Codex, remove the installed package and marketplace, then install the intended exact tag:

```powershell
codex plugin remove yiyuan-accord-codex@yiyuan-accord
codex plugin marketplace remove yiyuan-accord
codex plugin marketplace add yiheng8023/YIYUAN-Accord --ref VERSION_TAG
codex plugin add yiyuan-accord-codex@yiyuan-accord
```

Before changing Claude Code, confirm through the list commands that this user-scope registration belongs to the route above. If same-named state across scopes cannot be distinguished safely, stop and report that adapter gap.

To update or roll back Claude Code, remove its current user-scope package and marketplace, then register and install the intended exact tag:

```powershell
claude plugin uninstall yiyuan-accord-claude@yiyuan-accord --scope user
claude plugin marketplace remove yiyuan-accord --scope user
claude plugin marketplace add yiheng8023/YIYUAN-Accord@VERSION_TAG --scope user
claude plugin install yiyuan-accord-claude@yiyuan-accord --scope user
```

To remove only the Claude Code projection installed by this user-scope route, stop after the first two commands and verify that both registrations are absent from that scope.

Use the corresponding current **Customize > Plugins** operation only after confirming that the GUI route still exists.

Prefer supported native reload and lifecycle operations.

These exact-ref commands perform an explicit replacement, not an atomic in-place update. Record the previous exact tag first; if target installation fails, reinstall that tag, verify health, and report the inactive interval.

Never move an existing tag. Do not edit global host configuration as a substitute for supported lifecycle commands.

Removal must preserve existing user configuration, concurrent user changes, shared state, and foreign plugins.

A host-owned inert cache is not active Accord state, but it is also not physical zero residue.

Do not bypass the host lifecycle to delete a cache covered by its bounded cleanup contract.

### Source verification

Verify an exact source checkout with a Python interpreter that provides the required standard-library features:

```powershell
python -B -m yiyuan_accord verify --root . --json
python -B -m yiyuan_accord host-check --adapter codex --root . --json
python -B -m yiyuan_accord host-check --adapter claude-code --root . --json
```

The current Release CI exercises CPython 3.10–3.14.

That matrix is current compatibility evidence, not a permanent version whitelist or part of Accord's identity.

These checks verify deterministic repository and package conformance.

They do not install a plugin, prove activation, establish field value, grant release authority, prove publication, or establish production safety.

---

## For developers and maintainers

The current schema-v3 authority set is:

- [`product/constitution.json`](product/constitution.json)
- [`product/program.json`](product/program.json)
- [`product/acceptance.json`](product/acceptance.json)

Accepted, revisable reshaping and dynamic-index guidance is in [`product/reshaping-guidance.json`](product/reshaping-guidance.json).

[`CONTEXT.md`](CONTEXT.md) is a derived glossary. It explains terms without adding semantic authority.

The generic verifier is [`yiyuan_accord/control.py`](yiyuan_accord/control.py).

Representative help-and-interference tasks are in [`evals/golden-tasks.json`](evals/golden-tasks.json).

Codex and Claude packages share the `deliver-demand-driven-outcome` Skill name while retaining host-specific manifests.

Detailed release evidence is in [`docs/releases/v3.1.0.md`](docs/releases/v3.1.0.md).

Architecture and trust boundaries are in [`docs/architecture.md`](docs/architecture.md).

Live continuation and gate ordering are in [`docs/operations/CONTINUATION.md`](docs/operations/CONTINUATION.md).

Maintenance and contribution rules are in [`CONTRIBUTING.md`](CONTRIBUTING.md). Security reporting is in [`SECURITY.md`](SECURITY.md).

A release progresses through exact local verification, independent review, same-revision push, hosted checks, named-human authority, immutable tag and Release, public verification, and cleanup.

Those stages remain distinct. Passing one does not manufacture evidence for another.

Report problems through [GitHub Issues](https://github.com/yiheng8023/YIYUAN-Accord/issues).

Include the exact tag and revision, host and version, installation route, requested outcome, starting state, observed result, human intervention, material effects, residue, and unknowns.

Never submit credentials, private session content, or unsanitized host transcripts.

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

| WeChat Pay (CNY) | Alipay (CNY) |
| --- | --- |
| ![WeChat Pay QR code](docs/assets/sponsoring/wechat-pay.png) | ![Alipay QR code](docs/assets/sponsoring/alipay.png) |

Verify the recipient before paying. See [`SPONSORING.md`](SPONSORING.md) for the complete terms.

### Disclaimer and compliance

YIYUAN Accord is an independent community open-source project.

It is not an OpenAI, Anthropic, Codex, Claude, Claude Code, or GitHub product. Those parties do not sponsor or endorse it.

Third-party names and marks belong to their respective owners.

Users remain responsible for reviewing Agent outputs and complying with applicable laws, contracts, host terms, licenses, and organizational policies.

The software is provided under Apache-2.0 on an “AS IS” basis, without warranties or conditions. See [`LICENSE`](LICENSE).

A full project release does not establish production safety or fitness for a particular purpose.
