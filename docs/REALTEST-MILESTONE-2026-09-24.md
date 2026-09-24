# Realtest milestone — 2026-09-24

This document records a sanitized development milestone from the private HP Server Recovery validation environment.

It intentionally excludes production backup data, credentials, hostnames, machine identities, private paths, raw recovery reports, private archive hashes and private release artifacts.

## K56 milestone

The private recovery package has progressed through K56 and completed the development and regression work required for a new focused application full-restore realtest.

Validated before the new focused run:

- final archive identity and fresh-extraction validation: **PASS**
- canonical private regression suite: **PASS**
- retained K24, K25 and K51 regression gates: **PASS**
- wizard and early gates: **PASS**
- dynamic backup-bound CURRENT release resolution: **PASS**
- exact backup/release tuple matching remains fail closed
- application version and image identity must match exactly
- previous-release handling remains separate from CURRENT release resolution
- realtest worker root binding has been corrected so standard realtest roots are no longer rewritten as a test root
- explicit fixture/test roots remain gated by the test-root safety contract
- a worker failure before the first recovery step can no longer be reported as a successful FULL restore
- recovery source read-only enforcement and host Docker isolation remain required

## Dynamic backup-bound CURRENT release binding

The wizard and expert CLI now use the same CURRENT release source-of-truth for isolated realtests.

For a selected backup set, CURRENT application release identity is resolved from the backup-bound release contract associated with that selected recovery set. A stale static CURRENT identity cannot override the selected backup metadata.

The contract remains fail closed:

- exact version match required
- exact image identity match required
- missing or ambiguous backup-bound release artifacts are rejected
- schema/contract errors remain distinct from identity mismatch
- no same-version fallback or silent substitution is allowed

## Wizard worker root hardening

A focused realtest exposed a worker-launch bug before any restore step executed.

The guided wizard incorrectly derived a worker test root from the parent of its state directory. In a real isolated run this caused the worker to enter the explicit test-root gate and stop before the first recovery action.

K56 now uses an explicit state/log root contract:

- standard realtest state and log roots launch the worker without a test-root override
- explicit fixture/test roots must map to one common base and retain the test-root gate
- ambiguous root combinations fail closed
- execute and resume use the same binding rules

The test-only environment gate remains a safety mechanism and is not used as a realtest workaround.

## Report correctness

The focused failure also exposed an inaccurate report fallback: a runtime state that had not completed could inherit planned service outcomes and appear FULL.

K56 now requires an actual completed runtime state before FULL/PARTIAL service outcomes are reported as a successful conclusion. Planned or running states cannot be promoted to a completed restore result.

## Current validation boundary

A fresh focused DeviceWatchdog `APP_FULL` isolated realtest is the next active validation step.

At the time of this documentation update, that focused run is still in progress and is **not** recorded as PASS.

This milestone does **not** claim:

- a successful DeviceWatchdog focused full-app restore after the K56 worker-root fix
- a successful full-server restore
- disaster-recovery certification
- production readiness

## Public/private separation

The public repository remains a sanitized engineering subset. Raw recovery archives, private backup data, credentials, hostnames, private infrastructure paths, machine identities, run identifiers and raw recovery evidence remain outside this repository.
