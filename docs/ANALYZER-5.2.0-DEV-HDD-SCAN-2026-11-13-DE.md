# HP-Server Analyzer 5.2.0-dev – HDD-Vollscan

Stand: 2026-11-13

## Ziel

Der reguläre HP-Server-Analyzer erfasst die externe Level-2-HDD sowohl im automatischen als auch im manuellen Lauf. Offline-Prüfmodi bleiben ohne HDD.

## Umgesetzt

- Manueller systemd-Lauf startet über einen Wrapper mit `--with-backup-hdd --verbose`.
- Manual- und Level-3-Locks verhindern parallele schwere Läufe.
- Den Level-2-Lock erwirbt weiterhin der Analyzer selbst.
- Die HDD wird ausschließlich read-only über bekannte UUID, ext4 und Sentinel akzeptiert.
- Zusätzliche HDD-Rohdaten: findmnt, blkid, SMART, ext4-Superblock, Größenanalyse, Baumansicht und jüngste Backup-Dateien.
- Docker-Inspect-Ausgaben werden vor Speicherung redigiert.
- Secret-Redaction wurde um authorization, bearer, cookie und client_secret erweitert.
- Sieben legitime Funktionsänderungen seit 5.1.0 sowie die neuen Sicherheitsänderungen sind mit aktualisierten Frozen-Function-Hashes gebunden.
- Entwicklungskennung: 5.2.0-dev.

## Installation / Realtest

Installation am 2026-11-13 erfolgreich. Produktiver Analyzer-SHA256 nach der Mount-Korrektur:

`d832f03a6cd9276d2641171d609e3c303d8c359f4dafeb17a671d8fa5f94f5ca`

Der erste manuelle Realtest zeigte zunächst, dass die alte systemd-Härtung des manuellen Services den notwendigen Mount-Namespace blockierte. Die Unit wurde deshalb an den bewährten automatischen Analyzer angeglichen: kein Mount-Namespace-Hardening im manuellen Service; die Datenträgersicherheit verbleibt vollständig im Analyzer selbst.

Nach der Korrektur ist der Realtest erfolgreich in den HDD-Scan gegangen:

- Gerät: `/dev/sdb2`
- UUID: `2a3c5e81-a7bf-471a-a99c-2622e326fb73`
- Dateisystem: ext4
- Mount: `/mnt/backup_hdd`
- Mountoption: `ro`
- Modulzahl mit HDD: 44
- aktuelle HDD-Inventur: `du -xhd 3 /mnt/backup_hdd`

## Fehlerursache vorheriger Läufe

Die technischen Scans liefen durch. Die Phase-9/10-Selbstvalidierung schlug fehl, weil eingefrorene Funktionshashes nach legitimen Änderungen (u. a. Nextcloud→Mealie, Snowflake-Entfernung, HDD-Direktstromlogik) nicht aktualisiert worden waren.

## Sicherheitsvertrag

- keine Schreibprobe auf der Backup-HDD;
- kein rw-Mount durch den Analyzer;
- keine automatischen Cleanup-/Restore-/Update-Aktionen;
- fail-closed bei falscher UUID, falschem Dateisystem oder falschem Sentinel;
- keine parallele Übernahme der HDD durch Level 2.

## Beobachtung / Optimierung

Die rekursive HDD-Inventur über rund 500 GB ist der mit Abstand langsamste Abschnitt. Für eine spätere Optimierung sollte geprüft werden, ob für reguläre Analyzer-Läufe SMART, Dateisystemzustand, Mount-/UUID-Verifikation, Backup-Frische und gezielte Verzeichnisprüfungen genügen, statt jedes Mal den gesamten HDD-Baum per `du` zu durchlaufen.
