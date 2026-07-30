# Human-AI Collaboration Process-Fidelity Information-Equivalent Trial Protocol V2

Date: 2026-07-27

Status: one absolute-task-valid v2 source-backed transport smoke; live
three-arm cohort not executed

## Purpose

This protocol isolates one question: when the task information is identical
and the task semantics are explicit, how does delivery topology affect a weak
Agent's terminal task fidelity?

V1 stopped after one calibration dispatch. Its state labels,
`unsupportedConclusionCount`, and exact source-set semantics were ambiguous,
and its source-backed design did not prove that the Agent could read only the
public bundle. V1 remains historical host/runner diagnostic evidence; zero v1
runs can enter this v2 cohort.

V2 uses a versioned `GEN-RESEARCH-01` synthetic fixture, a parent-only private
oracle, the weak-Agent route contract, and a parent-scoped public-bundle reader.
It does not create a capability manager, lifecycle controller, candidate-Skill
comparison, or general filesystem reader.

This is a delivery-topology and absolute-task-fidelity subprotocol. It does
not produce a process-hop ledger or cascade measurement, because no Agent
output becomes the next material transform's sole input. It cannot by itself
satisfy end-to-end process-fidelity acceptance. A separate chained
output-to-input trace contract must complement it.

## Frozen comparison

All three arms use:

- the same four source records and five public claims to assess;
- an explicit semantic contract: `supported` requires entailment,
  `contradicted` requires entailment of the logical negation, and all other
  cases are `unknown`;
- public `requiredSourceIds` that must be copied unchanged, so source-set
  selection is not a hidden second task;
- an explicit definition that `unsupportedConclusionCount` counts only extra
  assertions outside the five requested claim classifications and therefore
  must be zero;
- one parent-owned private oracle of expected states and source sets, frozen
  before dispatch;
- `gpt-5.3-codex-spark` at `low`, with the actual route revalidated;
- the same no-network, no-account, no-write, no-shell,
  no-MCP/App/Plugin/Skill boundary;
- the same structured result and protocol-local hard gates;
- at least three valid repetitions per arm, each in a fresh task.

The protocol keeps three identities separate:

- `fixtureId=fixture.synthetic-conflicting-claims-v2` identifies the fixed
  task and source content;
- submission `armId=GEN-NATIVE-SPARK` identifies the fixed native weak-model
  treatment and must be echoed unchanged by every topology;
- parent-side `informationArmId` identifies complete, incremental, or
  source-backed delivery.

These identities cannot substitute for one another. The Agent does not choose
the parent-side delivery topology.

The only allowed difference is the delivery topology, including the scoped
public-bundle read transport intrinsic to the source-backed arm:

1. `complete-single-turn`: all public information arrives in one turn.
2. `same-thread-incremental-information`: the same four sources arrive as
   preregistered shards in one task; the Agent must acknowledge without
   analysis until the unchanged run instruction arrives.
3. `source-backed-fresh-session-recovery`: a deterministic parent-owned
   package projects only the public bundle into an Agent-visible root; a
   separately authorized fresh task receives its stable locator and retrieves
   it through exactly one parent-scoped dynamic read tool.

Information equivalence is judged by canonical fact identity, value, source
lineage, authority class, and applicability, not by raw prompt-byte equality.
Any missing, added, stale, differently authorized fact, unregistered tool,
parent-evidence exposure, or carrier/oracle isolation failure stops before
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

Scoring uses two ledgers that cannot cancel each other.

The absolute task ledger records exact claim IDs, states, required source sets,
unsupported conclusions, external access, writes, authority violations, and
oracle-isolation gates. Any hard failure blocks task acceptance.

The relative process ledger is the required comparison boundary, but the
current runner does not yet produce it from frozen per-edge events. A future
eligible cohort must record invariant survival, weighted omission, added
assumptions, provenance breaks, authority drift, detection latency,
amplification, recovery distance, rollback, and opaque edges. It must report
raw per-run and paired differences rather than a synthetic total score.
Relative improvement cannot rescue an absolute weak-Agent failure.

A matching final answer does not erase intermediate process loss. An earlier
authority drift, provenance break, unsupported assumption, invalid recovery,
or opaque material edge remains a process-fidelity failure.

The comparison stops without ranking or evidence promotion when:

