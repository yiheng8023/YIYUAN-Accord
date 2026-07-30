# Codex App-Server Structured Skill Input Evidence

Date: 2026-07-24
Status: host accepted structured Skill input; loader delivery unproved

## Interface finding

The locally generated Codex app-server `0.145.0` v2 protocol schema defines a
`SkillUserInput` object with required `name`, `path`, and `type` fields, where
`type` is exactly `skill`.

The same schema exposes Skill inventory, configuration, extra-root, plugin
read, and metadata-invalidation surfaces. It does not expose a notification
that proves a Skill body was loaded, injected, read by the model, or causally
used. `skills/changed` is an invalidation signal, not an invocation event.

## Bounded live probe

One isolated Spark/low treatment run:

- enabled only CC Switch `disciplined-coding`;
- submitted a structured `type="skill"` input with the exact selected name and
  path;
- did not textually name `$disciplined-coding`;
- received a successful `turn/start` response;
- changed exactly `retry_policy.py` and `test_retry_policy.py`;
- passed visible and hidden tests;
- ran the fixture test command;
- used no network, MCP, App, account, dependency install, global configuration
  write, commit, push, or external communication.

This proves that the current host accepted the exact structured Skill input and
that the selected metadata exposure remained isolated. It is stronger
treatment fidelity than merely putting `$disciplined-coding` in text.

## Claim boundary

The probe does not prove that the Skill loader invoked the Skill, that the
Skill body was read, that its instructions reached the model, or that the
observed behavior was caused by the Skill. It also does not invalidate the
earlier text-named runs; those remain bounded metadata-exposure and behavior
observations.

Future Codex treatment arms should use structured Skill input when the selected
Skill appears in `skills/list`. Causal, portfolio, retention, overlap, and
self-authored-chain decisions remain blocked until treatment fidelity is
stronger or the remaining uncertainty is explicitly modeled. A second
software-lifecycle scenario and a separate synthetic body-only canary assay are
now recorded; the latter proves the bound host mechanism can deliver Skill
body content, but does not prove the exact installed candidate body was
delivered or caused its task result.

Machine record:
`registry/codex-app-server-structured-skill-input-evidence-2026-07-24.json`.
