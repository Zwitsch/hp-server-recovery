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

## Development milestone — 2026-09-16

The private full recovery package has progressed through K25 and completed the current read-only isolated-realtest stage on a dedicated recovery environment:

- archive identity and fresh extraction validation: **PASS**
- full regression/root-gate suite: **PASS**
- isolated container-runtime gate and clean post-state: **PASS**
- read-only application backup/release compatibility planning: **PASS**
- compatible application backup tuples remain planable
- mismatched backup/runtime image identities are classified as `INCOMPATIBLE_RELEASE_IDENTITY`
- mismatched application tuples fail closed for data-only, full-app and full-server planning
- application backup identity requires both version and executable image identity to match the selected release
- no metadata normalization, same-version fallback or silent release substitution is allowed

This milestone validates the K25 read-only planning boundary and real backup/release identity checks. It does **not** claim a successful application restore, full-server restore, production-ready release or disaster-recovery certification.

The public repository intentionally remains a sanitized subset and does not contain production backup archives, credentials, machine identities, private infrastructure paths or raw recovery evidence.

See `docs/REALTEST-MILESTONE-2026-09-16.md` for the sanitized milestone summary.

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
