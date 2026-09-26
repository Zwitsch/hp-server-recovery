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

### Verified development contracts

- BLAKE3-only identity verification
- deterministic path-preserving manifest
- local + remote + offline-backup verification
- protected offline mirror entries
- read-only rclone mount
- bounded VFS full cache
- one-file bind mounts only
- HOT neighbors remain local
- fail-closed systemd ordering
- Docker restart-policy gate
- crash-safe activation transaction
- atomic rehydrate
- fail-closed runtime watcher
- explicit shared rclone configuration for FUSE and runtime verification
- no automatic remote garbage collection
- privacy-preserving structured logs
- activation disabled by default
- pilot hard limit: at most three files

### Phase 2.1 delete-safety result

Immich v3.2.1 has no native synchronous pre-delete hook that covers every permanent delete path. Therefore Phase 2.1 uses a minimal integration at the common permanent delete handler.

The enforced contract is:

COLD_ACTIVE
→ verify remote object
→ verify size and BLAKE3
→ synchronously rehydrate
→ verify HOT_LOCAL
→ allow Immich permanent delete

If the gate is unavailable, times out, the remote object is missing, BLAKE3 differs, rehydrate fails, or the request conflicts with another delete, deletion is blocked before the database asset is removed.

The gate covers:

- force/permanent delete
- Empty Trash
- automatic retention deletion
- internal AssetDelete jobs

Move to Trash and Restore remain non-permanent operations and do not force rehydration.

### Verification status

- Phase 1 regression: 36/36 PASS
- Phase 2 regression: 43/43 PASS
- Immich v3.2.1 lifecycle A–R: 18/18 PASS
- Delete-safety realtests DS01–DS16: 16/16 PASS
- Full regression after the final delete-gate changes: 178/178 PASS
- common permanent delete handler: PASS
- pre-delete gate before database removal: PASS
- finalize only after FileDelete semantics: PASS
- force delete gate: PASS
- Empty Trash gate: PASS
- retention delete gate: PASS
- gate failure fail-closed: PASS
- database consistency gate: PASS
- tombstone creation: PASS
- remote garbage collection remains blocked by default: PASS

### Current release gate

PHASE21_IMPLEMENTATION_COMPLETE = true  
TRASH_DELETE_GATES = PASS  
PILOT_READY = true

No production cold activation, production overlay, production file deletion, or automatic remote garbage collection was performed during Phase 2.1.

The next step is a production mini-pilot with one to three already verified assets before any broader activation.

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

### Ergebnis Phase 2.1 Delete-Safety

Immich v3.2.1 besitzt keinen nativen synchronen Pre-Delete-Hook für alle permanenten Löschpfade. Phase 2.1 integriert deshalb einen kleinen Gate-Aufruf am gemeinsamen permanenten Delete-Handler.

Verbindlicher Ablauf:

COLD_ACTIVE
→ Remote prüfen
→ Größe und BLAKE3 prüfen
→ synchron rehydrieren
→ HOT_LOCAL prüfen
→ erst dann permanentes Immich-Delete zulassen

Bei Gate-Ausfall, Timeout, fehlendem Remote-Objekt, falschem BLAKE3, Rehydrate-Fehler oder konkurrierendem Delete wird vor der Datenbanklöschung fail-closed blockiert.

Abgedeckt sind:

- Force/Permanent Delete
- Empty Trash
- automatischer Retention Delete
- interne AssetDelete-Jobs

Move to Trash und Restore bleiben nicht-permanente Vorgänge und erzwingen keine Rehydration.

### Verifizierter Stand

- Phase 1: 36/36 PASS
- Phase 2: 43/43 PASS
- Immich-v3.2.1-Lifecycle A–R: 18/18 PASS
- Delete-Safety-Realtests DS01–DS16: 16/16 PASS
- vollständige Regression nach den finalen Gate-Änderungen: 178/178 PASS
- gemeinsamer permanenter Delete-Handler: PASS
- Pre-Delete-Gate vor DB-Remove: PASS
- Finalize erst nach FileDelete-Semantik: PASS
- Force Delete Gate: PASS
- Empty Trash Gate: PASS
- Retention Delete Gate: PASS
- Gate-Fehler fail-closed: PASS
- DB-Konsistenz-Gate: PASS
- Tombstone-Erzeugung: PASS
- Remote-GC standardmäßig blockiert: PASS

### Aktuelles Freigabe-Gate

PHASE21_IMPLEMENTATION_COMPLETE = true  
TRASH_DELETE_GATES = PASS  
PILOT_READY = true

Während Phase 2.1 wurden kein produktives COLD_ACTIVE, kein produktives Overlay, keine produktive Dateilöschung und kein automatisches Remote-GC aktiviert.

Nächster Schritt ist ein produktiver Mini-Pilot mit ein bis drei bereits verifizierten Assets, bevor eine breitere Aktivierung erfolgt.
