
## English

This project explores a fail-closed architecture for keeping selected Immich source assets remotely while preserving the exact filesystem path expected by Immich.

### Architecture

Remote object storage
→ read-only rclone FUSE mount
→ validated manifest
→ per-file read-only bind mounts
→ unchanged Immich original path

The design intentionally avoids rewriting Immich database paths.

### Implemented development contracts

- BLAKE3-only identity verification
- deterministic path-preserving manifest
- local + remote + offline-backup verification
- protected offline mirror entries
- read-only rclone mount
- VFS full cache with maximum size and minimum free-space guard
- one-file bind mounts only
- hot neighbors remain local
- fail-closed systemd ordering
- explicit Docker restart-policy gate
- crash-safe activation transaction
- atomic rehydrate
- no automatic remote garbage collection
- privacy-preserving structured logs
- default activation disabled
- pilot hard limit: at most three files

### Current verification

Phase 1 regression tests: 36/36 PASS

Phase 2 isolated tests: 36/36 PASS

Real isolated runtime gates:
- read-only FUSE mount PASS
- random seek PASS
- ffprobe PASS
- Docker visibility PASS
- VFS cache PASS
- remote-loss read failure PASS
- reconnect PASS
- one-file read-only bind mount PASS
- hot-neighbor isolation PASS
- systemd unit verification PASS

### Important blocker

The architecture is NOT pilot-ready yet.

Immich can delete original files when trash is emptied or assets are permanently deleted. A file bind mount is itself a mountpoint, so the project requires a provable pre-delete rehydrate contract for every Immich deletion path before any production pilot can be approved.

For this reason the delivered configuration is fail-closed:

activationMode = disabled
trashDeleteGate = BLOCKED

No production deletion, no production cold activation, and no remote garbage collection are enabled.

### Next development gate

Use an isolated Immich test stack and a disposable asset to validate:
- playback
- original download
- thumbnails/transcoding
- health
- container restart
- Docker restart
- reboot recovery
- remote unavailable at boot/runtime
- trash
- restore from trash
- empty trash
- force delete
- retention delete
- automatic rehydrate before every filesystem unlink

Only after those tests pass may a 1–3 file production pilot be considered.

---

## Deutsch

Dieses Projekt entwickelt eine Fail-Closed-Architektur, mit der ausgewählte Immich-Originaldateien remote gespeichert werden können, während der von Immich erwartete Dateipfad unverändert bleibt.

### Architektur

Remote-Speicher
→ read-only rclone-FUSE
→ validiertes Manifest
→ einzelne read-only File-Bind-Mounts
→ unveränderter Immich-originalPath

Die Immich-Datenbankpfade werden nicht umgeschrieben.

### Implementierter Entwicklungsstand

- BLAKE3-only Identitätsprüfung
- deterministisches path-preserving Manifest
- lokale, Remote- und Offline-Backup-Verifikation
- geschützte Offline-Mirror-Dateien
- read-only rclone-Mount
- VFS Full Cache mit Max-Size und Min-Free-Space
- ausschließlich einzelne File-Bind-Mounts
- lokale HOT-Nachbarn bleiben unverändert
- Fail-Closed-systemd-Reihenfolge
- explizites Docker-Restart-Policy-Gate
- crash-sichere Aktivierungstransaktion
- atomarer Rehydrate-Pfad
- kein automatisches Remote-GC
- datensparsame strukturierte Logs
- Aktivierung standardmäßig gesperrt
- Pilotlimit maximal drei Dateien

### Verifikation

Phase 1: 36/36 PASS

Phase 2 isoliert: 36/36 PASS

Reale isolierte Gates:
- FUSE read-only PASS
- Random Seek PASS
- ffprobe PASS
- Docker-Sichtbarkeit PASS
- VFS Cache PASS
- Remote-Ausfall erzeugt Read-Fail PASS
- Wiederverbindung PASS
- einzelner read-only File-Bind-Mount PASS
- HOT-Nachbar unverändert PASS
- systemd Unit-Verifikation PASS

### Kritischer Blocker

Der Stand ist noch NICHT pilotbereit.

Immich löscht Originaldateien beim endgültigen Löschen bzw. Leeren des Papierkorbs. Ein File-Bind-Mount ist selbst ein Mountpoint. Vor einem produktiven Pilot muss deshalb für jeden Immich-Löschpfad beweisbar sein, dass eine COLD-Datei zwingend vorher rehydriert wird.

Darum lautet der ausgelieferte Fail-Closed-Stand:

activationMode = disabled
trashDeleteGate = BLOCKED

Keine produktive Dateilöschung, kein produktives COLD_ACTIVE und kein automatisches Remote-GC.

### Nächster Entwicklungs-Gate

Ein isolierter Immich-Teststack mit Wegwerf-Testasset muss anschließend real prüfen:
- Wiedergabe
- Originaldownload
- Thumbnail/Transcode
- Health
- Container-Neustart
- Docker-Neustart
- Reboot
- Remote beim Boot/Lauf nicht verfügbar
- Trash
- Restore
- Empty Trash
- Force Delete
- Retention Delete
- automatische Rehydrate-Pflicht vor jedem Dateisystem-Unlink

Erst danach darf ein produktiver Pilot mit 1–3 Dateien bewertet werden.