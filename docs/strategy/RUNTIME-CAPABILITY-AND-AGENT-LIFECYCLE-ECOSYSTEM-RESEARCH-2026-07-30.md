# Runtime Capability And Agent Lifecycle Ecosystem Research

- Date: 2026-07-30
- Scope: read-only ecosystem research
- Evidence class: official documentation and project-owned primary sources
- Decision status: bounded research finding, not implementation authority

## Executive finding

Within the official and project-owned primary sources reviewed for this
research, no single mature, turnkey implementation was documented as covering
all of the following at once:

1. dynamically enabling and disabling MCP servers, plugins, or tools according
   to task intent and execution phase;
2. creating, pausing, resuming, scaling, and reclaiming Agents or threads
   according to dependencies and load;
3. enforcing host-native permission and account boundaries;
4. maintaining shared leases or reference counts across concurrent consumers;
5. recovering from failure and reconciling or compensating external effects;
6. exposing lifecycle state, resource use, traces, and cleanup debt;
7. adapting the same control semantics to both Codex and Claude Code.

This is a bounded finding, not proof that no such implementation exists
anywhere. The ecosystem contains several strong and reusable components, but
the reviewed evidence does not establish a mature, integrated cross-host
substitute for the whole target.

The residual opportunity is therefore narrower than “build an orchestration
platform from scratch.” A plausible self-authored component would be a thin,
host-aware lifecycle coordinator that reuses established gateway, session,
lease, durable-execution, permission, and observability primitives. Its
distinct responsibility would be:

```text
semantic desired state
-> host and gateway actuation
-> lease and ownership accounting
-> observed actual state
-> reconciliation, cleanup, and bounded recovery
```

## Research question and evaluation dimensions

The central question is whether a mature official or reviewed third-party
solution can be reused directly as the runtime counterpart of the project's
portable intent and capability-decision chain.

The evaluation separates eight dimensions that are often conflated:

- task- or phase-scoped MCP/tool lifecycle;
- dependency- or load-driven Agent/thread lifecycle;
- permissions and isolation;
- leases, reference counts, and stale-resource reclamation;
- retries, durable recovery, rollback, or compensation;
- observability and lifecycle evidence;
- Codex host integration;
- Claude Code host integration.

Legend used below:

- `Strong`: directly documented and materially aligned.
- `Partial`: documented adjacent capability with a narrower lifecycle or
  different control object.
- `Experimental`: documented but explicitly experimental, preview, beta, or
  otherwise unsuitable as a proven reliability foundation.
- `Custom`: achievable only through application-specific integration.
- `Absent`: not found in the reviewed documented scope.

Maturity labels describe the reviewed primary-source posture. They are not an
independent reliability certification.

## Coverage and maturity matrix

