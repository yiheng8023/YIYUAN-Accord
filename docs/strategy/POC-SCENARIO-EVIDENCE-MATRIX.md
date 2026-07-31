# PoC Scenario And Evidence Matrix

Status: working research gate; not implementation or runtime-change authority
Date: 2026-07-19

## Purpose

This matrix binds the first three proof lanes to concrete scenarios, host
differences, authority boundaries, observable acceptance, reuse order, failure
handling, falsifiers, and claim limits before targeted external research or
implementation begins.

It implements the sequence in
[`RESEARCH-AND-POC-PLAN.md`](RESEARCH-AND-POC-PLAN.md): scenario and evidence
binding comes before native inventory, official research, reviewed external
research, composition, or residual-gap authoring.

## Scope boundary

In scope:

- context lifecycle, repository-anchored handoff, and same-workspace
  continuation;
- Git branch/worktree topology, safe creation, governed merge, and governed
  cleanup;
- task-scoped MCP lifecycle, including startup control, possible mid-session
  control, leases, idle release, failure recovery, and resource measurement;
- Codex and Claude Code as named initial hosts, plus an opaque-host class that
  prevents unsupported portability claims;
- portable decision contracts separated from host-owned actuation and
  verification.

Out of scope:

- repository bootstrap, migration history, project registration, and the
  historical thread-creation snapshot;
- broad capability catalog discovery before a matrix row requires it;
- installing, enabling, authenticating, executing, or vendoring an external
  capability;
- persistent MCP, Plugin, Hook, Agent Home, consumer, or host configuration
  changes;
- branch creation, worktree creation, merge, cleanup, deletion, commit, push,
  release, or publication;
- reactivating the retired custom Manager. CC Switch remains the operational
  source/install/update/distribution/backup/restore manager where suitable;
  it is not assumed to be a task-level process supervisor.

The bootstrap registry record is related to this repository, but it is a dated
repository-creation and migration authority record rather than product runtime
or PoC evidence. This matrix does not update it.

## Evidence vocabulary

| State | Meaning |
| --- | --- |
| `recorded-static` | Source, configuration, fixture, or documentation was inspected, but live host behavior was not exercised. |
| `observed-single-host` | A dated behavior was observed on one named host/version under recorded conditions. |
| `repeatable-single-host` | The observation was repeated with the same bounded result on one host/version. |
| `observed-cross-host` | Equivalent probes were run on at least two named hosts; differences remain explicit. |
| `blocked-external` | The probe could not start for a non-code boundary such as billing, missing account access, or unavailable host support. |
| `unknown` | Evidence is absent or cannot distinguish competing explanations. Unknown is not a residual gap. |
| `falsified` | A stated hypothesis failed its predeclared acceptance condition. |

No row may advance from static evidence to a live or portable claim without a
dated host-owned observation. A deterministic fixture can validate a decision
contract, but it cannot prove loader behavior, process actuation, latency,
resource savings, or cross-host parity.

## Common evidence record

Every executed scenario must record:

1. scenario and evidence IDs;
2. host, host version/build, model when relevant, loader, and activation mode;
3. date, workspace, repository HEAD, branch/worktree posture, and relevant
   dirty paths;
4. capability source and exact revision/version;
5. account/data boundary and permissions granted, denied, or not requested;
6. pre-state, action or event, post-state, and restoration state;
7. observable measurements, raw log/artifact location, and redactions;
8. acceptance result, counterexample, supported claim, unsupported claims,
   and recheck trigger;
9. user interventions and native approval prompts;
10. cleanup requirements and whether cleanup was actually authorized and
    observed.

Secret values, tokens, authentication state, and unrelated user data must not
enter repository evidence.

## Reuse codes

Each scenario follows the same ordered decision path:

- `N` — healthy native or runtime-owned capability;
- `O` — suitable official capability or documented host interface;
- `E` — reviewed and maintained external capability;
- `C` — composition of existing capabilities;
- `R` — self-authored residual-gap implementation.

`R` is eligible only after a named scenario has repeatable evidence that
`N -> O -> E -> C` is insufficient, the consumer and maintenance owner are
known, and separate implementation authority is granted.

## Cross-arm hard-standard control

The reuse codes vary capability paths, not mandatory standards. Every arm keeps
the repository instruction baseline, native host approvals, bound scenario
facts, truth/safety/authority thresholds, and acceptance verification active.
These controls are not an Arm `B`, `C`, or `D`, and their effect is not credited
as Skill value. Disabling a repository-authored Skill removes only that
capability payload; it does not remove the standards against which all outputs
and actions are judged.

## PoC 1 — Context lifecycle and continuation

