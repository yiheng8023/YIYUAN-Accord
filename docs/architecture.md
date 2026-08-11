# Architecture

Agent Autonomy Harness has one deep portable product seam and replaceable
execution edges.

```text
real task + authority + observed state
                  |
                  v
        portable Harness core
 intent -> route -> lifecycle -> evidence -> handoff -> cleanup
                  |
          desired operations
                  v
         host/manager adapters
                  |
          observed receipts
                  v
       acceptance and replanning
```

## 1. Product-control authority

`product/constitution.json`, `product/program.json`, and
`product/acceptance.json` form one authority set. The constitution fixes the
purpose and invariants. The program chooses one causal increment. Acceptance
defines measurable outcomes and mandatory guardrails. The product-control
kernel rejects disagreement among them.

This layer prevents a research record, candidate inventory, test suite, or
historical verifier from silently becoming the scheduler.

## 2. Portable Harness core

The target core exposes one conceptual transaction:

```text
observe -> bind intent and authority -> choose route -> actuate through adapter
-> observe effects -> verify -> continue or release -> emit receipt
```

The portable contract owns outcome semantics, authority requirements,
unsupported states, evidence shape, fallback, recovery, and cleanup. It does
not own host-specific commands, databases, UI, or permission dialogs.

The current implemented slice is product control: finite plan-to-acceptance
mapping, identity isolation, real-task route evidence, and cleanup evidence.
Runtime actuation remains a later v0.1 outcome and must not be inferred from
the control kernel.

## 3. Lifecycle plane

Lifecycle state distinguishes acquisition, installation, enablement, exposure,
invocation, instruction delivery, behavior, value, rollback, release, and
cleanup. One state never proves the next.

Each live component has one lifecycle owner. A manager, host, or adapter may
own operations for its scope; it does not become portable product authority.

## 4. Adapters

Adapters translate only unavoidable host details:

- available observation and actuation surfaces;
- authorization and permission mechanisms;
- event, Hook, command, process, and filesystem shapes;
- manager transaction and rollback behavior;
- unsupported-state degradation.

An adapter must report unavailable observations or operations. It must not
simulate support or generalize one host's behavior into a cross-host claim.

## 5. Evidence and acceptance

Evidence records bind source, time, operation, result, authority, and claim
limits. Deterministic checks verify structure and invariants. Real tasks and
host observations support behavior and value claims. Accountable human review
owns consequential acceptance.

Product outcomes O1-O5 are separate from guardrails G1-G4. Passing every
guardrail with zero product outcomes is safe non-delivery, not progress.

## 6. Legacy boundary

The predecessor evidence corpus is absent from the current Git index and may be
consulted through an exact Git revision. A repository-local ignored `legacy/`
quarantine may remain when host policy blocks physical deletion; it is not a
durable provenance authority and is excluded from product authority, scanning,
planning, acceptance, runtime, release, and the public verification seam.