| Candidate | Maturity posture | MCP/tool lifecycle | Agent/thread lifecycle | Permission boundary | Lease/refcount | Recovery/rollback | Observability | Codex + Claude adaptation | Host intrusion | Result |
|---|---|---|---|---|---|---|---|---|---|---|
| Codex App Server | Official host control surface | Partial: static enable/deny lists, reload, status | Partial: start/interrupt/archive/delete/unsubscribe and delayed unload | Strong host-native approvals/config | Absent for shared capability ownership | Partial: interruption and persisted thread operations, not general compensation | Strong protocol events and status APIs | Codex only | Low inside Codex; unavailable as Claude control plane | Essential Codex adapter, not an integrated scheduler |
| Claude Code | Official host control surface | Strong at a subagent boundary: inline MCP starts with the subagent and disconnects when it finishes; plugin reload can connect/disconnect | Partial: foreground/background subagents and lifecycle hooks, not a load scheduler | Strong per-subagent permission modes and host prompts | Absent as a cross-session shared lease model | Partial: task lifecycle controls, not general rollback | Partial: hooks, status, session tooling | Claude only | Low inside Claude; unavailable as Codex control plane | Strongest reviewed host-native scoped MCP primitive, still host-specific |
| MCP specification and official Registry | Official standard and catalog | Partial: connection lifecycle, capability negotiation, list-change events | Absent | Partial: standardized HTTP authorization | Absent | Absent beyond connection shutdown semantics | Partial protocol events | Protocol portable | Low | Interoperability plumbing, not a lifecycle coordinator |
| Docker MCP Gateway | Official Docker gateway; operational gateway, Toolkit remains beta | Strong: gateway can start an isolated server container when a tool is requested and route the call | Absent for host Agent/thread lifecycle | Strong secrets, OAuth, isolation, restrictions | Partial internal server lifecycle; no documented cross-thread semantic refcount | Partial container/process recovery, not external-effect compensation | Strong logging and call tracing | Client-facing MCP compatibility, not internal Codex/Claude thread control | Medium: adds Docker gateway/runtime | Closest reusable MCP-side actuator |
| Docker Dynamic MCP | Explicitly experimental and early-development | Strong conceptually: session-scoped find/add/remove/config/execute | Absent | Partial through Docker gateway policy | Absent | Partial session cleanup | Partial | Client-facing only | Medium | Valuable PoC/reference, not a mature foundation |
| ToolHive | Production-oriented and operationally substantial by project-owned sources; not independently benchmarked here | Strong runtime/gateway management and tool filtering | Partial workflow facilities, not native Codex/Claude thread lifecycle | Strong isolation, identity, policy, RBAC-oriented controls | Partial lifecycle management; no documented cross-host semantic refcount | Partial | Strong OpenTelemetry/Prometheus posture | Supports multiple MCP clients, but does not control their internal thread schedulers | Medium to high: deploys a control plane/runtime | Strong secure MCP control-plane component, not a complete substitute |
| Microsoft MCP Gateway | Project-owned gateway; core gateway substantial, Agents and Sessions explicitly preview | Strong server registration, routing, deployment, update, and deletion | Experimental preview Agents and Sessions subsystem | Strong Kubernetes/RBAC/auth posture | Partial session-aware routing; no proven target refcount model | Partial Kubernetes/runtime recovery | Strong telemetry posture | MCP client compatibility only | High: Kubernetes-oriented control plane | Strong enterprise gateway component; preview Agent layer is not sufficient |
| MCPJungle | Community operational gateway; maturity not independently established | Strong unified endpoint, registration, global enable/disable, tool groups | Absent | Strong ACL/auth features | Absent | Partial graceful shutdown | Strong OpenTelemetry metrics | MCP client-facing, not host-internal | Medium | Useful aggregation and policy component |
| MetaMCP | Active community aggregator/gateway; reliability not established here | Strong aggregation, middleware, routing, and management | Absent | Strong auth, API keys, OAuth, multi-tenancy, rate limits | Absent | Partial middleware-level failure handling | Strong logging posture | MCP client-facing, not host-internal | Medium | Useful middleware component, not a lifecycle scheduler |
| LangGraph / LangChain Agent Server | Production-oriented durable graph/runtime services; exact deployment maturity depends on product surface | Strong session primitives: stateless per-call cleanup or explicit persistent MCP sessions | Strong for graph workers, persisted threads/runs, queues, checkpoints, and load scaling | Strong interceptors and service controls | Strong worker run leases; Custom for shared MCP ownership | Strong durable resume/retry; external-effect compensation remains application-defined | Strong LangSmith traces | Custom wrappers required for Codex/Claude native tasks | High if adopted as the main runtime | Strong durable execution and lease substrate, not a host-neutral drop-in |
| Microsoft AutoGen | Substantial framework; distributed runtime and some pause/resume paths remain experimental | Strong explicit `McpWorkbench` start/stop/context management | Strong lazy Agent creation in Core runtime; several lifecycle boundaries remain experimental or application-owned | Strong intervention/approval extension points | Absent as target shared-resource refcount | Partial state save/load and cancellation; no general rollback | Strong OpenTelemetry support | Custom wrappers required | High if replacing native host execution; medium as a sidecar | Closest reviewed Agent-runtime reference, not a complete cross-host answer |
| CrewAI | Active framework with documented MCP adapter lifecycle | Strong at crew kickoff: lazy adapter start and after-kickoff stop | Partial Crews/Flows execution and persistence | Partial framework/RBAC surfaces | Absent | Partial retries/persistence; no general compensation guarantee | Strong commercial/platform observability surfaces | Custom wrappers required | High as runtime replacement; medium as reference adapter | Important proof that automatic scoped MCP cleanup already exists |
| Semantic Kernel | Mature SDK family, but Agent Orchestration is experimental/prerelease | Partial: explicit MCP connect/close and contextual function exposure | Experimental orchestration runtime | Strong filters and approval patterns | Absent | Partial; documented cancellation limits | Strong OpenTelemetry support | Custom wrappers required | High as orchestration runtime; medium as SDK component | Strong tool-exposure and policy component, not lifecycle closure |
| Temporal | Mature durable workflow platform | Custom MCP activities/workers required | Strong durable worker/task lifecycle, queues, retries, signals, and timers | Strong platform security controls | Partial task ownership and queues; Custom for MCP refcount | Strong durable replay/retry and Saga-style compensation, with application-defined compensators | Strong production observability | Custom adapters required | High | Mature durable control-plane substrate, not an Agent/MCP product solution |
| Prefect | Mature workflow orchestrator | Custom | Strong work-pool, queue, deployment, pause/resume, and dynamic infrastructure controls | Strong platform RBAC/ACL surfaces | Strong timed concurrency leases with renewal and expiry | Strong retries and transaction rollback hooks, but effects remain application-defined | Strong events and logs | Custom adapters required | High | Best reviewed reference for lease semantics, not a direct substitute |
| Dagster | Mature data orchestrator | Custom | Strong job/step concurrency and worker monitoring in its domain | Strong deployment controls | Strong concurrency slots and stale-slot reclamation in its domain | Strong retries/run recovery in supported deployments; not general external rollback | Strong event log and UI | Custom adapters required | High | Useful stale-resource and monitor reference, not an Agent/MCP solution |

