# Experiment Contract Reuse Map — 2026-07-23

## Decision

Overlapping experiment names do not create independent evidence. Reuse the
strongest existing packet, private oracle, and scorer, then add only the missing
parent-host envelope. Do not count the same Context or Git observation twice.

## Fresh-session source-backed handoff

`HND-FRESH-01` is a live intervention view of
`ABL-CTX-HANDOFF-01`, not a new independent scenario. The existing Batch 01
contract already separates the CC source-backed `handoff` payload, producer
artifact, parent-observed bytes, receiver artifact, repository truth, and
private oracle.

The 2026-07-24
[`handoff` loader-observability preflight](../handoff-loader-trial-preflight-contract-2026-07-24.md)
binds the fixed canonical protocol, selected payload, prospective host adapter,
and capture-capability evidence before any live Arm C attempt. It is a
preflight for this same canonical scenario, not new evidence and not a new
scorer.

The view records five independent axes:

1. producer artifact integrity;
2. task-level host exposure;
3. exact loader invocation;
4. receiver repository-truth recovery;
5. thread creation mode.

Arm A uses the repository-anchored artifact without exposing the source-backed
handoff payload. Arm C uses the same facts with the exact CC payload and a
producer/receiver sequence. Both retain the same hard standards and repository
oracle.

Offline source attribution and symlink visibility do not prove fresh-session
loading. A live result still requires a fresh host thread, the same bound
project/workspace, parent-observed actual model/reasoning, task-scoped exposure,
an exact host loader event, producer/parent/receiver artifact hash equality,
receiver oracle matching, manual user-authorized creation mode, and three
independent host runs per eligible arm.

Automatic thread creation, automatic project registration, lossless handoff,
cross-device equality, and cross-host parity remain unproved.

## Git and engineering overlap

`GIT-OVERLAP-01` reuses `ABL-GIT-TOPOLOGY-01` and the deterministic Git topology
oracle. `ENG-SLICE-01` and `ENG-ORACLE-02` may check branch-safety effects inside
an engineering task, but they do not replace topology judgment or become a
second copy of the Git evidence.

## Instruction-carrier adherence

`INSTRUCTION-CARRIER-CTX-07` has an independent carrier-specific private oracle
because discovery, loading, and rule adherence are not intake, routing,
closure, or engineering-task outcomes. It reuses only outer parent-host fields:
host/model identity, distinct run/thread/task identities, raw response digest,
repository before/after truth, and the three-run repetition structure.

The outer envelope does not replace the carrier private oracle. Hard-standard
success and host approval remain controls and cannot be credited to the carrier.
A repeated single-host pass does not prove cross-Agent parity.

## Outer live envelope

The Skill live-run envelope records parent-host identity, actual model,
task-scoped exposure, loader evidence, payload and response digests, repository
before/after truth, and repetition. It requires the canonical scenario scorer
verdict and digest; it does not replace canonical scenario scoring. Synthetic
envelopes never count as live evidence.
