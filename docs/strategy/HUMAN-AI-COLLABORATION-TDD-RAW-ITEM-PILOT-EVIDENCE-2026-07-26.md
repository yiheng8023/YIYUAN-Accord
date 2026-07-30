# Human-AI Collaboration TDD Raw-Item Pilot Evidence

This record separates measurement validity from Agent performance. It does
not score a treatment arm and does not count toward weak-Agent acceptance.

## Current-host result

On Codex Desktop 0.145.0 for Windows, a disposable native
`gpt-5.3-codex-spark` / `low` turn produced an ordered stream containing item
lifecycles, command-output deltas, file changes, hook lifecycle notifications,
and token-usage notifications. Reanalysis of the first sealed raw artifact
under the current normalizer produced `normalized-observable`. The artifact
hash matched the original report and the Agent was not rerun.

The same run did not pass the TDD behavior contract. It ran the full test
file rather than the required focused test identity, so the parent classifier
rejected the RED-to-GREEN process even though the final visible suite was
green. This is evidence that the instrumentation can distinguish measurement
readiness from task success, not evidence of weak-Agent TDD ability.

## Fail-closed counterexample

A second disposable trace contained a failed command-channel `apply_patch`
attempt and an empty command output. Because a failed write-capable command
could have an unobserved transient effect, the normalizer rejected that trace
with `opaque-write-command` and `command-output-missing`. The boundary was not
relaxed to obtain a green result.

Parallel read-only command lifecycles are allowed because they do not order
the TDD mutation sequence. Test commands, write-capable commands, and
file-change items remain causally ordered. Current-host hook lifecycle and
token-usage methods are recorded as bounded environmental observations; hook
context is not attributed as the cause of the TDD outcome.

## Evidence handling

The two raw event streams remain under `.tmp/` as explicit cleanup debt. They
are not vendored into durable source evidence. The registry stores their byte
lengths and SHA-256 digests, so removal during final-program cleanup will not
silently upgrade or invalidate the bounded conclusion.

The current-host result proves only that this Codex 0.145.0 trace shape can be
captured and normalized and that an opaque trace fails closed. It does not
prove cross-host schema stability, absence of all transient writes, dynamic
MCP lifecycle control, treatment delivery, Skill causation, candidate
preference, or formal weak-Agent acceptance.

## Next gate

At this pilot checkpoint, formal three-arm repetitions remained blocked. The
then-next bounded action was to make the parent-owned hidden oracle and
predeclared mutants executable, then build a formal runner that refreshed
model route, Skill exposure, repository tree, configuration, and raw-event
evidence for every repetition.

The subsequent formal runner and capped native batch are recorded separately.
The retained traces were later reanalyzed under normalizer v2, which validates
the observed plan-update payload shape and excludes `2>$null` from file-write
classification without weakening fail-closed handling of real opaque writes.
