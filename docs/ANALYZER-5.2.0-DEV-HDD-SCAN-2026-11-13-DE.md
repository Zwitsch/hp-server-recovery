# HP-Server Analyzer 5.2.0-dev – HDD-Vollscan und Health-Scoring

Stand: 2026-11-13

## Ziel

Der reguläre HP-Server-Analyzer erfasst die externe Level-2-HDD sowohl im automatischen als auch im manuellen Lauf. Offline-Prüfmodi bleiben ohne HDD. Zusätzlich wird das Health-Scoring so korrigiert, dass Modellierungs- und Historienartefakte nicht wie reale Betriebsfehler gewertet werden.

## Umgesetzt

- Manueller systemd-Lauf startet über einen Wrapper mit `--with-backup-hdd --verbose`.
- Manual- und Level-3-Locks verhindern parallele schwere Läufe.
- Den Level-2-Lock erwirbt weiterhin der Analyzer selbst.
- Die HDD wird ausschließlich read-only über bekannte UUID, ext4 und Sentinel akzeptiert.
- HDD-Rohdaten: findmnt, blkid, SMART, ext4-Superblock, Kapazität/Inodes und begrenzte Top-Level-Strukturprüfung.
- Der frühere rekursive `du -xhd 3`-Vollscan über rund 500 GB sowie die rekursive Dateisuche entfallen.
- Docker-Inspect-Ausgaben werden vor Speicherung redigiert.
- Secret-Redaction umfasst authorization, bearer, cookie und client_secret.
- Frozen-Function-Hashes sind auf den kontrolliert geprüften 5.2.0-dev-Stand aktualisiert.

## Health-Scoring-Korrektur

Der vollständige Lauf vom 2026-11-13 09:46 zeigte 68,8/100, obwohl technische Validierung und Systemzustand weitgehend sauber waren. Die Ursachen waren überwiegend fachliche Fehlklassifizierungen:

- bewusst entfernte Dienste Nextcloud und Snowflake wurden weiterhin als Sollbestand gewertet;
- ein alter ExecMainStatus wurde trotz `Result=success` als fehlgeschlagene Unit gewertet;
- die dedizierte Datei `backup-hdd-smart.txt` wurde vom SMART-Parser nicht erfasst;
- sieben bekannte produktive Mounts wurden als unbekannte Storage-Risiken bewertet;
- unklassifizierte Units und Resolver-Lücken wurden mehrfach als operative Fehler abgezogen;
- Recovery wurde fast ausschließlich aus dem Dokumentationsflag bewertet;
- recreatable/disposable Daten wurden wie kritische Originaldaten für fehlende L3-Redundanz bestraft.

Der neue Stand:

- filtert Nextcloud und Snowflake aus dem aktuellen Sollmodell;
- unterscheidet bekannte, aber noch nicht vollständig modellierte Mounts von echten unbekannten Mounts;
- wertet `backup-hdd-smart.txt` aus;
- zählt eine inaktive Unit mit `Result=success` nicht wegen eines alten ExecMainStatus als Fehler;
- lässt Modellierungs-Lücken sichtbar, gewichtet sie aber deutlich schwächer als reale Betriebsstörungen;
- kombiniert Recovery-Dokumentation mit technischer Wiederherstellbarkeit;
- behandelt recreatable/disposable Daten entsprechend ihrer tatsächlichen Kritikalität.

Auf Basis des hochgeladenen 09:46-Laufs ergibt die neue Logik rechnerisch ungefähr:

- Docker: 97,5
- Storage: 96,0
- SMART: 100,0
- Backups: 97,4
- Monitoring: 90,8
- Recovery: 73,4
- Updates: 100,0
- Risiken: 86,9
- Gesamt: ca. 93,4/100

Recovery bleibt damit bewusst der schwächste Bereich; das Scoring wird also nicht pauschal angehoben.

## Installation / Realtest

Produktiver Stand vor dieser Scoring-Korrektur:

`d832f03a6cd9276d2641171d609e3c303d8c359f4dafeb17a671d8fa5f94f5ca`

Vorbereiteter Kandidat nach Scoring- und Performance-Korrektur:

`70b3b7b0742f3160af327b44186811749ad1899446f3abe8426cd9674bf98fd1`

Statische Validierung:

- Bash-Syntax: PASS
- 27 eingebettete Python-Blöcke: 0 Syntaxfehler
- 2 Frozen-Hash-Tabellen mit je 57 Funktionen: 0 Abweichungen

## Sicherheitsvertrag

- keine Schreibprobe auf der Backup-HDD;
- kein rw-Mount durch den Analyzer;
- keine automatischen Cleanup-/Restore-/Update-Aktionen;
- fail-closed bei falscher UUID, falschem Dateisystem oder falschem Sentinel;
- keine parallele Übernahme der HDD durch Level 2.
