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

## Current private recovery milestone — 2026-10-03

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

The remaining project-endgame work is primarily automatic onboarding of unknown applications, final recovery-medium/GUI integration, restore-from-Cold integration and a real bare-metal end-to-end disaster-recovery run.

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

Die verbleibenden Arbeiten bis zum eigentlichen Disaster-Recovery-Endziel betreffen vor allem Auto-Onboarding unbekannter Apps, das finale Recovery-Medium samt GUI, Restore-from-Cold sowie einen echten Bare-Metal-End-to-End-Lauf.

See:

- `docs/FINAL-RECOVERY-MILESTONE-2026-09-27.md`
- `docs/RECOVERY-IMMICH-MILESTONE-2026-10-03.md`

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

The productive daily Level-2 backup script remains unchanged. The large Cold archive is stored outside the normal mirror tree, so daily backup operation does not require an 81k-entry rsync protection filter or daily full-content hashing.

The first scheduled automatic Cold deep-verify and the first normal productive Level-2 backup after the reclaim remain the next operational proof points.

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

Das produktive tägliche Level-2-Backup-Skript bleibt unverändert. Das große Cold-Archiv liegt außerhalb des normalen Mirror-Baums; dadurch sind weder ein 81k-Rsync-Schutzfilter noch tägliche Vollhashes erforderlich.

Der erste automatische Cold-Deep-Verify und ein normaler produktiver Level-2-Lauf nach dem Reclaim sind die nächsten noch offenen Betriebsnachweise.

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

The private full recovery package has the broader **1050/1050 PASS** regression suite plus the successful isolated FULL_SERVER realtest described above. Those private results are tracked separately from the sanitized public tree to avoid implying that unpublished private tests are part of this repository.

The public repository intentionally excludes production backup data, credentials, personal identifiers, private infrastructure details, machine-specific paths, raw recovery evidence and private archive hashes.
