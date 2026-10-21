# Analyzer discovery integration — 2026-10-21

[Deutsch](ANALYZER-DISCOVERY-INTEGRATION-2026-10-21-DE.md)

## Status

The HP-Server Analyzer was repaired and validated against the current production state before being accepted as a recovery discovery source.

The production Analyzer completed its real run successfully. Its current structured models matched the observed production baseline for containers, failed systemd units, storage mounts, backup scheduling, and relevant service relationships.

## Authority boundary

The integration follows one binding rule:

**Analyzer = discovery/inventory → recovery contracts = authority → manifest/release/certificate gates = approval.**

Analyzer findings are therefore evidence and candidates only. They do not authorize a restore, do not bypass application certification, and do not turn Analyzer recovery-maturity heuristics into recovery authority.

The recovery-side Analyzer profile records `restore_authority: false`. Discovery remains non-mutating and report-only.

## Validation

After the current Analyzer contract was bound into the runtime catalog and the USB manifest was resealed, the authoritative root canonical suite completed:

- canonical tests: **1376 / 1376 PASS**
- canonical status: **PASS**
- runtime catalog binding: **PASS**
- USB manifest verification: **PASS**
- system Docker socket in the recovery environment: **absent**
- isolated Docker/containerd services after validation: **inactive**

A non-root canonical run was intentionally not treated as authoritative because ownership/runtime cleanup safety gates require root. Those safety checks were not weakened.

## Remaining final gate

Analyzer repair and discovery integration are complete. The remaining project-level recovery gate is the genuine fresh-Ubuntu end-to-end restore, reboot, and post-reboot verification. Until that passes, this milestone must not be interpreted as full disaster-recovery completion.
