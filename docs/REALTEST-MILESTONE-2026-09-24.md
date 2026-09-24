# Realtest milestone — 2026-09-24

## English

This document records a sanitized development milestone from the private HP Server Recovery validation environment.

It intentionally excludes production backup data, credentials, hostnames, machine identities, private paths, raw recovery reports, private archive hashes and private release artifacts.

### K56 milestone

The private recovery package has progressed through K56 and completed the development and regression work required for a new focused application full-restore realtest.

Validated before the new focused run:

- final archive identity and fresh-extraction validation: **PASS**
- canonical private regression suite: **PASS**
- retained K24, K25 and K51 regression gates: **PASS**
- wizard and early gates: **PASS**
- dynamic backup-bound CURRENT release resolution: **PASS**
- exact backup/release tuple matching remains fail closed
- application version and image identity must match exactly
- previous-release handling remains separate from CURRENT release resolution
- realtest worker root binding has been corrected so standard realtest roots are no longer rewritten as a test root
- explicit fixture/test roots remain gated by the test-root safety contract
- a worker failure before the first recovery step can no longer be reported as a successful FULL restore
- recovery source read-only enforcement and host Docker isolation remain required

### Dynamic backup-bound CURRENT release binding

The wizard and expert CLI now use the same CURRENT release source-of-truth for isolated realtests.

For a selected backup set, CURRENT application release identity is resolved from the backup-bound release contract associated with that selected recovery set. A stale static CURRENT identity cannot override the selected backup metadata.

The contract remains fail closed:

- exact version match required
- exact image identity match required
- missing or ambiguous backup-bound release artifacts are rejected
- schema/contract errors remain distinct from identity mismatch
- no same-version fallback or silent substitution is allowed

### Wizard worker root hardening

A focused realtest exposed a worker-launch bug before any restore step executed.

The guided wizard incorrectly derived a worker test root from the parent of its state directory. In a real isolated run this caused the worker to enter the explicit test-root gate and stop before the first recovery action.

K56 now uses an explicit state/log root contract:

- standard realtest state and log roots launch the worker without a test-root override
- explicit fixture/test roots must map to one common base and retain the test-root gate
- ambiguous root combinations fail closed
- execute and resume use the same binding rules

The test-only environment gate remains a safety mechanism and is not used as a realtest workaround.

### Report correctness

The focused failure also exposed an inaccurate report fallback: a runtime state that had not completed could inherit planned service outcomes and appear FULL.

K56 now requires an actual completed runtime state before FULL/PARTIAL service outcomes are reported as a successful conclusion. Planned or running states cannot be promoted to a completed restore result.

### Current validation boundary

A fresh focused DeviceWatchdog `APP_FULL` isolated realtest is the next active validation step.

At the time of this documentation update, that focused run is still in progress and is **not** recorded as PASS.

This milestone does **not** claim:

- a successful DeviceWatchdog focused full-app restore after the K56 worker-root fix
- a successful full-server restore
- disaster-recovery certification
- production readiness

### Public/private separation

The public repository remains a sanitized engineering subset. Raw recovery archives, private backup data, credentials, hostnames, private infrastructure paths, machine identities, run identifiers and raw recovery evidence remain outside this repository.

---

## Deutsch

Dieses Dokument hält einen sanitisierten Entwicklungsmeilenstein aus der privaten HP-Server-Recovery-Validierungsumgebung fest.

Produktive Backup-Daten, Zugangsdaten, Hostnamen, Maschinenidentitäten, private Pfade, Rohberichte, private Archiv-Hashes und private Release-Artefakte sind bewusst nicht enthalten.

### K56-Meilenstein

Das private Recovery-Paket ist bis K56 fortgeschritten und hat die Entwicklungs- und Regression-Arbeiten abgeschlossen, die für einen neuen fokussierten vollständigen App-Realtest erforderlich sind.

Vor dem neuen fokussierten Lauf validiert:

