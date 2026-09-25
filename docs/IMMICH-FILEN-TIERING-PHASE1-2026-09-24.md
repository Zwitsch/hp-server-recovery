# Immich / Filen path-preserving remote archive — Phase 1 milestone — 2026-09-25

## English

This document records a sanitized milestone from a separate private storage-tiering development track associated with HP Server Recovery.

It intentionally excludes production paths, media names, credentials, account identifiers, host topology, raw manifests, private hashes and backup artifacts.

### Phase 1 corrected result

Phase 1 has completed its first corrective iteration after a real verification run exposed an overly broad local hash path.

Status:

- Phase 1 corrected implementation: **COMPLETE**
- isolated regression tests: **36/36 PASS**
- small real BLAKE3-only performance/I/O gate: **PASS**
- first non-destructive remote tier copy: **COMPLETE**
- productive media deletion: **NOT PERFORMED**
- productive overlay activation: **NOT PERFORMED**
- productive Level-2 protection integration: **INSTALLED; REAL DRY RUN PASS**
- K56 recovery package changed: **NO**
- full-server realtest performed as part of this work: **NO**

The first non-destructive tier batch contains roughly 100 GiB of media. The remote copy completed successfully while all local source media remained present.

### BLAKE3-only correction

The initial implementation used a generic rclone metadata listing with hash collection. On a local backend that advertises many hash algorithms, that path could request more hashing work than the tiering contract actually needs.

The corrected contract separates content identity from metadata:

- content identity: explicit **BLAKE3 only**
- remote/local metadata: collected separately without hash expansion
- remote verification does not force a download when the backend can provide BLAKE3 directly
- no fallback to a broader multi-hash path

The private implementation now executes an explicit BLAKE3 batch operation and validates its exact argument contract.

### Parser and fail-closed behavior

The corrected hash parser requires:

- exactly one expected path result
- exactly one 64-character lowercase hexadecimal BLAKE3 digest per expected path
- lossless preservation of full relative paths, including spaces and literal wildcard characters
- no missing, duplicate or unexpected results
- no silent canonicalization of invalid uppercase digests
- no partial manifest on batch failure

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

The corrected private isolated suite reports **36/36 PASS**.

Coverage includes the previous Phase 1 manifest/path/L2 protection tests plus dedicated regression checks that:

- local, remote and Level-2 content hashing request only BLAKE3;
- no productive content-hash path uses the broader metadata hash expansion;
- remote verification does not force content download;
- spaces and literal wildcard characters survive path parsing;
- BLAKE3 mismatch, missing hashes, duplicate paths and unexpected paths fail closed;
- batch failure cannot leave a partial manifest.

A small real local performance/I/O gate also passed and confirmed that only selected files were read and that the manifest BLAKE3 matched a direct reference BLAKE3 command.

These private tests are not part of the sanitized public repository test count.

### Real Tier-1 and Level-2 validation

The first roughly 100 GiB tier batch has now passed all Phase 1 identity and Level-2 protection gates:

- local BLAKE3 verification: **410/410 PASS**
- remote BLAKE3 verification: **410/410 PASS**
- offline Level-2 BLAKE3 verification: **410/410 PASS**
- READY_TO_TIER state: **410/410**
- Level-2 protection approval: **410/410**
- real Level-2 dry run with the production protection integration: **PASS**
- managed shrink difference: **0.00 GiB**
- protected cold-path matches in the dry-run transfer/delete log: **0**
- Level-2 dry-run final result: **rc=0**
- backup disk unmounted and powered off after completion

The dry run still reported ordinary non-cold mirror changes, which is expected; the protected cold set did not appear as transfer or delete candidates.

### Current boundary

Phase 1 is now complete through real Level-2 dry-run validation. Production media are still not removed and no productive overlay is active.

The next work belongs to Phase 2 and must validate the read-only remote mount/overlay lifecycle, boot dependencies, Immich lifecycle behavior, fail-closed startup, rollback/rehydration and a small controlled productive pilot before any large local payload deletion.

---

## Deutsch

Dieses Dokument hält einen sanitisierten Meilenstein aus einem separaten privaten Storage-Tiering-Entwicklungszweig im Umfeld von HP Server Recovery fest.

Produktive Pfade, Mediennamen, Zugangsdaten, Konto-IDs, Host-Topologie, Roh-Manifeste, private Hashes und Backup-Artefakte werden bewusst nicht veröffentlicht.

### Korrigiertes Ergebnis Phase 1

Phase 1 hat die erste Korrekturrunde abgeschlossen, nachdem ein realer Verifikationslauf einen zu breiten lokalen Hashpfad offengelegt hatte.

Status:

- korrigierte Phase-1-Implementierung: **ABGESCHLOSSEN**
- isolierte Regressionstests: **36/36 PASS**
- kleiner realer BLAKE3-only Performance-/I/O-Gate: **PASS**
- erste nicht-destruktive Remote-Tier-Kopie: **ABGESCHLOSSEN**
- produktive Medienlöschung: **NICHT AUSGEFÜHRT**
- produktives Overlay: **NICHT AKTIVIERT**
- produktive Level-2-Schutzintegration: **INSTALLIERT; REALER DRY RUN PASS**
- K56-Recovery-Paket verändert: **NEIN**
- Full-Server-Realtest im Rahmen dieser Arbeiten: **NEIN**

