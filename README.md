# Agent Autonomy Harness

English | [简体中文](README.zh-CN.md)

> Describe the outcome. Let the Agent work out which capabilities it needs.

Agent Autonomy Harness is an open research project for reducing the amount of
Agent and tool knowledge a person must carry into a task.

The intended experience is simple: the user states a goal, supplies facts and
judgment, and grants bounded authority. The Agent chooses a sufficient route
and task carrier, uses them safely, reconciles any split work, verifies the
result, and cleans up afterward.

**Current status:** v1.2 is ready with no active causal increment. The bounded
pre-response enrollment repair that followed the v1.1 stop is retained in Git
and in an inactive source candidate, without inheriting that cohort or installing
a runtime. The repository verifier reports `programStatus=ready`,
`completionState=in-progress`, O1-O5 `0/5`, and G1-G4
`4/4`; run it for live truth. The tree contains a code-pinned, pre-freeze v1.2
profile and paired protocol candidate that make pre-response enrollment,
dynamic environment and context adaptation, and Agent-owned process-drift
correction reviewable without creating a monitor or runtime. The current
profile binding is still unfrozen, so this is not evidence that self-correction
or any other outcome works in real tasks, and no
cohort, private source, result validator, terminal authorization validator,
installed plugin, or outcome is active. The inactive Codex candidate now uses
`UserPromptSubmit` only to create a keyed pre-model source commitment and
bounded mandatory-resolution context; it does not claim to withhold all
user-visible output or intercept hosted tools. Installation, Hook trust,
private-key materialization, profile freeze, and cohort activation remain
separate human gates.
The constitution's terminal product proposition has not been established.

v1.1 remains an immutable stopped zero-outcome attempt at revision `5ae71bb`.
A source-bound private-window audit established that its first post-activation
real product-delivery demand received outcome-bearing assistance before
immutable task registration. Its only generation is revoked, and the exact
protected resource and one-time expiry trigger were deleted under the authorized
deterministic-failure disposition. It cannot be repaired, resumed, or inherited.
v1.0 is
an immutable stopped zero-outcome attempt at revision `910ac01`; none of its
profile binding, cohort state, authorization, or results can be inherited.
v0.2 remains an
immutable accepted bounded-calibration milestone at revision
`0dbcb0af34197e5c35c75d69a1aeacf4fd91b404`; its `5/5` result cannot be inherited
as proof of sustained real-task autonomy, proactive carrier management, live
installed value, publication, production, or the constitution's terminal
product proposition.

The current tree does not materialize the 41 raw v0.2-era evidence JSON files
that contained machine-local and host-session metadata. The fixed v0.2 revision
and bounded aggregate claims remain; public Git history and historical author
email remain retrievable under the explicit no-history-rewrite privacy
disposition, so this is forward current-tree sanitization rather than erasure.

A historical [v1.0 profile candidate](docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md)
and [prospective cohort protocol candidate](docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json)
co-locate the pre-measurement method, mandatory floors, baseline, carrier,
cross-host, privacy/residue, and release semantics. Their exact frozen bytes
remain v1.0 historical inputs; the separately frozen and now revoked v1.1 binding does not
reuse them. Both zero-task v1.0 cohort generations are now revoked and
carry no outcome evidence. The one permitted successor freeze at revision
`8e8e76b` and canonical binding digest `d2cf0cd` received independent exact
authorization, but a later validator-ordering failure deleted its protected
evidence and expiry task under the authorized deterministic-failure cleanup
rule. The generation cannot be reconstructed or restarted honestly.

The historical v0.2 O1 is supported by accepted public-intake, Codex Skill-source, and Claude
Skill-source results. O2 uses the materially distinct public-intake, Codex
Skill-source, and continuation-reconciliation scenarios without double-counting
the similar host package deliveries. O3 binds the three observed route decisions
across native retention and finite source-bound discovery or adaptation. O4
accepts the unchanged candidate.5 methodology and minimum profile only for the
registered Codex 0.147.0 Windows cohort, including its honestly stopped case.

Historical v0.2 O5 adds one pre-registered matched natural task on Codex CLI
0.147.0/gpt-5.6-sol and distinct-host Claude Code 2.1.233 routed to
DeepSeek-V4-Pro through the official Anthropic-format endpoint. Both hosts
independently returned the same useful `blocked` decision: the target Claude
adapter source identifies 2.1.232 while the measured carrier is 2.1.233. The
named human accepted both outcomes, their normalized single-P1 equivalence, and
only the registered task/target/host/model/adapter/date claim. The reported
`deepseek-v4-pro[1m]` spelling was the case-normalized form of the requested
`deepseek-v4-pro[1M]`; no fallback was observed. One out-of-source Claude Glob
was denied without data exposure. All temporary plugin, Hook, credential-link,
process, and filesystem state was removed without user cleanup.

