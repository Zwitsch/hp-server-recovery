# K58 Inventar- und Backup-Run-Bindung — 2026-10-04

**Sprache / Language:** Deutsch · [English](K58-INVENTORY-BINDING-MILESTONE-2026-10-04.md)

K58 ergänzt den privaten Recovery-Arbeitsbaum um konservative App-Erkennung und ein bereinigtes Docker-Inventar. Diese Seite dokumentiert die akzeptierten Checkpoints; sie zertifiziert weder automatisches Onboarding noch einen neuen Full-Server-Restore.

## Akzeptierte Validierung

- Private Phase-1-Root-Canonical-Suite: **1116/1116 PASS**, Return Code **0**.
- Private Phase-2-Root-Canonical-Suite: **1144/1144 PASS**, Return Code **0**.
- Fokussierte Discovery-/Inventory-Tests: **52/52 PASS**.
- Produktiver Read-only-Inventory-Pilot: **PASS**.
- Backup-Run-Binding-Tests: **18/18 PASS** auf dem Produktivhost.
- Produktive Installation, frischer App-Export, Receipt-Verifikation und Inventar-Veröffentlichung auf ein lokales Pilotziel: **PASS**, Return Code **0**.

Die 18 Backup-Integrationstests sind von der privaten Recovery-Suite mit 1144 Tests getrennt. Diese Zahlen beschreiben nicht die bereinigte öffentliche Testsuite.

## Implementiertes Verhalten

Discovery hält unbekannte Anwendungen sichtbar, einschließlich gestoppter Deployments. Metadaten unbekannter Anwendungen und bekannte Projektnamen erteilen keine Restore-Berechtigung.

Das Inventar enthält exakte Container-/Image-Identitäten, Compose-Projekt-/Service-Identitäten, normalisierte Mounts und Host-Binding-Risiken. Environment-Werte, Commands und beliebige Labels werden ausgeschlossen. Die Erfassung verwendet explizit den lokalen Docker-Socket und ausschließlich lesende Inspektionsbefehle.

Ein neuer App-Export erfasst das Inventar vor und nach dem Export und verlangt identische Ergebnisse. Das erfolgreiche Run-Receipt bindet den normalisierten Inventory-Digest und den exakten Digest der Inventory-Datei. Die Verifikation verlangt Übereinstimmung zwischen Current-Receipt und Run-Receipt.

Die installierten Level-2- und Level-3-Skripte veröffentlichen dieses gebundene Inventar explizit an ihren jeweiligen Backup-Zielen. Level 3 benötigt diesen expliziten Schritt, weil ausgewählte Quellen kopiert werden. Frischer Export und lokale Veröffentlichung bestanden; ein vollständiger Level-2- oder Level-3-Backup-Lauf nach Installation war zu diesem Stand noch nicht abgenommen.

## Offene Arbeiten

Ein frischer Produktionsvergleich mit der privaten Restore-Profile-Vorlage identifizierte zusätzliche Runtime-Mounts zur Prüfung, darunter Redis-Datenvolumes und External-Library-Bindungen. Ein passender Compose-Projektname beweist keine vollständige Datenabdeckung. Ein zu einem Zeitpunkt leer beobachteter Mount reicht nicht aus, ihn dauerhaft als entbehrlich einzustufen.

Automatisches Onboarding war zu diesem Stand noch unvollständig. Konsistenter Datenexport, exakte Offline-Release-Identität, Secret-Bindung, isolierte Runtime und Restore-Integritätsverträge bleiben verpflichtend. Gestoppte Deployments wurden nicht automatisch ausgeschlossen oder gelöscht.

Das frühere isolierte K56-Full-Server-Ergebnis bleibt die abgeschlossene Baseline. K58 hat zu diesem Stand noch keinen neuen Full-Server- oder Bare-Metal-Abnahmelauf. Auch der vollständige Cold-Restore mit **81,328 Dateien / 252.66 GiB** bleibt offen.

Rohe Inventare, Container-/Image-IDs, Volume-Pfade, Maschinenidentitäten, Receipts, Logs und private Recovery-Payloads bleiben außerhalb dieses öffentlichen Repositorys.
