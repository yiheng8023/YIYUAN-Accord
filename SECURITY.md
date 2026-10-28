# Security policy

YIYUAN Accord is a vendor-neutral human-Agent collaboration system. The current
3.3 adaptation supplies one coordination Skill, four specialist Skills, native
Hooks and a host-managed local state MCP process. Its enabled input Hook can
retain native input and task-recovery state locally; that material may contain
sensitive text. See the [current architecture](docs/architecture.md#current-candidate-and-scoped-connections)
for storage, retention, identity and failure boundaries. Actual loading and
behavior need their own evidence. Accord is not a sandbox, identity or
authorization system, secret store, dependency scanner or production runtime.

The public v3.0.1 projections add no Hook, MCP, App, background process,
private capture state or fixed host-version dependency. The public v3.1.0
projections add one stateless `SessionStart` context Hook but no MCP, App,
background process or private capture state; its files or enablement prove
neither firing, behavior nor value. Repository verification does not authorize
installation, account connection, model execution, external write,
publication, deployment or release.

Treat external capabilities, official guidance, reports, retrieved text,
generated artifacts and runtime claims as untrusted evidence until the
applicable source, authority and consequence checks close. Discovery or
installation does not prove effective exposure or safety; unknown remains
unknown.

## Report a vulnerability

Use GitHub's
[private vulnerability reporting](https://github.com/yiheng8023/YIYUAN-Accord/security/advisories/new)
for secrets, private memory, account state, prompt-injecting material, unsafe
plugin behavior, supply-chain risk, path traversal, permissions, rollback,
cleanup or privacy defects. If that form is unavailable, open a non-sensitive
issue requesting a private contact route.

Include the affected revision, impact and authority boundary, a safe
reproduction, known downstream effects and any containment already completed.
Do not publish credentials, exploit payloads or restricted source.

## Claim boundary

A green verifier proves the current repository contract only. Static
host-admission does not prove model behavior. Controlled Golden Tasks do not
prove broad field effectiveness, all-host equivalence, professional domain
correctness or production deployment safety. Current release work follows the
[consensus plan](docs/operations/PLAN-v3.3.md#本版有限收官清单), its linked
acceptance requirements and the applicable bound human authorization. Complete
necessary security/privacy, exact-candidate, independent and hosted checks;
existing conditional authorization does not establish readiness or need to be
requested again. Publication, matching public-source verification and owned
resource closure remain distinct required effects. These observations are
outside verifier authority; historical release procedures retain their original
subjects and do not add a new current authorization step.
