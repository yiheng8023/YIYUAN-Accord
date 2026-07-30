# Git Truth And Topology Decision PoC — 2026-07-19

Status: current-repository snapshot observed; deterministic `GIT-01` through
`GIT-05` decision fixtures plus disposable real-repository read-only and native
lifecycle integration verified; no user-repository Git topology mutation
authorized
Repository: `C:/Projects/agent-autonomy-harness`
Snapshot date: 2026-07-19

## Question

Can a small native-Git decision contract recover repository truth without
inventing upstream or remote freshness, then distinguish when to remain in the
current workspace, recommend a new branch, or recommend an isolated worktree?

This PoC tests read-only observation, recommendation, and a fixture-local
native Git lifecycle. It does not create a branch/worktree in the user
repository or prove general merge, cleanup, crash recovery, or cross-host
parity.

## Current live snapshot

The current repository observation recorded:

- branch `main`;
- HEAD `55659f30091990f7c589932e0379880de30dc403`;
- configured upstream `origin/main`;
- local HEAD versus local `origin/main`: ahead/behind `0/0`;
- one current worktree at `C:/Projects/agent-autonomy-harness` on `main`;
- origin fetch/push identity
  `git@github.com:yiheng8023/agent-autonomy-harness.git`;
- the following exact dirty paths:

```text
 M docs/strategy/PRODUCT-NORTH-STAR.md
 M docs/strategy/RESEARCH-AND-POC-PLAN.md
 M scripts/verify.py
 M tests/test_verify_integration.py
?? docs/context-continuation-paired-trial-protocol-2026-07-19.md
?? docs/context-continuation-poc-evidence-2026-07-19.md
?? docs/git-topology-decision-poc-2026-07-19.md
?? docs/mcp-current-host-inventory-2026-07-19.md
?? docs/mcp-runtime-refresh-interface-and-trial-protocol-2026-07-19.md
?? docs/skill-ablation-batch-01-selection-2026-07-19.md
?? docs/skill-portfolio-and-closeout-inventory-2026-07-19.md
?? docs/skill-source-authority-and-runtime-reconciliation-2026-07-19.md
?? docs/strategy/POC-SCENARIO-EVIDENCE-MATRIX.md
?? docs/strategy/SKILL-PORTFOLIO-REBASELINE-AND-CLOSEOUT-GATES.md
?? registry/mcp-current-host-inventory-2026-07-19.json
?? registry/mcp-runtime-refresh-interface-review-2026-07-19.json
?? registry/skill-ablation-batch-01-selection-2026-07-19.json
?? registry/skill-portfolio-and-closeout-inventory-2026-07-19.json
?? registry/skill-portfolio-rebaseline-and-closeout-gate-2026-07-19.json
?? registry/skill-source-authority-and-runtime-reconciliation-2026-07-19.json
?? scripts/build_context_continuation_trial_packet.py
?? scripts/evaluate_context_continuation_trial.py
?? scripts/evaluate_git_topology_trial.py
?? scripts/evaluate_mcp_runtime_refresh_trial.py
?? scripts/inventory_skill_portfolio.py
?? scripts/observe_git_snapshot.py
?? scripts/reconcile_skill_source_authority.py
?? tests/fixtures/context-continuation-paired-trial-2026-07-19.json
?? tests/fixtures/git-topology-decision-fixtures-2026-07-19.json
?? tests/fixtures/mcp-runtime-refresh-trial-2026-07-19.json
?? tests/test_context_continuation_trial.py
?? tests/test_context_continuation_trial_packet.py
?? tests/test_git_snapshot_integration.py
?? tests/test_git_topology_trial.py
?? tests/test_mcp_runtime_refresh_trial.py
?? tests/test_skill_portfolio_inventory.py
?? tests/test_skill_source_authority_reconciliation.py
```

Every path belongs to the currently authorized context/Git PoC work package.
The current task depends on that related uncommitted state, so the bounded
`GIT-02` result is `continue-current-workspace-related-dirty-state`. A new
worktree would not automatically contain these changes. This is one observed
application of the decision inputs, not proof that the rule generalizes.

This snapshot is `observed-single-host` for native local Git state. No network
refresh was run in this slice, so `origin/main` is a local tracking ref and must
not be described as current live remote truth.

## `GIT-01` snapshot contract

A complete local snapshot binds:

1. repository locator;
2. branch or detached-HEAD state;
3. exact HEAD;
4. complete status and relevant dirty paths;
5. recent commit identity;
6. configured upstream state: present or explicitly absent;
7. ahead/behind only when an upstream exists;
8. worktree inventory;
9. remote identity when configured;
10. remote freshness scope: none, local tracking ref only, or live remote after
    an explicitly recorded network refresh.