| ID | Scenario and host split | Authority boundary | Observable acceptance | Reuse and fallback | Falsifier and claim limit | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `CTX-01` | Observe direct context/token/compaction signals. Split hosts into transparent counters, event-only telemetry, and opaque hosts. | Read-only host telemetry only. No account, config, or Hook changes. | Record which counters/events exist, their units and update timing, and whether repeated reads are consistent. | `N -> O`; if opaque, fall back to `CTX-03` heuristics, not synthetic precision. | No stable supported signal falsifies direct-telemetry availability for that host/version. Never claim a universal context percentage or exact hidden counter. | Codex docs provide `recorded-static` OTel counts and Hook compaction events. The local 0.144.6 non-`--experimental` generated bundle also contains a token-usage notification with optional `modelContextWindow`, but the generator command is experimental and no live notification or Desktop exposure was observed. Sampling, thresholds, and other hosts remain `unknown`. |
| `CTX-02` | Observe automatic compression or degradation around long collaboration on each host. | Bounded disposable or non-sensitive task; no deliberate exposure of private history. | Detect a dated event or behavioral discontinuity, preserve before/after task facts, and measure lost, retained, or distorted facts. | `N -> O -> C`; use repository facts as the comparison oracle. | An inferred event without a host signal remains heuristic. One run cannot define the best efficiency interval. | Codex `PreCompact`/`PostCompact`, generated `ContextCompaction`-related schema, and explicit `ThreadCompactStartParams` are `recorded-static`; no enabled event observation, automatic quality-impact probe, or best-efficiency interval exists. |
| `CTX-03` | Evaluate heuristic pressure signals when counters are opaque: turn count, tool volume, repeated corrections, retrieval misses, and evidence drift. | Read-only observation; heuristics may recommend but not create a thread or mutate state. | Predeclare triggers, compare recommendations with observed retrieval quality, and record false positives/negatives and user interventions. | `N -> C`; prefer a simple explainable rule before any external monitor. | Unacceptable false-positive/negative rate falsifies the heuristic. Never relabel a heuristic as native telemetry. | A [twelve-fixture default-no-action advisory contract](../context-pressure-advisory-contract-2026-07-23.md) separates direct counters, host events, heuristics, user observations, and unknown evidence; it waits without explicit thread authority and a prepared CTX-04/05 packet. An [11-fixture provenance envelope](../context-pressure-provenance-evidence-envelope-2026-07-24.md) now requires a separate exact host/version/profile/run/time binding plus SHA-256-backed host evidence and rejects heuristic-to-telemetry masquerading before the advisory consumes a signal. These are deterministic classifier and input-contract evidence only. No live signal delivery, retrieval-quality comparison, false-positive/negative measurement, best-efficiency interval, or automatic thread action is proved. |
| `CTX-04` | Produce and consume a repository-anchored handoff after an interrupted or long task. Test clean and dirty workspaces separately. Use the weak-Agent floor first when the result informs self-authored Skill acceptance; add a capable diagnostic only when attribution is ambiguous. | Handoff is a navigation artifact. It cannot authorize writes or replace repository truth. Each live trial thread is a separate creation gate. A progress ledger cannot override a newer user correction. | Fresh intake recovers goal, scope, branch/worktree, HEAD, dirty paths, evidence, open work, risks, and first verification steps; every claimed fact is rechecked. Every executed arm requires 100% critical facts and stale-fact rejection. After compaction, completed progress is preserved but an undispatched brief derived from an invalidated plan must be dropped before the next dispatch. | `N -> O -> C`; manual handoff remains the fallback. | Missing or stale critical facts falsify that arm. A triggered diagnostic difference may be model-sensitive and does not alone prove a protocol defect. Successful recovery proves only the tested carrier/host/model conditions. An offline decision packet does not prove runtime subagent interruption. | One Codex local-host intake is [`observed-single-host`](../context-continuation-poc-evidence-2026-07-19.md). A [conditional two-arm protocol](../context-continuation-paired-trial-protocol-2026-07-19.md), 12 decision fixtures, and a read-only live packet builder are prepared. A [seven-case pre-dispatch freshness gate](../context-handoff-packet-freshness-2026-07-24.md) binds the exact trial contract and rejects source, local repository-truth, remote-freshness, authority, and public-prompt drift; one newly built packet matched an immediate local recheck. A [shared Git-observer projection contract](../context-git-snapshot-projection-contract-2026-07-27.md) removes the packet builder's duplicate Git subprocess parser, preserves rename/copy paths, detached/no-upstream states, worktrees, and local-ref-only freshness, and fails closed on live-remote or unknown ahead/behind claims. It proves local mechanism parity and one-observation projection only, not source-semantic freshness, an atomic creation transaction, live remote freshness, thread creation, or receiver behavior. The [ablation packet protocol](../skill-ablation-batch-01-protocol-2026-07-19.md) separates payload identity, loader invocation, artifact production, and receiver outcome; the overlap matrix adds a nine-packet offline `ORCH-RESUME-CORRECTION-01` composition probe for stale undispatched Superpowers SDD briefs. Weak-floor live behavior, task-scoped combined exposure, runtime interruption, and repeatability remain open. |
| `CTX-05` | Continue in a same-workspace new thread. Test manual user-authorized creation separately from any automatic host action. | Thread creation is a host side effect and requires the applicable user/host authority. No project registration is part of this PoC. Model choice must be verified before any named-model claim. | New thread is bound to the same repository, starts from repository truth, and does not inherit unverified claims as fact. Record who initiated creation, which API/UI acted, actual model, and actual reasoning effort. | `N -> O`; one-click/manual creation is the mandatory fallback. | Absence of a supported automatic action falsifies automation for that host/version, not continuation itself. Manual creation must never be reported as automatic capability; an unavailable requested model must not be silently substituted. | The [manual user-authorized Codex path](../context-continuation-poc-evidence-2026-07-19.md) is `observed-single-host`. Generated start/resume/fork schemas are `recorded-static`; start exposes `startup`/`clear`, not a context-pressure trigger. The [paired protocol](../context-continuation-paired-trial-protocol-2026-07-19.md) remains unexecuted. Its packet now has a [read-only pre-dispatch freshness gate](../context-handoff-packet-freshness-2026-07-24.md), but creation authority, actual model/effort, receiver behavior, and automatic creation remain unproved. Bootstrap handoff fields remain historical snapshots. |
| `CTX-06` | In a fresh session, test explicit and implicit invocation of the source-backed `handoff` Skill separately. | Read-only probe; no Skill replacement, update, sync, or consumer mutation. | Record loader visibility, explicit load, implicit activation or non-activation, body/source identity, latency, and result quality. | `N -> O -> existing reviewed Skill`; manual repository handoff is fallback. | Filesystem presence or source identity without invocation falsifies no claim and remains partial. Never infer loader priority or implicit activation from matching bytes. Initial-list absence does not prove loader unavailability because the host may omit Skills under its list budget. | Source-backed CC Switch canary and update chain were observed. The 2026-07-19 [fresh-task exposure preflight](../skill-ablation-batch-01-host-preflight-2026-07-19.md) reported `handoff` absent from the startup Skill list, but loader availability remains unknown. A [canonical protocol/payload and adapter-bound loader preflight](../handoff-loader-trial-preflight-contract-2026-07-24.md) has an empty repository-admitted capture-capability registry and rejects caller-supplied shape-only evidence. A later [Codex CLI 0.145.0 explicit-cue/control probe](../handoff-loader-cli-0.145.0-capability-probe-2026-07-28.md) observed the Skill-specific `Suggested Skills` section only under `$handoff`, but the host emitted no task-bound loader identity or digest and reported Skills budget omission. This is behavior association, not invocation proof; the formal preflight remains blocked. Implicit invocation, canonical Arm C, application-restart revalidation, and cross-device equality remain open. |
| `CTX-07` | Run equivalent instruction-carrier probes across Codex, Claude Code, and any later host. Separate discovery, loading, adherence, and behavior. | Disposable/non-sensitive task; no consumer writes or hidden policy extraction. | For each host record effective instruction surface, precedence evidence, compliance and counterexample behavior under the same bounded scenario. | `N -> O -> C`; host-specific adapters remain explicit. | Any divergence falsifies universal adherence. A pass on one host proves only that host/model/version/scenario. | The [fourteen-fixture independent evidence contract](../instruction-carrier-adherence-contract-2026-07-23.md) separates file visibility, discovery, exact loader evidence, private-oracle adherence, hard standards, and host approval. A [read-only public/private preflight builder](../instruction-carrier-trial-preflight-contract-2026-07-23.md) now binds the exact carrier and blocks when task-bound loader capture is unavailable or unknown. Both remain offline; no weak-Agent host run or cross-Agent parity is proved. |

For `CTX-04`, the additive
[receiver delta ledger](../context-handoff-receiver-delta-ledger-evidence-2026-07-27.md)
now re-runs the unchanged canonical scorer and binds exact artifact, response,
oracle, manifest, and shared-Git before/after digests across sixteen
deterministic falsification cases. It accounts for exact omission, change,
provenance, stale-fact, unsupported-claim, repository-drift, opacity, and
failure-code deltas without changing the canonical verdict. This is an offline
parent-recomputed accounting mechanism, not evidence of receiver recovery,
fresh-session behavior, Skill invocation, losslessness, atomic creation,
AGENTS adherence, weak-Agent behavior, or cross-host parity.

### PoC 1 metrics

- user interventions and corrections;
- approval prompts caused by continuation;
- direct counter/event availability and sampling stability;
- handoff fact loss, stale claims, and recovery time;
- heuristic false-positive and false-negative rates;
- context/tool-output volume at observed degradation or compression points;
- explicit versus implicit Skill invocation and latency;
- cross-host behavioral variance.

## PoC 2 — Git collaboration topology