The historical Codex and Claude candidate.7 revisions remain inactive thin
Skill-plus-Hook projections over the same candidate.5 method. Their exact Git
revisions remain the evidence boundary; no measured value transfers to later
source. The current Codex tree is instead an inactive v1.2 projection candidate:
one package-owned Hook records bounded native lifecycle counters, while a
separate `UserPromptSubmit` Hook reads the submitted prompt only in memory and
stores or emits keyed commitments rather than raw prompt or session identity.
Derived capture state is removed at `SessionEnd`; the separately authorized
cohort key is not materialized by the source candidate. Neither Hook executes
task-repository code, and their checked-in commands fail closed until an
absolute trusted interpreter is materialized. The capture Hook is an evidence
and attention seam, not proof of registration or universal output/tool blocking.
Measured activation requires a future independently authorized cohort and new
environment-attributed profile binding. It is not installed or enabled. The
current Claude candidate.7 lineage now also has bounded input and a fail-closed
unmaterialized interpreter command, but still loads only exact-hash reviewed
repository runtime bytes and is not a live v1 carrier implementation. Neither
adds an MCP server, App, provider manager, or product authority; only the Codex
candidate has the bounded keyed pre-model capture described above. CC Switch 3.19.2 supplied replaceable static
DeepSeek settings for the measured distinct host; its proxy runtime was off and
it is neither portable-core nor runtime dependency. O5 proves decision
portability only within the registered pair. It does not prove that the 2.1.232-
pinned adapter supports Claude Code 2.1.233, matching model vendors, Anthropic-
model behavior, long-context parity, installed value, release publication,
production, model superiority, or all-Agent portability. The verifier is the
current machine-readable state source.

## The problem

Agent platforms keep gaining native features, tools, Skills, Plugins, Apps,
MCP servers, and other extensions. That growth is useful.

Users are still often expected to know what exists, choose the right route,
configure it, recover failures, verify completion, and remove residue.

The Harness asks whether that burden can move upstream to the Agent without
moving away the decisions that should remain human.

## The target experience

Imagine a user says:

> Audit this repository and make it ready for a public release. Do not publish
> anything until I approve it.

The target behavior is that the Agent:

1. understands the desired result and the publication boundary;
2. checks whether its healthy, authorized native capabilities are sufficient,
   including native adaptive model, provider, reasoning-effort, and delegation
   selection;
3. preserves a sufficient native route, and discovers, installs, configures,
   switches, escalates, de-escalates, disables, rolls back, retires, or persists
   another route only as current need, evidence, and authority justify;
4. stays in the current task and checkout by default, creating a branch,
   worktree, repository fork, conversation fork, or new task only when
   isolation, parallelism, host capacity, or an authority boundary requires it;
5. observes whether the current conversation remains a safe carrier and owns
   native compaction or verified handoff before preventable context loss;
6. owns synchronization, code merge or conclusion reconciliation, archive or
   release, and cleanup for any such carrier;
7. asks the user only for missing facts, consequential judgment, new authority,
   or a technically reserved host action; in the last case it gives the smallest
   exact step and verifies it afterward, never asking for tool discovery or
   invocation design;
8. executes, recovers, verifies, releases task-scoped capability exposure, and
   removes task-created residue;
9. returns the result and its evidence for accountable human judgment.

This is the product target, not a claim about current runtime behavior.

A known collaboration shortfall is not solved because a report names it or a
control is implemented. For a material task risk, the Harness first reuses a
sufficient native, official, maintained external, or accountable domain
control. It adds only the smallest evidenced residual mechanism and requires
task-relevant prevention, detection, recovery, degradation, escalation, or
claim limitation. If the risk remains unresolved or unobservable, the claim
narrows or the route stops. The Harness does not run a fifty-item checklist on
every task or build a model router where the host already adapts sufficiently.

## What belongs to the Harness

