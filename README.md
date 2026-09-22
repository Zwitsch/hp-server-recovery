# HP Server Recovery

[![Tests](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml/badge.svg)](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml)

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

## Development milestone — 2026-09-22

The private full recovery package has progressed through K51. Controlled isolated application restores and a focused database recovery workflow have completed successfully, and backup-bound application release selection has now been validated before the next full-server realtest:

- final archive identity and fresh-extraction validation: **PASS**
- retained regression and release gates: **PASS**
- isolated application `APP_DATA_ONLY` restore: **PASS**
- isolated application `APP_FULL` restore: **PASS**
- backup/release tuple classification: **COMPATIBLE**
- offline image provenance and runtime binding: **PASS**
- application-specific database integrity validation: **PASS**
- runtime cleanup and final secret-marker verification: **PASS**
- focused Nextcloud database recovery workflow: **PASS**
- backup-bound application release preflight for the selected snapshot: **PASS**
- full-server planning rejects stale static release identity and resolves the required application release from backup metadata
- recovery source remained read-only throughout the run
- host Docker remained isolated from the realtest runtime
- mismatched backup/runtime image identities remain classified as `INCOMPATIBLE_RELEASE_IDENTITY`
- no metadata normalization, same-version fallback or silent release substitution is allowed

This milestone validates a real isolated application data restore and full application restore. It does **not** claim a successful full-server restore, production-ready release or disaster-recovery certification.

The previously observed application backup/release mismatch was traced to a stale static binding in the direct full-server planning path. The corrected planning path retains fail-closed exact release-provenance checks and has passed the focused release preflight. Full-server real restore validation is still pending.

The public repository intentionally remains a sanitized subset and does not contain production backup archives, credentials, machine identities, private infrastructure paths or raw recovery evidence.

See `docs/REALTEST-MILESTONE-2026-09-17.md` for the sanitized milestone summary.

## Repository structure

- `lib/hp_recovery/` — reusable recovery engine
- `bin/` — command-line entry points
- `config/` — sanitized example configuration
- `tests/` — automated tests and synthetic fixtures
- `runtime-data/` — synthetic catalog data used by the test package
- `manifests/` — integrity manifest for the synthetic package
- `payload/` — synthetic test-only package contracts; no production payloads

## Test status

The sanitized public release tree currently passes **183/183 automated tests**, including:

- recovery planner and state-machine tests
- confirmation and storage safety gates
- wizard behavior
- isolated realtest identity binding
- read-only source enforcement
- target/source overlap protection
- Docker Compose isolation
- cleanup and resume behavior
- secret-marker redaction and final evidence checks

The private full recovery package has a broader regression suite and additional real-runtime gates; those results are tracked separately from the sanitized public tree to avoid implying that unpublished private tests are part of this repository.

The publication scan currently reports no personal username, personal domain, private-LAN address, standard UUID, e-mail address, private key or risky archive/database/dump file in the release tree.
