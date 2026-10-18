# Änderungsprotokoll

**Sprache / Language:** Deutsch · [English](CHANGELOG.md)

Alle wesentlichen Änderungen an HP Server Recovery werden in dieser Datei dokumentiert.

Das Projekt bereitet derzeit seine erste stabile OSS-Veröffentlichung vor.

## Unveröffentlicht

### Hinzugefügt

- Öffentlich bereinigter Quellbaum für die wiederverwendbare Recovery-Engine.
- Synthetischer Runtime-Katalog, Image-Lock-Verträge und App-Release-Fixtures.
- Vorlagen für isolierte Realtest-Konfigurationen mit ausschließlich für Dokumentation vorgesehenen Netzwerkadressen und reservierten Beispieldomains.
- GitHub-Actions-CI auf Ubuntu 24.04 mit Python 3.12.
- Architektur-, Sicherheits- und Beitragsdokumentation.
- Öffentliche Dokumentation des K22-Meilensteins zur Real-Runtime-Validierung vom 2026-09-15; private Recovery-Nachweise und Produktivdaten bleiben außerhalb des Repositorys.
- Öffentlich bereinigte Dokumentation des K25-Read-only-Realtest-Meilensteins vom 2026-09-16 sowie der Prüfungen von Backup-/Release-Identitäten.
- Öffentlich bereinigte Dokumentation des K27-Meilensteins zur isolierten Wiederherstellung von App-Daten vom 2026-09-16.
- Öffentlich bereinigte Dokumentation des K30-Meilensteins zur isolierten vollständigen App-Wiederherstellung vom 2026-09-17.
- Öffentlich bereinigte Dokumentation des Recovery- und Immich/Filen-Migrationsmeilensteins vom 2026-10-03.

### Geändert

- Host- und Protected-Path-Bindungen isolierter Realtests wurden verallgemeinert, damit keine produktiven Identitäten fest codiert sind.
- Repository-Metadaten wurden von der Manifest-Abdeckung des Recovery-Pakets getrennt.
- Git-Checkout-Metadaten wurden aus der Validierung des Recovery-Pakets ausgeschlossen.
- README auf den öffentlichen Pre-Release-Stand aktualisiert und um einen extern reproduzierbaren Testbefehl ergänzt.
- Isolierte Runtime-Validierung gegen containerd 2.2.x und OverlayFS-Verhalten fortgeführt.
- Recovery-Design an Mutationsgrenzen gehärtet: Nach zustandsverändernden Image- oder Snapshot-Operationen muss der Runtime-Zustand erneut inventarisiert werden, statt sich auf einen zuvor berechneten Löschplan zu verlassen.
- Explizites Fail-Closed-Verhalten für unerwartete Snapshot-Lifecycle-Übergänge aus isolierten Roundtrip-Tests ergänzt.
- Privaten K22-Migrations-Lifecycle erweitert, sodass der reale System-Apply-Pfad dasselbe begrenzte Stabilisierungsmodell nach Image-Entfernung wie die isolierte Validierung verwendet.
- Fail-Closed-Behandlung für asynchrones Verschwinden von Snapshots ergänzt, ohne breite Bereinigung, Snapshotter-Fallback oder generische `NOT_FOUND`-Unterdrückung einzuführen.
- App-Backup-Planung gehärtet: Kompatibilität erfordert exakte Übereinstimmung von Version und ausführbarer Image-Identität mit dem ausgewählten Release.
- Explizite Behandlung von `INCOMPATIBLE_RELEASE_IDENTITY` bei nicht passenden App-Backup-/Release-Tupeln ergänzt.
- Data-only-Planung bleibt innerhalb desselben Provenienzvertrags und wird nicht als Ausnahme von der Image-Identität behandelt.
- Same-Version-Image-Fallback, Metadaten-Normalisierung und stiller Release-Austausch verhindert.
- Identität des ausgewählten Releases zwischen Planung und Ausführung vereinheitlicht, einschließlich Previous-Release-Behandlung.
- Full-App-Runtime-Identität für containerd-basierte Docker-Image-Stores gehärtet: verifizierte Archividentität, OCI-Target-/Manifest-Digest, Image-Config-Digest, ausgewählte Release-Identität und zur Laufzeit aufgelöste Identität werden gebunden.
- Fail-Closed-Bereinigung des isolierten Runtime-Stores vor dem abschließenden Secret-Marker-Scan ergänzt; der Marker-Scan selbst bleibt unverändert und verpflichtend.
- Full-App-Dateneigentum an den numerisch deklarierten Runtime-User aus der verifizierten Image-Konfiguration gebunden statt eines privilegierten Container-Workarounds.

