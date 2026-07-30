# Skill Ablation Batch 01 Host Preflight — 2026-07-19

Status: fresh-task exposure preflight observed; formal ablation arms blocked
Machine evidence:
[`../registry/skill-ablation-batch-01-host-preflight-2026-07-19.json`](../registry/skill-ablation-batch-01-host-preflight-2026-07-19.json)

## Result first

A user-authorized Codex desktop project task was created with the control-plane
request `gpt-5.3-codex-spark` and `low`. It ran only an exposure preflight. The
task reported all three self-authored Skills visible and `handoff` absent from
its startup `Available skills` list:

- `intent-contract`: visible;
- `capability-router`: visible;
- `closure-contract`: visible;
- `handoff`: not visible.

This definitively fails the self-authored-disabled precondition for the formal
arms. It does not determine whether the source-backed `handoff` loader is
available: official Codex documentation states that the initial Skill list has
a context budget and may omit Skills when the set is large. Startup-list
absence is therefore not proof of loader unavailability. This is not a failed
Git or context trial because neither formal prompt was sent, and it is not
evidence that any Skill body is defective.

The failure concerns isolation of the upstream Skill variable only. The
hard-standard baseline was expected to remain active and was never a removal
target. A future successful disablement must hide the three named Skill
payloads while preserving repository instructions, host approvals, fixed
facts, safety/authority thresholds, and acceptance verification.

## Model and host boundary

The desktop control plane accepted the requested weak model and reasoning
setting. The task itself reported only `gpt-5` and `unknown`, so exact runtime
model and reasoning identity remain unverified rather than silently inferred.

Because that weak self-report was ambiguous, the prepared conditional
`gpt-5.6-luna`/`low` capacity diagnostic was triggered. Its first creation call
returned a thread ID that was neither readable nor present in the thread list;
one bounded retry completed. The completed task reported the same exposure:
the three self-authored Skills visible and `handoff` absent. It also preserved
the intended interpretation that Skills are upstream variables while hard
standards remain active. This cross-requested-model agreement strengthens only
the startup-list exposure observation for the three self-authored Skills. It
does not resolve `handoff` loader availability, and neither task exposed
independent exact runtime model or reasoning metadata. A later Arm C must
explicitly invoke the exact source-backed payload and record invocation,
payload identity, and outcome even if the Skill remains omitted from the
startup list.

The nested CLI is a different host surface: its read-only `debug prompt-input`
render showed only system Skills under an isolated user root. That surface can
make the self-authored Skills absent, but it also makes the CC Switch `handoff`
payload absent and therefore cannot substitute for the desktop Arm C loader
test.

## Native control that remains available

Current official Codex documentation defines actual per-Skill disablement as
`[[skills.config]]` with the exact `SKILL.md` path and `enabled = false`.
`allow_implicit_invocation = false` is not equivalent because explicit
invocation remains possible. The documented user-config path requires a Codex
restart after changing it.

The next experiment therefore crosses two new host-wide boundaries: reversible
mutation of the global Codex Skill configuration and application restart. The
existing authorization covered fresh tasks, a temporary handoff artifact, and
task-scoped disablement; it did not cover those host-wide actions. No CC Switch
mutation, Skill projection, cleanup, commit, or push was performed.
