# K22 Real-Runtime-Validierungsmeilenstein — 2026-09-15

**Sprache / Language:** Deutsch · [English](REALTEST-MILESTONE-2026-09-15.md)

Dieses Dokument hält einen bereinigten Entwicklungsmeilenstein von HP Server Recovery fest.

Produktive Backup-Daten, Zugangsdaten, Maschinenidentitäten, private Hostnamen, private Dateisystempfade, Archiv-Hashes und rohe Recovery-Berichte sind bewusst ausgeschlossen.

## Umfang

Das private vollständige Recovery-Paket wurde auf einer dedizierten Recovery-VM mit einer realen containerd-2.2.x-Runtime und explizit gebundenem OverlayFS-Snapshotter validiert.

Die Validierungssequenz umfasste:

1. finale Paketintegritäts- und Fresh-Validation-Gates
2. Root-Level-Regression-Gates
3. kontrollierte Runtime-Installation
4. Read-only-Inspektion des gebundenen containerd-Zustands
5. isolierten Snapshot-Migrations-Roundtrip
6. unabhängige Verifikation des persistenten Roundtrip-Berichts
7. separat autorisierten gebundenen System-Migration-Apply
8. separat autorisierten reportgebundenen Rollback
9. Read-only-Audit des wiederhergestellten Pre-Migration-Zustands
10. zweiten separat autorisierten gebundenen System-Migration-Apply
11. Post-Apply-Verifikation von Runtime- und Sicherheitsgrenzen

## Ergebnis

Die K22-Validierungssequenz wurde erfolgreich abgeschlossen:

- Read-only-Audit: **PASS**
- isolierter Migrations-Roundtrip: **PASS**
- Verifikation des persistenten Roundtrip-Berichts: **PASS**
- erster gebundener System-Migration-Apply: **PASS**
- reportgebundener Rollback: **PASS**
- Post-Rollback-State-Audit: **PASS**
- zweiter gebundener System-Migration-Apply: **PASS**
- `apply -> rollback -> apply`: **PASS**
- System-Docker-Sicherheitsgrenze blieb während der Validierung isoliert
- Rollback-Nachweise blieben nach erfolgreichen Migrationen verfügbar

Der Rollback stellte die erwartete Snapshot-Struktur vor der Migration wieder her, einschließlich erwarteter Snapshot-Anzahl, ChainID-Menge, Parent-Beziehungen und committed kinds. Der zweite Apply reproduzierte denselben begrenzten asynchronen Cleanup-Lebenszyklus wie der erste erfolgreiche Apply.

## Erkenntnis zum Lebenszyklus

Frühere Real-Runtime-Tests zeigten, dass das Entfernen eines Images zurückkehren kann, bevor containerd die asynchrone Bereinigung der zugehörigen Snapshots abgeschlossen hat.

Ein Löschplan auf Basis eines einzigen Inventars kann daher zwischen Beobachtung und Mutation veralten.

K22 begegnet dem mit einem begrenzten Fail-Closed-Vertrag zur Zustandsstabilisierung:

- Snapshot-Zustand nach der Image-Mutation erneut inventarisieren
- Namespace- und Snapshotter-Bindungen explizit halten
- ausschließlich strukturell gültige erwartete Inventarzustände akzeptieren
- transiente Teilzustände nur zulassen, solange sie monoton zu einem erlaubten Endzustand konvergieren
- vor der ersten expliziten Snapshot-Entfernung erneut inventarisieren
- `NOT_FOUND` nicht pauschal ignorieren
- kein generisches Cleanup, Prune-Verhalten oder Snapshotter-Fallback einführen

Bei beiden erfolgreichen realen System-Applies waren die erwarteten Snapshots nach der Image-Entfernung zunächst noch sichtbar und wurden anschließend von containerd asynchron entfernt. K22 erkannte den terminalen leeren Zustand korrekt und führte keine unnötigen expliziten Snapshot-Entfernungen aus.

## Sicherheitsgrenze

Dieser Meilenstein weist den K22-containerd-Migrations- und Rollback-Lebenszyklus in der dedizierten Recovery-Umgebung nach.

Er weist **nicht** nach:

- Production Readiness
- vollständigen Restore eines physischen Servers
- End-to-End-Disaster-Recovery für jeden Service und jede Datenklasse
- stabiles öffentliches Release

Der nächste private Validierungsschritt dieses Entwicklungsstands war der vollständige Server-Restore-Workflow auf der Recovery-VM.

Das öffentliche Repository bleibt ein bereinigter Entwicklungsbaum. Private Recovery-Archive und rohe maschinenspezifische Nachweise werden bewusst nicht veröffentlicht.
