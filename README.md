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

## Development milestone — 2026-09-24

The private full recovery package has progressed through K56. The current development state retains the previously validated isolated application restore and database-recovery work while adding two important hardening fixes before the next focused application full-restore realtest:

- dynamic backup-bound CURRENT release resolution is now shared by the wizard and expert CLI
- exact backup/release version and image identity matching remains fail closed
- missing or ambiguous backup-bound release artifacts remain blockers
- previous-release handling remains separate from CURRENT release resolution
- the guided wizard no longer rewrites standard realtest state/log roots into an explicit test root
- explicit fixture/test roots remain protected by the test-root safety gate
- execute and resume share the same worker-root contract
- a worker failure before the first recovery step can no longer be reported as a successful FULL restore
- recovery source read-only enforcement and host Docker isolation remain required
- canonical private regression and retained focused regression gates: **PASS**

The next validation step is a focused DeviceWatchdog `APP_FULL` isolated realtest using the selected backup-bound CURRENT release. At the time of this documentation update that run is still in progress and is **not** recorded as PASS.

This milestone does **not** claim a successful full-server restore, production-ready release or disaster-recovery certification.

The public repository intentionally remains a sanitized subset and does not contain production backup archives, credentials, machine identities, private infrastructure paths, raw recovery evidence, private run identifiers or private archive hashes.

See `docs/REALTEST-MILESTONE-2026-09-24.md` for the sanitized K56 milestone summary.

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
