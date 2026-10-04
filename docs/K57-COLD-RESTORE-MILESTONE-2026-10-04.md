# K57 manifest-bound Immich Cold restore — 2026-10-04

## Scope

The private recovery package extends the previously completed K56 FULL_SERVER restore with a manifest-bound Cold overlay. These private validation results are separate from the sanitized public repository's test suite.

## Restore contract

- Restore the normal Level-2 mirror first.
- Discover the separate Cold archive and bind its identity into the immutable recovery plan.
- Restore only manifest entries in COLD_ACTIVE state; READY_TO_RECLAIM entries are excluded.
- Add Cold bytes to storage preflight for L2_ONLY and COMBINED_L2_L3.
- Validate manifest schema, unique identities, safe relative paths, source containment, file type and size before copying.
- Copy the selected files using one NUL-delimited rsync file list, without --delete.
- Verify target structure and BLAKE3 using the hash-bound offline b3sum payload.
- Complete Cold verification before database, Compose and service operations.
- Fail closed on identity, structure or content mismatches.

Deep-verify receipts are bound to the canonical manifest digest. A present invalid receipt is rejected; a missing receipt does not bypass target BLAKE3 verification. A latest-receipt symlink is not a trust anchor.

## Validation

- Focused K57 tests: **42/42 PASS**.
- Relevant combined regression: **113/113 PASS**.
- Private root canonical suite: **1092/1092 PASS**, return code **0**.
- Fresh archive extraction root canonical suite: **1092/1092 PASS**, return code **0**.
- Two independent fresh extraction manifest checks: **PASS**, covering **124 payload files / 489 package files** each.
- Final private archive SHA256 sidecar check: **PASS**.
- Real L2 Cold pilot: **100 production-origin files / 2,167,636 bytes**, target **BLAKE3 100/100 PASS**.
- Real COMBINED Cold pilot: **100 production-origin files / 2,167,636 bytes**, target **BLAKE3 100/100 PASS**.
- Existing non-Cold sentinel preservation: **PASS** in both pilot restores.

The pilot uses actual COLD_ACTIVE files selected from the production Cold archive. It is not limited to synthetic test data.

## Acceptance boundary

**FULL_81328_COLD_RESTORE_PASS=false**

The full **81,328-file / 252.66-GiB** Cold restore has not been executed on the capacity-limited recovery VM. The COMBINED Cold pilot does not certify a new complete K57 FULL_SERVER end-to-end run. The earlier K56 FULL_SERVER result remains the completed baseline.

Remaining acceptance work includes the full Cold restore on a sufficiently large fresh target, unknown-application onboarding, recovery-medium and GUI boot integration, and real bare-metal end-to-end disaster recovery.

Production payloads, private identities, raw runtime evidence, archive hashes and credentials remain outside this public repository.
