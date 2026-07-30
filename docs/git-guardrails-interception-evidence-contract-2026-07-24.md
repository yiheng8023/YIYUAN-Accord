# Git guardrails interception evidence contract

`ABL-GIT-INTERCEPT-01` separates an attractive safety claim from mechanisms
that can actually intercept a specific Git command.

Before repository suspension, the observed CC Switch payload and repository
payload were byte-equal at:

- `SKILL.md`: `27bb96d...d790`
- `scripts/block-dangerous-git.sh`: `9acf0e8...564a`

Static cross-checking against the
[official Git hooks documentation](https://git-scm.com/docs/githooks) shows:

- `pre-push` can abort a push, and receives ref-update records on stdin;
- `pre-auto-gc` is invoked only by `git gc --auto`;
- `post-checkout` runs after the worktree update;
- the packaged blocker script expects Claude-style JSON on stdin, so it is not
  directly compatible with the native `pre-push` protocol;
- native Git hooks therefore do not establish universal pre-execution
  interception for reset, clean, branch deletion, checkout, and restore.

The current execution eligibility is `preview-only-pending-command-by-command-live-canary`.
No Hook write, dangerous command, global configuration change, or real remote
operation is authorized by this contract. An `approved` / `validated`
admission and byte equality are provenance or governance facts, not runtime
efficacy evidence.

The repository release transaction is now suspended coherently:
`git-guardrails` is absent from the approved inventory and routing projection,
its admission is `recipe-only` / `validated=false`, and the two repository
payload files were deleted before rebuilding the manifest and projections.
This preserves design-review value without making the payload executable.
The CC Switch copy is outside this repository transaction and remains
unchanged; repository suspension is not a CC Switch uninstall claim.

The nine deterministic fixtures reject native-hook coverage inflation,
`pre-auto-gc` misuse, packaged-script protocol conflation, universal
cross-caller claims, unauthorized mutation, collapsed authorization gates, and
the use of one push canary or admission metadata as proof for other commands.
They prove only an offline decision boundary, never live interception,
cross-caller protection, or weak-Agent behavior.

A future live gate requires a separately authorized disposable repository and
local bare remote. Hook write, dangerous-command canaries, and recovery are
three independent authorization transitions. Each listed command must preserve
parent-observed exit code, sentinel state, mechanism-hit evidence, and recovery
state. A pass for one command, shell, host, Agent, or caller cannot be upgraded
to another.
