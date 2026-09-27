# Immich / Filen official External Libraries milestone — 2026-09-27

## Architecture

The private production Immich system has moved away from a permanent Immich code-patch architecture for the migrated tier.

The validated architecture is:

Filen -> read-only rclone FUSE -> official Immich External Libraries -> stock Immich

Operational controls:

- exactly four owner-specific External Libraries;
- stock Immich image;
- remote mount is read-only;
- Immich file watcher disabled for the remote library path;
- automatic External Library scans disabled;
- scans are initiated only through a systemd Safe-Scan Guard;
- Level-2 protection remains available even after the corresponding local Tier-1 originals have been reclaimed.

## Production state

Current private production validation:

- Immich version: **v3.2.2**
- health: **healthy**
- migrated external assets: **410**
- sidecars: **11**
- total reclaimed file set: **421 files**
- offline external assets: **0**
- deleted external assets: **0**
- duplicate external original paths: **0**
- local space reclaimed: **100.03 GiB**

Owner distribution is preserved across the four official External Libraries.

A direct Filen-side post-delete verification confirmed the exact 421-file allowlist and byte total after the local originals had been removed.

## Level-2 protection after local reclaim

The Level-2 protection helper was changed so that a locally reclaimed source is not treated as an error when the manifest already carries approved and verified Level-2 evidence.

The missing-local-source realtest passed with all migrated entries absent locally while producing the same protected filter as the pre-reclaim test.

Daily backup protection therefore does not require re-reading and hashing the full approximately 100 GiB migrated tier. Full-content hashing remains appropriate for a separate periodic scrub rather than every daily backup run.

## Immich update validation

The production instance was updated from v3.2.1 to v3.2.2 after the cutover.

Post-update checks remained clean:

- health remained healthy;
- all four External Library asset counts were unchanged;
- offline count remained zero;
- deleted count remained zero;
- duplicate original-path count remained zero;
- Filen FUSE remained read-only;
- the mount service remained active;
- the Safe-Scan timer remained active.

## Scope boundary

This milestone does **not** mean the entire Immich media library is already stored on Filen.

The architecture is complete and the first approximately 100 GiB / 410-asset production tranche has been migrated, verified and locally reclaimed.

The next storage phase is to migrate the remaining suitable Immich media through the same ID-preserving, owner-preserving, fail-closed process.
