# K58 Phase 25 — Bindung des privaten Captures

**Sprache / Language:** Deutsch · [English](K58-PHASE25-PRIVATE-CAPTURE-BINDING-2026-10-05.md)

Datum: 2026-10-05

Dies ist ein bereinigter Meilensteinbericht. Private Implementierungsdetails, produktive Payloads, maschinenspezifische Pfade, Run-IDs, Archiv-Hashes und Secrets bleiben aus dem öffentlichen Repository ausgeschlossen.

## Akzeptierte private Validierung

- private Phase-25-Capture-Bindung: **PASS**
- gebundene App-Dateien: **335**
- gebundene Runtime-/Image-Rollen: **6**
- vollständige Archiv-Anker-Verifikation: **PASS**
- fokussierte Pilot-Binding-/Redis-Engine-/Transactional-Publication-Regression: **45/45 PASS**
- beibehaltene gemeinsame Phase-24-Capture-Contract-Regression: **42/42 PASS**
- kanonische private Root-Regression: **1293/1293 PASS**

Der private Restore-/Realtest-Pfad verwendet nun den gemeinsamen Capture-Vertrag und validiert gebundene Quellenmetadaten erneut vor zielverändernden Operationen.

## Fail-Closed-Härtung der Veröffentlichung

Die Redis-gebundene Veröffentlichung wurde so gehärtet, dass eine fehlgeschlagene neue Veröffentlichung `CURRENT` nicht stillschweigend weiterschalten kann, während ein älteres Receipt oder ein unvollständiger Payload-Satz bestehen bleibt.

Akzeptierte Negativabdeckung umfasst:

- gemischte Capture-Runs werden abgewiesen
- inkonsistente oder manipulierte Bindungen werden abgewiesen
- eine fehlgeschlagene neue Veröffentlichung erhält das vorherige gültige `CURRENT`
- ein synthetischer Fehler während des Commits stellt den vollständigen vorherigen Veröffentlichungssatz wieder her
- private Capture-Bindungen sind auf isolierten Realtest-Modus begrenzt
- `APP_FULL` bleibt blockiert, solange Datenbank-/Job-Queue-Konsistenz nicht zertifiziert ist

## Abnahmegrenzen

Diese Ergebnisse zertifizieren **nicht** die Konsistenz von App-Datenbank und Job-Queue, das Queue-Consumer-Verhalten, einen vollständigen K58-`FULL_SERVER`-Restore, den Cold-Restore mit 81,328 Dateien oder eine Bare-Metal-Wiederherstellung.

- `APP_DATABASE_JOBQUEUE_CONSISTENCY=NOT_CERTIFIED`
- `RESTORE_ALLOWED=false` für den Capture-Vertrag selbst
- `FULL_81328_COLD_RESTORE_PASS=false`

Das frühere isolierte K56-`FULL_SERVER`-Ergebnis bleibt die abgeschlossene End-to-End-Baseline. K58 Phase 25 ist ein Sicherheits-/Integrations-Checkpoint auf dem Weg zur abschließenden Disaster-Recovery-Abnahme auf einem frischen Ziel und kein Ersatz dafür.
