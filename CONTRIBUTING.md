# Contributing

HP Server Recovery handles destructive recovery operations. Changes must therefore preserve fail-closed behavior and remain independent of any maintainer's production infrastructure.

## Before opening a pull request

1. Do not commit secrets, credentials, private keys, backup contents, database dumps, machine UUIDs, personal domains or production host identities.
2. Use synthetic fixtures for tests.
3. Keep destructive behavior behind explicit validation and confirmation gates.
4. Do not replace a failed safety check with a permissive fallback.
5. Run the full test suite:

```bash
python3 -m unittest tests.test_t01_t35 tests.test_wizard_v028 tests.test_realtest_mode
```

## Pull requests

A pull request should explain:

- what recovery or safety behavior changes
- which failure modes are covered
- whether persistent state, cleanup or resume semantics change
- which tests demonstrate the behavior

Security-sensitive changes should include negative tests showing that unsafe input is rejected.

## Test data

All repository fixtures must be synthetic. Values that resemble infrastructure identifiers should use clearly fictional or documentation-safe values.

## Security reports

Do not open public issues for vulnerabilities that could make a destructive restore bypass safety gates or disclose secrets. Follow the process in [SECURITY.md](SECURITY.md).
