# HP Server Recovery

> **Deutsch** | [English](README.md)

**Fail-closed Disaster Recovery für selbst gehostete Linux-Server – Wiederherstellung erst nach belastbarem Nachweis.**

HP Server Recovery bindet Backup-Quelle, Snapshot, Release-Identität, Zielidentität und Recovery-Zustand, bevor destruktive Aktionen erlaubt werden. Fehlende, veraltete oder mehrdeutige Nachweise stoppen den Lauf. Hinzu kommen isolierte Restore-/Runtime-Zertifizierung, Prüfungen gegen Secret-Leaks, fortsetzbarer auditierbarer Zustand und explizite Cleanup-Gates für anwendungsbewusste Wiederherstellung.

Das öffentliche Repository ist bewusst ein bereinigter, reproduzierbarer Engineering-Ausschnitt. Produktive Backups, Zugangsdaten, persönliche Kennungen und Maschinenidentitäten sind ausgeschlossen.

> **Status — 2026-10-16:** Das private Recovery-Paket hat isoliertes FULL_SERVER-Recovery, die K59-Fresh-Host-Bootstrap-Validierung und die K60-Real-Runtime-Zertifizierung für das fail-closed Onboarding einer unbekannten Anwendung bestanden. Die abschließende Zertifizierung eines vollständigen Restores auf einem frisch installierten Host einschließlich Reboot steht noch aus. Das öffentliche Repository ist kein sofort einsetzbares produktives Recovery-Image.

## Recovery-Modell im Überblick

```text
Backup-Quelle
     |
     v
Erkennen + Inventarisieren
     |
     v
Snapshot + Manifeste + Release-Identität binden
     |
     v
Deterministischer Restore-Plan
     |
     v
Safety- + Ziel- + Secret-Gates
     |
     v
Isolierter Restore + Runtime-Verifikation
     |
     v
Zertifikat
     |
     v
Realer Restore
     |
     v
Integrität + Cleanup + Reboot-Verifikation
```

Die Kernregel lautet: **Discovery ist keine Autorisierung.** Fehlende, veraltete oder mehrdeutige Nachweise führen zum Abbruch statt zu Annahmen.

## Unterschied zu ReaR

