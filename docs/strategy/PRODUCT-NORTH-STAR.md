# Product North Star

## Purpose

Agent Autonomy Harness helps an Agent sense the collaboration state, select the
smallest sufficient capability path, manage its task lifecycle, release idle
resources, and continue work without forcing the user to learn every Agent,
Skill, MCP server, Plugin, Hook, repository, or context-management mechanism.

The user should primarily provide ideas, goals, corrections, creative judgment,
important decisions, and authorization where the host requires it.

The Harness must not reduce value to code volume, task throughput, saved time,
or money. It should also preserve intent fidelity, epistemic integrity, human
judgment and authorization, accountable evidence, reversibility, continuity,
resilience, and long-term system health as AI increases execution speed.

## Desired outcomes

- less user effort spent learning or manually orchestrating Agent mechanics;
- Agent-owned system judgment, self-observation, scheduling, and resource
  stewardship so the user is not required to inspect threads, workers, MCP
  sessions, or processes during ordinary collaboration;
- more reliable initiative without broad uncontrolled authority;
- task-scoped capability activation and resource release;
- context-aware handoff before collaboration quality degrades;
- durable shared domain language and decision continuity across lifecycle hops;
- evidence-based branch, worktree, verification, rollback, and cleanup choices;
- reusable cross-Agent contracts with honest host-specific adapters;
- task-bound discovery when the current native and loaded ecosystem is
  insufficient or stale, without turning discovery into automatic admission;
- native and external reuse before residual-gap implementation;
- AI-era revalidation of classical engineering principles without blanket
  revival of legacy process or blanket dismissal of pre-AI experience.

## AI-era engineering value

AI can lower the cost of producing code without lowering the cost of forming
intent, judging correctness, carrying responsibility, integrating change,
verifying outcomes, or maintaining a system over time. The Harness therefore
treats classical engineering principles as candidates for revalidation, not
automatic standards.

The research vocabulary distinguishes candidate invariants, adaptive practices,
obsolete ceremonies, and insufficient-evidence items. A principle can regain
importance while its historical workflow remains too rigid. Conversely, faster
generation does not justify weaker evidence, review, provenance, rollback,
authority, or maintenance boundaries. This is a horizontal evaluation lens;
it does not promote a hard standard, prescribe one universal process, or
reorder current candidate and residual-gap work.

## Product layers

1. **Portable decision core** — intent, capability routing, event-driven
   rerouting, context lifecycle, task topology, handoff, verification, closure.
2. **Runtime lifecycle plane** — desired-state reconciliation, ownership,
   leases, observed state, release, recovery, and cleanup evidence. Portable
   rules and Skills may request this behavior, but host adapters, gateways, or
   runtimes must actuate and observe it.
3. **Host adapters** — Codex, Claude Code, and future host-specific paths,
   Hooks, events, telemetry, thread APIs, and commands.
4. **Capability ecosystem** — task-bound source discovery, revision pinning,
   security,
   quality, superiority, overlap, redundancy, naming, permissions, and update
   review for Skills, MCPs, Plugins, Apps, Hooks, and future capability types.
5. **Consumer projections** — user configuration and operational distribution,
   including CC Switch where it is the suitable manager.

The capability universe is dynamic. A current inventory is only a dated
snapshot of what the host can see, not proof that the best suitable capability
is already installed or loaded. `capability-router` should first use healthy
current capability, then trigger targeted discovery when a bound task exposes
an evidenced gap, current options are materially weaker or stale, or ecosystem
drift is decision-relevant. Discovery does not itself authorize download,
installation, account connection, execution, persistent enablement, or
admission; those remain separately governed and verified.

The lifecycle chain also has distinct responsibilities: `AGENTS.md` supplies
portable constraints, Skills produce bounded semantic desired state, Hooks may
observe or bridge reliable host events, adapters or gateways actuate, and live
verification proves actual state and cleanup. Task completion, turn completion,
thread persistence, thread unloading, worktree cleanup, and process release
are separate states.

Resource pressure must be attributed at the same level of precision. A
colloquial "zombie thread" may mean accumulated context, an active or loaded
thread, a persisted but unloaded thread, an unfinished subagent or worker, an
MCP connection or subscription, a child process, or host cache/rendering state.
These are different lifecycle objects with different release mechanisms. A
persisted thread is not by itself a resource leak, while a completed task is
not proof that its workers, connections, processes, or context-related host
resources were reclaimed.

