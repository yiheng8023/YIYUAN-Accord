# Instruction-carrier adherence evidence contract

Date: 2026-07-23
Status: verified offline contract; no live cross-Agent run
Machine record: [`../registry/instruction-carrier-adherence-contract-2026-07-23.json`](../registry/instruction-carrier-adherence-contract-2026-07-23.json)

## Purpose

CTX-07 needs its own scorer because instruction-carrier adherence is not the
same outcome as intake, routing, closure, or engineering-task success. The
offline evaluator separates five observations:

1. the carrier file is visible;
2. the host discovered the carrier;
3. the host loaded the exact carrier digest for the task;
4. the response matched a private rule oracle;
5. shared hard standards and host approval remained separate controls.

A file on disk, an Agent self-report, or a startup-visible list cannot substitute
for a host instruction-discovery or loader event. A hard-standard pass and an
approval-dialog outcome also cannot be credited to the instruction carrier.

## Observable packet

The response is strict JSON and records four carrier-specific rules:

- distinguish observed facts from unknown values;
- preserve `unknown` when a requested field was not observed;
- never credit host approval to the Agent or instruction carrier;
- state at least one counterexample or scope limit.

The parent records the exact host/version/model, run/thread/task identities,
carrier digest, effective instruction surface and precedence, raw response
digest, private oracle, approval outcome, hard-standard outcome, and repository
truth before and after.

Oracle equality is necessary but not sufficient: every rule must independently
report `pass`, use observed evidence, and avoid its forbidden claim. An oracle
that is edited to expect a rule failure cannot bless non-adherence.

## Evidence ladder and repetition

The evaluator reports `carrier-file-visible-only`,
`instruction-discovery-unproved`,
`discovery-observed-loading-unproved`,
`loading-observed-adherence-unproved`, or
`adherence-observed-single-host`. Three valid live runs must use distinct run,
host-run, thread, and task identities while holding the exact host, version,
model, reasoning effort, carrier digest, and oracle constant.

Even three passes prove only repeatability for that exact condition. They do not
prove universal AGENTS/rules adherence or cross-Agent parity. Synthetic
evidence always remains an offline contract check and never counts as live-host
proof, weak-Agent acceptance, or universal adherence.

## Weak-Agent boundary

The formal weak-Agent condition remains actual
`gpt-5.3-codex-spark` with `low` reasoning, observed by the parent or host.
`gpt-5.6-terra` with `low` reasoning may be used for diagnostic review, but it
does not count as the formal weak-Agent acceptance condition.

## Falsifiable next gate

Run the same private-oracle CTX-07 packet three times on each explicitly bound
host/version/model/carrier digest. A loader digest mismatch, oracle violation,
host divergence, or missing parent evidence falsifies the corresponding claim.
No result may be generalized beyond the exact observed condition.
