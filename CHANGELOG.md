# Changelog

All notable changes to HP Server Recovery will be documented in this file.

The project is currently preparing its first stable OSS release.

## Unreleased

### Added

- Public sanitized source tree for the reusable recovery engine.
- Synthetic runtime catalog, image-lock contracts and application-release fixtures.
- Isolated realtest configuration templates using documentation-only network addresses and reserved example domains.
- GitHub Actions CI on Ubuntu 24.04 with Python 3.12.
- Architecture, safety and contribution documentation.
- Public documentation of the 2026-09-15 K22 real-runtime validation milestone, while keeping private recovery evidence and production data out of the repository.

### Changed

- Generalized isolated realtest host and protected-path bindings so production identities are not hard-coded.
- Separated repository metadata from recovery-package manifest coverage.
- Excluded Git checkout metadata from recovery-package validation.
- Updated the README to reflect the public pre-release state and provide a reproducible external test command.
- Continued isolated runtime validation against containerd 2.2.x and overlayfs behavior.
- Hardened the recovery design around mutation boundaries: runtime state must be re-inventoried after state-changing image or snapshot operations instead of relying on a previously computed deletion plan.
- Added explicit fail-closed handling for unexpected snapshot lifecycle transitions discovered during isolated round-trip testing.
- Extended the private K22 migration lifecycle so the real system-apply path uses the same bounded post-image-removal stabilization model as isolated validation.
- Added fail-closed handling for asynchronous snapshot disappearance without introducing broad cleanup, snapshotter fallback or generic `NOT_FOUND` suppression.

### Development status — 2026-09-15

- K22 read-only runtime audit: **PASS**.
- K22 isolated snapshot migration round-trip: **PASS**.
- Independent K22 round-trip report verification: **PASS**.
- First K22 bound system containerd migration apply on the dedicated recovery VM: **PASS**.
- Report-bound K22 rollback: **PASS**.
- Post-rollback read-only audit of the restored pre-migration snapshot structure: **PASS**.
- Second K22 bound system containerd migration apply: **PASS**.
- `apply -> rollback -> apply`: **PASS**.
- Both successful applies reproduced the same bounded asynchronous snapshot-cleanup lifecycle without unnecessary explicit snapshot removals.
- The next private validation stage is the complete server-restore workflow on the recovery VM.
- No production-ready, full-server-restore or disaster-recovery certification is claimed yet.
- Public releases remain intentionally sanitized and exclude production backup data, credentials, private infrastructure details, machine-specific paths and raw recovery evidence.

### Security

- Destructive recovery logic remains fail-closed when required target identity or safety bindings are missing.
- Public fixtures contain no production credentials, backup data, personal domains, machine UUIDs or private-LAN topology.
- Broad cleanup and fallback behavior remain prohibited in the validated migration lifecycle.
- The sanitized public release tree currently passes 183 automated tests.

## 0.1.0

Planned as the first stable public OSS release after final release-readiness review. No tag has been published yet.