- an arm projects a different information manifest or oracle;
- model, effort, tools, workspace, threshold, or ambient history differ;
- private-oracle content reaches a public message or source-backed artifact;
- the parent evidence root appears in a runtime workspace root;
- a source-backed task uses shell or command execution, omits the scoped
  reader, calls it more than once, or receives a nonmatching public-bundle
  hash;
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

This artifact proves only that a corrected offline v2 three-arm
delivery-topology contract has been preregistered and one source-backed
transport smoke passed its terminal oracle. It does not prove:

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

The zero-Agent chained-trace calibration passed: frozen controlled
transcriptions exposed predecessor linkage failure, cascading amplification,
non-erased intermediate loss after terminal restoration, and opaque material
edges without any model call. It did not make the existing smoke
process-trace-valid.

The raw-event trace adapter then assessed the durable record without manual
supplementation. The existing smoke is process-trace ineligible: its
source-read-to-response transform is an opaque material edge and no
process-hop ledger exists. It remains a transport pilot; any later formal
process cohort starts from zero.

The next bounded step is to design the smallest future frozen
chained-transform protocol and balanced order without dispatch. Every later
live task still requires separate applicable creation authority.

## Local packet preparation

The packet builder and preflight must create a parent evidence root containing
the frozen public bundle, three-arm packet, and build manifest. The runtime
workspace is a distinct Agent-visible root: it is empty for direct and
incremental arms and contains only `PUBLIC-SOURCE-BUNDLE.json` for the
source-backed arm. The private oracle remains parent-owned and its content is
not written into either public carrier.

The preflight recomputes the source, public claims, task instruction, public
bundle, protocol, private-oracle, Agent-visible file-set, and scoped-reader
fingerprints. It rejects source, information, oracle, model, arm, authority,
locator, package, runtime-root, or manifest drift with zero dispatch and zero
scored arms. This proves local construction and fail-closed preparation only;
it is not live Agent evidence.

The existing read-only research app-server runner remains the host transport.
It must report the actual public bundle, turn-plan, per-turn text hashes,
input mode, visible-root file set, and private-oracle isolation proof rather
than inheriting metadata from an unused default prompt. The incremental arm
adds only the preregistered ACK sequence. The source-backed arm may expose one
dynamic tool named `read_public_information_bundle`; command execution remains
forbidden in every arm.

The adapter defaults to no live dispatch. With no exact authorization it
builds and validates the package, returns
`blocked-live-task-creation-authority-required`, and records zero dispatch and
zero scored arms. When a live run is separately authorized, the reused runner
must verify the actual `gpt-5.3-codex-spark/low` route after ephemeral task
creation but before the first task turn. A mismatch stops before task
dispatch; provider fallback remains forbidden.

One live v2 calibration dispatch occurred after repository-wide validation,
and it is excluded from all arm counts. The scoped dynamic tool was called
exactly once with the required locator and canonical hash, the runtime read
boundary passed, all five claims and non-identity oracle fields matched, no
command or file change was observed, and the visible tree and global
configuration stayed stable.

The dispatch nevertheless failed the measurement contract because the
source-backed renderer omitted the fixed submission `armId` instruction that
the complete and incremental renderers append. The Agent returned the visible
`fixtureId` as `armId`, producing the sole historical failure `unknown-arm`.
This is a renderer-calibration failure, not a weak-Agent or scoped-read
failure. It consumes one smoke dispatch and counts as zero valid arms.

The correction declares `fixtureId`, submission `armId`, and parent-side
`informationArmId` separately; every rendered topology must state the same
submission arm, and identity substitution now has a negative test. The single
v1 calibration run and this first v2 smoke remain quarantined. The corrected
runner passed focused, repository-wide, and zero-dispatch revalidation before
one replacement source-backed smoke was separately authorized.

That replacement smoke passed the frozen absolute oracle, called the scoped
dynamic reader exactly once with the required locator and hash, and preserved
the observed read-only tree and configuration boundary. It counts as one
absolute-task-valid transport repetition out of three required for the
source-backed arm. It is not a process-trace-valid repetition. Complete and
incremental topologies remain unrun, no information arm is complete, and no
relative process-fidelity comparison exists. The evidence stop is now active;
no wider cohort may start from this record.
