# HP Server Recovery

Fail-closed disaster recovery framework for self-hosted Linux servers.

> **Status:** public sanitized pre-release. The current codebase is published for review, testing and continued development. Do not use it as a production recovery solution yet.

## What it does

HP Server Recovery is designed to make restoration of a self-hosted Linux server reproducible, testable and conservative by default.

Core design goals:

- fail closed when recovery inputs, target identity or safety bindings are missing or ambiguous
- separate generic recovery logic from host-specific configuration
- validate manifests and release identity before destructive operations
- support fixture-driven tests and isolated real-restore testing
- make recovery state, command execution and cleanup auditable
- keep secrets, production payloads and machine identities outside the source repository

## Safety model

The recovery engine treats destructive actions as explicitly gated operations. Isolated realtests require bound target identities, allowed and forbidden hostnames, protected path prefixes, read-only recovery sources and an isolated container runtime. Missing bindings cause the operation to stop instead of falling back to permissive defaults.

Persistent reports and audit data are checked for secret-marker leakage before a run can be considered complete.

See [SECURITY.md](SECURITY.md) and `docs/SAFETY-MODEL.md`.

## Repository structure

- `lib/hp_recovery/` — reusable recovery engine
- `bin/` — command-line entry points
- `config/` — sanitized example configuration
- `tests/` — automated tests and synthetic fixtures
- `runtime-data/` — synthetic catalog data used by the test package
- `manifests/` — integrity manifest for the synthetic package
- `payload/` — synthetic test-only package contracts; no production payloads

## Test status

The sanitized release tree currently passes **183/183 automated tests**, including:

- recovery planner and state-machine tests
- confirmation and storage safety gates
- wizard behavior
- isolated realtest identity binding
- read-only source enforcement
- target/source overlap protection
- Docker Compose isolation
- cleanup and resume behavior
- secret-marker redaction and final evidence checks

The publication scan currently reports no personal username, personal domain, private-LAN address, standard UUID, e-mail address, private key or risky archive/database/dump file in the release tree.

## Quick start

For development and test use only:

```bash
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=lib \
python3 -B -m unittest \
  tests.test_t01_t35 \
  tests.test_wizard_v028 \
  tests.test_realtest_mode -q
```

Expected result:

```text
Ran 183 tests
OK
```

Run the CLI help:

```bash
PYTHONPATH=lib ./bin/hp-recovery menu --help
```

The realtest mode is intentionally not plug-and-play. It requires an explicitly bound isolated environment and validated target/sentinel configuration.

## Development status

The repository is now public, but the project is still preparing its first stable OSS release. Current work focuses on release-readiness, documentation quality, external reproducibility and preserving the fail-closed safety model while removing remaining internal-version terminology.

See [CHANGELOG.md](CHANGELOG.md) for ongoing changes.

## Origin

The project originated from a real self-hosted server recovery system after treating backup creation alone as insufficient. The public version publishes the reusable engine, safety model and synthetic tests — not the original infrastructure, backup contents, secrets or machine identities.

## License

MIT — see [LICENSE](LICENSE).