| The Harness owns | The Harness reuses | The Harness does not become |
| --- | --- | --- |
| Portable demand-to-outcome collaboration semantics | Healthy Agent-native behavior | A universal Agent runtime |
| An open minimum quality and evidence-conformance contract | Tool and Agent protocols such as MCP, A2A, or CHAP when suitable | A fixed capability catalog or marketplace |
| Measures for user burden, outcome quality, authority, evidence, recovery, context-carrier fitness and transition, code and conversation task-topology lifecycle, resource lifecycle, model/provider/reasoning route fitness, and cleanup | Existing discovery, identity, authorization, native model/reasoning/delegation routing, audit, provenance, Git, and host task primitives | A new wire protocol, model router, context monitor, Git or task manager, identity system, or audit format without a proven residual gap |
| Adaptive thin reference projections that test the same semantics on real hosts | Maintained external implementations with source, version, license or terms, maturity, and boundary recorded | A replacement for human goals, domain judgment, consent, or final accountability |

Codex is the first reference host because it is a strong, practical test bed.
Codex-specific configuration remains outside the portable product core. A
distinct second host is required before any cross-host claim can pass. Terminal
O5 also requires the live pair set to span at least two operating-system
families and at least one pair to cross that boundary. Every claim names only
the tested host, OS/version, runtime, and virtualization or compatibility
relationship; WSL2 may supply bounded Linux evidence hosted by Windows, but it
is not bare-metal Linux or macOS proof. CLI, API, Skill, plugin, MCP, Hook,
adapter, package, service, and later carriers remain non-exhaustive adaptive
delivery shapes rather than the product definition.

## What exists today

The current repository provides:

- a machine-readable [constitution](product/constitution.json) for purpose and
  fixed boundaries;
- a [program](product/program.json) for the current causal work state;
- explicit terminal [v1.2 acceptance criteria](product/acceptance.json), with
  observed-native-minimum and user-configured environment strata and all
  outcomes still planned;
- the exact [candidate.5 methodology and minimum quality profile](docs/DEMAND-TO-CAPABILITY-PROFILE.md),
  accepted only for the bounded O4 Codex reference-host calibration; its source
  bytes retain the pre-calibration status header frozen by registration;
- a distinct historical frozen [v1.0 method/profile candidate](docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md)
  and [prospective cohort protocol candidate](docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json),
  retained as stopped subordinate inputs but carrying no task or outcome evidence;
- a separate code-pinned [v1.1 method/profile candidate](docs/DEMAND-TO-CAPABILITY-PROFILE-V1.1.md)
  and [paired cohort protocol candidate](docs/PROSPECTIVE-COHORT-PROTOCOL-V1.1.json)
  that preserve the stopped v1.1 adaptive environment and human-intervention contract;
  their exact bytes are a revoked historical normative binding and
  they still carry no task, result, installation, or authority of their own;
- a distinct current, code-pinned, still-unfrozen
  [v1.2 collaboration profile candidate](docs/DEMAND-TO-CAPABILITY-PROFILE-V1.2.md)
  and [pre-response cohort protocol candidate](docs/PROSPECTIVE-COHORT-PROTOCOL-V1.2.json)
  that realize dynamic native-first routing, context-variable adaptation,
  continuous Agent-owned drift correction, cross-OS claim limits, and current
  terminal privacy semantics without adding acceptance thresholds or outcome
  credit;
- a standard-library-only verifier that rejects invalid authority, evidence,
  work graphs, and repository residue, and derives a privacy-safe
  `sourceCarrierRelease` preflight so an Agent does not archive a conversation
  that still carries live cohort source evidence;
- a legacy inactive, standard-library-only `SessionStart` repository seam that
  projects bounded code-owned authority and verifier state after startup,
  resume, clear, or compaction without reading prompt, transcript, or session
  content or storing session state; active-work identity is hashed, raw
  diagnostics are excluded, and repository state remains explicitly unknown
  until the Agent observes it through a trusted native execution boundary;
- an inactive Codex plugin source candidate with one task-facing Skill, one
  package-contained Hook for bounded native compaction/clear state and
  conservative carrier decisions, and one keyed pre-response enrollment-capture
  Hook with explicit enforcement claim ceilings; it works
  outside a Harness-shaped repository, never executes task-repository code or
  Git, and remains deliberately unmaterialized until a trusted absolute runtime
  is bound; it is not eligible for measured activation until a new v1.2 profile,
  cohort protocol, private source and exact Hook trust are independently bound;
- a workspace-scoped Codex marketplace entry that exposes only that projection
  as `AVAILABLE`; discovery does not install, enable, or trust it;
- one content-addressed stopped Codex continuity result showing that an exact
  temporary install delivered the Skill and both startup and compact
  projections, while preserving the missing native Hook-event evidence as a
  failed mandatory floor and restoring all consumer state afterward;
