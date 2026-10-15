# K59 USB Cold Recovery – WIP

Status: 2026-10-15

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
- A productive base executor exists with explicit root/confirmation gates and has passed isolated test-root deployment.
- Fresh Jammy rootfs creation and preflight passed on the isolated system target.
- The productive executor passed on the mapped fresh Jammy root: repositories/keyrings, filesystem layout, payload deployment and the systemd no-autostart gate were applied successfully.
- Real package installation inside the isolated fresh root passed. Required Ubuntu/Docker/NodeSource repository access was validated. Filen remained excluded.
- Required identities were created and verified without UID/GID conflicts.
- A metadata finalizer was added and certified. The authoritative mapped-root certification covers 92 known metadata objects with zero missing objects and zero post-apply mismatches. Three scripts with explicitly unknown owner/group remain deferred rather than guessed.
- Post-metadata payload integrity passes for repositories, systemd files and scripts.
- Chroot cleanup is certified with no leftover mounts and no persistent `policy-rc.d` suppression file.
- Boot-package preparation passed in the isolated fresh root: `systemd-sysv`, initramfs support and the generic Jammy kernel were installed successfully.
- `/sbin/init` is present and exactly one kernel plus one initrd were generated in the isolated fresh root.
- Boot-package execution completed with explicit `K59_BOOT_BASE=PASS`; cleanup left no descendant mounts and removed temporary service-start suppression.
- GRUB installation and repartitioning were deliberately not performed. The isolated system target has only one ext4 partition and no EFI System Partition; forcing it bootable would not represent the intended recovery workflow.
- Read-only boot-strategy audit confirmed the current recovery VM is itself a QEMU guest. No local libvirt/QEMU control plane is available from inside that VM to launch the isolated target as a separate fresh test machine.
- Therefore the final reboot certification is defined against a genuinely fresh, separately installed Ubuntu 22.04 VM/host, matching the actual disaster-recovery goal: Ubuntu is already installed, then the recovery USB performs bootstrap and restore.
- Automated K59 unit tests cover wrong OS, missing/malformed payloads, target-root rejection, fail-closed filesystem rules and sandbox path safety.
- Combined K59 regression (unit tests + payload integrity + fresh-host plan) passes.

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
- K59 combined regression: PASS.
- Final fresh-installed-host restore + reboot certification: PENDING.

## Important scope decision

K59 is a recovery system for a machine on which a fresh supported Ubuntu installation already exists. It is not an Ubuntu installer and does not repartition the system disk or install a bootloader as part of normal recovery. The isolated debootstrap/rootfs tests prove bootstrap, package, identity, filesystem, payload, metadata and kernel/initramfs behavior, but they are not a substitute for the final reboot test on a genuinely fresh installed Ubuntu target.

## Remaining before final K59 certification

1. Create a genuinely fresh Ubuntu Server 22.04 LTS amd64 VM/host with UEFI, an empty system installation and a dedicated data target for `/mnt/data`.
2. Start recovery only through the intended USB/recovery entry point; do not manually preinstall Docker, identities, recovery services or application prerequisites.
3. Validate the complete fresh-host bootstrap on that target, including package installation, identities, metadata and controlled systemd preparation.
4. Hand off to the existing K58 recovery UI/engine and perform an end-to-end restore from the selected L2/L3 source.
5. Certify applications, databases, integrity gates and fail-closed conditions before reboot.
6. Reboot the restored fresh host and repeat the required system/application/integrity checks.
7. Complete the physical USB/target-disk pilot after the VM-level cold-recovery flow passes. Any destructive disk action remains separately gated by explicit target identity confirmation.

No private capture IDs, evidence hashes, secrets, private UUIDs or internal recovery paths are published in this document.
