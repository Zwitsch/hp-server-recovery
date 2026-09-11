# Architecture

HP Server Recovery separates recovery planning, validation and execution from host-specific data.

## Core layers

1. **Catalog and manifest layer** — loads the recovery package and verifies integrity bindings.
2. **Source scanning** — discovers eligible Level 2 and Level 3 recovery sources without mutating them.
3. **Planner** — produces an explicit recovery plan, estimates storage requirements and binds the selected sources and targets.
4. **State manager** — persists run state and enforces valid state transitions and resumability.
5. **Executor** — runs planned steps only after confirmation and records completion/failure state.
6. **Realtest isolation** — validates isolated host, device, path and container-runtime identity before target-changing operations.
7. **Reporting and audit** — writes bounded reports and redacts or rejects sensitive marker data.

## Public vs. private data

The public repository contains the reusable engine and synthetic fixtures only. Production inventories, backup contents, secrets, device identities and server-specific payloads are intentionally external to the repository.

## Recovery modes

The planner supports combined L2/L3 recovery, L2-only, L3-only, deferred L3 and base-only workflows. Service-specific behavior is expressed as explicit rules in the plan rather than inferred at execution time.

## Design constraint

Safety checks are not advisory. If a required identity or binding cannot be established, the operation stops.
