# Realtest milestone — 2026-09-16

This document records a sanitized development milestone from the private HP Server Recovery validation environment.

It intentionally excludes production backup data, credentials, hostnames, machine identities, private paths, raw recovery reports and private release artifacts.

## K25 milestone

The private recovery package reached the K25 read-only isolated-realtest boundary.

Validated in the dedicated recovery environment:

- final archive identity and fresh extraction checks: **PASS**
- full development/root regression gates: **PASS**
- isolated container-runtime safety gate: **PASS**
- clean runtime post-state after the isolation gate: **PASS**
- read-only application backup/release compatibility classification: **PASS**
- compatible application backup tuples remain planable
- incompatible executable-image provenance is rejected before restore
- full-server planning does not swallow an incompatible mandatory application tuple

## Backup/release identity rule

An application backup is compatible with a selected executable release only when both of these identities match:

1. application version
2. executable image identity

A matching version string by itself is not sufficient.

K25 classifies application backup/release tuples as one of:

- `COMPATIBLE`
- `INVALID_BACKUP`
- `INCOMPATIBLE_RELEASE_IDENTITY`

Only `COMPATIBLE` input may proceed as a planable application backup source.

The same provenance rule applies to data-only planning. Data-only recovery does not bypass executable-image provenance checks.

## Fail-closed behavior

The validated read-only planning path rejects mismatched application identity for:

- application data-only planning
- full application planning
- full-server planning when the application is mandatory

The implementation does not normalize backup metadata to a preferred release, rewrite the selected release to match a backup, fall back to another same-version image, or silently substitute another release.

Previous-release planning is also bound to the explicitly selected previous release identity so planner and executor cannot silently evaluate different releases.

## Scope boundary

This milestone does **not** claim:

- a successful real application restore
- a successful full-server restore
- disaster-recovery certification
- production readiness

The next private validation stage begins with a controlled isolated application restore after explicit approval.

## Public/private separation

The public repository remains a sanitized engineering subset. Raw recovery archives, private backup data, production credentials, private infrastructure details and machine-specific evidence remain outside this repository.
