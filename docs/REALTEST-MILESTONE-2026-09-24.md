# Realtest milestone — 2026-09-24

## English

This document records a sanitized development milestone from the private HP Server Recovery validation environment.

It intentionally excludes production backup data, credentials, hostnames, machine identities, private paths, raw recovery reports, private archive hashes, private run identifiers and private release artifacts.

### K56 milestone

The private recovery package has progressed through K56.

Validated in the current K56 line:

- final archive identity and fresh-extraction validation: **PASS**
- canonical private regression suite: **PASS**
- retained K24, K25 and K51 regression gates: **PASS**
- wizard and early gates: **PASS**
- dynamic backup-bound CURRENT release resolution: **PASS**
- exact backup/release version and image-identity matching remains fail closed
- previous-release handling remains separate from CURRENT release resolution
- wizard worker-root handling has been corrected for standard realtest roots
- execute and resume share the same worker-root contract
- incomplete runtime states cannot be reported as successful FULL restores
- symbolic Compose release bindings are preserved separately from resolved runtime identities
- DeviceWatchdog configuration-format validation now matches the authoritative backup/restore schema
- recovery source read-only enforcement and host Docker isolation remain required

### Focused DeviceWatchdog APP_FULL realtest

A fresh focused isolated DeviceWatchdog `APP_FULL` realtest has now completed successfully.

Sanitized result:

- restore runtime completed
- final report status: **FULL**
- DeviceWatchdog service result: **FULL**
- runtime health verification: **PASS**
- marker verification: **PASS**
- isolated runtime cleanup after completion: **PASS**
- productive Docker isolation remained intact
- recovery source remained read-only

This closes the focused application full-restore gate that was still open in the earlier 2026-09-24 milestone text.

### Current validation boundary

The remaining major recovery gate is a current-K56 `FULL_SERVER` isolated realtest.

That full-server run has **not** been executed under the current final K56 package because the available isolated target storage is insufficient for a meaningful full-server restore test.

Therefore:

- focused DeviceWatchdog `APP_FULL`: **PASS**
- current-K56 `FULL_SERVER`: **NOT YET EXECUTED**
- full-server restore pass: **NOT CLAIMED**
- disaster-recovery certification: **NOT CLAIMED**
- production readiness: **NOT CLAIMED**

The storage-capacity blocker is treated separately from K56 code correctness.

### Related storage-tiering work

A separate private Immich/Filen path-preserving archive track has completed its non-destructive Phase 1 design and isolated regression work.

That work does not change K56 and does not count as a full-server recovery validation. See `docs/IMMICH-FILEN-TIERING-PHASE1-2026-09-24.md`.

### Public/private separation

The public repository remains a sanitized engineering subset. Raw recovery archives, private backup data, credentials, hostnames, private infrastructure paths, machine identities, run identifiers and raw recovery evidence remain outside this repository.

---

## Deutsch

Dieses Dokument hält einen sanitisierten Entwicklungsmeilenstein aus der privaten HP-Server-Recovery-Validierungsumgebung fest.

Produktive Backup-Daten, Zugangsdaten, Hostnamen, Maschinenidentitäten, private Pfade, Rohberichte, private Archiv-Hashes, private Run-IDs und private Release-Artefakte sind bewusst nicht enthalten.

### K56-Meilenstein

Das private Recovery-Paket ist bis K56 fortgeschritten.

Im aktuellen K56-Stand validiert:

- finale Archividentität und Prüfung einer frischen Extraktion: **PASS**
- kanonische private Regression-Suite: **PASS**
- beibehaltene K24-, K25- und K51-Gates: **PASS**
- Wizard- und Early-Gates: **PASS**
- dynamische backup-gebundene CURRENT-Release-Auflösung: **PASS**
- exakter Abgleich von Backup-/Release-Version und Image-Identität bleibt fail-closed
- PREVIOUS-Release-Behandlung bleibt von CURRENT getrennt
- Worker-Root-Behandlung des Wizards ist für Standard-Realtest-Roots korrigiert
- Execute und Resume verwenden denselben Worker-Root-Vertrag
- unvollständige Runtime-Zustände können nicht als erfolgreiche FULL-Restores ausgewiesen werden
- symbolische Compose-Release-Bindungen bleiben getrennt von aufgelösten Runtime-Identitäten erhalten
- die DeviceWatchdog-Formatvalidierung entspricht jetzt dem autoritativen Backup-/Restore-Schema
- Read-only-Recovery-Quelle und Host-Docker-Isolation bleiben verpflichtend

### Fokussierter DeviceWatchdog-APP_FULL-Realtest

Ein neuer fokussierter isolierter DeviceWatchdog-`APP_FULL`-Realtest wurde inzwischen erfolgreich abgeschlossen.

Sanitisiertes Ergebnis:

- Restore-Runtime abgeschlossen
- finaler Reportstatus: **FULL**
- DeviceWatchdog-Serviceergebnis: **FULL**
- Runtime-Health-Verifikation: **PASS**
- Marker-Verifikation: **PASS**
- Cleanup der isolierten Runtime nach Abschluss: **PASS**
- Isolation vom produktiven Docker blieb erhalten
- Recovery-Quelle blieb read-only

Damit ist das fokussierte Full-App-Gate geschlossen, das im früheren Meilensteintext vom 24.09.2026 noch offen war.

### Aktuelle Validierungsgrenze

Das verbleibende große Recovery-Gate ist ein aktueller isolierter K56-`FULL_SERVER`-Realtest.

Dieser Full-Server-Lauf wurde mit dem finalen aktuellen K56-Paket **noch nicht ausgeführt**, weil der verfügbare isolierte Zielspeicher für einen aussagekräftigen vollständigen Restore-Test nicht ausreicht.

Daher gilt:

- fokussierter DeviceWatchdog-`APP_FULL`: **PASS**
- aktueller K56-`FULL_SERVER`: **NOCH NICHT AUSGEFÜHRT**
- Full-Server-Restore-PASS: **NICHT BEANSPRUCHT**
- Disaster-Recovery-Zertifizierung: **NICHT BEANSPRUCHT**
- Produktionsreife: **NICHT BEANSPRUCHT**

Der Kapazitätsblocker wird getrennt von der K56-Codekorrektheit behandelt.

### Zugehörige Storage-Tiering-Arbeiten

Ein separater privater Immich/Filen-Zweig für ein pfaderhaltendes Remote-Archiv hat seine nicht-destruktive Phase-1-Entwicklung und die isolierten Regressionen abgeschlossen.

Diese Arbeiten verändern K56 nicht und gelten nicht als Full-Server-Recovery-Validierung. Siehe `docs/IMMICH-FILEN-TIERING-PHASE1-2026-09-24.md`.

### Trennung öffentlich/privat

Das öffentliche Repository bleibt ein sanitisiertes Engineering-Teilprojekt. Roharchive, private Backup-Daten, Zugangsdaten, Hostnamen, private Infrastrukturpfade, Maschinenidentitäten, Run-IDs und Roh-Evidenz bleiben außerhalb des Repositories.
