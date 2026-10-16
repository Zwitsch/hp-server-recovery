# K59 USB Cold Recovery – WIP

Status: 2026-10-16

## Goal

Fresh Ubuntu 22.04 Jammy amd64 host -> recovery USB -> validated base bootstrap -> existing K58 recovery engine -> application/data restore -> reboot certification.

## Current verified K59/K60 state

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
- Repository, systemd and script payload integrity are verified.
- Filesystem creation is fail-closed; `/mnt/data` is never auto-created and must pass the dedicated-mount gate first.
- A deterministic fresh-host plan is generated without writes.
- systemd units are never auto-started during bootstrap.
- Sandbox apply and productive mapped-root apply passed on the isolated fresh Jammy root.
- Required package installation, identities, metadata finalization, kernel/initramfs preparation and cleanup passed in isolation.
- The USB recovery tree contains the productive K59 bootstrap sources and portable entry points for preflight, plan and apply.
- `START-RECOVERY.sh` exposes fresh-host processing only through explicit options: `--fresh-host-preflight`, `--fresh-host-plan`, and `--fresh-host-apply`. Normal invocation continues to the existing recovery wizard. There is no silent fresh-host apply.
- USB entry points derive their root from `HP_RECOVERY_USB_ROOT`; they do not depend on a fixed development checkout path.
- Recovery-VM integration testing uses its dedicated isolated data target explicitly. A genuine fresh host retains `/mnt/data` as the production default.
- K60 adds fail-closed onboarding for applications that are not yet covered by an existing certified recovery contract.
- Unknown applications are first represented by an inventory-bound candidate with restore permission disabled.
- Certification requires isolated real restore/runtime evidence; metadata discovery alone cannot authorize restore.
- The K60 real-runtime pilot passed using an offline, immutable image source, no external network, read-only restored-data binding, runtime content verification and mandatory cleanup.
- Tagless OCI archives are bound using two distinct identities where applicable: the archive config blob is cryptographically verified while Docker runtime addressability is bound to the immutable OCI manifest digest. These identities are not assumed to be interchangeable.
- The real K60 candidate remained `PENDING_ONBOARDING` and non-restorable until the isolated runtime report passed; only then was a `CERTIFIED` certificate with restore permission generated.
- K60 certificate binding is enforced both when a plan is created and again after fresh rediscovery at runtime.
- After K60 real-runtime certification and final manifest reseal, the authoritative root canonical suite passed 1376/1376 tests.
- Post-certification safety state: isolated Docker/containerd services inactive and both production and isolated Docker sockets absent.

## Current proof summary

- K58 restore engine: certified.
- K59 preflight/target guards: PASS.
- K59 repository/package plan: PASS.
- K59 payload integrity: PASS.
- K59 fresh-host plan: PASS.
- K59 sandbox apply simulation: PASS.
- K59 productive executor mapped fresh-root apply: PASS.
- K59 real package installation in isolated fresh root: PASS.
- K59 identity creation: PASS.
- K59 metadata finalization: PASS.
- K59 boot-package/kernel/initramfs preparation: PASS.
- K59 cleanup/no-leftover-mount gate: PASS.
- K59 USB entry-point integration: PASS.
- K60 unknown-app candidate/classification/certificate chain: PASS.
- K60 dual plan/runtime certificate gate: PASS.
- K60 actual isolated unknown-app restore/runtime/integrity certification: PASS.
- Final manifest reseal: PASS.
- Authoritative root canonical regression: 1376/1376 PASS.
- Safety postcheck: PASS.
- Final fresh-installed-host restore + reboot certification: PENDING.

## Important scope decision

K59/K60 is a recovery system for a machine on which a fresh supported Ubuntu installation already exists. It is not an Ubuntu installer and does not repartition the system disk or install a bootloader as part of normal recovery. The isolated rootfs and K60 runtime tests prove bootstrap, package, identity, filesystem, payload, metadata, kernel/initramfs and unknown-application onboarding behavior, but they are not a substitute for the final reboot test on a genuinely fresh installed Ubuntu target.

## Remaining before final certification

1. Create a genuinely fresh Ubuntu Server 22.04 LTS amd64 VM/host with UEFI, an empty system installation and a dedicated data target for `/mnt/data`.
2. Start recovery only through the intended USB/recovery entry point; do not manually preinstall Docker, identities, recovery services or application prerequisites.
3. Validate the complete fresh-host bootstrap on that target, including package installation, identities, metadata and controlled systemd preparation.
4. Hand off to the existing recovery UI/engine and perform an end-to-end restore from the selected L2/L3 source.
5. Certify applications, databases, integrity gates, K60 onboarding behavior where applicable, and fail-closed conditions before reboot.
6. Reboot the restored fresh host and repeat the required system/application/integrity checks.
7. Complete the physical USB/target-disk pilot after the VM-level cold-recovery flow passes. Any destructive disk action remains separately gated by explicit target identity confirmation.

No private capture IDs, evidence hashes, secrets, private UUIDs or internal recovery paths are published in this document.
