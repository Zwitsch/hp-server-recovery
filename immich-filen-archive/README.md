# Path-Preserving Remote Archive for Immich / Filen

## English

This project explores a fail-closed architecture for keeping selected Immich source assets remotely while preserving the exact filesystem path expected by Immich.

### Architecture

Remote object storage  
→ read-only rclone FUSE mount  
→ validated BLAKE3 manifest  
→ per-file read-only bind mounts  
→ unchanged Immich original path

The design does not rewrite Immich database paths.

### Delete-safety contract

Immich v3.2.1 has no native synchronous pre-delete hook that covers every permanent delete path. Phase 2.1 therefore integrates a minimal gate at the common permanent delete handler.

For a cold asset the enforced sequence is:

COLD_ACTIVE  
→ verify remote object  
→ verify size and BLAKE3  
→ synchronously rehydrate  
→ verify HOT_LOCAL  
→ allow Immich permanent delete

The operation fails closed before the database asset is removed if the gate is unavailable, times out, the remote object is missing, BLAKE3 differs, rehydration fails, or another delete conflicts.

Covered paths include force/permanent delete, Empty Trash, automatic retention deletion, and internal AssetDelete jobs. Move to Trash and Restore remain non-permanent operations and do not force rehydration.

### Verification status

- Phase 1 regression: 36/36 PASS
- Phase 2 regression after the path-space fix: 44/44 PASS
- Immich v3.2.1 lifecycle A–R: 18/18 PASS
- Delete-safety realtests DS01–DS16: 16/16 PASS
- Full regression after the final fix: 179/179 PASS
- pre-delete gate before database removal: PASS
- finalize after FileDelete semantics: PASS
- fail-closed gate errors and timeouts: PASS
- database consistency: PASS
- tombstone and remote-GC blocking: PASS

### Production mini-pilot 1

A one-asset production mini-pilot has passed.

Verified:

- exactly one intended COLD_ACTIVE asset
- read-only FUSE overlay
- Docker/Immich visibility
- ffprobe
- random seek with identical remote/Immich chunk hash
- unchanged Immich asset identity and original path
- runtime watcher
- delete-gate socket visibility
- managed Immich restart
- complete tiering lifecycle stop/start
- Immich returns healthy after restart
- offline-backup verification/protection remains approved in the manifest
- remote garbage collection remains disabled

No real user asset was permanently deleted as part of the production pilot. Permanent-delete safety remains covered by the isolated DS01–DS16 realtests.

### Path-with-spaces regression

The first production activation safely rolled back after revealing a real-path edge case: raw `findmnt` output escapes spaces in mount targets. The runtime now uses JSON `findmnt` output for exact mount identity checks, and a dedicated regression test covers paths containing spaces.

### Current state

PHASE21_IMPLEMENTATION_COMPLETE = true  
PILOT1_PASS = true  
PRODUCTIVE_COLD_ACTIVE = 1  
PRODUCTIVE_REMOTE_GC = false  
PRODUCTIVE_PERMANENT_DELETE = false

Broader activation should proceed incrementally, with an exact COLD_ACTIVE count and path-identity gate after each batch.

---

## Deutsch

Dieses Projekt entwickelt eine Fail-Closed-Architektur, mit der ausgewählte Immich-Originaldateien remote gespeichert werden können, während der von Immich erwartete Dateipfad unverändert bleibt.

### Architektur

Remote-Speicher  
→ read-only rclone-FUSE  
→ validiertes BLAKE3-Manifest  
→ einzelne read-only File-Bind-Mounts  
→ unveränderter Immich-originalPath

Die Immich-Datenbankpfade werden nicht umgeschrieben.

### Delete-Safety-Vertrag

Immich v3.2.1 besitzt keinen nativen synchronen Pre-Delete-Hook für alle permanenten Löschpfade. Phase 2.1 integriert deshalb einen kleinen Gate-Aufruf am gemeinsamen permanenten Delete-Handler.

Für ein ausgelagertes Asset gilt:

COLD_ACTIVE  
→ Remote prüfen  
→ Größe und BLAKE3 prüfen  
→ synchron rehydrieren  
→ HOT_LOCAL prüfen  
→ erst dann permanentes Immich-Delete zulassen

Bei Gate-Ausfall, Timeout, fehlendem Remote-Objekt, falschem BLAKE3, Rehydrate-Fehler oder konkurrierendem Delete wird vor der Datenbanklöschung fail-closed blockiert.

Abgedeckt sind Force/Permanent Delete, Empty Trash, automatischer Retention Delete und interne AssetDelete-Jobs. Move to Trash und Restore bleiben nicht-permanente Vorgänge.

### Verifizierter Stand

- Phase 1: 36/36 PASS
- Phase 2 nach dem Pfad-Leerzeichen-Fix: 44/44 PASS
- Immich-v3.2.1-Lifecycle A–R: 18/18 PASS
- Delete-Safety-Realtests DS01–DS16: 16/16 PASS
- vollständige Regression nach dem finalen Fix: 179/179 PASS
- Pre-Delete-Gate vor DB-Remove: PASS
- Finalize nach FileDelete-Semantik: PASS
- Fail-Closed bei Gate-Fehlern/Timeouts: PASS
- DB-Konsistenz: PASS
- Tombstone und Remote-GC-Sperre: PASS

### Produktiver Mini-Pilot 1

Ein produktiver Pilot mit genau einem Asset ist bestanden.

Geprüft wurden:

- exakt ein beabsichtigtes COLD_ACTIVE
- read-only FUSE-Overlay
- Docker-/Immich-Sichtbarkeit
- ffprobe
- Random Seek mit identischem Remote-/Immich-Chunk-Hash
- unveränderte Immich-Asset-Identität und unveränderter originalPath
- Runtime-Watcher
- Delete-Gate-Socket
- verwalteter Immich-Restart
- vollständiger Stop/Start des Tiering-Lifecycles
- Immich danach wieder healthy
- L2-Verifikation und L2-Schutz bleiben im Manifest freigegeben
- Remote-GC bleibt deaktiviert

Für den produktiven Pilot wurde kein reales Benutzerasset permanent gelöscht. Die Permanent-Delete-Sicherheit bleibt durch die isolierten DS01–DS16-Realtests abgedeckt.

### Regression bei Pfaden mit Leerzeichen

Der erste produktive Aktivierungsversuch rollte sicher zurück und deckte einen realen Pfad-Fall auf: Raw-`findmnt` escaped Leerzeichen im Mount-Target. Der Runtime-Code verwendet nun die JSON-Ausgabe von `findmnt`; zusätzlich existiert ein Regressionstest für Pfade mit Leerzeichen.

### Aktueller Stand

PHASE21_IMPLEMENTATION_COMPLETE = true  
PILOT1_PASS = true  
PRODUCTIVE_COLD_ACTIVE = 1  
PRODUCTIVE_REMOTE_GC = false  
PRODUCTIVE_PERMANENT_DELETE = false

Eine breitere Aktivierung soll schrittweise erfolgen und nach jedem Batch COLD_ACTIVE-Anzahl und exakte Pfadidentität prüfen.