| ID | Scenario and host split | Authority boundary | Observable acceptance | Reuse and fallback | Falsifier and claim limit | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `GIT-01` | Recover branch, status, HEAD, configured upstream, ahead/behind, recent commit, worktrees, and relevant dirty paths. Test repositories with and without upstreams. | Non-recovery Git inspection. Network refresh is a separately recorded read boundary if needed. Filesystem zero-write behavior is not presumed because Git may refresh internal metadata. | Snapshot is complete, distinguishes local refs from live remote truth, and makes no `origin/main` assumption when absent. | `N`; native Git is sufficient. | Any omitted dirty path or invented upstream falsifies truth recovery. A clean status is not task completion evidence. | The [current local snapshot and disposable integration](../git-topology-decision-poc-2026-07-19.md) are `observed-single-host`. Nine deterministic `GIT-01` fixtures plus real temporary repositories cover no-upstream, local upstream, clean/dirty, rename and repository-local copy-detection paths, detached HEAD, multiple worktrees, and local-ref freshness labeling. A [two-sample read-only envelope](../git-readonly-preflight-envelope-contract-2026-07-24.md) now rejects concurrent drift, raw-porcelain path mismatch, proof-counter promotion, and live-remote overclaim while leaving dirty ownership unknown. The [Context/Git projection contract](../context-git-snapshot-projection-contract-2026-07-27.md) now makes the continuation packet consume that same observer exactly once instead of maintaining a weaker second truth collector. Logical/content containment and projection parity are observed across bounded disposable cases, but filesystem zero-write behavior, live remote refresh, ownership, approval, and cross-host behavior remain open. |
| `GIT-02` | Decide current workspace vs branch vs isolated worktree for simple, dirty, risky, heavy-test, and parallel tasks. | Recommendation only until creation is explicitly authorized. Preserve unrelated dirty work. | Decision uses task scope, current posture, isolation need, test cost, collision risk, and cleanup burden; gold scenarios have explainable outcomes. | `N -> C`; no external capability is presumed necessary. | Incorrect isolation or unacknowledged dirty-work collision falsifies the decision rule. Never claim a worktree preserves thread intent. | Eleven deterministic [topology fixtures](../git-topology-decision-poc-2026-07-19.md) pass. Content review found `git-guardrails` unsuitable as a topology-decision Arm C because it installs interception Hooks rather than choosing branch/worktree topology. The later [nine-fixture interception decision contract](../git-guardrails-interception-evidence-contract-2026-07-24.md) rejects universal native-hook coverage, packaged-script/`pre-push` protocol conflation, and one-command evidence upgrades. Repository admission is now `recipe-only` / `validated=false`, with approved route and payload removed; the live CC copy is unchanged. Eight prompt-only weak-Agent topology fixtures are prepared; Agent adherence, live interception, live creation, and cross-host behavior remain unproven. |
| `GIT-03` | Safely create a branch or worktree after approval, including denial and partial-failure paths. | Branch/worktree creation requires explicit scope and host approval where applicable. No merge, deletion, or push authority is implied. | Exact start point is recorded, unrelated files remain unchanged, failure leaves no ambiguous partial topology, and denial causes a safe stop. | `N -> O`; manual command/UI fallback. | Wrong base, overwritten work, or residual ambiguous state falsifies safe creation. Creation success proves no merge or cleanup safety. | A [disposable native lifecycle](../git-topology-decision-poc-2026-07-19.md) created one exact-base branch/worktree inside a Python temporary root and kept primary `main` at the bound base before merge. The [23-fixture host-preflight contract](../git-host-preflight-evidence-contract-2026-07-23.md) separately binds locator, dirty ownership, parent approval, exact command, denial, and independent re-observation without calling Git. These are fixture-local facts, not user-repository creation, native-dialog, or recovery proof. |
| `GIT-04` | Recommend and, only when separately authorized, perform merge or handoff of completed work. Test clean, diverged, conflicted, and denied cases. | Merge, overwrite, rebase, commit, and remote mutation are distinct authority gates. | Exact source/target SHAs, checks, conflicts, approval result, and post-state are recorded; denial does not trigger a workaround. | `N -> O -> C`; stop for human judgment on semantic conflicts. | Silent conflict resolution, unverified target, or approval bypass falsifies safety. Local green does not prove remote or release readiness. | In the disposable lifecycle, one single-commit `git merge --ff-only` advanced `main` to the exact feature SHA without a merge commit. A dirty primary refused the merge while preserving state. Deterministic fixtures stop on denied authority, dirty targets, conflicts, missing checks, or absent fast-forward proof. Non-fast-forward, semantic conflict, remote, and bound-user-repository merge remain unproved. |
| `GIT-05` | Recommend cleanup and, only when authorized, remove temporary branches/worktrees or artifacts. | Deletion is never implied by task completion. Exact targets and recoverability must be bound. | Cleanup preview names exact targets, material is delivered or explicitly disposable, native approval is honored, and post-state is verified. | `N`; retain safely when authority or evidence is absent. | Deleting the wrong target or losing undelivered evidence falsifies cleanup automation. Recommendation does not prove cleanup occurred. | Clean fixture-local cleanup used exact-target `git worktree remove` without force and `git branch -d`; the merged commit remained reachable through `main`. Native Git refused dirty-worktree removal and unmerged-branch deletion. Decision fixtures retain when authority, delivery/disposability, cleanliness, or merged-history evidence is absent. User-repository cleanup still requires separate deletion authority. |
| `GIT-06` | Protect unrelated dirty work during analysis, testing, creation, merge, and cleanup. | No stash, restore, reset, checkout, overwrite, or broad format action without explicit scope. | Pre/post path and byte/hash comparison shows unrelated work unchanged; test artifacts are identified and bounded. | `N -> C`; isolated worktree is a candidate only after posture inspection. | Any unrelated modification is a hard failure and triggers stop/recovery review. | Disposable real-repository tests keep unrelated SHA-256 sentinels byte-identical across bounded observer calls, exact-base worktree creation, fast-forward merge, non-force cleanup, and dirty-target merge refusal. This does not establish filesystem zero-write observation. Repeatability across hosts, concurrent mutation, and Agent adherence remain open. |
| `GIT-07` | Evaluate recovery after command failure, interruption, or host crash at each topology phase. | Recovery may inspect without recovery mutation; mutation requires the original or renewed authority. Inspection itself is not claimed filesystem-zero-write. | Pre-state can be reconstructed, partial artifacts identified, safest reversible option presented, and no status is falsely closed. | `N -> O -> C`; human confirmation for ambiguous ownership or destructive recovery. | Inability to distinguish partial from completed state falsifies automatic recovery. Never infer success from command exit alone. | Three disposable single-host failures are observed: nonexistent checkout leaves reconstructed state and bytes unchanged; nonempty-target worktree failure leaves no partial registration; and a real content conflict is reobserved as `UU tracked.txt` while `HEAD`, `MERGE_HEAD`, the unmerged index, conflict bytes, worktrees, and unrelated bytes remain unchanged across the observer call. The conflict is neither resolved nor aborted. Filesystem zero-write behavior, interruption, crash, partial filesystem mutation, broader recovery writes, user repositories, and cross-host behavior remain open. |

### PoC 2 metrics

- incorrect topology recommendations and actions;
- unrelated dirty paths or bytes changed;
- unnecessary native approval prompts;
- denial handling and workaround attempts;
- start-point, source-SHA, and target-SHA accuracy;
- conflict detection and human-decision count;
- rollback/recovery success and ambiguous residual state;
- cleanup false positives and retained-undelivered evidence.

## PoC 3 — Task-scoped MCP lifecycle

