# K58 phases 27–28 — certified capture and worker-start certification

Date: 2026-10-08

This document records a **sanitized private validation milestone**. Production payloads, host-specific paths, addresses, run identifiers, container identifiers, secrets and private hashes are intentionally excluded.

## Phase 27 — certified quiescent capture

The private recovery package completed a production writer-hold capture for the application database/job-queue consistency contract.

Sanitized result:

- capture consistency: **CERTIFIED_QUIESCENT_CAPTURE**
- application writer hold and service resumption: **PASS**
- live and exported queue gates: **PASS**
- runnable jobs after capture gate: **0**
- missing queue/job linkage: **0**
- orphan queue/job linkage: **0**
- unclassified queue entries: **0**
- captured database, Redis and required limited application-file inputs: **hashed and bound**
- worker start remained fail-closed after capture: **not yet certified at phase 27**

The original capture evidence is immutable input for the later worker-start certification.

## Phase 28 — isolated worker-start certification

The private package restored the phase-27 capture into the isolated recovery runtime and certified bounded worker startup without access to the productive container engine.

Final sanitized gates:

- capture binding: **PASS**
- read-only source / isolation gate: **PASS**
- exact offline runtime image binding: **PASS**
- PostgreSQL restore: **PASS**
- pre-worker queue profile: **PASS**
- Immich worker start, microservices scope only: **PASS**
- Paperless Celery worker start, worker-only scope: **PASS**
- Paperless Beat: **disabled**
- Paperless document consumer: **disabled**
- bounded 60-second worker observation: **PASS**
- post-worker queue profile: **PASS**
- PostgreSQL schema integrity: **UNCHANGED**
- PostgreSQL health check: **PASS**
- Paperless SQLite integrity and foreign keys: **PASS**
- Paperless SQLite content: **UNCHANGED**
- isolated runtime cleanup: **PASS**
- final worker-start certification: **PASS**

`WORKER_START_CERTIFIED=true`

## Important engineering findings

### Docker Engine 29 / containerd image store

On the tested recovery runtime, the Docker image ID exposed by the containerd image store represents the OCI target/manifest digest rather than the image-config digest used by the classic Docker image store. The final binding therefore validates the chain:

`bound tag -> runtime OCI manifest digest -> manifest blob -> config.digest -> capture-bound config digest`

This prevents a false mismatch while retaining strict identity checking.

### PostgreSQL schema comparison

Raw `pg_dump --schema-only` output is not byte-stable because PostgreSQL may emit randomly generated `\restrict` / `\unrestrict` psql meta-command tokens. The final comparison normalizes **only** those non-semantic lines before hashing; real DDL differences remain fail-closed. A negative test verifies that an actual DDL change is still detected.

## Cleanup result

After successful certification:

- isolated Docker service: **inactive**
- isolated containerd service: **inactive**
- isolated Docker socket: **absent**
- temporary read-only source mount: **absent**
- temporary shared-memory extraction tree: **absent**
- isolated worker containers: **absent**
- successful temporary target tree: **removed**

## Acceptance boundary

This milestone certifies the **captured application database/job-queue state and bounded worker startup** for the tested private recovery contract. It does not by itself claim a full bare-metal disaster-recovery acceptance.

The separate full Cold restore of **81,328 files / 252.66 GiB** remains deferred until a sufficiently large fresh target is available.

The next private software step is to bind the phase-28 certification artifact explicitly into the normal recovery contract/engine. The existing fail-closed worker guard must not simply be removed.