## Host-native findings

### Codex and App Server

Codex exposes useful control-plane primitives rather than a documented semantic
lifecycle scheduler:

- MCP servers can be enabled or disabled statically and their tools narrowed by
  allow and deny lists.
- MCP status, tools, resources, authentication state, startup progress, and
  configuration reload are observable through App Server APIs.
- App Server can atomically update user configuration and reload MCP state for
  loaded threads.
- Threads and turns support start, interrupt, archive, delete, subscribe, and
  unsubscribe operations. A last-unsubscribed inactive thread can unload after
  a grace period.
- Stable multi-agent tools can spawn, message, resume, wait for, and close
  subagents, subject to configured concurrency.

These APIs are suitable actuators and evidence surfaces. They do not document
task-semantic MCP switching, dependency-aware subagent scheduling, shared
capability ownership, or a lease/refcount scheme. Mutating shared user
configuration to approximate per-thread switching would require conflict
control and reconciliation outside App Server.

### Claude Code

Claude Code provides a notably stronger scoped primitive: an MCP server defined
inline for a subagent connects when that subagent starts and disconnects when
it finishes. A named reference can instead share the parent session connection.
Per-subagent permissions and foreground/background execution further constrain
the lifecycle.

This proves that host-native automatic MCP cleanup is possible and already
exists for one useful boundary. It does not establish arbitrary phase changes
inside a task, shared leases across concurrent subagents, load-based scaling, or
cross-host coordination. Claude hooks can observe and gate lifecycle events,
but a hook is not by itself a durable authority, resource ledger, or portable
scheduler.

## MCP gateways and registries

The MCP specification standardizes initialization, capability negotiation,
operation, shutdown, authorization, and change notification. The official
Registry provides discovery, publishing, provenance, and ownership metadata.
Neither defines the project-level semantics for deciding *when* a capability
should exist, *who* owns it, or *when* it is safe to reclaim.

The gateway family supplies much of the missing actuation and security layer:

- Docker MCP Gateway can start isolated containers on tool demand, inject
  credentials and restrictions, route calls, and trace them.
- Docker Dynamic MCP demonstrates session-scoped discovery and add/remove, but
  is explicitly experimental.