### Entwicklungsstand — 2026-09-22

- K22 Read-only-Runtime-Audit: **PASS**.
- K22 isolierter Snapshot-Migrations-Roundtrip: **PASS**.
- Unabhängige Prüfung des K22-Roundtrip-Berichts: **PASS**.
- K22 gebundener System-Migration Apply-/Rollback-/Repeat-Apply-Lifecycle: **PASS**.
- K25 abschließende frische Validierung des privaten Recovery-Pakets: **PASS**.
- K25 isoliertes Runtime-Gate in der dedizierten Recovery-Umgebung: **PASS**.
- K25 Read-only-Klassifizierung des App-Backup-/Release-Tupels: **PASS**.
- K27 isolierter Single-App-`APP_DATA_ONLY`-Restore: **PASS**.
- K30 isolierter Single-App-`APP_FULL`-Restore: **PASS**.
- Wiederhergestellte App-Daten bestanden Integritäts- und app-spezifische Datenbankprüfungen.
- Offline-Image-Provenienz, Runtime-Identitätsbindung, Runtime-Cleanup und abschließende Secret-Marker-Prüfung erfolgreich abgeschlossen.
- Ein Same-Version-Backup mit abweichender ausführbarer Image-Identität wird als `INCOMPATIBLE_RELEASE_IDENTITY` abgewiesen.
- Der Mismatch ist für Data-only-, Full-App- und Full-Server-Planung fail-closed.
- Der fokussierte Nextcloud-Datenbank-Recovery-Workflow wurde in der isolierten Realtest-Umgebung erfolgreich abgeschlossen.
- Der erste Full-Server-Start stoppte fail-closed während der Planung, weil eine veraltete statische App-Release-Bindung den ausgewählten Backup-Metadaten widersprach.
- Der direkte Full-Server-Planungspfad löst App-Releases nun vor der Kompatibilitätsklassifizierung aus ausgewähltem Backup und Snapshot auf und erhält die exakte Prüfung von Version + ausführbarer Image-Identität.
- Ein fokussierter backupgebundener App-Release-Preflight besteht gegen den ausgewählten Recovery-Snapshot, ohne einen Restore auszuführen.
- Full-Server-Real-Restore-Validierung bleibt zu diesem Stand ausstehend; ein vollständiger Server-Restore wurde noch nicht beansprucht.
- Zu diesem Stand wird noch keine Production-Ready- oder Disaster-Recovery-Zertifizierung beansprucht.
- Öffentliche Releases bleiben bewusst bereinigt und schließen produktive Backup-Daten, Zugangsdaten, private Infrastrukturdetails, maschinenspezifische Pfade und rohe Recovery-Nachweise aus.

### Entwicklungsstand — 2026-10-03

- Private K56-Canonical-Regression-Suite: **1050/1050 PASS**.
- Isolierter privater `FULL_SERVER`-Realtest: **COMPLETED**, `COMBINED_L2_L3`, Cleanup **PASS**, Return Code **0**.
- Verbleibender Disaster-Recovery-Endspurt zu diesem Stand: Recovery-Medium/GUI-Integration, automatisches Onboarding unbekannter Apps, Restore-from-Cold-Integration und echter Bare-Metal-End-to-End-Lauf.
- Produktives Immich verwendet Stock-Immich mit offiziellen External Libraries über einen schreibgeschützten Filen/rclone-FUSE-Mount.
- Aktiver Asset-Stand: **83,227 gesamt**, **81,735 extern**, **1,492 lokal**, **0 extern offline**.
- Abschließendes großes Reclaim-Manifest: **81,328 Dateien / 252.66 GiB**.
- Exact-set Local-to-Filen-BLAKE3-Prüfung: **81,328/81,328 PASS**.
- Exact-set Local-to-Level-2-BLAKE3-Prüfung: **81,328/81,328 PASS**.
- Level-2-Cold-Archiv-Materialisierung und Same-Inode-Prüfung: **81,328/81,328 PASS**.
- Level-2-Mirror-Detach: **81,328/81,328 PASS**.
- Abschließender lokaler Reclaim: **PASS**, **0** verbleibende lokale Reclaim-Ziele und **949/949** Sidecars erhalten.
- Datenbankvalidierung nach Reclaim: **PASS**; External-Offline-Anzahl blieb **0**.
- Tägliches Level-2-Backup bleibt unverändert; monatliche vollständige BLAKE3-Prüfung des Cold-Archivs ist aktiviert.
- Der erste geplante automatische Cold-Deep-Verify und der erste normale produktive Level-2-Lauf nach Reclaim waren zu diesem Stand noch offene Betriebsnachweise.

