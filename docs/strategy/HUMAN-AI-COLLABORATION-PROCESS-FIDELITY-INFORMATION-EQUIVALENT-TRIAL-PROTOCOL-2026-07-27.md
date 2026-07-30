# Human-AI Collaboration Process-Fidelity Information-Equivalent Trial Protocol

Date: 2026-07-27

Status: preregistered offline contract; live three-arm trial not executed

## Purpose

This protocol isolates one question: when the task information is identical,
how does delivery topology affect a weak Agent's process fidelity?

It reuses the existing `GEN-RESEARCH-01` synthetic conflicting-claims fixture,
its private claim oracle, the weak-Agent route contract, the context
continuation authority boundary, and the multi-hop process-fidelity metrics.
It does not create a new capability manager, lifecycle controller, domain
fixture, or candidate-Skill comparison.

## Frozen comparison

All three arms use:

- the same four source records and five public claims to assess;
- one parent-owned private oracle of expected states and source sets, frozen
  before dispatch;
- `gpt-5.3-codex-spark` at `low`, with the actual route revalidated;
- the same no-network, no-account, no-write, no-MCP/App/Plugin/Skill boundary;
- the same structured result and protocol-local hard gates;
- at least three valid repetitions per arm, each in a fresh task.

The only allowed difference is the delivery topology:

1. `complete-single-turn`: all public information arrives in one turn.
2. `same-thread-incremental-information`: the same four sources arrive as
   preregistered shards in one task; the Agent must acknowledge without
   analysis until the unchanged run instruction arrives.
3. `source-backed-fresh-session-recovery`: a deterministic parent-owned
   artifact contains the same public instruction and sources; a separately
   authorized fresh task receives its stable locator and reads it.

Information equivalence is judged by canonical fact identity, value, source
lineage, authority class, and applicability, not by raw prompt-byte equality.
Any missing, added, stale, or differently authorized fact fails before
dispatch with zero trial calls.

## Why the scope is narrow

`GEN-RESEARCH-01` is the only scored domain scenario.
`XCR-01-process-fidelity-and-loss` supplies the cross-cut.
`CTX-04` and `CTX-05` constrain the source-backed recovery and fresh-task
authority surfaces. `HR-05-reversibility-recovery-and-continuity` is bound at
the protocol level because recovery and opaque-edge stopping require it.

The protocol does not bind:

- `CTX-02`: incremental turns are not automatic compression;
- `CTX-03`: this is not a context-pressure heuristic trial;
- `CTX-06`: consuming a source-backed artifact is not evidence that the
  `handoff` Skill loaded or ran;
- `CTX-07`: one Codex-host trial is not cross-Agent instruction adherence.

The primary program acceptance link remains
`acceptance.end-to-end-process-fidelity`, which stays `partial`.

## Measurement and falsifiers

Terminal scoring reuses exact claim IDs, states, source sets, unsupported
conclusions, external access, and write checks. Process scoring records
invariant survival, weighted omission, added assumptions, provenance breaks,
authority drift, detection latency, amplification, recovery distance, and
rollback.

A matching final answer does not erase intermediate process loss. An earlier
authority drift, provenance break, unsupported assumption, invalid recovery,
or opaque material edge remains a process-fidelity failure.

The comparison stops without ranking or evidence promotion when:

- an arm projects a different information manifest or oracle;
- model, effort, tools, workspace, threshold, or ambient history differ;
- private-oracle content reaches a public message or source-backed artifact;
- any arm has fewer than three valid repetitions;
- an arm or material host edge is opaque;
- the requested weak-model route is unavailable and would require
  substitution.

## Host and authority boundary

Every live task requires separate applicable creation authority. Manual or
parent-authorized fresh-task creation may prove only that manual path. It
cannot prove automatic thread creation. Likewise, source-backed artifact
consumption cannot prove automatic compression, an automatic recovery
decision, or `handoff` Skill invocation.

Claims about automatic compression, automatic task creation, or Skill
invocation require their own native event or loader evidence. Missing evidence
is `opaque-or-unproved-not-inferred`.

## Claim limits

This artifact proves only that an offline three-arm contract has been
preregistered and can be validated. It does not prove:

- live three-arm behavior or lossless fresh-session recovery;
- a universal best context percentage, turn count, or compression threshold;
- automatic compression or automatic task creation;
- `handoff` Skill discovery, loading, invocation, or causal effect;
- cross-host portability or broad weak-model ordering;
- Matt, Superpowers, CC, or self-authored capability superiority;
- a residual gap that justifies new self-authored runtime capability;
- real-domain research quality, software-lifecycle coverage, or long-term
  human skill retention;
- verified end-to-end process fidelity or a matrix evidence-state promotion.

The next bounded step is offline validation and rejection testing. A later
packet builder and preflight should reuse existing components and must obtain
separate live task-creation authority before dispatch.

## Local packet preparation

The minimal packet builder and preflight are now implemented. They create only
three temporary public package files: the frozen public information bundle,
the three-arm packet, and a build manifest. The private oracle remains a
parent-owned fingerprint; its content is not written into any public carrier.

The preflight recomputes the source, public claims, task instruction, public
bundle, protocol, and private-oracle fingerprints. It rejects source,
information, oracle, model, arm, authority, locator, package, or manifest
drift with zero dispatch and zero scored arms. This proves local package
construction and fail-closed preparation only. It is not a three-arm runner
and not live Agent evidence.

The existing read-only research app-server runner is now parameterized for
these information arms. It reuses session handling, configurable-Skill
disablement, MCP isolation, read-only and no-network sandboxing, response
parsing, oracle scoring, tree checks, and configuration checks. The
incremental arm adds only the preregistered ACK and final-response sequence;
the source-backed arm alone permits observable read-only command items inside
the isolated public packet root.

The adapter defaults to no live dispatch. With no exact authorization it
builds and validates the package, returns
`blocked-live-task-creation-authority-required`, and records zero dispatch and
zero scored arms. When a live run is separately authorized, the reused runner
must verify the actual `gpt-5.3-codex-spark/low` route after ephemeral task
creation but before the first task turn. A mismatch stops before task
dispatch; provider fallback remains forbidden.

No live runner execution has occurred. The next step is repository-wide
validation, followed by one exact cohort-level live authority and route-health
gate.
