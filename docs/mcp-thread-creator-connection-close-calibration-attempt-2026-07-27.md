# MCP Creator-Connection-Close Calibration Attempt

Date: 2026-07-27
Status: invalid before paired window; compact authority and runner-prerequisite evidence retained

## Outcome

One calibration command started the `connected-control` isolated app-server
arm but stopped before either five-second paired observation window. The runner
waited 30 seconds for a zero-model-turn thread rollout file that did not
materialize. That prerequisite was not part of the protocol's validity oracle
and cannot be treated as an MCP release or retention outcome.

No `pair-report.json` was generated. The local Sentinel emitted one exact
`instance-start` and one exact `instance-stop`; its PID was absent during the
post-failure inspection. The wider command-line process-family inspection was
denied by the host, so broader orphan absence is not proved.

## Authority incident

The protocol record had
`loopbackTransportExecutionAuthorized=false`. Starting even a pre-window
loopback calibration crossed that local protocol boundary. The attempt did not
reach a formal paired window and does not authorize another run. A fresh
calibration or formal repetition requires explicit authorization for this
specific loopback live-host execution boundary.

## Offline remediation

The attempted runner source is bound only by its attempt-time SHA-256
`98B248688F98DECB35AE0B1F34DB4AA2DA819ED7DDF91BA3E4AC1C707AFCAC6`;
it is not the identity of the remediated probe. The current probe SHA-256 is
`66CF7066B68D92139653C5E41AD74CAA64D00273C662A2899E396501974C2CF6`.

The probe no longer calls `wait_for_rollout` as a zero-turn prerequisite.
Rollout presence is recorded as an observation after the observer connection's
configuration barrier. A deterministic regression test requires an absent
rollout to return `observed=false` instead of raising. No live rerun was
performed after this correction.

## Cleanup and claim boundary

The two exact repository-local roots were originally retained:
`.tmp/mcp-creator-close-calibration-20260727-01` and
`.tmp/mcp-creator-close-calibration-workspace-20260727-01`.
The 2026-07-30 cleanup transaction removed them together with the other exact
repository-local temporary roots. Before deletion, all five Sentinel events
and the isolated configuration semantics were normalized into
`audits/mcp-thread-creator-connection-close-calibration-attempt-2026-07-27/normalized-evidence.json`.
The compact record keeps the original byte counts and hashes while excluding
raw runtime state, machine-absolute paths, and secret material. The cleanup
transaction is governed by
`registry/closeout-cleanup-execution-2026-07-30.json`.

This invalid calibration proves no creator-connection-close release or
retention, task end, final-owner behavior, lease or reference count, resource
benefit, arbitrary-MCP behavior, cross-host behavior, or need for a
self-authored controller.
