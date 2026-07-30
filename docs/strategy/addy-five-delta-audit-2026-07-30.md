# Addy Five Delta Audit

Date: 2026-07-30

Status: **read-only current-source audit; five live bodies remain frozen**

## Result first

The five Addy-derived Skills in the current 55-item CC Switch portfolio are:

1. `ci-cd-and-automation`
2. `deprecation-and-migration`
3. `observability-and-instrumentation`
4. `performance-optimization`
5. `shipping-and-launch`

None should be removed or replaced wholesale from current evidence. None of the
five live bodies is an exact copy of Addy's current `main`, but this is not
ordinary staleness: the live bodies are governed cross-Agent adaptations with
explicit authority, privacy, routing, and self-containment changes. A blind
update would discard those controls and, for three Skills, introduce references
to files or sibling Skills that are absent from their one-file CC projections.

The bounded dispositions are:

| Skill | Current disposition | Next bounded gate |
| --- | --- | --- |
| `ci-cd-and-automation` | Retain frozen; no upstream update | Rebind derivative provenance and test whether vendor-neutral pipeline design adds value beyond native plus host-specific official capabilities |
| `deprecation-and-migration` | Retain only as a falsifiable candidate | Run a materially different ablation after exact treatment fidelity; remove or host-disable if it again adds no value over native governance |
| `observability-and-instrumentation` | Retain, but reference repair is required before removing legacy `diagnose` | Replace the hard-coded legacy identity with a neutral diagnosis route or current `diagnosing-bugs`; review the PII-bearing example |
| `performance-optimization` | Re-review for a selective merge, not exact replacement | Port the upstream keep-or-revert measurement loop while preserving local authority and portability controls |
| `shipping-and-launch` | Retain adapted body; selectively neutralize the dependency-audit wording | Keep local intended/implemented/ready evidence split, authorization gates, and non-personal correlation examples |

This audit did not install, update, delete, enable, disable, invoke, or expose a
Skill. It did not change CC Switch, global configuration, Hooks, MCPs, Plugins,
Apps, or host state, and it sent no model request.

## Authority and repository posture

The repository was inspected before research:

- branch: `main`;
- `HEAD`: `55659f30091990f7c589932e0379880de30dc403`;
- upstream: `origin/main`;
- `origin/main`: `55659f30091990f7c589932e0379880de30dc403`;
- ahead/behind: `0/0`;
- the worktree is intentionally large and dirty; inherited modifications were
  not edited or normalized.

The only durable change made by this audit is this Markdown file.

## Bound source identities

### Governed and live identities

