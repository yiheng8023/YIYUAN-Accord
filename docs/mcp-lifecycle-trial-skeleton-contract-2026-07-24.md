# MCP selection-to-lifecycle trial skeleton

Date: 2026-07-24
Status: verified offline binding only; no host actuation
Machine record: [`../registry/mcp-lifecycle-trial-skeleton-contract-2026-07-24.json`](../registry/mcp-lifecycle-trial-skeleton-contract-2026-07-24.json)

## Purpose

This is a small handoff layer between the existing MCP selection decision and
the existing lifecycle evidence scorer. It copies only the facts a future
trial must keep stable: the valid selection digest and status, upstream routing
decision, target host/version/adapter, the exact task/phase/concrete use case/
acceptance surface plus a task-contract digest, exact selected payload
identities and source digests, release request/fallback, and the planned
lifecycle dimensions.

It does not repeat either upstream algorithm. The selection evaluator remains
the authority for whether an MCP is justified and minimal inside its declared
candidate universe. The lifecycle scorer remains the authority for lease,
reference count, task-end exit, duplicate, crash, and resource evidence.

The planned dimension list is a subset declaration, not coverage. The skeleton
explicitly keeps `fullLifecycleCoverageProved=false`; a short trial may bind
only the dimensions it names and cannot be promoted to a full lifecycle claim.

## Hard boundary

The skeleton requires an already-valid, selected offline decision. A no-MCP
decision cannot seed a lifecycle trial. It contains no activation, approval,
acquire, release, exit, process, or resource observation: those fields are
explicitly `unobserved` or empty. All live-host, weak-Agent, activation, and
release counters remain false.

Selection authority is not activation, release, recovery, or cleanup authority.
The release request and fallback are copied as planning constraints only; they
do not prove that a host loaded, unloaded, switched in the same session,
released, or saved resources.

## Falsification cases

The eighteen synthetic cases reject selection/routing digest drift, host or
adapter drift, task/phase/concrete-use-case/acceptance-surface/task-contract
digest drift, unselected-payload injection, release-plan drift, unsupported
dimensions, any prefilled host observation, claim/counter promotion (including
promoting a planned subset to full lifecycle coverage), and skeleton digest
drift. The focused tests also reject an empty or invalid source selection.

## Next gate

Only a separately authorized concrete workload may add parent-observed host
events to this skeleton. `sameSessionSwitching` now has a separately designed
and verified live-host adapter/evaluator contract in
`mcp-same-thread-refresh-evidence-contract-2026-07-24.md`; it is still
offline-only and has not run a host trial. The generic
`evaluate_mcp_task_lifecycle_evidence.py` remains an offline synthetic
dimension contract and cannot validate future parent-observed live host events.
It must not be given real events or treated as a live scorer.
Selection authority remains separate from host activation, release, recovery,
and approval authority. A future resource-benefit claim must include repeated,
bounded task/tool response-latency observations against the same control
workload; a smaller process or tool count is not responsiveness proof.
