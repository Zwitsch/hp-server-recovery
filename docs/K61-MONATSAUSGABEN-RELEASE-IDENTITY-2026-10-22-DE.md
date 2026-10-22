# K61 – Monatsausgaben Release-Identität und Backup/Restore-Vertrag

Stand: 2026-10-22

## Ergebnis

Der Monatsausgaben-Recovery-Vertrag wurde auf den produktiven Stand `1.0.0` aktualisiert und auf `hp-server` verifiziert.

### Produktive Identität

- Version: `1.0.0`
- Image-Referenz: `monatsausgaben:1.0.0`
- Image-ID: `sha256:3a20da23aed5bf7352142e18e75c80308dfc9921663120c3aab05cfcdf9c779f`
- Source-Archiv SHA256: `fae2e9b978549f929abf054bbe3ba4cdb84b3978e63d4b92708aa96787130e4a`
- Image-Archiv SHA256: `a17b4ac3aec669bb44f4afbb2f8c7e276abe58684c491b2cf47575ed864a096b`

### Release-Status

- `1.0.0`: `CURRENT`
- `legacy-2026-08-02`: `PREVIOUS`

Die Promotion wurde fail-closed gegen die laufende Runtime-Identität geprüft und mit `MONATSAUSGABEN_RELEASE_PROMOTION=PASS` abgeschlossen.

## Installierte Recovery-Helfer auf hp-server

### app_release.py

- Pfad: `/usr/local/lib/hp-server-recovery/app_release.py`
- Zeilen: `1046`
- SHA256: `c5e064b76279f658b61b27344da5a9bf506cf2e59cefb15815b2b47a51fdf955`
- Syntax: PASS

### app_restore.py

- Pfad: `/usr/local/lib/hp-server-recovery/app_restore.py`
- Zeilen: `310`
- SHA256: `362f466f80a55f9d1e146c8c8799b5d7ca8f452f566385997bb5c495475a9a97`
- Syntax: PASS

Die vorigen Dateien wurden vor Austausch mit Zeitstempel `20261022T152610` gesichert.

## Backup-Gate

Produktiver Testlauf:

- Run: `/mnt/data/app-backups/runs/20261022T133650Z-fadbe5ab1d38`
- `prepare --consumer manual`: RC 0
- `verify-run --max-age 1800`: RC 0
- Ergebnis: `K61_MONATSAUSGABEN_BACKUP_GATE=PASS`

Damit sind aktuelles Tabellen-/Migrationsschema, Runtime-Identität und Backup-Metadaten konsistent.

## Legacy-Kompatibilität

Der historische Restore-Zweig bleibt getrennt vom aktuellen Schema:

- `legacy-2026-08-02` erwartet den historischen Zwei-Tabellen-Vertrag `expenses` + `payments`.
- `1.0.0` verwendet den aktuellen Tabellen-/Migrationsvertrag inklusive Versicherungs-Tabellen.
- Beide Restore-Zweige wurden isoliert getestet.

## Sicherheits-/Betriebsregeln

- Keine Live-WAL-SQLite-DB mit `immutable=1` prüfen.
- Release-Status allein ist kein Identitätsnachweis; Version + Image-Referenz + exakte Image-ID müssen zusammenpassen.
- Vor teuren L2/L3-Läufen zuerst `app_backup.py prepare --consumer manual` und anschließend `verify-run` ausführen.
- Historische Releases nicht löschen; sie bleiben als `PREVIOUS` erhalten.
- Recovery-VM wurde in diesem K61-Schritt nicht verändert, da dort parallel ein anderer Arbeitsstrang aktiv ist.

## Offener nächster Schritt

Nach Abschluss des parallelen Recovery-VM-Arbeitsstrangs muss der K61-Vertrag dort in den Recovery-Code übernommen und im isolierten Realtest gegen Monatsausgaben `1.0.0` geprüft werden.