| ID | Scenario and host split | Authority boundary | Observable acceptance | Reuse and fallback | Falsifier and claim limit | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `MCP-01` | Inventory enabled MCPs, Plugin-provided MCPs, tool filters, processes, startup latency, and observable resource baseline per host. | Read-only inventory and process observation. Do not read secrets or account payloads. | Dated host/version inventory distinguishes configured, enabled, initialized, connected, authenticated, and callable states. | `N -> O`; static metadata fallback remains explicitly partial. | A config row without process/tool evidence cannot prove live availability. Tool visibility cannot prove ecosystem completeness. One point-in-time process-forest total cannot prove MCP-only, per-server, per-task, idle, or steady-state resource use. | The [current Codex host inventory](../mcp-current-host-inventory-2026-07-19.md) is `observed-single-host` partial: CLI standalone config reported zero servers, Desktop projected 457 MCP-named definitions across 12 namespaces, one local `node_repl` call succeeded, and safe process ownership remained unresolved. A bounded Codex descendant-forest snapshot found 107 processes with about 5.05 GB working set and 3.70 GB private memory, but no specific MCP or task attribution. A separate [isolated app-server probe](../../registry/codex-app-server-isolated-mcp-status-probe-2026-07-19.json) called `mcpServerStatus/list` without a thread and returned zero servers from a new CODEX_HOME. A newer [0.145.0 direct-call probe](../mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.md) listed one local Sentinel and successfully invoked it, while observing two Sentinel instances for the single configured server. This does not observe the current Desktop account/Plugin surface or establish a universal process topology. Startup/idle comparability, other tool health/auth, and other hosts remain open. |
| `MCP-02` | Compare one-shot startup baselines: all configured, selected MCP disabled, Plugin MCP disabled, and tool allow/deny filtering. | Disposable startup environment; no persistent config changes. Any temporary config must have exact pre/post restoration evidence. | Record initialized servers/tools, task success, startup time, process count, RSS where available, prompts, and restoration. | `N -> O`; use supported startup filtering before any custom controller. | No measurable or functional distinction falsifies the expected benefit for the tested workload. One-shot startup control is not mid-session lifecycle control. | A [two-repetition isolated startup-profile comparison](../mcp-app-server-0.145.0-startup-profile-evidence-2026-07-23.md) observed full `identity/hold` access with one Sentinel, allow-then-deny filtering retain `identity` while rejecting `hold` with one Sentinel, and `enabled=false` reject both calls with zero Sentinel instances. All six runs used new app-server/new-thread boundaries and cleaned up exactly. This validates a startup-profile fallback for this host/version/Sentinel, not Plugin disable, same-thread switching, stable latency/resource benefit, or cross-host parity. |
| `MCP-03` | Test whether a running session supports safe enable, disable, unload, and re-enable without restart. Split config mutation from supported runtime actuation. The desired operating policy is the smallest task-relevant MCP set, re-evaluated at phase changes, because an unnecessarily broad active set can degrade host responsiveness. | No live config mutation without a separate, reversible authorization. Use disposable sessions first. | Supported interface, state transition, tool-list change, process change, in-flight behavior, and restoration are all observed. An on-demand claim also requires a bounded task-to-MCP decision, transition latency, task correctness, failure fallback, and repeated task/tool response-latency comparison against the same control workload. | `N -> O`; session restart/startup profile is fallback. Research `E` only after native/official insufficiency is evidenced. | Config edit without live unload falsifies hot-switch actuation. Lower process or tool count without a bounded responsiveness comparison proves no latency benefit. If no supported interface exists, mark the host/version unsupported or unknown; do not claim Skill/Hook control. | A [pinned official-source, local schema, and isolated status review](../mcp-runtime-refresh-interface-and-trial-protocol-2026-07-19.md) found `config/mcpServer/reload` and thread-aware `mcpServerStatus/list`. The [0.145.0 direct-call evidence](../mcp-app-server-0.145.0-direct-tool-call-evidence-2026-07-23.md) established a no-model-turn local call. A subsequent [isolated new-thread trial](../mcp-app-server-0.145.0-new-thread-reload-evidence-2026-07-23.md) observed a disabled new thread reject the Sentinel and a post-restoration new thread call a distinct instance. It did not isolate reload as the cause. Reload acceptance is still not completed actuation evidence. Thread A's status lost tools while its old runtime still called successfully, and thread B's status regained tools while its old disabled runtime still rejected the server. Thus status is not a sufficient loaded-thread availability oracle. The separate startup-profile comparison now validates restart/new-thread configuration as the bounded fallback. A [27-fixture task-selection contract](../mcp-task-selection-decision-contract-2026-07-23.md) enforces the smallest admitted declared set, task-or-phase-only default activation, and inactivity for unselected candidates. An [18-fixture lifecycle skeleton](../mcp-lifecycle-trial-skeleton-contract-2026-07-24.md) now carries that selection into a future trial without observations or inherited authority. A [12-fixture same-thread parent-event adapter](../mcp-same-thread-refresh-evidence-contract-2026-07-24.md) now requires the exact same thread, an active turn, direct-call outcomes, one-key config digests, raw event hashes, and exact restoration while treating status and reload acceptance as diagnostic only. It has not executed a live host transition. Same-thread actuation, on-demand automatic switching, old-process release caused by reload, task-end release, and responsiveness benefit remain unproved. |
| `MCP-04` | Model two tasks sharing or competing for one MCP using leases/reference counts, including cancellation and nested tasks. | Start with simulation or disposable supervisor evidence. No production process ownership. A live final-release trial requires two independently releasable subscriptions bound to the same exact loaded runtime; two app-servers, repeated resume on one connection, or a callable but unsubscribed connection cannot substitute. | Server remains available while any valid lease exists, releases after the last lease, isolates task denial/failure, and records owner/refcount transitions. A host preflight must first observe two connection-scoped subscription acquisitions and releases without a model-turn or state-fabrication side channel. | `N -> O -> E -> C -> R`, with each transition gated by evidence. | Premature release, leaked lease, cross-task interference, unverifiable ownership, or failure to establish the second owner stops the live final-release branch. A model/fixture is not live process proof. | The 22-fixture [offline lifecycle contract](../mcp-task-lifecycle-evidence-contract-2026-07-23.md) evaluates one overlapping multi-task trace and rejects duplicate acquisition, cross-task/double release, premature release, leaked leases, missing final release, and non-overlapping pseudo-concurrency. The direct-call observation is not a lease or reference-count API. A newer [three-run multi-connection preflight](../mcp-app-server-0.145.0-multi-connection-subscription-preflight-evidence-2026-07-27.md) used one App Server and two independent loopback WebSockets per run. Both connections called the same exact Sentinel, but B returned `notSubscribed` twice in all three formal runs; a zero-turn resume calibration had no materialized rollout. Thus the overlapping-owner precondition is not met and the final-release trial is stopped. A separate `MCP-THREAD-CREATOR-CONNECTION-CLOSE-ATTRIBUTION-01` protocol now pre-registers a narrower paired observation: keep an independent observer connection and the same exact Sentinel, then compare a no-action control with closure of only the thread-creating connection over five seconds. It has deterministic classification tests but no live result; even a positive association would not establish task end, lease/refcount semantics, final-owner release, arbitrary-MCP behavior, or resource benefit. |
| `MCP-05` | Release an idle MCP and measure whether the task remains correct and resources improve. | Disposable session; no unrelated process termination. Exact PID/owner identity required before any stop action. | Pre/post process count, RSS/CPU where available, tool availability, release latency, next-use recovery, task success, and prompt count are recorded. | `N -> O`; restart fallback. External supervisor research requires a measured residual benefit. | No stable resource benefit or unacceptable restart/task cost falsifies automatic idle release for that workload. Never generalize one server's savings to all MCPs. | Official 0.145.0 behavior retains the last-unsubscribed inactive thread for 30 minutes before attempting unload. In the earlier direct-call probe, the 30-minute path was not executed. A newer [isolated 30-minute observation](../mcp-app-server-0.145.0-idle-unload-evidence-2026-07-23.md) sent no request during the idle window and, at about 1,800.7 seconds, jointly observed `thread/closed`, a natural stop event, and disappearance of the exact bound Sentinel identity; a new thread then called through a new instance. It does not prove task-end immediate release, an on-demand switch, a lease/refcount API, causation between the adjacent events, all child exit, stable resource savings, or cross-host parity. A separate [three-pair thread-unsubscribe attribution trial](../mcp-app-server-0.145.0-thread-unsubscribe-release-attribution-evidence-2026-07-27.md) used six independent runtimes: all three unsubscribe responses were `unsubscribed`, yet all 66 exact samples across unsubscribe and subscribed-control arms retained their baseline identities for five seconds with no stop event. This falsifies unsubscribe as an observed immediate-release mechanism only for those host/version/Sentinel windows. It does not prove task end, a later release cause, overlapping ownership or final-release semantics, arbitrary-MCP behavior, or cross-host parity. |
| `MCP-06` | Recover from host, MCP, wrapper, or lease-controller crash and restore prior enabled/disabled state. | Failure injection only in disposable environments. Persistent-state restoration requires explicit scope and backup. | Crash is detected, active task impact recorded, leaked processes/leases identified, prior state restored or safely reported, and restart is idempotent. | `N -> O -> E -> C -> R`; fail closed when state ownership is ambiguous. | Lost prior state, duplicate process, leaked lease, or false healthy report falsifies recovery. One local child-exit class cannot establish host, network, wrapper, Plugin, or lease-controller resilience. | A [two-run local child-exit probe](../mcp-app-server-0.145.0-child-exit-recovery-evidence-2026-07-23.md) used an exact token-gated `os._exit(86)` fault in one Sentinel alias. The same app-server and original control instance survived both faults, but the victim's same-thread next call failed twice. A new thread recovered the victim twice through a new exact instance and also initialized an additional control instance. Run 02 required owned-handle app-server termination. This supports a new-thread/startup fallback for this host/version/failure class only; it does not prove proactive restart, duplicate freedom, prior enabled-state restoration, leases, stable graceful shutdown, or a generic recovery controller. |
| `MCP-07` | Compare tool filtering with full process disable for high-tool-count but low-resource MCPs. | Startup/disposable controls only. | Measure tool-list/context reduction, process/resource change, task success, latency, and operational complexity. | `N -> O`; prefer filtering when it achieves the scenario objective with lower lifecycle risk. | If filtering does not reduce the target cost, it is not a substitute; if disable adds no benefit, process control may be unnecessary. | In the isolated startup-profile comparison, allow-then-deny filtering changed the callable surface but still started one Sentinel in both runs; complete disable rejected both tools and started zero Sentinel instances. Thus filtering and disable addressed different costs for this local server. The two sequential repetitions do not prove context/token reduction, stable latency/resource benefit, or a universal ranking. |
| `MCP-08` | Verify ownership boundaries among host runtime, Plugin, CC Switch, consumer config, Hook, wrapper, proxy, and any supervisor candidate. | Read-only mapping first. No component may take over foreign state by discovery alone. | Each state has one recorded authority, mutation surface, verification surface, rollback owner, and conflict rule. | `N -> O -> existing CC Switch where suitable -> E/C/R only for a named residual gap`. | Overlapping writers or unverifiable restoration falsify the ownership design. CC Switch source management must not be reported as proven process lifecycle control. | CC Switch source/update/backup/restore evidence exists; runtime process control does not. Custom Manager remains retired. |

