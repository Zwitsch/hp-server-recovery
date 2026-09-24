# Immich / Filen path-preserving remote archive — Phase 1 milestone — 2026-09-24

## English

This document records a sanitized milestone from a separate private storage-tiering development track associated with HP Server Recovery.

It does not publish production paths, media names, credentials, account identifiers, host topology, raw manifests, private hashes or backup artifacts.

### Phase 1 result

Phase 1 development for a path-preserving Immich/Filen archive contract is complete in the private development environment.

Status:

- Phase 1 development: **COMPLETE**
- isolated Phase 1 regression tests: **PASS**
- productive media deletion: **NOT PERFORMED**
- productive overlay activation: **NOT PERFORMED**
- productive Level-2 backup replacement: **NOT PERFORMED**
- K56 recovery package changed: **NO**
- full-server realtest performed as part of this work: **NO**

A first non-destructive tier batch of roughly 100 GiB is currently being copied to the remote archive. Local source media remain present while that transfer and subsequent verification are incomplete.

### Architecture contract

The target architecture separates three responsibilities:

1. local storage holds active/hot media;
2. the remote archive holds verified cold media while preserving Immich paths;
3. the offline Level-2 backup remains a complete independent copy of the logical Immich library.

The remote archive is not intended to replace the offline Level-2 backup.

A media object may become cold-active only after both its remote copy and its existing Level-2 copy have been independently verified.

### Manifest contract

The private Phase 1 implementation uses a deterministic, versioned manifest with relative-path identity.

Per-file state records include:

- relative path
- size
- modification timestamp
- BLAKE3 identity
- tiering state
- remote verification state
- Level-2 verification state
- Level-2 protection approval
- verification timestamps

Path validation is fail closed for absolute paths, traversal, control characters, symlinks, root escape, duplicate entries and non-deterministic ordering.

### Verification contract

Remote verification is based on exact relative path, size and BLAKE3 identity. Modification time is recorded as supporting metadata but is not trusted as the sole identity.

Level-2 verification independently checks the already existing offline backup copy without requiring access to the remote archive.

### Level-2 protection contract

The existing Level-2 mirror remains a normal delete-capable mirror for unmanaged data.

For explicitly approved cold media, Phase 1 introduces a manifest-driven protection model:

- the receiver-side backup copy is protected from deletion;
- the sender-side cold path is hidden from normal transfer;
- protected cold files are therefore not repeatedly downloaded from the remote archive during Level-2 backup;
- unprotected files in the same directories retain normal mirror behavior;
- missing or mismatched protected backup files fail closed.

The existing shrink guard remains in place and is adjusted conceptually so managed cold data does not create false shrink alarms while unexpected loss outside the managed set remains detectable.

### Private test coverage

The private isolated suite reports **24/24 PASS**, including:

- manifest and path validation
- local and remote identity mismatch handling
- Level-2 verification failures
- protection-approval gates
- literal handling of rsync wildcard characters
- receiver protection with delete-enabled mirroring
- sender hiding without disabling normal sibling-file mirroring
- preservation of protected data when the remote archive is unavailable

These private tests are not part of the sanitized public repository test count.

### Current boundary

No production media may be removed until all of the following gates pass:

1. the current remote copy finishes successfully;
2. the full tier batch is verified locally;
3. the same batch is verified on the remote archive using size and BLAKE3;
4. the existing Level-2 copies are verified using size and BLAKE3;
5. the Level-2 protection integration passes a real dry run against the offline backup disk;
6. a later Phase 2 validates the read-only mount/overlay lifecycle, boot dependencies, Immich lifecycle behavior and rollback.

The system remains deliberately non-destructive at this milestone.

---

## Deutsch

Dieses Dokument hält einen sanitisierten Meilenstein aus einem separaten privaten Storage-Tiering-Entwicklungszweig im Umfeld von HP Server Recovery fest.

Produktive Pfade, Mediennamen, Zugangsdaten, Konto-IDs, Host-Topologie, Roh-Manifeste, private Hashes und Backup-Artefakte werden nicht veröffentlicht.

### Ergebnis Phase 1

Die Phase-1-Entwicklung für einen pfaderhaltenden Immich/Filen-Archivvertrag ist in der privaten Entwicklungsumgebung abgeschlossen.

Status:

- Phase-1-Entwicklung: **ABGESCHLOSSEN**
- isolierte Phase-1-Regressionstests: **PASS**
- produktive Medienlöschung: **NICHT AUSGEFÜHRT**
- produktives Overlay: **NICHT AKTIVIERT**
- produktiver Austausch des Level-2-Backups: **NICHT AUSGEFÜHRT**
- K56-Recovery-Paket verändert: **NEIN**
- Full-Server-Realtest im Rahmen dieser Arbeiten: **NEIN**