[Relax-and-Recover (ReaR)](https://relax-and-recover.org/) ist ein ausgereiftes Linux-Disaster-Recovery-System mit Schwerpunkt auf Rescue-Umgebung, Storage-Layout und Backup-/Restore-Workflow. HP Server Recovery soll ReaR bei Rescue-Medien und Bare-Metal-Fähigkeiten nicht ersetzen.

Der Schwerpunkt liegt bewusst auf einer streng fail-closed ausgelegten **Application-Recovery-Contract-Schicht**: explizite Bindung von Quelle, Snapshot, Manifesten und Release-Identität; exakte Anwendungs-/Runtime-Identität; isolierte Runtime-Prüfung; und keine Restore-Freigabe unbekannter Anwendungen ohne bestandenen isolierten Restore-/Runtime-Nachweis.

„Strenger“ bedeutet hier ausschließlich **mehr fail-closed Evidence-Gates rund um den Anwendungs-Restore**, nicht eine größere Vollständigkeit als ReaR als allgemeines Linux-Disaster-Recovery-System.

Siehe auch [Warum HP Server Recovery?](docs/WHY-HP-SERVER-RECOVERY-DE.md) sowie die englische Originalfassung [Why HP Server Recovery?](docs/WHY-HP-SERVER-RECOVERY.md).

## Öffentlicher 5-Minuten-Schnellstart

Der Schnellstart führt ausschließlich das bereinigte öffentliche Testpaket mit synthetischen Fixtures aus. Produktive Backups werden nicht berührt und es erfolgt kein destruktiver System-Restore.

Voraussetzungen: Linux/macOS/WSL, Git, Python 3.12+ und `pip`.

```bash
git clone https://github.com/Zwitsch/hp-server-recovery.git
cd hp-server-recovery
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --disable-pip-version-check PyYAML
bash demo.sh
```

Ein erfolgreicher Lauf endet mit:

```text
DEMO_RESULT=PASS
```

`demo.sh` kompiliert die öffentlichen Python-Quellen und führt dieselben drei bereinigten Regression-Suites aus wie GitHub Actions. Es enthält weder produktive Backup-Pfade noch destruktive Restore-Befehle.

## Ziele

HP Server Recovery soll die Wiederherstellung eines selbst gehosteten Linux-Servers reproduzierbar, testbar und standardmäßig konservativ machen:

- fail-closed bei fehlenden oder mehrdeutigen Recovery-Eingaben, Zielidentitäten oder Safety-Bindings
- Trennung generischer Recovery-Logik von hostspezifischer Konfiguration
- Manifest- und Release-Identitätsprüfung vor destruktiven Aktionen
- Fixture-basierte Tests und isolierte reale Restore-Tests
- auditierbarer Recovery-Zustand, Befehlsausführung und Cleanup
- keine Secrets, produktiven Payloads oder Maschinenidentitäten im Quell-Repository

## Sicherheitsmodell

Destruktive Aktionen sind explizit gegatete Operationen. Isolierte Realtests benötigen gebundene Zielidentitäten, erlaubte/verbotene Hostnamen, geschützte Pfadpräfixe, schreibgeschützte Recovery-Quellen und eine isolierte Container-Runtime. Fehlende Bindings führen zum Abbruch statt zu permissiven Fallbacks.

Persistente Reports und Audit-Daten werden vor Abschluss auf Secret-Marker-Leaks geprüft.

Siehe `SECURITY.md` und `docs/SAFETY-MODEL.md`.

## Aktuelle private Zertifizierung — K59/K60, 2026-10-16

Aktueller bereinigter Validierungsstand:

- K58 Restore-Engine und vorheriger isolierter FULL_SERVER-Restore: **zertifizierte Baseline**
- K59 Fresh-Host-Preflight, Paket-/Repository-Plan, Mapped-Root-Apply, Identitäten, Metadaten und Boot-Vorbereitung: **PASS**
- K59 USB-/Recovery-Einstiegspunkt-Integration: **PASS**
- K60 fail-closed Candidate-/Classification-/Certificate-Kette für unbekannte Anwendungen: **PASS**
- K60 duales Plan-/Runtime-Certificate-Gate: **PASS**
- K60 tatsächlicher isolierter Unknown-App-Restore inklusive Runtime-/Integritätszertifizierung: **PASS**
- finales Manifest-Reseal nach K60: **PASS**
- letzte autoritative private Root-Canonical-Regression: **1376/1376 PASS**
- Cleanup der isolierten Docker/containerd-Runtime und Socket-Grenze: **PASS**
- vollständiger Restore auf frisch installiertem Host + Reboot: **PENDING**

K60 verhindert ausdrücklich, dass reine Metadaten-Erkennung eine neue Anwendung stillschweigend autorisiert. Eine erkannte Anwendung bleibt `PENDING_ONBOARDING` und nicht wiederherstellbar, bis ein isolierter Restore-/Runtime-Report bestanden wurde und ein gebundenes Zertifikat den Restore explizit erlaubt.

Bei taglosen OCI-Archiven werden Archiv-/Config-Identität und Docker-Runtime-Adressierbarkeit als getrennte unveränderliche Bindings behandelt.

## Frühere Meilensteine

Das Repository enthält detaillierte Meilenstein-Dokumente der K56–K58-Entwicklung sowie der Immich/Filen-Cold-Storage-Arbeiten. Historische Checkpoint-Zahlen sind nicht mit dem aktuellen Regression-Stand gleichzusetzen. Autoritativ ist der oben genannte K60-Stand.

Beispiele:

- K57 L2- und COMBINED-Cold-Piloten: **je 100/100 BLAKE3 PASS**
- Immich/Filen-Cold-Archiv: **81.328/81.328 BLAKE3 PASS**
- K58 Capture-/Datenbank-/Runtime-Phasen: in die spätere zertifizierte K59/K60-Baseline integriert

## Repository-Struktur

- `lib/hp_recovery/` — wiederverwendbare Recovery-Engine
- `bin/` — Kommandozeilen-Einstiegspunkte
- `config/` — bereinigte Beispielkonfiguration
- `tests/` — automatisierte Tests und synthetische Fixtures
- `runtime-data/` — synthetische Katalogdaten des Testpakets
- `manifests/` — Integritätsmanifest des synthetischen Pakets
- `payload/` — ausschließlich synthetische Testverträge, keine produktiven Payloads
- `demo.sh` — Ein-Befehl-Demo der öffentlichen synthetischen Regression

## Öffentliche und private Validierung

Das öffentliche Repository enthält absichtlich nur bereinigte Logik, Tests und synthetische Fixtures. Das private Recovery-System enthält zusätzlich hostspezifische Verträge, Recovery-Payload-Metadaten, isolierte Runtime-Komponenten und Zertifizierungstests. Seine letzte autoritative Root-Canonical-Regression nach der K60-Real-Runtime-Zertifizierung lautet **1376/1376 PASS**.

Private Resultate werden getrennt ausgewiesen, damit nicht veröffentlichte Tests niemals so dargestellt werden, als seien sie aus dem öffentlichen Repository ausführbar.

## Noch offene End-to-End-Abnahme

Die endgültige Projektabnahme bleibt bewusst offen, bis der komplette Ablauf auf einer tatsächlich frisch installierten Ubuntu-22.04-Installation nachgewiesen wurde:

1. Start über den vorgesehenen Recovery-/USB-Einstiegspunkt
2. Fresh-Host-Bootstrap und dediziertes Datenziel validieren
3. Recovery-Quelle/Snapshot auswählen und binden
4. vollständigen Restore über die Recovery-Engine durchführen
5. Anwendungen, Datenbanken und Integritäts-Gates zertifizieren
6. wiederhergestellten Host neu starten
7. erforderliche System-/Anwendungs-/Integritätsprüfungen nach dem Reboot wiederholen

Bis dies erfolgreich abgeschlossen ist, beansprucht das Projekt keine endgültige Bare-Metal-/Fresh-Host-Disaster-Recovery-Zertifizierung.
