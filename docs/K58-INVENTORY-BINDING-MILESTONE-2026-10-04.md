# K58 inventory and backup-run binding — 2026-10-04

K58 adds conservative discovery of applications and a sanitized Docker inventory to the private recovery work tree. This page records the accepted checkpoints; it does not certify automatic onboarding or a new full-server restore.

## Accepted validation

- Phase 1 private root canonical suite: **1116/1116 PASS**, return code **0**.
- Phase 2 private root canonical suite: **1144/1144 PASS**, return code **0**.
- Discovery and inventory focused tests: **52/52 PASS**.
- Production read-only inventory pilot: **PASS**.
- Backup-run binding tests: **18/18 PASS** on the production host.
- Production installation, fresh application export, receipt verification and inventory publication to a local pilot target: **PASS**, return code **0**.

The 18 backup integration tests are separate from the 1144-test private recovery suite. These counts do not describe the sanitized public test suite.

## Implemented behavior

Discovery keeps unknown applications visible, including stopped deployments. Unknown application metadata and known project names grant no restore authorization.

Inventory includes exact container/image identities, Compose project/service identities, normalized mounts and host-binding risks. It excludes environment values, commands and arbitrary labels. Collection uses the explicit local Docker socket and read-only inspection commands.

A new application export captures inventory before and after the export and requires identical results. The successful run receipt binds the normalized inventory digest and exact inventory-file digest. Verification requires agreement between the current receipt and the run receipt.

The installed Level-2 and Level-3 scripts explicitly publish that bound inventory to their respective backup destinations. Level-3 needs this explicit step because it copies selected sources. The fresh export and local publication passed; a complete post-installation Level-2 or Level-3 backup run has not yet been accepted.

## Open work

A fresh production comparison against the private restore-profile template identified additional runtime mounts requiring review, including Redis data volumes and external-library bindings. A matching Compose project name does not prove complete data coverage. An empty mount observed at one moment is insufficient to classify it permanently as disposable.

Automatic onboarding remains incomplete. Consistent data export, exact offline release identity, secret binding, isolated runtime and restore-integrity contracts remain mandatory. Stopped deployments have not been automatically excluded or deleted.

The earlier K56 isolated full-server result remains the completed baseline. K58 does not yet have a new full-server or bare-metal acceptance run. The full **81,328-file / 252.66-GiB** Cold restore also remains open.

Raw inventory, container/image IDs, volume paths, machine identities, receipts, logs and private recovery payloads remain outside this public repository.
