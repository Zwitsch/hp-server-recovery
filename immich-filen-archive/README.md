
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

### Verification status

- Phase 1 regression: 36/36 PASS
- Phase 2 regression: 43/43 PASS
- Immich v3.2.1 lifecycle A–R: 18/18 PASS
- Trash/Delete evidence tests: 9/9 PASS
- Crash recovery: 12/12 PASS
- systemd verification: PASS
- read-only FUSE / seek / ffprobe / Docker visibility / cache / reconnect: PASS
- per-file overlay and hot-neighbor isolation: PASS
- rehydrate-before-delete: PASS

### Confirmed Immich v3.2.1 delete behavior

Real isolated testing proved:

- Move to Trash does not immediately unlink the original.
- Restore from Trash works with COLD_ACTIVE assets.
- Empty Trash, force/permanent delete, and automatic retention deletion can remove the database asset while the filesystem unlink fails with EBUSY on a mounted cold file.
- Immich's deletion job removes the database asset before queuing the file deletion.
- the available AssetDelete event occurs after database removal.
- automatic retention deletion is an internal job path and does not pass through an external HTTP gateway.

A manual rehydrate-before-delete flow works correctly, but Immich v3.2.1 exposes no native blocking pre-delete hook that can enforce it for every internal delete path.

Therefore:

TRASH_DELETE_GATES = FAIL
PILOT_READY = false

The fail-closed delivery remains:

activationMode = disabled
trashDeleteGate = BLOCKED

No production deletion, production cold activation, writable remote remount, or automatic remote GC is enabled.

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

### Verifizierter Entwicklungsstand

- Phase 1: 36/36 PASS
- Phase 2: 43/43 PASS
- Immich-v3.2.1-Lifecycle A–R: 18/18 PASS
- Trash/Delete-Evidenztests: 9/9 PASS
- Crash Recovery: 12/12 PASS
- systemd-Verifikation: PASS
- read-only FUSE / Seek / ffprobe / Docker-Sichtbarkeit / Cache / Reconnect: PASS
- Einzeldatei-Overlay und HOT-Nachbar-Isolation: PASS
- Rehydrate-before-delete: PASS

### Real bestätigte Delete-Semantik

Isolierte v3.2.1-Tests zeigen:

- Move to Trash löscht die Originaldatei nicht sofort.
- Restore aus Trash funktioniert mit COLD_ACTIVE.
- Empty Trash, Force/Permanent Delete und automatischer Retention-Delete können den DB-Datensatz entfernen, obwohl der Filesystem-Unlink am gemounteten Cold-Original mit EBUSY scheitert.
- Immich entfernt beim permanenten Delete zuerst den DB-Datensatz und queued den FileDelete erst danach.
- AssetDelete ist kein blockierender Pre-Delete-Hook.
- Retention läuft als interner Job und umgeht einen externen HTTP-Gateway-Pfad.

Rehydrate-before-delete funktioniert technisch korrekt. Immich v3.2.1 bietet aber keinen nativen blockierenden Hook, der diesen Vertrag für alle internen Deletepfade erzwingt.

Daher:

TRASH_DELETE_GATES = FAIL
PILOT_READY = false

Der ausgelieferte Stand bleibt fail-closed:

activationMode = disabled
trashDeleteGate = BLOCKED

Keine produktive Dateilöschung, kein produktives COLD_ACTIVE, kein writable Remote und kein automatisches Remote-GC.