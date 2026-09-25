# HP Server Recovery

[![Tests](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml/badge.svg)](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml)

Fail-closed disaster recovery framework for self-hosted Linux servers.

> **Status:** public sanitized pre-release. The current codebase is published for review, testing and continued development. Do not use it as a production recovery solution yet.

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

## Development milestone — 2026-09-24

### English

The private full recovery package has progressed through K56.

Current sanitized validation status:

- canonical private regression and retained focused gates: **PASS**
- dynamic backup-bound CURRENT release resolution: **PASS**
- worker-root and report-state hardening: **PASS**
- Compose symbolic/runtime release-binding hardening: **PASS**
- DeviceWatchdog configuration-format contract hardening: **PASS**
- focused isolated DeviceWatchdog `APP_FULL` realtest: **PASS**
- isolated runtime cleanup and read-only source boundary after that run: **PASS**
- current-K56 `FULL_SERVER` realtest: **not yet executed**
- full-server restore, disaster-recovery certification and production readiness: **not claimed**

The remaining full-server gate is currently blocked by insufficient isolated target capacity rather than by a known K56 code failure.

A separate private Immich/Filen path-preserving remote-archive track has completed its corrected non-destructive Phase 1 implementation. The corrected private tiering suite reports **36/36 PASS**, including an explicit BLAKE3-only hashing contract and a small real performance/I/O gate. The first roughly 100 GiB remote tier copy has completed, while local media remain present until local, remote, Level-2 and later lifecycle gates have all passed.

See:

- `docs/REALTEST-MILESTONE-2026-09-24.md`
- `docs/IMMICH-FILEN-TIERING-PHASE1-2026-09-24.md`

The public repository intentionally remains a sanitized subset and does not contain production backup archives, credentials, machine identities, private infrastructure paths, raw recovery evidence, private run identifiers or private archive hashes.

### Deutsch

Das private vollständige Recovery-Paket ist bis K56 fortgeschritten.

Aktueller sanitisierter Validierungsstand:

- kanonische private Regressionen und beibehaltene fokussierte Gates: **PASS**
- dynamische backup-gebundene CURRENT-Release-Auflösung: **PASS**
- Worker-Root- und Report-State-Härtung: **PASS**
- Härtung der symbolischen/Runtime-Compose-Release-Bindung: **PASS**
- Härtung des DeviceWatchdog-Konfigurationsformat-Vertrags: **PASS**
- fokussierter isolierter DeviceWatchdog-`APP_FULL`-Realtest: **PASS**
- Cleanup der isolierten Runtime und Read-only-Quellgrenze nach diesem Lauf: **PASS**
- aktueller K56-`FULL_SERVER`-Realtest: **noch nicht ausgeführt**
- Full-Server-Restore, Disaster-Recovery-Zertifizierung und Produktionsreife: **nicht beansprucht**

Das verbleibende Full-Server-Gate ist derzeit durch unzureichende isolierte Zielkapazität blockiert, nicht durch einen bekannten K56-Codefehler.

Ein separater privater Immich/Filen-Zweig für ein pfaderhaltendes Remote-Archiv hat außerdem seine korrigierte nicht-destruktive Phase-1-Implementierung abgeschlossen. Die korrigierte private Tiering-Suite meldet **36/36 PASS**, einschließlich eines expliziten BLAKE3-only-Hashvertrags und eines kleinen realen Performance-/I/O-Gates. Die erste Remote-Tier-Kopie von ungefähr 100 GiB ist abgeschlossen; lokale Medien bleiben erhalten, bis lokale, Remote-, Level-2- und spätere Lifecycle-Gates vollständig bestanden sind.

Siehe:

- `docs/REALTEST-MILESTONE-2026-09-24.md`
- `docs/IMMICH-FILEN-TIERING-PHASE1-2026-09-24.md`

Das öffentliche Repository bleibt absichtlich ein sanitisiertes Teilprojekt und enthält keine produktiven Backup-Archive, Zugangsdaten, Maschinenidentitäten, privaten Infrastrukturpfade, Roh-Evidenz, privaten Run-IDs oder privaten Archiv-Hashes.

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

The private full recovery package has a broader regression suite and additional real-runtime gates; those results are tracked separately from the sanitized public tree to avoid implying that unpublished private tests are part of this repository.

The publication scan currently reports no personal username, personal domain, private-LAN address, standard UUID, e-mail address, private key or risky archive/database/dump file in the release tree.
