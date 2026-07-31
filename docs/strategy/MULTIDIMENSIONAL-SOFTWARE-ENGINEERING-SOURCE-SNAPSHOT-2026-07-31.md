# Multidimensional Software-Engineering Source Snapshot — 2026-07-31

## Purpose

This package calibrates the dynamic source-intelligence layer without creating
an evaluation Skill, automatic browser, permanent network dependency, or hard
standard. It keeps three stages distinct:

1. read-only observation of the exact official locators already admitted by
   the evaluation contract;
2. deterministic offline freezing of that captured observation;
3. deterministic offline validation against the parent source set and all
   bound repository bytes.

Observation is not freezing. Locator reachability, a search result, a page
title, or one Agent interpretation is not source truth. Freezing does not make
an external claim correct; it preserves exactly what was observed, how it may
be used, and why it may be weak, restricted, stale, or disputed.
The current observation is model-mediated and retains no network response
receipt, so the snapshot records reported locator observation at the stated
time but does not independently prove reachability.

## Carrier and pipeline boundary

The checked-in inputs and output are:

- `registry/multidimensional-software-engineering-source-snapshot-contract-2026-07-31.json`;
- `registry/multidimensional-software-engineering-source-observation-2026-07-31.json`;
- `registry/multidimensional-software-engineering-source-snapshot-2026-07-31.json`.

`scripts/build_multidimensional_software_engineering_source_snapshot.py`
performs no network operation. It requires exact source-set, owner, and locator
equality with the parent evaluation contract; sorts source records; binds the
parent contract, snapshot contract, and observation bytes; and adds a canonical
manifest digest. Each row keeps the parent bounded-use claim and parent
limitation separate from the narrower use supported by this observation.

`scripts/validate_multidimensional_software_engineering_source_snapshot.py`
rebuilds the snapshot from those repository inputs. Offline reconstruction
must exact-match the checked-in JSON. Negative tests reject source omission,
locator drift, unadmitted refresh, rights-boundary escalation, mutable
unpinned normative force, missing archive digest, and manifest drift.

## Evidence and rights boundaries

No raw external body is retained. The snapshot therefore proves neither exact
external content bytes nor complete source meaning. Five ISO sources have an
additional ISO metadata-only boundary: the official pages state restrictions
on using ISO content with AI, so the snapshot retains only bibliographic
identity, edition, publication or review state, locator, and the restriction.
It does not treat an ISO abstract or unlicensed standard text as machine
evidence. Any normative use requires separately licensed and authorized human
review. The parent's earlier high-level interpretation remains visible as a
historical claim but does not gain evidence strength from this metadata-only
snapshot.

The remaining sources retain only public publication identity and bounded
summary-level observations. SLSA has a versioned public route; DORA has a dated
mutable page; OWASP SAMM v2 remains a mutable unpinned model-family page. Those
differences are evidence strength, not cosmetic metadata.

The ISO/IEC 5055 page is intentionally preserved as disputed: it presents the
standard as published while also showing stage 90.60 with close-of-review or
under-review wording. The snapshot does not invent the final review
disposition.

## Bounded result

The current calibration freezes all twelve declared source identities:

- five bibliographic-metadata-only sources;
- six bounded-public-summary sources;
- one versioned-public-specification summary;
- zero retained raw bodies or content digests;
- one mutable unpinned source;
- one source with an explicit official-page-state ambiguity;
- two sources whose parent-contract status is only partially observed on the
  bound locator.

The checked-in builder `--check` and the dedicated snapshot validator also pass
from an exact Git archive with LF-normalized tracked files. The same archive's
repository-wide `scripts/verify.py` remains blocked by the inherited historical
process-fidelity `RAW-REPORT.json` Windows-CRLF runtime-byte versus Git-LF
durable-hash mismatch already recorded by the second bounded evaluation. That
failure neither cancels the source-snapshot portability result nor becomes a
source-snapshot success.

This does not prove external interpretation correctness, normative
completeness, current cross-jurisdiction applicability, independent validity,
evaluation Skill necessity, hard-standard eligibility, or acceptance.
Independent review remains deferred behind candidate capability coverage. Any
later refresh must create a new dated
observation and snapshot rather than silently editing this historical record.

## Authority boundary

This package authorizes no automatic network refresh, external-content
vendoring, license or terms override, Skill, Hook, MCP, Plugin, App, model,
global configuration, CC Switch, hard-standard, acceptance, cross-repository,
release, or deployment mutation.