The original governed source pin is
[`17214a29c429a19f7a9607f2c06f9d650ea87eb0`](https://github.com/addyosmani/agent-skills/tree/17214a29c429a19f7a9607f2c06f9d650ea87eb0).
It remains declared in `sources/lock.json`, the selection record, and each live
body's `metadata.source`. The repository adaptations entered at Harness commit
`3e041f02f217b1a1fee5c85f52dfb1463ea34941`; the
`shipping-and-launch` intended/implemented/ready split was added at
`e9832c89c21593d4671db5a731deb49a300cd730`.

All five current live CC bodies are byte-identical to their Harness
`skills/<name>/SKILL.md` copies:

| Skill | Live and Harness SHA-256 | Bytes | Lines |
| --- | --- | ---: | ---: |
| `ci-cd-and-automation` | `7aa008e4be26068c9e61ea8a9303711020e376c6cbfdf10d581a9fd400acf8ea` | 11,470 | 360 |
| `deprecation-and-migration` | `52ef07de05726292c0f5e9fe666cc30e6efbe580ed775621e785a49ec80bd4ea` | 12,510 | 266 |
| `observability-and-instrumentation` | `4ff6d4d23e5b41db29e9b4e289e033ccc1281b986053ca45e83b889955395aa0` | 11,761 | 222 |
| `performance-optimization` | `7faa154ece0c18f4682626016565e4b428b00cebce233b3aa91242126bcc76d2` | 13,282 | 377 |
| `shipping-and-launch` | `195a1fad5612627464df4581954727b8ebd649b0ce4bfe91e06655bcc32302b0` | 11,464 | 338 |

The live CC database rows themselves carry no source metadata. Body metadata
therefore preserves a historical derivation pointer, not manager-enforced
lineage or proof that the body is exact upstream.

### Last reviewed and current upstream identities

The last read-only source review pinned
[`06300e258ef62cdbfbc9b1615ac5b4f58bee05ac`](https://github.com/addyosmani/agent-skills/tree/06300e258ef62cdbfbc9b1615ac5b4f58bee05ac).
Current upstream `main` resolved during this audit to the verified GitHub merge
commit
[`7829ffd90d973b6325f5f12f1b1226dcace74443`](https://github.com/addyosmani/agent-skills/tree/7829ffd90d973b6325f5f12f1b1226dcace74443),
dated 2026-07-26T12:51:12Z.

Only two selected paths changed between the last review and current `main`:

- `performance-optimization`: `+47/-1`, from
  [`611990819839b2847964c6f7fc86eda60d095935`](https://github.com/addyosmani/agent-skills/commit/611990819839b2847964c6f7fc86eda60d095935);
- `shipping-and-launch`: `+1/-1`, from
  [`45ccfb6f3dcb0116e91f8a0d5a8338840c1b404f`](https://github.com/addyosmani/agent-skills/commit/45ccfb6f3dcb0116e91f8a0d5a8338840c1b404f).

The other three selected path blobs did not change in that interval.

| Skill | `17214a2` blob | `06300e2` blob | Current `7829ffd` blob | Current upstream relative to live, LF-normalized |
| --- | --- | --- | --- | ---: |
| `ci-cd-and-automation` | `118456fcb10225c030769a4fee7815b9c536b0ce` | same | same | `+65/-35` |
| `deprecation-and-migration` | `258e2a0396c9c2cb639cff84a9db64753740be96` | `765bdde6329dbd5fd22d5d3fc2c185737fc9f908` | same | `+77/-96` |
| `observability-and-instrumentation` | `c151387152bf203eee2e7f44b16f3d90341d26f2` | same | same | `+4/-23` |
| `performance-optimization` | `dcc37e047cbd9e95f15c06dfa9bff860214acf92` | `fbfcc55773b345bb0edec75bc22bd71629cf2fb5` | `d4c1b9fc5925d8f0d6e9f1dc70796ba6ff624687` | `+63/-44` |
| `shipping-and-launch` | `870323c394390744c3c111b5f7810985bc323d03` | `eebcc6cbb1b89d978fef1b594136b6b28990e5eb` | `d679f3ccec9326da488ded6bfbc0c4a7ee07b497` | `+13/-41` |

The current upstream license remains MIT. The selected upstream directories
contain one `SKILL.md` each and no executable scripts. That sharply limits the
selected-tree supply-chain surface, but the Markdown remains a behavioral
execution surface because it tells an authorized Agent to run commands and
change systems.

## Cross-cutting dependency and supply-chain findings

### One-file CC projections are not dependency-complete for exact current upstream

Current upstream assumes the full repository/plugin context:

- `observability-and-instrumentation` refers to
  `debugging-and-error-recovery`, `security-and-hardening`,
  `performance-optimization`, `shipping-and-launch`, and
  `references/observability-checklist.md`;
- `performance-optimization` refers to a Chrome DevTools MCP and
  `references/performance-checklist.md`;
- `shipping-and-launch` refers to four root `references/*.md` files;
- `deprecation-and-migration` refers to `incremental-implementation`.

Those root references are not present in any of the live one-file CC trees,
and the current 55-item portfolio does not carry every named Addy sibling.
Whole-repository installation would change the trust, routing, Hook, command,
agent, and maintenance boundary and is not an acceptable shortcut around this
dependency gap.

### Current live adaptations retain important controls

Across the five bodies, the local adaptations add or preserve:

- explicit separation between planning/evidence and commit, push, merge,
  release, deploy, rollback, deletion, production, account, secret, and data
  authority;
- environment-neutral handoff to specialized capabilities;
- self-contained verification instead of missing root reference files;
- privacy, retention, redaction, data-minimization, access-control, and cost
  gates for telemetry;
- a shipping evidence split between intended, implemented, and ready;
- a non-personal request/correlation identifier instead of current upstream's
  direct `userId` logging examples.

These are material differences. An exact-source update is not semantics
preserving.

### Remaining instruction-level risks

The live bodies still contain runnable-looking examples whose dependencies and
authority must be resolved per task:

- unpinned `npx` commands such as `npx migrate-check`, `npx bundlesize`, and
  `npx lhci`;
- GitHub Actions using mutable major tags such as `actions/checkout@v4`;
- Vercel deployment and token examples;
- database migrations, cache changes, feature flags, rollback, external
  telemetry, and production configuration;
- a structured-log example containing `userId`, despite the surrounding PII
  warning.

No command was executed in this audit. Before future admission or adaptation,
runnable examples should be treated as illustrative until the repository,
package version, account, secret, data, cost, and mutation authority are bound.

The full Addy repository also contains Hooks, commands, agents, CI workflows,
and validators outside the selected five trees. Prior review found risks in
those broader surfaces. This audit does not inherit their trust merely because
the five Markdown files remain candidates.

## Per-Skill adjudication

### `ci-cd-and-automation`

**Function.** Designs pipeline quality gates, test stages, feedback loops,
preview delivery, secrets layout, dependency automation, and CI performance.

**Current upstream delta.** Its selected-path blob is unchanged from both the
original pin and last review. The large live/current difference is the governed
adaptation, not new upstream work.

**Dependencies and authority.** Examples assume GitHub Actions, Node/npm,
PostgreSQL, Playwright, Vercel, repository workflow writes, CI secrets, branch
protection, deployment credentials, and possibly account configuration. Live
wording correctly withholds those authorities and delegates active failure
diagnosis.

**Overlap.**

- Native reasoning and repository commands can edit a pipeline but do not
  provide a durable cross-platform pipeline policy.
- The current OpenAI GitHub `gh-fix-ci` Skill is specifically for failing
  GitHub PR checks and requires GitHub/`gh` access; it does not replace pipeline
  design.
- The current Vercel `deployments-cicd` Skill is deeper but Vercel-specific.
- Matt's `tdd`, `implement`, `code-review`, and `diagnosing-bugs` provide
  adjacent test/change/failure workflows, not CI architecture.
- `shipping-and-launch` should retain rollout and GO/NO-GO ownership; the live
  CI adaptation already removes most duplicated rollout policy.

**Decision.** **Retain frozen and rebind provenance; no upstream update.**
Future value testing should compare one concrete non-Vercel pipeline-design
task against native plus official host-specific capabilities. If that test
shows no incremental value, host-disable or removal becomes supportable.

### `deprecation-and-migration`

**Function.** Governs lifecycle cost, consumer migration, compatibility,
strangler/adapter/feature-flag patterns, controlled withdrawal, retention, and
removal readiness.

**Current upstream delta.** No change since `06300e2`. Between the original pin
and last review, upstream added a database expand/backfill/contract section,
including destructive schema guidance and a requirement for a tested down
path. The live adaptation deliberately keeps broader safety, retention,
withdrawal, affected-subject, and explicit-removal controls instead of taking
that section wholesale.

**Dependencies and authority.** Migration can change code, schemas, data,
consumer access, production configuration, archival and retention state. The
literal `npx migrate-check` example is not repository-bound and must not be
treated as an approved executable. Upstream also refers to the absent Addy
`incremental-implementation` sibling.

**Overlap.**

- Native intake and repository governance cover authority and evidence but do
  not necessarily supply a reusable lifecycle migration method.
- Matt's `migrate-to-shoehorn` is a narrow TypeScript test-data migration, not
  a general deprecation workflow.
- `observability-and-instrumentation` supplies usage evidence, and
  `shipping-and-launch` supplies rollout/rollback decisions; neither replaces
  migration ownership.
- The existing bounded comparison produced visible `3/3` versus `3/3`, hidden
  native `3/3` versus selected Skill `1/3`, and clean-process `3/3` versus
  `3/3`. It proves neither causation nor general preference, but it does reject
  an assumption that installation alone adds value.

**Decision.** **Retain temporarily as a falsifiable candidate; prioritize
re-review and ablation.** Do not update. A materially different scenario with
exact treatment fidelity should determine whether the Skill has a repeatable
residual advantage. If not, this is the strongest subtraction candidate among
the five.

### `observability-and-instrumentation`

**Function.** Provides logs, RED/USE metrics, traces, OpenTelemetry, SLOs,
alerts, cardinality controls, and staging verification.

**Current upstream delta.** No selected-path change since the original pin.
Current upstream replaces the live neutral/legacy diagnosis route with
`debugging-and-error-recovery`, delegates privacy to
`security-and-hardening`, and points to a missing root checklist.

**Dependencies and authority.** Installing SDKs, connecting telemetry vendors,
expanding data collection, changing production configuration, and deploying
cross new account, privacy, retention, cost, and data boundaries. Both live and
upstream include a `userId` logging example; the live body otherwise states a
strong no-unredacted-PII policy.

**Overlap.**

- The current Vercel `observability` Skill is a deep official adapter for
  Vercel logs, drains, analytics, Speed Insights, and OpenTelemetry, not a
  portable default.
- Native capabilities and Matt `diagnosing-bugs` consume telemetry for
  investigation but do not replace instrumentation design.
- `performance-optimization` consumes measurements; `shipping-and-launch`
  consumes health signals. Their ownership boundaries are complementary.

**Decision.** **Retain, but do not leave the legacy identity unresolved.**
Before `diagnose` can be removed, authorize a narrow adaptation that replaces
it with a neutral diagnosis capability or current Matt `diagnosing-bugs`.
During the same review, replace the `userId` example with a non-personal
correlation identifier. Do not replace the body with exact upstream because
that would lose local privacy/authority controls and create missing
dependencies.

### `performance-optimization`

**Function.** Supplies measurement-first frontend/backend/database performance
work, budgets, bottleneck isolation, profiling, Web Vitals, caching, query and
bundle guidance, and regression checks.

**Current upstream delta.** The new upstream section is materially useful:
repeat the baseline under identical conditions, change one variable at a time,
beat observed variance, revert neutral or correctness-breaking changes, and
record both successful and rejected experiments. This closes a real process
loss between `FIX` and `GUARD`.

**Dependencies and authority.** Profilers, RUM, CrUX, database traces, package
execution, caching, CI budgets, infrastructure changes, and production
telemetry cross tool, privacy, cost, and mutation boundaries. Current upstream
also assumes a Chrome DevTools MCP and a missing root checklist. The live body
correctly uses whatever specialized capability is available and states that
optimization starts after evidence identifies a target.

**Overlap.**

- The bundled Chrome/browser capability can collect runtime evidence, but it
  is an execution adapter rather than a cross-stack optimization contract.
- Vercel `react-best-practices` is high-value but React/Next.js-specific;
  Vercel `observability` is platform-specific.
- Matt `diagnosing-bugs` covers hard performance regressions but not proactive
  budgets or cross-stack optimization.
- The live observability and shipping Skills own production measurement and
  launch decisions respectively.

**Decision.** **Re-review for a selective upstream merge.** Port the
keep-or-revert loop and attempt ledger into the adapted body after separate
authorization, while preserving environment-neutral profiling, project SLOs,
authorization gates, and self-contained verification. Do not take current
upstream verbatim.

### `shipping-and-launch`

**Function.** Owns production readiness, staged rollout, feature-flag
lifecycle, monitoring thresholds, rollback planning, communication, and
post-launch verification.

**Current upstream delta.** One useful but small change replaces a
Node-only `npm audit` checkbox with the active ecosystem's dependency audit.
The rest of the current/live difference predates the last review.

**Dependencies and authority.** Production deploy, feature flags, databases,
monitoring, security scans, support communication, Git revert/push, and
rollback are independent state transitions. Current upstream directly shows
`git revert <commit> && git push`, says to roll back immediately, and logs
`userId`; the live adaptation instead requires authorization and uses a
request/correlation identifier. Current upstream also points to four absent
root checklists.

**Overlap.**

- Vercel `deployments-cicd` is a deep official adapter when Vercel is the
  target; it does not own a vendor-neutral release-readiness decision.
- GitHub publication and CI capabilities can publish or validate artifacts but
  do not replace cross-system GO/NO-GO, rollout, monitoring, and rollback
  evidence.
- Matt `code-review`, `tdd`, `implement`, and `handoff` provide prerequisite
  evidence. They do not own production launch.
- The self-authored `closure-contract` guards truthful task closeout; it is not
  a deployment procedure and should not be treated as a replacement.

**Decision.** **Retain the adapted body and selectively adopt only the
ecosystem-neutral dependency-audit wording after review.** Preserve the local
intended/implemented/ready split, authorization gates, non-personal telemetry
examples, and self-contained specialized handoffs.

## Portfolio-level decision

The current evidence supports no bulk Addy transaction.

Recommended order:

1. repair the `observability-and-instrumentation` reference before any
   authorized `diagnose` removal;
2. review a selective `performance-optimization` verification-loop merge;
3. run the materially different `deprecation-and-migration` ablation;
4. optionally neutralize the one `shipping-and-launch` audit line;
5. leave `ci-cd-and-automation` unchanged until a task-bound pipeline-design
   value test exists;
6. after each change candidate, rerun source identity, one-file dependency,
   host exposure, instruction delivery, behavior, and value checks separately.

Each body should eventually have a derivative identity that binds:

- exact upstream source pin;
- exact local adaptation commit or patch digest;
- co-located license/notice handling for redistribution;
- current CC manager lineage;
- declared sibling/reference dependencies;
- task, data, account, permission, and verification boundaries;
- host-specific enablement and exposure evidence.

That work is provenance and admission repair, not a reason to install the full
upstream repository or overwrite the live bodies.

## Primary sources and commands

Primary external sources:

- Addy source repository at current pin:
  <https://github.com/addyosmani/agent-skills/tree/7829ffd90d973b6325f5f12f1b1226dcace74443>
- Addy MIT license at current pin:
  <https://github.com/addyosmani/agent-skills/blob/7829ffd90d973b6325f5f12f1b1226dcace74443/LICENSE>
- performance delta:
  <https://github.com/addyosmani/agent-skills/commit/611990819839b2847964c6f7fc86eda60d095935>
- ecosystem-neutral shipping delta:
  <https://github.com/addyosmani/agent-skills/commit/45ccfb6f3dcb0116e91f8a0d5a8338840c1b404f>
- Addy plugin manifests at the same current pin:
  [Claude](https://github.com/addyosmani/agent-skills/blob/7829ffd90d973b6325f5f12f1b1226dcace74443/.claude-plugin/plugin.json) and
  [Codex](https://github.com/addyosmani/agent-skills/blob/7829ffd90d973b6325f5f12f1b1226dcace74443/.codex-plugin/plugin.json)
- current Matt exact source pin used for overlap:
  <https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c>
- installed OpenAI-owned capability sources inspected read-only:
  GitHub `gh-fix-ci` package `0.1.8-2841cf9749ae`,
  Vercel package `0.21.4`, Codex Security package `0.1.14`, and bundled Chrome
  package `26.721.41059`.

Repository evidence used:

- `registry/skill-portfolio-current-55-subtractive-triage-2026-07-30.json`;
- `registry/legacy-curated-skill-source-migration-review-2026-07-18.json`;
- `sources/lock.json`;
- `sources/addyosmani-agent-skills/selection.json`;
- `audits/addyosmani-agent-skills/17214a29c429a19f7a9607f2c06f9d650ea87eb0/`;
- `registry/human-ai-collaboration-scenario-evidence-matrix-batch-01-2026-07-24.json`;
- `docs/strategy/SKILL-ECOSYSTEM-CURRENT-EVIDENCE-RECONCILIATION-2026-07-27.md`;
- the five live CC bodies and corresponding Harness Skill copies.

Representative commands:

```powershell
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git rev-list --left-right --count HEAD...origin/main
git clone --filter=blob:none --no-checkout https://github.com/addyosmani/agent-skills.git <temporary-root>
git checkout --detach 7829ffd90d973b6325f5f12f1b1226dcace74443
git log --format="%H`t%aI`t%s" 06300e2..HEAD -- <five-paths>
git diff --name-status 06300e2..HEAD -- <five-paths>
git diff --no-index --ignore-space-at-eol --numstat <live-body> <upstream-body>
git rev-parse <revision>:skills/<name>/SKILL.md
gh api repos/addyosmani/agent-skills/commits/<sha>
Get-FileHash -Algorithm SHA256 <live-body>
rg -n <dependency-and-authority-patterns> <five-bodies>
```

## Residual uncertainty

- This is static source, dependency, overlap, and permission analysis. It is not
  invocation, instruction-delivery, behavioral-value, or cross-host evidence.
- The current official Plugin source inventory proves source presence only; it
  does not prove enablement, exposure, invocation, or value in a particular
  task.
- The mixed `deprecation-and-migration` trial did not independently prove
  loader causation or candidate instruction delivery.
- No real CI provider, telemetry account, production system, database,
  deployment platform, or user data was accessed.
- No legal conclusion is made beyond observing the upstream MIT license and
  the need to preserve license/provenance when redistributing derivatives.
- Upstream `main` can move. All findings are bound to
  `7829ffd90d973b6325f5f12f1b1226dcace74443`.
- This audit does not prove that any retained Skill has cross-Agent value.
  Removal, selective adaptation, source rebinding, and host toggles remain
  separate, authorization-gated transactions.
