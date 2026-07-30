# CTX-04/05 pre-dispatch handoff packet freshness

Status: local read-only validator and fixtures; no thread or host action.

This narrow gate reuses the existing context-continuation packet builder's
`SOURCE_PATHS`, `collect_git_truth`, and `collect_source_hashes`. It compares an
already-generated packet with a new local file/Git observation immediately
before a separately authorized CTX-04/05 creation call.

It binds the exact repository-owned trial-contract bytes and blocks on
contract drift, source-byte drift, repository-truth drift, malformed private
oracle identity, public-prompt drift, authority promotion, or any
remote-freshness value other than
`local-refs-only-no-network-refresh`. A current result means only that the
packet matched this read-only local observation. It does not create a thread,
read a conversation, invoke a loader, refresh the network, prove a receiver
recovered facts, establish a model condition, prove automatic creation, or
prove live remote freshness.

This is source-byte freshness plus canonical-builder consistency. Several
non-Git critical values are versioned builder/contract assertions rather than
facts semantically extracted from prose, so the gate fixes
`countsAsSourceSemanticFreshnessProof=false`; a current result must not be
described as proof that every source document's meaning was re-derived.

Its result deliberately returns only canonical digests and failure codes; it
does not echo live dirty paths, remotes, branch data, or other repository-truth
details into a caller-visible result.

The public prompt and stale assertions are rebuilt through the existing packet
builder's shared functions. A nonempty but altered prompt therefore fails
closed instead of being treated as current.

The validator is not an atomic cross-file snapshot. Revalidate immediately
inside the future authorized creation critical section; any later source or Git
change requires a newly generated packet. The machine result fixes
`atomicSnapshotProved=false` and
`mustRevalidateInsideAuthorizedCreationCriticalSection=true`; the registry
also fixes `provesAtomicSnapshot=false`.
