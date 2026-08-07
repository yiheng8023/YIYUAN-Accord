# Process-Loss External Reuse Research: LongHorizon-Harness

Date: 2026-08-07

Status: read-only external-candidate assessment

Disposition: high-value reuse candidate; not admitted, installed, enabled, or
executed

Governed evidence:
[`process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07.json`](../../registry/process-loss-longhorizon-harness-static-reuse-assessment-2026-08-07.json)

## Question and boundary

This note evaluates whether the project referenced by [Xudong Han's X
post](https://x.com/Xudong07452910/status/2085206732096025020) is open source,
whether it materially addresses process loss from requirements to delivery,
and whether it can prevent duplicate implementation in Agent Autonomy Harness.

The review used public primary sources and exact-revision source inspection. It
did not install the package, execute the harness, dispatch a model, connect an
account, or alter a consumer host. Benchmark results remain author-reported and
were not independently reproduced.

## Executive judgment

LongHorizon-Harness is genuinely open source: the public core repository uses
the MIT License. Its Manage-Execute-Audit loop is a highly relevant operational
implementation of audited long-horizon progress, fresh-context execution,
completion gating, and persistent round evidence. Those mechanisms are strong
enough that Agent Autonomy Harness should not self-author an equivalent
operational coordinator before this candidate is tested and falsified against
the repository's residual-gap criteria.

It is not a replacement for the Harness process-fidelity contract. The project
primarily governs the execution-to-audit-to-next-step loop. The Harness also
requires source binding, semantic and authority continuity, cumulative loss
accounting, human acceptance, lifecycle edges, cross-host evidence, rollback,
and cleanup. The external project should therefore be treated as a possible
runtime component or comparison arm under Harness-owned governance, not as the
new product authority.

Direct adoption is not currently justified. At the reviewed revision, the
default Claude and Codex routes bypass host approval or sandbox controls, the
auditor's read-only property is not enforced as a hard sandbox boundary,
cross-process resume was not found, Windows support is not thoroughly tested,
and the core package lacks a top-level test suite and test-running CI workflow.

## Frozen source snapshot

| Field | Reviewed value |
| --- | --- |
| X source | [Xudong Han post](https://x.com/Xudong07452910/status/2085206732096025020) |
| Paper | [LongHorizon-Harness: Advancing Long-Horizon Agents for Real-World Tasks](https://arxiv.org/abs/2608.01964), arXiv:2608.01964v1, submitted 2026-08-03 |
| Paper HTML | [arXiv HTML](https://arxiv.org/html/2608.01964v1) |
| Project site | [lh-harness.pages.dev](https://lh-harness.pages.dev/) |
| Official source | [AMAP-ML/LongHorizon-Harness](https://github.com/AMAP-ML/LongHorizon-Harness) |
| Reviewed revision | [`b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58`](https://github.com/AMAP-ML/LongHorizon-Harness/commit/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58) |
| Code license | [MIT](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/LICENSE) |
| Package metadata | [`lh-harness` 0.1.2, Python >=3.10, MIT](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/pyproject.toml) |
| Retrieval date | 2026-08-07 |

The paper identifies the authors as DreamX Team, Alibaba Group and links the
official repository and project site. The X post is a useful discovery and
summary surface, but its claims are not treated as primary implementation or
benchmark evidence.

The MIT license permits reuse, modification, and distribution subject to
preserving its notice and license terms. Benchmark subtrees carry their own
license and notice files and require separate review if any evaluation payload
is reused.

## What the project implements

The implementation contains the core mechanism described by the paper:

- a Manager reads the original task, maintained task state and contract, and
  auditor reports, then selects a bounded next route;
- an Executor receives a fresh context with the current bounded contract rather
  than the complete prior trajectory;
- an Auditor runs separately and its result becomes evidence for the next
  Manager decision;
- task state, task contract, round events, trajectories, audit reports, and a
  final report are persisted under a run directory;
- a `done` decision is rejected unless the latest audit is complete, clean, and
  aligned;
- `ask`, `blocked`, `completed`, and maximum-round conditions provide explicit
  termination or human-intervention gates;
- adapters keep the backend agent loop comparatively thin instead of
  reimplementing Claude Code or Codex behavior.

Primary code anchors:

- [Manager inputs and fresh-state planning](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/manager.py#L204-L220)
- [task-state and task-contract persistence](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/manager.py#L264-L279)
- [completion guard](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/manager.py#L297-L333)
- [executor and auditor sequence](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/manager.py#L397-L574)
- [human and blocked routes](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/manager.py#L638-L707)
- [append-only round record](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/manager.py#L1019-L1033)

The code uses natural-language `task_state` and `task_contract` artifacts plus
control-header parsing rather than a fully typed requirement, evidence, and
authority transition model. This is useful and inspectable, but it is more
brittle than the paper's conceptual structured state may suggest.

## Reported results and evidence limit

The paper reports that, for Qwen 3.7-Plus, the harness changes:

- WeaveBench pass rate from 51.8 to 80.7;
- Terminal-Bench 2.1 from 69.7 to 77.2;
- OSWorld 2.0 binary score from 2.8 to 8.3 and partial score from 21.5 to 35.2.

These are material author-reported aggregate gains across different task and
host surfaces. They demonstrate that the hypothesis is worth testing; they do
not prove general value for the current Harness, Windows, this repository, or
all models and tasks. Some category and task results in the paper decline, so
the gain is task-dependent. The README's token-reduction claim is tied to a
particular Terminal-Bench comparison and must not be promoted to a universal
efficiency claim. No independent reproduction was performed in this review.

## Fit with Agent Autonomy Harness

### Strong overlap worth reusing or comparing

| LongHorizon-Harness mechanism | Harness need it can address |
| --- | --- |
| Manage-Execute-Audit loop | operational coordinator for bounded next-action selection |
| audited persistent task state | verified progress that survives fresh contexts within a run |
| fresh-context Executor | limits raw-trajectory accumulation and context contamination |
| completion guard | prevents an unaudited terminal claim from advancing state |
| append-only round and event records | inspectable provenance for process-loss measurement |
| ask, blocked, and maximum-round gates | human intervention without requiring the user to orchestrate every round |
| thin backend adapters | comparison across Claude Code, Codex, and other backends without replacing their agent loops |

This is a credible candidate for the operational coordinator that the Harness
has not yet proved it must author. Reuse evaluation should focus on the loop,
state/audit artifact contract, completion guard, event record, and adapter
seams rather than vendoring the repository wholesale.

### Harness scope it does not replace

The current `acceptance.end-to-end-process-fidelity` is broader. It requires
loss and recovery evidence across intake, interpretation, decomposition,
routing, delegation, compression, handoff, aggregation, review, acceptance,
and lifecycle transitions. It also keeps absolute terminal correctness separate
from relative process loss.

LongHorizon-Harness does not currently provide sufficient evidence for:

- human-to-source binding and terminal-to-human accountable review;
- semantic identity and consequential decision continuity from requirements
  through architecture, implementation, release or rollback, operations, and
  closure;
- explicit new, carried, recovered, unique, peak, and budget-breach loss
  accounting;
- provenance breaks, authority drift, detection latency, amplification,
  recovery distance, and rollback measurement;
- native, official, and mature-external ablation under a common frozen
  protocol;
- cross-host portability, permission integrity, cleanup, and user-burden
  evidence.

It is therefore a runtime candidate under the Harness contract, not a substitute
for the contract, acceptance registry, verifier, or human authority boundary.

## Material adoption blockers

### 1. Permission and sandbox defaults conflict with Harness governance

The Claude adapter invokes `--dangerously-skip-permissions`. Its role policy
uses tool deny-lists and workspace snapshots while explicitly not relying on
the native Claude sandbox:

- [Claude adapter invocation](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/adapters/claude_code.py#L86-L155)
- [Claude role policy](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/adapters/claude_permissions.py#L32-L68)

The snapshot-diff response records `restore_on_mutation: true`, but the
reviewed implementation fixes `restored: false`; it detects and rejects an
auditor mutation rather than restoring it:

- [workspace mutation result](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/adapters/claude_permissions.py#L128-L165)

The Codex adapter defaults to
`--dangerously-bypass-approvals-and-sandbox`. The CLI creates separate adapter
instances but does not pass a Codex role that establishes source-level
manager/auditor permissions:

- [Codex adapter default](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/adapters/codex.py#L42-L56)
- [CLI adapter construction](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/cli.py#L993-L1021)

The current evidence supports mutation detection for part of the Claude path,
not a generally enforced read-only auditor. It does not support direct use in a
user's main working directory under the Harness authority floor.

### 2. Persisted progress is not verified crash resume

Each run persists state and evidence, but the reviewed CLI initializes a new
manager state and no resume command or replay path from an earlier run was
found:

- [new-run state initialization](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/src/lh_harness/cli.py#L825-L864)

The supported claim is narrower: fresh-context continuation and repair inside a
running process, plus human-inspectable persisted artifacts. Evidence does not
support automatic recovery after process failure, crash-consistent replay, or
cross-host recovery.

### 3. The project is early and its verification surface is thin

At the snapshot date, the repository was created on 2026-08-04 and had six
visible commits and three tags. Recent activity and maintainer responses are
positive signals, not evidence of long-term maintenance.

The README says macOS is currently tested and Windows support is included but
not thoroughly tested. The exact-revision tree has no independent top-level
core-package test suite. Its only GitHub workflow builds and publishes a
package; it does not run core tests:

- [release workflow](https://github.com/AMAP-ML/LongHorizon-Harness/blob/b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58/.github/workflows/release.yml)

This assessment deliberately does not rely on GitHub Actions as quality proof.
The workflow is mentioned only to delimit what is and is not automatically
verified.

## Reuse decision

The current bounded decision is:

1. Stop self-authoring an equivalent operational long-horizon coordinator until
   this candidate is disproved against explicit residual gaps.
2. Register or compare it as an exact-revision external candidate, keeping its
   code upstream and unmodified by default.
3. Reuse or adapt only the demonstrated seams: Manage-Execute-Audit,
   task-state/task-contract/audit artifacts, completion guard, append-only event
   records, human gates, and thin adapters.
4. Keep Harness-owned governance for requirement/source binding, structured
   semantic and authority continuity, cumulative process-loss accounting,
   verification, rollback, cleanup, and cross-host acceptance.
5. Do not install, activate, execute, dispatch a model, or point the current
   implementation at a real workspace until the permission, isolation,
   recovery, platform, and test gaps have a separately authorized and
   disposable verification plan.

## Smallest next gate

The next authorized research slice should remain no-model and non-activating:

- freeze the exact source revision and license/provenance metadata;
- map its state, contract, audit, event, and adapter interfaces to the current
  process-fidelity protocol and acceptance subgates;
- specify a fail-closed host-owned permission profile, an isolated disposable
  workspace, and mutation/rollback oracle that would be required for any later
  execution;
- define a comparison arm against native continuation plus the current mature
  handoff composition;
- state in advance which residual gaps would justify a thin adapter, which
  would require upstream contribution, and which would stop adoption.

Any later installation, third-party code execution, model dispatch, account or
data-boundary expansion, or work against a non-disposable workspace remains a
new authorization gate. No real Claude task is required to preserve this
candidate finding; a future real task is only needed if and when live behavioral
value is evaluated.

## Authorized exact-source acquisition and deeper static review

After the preflight, the owner separately authorized one exact transaction:
acquire revision `b49ebf9654c1ee75eaf56dfe9eec1745fddcfa58` anonymously
into a new operating-system temporary directory outside repositories, projects,
capability roots, and user configuration; perform static review only; record
evidence; then send that exact directory to the Windows Recycle Bin.

The first depth-one fetch timed out after downloading its pack and before
creating a ref. The target commit object was present, a full Git object check
passed, and a clean detached checkout was recovered from that verified object.
This is acquisition-workflow recovery, not evidence that the candidate can
resume a crashed manager process.

The checkout matched the frozen commit and tree, contained 1,367 tracked paths,
and had no gitlinks or symlinks. The repository occupied 211,769,067 bytes
including Git objects. Its 39-path `src` package is small and the built sdist is
core-scoped, but the repository also carries 1,317 evaluation paths, separate
OSWorld and WeaveBench license/notice boundaries, and a 70,969,154-byte
promotional video. Core reuse must therefore not import the evaluation and
media surface by accident.

### Refined blocker findings

The exact checkout strengthens the earlier adoption blockers:

1. Claude always receives `--dangerously-skip-permissions`; Codex defaults to
   `--dangerously-bypass-approvals-and-sandbox` without an explicit sandbox.
2. The Claude auditor denies direct write tools but retains Bash and computer
   MCP access. It compares pre/post workspace snapshots after execution.
   `verifier_workspace_restore_on_mutation` defaults true, yet
   `verifier_workspace_restored` is always initialized false and no restoration
   implementation was found. This is fail-closed reporting, not preventive
   read-only enforcement or rollback.
3. Files over 4 MiB are not content-hashed by the snapshotter; mode, size, and
   mtime remain, but a content-level mutation can escape that oracle.
4. Persisted round artifacts are inspectable, but the CLI exposes no resume or
   recovery command for an interrupted prior manager process.
5. Command construction and process control are POSIX-shaped: `shlex` quoting,
   shell environment prefixes, `start_new_session`, `killpg`, Unix signals, and
   Linux screenshot commands. Windows behavior remains unproved.
6. A caller may point `--workspace` at an arbitrary existing path; the source
   supplies no protected-root exclusions, transaction journal, or implemented
   rollback.
7. Community computer-use packages are installed globally from unpinned npm
   names and may execute consent or OS-permission activation. The Codex-owned
   computer-use plugin delegates to Codex's persistent plugin registry. This
   cannot replace CC Switch and host-owned lifecycle authority without a
   separately governed adapter.
8. The root repository has no independent core-package test suite. Its release
   workflow builds and publishes but does not run core tests. Evaluation-subtree
   tests are not a substitute.

The source remains a high-value coordinator reference, and equivalent local
authoring remains stopped. Direct adoption stays blocked. A safe adapter or
upstream-change design would require a new owner decision; installation,
execution, model dispatch, account/configuration changes, CC Switch changes,
consumer mutation, and a real task were not authorized or performed.

## Cleanup receipt

The exact temporary directory was sent to the Windows Recycle Bin. Its original
path no longer exists, and the Recycle Bin contains a matching item whose
deleted-from location is the operating-system temp root. The operation is
recoverable by the user from the Recycle Bin. No other path was removed.

The public record retains only transaction id
`longhorizon-exact-source-2f46ee51636042b0843133510a7d629d` and normalized-path
SHA-256 `090e746768a20f4273ed6925e5a0b0740246cc7b7b6bb8a33ac400758d3e3aa8`,
not the user-local absolute path. Governed evidence:
`registry/process-loss-longhorizon-harness-exact-source-static-review-2026-08-07.json`.