- ToolHive adds runtime isolation, identity-aware policy, tool filtering,
  telemetry, registry, and Kubernetes-oriented operation.
- Microsoft MCP Gateway adds session-aware routing, Kubernetes deployment
  management, RBAC, and telemetry, while its Agents and Sessions subsystem is
  explicitly preview.
- MCPJungle and MetaMCP provide aggregation, routing, tool grouping, access
  controls, and observability at varying community maturity levels.

These can reduce how much MCP process, transport, credential, and telemetry
machinery the project must own. None of the reviewed gateway evidence shows
control over Codex and Claude Code's internal Agent/thread lifecycles or a
portable semantic desired-state protocol spanning both hosts.

## Agent runtimes and workflow orchestrators

### LangGraph / LangChain

LangChain's MCP client offers two useful lifecycle models:

- stateless-by-default calls create a session for a tool call and clean it up
  afterward;
- stateful sessions can be held explicitly when continuity is needed.

LangGraph and Agent Server add durable execution, checkpoint/resume,
interrupts, dynamic workers, persisted threads/runs, queues, worker leases, and
load-oriented scaling. This is a powerful execution substrate, but its workers
and threads are LangGraph objects. Treating Codex and Claude native tasks as
those objects requires host adapters and may amount to adopting a new primary
runtime.

### AutoGen

AutoGen Core can lazily create an Agent on first message and manage runtime
start, stop, idle shutdown, and distributed execution. `McpWorkbench` supplies
explicit and context-managed MCP cleanup, while intervention handlers and
OpenTelemetry cover policy and evidence.

The important boundary is that several distributed and pause/resume features
remain experimental or application-owned. AgentChat objects are not
automatically equivalent to Core runtime actors, and pause or cancellation does
not guarantee consistent resource recovery without application design.

### CrewAI

CrewAI is evidence against the overbroad claim that no third party automatically
opens and closes MCP resources. Its annotated crew path can lazily start an MCP
adapter when tools are obtained and stop it through an internal after-kickoff
hook.

That lifecycle is tied to a crew kickoff, generally hydrates declared tools,
and does not supply arbitrary semantic phases, shared leases, load-driven host
thread recovery, or Codex/Claude native control. It is a reusable pattern and
PoC comparator, not a system-level substitute.

### Semantic Kernel

Semantic Kernel provides explicit MCP plugin connect/close, contextual function
selection that limits what is advertised to a model, function filters for
approval and policy, and OpenTelemetry.

Contextual exposure reduction must not be misreported as server process
shutdown. Its Agent Orchestration runtime remains experimental/prerelease, and
documented cancellation behavior does not provide full execution interruption
or resource reconciliation.

### Temporal, Prefect, and Dagster

These mature orchestrators solve adjacent control-plane problems:

- Temporal supplies durable replay, task queues, retries, signals, timers, and
  application-defined Saga compensation.
- Prefect supplies work pools, dynamic infrastructure, event automation, and
  timed concurrency leases with renewal and expiry.
- Dagster supplies concurrency slots, stale-slot reclamation, worker/run
  monitoring, retries, and event-based observability.

They do not understand MCP servers, Skills, Agent turns, host-native approval
dialogs, or Codex/Claude thread semantics. Using one would require wrapping
host actions as workflow activities and defining every ownership,
authorization, compensation, and reconciliation rule. They are reference
semantics or durable substrates, not ready-to-use answers.

## Reusable components versus residual gaps

### Components that should be reused or emulated

1. **Host actuation**
   - Codex App Server thread, turn, MCP status, reload, and config APIs.
   - Claude inline subagent MCP lifecycle and per-subagent permissions.

2. **MCP runtime isolation and routing**
   - Docker MCP Gateway for start-on-demand isolated server execution.
   - ToolHive or Microsoft MCP Gateway patterns where stronger identity,
     policy, registry, or Kubernetes operation is justified.

3. **Session lifecycle**
   - LangChain stateless per-call cleanup and explicit persistent sessions.
   - AutoGen `McpWorkbench` context management.
   - CrewAI kickoff-scoped lazy start and cleanup.

