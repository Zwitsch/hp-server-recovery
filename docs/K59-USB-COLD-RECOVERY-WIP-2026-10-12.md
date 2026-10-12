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
- Dry-run/apply separation is implemented. Non-root apply is rejected.
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
- A productive base executor now exists with explicit root/confirmation gates. Its isolated test-root path has passed repository/keyring deployment, filesystem creation, payload deployment and systemd no-autostart checks. A real fresh-host root run has not yet been performed.
- Automated K59 unit tests cover wrong OS, missing/malformed payloads, target-root rejection, fail-closed filesystem rules and sandbox path safety.
- Combined K59 regression (unit tests + payload integrity + fresh-host plan) passes.

## Current proof summary

- K58 restore engine: certified.
- K59 preflight/target guards: PASS.
- K59 repository/package plan: PASS.
- K59 payload integrity: PASS.
- K59 fresh-host plan: PASS.
- K59 sandbox apply simulation: PASS.
- K59 productive executor test-root gates: PASS.
- K59 combined regression: PASS.

## Remaining before final K59 certification

1. Run the productive executor as root on a genuinely fresh Ubuntu 22.04 target, not on the production host, and validate actual APT package installation, identity creation, metadata ownership/modes and systemd daemon reload.
2. Validate controlled service enablement only after component/path/secret gates pass; automatic bootstrap start remains forbidden.
3. Hand off to the existing K58 recovery UI/engine and perform an end-to-end restore.
4. Reboot the restored host and repeat the required integrity/application checks.
5. Complete a physical USB/target-disk pilot. Any destructive disk action remains separately gated by explicit target identity confirmation.

No private capture IDs, evidence hashes, secrets or internal recovery paths are published in this document.
