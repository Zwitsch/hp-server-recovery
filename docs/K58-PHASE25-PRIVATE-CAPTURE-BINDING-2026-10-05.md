# K58 Phase 25 — private capture binding

Date: 2026-10-05

This is a sanitized milestone record. Private implementation details, production payloads, machine-specific paths, run identifiers, archive hashes and secrets remain excluded from the public repository.

## Accepted private validation

- private Phase-25 capture binding: **PASS**
- bound application files: **335**
- bound runtime/image roles: **6**
- full archive-anchor verification: **PASS**
- focused pilot-binding / Redis-engine / transactional-publication regression: **45/45 PASS**
- retained Phase-24 common capture-contract regression: **42/42 PASS**
- canonical private root regression: **1293/1293 PASS**

The private restore/realtest path now consumes the common capture contract and revalidates bound source metadata before target-changing operations.

## Fail-closed publication hardening

Redis-bound publication was hardened so a failed new publication cannot silently advance `CURRENT` while leaving an older receipt or partial payload set in place.

Accepted negative coverage includes:

- mixed capture runs are rejected
- inconsistent or tampered bindings are rejected
- a failed new publication preserves the previous valid `CURRENT`
- a synthetic failure during commit restores the complete previous publication set
- private capture bindings are limited to isolated realtest mode
- `APP_FULL` remains blocked while database/job-queue consistency is not certified

## Acceptance limits

These results do **not** certify application database/job-queue consistency, queue-consumer behavior, a complete K58 `FULL_SERVER` restore, the 81,328-file Cold restore, or a bare-metal recovery.

- `APP_DATABASE_JOBQUEUE_CONSISTENCY=NOT_CERTIFIED`
- `RESTORE_ALLOWED=false` for the capture contract itself
- `FULL_81328_COLD_RESTORE_PASS=false`

The earlier K56 isolated `FULL_SERVER` result remains the completed end-to-end baseline. K58 Phase 25 is a safety/integration checkpoint toward the final fresh-target disaster-recovery acceptance, not a replacement for it.
