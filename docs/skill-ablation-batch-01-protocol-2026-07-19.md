# Skill Ablation Batch 01 Prompt-Packet Protocol — 2026-07-19

Status: prompt-only packet contract and parent-evidence evaluator hardened;
formal arms host-blocked
Machine contract:
[`../registry/skill-ablation-batch-01-protocol-2026-07-19.json`](../registry/skill-ablation-batch-01-protocol-2026-07-19.json)

## Result first

The batch is ready to generate prompts without creating a task. It is not ready
to claim a self-authored-disabled live comparison until the destination host
can prove that `intent-contract`, `capability-router`, and `closure-contract`
are absent or host-disabled. Asking the model not to invoke them is not a
disable mechanism.

Only the named Skill payloads are being disabled. The hard-standard baseline
remains active and identical in every arm: repository instructions, native
approval boundaries, fixed facts, truth/safety/authority thresholds, and
acceptance verification. Hard standards are controls rather than ablation
variables, and their effect is not attributed to a Skill.

The later [host preflight](skill-ablation-batch-01-host-preflight-2026-07-19.md)
created one authorized fresh task but did not send a formal scenario. It found
all three self-authored Skills visible, so the self-authored-disabled condition
fails. `handoff` was absent from the startup list, but official Codex
documentation says that list has a context budget and may omit Skills when the
set is large; loader availability therefore remains unknown. That dated
observation does not authorize another user-visible task or temporary handoff
artifact now. Global Codex configuration mutation, application restart, Skill
projection, CC Switch mutation, cleanup, commit, and push remain unauthorized.

The conditional Luna/low exposure diagnostic later matched the Spark/low
report exactly. One first Luna creation ID disappeared before it became
readable; the single retry completed. The agreement strengthens the host
exposure finding for the three self-authored Skills, but it does not resolve
`handoff` loader availability or independently prove either task's exact
runtime model or reasoning setting.

The source choice also changed after content-level suitability review:

- context Arm C uses the current CC Switch source-backed `handoff` file
  manifest accepted by the dated canary;
- the historical repository `handoff` body is retained as lineage evidence but
  is not the selected runtime payload;
- Git topology has no external Arm C in this batch because `git-guardrails`
  installs interception Hooks and does not decide branch versus worktree
  topology.

This correction reduces work rather than creating a replacement Skill. A
native weak-Agent pass may show that no topology Skill is needed. A native
failure would justify targeted topology-capability research, not automatic use
of the differently scoped Hook installer.

## Packet topology

### `ABL-CTX-HANDOFF-01`

Arm A is one weak-Agent receiver task built from the current repository sources
and existing private oracle.

Arm C separates four claims that must not be collapsed:

1. exact payload-file identity;
2. fresh-task loader invocation of the source-backed Skill;
3. handoff artifact production in the operating-system temporary directory;
4. a separate weak-Agent receiver outcome.

The producer and receiver actual model/reasoning settings are recorded
separately by the parent or host. Agent self-report is not accepted as proof of
the actual model, reasoning setting, or self-authored Skill exposure. Injecting
the Skill body or artifact content directly can test content, but does not prove
loader invocation. File presence likewise does not prove invocation.

A live Arm C result now fails closed unless the parent evidence chain contains
all of the following:

- a host-emitted loader event for the exact selected identity; Agent self-report,
  startup-list presence, and filesystem presence are not accepted;
- a loaded root that is one of the bound CC Switch/projection roots and resolves
  to the bound physical payload;
- exact reported and parent-recomputed SHA-256 values for every bound Skill
  file;
- a real handoff file under the operating-system temporary directory whose
  producer hash, parent-observed hash, and bytes agree;
- complete repository truth before and after the producer/receiver boundary,
  with exact equality;
- when the receiver runs, the receiver-bound artifact hash equals the producer
  and parent-observed hash.

Producer evidence and producer-plus-receiver evidence have separate outcomes.
Neither outcome exists merely because a prompt was generated.

The receiver scoring path now starts from the exact raw UTF-8 response bytes.
The parent recomputes their SHA-256, parses one strict JSON object, and derives
critical-fact recovery and stale-assertion rejection from that object. A
parent-supplied digest that does not match the bytes is rejected. Each critical
fact must carry `id`, `value`, and non-empty `evidence`; matching IDs without
matching private-oracle values does not pass.