4. **Lease and reclamation semantics**
   - Prefect timed leases, renewal, expiry, strict behavior, and slot release.
   - Dagster concurrency slots and stale-slot cleanup.

5. **Durability and recovery**
   - LangGraph checkpoints, interrupts, queues, and run leases.
   - Temporal durable workflows, retries, and explicit compensation.

6. **Policy and evidence**
   - Host-native approval dialogs as the enforcement boundary.
   - Gateway identity, isolation, ACL/RBAC, tool filtering, and tracing.
   - OpenTelemetry-compatible event and state reporting.

### Residual gaps not closed by one reviewed component

- translating user intent and task phase into an explicit capability desired
  state;
- deciding whether one capability instance is private, shareable, or forbidden
  across threads;
- reference counting or leasing a shared MCP capability across Codex and Claude
  consumers;
- reconciling shared config mutations and preventing one thread from disabling
  another thread's dependency;
- mapping host-specific thread and subagent states into one portable lifecycle
  model without pretending the hosts are identical;
- distinguishing schema deferral, tool exposure, connection establishment,
  process existence, authentication, invocation, and useful behavior;
- reclaiming resources after cancellation, crash, context compression, host
  restart, or abandoned work;
- verifying actual route, permission, cleanup, and rollback outcomes;
- preserving repository-anchored continuity without treating chat history,
  handoffs, installed counts, or static configuration as live runtime truth.

### 2026-07-31 resource-pressure hypothesis calibration

The user's observation that long-running and concurrent Agent use can lead to
system slowdown or application failure identifies a material product risk.
The proposed "zombie thread" cause is retained as a hypothesis, not yet a
single proved runtime mechanism. The observable candidates are:

- growing conversation or tool-result context;
- an active turn or loaded thread that did not quiesce;
- a persisted thread that may or may not still hold live resources;
- an unfinished or abandoned subagent/worker;
- an MCP connection, subscription, server, or child process that remained
  live;
- host cache, rendering, indexing, or other application-owned state.

The next same-workload profile must correlate host-visible lifecycle events
with time-series CPU, memory, process/handle or connection inventory, release
latency, and post-completion/cancellation/archive/unsubscribe/restart state.
Repeated and concurrent arms plus idle controls are required. Persisted thread
count alone cannot prove a leak, and a task-complete event cannot prove resource
release.

## Implication for the project chain

The findings do not contradict an `AGENTS.md -> Skills -> Hook` chain, but they
require a sharper separation of responsibilities.

- `AGENTS.md` should remain the portable policy baseline, negative boundaries,
  authority rules, and capability-selection order. It is not a daemon,
  scheduler, or live resource ledger.
- `intent-contract`, `capability-router`, and `closure-contract` can produce
  semantic decisions and desired state. They are not proof that a resource was
  started, stopped, authorized, reclaimed, or useful.
- A Hook can be an optional event source, observer, or enforcement bridge where
  a host exposes reliable lifecycle events. It must not be the sole authority
  or the only recovery path, and it cannot be assumed portable.
- Host adapters should translate desired state into Codex App Server, Claude
  subagent/MCP, and gateway operations.
- A minimal lifecycle ledger should track ownership, leases, observed state,
  expiry, and cleanup debt.
- Verification and reconciliation should compare desired state with live host
  and gateway state before making completion claims.

The refined chain is:

```text
AGENTS portable baseline
-> Skills produce bounded semantic desired state
-> runtime event adapter (Hook when suitable, host API otherwise)
-> lease and ownership ledger
-> Codex / Claude / MCP-gateway actuators
-> live observation, reconciliation, cleanup, and evidence
```

If a durable orchestrator later becomes necessary, it should sit beneath this
portable semantic contract rather than redefine it. The first PoC should test a
small state machine and lease ledger before adopting Temporal, Prefect,
LangGraph Agent Server, or another heavyweight runtime.

## Recommended falsifiable PoC sequence

This research does not authorize implementation, installation, or trust-boundary
changes. If implementation is separately authorized, the smallest useful
sequence is:

1. model one capability with explicit states: unavailable, stopped, starting,
   healthy, leased, draining, failed, and cleanup-debt;