Ein erster nicht-destruktiver Tier-Batch von ungefähr 100 GiB wird derzeit in das Remote-Archiv kopiert. Die lokalen Quelldateien bleiben vollständig vorhanden, solange Transfer und anschließende Verifikation nicht abgeschlossen sind.

### Architekturvertrag

Die Zielarchitektur trennt drei Aufgaben:

1. lokaler Speicher hält aktive/heiße Medien;
2. das Remote-Archiv hält verifizierte kalte Medien bei unveränderten Immich-Pfaden;
3. das Offline-Level-2-Backup bleibt eine vollständige unabhängige Kopie der logischen Immich-Mediathek.

Das Remote-Archiv ersetzt das Offline-Level-2-Backup nicht.

Ein Medium darf erst dann cold-active werden, wenn sowohl die Remote-Kopie als auch die bestehende Level-2-Kopie unabhängig verifiziert wurden.

### Manifestvertrag

Die private Phase-1-Implementierung verwendet ein deterministisches, versioniertes Manifest mit relativer Pfadidentität.

Pro Datei werden unter anderem gespeichert:

- relativer Pfad
- Größe
- Änderungszeit
- BLAKE3-Identität
- Tiering-Zustand
- Remote-Verifikationsstatus
- Level-2-Verifikationsstatus
- Level-2-Schutzfreigabe
- Verifikationszeitpunkte

Die Pfadvalidierung arbeitet fail-closed bei absoluten Pfaden, Traversal, Steuerzeichen, Symlinks, Root-Escape, doppelten Einträgen und nicht deterministischer Sortierung.

### Verifikationsvertrag

Die Remote-Verifikation basiert auf exakt übereinstimmendem relativem Pfad, Größe und BLAKE3-Identität. Die Änderungszeit wird als Zusatzmetadatum dokumentiert, aber nicht als alleinige Identität vertraut.

Die Level-2-Verifikation prüft unabhängig die bereits vorhandene Offline-Backup-Kopie und benötigt dafür keinen Zugriff auf das Remote-Archiv.

### Level-2-Schutzvertrag

Der bestehende Level-2-Mirror bleibt für nicht verwaltete Daten ein normaler Mirror mit Löschfunktion.

Für ausdrücklich freigegebene Cold-Medien führt Phase 1 einen manifestgesteuerten Schutzvertrag ein:

- die vorhandene Backup-Kopie auf der Empfängerseite wird vor Löschung geschützt;
- der Cold-Pfad wird auf der Senderseite aus dem normalen Transfer ausgeblendet;
- geschützte Cold-Dateien werden dadurch bei Level-2-Backups nicht wiederholt aus dem Remote-Archiv heruntergeladen;
- ungeschützte Dateien im selben Verzeichnis behalten normales Mirror-Verhalten;
- fehlende oder nicht übereinstimmende geschützte Backup-Dateien führen fail-closed zum Abbruch.

Der bestehende Shrink-Guard bleibt erhalten und wird konzeptionell so angepasst, dass verwaltete Cold-Daten keine falschen Schrumpfalarme erzeugen, während unerwarteter Datenverlust außerhalb des verwalteten Bestands weiterhin erkannt wird.

### Private Testabdeckung

Die private isolierte Suite meldet **24/24 PASS**, unter anderem für:

- Manifest- und Pfadvalidierung
- lokale und Remote-Identitätsabweichungen
- Level-2-Verifikationsfehler
- Schutzfreigabe-Gates
- literale Behandlung von rsync-Wildcardzeichen
- Empfängerschutz bei aktivem Mirror-Delete
- Sender-Hiding ohne Verlust normalen Mirror-Verhaltens benachbarter Dateien
- Erhalt geschützter Daten bei nicht verfügbarem Remote-Archiv

Diese privaten Tests gehören nicht zum Testzähler des sanitisierten öffentlichen Repositories.

### Aktuelle Grenze

Produktive Medien dürfen erst entfernt werden, wenn alle folgenden Gates bestanden sind:

1. die aktuelle Remote-Kopie endet erfolgreich;
2. der vollständige Tier-Batch ist lokal verifiziert;
3. derselbe Batch ist remote anhand von Größe und BLAKE3 verifiziert;
4. die bestehenden Level-2-Kopien sind anhand von Größe und BLAKE3 verifiziert;
5. die Level-2-Schutzintegration besteht einen realen Dry Run gegen die Offline-Backup-HDD;
6. eine spätere Phase 2 validiert Read-only-Mount-/Overlay-Lifecycle, Boot-Abhängigkeiten, Immich-Lifecycle-Verhalten und Rollback.

Dieser Meilenstein bleibt bewusst nicht-destruktiv.
