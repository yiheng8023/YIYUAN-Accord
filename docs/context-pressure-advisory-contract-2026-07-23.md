# Context Pressure Advisory Contract — 2026-07-23

Status: verified local classifier and fixtures; no live-host pressure evidence.

This is a default-no-action, offline contract. It classifies evidence that may
justify a recommendation or a request for a user decision. It never compacts a
thread, creates a thread, invokes a Skill, changes configuration, or changes a
repository.

## Signal provenance

The only values are `direct-counter`, `host-event`, `heuristic`,
`user-observed`, and `unknown`.

- Direct counters and host events enter `EVALUATE`.
- Heuristics and user observations enter `HEURISTIC_EVALUATE`.
- Absent or unsupported evidence enters `UNKNOWN`; it is not synthetic
  telemetry.

No fixed context percentage, best-efficiency interval, or cross-host threshold
is defined by this contract.

A future live observation must additionally record the exact host, version,
profile, evidence source, value, unit, timestamp, parent run identity, delivery
observation, action authority, and the post-handoff private-oracle result. A
direct counter still does not define a universal percentage; a compact event
does not prove token usage; a heuristic is not telemetry; and a user report is
not a host metric.

## States and authority

`OBSERVE` leads to `EVALUATE`, `HEURISTIC_EVALUATE`, or `UNKNOWN`. Evaluation
then leads to `CONTINUE`, `RECOMMEND_HANDOFF`, or
`REQUIRE_USER_DECISION`. A handoff recommendation or required decision reaches
`WAIT` unless both explicit thread-creation authority and an existing CTX-04/05
packet are present. Only then is `HANDOFF_PACKET_READY` recorded.

`HANDOFF_PACKET_READY` means only that the existing repository-anchored
CTX-04/05 packet may be used at its separate live-thread authorization gate. It
does not create the thread or prove a host action.

## Hard claim firewall

The classifier hard-fails claims of automatic thread creation, lossless
handoff, cross-host parity, a fixed universal context percentage, or treating
Terra as weak-Agent acceptance. Terra remains diagnostic-only; a local fixture
does not substitute for a Spark/low live weak-Agent arm.

## Evidence boundary

The twelve fixtures exercise direct, event, heuristic, user-observed, and
unknown paths; unauthorized wait behavior; packet readiness; and all hard
claim failures. They prove only deterministic contract behavior. Live host
work must separately observe actual counter/event delivery, units and timing,
automatic-compaction behavior, retention quality, user-intervention effects,
and any supported thread action for that exact host and version.
