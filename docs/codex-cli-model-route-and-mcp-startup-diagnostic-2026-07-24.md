# Codex CLI weak-model route and MCP startup diagnostic — 2026-07-24

Status: both requested low-capacity CLI routes returned; formal Skill ablation
is still blocked; MCP startup is degraded and the root cause is open.
Machine record:
[`../registry/codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.json`](../registry/codex-cli-model-route-and-mcp-startup-diagnostic-2026-07-24.json)

## Result first

`gpt-5.3-codex-spark/low` and `gpt-5.4-mini/low` both returned exact markers
from ephemeral, read-only, no-tool `codex exec` probes. The unsandboxed CLI
reported `Logged in using ChatGPT`; the earlier sandboxed `Not logged in`
result was a sandbox-visibility observation, not current account truth.

This supersedes the current-state login and route block in the dated
2026-07-23 preflight without rewriting that historical record. It does not
create a formal weak-Agent result. The event stream exposed no independent
actual-model or actual-reasoning field, and neither probe established
task-scoped selected/unselected Skill exposure.

The bootstrap itself is now a material confound. Spark exceeded the two-percent
Skills context budget: every Skill description was removed and 130 additional
Skills were omitted from the model-visible list. Mini kept the Skills visible
only after shortening their descriptions. Both probes consumed roughly 27,000
input tokens before doing a one-marker task. Route availability is therefore
proved only at the requested control-plane path; Skill isolation, task quality,
and weak-Agent acceptance are not.

Spark/low remains the primary weak acceptance candidate because it is the
weaker coding route requested for the formal floor. Mini/low is a useful
secondary low-capacity diagnostic. Neither may be silently replaced by
`gpt-5.6-terra`, `gpt-5.6-sol`, or another stronger condition.

## MCP correction and split

The screenshot contains two yellow lines for one visible failed server:
`sites-design-picker`. The first line is the detailed initialize-handshake
failure; the second is the aggregate `MCP startup incomplete` summary.
Therefore the screenshot alone does not show two failed MCP servers.

Sanitized process evidence does show a second, distinct failure surface in the
same CLI startup: the remote Plugin service MCP transport also failed. This
background failure was not the second yellow line. It must remain separate
from the local `sites-design-picker` failure until a shared cause is proved.

`sites-design-picker` is absent from `codex mcp list`, so it is not a static
user MCP row that can be responsibly fixed by blindly disabling or editing the
listed configuration. The current Sites Plugin manifest is `0.1.31`; it
declares Skills and an App but no MCP entry or local `mcp/server.mjs`. An empty
`0.1.30` cache directory remains. Separate historical logs show successful
`Sites Design Picker` `0.1.30` initialization in other Desktop processes.
Those facts make a version transition and remote Plugin timing plausible
hypotheses, not causes.

No global configuration, Plugin, MCP, account, or credential state was changed.
No restart was attributed to this diagnostic. Persistent failure across clean
restarts remains unproved.

## Sensitive evidence boundary

The local debug database can contain configuration material including
authorization headers. Raw log bodies are not repository evidence and were not
copied here. This record contains only derived classifications and non-secret
counts. Future queries must remain sanitized.

No credential was rotated and no log was deleted. Those are separate account
or destructive actions. The existence of sensitive debug material is a reason
to rotate the affected credential deliberately, not permission to mutate it.

## Next gate

For weak-Agent testing, the next admissible gate is task-scoped Skill exposure:
the parent or host must prove the selected and unselected Skills for each arm
before a formal scenario is sent.

For MCP startup, the next admissible gate is one clean-restart reproduction
with sanitized, process-bound evidence that distinguishes:

- local `sites-design-picker` initialize outcome;
- remote Plugin service MCP transport outcome;
- Sites Plugin version and injected runtime identity; and
- whether the failure persists after startup synchronization.

Until then, do not call either route a completed ablation and do not present a
static MCP config edit as a verified fix.
