# Contributing / Mitwirken

HP Server Recovery handles destructive recovery operations. Changes must therefore preserve fail-closed behavior and remain independent of any maintainer's production infrastructure.

HP Server Recovery führt potenziell destruktive Wiederherstellungsoperationen aus. Änderungen müssen deshalb das Fail-Closed-Verhalten erhalten und von der produktiven Infrastruktur der Maintainer unabhängig bleiben.

## Before opening a pull request / Vor einem Pull Request

1. Do not commit secrets, credentials, private keys, backup contents, database dumps, machine UUIDs, personal domains or production host identities. / Keine Secrets, Zugangsdaten, privaten Schlüssel, Backup-Inhalte, Datenbank-Dumps, Maschinen-UUIDs, persönlichen Domains oder produktiven Host-Identitäten committen.
2. Use synthetic fixtures for tests. / Für Tests ausschließlich synthetische Fixtures verwenden.
3. Keep destructive behavior behind explicit validation and confirmation gates. / Destruktives Verhalten muss durch explizite Validierungs- und Bestätigungsgates geschützt bleiben.
4. Do not replace a failed safety check with a permissive fallback. / Fehlgeschlagene Sicherheitsprüfungen niemals durch permissive Fallbacks ersetzen.
5. Run the full test suite / Vollständige Testsuite ausführen:

```bash
python3 -m unittest tests.test_t01_t35 tests.test_wizard_v028 tests.test_realtest_mode
```

## Pull requests

A pull request should explain / Ein Pull Request sollte erläutern:

- what recovery or safety behavior changes / welches Recovery- oder Sicherheitsverhalten geändert wird
- which failure modes are covered / welche Fehlerfälle abgedeckt werden
- whether persistent state, cleanup or resume semantics change / ob sich persistenter Zustand, Cleanup oder Resume-Semantik ändern
- which tests demonstrate the behavior / welche Tests das Verhalten nachweisen

Security-sensitive changes should include negative tests showing that unsafe input is rejected.

Sicherheitsrelevante Änderungen sollten Negativtests enthalten, die nachweisen, dass unsichere Eingaben abgewiesen werden.

## Test data / Testdaten

All repository fixtures must be synthetic. Values that resemble infrastructure identifiers should use clearly fictional or documentation-safe values.

Alle Repository-Fixtures müssen synthetisch sein. Werte, die Infrastrukturkennungen ähneln, müssen eindeutig fiktive oder dokumentationssichere Werte verwenden.

## Security reports / Sicherheitsmeldungen

Do not open public issues for vulnerabilities that could make a destructive restore bypass safety gates or disclose secrets. Follow the process in [SECURITY.md](SECURITY.md).

Für Schwachstellen, durch die ein destruktiver Restore Sicherheitsgates umgehen oder Secrets offenlegen könnte, keine öffentlichen Issues erstellen. Das Verfahren in [SECURITY.md](SECURITY.md) verwenden.
