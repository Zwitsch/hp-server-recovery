# Immich / Filen — Meilenstein offizielle External Libraries — 2026-09-27

**Sprache / Language:** Deutsch · [English](IMMICH-FILEN-EXTERNAL-LIBRARIES-2026-09-27.md)

## Architektur

Das private produktive Immich-System wurde für den migrierten Tier von einer dauerhaften Immich-Code-Patch-Architektur weggeführt.

Die validierte Architektur lautet:

Filen -> read-only rclone FUSE -> offizielle Immich External Libraries -> Stock Immich

Betriebliche Kontrollen:

- exakt vier owner-spezifische External Libraries;
- Stock-Immich-Image;
- Remote-Mount ist schreibgeschützt;
- Immich File Watcher für den Remote-Library-Pfad deaktiviert;
- automatische External-Library-Scans deaktiviert;
- Scans werden ausschließlich über einen systemd Safe-Scan Guard gestartet;
- Level-2-Schutz bleibt verfügbar, auch nachdem die entsprechenden lokalen Tier-1-Originale zurückgewonnen bzw. gelöscht wurden.

## Produktiver Stand

Aktuelle private Produktivvalidierung dieses Meilensteins:

- Immich-Version: **v3.2.2**
- Health: **healthy**
- migrierte externe Assets: **410**
- Sidecars: **11**
- insgesamt zurückgewonnener Dateisatz: **421 Dateien**
- externe Offline-Assets: **0**
- gelöschte externe Assets: **0**
- doppelte externe Originalpfade: **0**
- lokal zurückgewonnener Speicherplatz: **100.03 GiB**

Die Owner-Verteilung bleibt über die vier offiziellen External Libraries erhalten.

Eine direkte Filen-seitige Post-Delete-Prüfung bestätigte nach Entfernung der lokalen Originale die exakte Allowlist mit 421 Dateien und die Byte-Gesamtsumme.

## Level-2-Schutz nach lokalem Reclaim

Der Level-2-Schutzhelfer wurde so geändert, dass eine lokal zurückgewonnene Quelle nicht als Fehler gilt, wenn das Manifest bereits genehmigte und verifizierte Level-2-Nachweise enthält.

Der Missing-Local-Source-Realtest bestand mit allen migrierten Einträgen lokal abwesend und erzeugte denselben geschützten Filter wie der Test vor dem Reclaim.

Der tägliche Backup-Schutz muss deshalb den vollständigen migrierten Tier von ungefähr 100 GiB nicht erneut lesen und hashen. Vollständiges Content-Hashing bleibt für einen separaten periodischen Scrub sinnvoll und nicht für jeden täglichen Backup-Lauf.

## Immich-Update-Validierung

Die Produktivinstanz wurde nach dem Cutover von v3.2.1 auf v3.2.2 aktualisiert.

Die Post-Update-Prüfungen blieben sauber:

- Health blieb healthy;
- Asset-Anzahlen aller vier External Libraries unverändert;
- Offline-Anzahl blieb null;
- Deleted-Anzahl blieb null;
- Anzahl doppelter Originalpfade blieb null;
- Filen FUSE blieb read-only;
- Mount-Service blieb aktiv;
- Safe-Scan-Timer blieb aktiv.

## Scope-Grenze

Dieser Meilenstein bedeutet **nicht**, dass die gesamte Immich-Medienbibliothek bereits auf Filen gespeichert war.

Die Architektur war vollständig und der erste produktive Abschnitt von ungefähr 100 GiB / 410 Assets wurde migriert, verifiziert und lokal zurückgewonnen.

Die nächste Storage-Phase bestand darin, die verbleibenden geeigneten Immich-Medien mit demselben ID-erhaltenden, Owner-erhaltenden und Fail-Closed-Prozess zu migrieren.