- an inactive Claude Code Skill-plus-Hook projection that reuses the same
  candidate method, translates native `SessionStart` input and plain-stdout
  context output into repository-owned continuation semantics, and can be
  exposed for one session without persistent installation;
- product tests for the public verification seam;
- a fixed-source external-landscape review that narrows what the project may
  build instead of duplicating existing layers.

It does not provide a task runtime, persistent capability installation, or an
accepted v1.2 live-routing result today. The revoked v1.1 binding carries zero
outcome evidence and is not terminal acceptance.
Candidate.5 has only the frozen,
bounded v0.2 Codex calibration acceptance described above; it is not the final
v1.2 profile or a general standard. The adapters are not installed in user
configuration. Passing repository checks and historical receipts do not prove
the terminal product result.

## Verify the repository

Prerequisites: Git and Python 3.10 or newer. No package installation, account,
or external service is required.

```powershell
git clone https://github.com/yiheng8023/agent-autonomy-harness.git
cd agent-autonomy-harness
python -B -m harness verify --root . --json
python -B -m unittest discover -s tests/product -v
```

The JSON report is the current state surface. See the
[continuation guide](docs/operations/CONTINUATION.md) for the work boundary.

Before any v1.2 outcome measurement, every O1-O5 registration must bind the
acceptance-owned environment attribution contract. The two declared strata are
`observed-native-minimum` and `user-configured`; each natural task-host unit runs
once in one pre-registered arm, and Harness-specific value estimates compare
only pre-registered matched tasks within the same stratum, starting task-relevant
environment manifest, and authority-and-available-source envelope. The exact
Harness package and activation is the only planned initial route/configuration
difference; later Agent-selected or human-authorized capability and configuration
changes are attributed treatment-mediated lifecycle deltas. Unavoidable task
differences stay explicit, so this is bounded matched observational evidence
rather than a single-variable causal experiment. “Minimum” does
not mean an unknowable pristine host: discoverable user-global instructions,
configuration, Skills, plugins, Apps, MCP, Hooks, rules, memory, and provider
overrides are excluded, while system, developer, built-in, account, managed,
administrator, and unobservable state remains explicitly retained or unknown.
It is a starting condition, not a static capability ceiling: after demand reveals
a gap, the Agent may adapt under the registered authority and lifecycle rules.
At each decision it resolves the current suitable official or maintained source
from bounded as-of evidence and binds the exact execution version, commit, or
package identity. It neither locks one historical version across tasks nor runs
an unresolved moving target such as `latest`; material in-run drift requires
re-registration or an honest stop. The Agent performs every supported authorized
mechanic. Online AI is the normal route, but privacy, availability, latency,
cost, edge execution, or provider failure may make a bounded local/offline route
the minimum sufficient choice; degradation, recovery, reconciliation, and
cleanup retain the same floors and remain attributed lifecycle deltas. A
technically or authoritatively unavoidable human-only action is
minimal, precisely guided, post-verified, and counted in burden separately from
a prohibited transfer of Agent-owned work.
A without-Harness baseline cannot run inside the Harness repository and inherit
its project guidance. Historical items are classified as environment-independent,
environment-bound, or invalidated; none inherit outcome credit.

The repository now also carries a distinct code-pinned v1.2 pre-freeze profile
and paired prospective cohort protocol. They are subordinate review candidates,
not an active binding: no v1.2 artifact revision, cohort activation, private
source, task registration, or outcome has been authorized or inherited. Their
continuous-correction semantics require the Agent to reconcile the bound goal,
later corrections, authority, causal and expected state, evidence, carrier
fitness, and resource disposition at material checkpoints; material process
drift stops further effects and triggers recovery, the smallest authorized
correction, and re-verification. Whether that behavior is sustained remains an
O1-O5 real-task question, not a document or test claim.

The repository retains one code-pinned v1.1 profile and paired prospective
cohort protocol as a revoked historical normative binding. The first-freeze
revision `5ce2773`, canonical binding digest, exact source-native enrollment
surface, activation cursor, cohort key identity/fingerprint, protected-source
window, retention disposition, and one-time S4U expiry trigger were independently
authorized and code-validated. The v1.0 profile, protocol, authorization,
cohort, registration and ordering state were not reused.

