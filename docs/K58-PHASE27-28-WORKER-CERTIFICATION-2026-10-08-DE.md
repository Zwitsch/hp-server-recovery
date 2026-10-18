# K58 Phasen 27–28 — zertifizierter Capture und Worker-Start-Zertifizierung

**Sprache / Language:** Deutsch · [English](K58-PHASE27-28-WORKER-CERTIFICATION-2026-10-08.md)

Aktualisiert: 2026-10-09

Dieses Dokument hält einen **bereinigten privaten Validierungsmeilenstein** fest. Produktive Payloads, hostspezifische Pfade, Adressen, Run-IDs, Container-IDs, Secrets und private Hashes sind bewusst ausgeschlossen.

## Phase 27 — zertifizierter quieszierter Capture

Das private Recovery-Paket hat einen produktiven Writer-Hold-Capture für den Konsistenzvertrag zwischen App-Datenbank und Job-Queue abgeschlossen.

Bereinigtes Ergebnis:

- Capture-Konsistenz: **CERTIFIED_QUIESCENT_CAPTURE**
- App-Writer-Hold und Wiederaufnahme der Services: **PASS**
- Live- und exportierte Queue-Gates: **PASS**
- ausführbare Jobs nach Capture-Gate: **0**
- fehlende Queue-/Job-Verknüpfung: **0**
- verwaiste Queue-/Job-Verknüpfung: **0**
- nicht klassifizierte Queue-Einträge: **0**
- erfasste Datenbank-, Redis- und erforderliche begrenzte App-Datei-Eingaben: **gehasht und gebunden**
- Worker-Start blieb nach Capture fail-closed: **in Phase 27 noch nicht zertifiziert**

Die ursprüngliche Capture-Evidenz ist unveränderliche Eingabe für die spätere Worker-Start-Zertifizierung.

## Phase 28 — isolierte Worker-Start-Zertifizierung

Das private Paket stellte den Phase-27-Capture in der isolierten Recovery-Runtime wieder her und zertifizierte einen begrenzten Worker-Start ohne Zugriff auf die produktive Container-Engine.

Abschließende bereinigte Gates:

- Capture-Bindung: **PASS**
- Read-only-Source-/Isolation-Gate: **PASS**
- exakte Offline-Runtime-Image-Bindung: **PASS**
- PostgreSQL-Restore: **PASS**
- Pre-Worker-Queue-Profil: **PASS**
- Immich-Worker-Start, ausschließlich Microservices-Scope: **PASS**
- Paperless-Celery-Worker-Start, ausschließlich Worker-Scope: **PASS**
- Paperless Beat: **disabled**
- Paperless Document Consumer: **disabled**
- begrenzte 60-Sekunden-Worker-Beobachtung: **PASS**
- Post-Worker-Queue-Profil: **PASS**
- PostgreSQL-Schema-Integrität: **UNCHANGED**
- PostgreSQL-Health-Check: **PASS**
- Paperless-SQLite-Integrität und Foreign Keys: **PASS**
- Paperless-SQLite-Inhalt: **UNCHANGED**
- isoliertes Runtime-Cleanup: **PASS**
- abschließende Worker-Start-Zertifizierung: **PASS**

`WORKER_START_CERTIFIED=true`

## Phase-28-Integrations-Root-Abnahme — 2026-10-09

Die private Worker-Start-Zertifizierung wird nun durch einen wiederverwendbaren Fail-Closed-Zertifizierungsvertrag repräsentiert, statt lediglich den zuvor bestehenden Worker-Guard zu entfernen.

Root-Abnahmeergebnis:

- Worker-Start-Certificate v1: **PASS**
- V9-Report-Bindung: **PASS**
- Certified-Capture-Contract-Bindung: **PASS**
- PostgreSQL-Schema-Fingerprint: **PASS**
- Paperless-Schema-Fingerprint: **PASS**
- exakte Worker-Image-Rollenbindung: **PASS**
- Queue-Gate-Versionsbindung: **PASS**
- Certificate-Integrity-Sidecar: **PASS**
- private Canonical-Root-Regression: **1317/1317 PASS**
- Recovery-Tree-Integritätsmanifest: **PASS**
- isoliertes Runtime-Cleanup nach Abnahme: **PASS**
- isolierter Runtime-Socket: **absent**
- produktiver Docker-Socket auf dem Recovery-Host: **absent**

Die Zertifizierung ist nur wiederverwendbar, solange ihre exakte Vertragsidentität gültig bleibt. Eine Änderung an Worker-Image, Queue-Gate, Capture-Semantik oder Datenbankschema macht die Zertifizierung ungültig und erfordert einen neuen Zertifizierungslauf.

## Wichtige Abnahmegrenze

Phase 28 zertifiziert ausschließlich die tatsächlich ausgeführten Scopes:

- Immich: `microservices`-Worker-Scope
- Paperless: ausschließlich Celery Worker
- Paperless Beat: disabled
- Paperless Document Consumer: disabled

Sie schaltet den normalen vollständigen App-Startpfad **nicht** frei. Die privaten Pfade `APP_FULL` und `FULL_SERVER` bleiben fail-closed, bis eine kombinierte Full-App-Start-Zertifizierung die verbleibenden App-Prozesse unter demselben wiederhergestellten Zustand abdeckt.

Der separate vollständige Cold-Restore mit **81,328 Dateien / 252.66 GiB** bleibt ebenfalls aufgeschoben, bis ein ausreichend großes frisches Ziel verfügbar ist.

## Wichtige technische Erkenntnisse

### Docker Engine 29 / containerd Image Store

In der getesteten Recovery-Runtime repräsentiert die vom containerd Image Store bereitgestellte Docker-Image-ID den OCI-Target-/Manifest-Digest und nicht den Image-Config-Digest des klassischen Docker Image Store. Die finale Bindung validiert deshalb die Kette:

`bound tag -> runtime OCI manifest digest -> manifest blob -> config.digest -> capture-bound config digest`

Dadurch wird ein falscher Mismatch verhindert, während die strikte Identitätsprüfung erhalten bleibt.

### PostgreSQL-Schemavergleich

Rohe Ausgabe von `pg_dump --schema-only` ist nicht byte-stabil, da PostgreSQL zufällig erzeugte `\restrict`-/`\unrestrict`-psql-Metacommand-Tokens ausgeben kann. Der finale Vergleich normalisiert **nur** diese nicht-semantischen Zeilen vor dem Hashing; reale DDL-Unterschiede bleiben fail-closed. Ein Negativtest bestätigt, dass eine tatsächliche DDL-Änderung weiterhin erkannt wird.

### Disziplin beim Recovery-Tree-Manifest

Temporäre Logs müssen außerhalb des durch das Integritätsmanifest abgedeckten Recovery-Baums bleiben. Statische Abnahme-Evidenz wird erst nach dem kanonischen Testlauf geschrieben, gefolgt von abschließendem Manifest-Reseal und Verifikation. Dadurch verändert der Testlauf nicht seine eigene Integritätsgrenze.

## Cleanup-Ergebnis

Nach erfolgreicher Zertifizierung und Root-Abnahme:

- isolierter Docker-Dienst: **inactive**
- isolierter containerd-Dienst: **inactive**
- isolierter Docker-Socket: **absent**
- temporärer Read-only-Source-Mount: **absent**
- temporärer Shared-Memory-Extraction-Tree: **absent**
- isolierte Worker-Container: **absent**
- erfolgreiches temporäres Target-Tree: **removed**

## Nächster privater Software-Schritt

Eine kombinierte Full-App-Start-Zertifizierung unter demselben zertifizierten wiederhergestellten Zustand ausführen. Erst nach deren Erfolg darf der Fail-Closed-Start-Guard für `APP_FULL` / `FULL_SERVER` neu bewertet werden.