The creator-connection-close formal paired protocol remains unexecuted. One
[calibration attempt](../mcp-thread-creator-connection-close-calibration-attempt-2026-07-27.md)
started only the isolated control arm and failed before either paired window
because the runner required a zero-turn rollout file that did not materialize.
This is invalid prerequisite and authority-conflict evidence, not release or
retention evidence: the protocol's loopback execution boundary was still
false. The offline probe was remediated and regression-tested but not rerun
live. Any fresh loopback calibration or formal paired run requires separate
explicit user authorization and fresh exact roots. The two retained roots are
cleanup debt only; deletion is not authorized. None of this proves task end,
leases/reference counts, final-owner release, resource benefit, arbitrary-MCP
behavior, or controller need.

The
[observer acquisition-path admission](../mcp-thread-creator-close-observer-acquisition-path-admission-2026-07-27.md)
now verifies that all three valid multi-connection reports used
`thread-created-auto-attach`, one app-server, two distinct bridges, one thread,
one exact Sentinel, a direct connection-B call, and zero model turns. It also
verifies that the current protocol/probe still requires `thread/resume`.
Therefore the current pair remains blocked until a new offline amendment is
validated. Auto-attach callability is not a second subscription, owner, lease,
task-end signal, release result, or live authorization.

The
[auto-attach v2 offline amendment](../mcp-thread-creator-connection-close-auto-attach-offline-amendment-v2-2026-07-27.md)
now supplies that offline revision: connection B completes initialization and
`config/read` before connection A creates the non-ephemeral read-only thread;
B then calls the same thread and exact Sentinel directly, without
`thread/resume`. Sixteen injected in-memory scenarios also require evidence
sealing before the post-window call and bounded cleanup on ordinary and cleanup
failures. This is deterministic protocol evidence only. Formal live runs and
paired reports remain zero, all live authority remains false, and no creator-
close retention/release result, second subscription, owner, lease/refcount,
task-end semantics, final release, resource benefit, cross-host/version parity,
or controller need is proved.

The 2026-07-24
[CLI/MCP startup diagnostic](../codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.md)
adds a current degraded-startup observation without changing lifecycle claims.
Two visible warning lines describe one injected `sites-design-picker` failure;
a separate background remote Plugin-service MCP transport failure was also
observed. The picker is absent from the static MCP list, and the shared root
cause, persistence, clean-restart outcome, task-end release, and dynamic
activation remain unproved.

### PoC 3 metrics

- configured, initialized, connected, authenticated, and callable MCP counts;
- startup and reactivation latency;
- process count, RSS, CPU, and idle duration where observable;
- tool-list/context surface before and after filtering;
- task success and failure rate;
- premature release, leaked lease, duplicate process, and cross-task interference;
- crash detection and prior-state restoration;
- approval prompts, user interventions, and operational complexity.

## Common stop and fallback rules

1. If evidence cannot distinguish unsupported behavior from missing access,
   record `unknown` or `blocked-external`; do not manufacture a residual gap.
2. If a probe requires installation, account connection, authentication,
   persistent configuration, third-party execution, or broader data access,
   stop for the smallest separate authorization.
3. If a Git probe reaches merge, overwrite, deletion, remote mutation, or
   cleanup, stop for the exact state-changing authority.
4. If an MCP probe cannot prove process ownership, do not terminate it.
5. If host behavior differs, preserve the adapter split; do not average it
   into a portable claim.
6. If native or official capability satisfies the scenario, stop the reuse
   search unless comparative evidence is explicitly required.
7. If a probe fails, restore only within the already authorized boundary,
   record partial state, and keep the result open when restoration is not
   verified.
8. GitHub Actions that do not execute steps because of account billing or
   spending limits are `blocked-external`, not code failure and not remote
   green evidence.

## Cross-cutting Skill portfolio gate

The three PoCs share the detailed
[`Skill portfolio rebaseline and closeout gates`](SKILL-PORTFOLIO-REBASELINE-AND-CLOSEOUT-GATES.md).
CC Switch is reused wherever its source, install, update, distribution, backup,
or restore capability is suitable and verified. No PoC may justify a parallel
manager merely because it needs a Skill or consumer projection.