- finale Archividentität und Prüfung einer frischen Extraktion: **PASS**
- kanonische private Regression-Suite: **PASS**
- beibehaltene K24-, K25- und K51-Gates: **PASS**
- Wizard- und Early-Gates: **PASS**
- dynamische backup-gebundene CURRENT-Release-Auflösung: **PASS**
- exakter Backup-/Release-Tupelabgleich bleibt fail-closed
- App-Version und Image-Identität müssen exakt übereinstimmen
- PREVIOUS-Release-Behandlung bleibt von der CURRENT-Auflösung getrennt
- die Worker-Root-Bindung wurde korrigiert, sodass Standard-Realtest-Roots nicht mehr als Test-Root umgeschrieben werden
- explizite Fixture-/Test-Roots bleiben durch den Test-Root-Vertrag abgesichert
- ein Worker-Fehler vor dem ersten Recovery-Schritt kann nicht mehr als erfolgreicher FULL-Restore gemeldet werden
- Read-only-Recovery-Quelle und Host-Docker-Isolation bleiben verpflichtend

### Dynamische backup-gebundene CURRENT-Release-Bindung

Wizard und Experten-CLI verwenden jetzt dieselbe Source of Truth für CURRENT-Releases in isolierten Realtests.

Für ein ausgewähltes Backup-Set wird die CURRENT-Release-Identität aus dem backup-gebundenen Release-Vertrag genau dieses Recovery-Sets aufgelöst. Eine veraltete statische CURRENT-Identität darf die ausgewählten Backup-Metadaten nicht überschreiben.

Der Vertrag bleibt fail-closed:

- exakte Versionsübereinstimmung erforderlich
- exakte Image-Identität erforderlich
- fehlende oder mehrdeutige backup-gebundene Release-Artefakte werden abgewiesen
- Schema-/Contract-Fehler bleiben von Identitätsabweichungen getrennt
- kein Same-Version-Fallback und keine stille Release-Substitution

### Härtung des Wizard-Worker-Roots

Ein fokussierter Realtest hat einen Fehler beim Worker-Start aufgedeckt, bevor ein Recovery-Schritt ausgeführt wurde.

Der geführte Wizard leitete den Worker-Test-Root fälschlich aus dem Parent-Verzeichnis seines State-Verzeichnisses ab. In einem echten isolierten Lauf führte das zum expliziten Test-Root-Gate und zum Abbruch vor der ersten Recovery-Aktion.

K56 verwendet jetzt einen expliziten State-/Log-Root-Vertrag:

- Standard-State-/Log-Roots eines Realtests starten den Worker ohne Test-Root-Override
- explizite Fixture-/Test-Roots müssen auf eine gemeinsame Basis zeigen und behalten das Test-Root-Gate
- mehrdeutige Root-Kombinationen scheitern fail-closed
- Execute und Resume verwenden dieselben Bindungsregeln

Das Test-Only-Environment-Gate bleibt ein Sicherheitsmechanismus und wird nicht als Realtest-Workaround verwendet.

### Korrekte Abschlussberichte

Der fokussierte Fehler hat zusätzlich einen ungenauen Report-Fallback offengelegt: Ein noch nicht abgeschlossener Runtime-State konnte geplante Service-Outcomes übernehmen und als FULL erscheinen.

K56 verlangt jetzt einen tatsächlich abgeschlossenen Runtime-State, bevor FULL/PARTIAL-Service-Outcomes als erfolgreicher Abschluss ausgewiesen werden. PLANNED- oder RUNNING-Zustände dürfen nicht zu einem abgeschlossenen Restore-Ergebnis hochgestuft werden.

### Aktuelle Validierungsgrenze

Ein neuer fokussierter isolierter DeviceWatchdog-`APP_FULL`-Realtest ist der nächste aktive Validierungsschritt.

Zum Zeitpunkt dieses Dokumentationsupdates läuft dieser fokussierte Test noch und wird **nicht** als PASS ausgewiesen.

Dieser Meilenstein beansprucht **nicht**:

- einen erfolgreichen fokussierten DeviceWatchdog-Full-App-Restore nach dem K56-Worker-Root-Fix
- einen erfolgreichen Full-Server-Restore
- eine Disaster-Recovery-Zertifizierung
- Produktionsreife

### Trennung öffentlich/privat

Das öffentliche Repository bleibt ein sanitisiertes Engineering-Teilprojekt. Roharchive, private Backup-Daten, Zugangsdaten, Hostnamen, private Infrastrukturpfade, Maschinenidentitäten, Run-IDs und Roh-Evidenz bleiben außerhalb des Repositories.