Der erste nicht-destruktive Tier-Batch umfasst ungefähr 100 GiB Medien. Die Remote-Kopie wurde erfolgreich abgeschlossen, während alle lokalen Quelldateien erhalten blieben.

### BLAKE3-only-Korrektur

Die ursprüngliche Implementierung verwendete eine generische rclone-Metadatenauflistung mit Hash-Erhebung. Auf einem lokalen Backend mit vielen angebotenen Hashalgorithmen konnte dieser Pfad deutlich mehr Hasharbeit auslösen als der Tiering-Vertrag tatsächlich benötigt.

Der korrigierte Vertrag trennt Inhaltsidentität und Metadaten:

- Inhaltsidentität: ausdrücklich **nur BLAKE3**
- lokale/Remote-Metadaten: separat ohne Hash-Expansion
- Remote-Verifikation erzwingt keinen Download, wenn das Backend BLAKE3 direkt bereitstellt
- kein Fallback auf einen breiteren Multi-Hash-Pfad

Die private Implementierung führt jetzt eine explizite BLAKE3-Batchoperation aus und regressionsprüft deren Argumentvertrag.

### Parser und Fail-Closed-Verhalten

Der korrigierte Hashparser verlangt:

- genau ein erwartetes Ergebnis pro Pfad
- genau einen 64 Zeichen langen lowercase-hexadezimalen BLAKE3-Digest je erwartetem Pfad
- verlustfreie Erhaltung des vollständigen relativen Pfades einschließlich Leerzeichen und literaler Wildcardzeichen
- keine fehlenden, doppelten oder unerwarteten Ergebnisse
- keine stille Kanonisierung ungültiger Uppercase-Digests
- kein partielles Manifest bei Batchfehler

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

Die korrigierte private isolierte Suite meldet **36/36 PASS**.

Die Abdeckung enthält die bisherigen Phase-1-Tests für Manifest/Pfade/L2-Schutz sowie eigene Regressionen dafür, dass:

- lokale, Remote- und Level-2-Inhaltshashes ausschließlich BLAKE3 anfordern;
- kein produktiver Inhaltshashpfad die breite Metadaten-Hash-Expansion verwendet;
- die Remote-Verifikation keinen Inhaltsdownload erzwingt;
- Leerzeichen und literale Wildcardzeichen beim Pfadparsing erhalten bleiben;
- BLAKE3-Mismatch, fehlende Hashes, doppelte Pfade und unerwartete Pfade fail-closed scheitern;
- ein Batchfehler kein partielles Manifest hinterlassen kann.

Zusätzlich bestand ein kleiner realer lokaler Performance-/I/O-Gate und bestätigte, dass nur ausgewählte Dateien gelesen wurden und der Manifest-BLAKE3 exakt mit einem direkten BLAKE3-Referenzlauf übereinstimmt.

Diese privaten Tests gehören nicht zum Testzähler des sanitisierten öffentlichen Repositories.

### Reale Tier-1- und Level-2-Validierung

Der erste Tier-Batch von ungefähr 100 GiB hat jetzt alle Phase-1-Identitäts- und Level-2-Schutzgates bestanden:

- lokale BLAKE3-Verifikation: **410/410 PASS**
- Remote-BLAKE3-Verifikation: **410/410 PASS**
- Offline-Level-2-BLAKE3-Verifikation: **410/410 PASS**
- READY_TO_TIER-Zustand: **410/410**
- Level-2-Schutzfreigabe: **410/410**
- realer Level-2-Dryrun mit der produktiven Schutzintegration: **PASS**
- verwaltete Shrink-Differenz: **0,00 GiB**
- geschützte Cold-Pfad-Treffer im Transfer-/Delete-Log des Dryruns: **0**
- finales Level-2-Dryrun-Ergebnis: **rc=0**
- Backup-HDD nach Abschluss unmountet und ausgeschaltet

Der Dryrun meldete weiterhin normale Änderungen außerhalb des geschützten Cold-Bestands, was erwartet ist; der geschützte Cold-Bestand erschien weder als Transfer- noch als Delete-Kandidat.

### Aktuelle Grenze

Phase 1 ist damit bis einschließlich realer Level-2-Dryrun-Validierung abgeschlossen. Produktive Medien werden weiterhin nicht entfernt und es ist kein produktives Overlay aktiv.

Die nächsten Arbeiten gehören zu Phase 2 und müssen Read-only-Remote-Mount-/Overlay-Lifecycle, Boot-Abhängigkeiten, Immich-Lifecycle-Verhalten, fail-closed Startup, Rollback/Rehydration sowie einen kleinen kontrollierten produktiven Pilot validieren, bevor größere lokale Payload-Mengen gelöscht werden.
