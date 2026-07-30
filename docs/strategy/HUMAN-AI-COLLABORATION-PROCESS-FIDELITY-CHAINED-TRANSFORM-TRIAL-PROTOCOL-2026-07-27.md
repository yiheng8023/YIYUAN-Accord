# Human-AI Collaboration Process-Fidelity Chained-Transform Trial Protocol

Date: 2026-07-27
Status: preregistered zero-dispatch design
Authority: local protocol design only

## Outcome

The smallest future process-fidelity trial is now frozen as an observable
artifact chain. Each Agent output becomes the next material input. The
protocol does not infer continuity from acknowledgements, a shared
conversation, terminal correctness, or hidden model state.

The formal process cohort starts from zero. The earlier source-backed smoke is
transport evidence and is not eligible for this cohort.

No Agent or model call was made while creating or validating this protocol.
The design does not authorize live execution.

## Chain

The frozen chain is:

```text
S0
-> weak Agent: decomposition -> O1
-> deterministic parent transcriber -> M1
-> weak Agent: routing -> O2
-> deterministic parent recovery gate -> R2(O2 + S0 + receipt)
-> weak Agent: acceptance and source-backed recovery -> O3
```

The control transcriber makes a canonical identity copy. The injected arm
removes only the `authority` invariant and its matching provenance from the
persisted fidelity snapshot. The mutation ledger must prove that exact delta;
any additional change invalidates the run.

Hop 2 receives only `M1`. The parent then creates one declared recovery
envelope containing exact `O2`, the explicit source anchor `S0`, and a trigger
receipt bound to `O2`. Hop 3 receives only that single envelope. No Agent hop
may use tools, shared conversation state, hidden earlier messages, or an
undeclared artifact.

Every material edge records predecessor and input artifact identities and
hashes. A mismatch fails closed. An opaque material edge remains unknown and
invalid; it cannot be scored as zero loss.

## Two ledgers

The absolute and process ledgers remain separate.

The absolute ledger asks whether the terminal output matches the frozen source
and acceptance oracle. The process ledger records per-hop invariant survival,
omissions, changed values, assumptions, provenance breaks, authority drift,
detection evidence, downstream impact, amplification, and recovery distance.

Terminal source-backed recovery therefore cannot erase an intermediate loss.
A locally correct final answer cannot override a process failure.

## Cohort and order

The weak-Agent primary route is `gpt-5.3-codex-spark` at `low` reasoning. The
exact route must be observed immediately before dispatch; no fallback model may
silently replace it.

There are four repetitions per arm and eight formal runs. Four paired blocks
use `AB`, `BA`, `BA`, `AB`, so each arm occurs first twice and second twice.
Every Agent hop is a fresh, parent-controlled invocation. This does not claim
that a host automatically creates a thread.

The cohort is exploratory and descriptive. Even a full pass cannot prove
statistical superiority, universal model behavior, cross-host portability, or
end-to-end process fidelity outside this frozen scenario.

## Weak and strong Agent roles

Weak-Agent performance is the primary acceptance surface. A named failed weak
run may trigger a separately authorized `gpt-5.6-luna`/`low` diagnostic using
the same packet and stage contract.

The strong-Agent diagnostic cannot rescue a weak-Agent failure, enter the
primary cohort, or change the frozen result. It is only an attribution aid for
distinguishing likely protocol ambiguity from model-capacity sensitivity.

## Acceptance and stops

The control arm requires all four runs to preserve every invariant without a
false detection. The injected arm requires all four runs to:

- detect the declared loss within one material hop;
- avoid adding assumptions or causing authority drift;
- avoid amplification above `1.0`;
- preserve exact output-to-input linkage;
- recover from the declared source anchor at the final hop; and
- retain the intermediate loss in the process ledger after terminal recovery.

The protocol stops on route drift, protocol or source drift, unexpected input
or tools, linkage mismatch, mutation drift, opaque edges, invalid detection,
late authority-loss detection, amplification, recovery mismatch, or inability
to preserve raw artifacts durably.

Invalid runs are not silently discarded. Any replacement needs a recorded
cause and a fresh run identity.

## Future boundary

Before a future run, a zero-dispatch packet builder and validator must bind the
exact protocol hash, source, stage contracts, model route, run order, and
non-temporary raw-evidence destination.

That future step requires separate live-dispatch authorization. It does not
inherit install, global configuration, cleanup, commit, push, publication, or
account authority from this design.

## Claim limit

This protocol proves only that a concrete, falsifiable chained-transform
experiment has been preregistered and statically validated. It does not prove
live Agent behavior, process-fidelity success, candidate-Skill value,
automatic compression, automatic thread creation, delivery-topology effects,
cross-host portability, or a residual need for a self-authored capability.