The frozen v1.1 protocol correctly required first-eligible enrollment and an
immutable registration after natural demand but before outcome-bearing work.
The execution path incorrectly treated real Harness product delivery as mere
Harness discussion. The first post-activation product demand therefore received
an outcome before registration, and the complete source window falsified the
prospective cohort. No task was retrospectively registered, no later task was
selected, and no O1-O5 credit exists. The binding is revoked, its exact private
resource and trigger are absent, and v1.1 cannot open a successor or resume.
Commit dates, self-reported timestamps, tests, and Git history cannot repair
that chronology failure.

The program froze candidate.5 and its cohort protocol at artifact revision
`502c4ff`, first-freeze revision `d19d2fb`, and canonical binding digest
`ee4ba7a`; the exact named-human authorization was independently verified from
the bound Codex source. On 2026-08-16, however, a transient source-unavailable
result was incorrectly classified as definitive validation failure. The
validator consequently deleted and absence-checked the exact protected
resource, revoking current live source verifiability. The verifier now
separates transient unavailability or concurrent change, which must
fail closed without destruction, from confirmed binding or content failure,
which retains exact deletion and absence checking. No eligible natural task
had been registered, so no O1-O5 result evidence was lost and O1-O5 remain
0/5. The revoked generation cannot resume. A fresh successor binding used new
public surface, cursor and key identities and received exact authorization and
code pinning at revision `8e8e76b`. During later lifecycle-validator hardening,
the Agent validated the old Scheduled Task definition before replacing it; the
new rule correctly rejected its battery-blocked settings and therefore invoked
the already-authorized deterministic-failure cleanup. The protected successor
resource and exact task were deleted, so v1.0 is stopped rather than silently
restarted. The candidate file's internal `pre-freeze candidate` label is
part of the frozen bytes; `product/program.json`, not that historical label,
is the current binding state. Hosted runners corroborate the remaining
contract only and cannot restore or prove a revoked local authorization.

The historical v1.0 contract required two-stage terminal publication: an immutable candidate tree would
predeclare a semantic-version tag, public remote and O5 evidence-set digest;
after named-human authorization, the Agent would create the annotated tag and
verify the identical public object and peeled commit. The stopped v1.0 cohort
never reached that gate, so it cannot now progress to `accepted`. Any future
release must bind its own terminal route through the next current authority.
The tag's human name and timestamp are never sufficient by themselves: a
code-owned validator must independently verify the bound authorization source.
The clean candidate prebinds that validator's kind, version, repository
locator, prior revision and digest plus the public-source policy before any tag
exists. The public tag carries only a random public authorization identity and
a keyed commitment; private source locators and raw event identities remain
inside the validator's protected source boundary.
The current annotation format also fixes the accepted scope to cross-host and
cross-OS equivalence, portable collaboration semantics, the minimum quality and
evidence-conformance contract, adaptive thin projections, privacy, the exact
tested host/OS/runtime/virtualization scope, bounded claims, candidate, tag, and
public release; the predecessor profile/adapter-only scope cannot pass.
At the v1.0 revision, the terminal-release validator entry remained absent and
the registry contained only the bounded initial-freeze and successor-freeze
source validators described above. The current v1.2 human-authorization and
outcome-validator registries are empty; the v1.1 source-authorization validator
and its execution-specific anchors are available only from the pinned stopped
revision. No historical validator can promote current state.
The v1.0 credential and Scheduled Task cleanup entrypoint is not executable from
the v1.1 module; its historical behavior remains recoverable only from the pinned
`910ac01` revision. The separate v1.1-only expiry command remains structurally
bound to the retired exact identity, but the protected resource and one-time
S4U task are now absent.

## What v1.2 requires

- **O1 — sustained autonomous delivery:** a finite six-or-more natural-task
  cohort covers the required scenario bands and both environment strata with
  accepted outcomes, zero prohibited transfer of Agent-owned capability,
  topology, or context work, and zero material collaboration loss. Any
  unavoidable human-only step is minimal, guided, verified, and recorded.
- **O2 — comparative burden reduction:** the same cohort strictly lowers total
  and median material orchestration burden against eligible pre-registered,
  source-bound ad-hoc baselines with the same starting environment and authority
  envelope. Exact Harness activation is the only planned initial difference;
  later lifecycle deltas and unavoidable task differences remain matching
  variables. All human actions count in burden, legitimate human-only actions
  stay separate from prohibited Agent-work transfers, and no quality, authority,
  evidence, or residue loss can compensate.
- **O3 — real capability lifecycle:** natural tasks cover healthy-route retain,
  current-source resolution, residual-gap discovery, governed installation or
  configuration, enable/use, disproportionate-route rejection or downgrade,
  disable/rollback/retirement, and release or separately accepted persistence.
