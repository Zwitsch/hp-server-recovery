# HP Server Recovery

[![Tests](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml/badge.svg)](https://github.com/Zwitsch/hp-server-recovery/actions/workflows/tests.yml) ![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg) ![Ubuntu](https://img.shields.io/badge/target-Ubuntu%2022.04-E95420) ![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB)

**Fail-closed disaster recovery for self-hosted Linux servers, built around proof before restore.**
HP Server Recovery binds backups, release identity, target identity and recovery state before destructive actions are allowed; ambiguous or stale evidence stops the run.
It adds isolated restore/runtime certification, secret-leak checks, resumable audited state and explicit cleanup gates around application-aware recovery.
The public repository is a sanitized, reproducible engineering subset; production backups, credentials and machine identities are deliberately excluded.

> **Status — 2026-10-16:** the private recovery package has passed isolated FULL_SERVER recovery, K59 fresh-host bootstrap validation and K60 real-runtime certification for fail-closed onboarding of an unknown application. The final fresh-installed-host restore + reboot certification is still pending. The public repository is not a drop-in production recovery image.

## Recovery model at a glance

```text
Backup source
     |
     v
Discover + inventory
     |
     v
Bind snapshot + manifests + release identity
     |
     v
Deterministic restore plan
     |
     v
Safety + target + secret gates
     |
     v
Isolated restore + runtime verification
     |
     v
Certificate
     |
     v
Real restore
     |
     v
Integrity + cleanup + reboot verification
```

The core rule is simple: **discovery is not authorization**. Missing, stale or ambiguous evidence stops the restore instead of being guessed around.

## How is this different from ReaR?

[Relax-and-Recover (ReaR)](https://relax-and-recover.org/) is a mature Linux disaster-recovery system focused on recreating a machine's rescue environment, storage layout and backup/restore workflow. HP Server Recovery is not intended as a replacement for ReaR's rescue-media and bare-metal capabilities.

The emphasis here is different and deliberately stricter at the **application recovery contract** layer:

| Area | ReaR | HP Server Recovery |
| --- | --- | --- |
| Primary focus | Linux rescue / system recreation / backup integration | Fail-closed, application-aware restore orchestration and certification |
| Ambiguous recovery input | Configuration/workflow dependent | Restore gate stops when required identity/binding evidence is missing or ambiguous |
| Backup binding | Integrates multiple backup methods | Explicit source, snapshot, manifest and release-identity binding before restore |
| Application identity | Not its primary abstraction | Exact application/runtime release identity is part of the recovery contract |
| Unknown applications | General system recovery model | Discovered app remains non-restorable until isolated restore/runtime evidence certifies it |
| Runtime isolation | Rescue/recovery environment | Dedicated isolated container runtime with production-socket boundary checks |
| Completion | Successful recovery workflow | Requires integrity evidence, cleanup state and secret-free persistent reports |
| Testing model | Rescue/recovery workflows | Synthetic fixtures + negative gates + isolated real-restore/runtime certification |

“Stricter” therefore means **more fail-closed evidence gates around application restore**, not a claim that HP Server Recovery is more complete than ReaR as a general-purpose Linux disaster-recovery product.

For a broader, non-competitive positioning against ReaR, Borg/Restic, disk imaging and Docker Compose backups, see [Why HP Server Recovery?](docs/WHY-HP-SERVER-RECOVERY.md).

## 5-minute public quickstart

This runs the sanitized public test package with synthetic fixtures. It does **not** touch production backups and does not perform a destructive system restore.

Requirements: Linux/macOS/WSL, Git, Python 3.12+ and `pip`.

```bash
git clone https://github.com/Zwitsch/hp-server-recovery.git
cd hp-server-recovery
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --disable-pip-version-check PyYAML
bash demo.sh
```

A successful run ends with:

```text
DEMO_RESULT=PASS
```

`demo.sh` compiles the public Python sources and runs the same three sanitized regression suites used by GitHub Actions. It refuses to continue if the required Python dependency is unavailable; it contains no production backup path or destructive restore command.

To focus specifically on the isolated-realtest contract and its synthetic fixtures:

```bash
python -m unittest tests.test_realtest_mode
```

The fixtures live under `tests/fixtures/`; synthetic catalog/package data is under `runtime-data/` and `payload/`. These public tests exercise safety and recovery logic without publishing or requiring the private production recovery payload.

## What it does

HP Server Recovery is designed to make restoration of a self-hosted Linux server reproducible, testable and conservative by default.

Core design goals:

- fail closed when recovery inputs, target identity or safety bindings are missing or ambiguous
- separate generic recovery logic from host-specific configuration
- validate manifests and release identity before destructive operations
- support fixture-driven tests and isolated real-restore testing
- make recovery state, command execution and cleanup auditable
- keep secrets, production payloads and machine identities outside the source repository

## Safety model

The recovery engine treats destructive actions as explicitly gated operations. Isolated realtests require bound target identities, allowed and forbidden hostnames, protected path prefixes, read-only recovery sources and an isolated container runtime. Missing bindings cause the operation to stop instead of falling back to permissive defaults.

Persistent reports and audit data are checked for secret-marker leakage before a run can be considered complete.

See [SECURITY.md](SECURITY.md) and `docs/SAFETY-MODEL.md`.

## Latest private certification — K59/K60, 2026-10-16

Current sanitized validation status:

- K58 restore engine and prior isolated FULL_SERVER recovery: **certified baseline**
- K59 fresh-host preflight, package/repository plan, mapped-root apply, identities, metadata and boot preparation: **PASS**
- K59 USB/recovery entry-point integration: **PASS**
- K60 fail-closed unknown-application candidate/classification/certificate chain: **PASS**
- K60 dual plan/runtime certificate gate: **PASS**
- K60 actual isolated unknown-app restore/runtime/integrity certification: **PASS**
- final manifest reseal after K60: **PASS**
- latest authoritative private root canonical regression: **1376/1376 PASS**
- post-certification isolated Docker/containerd cleanup and socket boundary: **PASS**
- final fresh-installed-host restore + reboot certification: **PENDING**

K60 specifically prevents metadata discovery from silently authorizing a new application. A discovered application remains `PENDING_ONBOARDING` and non-restorable until an isolated restore/runtime report has passed and a bound certificate explicitly permits restore.

For tagless OCI archives, archive/config identity and Docker runtime addressability are treated as separate immutable bindings instead of assuming that a config-blob digest is interchangeable with Docker's runtime image identity.

See [K59/K60 USB Cold Recovery status](docs/K59-USB-COLD-RECOVERY-WIP-2026-10-12.md).

## Earlier recovery milestones

The repository retains detailed milestone documents for the earlier K56-K58 development and the Immich/Filen Cold-storage work. Those checkpoints document the progression from isolated FULL_SERVER recovery through Cold-restore pilots, capture binding, database/Redis restoration and application-start certification.

Notable retained results include:

- K57 L2 and COMBINED Cold pilots: **100/100 BLAKE3 PASS** for each pilot
- Immich/Filen Cold archive: **81,328/81,328 BLAKE3 PASS**
- K58 capture/database/runtime phases: progressively integrated into the later certified K59/K60 baseline

Earlier checkpoint counts are historical and must not be interpreted as the current regression total. The current authoritative private regression result is the K60 result above.

See:

- `docs/FINAL-RECOVERY-MILESTONE-2026-09-27.md`
- `docs/RECOVERY-IMMICH-MILESTONE-2026-10-03.md`
- `docs/K57-COLD-RESTORE-MILESTONE-2026-10-04.md`
- `docs/K58-INVENTORY-BINDING-MILESTONE-2026-10-04.md`
- `docs/K59-USB-COLD-RECOVERY-WIP-2026-10-12.md`

## Repository structure

- `lib/hp_recovery/` — reusable recovery engine
- `bin/` — command-line entry points
- `config/` — sanitized example configuration
- `tests/` — automated tests and synthetic fixtures
- `runtime-data/` — synthetic catalog data used by the test package
- `manifests/` — integrity manifest for the synthetic package
- `payload/` — synthetic test-only package contracts; no production payloads
- `demo.sh` — one-command synthetic public regression demo

## Public vs. private validation

The public repository intentionally contains only sanitized logic, tests and synthetic fixtures. Its GitHub Actions workflow compiles the Python sources and runs the three published unittest suites shown in the quickstart.

The private recovery tree contains additional host-specific contracts, recovery payload metadata, isolated runtime machinery and certification tests. Its latest authoritative root canonical regression is **1376/1376 PASS** after K60 real-runtime certification.

Private results are stated separately so that unpublished tests are never presented as if they were executable from this public repository.

The public repository intentionally excludes production backup data, credentials, personal identifiers, private infrastructure details, machine-specific paths, raw recovery evidence and private archive hashes.

## Remaining end-to-end acceptance

The final project-level acceptance remains intentionally open until the complete workflow is demonstrated on a genuinely fresh Ubuntu 22.04 installation:

1. start through the intended recovery/USB entry point
2. validate fresh-host bootstrap and dedicated data target
3. select and bind the recovery source/snapshot
4. perform the complete restore through the recovery engine
5. certify applications, databases and integrity gates
6. reboot the restored host
7. repeat the required post-reboot system/application/integrity checks

Until that succeeds, the project does not claim final bare-metal/fresh-host disaster-recovery certification.