Unknown upstream state, omitted/invented dirty paths, an ahead/behind claim
without an upstream, or a live-remote claim without observed refresh falsifies
snapshot completeness.

Repositories without upstreams are a supported state. The contract returns
`snapshot-complete-no-upstream`; it does not invent `origin/main` or treat
ahead/behind as zero.

## `GIT-02` topology contract

Topology is a recommendation until separately authorized. Decision inputs are:

- bound task and completed snapshot;
- task kind: read-only, small write, risky write, heavy test, or parallel work;
- whether dirty paths are related, unrelated, absent, or still unknown;
- whether the task depends on current related dirty state;
- whether runtime/filesystem isolation is required;
- whether the current branch purpose matches the task.

Decision rules:

| Condition | Recommendation |
| --- | --- |
| Read-only task | Continue in the current workspace; no topology mutation. |
| Task explicitly depends on related dirty state | Continue in the current workspace with bounded scope. |
| Dirty-path ownership is unknown | Resolve ownership before deciding topology. |
| Unrelated dirty work could collide with a write | Recommend an isolated worktree. |
| Risky write, heavy test, parallel work, or runtime isolation | Recommend an isolated worktree. |
| Small write, clean/non-colliding workspace, wrong branch purpose | Recommend a new branch in the current workspace. |
| Small related write on an aligned branch | Continue on the current branch. |

A branch changes review lineage but does not isolate the working directory. A
worktree isolates a checkout but does not preserve thread intent, inherit
uncommitted state by default, or authorize cleanup.

## Authority boundary

This slice authorizes read-only Git inspection plus creation, exact-base
branch/worktree operations, fixture-local fast-forward merge, safe native
cleanup, and automatic teardown of test-only repositories under Python
temporary directories. That fixture authority is not authority to mutate the
bound user repository. It does not authorize there:

- branch or worktree creation;
- checkout, switch, stash, reset, restore, rebase, or merge;
- commit or push;
- deletion or cleanup;
- live remote refresh as proof unless that network action is explicitly
  included and recorded.

An evaluator result named `recommend-*` is advice, not action authority. Any
attempted topology mutation without separate authorization is a hard failure.

## Deterministic preflight

The corpus
[`git-topology-decision-fixtures-2026-07-19.json`](../tests/fixtures/git-topology-decision-fixtures-2026-07-19.json)
contains 32 cases across `GIT-01` through `GIT-05`. It is evaluated by
[`evaluate_git_topology_trial.py`](../scripts/evaluate_git_topology_trial.py).

The fixtures cover unbound inputs, incomplete snapshots, absent/unknown
upstreams, dirty-path mismatch, remote-freshness overclaim, read-only work,
related and unrelated dirty state, heavy tests, branch sufficiency, worktree
isolation, creation authority and exact-base gates, merge authority and
fast-forward preconditions, and exact cleanup authority and retention gates.

Passing fixtures prove only that the deterministic policy returns its
predeclared decisions. They are not evidence that an Agent will follow the
policy, that branch/worktree creation is safe, or that a host preserves
unrelated dirty bytes.

## Disposable real-repository integration

[`observe_git_snapshot.py`](../scripts/observe_git_snapshot.py) runs only
read-only Git commands and labels upstream comparisons `local-ref-only` unless
a separate network refresh is actually observed. The integration runner
[`test_git_snapshot_integration.py`](../tests/test_git_snapshot_integration.py)
creates repositories only inside automatically removed Python temporary
directories. It uses the system default temporary root unless the task-specific
`AGENT_AUTONOMY_GIT_TEST_ROOT` override binds a writable, unwatched sandbox
root. Git automatic maintenance and auto-gc are disabled inside each fixture
to keep process ownership and cleanup deterministic. The runner asserts through
normal test teardown that the temporary directory context exits successfully.

The current Codex sandbox run uses its separately writable visualization
artifact root because the user temporary directory is outside the cleanup
write boundary and the repository root is actively watched by the host. This
is a host test-runner constraint, not a Git product capability claim.

On the current Windows host, the runner verifies:

1. a clean repository without an upstream returns
   `snapshot-complete-no-upstream` and invents no remote;
2. a repository tracking a local-filesystem bare remote reports
   `origin/main`, exact tracked/untracked paths, `0/0`, and
   `local-ref-only` rather than live-remote freshness;
3. detached HEAD is reported explicitly with no invented branch name;
4. rename porcelain retains both the old and new paths;
5. copy porcelain, with repository-local `status.renames=copies`, retains both
   the source and target paths;
