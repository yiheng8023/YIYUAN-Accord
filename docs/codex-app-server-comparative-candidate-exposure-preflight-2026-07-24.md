# Codex app-server Comparative Candidate Exposure Preflight

Date: 2026-07-24
Status: partial current-host evidence

This preflight tested only whether each exact pinned candidate could be made the
only enabled user Skill through Codex app-server `skills/list` and
`skills.config`. It sent no task turn, requested no model response, installed
nothing, changed no global configuration, invoked no MCP, and performed no Git
mutation.

## Disciplined Coding

`disciplined-coding` passed the current-host metadata exposure check. The
control inventory contained 105 user Skills and six system Skills. In the
selected process, exactly one user Skill was enabled, all other user Skills
were disabled, non-user states were preserved, and the identity manifest was
unchanged. The ephemeral thread configuration reported
`gpt-5.3-codex-spark/low`, provider fallback disabled, approval policy `never`,
and a read-only network-disabled sandbox.

The candidate file, global configuration, and repository-status digest were
stable before and after the successful probe. This proves selected exposure
only. It does not prove loader invocation, instruction delivery, behavior, or
net value.

## Historical Matt Diagnose

The installed CC `diagnose` payload also passed exact current-host selected
exposure. The same 105-user/6-system identity set was preserved, exactly one
user Skill was enabled, and the Spark/low read-only ephemeral thread was
created without a task turn. The file, global configuration, and repository
status remained stable.

The payload is byte-identical to Matt upstream commit
`7afa86d3a5dd96edde06ffa014e16c64e733681e`, but it is not byte-identical to
current Matt `main`, which renamed and strengthened the Skill. Any later live
result is therefore evidence about this installed historical payload, not
current Matt.

## Superpowers TDD

The exact installed Superpowers `test-driven-development` Skill was absent from
the app-server `skills/list` selection surface under three bounded profiles:

1. all plugin features disabled;
2. local `plugins` discovery retained while `remote_plugin`, Apps, and plugin
   sharing remained disabled;
3. installed `plugins + remote_plugin` discovery retained while Apps and
   plugin sharing remained disabled.

No same-name or same-path hint appeared in any profile, so no selected process
or thread was started for this candidate. Static MCPs remained outside the
probe path.

This is a host-interface selection result, not a content rejection. It does
not establish that Superpowers is unavailable to Codex Desktop, unavailable
through explicit invocation or another interface, or behaviorally ineffective.
The Superpowers live arm remains held until a task-scoped plugin Skill selection
surface is evidenced.

The exact Superpowers `systematic-debugging` payload was checked independently
under the same three profiles and was also absent from `skills/list`. This is
the same bounded host-interface selection result, not a content rejection or a
claim that Superpowers is unavailable through every Codex interface.

## Managed Command Sandbox Boundary

The first `diagnose` preflight attempt ran inside the managed command sandbox
and observed zero user Skills because the child app-server could not see the
user-Skill symlink targets. The same read-only probe outside that sandbox saw
all 105 user Skills and passed exact selection. A trial whose child process
cannot read those symlink targets is environment-invalid; it must not be scored
as a CC, Codex, or candidate failure.

The machine-readable evidence is
`registry/codex-app-server-comparative-candidate-exposure-preflight-2026-07-24.json`.
