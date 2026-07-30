# Codex App-Server Skill Treatment-Fidelity Protocol

Date: 2026-07-24
Status: live assay passed; synthetic body-only delivery proved

## Why This Exists

The current host has already proved exact Skill inventory, task-scoped selected
metadata exposure, and acceptance of structured `type="skill"` input. It has
not emitted a loader event or captured model input that binds a Skill body to a
turn. Repeating the same task comparison cannot close that gap.

This protocol tests the host mechanism without editing an installed Skill. A
disposable project-local canary Skill receives a fresh random token in its body
only. The token is absent from the Skill name, description, path, public
prompt, structured input, and process-scoped config.

## Paired Assay

Each of three repetitions uses one body and one token, with fresh ephemeral
threads:

- the control keeps the canary visible in the inventory but disables all user
  Skills and sends text only; it must return exactly `NO_TREATMENT`;
- the selected arm enables only the canary and sends the exact structured Skill
  name and path; it must return exactly the body-only token;
- arm order alternates across repetitions;
- both arms use `gpt-5.3-codex-spark/low`, read-only/no-network sandbox,
  approval `never`, and no provider fallback.

Commands, file changes, MCP, Apps, dynamic tools, collaboration Agents,
network, dependency changes, Git operations, and external writes are hard
failures. Global Codex config, repository status, inventory identity, and the
canary body must remain stable.

## What A Pass Would Mean

A clean three-pair result would prove that body-only canary content reached the
model through the bound Codex app-server mechanism. It would be stronger than
structured-input acceptance and stronger than behavior merely consistent with
an installed Skill.

It would still not be an independent loader notification, and it would not
prove that the installed historical `diagnose` body reached the model, caused
the 2/3 strict-process association, represents current Matt, is superior, or
is ready for a portfolio decision. Candidate-specific attribution still needs
either an exact loader/model-input event or a separately adequate causal
treatment.

Machine contract:
`registry/codex-app-server-skill-treatment-fidelity-protocol-2026-07-24.json`.

The completed result is recorded in
`registry/codex-app-server-skill-treatment-fidelity-evidence-2026-07-24.json`.
All three controls returned the public fallback and all three selected arms
returned their distinct body-only tokens, with no forbidden item or state
drift. The independent-loader and installed-candidate boundaries above remain
unchanged.
