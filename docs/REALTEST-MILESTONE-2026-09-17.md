# Realtest milestone — 2026-09-17

This document records a sanitized development milestone from the private HP Server Recovery validation environment.

It intentionally excludes production backup data, credentials, hostnames, machine identities, private paths, raw recovery reports and private release artifacts.

## K30 milestone

The private recovery package reached K30 and completed controlled isolated application restore validation for the current Urlaubsplaner release.

Validated in the dedicated recovery environment:

- final archive identity and fresh-extraction validation: **PASS**
- retained regression and release gates: **PASS**
- isolated application `APP_DATA_ONLY` restore: **PASS**
- isolated application `APP_FULL` restore: **PASS**
- backup/release tuple classification: **COMPATIBLE**
- offline application image provenance and runtime binding: **PASS**
- application-specific database integrity validation: **PASS**
- container/runtime cleanup and secret-marker verification: **PASS**
- read-only recovery source remained read-only throughout the run
- host Docker remained isolated from the realtest runtime
- the isolated runtime returned to a clean inactive state after completion

## Runtime image identity hardening

K30 retains the exact application release identity contract while supporting containerd-backed Docker image stores where the runtime image target digest can differ from the image config digest.

The validated chain binds:

1. verified image archive
2. OCI target / manifest digest
3. image config digest
4. selected release identity
5. runtime-resolved image identity
6. the image actually used by the isolated application runtime

The implementation does not rely on a tag alone and does not accept ambiguous or unbound runtime identities.

## Full-app runtime cleanup hardening

The isolated full-app path now additionally validates application runtime ownership requirements and removes Recovery-owned isolated runtime residue before the final secret-marker scan.

The final marker scan remains fail closed. It was not weakened or bypassed.

## Scope boundary

This milestone does **not** claim:

- a successful full-server restore
- disaster-recovery certification
- production readiness

A separate application backup/release identity mismatch remains a blocker for broader full-server validation and must be resolved without weakening the exact release-provenance contract.

## Public/private separation

The public repository remains a sanitized engineering subset. Raw recovery archives, private backup data, production credentials, private infrastructure details, machine-specific paths and raw recovery evidence remain outside this repository.