6. primary and secondary worktrees are both enumerated;
7. a local-filesystem tracking ref reports `1/0` after one local commit and
   `1/1` after a peer commit is fetched, while freshness remains
   `local-ref-only`;
8. a SHA-256 sentinel for unrelated bytes is identical before and after the
   observer runs;
9. after a real content conflict, `UU tracked.txt`, the exact dirty path,
   `HEAD`, `MERGE_HEAD`, the unmerged index, conflict bytes, worktree
   registration, and unrelated sentinel bytes are observed unchanged across
   the observer call.

In this bounded observation, the unrelated SHA-256 sentinel remains
byte-identical.

This is real single-host Git behavior evidence for bounded logical-state and
content containment across the observer call, plus one bounded `GIT-06`
preservation case. It is not proof of filesystem zero-write observation:
`git status` may refresh Git metadata such as index stat-cache fields. The
worktree command is disposable fixture setup; it does not prove
branch/worktree creation safety in a bound user repository. This is not
external-network freshness, general failure recovery, Agent adherence, or
cross-host evidence.

## Disposable native lifecycle integration

On Windows with Git `2.55.0.windows.3`, one test-only repository lifecycle
inside a Python `TemporaryDirectory` observed:

1. `git worktree add -b` created an exact-base branch and secondary worktree
   while leaving `main` at the bound base SHA;
2. one controlled secondary-worktree commit advanced only the feature branch;
3. `git merge --ff-only` advanced `main` to that exact commit without a merge
   commit or `MERGE_HEAD`;
4. the clean secondary worktree was removed without `--force`;
5. the now-merged branch was removed with `git branch -d`, never `-D`;
6. the feature commit remained reachable through `main`, the final worktree
   inventory contained only the primary checkout, and an unrelated sibling
   SHA-256 sentinel remained byte-identical.

Three bounded refusal cases also passed:

- a dirty primary checkout prevented the fast-forward merge and preserved
  HEAD, refs, dirty bytes, status, worktrees, and the unrelated sentinel;
- a dirty secondary worktree prevented non-force worktree removal and
  preserved its path, registration, branch, and dirty bytes;
- a clean but unmerged branch survived safe `git branch -d` after its worktree
  was removed.

The focused command
`python -B -m unittest tests.test_git_topology_trial
tests.test_git_snapshot_integration` ran 18 tests successfully on 2026-07-24.
Python temporary-directory teardown is test containment, not Git cleanup
evidence; the successful path verifies Git registration and refs before that
outer teardown occurs.

The lifecycle uses native Git directly. It does not add a branch/worktree
manager, automatic stash/reset, conflict resolver, broad prune, force removal,
or cross-repository cleanup layer.

## Bounded failure injection

Three disposable failure cases add narrow `GIT-07` evidence:

1. checkout of a nonexistent branch returns nonzero while HEAD, current branch,
   porcelain status, worktree inventory, and an unrelated byte hash remain
   identical;
2. worktree creation into an existing nonempty directory returns nonzero,
   preserves its sentinel bytes, and leaves no partial worktree registration;
3. merging two commits that changed the same tracked line returns nonzero and
   leaves a real content conflict. The existing observer reports
   `UU tracked.txt`; `HEAD`, `MERGE_HEAD`, the unmerged index, conflict bytes,
   worktree registration, and unrelated sentinel bytes are observed unchanged
   across that call. The test does not resolve or abort the merge, and it does
   not establish filesystem zero-write behavior.

These observations prove reconstruction only for the exact local failures.
They do not prove recovery after interruption, process crash, disk failure,
conflict resolution or abort safety, partial filesystem mutation, broader
merge/rebase failure recovery, or unknown process ownership. A nonzero exit is
evidence to inspect state, not automatic proof that every command failed
atomically.

## Falsifiers and next evidence

Downgrade this decision contract if controlled repository fixtures show that
it omits a material Git state, recommends current-workspace work over unrelated
dirty paths, recommends a worktree when current dirty state is required, or
attempts a mutation from recommendation alone.

Copy-detection and content-conflict observation coverage are now observed only
on this Windows/Git version and repository-local test configuration. The next
stronger read-only evidence is a separately authorized live remote refresh
comparison. Broader `GIT-07` evidence requires interruption, crash, or
partial-state recovery fixtures with exact recovery authority. The disposable
lifecycle does not authorize `GIT-03`
creation, `GIT-04` merge, or `GIT-05` cleanup in a bound user repository; each
remains a separate authorization gate.
