# Security Policy / Sicherheitsrichtlinie

## Scope / Geltungsbereich

HP Server Recovery performs disaster-recovery and restore operations that may interact with filesystems, storage devices, service configuration and backup data. Safety checks are therefore part of the product contract, not optional convenience features.

HP Server Recovery führt Disaster-Recovery- und Restore-Operationen aus, die mit Dateisystemen, Datenträgern, Service-Konfigurationen und Backup-Daten interagieren können. Sicherheitsprüfungen sind deshalb Bestandteil des Produktvertrags und keine optionalen Komfortfunktionen.

## Public repository policy / Richtlinie für das öffentliche Repository

Do not commit or publish / Nicht committen oder veröffentlichen:

- passwords, API tokens, private keys or session credentials / Passwörter, API-Tokens, private Schlüssel oder Sitzungs-Zugangsdaten
- real production `.env` files / echte produktive `.env`-Dateien
- backup archives or restored application data / Backup-Archive oder wiederhergestellte Anwendungsdaten
- real hostnames, private domains or personal e-mail addresses / echte Hostnamen, private Domains oder persönliche E-Mail-Adressen
- machine UUIDs, filesystem UUIDs, device serials or other deployment identities / Maschinen-UUIDs, Dateisystem-UUIDs, Geräte-Seriennummern oder andere Deployment-Identitäten
- production database dumps / produktive Datenbank-Dumps
- private container registry credentials / Zugangsdaten privater Container-Registries
- Pushover or other notification credentials / Pushover- oder andere Benachrichtigungs-Zugangsdaten
- production recovery evidence containing identifying data / produktive Recovery-Nachweise mit identifizierenden Daten

Use sanitized examples and placeholders instead. / Stattdessen bereinigte Beispiele und Platzhalter verwenden.

## Destructive operations / Destruktive Operationen

Restore functionality should fail closed. A destructive action must not proceed when the expected target identity, required source data, manifest integrity or explicit authorization cannot be established.

Restore-Funktionen müssen Fail-Closed arbeiten. Eine destruktive Aktion darf nicht fortgesetzt werden, wenn erwartete Zielidentität, erforderliche Quelldaten, Manifest-Integrität oder explizite Autorisierung nicht eindeutig festgestellt werden können.

Generic examples must not embed the identity of the original development server.

Allgemeine Beispiele dürfen keine Identität des ursprünglichen Entwicklungsservers enthalten.

## Reporting a vulnerability / Schwachstelle melden

Please open a GitHub issue for non-sensitive security design concerns. Do not include credentials, private infrastructure details or exploit material containing third-party secrets in a public issue.

Für nicht sensible Fragen zum Sicherheitsdesign kann ein GitHub-Issue eröffnet werden. Öffentliche Issues dürfen keine Zugangsdaten, privaten Infrastrukturdetails oder Exploit-Material mit Secrets Dritter enthalten.

For an accidentally committed secret, revoke or rotate the credential first. Removing it from the current tree alone is not sufficient because Git history may retain it.

Bei versehentlich committeten Secrets zuerst die Zugangsdaten widerrufen oder rotieren. Das bloße Entfernen aus dem aktuellen Dateibaum reicht nicht aus, da die Git-Historie den Wert weiterhin enthalten kann.