| ID | Scenario | Authority boundary | Observable acceptance | Failure and claim limit |
| --- | --- | --- | --- | --- |
| `SKL-01` | Reconcile the live physical pool, database rows, consumer projections, broken links, and same-name different-content collisions. | Read-only inventory; no relink, move, repair, install, or delete. | Every counted class has an exact path/source definition and unresolved ownership remains explicit. | UI counts or path presence alone do not prove physical, usable, source-backed, or backed-up equality. |
| `SKL-02` | Classify official/runtime, direct third-party, aggregate/index, project-local, and repository-authored origins. | Metadata and source review only. | Each candidate has one origin, upstream/revision boundary, and active/non-active state. | Public availability or catalog presence is not admission or license proof. |
| `SKL-03` | Use CC Switch repositories and `skills.sh` as primary discovery, with the existing public pool as bounded supplemental evidence. | Discovery does not authorize download, installation, or execution. | New searches begin from a named demand and stop when the primary surfaces are sufficient. | Catalog breadth does not prove suitability, completeness, health, or trust. |
| `SKL-04` | Run mechanical deduplication, collision review, and weak-Agent-floor ablation with self-authored Skills absent or host-disabled before enabling them; add a capable-model diagnostic only when attribution is ambiguous. | Candidate content remains outside active roots until separately approved. Prompt-only non-invocation is not disablement evidence. The hard-standard baseline remains active in every arm. | Native, official, reviewed external, self-authored, and composed value is attributable to recorded arms under fixed acceptance and named payload hashes. Candidate suitability is checked before constructing an arm. | A self-authored Skill cannot be credited without a weak-Agent self-authored-disabled baseline; a capable-model pass cannot substitute for the weak floor, an unsuitable external candidate cannot be forced into an arm, and a weak-Agent improvement cannot waive safety or authority failures. |
| `SKL-05` | Install an approved shared Skill through CC Switch and verify each named host. | Installation and consumer mutation require separate authority. | Source/revision/digest, backup, projection, host visibility, invocation, update path, and rollback are verified. | One host or filesystem link does not prove cross-host invocation or cross-device equality. |
| `SKL-06` | Consider a repository-authored Skill only after alternatives fail repeatedly. | Design and implementation require residual-gap evidence and separate authority. | The gap, alternatives, owner, tests, maintenance, consumer path, and retirement trigger are bound. | Unknown host behavior, discovery membership, or preference for local control is not a residual gap. |

The 2026-07-24
[source-lineage and collision index](../skill-source-lineage-collision-index-2026-07-24.md)
joins seven dated repository records into eight evidence groups covering 56
logical Skill identifiers. It is a derived SKL-01/02/04 navigation surface,
not a current CC or Agent Home scan. The selected CC cohort proves bounded
historical content ancestry for all three samples and exact current
CC-to-repository adapted-payload equality for `grill-with-docs` and `review`;
it does not prove the producing CC source row or installation path. Its dated
occurrences do not prove
projection, loader invocation, behavioral equivalence, replacement, migration,
or deletion eligibility.

The current `SKL-04` host transaction is not executable. Its
[2026-07-24 read-only revalidation](../skill-ablation-host-transaction-revalidation-2026-07-24.md)
found the prepared config digest had drifted and returned
`blocked-baseline-drift-reintake-required`. Matching target hashes and zero
`skills.config` entries do not authorize silent rebaselining, configuration
mutation, restart, or a weak-Agent arm.

The later
[authenticated CLI route diagnostic](../codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.md)
observed successful exact-marker returns from both Spark/low and Mini/low. It
removes authentication and basic route reachability as the immediate block,
but not the `SKL-04` exposure gate: Spark omitted 130 additional Skills after
exceeding the two-percent Skills budget, Mini shortened descriptions, and
neither run proved task-scoped selected/unselected exposure or actual-condition
telemetry. No formal live arm is credited.

The subsequent
[app-server task-scoped exposure probe](../codex-app-server-task-scoped-skill-exposure-evidence-2026-07-24.md)
closes only the all-user-disabled preflight on Codex `0.145.0`. It preserved
the same 111 Skill identities, changed all 105 user Skills from enabled to
disabled, retained 6 enabled system Skills, and obtained parent-observed exact
Spark/low plus an action-free marker turn. Config and repository-status digests
were stable. This makes the self-authored-disabled baseline executable without
the blocked global transaction, but it does not expose one selected external
Skill, prove invocation, execute a formal `SKL-04` arm, or establish
cross-host behavior.

The next
[single-selected exposure preflight](../codex-app-server-selected-skill-exposure-evidence-2026-07-24.md)
kept only the exact CC Switch-managed `grill-me` user Skill enabled, disabled
the other 104 user Skills, and preserved all 6 system Skill states. It started
an exact Spark/low read-only ephemeral thread but intentionally sent no
`turn/start`. This proves selected exposure only. Loader invocation, prompt
inclusion, trigger behavior, private-oracle outcome, repeated value, and
superiority remain open.

The later
[source-pinned debugging comparison](../human-ai-collaboration-weak-agent-live-comparison-batch-03-2026-07-24.md)
ran three valid Spark/low current-Matt versus historical Superpowers `6.1.1`
pairs in disposable project projections and retained an earlier
classifier-invalid guard pair unchanged. Both candidates passed visible tests
3/3. Full hidden contract passed Matt 1/3 and historical Superpowers `6.1.1`
2/3; complete strict process passed 1/3 each.
The mixed result favors neither candidate. It proves no independent loader
event, candidate-specific instruction delivery, causation, production
competence, full-Superpowers orchestration, cross-host value, portfolio
decision, or self-authored residual gap.

The
[current Skill evidence reconciliation](SKILL-ECOSYSTEM-CURRENT-EVIDENCE-RECONCILIATION-2026-07-27.md)
binds this behavior cell explicitly to historical Superpowers `6.1.1`.
In that dated reconciliation, Superpowers `6.2.0` remains a source/package
baseline only. Separate later decisions now give the exact current Matt
projection and Superpowers `6.2.0` projection their own identity-bound
diagnostic-only admissions
([Matt](HUMAN-AI-COLLABORATION-TDD-MATT-CURRENT-DIAGNOSTIC-ONLY-ADMISSION-DECISION-2026-07-27.md);
[Superpowers](HUMAN-AI-COLLABORATION-TDD-SUPERPOWERS-620-DIAGNOSTIC-ONLY-ADMISSION-DECISION-2026-07-27.md)).
Neither admission authorizes materialization, dispatch, or execution or turns
the historical behavior cell into current-version behavior. A
[current self-authored treatment audit](HUMAN-AI-COLLABORATION-TDD-CURRENT-SELF-AUTHORED-TREATMENT-GAP-AUDIT-2026-07-27.md)
found no symmetric repository-authored TDD treatment: the three-contract chain
is phase-control orchestration, the approved adapted TDD payload is Matt
third-party lineage, and runner/ledger components are infrastructure. The
missing arm is therefore an experiment-identity/attribution gap, not zero
performance, net-value evidence, a residual functional gap, or authority to
author another Skill. In the dated reconciliation vocabulary, the missing arm
remains `unknown`, not zero performance; the later audit narrows why that arm
cannot be constructed from current self-authored components.

The
[current TDD execution-readiness reconciliation](HUMAN-AI-COLLABORATION-TDD-CURRENT-EXECUTION-READINESS-RECONCILIATION-2026-07-27.md)
keeps both exact candidates blocked from dispatch. Static diagnostic admission
does not supply protocol eligibility, dispatch freshness, a short-lived
authorization envelope, live ledger authority, formal-runner integration,
atomic source materialization, real app-server resource ownership,
cross-process exclusion, or crash recovery. No weak-Agent candidate diagnostic
or model request is currently eligible.

