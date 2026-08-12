# History Boundary

The current product was reset from repository state
`c53866726834d79a68c61a5b87b4f7ce90698a2c` on 2026-08-11 after a live audit
showed that a predecessor program still controlled the plan, acceptance map,
verifier, tests, and next-work scheduler.

The exact pre-reset state remains recoverable through Git:

```powershell
git show c53866726834d79a68c61a5b87b4f7ce90698a2c:<path>
git worktree add <isolated-path> c53866726834d79a68c61a5b87b4f7ce90698a2c
```

Do not restore an old file into the current product merely because it existed
or passed its historical verifier. Reuse requires a current acceptance gap, an
exact source, a causal rationale, a bounded authority and cleanup contract, and
the current product verifier.

The predecessor payload corpus and v0.1 receipt files were removed from the
current Git index. Git history is their durable provenance authority. This
keeps raw prompts, machine-local paths, lifecycle incidents, and one-off
scorecards out of the current public tree without rewriting their history. The
accepted v0.1 machine state and its event-specific verifier remain reproducible
at `be498f960c9e0587d355291fb24261c91e75cd77`.

The later user-executed cleanup removed the local ignored `legacy/` quarantine
plus old bytecode caches; exact receipts preserve encountered PowerShell
compatibility errors rather than claiming an error-free script run.

The reset index retains only the bounded current product surface. It removes
the unmapped predecessor payloads from the current index and adds one small
product-control kernel, one product test seam, and one five-outcome acceptance
authority. Exact file and line counts belong in the reviewed Git diff, not in
this long-lived boundary statement.

The v0.2 causal-authority reset was committed and pushed at `a5a0834`. It
established the current terminal-proposition contract and smaller
historical-event-neutral control seam, but deliberately verified none of
O1-O5. After that stop condition was reached, the program moved to `paused`
with no active increment rather than inventing a real task or silently opening
capability work.

A later outcome-neutral authority repair made the product form explicit: an
open, Agent-neutral, demand-driven human-Agent capability control plane whose
durable outputs are a methodology, open standard, and executable reference
implementation. It bound goal-level demand, Agent-owned capability
observation, gap detection, adaptive source-bound discovery, task-scoped
dispatch and release, and Codex-first reference delivery without making Codex,
a fixed catalog, a provider, or a manager part of the portable core. It also
generalized O4 from a software-engineering-only standard to the human-Agent
collaboration core with software engineering as the first reference profile.
This repaired authority and validation semantics but counted as zero O1-O5
progress; the program returned to `paused` with an empty current graph.
