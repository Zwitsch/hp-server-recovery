# HP Server Recovery

Fail-closed disaster recovery framework for self-hosted Linux servers.

> **Status:** private preparation repository. The public release is being rebuilt from a sanitized codebase. Do not use this repository for production recovery yet.

## Goals

HP Server Recovery is intended to make restoration of a self-hosted Linux server reproducible, testable and conservative by default.

Core design goals:

- fail closed when required recovery inputs are missing or ambiguous
- separate generic recovery logic from host-specific configuration
- validate manifests and release identity before destructive actions
- support dry runs and isolated restore tests
- make recovery steps auditable and repeatable
- keep secrets, production payloads and machine identifiers outside the source repository

## Planned public structure

- `lib/` — reusable recovery engine
- `bin/` — command-line entry points
- `profiles/` — generic service profiles and examples
- `config/` — sanitized templates only
- `tests/` — automated tests and fixtures
- `docs/` — architecture, recovery model and safety documentation
- `tools/` — build and validation helpers

## Security model

The public repository must never contain production secrets, private keys, access tokens, real server payloads, personal hostnames/domains, device UUIDs, backup contents or machine-specific restore identities.

Destructive restore operations must require explicit, validated target identity and should refuse to continue when safety preconditions are not met.

See [SECURITY.md](SECURITY.md).

## Current state

The project originated as a private recovery system for a real self-hosted server. The reusable implementation is currently being separated from production-specific data and rewritten into a publishable form.

The first public release will be published only after a clean-source review, secret scan and isolated recovery test.

## License

MIT — see [LICENSE](LICENSE).
