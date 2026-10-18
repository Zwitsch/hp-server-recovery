# Recovery- und Immich/Filen-Meilenstein — 2026-10-03

**Sprache / Language:** Deutsch · [English](RECOVERY-IMMICH-MILESTONE-2026-10-03.md)

## Umfang

Dieses Dokument hält den bereinigten privaten Systemmeilenstein für HP Server Recovery und die Immich/Filen-Speicherarchitektur fest. Private Infrastruktur- und Rohdaten bleiben außerhalb des öffentlichen Repositorys.

## Recovery-Stand

Das private K56-Recovery-Paket blieb End-to-End validiert:

- private kanonische Regression-Suite: **1050/1050 PASS**
- fokussierte Fresh-Tree-Gates: **PASS**
- Restore-Scope: **FULL_SERVER**
- Restore-Modus: **COMBINED_L2_L3**
- isolierter FULL_SERVER-Realtest: **COMPLETED**
- Cleanup der isolierten Runtime: **PASS**
- finaler Realtest-Return-Code: **0**
- Read-only-Grenze der Recovery-Quelle: **PASS**
- backupgebundene Release- und Runtime-Image-Identität bleiben fail-closed

Die verbleibenden Endarbeiten waren vor allem Produktisierung und Disaster-Recovery-Paketierung: automatisches Onboarding unbekannter Apps, Recovery-Medium, GUI-Ablauf, echter Bare-Metal-Restore und Restore-from-Cold.

## Immich / Filen

Produktive Architektur:

Filen -> read-only rclone FUSE -> offizielle Immich External Libraries -> Stock Immich

Bereinigter damaliger Stand:

- Immich-Server: **v3.2.1**, healthy
- Machine-Learning-Service: **v3.2.4**, healthy
- vier owner-spezifische External Libraries
- aktive Assets gesamt: **83,227**
- aktive externe Assets: **81,735**
- aktive lokale Assets: **1,492**
- externe Offline-Assets: **0**

## Großer Reclaim und Cold-Archiv

Der Migrations-/Reclaim-Satz war abgeschlossen:

- **81,328** lokale Quelldateien
- logische Größe: **252.66 GiB**
- Local-to-Filen BLAKE3: **81,328/81,328 PASS**
- Local-to-Level-2 BLAKE3: **81,328/81,328 PASS**
- Datenbankprüfung: **PASS**
- besondere Pfadzuordnungen: **21**, alle validiert

Die bereits auf Level 2 vorhandenen validierten Dateien wurden als Same-Filesystem-Hardlinks in ein dediziertes Cold-Archiv außerhalb des normalen Mirror-Baums materialisiert.

- Cold-Archiveinträge: **81,328/81,328 PASS**
- Same-Inode-Nachweis vor Detach: **PASS**
- Mirror-Detach: **81,328/81,328 PASS**
- keine zweite Kopie des 252.66-GiB-Payloads erforderlich

Ein früheres rsync-Filterdesign mit rund 81.000 Einträgen wurde wegen zu hoher betrieblicher Kosten verworfen.

## Lokaler Reclaim

Die Fail-Closed-Transaktion wurde erfolgreich abgeschlossen:

- exakte lokale Allowlist entfernt: **81,328**
- verbleibende lokale Reclaim-Ziele: **0**
- Manifeststatus: **81,328 COLD_ACTIVE**
- erhaltene Sidecars: **949/949**
- Post-Reclaim-Datenbank-Gate: **PASS**
- Immich anschließend healthy
- externe Offline-Anzahl: **0**

Die 1,492 aktiven lokalen Assets lagen außerhalb der Reclaim-Allowlist.

## Periodische Integritätsprüfung

Der monatliche Cold-Archive-Deep-Verifier führt eine vollständige BLAKE3-Prüfung unabhängig vom täglichen Level-2-Backup aus. Der erste automatische Lauf am 2026-10-04 war erfolgreich:

- Cold-Archive-BLAKE3: **81,328/81,328 PASS**
- Service: **SUCCESS / Return Code 0**
- Level-2-Dateisystem anschließend sauber unmounted

Auch der erste normale produktive Level-2-Lauf nach Reclaim war nachgewiesen: Service `rc=0`, Daten- und ioBroker-Mirror **OK**, strukturelle Post-Run-Verifikation **PASS**, normale Mirror-Reclaim-Pfade **0/81,328**, Cold-Archiv **81,328/81,328**.

## Verbleibende Arbeiten dieses Stands

1. Restore-from-Cold gegen ein frisches Ziel testen.
2. Die verbleibenden 1,492 lokalen Immich-Assets klassifizieren.
3. Den früheren kleinen Tiering-Abschnitt in das langfristige Cold-/Recovery-Modell konsolidieren.
4. Recovery-Medium, automatisches Onboarding und Bare-Metal-End-to-End-Validierung abschließen.

## Trennung öffentlich/privat

Nur bereinigte Engineering-Fakten werden hier dokumentiert. Private Betriebsdaten und rohe Recovery-Nachweise bleiben außerhalb dieses Repositorys.
