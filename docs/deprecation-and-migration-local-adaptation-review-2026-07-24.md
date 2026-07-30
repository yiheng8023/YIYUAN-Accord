# Deprecation And Migration Local Adaptation Review

Date: 2026-07-24
Status: review complete; candidate not live-validated

## Outcome

The CC Switch-managed `deprecation-and-migration` Skill is eligible for the
disposable maintenance/migration fixture preflight. It is not an exact copy of
the pinned Addy Osmani source, and any later result must be attributed to the
**CC Switch-managed local adapted derivative**, not to the upstream original.

This review does not authorize a live Agent run, candidate mutation, vendoring,
installation, removal, migration, deployment, commit, or push.

## Exact pins

| Surface | Pin |
|---|---|
| Upstream repository | `addyosmani/agent-skills` |
| Upstream revision | `17214a29c429a19f7a9607f2c06f9d650ea87eb0` |
| Upstream Skill blob | `258e2a0396c9c2cb639cff84a9db64753740be96` |
| Upstream Skill SHA-256 | `bf2d9b4e3bc635b32e8de70b0ab41e4395d7b585e6474347c53ce89d45fbdb75` |
| Upstream license | MIT; SHA-256 `6f202f8bd568cd730dbb2b0d1f8e243bc74c2fa1f64dbce9b2c7ea08bd5c9fd7` |
| Local Skill SHA-256 | `52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea` |
| Local declaration | exact upstream revision and path; MIT; adapted for cross-Agent use |

The upstream commit is unsigned. That is recorded as missing signature
evidence, not mislabeled as a code failure or a verified identity claim.

## Diff review

The complete upstream body, complete local body, complete unified line diff,
and upstream LICENSE were reviewed. The local file has 266 lines versus 206
upstream lines. The comparison found 170 equal lines, 25 non-equal blocks, and
a net increase of 60 lines. The local and upstream Git blobs are unequal.

Material local changes:

- separate migration analysis from debugging, observability, testing, shipping,
  and host authorization;
- replace “code is a liability” with a contextual value and carrying-cost test;
- permit only a separately authorized controlled-withdrawal route when a
  replacement cannot exist;
- support incremental, atomic, or batched migration according to coupling;
- preserve shared owner and consumer accountability;
- make zero observed usage necessary but insufficient for ordinary removal;
- preserve explicitly governed retention, compatibility, audit, rollback, and
  historical artifacts;
- add explicit unknown-consumer, recovery, compliance, and approval boundaries.

These are material adaptations, not formatting-only changes. They are retained
as positive safety and governance changes for the proposed fixture.

## Executable and overlap boundaries

The Skill is Markdown and ships no executable script, hook, dependency, or tool
binding. It contains illustrative TypeScript and an example `npx` command.
The trial therefore keeps network and installation disabled and does not treat
examples as authorization to execute them.

The candidate complements intake, routing, debugging, observability, testing,
shipping, rollback, and closure controls. It does not replace host approval,
domain review, production telemetry, human removal authority, or repository
hard standards. The treatment arm will expose this one candidate while the
control arm disables user Skills; both retain identical hard standards.

## Gate decision

Source and adaptation review passed. Live weak-Agent execution remains closed
until the fixture builder, private oracle, offline classifier fixtures, fresh
candidate hash, native-disabled exposure, and candidate-specific selected
exposure all pass.

This record proves no behavioral value, causation, cross-host portability,
production migration safety, or equivalence with the upstream original.
