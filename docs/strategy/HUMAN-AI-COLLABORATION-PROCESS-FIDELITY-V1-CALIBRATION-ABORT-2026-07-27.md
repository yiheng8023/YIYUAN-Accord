# Process-Fidelity V1 Calibration Abort

Date: 2026-07-27
Status: measurement-ambiguous v1; cohort stopped after one dispatch

## Outcome

The first `complete-single-turn` repetition reached the requested
`gpt-5.3-codex-spark/low` route with provider fallback disabled. The task was
ephemeral, read-only, network-disabled, approval policy was `never`, and all
105 configurable Skills were disabled. No command, dynamic tool, MCP call,
web search, file change, trial-tree change, or global-config change was
observed.

The response did not match the v1 private oracle. It returned C3 as
`contradicted` rather than `unknown` and set `unsupportedConclusionCount` to
3 rather than 0. The runner therefore stopped the cohort before the other
eight planned tasks.

## Why This Is Not a Weak-Agent Capability Finding

The v1 public contract does not define the entailment boundary between
`contradicted` and `unknown`. Three units stopped early after a temperature
limit was exceeded, while a draft checklist requires every unit to complete
the cycle threshold. Treating readiness as contradicted is a reasonable
reading; the private `unknown` label is not uniquely compelled.

The v1 contract also does not define `unsupportedConclusionCount`. The private
oracle assumes it counts only extra output assertions, while the response can
reasonably be read as counting the three requested claims that were not
supported. It likewise does not define whether `sourceIds` must contain all
material sources or only a sufficient evidence set.

These are measurement defects. The run remains useful as bounded host and
runner diagnostic evidence, but it cannot be counted as a valid weak-Agent
failure, a three-arm repetition, or process-fidelity acceptance evidence.

## Additional Isolation Defect

The unexecuted v1 source-backed arm would have allowed read-only command
execution. Its prepared directory also contained a packet that exposed the
parent fixture path. Read-only execution prevents mutation but does not prove
that the Agent can read only the public bundle. The v1 scorer did not verify
the exact read target or block parent-oracle reads.

The source-backed arm therefore requires a parent-owned scoped read interface,
positive evidence of the exact public-bundle hash returned, and failure on any
shell, out-of-root, or unregistered read before it can enter a live cohort.

## Next Gate

V1 evidence and hashes remain unchanged. A new v2 fixture must define state
semantics, counting semantics, and source-set semantics before dispatch. The
three arms must restart from zero under one v2 protocol; no v1 result may be
mixed into the v2 cohort.

Absolute task correctness and relative process loss will be reported
separately. Relative improvement cannot rescue an absolute weak-Agent failure,
and strong-Agent diagnostics cannot replace weak-Agent acceptance.

Raw reports remain temporary cleanup debt. The governed registry record keeps
the essential hashes, structured submission, observed host boundary, design
invalidity, and claim limits.
