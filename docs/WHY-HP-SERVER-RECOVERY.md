# Why HP Server Recovery?

**Language / Sprache:** English · [Deutsch](WHY-HP-SERVER-RECOVERY-DE.md)

HP Server Recovery explores a specific problem in self-hosted disaster recovery: **how do you prove that the backup, application release, target, restore procedure and recovered runtime still belong together before declaring a restore successful?**

It is not intended to replace established backup, imaging or Linux rescue tools. It adds a fail-closed orchestration and certification layer around application-aware recovery.

## Where it fits

| Tool/category | Strong at | Different emphasis in HP Server Recovery |
| --- | --- | --- |
| Relax-and-Recover (ReaR) | Linux rescue media, system recreation and integration with backup methods | Application-level identity binding, isolated runtime evidence and fail-closed certification gates |
| Borg / Restic | Efficient versioned backup repositories, deduplication, encryption and retention | Restore orchestration and proof that the selected application/runtime contract is the one being restored |
| Clonezilla / disk imaging | Reproducing disk/partition state | Selective service/application recovery with explicit source, release and runtime evidence |
| Docker Compose backups | Simple service definitions plus application-specific volume/database backup | Cross-checking backup snapshot, release identity, runtime identity, target identity, integrity and cleanup before certification |

These approaches are complementary. A recovery system can use established backup storage while applying stricter restore-time contracts on top.

## The additional problem this project targets

A backup being readable does not prove that an application can be restored correctly. A container starting does not prove that it is the intended release. A successful database import does not prove that the surrounding files, queue state, secrets and runtime belong to the same recovery snapshot.

HP Server Recovery therefore treats recovery as a chain of evidence:

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
Build deterministic restore plan
    |
    v
Safety / target / secret gates
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

Missing or ambiguous required evidence is a stop condition rather than an invitation to guess.

## Unknown applications

A central design goal is avoiding the assumption that every future application was manually encoded in advance. Discovery can produce a candidate recovery contract, but discovery alone does not grant permission to restore it.

The intended lifecycle is:

```text
DISCOVERED
   -> PENDING_ONBOARDING
   -> isolated restore/runtime evidence
   -> CERTIFIED
   -> restore allowed
```

If required contracts, evidence or runtime bindings cannot be established, the application remains non-restorable.

## What the public repository proves

The public repository contains sanitized recovery logic, synthetic fixtures and automated negative/positive tests. It is designed so that the safety model can be inspected and exercised without access to the private server, backups, credentials or production payload.

The private package has additional real recovery evidence. Those private results are documented only as sanitized milestone summaries and are deliberately kept distinct from what a fresh public checkout can reproduce.

## What it does not claim

HP Server Recovery is not currently a general-purpose replacement for ReaR, Borg, Restic, Clonezilla or application-native backup tools. It is also not yet presented as a drop-in production recovery distribution.

The remaining top-level acceptance gate is a complete recovery on a genuinely fresh installed Ubuntu target followed by reboot and post-reboot verification.