The
[TDD non-comparative dispatch successor contract v2](HUMAN-AI-COLLABORATION-TDD-NONCOMPARATIVE-DISPATCH-SUCCESSOR-CONTRACT-V2-2026-07-27.md)
adds a pure offline, fail-closed preparation boundary. Its current decision is
`NO-GO`; it authenticates neither authority, clock, nor toolchain and does not
authorize candidate materialization, app-server start, model dispatch, formal
acceptance credit, or portfolio change. Any future authorized runtime slice
must establish one shared ledger authority before snapshot and preflight
capture, then receive a separate independent grant.

The distinct software-lifecycle protocol
[maintenance/migration Batch 01](HUMAN-AI-COLLABORATION-MAINTENANCE-MIGRATION-PROTOCOL-BATCH-01-2026-07-24.md)
has now produced three valid native-disabled versus exact-selected CC pairs on
the synthetic affected-consumer compatibility migration. Both arms passed the
visible oracle 3/3; the hidden contract passed native 3/3 and candidate 1/3,
while both arms met the clean process boundary 3/3. This is a bounded native
association on one synthetic fixture, not candidate harm, general preference,
causation, removal readiness, portfolio action, or residual-gap proof. The
candidate remains a local adapted derivative whose exact upstream equality is
false. The security slice remains deferred because the suitable proprietary
system Skill lacks a proved clean disabled control and cannot be vendored.

The
[other CC and external Skill coverage audit](OTHER-CC-AND-EXTERNAL-SKILL-SCENARIO-COVERAGE-AUDIT-2026-07-27.md)
classifies the current bounded behavior cells under requirements discovery,
implementation/review, incident diagnosis, and maintenance/migration without
crediting loader invocation, instruction delivery, or causation. It identifies
`SE-RELEASE-CHANGE-01` as the highest-priority named planned-only
software-lifecycle slice. Approved `ci-cd-and-automation` and
`shipping-and-launch` records support only a zero-model
source/admission/overlap preflight; they do not prove current CC availability,
candidate-specific exposure, release competence, live value, or a residual
self-authored gap.

The follow-on
[release/change zero-model protocol](HUMAN-AI-COLLABORATION-RELEASE-CHANGE-ZERO-MODEL-PROTOCOL-2026-07-27.md)
and
[candidate preflight](HUMAN-AI-COLLABORATION-RELEASE-CHANGE-CANDIDATE-PREFLIGHT-2026-07-27.md)
freeze one repository-only negative-control fixture across the native arm,
`ci-cd-and-automation`, and `shipping-and-launch`. Fifteen required evidence
codes remain missing, so the only valid oracle is
`preparation-only-no-go / NO-GO`; all commit, push, CI rerun, signing,
publishing, deployment, traffic-change, and rollback transitions remain
stopped. This validates only the offline fail-closed protocol cell for
`SE-RELEASE-CHANGE-01`. It does not promote the slice from planned-only to
live-domain evidence and supplies no Skill treatment, host, release-readiness,
value, causation, superiority, or residual-gap claim.

The separate
[access/comms zero-model calibration](HUMAN-AI-COLLABORATION-ACCESS-COMMS-ZERO-MODEL-CALIBRATION-2026-07-27.md)
adds one general, non-software structured-semantic process-loss cell for
`GEN-ACCESS-COMMS-01`. It reuses the existing cumulative-loss accounting over
one control and eight registered faults, including obligation, actor,
negation, deadline/unit, uncertainty, invented-commitment, terminology, and
accessibility-structure loss. Terminal recovery preserves the historical loss
ledger. The result is calibration-only and does not promote the source
scenario to live-domain evidence or prove free-form language, comprehension,
accessibility conformance, actual human review, candidate value, or cross-host
behavior.

## Cross-cutting persistent semantic authority gate

The
[semantic-authority layer reconciliation](HUMAN-AI-COLLABORATION-SEMANTIC-AUTHORITY-LAYER-RECONCILIATION-2026-07-28.md)
adds a cross-lifecycle state gate without making one Skill mandatory:

| ID | Scenario | Authority boundary | Observable acceptance | Failure and claim limit |
| --- | --- | --- | --- | --- |
| `SEM-01` | Consume the same accepted domain language and consequential decisions across requirements, architecture, implementation/TDD, independent review, release/rollback, operations/maintenance, handoff, and closure. | Read-only consumption is baseline. A Skill invocation is not required merely to read existing semantic authority. | Each stage binds the same accepted term/decision identities, reports conflicts and supersession, and preserves unresolved material as unresolved. | Matching filenames or fluent terminology do not prove semantic continuity. A downstream pass cannot erase an earlier semantic delta. |
| `SEM-02` | Evolve ambiguous or conflicting domain language through one-question-at-a-time human decision elicitation, code/document cross-check, concrete scenarios, and sparse ADRs. | Canonical terms and authoritative decisions require responsible-human acceptance. Working notes, generated projections, and handoffs cannot self-promote. | The glossary remains implementation-free; ADRs satisfy hard-to-reverse, surprising, and real-trade-off criteria; rejected alternatives, status, supersession, and evidence are traceable when material. | Mandatory grilling for every code task, invented domain truth, silent terminology replacement, or ADR inflation falsifies the route. |
| `SEM-03` | Compare the exact current Matt `grilling + domain-modeling` composition with the exact existing adapted `grill-with-docs` monolith or a native composition under fixed facts and hard standards. | No CC update, missing-primitive install, wrapper replacement, or portfolio change before exact source, dependency, exposure, invocation, authority, and rollback gates. | Treatment identities, dependency completeness, loader evidence, semantic deltas, human burden, token/latency cost, and downstream continuity are measured separately. | Current source structure is not value proof. A local monolith and upstream wrapper are not interchangeable treatments. |

The source reconciliation accepts the architectural principle but proves no
local invocation, token reduction, candidate superiority, cross-Agent
adherence, full lifecycle continuity, or residual need for a self-authored
Skill.

The
[SEM-03 continuity protocol](HUMAN-AI-COLLABORATION-SEMANTIC-AUTHORITY-CONTINUITY-PROTOCOL-2026-07-28.md)
now freezes the three treatment identities, the four fresh-thread lifecycle
phases, the common hard gates, and direction-falsification rules. It reuses the
existing weak-Agent and parent-private oracle seams. The disposable fixture and
private oracle reject seven injected continuity faults without exposing the
oracle or pre-injecting human decisions. Exact current-source static admission
covers eight raw Git-blob files, the MIT license, relative format dependencies,
host-specific composition, document-write authority, and the Windows EOL
conversion hazard. The isolated projection and no-turn exposure gates passed
first on Codex Desktop `0.145.0` and again after current-host drift to `0.146.0`.
The refresh used a temporary empty Codex home and empty MCP-table override,
observed exactly the three required repo Skills, retained no runtime home, and
left projection bytes, global config, and repository status stable. The current
50-Skill inventory versus the earlier 114-Skill snapshot is dated host drift,
not deletion or value evidence. A 2026-08-01 no-turn checkpoint then used one
stable 48-Skill identity set to prove zero configurable Skills enabled in the
native arm and only the exact repository-pinned local monolith enabled in its
treatment arm. The same report records positive-packet acceptance and
fail-closed full-oracle and partial-canary leakage mutants. Temporary treatment
and Codex homes were removed. Loader/instruction delivery, behavior, value, and
all model runs remain open. The records authorize no model dispatch, CC
mutation, candidate preference, or self-authored arm.

