# Context Evidence Envelope — 2026-07-23

Status: verified local negative probes; live thread and loader evidence pending
Machine record:
[`../registry/context-evidence-envelope-2026-07-23.json`](../registry/context-evidence-envelope-2026-07-23.json)

## Result first

The context-continuation classifier no longer accepts a self-reported
`repositoryTruthChecked=true` flag as sufficient evidence for a passing result.
Any would-be pass now requires all of the following:

- the complete repository-truth field set with exact expected/observed equality;
- exact SHA-256 equality for every bound source file;
- complete before/after Git truth with exact equality;
- the existing exact critical-fact recovery and stale-fact rejection gates.

The packet builder computes the repository truth and bound source digests in the
parent process. The Agent-facing prompt does not receive the private oracle.

## Falsification probes

| Probe | Required result |
| --- | --- |
| Boolean-only repository recheck claim | `fail-repository-truth-evidence-missing` |
| Correct shape but different HEAD or status | `fail-repository-truth-value-drift` |
| Plausible but different source digest | `fail-source-evidence-drift` |
| Missing before/after Git envelope | `fail-repository-mutation-envelope-missing` |
| Git truth changes during the trial | `hard-fail-repository-mutated-during-trial` |

The focused local suite executes 12 tests covering the evaluator and packet
builder. This is deterministic contract evidence only. It is not a live
fresh-thread result.

## Claim boundary

This work does not prove:

- that Codex automatically creates a new thread under context pressure;
- that context telemetry or an optimal token interval is available;
- that `gpt-5.3-codex-spark/low` actually served a trial;
- that a fresh session invoked a source-backed handoff Skill;
- that AGENTS/rules are followed across Agents or hosts;
- that a handoff is lossless.

Codex CLI `0.145.0` is a host-version observation that triggers future
revalidation; it does not upgrade older host evidence. The next live gate
remains a separately authorized fresh-thread trial with verified model identity
and parent-observed evidence.

## Mutation boundary

No live thread was created, no loader was invoked, no model was sampled, and no
repository or host configuration was changed by this evidence-envelope step.
