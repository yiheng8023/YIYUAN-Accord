# Source-pinned debugging Skill projection protocol — 2026-07-24

Status: both candidates passed byte-exact materialization and no-turn
app-server inventory isolation; no weak-Agent arm has run under this protocol.

## Result first

The next debugging comparison must not reuse the installed historical
`diagnose` body as “current Matt,” and it must not treat an unselectable plugin
path as a Superpowers behavior failure. The bounded route is a disposable,
project-scoped, byte-exact projection of each selected candidate.

The Matt candidate is the complete `diagnosing-bugs` directory at immutable
public commit `ed37663cc5fbef691ddfecd080dff42f7e7e350d`. The navigation checkout
is detached at the older `9603c1cc8118d08bc1b3bf34cf714f62178dea3b`;
therefore the builder reads Git objects with `git show` and never copies the
checkout working tree.

The Superpowers candidate is the installed OpenAI-curated runtime package
`6.1.1`. Its selected directory's public files are Git-blob equal to upstream
tag `v6.1.1` at `c984ea2e7aeffdcc865784fd6c5e3ab75da0209a`.
The package also contains `agents/openai.yaml`, an OpenAI runtime metadata
extension that is not present in that public tag; it remains part of the exact
runtime-distributed projection and is labeled separately.

## Projection boundary

The builder writes only:

- `<disposable-root>/.agents/skills/<exact-skill-name>`;
- `<disposable-root>/.aah-provenance/<candidate-id>/LICENSE`;
- `<disposable-root>/SOURCE-PINNED-SKILL-PROJECTION.json`.

It refuses a nonempty output root by default, verifies every byte count,
SHA-256, and Git-blob SHA-1 before writing, and never rewrites the Skill body.
The MIT notice accompanies the disposable substantial copy. No CC Switch,
installed plugin, source checkout, global Codex configuration, Git remote, or
account state is mutated.

## Dependency boundary

The complete selected Matt directory includes its HITL template and runtime
metadata. Its optional reads of target-workspace `CONTEXT.md` and ADRs remain
conditional on those target artifacts existing.

The complete selected Superpowers directory includes all local helper
documents and scripts. Its body also names
`superpowers:test-driven-development` and
`superpowers:verification-before-completion`. Those separate Skills are not
projected in the first single-Skill arm. Consequently the arm can evaluate only
the instructions present in `systematic-debugging`; it cannot prove full
Superpowers orchestration equivalence.

## Live preflight gate

Before a weak-Agent turn, the app-server inventory must expose exactly the
projected name/path, only that configurable Skill may be enabled, plugins,
Apps, and static MCPs stay disabled, and the turn must use structured Skill
input with the exact name and path. Source bytes, projection bytes, global
configuration, and repository truth must remain stable.

A projection pass proves only that an exact source-pinned candidate directory
can be presented through the already-observed project Skill mechanism. It does
not prove an independent loader event, installed-candidate delivery,
behavioral causation, candidate superiority, production incident competence,
or cross-host portability.

## Observed no-turn preflight

Both candidates were materialized into separate disposable roots. For each
root, Codex Desktop `0.145.0` reported 112 Skills: one repository Skill, six
system Skills, and 105 user Skills. The unselected arm enabled zero
configurable Skills; the selected arm enabled exactly the one repository
projection and zero user Skills. No thread or model turn started, and the
projected tree, global configuration observation, and repository status
remained stable.

The durable bounded record is
`registry/source-pinned-debugging-skill-projection-preflight-evidence-2026-07-24.json`.

## Next gate

The existing synthetic incident runner may now gain source-pinned Matt and
Superpowers arms while preserving the same fixture, prompt, weak-model route,
hard standards, and shared functional oracle. No installation, update,
cleanup, commit, or push is authorized by this protocol.