A subsequent zero-model execution-plan preflight found that the existing
shared weak-Agent runner cannot represent the SEM-03 treatment IDs and provides
no independent loader or instruction-delivery event. A dedicated compiler now
materializes one parent plan and one oracle-isolated public packet for each
treatment with visible `gpt-5.3-codex-spark`/`low` routing, zero dispatch
budget, no fallback, bounded sandboxing, four fresh phase threads, human
decision injection, hard stops, and exact cleanup. All three bundles passed and
the temporary root was removed. This is adapter-plan evidence only: the runtime
adapter, dispatch readiness, every model run, loader/instruction delivery,
behavior, continuity, value, and cross-host claims remain open.

## Program closeout cleanup gate

Program closeout is blocked until the portfolio/closeout gate inventories and
dispositions historical debt and temporary process artifacts. The gate covers
temporary source trees, disposable repositories and test homes, branches and
worktrees, generated trial packets and logs, backups, broken links, stale
projections, superseded capabilities, adapters, and unresolved verification,
CI, release, or remote-state debt.

Cleanup is a separately authorized transaction. Each exact target must be
classified as authoritative, historical, archivable, replaceable/migratable,
deletable after authorization, or blocked. Post-cleanup evidence must verify
target state, remaining links, repository posture, required tests, generated
state, and any separately authorized remote state. Finishing a PoC, passing
local tests, or accepting a handoff never implies cleanup or deletion authority.

## Existing evidence anchors

- [`PRODUCT-NORTH-STAR.md`](PRODUCT-NORTH-STAR.md) — product layers,
  non-goals, and current research hypotheses.
- [`RESEARCH-AND-POC-PLAN.md`](RESEARCH-AND-POC-PLAN.md) — required research
  order and initial acceptance signals.
- [`../dynamic-runtime-control-gap-review-2026-07-18.md`](../dynamic-runtime-control-gap-review-2026-07-18.md)
  — dated Codex startup-control evidence and hot-switch limits.
- [`../cross-agent-claim-limit-reconciliation-2026-07-18.md`](../cross-agent-claim-limit-reconciliation-2026-07-18.md)
  — claim firewall separating static, runtime, and cross-host evidence.
- [`../consumer-mapping-evidence-gap-reconciliation-2026-07-18.md`](../consumer-mapping-evidence-gap-reconciliation-2026-07-18.md)
  — dated consumer mapping, ownership, loader, and activation gaps.
- [`../cc-switch-handoff-real-canary-execution-2026-07-18.md`](../cc-switch-handoff-real-canary-execution-2026-07-18.md)
  — source-backed `handoff` canary, recovery, update-chain, and remaining
  fresh-session/cross-device limits.
- [`../custom-manager-retirement-reconciliation-2026-07-18.md`](../custom-manager-retirement-reconciliation-2026-07-18.md)
  — CC Switch reuse boundary and custom-Manager reactivation gate.
- [`../round03-evidence-protocol-batch-01.md`](../round03-evidence-protocol-batch-01.md)
  — deterministic-fixture versus live-evidence boundary.
- [`../context-continuation-poc-evidence-2026-07-19.md`](../context-continuation-poc-evidence-2026-07-19.md)
  — dated Codex manual continuation observation, repository-truth recovery,
  and explicit automatic/lossless/cross-host claim limits.
- [`../context-continuation-paired-trial-protocol-2026-07-19.md`](../context-continuation-paired-trial-protocol-2026-07-19.md)
  — weak-Agent-first conditional two-arm design, predeclared fact oracle,
  guardrails, and separate live-thread authority gates.
- [`../git-topology-decision-poc-2026-07-19.md`](../git-topology-decision-poc-2026-07-19.md)
  — dated native-Git snapshot, local-versus-live ref boundary, 20 decision
  fixtures, and recommendation-versus-mutation authority separation.
- [`../mcp-current-host-inventory-2026-07-19.md`](../mcp-current-host-inventory-2026-07-19.md)
  — current CLI/Desktop inventory split, bounded local callability, safe process
  attribution limit, and explicit lifecycle non-claims.
- [`../mcp-runtime-refresh-interface-and-trial-protocol-2026-07-19.md`](../mcp-runtime-refresh-interface-and-trial-protocol-2026-07-19.md)
  — pinned official refresh semantics, current local stable app-server schema,
  deterministic claim firewall, and staged live-evidence authority gates.
- [`../skill-ablation-batch-01-protocol-2026-07-19.md`](../skill-ablation-batch-01-protocol-2026-07-19.md)
  — exact source-backed payload binding, candidate-suitability correction,
  weak-Agent prompt packets, self-authored exposure gate, and live-task limits.
- [`SKILL-PORTFOLIO-REBASELINE-AND-CLOSEOUT-GATES.md`](SKILL-PORTFOLIO-REBASELINE-AND-CLOSEOUT-GATES.md)
  — CC Switch reuse invariant, Skill ablation and admission sequence, historical
  debt settlement, and program closeout cleanup acceptance.

These anchors are dated inputs, not current host truth. Each PoC must recheck
the relevant host, repository, consumer, and capability version before relying
on them.

## Decision gate after matrix review

After the owner reviews this matrix, choose the smallest next slice from one
scenario row. The next slice should normally be:

1. a read-only native/runtime inventory for the selected host and scenario;
2. targeted official documentation/source verification for the exact scenario
   question or suspected shortfall;
3. only if still needed, targeted maintained external candidate research;
4. a disposable, reversible, falsifiable probe with predeclared acceptance;
5. an evidence record and claim-boundary update before any implementation
   decision.

Matrix approval does not authorize any of those execution steps by itself.

## Cross-cutting unknown-class overlay

The
[unknown-quadrant process-fidelity mapping](HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-PROCESS-FIDELITY-MAPPING-2026-07-27.md)
adds `UNK-KK-01`, `UNK-KU-01`, `UNK-UK-01`, `UNK-UU-01`, and `UNK-LIFE-01`
as a cross-cutting overlay rather than a fourth product lane. Each row binds
host difference, permission boundary, metric, reuse order, fallback, and a
falsifiable conclusion. The overlay keeps discovery separate from action
authority and keeps terminal correctness separate from intermediate process
fidelity. It authorizes no model dispatch, Skill invocation, installation, or
portfolio mutation.

The
[unknown-quadrant attribution-oracle PoC](HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-ATTRIBUTION-ORACLE-POC-EVIDENCE-2026-07-27.md)
is the current deterministic evidence surface for this overlay. Its 22 cases
cover the four unknown classes, isolated-versus-confounded method attribution,
Spark/low route identity, Luna/low diagnostic-only use, and residual-gap
admission. Deterministic fixture matches are not live Agent evidence and do not
count toward the required independent weak-Agent repetitions.

The
[unknown-quadrant packet-overlay PoC](HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-PACKET-OVERLAY-POC-EVIDENCE-2026-07-27.md)
binds each overlay row to one byte-identified zero-model packet. The creative
Unknown Knowns row required a derived packet; that closes a fixture-coverage
gap but is not residual capability evidence. Private-oracle exposure,
hard-standard drift, packet mutation, unverified source identity, and live
authority expansion all fail closed.

The
[parent-oracle seam reuse decision](HUMAN-AI-COLLABORATION-UNKNOWN-QUADRANT-PARENT-ORACLE-SEAM-REUSE-DECISION-2026-07-27.md)
prevents this overlay from becoming another global runtime layer. Existing
builders already support parent-only oracle separation. Any future live
attachment belongs to one exact scenario and arm and must preserve public
projection hash, private oracle hash, leakage rejection, route authority, and
ledger reservation.
