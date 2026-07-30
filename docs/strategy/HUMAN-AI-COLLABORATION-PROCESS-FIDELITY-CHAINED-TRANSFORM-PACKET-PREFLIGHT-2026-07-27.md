# Chained-Transform Packet Preflight

Date: 2026-07-27
Status: zero-dispatch preflight passed
Live dispatch: not authorized and not ready

## Outcome

The frozen chained-transform protocol now has a deterministic first-hop packet
builder and a strict trace schema. A disposable local preflight rebuilt and
validated the packet without an Agent or model call.

The packet binds the exact protocol and trace-schema file hashes. It
materializes only `hop-1-decomposition`; later Agent stages remain deferred.
The formal process cohort still starts at zero.

## Parent and Agent roots

The parent-only root contains:

- `PROTOCOL.json`;
- `PRIVATE-SCORING-ORACLE.json`;
- `RUN-PLAN.json`; and
- `DEFERRED-STAGE-TEMPLATES.json`.

The Agent-visible first-hop root contains exactly:

- `INPUT-ENVELOPE.json`; and
- `STAGE-CONTRACT.json`.

The Agent-visible envelope has one dynamic input: the frozen `S0` artifact.
The stage contract exposes required invariant IDs but not scoring weights,
expected mutation deltas, thresholds, or unauthorized-assumption weights.

The preflight found two Agent-visible files and zero private scoring-field
leaks. It did not materialize Hop 2 or Hop 3.

## Trace schema

The v1 trace schema requires:

- exact run and route identity;
- five material-edge ledgers;
- three Agent-hop metric ledgers;
- separate absolute and process ledgers;
- durable raw artifacts; and
- `manualMetricSupplementationUsed=false`.

The schema retains nullable metrics for opaque or unobservable evidence. It
does not permit a missing measurement to become zero.

## Readiness boundary

This preflight intentionally records:

- `actualRouteObserved=false`;
- `rawEvidenceDestinationBound=false`;
- `dispatchAuthorized=false`; and
- `liveDispatchReady=false`.

Therefore a passing packet does not authorize Spark, create a real task,
verify later-hop isolation, or prove raw-evidence durability.

The next bounded result is a sequential no-dispatch runtime adapter and formal
trace evaluator with fault fixtures. That layer must bind a non-temporary raw
evidence destination and preserve the separate live-dispatch gate.

## Claim limit

This result proves only deterministic first-hop carrier isolation and exact
protocol/schema binding. It does not prove a live model route, Agent behavior,
sequential execution, automatic thread creation, later-hop isolation, process
fidelity, candidate-Skill effect, or a self-authored residual gap.
