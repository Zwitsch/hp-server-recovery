# K57 manifestgebundener Immich-Cold-Restore — 2026-10-04

**Sprache / Language:** Deutsch · [English](K57-COLD-RESTORE-MILESTONE-2026-10-04.md)

## Umfang

Das private Recovery-Paket erweitert den zuvor abgeschlossenen K56-`FULL_SERVER`-Restore um ein manifestgebundenes Cold-Overlay. Diese privaten Validierungsergebnisse sind von der Testsuite des bereinigten öffentlichen Repositorys getrennt.

## Restore-Vertrag

- Zuerst den normalen Level-2-Mirror wiederherstellen.
- Das separate Cold-Archiv erkennen und seine Identität in den unveränderlichen Recovery-Plan binden.
- Nur Manifest-Einträge im Zustand `COLD_ACTIVE` wiederherstellen; `READY_TO_RECLAIM` wird ausgeschlossen.
- Cold-Datenmenge für `L2_ONLY` und `COMBINED_L2_L3` in den Storage-Preflight einbeziehen.
- Vor dem Kopieren Manifest-Schema, eindeutige Identitäten, sichere relative Pfade, Quellenbegrenzung, Dateityp und Größe validieren.
- Ausgewählte Dateien mit einer NUL-begrenzten rsync-Dateiliste ohne `--delete` kopieren.
- Zielstruktur und BLAKE3 mit dem hashgebundenen Offline-`b3sum`-Payload prüfen.
- Cold-Verifikation vor Datenbank-, Compose- und Service-Operationen abschließen.
- Bei Identitäts-, Struktur- oder Inhaltsabweichungen fail-closed stoppen.

Deep-Verify-Receipts sind an den kanonischen Manifest-Digest gebunden. Ein vorhandenes ungültiges Receipt wird abgewiesen; ein fehlendes Receipt umgeht die BLAKE3-Zielprüfung nicht. Ein Latest-Receipt-Symlink ist kein Vertrauensanker.

## Validierung

- Fokussierte K57-Tests: **42/42 PASS**.
- Relevante kombinierte Regression: **113/113 PASS**.
- Private Root-Canonical-Suite: **1092/1092 PASS**, Return Code **0**.
- Fresh-Archive-Extraction-Root-Canonical-Suite: **1092/1092 PASS**, Return Code **0**.
- Zwei unabhängige Manifest-Prüfungen frischer Extraktionen: **PASS**, jeweils **124 Payload-Dateien / 489 Package-Dateien**.
- Abschließende private Archiv-SHA256-Sidecar-Prüfung: **PASS**.
- Realer L2-Cold-Pilot: **100 produktionsstämmige Dateien / 2,167,636 Bytes**, Ziel **BLAKE3 100/100 PASS**.
- Realer COMBINED-Cold-Pilot: **100 produktionsstämmige Dateien / 2,167,636 Bytes**, Ziel **BLAKE3 100/100 PASS**.
- Erhalt bestehender Non-Cold-Sentinels: in beiden Pilot-Restores **PASS**.

Der Pilot verwendet tatsächliche `COLD_ACTIVE`-Dateien aus dem produktiven Cold-Archiv und ist nicht auf synthetische Testdaten beschränkt.

## Abnahmegrenze

**FULL_81328_COLD_RESTORE_PASS=false**

Der vollständige Cold-Restore mit **81,328 Dateien / 252.66 GiB** wurde auf der kapazitätsbegrenzten Recovery-VM nicht ausgeführt. Der COMBINED-Cold-Pilot zertifiziert keinen neuen vollständigen K57-`FULL_SERVER`-End-to-End-Lauf. Das frühere K56-`FULL_SERVER`-Ergebnis bleibt die abgeschlossene Baseline.

Verbleibende Abnahmearbeiten umfassen zu diesem Stand den vollständigen Cold-Restore auf einem ausreichend großen frischen Ziel, Onboarding unbekannter Anwendungen, Recovery-Medium-/GUI-Boot-Integration sowie echte Bare-Metal-End-to-End-Disaster-Recovery.

Produktive Payloads, private Identitäten, rohe Runtime-Nachweise, Archiv-Hashes und Zugangsdaten bleiben außerhalb dieses öffentlichen Repositorys.
