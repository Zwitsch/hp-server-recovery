# Recovery and Immich/Filen milestone — 2026-10-03

## Scope

This document records a sanitized private-system milestone for HP Server Recovery and the Immich/Filen storage architecture.

The public repository intentionally excludes production backup archives, credentials, machine identities, private infrastructure paths, raw evidence, private run identifiers and private archive hashes.

## Recovery status

The private K56 recovery package remains end-to-end validated:

- private canonical regression suite: **1050/1050 PASS**
- retained focused fresh-tree gates: **PASS**
- restore scope: **FULL_SERVER**
- restore mode: **COMBINED_L2_L3**
- isolated FULL_SERVER realtest: **COMPLETED**
- isolated-runtime cleanup: **PASS**
- final realtest return code: **0**
- read-only recovery-source boundary: **PASS**
- backup-bound release identity and runtime image identity remain fail closed

The remaining project-endgame work is not a new restore-engine blocker. It is primarily productization and disaster-recovery packaging:

- automatic discovery/onboarding for previously unknown applications;
- final recovery-medium integration;
- end-to-end GUI flow on the recovery environment;
- a real bare-metal restore from a fresh system;
- final restore-from-Cold integration for the new Immich archive tier.

## Immich / Filen architecture

The production architecture is now:

Filen -> read-only rclone FUSE -> official Immich External Libraries -> stock Immich

Current sanitized production state:

- Immich server: **v3.2.1**, healthy
- machine-learning service: **v3.2.4**, healthy
- exactly four owner-specific External Libraries
- active assets total: **83,227**
- active external assets: **81,735**
- active local assets: **1,492**
- offline external assets: **0**

## Final large reclaim

The large migration/reclaim set is complete.

Exact reclaim manifest:

- **81,328** local source files
- logical size: **252.66 GiB**
- local-to-Filen full BLAKE3 verification: **81,328/81,328 PASS**
- local-to-Level-2 full BLAKE3 verification: **81,328/81,328 PASS**
- database owner/path/library/offline validation: **PASS**
- special old-local to current-external path mappings: **21**, all validated

Before any local deletion, all reclaim targets were independently proven against both Filen and Level-2.

## Level-2 Cold archive

The Level-2 mirror already contained the validated files, so the final design avoids an 81k-entry daily rsync protection filter.

Instead, the validated files were materialized as same-filesystem hard links into a dedicated Cold archive outside the normal rsync mirror tree.

Validated result:

- Cold archive entries: **81,328/81,328 PASS**
- same-inode proof before detach: **PASS**
- mirror detach: **81,328/81,328 PASS**
- Cold archive remains outside the productive mirror destination
- productive daily Level-2 backup script remains unchanged
- no second copy of the 252.66 GiB payload was required on Level-2

A previous 81k rsync-filter design was rejected because it was functionally correct but operationally too expensive in CPU, memory and scan time.

## Local reclaim result

The final fail-closed transaction completed successfully:

- exact local allowlist removed: **81,328**
- local reclaim targets still present afterwards: **0**
- manifest state after reclaim: **81,328 COLD_ACTIVE**
- preserved local sidecars: **949/949**
- post-reclaim database gate: **PASS**
- Immich returned healthy after the transaction
- external offline count remained **0**
- Level-2 timer returned active
- Level-2 filesystem returned unmounted

The current local active set of 1,492 assets was outside this reclaim allowlist and was not touched.

## Periodic integrity verification

A dedicated monthly Cold-archive deep verifier is installed and enabled.

It performs full-content BLAKE3 verification of the Cold archive independently from the normal daily Level-2 backup.

The first scheduled automatic run completed successfully on 2026-10-04.

Validated result:

- full Cold archive BLAKE3 verification: **81,328/81,328 PASS**
- service result: **SUCCESS / return code 0**
- Level-2 filesystem was unmounted cleanly afterwards

## Remaining storage/recovery work

The main remaining items are:

1. integrate restore-from-Cold into the final disaster-recovery workflow and test it against a fresh target;
2. classify the remaining 1,492 active local Immich assets;
3. consolidate the earlier small legacy tiering tranche into the long-term Cold/recovery model;
4. complete recovery-medium, automatic onboarding and bare-metal end-to-end validation.

The first normal productive Level-2 run after reclaim is also proven:

- Level-2 service result: **rc=0**
- data mirror: **OK**
- ioBroker mirror: **OK**
- productive Level-2 script identity remained unchanged
- exact post-run structural verification: **PASS**
- detached reclaim paths present in normal mirror: **0/81,328**
- reclaim files present in Cold archive: **81,328/81,328**
- Level-2 filesystem unmounted after verification

## Public/private separation

Only sanitized engineering facts are recorded here. Production archives, credentials, personal identifiers, private network details, raw manifests, private path mappings and raw evidence remain outside this repository.
