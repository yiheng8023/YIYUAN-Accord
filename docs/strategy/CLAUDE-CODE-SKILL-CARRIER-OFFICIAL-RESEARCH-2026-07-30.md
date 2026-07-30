# Claude Code Skill carrier official research

Date: 2026-07-30
Status: read-only official-source research; no host or Skill mutation

## Question

Can the three source-owned Skills remain portable physical trees under
`~/.agents/skills` while Claude Code receives a small, supported host-specific
projection, without adding a Hook, custom loader, duplicate body, or Plugin
lifecycle?

## Official carrier contract

The current Claude Code Skills documentation names these locations:

| Scope | Path |
|---|---|
| Personal | `~/.claude/skills/<skill-name>/SKILL.md` |
| Project | `.claude/skills/<skill-name>/SKILL.md` |
| Plugin | `<plugin>/skills/<skill-name>/SKILL.md` |

The same page explicitly states that Claude Code 2.1.203 or later accepts a
`<skill-name>` entry in an enterprise, personal, or project location as a
symbolic link to a directory elsewhere on disk. Claude follows the link to
`SKILL.md`; if the same target is reachable from multiple locations, it loads
that target once. The locally observed Claude Code version is 2.1.220.

This supports an individual standalone carrier of:

```text
~/.claude/skills/<name> -> ~/.agents/skills/<name>
```

It does not prove that linking the entire `~/.claude/skills` root is equally
supported in every sandbox, worktree, or remote mode. The recommendation is
therefore three explicit per-Skill links, not one root-level redirect.

Primary source:
[Extend Claude with skills](https://code.claude.com/docs/en/skills), accessed
2026-07-30.

## Discovery and precedence boundaries

The official page documents this name-collision order:

```text
enterprise overrides personal; personal overrides project
```

It also says a standalone enterprise, personal, or project Skill overrides a
bundled Skill with the same name, while Plugin Skills use a
`plugin-name:skill-name` namespace.

That is the documented contract, not independent proof of the current runtime
implementation. An official-repository issue reports that a project Skill was
observed overriding a personal Skill and asks for clarification. The issue was
closed without a product resolution. Until a dedicated collision fixture is
run, the current live precedence remains unproved and the three first-party
names should stay unique across standalone scopes.

Secondary evidence:
[anthropics/claude-code issue 53288](https://github.com/anthropics/claude-code/issues/53288),
accessed 2026-07-30.

The official documentation does not name `~/.agents/skills` as a direct Claude
Code discovery root. An open official-repository feature request asks Claude
Code to add that discovery path. This supports a narrow conclusion only:
direct discovery is not documented, so the portable root still needs a
documented Claude carrier. It does not prove that every historical or future
build lacks an undocumented experiment.

Secondary evidence:
[anthropics/claude-code issue 31005](https://github.com/anthropics/claude-code/issues/31005),
accessed 2026-07-30.

## Standalone and Plugin are different lifecycle classes

A personal or project Skill is a standalone filesystem carrier. A Plugin Skill
is distributed and enabled through the Plugin lifecycle and is namespaced.
Plugin installation, enablement, update, cache, marketplace, and removal are
therefore not substitutes for proving a standalone Skill carrier.

The local read-only `claude --bare plugin list` result reported no installed
Plugins, and `plugin details <name>@skills-dir` did not find the three
first-party names. That does not disprove standalone discovery: it checks a
different registry and lifecycle surface.

For the present goal, Plugin packaging would add namespace and lifecycle cost
without an evidenced residual need. It remains a candidate only if later work
requires Plugin-level distribution of agents, Hooks, MCP servers, or other
Plugin-owned resources.

Official repository references:

- [Plugin skill development](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/skill-development/SKILL.md)
- [Plugin structure](https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/plugin-structure/SKILL.md)

Both were accessed 2026-07-30.

## Loading and authoring boundaries

The official documentation says:

- Claude may select a Skill automatically from its description, or the user may
  invoke it explicitly;
- the full Skill body loads only when the Skill is used;
- existing personal and project Skill directories have live `SKILL.md` change
  detection;
- `skillOverrides` can hide or reduce a standalone Skill's listing;
- `SKILL.md` should remain under 500 lines, with detailed material moved to
  supporting files.

The exact current line counts are 504 for `intent-contract`, 419 for
`capability-router`, and 253 for `closure-contract`. The four-line excess is an
authoring-quality warning. The documentation presents it as guidance, not a
hard parser or loader rejection threshold. It therefore does not invalidate
the static carrier choice and does not authorize an edit before exposure and
value testing shows what should actually change.

## No-model exposure surface

The documented `/skills` menu lists Skills and writes `skillOverrides`
settings. Autocomplete also exposes invocable names. These are the closest
current standalone host-enumeration surfaces. No official stable,
machine-readable CLI inventory was found that fully reports standalone
registration, collision resolution, parsing failure, budget dropping, and
visibility state.

Using `/skills` or autocomplete without submitting a task can provide bounded
host-exposure evidence. The documentation does not formally guarantee that
every host implementation performs those UI operations without any background
model traffic, so the actual probe must observe the route and stop before
sending a prompt.

Even a visible name proves only listing/exposure. It does not prove invocation,
full instruction delivery, behavioral causation, or incremental value.

## Research conclusion

The official evidence supports the static eligibility of the source-owned
per-Skill symlink adapter. It does not prove the recommended links have been
created, discovered, enabled, invoked, delivered to a model, or improved an
outcome.

The recommended order is therefore:

1. preserve the current portable physical `.agents` projections;
2. fixture-test an explicit opt-in Claude link adapter in the source-owned
   installer;
3. remove each legacy CC-owned Claude link only through the separately governed
   collision-safe manager transaction;
4. install the new link only after its destination is absent; and
5. obtain fresh no-model host exposure before any separately authorized model
   trial.

No Claude session, Skill, Plugin, Hook, MCP, configuration, CC Switch row,
projection, backup, commit, or remote changed during this research.