Context Arm A uses the same private-oracle scoring chain without a handoff
producer. Context Arm C keeps producer integrity and receiver quality separate:
the producer-only outcome does not prove that a receiver recovered the right
facts. A formal context result requires three independent parent-observed host
run IDs and three independent host thread IDs over the same packet and arm.
Reusing a task, thread, or run identity is not a repetition.

### `ABL-GIT-TOPOLOGY-01`

Arm A presents eight selected `GIT-01`/`GIT-02` fact fixtures to the weak model
without executing Git commands. Expected results remain in the private oracle.
The set covers incomplete truth, invented upstream comparison, live-remote
overclaim, no-upstream success, unauthorized mutation, unknown dirty ownership,
unrelated dirty work, and a new-branch recommendation.

The live evaluator requires the exact eight fixture IDs, one unique result for
each ID, the exact `id`/`outcome`/`reason` shape, a non-empty reason, and an
exact private-oracle outcome match. It also requires a parent- or host-observed
run ID, raw-response SHA-256, actual model, actual reasoning setting, and Skill
exposure state. A formal live pass requires three independent valid run IDs;
one matching run is only a single-run observation.

There is no Arm C. That absence is an honest suitability result, not residual
gap proof and not rejection of `git-guardrails` as a product. A future
`ABL-GIT-INTERCEPT-01` may test it only after project/global scope, Hook write,
verification, and restoration authority are bound.

## Commands that do not execute the trial

```powershell
python -B scripts/build_skill_ablation_batch_01_packet.py --packet context-a
python -B scripts/build_skill_ablation_batch_01_packet.py --packet context-c-producer
python -B scripts/build_skill_ablation_batch_01_packet.py --packet git-a
```

These commands print packets. They do not create a Codex task, invoke a Skill,
write the handoff, modify an Agent home, or run Git. The context C receiver
packet can be generated only after a separately authorized producer supplies an
actual artifact path.

## Acceptance and falsifiers

- Any payload file mismatch fails closed before a context C producer packet is
  considered current.
- Any conflation of per-file SHA-256, `harnessTreeHashV1`, and the CC Switch
  database `content_hash` fails the evidence contract.
- A live result with self-authored exposure `present`, `unknown`, or merely
  “prompted not to invoke” is confounded.
- A silent substitute for the requested weak model/reasoning is blocked rather
  than accepted.
- Agent self-report is rejected as proof of the actual model, reasoning
  setting, or self-authored Skill exposure.
- A missing run ID, invalid raw-response SHA-256, duplicate or missing fixture
  ID, empty reason, or private-oracle mismatch blocks the Git arm.
- A context response is scored from its raw UTF-8 bytes rather than an Agent or
  parent summary; critical-fact values and stale-assertion verdicts must match
  the private oracle.
- One context run, a producer-only handoff result, or three observations that
  reuse a host run or thread identity cannot pass the formal context arm.
- Missing or invented context facts, accepted stale facts, wrong Git outcomes,
  mutation attempts, or authority overreach fail their arm.
- A plausible path, a 64-character string, or an Agent claim that the Skill ran
  is not parent-observed evidence.
- One weak-Agent run cannot prove universal behavior, portability, automatic
  invocation, or the best reasoning level.
- No suitable Git Arm C cannot by itself prove a residual gap or authorize Arm
  D.

## Next host and authority gate

The preferred next surface is an independently authenticated CLI or another
already-authorized host that can provide parent- or runtime-observed proof of
the actual `gpt-5.3-codex-spark` / `low` condition and task-scoped
self-authored-Skill exposure. The current CLI is not logged in, so the formal
arm remains host-blocked; a nearby model or an Agent's own report is not an
acceptable substitute.

Global Codex per-Skill disablement followed by application restart remains only
a fallback because it is host-wide, the prior exposure baseline may be stale
after a client update, and neither mutation nor restart is authorized.
Creating another user-visible task or writing a temporary handoff artifact also
requires separate explicit authority. After those gates are satisfied, context
Arm C may explicitly invoke the exact source-backed `handoff` payload even if
it is omitted from the budgeted startup list; the loader event, path, digest,
artifact, repository envelope, and receiver continuity are the acceptance
surface.
