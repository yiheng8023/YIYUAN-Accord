# Skill Live-Run Evidence Contract — 2026-07-23

## Purpose

The overlap matrix now has deterministic scenario packets, private-oracle
scorers, and a separate parent-observed evidence envelope for a future live
run. This layer prevents a correct-looking response, installed payload, Agent
self-report, or global startup visibility from being upgraded into verified
Skill invocation or weak-Agent acceptance.

The evaluator is side-effect free. It does not create a task, invoke a model or
Skill, inspect a host, or change configuration.

## One-run gate

Every runnable scenario/arm cell must bind:

- the exact public packet and digest plus the private-oracle version and digest;
- requested and actual `gpt-5.3-codex-spark` / `low`, observed by the parent or
  host rather than reported by the tested Agent;
- distinct task, run, host-run, and host-thread identities;
- the selected payload source, revision, path, and SHA-256 manifest;
- task-scoped exposure for every selected and unselected intervention arm;
- one exact host loader event for every selected payload;
- the trigger mode and trigger boundary plus parent-observed or host trigger
  evidence;
- the raw UTF-8 response digest recomputed from bytes;
- the scenario scorer verdict and evidence digest;
- repository truth before and after, plus authority and mutation envelopes.

The hard-only arm must expose none of the four intervention arms. Selective
Matt and Superpowers arms must bind exactly one payload. The full Superpowers
bootstrap must remain a distinct multi-payload arm. Shared hard standards stay
active in every arm and receive no Skill value credit.

## Repetition gate

A cell needs three valid live runs with distinct run, host-run, thread, and task
identities. Scenario, arm, packet, oracle, payload manifest, trigger mode, and
trigger boundary must remain constant. A not-applicable cell requires a
concrete reason and is not silently
treated as a failed arm or residual gap.

## Evidence boundary

The fifteen deterministic fixtures are synthetic. They exercise missing live
execution, response digest drift, absent intervention payloads, missing loader
events, selective/full-bootstrap trigger confusion, top-level `ask-matt`
trigger leakage, cross-arm exposure contamination, hard-control credit leakage,
authority overreach, repository mutation, Terra substitution, non-task-scoped
exposure, and private-oracle failure.

Synthetic evidence always returns
`evidence-contract-ready-not-live-host-proved`; it never counts as live host
proof or weak-Agent acceptance. No five-arm comparison, task-scoped loading,
Spark/low availability, Skill superiority, or self-authored residual gap has
been proved by this contract.
