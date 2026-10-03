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
- Public sanitized documentation of the 2026-09-16 K25 read-only realtest milestone and backup/release identity checks.
- Public sanitized documentation of the 2026-09-16 K27 isolated application data restore milestone.
- Public sanitized documentation of the 2026-09-17 K30 isolated full-application restore milestone.\n- Public sanitized documentation of the 2026-10-03 recovery and Immich/Filen migration milestone.

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
- Hardened application backup planning so compatibility requires an exact version + executable image identity match with the selected release.
- Added explicit `INCOMPATIBLE_RELEASE_IDENTITY` handling for mismatched application backup/release tuples.
- Kept data-only planning inside the same provenance contract instead of treating it as an image-identity exception.
- Prevented same-version image fallback, metadata normalization and silent release substitution.
- Unified selected-release identity between planning and execution paths, including previous-release handling.
- Hardened full-app runtime identity handling for containerd-backed Docker image stores by binding verified archive identity, OCI target/manifest digest, image config digest, selected release identity and runtime-resolved identity.
- Added fail-closed isolated runtime-store cleanup before the final secret-marker scan; the marker scan itself remains unchanged and mandatory.
- Bound full-app data ownership to the numerically declared runtime user from the verified image config instead of using a privileged-container workaround.

### Development status — 2026-09-22

- K22 read-only runtime audit: **PASS**.
- K22 isolated snapshot migration round-trip: **PASS**.
- Independent K22 round-trip report verification: **PASS**.
- K22 bound system migration apply / rollback / repeat-apply lifecycle: **PASS**.
- K25 final fresh validation of the private recovery package: **PASS**.
- K25 isolated runtime gate on the dedicated recovery environment: **PASS**.
- K25 read-only application backup/release tuple classification: **PASS**.
- K27 isolated single-application `APP_DATA_ONLY` restore: **PASS**.
- K30 isolated single-application `APP_FULL` restore: **PASS**.
- The restored application data passed integrity and application-specific database checks.
- Offline image provenance, runtime identity binding, runtime cleanup and final secret-marker verification completed successfully.
- A same-version backup created from a different executable image identity is rejected as `INCOMPATIBLE_RELEASE_IDENTITY`.
- The mismatch is fail-closed for data-only, full-app and full-server planning.
- The focused Nextcloud database recovery workflow has completed successfully in the isolated realtest environment.
- The first full-server launch stopped fail-closed during planning when a stale static application-release binding disagreed with the selected backup metadata.
- The direct full-server planning path now resolves application releases from the selected backup and snapshot before compatibility classification, preserving exact version + executable image identity checks.
- A focused backup-bound application release preflight now passes against the selected recovery snapshot without executing a restore.
- Full-server real restore validation remains pending; a full-server restore has not been claimed yet.
- No production-ready or disaster-recovery certification is claimed yet.
- Public releases remain intentionally sanitized and exclude production backup data, credentials, private infrastructure details, machine-specific paths and raw recovery evidence.

### Development status — 2026-10-03

- Private K56 canonical regression suite: **1050/1050 PASS**.
- Isolated private `FULL_SERVER` realtest: **COMPLETED**, `COMBINED_L2_L3`, cleanup **PASS**, return code **0**.
- The remaining disaster-recovery endgame is recovery-medium/GUI integration, automatic onboarding of unknown applications, restore-from-Cold integration and a real bare-metal end-to-end run.
- Production Immich uses stock Immich with official External Libraries through a read-only Filen/rclone FUSE mount.
- Current active asset state: **83,227 total**, **81,735 external**, **1,492 local**, **0 external offline**.
- Final large reclaim manifest: **81,328 files / 252.66 GiB**.
- Exact-set local-to-Filen BLAKE3 verification: **81,328/81,328 PASS**.
- Exact-set local-to-Level-2 BLAKE3 verification: **81,328/81,328 PASS**.
- Level-2 Cold archive materialization and same-inode verification: **81,328/81,328 PASS**.
- Level-2 mirror detach: **81,328/81,328 PASS**.
- Final local reclaim: **PASS** with **0** reclaim targets remaining locally and **949/949** sidecars preserved.
- Post-reclaim database validation: **PASS**; external offline count remained **0**.
- Daily Level-2 backup remains unchanged; monthly full BLAKE3 verification of the Cold archive is enabled.
- The first scheduled automatic Cold deep verify and the first normal productive Level-2 run after reclaim remain open operational proof points.

### Security

- Destructive recovery logic remains fail-closed when required target identity or safety bindings are missing.
- Public fixtures contain no production credentials, backup data, personal domains, machine UUIDs or private-LAN topology.
- Broad cleanup and fallback behavior remain prohibited in the validated migration lifecycle.
- Application backup provenance is bound to the selected executable release identity; equal version strings alone are insufficient.
- The final secret-marker scan remains mandatory after isolated runtime cleanup.
- Backup-bound release selection remains metadata-driven; the newest or merely present release artifact is never selected implicitly.
- The sanitized public release tree remains independently tested; private recovery-package realtest results are not represented as public-suite results.

## 0.1.0

Planned as the first stable public OSS release after final release-readiness review. No tag has been published yet.
