# K58 phases 27–28 — certified capture and worker-start certification

Updated: 2026-10-09

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

## Phase-28 integration root acceptance — 2026-10-09

The private worker-start certification is now represented by a fail-closed reusable certification contract rather than by simply removing the pre-existing worker guard.

Root acceptance result:

- worker-start certificate v1: **PASS**
- V9 report binding: **PASS**
- certified-capture contract binding: **PASS**
- PostgreSQL schema fingerprint: **PASS**
- Paperless schema fingerprint: **PASS**
- exact worker-image role binding: **PASS**
- queue-gate version binding: **PASS**
- certificate integrity sidecar: **PASS**
- private canonical root regression: **1317/1317 PASS**
- recovery-tree integrity manifest: **PASS**
- isolated runtime cleanup after acceptance: **PASS**
- isolated runtime socket: **absent**
- productive Docker socket on the recovery host: **absent**

The certification is reusable only while its exact contract identity remains valid. A worker-image, queue-gate, capture-semantics or database-schema change invalidates the certification and requires a new certification run.

## Important acceptance boundary

Phase 28 certifies only the scopes that were actually exercised:

- Immich: `microservices` worker scope
- Paperless: Celery worker only
- Paperless Beat: disabled
- Paperless document consumer: disabled

It **does not** unlock the normal complete application-start path. The private `APP_FULL` and `FULL_SERVER` paths remain fail-closed pending a combined full-application start certification that covers the remaining application processes under the same restored state.

The separate full Cold restore of **81,328 files / 252.66 GiB** also remains deferred until a sufficiently large fresh target is available.

## Important engineering findings

### Docker Engine 29 / containerd image store

On the tested recovery runtime, the Docker image ID exposed by the containerd image store represents the OCI target/manifest digest rather than the image-config digest used by the classic Docker image store. The final binding therefore validates the chain:

`bound tag -> runtime OCI manifest digest -> manifest blob -> config.digest -> capture-bound config digest`

This prevents a false mismatch while retaining strict identity checking.

### PostgreSQL schema comparison

Raw `pg_dump --schema-only` output is not byte-stable because PostgreSQL may emit randomly generated `\restrict` / `\unrestrict` psql meta-command tokens. The final comparison normalizes **only** those non-semantic lines before hashing; real DDL differences remain fail-closed. A negative test verifies that an actual DDL change is still detected.

### Recovery-tree manifest discipline

Temporary logs must stay outside the integrity-manifested recovery tree. Static acceptance evidence is written only after the canonical test run, followed by a final manifest reseal and verification. This prevents the test run itself from mutating its own integrity boundary.

## Cleanup result

After successful certification and root acceptance:

- isolated Docker service: **inactive**
- isolated containerd service: **inactive**
- isolated Docker socket: **absent**
- temporary read-only source mount: **absent**
- temporary shared-memory extraction tree: **absent**
- isolated worker containers: **absent**
- successful temporary target tree: **removed**

## Next private software step

Run a combined full-application start certification under the same certified restored state. Only after that succeeds may the `APP_FULL` / `FULL_SERVER` fail-closed start guard be reconsidered.