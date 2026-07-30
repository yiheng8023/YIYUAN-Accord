# Matt Current 22 Skill Reuse Boundary Audit

Date: 2026-07-31

Status: **exact-source static reuse audit; no execution or portfolio mutation**

## Result first

Matt's promoted 22 are not 22 equally general-purpose capabilities. They are a
mixture of reusable engineering methods, host- and tracker-bound operating
flows, thin composition wrappers, and two explicit control-plane Skills for
Matt's own suite.

The important correction is not that the suite is "personal and therefore
useless." None of the formal 22 lives under the upstream `skills/personal/`
lifecycle class. The upstream README describes these as the author's everyday
engineering Skills, but most bodies contain no private data or Matt-specific
repository path. Seventeen contain a substantive reusable method or workflow;
the other five are suite control-plane or thin composition entries. The real
reuse boundary is that adopting the whole suite also carries a coherent,
opinionated operating system:

- a fixed idea-to-ship route;
- `CONTEXT.md`, ADR, and `docs/agents/*` conventions;
- a configured issue tracker and canonical triage roles;
- TDD-first implementation and two-axis review;
- parallel/background agents at several stages;
- fresh-session handoffs, temporary HTML, branches, and commits;
- slash-name composition and host-specific invocation metadata.

That operating system may be useful, but it must be evaluated as a workflow,
not inferred from 22 installed names.

The clearest author/suite-bound items are `ask-matt` and
`setup-matt-pocock-skills`. Three more—`grill-with-docs`, `grill-me`, and
`implement`—are thin wrappers whose value comes almost entirely from other
Skills. At the other end, the strongest reusable method bodies are
`diagnosing-bugs`, `tdd`, `to-tickets`, `domain-modeling`,
`codebase-design`, `grilling`, and `handoff`, subject to the authority and host
qualifications below.

No static conclusion here proves invocation, instruction delivery, behavior,
causation, user preference, cross-host parity, or incremental value over
healthy native/official/current capabilities.

## Exact source and method

The governed release authority remains the 22 paths in
[`plugin.json`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/.claude-plugin/plugin.json),
not recursive discovery of every `SKILL.md`. The existing Harness pin is
recorded in
[`skill-portfolio-current-55-subtractive-triage-2026-07-30.json`](../../registry/skill-portfolio-current-55-subtractive-triage-2026-07-30.json).
On 2026-07-31, a live read-only `refs/heads/main` lookup still resolved to the
same immutable revision:

`2ab958093e83e0ec752e6c1c5932da465bf23e0c`

