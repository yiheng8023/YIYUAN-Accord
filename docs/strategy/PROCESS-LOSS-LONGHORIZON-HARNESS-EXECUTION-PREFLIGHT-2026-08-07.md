# LongHorizon-Harness Execution Preflight

Date: 2026-08-07

Status: verified synthetic fail-closed preflight; no live execution

Governed evidence:
[`process-loss-longhorizon-harness-execution-preflight-2026-08-07.json`](../../registry/process-loss-longhorizon-harness-execution-preflight-2026-08-07.json)

## Decision

The preflight mechanism rejects twenty-five single-boundary mutations across
candidate identity, disposable workspace isolation, host-owned permissions,
parent-derived receipts, mutation and rollback, recovery semantics, external
access, verification, and stop rules. A complete synthetic request is eligible
only as a preflight mechanism and remains non-executing.

This gate does not execute LongHorizon-Harness, acquire its source, install its
package, implement an adapter, call a model, connect an account, or touch a
consumer workspace. Synthetic eligibility is never execution authority.

## Frozen candidate boundary

The only candidate identity accepted by this preflight is public repository
revision `b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58` together with the governed
twelve-interface mapping. A mutable branch name, later tag, different commit,
or an unbound fork fails closed.

## Disposable workspace floor

Any future live comparison must target a newly created operating-system
temporary root. It must not point to the Harness repository, another user
project, an Agent Skill root, a Plugin/App/MCP/Hook root, consumer
configuration, credentials, sessions, or caches.

Before construction, the absolute resolved path must be checked. Reparse-point
or symbolic-link escape is forbidden. Pre-state and post-state snapshots are
mandatory. Existing user workspaces are ineligible even when the task is
described as harmless.

## Host-owned permission floor

Native approval and sandbox enforcement must remain active. Dangerous bypass
flags are forbidden.

- Manager may read the bounded contract and receipts but may not write the
  workspace, spawn processes, or use the network.
- Executor may write and execute only inside the disposable workspace; network
  access and outside-workspace writes remain forbidden in this preflight.
- Auditor must have a preventive read-only workspace profile with no process or
  network access. Post-hoc mutation detection is not sufficient.

This deliberately rejects the default dangerous Claude and Codex routes found
in the frozen source. A future safe route must be supplied by a separately
reviewed host-specific adapter or upstream change; the preflight does not
invent or authorize that implementation.

## Parent-derived receipt floor

A future comparison must bind thread and turn identity, the effective host
route, and parent-computed hashes for the input artifact, output artifact, and
stage contract. A requested route is not effective-route evidence. Unknown
receipt fields fail closed, and Agent self-report cannot substitute for the
parent-owned receipt.

## Mutation and rollback floor

A transaction journal, pre/post digests, mutation disposition, restoration
requirement, and rollback receipt are mandatory. Any mutation outside the
disposable workspace halts the run. Detected auditor mutation must be restored,
not merely reported and ignored. Rollback failure preserves evidence and
requires human intervention rather than continuing.

This is a contract for future implementation. It does not prove that the
candidate or a Harness adapter currently provides transactions or rollback.

## Recovery claim floor

Within-process audit repair and process-crash resume are distinct states. A
crash-resume claim requires reloaded persisted state, a source run identifier,
a checkpoint digest, and a replay or continuation receipt. Unknown resume state
is blocked without substitution. Persisted files or a later fresh run cannot by
themselves support a resume claim.

## Fail-closed matrix

The deterministic evaluator covers twenty-five mutations:

- synthetic versus real authority and exact candidate revision;
- workspace class, existing workspace use, path resolution, exclusions,
  reparse escape, and pre/post snapshots;
- native approval bypass, sandbox bypass, dangerous flags, and each role
  profile;
- effective route and parent-derived artifact receipts;
- transaction journal, outside-workspace mutation, and rollback proof;
- within-process versus crash recovery and crash-resume evidence;
- external/model boundary, verification surface, and stop rules.

Every mutation returns `blocked` while execution, installation, and model
dispatch remain false.

## Current boundary and next state transition

The preflight proves only a synthetic fail-closed mechanism. It does not prove
live permission enforcement, disposable workspace construction, rollback,
effective route receipts, crash recovery, behavior, value, portability,
residual gap, or production readiness. The canonical acceptance inventory
remains 46 verified, 15 partial, and zero planned.

A real Claude task is still not required for this zero-model result. However,
the next state transition crosses a new trust boundary: candidate acquisition,
installation, safe adapter or upstream implementation, model dispatch, and a
real task comparison each need their own bound authority and verification
surface. The mainline must pause before those actions rather than treating this
synthetic PASS as permission.
