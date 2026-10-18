# Realtest-Meilenstein — 2026-09-17

**Sprache / Language:** Deutsch · [English](REALTEST-MILESTONE-2026-09-17.md)

Dieses Dokument hält einen bereinigten Entwicklungsmeilenstein aus der privaten HP-Server-Recovery-Validierungsumgebung fest.

Produktive Backup-Daten, Zugangsdaten, Hostnamen, Maschinenidentitäten, private Pfade, rohe Recovery-Berichte und private Release-Artefakte sind bewusst ausgeschlossen.

## K30-Meilenstein

Das private Recovery-Paket erreichte K30 und schloss die kontrollierte isolierte App-Restore-Validierung für das damalige Urlaubsplaner-Release ab.

In der dedizierten Recovery-Umgebung validiert:

- finale Archividentität und Fresh-Extraction-Validierung: **PASS**
- beibehaltene Regression- und Release-Gates: **PASS**
- isolierter App-`APP_DATA_ONLY`-Restore: **PASS**
- isolierter App-`APP_FULL`-Restore: **PASS**
- Backup-/Release-Tupelklassifizierung: **COMPATIBLE**
- Offline-App-Image-Provenienz und Runtime-Bindung: **PASS**
- app-spezifische Datenbankintegritätsprüfung: **PASS**
- Container-/Runtime-Cleanup und Secret-Marker-Verifikation: **PASS**
- Read-only-Recovery-Quelle blieb während des gesamten Laufs schreibgeschützt
- Host-Docker blieb von der Realtest-Runtime isoliert
- isolierte Runtime kehrte nach Abschluss in einen sauberen inaktiven Zustand zurück

## Härtung der Runtime-Image-Identität

K30 erhält den exakten App-Release-Identitätsvertrag und unterstützt zugleich containerd-basierte Docker-Image-Stores, bei denen sich Runtime-Image-Target-Digest und Image-Config-Digest unterscheiden können.

Die validierte Kette bindet:

1. verifiziertes Image-Archiv
2. OCI-Target-/Manifest-Digest
3. Image-Config-Digest
4. ausgewählte Release-Identität
5. zur Laufzeit aufgelöste Image-Identität
6. das tatsächlich von der isolierten App-Runtime verwendete Image

Die Implementierung verlässt sich nicht allein auf einen Tag und akzeptiert keine mehrdeutigen oder ungebundenen Runtime-Identitäten.

## Härtung des Full-App-Runtime-Cleanups

Der isolierte Full-App-Pfad validiert zusätzlich die Anforderungen an die App-Runtime-Eigentümerschaft und entfernt Recovery-eigene isolierte Runtime-Reste vor dem abschließenden Secret-Marker-Scan.

Der finale Marker-Scan bleibt fail-closed. Er wurde weder abgeschwächt noch umgangen.

## Scope-Grenze

Dieser Meilenstein beanspruchte **nicht**:

- erfolgreichen Full-Server-Restore
- Disaster-Recovery-Zertifizierung
- Production Readiness

Ein separater Mismatch zwischen App-Backup und Release-Identität blieb damals ein Blocker für die breitere Full-Server-Validierung und musste ohne Abschwächung des exakten Release-Provenienzvertrags behoben werden.

## Trennung öffentlich/privat

Das öffentliche Repository bleibt eine bereinigte Engineering-Teilmenge. Rohe Recovery-Archive, private Backup-Daten, produktive Zugangsdaten, private Infrastrukturdetails, maschinenspezifische Pfade und rohe Recovery-Nachweise bleiben außerhalb dieses Repositorys.
