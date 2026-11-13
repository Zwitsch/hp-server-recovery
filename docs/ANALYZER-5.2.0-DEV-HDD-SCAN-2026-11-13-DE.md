# HP-Server Analyzer 5.2.0-dev – HDD-Vollscan

Stand: 2026-11-13

## Ziel

Der reguläre HP-Server-Analyzer soll die externe Level-2-HDD sowohl im automatischen als auch im manuellen Lauf erfassen. Offline-Prüfmodi bleiben ohne HDD.

## Änderungen

- Manueller systemd-Lauf wird auf einen Wrapper umgestellt, der den Analyzer mit `--with-backup-hdd --verbose` startet.
- Manual- und Level-3-Locks verhindern parallele schwere Läufe.
- Den Level-2-Lock erwirbt weiterhin der Analyzer selbst.
- Die HDD wird ausschließlich read-only über bekannte UUID, ext4 und Sentinel akzeptiert.
- Zusätzliche HDD-Rohdaten: findmnt, blkid, SMART, ext4-Superblock, Größenanalyse, Baumansicht und jüngste Backup-Dateien.
- Docker-Inspect-Ausgaben werden vor Speicherung redigiert.
- Secret-Redaction wurde um authorization, bearer, cookie und client_secret erweitert.
- Sieben legitime Funktionsänderungen seit 5.1.0 sowie die neuen Sicherheitsänderungen werden mit aktualisierten Frozen-Function-Hashes gebunden.
- Entwicklungskennung: 5.2.0-dev.

## Fehlerursache vorheriger Läufe

Die technischen Scans liefen durch. Die Phase-9/10-Selbstvalidierung schlug fehl, weil eingefrorene Funktionshashes nach legitimen Änderungen (u. a. Nextcloud→Mealie, Snowflake-Entfernung, HDD-Direktstromlogik) nicht aktualisiert worden waren.

## Sicherheitsvertrag

- keine Schreibprobe auf der Backup-HDD;
- kein rw-Mount durch den Analyzer;
- keine automatischen Cleanup-/Restore-/Update-Aktionen;
- fail-closed bei falscher UUID, falschem Dateisystem oder falschem Sentinel;
- keine parallele Übernahme der HDD durch Level 2.

## Lokaler Kandidat

Der vollständige Kandidat wird auf hp-server unter `/home/daniel/hp-analyzer-5.2.0-dev/` vorbereitet und erst nach statischer Validierung installiert.
