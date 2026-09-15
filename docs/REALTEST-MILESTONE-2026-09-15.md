# K22 real-runtime validation milestone — 2026-09-15

This document records a sanitized development milestone for HP Server Recovery.

It deliberately excludes production backup data, credentials, machine identities, private hostnames, private filesystem paths, archive hashes and raw recovery reports.

## Scope

The private full recovery package was validated on a dedicated recovery VM using a real containerd 2.2.x runtime with an explicitly bound overlayfs snapshotter.

The validation sequence included:

1. final package integrity and fresh validation gates
2. root-level regression gates
3. controlled runtime installation
4. read-only inspection of the bound containerd state
5. isolated snapshot migration round-trip
6. independent verification of the persisted round-trip report
7. separately authorized bound system migration apply
8. post-apply verification of runtime and safety boundaries

## Result

The K22 validation sequence completed successfully:

- read-only audit: **PASS**
- isolated migration round-trip: **PASS**
- persisted round-trip report verification: **PASS**
- bound system migration apply: **PASS**
- system Docker safety boundary remained isolated during validation
- rollback evidence remained available after successful migration

## Lifecycle finding

Earlier real-runtime testing showed that an image removal can return before containerd has completed asynchronous cleanup of associated snapshots.

A deletion plan based on a single inventory can therefore become stale between observation and mutation.

K22 addresses this by using a bounded, fail-closed state-stabilization contract:

- re-inventory snapshot state after the image mutation
- keep namespace and snapshotter bindings explicit
- accept only structurally valid expected inventory states
- allow transient partial states only while they monotonically converge toward an allowed terminal state
- re-inventory again before the first explicit snapshot removal
- do not broadly ignore `NOT_FOUND`
- do not introduce generic cleanup, prune behavior or snapshotter fallback

During the successful real system apply, the snapshots were initially still visible after image removal and were then removed asynchronously by containerd. K22 correctly recognized the terminal empty state and did not execute unnecessary explicit snapshot removals.

## Safety boundary

This milestone proves the K22 containerd migration lifecycle in the dedicated recovery environment.

It does **not** prove:

- production readiness
- a complete physical-server restore
- end-to-end disaster recovery for every service and data class
- a stable public release

The public repository remains a sanitized development tree. Private recovery archives and raw machine-specific evidence are intentionally not published.