The audit read the exact upstream
[`README.md`](https://github.com/mattpocock/skills/blob/2ab958093e83e0ec752e6c1c5932da465bf23e0c/README.md),
all 22 `SKILL.md` files, every `agents/openai.yaml`, and every co-located
support file. It did not run any Skill instruction or bundled script.
The 22 package trees contain 66 files; the live CC Switch central copies were
also read byte-for-byte against the exact raw Git objects, with zero mismatch,
consistent with the durable
[`2026-07-28 installation report`](../../audits/cc-switch-matt-promoted-suite-installation-2026-07-28/REPORT.json).

At this revision:

- all 22 promoted directories contain `SKILL.md` and
  `agents/openai.yaml`;
- 10 are multi-file packages with additional templates, references, or one
  shell template;
- every Markdown relative link observed in the 22 entry bodies resolves inside
  its exact source directory;
- file completeness does not close cross-Skill or host dependencies;
- `setup-matt-pocock-skills` still mentions deprecated `qa`, which is not in
  the promoted manifest;
- `ask-matt` depends on a host built-in `/compact`, and several flows depend on
  slash-name resolution, background/parallel agents, tracker operations, or
  OS-specific file opening.

The upstream README claims the Skills work with any model, but it also says a
native Codex plugin is still on the roadmap and currently directs Codex and
other agents through `skills.sh`. All 22 include OpenAI interface metadata, but
metadata presence is not proof that Codex and Claude load, compose, authorize,
or execute the bodies equivalently.

## Classification vocabulary

- **General method**: the central reasoning/process can be reused without
  Matt's personal environment.
- **Suite-bound**: the Skill primarily indexes, configures, or composes this
  exact repository's other Skills.
- **Workflow/tool-bound**: the method can be reused, but the current body
  assumes a tracker, Git operation, subagent API, filesystem layout, browser,
  shell, or other host surface.
- **Portable: high/conditional/low**: a static portability estimate, not a
  cross-host test result.
- **Marginal value**: expected contribution to this Harness's ordinary
  human-AI collaboration goals after accounting for current native, official,
  and installed overlap. It is a hypothesis, not behavioral evidence.

## Per-Skill audit

| Skill | Reuse boundary | Dependency and portability | Marginal value for this Harness |
| --- | --- | --- | --- |
| [`ask-matt`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/ask-matt) | **Suite-bound router.** Its useful asset is the explicit topology from idea to ship, not a neutral capability router. It names Matt's flows, assumes their semantics, and even hard-codes a context “smart zone” heuristic. | Two-file package, but operationally depends on almost the whole promoted suite plus host `/compact`. It does not route every promoted item. Slash composition and explicit-only metadata make portability **low** without a suite adapter. | **Low as a runtime adoption; medium as design evidence.** It overlaps the Harness `capability-router` role but supplies a useful concrete workflow graph. It should not replace a dynamic ecosystem router. |
| [`diagnosing-bugs`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/diagnosing-bugs) | **General method.** Tight red-capable feedback loop, minimisation, ranked falsifiable hypotheses, instrumentation, regression test, and cleanup are broadly reusable. No Matt-specific repository is assumed. | Whole package requires the co-located `scripts/hitl-loop.template.sh`; optional `CONTEXT.md`/ADR consumption and handoff to `improve-codebase-architecture` add workflow coupling. The bash fallback is not host-neutral on Windows. Portability **conditional-high** with tool/shell adaptation. | **High method value; incremental value still open.** It targets a real collaboration failure mode, but existing native and historical/current diagnostic comparisons are mixed and do not prove this exact body wins. |
| [`grill-with-docs`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/grill-with-docs) | **Thin suite wrapper.** The seven-line body contributes no independent interview or semantic-authority method; it composes `grilling` and `domain-modeling`. | Its own two files are complete, but dependency completeness requires both named Skills, their support files, slash resolution, and document-write authority. Portability **low** unless the host proves cross-Skill composition. | **Low alone; potentially high only as a tested composition.** This is exactly the SEM-03 question, so source shape must not be credited as semantic continuity. |
| [`triage`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/triage) | **General issue-triage method, strongly workflow-bound.** Its state machine, verification-before-grilling, agent brief, and out-of-scope knowledge capture are reusable. The exact labels and required AI disclaimer are policy choices. | Four-file package; both relative references resolve. Depends on the configured tracker, label mutations, issue/PR comments and closures, code checkout/tests, `grilling`, `domain-modeling`, and setup output. Portability **conditional** on account, tracker, and write authority. | **Medium-high for maintained issue queues; low for ordinary local work.** Valuable only when a real request surface and mutation verification are bound. |
| [`improve-codebase-architecture`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/improve-codebase-architecture) | **General architecture-audit idea, vocabulary-bound.** Hot-spot-first exploration, deletion tests, and visual before/after reports are reusable; mandatory use of one deep-module vocabulary is an author preference. | Three-file package; `HTML-REPORT.md` resolves. Depends on `codebase-design`, `domain-modeling`, `grilling`, an `Agent`/Explore subagent surface, Tailwind/Mermaid CDNs, OS temp, and an OS-specific open command. Portability **low-conditional** without adapters. | **Medium.** Useful for agent-navigability and test seams, but native code exploration and official design/report tools overlap it; the forced vocabulary and CDN report are not universal requirements. |
| [`setup-matt-pocock-skills`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/setup-matt-pocock-skills) | **Suite-specific control plane.** It is not the external one-click installer; it scaffolds repository configuration for the rest of Matt's suite. Its tracker/domain-doc schema is reusable as a reference, not neutral setup authority. | Seven-file package; all five linked templates resolve. It inspects Git/host files, edits `CLAUDE.md` or `AGENTS.md`, writes `docs/agents/*`, and assumes the companion suite. It mentions non-promoted deprecated `qa`. Portability **low** and mutation-heavy. | **Low as-is.** CC Switch and Harness rules already own different layers. Adopting this body would create a second workflow/config authority; only its configuration questions merit reuse. |
| [`tdd`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/tdd) | **General method.** Public-seam tests, red-before-green, independent expected values, and vertical tracer bullets are broadly reusable. “Refactoring is not part of the loop” is a specific process choice, not a universal fact. | Four-file package; `tests.md` and `mocking.md` resolve. Optional project glossary/ADRs and human seam confirmation are the main prerequisites. Portability **high** if the whole folder is exposed. | **High method value, medium incremental value.** Native/runtime and Superpowers TDD capabilities already overlap it, so exact current-body advantage requires scenario evidence. |
| [`to-spec`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/to-spec) | **General synthesis method, tracker-bound.** It converts already-settled conversation into a spec and correctly avoids restarting the interview. The prescribed “extremely extensive” user-story list can introduce verbosity and is not universally desirable. | Two-file package, but requires repository exploration, glossary/ADR conventions, user confirmation of test seams, setup output, tracker publishing, and label mutation. Portability **conditional**. | **Medium.** It can reduce process loss after intent convergence, but the Harness already owns source binding and continuity; tracker publication and template size need adaptation. |
| [`to-tickets`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/to-tickets) | **General method with a valuable graph model.** Tracer-bullet vertical slices, explicit blocking edges, frontier work, and expand-contract treatment for wide refactors are broadly reusable. | Two-file package; operationally depends on setup output and either local `.scratch` files or tracker issue creation/native blocking relations. It requires user approval before publication. Portability **conditional-high** with a tracker adapter. | **High.** This directly supports bounded execution topology and avoids horizontal-plan drift. Reuse should separate the abstract DAG from tracker-specific writes. |
| [`wayfinder`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/wayfinder) | **General large-effort planning model, heavily workflow-bound.** Destination, decision tickets, frontier, and fog-of-war are strong concepts; the exact issue-map operating system is one opinionated implementation. | Two-file package but depends on setup output, tracker child/blocking/assignment/label APIs, concurrent sessions, `grilling`, `domain-modeling`, `prototype`, `research`, subagents, and throwaway research branches. Portability **low-conditional**. | **Medium-high concept value, low immediate adoption value.** It may help very large uncertain programs, but introduces another tracker/thread/branch lifecycle that must be reconciled with Harness authority first. |
| [`implement`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/implement) | **Thin suite wrapper with a full-ownership workflow posture.** It delegates to `tdd` and `code-review` and then completes Matt's expected flow by committing the current branch. | Its two-file package is complete, but real behavior depends on both named Skills, test/typecheck discovery, Git state, commit authority, and branch safety. Portability is **low** without a host authority adapter; the commit step is valid only when that state transition is already authorized. | **Low as a standalone item; useful inside its intended suite flow.** Native implementation plus explicit routing already covers the method. Harness reuse should preserve the sequence while supplying its own side-effect gate. |
| [`prototype`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/prototype) | **General method, artifact-workflow-bound.** A throwaway prototype that answers one question and exposes state is reusable. Mandatory capture on a throwaway branch is a workflow choice. | Four-file package; `LOGIC.md` and `UI.md` resolve. Depends on the project's runner/router, possible browser UI, scratch storage, issue context, branch creation, and commit authority. Portability **conditional**. | **Medium-high for unknown UI/logic questions; medium overall.** It supports simulation-first work, but branch/commit behavior must remain separately authorized. |
| [`research`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/research) | **General method.** Primary-source research delegated to a background agent and captured as a cited Markdown artifact is broadly reusable. | Two-file package with no relative dependency, but requires background-agent support and repository write authority. It does not itself specify source custody, sensitive-data handling, cleanup, or fact-refresh rules. Portability **conditional-high**. | **Medium-high.** It matches the Harness research phase, but the Harness needs stronger provenance, authority, cleanup, and stale-evidence gates than this short body provides. |
| [`domain-modeling`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/domain-modeling) | **General method, document-layout-bound.** Challenging terminology, checking code contradictions, concrete scenarios, and sparing ADR criteria are highly reusable. | Four-file package; both format references resolve. Assumes root or mapped `CONTEXT.md` plus `docs/adr/` and inline repository writes. Portability **conditional-high** when the whole tree and write authority exist. | **High.** It directly targets semantic authority and intent-to-implementation continuity. Exact layout and inline mutation remain treatment choices, not Harness requirements. |
| [`codebase-design`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/codebase-design) | **General but opinionated reference.** Deep modules, seams, leverage, locality, deletion tests, and interface-as-test-surface are reusable; the banned synonym list and one-adapter/two-adapter rule are author choices. | Four-file package; both deeper references resolve. `DESIGN-IT-TWICE.md` introduces parallel-subagent dependence when that branch is used. Core reference portability is **high**, full workflow portability **conditional**. | **Medium-high.** Useful for architecture and test seams, but narrower than the Harness's collaboration goal and should not become universal vocabulary by default. |
| [`code-review`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/code-review) | **General two-axis review method, host/workflow-bound.** Keeping standards and spec fidelity separate is strongly reusable. The fixed smell list is a review policy, not objective truth. | Two-file package; requires a user-bound Git fixed point, repository standards, a spec/tracker source, two parallel general-purpose subagents, and diff/log commands. Portability **conditional** on subagent and tracker surfaces. | **Medium-high method value, medium incremental value.** Native and official code-review capability already exists; value must be tested on missed-requirement and standard-conflict scenarios. |
| [`resolving-merge-conflicts`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/engineering/resolving-merge-conflicts) | **General source-intent method with a resolve-to-completion posture.** Reading commits/issues and preserving both intents is highly reusable. “Always resolve; never abort” plus stage/commit assumes the user has already delegated the complete merge/rebase transaction. | Two-file package and no relative dependencies. It still requires full Git merge/rebase state, issue/PR access, test tools, staging, continuation, and commit authority. Technically portable; governance portability is **conditional** on that full authorization. | **Medium method value; low exact-fit without a transaction gate.** The primary-source and intent-preservation clauses are strong. Harness reuse should add an abort/escalation branch when the complete transaction was not delegated. |
| [`grill-me`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/productivity/grill-me) | **Thin suite wrapper.** The seven-line body contributes no independent elicitation method; all value is in `grilling`. | Two-file package, but depends on host resolution of `/grilling`. Portability **low** without composition; high only if flattened, which would no longer be exact upstream. | **Low as a separate portfolio item.** Keep `grilling` as the candidate method and treat this as a convenience alias. |
| [`grilling`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/productivity/grilling) | **General method.** One decision question at a time, recommended answers, environment lookup for facts, and human ownership of decisions are directly reusable. “Relentlessly” can over-apply if the intake is already clear. | Two-file, dependency-free package. It needs only normal environment access and a multi-turn user channel; action remains explicitly blocked until shared understanding. Portability **high**. | **High.** It addresses intent misalignment without requiring plan mode. It still needs proportional triggering and does not by itself prove downstream projection fidelity. |
| [`handoff`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/productivity/handoff) | **General continuity method.** Referencing durable artifacts instead of duplicating them and redacting sensitive data are broadly reusable. | Two-file package. Assumes access to current conversation context, OS temp writes, a fresh-agent continuation path, and later source loading. It does not verify repository truth or receiver uptake. Portability **conditional-high**. | **High.** It targets process loss directly. Static output quality, fresh-session ingestion, delta detection, and repository freshness still require independent evidence. |
| [`teach`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/productivity/teach) | **General but specialized workspace product.** Mission grounding, learning records, retrieval practice, reusable lesson assets, and primary sources are reusable; the exact HTML curriculum workspace is an opinionated product. | Six-file package; all four format files are present, though only three are linked directly from the entry body. Requires extensive workspace writes, web research, HTML rendering/opening, persistent multi-session state, and sometimes community discovery. Portability **conditional** and lifecycle-heavy. | **Low-medium for the current software-collaboration core; potentially high for a bound teaching use case.** Do not keep it active merely as speculative breadth. |
| [`writing-great-skills`](https://github.com/mattpocock/skills/tree/2ab958093e83e0ec752e6c1c5932da465bf23e0c/skills/productivity/writing-great-skills) | **General Skill-authoring method with ecosystem-specific semantics.** Predictability, progressive disclosure, context pointers, pruning, and failure-mode analysis are reusable. `disable-model-invocation`, description load, and router semantics reflect a particular Skill model. | Three-file package; `GLOSSARY.md` resolves. No executable dependency, but applying the guidance across Claude, Codex, Plugins, and Apps requires mapping each host's actual discovery/invocation lifecycle. Portability **conditional-high as reference**, unproved as runtime behavior. | **Medium-high for later residual-gap authoring; low as ordinary task capability.** It can improve self-authored Skills only after necessity is proved. |

## Cross-cutting conclusions

### 1. "Matt uses it himself" is a provenance clue, not a rejection rule

The exact README says these are the author's everyday engineering Skills and
encourages adaptation. That supports treating the suite as a tested personal
workflow source, but not as universal value evidence. Only two promoted names
are directly suite/control-plane-specific; many others encode general methods.
The correct operation is selective reuse, not bulk rejection or bulk adoption.

### 2. Exact whole-tree acquisition closes only package integrity

The current 22 are dependency-complete at the file-tree level for the observed
revision: entry files, OpenAI metadata, and relative files are present. It does
not follow that:

- a host resolves `/skill-name` references;
- an explicit-only wrapper can invoke another explicit-only Skill;
- background or parallel agents exist with the named interface;
- tracker, Git, browser, shell, and OS-temp operations are authorized;
- the model actually receives every referenced instruction;
- behavior follows the described process;
- the process improves outcomes enough to justify lifecycle cost.

### 3. Cross-host intent exists; cross-host parity does not

Every promoted directory contains `agents/openai.yaml`, and the README offers a
Codex/other-agent installation route. The same README says the native Codex
plugin is future work, while Claude receives a managed plugin. Therefore:

- Claude plugin promotion and Codex file projection are different carriers;
- `disable-model-invocation` and `allow_implicit_invocation` are metadata
  translations, not a universal standard;
- wrappers, slash composition, subagent instructions, and side-effect prompts
  need host-specific exposure and behavior tests;
- CC Switch installation/projection evidence cannot be promoted to parity or
  value evidence.

### 4. Reuse should occur below the bundle boundary

The most defensible next comparison units are:

1. **method candidates**: `diagnosing-bugs`, `tdd`, `to-tickets`,
   `domain-modeling`, `codebase-design`, `grilling`, `handoff`;
2. **workflow candidates requiring host mapping/adapters**: `triage`, `to-spec`,
   `wayfinder`, `prototype`, `research`, `code-review`,
   `improve-codebase-architecture`;
3. **reference-only or convenience composition**: `ask-matt`,
   `grill-with-docs`, `grill-me`, `writing-great-skills`;
4. **reuse inside an explicit authority adapter**: `implement`,
   `resolving-merge-conflicts`, and suite-level
   `setup-matt-pocock-skills`;
5. **task-bound specialist**: `teach`.

These are audit dispositions, not install/disable/delete decisions.

## Evidence boundary and next gate

This review:

- verified the exact current governed revision and promoted manifest;
- read all 22 exact packages and their support files;
- assessed static dependency closure, author/workflow binding, host
  prerequisites, and likely overlap;
- installed, enabled, disabled, updated, or deleted no Skill;
- changed no CC Switch row, projection, Hook, global config, or host rule;
- executed no third-party Skill body or script and sent no model trial.
- removed the exact temporary source checkout after evidence extraction.

The next meaningful gate is scenario-bound comparison, not another count or
metadata pass. Each candidate should be tested only when a concrete task binds
the current-capability gap, data/account boundary, authority boundary, and
verification surface. Exact source presence, installation, exposure, or a
well-written process remains insufficient to claim behavioral value.
