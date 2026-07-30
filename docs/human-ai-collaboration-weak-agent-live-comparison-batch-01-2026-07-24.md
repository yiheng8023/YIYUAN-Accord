# Weak-Agent Live Comparison: Batch 01

Date: 2026-07-24
Status: three paired observations complete; mixed process outcome

## Bound question

For the dependency-free `fixture.python-retry-policy-v1` task, does a
task-scoped CC Switch Skill arm behave differently from a native weak-Agent
arm when the model, reasoning effort, sandbox, fixture, mutation allowlist, and
hidden oracle are held fixed?

This batch compares:

- native `gpt-5.3-codex-spark` at `low`, with all user Skills disabled;
- the same model and effort with only CC Switch
  `disciplined-coding` enabled and explicitly named.

The host was Codex app-server `0.145.0`. Both arms used `approvalPolicy=never`,
workspace-write isolation, no network, no provider fallback, no MCP/App use,
and only `retry_policy.py` plus `test_retry_policy.py` as allowed mutable
files.

## First paired observation

| Arm | Fixture | Hidden oracle | Commands | Failed commands | Agent ran fixture tests | Transient out-of-scope writes |
| --- | --- | --- | ---: | ---: | --- | --- |
| Native Spark R1 | pass | pass | 1 | 0 | no | none observed |
| Matt `disciplined-coding` R1 | pass | pass | 4 | 0 | yes | none observed |
| Native Spark R2 | pass | pass | 3 | 1 | no | none observed |
| Matt `disciplined-coding` R2 | pass | pass | 2 | 0 | yes | none observed |
| Native Spark R3 | pass | pass | 3 | 0 | yes | none observed |
| Matt `disciplined-coding` R3 | pass | pass | 17 | 5 | yes | `.tmp.patch` |

Both formal runs preserved the global Codex configuration, changed exactly the
two allowed files, and exposed no forbidden MCP, App, web, or collaboration
item type.

The empty `.agents`, `.codex`, and `.git` directories seen in both formal runs
were classified as a host projection only because all three appeared together
during the turn, remained empty, and no command or file-change item targeted
them. A partial pattern, a non-empty directory, or a targeting command remains
a failure.

## Pilot findings retained

The formal pair was preceded by deliberately excluded pilots:

- a functionally passing run exposed the legacy thread-start network policy;
- one run was rejected before the Agent turn because the experimental API
  capability had not been negotiated;
- Python bytecode cache output showed that final-state-only file accounting
  was too weak;
- a later run established the exact empty host-projection pattern;
- one functionally passing run issued 39 commands, 22 of which failed, and
  repeatedly created and removed `tmp.patch`.

The last pilot is important: a clean final directory is not proof that the
process respected the mutation boundary. The runner now records bounded command
evidence, failure counts, and heuristic transient-write findings. That
heuristic is evidence of detected violations; it does not prove that every
short-lived write would be observed.

## Interpretation boundary

The eligible statement is narrow:

> Across three paired observations, both arms passed the bounded functional
> oracle in every run. The Matt treatment arm ran tests in every run but failed
> the strict process boundary once; the native arm passed the strict process
> boundary in all three runs and ran tests once.

This does not prove that the Skill loader invoked the Skill, that the Skill
instructions reached the model, that the Skill caused the behavior, that Matt
is generally better, or that either arm is production-ready. Explicitly naming
the selected Skill in one arm is itself part of the treatment and prevents a
causal claim from this pair alone.

The predeclared three-run-per-arm threshold is met, but this single fixture does
not justify a preference, overlap, retention, or self-authored-chain adjustment
decision. Loader observation or an equivalent treatment-fidelity mechanism and
a second software-lifecycle scenario are required first. Every failure and
excluded run remains visible. A stronger model must not replace weak-model
acceptance, and the Superpowers arm stays blocked until its task-scoped
host-selection path is proved.

Canonical machine record:
`registry/human-ai-collaboration-weak-agent-live-comparison-batch-01-2026-07-24.json`.
