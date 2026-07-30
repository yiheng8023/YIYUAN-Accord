# Weak-Agent Live Comparison Batch 03 — Source-Pinned Debugging Skills

Date: 2026-07-24
Status: three source-pinned pairs; mixed outcomes; no preference or causation

This batch compares current Matt `diagnosing-bugs` at immutable revision
`ed37663cc5fbef691ddfecd080dff42f7e7e350d` with the OpenAI-curated
Superpowers 6.1.1 `systematic-debugging` payload. Exact candidate bytes were
materialized into each disposable project's `.agents/skills` directory. No
installed Skill, global configuration, source checkout, account, MCP, network,
Git state, or CALIBRATION artifact was changed.

## Measurement guard

The first attempted pair is retained but excluded. The old marker classifier
treated a stable non-empty project Skill projection as mutation. Both raw
reports are preserved unchanged. After the classifier learned the valid
project-projection pattern, three new pairs were run; the invalid pair is not
silently promoted or discarded.

## Three valid pairs

All six `gpt-5.3-codex-spark/low` runs passed the visible tests, changed only
the three allowed incident files, kept global configuration stable, and
claimed no production recovery.

- Pair 1: Matt recorded two hypotheses instead of its required 3–5.
  Superpowers wrote `exactSymptomReproducedBeforeFix` as an object rather than
  the required boolean. Both failed the full hidden contract for different
  reasons.
- Pair 2: Superpowers passed the full contract. Matt again recorded only one
  hypothesis and failed its candidate-specific process gate.
- Pair 3: Matt passed the full contract. Superpowers passed the hidden
  contract but left no machine-observable failing feedback-loop command before
  the passing test, so it failed the strict red-before-green boundary.

Visible outcomes were 3/3 for both candidates. Full hidden-contract outcomes
were 1/3 for Matt and 2/3 for Superpowers, while the complete strict-process
outcome was 1/3 for each. The failures are qualitatively different and the
sample is one synthetic incident, so the evidence favors neither candidate.

## Treatment and claim boundary

The host discovered and selected the exact project Skill path and accepted the
structured Skill input. A separate synthetic canary established that this host
mechanism can deliver body-only project-Skill content. There is still no
independent loader event or candidate-specific instruction-delivery event, so
the observations remain association rather than causation.

Only the single Superpowers `systematic-debugging` directory was projected.
Its references to other Superpowers Skills were not projected, so this batch
does not represent or evaluate full-Superpowers orchestration.

These results do not prove broad debugging superiority, production incident
competence, cross-host value, portfolio readiness, or a residual gap requiring
self-authored changes. Identical repetitions should stop. The next bounded
step is to project the mixed result into the scenario-evidence matrix and
select a materially different falsifiable software-lifecycle scenario or a
treatment-fidelity probe. The oracle must not be tuned to make either
candidate pass.

Machine-readable evidence:
`registry/human-ai-collaboration-weak-agent-live-comparison-batch-03-2026-07-24.json`.