- **O4 — proactive carrier lifecycle:** real work proves keep-current,
  compact-and-reconcile, and verified same-goal conversation transition before
  preventable loss; every necessary code split is reconciled and cleaned.
- **O5 — live portable open delivery:** two matched live Codex/distinct-host
  pairs jointly cover observed-native-minimum and user-configured, include a
  useful completion and an honest stop or recovery, span at least two
  operating-system families with at least one cross-OS pair, bind exact OS and
  virtualization identities, reproduce public contract checks and task-scoped
  activation/rollback/cleanup from a clean checkout on every claimed OS family,
  keep live private-source terminal verification on its authorized evidence-
  holder surface, and pass the pre-closeout cross-dimensional counterexample
  audit with zero unresolved P0/P1 findings and zero temporary process artifacts,
  and end with human acceptance of the versioned conformance contract,
  adaptive thin projections, privacy disposition, exact tested OS scope, claim
  ceiling, and exact public release.

O5 pre-registration binds the deterministic candidate/tag derivation and
no-mutation rule, not an unknowable future commit. The exact candidate and tag
are fixed later by the clean terminal candidate and named-human release gate.

One-execution means one run per pre-registered task-host unit. O5 deliberately
runs each matched task once on each host as portability replication; it does not
replay one host/treatment arm to manufacture a favorable comparison.

For O1-O4, a natural task is a logical pre-registered demand-and-outcome unit,
not a Codex sidebar task or thread. Sequential receipts may remain in one
healthy host task, and one receipt may support more than one criterion only
when it independently meets each criterion's pre-registration and validation
burden. It cannot be counted twice toward one criterion's sample minimum.
An authorized product-plan delivery is already real demand when its primary
purpose is the needed deliverable; the excluded case is a task created mainly
to exercise or diagnose the Harness. This distinction does not waive
pre-registration, evidence, floors, or named-human acceptance.

Human authority, zero-trust evidence, lean independent authority, and bounded
process/resource loss are mandatory guardrails, not substitutes for outcomes.

## Design rules

- Start from the user's goal, not a named tool or catalog.
- Observe healthy authorized capability before searching for more.
- Add only for an evidenced residual gap; release task-scoped exposure when the
  need ends.
- Reuse sufficient protocols, runtimes, and evidence layers before composing or
  authoring anything new.
- Keep goals, consequential judgment, new trust, cost, publication, release,
  and irreversible actions under human authority.
- Claim only what source-bound evidence actually proves.

## Read, contribute, and report

| Need | Document |
| --- | --- |
| Understand the product boundary | [Product North Star](docs/strategy/PRODUCT-NORTH-STAR.md) |
| Review the current unfrozen v1.2 method and enrollment contract | [v1.2 collaboration profile](docs/DEMAND-TO-CAPABILITY-PROFILE-V1.2.md) and [pre-response cohort protocol](docs/PROSPECTIVE-COHORT-PROTOCOL-V1.2.json) |
| Inspect the stopped v1.0 profile and cohort history | [v1.0 profile candidate](docs/DEMAND-TO-CAPABILITY-PROFILE-V1.md) and [prospective cohort protocol](docs/PROSPECTIVE-COHORT-PROTOCOL-V1.json) |
| Apply the bounded Codex-reference-calibrated candidate profile | [Demand-to-capability profile](docs/DEMAND-TO-CAPABILITY-PROFILE.md) |
| Understand the technical separation of concerns | [Architecture](docs/architecture.md) |
| Inspect the proof sequence and external reuse gate | [Research and proof plan](docs/strategy/RESEARCH-AND-POC-PLAN.md) |
| Resume repository work | [Continuation](docs/operations/CONTINUATION.md) |
| See why earlier assets are not current authority | [History boundary](docs/operations/HISTORY.md) |
| Propose a focused change | [Contributing](CONTRIBUTING.md) |
| Read participation expectations | [Code of Conduct](CODE_OF_CONDUCT.md) |
| Ask a non-sensitive question | [Support](SUPPORT.md) |
| Report a sensitive vulnerability | [Security policy](SECURITY.md) |
| Support maintenance | [Sponsoring](SPONSORING.md) |

Repository-owned code and documentation are Apache-2.0 unless a file says
otherwise. Third-party material keeps its original rights.

See [LICENSE](LICENSE), [NOTICE](NOTICE),
[third-party notices](THIRD_PARTY_NOTICES.md), and the
[license policy](docs/license-policy.md).
