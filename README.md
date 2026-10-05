# HP Server Recovery

[![Tests](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml/badge.svg)](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml)

Fail-closed disaster recovery framework for self-hosted Linux servers.

> **Status:** public sanitized pre-release. The complete private recovery package has passed its isolated FULL_SERVER end-to-end realtest. The public repository remains a sanitized engineering subset and is not a drop-in production recovery image.

## What it does

HP Server Recovery is designed to make restoration of a self-hosted Linux server reproducible, testable and conservative by default.

Core design goals:

- fail closed when recovery inputs, target identity or safety bindings are missing or ambiguous
- separate generic recovery logic from host-specific configuration
- validate manifests and release identity before destructive operations
- support fixture-driven tests and isolated real-restore testing
- make recovery state, command execution and cleanup auditable
- keep secrets, production payloads and machine identities outside the source repository

## Safety model

The recovery engine treats destructive actions as explicitly gated operations. Isolated realtests require bound target identities, allowed and forbidden hostnames, protected path prefixes, read-only recovery sources and an isolated container runtime. Missing bindings cause the operation to stop instead of falling back to permissive defaults.

Persistent reports and audit data are checked for secret-marker leakage before a run can be considered complete.

See [SECURITY.md](SECURITY.md) and `docs/SAFETY-MODEL.md`.

## Current private recovery milestone — 2026-10-04

### English

The private K56 recovery package remains end-to-end proven.

Current sanitized validation status:

- private canonical regression suite: **1050/1050 PASS**
- retained focused fresh-tree gates: **PASS**
- dynamic backup-bound CURRENT release resolution: **PASS**
- worker-root and report-state hardening: **PASS**
- Compose symbolic/runtime release-binding hardening: **PASS**
- DeviceWatchdog configuration-format contract hardening: **PASS**
- isolated FULL_SERVER realtest: **COMPLETED**
- restore mode: **COMBINED_L2_L3**
- isolated runtime cleanup: **PASS**
- final realtest return code: **0**

The remaining project-endgame work is primarily automatic onboarding of unknown applications, final recovery-medium/GUI integration, full Cold-restore acceptance and a real bare-metal end-to-end disaster-recovery run.

### Deutsch

Das private K56-Recovery-Paket ist weiterhin End-to-End real bewiesen.

Aktueller sanitisierter Validierungsstand:

- private kanonische Regression: **1050/1050 PASS**
- beibehaltene fokussierte Fresh-Gates: **PASS**
- dynamische backup-gebundene CURRENT-Release-Auflösung: **PASS**
- Worker-Root- und Report-State-Härtung: **PASS**
- Härtung der symbolischen/Runtime-Compose-Release-Bindung: **PASS**
- Härtung des DeviceWatchdog-Konfigurationsformat-Vertrags: **PASS**
- isolierter FULL_SERVER-Realtest: **COMPLETED**
- Restore-Modus: **COMBINED_L2_L3**
- Cleanup der isolierten Runtime: **PASS**
- finaler Realtest-Rückgabecode: **0**

Die verbleibenden Arbeiten bis zum eigentlichen Disaster-Recovery-Endziel betreffen vor allem Auto-Onboarding unbekannter Apps, das finale Recovery-Medium samt GUI, die vollständige Cold-Restore-Abnahme sowie einen echten Bare-Metal-End-to-End-Lauf.

See:

- `docs/FINAL-RECOVERY-MILESTONE-2026-09-27.md`
- `docs/RECOVERY-IMMICH-MILESTONE-2026-10-03.md`

## K57 Cold-restore validation — 2026-10-04

The private K57 package now supports a manifest-bound Cold overlay after the normal Level-2 mirror restore and before database/service restoration.

- private canonical regression and fresh-extraction root regression: **1092/1092 PASS** each
- fresh extraction manifests: **PASS** for both independent extractions
- real L2 and COMBINED Cold pilots: **100 production-origin files / 2,167,636 bytes** each
- target BLAKE3: **100/100 PASS** in both pilots
- existing non-Cold sentinel preservation: **PASS** in both pilots
- full **81,328-file / 252.66-GiB** Cold restore: **not yet executed**

K57 pilot validation does not replace the earlier K56 FULL_SERVER result or certify a complete K57 bare-metal recovery.

