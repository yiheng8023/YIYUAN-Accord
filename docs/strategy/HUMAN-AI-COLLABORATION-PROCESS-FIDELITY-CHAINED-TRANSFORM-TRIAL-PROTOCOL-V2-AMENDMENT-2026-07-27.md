# Human-AI Collaboration Process-Fidelity Chained-Transform Protocol v2 Amendment

Date: 2026-07-27

Status: preregistered, zero dispatch

## Why the amendment exists

The v1 protocol correctly froze the source, weak-Agent route, two arms,
position-balanced order, metrics, and claim limits. Its recovery-envelope
wording nevertheless allowed the exact `S0` payload to be present
unconditionally. That makes a terminal restoration ambiguous: the last hop
could recover from the source even when the prior hop never produced a valid
detection receipt.

This amendment preserves the v1 protocol by hash and changes only the recovery
gate and the raw-capture/evaluation boundary.

## Recovery gate

The parent always retains an `S0` identity and digest. It exposes the `S0`
payload to the final hop only when the parent recomputes the hop-2 active loss
set and finds an exact, non-empty match in the hop-2 detection marker.

- A control run forwards the predecessor and a sealed source reference.
- A valid injected run may receive the unsealed source payload.
- An empty, partial, excessive, or otherwise invalid detection marker stops the
  sequence before hop 3.
- A terminal source match cannot erase an intermediate process loss.

## Raw capture before scoring

The sequential artifact adapter writes raw artifacts and parent-computed
receipts before evaluation. The evaluator ignores any Agent- or fixture-supplied
metrics and recomputes all scores from persisted artifacts plus the parent-only
oracle.

Zero-model scripted captures are calibration evidence only. They do not prove
the requested Spark route was observed, do not start the formal cohort, and do
not establish live Agent behavior or end-to-end acceptance.

## Unchanged boundaries

The weak primary route remains `gpt-5.3-codex-spark` with `low` reasoning for a
future separately authorized live run. Automatic fallback remains forbidden.
The formal cohort count remains zero. No installation, global configuration,
external access, commit, push, publication, deletion, or cleanup is authorized
by this amendment.