2. implement two host adapters only: Codex status/reload/thread observation and
   Claude inline subagent MCP observation;
3. use an existing gateway or a simulated actuator rather than writing an MCP
   process supervisor;
4. borrow timed-lease semantics from Prefect and stale-resource reconciliation
   from Dagster;
5. test concurrent consumers, cancellation, startup failure, authentication
   failure, host restart, lease expiry, stale observations, and conflicting
   desired states;
6. prove that native approval boundaries remain authoritative;
7. compare the thin coordinator against direct host-native operation and
   CrewAI/LangChain session cleanup before expanding scope.

The PoC should be rejected or reduced if host APIs cannot expose enough
observed state, if configuration changes cannot be isolated safely, if the
coordinator becomes a second permission system, or if lifecycle overhead
exceeds the resource savings it is intended to create.

## Primary sources

### OpenAI Codex

- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- [Codex App Server](https://learn.chatgpt.com/docs/app-server)

### Claude Code

- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code hooks guide](https://code.claude.com/docs/en/hooks-guide)
- [Claude Code features overview](https://code.claude.com/docs/en/features-overview)

### MCP and gateways

- [MCP lifecycle specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle)
- [MCP authorization specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [MCP tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Official MCP Registry](https://github.com/modelcontextprotocol/registry)
- [Docker Dynamic MCP](https://docs.docker.com/ai/mcp-catalog-and-toolkit/dynamic-mcp/)
- [Docker MCP Gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/)
- [Docker MCP Gateway repository](https://github.com/docker/mcp-gateway)
- [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/)
- [ToolHive repository](https://github.com/stacklok/toolhive)
- [ToolHive documentation](https://docs.stacklok.com/)
- [Microsoft MCP Gateway](https://microsoft.github.io/mcp-gateway/)
- [MCPJungle repository](https://github.com/mcpjungle/MCPJungle)
- [MetaMCP repository](https://github.com/metatool-ai/metamcp)

### Agent runtimes and orchestrators

- [LangChain MCP adapter](https://docs.langchain.com/oss/python/langchain/mcp)
- [LangGraph workflows and dynamic workers](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangGraph persistence](https://docs.langchain.com/oss/javascript/langgraph/persistence)
- [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangSmith Agent Server](https://docs.langchain.com/langsmith/agent-server)
- [LangSmith Agent Server scaling](https://docs.langchain.com/langsmith/agent-server-scale)
- [AutoGen MCP Workbench](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/components/workbench.html)
- [AutoGen Agent Runtime](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/agent-and-agent-runtime.html)
- [AutoGen Team API](https://microsoft.github.io/autogen/stable/reference/python/autogen_agentchat.teams.html)
- [AutoGen distributed runtime](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/framework/distributed-agent-runtime.html)
- [AutoGen tracing](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tracing.html)
- [CrewAI annotations and MCP lifecycle](https://docs.crewai.com/learn/using-annotations)
- [CrewAI tools and MCP adapters](https://github.com/crewAIInc/crewAI-tools)
- [Semantic Kernel MCP plugins](https://learn.microsoft.com/en-us/semantic-kernel/concepts/plugins/adding-mcp-plugins)
- [Semantic Kernel Agent Orchestration](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/)
- [Semantic Kernel orchestration advanced topics](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/advanced-topics)
- [Semantic Kernel contextual function selection](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-contextual-function-selection)
- [Temporal Task Queues](https://docs.temporal.io/task-queue)
- [Temporal retry policies](https://docs.temporal.io/encyclopedia/retry-policies)
- [Temporal official TypeScript samples](https://github.com/temporalio/samples-typescript)
- [Prefect automations](https://docs.prefect.io/v3/concepts/automations)
- [Prefect global concurrency limits and leases](https://docs.prefect.io/v3/concepts/global-concurrency-limits)
- [Prefect deployments](https://docs.prefect.io/v3/concepts/deployments)
- [Dagster concurrency](https://docs.dagster.io/guides/operate/managing-concurrency)
- [Dagster run monitoring and stale-slot cleanup](https://docs.dagster.io/deployment/execution/run-monitoring)
