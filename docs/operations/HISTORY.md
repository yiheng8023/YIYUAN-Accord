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

The unmapped predecessor payload corpus was removed from the current Git index.
Git history is its durable provenance authority. A small bounded set of v0.1
release receipts remains tracked under `product/evidence`; those files are
inactive historical evidence, not current product, planning, acceptance,
runtime, or release authority. The accepted v0.1 machine state and its
event-specific verifier remain reproducible at
`be498f960c9e0587d355291fb24261c91e75cd77`.

The later user-executed cleanup removed the local ignored `legacy/` quarantine
plus old bytecode caches; exact receipts preserve encountered PowerShell
compatibility errors rather than claiming an error-free script run.

The reset index retains only the bounded current product surface. It removes
the unmapped predecessor payloads from the current index and adds one small
product-control kernel, one product test seam, and one five-outcome acceptance
authority. Exact file and line counts belong in the reviewed Git diff, not in
this long-lived boundary statement.
