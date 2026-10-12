# K59 USB Cold Recovery – WIP

Status: 2026-10-12

## Goal

Fresh Ubuntu 22.04 Jammy amd64 host -> recovery USB -> validated base bootstrap -> existing K58 recovery engine -> application/data restore -> reboot certification.

## Current verified K59 state

- Fresh-host preflight is implemented and fail-closed.
- Host contract is locked to Ubuntu 22.04 Jammy amd64 for the first physical certification.
- Wrong OS release/codename is rejected.
- Missing or malformed required recovery payloads are rejected without traceback.
- UID/GID conflicts are checked.
- The data target must already exist as a dedicated mount; `/` is explicitly rejected as a data target.
- Dry-run/apply separation is implemented. Non-root apply is rejected and no productive writes are currently performed by the apply gate.
- APT/repository policy is validated in dry-run mode.
- Docker engine/runtime remain Ubuntu packages (`docker.io`, `containerd`, `runc`).
- Docker upstream repository is limited to the plugin family required by the captured contract (Buildx/Compose); Docker CE substitution is forbidden.
- Filen APT source is evidence-only and excluded from restoration.
- Repository payload integrity is verified.
- systemd payload integrity is verified.
- Script payload byte integrity is verified against the authoritative payload manifest. The older script index contains stale metadata for four payloads and is not used as the byte-integrity authority.
- Filesystem creation logic is fail-closed: only contracts with explicit numeric owner/group, exact mode, fail-closed flag and an explicit create-if-missing contract are eligible for automatic directory creation.
- `/mnt/data` itself is never auto-created and must pass the dedicated-mount gate first.
- A deterministic fresh-host plan is generated without writes.
- systemd units are never auto-started during bootstrap; enablement is deferred until validation according to each captured unit policy.
- Sandbox apply simulation copies the planned repository, keyring, systemd and script payloads into an isolated test root with hash-preserving verification and rejects unsafe sandbox roots.
- Automated K59 unit tests cover wrong OS, missing/malformed payloads, target-root rejection, fail-closed filesystem rules and sandbox path safety.

## Current proof summary

- K58 restore engine: certified.
- K59 preflight/target guards: PASS.
- K59 repository/package plan: PASS.
- K59 payload integrity: PASS.
- K59 fresh-host plan: PASS.
- K59 sandbox apply simulation: PASS.
- K59 unit tests: PASS.

## Remaining before final K59 certification

1. Implement and certify the productive root apply executor for repository/keyring installation, compatible Jammy package installation, identity handling, verified filesystem creation, payload deployment and systemd daemon reload/controlled enablement.
2. Run that executor on a genuinely fresh Ubuntu 22.04 target, not on the production host.
3. Hand off to the existing K58 recovery UI/engine and perform an end-to-end restore.
4. Reboot the restored host and repeat the required integrity/application checks.
5. Complete a physical USB/target-disk pilot. Any destructive disk action remains separately gated by explicit target identity confirmation.

No private capture IDs, evidence hashes, secrets or internal recovery paths are published in this document.
