# Skill Ablation Host Configuration Transaction — 2026-07-19

Status: prepared but not executed; host-wide authorization pending
Machine contract:
[`../registry/skill-ablation-host-config-transaction-2026-07-19.json`](../registry/skill-ablation-host-config-transaction-2026-07-19.json)

The 2026-07-24
[read-only revalidation](skill-ablation-host-transaction-revalidation-2026-07-24.md)
found that the bound config SHA-256 has drifted while all six target hashes
still match. This historical transaction is therefore blocked and must not be
executed or silently rebaselined.

## Result first

The existing design is unchanged. Skills remain upstream capability variables,
while repository instructions, native approval boundaries, fixed facts,
truth/safety/authority thresholds, and acceptance verification remain mandatory
cross-arm controls.

The current user config was observed read-only. It contains no
`[[skills.config]]` entries. Six exact target files exist: the `.agents` and
`.codex` copies of `intent-contract`, `capability-router`, and
`closure-contract`. Corresponding copies have equal SHA-256 values, but byte
equality does not prove whether the host treats them as copies, links, or one
deduplicated logical Skill.

Official Codex documentation specifies `[[skills.config]]`, the exact
`SKILL.md` path, and `enabled = false` as the disable mechanism, followed by a
Codex restart. It also states that the initial Skill list is budgeted and may
omit entries. The transaction therefore disables all six observed paths but
does not require `handoff` to appear in the initial list; explicit invocation,
path, and digest evidence decide that loader claim.

## Transaction boundary

No user config, CC Switch state, Skill projection, or application process has
been changed. The prepared transaction is one inseparable reversible unit:

1. re-hash the live config and all targets;
2. create an exact-byte backup and verify its hash;
3. add exactly six disabled Skill entries and validate the TOML;
4. restart Codex Desktop;
5. repeat the exposure-only preflight;
6. execute formal weak-model arms only if self-authored exposure is absent or
   host-disabled;
7. restore the exact backup on success, failure, or interruption;
8. verify the original config hash, restart again, and verify restored host
   behavior;
9. remove only the transaction backup after restoration is proven.

Any baseline drift causes re-intake before mutation. Any visible or unknown
self-authored exposure blocks formal attribution. Failure to load `handoff`
after explicit invocation is recorded as a falsifying host result rather than
repaired through CC Switch or a new Skill.

## Authority still required

The remaining request is authorization for the complete unit: global Codex
config backup/mutation/restoration, two application restarts, formal fresh-task
trials, and deletion of only the verified transaction backup. It does not
include CC Switch mutation, installation, Skill projection changes, commit, or
push.
