# Self-authored control-chain carrier audit — 2026-07-28

## Result

The current `intent-contract -> capability-router -> closure-contract` chain
remains a falsifiable upstream candidate. Its presence, manual selection, and
current-thread reading do not establish maturity, implicit-loader reliability,
weak-Agent value, or a residual gap. No Skill installation, update, deletion,
replacement, retirement, CC Switch change, model dispatch, commit, or push is
authorized by this audit.

The main premise risk is not one obviously incorrect rule. It is duplicated
authority and process cost across global rules, two user Skill roots, divergent
CC Switch copies, an active advisory Hook, host discovery, and handoff or
compression fallbacks. A locally correct answer can hide that chain-level
redundancy.

## Current carrier truth

The `.agents` and `.codex` copies are byte-equal for all three current Skills:

| Skill | Current bytes | Current SHA-256 |
| --- | ---: | --- |
| `intent-contract` | 29,139 | `1d67e4b84856bcd0828d89b82803a7275d95d8e586fd8efcd127f89e82845753` |
| `capability-router` | 22,018 | `eb9f7d253d12682a3e8b9f87faf5bad4284a2d268b25c30cc5ad9f6dd36eb8fe` |
| `closure-contract` | 12,187 | `59edfc131c45b7aa1ef85a1737317a0cc97adcfb0ddceb7ee81e9c744b13bbb3` |

The CC Switch bodies are different and shorter: 23,075, 16,581, and 7,872
bytes with distinct hashes. They are older common ancestors rather than
current byte-equal projections. This proves current consumer divergence; it
does not identify which copy is behaviorally superior or authorize a migration.

Body identity is not the complete package identity. `intent-contract` also
depends on `references/intake-contract.md` (20,948 bytes,
`66e3990e...92b93`) and `capability-router` on
`references/routing-contract.md` (10,108 bytes, `17d7ef38...90c3b`).
Both references are byte-equal across `.agents` and `.codex`, while their CC
Switch counterparts are shorter and byte-distinct. Any exact-chain exposure
must therefore project five files, not just the three `SKILL.md` bodies.

The current startup-visible catalog presents each logical Skill from both
`.agents/skills` and `.codex/skills`. That is parent-visible discovery evidence,
not an independent loader event. Duplicate names and equal bytes may still
consume discovery budget or create path ambiguity; no benefit is credited.

## 2026-07-29 owner recalibration

`~/.agents/skills` is a retained common compatibility root. It must not be
cleared or removed merely to deduplicate the current Codex projection because a
future Agent may use the common root. Root retention and payload retention are
separate decisions: physical Skill bodies and managed links remain eligible for
item-level authority, overlap, and loader review.

Codex and Claude are distinct hosts, so byte-distinct effective packages are
not inherently a defect. Portable semantics, source lineage, and each host
adapter's contract must converge; host-specific bodies may differ when the
difference is deliberate, bounded, and verified.

This Codex turn exhibits behavior consistent with implicit Skill selection, but
it cannot attribute that behavior to a native runtime capability. Global
`AGENTS.md` rules, the self-authored Skill chain, the startup-visible Skill
inventory, and runtime trigger instructions are present and may act alone or in
composition. A 2026-07-29 live recheck found `hooks.json={}`, so the earlier
registered-Hook observation is historical and is not a current competing cause.
The mixed-carrier turn still cannot prove either that native Codex supersedes
the chain or that the chain caused the behavior.

That bounded capability question is now resolved by a separate current-host
sentinel ablation. Official Codex documentation states that implicit invocation
matches the Skill `description`, defaults
`allow_implicit_invocation` to `true`, and reads the full `SKILL.md` after
selection. On Codex `0.145.0`, two fresh ephemeral read-only CLI tasks used the
same prompt under a temporary `CODEX_HOME`. This excluded the live global
`AGENTS.md`, Codex-private Skill copies, configuration, and Hooks; the three
self-authored `.agents` Skills were temporarily moved out while the common root
remained present. The no-sentinel control returned a normal receipt and did not
emit the private token. The sentinel treatment visibly read the full body and
returned exactly `PURPLE_COMPASS_RECEIPT_7D29`, a token absent from its
description. Both tasks used `gpt-5.6-sol`, provider `openai`, reasoning
`none`, approval `never`, and read-only sandboxing.

This proves current-host native implicit discovery, semantic selection, and
full-body reading. It does not retroactively attribute the earlier mixed-carrier
turn, prove universal trigger reliability, establish the value of any current
self-authored Skill, or satisfy the Desktop app-server exact-chain factorial
contract. The three moved Skills were restored by tree digest; the sentinel and
temporary authentication copy were removed.

The global Codex `AGENTS.md` is 62,363 bytes and 1,077 lines. Exact normalized
overlap with the current Skill bodies includes 73/36, 28/12, and 10/2 shared
lines/three-line windows for intent, routing, and closure respectively. The
shared hard boundaries are expected controls, but they prevent crediting a
Skill merely because the final answer obeyed the same rule.