Der private K57-Cold-Restore ist im L2- und COMBINED-Pilot real bewiesen. Beide Piloten restaurierten je **100 echte Dateien / 2.167.636 Bytes**, mit **100/100 BLAKE3-PASS**. Die Root-Regression und die Fresh-Root-Regression bestanden jeweils **1092/1092** Tests. Der vollständige Restore von **81.328 Dateien / 252,66 GiB** bleibt für den ausreichend großen Fresh-Target-/Bare-Metal-Abnahmetest offen.

See [K57 Cold-restore milestone](docs/K57-COLD-RESTORE-MILESTONE-2026-10-04.md).

## K58 progress checkpoint — 2026-10-05

This checkpoint supersedes the earlier K58 progress paragraph below. It records private validation results; it does not claim that the corresponding private implementation or tests have been published in this sanitized repository.

- latest completed private canonical root regression (phase 14): **1281/1281 PASS**
- real Redis restore from bound published input, package materialization and engine staging: **PASS**, including isolated cleanup
- complete post-integration L2 and local L3 backup runs: **PASS**; remote cloud completion is not established by the local L3 result
- application writer-hold capture with subsequent service resumption and payload hashing: **PASS**
- isolated restore of the captured Immich PostgreSQL database, Paperless SQLite database and both Redis snapshots (phase 20): **PASS**
- additional capture-bound offline image export, transfer and archive validation (phase 21): **PASS**
- bound Paperless file package and limited Immich marker package, including transfer verification (phase 22): **PASS**
- limited Paperless ORM / Immich API start pilot (phase 23): **PASS**, with both database and Redis loads, source binding, isolation and cleanup passing; elapsed time **15 min 42 sec**

**Acceptance limits remain explicit:**

- `APP_DATABASE_JOBQUEUE_CONSISTENCY=NOT_CERTIFIED`
- `FULL_81328_COLD_RESTORE_PASS=false`
- no complete K58 FULL_SERVER or bare-metal acceptance is claimed
- common database/queue capture is not yet integrated and accepted throughout the regular backup/restore workflow
- the app-start pilot does not include the complete Immich media library or certify queue-consumer behavior
- the full Cold restore remains deferred because an adequately sized recovery target is unavailable

Deutsch: Der private Stand ist bis Phase 23 durch die genannten Teilnachweise dokumentiert. Paperless-ORM und Immich-API-Start sowie das Cleanup bestanden; vollständige App-/Queue-Funktionalität bleibt offen. Erfolgreiche Datenbank- und Redis-Ladevorgänge ersetzen weder die Prüfung der Datenbank-/Jobqueue-Konsistenz noch einen vollständigen Disaster-Recovery-Test. Der letzte kanonische Root-Lauf bestand 1281/1281 Tests; die spätere Pilotentwicklung wurde separat geprüft.

## K58 inventory and backup binding — 2026-10-04

The private K58 phase-2 root regression passed **1144/1144** tests. The production backup integration passed **18/18** separate binding tests, installation, a fresh application export, receipt verification and bound inventory publication to a local pilot target.

The installed L2/L3 scripts now include explicit inventory publication. Complete post-installation L2/L3 backup runs and full K58 recovery acceptance remain open. Automatic onboarding is incomplete: runtime service/mount coverage, exact offline images, secrets and isolated restore contracts still require validation.

Die K58-Root-Regression bestand **1144/1144** Tests; **18/18** separate Bindungstests und der frische produktive App-Export mit Inventarpublikation bestanden ebenfalls. Dies bestätigt noch keinen vollständigen L2/L3-Backup-Lauf oder K58-Full-Server-Restore.

See [K58 accepted checkpoints and remaining work](docs/K58-INVENTORY-BINDING-MILESTONE-2026-10-04.md).

## Immich / Filen official External Libraries — 2026-10-03

### English

The production storage architecture is now:

Filen -> read-only rclone FUSE -> official Immich External Libraries -> stock Immich

Current sanitized production state:

