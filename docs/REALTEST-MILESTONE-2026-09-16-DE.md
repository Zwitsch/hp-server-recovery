# Realtest-Meilenstein — 2026-09-16

**Sprache / Language:** Deutsch · [English](REALTEST-MILESTONE-2026-09-16.md)

Dieses Dokument hält einen bereinigten Entwicklungsmeilenstein aus der privaten HP-Server-Recovery-Validierungsumgebung fest.

Produktive Backup-Daten, Zugangsdaten, Hostnamen, Maschinenidentitäten, private Pfade, rohe Recovery-Berichte und private Release-Artefakte sind bewusst ausgeschlossen.

## K25-Meilenstein

Das private Recovery-Paket erreichte die K25-Grenze des isolierten Read-only-Realtests.

In der dedizierten Recovery-Umgebung validiert:

- finale Archividentität und Fresh-Extraction-Prüfungen: **PASS**
- vollständige Development-/Root-Regression-Gates: **PASS**
- Sicherheits-Gate der isolierten Container-Runtime: **PASS**
- sauberer Runtime-Post-State nach dem Isolation-Gate: **PASS**
- Read-only-Kompatibilitätsklassifizierung von App-Backup und Release: **PASS**
- kompatible App-Backup-Tupel bleiben planbar
- inkompatible Provenienz des ausführbaren Images wird vor dem Restore abgewiesen
- Full-Server-Planung verschluckt kein inkompatibles verpflichtendes App-Tupel

## Backup-/Release-Identitätsregel

Ein App-Backup ist mit einem ausgewählten ausführbaren Release nur kompatibel, wenn beide Identitäten übereinstimmen:

1. App-Version
2. Identität des ausführbaren Images

Ein übereinstimmender Versionsstring allein reicht nicht aus.

K25 klassifiziert App-Backup-/Release-Tupel als:

- `COMPATIBLE`
- `INVALID_BACKUP`
- `INCOMPATIBLE_RELEASE_IDENTITY`

Nur `COMPATIBLE` darf als planbare App-Backup-Quelle fortgesetzt werden.

Dieselbe Provenienzregel gilt für Data-only-Planung. Data-only-Recovery umgeht die Provenienzprüfung des ausführbaren Images nicht.

## Fail-Closed-Verhalten

Der validierte Read-only-Planungspfad weist nicht passende App-Identitäten ab für:

- App-Data-only-Planung
- vollständige App-Planung
- Full-Server-Planung, wenn die App verpflichtend ist

Die Implementierung normalisiert Backup-Metadaten nicht auf ein bevorzugtes Release, schreibt das ausgewählte Release nicht passend zu einem Backup um, fällt nicht auf ein anderes Same-Version-Image zurück und ersetzt kein Release stillschweigend.

Auch Previous-Release-Planung ist an die explizit ausgewählte Previous-Release-Identität gebunden, damit Planner und Executor nicht stillschweigend unterschiedliche Releases bewerten können.

## Scope-Grenze

Dieser Meilenstein beanspruchte **nicht**:

- erfolgreichen realen App-Restore
- erfolgreichen Full-Server-Restore
- Disaster-Recovery-Zertifizierung
- Production Readiness

Der nächste private Validierungsschritt dieses Stands begann nach expliziter Freigabe mit einem kontrollierten isolierten App-Restore.

## Trennung öffentlich/privat

Das öffentliche Repository bleibt eine bereinigte Engineering-Teilmenge. Rohe Recovery-Archive, private Backup-Daten, produktive Zugangsdaten, private Infrastrukturdetails und maschinenspezifische Nachweise bleiben außerhalb dieses Repositorys.
