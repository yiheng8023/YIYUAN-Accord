# Standard Revalidation Cascade PoC

## Status and purpose

This checkpoint implements a deterministic, pure-zero-model planner for the
graph-scoped revalidation cascade described by the historical design contract.
It uses one declared-synthetic accepted-standard record and graph. It does not
represent or admit a real standard, execute a migration, mutate another
repository, deprecate a projection, or authorize a big-bang rewrite.

The planner computes only the downstream closure of explicitly affected nodes,
excludes unrelated nodes, rejects affected cycles, unknown relationship or node
types, and duplicate node identities, requires accountable owner and revision
identity, orders bounded batches after all affected predecessors, and carries
per-node historical debt, migration fixture, verification fixture, rollback,
and target-revision fields. The checked-in ledger exercises twenty-one
single-boundary mutations. Old projection deprecation remains after verification
of every affected node.

## Acceptance boundary

This PoC supplies an implemented graph query, synthetic migration fixtures, and
deterministic plan verification. It does not supply real owner admission or
project admission evidence, so `acceptance.standard-revalidation-cascade`
remains `partial`.

Evidence identifiers and synthetic admission receipts prove structural binding
only. They do not establish evidence truth, standard value, operational
correctness, cross-host behavior, production readiness, or authority to write.
