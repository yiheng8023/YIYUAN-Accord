# Architecture

Agent Autonomy Harness has one Agent-neutral product contract, one small
control seam, and replaceable host edges.

```text
user goal + domain facts + bounded authority
                    |
                    v
          Agent-neutral Harness loop
 intent -> route -> act -> observe -> recover -> verify -> clean -> continue
                    |
             desired operations
                    v
       native host / manager adapters
                    |
          source-bound observations
                    v
       evaluation, acceptance, replan
```

## 1. Current product authority

`product/constitution.json`, `product/program.json`, and
`product/acceptance.json` are the machine authority. `harness/control.py`
verifies their identity, mapping, authority, evidence-admission, and
process-loss invariants. The verifier derives release identities instead of
hard-coding one release.

Historical release evidence remains in Git and `product/evidence`, but it is
not scanned as current authority. The accepted v0.1 verifier and event-specific
validators remain reproducible at revision `be498f9`; carrying their one-off
logic into every later release would turn evidence history into product debt.

Supporting strategy, README, architecture, and continuation documents explain
the current contract but do not override the three machine-authority files.

## 2. Portable Harness loop

The product target is one conceptual transaction:

```text
observe -> bind intent and authority -> choose route -> preview and actuate
-> observe effects -> recover when needed -> verify -> release and clean
-> emit a bounded receipt or continue
```

The portable layer owns semantics, not host commands. It defines required
authority, unsupported states, lifecycle ownership, evidence shape, outcome
floors, fallback, recovery, cleanup, and process-loss stop rules.

The current implemented slice is the v0.2 historical-event-neutral
product-control kernel. O1-O5 are deliberately planned and false. A repository-authored JSON
file cannot promote them: every verified outcome requires a code-owned
validator added with the real slice that needs it.

## 3. Capability and lifecycle plane

Capabilities include native functions, official runtime capabilities, reviewed
external Skills and tools, compositions, self-authored components, Apps,
Plugins, MCP servers, and optional Hooks. User-installed breadth is legitimate;
the Harness must arbitrate it and expose only the minimal task-relevant subset.

Acquisition, installation, enablement, exposure, invocation, instruction
delivery, behavior, value, projection, rollback, cleanup, acceptance, release,
and publication are distinct states. One never proves the next. One live
component has one lifecycle owner.

Healthy installed and authorized capabilities may be used proactively for a
bound task. Installation, enablement, account connection, new data or trust,
meaningful cost, consumer mutation, publication, and release remain separate
authority transitions.

## 4. Host and manager adapters

Adapters translate only unavoidable host facts:

- available observation and actuation surfaces;
- native authorization and permission mechanisms;
- event, Hook, command, process, and filesystem shapes;
- manager preview, transaction, rollback, and cleanup behavior;
- unsupported-state degradation.

`codex-user-config` is a Codex consumer adapter and projection. CC Switch is a
separately governed capability manager. Neither is Agent-neutral product
authority. A second host must implement the same portable semantics through
its own thin adapter; a Codex projection cannot prove cross-Agent behavior.

## 5. Evidence and acceptance

Evidence binds source, time, authority, operation, result, verification, and
claim limits. Deterministic validation proves structure and invariants. Real
tasks and observations support behavior and value. Accountable human judgment
owns consequential acceptance.

The 15 partial criteria, six evidence clusters, 14 lifecycle slices, 12
evaluation dimensions, and 13 Harness scenarios are sampling and risk
coordinates. Membership is not coverage, a fixture is not behavior, and a
green test is not user value.

## 6. Process-loss control

Every causal increment declares a correction budget, a guardrail-only-work
budget, a material user tool-orchestration budget, hard authority stops, and
exact repository cleanup paths. At most one explicit guardrail-only reset may
precede real outcome work; it counts as zero product progress. Actual process
loss is measured by O1/O2 receipts, not inferred from a budget declaration.
