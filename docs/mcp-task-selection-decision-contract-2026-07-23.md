# MCP task-selection and release-decision contract

Date: 2026-07-23
Status: verified offline selection contract; no host actuation
Machine record: [`../registry/mcp-task-selection-decision-contract-2026-07-23.json`](../registry/mcp-task-selection-decision-contract-2026-07-23.json)

## Purpose

The MCP lifecycle contract describes the evidence needed after a lifecycle is
observed. This separate decision contract addresses the upstream question:
which MCP, if any, is the smallest justified set for one bound task or phase,
and what release request and fallback must be prepared?

It is not a second capability router. It consumes an upstream decision that the
MCP capability class may be evaluated, then refines only the declared MCP
candidate subset. It performs no discovery, installation, enablement, call,
process inspection, release, or configuration mutation.

## Decision boundary

A valid packet binds:

- the task, phase, concrete use case, and acceptance surface;
- the exact target host/version/adapter and upstream routing decision digest;
- a native/current-capability assessment with evidence class, reference, digest,
  and stable residual capability IDs;
- each candidate's identity, source revision and digest, review state and
  evidence, capability IDs, declared surface-area score, data boundary, account
  boundary, authority boundary, cost boundary, and maintenance state;
- a computed minimal selected set and an explicit reason for every selected or
  rejected candidate;
- activation state and authority kept separate from selection;
- task-or-phase-only activation as the default scope, with every unselected
  candidate remaining inactive; persistent activation exits this default
  contract and requires separate evidence and authorization;
- a task-or-phase-end release request, observed host lifecycle capability, and
  bounded fallback.

If native or current capabilities are sufficient, the correct set is empty. If
there is a residual gap, the selected set must cover every stable capability ID.
Inside the declared admitted candidate universe, the evaluator minimizes
candidate count first and declared surface-area score second. A redundant or
larger set fails. This proves only deterministic minimality inside the supplied
candidate/evidence declarations; it does not prove that the universe is
complete or that its review and scores are true.

The user's report that many simultaneously open MCPs can make the host sluggish
is treated as a bounded performance concern, not a universal benchmark result.
This contract therefore fails closed when a selected candidate is silently
promoted to persistent activation or when an unselected candidate is allowed to
remain active. Actual startup latency, interaction latency, memory, process, or
resource benefit still requires repeated host-bound measurement.

## Release and approval separation

Planning or requesting release does not prove release. A status endpoint,
refresh response, config edit, or policy field also does not prove unload,
process exit, lease release, or resource improvement. Host approval remains a
host control and cannot be credited to this contract.

The fallback may be a startup/new-thread profile or documented native idle
timeout, but it must match a lifecycle state and evidence reference bound to the
exact host, version, and adapter version. A same-session observed claim requires
`observed-single-host` evidence; static evidence cannot be relabeled as an
observed lifecycle or fallback.
An unknown lifecycle state permits only a startup/new-thread fallback explicitly
marked `planned-unproved`. `none-selected` is valid only when no MCP is selected.

## Offline evidence

Twenty-seven synthetic fixtures cover the minimal-selection and no-MCP paths plus
unbound tasks, missing acceptance, absent native assessment, selection despite
native sufficiency, unreviewed or placeholder candidates, redundant or larger
sets, uncovered capability IDs, host/lifecycle/fallback mismatches,
selection/actuation conflation, persistent-by-default activation, unselected
candidate activation, approval credit, claim promotion, and packet digest
drift.

The declared candidate universe is capped at 32 entries before set-cover
minimality is evaluated. This bounds offline computation; it does not prove the
candidate universe is complete.

Every fixture has `countsAsLiveHostProof=false`,
`countsAsWeakAgentAcceptance=false`, and
`countsAsActivationOrReleaseProof=false`.

## Falsifiable next gate

A live trial must bind one separately authorized concrete workload and the
exact selected identities to parent-observed activation and release evidence.
Selection, approval, actuation, exact process identity, task correctness, and
resource results remain separate evidence axes.