### Entwicklungsstand — 2026-10-04

- Privates K57 manifestgebundenes Immich-Cold-Overlay für L2_ONLY und COMBINED_L2_L3 implementiert.
- Private Canonical- und Fresh-Extraction-Root-Suites jeweils **1092/1092 PASS**.
- Fokussierte K57-Tests: **42/42 PASS**; relevante kombinierte Regression: **113/113 PASS**.
- Beide frischen Archivextraktionen bestanden Payload-/Package-Manifest-Prüfung.
- Reale L2- und COMBINED-Cold-Piloten stellten jeweils **100 produktionsstämmige Dateien / 2,167,636 Bytes** wieder her, mit **100/100 Target-BLAKE3 PASS** und Erhalt bestehender Non-Cold-Sentinels.
- Cold-Inhalte werden nach dem normalen Mirror wiederhergestellt und vor Datenbank-/Service-Operationen geprüft.
- Vollständiger Cold-Restore mit **81,328 Dateien / 252.66 GiB** bleibt auf einem ausreichend großen frischen Ziel ausstehend.
- K57-Cold-Piloten zertifizieren keinen vollständigen neuen FULL_SERVER- oder Bare-Metal-Lauf.
- Erster automatischer Cold-Deep-Verify und normaler Level-2-Backup-Lauf nach Reclaim wurden erfolgreich abgeschlossen und schließen die früher offenen Betriebsnachweise.
- Siehe `docs/K57-COLD-RESTORE-MILESTONE-2026-10-04.md`.

### K58 akzeptierte Checkpoints — 2026-10-04

- Private Phase-2-Root-Canonical-Suite: **1144/1144 PASS**, Return Code **0**.
- Discovery-/Inventory-Fokustests: **52/52 PASS**.
- Separate Production-Backup-Binding-Tests: **18/18 PASS**.
- Produktive Installation, frischer App-Export, Receipt-Verifikation und Veröffentlichung des gebundenen Inventars auf ein lokales Pilotziel: **PASS**.
- L2/L3-Skripte veröffentlichen nun explizit das laufgebundene Inventar; vollständige Backup-Läufe nach Installation waren zu diesem Stand noch offen.
- Automatisches Onboarding, vollständige Runtime-Mount-Abdeckung und neue K58-Full-Server-/Bare-Metal-Abnahme waren zu diesem Stand noch unvollständig.
- Siehe `docs/K58-INVENTORY-BINDING-MILESTONE-2026-10-04.md`.

### Sicherheit

- Destruktive Recovery-Logik bleibt fail-closed, wenn erforderliche Zielidentität oder Sicherheitsbindungen fehlen.
- Öffentliche Fixtures enthalten keine produktiven Zugangsdaten, Backup-Daten, persönlichen Domains, Maschinen-UUIDs oder private LAN-Topologie.
- Breite Bereinigung und Fallback-Verhalten bleiben im validierten Migrations-Lifecycle verboten.
- App-Backup-Provenienz ist an die ausgewählte ausführbare Release-Identität gebunden; identische Versionsstrings allein reichen nicht aus.
- Der abschließende Secret-Marker-Scan bleibt nach isoliertem Runtime-Cleanup verpflichtend.
- Backupgebundene Release-Auswahl bleibt metadatengesteuert; das neueste oder lediglich vorhandene Release-Artefakt wird niemals implizit ausgewählt.
- Der bereinigte öffentliche Release-Baum wird unabhängig getestet; private Realtest-Ergebnisse des Recovery-Pakets werden nicht als Ergebnisse der öffentlichen Suite dargestellt.

## 0.1.0

Als erste stabile öffentliche OSS-Version nach abschließender Release-Readiness-Prüfung geplant. Es wurde noch kein Tag veröffentlicht.
