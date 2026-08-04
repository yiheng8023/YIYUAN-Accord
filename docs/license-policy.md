# License Policy

This repository uses layered licensing because it mixes repository-owned governance code, documentation, generated projections, adapted third-party Skill bodies, source evidence, and external capability baselines.

This document explains the intended license boundaries. It is not legal advice.

## Repository-owned code and governance machinery

Unless a file says otherwise, repository-owned code and governance machinery are licensed under the Apache License 2.0:

- scripts;
- schemas;
- tests and fixtures authored for this repository;
- GitHub Actions workflows;
- validation tooling;
- registry and projection machinery;
- policy files authored for this repository.

Apache-2.0 is chosen because it is permissive, widely used, and includes an explicit patent grant.

## Repository-owned documentation and governance text

Unless a file says otherwise, repository-owned documentation and public governance text are intended to be licensed under Creative Commons Attribution 4.0 International (CC BY 4.0):

- documentation;
- review explanations;
- taxonomy descriptions;
- capability topology explanations;
- public-safe coverage matrices written by contributors;
- release and intake process descriptions.

Attribution should identify this project and, where applicable, the original contributor.

## Third-party Skill bodies

Third-party Skill bodies are governed by their original upstream licenses and any adaptation notices recorded by this repository. The top-level Apache-2.0 license does not relicense third-party Skill bodies beyond what their upstream licenses permit.

For every historically admitted derivative or future approved third-party
Skill body, this repository should preserve:

- source repository;
- pinned revision;
- original license;
- original path when applicable;
- exact-upstream status or separately owned derivative/adaptation notes;
- relevant notices in `THIRD_PARTY_NOTICES.md` or source-specific evidence.

If redistribution rights are missing, unclear, source-available only,
all-rights-reserved, or otherwise unsuitable, the safe disposition is
reference-only, adapter-only, recipe-only, or reject rather than vendoring the
body. Portability metadata must not silently rewrite an upstream body.

## Official or runtime-owned capability baselines

Official, runtime-owned, built-in, or first-party capability baselines may be linked, summarized, and compared for coverage. They are not managed inventory and are not relicensed by this repository.

Do not vendor official/runtime-owned Skill bodies unless there is an explicit permission path and the normal intake process approves the adaptation.

## Generated outputs

Generated projections inherit the license of their repository-owned inputs when those inputs are repository-owned. Generated metadata about third-party Skills or external capability baselines remains governance metadata and does not relicense the underlying source.

Generated outputs must preserve provenance and notice references when they describe third-party or official sources.

## Private overlays are excluded

The following are outside the public license grant unless separately sanitized and explicitly released by their owner:

- private user configuration;
- memory snapshots;
- private bookmarks;
- personal preference overlays;
- account state;
- unsanitized local paths when they are not necessary evidence identities;
- tokens, credentials, OAuth/session state, cookies, and caches;
- private repository metadata.

## Contribution default

Unless a contributor explicitly marks a contribution otherwise before acceptance:

- code and governance-machinery contributions are accepted under Apache-2.0;
- documentation and public governance-text contributions are accepted under CC BY 4.0;
- third-party Skill suggestions remain references to their upstream source and
  are not copied into this repository unless their license permits it and the
  applicable admission authority approves that separate state transition.

## Commercial use

Commercial use of this repository's Apache-2.0 and CC BY 4.0 materials is allowed under those licenses. Commercial use of third-party Skill bodies, official baselines, or external resources depends on their own licenses and terms, not on this repository.

Funding, sponsorship, paid review work, or paid adaptation must not bypass
source pinning, license, provenance, security, portability, overlap,
exact-upstream or derivative-ownership classification, validation, or release
gates.