## Hook finding

On 2026-07-28, `C:\Users\15521\.codex\hooks.json` registered the
capability-router command on `UserPromptSubmit`. Its recorded policy was
`status=candidate`, `mode=auto`; it may inject advisory context but may not deny
permission or mutate external state, denies external transmission, and fails
open on handler error.

One bounded positive synthetic prompt emitted 428 bytes of routing context in
about 1.2 seconds. One negative prompt emitted nothing in about 1.6 seconds.
One sample per class cannot establish stable latency or false-positive rates,
but it disproves the weaker assumption that the Hook is merely dormant. Its
recall value, context cost, per-prompt latency, trigger precision, and
interaction with the full `capability-router` Skill require a separate
Hook-off versus Hook-auto treatment.

The 2026-07-29 live recheck found the file still present but containing `{}`,
zero files under `C:\Users\15521\.codex\hooks`, and one historical
`hooks.state` entry in `config.toml`. There is no current Hook registration.
The directory and state row are residue, not invocation or active-policy
evidence.

## Native, official, and reviewed-external comparison

- Native/hard-only behavior already owns mandatory source binding, repository
  posture, permission, and honest-status floors. `intent-contract` and
  `closure-contract` overlap materially with those controls.
- `capability-router` claims a broader cross-ecosystem role than Matt
  `ask-matt` or Superpowers `using-superpowers`, but that ownership is a design
  claim. The external routers remain bounded subflows, and no live comparison
  proves the repository router's net value.
- Current runtime-owned Superpowers `6.2.0` is a source/package baseline, while
  bound behavior remains historical or scenario-specific. Its
  `verification-before-completion`, planning, review, and worktree flows
  overlap parts of closure and engineering execution without replacing the
  cross-task evidence boundary by name alone.
- Current Matt `grilling + domain-modeling` now has exact eight-file,
  dependency-complete task-scoped exposure. That closes exposure only; it does
  not prove loader delivery or semantic-continuity value. Matt `handoff`
  remains the source-backed continuation candidate, not evidence that fresh
  sessions invoke or recover from it.

The current evidence therefore supports no winner. The subtraction order stays
native/runtime, official, reviewed external, composition, then only an
evidenced residual self-authored gap.

## Host loading, compression, and handoff

The focused 60-test overlap, instruction-carrier, handoff-loader, and
context-pressure set passes. Those are deterministic contract checks. Current
host evidence still separates:

- file and catalog visibility;
- exact task-scoped exposure;
- independent loader invocation;
- instruction delivery;
- behavioral adherence;
- causation and value.

The current chain has evidence for the first two surfaces only in bounded
contexts. Automatic compression telemetry and automatic thread creation remain
unproved. The source-backed handoff CLI probe remains blocked on a task-bound
loader identity/digest event. This task's successful repository-first intake
shows that `CONTINUATION.md` can be used as a navigation carrier; it does not
prove automatic host continuity or receiver recovery.

After the evidence record was added, the exact temporary projection root and
temporary report were removed; the byte-equal durable report remains under
`audits/`. The updated 23-test SEM-03 projection, exposure, protocol, and audit
set passes, and `python -B scripts/verify.py` passes after the cleanup-debt
inventory returned to its governed state. These are local verification results,
not remote CI, release, loader, or behavioral evidence.

## Decision

Keep the common `.agents/skills` root and all current payloads unchanged while
evidence is gathered. The next bounded experiment should reuse the existing
`INT`, `ROUTE`, and `CLOSE` packets and preregister two independent variables:

1. hard-only native versus the exact current three-Skill chain;
2. Hook off versus Hook auto.

Measure loader evidence, prompt-context bytes, latency, hard-oracle outcome,
authority errors, unnecessary questions or capability calls, failure fallback,
and repeated-context loss separately. A chain pass cannot credit the Hook, and
a Hook recall cannot prove the full Skill was loaded. No portfolio mutation is
eligible from this audit.

The factorial protocol, isolated Hook-mode preflight, and run-evidence adapter
now close the offline preregistration and evidence-shape steps. The next
bounded host step must first materialize the five-file dependency-complete
current chain before attempting no-model four-cell exposure.

The native implicit-invocation capability question no longer needs another
fresh-task repetition before design review. The next self-authored decision
must instead identify which semantics, reliability, cross-host portability, or
failure fallback remain incrementally useful over the verified native baseline.
The frozen exact-chain factorial remains separate because it asks for
candidate-specific value attribution, not native capability existence.

The machine-readable record is
[`registry/human-ai-collaboration-self-authored-control-chain-carrier-audit-2026-07-28.json`](../../registry/human-ai-collaboration-self-authored-control-chain-carrier-audit-2026-07-28.json).