The target experience is a bounded autonomous closed loop: the Agent judges
the workload and desired state, observes what the host actually exposes,
schedules or releases resources within existing authority, verifies the
outcome, and keeps cleanup debt visible. The user should receive only the
smallest decision that genuinely changes permission, trust, cost, shared
ownership, or destructive scope. When the host cannot expose or actuate a
state, the Agent must report that limit and degrade to the smallest manual
step; it must not simulate observability or invent successful reclamation.

## Existing hard-standard invariant

Hard standards and Skills are deliberately not peers in an ablation ladder.
Hard standards are cross-cutting, mandatory constraints on every capability
path: native, official, reviewed external, composed, or self-authored. They
remain active at intake, before side effects, during verification, and at
closeout. They are never disabled to make a Skill look useful, and a Skill
cannot waive them.

Skills are upstream capability mechanisms. They may help an Agent satisfy the
standards more reliably or efficiently, but they remain selectable,
replaceable, composable, and removable. Skill ablation varies that capability
layer while keeping the same facts, truth thresholds, safety floor, authority
boundaries, and acceptance checks. This paragraph makes the existing design
explicit; it does not introduce a new product layer.

## Persistent semantic authority

Accepted domain language and consequential decision records form a
cross-cutting semantic authority plane. They are durable state consumed by
requirements, architecture, implementation, review, release, operations,
handoff, and closure; they are not a universal Skill and do not require a
grilling session for every clear task.

The portable contract does not require one literal filename. A project may use
`CONTEXT.md`, bounded-context glossaries, or an equivalent authoritative
carrier. Glossaries contain domain vocabulary rather than implementation
plans. Working notes, generated projections, and handoffs do not become
authority automatically. New canonical terms and hard-to-reverse decisions
require responsible-human acceptance, while downstream stages must surface
conflicts and supersession rather than silently normalize them. This semantic
plane complements, but never replaces, repository truth, evidence, tests,
authorization, or the mandatory hard-standard gates.

## Target Skill ownership

The long-term repository product body maintains only self-authored human-Agent
collaboration capabilities that survive residual-gap proof and ordinary
admission, together with their contracts, relations, tests, adapters, and
evidence. The admitted payload count may be zero. A mature admitted
self-authored Skill is installed and distributed through CC Switch rather than
through a repository-built manager.

Official, runtime/plugin-owned, and third-party domain Skills remain owned by
their upstreams and are consumed through the host or CC Switch. This repository
may retain source metadata, licenses, review outcomes, ablation evidence,
compatibility mappings, and migration records without becoming their long-term
payload mirror. Project-only Skills remain project-scoped.

The inherited third-party approved payloads are transition evidence and
comparison baselines. They may leave the active product body only after a
behaviorally equivalent CC/host route or an evidenced self-authored residual-
gap successor is mapped and verified. Behavioral equivalence requires the same
named scenario, fixed facts, and acceptance thresholds plus verified host
invocation, authority behavior, failure/fallback, recovery, and maintenance
boundaries. A same name, similar description, overlapping content, directory
presence, or catalog hit does not prove equivalence. This target is not current
deletion authority.

Repository-authored collaboration-control Skills must ultimately pass a weak-
Agent floor using the weakest suitable host model/reasoning combination that is
actually available and recordable. As of the current Codex calling-host
contract, the requested floor is `gpt-5.3-codex-spark` with `low` reasoning.
The same truth, safety, and authority thresholds apply at that floor. A more
capable model such as `gpt-5.6-terra`/`low` is a conditional attribution aid,
not a universal second run and not a substitute for the weak-Agent result.

## Non-goals

- maximizing installed capability count;
- replacing native permission dialogs;
- keeping every MCP or Plugin active;
- assuming one fixed context threshold works across all Agents;
- forcing every creative or exploratory task into rigid structure;
- claiming portability from one successful host test;
- rebuilding mature native, official, or maintained external solutions.
- maintaining a general third-party Skill mirror as the final product body;
- pre-authoring self-authored Skills before a repeatable residual gap exists.

## Current hypotheses

The following are research questions, not product claims:

- whether a host exposes safe mid-session MCP activation and release;
- whether task-scoped MCP leases can survive failure and restore prior state;
- whether dynamic capability discovery can reliably move from an evidenced
  current-capability gap through review and authorization to a verified,
  task-scoped route without catalog sprawl or silent trust expansion;
- which reviewed gateway, session, lease, durable-execution, and stale-resource
  primitives can be composed before any thin host-aware coordinator is
  justified;
- whether useful context pressure can be measured directly or inferred safely;
- whether a host can create a same-workspace continuation thread automatically;
- how consistently different Agents follow repository instruction carriers;
- which Git topology decisions can be automated without unacceptable false
  positives or destructive consequences.
