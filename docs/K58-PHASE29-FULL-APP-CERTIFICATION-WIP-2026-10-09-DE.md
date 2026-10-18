# K58 Phase 29 – Full-App Certification – PASS

**Language / Sprache:** English · [Deutsch](K58-PHASE29-FULL-APP-CERTIFICATION-WIP-2026-10-09.md)

Status: 2026-10-10

## Result

Phase 29 has been fully real-tested, accepted under root execution, and integrated into the K58 recovery contract.

- Full-App realtest: PASS
- Full-App Start Certificate v1: PASS
- Phase29 Report Binding: PASS
- Capture Contract Reuse: PASS
- Full-App Scope Binding: PASS
- Paperless Process Roles: PASS
- Database Integrity: PASS
- Certificate Sidecar: PASS
- Canonical Root Regression: 1330/1330 PASS
- USB Manifest Final: PASS
- Runtime Cleanup / Socket Absence: PASS
- K58 Phase29 Integration Root Acceptance: PASS

## Certified scope

- Immich: stock API + Microservices in the normal server process scope.
- Paperless: stock `/init` with web server, Celery Worker, Celery Beat/Scheduler, and Document Consumer.
- No external network.
- Pre-/post-queue gates and database/schema integrity remain part of the fail-closed contract.

## Failure chain and corrections

### V1

Capture, isolation, image binding, PostgreSQL restore, and the pre-start queue gate passed. Stock startup failed because of the Redis URL for Paperless. The stock init path requires `unix://`; Paperless internally translates this value appropriately for Celery.

### V2

After correcting the Redis URL, Paperless started successfully and became healthy. The certification run then failed during process-role verification. The cause was not Paperless but the Docker top query: Docker Engine 29 requires a PID field in `ps` output. Therefore `docker top <cid> -eo args` is unsuitable.

### V3

Process-role verification uses `docker top <cid> -eo pid,args`. After a preliminary stop caused solely by insufficient free space, fail evidence was moved losslessly to the separate evidence target and the complete run was restarted.

The subsequent realtest passed completely, including:

- Capture Binding
- Isolation
- Image Binding
- PostgreSQL Restore
- Pre-Start Queue Gate
- Stock Apps Started
- Post-Start Queue Gate
- Full-App Certification
- Runtime Cleanup

## Integration

Phase 28 remains a separate worker-start contract. Phase 29 adds a separate full-app-start contract. A worker certificate alone must still not authorize the broader startup scope.

Full-app authorization is bound to the scope actually certified and to its capture, image, queue, and database-integrity conditions. Missing or tampered bindings remain fail-closed.

The canonical test-ID list was re-registered after adding the new Phase29 contract and guard tests. The final root run passed 1330/1330 tests. The USB manifest was then resealed and verified successfully.

## Security state after completion

- isolated Docker service: inactive
- isolated containerd service: inactive
- isolated Docker socket: absent
- system Docker socket in recovery context: absent

## Lessons learned

- With Docker Engine 29, use `docker top <cid> -eo pid,args` directly for process-role verification.
- `required=False` handles nonzero return codes but not `subprocess.TimeoutExpired`; diagnostic probes must handle timeouts explicitly.
- Do not start retained mutable application targets directly for diagnostics when schedulers/workers can modify data; use fresh or cloned staging data.
- Check free space before large realtests. If necessary, move diagnosed fail evidence losslessly to a separate evidence target rather than deleting it broadly.
- `systemctl show Result=success` is not final for running units; evaluate ActiveState/SubState together with journal markers.
- Do not weaken permissions on root-private evidence for easier inspection; extract only bounded safe fields.
- After extending the canonical test set, update the test-ID contract and USB manifest together and then validate them under root execution.

## Completion

`K58_PHASE29_INTEGRATION_ROOT_ACCEPTANCE=PASS`

Phase 29 is complete. Private capture identities, run IDs, container IDs, internal paths, and complete private evidence hashes are deliberately not documented in the public repository.
