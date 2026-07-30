# Skill Ablation Batch 01 Selection — 2026-07-19

Status: scenario selection reconciled and exact payload bound; current
research/PoC phase; no live thread, temporary Agent home, Skill installation,
Git mutation, cleanup, commit, or push authority
Machine record:
[`../registry/skill-ablation-batch-01-selection-2026-07-19.json`](../registry/skill-ablation-batch-01-selection-2026-07-19.json)

## Why this batch

The first batch tests collaboration failures already bound by the main PoC
matrix and uses payloads with known source authority. It does not search for or
install more Skills. Repository-authored `intent-contract`,
`capability-router`, and `closure-contract` must be absent or host-disabled in
Arms A through C and are deferred to the later self-authored comparison arm. A
prompt that merely asks the Agent not to invoke them does not prove that the
host did not load them; a present or unknown exposure makes the live result
confounded rather than a self-authored-disabled baseline.

That exposure gate isolates the upstream Skill variable only. It does not turn
off AGENTS/rules, native approval enforcement, fixed scenario facts, or the
truth, safety, authority, and acceptance thresholds shared by every arm. Those
hard standards are the experiment control and are never credited as Skill
value. This is the original design invariant, not a new arm or architecture.

The external Arm C payloads are reuse and comparison baselines, not a decision
to keep third-party payloads in the final repository product body. Their result
determines whether a self-authored control Skill is unnecessary or whether a
repeatable residual gap remains for Arm D.

## Weak-Agent floor and conditional diagnostic

| Condition | Requested host selection | Purpose |
| --- | --- | --- |
| Weak-Agent floor | user-proposed `gpt-5.3-codex-spark` (`5.3 Spark`), lowest supported reasoning; currently requested as `low` | Primary acceptance condition for the self-authored-disabled counterfactual and any later repository-authored Arm D. |
| Capacity diagnostic | `gpt-5.6-terra`, `low` reasoning | Run only when a weak-Agent failure or ambiguous result needs capacity-versus-protocol attribution. |

The destination host must revalidate the requested model identifier and actual
reasoning setting at creation. A rejected combination is recorded as blocked;
no nearest model or higher reasoning level is silently substituted. The weak
arm may be shorter or less polished, but it receives the same critical-fact,
stale-fact, and zero-authority-overreach thresholds. A capable diagnostic is
not a universal second run and cannot substitute for weak-Agent evidence when
a repository-authored Skill is considered for admission.

## `ABL-CTX-HANDOFF-01`

Goal: recover a repository-anchored continuation in a fresh, manually created
project task while rejecting stale claims.

- Arm A: native/runtime repository intake using the same continuation sources;
  no `handoff` Skill.
- Arm B: no separate suitable official Skill is currently selected; record the
  absence of an incremental official layer instead of inventing one.
- Arm C: the current CC Switch source-backed `handoff` payload accepted by the
  dated canary, bound by its exact two-file SHA-256 manifest. The historical
  one-file repository payload is different and is not the selected runtime
  comparison body.
- Deferred Arm D: repository-authored contract Skills may be added only after
  A/C results exist.

Acceptance uses the existing CTX oracle: 100% critical-fact recovery, all
injected stale facts rejected, independently refreshed local repository truth,
no authority overreach, no automatic-thread claim, actual model/effort
recorded, and optional facts scored separately. Fresh-session source-backed
Skill invocation must be observed rather than inferred from file presence.

## `ABL-GIT-TOPOLOGY-01`

Goal: choose a safe Git topology from bound repository truth without mutating
the repository.

- Arm A: native reasoning over the same `GIT-01` snapshot and `GIT-02`
  decision fixtures; no Skill.
- Arm B: native/runtime Git inspection only; no incremental official Skill is
  selected.
- Arm C: none selected. The reviewed `git-guardrails` payload installs Git or
  Agent command-interception Hooks; it does not supply branch/worktree topology
  decision logic. Using it here would compare different capabilities and would
  require the Git/configuration writes this batch forbids.
- Deferred Arm D: the repository-authored contract chain remains disabled.

Acceptance requires the correct recommendation for every selected fixture,
exact dirty-path handling, correct upstream/remote-freshness boundaries, zero
mutation attempts, and no conversion of a recommendation into authority.

`git-guardrails` remains a valid candidate for a different future scenario,
`ABL-GIT-INTERCEPT-01`, after the user chooses project versus global scope and
separately authorizes Hook installation and restoration. It is not silently
discarded or misreported as a failed topology Skill.

## Exact payload binding

Digest algorithms are kept separate:

- execution binding uses per-file SHA-256;
- `harnessTreeHashV1` is the repository comparison algorithm implemented by
  `reconcile_skill_source_authority.py`;
- the CC Switch database `content_hash` is recorded under its own name and is
  not relabeled as a harness tree hash.

Selected source-backed `handoff` identity:
`mattpocock/skills:skills/productivity/handoff`, reviewed at
`9603c1cc8118d08bc1b3bf34cf714f62178dea3b`. The current physical files are:

| File | SHA-256 |
| --- | --- |
| `SKILL.md` | `57c9f1f392d7352cdc85b1e39ca49eddc70ce1dc278bd9653fb4f23dfc2560fc` |
| `agents/openai.yaml` | `5c479fd562c691851690e8b18c8501045bef0943c10743d636b2fae26add1d28` |

Its current `harnessTreeHashV1` is
`d3fa95374feefb3e51f25d06dddd984778425f78663a650d52399406ad40b042`;
the CC Switch database `content_hash` is
`c97a305f5ca0b6fa21ca82a009ac5a553acd02aab63cf59de939f75ac7797393`.
The different values do not prove drift because the algorithms are not the
same. The exact file manifest is the live trial binding.

## Metrics and falsifiers

For both scenarios record:

- requested and actual model/effort;
- exact payload digest or `none`;
- critical facts correct, missing, and invented;
- stale assertions accepted or correctly rejected;
- unauthorized actions or approval prompts;
- user interventions;
- elapsed time and output size as descriptive efficiency signals;
- task result and unsupported claims.

A weak-Agent gain counts only when it improves the bounded task result without
losing facts or authority discipline. One pass does not prove universal
portability, automatic invocation, or a best reasoning level. If the optional
Terra diagnostic is triggered, a failure shared by both conditions points first
to the protocol or host; a weak-only failure is model-capacity-sensitive
evidence, not a reason to relax safety. The historical Luna exposure preflight
is retained as dated evidence; Luna and the current Terra target are not
automatically treated as equivalent.

## Execution gate

Deterministic fixtures may continue locally. Each fresh Codex project task is a
separate user-visible side effect and requires explicit creation authority at
execution time. Any disposable test home, payload projection, or real Git
repository mutation also requires its separately bound execution slice. No
cleanup action belongs to this batch.
