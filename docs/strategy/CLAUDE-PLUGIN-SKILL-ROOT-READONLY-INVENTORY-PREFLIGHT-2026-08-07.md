# Claude Plugin Skill-root read-only inventory preflight

## Current decision

The next consumer-mapping step is blocked pending explicit user authorization
for one local read-only inventory. The observed existence of
`C:/Users/15521/.claude/plugins` is not authorization to inspect its managed
Skill roots, manifests, payloads, settings, or runtime state. A declared
synthetic complete fixture validates the preflight mechanism only and always
returns `inventoryExecutionAuthorized: false`.

## Proposed read boundary

If separately authorized, the inventory may read only marketplace manifest,
version metadata, Skill-root locator, and filesystem-link metadata required to
record plugin ID, name, version, marketplace, source locator, revision or
digest, Skill-root relative path, link target, and cache or install state.

It must not read credentials, account or session data, prompt or settings
content, Plugin payload bodies, Skill bodies, or runtime logs. It must not use
the network, execute a Plugin, change configuration, write external state, or
substitute a guessed source when identity is absent. A path escape, required
execution, required network refresh, or sensitive-content boundary stops the
inventory rather than broadening access.

## Verification and claim boundary

Any future authorized result must be a repository-local machine record with a
dedicated validator, field-bound evidence truth, and
`acceptance.consumer-mapping-evidence` still `partial`. The preflight proves no
live inventory, Plugin or Skill identity, enablement, loader precedence,
invocation, behavior, value, or production readiness. It authorizes no read or
side effect by itself.