- Immich server **v3.2.1**, healthy
- machine-learning service **v3.2.4**, healthy
- exactly four owner-specific External Libraries
- **83,227** active assets total
- **81,735** active external assets
- **1,492** active local assets
- **0** offline external assets
- final large reclaim set: **81,328 files / 252.66 GiB**
- local-to-Filen BLAKE3: **81,328/81,328 PASS**
- local-to-Level-2 BLAKE3: **81,328/81,328 PASS**
- Level-2 Cold archive: **81,328/81,328 PASS**
- Level-2 mirror detach: **81,328/81,328 PASS**
- final local reclaim: **PASS**
- local reclaim targets remaining: **0**
- preserved sidecars: **949/949**
- post-reclaim database validation: **PASS**
- monthly Cold-archive BLAKE3 deep verifier: **enabled**

At the 2026-10-03 milestone, the productive daily Level-2 backup script remained unchanged; the later K58 inventory integration is recorded above. The large Cold archive is stored outside the normal mirror tree, so daily backup operation does not require an 81k-entry rsync protection filter or daily full-content hashing.

The first scheduled automatic Cold deep-verify and the first normal productive Level-2 backup after reclaim have both completed successfully. Exact post-run structure verification confirmed **0/81,328** detached reclaim paths in the normal mirror and **81,328/81,328** files present in the Cold archive.

### Deutsch

Die produktive Speicherarchitektur lautet jetzt:

Filen -> read-only rclone FUSE -> offizielle Immich External Libraries -> Stock-Immich

Aktueller sanitisierter Produktivstand:

- Immich-Server **v3.2.1**, healthy
- Machine-Learning-Service **v3.2.4**, healthy
- genau vier benutzerspezifische External Libraries
- **83.227** aktive Assets insgesamt
- **81.735** aktive External Assets
- **1.492** aktive lokale Assets
- **0** Offline-External-Assets
- finaler großer Reclaim: **81.328 Dateien / 252,66 GiB**
- Local↔Filen BLAKE3: **81.328/81.328 PASS**
- Local↔Level-2 BLAKE3: **81.328/81.328 PASS**
- Level-2-Cold-Archiv: **81.328/81.328 PASS**
- Level-2-Mirror-Detach: **81.328/81.328 PASS**
- finaler lokaler Reclaim: **PASS**
- verbleibende Reclaim-Zieldateien lokal: **0**
- Sidecars erhalten: **949/949**
- Post-Reclaim-Datenbankprüfung: **PASS**
- monatlicher Cold-Archiv-BLAKE3-Deep-Verify: **enabled**

Zum Meilenstein vom 03.10.2026 blieb das produktive tägliche Level-2-Backup-Skript unverändert; die spätere K58-Inventarintegration ist oben dokumentiert. Das große Cold-Archiv liegt außerhalb des normalen Mirror-Baums; dadurch sind weder ein 81k-Rsync-Schutzfilter noch tägliche Vollhashes erforderlich.

Der erste automatische Cold-Deep-Verify und der erste normale produktive Level-2-Lauf nach dem Reclaim sind erfolgreich abgeschlossen. Die exakte Strukturprüfung bestätigte **0/81.328** abgetrennte Reclaim-Pfade im normalen Mirror und **81.328/81.328** Dateien im Cold-Archiv.

See:

- `docs/RECOVERY-IMMICH-MILESTONE-2026-10-03.md`
- `docs/IMMICH-FILEN-EXTERNAL-LIBRARIES-2026-09-27.md`

## Repository structure

- `lib/hp_recovery/` — reusable recovery engine
- `bin/` — command-line entry points
- `config/` — sanitized example configuration
- `tests/` — automated tests and synthetic fixtures
- `runtime-data/` — synthetic catalog data used by the test package
- `manifests/` — integrity manifest for the synthetic package
- `payload/` — synthetic test-only package contracts; no production payloads

## Test status

The sanitized public release tree currently passes **183/183 automated tests**, including:

- recovery planner and state-machine tests
- confirmation and storage safety gates
- wizard behavior
- isolated realtest identity binding
- read-only source enforcement
- target/source overlap protection
- Docker Compose isolation
- cleanup and resume behavior
- secret-marker redaction and final evidence checks

The private K58 phase-14 package has a **1281/1281 PASS** canonical root regression; K57 additionally has real Cold pilots; the earlier K56 isolated FULL_SERVER realtest remains the completed end-to-end baseline. Those private results are tracked separately from the sanitized public tree to avoid implying that unpublished private tests are part of this repository.

The public repository intentionally excludes production backup data, credentials, personal identifiers, private infrastructure details, machine-specific paths, raw recovery evidence and private archive hashes.
