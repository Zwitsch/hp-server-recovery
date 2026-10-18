# Sicherheitsmodell

**Sprache / Language:** Deutsch · [English](SAFETY-MODEL.md)

HP Server Recovery ist um eine Fail-Closed-Recovery-Grenze herum konzipiert.

## Erforderliche Prinzipien

- Recovery-Ziele müssen explizit identifiziert und validiert werden.
- Recovery-Quellen dürfen sich nicht mit Zielen überschneiden.
- Realtest-Quellmounts müssen schreibgeschützt sein.
- System- und Datenziele müssen getrennt sein.
- Geschützte Pfade müssen explizit gebunden sein.
- Erlaubte und verbotene Hostnamen müssen für isolierte Realtests explizit gebunden sein.
- Der produktive Docker-Socket ist keine zulässige isolierte Runtime.
- Veröffentlichte Container-Ports sind in isolierten Tests ausschließlich an Loopback gebunden.
- Destruktive Schritte erfordern eine exakte Bestätigungsphrase.
- Cleanup-Fehler verhindern, dass ein Lauf als abgeschlossen gemeldet wird.
- Resume darf bereits abgeschlossene destruktive Schritte nicht erneut ausführen.
- Secret-haltige Werte dürfen nicht dauerhaft in Statusdaten, Berichten oder Command-Audit-Daten gespeichert werden.

## Kein permissiver Fallback

Fehlende Zielidentität, fehlende Sentinel-Bindung, geänderte Quellenidentität, unerwartete Compose-Services, veränderliche Image-Referenzen oder unsichere Pfadbeziehungen führen zum Abbruch.

Die Software darf eine fehlgeschlagene Sicherheitsprüfung nicht als Berechtigung interpretieren, mit Standardwerten fortzufahren.

## Synthetische öffentliche Fixtures

Das öffentliche Repository verwendet synthetische Hostnamen, Geräte, Image-Digests und Recovery-Daten. Diese Fixtures dienen dazu, das Sicherheitsverhalten zu validieren, ohne eine reale Installation zu veröffentlichen.

## Produktiver Einsatz

Das aktuelle Repository ist ein Pre-Release-Framework und eine Testreferenz. Produktive Wiederherstellung erfordert eine unabhängig geprüfte, umgebungsspezifische Bindung und Restore-Prozedur.
