# HP Server Recovery

[![Tests](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml/badge.svg)](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml)

Fail-closed disaster recovery framework for self-hosted Linux servers.

> **Status:** public sanitized pre-release. The public tree is intended for review, testing and continued development. The complete private recovery package has now passed its isolated FULL_SERVER end-to-end realtest; the public repository is still only a sanitized subset and is not a drop-in production recovery image.

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

## Final private recovery milestone — 2026-09-27

### English

The private recovery package has completed its final K56 end-to-end validation.

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
- isolated containerd and Docker after completion: **inactive**
- system Docker and Docker socket after completion: **inactive / absent**

The final full-server blocker was resolved by keeping declarative APP_RELEASE binding separate from the validated runtime image identity and Docker image ID, and by applying writable-mount ownership only after both symbolic and runtime bindings are complete and unambiguous.

The current private recovery scope is therefore end-to-end proven. Automatic onboarding of entirely unknown new applications remains a future enhancement and is not part of this completed scope.

See:

- `docs/FINAL-RECOVERY-MILESTONE-2026-09-27.md`

### Deutsch

Das private Recovery-Paket hat seine finale K56-End-to-End-Validierung abgeschlossen.

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
- isoliertes containerd und Docker nach Abschluss: **inactive**
- System-Docker und Docker-Socket nach Abschluss: **inactive / absent**

Der letzte Full-Server-Blocker wurde dadurch behoben, dass die deklarative APP_RELEASE-Bindung getrennt von validierter Runtime-Image-Identität und Docker-Image-ID erhalten bleibt und Writable-Mount-Ownership erst nach vollständiger, eindeutiger symbolischer und realer Bindung angewendet wird.

Der aktuelle private Recovery-Umfang ist damit End-to-End real bewiesen. Die automatische Integration völlig unbekannter neuer Apps bleibt ein späterer Ausbau und gehört nicht zum jetzt abgeschlossenen Umfang.

Siehe:

- `docs/FINAL-RECOVERY-MILESTONE-2026-09-27.md`

## Immich / Filen official External Libraries — 2026-09-27

### English

The private production Immich system now uses the official External Libraries path for the migrated tier:

Filen -> read-only rclone FUSE -> official Immich External Libraries -> stock Immich

Validated production state:

- Immich **v3.2.2**, healthy
- exactly four owner-specific External Libraries
- **410** migrated external assets
- **11** sidecars
- **421** files in the reclaimed allowlist
- **0** offline external assets
- **0** deleted external assets
- **0** duplicate external original paths
- **100.03 GiB** local space reclaimed
- direct Filen-side post-delete verification: **PASS**
- Level-2 protection with all migrated local sources absent: **PASS**
- read-only Filen mount and systemd Safe-Scan Guard: **active**

The entire Immich media library has not yet been moved to Filen. The architecture is complete and the first approximately 100 GiB production tranche has been migrated, verified and locally reclaimed. The remaining suitable media will be migrated in a later storage phase using the same ID-preserving, owner-preserving process.

See:

- `docs/IMMICH-FILEN-EXTERNAL-LIBRARIES-2026-09-27.md`

### Deutsch

Das private produktive Immich-System nutzt für die bereits migrierte Tranche jetzt den offiziellen External-Libraries-Pfad:

Filen -> read-only rclone FUSE -> offizielle Immich External Libraries -> Stock-Immich

Bewiesener Produktivstand:

- Immich **v3.2.2**, healthy
- genau vier benutzerspezifische External Libraries
- **410** migrierte External Assets
- **11** Sidecars
- **421** Dateien in der lokal freigegebenen Allowlist
- **0** Offline-Assets
- **0** Deleted-Assets
- **0** doppelte External-Originalpfade
- **100,03 GiB** lokaler Speicher freigegeben
- direkter Filen-Post-Delete-Nachweis: **PASS**
- Level-2-Schutz bei vollständig fehlenden lokalen Quellen: **PASS**
- read-only Filen-Mount und systemd Safe-Scan Guard: **active**

Die gesamte Immich-Mediathek liegt noch nicht auf Filen. Die Architektur ist vollständig und die erste produktive Tranche von ungefähr 100 GiB wurde migriert, verifiziert und lokal freigegeben. Der verbleibende geeignete Medienbestand wird in einer späteren Speicherphase nach demselben ID- und Owner-erhaltenden Verfahren migriert.

Siehe:

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

The publication scan currently reports no personal username, personal domain, private-LAN address, standard UUID, e-mail address, private key or risky archive/database/dump file in the release tree.
