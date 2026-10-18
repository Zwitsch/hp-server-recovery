# Architektur

**Sprache / Language:** Deutsch · [English](ARCHITECTURE.md)

HP Server Recovery trennt Recovery-Planung, Validierung und Ausführung von hostspezifischen Daten.

## Kernschichten

1. **Katalog- und Manifest-Schicht** — lädt das Recovery-Paket und prüft die Integritätsbindungen.
2. **Quellenscan** — erkennt geeignete Level-2- und Level-3-Recovery-Quellen, ohne sie zu verändern.
3. **Planner** — erzeugt einen expliziten Recovery-Plan, schätzt den Speicherbedarf und bindet die ausgewählten Quellen und Ziele.
4. **State Manager** — speichert den Laufzustand und erzwingt gültige Zustandsübergänge sowie Wiederaufsetzbarkeit.
5. **Executor** — führt geplante Schritte erst nach Bestätigung aus und protokolliert Abschluss- bzw. Fehlerzustände.
6. **Realtest-Isolation** — validiert isolierte Host-, Geräte-, Pfad- und Container-Runtime-Identitäten vor zielverändernden Operationen.
7. **Reporting und Audit** — schreibt begrenzte Berichte und entfernt oder verwirft sensible Markerdaten.

## Öffentliche und private Daten

Das öffentliche Repository enthält ausschließlich die wiederverwendbare Engine und synthetische Fixtures. Produktive Inventare, Backup-Inhalte, Secrets, Geräteidentitäten und serverspezifische Payloads liegen bewusst außerhalb des Repositorys.

## Recovery-Modi

Der Planner unterstützt kombinierte L2/L3-Wiederherstellung, L2-only, L3-only, aufgeschobenes L3 sowie Base-only-Workflows. Servicespezifisches Verhalten wird als explizite Regel im Plan beschrieben und nicht erst während der Ausführung abgeleitet.

## Designvorgabe

Sicherheitsprüfungen sind nicht nur Hinweise. Kann eine erforderliche Identität oder Bindung nicht hergestellt werden, wird die Operation gestoppt.
